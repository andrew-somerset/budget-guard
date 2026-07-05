# References & source map — for the paper write-up

Compiled 2026-07-04. Confidence key: ✅ = verified against arXiv/web today;
🟡 = standard citation, high confidence from memory — verify ID before camera-ready;
🔎 = unresolved, lit-review team to identify.

## The base paper & data

| What we use | Source |
|---|---|
| Problem, dataset, agent-self-report baselines, `y_t` definition, 47% headline | 🟡 **BAGEN**, arXiv:2606.00198 (MLL-Lab). Cite for: the miscalibration finding, the 28–64% early-stop savings claim, the token-estimation env, the released rollouts. |
| All rollout/estimation data | ✅ HF dataset **`MLL-Lab/BAGEN`** (public). The `turn_excluding_history` token accounting we port is from their `ragen/env/token_estimation/env.py` (BAGEN repo, MIT/see LICENSE). |

## Conformal prediction — per module in `budget_guard/`

| Our code | Method | Citation |
|---|---|---|
| `conformal.split_conformal_absres` | split/inductive conformal | 🟡 Papadopoulos, Proedrou, Vovk, Gammerman, "Inductive Confidence Machines for Regression," ECML 2002. Modern treatment: 🟡 Lei, G'Sell, Rinaldo, Tibshirani, Wasserman, "Distribution-Free Predictive Inference for Regression," JASA 2018, arXiv:1604.04173. |
| (tutorial framing, finite-sample (n+1) correction) | — | 🟡 Angelopoulos & Bates, "A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification," arXiv:2107.07511. |
| `conformal.cqr_split` | Conformalized Quantile Regression | 🟡 Romano, Patterson, Candès, "Conformalized Quantile Regression," NeurIPS 2019, arXiv:1905.03222. |
| `conformal.aci_cqr` | Adaptive Conformal Inference (incl. the unbounded-interval fallback we rely on in transfer) | 🟡 Gibbs & Candès, "Adaptive Conformal Inference Under Distribution Shift," NeurIPS 2021, arXiv:2106.00170. |
| `conformal.dtaci` | DtACI / expert aggregation over γ (our simplified constants noted in docstring) | 🟡 Gibbs & Candès, "Conformal Inference for Online Prediction with Arbitrary Distribution Shifts," arXiv:2208.08401 (JMLR 2024). Related aggregation variant (AgACI): 🟡 Zaffran, Féron, Goude, Josse, Dieuleveut, "Adaptive Conformal Predictions for Time Series," ICML 2022, arXiv:2202.07282. |
| `conformal.spci` | SPCI — we implement a **windowed empirical-quantile simplification**, say so | 🟡 Xu & Xie, "Sequential Predictive Conformal Inference for Time Series," ICML 2023, arXiv:2212.03463. |
| `conformal.mondrian_cqr` | Mondrian / group-conditional conformal | 🟡 Vovk, Gammerman, Shafer, *Algorithmic Learning in a Random World*, Springer 2005 (Mondrian taxonomy); also 🟡 Vovk, "Conditional validity of inductive conformal predictors," ACML 2012. |
| (weighted conformal under shift — cited as alternative, not implemented) | NexCP | 🟡 Barber, Candès, Ramdas, Tibshirani, "Conformal Prediction Beyond Exchangeability," arXiv:2202.13415 (Ann. Statist. 2023). |

## Multi-resource (C2) — `multiresource.py`

| Our code | Citation |
|---|---|
| `bonferroni` scheme | Standard union bound; no dedicated citation needed (cite Vovk 2005 or state directly). |
| `copula` scheme (shared empirical rank level) | ✅ Messoudi, Destercke, Rousseau, "Copula-based Conformal Prediction for Multi-Target Regression," Pattern Recognition 2021, **arXiv:2101.12002**. Also relevant: ✅ Sun & Yu, "Copula Conformal Prediction for Multi-Step Time Series Forecasting," ICLR 2024, arXiv:2212.03281 — check which is closer to our construction. |

## Censored conformal (P2) — `censored.py`

| Our code | Citation |
|---|---|
| framing + IPCW route | 🟡 Candès, Lei, Ren, "Conformalized Survival Analysis," JRSS-B 2023, arXiv:2103.09763. Follow-up with adaptive cutoffs: 🟡 Gui, Hore, Ren, Barber, arXiv:2211.01227 — verify. |
| IPCW itself | 🟡 Robins & Rotnitzky (1992) / standard inverse-probability-of-censoring weighting from survival analysis — lit team pick the canonical cite. |
| **Our empirical findings** (IPCW positivity failure on agent data; cross-resource censoring; bound-informed calibration) | Ours — nothing to cite; these are the candidate contribution. Verify nobody else has them. |

## Economics (C3/C4)

