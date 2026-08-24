# Budget Guard — submission-readiness report

Companion to **`budget_guard_neurips2026.pdf`** (the submission; the same file is named
`budget_guard.pdf` inside the zip) and **`BudgetGuard_NeurIPS2026_source.zip`** (the LaTeX
source that builds it).

The paper is now in the actual NeurIPS 2026 template, anonymised, with line numbers, at
**9 pages of main text** (references start on page 9; appendices and the checklist follow
and are exempt). The build is clean: **0 undefined references, 0 undefined citations, 0
overfull boxes, 0 placeholders**.

Nothing in your repo or in `paper/` was edited or deleted. Every file here is new.

---

## 1. What changed from the draft you gave me

Beyond reformatting, the draft had defects that would have cost you reviewers. I found
them by checking every quantitative claim against the generated CSVs, verifying all 27
citations, and running two independent adversarial review passes. The five that were
outright wrong:

**The Cost-of-Pass comparison was backwards.** The draft said hard caps "reduce
Cost-of-Pass further only by discarding a substantial share of passes." They don't reduce
it at all. In `cost_of_pass_warehouse.csv` every cap lands between $1,608,594 and
$3,189,578 against the unstopped agent's $1,609,569 and the guard's $870,986 — discarding
passes *raises* cost per pass. Figure 4(b) slopes upward as retention falls, which
directly contradicted the caption printed under it. Now stated correctly, and it is a
stronger result for you: no cap beats the unstopped agent by more than a rounding error.

**A sharpness claim that only held on two environments of three.** "22% narrower on
Sokoban and 55% on SWE-bench" was true, but windowed-CQR is **23% wider** than
constant-quantile on Search-R1 (1.104 vs 0.898), and Search-R1 was silently omitted from
both §5.1 and the limitations. Now stated in full in both places.

**The breadth claim was a single split presented as an average.** §6 said "our breadth
figures are averages," but `run_allruns.py` is seed 0 only — the "18 of 19" and "11 of 19"
counts are not covered by the paper's own five-seed protocol. Now labelled as a
single-split count in the abstract, §5.1, §6 and the Table B1 caption.

**Figure 2's error bars didn't exist.** Appendix C and NeurIPS checklist Q7 both claimed
they did. A false statement in the checklist is an ethics-reviewer flag. I added real
error bars (across-seed standard deviation, from `coverage.csv`), so both statements are
now true.

**Figure 3's caption over-claimed on panel (b).** "Frozen calibration collapses… online
recalibration recovers much of the loss" holds for the environment swap. Under the model
swap, frozen averages 0.742 and windowed averages 0.731 — frozen is *better*. The caption
now says what the data says: a model swap defeats every method tried.

Twenty-nine further should-fix items were applied — the abstract's `0.53` (should be
`0.35`), `Table 3, Appendix B` pointing at a table that never existed, the empty
`See Appendix ___`, `SPCI` where the paper elsewhere retracts that name, `20%` vs `22%`,
the δ symbol doing double duty for the gate tolerance and the stopping tolerance, the
never-reported Warehouse shift experiment, and so on. Full list in §4 below.

---

## 2. Citations: all 27 verified against primary sources

**Corrected in round 2 (see §7).** My first pass verified entries 1--13 against primary
sources but wrote the venue, volume and page details for the rest from memory. That was
the exact failure this project's checklist warns about. Every entry has now been checked
against arXiv abstract pages, publisher pages, official proceedings, DBLP, Crossref or
zbMATH. Two fields were wrong and are fixed; the rest held.

**Fifteen references had peer-reviewed versions and were cited as preprints**, which
your checklist explicitly forbids. All now cite the published venue:

| Ref | Was | Now |
|---|---|---|
| Kwa et al. | arXiv:2503.14499 | NeurIPS 2025 |
| Sui et al. | arXiv:2503.16419 | TMLR 2025 |
| Chen, Zaharia, Zou (FrugalGPT) | arXiv:2305.05176 | TMLR 2024 |
| Davidov et al. | arXiv:2604.18419 | ICML 2026 |
| Romano et al. (CQR) | arXiv:1905.03222 | NeurIPS 2019, pp. 3538–3548 |
| Gibbs & Candès (ACI) | arXiv:2106.00170 | NeurIPS 2021 |
| Gibbs & Candès (DtACI) | arXiv:2208.08401 | JMLR 25(162):1–36, 2024 |
| Angelopoulos & Bates | arXiv:2107.07511 | Found. Trends ML 16(4):494–591, 2023 |
| Lei et al. | arXiv:1604.04173 | JASA 113(523):1094–1111, 2018 |
| Xu & Xie (SPCI) | arXiv:2212.03463 | ICML 2023, PMLR 202:38707–38727 |
| Barber et al. | arXiv:2202.13415 | Ann. Statist. 51(2):816–845, 2023 |
| Vovk | arXiv:1209.2673 | ACML 2012, PMLR 25:475–490 |
| Messoudi et al. | arXiv:2101.12002 | Pattern Recognition 120:108101, 2021 |
| Gui et al. | arXiv:2211.01227 | Biometrika 111(2):459–477, 2024 |
| Erol et al. (Cost-of-Pass) | arXiv:2504.13359 | ICLR 2026 (re-confirmed, see §7) |
| Angelopoulos et al. (Risk Control) | arXiv:2208.02814 | ICLR 2024 |

