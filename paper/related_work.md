# Related work

**Our position.** A post-hoc, training-free, distribution-free wrapper that produces
calibrated *remaining-budget* intervals for logged LLM agents, adapts under deployment
shift using only labels a deployed guard could observe (rollout-safe revelation), and
extends to multi-resource joint coverage, censored (doomed-run) labels, and an
economically calibrated stopping rule.

This note is a compact map for readers of the code and write-up. Full bibliographic
details are listed below; arXiv IDs for recent entries were checked against live abstract
pages (2026-07-21).

## Positioning

| Line of work | Representative work | What it provides | Gap relative to this project |
| --- | --- | --- | --- |
| Budget-aware agents | BAGEN, *Are LLM Agents Budget-Aware?* (arXiv:2606.00198) | Benchmark and logged rollouts; SFT+RL self-estimation of remaining budget; early-stop savings on failed trajectories | Self-estimates cover truth only ~35–48%; no distribution-free calibration; requires fine-tuning; no drift story |
| Conformal foundations | Vovk et al. (2005); Papadopoulos et al. (2002); Lei et al. (2018); CQR: Romano et al. (2019) | Finite-sample, distribution-free interval validity under exchangeability | Exchangeability fails here twice: within-trajectory depth drift and cross-deployment shift |
| Online conformal under shift | ACI: Gibbs & Candès (2021); DtACI: Gibbs & Candès (2024); AgACI: Zaffran et al. (2022); SPCI: Xu & Xie (2023); Barber et al. (2023); Tibshirani et al. (2019) | Coverage tracking on drifting streams; parameter-free variants | Typically assume per-step label revelation. Agent remaining-budget labels arrive per *rollout*; evaluating as if prefixes self-label inflates transfer coverage (e.g. cross-env recovery ~0.90 → ~0.80). We adapt online methods to rollout-atomic revelation |
| Multi-target / copula conformal | Messoudi et al. (2021); Sun & Yu (2024) | Joint multi-output coverage via a shared empirical-copula rank | Usually static calibration. We recalibrate per-resource margins *and* the shared rank online, rollout-safely, under model swap |
| Conditional / Mondrian conformal | Vovk et al. (2005); Vovk (2012); Boström & Johansson (2020) | Group-conditional validity | We bucket by turn depth (early-turn / first-abort risk) and report where Mondrian helps vs where marginal coverage already suffices |
| Conformal for LLM outputs | Quach et al. (2024); Mohri & Hashimoto (2024); Campos et al. (2024) | Guarantees on generation or factuality sets | Targets output correctness, not remaining *resource* consumption or sequential budget state |
| Conformal for agent decisions | KnowNo: Ren et al. (2023); MiCP (arXiv:2604.01413); CCPO (arXiv:2511.11828); related agent conformal work (arXiv:2605.06788, arXiv:2602.06038) | Ask-for-help triage; turn-budgeted stopping; cost-aware orchestration with conformal reliability | Objectives center on correctness or stop timing, not forecasting remaining resource use; no censored doomed-run labels or joint multi-resource validity |
| Cost-aware LLM serving / routing | FrugalGPT: Chen et al. (2023); RouteLLM: Ong et al. (2025); Cost-of-Pass: Erol et al. (2025); related budget-aware tool-use and reasoning-token work | Cheaper model/route selection; economic metrics; token budgeting | Point decisions or heuristics without distribution-free remaining-budget intervals. We evaluate stopping with a trajectory cost-of-pass metric in their spirit |
| Censored / survival conformal | Kaplan & Meier (1958); IPCW: Robins & Rotnitzky (1992); Candès, Lei & Ren (2023); Gui et al. (2024) | Conformal / survival tools under right-censoring | Often assume usable censoring times and positivity. Agent “doom” can be near-deterministic in features (positivity fails). We use resource-binding lower bounds and feasibility-gated (selective) intervals; gated IPCW remains future work |

## Selected references

### Substrate and economics

- BAGEN. *Are LLM Agents Budget-Aware?* arXiv:2606.00198 (2026). https://arxiv.org/abs/2606.00198 · code: https://github.com/mll-lab-nu/BAGEN
- Erol, El, Suzgun, Yüksekgönül, Zou. *Cost-of-Pass: An Economic Framework for Evaluating Language Models.* arXiv:2504.13359. https://arxiv.org/abs/2504.13359
- Chen, Zaharia, Zou. *FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance.* arXiv:2305.05176 (2023).
- Ong, Almahairi, Wu, Chiang, et al. *RouteLLM: Learning to Route LLMs with Preference Data.* ICLR 2025. arXiv:2406.18665.
- *Budget-Aware Tool-Use Enables Effective Agent Scaling.* arXiv:2511.17006 (2025).
- Han et al. *Token-Budget-Aware LLM Reasoning.* arXiv:2412.18547 (2024). (TALE)
- Fu et al. *Efficiently Serving LLM Reasoning Programs with Certaindex.* arXiv:2412.20993 (2025). (Dynasor)

