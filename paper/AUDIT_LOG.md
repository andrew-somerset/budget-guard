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