**One date was wrong.** MiCP (Zhou et al., arXiv:2604.01413) was cited as Aug 14 2026; the
paper has only two versions, v1 on 1 Apr and v2 on 5 Apr 2026. Fixed.

**Two fields I got wrong and have now fixed:** CQR's page range (3543–3553 → **3538–3548**,
per DBLP `conf/nips/RomanoPC19`), and the author list for Ruan et al. (I had invented a
seventh author, "Jinghao Lin"; arXiv:2607.06503 has six: Ruan, Huang, Zhou, Wei, Wang,
Sun). LightGBM's full author list is now confirmed against DBLP and restored, so only
Kwa et al. and Sui et al. still use `and others` — deliberately, because their complete
lists could not be confirmed from a primary source.

Eight remain legitimate preprints with no published version: Chen et al. (token
economics), Bai et al., Wang et al., Yue et al., Zellinger et al., Lin et al. (BAGEN),
Ruan et al. (DFS), Zhou et al. (MiCP).

Where a subagent could not confirm a full author list (Kwa et al., Sui et al., LightGBM)
the bib uses `and others` rather than an invented list — the exact failure mode your
checklist warns about.

---

## 3. New content

**Table 2 (main text): multi-resource joint coverage.** Contribution (3) previously rested
on four numbers in one sentence with no table or figure. Table 2 now gives per-resource
and joint coverage for all four schemes, in-distribution and under model swap.

**The Warehouse shift experiment is now reported.** §4 promised three shift scenarios and
§5 reported two. The third exists in `transfer_warehouse.csv` and was never in the paper.
It is unflattering — frozen Bonferroni falls from 0.95 to 0.71 joint under model swap,
losing to the un-guaranteed adaptive copula at 0.87 — so the abstract now says the 0.95 is
in-distribution, and §5.3 reports the shift result. A reviewer who found this themselves
would have been much less generous than one who reads you finding it first.

**Table B3 (gate sweep) and Table B4 (censored calibrations).** Appendix C described both
sweeps; neither had ever been reported.

**Appendix A now discusses Table A1** rather than only pointing at it, naming the four
components that carry no finite-sample guarantee.

**Figures 1–4 redrawn** at the 5.5in NeurIPS text width, from the CSVs, with no in-figure
titles (captions do that job), paper-facing names (`Sokoban`/`Search-R1`/`SWE-bench`, not
`sokoban`/`searchr1`/`swebench`), direction markers, and error bars.

---

## 4. Algoverse checklist, section by section

| § | Status |
|---|---|
| 1. Citations real | **Pass.** All 27 verified against arXiv/publishers; 15 upgraded to peer-reviewed venues; 1 date corrected; 0 hallucinated. |
| 2. Approach diagram | **Pass.** Figure 1 is a single self-contained schematic; caption names input, output and the novel component explicitly. |
| 3. Numbers consistent | **Pass.** Every abstract number traced to a CSV and to its body/table restatement. Five mismatches found and fixed. |
| 4. AI sanity pass | **Pass.** Two independent adversarial passes; every finding fixed or consciously dismissed (dismissals in §5). |
| 5. Claims map to evidence | **Pass.** All four contributions now carry section/table pointers. Conclusion claims split by method rather than merged into a range neither attains. |
| 6. Baselines fair | **Pass.** Seven comparators, same splits/seeds/hyperparameters, stated in C.5. BAGEN's SFT+RL was listed as a baseline but never reported anywhere — moved to related work with a stated reason. |
| 7. Tables/figures self-contained | **Pass.** All 12 figures and tables referenced *and* discussed; every caption leads with a takeaway; units and ↑/↓ stated; best values bold in Tables 2, A2, B1, B2, B4. |
| 8. Notation consistent | **Pass.** q̂ now means only the conformal threshold (regressor outputs renamed f̂_lo/f̂_hi); δ split into rollout-level δ and gate-level δ_gate; one name per method throughout; Search-R1 spelled one way. |
| 9. Anonymisation | **Pass.** Stock anonymous author block; no names, affiliations, repo links or acknowledgments anywhere in 27 pages. |
| 10. Venue compliance | **Pass.** Main text 9 pages; `neurips_2026.sty` byte-identical to the supplied file; no margin, font or spacing tweaks; checklist included after references. |
| 11. Final mechanics | **Pass.** No `??`, no TODO, no unresolved refs or cites, no overfull boxes, limitations section present and expanded. |

---

## 5. Four optional improvements — none of them blocking

**Resolved:** the code-availability claim now matches what you're actually doing. Appendix
C.9 says the pipeline is *not* attached and will be released publicly under MIT on
acceptance; checklist Q5 is answered **No** (the data is open and pinned, the code is
held) and Q13 **N/A** (no new asset released with this submission). The checklist now
reads 9 Yes / 6 N/A / 1 No. A well-justified No on Q5 is explicitly fine under the NeurIPS
guidelines — papers cannot be rejected for withholding code unless the code is the
contribution, which here it isn't.

