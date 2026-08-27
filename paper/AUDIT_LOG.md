# Audit log

Chronological record of every verification pass over the paper. Newest last. Detailed
round reports live where noted; this file is the index and carries the findings of
passes that have no standalone report.

## 1 — 2026-07-21: internal results audit

Retracted the per-prefix "self-heals to 0.90" transfer claim; per-prefix label
revelation inflates online coverage (a deployed guard cannot observe a label mid-run).
Rollout-safe revelation is the protocol everywhere since. Recorded in
`docs/results_explained.md`; enforced by the `groups` argument of the online methods
(`budget_guard/conformal.py`) and the contiguous-rollout-id check.

## 2 — 2026-08-19: submission build, round 1 (report: `submission/VERIFICATION_REPORT.md` §1–§6)

Ported the approved draft into the NeurIPS 2026 template. Checked every quantitative
claim against `tables/*.csv`. Five outright-wrong claims fixed (backwards Cost-of-Pass
direction; omitted Search-R1 sharpness result; single split presented as an average;
nonexistent Figure 2 error bars; Figure 3(b) caption over-claim), 29 should-fix items
applied, previously unreported results added (Warehouse model swap, Table 2, gate sweep,
censored calibrations).

## 3 — 2026-08-19/20: round 2, independent audit + response (report: `VERIFICATION_REPORT.md` §7)

All 27 references verified against primary sources; CQR pages corrected; an invented
Ruan et al. co-author removed; Erol et al. ICLR 2026 confirmed real; figures rebuilt
under the pinned matplotlib; BAGEN dataset card confirmed to state **no licence** and the
paper reworded accordingly. Output: `submission/budget_guard_neurips2026.pdf` (27 pp) +
`submission/BudgetGuard_NeurIPS2026_source.zip`. This is the **last version whose every
sentence was verified and whose source is in hand.**

## 4 — 2026-08-23: audit of the condensed 18-page rewrite (`drafts/2026-08-23_condensed_18pp.pdf`)

A teammate condensed the submission to 18 pages in a pass described as "removing
hallucinations". Full-text audit against `tables/*.csv` and the code found:

**Numerically clean.** Every number in every table and claim — including the new
Table 3 (token-abort economics at δ=0.10: Sokoban 7.1%/1.9%, SWE-bench 3.1%/0%) and the
new Table 6 four-decimal footnote — traces correctly to the CSVs. No hallucinated
numbers were introduced.

**But there were no hallucinations to remove** (round 2 had already verified the
submission), **and the pass deleted verified disclosures instead**, producing three
regressions:

