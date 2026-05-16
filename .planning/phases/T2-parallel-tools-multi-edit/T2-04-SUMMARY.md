---
phase: T2-parallel-tools-multi-edit
plan: 04
type: summary
---

# T2-04 Summary — `fs_edit_many` atomic single-file multi-edit (PAR-03)

## Goal achieved

`fs_edit_many(path, edits=[{old, new}, ...])` lands as a new mutating
tool. Validates all edits against a working buffer left-to-right; aborts
the entire batch on any uniqueness / not-found failure (file unchanged);
builds `list[Hunk]` for M9-05 DiffModal; treats any `reject` OR `skip`
decision as batch denial (atomicity invariant); writes once on
all-accept. Registered with `is_mutating=True` alongside the unchanged
`fs_edit` tool (D-10). `make_toolset` signature extended to
`(cwd, *, renderer=None)`; production call sites threaded with the
agent's renderer.

## Skip-is-strict decision (Open Question 1 resolved)

`d.decision in ("reject", "skip")` returns `<denied: hunk N rejected>`.
Rationale: atomicity invariant favors safety; per-hunk acceptance is
already available via N separate `fs_edit` calls. Documented in code
comment at `voss/harness/tools.py:198`. Locked here; downstream phases
treat skip and reject identically.

## Code locations

| Symbol | File | Line |
|--------|------|------|
| `DiffDecision`/`Hunk` import | `voss/harness/tools.py` | 12 |
| `make_toolset(cwd, *, renderer=None)` signature | `voss/harness/tools.py` | 45 |
| `fs_edit_many` definition | `voss/harness/tools.py` | 140–210 |
| `fs_edit` (preserved, D-10) | `voss/harness/tools.py` | 117–128 |
| `"fs_edit_many"` registration | `voss/harness/tools.py` | 281 |
| skip-is-strict check | `voss/harness/tools.py` | 200 |
| modal getattr guard | `voss/harness/tools.py` | 196 |

## make_toolset call sites

| File | Line | State |
|------|------|-------|
| `voss/harness/cli.py` | 1032 | `make_toolset(cwd, renderer=renderer)` — `do_cmd` |
| `voss/harness/cli.py` | 1256 | `make_toolset(cwd, renderer=renderer)` — chat_cmd path |
| `voss/harness/cli.py` | 1628 | `make_toolset(cwd)` — `tools_cmd` (lists tools only; no edits) |
| `voss/harness/cli.py` | 1651 | `make_toolset(cwd, renderer=renderer)` — `_extension_context` (reordered: renderer resolved before make_toolset) |
| `voss/harness/subagents.py` | 91 | `make_toolset(cwd, renderer=renderer)` |
| `voss/eval/runner.py` | 127, 149, 185, … | unchanged — eval uses `PlainRenderer` (no `show_diff_modal` attribute); the `getattr` guard in `fs_edit_many` skips the modal step automatically |
| `tests/**` | many | unchanged — default `renderer=None` |

## Renderer protocol guard

`fs_edit_many` checks `getattr(renderer, "show_diff_modal", None)` rather
than calling unconditionally. Three behavior paths:

1. `renderer is None` → modal skipped (test-friendly).
2. Renderer present but lacks `show_diff_modal` (JSON / Plain / eval) →
   modal skipped; tool still writes after validation.
3. Renderer exposes `show_diff_modal` (TUI) → modal blocks until user
   decides; reject/skip/empty → file unchanged.

The getattr approach is additive over plan code (which called
`renderer.show_diff_modal` unconditionally if not None); needed because
production has multiple renderer types and only the TUI renderer
implements the modal.

## Phase separation (atomicity invariant)

```
Phase 1 — validate-and-build against working buffer (no IO):
  for i, e in enumerate(edits):
      check empty old / not found / non-unique against `buf`
      if fail: return error envelope (file untouched)
      hunks.append(Hunk(...))
      buf = buf[:idx] + new + buf[idx+len(old):]

Phase 2 — modal (skipped when no show_diff_modal):
  decisions = renderer.show_diff_modal(hunks, timeout_s=300.0)
  if not decisions: return "<denied: modal cancelled or timed out>"
  for d in decisions:
      if d.decision in ("reject", "skip"): return "<denied: hunk N rejected>"

Phase 3 — single atomic write:
  p.write_text(buf)
  return "edited {path} ({sign}{delta} lines, {N} hunks)"
```

File is byte-for-byte unchanged on any failure path verified via
`Path.read_bytes()` before/after in tests.

## SPEC acceptance criteria mapping

