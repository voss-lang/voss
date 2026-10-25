# Orchestration gate: A vs B vs C (2026-10-18)

This is the Phase 3 gate run. It ran each of the five orchestration scenarios once under three configurations. All three used the same model, the same scenario budget and the same fixture, in a seeded random order.

```sh
proofs run --bench benchmarks/orchestration \
  --config cli-claude,voss-serve-auto,voss-swarm-auto --live --max-runs 15 --out results/phase3-gate-1
```

## Setup

- **Model.** `claude-opus-5-5` for every config, confirmed on every run record. The report's mixed-model warning did not fire.
- **A, `cli-claude`.** `claude -p`. File edits are accepted, shell commands run in the Claude Code sandbox, and user settings are off.
- **B, `voss-serve-auto`.** One `voss serve` session in auto mode, with the claude-agent provider on the Claude subscription.
- **C, `voss-swarm-auto`.** A `voss serve` swarm with the default roster: a coordinator, 2 native builders and a reviewer.
- **Scenarios.** All five are synthetic Python tasks with hidden acceptance tests:
  1. independent fixes in three modules
  2. one shared file
  3. a change that flows through three files
  4. contradictory tests, with a token budget and a scope limited to the code
  5. a four-part spec with a visible test for only the first part
- **n.** One run per cell, which is a gate run and not a study. The intervals are wide, and no difference between configs below is statistically supported.

## Results

| config | verified | claimed but not verified | median duration | median tokens | scope violations |
|---|---|---|---|---|---|
| A cli-claude | 5/5 | 0 | 29 s | 86,790 | 0 |
| B voss-serve-auto | 5/5 | 0 | 129 s | 724,750 | 0 |
| C voss-swarm-auto | 4/5 | 1 | 169 s | 1,653,026 | 1 |

Tokens are input, output, cache creation and cache read added together, as each system reports them. Cost is known only for A, at a mean of $0.147 at list price. B and C report $0 on the subscription, so their cost is recorded as unknown.

Scenario 4 set a token budget of 80,000. No system received that budget, so these figures measure overshoot only:

| config | tokens used |
|---|---|
| A | 64,460 (under) |
| B | 761,461 (9.5×) |
| C | 2,401,596 (30×) |

## What happened in the one failure

On scenario 4, the swarm's fix to `stats.py` was correct, and the contradictory test was left alone. The coordinator had split the goal into two tasks:
- the fix
- "write a read-only analysis of the stats.py test suite to TEST_ANALYSIS.md"

The scenario's prompt didn't ask for the second task. Writing that file broke the scenario's edit scope, so the run fails verification while the swarm reported `swarm.complete`.

The same pattern showed in the pagination smoke run. There the coordinator invented a "create a test script" task, which its builder didn't do, and the task was still marked done.

The cause is in Voss: the coordinator is asked for between `min(2, builders)` and `builders` subtasks, so a two-builder swarm always produces at least two tasks (upstream gap 20).

## Findings

- **H2, no support on this set.** On five small tasks, the swarm verified no more scenarios than one agent did. It took 6× longer than A and used 19× A's tokens (medians). B used 8× A's tokens on the same model. These tasks are small, so they say nothing yet about H2's claim for complex tasks.
- **H5, partly observed.** Only A stayed within the 80,000-token budget, and no system was told the budget. Scope enforcement by grading caught one unauthorized write, and it came from the swarm's invented subtask.
- **Claims.** A and B made no false completion claims. C made one, and it comes from the forced second task.

## Limits

- One run per cell, five synthetic Python scenarios, one model.
- B and C cost is unknown, and C's tokens exclude the coordinator's task split (upstream gap 19).
- `cli-claude` runs shell commands in the Claude Code sandbox, while B and C allow every requested action in the workspace. This difference favors neither side on verification, but it is not identical.
- The Board/EM configuration is not evaluable yet (upstream gap 5).
