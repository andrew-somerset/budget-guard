# Budget Guard — Results Explained

Short guide to the headline figures/tables: what they show and why they matter for
the write-up. **Authoritative numbers live in the generated `tables/`.** A 2026-07-21
audit retracted per-prefix “SPCI self-heals to 0.90”; rollout-safe evaluation is the
claim to cite.

**Claim in one line.** A training-free conformal wrapper turns logged-agent budget
signals into calibrated remaining-budget intervals that adapt under deployment shift,
and a feasibility abort rule makes stopping doomed runs economically useful.

Splits are always **by rollout**, never by prefix.

## Metrics

| Metric | Meaning |
| --- | --- |
| Coverage | Fraction of prefixes where true remaining budget `y` is inside the interval. Target ≈ 0.90 (α = 0.10). |
| Normalized width | Interval width ÷ a remaining-budget scale; smaller is sharper at the same coverage. |
| Frac. unbounded | Share of infinite-width intervals (coverage recovered by giving up). |
| False-abort rate | Among runs that would succeed, fraction stopped early. |
| Doomed-savings frac. | Fraction of doomed-run spend avoided by aborting. |
| Cost of pass | Total spend ÷ number of successful runs. |

## C1 — Calibrated intervals

**Gap / coverage (`gap_sokoban`, `coverage_main`).** Agent self-report is uncalibrated
(~0.2–0.5 here; ~47% in BAGEN). Offline split conformal already hits ~0.90 when
calibration and test match. Constant-quantile is close on some envs but under-covers
searchr1; features and online methods earn their keep on sharpness and shift.

**Label efficiency.** A handful of CAL rollouts (about 5–8) reaches ~0.90; with 2
rollouts the finite-sample correction fails **safe** (over-covers), not silent
under-coverage.

**Transfer.** Frozen split-CQR collapses under model/env swap. Online methods recover
much of the coverage using only labels a deployed guard could observe. Cite
rollout-safe numbers (cross-env SPCI recovery **0.80** at 0% unbounded, not 0.90).
ACI can look covered while emitting many unbounded
intervals.

**All-19 breadth.** `run_allruns` is on `main`; it is no longer data-blocked.

## C2 — Multi-resource (Warehouse)

Independent 90% margins under-cover **jointly** (~0.80). Bonferroni restores joint
coverage (~0.95) via a stricter per-axis α; copula uses CAL dependence to get near
nominal with less width waste.

Censored rows (`can_finish=False`) are informative, not missing. Naive drop
under-covers the expensive failures; bound / resource_bound / KM / gated intervals
are the methods options (see `tables/censored_upper.csv`).

## C3 / C4 — Stopping and cost-of-pass

Warehouse: feasibility guard at modest δ saves **~86%** of doomed-$ at **0%** false
abort and roughly halves $/success (~$1.61M → ~$0.87M) at full pass retention.

Sokoban: short runs, modest savings unless false-abort rises.
SWE-bench: a hard token cap is structurally strong when doom *is* cap exceedance.

C3 is the frontier; C4 prices the operating point.

## How the pieces fit

Transfer (deployment shift) should lead the paper. Warehouse abort + cost-of-pass
lead the economics. Honest limits: logged (counterfactual-free) evaluation;
closed-loop selection bias; SWE-bench cap strength.

## Reproduce

See the README on `main` (`scripts/fetch_bagen.py`, `run_transfer`,
`run_transfer_warehouse`). Figures and tables are gitignored.
