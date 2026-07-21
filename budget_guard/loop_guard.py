"""Stateful, task-neutral multi-resource guard for long-horizon agent loops."""
from __future__ import annotations

from collections import deque
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import pickle
from pathlib import Path
import platform
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, _cqr_scores, _finite_sample_quantile, _fit_cqr
from .economic import fit_feasibility
from .loop_features import LoopDataset, build_loop_dataset, prefix_feature_row
from .loop_policy import (
    DefaultInterventionPolicy,
    GuardState,
    InterventionPolicy,
    LoopDecision,
    PolicyInput,
    ResourceInterval,
)
from .loop_schema import (
    ResourceLedger,
    ResourceSpec,
    RunAbort,
    RunFinish,
    RunStart,
    RunTrace,
    StepUsage,
    UsageCorrection,
)
from .multiresource import _joint_rank_qhats

ARTIFACT_VERSION = 1


def _ordered_unique(values: Sequence[Any]) -> list[Any]:
    return list(dict.fromkeys(values))


def _rollout_max_scores(
    score_matrix: np.ndarray, groups: np.ndarray
) -> tuple[np.ndarray, list[Any]]:
    order = _ordered_unique(groups.tolist())
    rows = [np.max(score_matrix[groups == group], axis=0) for group in order]
    return np.asarray(rows, dtype=float), order


