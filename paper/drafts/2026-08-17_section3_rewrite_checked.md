# §3 — fact-checked, formalism restored, em dashes removed. Paste-ready.

Your rewrite, with: 8 em dashes removed; five restorations the rest of the paper
depends on (adaptive joint scheme, which §5.2 cross-references; the Table 1
anchor; the symbol δ, used by Table 1 and Figure 1's caption; the workshop
"verifier" framing; citations [17] and [24]); a short formal statement of the
interval construction, so the section is reimplementable; and about six
rhetorical constructions replaced with plain statements. The "routinely
violated" claim is now our own correction rather than an uncited swipe at
others. Voice and structure are yours.

---

## 3. Budget Guard

An agent is partway through a task. It has spent some tokens, taken some turns, and may or may not
finish. We want to say, right now, how much more it will need, and we want that answer to come with
a number attached: an interval that contains the true requirement 90% of the time.

Conformal prediction gives us that. The idea is simple enough to state in a sentence: take any
predictor, measure how badly it missed on data it never trained on, and widen its output by a high
quantile of those misses. Concretely, we fit two quantile regressors, one at α/2 and one at
1 − α/2, giving a band [*q̂*<sub>lo</sub>(*x*), *q̂*<sub>hi</sub>(*x*)]. On each of the *n*
calibration points we record how far the truth fell outside that band,
*s* = max(*q̂*<sub>lo</sub> − *y*, *y* − *q̂*<sub>hi</sub>), a quantity that is negative when the
point sat comfortably inside. Taking *q̂* to be the ⌈(*n*+1)(1 − α)⌉/*n* empirical quantile of those
*n* scores and issuing [*q̂*<sub>lo</sub>(*x*) − *q̂*, *q̂*<sub>hi</sub>(*x*) + *q̂*] yields an
interval that contains *y* with probability at least 1 − α. We use α = 0.1 throughout, and clip the
lower endpoint at zero since no run needs negative resources. The proof requires nothing about the
data except that the calibration runs and the deployment runs are exchangeable, and everything
difficult in this paper comes from the fact that they are not. Table 1 records, for each component
below, exactly which statement we claim and under what conditions.

**What the guard sees, and what it has to predict.** At turn *k*, Budget Guard sees only the past:
how much the agent has spent per turn, and its own estimate of what it still needs, if it offers
one. It predicts *y*, the resources the run still needs before it can finish. Two properties of *y*
shape everything downstream.

First, *y* cannot be known until the run is over. The consequence is easy to miss: a method that
observes turn *k*'s label before predicting turn *k*+1 is using information that will not exist at
deployment time, and its measured coverage is inflated. We had this wrong in an earlier version of
this evaluation, and correcting it cost ten points of headline cross-environment coverage (§5.2
reports the corrected figure). Labels are therefore released only at rollout boundaries, and every
method's internal state is frozen within a run.

Second, *y* does not exist at all for a run that can no longer finish: its label is undefined
rather than merely late. Half of our Warehouse prefixes are in this state, and they are precisely
the runs a budget guard exists to catch.

**Features.** Everything the guard uses comes from four families, all computable from the usage
stream alone: how far along the run is (the turn index); how much it has consumed (total spend,
and spend divided by turns, which is the burn rate); how it has been consuming recently (the last
turn, the mean of the last three, and the mean, spread, min, max and trend of per-turn usage); and
the agent's own estimate, when it gives one. Nothing that depends on the future (final totals,
success, feasibility) enters the feature matrix; we assert this in code rather than trusting
ourselves to have left it out. No weights, no logits, no environment internals: only the usage
accounting that provider APIs already return, which is what makes the guard a wrapper rather than
a modification. It is also what makes it a verifier. The guard never has to trust the agent's own
budget estimate, because it wraps that estimate in a guarantee that holds whether the estimate is
any good or not.

**Calibration, and what breaks it.** The predictor behind the band is gradient-boosted quantile
regression (LightGBM), conformalized as above [14], which lets the interval width vary with the
input instead of applying one global margin. We split calibration and test by *rollout*, never by
prefix: two prefixes of the same run share its final total, so splitting them apart leaks each test
answer into calibration.

This works when calibration and deployment resemble each other. Swap the underlying model, or
point the guard at a new task type, and the resemblance is gone; so is the guarantee. Our response
is to let the deployment stream recalibrate the guard as it goes, using the runs that have already
finished. We evaluate three ways of doing this. ACI [15] nudges its working confidence level up
whenever it has been missing too often and down when it has been too safe. DtACI [16] runs several
such nudges at different speeds in parallel and leans on whichever is currently working, which
removes the step-size choice rather than hiding it. Windowed-CQR keeps a sliding window of the most
recent 100 scores and reads *q̂* straight off them; the idea is borrowed from SPCI [17], though we
take the plain empirical quantile rather than fitting their model of the residual series. It
carries no finite-sample guarantee, and the honest statement of what it does provide is a coverage
gap that grows with how far the window has drifted from the stream [20].

Two reporting rules matter here. An interval with no upper bound covers everything and tells you
nothing, so we report the fraction of unbounded intervals beside every coverage number rather than
counting the coverage they buy as if it were informative. And because a single margin gets set by
the many easy late-turn prefixes, a good average can conceal a hole at turn one, which is where an
abort decision is worth the most. We therefore also calibrate a separate *q̂* per turn-depth
bucket [18].

**When several budgets bind at once.** Warehouse runs can fail three ways: out of time, out of
warehouse space, or out of money. The run survives only if *all three* estimates hold, and
covering each one 90% of the time does not cover all three 90% of the time, because the failures
accumulate. The fix is to demand more of each: calibrate every resource at 96.7% instead of 90%,
so that by the union bound the chance any one fails is at most 10%. This is conservative by
construction, and it buys the joint guarantee with wider margins. A tighter alternative shares one
threshold across resources by ranking their errors jointly [24], but that ranking is chosen using
the same errors it then thresholds, so it carries no guarantee; we report it as an observation and
rest the claim on the conservative version. When the deployed model changes, we let this joint
calibration move as well: a rolling window of recent three-resource errors updates both the
per-resource margins and the shared ranking, and, as everywhere else, only once a run has finished.

**Runs that cannot finish.** When a run is doomed we do not learn *y*; we learn only that *y*
exceeded what was left. Statisticians call such observations censored. Dropping them removes
exactly the hard cases and leaves a guard calibrated only on runs that were never going to be a
problem. We calibrate one-sided upper bounds several ways: treating censored scores as infinite
(always valid, useless once censoring exceeds 10%), substituting the lower bound we do know,
reweighting by how likely each run was to be censored [25], and charging a censored run only
against the resource that actually stopped it, since a run killed by its clock says nothing about
its remaining dollars. A survival estimator [26] tells us when no finite bound is available at all.

Finally, a classifier on the same features decides whether to issue an interval. This changes what
we can promise: coverage holds *among the prefixes the gate lets through*, not across all prefixes.
That is weaker than a marginal guarantee, but it is what the construction supports, so it is what
we claim.

**Stopping rule.** The same feasibility score decides when to quit: abort at the first turn where
it drops below a threshold τ. Since a run is aborted the moment its lowest score crosses τ, we set
τ from the distribution of *lowest* scores across calibration runs, taking the δ-quantile of the
feasible ones with the same finite-sample correction used above. That bounds the probability of
aborting a run that would have succeeded at δ, which we set to 0.1. The guarantee is therefore
per-run rather than per-prefix, matching the decision actually being made. Aborting a doomed run
recovers whatever it had left to spend; aborting a good one throws away a success. Both land in the
same currency, so we judge the rule on cost per successful run [32] rather than on coverage.
