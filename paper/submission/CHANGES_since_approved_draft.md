# What changed since the draft you approved

**Baseline:** `paper/Budget Guard - Research Paper (1).docx` — the version the team signed off on.
**Submitted:** `paper/submission/budget_guard_neurips2026.pdf`.

Every place the submitted paper says something *different* from the approved draft is listed
here. You should not need to reread the paper.

**Read section 1 and section 2.** Section 1 is content that was never in the approved
draft, so it has not been signed off by anyone. Section 2 is claims whose meaning changed —
mostly because the approved wording disagreed with our own result tables. Sections 3–7 are
bookkeeping and can be skimmed.

Nothing in the methodology changed. No experiment was re-run. Every number still comes from
the same `tables/*.csv` the approved draft drew on, and all six generated tables regenerate
byte-identically from those CSVs.

---

## 0. At a glance

| Category | Count | Needs your sign-off |
|---|---|---|
| 1. New content never in the approved draft | 11 items | **Yes** |
| 2. Claims whose meaning changed | 17 items | **Yes** |
| 3. Broken cross-references and notation | 6 items | No — all were defects |
| 4. Structural changes | 4 items | Skim |
| 5. Reference changes | 19 entries touched | Skim |
| 6. NeurIPS checklist | 16 answers, new artifact | Skim |
| 7. Explicitly unchanged | — | No |

---

## 1. New content — never in the approved draft

### 1.1 The Warehouse model-swap result is now reported *(§5.3, Table 2, abstract)*

§4 of the approved draft promised **three** shift scenarios; §5 reported **two**. The third
was sitting unused in `transfer_warehouse.csv`. It is now in the paper, and it is not
flattering:

> Under an external-resource model swap, however, frozen Bonferroni falls to 0.71 — below
> its nominal level, and below the 0.87 reached by the un-guaranteed adaptive copula, which
> recalibrates from finished rollouts. The guaranteed method is the right default in
> distribution and the wrong one under shift; we report both rather than choosing the
> flattering one.

The abstract now says the 0.95 is in-distribution and states the 0.71. **This is the single
biggest content change in the submission** — a reviewer who found it themselves would have
been far less forgiving than one who reads us finding it first, but the team should agree
we want it in.

### 1.2 Table 2 is new *(main text, §5.3)*

Per-resource and joint Warehouse coverage for all four calibration schemes, in-distribution
and under model swap. Contribution (3) previously rested on four numbers in a single
sentence with no table or figure behind it.

### 1.3 Tables B3 and B4 are new *(Appendix B)*

The feasibility-gate sweep and the six censored-calibration treatments. Appendix C described
both sweeps in the approved draft; neither had ever been reported.

### 1.4 The Search-R1 sharpness result is now disclosed *(§5.1 and §6)*

The approved draft said windowed-CQR "produces 22% narrower intervals on Sokoban and 55%
narrower on SWE-bench." Both true. It omitted the third environment, where our method is
**worse**:

> It is also sharper than the feature-free baseline on two environments of three: 22%
> narrower than constant-quantile on Sokoban and 55% narrower on SWE-bench, but 23% wider on
> Search-R1, where constant-quantile is the sharpest bounded method.

### 1.5 The guard+self-est ablation now has a stated result *(§5.1)*

Table A2 always contained it; no sentence ever said what it showed.

> guard+self-est is within 0.01 of split-CQR on Sokoban (0.91 against 0.92), identical on
> SWE-bench (0.96), and worse on Search-R1 (0.85 against 0.90) — consistent with the
> self-reports carrying little signal the usage stream does not already contain.

This is a negative ablation and it supports the paper's own framing.

### 1.6 The model-swap variance claim now carries numbers *(§5.2)*

Approved: "with substantially lower variance than frozen calibration" — no number anywhere.
Submitted: the seed-to-seed standard deviations, **0.006–0.011 against 0.122–0.224**.

### 1.7 A sample-size caution on the economics *(§5.5)*