def _ordered_predictions(mlo: Any, mhi: Any, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Order independently fitted quantiles; crossings must never create invalid bands."""
    first = np.asarray(mlo.predict(X), dtype=float)
    second = np.asarray(mhi.predict(X), dtype=float)
    return np.minimum(first, second), np.maximum(first, second)


def _calibrate_gate_threshold(
    probabilities: np.ndarray,
    feasible: np.ndarray,
    groups: np.ndarray,
    delta: float,
) -> float:
    """Threshold the minimum prefix probability per feasible calibration rollout."""
    minima = _successful_rollout_minima(probabilities, feasible, groups)
    return _gate_threshold_from_minima(minima, delta)


def _successful_rollout_minima(
    probabilities: np.ndarray,
    feasible: np.ndarray,
    groups: np.ndarray,
) -> np.ndarray:
    minima = []
    for group in _ordered_unique(groups.tolist()):
        mask = groups == group
        if bool(feasible[mask][0]):
            minima.append(float(np.min(probabilities[mask])))
    return np.asarray(minima, dtype=float)


def _gate_threshold_from_minima(minima: Sequence[float], delta: float) -> float:
    values = np.sort(np.asarray(minima, dtype=float))
    n = len(values)
    if n == 0:
        return -np.inf
    rank = int(np.floor((n + 1) * delta))
    if rank < 1:
        return -np.inf
    return float(values[min(rank, n) - 1])


class LoopBudgetGuard:
    """Online, jointly calibrated monitor for arbitrary additive resource sets.

    The prediction models and gate are fit from naturally finished historical traces.
    During deployment, all decisions in one run use the same existing calibration
    window. Only a naturally completed, successful, in-budget run contributes one new
    vector of worst-prefix resource errors after it finishes. Aborted or failed runs do
    not receive invented completion labels.
    """

    def __init__(
        self,
        *,
        models: Mapping[str, tuple[Any, Any]],
        feature_columns: Sequence[str],
        schema_signature: tuple[tuple[str, str, str], ...],
        score_window: Sequence[np.ndarray],
        alpha: float,
        window_rollouts: int,
        min_evidence_runs: int,
        context_keys: Sequence[str],
        progress_keys: Sequence[str],
        calibration_scheme: str,
        gate_model: Any | None,
        gate_threshold: float | None,
        gate_success_window: Sequence[float],
        gate_delta: float,
        policy: InterventionPolicy,
        online: bool = True,
    ):
        self._models = dict(models)
        self._feature_columns = tuple(feature_columns)
        self._schema_signature = schema_signature
        self.resource_names = tuple(item[0] for item in schema_signature)
        self.alpha = alpha
        self.window_rollouts = window_rollouts
        self.min_evidence_runs = min_evidence_runs
        self.context_keys = tuple(context_keys)
        self.progress_keys = tuple(progress_keys)
        if calibration_scheme not in {"joint", "independent"}:
            raise ValueError("calibration_scheme must be 'joint' or 'independent'")
        self.calibration_scheme = calibration_scheme
        self._gate_model = gate_model
        self.gate_threshold = gate_threshold
        self.gate_delta = gate_delta
        self._gate_success_window: deque[float] = deque(
            (float(value) for value in gate_success_window),
            maxlen=window_rollouts if online else None,
        )
        self.policy = policy
        self.online = online
        self._score_window: deque[np.ndarray] = deque(
            (np.asarray(row, dtype=float).copy() for row in score_window),
            maxlen=window_rollouts if online else None,
        )
        self._ledger: ResourceLedger | None = None
        self._last_decision: LoopDecision | None = None
        self._current_gate_probabilities: list[float] = []

    @classmethod
    def from_traces(
        cls,
        traces: Iterable[RunTrace],
        *,
        alpha: float = DEFAULT_ALPHA,
        window_rollouts: int = 10,
        min_evidence_runs: int = 5,
        train_frac: float = 0.7,
        gate_delta: float = 0.1,
        seed: int = 0,
        context_keys: Sequence[str] = (),
        progress_keys: Sequence[str] = (),
        calibration_scheme: str = "joint",
        policy: InterventionPolicy | None = None,
        online: bool = True,
    ) -> "LoopBudgetGuard":
        traces = list(traces)
        if calibration_scheme not in {"joint", "independent"}:
            raise ValueError("calibration_scheme must be 'joint' or 'independent'")
        if not 0 < train_frac < 1:
            raise ValueError("train_frac must be between 0 and 1")
        if window_rollouts < 1 or min_evidence_runs < 1:
            raise ValueError("window_rollouts and min_evidence_runs must be positive")
        data = build_loop_dataset(
            traces, context_keys=context_keys, progress_keys=progress_keys
        )
        observed_ids = _ordered_unique(data.groups[data.feasibility_observed].tolist())
        if len(observed_ids) < 4:
            raise ValueError("at least four naturally finished historical runs are required")
        rng = np.random.default_rng(seed)
        shuffled = rng.permutation(observed_ids)
        cut = int(np.clip(round(len(shuffled) * train_frac), 1, len(shuffled) - 1))
        train_ids, cal_ids = set(shuffled[:cut]), set(shuffled[cut:])
        train_mask = np.isin(data.groups, list(train_ids))
        cal_mask = np.isin(data.groups, list(cal_ids))
        interval_train = train_mask & (data.feasible == 1) & data.y.notna().all(axis=1).to_numpy()
        interval_cal = cal_mask & (data.feasible == 1) & data.y.notna().all(axis=1).to_numpy()
        if len(set(data.groups[interval_train])) < 2 or len(set(data.groups[interval_cal])) < 1:
            raise ValueError("need successful runs in both train and calibration splits")

        models: dict[str, tuple[Any, Any]] = {}
        cal_columns = []
        for resource in data.resource_names:
            target = data.y[resource].to_numpy(dtype=float)
            mlo, mhi = _fit_cqr(
                data.X.loc[interval_train], target[interval_train], alpha
            )
            models[resource] = (mlo, mhi)
            cal_lo, cal_hi = _ordered_predictions(mlo, mhi, data.X.loc[interval_cal])
            cal_columns.append(
                _cqr_scores(
                    cal_lo,
                    cal_hi,
                    target[interval_cal],
                )
            )
        cal_score_matrix = np.column_stack(cal_columns)
        score_window, _ = _rollout_max_scores(
            cal_score_matrix, data.groups[interval_cal]
        )

        gate_train = train_mask & data.feasibility_observed
        gate_cal = cal_mask & data.feasibility_observed
        gate_model = None
        gate_threshold = None
        gate_success_window: np.ndarray = np.array([], dtype=float)
        gate_labels = data.feasible[gate_train]
        if len(np.unique(gate_labels)) >= 2:
            gate_model = fit_feasibility(data.X.loc[gate_train], gate_labels.astype(bool))
            probabilities = gate_model.predict_proba(data.X.loc[gate_cal])[:, 1]
            gate_success_window = _successful_rollout_minima(
                probabilities,
                data.feasible[gate_cal].astype(bool),
                data.groups[gate_cal],
            )
            gate_threshold = _gate_threshold_from_minima(gate_success_window, gate_delta)

        first_resources = traces[0].start.resources
        signature = tuple(
            (resource.name, resource.unit, resource.aggregation)
            for resource in first_resources
        )
        return cls(
            models=models,
            feature_columns=data.X.columns,
            schema_signature=signature,
            score_window=score_window,
            alpha=alpha,
            window_rollouts=window_rollouts,
            min_evidence_runs=min_evidence_runs,
            context_keys=context_keys,
            progress_keys=progress_keys,
            calibration_scheme=calibration_scheme,
            gate_model=gate_model,
            gate_threshold=gate_threshold,
            gate_success_window=gate_success_window,
            gate_delta=gate_delta,
            policy=policy or DefaultInterventionPolicy(),
            online=online,
        )

    @property
    def evidence_runs(self) -> int:
        return len(self._score_window)

    @property
    def gate_evidence_runs(self) -> int:
        return len(self._gate_success_window)

    @property
    def active(self) -> bool:
        return self._ledger is not None and not self._ledger.closed

    @property
    def last_decision(self) -> LoopDecision | None:
        return self._last_decision

    def start(
        self,
        run_id: str,
        resources: Sequence[ResourceSpec],
        context: Mapping[str, Any] | None = None,
        *,
        allow_partial_usage: bool = False,
    ) -> None:
        if self.active:
            raise RuntimeError("finish or abort the active run before starting another")
        signature = tuple(
            (resource.name, resource.unit, resource.aggregation) for resource in resources
        )
        if signature != self._schema_signature:
            raise ValueError("live resources do not match the guard's trained schema")
        self._ledger = ResourceLedger(
            RunStart(run_id, tuple(resources), dict(context or {})),
            allow_partial_usage=allow_partial_usage,
        )
        self._last_decision = None
        self._current_gate_probabilities = []

    def after_step(
        self,
        usage: Mapping[str, float] | StepUsage,
        progress: Mapping[str, float] | None = None,
        *,
        step_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> LoopDecision:
        ledger = self._require_active()
        if isinstance(usage, StepUsage):
            step = usage
        else:
            next_id = step_id or str(len(ledger.steps) + 1)
            step = StepUsage(next_id, dict(usage), dict(progress or {}), dict(metadata or {}))
        ledger.record(step)
        return self._decide_current(ledger)

    def correct_usage(
        self,
        step_id: str,
        usage: Mapping[str, float],
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> LoopDecision:
        """Apply delayed authoritative telemetry and recompute the current decision."""
        ledger = self._require_active()
        ledger.correct(UsageCorrection(step_id, dict(usage), dict(metadata or {})))
        # Recompute from corrected history without recording another step or another
        # gate probability for the same decision point.
        if self._current_gate_probabilities:
            self._current_gate_probabilities.pop()
        return self._decide_current(ledger)

    def _decide_current(self, ledger: ResourceLedger) -> LoopDecision:
        snapshot = ledger.snapshot()
        X = self._live_features(ledger)
        qhats = self._current_qhats()
        intervals: dict[str, ResourceInterval] = {}
        for index, resource in enumerate(self.resource_names):
            mlo, mhi = self._models[resource]
            predicted_lo, predicted_hi = _ordered_predictions(mlo, mhi, X)
            base_lo, base_hi = float(predicted_lo[0]), float(predicted_hi[0])
            qhat = float(qhats[index])
            if np.isfinite(qhat):
                effective_qhat = max(qhat, -(base_hi - base_lo) / 2)
                lo = max(base_lo - effective_qhat, 0.0)
                hi = max(base_hi + effective_qhat, lo)
            else:
                lo, hi = 0.0, float("inf")
            intervals[resource] = ResourceInterval(lo, hi)

        finish_probability = None
        if self._gate_model is not None:
            finish_probability = float(self._gate_model.predict_proba(X)[0, 1])
            self._current_gate_probabilities.append(finish_probability)
        if not np.isfinite(qhats).all():
            state = GuardState.FAIL_SAFE
        elif self.evidence_runs < self.min_evidence_runs:
            state = GuardState.WARMING_UP
        elif self._gate_model is None:
            state = GuardState.DEGRADED
        else:
            state = GuardState.ACTIVE
        decision = self.policy.decide(
            PolicyInput(
                resources=ledger.start_event.resources,
                spent=snapshot.spent,
                intervals=intervals,
                finish_probability=finish_probability,
                gate_threshold=self.gate_threshold,
                state=state,
                evidence_runs=self.evidence_runs,
                progress=snapshot.latest_progress,
            )
        )
        self._last_decision = decision
        return decision

    def finish(
        self,
        success: bool,
        totals: Mapping[str, float] | None = None,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> RunTrace:
        ledger = self._require_active()
        trace = ledger.finish(RunFinish(success, totals, dict(metadata or {})))
        if self.online and trace.successful and len(trace.steps) >= 2:
            # A successful run that exceeded a configured budget is not a valid
            # successful-within-budget interval label.
            final_totals = trace.totals
            assert final_totals is not None
            inside = all(
                final_totals[resource.name] <= resource.budget
                for resource in trace.start.resources
            )
            if inside:
                self._score_window.append(self._trace_max_scores(trace))
                if self._current_gate_probabilities:
                    self._gate_success_window.append(min(self._current_gate_probabilities))
                    self.gate_threshold = _gate_threshold_from_minima(
                        self._gate_success_window, self.gate_delta
                    )
        self._ledger = None
        self._current_gate_probabilities = []
        return trace

    def abort(
        self,
        reason: str,
        observed_lower_bounds: Mapping[str, float] | None = None,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> RunTrace:
        ledger = self._require_active()
        trace = ledger.abort(
            RunAbort(reason, dict(observed_lower_bounds or ledger.spent), dict(metadata or {}))
        )
        # Deliberately no interval-window update: completion totals are unknown.
        self._ledger = None
        self._current_gate_probabilities = []
        return trace

    def save(self, path: str | Path) -> None:
        """Persist a versioned trusted artifact plus auditable checksum metadata.

        Never load pickle from an untrusted source; a checksum detects corruption or
        accidental mismatch, not a malicious artifact accompanied by its own manifest.
        """
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            pickle.dump(
                {
                    "artifact_version": ARTIFACT_VERSION,
                    "metadata": self.artifact_metadata(),
                    "guard": self,
                },
                handle,
            )
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        manifest = {**self.artifact_metadata(), "sha256": digest, "artifact": destination.name}
        destination.with_suffix(destination.suffix + ".json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: str | Path) -> "LoopBudgetGuard":
        """Load an artifact created by :meth:`save` from a trusted source only."""
        source = Path(path)
        manifest_path = source.with_suffix(source.suffix + ".json")
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
            if actual != manifest.get("sha256"):
                raise ValueError("guard artifact checksum does not match its manifest")
        with source.open("rb") as handle:
            payload = pickle.load(handle)
        if payload.get("artifact_version") != ARTIFACT_VERSION:
            raise ValueError("unsupported guard artifact version")
        guard = payload.get("guard")
        if not isinstance(guard, cls):
            raise ValueError("artifact does not contain a LoopBudgetGuard")
        guard._ledger = None
        guard._last_decision = None
        guard._current_gate_probabilities = []
        return guard

    def artifact_metadata(self) -> dict[str, Any]:
        packages = {}
        for package in ("numpy", "pandas", "scikit-learn", "lightgbm"):
            try:
                packages[package] = version(package)
            except PackageNotFoundError:
                packages[package] = None
        return {
            "artifact_version": ARTIFACT_VERSION,
            "python": platform.python_version(),
            "packages": packages,
            "resources": [
                {"name": name, "unit": unit, "aggregation": aggregation}
                for name, unit, aggregation in self._schema_signature
            ],
            "feature_columns": list(self._feature_columns),
            "context_keys": list(self.context_keys),
            "progress_keys": list(self.progress_keys),
            "alpha": self.alpha,
            "calibration_scheme": self.calibration_scheme,
            "window_rollouts": self.window_rollouts,
            "evidence_runs": self.evidence_runs,
            "gate_evidence_runs": self.gate_evidence_runs,
        }

    def _require_active(self) -> ResourceLedger:
        if self._ledger is None or self._ledger.closed:
            raise RuntimeError("start a run before recording, finishing, or aborting")
        return self._ledger

    def _current_qhats(self) -> np.ndarray:
        scores = np.asarray(self._score_window, dtype=float)
        if self.calibration_scheme == "joint":
            return _joint_rank_qhats(scores, self.alpha)[0]
        if scores.size == 0:
            return np.full(len(self.resource_names), np.inf)
        per_resource_alpha = self.alpha / len(self.resource_names)
        return np.asarray(
            [
                _finite_sample_quantile(scores[:, index], per_resource_alpha)
                for index in range(len(self.resource_names))
            ],
            dtype=float,
        )

    def _live_features(self, ledger: ResourceLedger) -> pd.DataFrame:
        row = prefix_feature_row(
            ledger.start_event,
            ledger.steps,
            context_keys=self.context_keys,
            progress_keys=self.progress_keys,
        )
        X = pd.DataFrame([row]).reindex(columns=self._feature_columns)
        return X

    def _trace_max_scores(self, trace: RunTrace) -> np.ndarray:
        data: LoopDataset = build_loop_dataset(
            [trace], context_keys=self.context_keys, progress_keys=self.progress_keys
        )
        X = data.X.reindex(columns=self._feature_columns)
        columns = []
        for resource in self.resource_names:
            mlo, mhi = self._models[resource]
            target = data.y[resource].to_numpy(dtype=float)
            predicted_lo, predicted_hi = _ordered_predictions(mlo, mhi, X)
            columns.append(_cqr_scores(predicted_lo, predicted_hi, target))
        return np.max(np.column_stack(columns), axis=0)
