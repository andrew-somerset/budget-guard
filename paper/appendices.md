## Appendix B. Per-run dataset composition

Table 3: Rollout and prefix-sample counts for every model x environment run evaluated in this paper.

| Environment | Model | Rollouts | Prefix samples |
|---|---|---|---|
| Sokoban | Claude Opus 4.7 | 123 | 355 |
| Sokoban | Claude Opus 4.6 | 116 | 410 |
| Sokoban | Claude Sonnet 4.6 | 126 | 400 |
| Sokoban | GPT-5.2-instant | 128 | 661 |
| Sokoban | GPT-5.2-Codex | 128 | 592 |
| Sokoban | Gemini 3.1 Pro | 126 | 389 |
| Sokoban | Qwen3-235B | 126 | 1,038 |
| Search-R1 | Claude Opus 4.7 | 66 | 87 |
| Search-R1 | Claude Opus 4.6 | 52 | 90 |
| Search-R1 | Claude Sonnet 4.6 | 64 | 102 |
| Search-R1 | GPT-5.2-instant | 125 | 324 |
| Search-R1 | GPT-5.2-Codex | 126 | 262 |
| Search-R1 | Gemini 3.1 Pro | 83 | 85 |
| Search-R1 | Qwen3-235B | 124 | 1,079 |
| SWE-bench | Claude Opus 4.7 | 64 | 712 |
| SWE-bench | Claude Sonnet 4.6 | 64 | 1,258 |
| SWE-bench | GPT-5.2-instant | 64 | 1,313 |
| SWE-bench | Gemini 3.1 Pro | 64 | 2,327 |
| SWE-bench | Qwen3-235B | 60 | 3,715 |
| Warehouse | Opus 4.7 + 4 swap targets | 64 each | 1,280 each (3 resources; 50% censored) |

## Appendix C. Supporting figures

Figure 6: Model-swap transfer on SWE-bench, guard calibrated on Claude Opus 4.7. Mean coverage is comparable between frozen split-CQR and windowed-CQR; the difference is the width of the seed-to-seed band.

[insert image: figures/final/transfer_swebench.png]

Figure 7: Conditional coverage by turn depth. The Sokoban k = 1 slice is the only place a marginal number materially overstates performance, and it is the slice the abort decision depends on most.

[insert image: figures/conditional_coverage.png]
