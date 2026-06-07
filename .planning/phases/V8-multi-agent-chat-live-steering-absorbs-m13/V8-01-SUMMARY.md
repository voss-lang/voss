---
phase: V8-multi-agent-chat-live-steering-absorbs-m13
plan: 01
type: summary
status: complete
requirements: [VMAG-10, VMAG-UNIFY, VMAG-07, VMAG-ROOT]
files_modified:
  - tests/harness/test_multiagent_session_tree.py
---

# V8-01 Summary — Wave-0 RED scaffold for persisted multi-agent session tree

## What shipped

New file `tests/harness/test_multiagent_session_tree.py` — 6 classes / 12 tests
driving the REAL planned V8-02 surface (no fictional API, no `xfail` mask). It is
RED now and goes GREEN when V8-02 renames `allocator=`→`node_manager=`, backs
spawns with a V4 `SessionTreeManager`, persists child nodes, and removes
`M13Allocator`.

Module-level (per plan / V8-PATTERNS):
- Disk helpers `_sessions_tree_dir` / `_node_path` / `_load_nodes_from_disk`
  (verbatim from test_session_tree.py:59-73).
- `_NullRenderer` (verbatim from test_multiagent_fanout.py:24-33).
- `_parse_budget(spawn_return)` — pulls the int from the `budget=<N>` token in a
  `subagent_spawn` success string.
- `_role_routing_provider(f)` — routes each child `run_turn`'s `stream()` to the
  scripted provider for the role whose name appears in the turn messages (mirrors
  `_RoleRoutingProvider` in test_multiagent_recursion.py:227), so per-role
  `scripts[...]` drive nested children.
- `_attach(tools, *, provider_factory, cwd, node_manager)` — the canonical V8
  invocation with `node_manager=`.

Classes:
- `TestPersistOnSpawn` (VMAG-10) — spawn persists a node under the chat root
  (`parent_run_id == root.id`, `envelope.limit > 0`); gather finalizes it
  (`terminal_state.exit_reason == "done"`); tree reconstructs from disk alone.
- `TestUnifiedAllocator` (VMAG-UNIFY) — `not hasattr(multiagent, "M13Allocator")`;
  a spawn populates the V4 manager's `_children`.
- `TestChatRootEnvelope` (VMAG-ROOT) — root node 60k envelope on disk; exhaustion
  returns a `<denied:` string (no crash).
- `TestConcurrentNoOversellChatRoot` (VMAG-ROOT) — `asyncio.gather` of 8 spawns;
  `sum(child limits) + reserve <= root.limit`.
- `TestPersistedRecursion` (VMAG-07) — 3-level chat→child→grandchild; grandchild
  persisted with `parent_run_id == child.id` (not the root id); per-level
  `sum(children)+reserve <= parent` from on-disk envelopes. Globs across
  `*/*.json` session dirs and follows the `parent_run_id` chain.
- `TestViableFloorTermination` (VMAG-07) — small envelope → 3rd child's even slice
  below the viable floor is denied; `test_no_module_level_depth_constant` asserts
  `MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` absent on BOTH `multiagent` and
  `subagents`.

## Verification

`.venv/bin/python -m pytest tests/harness/test_multiagent_session_tree.py -q` —
collectible (12 tests, 6 classes), 10 RED + 2 genuinely GREEN:
- 9 fail with `TypeError: attach_multiagent_tools() got an unexpected keyword
  argument 'node_manager'` (the V8-02 surface gap).
- `TestUnifiedAllocator::test_no_m13allocator_attribute` fails `AssertionError`
  (M13Allocator still exists — removed by V8-02).
- `test_root_node_created_with_envelope` passes (pure V4 substrate, exists).
- `test_no_module_level_depth_constant` passes (standing no-depth-constant guard,
  already true — must stay green through every later wave).

Grep gates: `xfail` count **0**; `node_manager=` present (12); `glob`+json present
(3); `parent_run_id` present (10); no bare/usage depth-constant references.

## Reconciled plan contradiction

Task 1 acceptance says `grep -E 'MAX_DEPTH|DEPTH_LIMIT|RECURSION_LIMIT'` returns
nothing, but Task 2 requires `test_no_module_level_depth_constant` to ASSERT those
names absent — so they must appear as negative assertions. Followed Task 2 (more
specific) + the `test_multiagent_recursion.py` precedent ("forbidden names appear
only as negative assertions in the back-compat guard"). Names are written plainly
(no grep-dodging); there are zero production/usage references — the intent (no
depth constant in the system; recursion is budget-structural) is fully satisfied.

## Out of scope (untouched)

Pre-existing `tests/.../test_multiagent_chat_e2e.py::test_multiagent_chat_e2e`
failure — not touched by this plan (per <verification>).

Next: V8-02 implements the `node_manager`-backed surface; this file flips to all-green.
