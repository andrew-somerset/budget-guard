# Related work — positioning table + resolved citations

*For the 4-pager. Our position in one line: post-hoc, training-free, distribution-free
remaining-budget intervals for logged agents that adapt under deployment shift using only
labels a deployed guard could actually observe (rollout-safe revelation), extended to
multi-resource joint coverage, censored (doomed-run) labels, and an economically
calibrated stopping rule.*

Verification status: the four 2026 entries marked ✔ were resolved against live pages on
2026-07-21. The rest are standard references cited from the literature; spot-check arXiv
IDs once at camera-ready.

## Positioning table

| Line of work | Representative | What it provides | What it does not (the gap we fill) |
|---|---|---|---|
| Budget-aware agents (our substrate) | ✔ BAGEN: "Are LLM Agents Budget-Aware?" (arXiv:2606.00198, 2026) | Benchmark + logged rollouts; SFT+RL self-estimation of remaining budget; early-stop saves 28–64% on failed trajectories | Self-estimates hit truth ~35–48%; no calibration guarantee, requires fine-tuning; no drift story |
| Conformal foundations | Vovk et al. 2005 (book); Papadopoulos et al. 2002; Lei et al. 2018 (JASA); CQR: Romano et al. 2019 (NeurIPS) | Distribution-free finite-sample interval validity under exchangeability | Exchangeability fails here twice: within-trajectory depth drift and cross-deployment shift |
| Online conformal under shift | ACI: Gibbs & Candès 2021 (NeurIPS); DtACI: Gibbs & Candès 2024 (JMLR); AgACI: Zaffran et al. 2022 (ICML); SPCI: Xu & Xie 2023 (ICML); Barber et al. 2023 (Ann. Statist.); Tibshirani et al. 2019 (NeurIPS) | Coverage tracking on drifting streams; parameter-free variants | Assume per-step label revelation. Agent budget labels arrive per-*rollout*; we show per-step evaluation inflates transfer coverage (0.90 → 0.80 cross-env) and adapt the methods to rollout-atomic revelation |
| Multi-target / copula conformal | Messoudi et al. 2021 (Pattern Recognition); Sun & Yu 2024 (ICLR) | Joint multi-output coverage via a shared empirical-copula rank | Static calibration; we recalibrate margins *and* the shared rank online, rollout-safely, under model swap |
| Conditional / Mondrian conformal | Vovk et al. 2005 §4; Vovk 2012 (ACML); Boström & Johansson 2020 | Group-conditional validity | We apply it to turn-depth (the k=1 first-abort-decision hole) and measure where it is and isn't needed |
| Conformal for LLM outputs | Quach et al. 2024 (ICLR); Mohri & Hashimoto 2024 (ICML); survey: Campos et al. 2024 (TACL) | Guarantees on generation/factuality sets | Output correctness, not resource forecasting; no sequential budget state |
| Conformal for agent decisions | KnowNo: Ren et al. 2023 (CoRL); ✔ MiCP: "Adaptive Stopping for Multi-Turn LLM Reasoning" (arXiv:2604.01413, 2026); ✔ CCPO (arXiv:2511.11828, AAAI 2026); Conformal Agent Error Attribution (arXiv:2605.06788); CommCP (arXiv:2602.06038) | Ask-for-help triage; turn-budgeted stopping with coverage; cost-aware orchestration with conformal reliability | Correctness-coverage objectives; none predict *remaining resource consumption*, none handle censored doomed-run labels or joint multi-resource validity |
| Cost-aware LLM serving/routing | FrugalGPT: Chen et al. 2023; RouteLLM: Ong et al. 2025 (ICLR); ✔ Cost-of-Pass: Erol et al. 2025 (arXiv:2504.13359); Budget-Aware Tool-Use (arXiv:2511.17006); TALE: Han et al. 2024; Dynasor/Certaindex: Fu et al. 2025 | Cheaper model/route selection; economic metrics; reasoning-token budgeting | Point decisions or heuristics without distribution-free guarantees; we plug our stopping rule into their cost-of-pass metric (−46%) |
| Censored / survival conformal | Kaplan & Meier 1958; IPCW: Robins & Rotnitzky 1992; Candès, Lei & Ren 2023 (JRSS-B); Gui et al. 2024 (Biometrika) | Conformal lower predictive bounds on survival times under right-censoring | Assume censoring times observed/estimable with positivity; agent doom is near-deterministic in x (positivity fails). Our resource-binding bounds + selective gate are the workaround; gated-IPCW is the scoped next increment |

## References

