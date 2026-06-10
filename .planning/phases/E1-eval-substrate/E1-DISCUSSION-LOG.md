# Phase E1: Eval Substrate - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** E1-eval-substrate
**Areas discussed:** Check executor design, Cap defaults + wiring, Dev gate wiring, Judge model pin

---

## Check executor design

| Option | Description | Selected |
|--------|-------------|----------|
| `[[checks]]` typed tables | Array of tables w/ type discriminator (cmd / file_exists / file_contains); pydantic discriminated union | ✓ |
| String mini-DSL | `checks = ["cmd: pytest -q", ...]` — compact but stringly-typed | |

| Option | Description | Selected |
|--------|-------------|----------|
| Run all, report all | Every check executes; per-check results array in JSONL | ✓ |
| Short-circuit first fail | Stop at first failing check | |

| Option | Description | Selected |
|--------|-------------|----------|
| 60s, per-check override | Optional `timeout` field on cmd checks | ✓ |
| 30s fixed | Tighter, risky for pytest-in-fixture | |
| You decide | Claude picks at plan time | |

**User's choice:** Typed tables, run-all, 60s+override.

---

## Cap defaults + wiring

| Option | Description | Selected |
|--------|-------------|----------|
| 15 | Generous headroom over 3–8 turn golden tasks | ✓ |
| 10 | Tighter, small cap-legit-work risk | |
| 25 | Catches only true runaways | |

| Option | Description | Selected |
|--------|-------------|----------|
| Skip judge on capped | Capped = FAIL; judge_verdict="skipped" | ✓ |
| Judge partial output | Rationale on near-misses, costs a judge call | |

| Option | Description | Selected |
|--------|-------------|----------|
| `[eval]` config + CLI flag | Config defaults, `--max-turns` overrides | ✓ |
| Flag + module constant only | No config plumbing | |

---

## Dev gate wiring

| Option | Description | Selected |
|--------|-------------|----------|
| CLI command callback | Gate at verb entry; run_suite stays importable | ✓ |
| Inside run_suite | Also blocks programmatic use | |

| Option | Description | Selected |
|--------|-------------|----------|
| `VOSS_DEV=1` | Generic internal-tooling gate, reusable E3–E5 | ✓ |
| `VOSS_EVAL=1` | Narrow, per-verb vars proliferate | |

| Option | Description | Selected |
|--------|-------------|----------|
| Conftest autouse + 2 gate tests | Suite stays green; explicit deny/allow tests | ✓ |
| You decide | Claude picks at plan time | |

---

## Judge model pin

| Option | Description | Selected |
|--------|-------------|----------|
| Smaller/cheaper gpt-5.x variant | Less sub burn, bias split achieved | ✓ |
| Same tier different variant | Equal-strength judge, more burn | |
| You decide | Researcher picks id at plan time | |

| Option | Description | Selected |
|--------|-------------|----------|
| Warn + proceed on same-model | Stderr warning, user override intentional | ✓ |
| Hard error | Force split always | |

---

## Claude's Discretion

- Dev-gate stderr wording + same-model warning wording
- Conftest mechanics
- Concrete judge model id (within smaller-gpt-5.x constraint)
- summary.md column layout for gate-pass vs judge-rate
- Turn-counter hook point (runner vs harness param) — least invasive wins

## Deferred Ideas

- Live-proof artifact commit policy — decide at execution
- Repeat-N success-rate aggregation — E2+
- `VOSS_DEV` gate reuse for E3–E5 internal verbs
