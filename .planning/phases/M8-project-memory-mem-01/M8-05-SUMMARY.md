---
phase: M8
plan: 05
status: complete
date: 2026-05-14
---

# M8-05 Summary — Memory Slash Commands (MEM-05)

Four new module-level slash handlers in `voss/harness/cli.py` dispatch to
`MemoryStore` via the existing `SlashRegistry`. `ctx.memory_store` was bound
at REPL boot during M8-04; this plan adds the user-facing surface that uses
it. Pitfall 1 regression pinned by `test_save_note_does_not_rename_session`.

## Slash Command Surface

| Command | Args | Behavior |
|---------|------|----------|
| `/recall <query> [--top N] [--source <s>]` | top default 5; source ∈ turn/decision/convention/ledger/note | Calls `memory_store.recall(query, top_k=N, source=source)`; prints one `[<source>] <locator>  (score 0.NN)` header per hit + truncated excerpt. Empty hit-set prints `(no hits)`. |
| `/forget <pattern> [--yes]` | mutating=True | Calls `memory_store.forget(pattern, confirm=confirm)`. Non-interactive (`sys.stdin.isatty() == False`) without `--yes` → stderr `requires --yes` + early return. |
| `/memory [--source <s>]` | | Calls `memory_store.summary(source=source)`; prints the markdown verbatim. |
| `/save <note>` | mutating=True | Calls `memory_store.write_note(text, session_id=ctx.record.id)`; prints `note saved: <path>`. **MUST NOT mutate `ctx.record.name`** — that is `/save-session`'s job. |

All four handlers live at module scope (`voss.harness.cli._recall`,
`_forget`, `_memory`, `_save_note`) and are importable for direct unit tests.

`_pop_flag_value(args, flag)` is a shared mini-parser used by `/recall` and
`/memory` to extract `--top` / `--source` keyword args from positional shlex
output.

## REPL Bind Wire

`ctx.memory_store = MemoryStore(cwd).bind(session_id=record.id)` is set in
`_run_repl` boot during M8-04 (alongside the conventions hook setup). M8-05
adds the consumers; no new boot wire required. `ReplContext.memory_store`
is the `object | None` field on the dataclass.

## Pitfall 1 Invariant

- `/save` (memory note) and `/save-session` (snapshot, renamed in M8-00) coexist as distinct registry entries.
- `_save_note` opens with `# Pitfall 1 invariant: do NOT mutate ctx.record.name — that is /save-session's job.`
- Regression test `tests/harness/test_slash_save_note.py::test_save_note_does_not_rename_session` asserts `ctx.record.name == "original-name"` after `_save_note(ctx, ["a", "new", "note"], ...)` — fails loudly if /save accidentally reverts to the old _save_session behavior.

## `/forget --yes` Gate

`_forget` reads `sys.stdin.isatty()`; non-interactive callers (CI, pipes, harness tests) must include `--yes` in args or get a stderr message and zero side effect. `--yes` is only honored from `args[1:]` (after the pattern), so `/forget --yes alone` is treated as pattern=`--yes`, no confirm — defensive against ambiguous orderings.

## Tests (9 new + 1 updated)

| File | Tests |
|------|-------|
| `tests/harness/test_slash_recall.py` | `test_recall_command_registered`, `test_recall_returns_top_n_with_source_filter`, `test_recall_no_args_prints_usage` |
| `tests/harness/test_slash_forget.py` | `test_forget_tombstones_matching_ids`, `test_forget_requires_yes_noninteractive` |
| `tests/harness/test_slash_memory.py` | `test_memory_summary_renders_counts_per_source` |
| `tests/harness/test_slash_save_note.py` | `test_save_note_writes_to_memory_notes_dir`, `test_save_note_does_not_rename_session`, `test_save_with_no_args_errors` |
| `tests/harness/test_repl_slash.py` | M8-00 placeholder replaced with `test_memory_commands_registered` — asserts all 5 of `/recall`, `/forget`, `/memory`, `/save`, `/save-session` are in the registry |

## Acceptance Gate Status

| Gate | Result |
|------|--------|
| `python -c "from voss.harness.cli import _recall, _forget, _memory, _save_note"` | passes |
| `grep -nE 'SlashCommand\("/(recall|forget|memory|save)"' voss/harness/cli.py` | 4 |
| `grep -nE 'SlashCommand\("/save-session"' voss/harness/cli.py` | 1 (M8-00 rename preserved) |
| `grep -nE "MemoryStore\(cwd\)\.bind" voss/harness/cli.py` | 1 (set in `_run_repl` boot during M8-04) |
| `grep -nE "memory_store:" voss/harness/cli.py` | ReplContext field present |
| `grep -v '^#' tests/harness/test_slash_save_note.py | grep -c "pytestmark.*skip"` | 0 |
| `grep -c 'record\.name == "original-name"' tests/harness/test_slash_save_note.py` | 1 (Pitfall 1 regression) |
| `grep -cE "^def test_" tests/harness/test_slash_*.py` total | 9 (≥7) |
| Full harness suite (excl. pre-existing diagnostics failures) | 283 passed, 7 skipped |

## Deviations from Plan

1. **Handlers at module scope** instead of nested in `_build_slash_registry`. Plan acceptance gate requires `from voss.harness.cli import _recall, ...` to succeed; nested closures would not be importable. Existing handlers (`_save_session`, `_help`, …) remain nested — only the four new M8-05 handlers are promoted to module scope. Trade-off: pure win for testability; no downside since they don't close over registry-local state.

2. **`MemoryStore(cwd).bind(...)` was already wired in M8-04**, not in this plan. Plan task 1(b) instructed insertion in `_run_repl`; M8-04 did so as part of the conventions hook wire. This plan verifies the binding is present and proceeds.

3. **`_pop_flag_value` shared helper** added to factor the `--top` / `--source` flag-extraction logic out of `_recall` and `_memory`. Plan suggested inline parsers; the helper deduplicates and keeps token-not-after-flag failure modes consistent.

4. **9 slash tests instead of 7** — added `test_recall_no_args_prints_usage` and `test_save_with_no_args_errors` for symmetry on the usage-line code path. Additive.

No other deviations.