| Fixture | Behavior | Test |
|---------|---------|------|
| a | all-match writes once | `test_all_match_writes`, `test_all_match_records_line_delta` |
| b | non-unique rejected, file unchanged | `test_ambiguous_rejected` |
| c | not-found rejected, file unchanged | `test_missing_rejected` |
| d | modal reject denies | `test_modal_reject_denies` |
| — | skip-is-strict (Open Question 1) | `test_modal_skip_denies_strict` |
| — | modal cancellation / timeout | `test_modal_cancelled_empty_denies` |
| — | left-to-right propagation | `test_buffer_propagation_left_to_right` |
| — | propagation creates ambiguity | `test_buffer_propagation_creates_new_ambiguity` |
| — | empty edits | `test_empty_edits_list` |
| — | empty old | `test_empty_old_string` |
| — | not found / dir / binary | `test_not_found`, `test_is_directory`, `test_binary_file` |
| — | jail violation propagates | `test_jail_violation_raises` |
| — | registration | `test_registered_with_is_mutating_true` |
| — | D-10 coexistence | `test_fs_edit_still_registered`, `test_both_tools_coexist_independently` |
| — | renderer=None test path | `test_renderer_none_skips_modal` |
| — | non-TUI renderer skip | `test_renderer_without_show_diff_modal_skips_modal` |
| — | Hunk shape | `test_hunks_passed_to_modal_have_expected_shape` |

## Pytest output

```
$ uv run pytest tests/harness/tools/test_fs_edit_many.py -x -q
.....................                                                    [100%]
21 passed
```

Regression (T2-03 partition + T2-01/02 + T1 surface):

```
$ uv run pytest tests/harness/test_tools.py tests/harness/test_partition_scheduler.py \
    tests/harness/test_permissions.py tests/harness/test_recorder.py \
    tests/harness/test_session_roundtrip.py tests/harness/test_agent_loop.py \
    tests/harness/test_agent_config.py tests/harness/test_cli_bootstrap.py \
    tests/harness/tools/ -x -q
...............................................s........................ [ 58%]
....................................................                     [100%]
126 passed, 1 skipped
```

The single skipped test pre-dates T2 (`test_decisions_mirror_to_markdown`
in `test_recorder.py`).

One pre-existing test updated for new mutating-tool count:
`tests/harness/test_tools.py::test_mutating_count` now asserts 5
mutating tools (was 4) — additive only.

## Acceptance grep gates

```
$ grep -n "async def fs_edit_many" voss/harness/tools.py
150:    async def fs_edit_many(path: str, edits: list[dict]) -> str:

$ grep -nE 'fs_edit_many.*is_mutating=True' voss/harness/tools.py
281:        "fs_edit_many": ToolEntry(descriptor=fs_edit_many, is_mutating=True),

$ grep -n '"fs_edit"' voss/harness/tools.py
280:        "fs_edit": ToolEntry(descriptor=fs_edit, is_mutating=True),

$ grep -n "renderer=None" voss/harness/tools.py
45:def make_toolset(cwd: Path, *, renderer=None) -> dict[str, ToolEntry]:

$ grep -n 'd.decision in ("reject", "skip")' voss/harness/tools.py
200:                if d.decision in ("reject", "skip"):

$ grep -cF "batch rejected at index" voss/harness/tools.py
3   (empty old, not found, non-unique)

$ grep -cF "denied: hunk" voss/harness/tools.py
1

$ grep -cF "denied: modal cancelled" voss/harness/tools.py
1

$ python -c "from voss.harness.tools import make_toolset; t = make_toolset('.'); print(t['fs_edit_many'].is_mutating, t['fs_edit'].is_mutating)"
True True
```

## Threat model verification

- **T-T2-04-01** (partial write on mid-batch failure): mitigated — 3-phase
  separation; tests assert byte-for-byte equality on rejection paths.
- **T-T2-04-02** (jail bypass): mitigated — `jail_path(cwd, path)` at
  function entry; `SandboxError` propagates (single-file primitive,
  whole-call failure); `test_jail_violation_raises`.
- **T-T2-04-03** (model bypass via renderer=None): mitigated — kwarg
  is keyword-only on `make_toolset`; LLM never invokes `make_toolset`.
  Production cli.py / subagents.py always pass the live renderer.
- **T-T2-04-04** (skip permissive): mitigated — locked STRICT;
  `test_modal_skip_denies_strict` confirms.
- **T-T2-04-05** (buffer drift): mitigated — validation walks `buf`, not
  `snapshot`; `test_buffer_propagation_creates_new_ambiguity` plants
  edit that becomes ambiguous after edit #1 and asserts rejection.
- **T-T2-04-06** (telemetry redaction of edits list): noted — existing
  `redact_tool_args` does not recurse into list-of-dict values, so
  `old`/`new` strings inside `edits` are emitted unredacted in
  `tool.call` events. **Follow-up suggested for T2-06 or a polish phase**:
  extend `redact_tool_args` to recurse into list[dict] when the key is
  `"edits"`. Out of scope for this plan per SPEC PAR-03 + the boundary
  on `_render_diff_preview` non-extension; flagged here so it doesn't
  silently regress.
- **T-T2-04-SC** (supply chain): accepted — no new third-party deps.

## Wave 3 handoff to T2-05

`fs_edit_many` is the single-file primitive. T2-05 introduces
`fs_read_many` (the partial-result read-batch primitive); it registers
with `is_mutating=False`, slots inside the T2-03 partition scheduler's
parallel read batches, and reuses none of `fs_edit_many`'s code paths
(reads and writes are deliberately distinct primitives).

Skip-is-strict semantics + `renderer.show_diff_modal` getattr guard
remain stable contracts for any future multi-edit variants.
