# Budget Guard — Results Explained

Guide to the headline figures and tables: what each result shows, how to read it, and
how to regenerate it. **Authoritative numbers live in the generated `tables/`** after
you run the experiment scripts; figures are gitignored and rebuilt locally.

**Claim in one line.** A training-free conformal wrapper turns logged-agent budget
signals into calibrated remaining-budget intervals that adapt under deployment shift,
and a feasibility abort rule makes stopping doomed runs economically useful.

## Evaluation protocol

- **Splits are by rollout**, never by prefix. Train / calibration / test rollouts are
  disjoint; every prefix from a rollout stays in the same split.
- **Rollout-safe online evaluation.** For transfer and online methods, a rollout's
  label is revealed only after that rollout finishes. Prefixes inside an in-flight
  rollout are never used to recalibrate mid-stream. Numbers quoted here use this
  protocol.
- **Audit note (2026-07-21).** An earlier per-prefix evaluation made online methods
  look as if they recovered to ~0.90 coverage under cross-environment transfer. Under
  rollout-safe evaluation, windowed-CQR recovery on SWE-bench is **0.80** at 0%
  unbounded — cite the rollout-safe tables, not the inflated prefix-level numbers.

## Method names

The online sliding-window method is labeled **windowed-CQR** in figures and tables.
It is inspired by sequential predictive conformal inference (SPCI; Xu & Xie 2023) but
is not a literal SPCI implementation — it applies a fixed-size calibration window to
split-CQR scores. See `budget_guard/conformal.py` for the distinction.

## Metrics

| Metric | Meaning |
| --- | --- |
| Coverage | Fraction of prefixes where true remaining budget `y` is inside the interval. Target ≈ 0.90 (α = 0.10). |
| Normalized width | Interval width ÷ a remaining-budget scale; smaller is sharper at the same coverage. |
| Frac. unbounded | Share of infinite-width intervals (coverage recovered by giving up). Hatched bars in coverage plots mark these. |
| False-abort rate | Among runs that would succeed, fraction stopped early. |
| Doomed-savings frac. | Fraction of doomed-run spend avoided by aborting. |
| Cost of pass | Total spend ÷ number of successful runs. |

## Calibrated intervals

**Coverage (`figures/coverage_main.png`).** Headline bar chart across Sokoban, SearchR1,
and SWE-bench. Compares agent self-report (~0.2–0.5 here; ~47% in BAGEN) against
offline split conformal and online methods (ACI-CQR, windowed-CQR, DtACI). When
calibration and test match, offline split-CQR already hits ~0.90; features and online
methods earn their keep on sharpness and under shift.

**Gap diagnostics (`figures/gap_<env>.png`).** Per-environment two-panel figure:
marginal coverage vs split-absres / split-CQR / Mondrian-CQR, and coverage conditional
on turn depth. Motivates conditional and Mondrian fixes when marginal coverage hides
depth-wise failure.

**Label efficiency (`figures/label_efficiency_sokoban.png`).** How many completed
calibration rollouts split-CQR needs to reach nominal coverage. A handful (about 5–8)
reaches ~0.90; with 2 rollouts the finite-sample correction fails **safe**
(over-covers), not silent under-coverage.

**Transfer (`figures/transfer_env.png`, `figures/transfer_swebench.png`).**
Cross-environment (same model, new task) and model-swap (same task, new model)
deployment. Frozen split-CQR collapses; online methods recover much of the coverage
using only labels a deployed guard could observe. Cross-env windowed-CQR recovery is
**0.80** on SWE-bench at 0% unbounded, not 0.90. ACI can look covered while emitting
many unbounded intervals — check `frac_unbounded` and hatched bars.

**All-run breadth (`figures/allruns.png`).** Coverage across every logged run in the
pinned BAGEN extract (single split seed; breadth, not variance).

**Conditional coverage (`figures/conditional_coverage.png`).** Split-CQR (one global
q̂) vs Mondrian-CQR (per depth bucket) across environments; includes worst-slice
coverage over k-buckets.