> And the operating point rests on a small number of test rollouts per seed, so the observed
> 0% false-abort rate should be read as consistent with the δ = 0.10 bound rather than as
> evidence that the true rate is zero.

### 1.8 A small-test-split caveat *(§6)*

> Some test splits are small: Search-R1 leaves about 24 test prefixes per seed, which is why
> its standard deviations reach 0.10–0.17 and why several Search-R1 entries in Table B1 sit
> at exactly 1.000. Those numbers are indicative rather than precise.

### 1.9 A Broader Impact paragraph *(§6)*

Required by NeurIPS and referenced by checklist Q10. States the intended benefit, the risk
of an over-aggressive threshold, and that δ calibration is the mitigation.

### 1.10 Figure 2 now has error bars

Across-seed standard deviation. Appendix C and checklist Q7 both *claimed* these existed;
they did not. Adding them was the honest fix.

### 1.11 A paragraph in Appendix A discussing Table A1

The approved draft pointed at Table A1 once and never returned to it. The new paragraph
names the four components that carry no finite-sample guarantee.

---

## 2. Claims whose meaning changed

Each of these was checked against the source CSV. "Approved" is what the signed-off draft
said; "Submitted" is what the PDF says now.

### 2.1 Abstract — SWE-bench agent baseline

- **Approved:** "compared with 0.51, 0.23, and **0.53** from agent-generated intervals"
- **Submitted:** "…reach 0.51, 0.23 and **0.35**"
- **Why:** §5.1 and Table A2 in the same approved draft both said 0.35; `coverage.csv` gives
  0.3537. The abstract was the outlier.

### 2.2 Abstract — the headline coverage range

- **Approved:** "conformal guards achieve approximately 0.87–0.96 empirical coverage"
- **Submitted:** "offline split-CQR reaches **0.90–0.96** and online windowed-CQR reaches
  **0.87–0.92**"
- **Why:** 0.87 and 0.96 are two *different methods*. The merged range is one no single
  method attains. Also now says the numbers are Claude Opus 4.7 only.

### 2.3 Abstract — Bonferroni joint coverage

- **Approved:** "Bonferroni joint calibration reaches 0.95 coverage."
- **Submitted:** "**in-distribution** Bonferroni calibration reaches 0.95 joint coverage
  across time, capacity and cost, **though it falls to 0.71 under a model swap**."
- **Why:** see 1.1.

### 2.4 Abstract — what drives the stopping rule

- **Approved:** "**Using these calibrated estimates** for early stopping at feasibility
  tolerance δ = 0.1 saves…"
- **Submitted:** "**Thresholding a separately calibrated feasibility score** at a false-abort
  tolerance δ = 0.10 avoids…"
- **Why:** §3 of the approved draft already said the rule "thresholds the feasibility score
  and does **not** read the remaining-budget intervals." The abstract contradicted the
  method section. Contribution (4) was reworded to match.

### 2.5 Abstract and Conclusion — Cost-of-Pass units

- **Approved:** "$1.61M to $0.87M per successful trajectory"
- **Submitted:** "…**in simulated Warehouse dollars** per successful run… — all in
  counterfactual replay of logged rollouts, not live deployment"
- **Why:** these are simulation dollars. The approved draft said so only in a figure caption
  and Appendix C; a reader of the abstract would take them for real money.

### 2.6 Abstract, §5.1, §6, Conclusion — the breadth counts

- **Approved:** "**Our headline figures are averages:** windowed-CQR reaches at least 0.85
  coverage in 18 of 19…"
- **Submitted:** "Our breadth figures are **single-split counts rather than seed averages**:
  on seed 0, windowed-CQR reaches at least 0.85 coverage in 18 of 19…"
- **Why:** `run_allruns.py` runs seed 0 only. The 18-of-19 and 11-of-19 counts are not
  covered by the paper's own five-seed protocol. The abstract now says "on one split each"
  and Table B1's caption says the same.

### 2.7 §5.5 — hard caps and Cost-of-Pass **(the most serious one)**

- **Approved:** "Hard spending caps can further reduce Cost-of-Pass only by sacrificing a
  substantial fraction of successful trajectories."
