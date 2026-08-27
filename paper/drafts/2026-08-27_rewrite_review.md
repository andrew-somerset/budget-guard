# Review of the narrative rewrite, as compiled on Overleaf (2026-08-27)

**Reviewed:** `~/Downloads/Budget_Guard__..._9_.pdf` (24 pp, pdfTeX, 26 Aug 23:59 EDT).
Its source is `BudgetGuard_Overleaf_REWRITE_2026-08-26_2355.zip`, whose `main.tex` is
byte-identical to `2026-08-26_rewrite_v2_main.tex`; a local tectonic compile reproduces
the same 24 pages and page breaks. Slack (#laryn-charlotte-agja): no comment on the
rewrite yet after Charlotte's 21:17 "report results as they are, no cherry-picking".

**Status of this document:** a review with proposed edits. Nothing has been applied to
the live Overleaf project. Every proposal is applied in
`2026-08-27_rewrite_v3_candidate.tex` (compiled: `..._local_compile.pdf`; diff:
`..._candidate.diff`; reproduced byte for byte by `tools/apply_rewrite_v3_edits.py`),
so each can be accepted or rejected by ID and the page budget is already verified.

## Verdict

The rewrite holds together. One thesis (two questions, two instruments), one picture
of the mechanism on page 2, a method that is one equation and five paragraphs, and
results ordered from what is guaranteed to what is not. The numbers are clean. What
still costs a reader: one factual overstatement (C6), one misdescribed mechanism (C4),
one abstract claim broader than the result (C2), jargon used before it is defined
(F2, F3), a revision-history aside in the introduction (F1), and the findings restated
four times with numbers (F4). All are sentence-level; none requires a new experiment.

## 1 Numbers and claims

Both checkers pass against the committed tables (`check_headline_numbers.py` 11/11,
`check_paper_numbers.py` 35/35). The rewrite's claims that the checkers do not cover
were checked by hand against `tables/*.csv`; all trace:

- breadth counts (windowed-CQR 18/19 at 0.85, 11/19 at 0.90; DtACI 14 and 8; agents
  clear neither on any run) from `allruns.csv`;
- worked example (Figure 1, Table 6, "400 to 900 for a run that needed 267",
  "misses from turn 2", spend plus upper bound under 2,500 at every turn) from
  `case_study_sokoban.csv`; tally 22/6/2 and 24/5/1 from `..._tally.csv`;
- sharpness 22% / 55% narrower, 23% wider; "up to 16%" unbounded; guard+self-est
  0.91 / 0.96 / 0.85 from `coverage.csv`;
- shift: 0.51 / 0.10, 0.71 / 0.80, unbounded 60–88%; model swap 0.66–0.89, std
  0.006–0.011 vs 0.122–0.224, caption averages 0.74 vs 0.73, unbounded 22–61% and
  4–7% from `transfer_env.csv`, `transfer_swebench.csv`;
- Table 2 including the swap column (0.34 / 0.71 / 0.62 / 0.87 are four-target means)
  from `multiresource.csv`, `transfer_warehouse.csv`;
- economics: 86.3%, 0% false aborts, 0.2% tightest cap, 19–55%, week cap 54.5% at
  100% false aborts, $1.61M to $0.87M (46%), $3.19M; Table 3 (5.8/7.1, 5.8/1.9,
  0.0/3.1, 0.0/0.0) from `abort_frontier_*.csv`, `cost_of_pass_warehouse.csv`;
- censoring: 0.50 on cost-binding drop; gated 0.92–0.95, 1.00, kept 51–89%;
  12–27% interpolation error (`budget_guard/multiresource.py`: 26.5% / 12.2%);
- Tables 5, 7, 8, 9, 10 cell by cell; Table 1 counts; §4 ranges 52–128 and 85–3,715.

Load-bearing wording from `CLAIMS_EVIDENCE.md` is all present: "on one split each",
"headline" in checklist Q7, "simulated dollars", "counterfactual replay",
"in distribution" on 0.95, the no-licence note and the licence list in C.9.
All 27 references are cited and none dangle; all 31 labels are unique and every
`\ref` resolves; no em dashes anywhere.

Four things are wrong or stale, and one is vague:

| ID | Where | Problem |
|---|---|---|
| C6 | §6, para 2 | "intervals roughly twice as wide as the agent's". Table 6 gives 1122/800, 892/600, 740/500 = 1.40, 1.49, 1.48. It is one and a half times. (The sentence was inserted in the 26 Aug base, audit-log entry 6; the error is mine.) |
| C4 | §3, "What the guard sees" | "it wraps that estimate in a guarantee": the conformal layer wraps the guard's own predictor; the agent's estimate is at most one feature of it (C.3). |
| C2 | Abstract | "sharper than a feature-free baseline", unqualified. §5.1 and intro finding (1) say two of three environments (23% wider on Search-R1). |
| C7, C8 | Checklist Q1, Q2 | Q1 says the abstract "reports token-environment abort results at the same δ"; the rewritten abstract does not. Q2 says §6 states that marginal coverage can hide early-turn under-coverage; that sentence now lives in §5.3. The checklist was carried over byte-identical from the base. |
| C5 | §5.4 | "dollar caps reach meaningful savings only at false-abort rates of 19–55%": the caps at 19% / 36% / 55% false aborts save 3.8% / 8.1% / 15.3%. Say what they save. |

## 2 Flow

What works: the first two paragraphs of the introduction; Figure 1 before the method;
"take any predictor, measure how badly it missed, widen by a high quantile"; "this is
where the guarantee stops and the experiment starts"; the intervals-measure,
gate-decides paragraph after Table 3; Table 4 as the guarantee ledger.

What trips a reader:

1. **Undefined terms at first use.** "prefix" and "rollout" first appear in §1 para 5
   and §3; they are defined only in Appendix A. "feasibility score" is used in "The
   gate" one paragraph after the classifier that produces it is introduced without
   the name.
2. **Two jobs for one score, under one word.** "The gate" abstains from issuing an
   interval per prefix (§5.5, δ_gate) and aborts runs per rollout (§5.4, δ). The paper
   says they differ but never says up front that the same score is used twice.
3. **Revision history in the introduction.** "an earlier revision of this evaluation
   read them per prefix ..." is a load-bearing admission (`CLAIMS_EVIDENCE.md`) but
   reads as process talk on page 2. It belongs in C.2, which already carries the
   protocol statement.
4. **Findings restated four times** with the same numbers: abstract, intro (1)–(5),
   §6 para 1, §7. §6 para 1 and §7 are near-duplicates.
5. **Density.** The abstract is 298 words and the findings paragraph 189, carrying
   about twenty numbers between them. This is a choice (Charlotte asked for the
   claims in the abstract, and all five are there), so no cut is proposed; the C/F
   edits below leave the abstract at 310 words.

## 3 Proposed edits (all applied in the candidate)

| ID | Where | Change |
|---|---|---|
| C1 | Abstract | "Claude Opus 4.7 contains the truth" → "Claude Opus 4.7's intervals contain the truth" (the interval contains the truth, not the model). |
| C2 | Abstract | "sharper than a feature-free baseline" → "... on two of three environments". |
| C3 | Abstract | after "which no hard cap approaches" add "; on token tasks it saves far less" (the conclusion already says this; the abstract should not read as a universal savings rate). |
| C4 | §3 | "It never has to trust the agent's own estimate, because it wraps that estimate in a guarantee that holds whether the estimate is any good or not." → "It never has to trust the agent's own estimate: that estimate is at most one more feature, and the guarantee holds whether or not it is any good." |
| C5 | §5.4 | "dollar caps reach meaningful savings only at false-abort rates of 19–55%" → "the dollar caps that save 4–15% abort 19–55% of the runs that would have succeeded". |
| C6 | §6 | "roughly twice as wide" → "about one and a half times as wide". |
| C7 | Checklist Q1 | "and reports token-environment abort results at the same δ" → "and notes that the same gate saves far less on token tasks" (true once C3 is in). |
| C8 | Checklist Q2 | replace the early-turns clause with "that censored capacity and cost results are measured against an interpolated label" (which §6 does say) and add "Section 5.3 shows that marginal coverage can hide under-coverage at the first turn." |
| F1 | §1 para 5 | "so online methods may read a label only at rollout boundaries; an earlier revision ... from 0.90 to 0.80" → "so a method that recalibrates online may learn a run's label only once that run has finished; revealing it turn by turn would hand the guard information it cannot have in deployment, and inflates coverage (Appendix C)". "Half of our Warehouse prefixes" → "Half of the Warehouse turns we evaluate belong to runs in that state". |
| F1b | C.2 | append: "An earlier revision of this evaluation revealed labels per prefix; correcting it lowered the headline cross-environment recovery, windowed-CQR on SWE-bench (§5.2), from 0.90 to 0.80." The admission is kept, with a sharper pointer. **If accepted, update the "where cited" column in `CLAIMS_EVIDENCE.md` (§1 → C.2).** |
| F2 | §3 | "the guard sees only the past" → "... the past, the prefix of the run through turn k"; "by rollout, never by prefix" → "by rollout (one complete run), never by prefix". |
| F3 | §3 | "a classifier on the same features can decline to issue an interval at all" → "a classifier on the same features, trained to predict whether a run can still finish, gives a feasibility score on which the guard can decline to issue an interval at all"; and "The same feasibility score decides when to quit" → "The same feasibility score, now read per run rather than per prefix, decides when to quit". |
| F4 | §6 para 1 | drop the first sentence (the fourth restatement of the findings; §7 keeps it) and open with "What the paper does not show matters as much as what it does." The three limitation sentences stay, with "only where doomed runs are expensive and identifiable early" folded into the savings-rate sentence. Saves about four lines, which pays for F1–F3. |
| L1 | Table 10 | `\small` → `\footnotesize` and `\tabcolsep` 4pt: removes the pre-existing 62pt overfull box (the table visibly ran into the right margin on page 16). |

Candidate compile (tectonic, which has matched Overleaf's breaks on every compile so
far): 24 pages; main text ends on page 9 three lines earlier than the base, so
References now begin at the foot of page 9; zero overfull boxes; no warnings; no em
dashes. The diff against `2026-08-26_rewrite_v2_main.tex` is 27 changed lines and
every hunk maps to one ID above.

## 4 Layout and figures (not changed; for the team)

- **O1 Figure 3.** Twenty-seven bars at 0.92 linewidth: the value labels above the
  bars are unreadable in print. Either drop them (Table 5 has every value) or enlarge
  them in `scripts/redraw_bar_figures.py`; the embedded file is a team asset, so this
  is a separate agreed-change item (keep the original aspect ratio, entry 6).
- **O2 Appendix B.** Its text is on page 11 and its tables on pages 13–16, under
  Appendix C headings, because the tables are `[t]` floats and B is one paragraph. A
  `\FloatBarrier` before Appendix C was tried: it adds a 25th page and the tables
  still land after B. Leave it, or change Figure 1's "Table 6 in Appendix B" to
  "Table 6 in the appendix".
- **O3 Table 4.** The `p{}` columns justify short lines (seven underfull boxes,
  visible as stretched gaps). `array` is not loaded; adding it and
  `>{\raggedright\arraybackslash}p{...}` would fix it. Cosmetic.

## 5 Optional wording, not applied

- **O4 §3 censoring list.** The parenthetical of five treatments is a 60-word
  sentence. Shorter: "We calibrate one-sided upper bounds five ways, from treating a
  censored score as +∞ (always valid, and vacuous once censoring exceeds α) to
  dropping censored runs (the naive comparison), with three informative repairs in
  between (Appendix C.7)". Cost: the IPCW citation moves to Table 4 and C.7 only.
- **O5 Notation.** "model–environment" (abstract, §5.1) vs "model×environment"
  (§4, §7, Appendix B). Pick one.
- **O6 Names.** "ACI" (§5.2 text) vs "ACI-CQR" (figures, tables, §5.1); "trend" (§3)
  vs "last minus mean" (Figure 2, C.3).
- **O7 Abstract length.** 298 words. Kept, for the reason in §2 item 5.

## 6 How to apply

Accept or reject by ID. To take all of them: upload `2026-08-27_rewrite_v3_candidate.tex`
as `main.tex` in the Overleaf project (figures and sty unchanged). To take a subset:
delete the unwanted entries from `tools/apply_rewrite_v3_edits.py` and run it on a copy
of `2026-08-26_rewrite_v2_main.tex`; recompile and confirm the conclusion still ends on
page 9 (F4 is the edit that pays for F1–F3). Then, if F1b is in, update
`CLAIMS_EVIDENCE.md`; and run `make repro-paper` unchanged, since no number moved.