## Multi-resource (Warehouse)

**Joint vs marginal (`figures/final/joint_vs_marginal.png`).** Independent 90% margins
under-cover **jointly** (~0.80). Bonferroni restores joint coverage (~0.95) via a
stricter per-axis α; copula uses calibration-set dependence to get near nominal with
less width waste.

**Model-swap transfer (`figures/transfer_warehouse.png`).** Rollout-safe joint
adaptation when the guard calibrated on claude-opus-4.7 is deployed on other models,
with native time / warehouse / cost accounting.

**Censored calibration (`tables/censored_upper.csv`).** Rows with `can_finish=False`
are informative, not missing. Naive drop under-covers the expensive failures; bound,
resource_bound, KM, and gated intervals are the method options.

**Selective frontier (`figures/final/selective_frontier.png`).** Feasibility-gated
intervals on Warehouse: keeping fewer runs (higher δ) lifts coverage on the kept set.

## Stopping and cost-of-pass

**Abort frontiers (`figures/final/abort_frontier_warehouse.png`,
`figures/abort_frontier_<env>.png`).** False-abort rate vs doomed-run savings. The
abort frontier shows where early stopping trades feasibility errors for spend saved.

**Cost-of-pass (`figures/final/cost_of_pass_warehouse.png`,
`figures/cost_of_pass_<env>.png`).** Prices an operating point: fraction of passes
retained vs cost per success.

**Warehouse headline.** Feasibility guard at modest δ saves **~86%** of doomed-$ at
**0%** false abort and roughly halves $/success (~$1.61M → ~$0.87M) at full pass
retention.

**Sokoban.** Short runs, modest savings unless false-abort rises.

**SWE-bench.** A hard token cap is structurally strong when doom *is* cap exceedance.

## Pipeline schematic

**`figures/final/pipeline.png`** — methods figure (not a results plot): agent loop →
prefix features → conformal layer → abort decision, with rollout-end label feedback
that makes online methods deployment-faithful. Generated by `scripts/make_pipeline_figure.py`.

## Figure captions (paper)

On-figure PNG titles are descriptive setup lines for standalone review. For submission,
paste sentence-case `\caption{}` text from [`scripts/figure_captions.tex`](../scripts/figure_captions.tex)
after `\includegraphics` in LaTeX (NeurIPS §4.3). Figure numbers are assigned in the
paper, not burned into PNGs.

## How the pieces fit

1. **Coverage under shift** — transfer experiments show the guard survives deployment
   change when labels arrive rollout-by-rollout.
2. **Multi-resource joint guarantees** — Warehouse shows independent margins are not
   enough; joint/copula methods and censored handling matter.
3. **Economics** — abort frontiers and cost-of-pass connect calibrated intervals to
   dollars saved and price per success.

**Limitations.** All stopping numbers are from logged rollouts (counterfactual-free:
we observe what the agent spent, not what it would have spent if aborted earlier).
SWE-bench cap strength partly reflects that doom is often cap exceedance. Closed-loop /
performative evaluation (where aborting changes future behavior) is future work.

## Reproduce

Figures and tables are gitignored. From a fresh clone:

```bash
pip install -r requirements.txt          # or: pip install -e ".[experiments]"
python scripts/fetch_bagen.py          # pinned BAGEN revision

# submission figure + table set
make repro-paper                       # Docker, bit-identical linux/amd64
# or on the host (conda):
python -m budget_guard.run_final --full
python scripts/make_pipeline_figure.py
python scripts/make_costofpass_figure.py

python scripts/check_headline_numbers.py   # 11 headline claims
python scripts/check_paper_numbers.py      # 35 paper claims (after repro-paper tables exist)
```

Optional: `python scripts/make_results_pdf.py` assembles a 19-page review PDF.
`python scripts/repro_doctor.py` diagnoses environment / data / table mismatches.

See the [README](../README.md) for setup, Docker details, and the `BudgetGuard` API.