- **Submitted:** "**No hard cap beats the unstopped agent by more than a rounding error:
  discarding passes *raises* cost per pass, to $3.19M at the tightest cap.**"
- **Why:** the approved sentence has the direction backwards. In
  `cost_of_pass_warehouse.csv` every cap lands between $1,608,594 and $3,189,578 against the
  unstopped agent's $1,609,569 and the guard's $870,986. Figure 4(b) slopes *upward* as
  retention falls — the approved caption contradicted the figure printed directly above it.
  The corrected version is a **stronger** result for us.

### 2.8 §5.5 — the hard-cap false-abort range

- **Approved:** "larger savings require substantially higher false-abort rates" (no numbers)
- **Submitted:** "**dollar caps** reach meaningful savings only at false-abort rates of
  19–55%; **the only week cap that saves anything (54.5%) aborts every feasible run**."
- **Why:** the week cap at 9.125 weeks is plotted in Figure 4(a) at a 100% false-abort rate.
  A range quoted as 19–55% silently excluded it.

### 2.9 §6 — width comparison

- **Approved:** "roughly **20%** narrower than a constant-quantile baseline on Sokoban"
- **Submitted:** "roughly **22%** narrower… though 23% wider on Search-R1"
- **Why:** §5.1 of the same draft said 22%; the table gives 1.099 → 0.858, i.e. 21.9%.

### 2.10 §6 — method name

- **Approved:** "**SPCI** maintains coverage with no unbounded intervals"
- **Submitted:** "**windowed-CQR** holds up under shift with no unbounded intervals —
  though, as §5.2 shows, windowed-CQR still under-covers the nominal level under severe
  shift."