| Our code | Citation |
|---|---|
| `run_costofpass` metric | ✅ Erol, El, Suzgun, Yüksekgönül, Zou, "Cost-of-Pass: An Economic Framework for Evaluating Language Models," **arXiv:2504.13359** — we extend from single-response to whole-trajectory agents; cite prominently. |
| cost-aware LLM routing (related work) | 🟡 Chen, Zaharia, Zou, "FrugalGPT," arXiv:2305.05176. |
| `economic.py` stopping rule | Ours (rollout-level min-score calibration). Related: sequential testing / e-values if we go that route — 🟡 Ramdas et al. e-value surveys, lit team to pick. |

## Unresolved — lit-review team (from `notes/positioning.md` + plan)

- 🔎 **MiCP**, **CCPO** — named in our planning docs as adjacent work; identify the actual papers (likely 2025–2026, past my reliable window) and diff our positioning.
- 🔎 Any conformal × LLM-agent budget/cost prediction work 2025–2026.
- 🔎 BAGEN team's newer output (MLL-Lab, post-2606.00198).
- 🔎 Canonical IPCW + censored-conformal citations (above).

## Software (cite in reproducibility appendix)

LightGBM (Ke et al., NIPS 2017 🟡) · scikit-learn (Pedregosa et al., JMLR 2011 🟡) ·
NumPy · pandas · matplotlib · huggingface_hub. Python 3.12, conda-forge; pinned
`requirements.txt` in repo root.

## BibTeX skeleton (verify 🟡 entries before submission)

```bibtex
@article{bagen2026,        title={<BAGEN title>}, author={<MLL-Lab>}, journal={arXiv:2606.00198}, year={2026}}
@article{angelopoulos2021gentle, title={A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification}, author={Angelopoulos, Anastasios N. and Bates, Stephen}, journal={arXiv:2107.07511}, year={2021}}
@inproceedings{romano2019cqr, title={Conformalized Quantile Regression}, author={Romano, Yaniv and Patterson, Evan and Cand{\`e}s, Emmanuel}, booktitle={NeurIPS}, year={2019}}
@inproceedings{gibbs2021aci, title={Adaptive Conformal Inference Under Distribution Shift}, author={Gibbs, Isaac and Cand{\`e}s, Emmanuel}, booktitle={NeurIPS}, year={2021}}
@article{gibbs2024dtaci, title={Conformal Inference for Online Prediction with Arbitrary Distribution Shifts}, author={Gibbs, Isaac and Cand{\`e}s, Emmanuel J.}, journal={JMLR}, year={2024}}
@inproceedings{xu2023spci, title={Sequential Predictive Conformal Inference for Time Series}, author={Xu, Chen and Xie, Yao}, booktitle={ICML}, year={2023}}
@inproceedings{zaffran2022agaci, title={Adaptive Conformal Predictions for Time Series}, author={Zaffran, Margaux and F{\'e}ron, Olivier and Goude, Yannig and Josse, Julie and Dieuleveut, Aymeric}, booktitle={ICML}, year={2022}}
@article{barber2023nexcp, title={Conformal Prediction Beyond Exchangeability}, author={Barber, Rina Foygel and Cand{\`e}s, Emmanuel J. and Ramdas, Aaditya and Tibshirani, Ryan J.}, journal={Annals of Statistics}, year={2023}}
@book{vovk2005alrw, title={Algorithmic Learning in a Random World}, author={Vovk, Vladimir and Gammerman, Alexander and Shafer, Glenn}, publisher={Springer}, year={2005}}
@article{lei2018distribution, title={Distribution-Free Predictive Inference for Regression}, author={Lei, Jing and G'Sell, Max and Rinaldo, Alessandro and Tibshirani, Ryan J. and Wasserman, Larry}, journal={JASA}, year={2018}}
@article{messoudi2021copula, title={Copula-based Conformal Prediction for Multi-Target Regression}, author={Messoudi, Soundouss and Destercke, S{\'e}bastien and Rousseau, Sylvain}, journal={Pattern Recognition}, year={2021}, note={arXiv:2101.12002}}
@inproceedings{sun2024copula, title={Copula Conformal Prediction for Multi-Step Time Series Forecasting}, author={Sun, Sophia and Yu, Rose}, booktitle={ICLR}, year={2024}, note={arXiv:2212.03281}}
@article{candes2023survival, title={Conformalized Survival Analysis}, author={Cand{\`e}s, Emmanuel and Lei, Lihua and Ren, Zhimei}, journal={JRSS-B}, year={2023}, note={arXiv:2103.09763}}
@article{erol2025costofpass, title={Cost-of-Pass: An Economic Framework for Evaluating Language Models}, author={Erol, Mehmet Hamza and El, Batu and Suzgun, Mirac and Y{\"u}ksekg{\"o}n{\"u}l, Mert and Zou, James}, journal={arXiv:2504.13359}, year={2025}}
@article{chen2023frugalgpt, title={FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance}, author={Chen, Lingjiao and Zaharia, Matei and Zou, James}, journal={arXiv:2305.05176}, year={2023}}
```
