---
phase: V8
slug: multi-agent-chat-live-steering-absorbs-m13
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-06
---

# Phase V8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from V8-RESEARCH.md `## Validation Architecture` + `## Security Domain` + `## Dependency Readiness`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2, asyncio-mode=auto (pytest-asyncio 1.3.0) |
| **Config file** | pyproject.toml (`asyncio_mode = "auto"`) |
| **Quick run command** | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/harness/ -q --tb=short` |
| **Estimated runtime** | ~30 seconds |

> **Use `.venv/bin/python`** — bare `python3` lacks deps (memory `voss-python-interpreter`).
> **Sequencing:** V8 hard-depends on **V4 + M13**. Verified at research time: V4-01+V4-02 on disk (scope/role, `"error"` reason, pre-emptive guard, all-reason finalize); V4-03 (export/CLI) NOT on disk — **V8 does not need it** (uses inline glob helpers). M13 **fully shipped** (all 10 xfail XPASSED, incl. in-memory recursive fan-out). Execute V8 only after V4-03 lands OR confirm V8 tasks avoid V4-03 surface.
> **Known pre-existing failure (DO NOT regress, fixing is out of scope):** `tests/.../test_multiagent_chat_e2e.py::test_multiagent_chat_e2e` fails on `AUTH_STEERED` before V8. V8 must add no NEW failures there.

---

## Sampling Rate

- **After every task commit:** `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -x -q`
- **After every plan wave:** `.venv/bin/python -m pytest tests/harness/ -q --tb=short`
- **Before `/gsd-verify-work`:** Full suite green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Req ID | Behavior | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists |
|--------|----------|------------|-----------------|-----------|-------------------|-------------|
| VMAG-10 | `/agent spawn` creates persisted V4 node; terminal finalized on disk; tree reconstructs from persisted nodes | — | N/A | unit/integration | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestPersistOnSpawn -x -q` | ❌ W0 |
| VMAG-UNIFY | Chat spawns via V4 `SessionTreeManager`; no separate in-memory allocator remains | — | N/A | unit | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestUnifiedAllocator -x -q` | ❌ W0 |
| VMAG-UNIFY | M13 spawn/gather/steer tool surface still works | — | N/A | regression | `.venv/bin/python -m pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_steer.py -x -q` | ✅ |
| VMAG-07 | Child-of-child persists as nested node; invariant `sum+reserve≤parent` at each level | T-V8-01 (Tampering) | Per-manager `asyncio.Lock`; `available` under lock | unit | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestPersistedRecursion -x -q` | ❌ W0 |
| VMAG-07 | Recursion terminates via viable-floor — NO depth/max_depth constant | T-V8-02 (DoS via depth) | `even < VIABLE_FLOOR → BudgetAllocationError`; budget-structural bound | unit | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestViableFloorTermination -x -q` | ❌ W0 |
| VMAG-ROOT | Chat root node w/ 60k (configurable) envelope + carved reserve; spawns draw from it; exhaustion denies | — | Session-scoped root; finalize on exit | unit | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestChatRootEnvelope -x -q` | ❌ W0 |
| VMAG-ROOT | Concurrent chat spawns cannot oversell the chat root | T-V8-01 (Tampering) | `asyncio.Lock` no-oversell | unit | `.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py::TestConcurrentNoOversellChatRoot -x -q` | ❌ W0 |
| verify | MAG-01..09 regress green (non-blocking spawn/handle/status/gather/steer/child-budget) | — | N/A | regression | `.venv/bin/python -m pytest tests/harness/test_multiagent_fanout.py tests/harness/test_multiagent_recursion.py tests/harness/test_multiagent_steer.py -x -q` | ✅ |
| verify | `test_subagent_recursion.py` green (zero changes — viable-floor const not in subagents.py) | — | N/A | regression | `.venv/bin/python -m pytest tests/harness/test_subagent_recursion.py -x -q` | ✅ |
| verify | Ctrl+C interrupts → `_teardown_orphans` + finalize | T-V8-04 (DoS orphan) | finalize on cancel; no leaked node/panel | regression | `.venv/bin/python -m pytest tests/harness/test_multiagent_fanout.py::TestOrphanTeardown -x -q` | ✅ |
| verify | TUI panel quiet-by-default + explicit reveal | — | N/A | manual-only | Visual inspection in TUI | N/A |
| bookkeeping | `git diff` zero field changes on RunRecord/SessionRecord/BudgetScope | — | Frozen-schema invariant | static/regression | `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q` + `git diff` review | ✅ |
| bookkeeping | M13 absorbed in ROADMAP/STATE; no ADE panel built | — | N/A | manual-only | Review ROADMAP/STATE | N/A |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/harness/test_multiagent_session_tree.py` — NEW file: `TestPersistOnSpawn` (VMAG-10), `TestUnifiedAllocator` (VMAG-UNIFY), `TestPersistedRecursion` + `TestViableFloorTermination` (VMAG-07), `TestChatRootEnvelope` + `TestConcurrentNoOversellChatRoot` (VMAG-ROOT). Reuse the M13 `scripted_multiagent_provider` fixture.
- [ ] Migrate `test_multiagent_fanout.py::TestEvenSplitRebalance` + `TestNoOversell` to the V4-backed allocation path.
- [ ] Migrate `test_multiagent_recursion.py::TestDepth2` to the persisted-nested-node version.

*`test_subagent_recursion.py` needs zero changes (research-confirmed).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TUI panel quiet-by-default + reveal | verify (MAG-08/09) | Visual TUI state | Launch chat, spawn agents, confirm panel quiet; trigger reveal key; confirm Ctrl+C interrupts |
| Frozen-schema zero-field-change | bookkeeping | `git diff` field-level | `git diff` on session/recorder/`voss_runtime` budget; confirm no field change on RunRecord/SessionRecord/BudgetScope (SessionTreeNode changes are V4's) |
| M13 absorbed | bookkeeping | Doc bookkeeping | Confirm ROADMAP/STATE mark M13 absorbed into V8 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (1 new file + 2 migrations)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
