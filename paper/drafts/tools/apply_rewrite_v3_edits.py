#!/usr/bin/env python3
"""Apply the 2026-08-27 review edits (C1-C8, F1-F4, L1) to a copy of
drafts/2026-08-26_rewrite_v2_main.tex, producing 2026-08-27_rewrite_v3_candidate.tex
byte for byte. Each edit is an exact single-match replacement; the script aborts if
any anchor is missing or ambiguous, and if an em dash would be introduced.

Usage: cp 2026-08-26_rewrite_v2_main.tex out.tex && python3 tools/apply_rewrite_v3_edits.py out.tex
Review: drafts/2026-08-27_rewrite_review.md; audit log entry 8.
"""
import sys, re
p = sys.argv[1]
s = open(p, encoding='utf-8').read()

EDITS = [
# ---- corrections ----
("C1 abstract subject",
 "Claude~Opus~4.7 contains the truth 51\\%, 23\\%, and 35\\% of the time",
 "Claude~Opus~4.7's intervals contain the truth 51\\%, 23\\%, and 35\\% of the time"),
("C2 abstract sharpness qualified",
 "and are sharper than a feature-free baseline; that much is guaranteed",
 "and are sharper than a feature-free baseline on two of three environments; that much is guaranteed"),
("C3 abstract token-task savings",
 "in simulated dollars, which no hard cap approaches. Feeding the intervals",
 "in simulated dollars, which no hard cap approaches; on token tasks it saves far less. Feeding the intervals"),
("C4 method: what the guarantee wraps",
 "It never has to trust the agent's own estimate, because it wraps that estimate in a guarantee that holds whether the estimate is any good or not.",
 "It never has to trust the agent's own estimate: that estimate is at most one more feature, and the guarantee holds whether or not it is any good."),
("C5 econ: cap trade-off made precise",
 "dollar caps reach meaningful savings only at false-abort rates of 19--55\\%, and the only week cap",
 "the dollar caps that save 4--15\\% abort 19--55\\% of the runs that would have succeeded, and the only week cap"),
("C6 discussion: width ratio",
 "intervals roughly twice as wide as the agent's,",
 "intervals about one and a half times as wide as the agent's,"),
("C7 checklist Q1",
 "and reports token-environment abort results at the same $\\delta$.",
 "and notes that the same gate saves far less on token tasks."),
("C8 checklist Q2",
 "that marginal coverage can hide under-coverage in slices such as early turns, and that the economic figures are counterfactual replays rather than live measurements.",
 "that censored capacity and cost results are measured against an interpolated label, and that the economic figures are counterfactual replays rather than live measurements; Section~\\ref{sec:joint} shows that marginal coverage can hide under-coverage at the first turn."),
# ---- flow ----
("F1 intro: label paragraph without jargon or revision history",
 "The resources a run still needs are known only when it ends, so online methods may read a label only at rollout boundaries; an earlier revision of this evaluation read them per prefix, and correcting that lowered our headline cross-environment recovery from 0.90 to 0.80. And the label does not exist at all for a run that can no longer finish, which is exactly the run a guard exists to catch. Half of our Warehouse prefixes are in that state.",
 "The resources a run still needs are known only when it ends, so a method that recalibrates online may learn a run's label only once that run has finished; revealing it turn by turn would hand the guard information it cannot have in deployment, and inflates coverage (Appendix~\\ref{app:protocol}). And the label does not exist at all for a run that can no longer finish, which is exactly the run a guard exists to catch. Half of the Warehouse turns we evaluate belong to runs in that state."),
("F1b appendix C.2: revision-history admission kept, moved here",
 "labels per prefix instead would use information a deployed guard does not have, so we\nreport only the rollout-safe protocol.",
 "labels per prefix instead would use information a deployed guard does not have, so we\nreport only the rollout-safe protocol. An earlier revision of this evaluation revealed\nlabels per prefix; correcting it lowered the headline cross-environment recovery,\nwindowed-CQR on SWE-bench (\\S\\ref{sec:shift}), from 0.90 to 0.80."),
("F2a method: define prefix at first use",
 "At turn $k$ the guard sees only the past (Figure~\\ref{fig:pipeline}):",
 "At turn $k$ the guard sees only the past, the prefix of the run through turn $k$ (Figure~\\ref{fig:pipeline}):"),
("F2b method: define rollout at first use",
 "We split calibration and test by rollout, never by prefix:",
 "We split calibration and test by rollout (one complete run), never by prefix:"),
("F3a method: name the feasibility score before the gate uses it",
 "and a classifier on the same features can decline to issue an interval at all.",
 "and a classifier on the same features, trained to predict whether a run can still finish, gives a feasibility score on which the guard can decline to issue an interval at all."),
("F3b method: the score's two uses",
 "The same feasibility score decides when to quit: abort at the first turn",
 "The same feasibility score, now read per run rather than per prefix, decides when to quit: abort at the first turn"),
("F4 discussion: drop the fourth restatement of the findings",
 "The paper shows that an agent's own remaining-budget estimate can be replaced, from outside, by an interval that is right as often as promised in distribution and degrades visibly rather than silently under shift; that no bounded method reaches the target under a model swap; that joint coverage over several budgets needs a joint correction and loses its guarantee under swap; and that a separately calibrated gate, not the intervals, is what saves money, and only where doomed runs are expensive and identifiable early. It does not show a general savings rate: the 86.3\\% is Warehouse, gate-only, and falls to 7.1\\% and 3.1\\% on token tasks at the same $\\delta$ (Table~\\ref{tab:abort}). The joint results rest on one multi-resource environment, which cannot support a claim that they generalise. The in-distribution coverage numbers should be read as a check on the construction; the evidence for the method is in the shift, sharpness, joint, censoring, and economic results.",
 "What the paper does not show matters as much as what it does. It does not show a general savings rate: the 86.3\\% is Warehouse, gate-only, and falls to 7.1\\% and 3.1\\% on token tasks at the same $\\delta$ (Table~\\ref{tab:abort}), and the gate pays only where doomed runs are expensive and identifiable early. The joint results rest on one multi-resource environment, which cannot support a claim that they generalise. The in-distribution coverage numbers are a check on the construction, not evidence for the method; the evidence is in the shift, sharpness, joint, censoring, and economic results."),
# ---- layout ----
("L1 Table 10 overfull box",
 "\\label{tab:censored}\n\\small\n\\begin{tabular}{@{}llcccc@{}}",
 "\\label{tab:censored}\n\\footnotesize\n\\setlength{\\tabcolsep}{4pt}\n\\begin{tabular}{@{}llcccc@{}}"),
]
for eid, old, new in EDITS:
    n = s.count(old)
    assert n == 1, f"{eid}: expected 1 match, found {n}"
    s = s.replace(old, new)
    print(f"applied {eid}")
assert '—' not in s, "em dash introduced"
open(p, 'w', encoding='utf-8').write(s)