1. Checklist Q7 now reads "Every **reported** number is a mean over five seeds" —
   false (Table 6 is seed-0 only; the paper's own §6 says so). Round 1's wording was
   "every **headline** number".
2. Checklist Q12 still points at a licence list that the pass deleted from C.9, and
   the BAGEN no-licence disclosure (added in round 2) is gone.
3. The abstract lost "on one split each" from the 18-of-19 claim, reversing
   sign-off item 2.6 of `submission/CHANGES_since_approved_draft.md`.

**Why the deletions happened** (relevant for any future editing pass): the removed
sentences cluster into four kinds — (a) external-world facts (licences, the HF card)
unverifiable without network; (b) precise claims about the unattached private code
("11 headline / 35 quantitative claims", "two checkers", "one-ulp"); (c)
revision-history admissions ("an earlier revision did X"); (d) hedges that read as
contradictions to a local consistency check ("on one split each" vs §4's five-seed
protocol). All four are load-bearing and now carry evidence entries in
[CLAIMS_EVIDENCE.md](CLAIMS_EVIDENCE.md) so the next pass can check instead of cut.

**Open items** (blocking submission of the rewrite):

- [ ] Obtain the rewrite's LaTeX source from its author — it is not in this repo, so
      the 18-pp PDF is currently not reproducible or fixable.
- [ ] Fix regressions 1–3 above in that source.
- [ ] Extend `scripts/check_paper_numbers.py` to cover the rewrite's new claims
      (Table 3; Table 6 footnote) so `make repro-all` verifies the current paper again.
- [ ] Re-verify or drop the "bit-identical / one-ulp" Q8 sentence (marked STALE in the
      registry).

## 5 — 2026-08-26: figure legends, worked example, "average across models" request

**Figure 2/3 legend (Anna's find).** The DtACI bar on Search-R1 in Figure 2 is hatched
because DtACI emitted unbounded intervals on 16% of that stream (`tables/coverage.csv`,
Table 5, and the "up to 16%" sentence in §5.1 all carry the same number); the bar is
correct. What misled readers was the legend: matplotlib draws a series' swatch from
its first bar, so ACI-CQR (first bar hatched) got a hatched swatch and DtACI (first
bar solid) a solid one, implying hatching is a method property. Fixed in
`budget_guard/plotting.py::method_legend` (solid method swatches plus a standalone
"hatched = unbounded intervals" entry), applied to Figures 2 and 3(a)/(b), which can
now be redrawn from the committed tables with `scripts/redraw_bar_figures.py`.
Note: the paper's embedded figure files are the team's originals, built from an
older script version without the hatch note; swapping in the redrawn files is an
agreed-change item, not done here.

**Worked example (meeting request).** `scripts/make_case_study.py` follows one
held-out Sokoban rollout turn by turn. Selection is by a rule fixed in the script,
not by hand: the first rollout in the seed-0 test stream (rollout 7). On it the
self-report covers 1 of 3 prefixes and split-CQR / windowed-CQR 3 of 3; spend plus
the guard's upper bound stays under the 2,500-token budget at every turn; the
feasibility gate (δ=0.10, τ=0.021) scores it 0.99 / 0.95 / 0.99 and says continue
throughout, and on the whole split aborts 0 of 16 feasible runs while saving 4.9% of
doomed spend (seed 0; Table 3 gives the five-seed means). The script
also tallies every rollout in that test split (`tables/case_study_sokoban_tally.csv`):
split-CQR covers more prefixes than the self-report on 22 of 30, ties on 6, trails on
2 (windowed-CQR 24 / 5 / 1), so the example is representative. Draft text, table and
optional figure in `drafts/2026-08-26_case_study.tex`. Added to `make repro-paper`.

**"Average the figures over all models" (meeting request): dropped.** Figures 2, 3(a)
and 4 are single-agent (Opus 4.7) by design; the other-model runs exist on one split
each with no seed error bars, and the self-report baseline is missing for one Sokoban
run (`tables/allruns.csv`). Averaging would mix five-seed means with single-split
values and hide the per-model spread that §5.2 is about. Andrew scrapped it on
2026-08-26; Table 6 remains the per-model record.

## 6 — 2026-08-26: Overleaf integration of entry 5, and the page budget

Base: the live Overleaf `main.tex` (Andrew's download diffed byte-identical to
`drafts/2026-08-26_overleaf_main_base.tex`). With the team's original figure files it
ends its main text 27 lines into page 9 with the references filling the rest; that is
the layout the meeting called "half a page free".

**Correction.** An earlier version of this entry claimed the base itself overflowed by
11 lines. That was wrong: the compile behind the claim used regenerated figure files,
and the regenerated two-panel Figure 3 was 0.55 in taller than the team's original
(aspect 3.0 against 4.4). The extra height pushed the `[H]` Figure 3 off page 6 and
cascaded every later float, which is the same failure recorded in commit 4847cc4. The
spacing overrides proposed to "fix the base" were compensating for that artifact and are
withdrawn; the delivered file changes no length, skip or font setting.
`scripts/make_paper_figures.py` now fits each regenerated figure to the original's
pixel aspect ratio (coverage 2.99, transfer 4.38), and the base compiled with those
files reproduces the original layout exactly.

Final patched copy: `drafts/2026-08-26_overleaf_main.tex`, produced by
`drafts/tools/patch_overleaf_content.py` (`--table main --para short --keep-discussion
--gate-in-discussion`, which reproduces the file byte for byte); the diff against the
base inserts or appends only and deletes nothing. Changes:

1. §5.4, after the Table-4 paragraph and before "Censored calibration": an 8-line
   worked-example paragraph and Table `tab:case_study` at `\footnotesize` (the size the
   paper's other dense tables use). Rule-selected rollout 7; interval, spent-plus-upper
   and gate columns; split-level tally 22/6/2 and 24/5/1. Placed after the last `[H]`
   figure so it consumes the page-9 slack instead of cascading floats; the table ends
   page 8 exactly, so anything added before it must be paid for by a trim (the model and
   budget were dropped from the paragraph's first sentence because the caption states
   them).
2. §6, end of the second paragraph: three sentences, two on interval width as the
   price of calibration and one giving the gate's result on the same split (0 of 16
   feasible runs aborted, 4.9% of doomed spend recovered, Table 4 for five-seed means).
3. Appendix B: Figure `fig:case_study` (`figures/fig_case_study.png`) and one sentence.
4. `figures/fig_coverage.png` and `figures/fig_transfer.png` regenerated with the fixed
   key at the originals' aspect ratios; bars and numbers unchanged.

Result (local tectonic compile, which has matched Overleaf's pdfLaTeX page breaks on
every compile so far): main text fills page 9 (48 numbered lines), References start on
page 10, 24 pages, no unresolved references, no em dashes. NeurIPS compliance: body font,
leading, margins, text block and caption gap are the template's, untouched; no font size
below the paper's existing `\footnotesize` is used. Pre-existing in the source and left
for the team: `\enlargethispage{2\baselineskip}` before §5.2 (extends the 9-inch text
block by two lines on that page) and a 62pt overfull box in Appendix B's
censored-calibration table (`tab:censored`). Superseded: `drafts/2026-08-26_case_study.tex`.

Bundle: `drafts/BudgetGuard_Overleaf_2026-08-26.zip`; reference compile:
`drafts/2026-08-26_local_compile.pdf`.

## 7 — 2026-08-26: narrative rewrite (proposal), after Charlotte's 19:21 warning

Charlotte (mentor) wrote that the paper will not be accepted without significant
revision: confusing to read, unclear narrative, claims argued from why the method
should work rather than from what the results show, and a methodology
misunderstanding inside the team (the Slack exchange on whether conformal coverage is
"automatic" or "evidence", and whether an interval "covers 90% of all possible
solutions"). Andrew asked for a full rewrite in his voice that keeps every result.

Diagnosis recorded here so the fix is checkable against it: (1) the two flagship
numbers come from two instruments (interval coverage; gate-only Warehouse savings) and
the paper never said which one it is about; (2) in-distribution coverage is guaranteed
by construction and was presented as a finding; (3) the method section was a catalogue
(eight interval methods, five censoring treatments) with no single idea to hold on to;
(4) the story contradicted itself (intro: "control problem"; Table 3: intervals do not
help stopping; conclusion: "control signal"); (5) no picture of the mechanism on a real
run.

Rewrite: `drafts/2026-08-26_rewrite_v2_maintext.tex` (abstract through conclusion),
assembled by `drafts/tools/assemble_rewrite_v2.py` into
`drafts/2026-08-26_rewrite_v2_main.tex`. Thesis: budget awareness is two questions, how
much more and whether to stop, each with its own calibrated instrument; coverage in
distribution is a check, and the findings are what the guarantee does not cover
(shift, sharpness, joint budgets, censoring, gate economics, and the negative result on
intervals-as-stopping-signal, reframed as the design principle). The worked-example
figure is Figure 1 in the introduction; its table moves to Appendix B. Method reduces
to one equation and five short paragraphs. Section labels are unchanged so the
appendices and checklist cross-references still resolve.

Integrity: every numeric token in the new main text traces to the 26 Aug source or to
`tables/case_study_sokoban*.csv` (109 tokens checked; the only untraceable one is the
figure width 0.72); preamble, title block, bibliography, appendices and checklist are
byte-identical to the base apart from the Appendix B table insertion; no em dashes; no
unresolved references. Layout: `\raggedbottom` from the introduction (the base set it
only from Section 5) and Figures 2 to 5 as `[t]` floats instead of `[H]`, which removes the
blank lower thirds that `[H]` figures left on pages 5 and 6; tables stay `[H]`. Page 9 full, References open page 10, 24 pages. Bundle: `drafts/BudgetGuard_Overleaf_REWRITE_2026-08-26.zip`;
reference compile: `drafts/2026-08-26_rewrite_local_compile.pdf`.

Addendum (21:30 Slack): Jermaine proposed bringing Table 6 (all 19 runs) into the
main text to answer the PI's request for multi-model evidence, and demoting the
economics to "a case study"; Charlotte replied that results must be reported as they
are, negative or mixed included, with no cherry-picking. Done: a new Figure 4
(`figures/fig_allruns.png`, `scripts/make_allruns_figure.py`, in `make repro-paper`)
plots every one of the 19 runs from `tables/allruns.csv` with no averaging (agent
self-report, split-CQR, windowed-CQR, DtACI per model per environment, against 0.90
and 0.85); Table 6 stays in the appendix as the values. Not done, on purpose: the
economics stay a full section with the token-task savings (7.1%, 3.1%) and the
negative intervals-in-the-rule result stated plainly, which is what Charlotte asked
for; folding them into a case study would hide the mixed result.

Status: a proposal. Anna owns the abstract, introduction and results text under the
team's split, and the mentors asked for the claims to be agreed; the rewrite should go
to the channel as "here is a draft implementing the claims list" rather than replace
the live project unilaterally.
