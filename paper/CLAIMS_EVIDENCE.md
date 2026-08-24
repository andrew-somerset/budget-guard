# Claims–evidence registry

Every quantitative claim in the paper is verifiable inside this repo: regenerate with
`make repro-all`, then `scripts/check_headline_numbers.py` (11 headline claims) and
`scripts/check_paper_numbers.py` (35 paper claims) verify the text against `tables/*.csv`.
**This file covers everything else** — the claims whose evidence lives *outside* the
generated tables, which makes them look unverifiable (or fabricated) to anyone auditing
the paper without this repo, network access, or the project history.

That is not hypothetical. On 2026-08-23 an editing pass by an agent without this context
deleted several of these statements as suspected hallucinations (see
[AUDIT_LOG.md](AUDIT_LOG.md), entry 4). Most of them were themselves the *outputs* of
earlier verification rounds: precise disclosures added because an audit demanded them. A
precise disclosure about an external fact is indistinguishable from a confabulation if
you cannot reach the fact — hence this registry.

## Rules

1. **Do not delete or reword any claim below without consulting its evidence entry.**
   If you cannot re-verify it, mark it `STALE` here and flag it in review — do not
   silently drop it from the paper.
2. When a new externally-evidenced claim enters the paper, add a row here in the same
   change.
3. When a claim's wording changes in the paper, update its "where cited" pointer.

## Registry

### Dataset and licensing

| Claim | Where cited | Evidence | Status |
|---|---|---|---|
| BAGEN's Hugging Face dataset card states **no licence** (no `license` key, no `license:*` tag); we assert none on its behalf | C.9; checklist Q12 | HF dataset card + HF API, checked 2026-08-19 (round 2, VERIFICATION_REPORT §7) | VERIFIED 2026-08-19 |
| Data pinned to HF revision `58189576e54b675fdd0e1d6c1c9f189c2992732f` | C.9 | `scripts/fetch_bagen.py:29` | in-repo |
| The upstream BAGEN repository is live (unpinned re-runs can silently evaluate different data) | C.9 (submission) | Observed during fetch-script development; re-check against HF before restoring | VERIFIED 2026-08 |
| Extractor reproduces BAGEN's turn-excluding-history accounting: **0 of 355 mismatches** on the reference run (Sokoban / Claude Opus 4.7, 355 prefixes) | C.9 | `budget_guard/extract.py` validation vs official per-sample ground truth; 355 = `tables/allruns.csv` sokoban/opus-4.7 row | in-repo |

### Software environment

| Claim | Where cited | Evidence | Status |
|---|---|---|---|
| LightGBM is MIT-licensed; numpy, pandas, scipy, scikit-learn are BSD-3-Clause; matplotlib uses a **PSF-style** licence (its own "License agreement", PSF-based) | C.9 + Q12 (submission) | Upstream LICENSE files / PyPI metadata, checked 2026-08-19 (round 2). matplotlib's is the odd-sounding one; it is correct | VERIFIED 2026-08-19 |
| Exact versions: numpy 2.5.1, pandas 3.0.3, LightGBM 4.6.0, scikit-learn 1.9.0, scipy 1.18.0, matplotlib 3.11.0 | C.9 | `requirements.lock.txt` (hash-locked) | in-repo |
| Base image `python:3.12-slim-bookworm` pinned by digest | C.9 | `Dockerfile:37` | in-repo |
| Results reproduce bit-identically across host architectures apart from one-ulp width differences | Q8 (submission) | Container runs on two hosts during repro hardening; **run logs were not kept** — re-run on two architectures before restoring this sentence | STALE — re-verify |

### The verification pipeline itself

| Claim | Where cited | Evidence | Status |
|---|---|---|---|
| One command regenerates everything and machine-verifies **11 headline claims and all 35 quantitative claims**, exiting non-zero on mismatch | Q5, Q13 (submission); paper/README | `make repro-all`; `scripts/check_headline_numbers.py` (11), `scripts/check_paper_numbers.py` (35) | in-repo |
| "Two checkers" verify the generated tables | Appendix B | Same two scripts | in-repo |
| ⚠ The checkers encode the **submission's** claim set. The 2026-08-23 rewrite added claims (Table 3 token-abort economics; Table 6 four-decimal footnote) not yet covered — extend `check_paper_numbers.py` when that rewrite's source lands | — | — | TODO |

### Revision-history admissions (deliberate honesty markers — do not trim as "self-talk")

| Claim | Where cited | Evidence | Status |
|---|---|---|---|
| "Earlier drafts of this work called the method SPCI; that overclaims, because SPCI fits a quantile regression on the residual series" | C.4 (submission) | Git history; CHANGES_since_approved_draft.md §2.10 | documented |
| "Averaging per-seed interval endpoints, which an earlier revision did, is not a confidence interval at any level" | C.6 (submission) | Git history; checklist Q7 justification (submission) | documented |
| 2026-07-21 audit retracted the per-prefix "self-heals to 0.90" claim; rollout-safe evaluation is the claim to cite | docs/results_explained.md | That audit; `tables/transfer_env.csv` shows the rollout-safe numbers | documented |

### Numbers quoted from cited papers (not our experiments)

| Claim | Where cited | Evidence | Status |
|---|---|---|---|
| BAGEN: early stopping saves ~28–64% of tokens on failed trajectories at ~1.6–4.2 pp task-success cost; interval coverage only 47% even after SFT+RL | §2 | BAGEN paper (arXiv:2606.00198), checked round 2 | VERIFIED 2026-08-19 |
| Doomed From the Start: recall targets 90–97% on TextCraft; saves 47.1% (Qwen-2.5-7B) / 37.2% (Llama-3.2-3B) of inference compute at the 90% target | §2 | DFS paper (arXiv:2607.06503; six authors — a seventh was once hallucinated and removed, VERIFICATION_REPORT §2) | VERIFIED 2026-08-19 |
| All 27 reference entries: venues, volumes, pages | References | Verified against arXiv/DBLP/Crossref/publisher pages, round 2 (VERIFICATION_REPORT §2, §7). Notable: Erol et al. ICLR 2026 is real (OpenReview camera-ready header) despite DBLP lag; CQR pages are 3538–3548 per DBLP | VERIFIED 2026-08-19 |

### Wording that is load-bearing (looks redundant, is not)

| Wording | Why it must stay |
|---|---|
| "**on one split each** / on seed 0" attached to the 18-of-19 and 11-of-19 breadth counts | `budget_guard/run_allruns.py` is seed-0 only; the counts are *not* covered by the five-seed protocol §4 states. Removing the qualifier makes the abstract false |
| "Every **headline** number is a mean over five seeds" (checklist Q7) | "Every *reported* number" is false: Table 6 is single-split, agent self-report is a single logged value |
| "in **simulated** (Warehouse) dollars" | The $1.61M/$0.87M are simulation currency, not real money |
| "counterfactual replay, not live deployment" | All stopping results are replays of logged rollouts |
| "**in-distribution**" on the 0.95 joint coverage | It falls to 0.71 under model swap (Table 2) |