- **Why:** Appendix C of the approved draft explicitly retracts the name SPCI ("that
  overclaims"), then §6 used it anyway. The "maintains coverage" claim was also softened:
  §5.2 reports 0.66–0.89 under shift, which is not maintaining coverage.

### 2.11 Table 1 — SWE-bench budget range

- **Approved:** "7,060–21,711 (per run)"
- **Submitted:** "**6,772**–21,711 (per run)"
- **Why:** §4 of the same draft lists the five per-model budgets, of which the smallest is
  6,772.

### 2.12 Figure 3 caption — what the transfer experiment shows

- **Approved:** "Online calibration improves robustness under environment and model
  distribution shifts."
- **Submitted:** "An environment change collapses frozen calibration and online
  recalibration recovers much of it; **a model swap defeats every method we tried.**"
- **Why:** under model swap, frozen split-CQR averages 0.742 and windowed-CQR 0.731 —
  frozen is *better*. The caption claimed a recovery that panel (b) does not show.

### 2.13 Figure 4(a) caption — hard-cap claim

- **Approved:** (no equivalent claim)
- **Submitted:** "Every hard cap that saves **more than 0.2%** of doomed spend also stops
  runs that would have succeeded"
- **Why:** an intermediate draft said "every hard cap that saves anything," which the same
  page contradicted with the 0.2% zero-false-abort cap.

### 2.14 §1 and §3 — "training-free"

- **Approved:** "a **training-free**, model-agnostic framework"
- **Submitted:** "a model-agnostic framework that… **requires no fine-tuning of the
  underlying LLM**", plus "No LLM is trained or fine-tuned; the only fitted components are
  lightweight gradient-boosted trees over usage-accounting features."
- **Why:** we do fit LightGBM models on a train split. Only the LLM is untouched. A reviewer
  reading "training-free" next to Appendix C's `n_estimators = 200` would call it.

### 2.15 §5.4 — gate coverage range

- **Approved:** "Feasibility-gated selective intervals provide one way to trade retained
  trajectory volume against failure detection." (no numbers)
- **Submitted:** "holds coverage at 0.92–0.95 **for capacity and cost, and at 1.00 for
  time**, on the prefixes it keeps, at the cost of keeping between 51% and 89% of them"
- **Why:** the numbers exist in `gated_intervals.csv` and were never reported. Time is
  quoted separately because it sits at 1.00, not in the 0.92–0.95 band.

### 2.16 Table A2 caption

- **Approved:** described the table's contents only.
- **Submitted:** leads with "every conformal method lands within 0.05 of the 0.90 target
  except the feature-free constant-quantile baseline on Search-R1, where the agent's own
  intervals miss by 0.39–0.67."
- **Why:** the venue checklist requires captions to state a takeaway. An intermediate
  version said "reaches the target band," which was never defined and was false for
  constant-quantile on Search-R1.

### 2.17 §2 — system name

- **Approved:** "…; **Guard** calibrates coverage over the remaining resource budget"
- **Submitted:** "**Budget Guard** calibrates coverage…"

---

## 3. Broken cross-references and notation

All of these were defects in the approved draft. None changes a claim.

| Where | Approved | Submitted |
|---|---|---|
| §2, end | "See Appendix ___ for the background concepts" (letter missing) | "See Appendix **A**" |
| §4, Models | "the per-run counts are in **Table 3, Appendix B**" — no such table existed | "Table **B1**, Appendix B" |
| Appendix A, C.4 | `q̂` used both for the conformal threshold and for the quantile regressor's outputs | regressor outputs renamed **f̂_lo / f̂_hi**; `q̂` is the threshold only |
| §5.4 vs C.7/C.8 | `δ` used for both the gate tolerance and the stopping tolerance | gate parameter renamed **δ_gate**, difference stated in §5.4 |
| throughout | "SearchR1" in figures/tables, "Search-R1" in prose | **Search-R1** everywhere |
| Figures/tables | Figure 1, Table 1 and Table B2 were never referenced in the body | all 12 figures and tables are now referenced *and* discussed |

---

## 4. Structural changes

1. **§5 was reorganised from four subsections to five.** In the approved draft, Figure 4 and
   the entire economics discussion sat under §5.3 "Conditional and Multi-Resource
   Calibration," while §5.4 was titled "Censoring and Economic Impact" but contained only
   censoring. Now: 5.1 within-run, 5.2 shift, 5.3 conditional + multi-resource, 5.4 censored
   calibration, **5.5 economic impact**.
2. **Appendix tables renumbered** to match their sections: A1, A2 (Appendix A) and B1–B4
   (Appendix B). Main-text tables stay 1 and 2.
3. **Section titles**: "Related Works" → "Related work"; "Methodology: Budget Guard" →
   "Method"; "Results & Analysis" → "Results"; "Discussion & Limitations" → "Discussion and
   limitations". The abstract is no longer numbered "0."
4. **Format**: the whole paper was ported into the official NeurIPS 2026 template —
   anonymised, line-numbered, 9 pages of main text, checklist after the references. Prose was
   reflowed and tightened to fit; that reflowing is not itemised here because it does not
   change any claim.

---

## 5. Reference changes

All 27 entries were verified against primary sources (arXiv abstract pages, publisher pages,
official proceedings, DBLP, Crossref, zbMATH).

**Fifteen were cited as preprints when a peer-reviewed version exists** — which the Algoverse
checklist forbids. Now citing the published venue:

| Reference | Now cited as |
|---|---|
| Kwa et al. | NeurIPS 2025 |
| Sui et al. | TMLR 2025 |
| Chen, Zaharia, Zou (FrugalGPT) | TMLR 2024 |
| Davidov et al. | ICML 2026 |
| Romano et al. (CQR) | NeurIPS 2019, pp. 3538–3548 |
| Gibbs & Candès (ACI) | NeurIPS 2021 |
| Gibbs & Candès (DtACI) | JMLR 25(162):1–36, 2024 |
| Angelopoulos & Bates | Found. Trends ML 16(4):494–591, 2023 |
| Lei et al. | JASA 113(523):1094–1111, 2018 |
| Xu & Xie (SPCI) | ICML 2023, PMLR 202:38707–38727 |
| Barber et al. | Ann. Statist. 51(2):816–845, 2023 |
| Vovk | ACML 2012, PMLR 25:475–490 |
| Messoudi et al. | Pattern Recognition 120:108101, 2021 |
| Gui et al. | Biometrika 111(2):459–477, 2024 |
| Erol et al. (Cost-of-Pass) | ICLR 2026 |
| Angelopoulos et al. (Conformal Risk Control) | ICLR 2024 |

**Three corrections:**

- **MiCP (Zhou et al.)** was dated Aug 14 2026. The paper has two versions, 1 Apr and 5 Apr
  2026.
- **CQR page numbers** were 3543–3553 in an intermediate draft; DBLP gives **3538–3548**.
- **Ruan et al. (DFS)** had a seventh author, "Jinghao Lin," who does not exist on
  arXiv:2607.06503. The paper has six authors. This was an error I introduced and an
  independent audit did not catch; it was found by re-verifying every entry.

**One reference added:** LightGBM (Ke et al., NeurIPS 2017), cited where §3 names the base
predictor.

**Deliberate:** two entries use "and others" for the author list (Kwa et al., Sui et al.)
because a complete list could not be confirmed from a primary source. That is a choice, not
an abbreviation.

---

## 6. NeurIPS Paper Checklist

New artifact — the approved draft did not include one, and NeurIPS desk-rejects papers
without it. Sixteen questions, all answered: **10 Yes, 5 N/A, 1 No.**

The one **No** is Q5, open access to code:

> The data is fully open… The code is not attached to this submission. We will release the
> full pipeline publicly under an MIT licence on acceptance…

This matches the team's plan to keep the repo private until acceptance. A well-justified No
on Q5 is explicitly acceptable under the NeurIPS guidelines — papers cannot be rejected for
withholding code unless the code *is* the contribution. Q13 (new assets) is N/A for the same
reason.

Q12 states that the BAGEN dataset card **states no licence**, so we assert none on the
release's behalf and credit the originators. Appendix C.9 says the same.

---

## 7. What did **not** change

So you know what not to reread:

- **Every headline number** except the corrections in section 2. Self-report 0.51 / 0.23 /
  0.35; split-CQR 0.90–0.96; windowed-CQR 0.87–0.92 at 0% unbounded; 18-of-19 and 11-of-19;
  frozen collapse to 0.51 and 0.10; windowed recovery to 0.71 and 0.80; model-swap 0.66–0.89;
  joint 0.42 / 0.80 / 0.95 / 0.89; first-turn 0.86 → 0.93 Mondrian; 0.50 censored-binding
  cost coverage; 86.3% doomed savings at 0 observed false aborts; Cost-of-Pass $1.61M →
  $0.87M (46%).
- **The method.** No experiment was re-run, no hyperparameter changed, no new result
  computed. Everything traces to the same CSVs.
- **The four contributions.** Same four, now with section and table pointers appended.
- **Related work.** Same three lines of prior work, same borrowed numbers from BAGEN and DFS,
  same attribution.
- **Appendix A glossary and Table A1.** Unchanged except the added τ entry, the new
  discussion paragraph, and `q̂` disambiguation.

---

## 8. Open items for the team

1. **Wall-clock compute.** Appendix C.9 and checklist Q8 say CPU-only, no GPU, no LLM trained
   or queried — enough for an honest Yes. One sentence with a real runtime would strengthen
   it, if anyone knows the number.
2. **The exact n behind the economics.** §5.5 now carries a qualitative caution instead of a
   count, because the rollout count could not be determined without running the pipeline. If
   someone knows it, it belongs in the Figure 4 caption.
3. **`scripts/make_pipeline_figure.py` is uncommitted.** A clean checkout of the repo still
   produces the old Figure 1, so the submitted figure's lineage is not reproducible from
   HEAD.
4. **`section3_rewrite_1_checked.md`** landed in neither the submitted paper nor the docx
   draft. Integrate or delete.
5. **If the code is ever attached** (camera-ready, or if the venue asks), strip `.git/` and
   change the copyright line in `LICENSE` first — those are the only two places author names
   survive in the codebase.
