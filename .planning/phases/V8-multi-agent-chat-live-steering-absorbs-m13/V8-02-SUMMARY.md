---
phase: V8-multi-agent-chat-live-steering-absorbs-m13
plan: 02
type: summary
status: complete
requirements: [VMAG-10, VMAG-UNIFY, VMAG-07, VMAG-ROOT]
files_modified:
  - voss/harness/session_tree.py
  - voss/harness/multiagent.py
  - voss/harness/cli.py
  - tests/harness/test_multiagent_session_tree.py  # see Deviation 4 (V8-01 helper fix)
---

# V8-02 Summary — V4-backed multi-agent unification

## What shipped

Swapped the in-memory even-split allocator for the V4 persisted
`SessionTreeManager`. Every chat spawn is now a persisted session-tree node;
recursion fans out via per-node managers; the chat session has a V4 root
envelope. V8-01's RED scaffold is GREEN (12/12).

- **session_tree.py** — additive `SessionTreeManager.release_child(node_id)`:
  prunes a finished child from `_children` so its envelope frees for
  reallocation (idempotent, holds no lock). ONLY change to the file; no frozen
  field touched.
- **multiagent.py** — removed `M13Allocator`; added `VIABLE_FLOOR` alias and the
  `from .session_tree import …` block. `attach_multiagent_tools` param
  `allocator` → `node_manager: SessionTreeManager`. `ChildHandle` gains
  `node: Any = None` (last field; `sub_allocator` kept, deprecated, set to None).
  `subagent_spawn` does inline even-split → `node_manager.allocate_child(scope=
  "chat", role=agent)` (BudgetAllocationError = authoritative no-oversell guard)
  → builds a per-node `SessionTreeManager(child_node, reserve=VIABLE_FLOOR)` and
  recurses with `node_manager=`. `subagent_status` snapshots from
  `node_manager._children`. `subagent_gather` / `_teardown_orphans` call
  `finalize_node` (done/error/interrupt, guarded `if h.node is not None`) +
  `release_child`. No depth constant anywhere.
- **cli.py** — imports `DEFAULT_PARENT_RESERVE` + session_tree symbols; creates
  `_chat_root = create_root(limit=60_000)` + `_chat_tree = SessionTreeManager(
  reserve=DEFAULT_PARENT_RESERVE)` ONCE per `_run_repl`; injects
  `node_manager=_chat_tree`; finalizes `_chat_root` (`exit_reason="done"`,
  idempotent) in the session-exit `finally`.

## Deviations from plan (4 — all plan contradictions reconciled)

1. **Even-split `// (active + 2)`** (operator-approved). PATTERNS/plan specified
   `allotment = available // n` (n=active+1), which is greedy: the first child
   takes ALL available, so every 2nd sequential spawn is denied — incompatible
   with V8-01's `test_tree_reconstructs_from_disk` (2 children must coexist).
   M13 made this work by rebalancing existing children down, but V4 node limits
   are immutable. Reserving headroom (`// (active+2)`) lets sequential children
   coexist; no-oversell (BudgetAllocationError) and viable-floor denial still
   hold. Trade-off: not exact `limit//k` equality (loosely affects the V8-03
   migration "≈limit//3" assertion — to reconcile there).

2. **V4-backed fallback when `node_manager is None`**. The plan said "remove the
   fallback, no in-module construction." But V8-03 (line 72) requires
   `TestOrphanTeardown` (a non-xfail hard gate) to stay green UNCHANGED, and it
   calls `attach` without `node_manager`. Reconciled by constructing a default
   V4 `SessionTreeManager` (fresh root, 60k/`DEFAULT_PARENT_RESERVE`) when none
   is injected — NOT the removed `M13Allocator`, so
   `test_no_m13allocator_attribute` stays green. cli.py's explicit injection
   overrides it.

3. **`allocator` grep can't be empty**. Task-2 acceptance says
   `grep -E 'allocator' multiagent.py` returns nothing, but the same task
   mandates KEEPING the `sub_allocator` field (which contains "allocator").
   Kept `sub_allocator` (plan-mandated); the only remaining `allocator` matches
   are that deliberately-retained back-compat field + its `=None` construction.
   `M13Allocator` mentions and the literal `MAX_DEPTH/DEPTH_LIMIT/RECURSION_LIMIT`
   tokens were reworded out of comments/docstrings (both greps now 0).

4. **Fixed the V8-01 test router** (`tests/harness/test_multiagent_session_tree.py`,
   beyond the declared 3 files). The `_role_routing_provider` I wrote in V8-01
   routed by scanning the WHOLE serialized message blob, which is contaminated:
   run_turn injects `Working directory: <tmp_path>`, and the pytest tmp_path
   embeds the test name `test_grandchild_node_persisted` → "grandchild" leaked
   into child-a's input → misrouted child-a to the grandchild script. Fixed to
   route on the last user-message text with the `Working directory` suffix
   stripped. Pure test-double fix (production never routes by string); no debug
   residue; xfail count stays 0.

## Verification

- `test_multiagent_session_tree.py` — **12/12 GREEN**.
- `test_session_tree.py` (40), `test_subagent_recursion.py`, fanout + recursion
  suites (xfail/xpass, no failures), `TestOrphanTeardown` (hard gate) — green.
- `import voss.harness.cli` — OK. cli greps: `create_root(cwd=cwd, limit=60_000)`,
  `node_manager=_chat_tree`, `finalize_node(_chat_root` each ×1.
- multiagent greps: `M13Allocator`=0, depth-consts=0, `finalize_node(`=3,
  `subagents.py` byte-unchanged.
- Frozen records (session.py/recorder.py/voss_runtime) untouched across V8;
  schema-freeze (`-k schema`) + `test_session_redaction.py` green. Only new
  dataclass field in the phase: `ChildHandle.node`.

## Out of scope / pre-existing (verified unchanged on baseline)

- `tests/e2e/test_multiagent_chat_e2e.py::test_multiagent_chat_e2e` — same
  AUTH_STEERED failure (line 399); not regressed (no crash/TypeError from V8).
- `test_repl_slash.py::test_m10_code_slash_commands_execute` — fails identically
  with V8-02 changes stashed (pre-existing `## Project Index` empty-output bug).

Next: V8-03 migrates the M13Allocator-direct fanout/recursion tests onto the V4
path (xfail dropped) + M13-absorbed bookkeeping.