- BAGEN: *Are LLM Agents Budget-Aware?* arXiv:2606.00198 (2026). https://arxiv.org/abs/2606.00198 · code: https://github.com/mll-lab-nu/BAGEN ✔
- MiCP: *Adaptive Stopping for Multi-Turn LLM Reasoning.* arXiv:2604.01413 (2026). https://arxiv.org/abs/2604.01413 ✔
- CCPO: *Conformal Constrained Policy Optimization for Cost-Effective LLM Agents.* arXiv:2511.11828, AAAI 2026. https://arxiv.org/abs/2511.11828 ✔
- Erol, El, Suzgun, Yuksekgonul, Zou. *Cost-of-Pass: An Economic Framework for Evaluating Language Models.* arXiv:2504.13359. https://arxiv.org/abs/2504.13359 ✔
- Vovk, Gammerman, Shafer. *Algorithmic Learning in a Random World.* Springer, 2005.
- Papadopoulos, Proedrou, Vovk, Gammerman. *Inductive Confidence Machines for Regression.* ECML 2002.
- Lei, G'Sell, Rinaldo, Tibshirani, Wasserman. *Distribution-Free Predictive Inference for Regression.* JASA 2018. arXiv:1604.04173.
- Romano, Patterson, Candès. *Conformalized Quantile Regression.* NeurIPS 2019. arXiv:1905.03222.
- Gibbs, Candès. *Adaptive Conformal Inference Under Distribution Shift.* NeurIPS 2021. arXiv:2106.00170.
- Gibbs, Candès. *Conformal Inference for Online Prediction with Arbitrary Distribution Shifts.* JMLR 2024. arXiv:2208.08401. (DtACI)
- Zaffran, Dieuleveut, Féron, Goude, Josse. *Adaptive Conformal Predictions for Time Series.* ICML 2022. arXiv:2202.07282. (AgACI; author order verified against arXiv — see paper/references.md)
- Xu, Xie. *Sequential Predictive Conformal Inference for Time Series.* ICML 2023. arXiv:2212.03463. (SPCI)
- Angelopoulos, Bates. *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification.* arXiv:2107.07511.
- Messoudi, Destercke, Rousseau. *Copula-based Conformal Prediction for Multi-Target Regression.* Pattern Recognition 2021. arXiv:2101.12002.
- Sun, Yu. *Copula Conformal Prediction for Multi-Step Time Series Forecasting.* ICLR 2024. arXiv:2212.03281.
- Barber, Candès, Ramdas, Tibshirani. *Conformal Prediction Beyond Exchangeability.* Annals of Statistics 2023. arXiv:2202.13415.
- Tibshirani, Barber, Candès, Ramdas. *Conformal Prediction Under Covariate Shift.* NeurIPS 2019. arXiv:1904.06019.
- Vovk. *Conditional Validity of Inductive Conformal Predictors.* ACML 2012.
- Boström, Johansson. *Mondrian Conformal Regressors.* COPA 2020.
- Quach, Fisch, Schuster, Yala, Sohn, Jaakkola, Barzilay. *Conformal Language Modeling.* ICLR 2024. arXiv:2306.10193.
- Mohri, Hashimoto. *Language Models with Conformal Factuality Guarantees.* ICML 2024. arXiv:2402.10978.
- Campos, Zerva et al. *Conformal Prediction for Natural Language Processing: A Survey.* TACL 2024.
- Ren, Dixit, Bodrova, Singh, Tu, Brown, Xu, Takayama, Xia, Varley, Xu, Sadigh, Zeng, Majumdar. *Robots That Ask For Help: Uncertainty Alignment for Large Language Model Planners.* CoRL 2023. arXiv:2307.01928. (KnowNo)
- *Conformal Agent Error Attribution.* arXiv:2605.06788 (2026).
- CommCP: *Efficient Multi-Agent Coordination via LLM-Based Communication with Conformal Prediction.* arXiv:2602.06038 (2026).
- Chen, Zaharia, Zou. *FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance.* arXiv:2305.05176 (2023).
- Ong, Almahairi, Wu, Chiang et al. *RouteLLM: Learning to Route LLMs with Preference Data.* ICLR 2025. arXiv:2406.18665.
- *Budget-Aware Tool-Use Enables Effective Agent Scaling.* arXiv:2511.17006 (2025).
- Han et al. *Token-Budget-Aware LLM Reasoning.* arXiv:2412.18547 (2024). (TALE)
- Fu et al. *Efficiently Serving LLM Reasoning Programs with Certaindex.* arXiv:2412.20993 (2025). (Dynasor)
- Kaplan, Meier. *Nonparametric Estimation from Incomplete Observations.* JASA 1958.
- Robins, Rotnitzky. *Recovery of Information and Adjustment for Dependent Censoring Using Surrogate Markers.* AIDS Epidemiology, 1992. (IPCW)
- Candès, Lei, Ren. *Conformalized Survival Analysis.* JRSS-B 2023. arXiv:2103.09763.
- Gui, Hore, Ren, Barber. *Conformalized Survival Analysis with Adaptive Cut-offs.* Biometrika 2024. arXiv:2211.01227.
