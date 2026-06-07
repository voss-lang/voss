---
phase: V7-engineering-manager-loop-supersedes-o5
plan: 02
type: summary
status: complete
requirements: [VEM-CLI, VEM-PERSIST, VEM-SIGNOFF]
files_modified:
  - voss/harness/cli.py
  - tests/harness/board/test_stub.py
  - tests/harness/em/test_em_handle_dispatch.py
---

# V7-02 Summary — `voss team run` composition + persistence + sign-off

## What shipped

Turned the V7-01 RED scaffold (10 tests) GREEN by adding three things to
`voss/harness/cli.py` — pure composition of the shipped V3–V6 + O5 stack, no
reimplementation:

1. **`_default_team_config()`** — module helper. Direct construction (no AST
   `TeamDecl`) of a `TeamConfig` over `DEFAULT_ROSTER` + a `SubagentRegistry`
   with one spec per role (`apply_role_defaults=True`, synthetic `Span`,
   ceiling 500_000 tokens / 3600s / scope None).

2. **`_persist_run_final(rf, cwd, decision=None)`** — module helper mirroring
   `session_tree._write_node_file`: writes
   `<cwd>/.voss/sessions/<rf.root_id>/run-final.json` via
   `dataclasses.asdict(rf)`, `mkdir(parents=True)`, `chmod(0o600)`. Adds a
   superset `sign_off` key `{decision, ts}` when a decision is passed.
   root_id is sourced ONLY from `rf.root_id` (SessionTreeNode UUID) — no path
   traversal (T-V7-05). RunFinal never mutated.

3. **`@team_group.command("run")` (`team_run_cmd`)** — `voss team run "<goal>"`.
   Resolves `.voss/team.voss` (parse + `compile_team`) or falls back to
   `_default_team_config()`. Builds the stack in order: session root + manager →
   **both** real V6 reviewer slots (`reviewer_a` source=A/fast, `reviewer_b`
   source=B/strong) → `Board.from_team_config` → `await board.spawn_card("med")`
   (pre-spawn so `total_cards>=1`) → `EMBoardHandle` → `DeterministicEMStub`
   (CreateTicketOp then NoopOp) → `em_loop` via `asyncio.run`. Persists RunFinal,
   prints a summary, `click.prompt(Choice(approve/reject))`, re-persists with the
   decision. reject is record-only (no disk revert).

## Deviations from plan

- **`rf = dataclasses.replace(rf, idea=goal)`** before persist. `em_loop`'s
  `finalize_run()` hardcodes `idea=""` (handle.py:352); the V7-01 contract
  (`test_rereadable`, `test_prompt_appears`) requires `rf.idea == goal`. Threaded
  the goal in via the same frozen-replace mechanism `em_loop` already uses to
  patch `em_iterations` — keeps `cli.py` the only production file touched and does
  not mutate the frozen record.

- **Scoped the V6 production-import guard** (user decision). `team_run_cmd`
  imports `DeterministicReviewerStub` into shipped `cli.py`, which tripped
  `tests/harness/board/test_stub.py::TestProductionImportGuard`. Per user
  direction, allowlisted `voss/harness/cli.py` (alongside `stub.py`) in that
  test, with a docstring explaining the smoke-run rationale. The guard stays
  meaningful for **every other** production file — the always-pass stub still
  cannot silently back a real review path anywhere else. SPEC explicitly frames
  this command as "exits 0 on stub provider", so the stub-backed CLI is the
  intended V7 deliverable. Real provider-backed `ReviewerA`/`ReviewerB` (needing
  a live provider) are the eventual replacement.

## Verification

- `tests/harness/test_team_run_cli.py` — **10/10 GREEN**.
- `tests/harness/em/` (required cage gate) — **green** (isolated + plan order).
- `tests/harness/board/` — **green** (guard scoped).
- Plan's exact gate `em/ + test_team_run_cli + test_team_check` — **green**.

## Pre-existing cross-suite flake — found and fixed

Running `tests/harness/board/` and `tests/harness/em/` in the **same** process
(board before em) yielded 3 `RuntimeError: There is no current event loop`
failures in `test_em_handle_dispatch.py`. Root cause: those 3 tests were sync
`def` methods hand-rolling `asyncio.get_event_loop().run_until_complete(...)`,
which raises in Python 3.13 once a prior `asyncio.run` (board's async tests) has
closed the loop — even though the suite is configured `asyncio_mode = "auto"`.
Reproduced on the untouched `board/ + em/` combo with zero V7 files involved
(pre-existing, not introduced here).

Fixed in-branch (3 identical swaps): `asyncio.get_event_loop().run_until_complete(X)`
→ `asyncio.run(X)`, which always uses a fresh loop and is immune to prior-suite
pollution. Folded in because V7-03 (cage re-verification) runs `em/` + `board/`
together and would otherwise open with phantom RED. Full
`board/ + em/ + test_team_run_cli + test_team_check` combo now green in the
polluting order.

## Cage

EMBoardHandle injected unchanged; no mutation methods added. Cage invariants
re-verified in V7-03 (not this plan).
