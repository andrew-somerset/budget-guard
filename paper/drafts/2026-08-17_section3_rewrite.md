# §3 rewritten — demonstration

Same claims, same numbers, same guarantees. ~930 words against 1,239. The difference is that this
version explains the ideas instead of naming them, and each paragraph sets up the next.

---

## 3. Budget Guard

An agent is partway through a task. It has spent some tokens, taken some turns, and may or may not
finish. We want to say, right now, how much more it will need — and we want that answer to come
with a number attached: not a guess, but an interval that contains the truth 90% of the time.

Conformal prediction gives us that. The idea is simple enough to state in a sentence: take any
predictor, measure how badly it missed on data it never trained on, and widen its output by the
90th percentile of those misses. The resulting interval is right 90% of the time, and the proof
requires nothing about the data except that the runs used to measure the misses look like the runs
you deploy on. That last condition is called exchangeability, and everything difficult in this
paper comes from the fact that it fails.

**What the guard sees, and what it has to predict.** At turn *k*, Budget Guard sees only the past:
how much the agent has spent per turn, and its own estimate of what it still needs, if it offers
one. It predicts *y*, the resources the run will consume before finishing. Two properties of *y*
shape everything downstream.

First, *y* cannot be known until the run is over. This sounds obvious and is routinely violated in
evaluation: if you let a method see turn *k*'s answer before predicting turn *k+1*, you are using
a label that would not exist in deployment, and your measured coverage is inflated. We therefore
release labels only at rollout boundaries, and freeze every method's internal state within a run.

Second, *y* does not exist at all for a run that can no longer finish. A doomed run does not
delay its label; it destroys it. Half of our Warehouse prefixes are in this state, and they are
precisely the runs a budget guard exists to catch.

**Features.** Everything the guard uses comes from four families, all computable from the usage
stream alone: how far along the run is (the turn index); how much it has consumed (total spend,
and spend divided by turns, which is the burn rate); how it has been consuming recently (the last
turn, and the mean, spread, min, max and recent trend of per-turn usage); and the agent's own
estimate, when it gives one. Nothing that depends on the future — final totals, success,
feasibility — enters the feature matrix; we assert this in code rather than trusting ourselves to
have left it out. No weights, no logits, no environment internals: only the usage accounting that
provider APIs already return, which is what makes the guard a wrapper rather than a modification.

**Calibration, and what breaks it.** The base predictor is a gradient-boosted quantile regressor
(LightGBM), conformalized with CQR [14], which adapts interval width to the input instead of
applying one global margin. We split calibration and test by *rollout*, never by prefix: two
prefixes of the same run share its final total, so splitting them apart leaks each test answer
into calibration.

This works when calibration and deployment resemble each other. Swap the underlying model, or
point the guard at a new task type, and the resemblance is gone — and with it the guarantee. Our
response is to let the deployment stream recalibrate the guard as it goes, using the runs that have
already finished. We evaluate three ways of doing this. ACI [15] nudges its working confidence
level up whenever it has been missing too often and down when it has been too safe. DtACI [16]
runs several such nudges at different speeds in parallel and leans on whichever is currently
working, which removes the step-size choice rather than hiding it. Windowed-CQR keeps a sliding
window of the most recent 100 errors and reads its margin straight off them; it carries no
finite-sample guarantee, and the honest statement of what it does provide is a coverage gap that
grows with how far the window has drifted from the stream [20].

Two reporting rules matter here. An interval with no upper bound covers everything and tells you
nothing, so we report the fraction of unbounded intervals beside every coverage number rather than
quietly banking the coverage they buy. And because a single margin gets set by the many easy
late-turn prefixes, a good average can conceal a hole at turn one — where an abort decision is
worth the most. We therefore also calibrate a separate margin per turn-depth bucket [18].

**When several budgets bind at once.** Warehouse runs can fail three ways: out of time, out of
warehouse space, or out of money. The run survives only if *all three* estimates hold, and
covering each one 90% of the time does not cover all three 90% of the time — the failures
accumulate. The fix is to demand more of each: calibrate every resource at 96.7% instead of 90%,
and the chance that any one fails is at most 10%. This is conservative by construction, and it
buys the joint guarantee with wider margins. A tighter alternative shares one threshold across
resources by ranking their errors jointly, but that ranking is chosen using the same errors it
then thresholds, so it carries no guarantee; we report it as an observation and rest the claim on
the conservative version.

**Runs that cannot finish.** When a run is doomed we do not learn *y*; we learn only that *y*
exceeded what was left. Statisticians call such observations censored, and dropping them is the
tempting mistake — it removes exactly the hard cases and leaves a guard that looks calibrated on
the runs that were never going to be a problem. We calibrate one-sided upper bounds several ways:
treating censored errors as infinite (always valid, useless once censoring exceeds 10%),
substituting the lower bound we do know, reweighting by how likely each run was to be censored
[25], and charging a censored run only against the resource that actually stopped it, since a run
killed by its clock says nothing about its remaining dollars. A survival estimator [26] tells us
when no finite bound is available at all.

Finally, a classifier on the same features decides whether to issue an interval. This changes what
we can promise: coverage holds *among the prefixes the gate lets through*, not across all prefixes.
That is a weaker statement than the usual one, and it is the one the construction actually
supports, so it is the one we make.

**Knowing when to quit.** The same feasibility score drives the stopping rule: abort at the first
turn where it drops below a threshold τ. Since a run is aborted the moment its lowest score crosses
τ, we set τ from the distribution of *lowest* scores across calibration runs — the 10th percentile
of the feasible ones, if we are willing to abort at most 10% of runs that would have succeeded.
That is a per-run promise about a sequential decision, which is what an operator actually needs.
Aborting a doomed run recovers whatever it had left to spend; aborting a good one throws away a
success. Both land in the same currency, so we judge the rule on cost per successful run [32]
rather than on coverage.
