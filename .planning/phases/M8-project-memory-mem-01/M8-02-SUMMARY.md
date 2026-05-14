---
phase: M8
plan: 02
status: complete
date: 2026-05-14
---

# M8-02 Summary — Migration + Symmetric Read/Write Rewire (MEM-02)

`voss_md.ensure_migrated` is now functional. The COG-02 read path
(`cognition._load_arch_from_voss_md`) and write path
(`skills/analyze.py` via staging + `voss_md.write_fence_body`) both
operate on the `id=architecture` fence of `cwd/VOSS.md`. Pitfall 2 closed.

## Migration Semantics (`voss_md.ensure_migrated`)

- **Idempotent.** When `cwd/VOSS.md` exists, returns `False` without touching disk.
- **Byte-identical archive.** Reads `.voss/architecture.md` bytes, writes them to `.voss/archive/architecture-YYYY-MM-DD.md`, asserts `sha256(archive) == sha256(original)`. Mismatch raises `RuntimeError` and leaves the original intact.
- **Collision-safe archive filename.** Appends `-2`, `-3`, ... numeric suffix when today's archive already exists.
- **Verbatim fence fold.** Decodes architecture.md as UTF-8 (replacement chars + stderr warning on rare decode failure), calls `write_fence_body(VOSS.md, fence_id="architecture", body=…)`. Frontmatter stays at the head of the fence body so `cognition.FRONTMATTER_RE` keeps matching.
- **Atomic inheritance.** `write_fence_body` is already temp-file + `os.replace`, so the migration is crash-safe.
- **Cleanup.** After archive sha verification, `arch_path.unlink()` removes the original (the archive is now the byte-identical source of truth).

## Boot Wires

- `voss/harness/cli.py::_run_repl`: `voss_md.ensure_migrated(cwd)` runs immediately before `cognition_mod.load(...)`. The read path never sees a half-migrated state.
- `voss/harness/cli.py::do_cmd`: same insertion order before `do_bundle = cognition_mod.load(cwd)`.
- `voss resume` rides on `_run_repl` so it inherits the wire automatically.

## Read Path Rewire (`cognition.py`)

- New helper `_load_arch_from_voss_md(cwd, errors)`:
  - Tries `voss_md.read_fence_body(cwd/VOSS.md, fence_id="architecture")` first.
  - On `HashMismatch`: uses `exc.on_disk` as body (read paths must keep working; `voss memory adopt` is the formal accept flow per D-07).
  - On `(OSError, UnicodeDecodeError)`: appends to errors, returns `(None, None)` — never raises.
  - When VOSS.md is absent OR the architecture fence is absent: delegates to the legacy `_load_arch(.voss/architecture.md, errors)` so M2-style direct-write fixtures still work.
- Shared frontmatter parser `_parse_arch_text(label, text, errors)` lifted from the old `_load_arch` body to keep return-shape parity across both code paths.
- `load(cwd)` gate now uses `_is_initialized(cwd)` — true when `cwd/VOSS.md` exists OR legacy `.voss/architecture.md` exists. Matches `voss_md_path` OR fallback.
- Old `_load_arch` retained as DEPRECATED but functional fallback.

## Write Path Rewire (`skills/analyze.py`)

- Backup read via `voss_md.read_fence_body(VOSS.md, fence_id="architecture")` inside try/except for `HashMismatch` + `(OSError, UnicodeDecodeError)`.
- Staging file at `cognition.voss_dir(cwd) / ".analyze.staging.md"`. Deleted before the agent runs.
- Agent prompt now references `target_path=".voss/.analyze.staging.md"` via the new `bootstrap_prompt(inventory, *, target_path=...)` kwarg (default kept as `.voss/architecture.md` for any external callers).
- Single-`fs_write` contract preserved: agent emits exactly one fs_write to the staging path.
- Post-skill: read staged content; check `cognition.FRONTMATTER_RE.match(staged)`; on success fold via `voss_md.write_fence_body(VOSS.md, fence_id="architecture", body=staged)`. On failure, restore via `write_fence_body(..., body=arch_backup)` and emit the existing warning. If both fail (no backup, no good staged content), emit "re-run /analyze" warning and leave VOSS.md untouched.
- Staging file unlinked after fold (success or rollback).

## Tests

