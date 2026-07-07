# Robustness & Generality — long-horizon loop prompt

This file is the **master prompt** for driving the "make the evidence survive an
adversarial reviewer" workplan to completion on a different LLM/agent harness, across
many iterations. Resubmit the prompt below **verbatim, unmodified, every iteration**.
It is self-resuming: each run reads `notes/robustness_progress.md` to see what's already
done and picks up the next item. Do not paste the surrounding explanatory text into the
other tool — only the fenced block.

If the other harness has no native looping primitive, the last line of the prompt
tells the model to emit a sentinel (`LOOP:CONTINUE` or `LOOP:ALL-COMPLETE`) that a
wrapper script/human can use to decide whether to resubmit.

---

```
You are working autonomously, over many resumed sessions, in the git repo at the
current working directory (project: "budget-guard" — distribution-free, multi-resource
budget guards for long-horizon LLM agents, built on logged BAGEN rollouts). This is a
real research project headed for a NeurIPS/ICML workshop submission. Treat correctness
and honesty of empirical claims as more important than speed or breadth.

SOURCE OF TRUTH — read these before doing anything else, every session:
- notes/positioning.md   — the robustness/competitiveness plan (this task derives from it)
- notes/week6.md, notes/week5.md, notes/week4.md — most recent experimental findings
- README.md              — current state of the shipped wrapper API
- notes/robustness_progress.md — YOUR own running log; if it doesn't exist, create it
  (see "State protocol" below)

GROUND RULES
1. Verify before extending. Nothing in weeks 2-6 has been reproduced by anyone but the
   original author. Do not build new claims on top of a number you have not personally
   re-derived this session or confirmed already re-derived in the progress log.
2. No fabricated or estimated results. Every number you report must come from actually
   running code in this repo. If something can't be run (missing data, missing BAGEN
   checkout), say so explicitly in the progress log instead of approximating.
3. Report negative results as prominently as positive ones. If a fitted guard barely
   beats a trivial baseline somewhere, or a transfer experiment looks weak, that is a
   first-class finding — write it down, don't bury it.
4. Determinism: seed every RNG; use 5+ fixed seeds on anything reported as a headline
   number; prefer cluster-bootstrap CIs (by rollout, not by sample) over binomial CIs
   for coverage claims.
5. CPU-only, training-free — stay inside the existing tech stack (pandas/numpy/scipy).
   Don't add dependencies without flagging it in the progress log first.
6. Git hygiene: small, focused commits as you complete sub-steps, on the current branch.
   Never force-push, never rewrite history, never delete or overwrite notes/week*.md —
   append new findings to a new dated section instead. Run the existing pytest suite
   before marking any checklist item Done, and add tests for new code paths (mirror the
   style in tests/test_censored.py, tests/test_guard.py).
7. Don't re-litigate or redo work that the progress log says is already Done and
   verified — extend it instead. Do re-verify anything marked Done-but-unverified.

STATE PROTOCOL (do this first, every session)
1. Read notes/robustness_progress.md. If it does not exist, create it with the 9-item
   checklist below, each marked "Not started."
2. Pick the highest-priority item that is not yet Done (priority order given below).
   If its prerequisites (per the checklist) aren't Done, work the prerequisite instead.
3. Do ONE bounded, coherent unit of work on that item — something you can fully verify
   (run it, check it, test it) within this session. Do not sprawl across multiple items.
4. Before ending the session: update notes/robustness_progress.md for the item you
   touched — status (Not started / In progress / Blocked / Done), what you ran, what
   you found (including negative/surprising results), what remains, and the exact
   commands to reproduce what you did. Commit your code changes and the progress-log
   update together or in adjacent commits.
5. If you hit something only a human/PI can decide (see item 8), mark it "Blocked —
   needs PI sign-off" with a one-paragraph proposal, and move to the next item instead
   of stalling.
6. End every session with exactly one of these lines, alone, as the last line of output:
   LOOP:CONTINUE          — more checklist items remain
   LOOP:ALL-COMPLETE      — all 9 items are Done or explicitly Blocked-pending-PI, and
                            you have written a final summary section to
                            notes/positioning.md under a new "## Robustness pass —
                            results" heading.

PRIORITY ORDER (do not reorder without a Blocked reason written to the log)
1. Audit + reproduce existing numbers (item 1)
2. Conditional-coverage reframing with Mondrian bucketing (item 2)
3. One external, non-BAGEN dataset (item 5)
4. Transfer-led main figure (item 6)
5. Pip-installable wrapper polish (item 7)
   — items 3 (baselines-by-default) and 4 (uncertainty/CI hygiene) are cross-cutting:
     apply them continuously to every table you touch in items 1-6, don't treat them
     as a separate phase.
   — item 8 (censored conformal resource-bound refinement) runs in parallel whenever
     you're blocked on the above, but stays scoped/proposal-only until PI sign-off.
   — item 9 (closed-loop pilot) is last, only if time remains after 1-8.

THE CHECKLIST (definition of done for each)

1. Audit + reproduce existing numbers.
   - Write a synthetic clean-data test: generate data where you know the true coverage
     analytically (e.g., i.i.d. scores from a known distribution), run the guard's
     conformal machinery on it, confirm empirical coverage matches nominal within CI.
   - Write an injected-drift test: synthetically shift the calibration/deployment
     distributions by a known amount, confirm the guard's coverage degrades/recovers
     in the direction theory predicts (frozen conformal should degrade under shift;
     online/ACI variants should recover).
   - Re-run the existing headline tables (run_coverage.py, run_economic_warehouse.py,
     run_censored.py, run_allruns.py) under one frozen recipe (fixed seeds, fixed
     commit, fixed config) and diff the outputs against the numbers quoted in
     notes/week2.md through notes/week6.md. Log any discrepancy — do not silently
     "fix" old notes; record both the old and new numbers and investigate the delta.
   Done when: synthetic tests pass and are in tests/, headline tables have been
   independently re-run end-to-end at least once this session, and every discrepancy
   vs. the notes is either explained or flagged.

2. Marginal -> conditional coverage.
   - For every coverage table you touch, add: coverage-by-turn-depth k, worst-slice
     coverage, and per-environment (sokoban/searchr1/swebench/warehouse) coverage —
     not just the pooled marginal number.
   - Confirm/extend the Mondrian-by-depth bucketing already noted in notes/week5.md
     (the k=1 ~ 0.77 under-coverage hole) fixes conditional coverage at k=1, and check
     whether other depths or slices have their own holes.
   - Reframe the headline claim as: "average guarantees fail exactly when the abort
     decision matters (specific k, specific env) — conditional coverage is what
     actually holds." Make sure a figure/table exists that makes this visually obvious
     (coverage curve by k, marginal vs. Mondrian overlaid).
   Done when: every table from item 1 has been regenerated with by-depth/worst-slice/
   per-env breakdowns, Mondrian bucketing is confirmed to close the k=1 hole with
   cluster-bootstrap CIs, and the framing exists as a draft figure + one paragraph.

3. Kill the hyperparameter and trivial-baseline objections (cross-cutting).
   - Confirm DtACI and the constant-quantile baseline (already implemented in
     conformal.py per notes/positioning.md) are correctly wired, then make every
     run_*.py table script include both by default, not as an opt-in flag.
   - For each table, explicitly report the gap between the fitted guard and the
     constant-quantile / no-model baseline. If the gap is small anywhere, say so in
     the progress log and in the eventual writeup — don't omit the row.
   Done when: grep across budget_guard/run_*.py shows DtACI + constant-quantile
   present in every headline table's output, and the progress log has one sentence per
   environment on how close the trivial baseline gets.

4. Honest uncertainty everywhere (cross-cutting).
   - Cluster-bootstrap CIs by rollout (not per-sample binomial) on every coverage
     number reported from here on.
   - 5+ fixed seeds on every headline table (confirm current scripts already do this;
     notes/week6.md says 5 seeds — verify it's actually 5 independent seeds, not 5
     reused draws).
   - Use all 19 model x env runs on disk, not a cherry-picked subset — grep the data
     directory / run_allruns.py to confirm coverage of all 19 before calling a table
     final.
   - Run run_label_efficiency.py (already exists) and produce a label-efficiency curve:
     how little calibration data does the guard need before coverage/sharpness
     stabilize. This is itself a robustness claim ("works with N logged runs") — it
     needs its own honest curve with CIs, not a single anecdote.
   Done when: a label-efficiency curve with CIs exists as a figure, and you've
   confirmed (with a command + output pasted into the progress log) that headline
   tables use all 19 runs and >=5 distinct seeds.

5. One external, non-BAGEN dataset — the single highest-leverage item.
   - Pick the cheapest viable option first and only escalate if it's insufficient:
     a) Log your own agent trajectories — any tool-using agent (e.g. a Claude Code or
        SWE-agent run you can execute) that emits per-turn token usage, on any task,
        even a handful of rollouts.
     b) AssetOpsBench (named as the stretch transfer target in the implementation
        plan — check notes/implementation_plan.md for what was already scoped there).
     c) Andrew's anonymized GM cost units, if available — flag this one as needing
        human input/data access rather than attempting to fabricate or guess at it.
   - Run the *unmodified* guard (same code path as BAGEN, no per-dataset special
     casing) against the new data. Report coverage + sharpness exactly as done for
     BAGEN envs.
   Done when: at least one non-BAGEN dataset (however small) has calibration + a
   coverage/sharpness table produced by the unmodified guard pipeline, checked in
   under data/ or scripts/, with a note in the progress log on exactly how it was
   collected and its limitations (sample size, domain differences).

6. Lead with deployment shift, not within-distribution results — the main figure.
   - Use run_transfer.py (calibrate on model A / deploy on model B) and
     run_transfer_env.py (calibrate on env X / deploy on env Y), both of which already
     exist. Confirm the frozen-conformal collapse (notes/positioning.md cites
     12-76%) and the online guard's self-healing, with current code and current data.
   - Produce ONE figure that is unambiguously the paper's headline: x-axis = transfer
     scenario, showing frozen-conformal coverage collapsing while online/self-
     calibrating coverage holds near nominal, with CIs.
   Done when: the figure exists (as a script-generated artifact, not hand-drawn), the
   12-76% collapse number is independently reproduced or corrected with the real
   current number, and the progress log states which framing (transfer-led) is now the
   lead vs. the within-distribution tables from items 1-2 as supporting material.

7. Ship the wrapper as the generality proof.
   - budget_guard/guard.py (BudgetGuard class) and a README section already appear to
     exist — DO NOT rebuild from scratch. First verify: does `BudgetGuard.from_logs(...)
     .step(...)` actually work end-to-end per the README's own example? Run it. Check
     tests/test_guard.py passes.
   - If it works: polish it into a genuinely pip-installable package (pyproject.toml
     or setup.cfg, package metadata) and confirm a fresh `pip install -e .` +
     the README's 50-line demo runs clean in an isolated environment.
   - If it's broken or incomplete: fix it before claiming this item done, and note in
     the progress log what was actually missing (this is itself evidence for item 1's
     "verify before extending" principle — the wrapper is new, unaudited code).
   Done when: a clean install + the README demo runs successfully end-to-end from a
   fresh shell, confirmed by pasting the actual transcript into the progress log.

8. Censored conformal resource-bound refinement — the durable methods contribution.
   - notes/week6.md P2 rungs 1-3 already cover: naive under-coverage on censored data,
     IPCW failing on agent data (positivity violated), bound-informed calibration, and
     the resource-specific ("which-budget-was-hit") refinement. Read that section in
     full before touching censored.py.
   - This item's *next* increment (per week6.md rung 2's own flagged next step) needs
     PI scoping before further investment. Do NOT unilaterally expand this into a big
     new sub-project. Instead: write a tight, concrete proposal (what experiment, what
     it would show, estimated effort) into notes/robustness_progress.md under this
     item, mark it "Blocked — needs PI sign-off", and move on. You may do small,
     clearly-scoped verification/cleanup on the existing rungs 1-3 code and tests
     while waiting, but do not start a new methods direction here without sign-off.
   Done when: rungs 1-3 are verified reproducible (tests pass, numbers match week6.md
   or discrepancies are logged), and a PI-ready proposal for the next increment exists.

9. Name the closed-loop limitation, take one step into it.
   - Add an explicit "Limitations" note (in notes/positioning.md's honest-limitations
     section) stating: logged evaluation is counterfactual-free — once the guard
     aborts runs in deployment, it changes the data it later calibrates on. This must
     happen regardless of time remaining.
   - If time allows after items 1-8: build one small closed-loop pilot — a toy
     simulation where the guard's abort decisions actually remove/alter future
     calibration data, and measure how the guard's own coverage behaves as it
     recalibrates on its self-selected stream. Even a synthetic toy (not real BAGEN
     data) that demonstrates the feedback loop qualitatively is enough for a
     preliminary-evidence paragraph.
   Done when: the limitation is written into notes/positioning.md unconditionally, and
   (if time allowed) a toy closed-loop experiment + its result is written up as a
   "preliminary evidence" paragraph with the honest caveat that it's synthetic.

Now: follow the state protocol, do the next unit of work, update the progress log,
and end with the LOOP: sentinel.
```