### Conformal prediction

- Vovk, Gammerman, Shafer. *Algorithmic Learning in a Random World.* Springer, 2005.
- Papadopoulos, Proedrou, Vovk, Gammerman. *Inductive Confidence Machines for Regression.* ECML 2002.
- Lei, G'Sell, Rinaldo, Tibshirani, Wasserman. *Distribution-Free Predictive Inference for Regression.* JASA 2018. arXiv:1604.04173.
- Romano, Patterson, Candès. *Conformalized Quantile Regression.* NeurIPS 2019. arXiv:1905.03222.
- Angelopoulos, Bates. *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification.* arXiv:2107.07511.
- Gibbs, Candès. *Adaptive Conformal Inference Under Distribution Shift.* NeurIPS 2021. arXiv:2106.00170.
- Gibbs, Candès. *Conformal Inference for Online Prediction with Arbitrary Distribution Shifts.* JMLR 2024. arXiv:2208.08401. (DtACI)
- Zaffran, Dieuleveut, Féron, Goude, Josse. *Adaptive Conformal Predictions for Time Series.* ICML 2022. arXiv:2202.07282. (AgACI)
- Xu, Xie. *Sequential Predictive Conformal Inference for Time Series.* ICML 2023. arXiv:2212.03463. (SPCI)
- Barber, Candès, Ramdas, Tibshirani. *Conformal Prediction Beyond Exchangeability.* Annals of Statistics 2023. arXiv:2202.13415.
- Tibshirani, Barber, Candès, Ramdas. *Conformal Prediction Under Covariate Shift.* NeurIPS 2019. arXiv:1904.06019.
- Vovk. *Conditional Validity of Inductive Conformal Predictors.* ACML 2012.
- Boström, Johansson. *Mondrian Conformal Regressors.* COPA 2020.
- Messoudi, Destercke, Rousseau. *Copula-based Conformal Prediction for Multi-Target Regression.* Pattern Recognition 2021. arXiv:2101.12002.
- Sun, Yu. *Copula Conformal Prediction for Multi-Step Time Series Forecasting.* ICLR 2024. arXiv:2212.03281.

### Conformal methods for LLMs and agents

- Quach, Fisch, Schuster, Yala, Sohn, Jaakkola, Barzilay. *Conformal Language Modeling.* ICLR 2024. arXiv:2306.10193.
- Mohri, Hashimoto. *Language Models with Conformal Factuality Guarantees.* ICML 2024. arXiv:2402.10978.
- Campos, Zerva, et al. *Conformal Prediction for Natural Language Processing: A Survey.* TACL 2024.
- Ren, Dixit, Bodrova, Singh, Tu, Brown, Xu, Takayama, Xia, Varley, Xu, Sadigh, Zeng, Majumdar. *Robots That Ask For Help: Uncertainty Alignment for Large Language Model Planners.* CoRL 2023. arXiv:2307.01928. (KnowNo)
- MiCP. *Adaptive Stopping for Multi-Turn LLM Reasoning.* arXiv:2604.01413 (2026). https://arxiv.org/abs/2604.01413
- CCPO. *Conformal Constrained Policy Optimization for Cost-Effective LLM Agents.* arXiv:2511.11828, AAAI 2026. https://arxiv.org/abs/2511.11828
- *Conformal Agent Error Attribution.* arXiv:2605.06788 (2026).
- CommCP. *Efficient Multi-Agent Coordination via LLM-Based Communication with Conformal Prediction.* arXiv:2602.06038 (2026).

### Censoring and survival

- Kaplan, Meier. *Nonparametric Estimation from Incomplete Observations.* JASA 1958.
- Robins, Rotnitzky. *Recovery of Information and Adjustment for Dependent Censoring Using Surrogate Markers.* In *AIDS Epidemiology*, 1992. (IPCW)
- Candès, Lei, Ren. *Conformalized Survival Analysis.* JRSS-B 2023. arXiv:2103.09763.
- Gui, Hore, Ren, Barber. *Conformalized Survival Analysis with Adaptive Cut-offs.* Biometrika 2024. arXiv:2211.01227.