- `tests/harness/test_voss_md_migration.py` — 5 tests GREEN:
  - `test_archive_sha256_matches_pre_migration` (Req 2(a) sha equality + source unlink + return True)
  - `test_voss_md_contains_pre_migration_content` (FRONTMATTER_RE still matches at fence head)
  - `test_re_analyze_preserves_human_sections` (write_fence_body preserves trailing human paragraph + cognition.load round-trips "UPDATED machine content")
  - `test_ensure_migrated_idempotent_on_voss_md_present` (second-run safety)
  - `test_ensure_migrated_missing_sources_returns_false` (no architecture.md + no VOSS.md → False, no side effect)
- M2 cognition tests (test_cognition.py) remain green via the legacy fallback in `_load_arch_from_voss_md`.

## Acceptance Gate Status

| Gate | Result |
|------|--------|
| `pytest tests/harness/test_voss_md_migration.py -x` | green (5 passed) |
| `pytest tests/harness/test_voss_md_fence.py tests/harness/test_voss_md_injection.py -x` | green |
| `grep -v '^#' voss/harness/voss_md.py | grep -c "NotImplementedError"` | 0 (all stubs filled) |
| `grep -nc "voss_md.ensure_migrated" voss/harness/cli.py` | 2 (`_run_repl` + `do_cmd`) |
| `python -c "...ensure_migrated(Path('/nonexistent-zzz')) is False"` | passes |
| `grep -nE "_load_arch_from_voss_md\|voss_md\.read_fence_body" voss/harness/cognition.py` | 4 matches |
| `grep -nE "voss_md\.(read\|write)_fence_body" voss/harness/skills/analyze.py` | 4 matches |
| `grep -nE 'arch_path = cognition\.voss_dir\(cwd\) / "architecture\.md"' voss/harness/skills/analyze.py` | 0 |
| `root / "architecture.md"` inside `load()` body | 0 (gate now via `_is_initialized` helper) |
| Full harness suite ignoring pre-existing diagnostics failures | green |

## Backward Compat

- `cognition.load` on a repo with neither `VOSS.md` nor `.voss/architecture.md` returns `CognitionBundle(initialized=False)` — no crash.
- `cognition.load` on a legacy repo with `.voss/architecture.md` and no `VOSS.md` continues to work via the fallback in `_load_arch_from_voss_md` (M2-era tests + direct-write fixtures pass unchanged).
- `bootstrap_prompt(inventory)` without the `target_path` kwarg still defaults to `.voss/architecture.md` so any external caller keeps working.

## Atomic-Write Inheritance

- `ensure_migrated` writes through `write_fence_body` → temp + `os.replace`. No partial-write window.
- `skills/analyze.py` rollback path uses the same atomic write helper.
- Archive write uses plain `path.write_bytes` followed by sha256 verification before unlinking the source — a corrupt archive aborts the migration and leaves the source intact.

## Files Touched

- `voss/harness/voss_md.py` — `ensure_migrated` implementation (~55 lines).
- `voss/harness/cognition.py` — `_parse_arch_text` extracted, `_load_arch` redocumented, `_load_arch_from_voss_md` new, `_is_initialized` new, `load()` rewired, `bootstrap_prompt` gains `target_path` kwarg.
- `voss/harness/skills/analyze.py` — full rewrite of arch path resolution + staging + fold + rollback.
- `voss/harness/cli.py` — two-line wire of `voss_md.ensure_migrated(cwd)` before `cognition_mod.load`.
- `tests/harness/test_voss_md_migration.py` — 5 working tests (skip removed).

## Deviations from Plan

1. **`_is_initialized` helper introduced.** Plan didn't anticipate the
   `if not (root / "architecture.md").exists(): return ...` gate in
   `load()`. Replacing the literal with a `_is_initialized(cwd)` helper
   covers VOSS.md OR `.voss/architecture.md` and keeps the `load()` body
   free of the literal `root / "architecture.md"` (plan acceptance gate
   satisfied).

2. **`_parse_arch_text` extracted from `_load_arch`.** Plan said "Re-use
   the existing FRONTMATTER_RE + pydantic schema parse code from the old
   `_load_arch` — copy the same parse-validate flow so the return shape is
   identical." Extracted to a single helper instead of copying to avoid
   drift. Both `_load_arch` and `_load_arch_from_voss_md` delegate.

3. **Two extra migration tests** beyond the 3 in the plan
   (`test_ensure_migrated_idempotent_on_voss_md_present` +
   `test_ensure_migrated_missing_sources_returns_false`) — pin the
   idempotency and missing-source contracts called out in the behavior
   block. Additive only.

No other deviations.