1. **Wall-clock compute.** C.9 says CPU-only, no GPU, no LLM trained or queried, and gives
   the pinned container — enough for an honest Yes on Q8. A reviewer would still like one
   sentence: "`make repro-all` completes in about NN minutes on N cores." Add it if you
   know the number.

2. **The BAGEN dataset licence.** C.9 says the data is used "under the terms of its dataset
   card." I could not reach huggingface.co to name the licence. If it is stated on the card,
   name it explicitly — Q12 is stronger for it.

3. **Sample size behind the economics.** The 86.3% / 0%-false-abort operating point rests
   on the Warehouse test split, and I could not determine the exact rollout count without
   running the pipeline (the CSV implies ~19 feasible test rollouts, which does not square
   with 64 rollouts × 25%). §5.5 now says the observed 0% should be read as *consistent
   with* the δ = 0.10 bound rather than as evidence the true rate is zero. Put the real n
   in the Figure 4 caption if you have it.

4. **Consciously dismissed.** Two review findings I judged not worth acting on: the
   suggestion to move Table A1/A2 out of Appendix C's pages (LaTeX float placement, normal
   in published papers), and the suggestion to add a binomial upper bound for the 0%
   false-abort rate (the caveat sentence covers it without adding a number the pipeline
   does not produce). Say the word if you disagree.

---

## 7. Round 2: response to the independent audit

An independent agent audited the submitted PDF and zip. Three must-fix items; two were
right, one was not.

**Right — CQR page numbers.** 3543–3553 was wrong. DBLP gives 3538–3548. Fixed. (The
3543–3553 range appears to be the ACM DL reprint pagination.)

**Right — the checklist contradicted the paper.** Q2 said the breadth numbers "are
averages"; §6 and the abstract say single-split. I had *tried* to fix this in the previous
round, but the edit was a `str.replace` that silently matched nothing because the string
was split across two source lines. It now asserts on every substitution, and the
generated checklist reads "the breadth counts come from a single split rather than a seed
average."

**Not right — Erol et al. ICLR 2026.** The audit called this a fabricated upgrade. It
isn't. The OpenReview camera-ready carries the header "Published as a conference paper at
ICLR 2026", and Stanford AI Lab's ICLR 2026 paper list contains the entry with the same
five authors. The audit's evidence (arXiv has no journal-ref; DBLP still lists only the
2025 preprint) is real but is absence of evidence — both lag acceptance. The venue stays.
Worth knowing: the preprint year is 2025, so the bib key `erol2026costofpass` refers to the
ICLR year, not the arXiv year.

**The audit also missed one.** Because my first pass had only verified entries 1–13, I
re-verified everything, which turned up the invented co-author in Ruan et al. that the
audit did not catch. Both are now fixed.

**Also fixed from the audit's should-fix list:** Table 2's bold no longer contradicts its
caption; Table A2's undefined "target band" is replaced by an explicit "within 0.05 of the
0.90 target, except constant-quantile on Search-R1"; Table B3's "where marginal
calibration cannot" is narrowed to capacity, where it is true; Table B4's caption now
defines what bold means; Figure 2's caption now states that its error bars are the
across-seed standard deviation; and every table now bolds *all* tied winners instead of
picking one arbitrarily (three exact ties existed).

**Matplotlib version.** The audit was right that the shipped figures were stamped 3.10.9
while Appendix C.9 claims 3.11.0. Rather than soften the claim, I installed 3.11.0 and
rebuilt all four figures; they now match the pinned environment.

**BAGEN licence.** The audit asked me to name it. I checked the Hugging Face dataset card
and its API: it states **no licence at all** — no `license` key, no `license:*` tag. So the
paper no longer says the data is used "under the terms of its dataset card," which implied
terms exist. It now says the card states no licence, that we assert none on the release's
behalf, and that we credit the originators. Checklist Q12 says the same.

**Zip hygiene.** `apply_fixes.py` is removed from the bundle, `fill_checklist.py` no longer
hardcodes a machine-specific path (the blank template ships alongside it), and the README
no longer refers to a Makefile that isn't in the zip.

**Not acted on.** The audit's minor notes about rounding (0.885 → 0.89, 45.89% → 46%,
0.171% → 0.2%) are ordinary half-up rounding and are fine. The dead labels and the
out-of-order first figure reference are cosmetic. Figure 4(a)'s legend overlapping one
hard-cap point is real but the point is still readable and moving the legend crowds the
guard curve.

**Two repo items are yours, not the submission's:** `scripts/make_pipeline_figure.py` is
uncommitted at HEAD, so a clean checkout reproduces the old Figure 1 — worth committing;
and `section3_rewrite_1_checked.md` landed in neither the tex nor the docx, so integrate
or delete it.

---

## 6. Rebuild

`README.md` in the zip has the four-command build. The one thing to change before
rebuilding is the `TABLES` path at the top of `make_paper_figures.py` and
`make_tables.py` — point it at your repo's `tables/`. Every number in every figure and
table is read from there, so regenerating results and re-running those scripts propagates
straight into the PDF.
