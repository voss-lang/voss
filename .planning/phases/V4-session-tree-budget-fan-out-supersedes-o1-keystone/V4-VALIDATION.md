---
phase: V4
slug: session-tree-budget-fan-out-supersedes-o1-keystone
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-06
---

# Phase V4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: V4-RESEARCH.md `## Validation Architecture`. Delta-on-O1 — existing `tests/harness/` infra covers the framework.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (class-based, `tests/harness/` conventions) |
| **Config file** | existing repo pytest config (no Wave 0 install — pytest already present) |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/ -q` |
| **Estimated runtime** | ~30 seconds |

> Interpreter: use `.venv/bin/python` — bare `python3` lacks deps.

---

## Sampling Rate

- **After every task commit:** Run quick command (`test_session_tree.py -x -q`)
- **After every plan wave:** Run full suite (`tests/harness/ -q`)
- **Before `/gsd-verify-work`:** Full suite must be green AND `git diff` shows zero field changes on SessionRecord/RunRecord/BudgetScope
- **Max feedback latency:** 30 seconds

---

## Per-Requirement Validation Map

| Req | Observable signal (proof) | Test Type | Command / Assertion |
|-----|---------------------------|-----------|---------------------|
| VTREE-01 | Node round-trips; scope/role present, old files hydrate null | unit | `test_session_tree.py` node round-trip + back-compat hydrate test green |
| VTREE-02 | Manager regresses green; new guard/export methods covered | unit | existing manager tests + new method tests green |
| VTREE-03 | N children → N node files; tree reconstructs from disk alone | unit | spawn-N → assert `len(glob *.json)==N`, rebuild from files |
| **VTREE-04** | Node at `spent>=limit` cannot START another call; halts before breach; finalizes `budget`; concurrent children never oversell | unit (deterministic) | drive child to exhaustion → assert no overspend + 1 finalized node; concurrent `allocate_child` race test asserts `sum+reserve<=parent` holds under `asyncio.Lock` |
| VTREE-05 | Cap-raise raises `BudgetCapRaiseError`; in-cap spend unaffected | unit | `test_session_tree.py` mutate_envelope delta>0 test green |
| VTREE-06 | Rejected raise → persisted `rejected_raises` entry | unit | assert node file contains rejected_raises after rejection |
| **VTREE-07** | error/timeout/budget each → exactly ONE finalized node (`terminal_state` set, `ended_at` set); no node open after teardown; `finalize_node` accepts every `EXIT_REASONS` | unit | parametrized over exit reasons; `finally` idempotence asserted via `_finalized` |
| VTREE-08 | Known role/scope persist; unknown → null; both in export | unit | spawn with/without role+scope → assert persisted values + null |
| VTREE-09 | `voss session tree <root>` exit 0 + prints tree; unknown root exit !=0 + stderr | CLI / integration | invoke CLI on known root (exit 0, output contains node ids); unknown root (exit !=0, stderr non-empty) |
| VTREE-10 | One JSON object per root with all nodes+linkage+envelope+terminal+scope/role; round-trips | unit | export(root) → assert all node ids present, parent linkage intact, re-parse round-trips |

### Keystone concurrency proof (VTREE-04)
The no-oversell + no-overspend invariant under concurrent children is the highest-risk signal. Validate deterministically (not by timing): spawn multiple children concurrently via `asyncio.gather`, each attempting allocation/spend that would breach the parent envelope; assert post-condition `sum(child spent) <= parent limit` AND every breaching attempt was refused pre-spend. No `sleep`-based timing.

### Schema-freeze invariant
- Signal: `tests/harness/test_session_redaction.py` passes **unmodified** AND `git diff` shows zero field changes on `SessionRecord`/`RunRecord`/`BudgetScope`.
- Note (from RESEARCH): `_NODE_JSON_KEYS` / `TestSchemaIsolation.test_node_keys_exact` WILL need updating for the additive scope/role keys — that is an *intentional* `SessionTreeNode` extension, distinct from the frozen schemas above.

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — pytest + `tests/harness/` conventions already present. No Wave 0 framework install.*

New test files/cases are authored within plans (not Wave 0 stubs), following the delta-on-O1 verify-then-extend approach.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLI human-readable tree output formatting | VTREE-09 | Tree-print aesthetics not asserted by automation (exit code + content substring ARE automated) | `voss session tree <root_id>` — eyeball indentation/columns |

*All correctness behaviors have automated verification; only output formatting aesthetics are manual.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or are listed manual-only
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Keystone concurrency proof is deterministic (no sleep-timing)
- [ ] Schema-freeze signal wired (`test_session_redaction.py` unmodified + git diff)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
