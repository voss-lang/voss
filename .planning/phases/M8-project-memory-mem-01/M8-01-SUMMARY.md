---
phase: M8
plan: 01
status: complete
date: 2026-05-14
---

# M8-01 Summary — VOSS.md Loader + System-Context Injection (MEM-01)

Wave-0 stubs in `voss/harness/voss_md.py` are now working code. Every
harness entry point (`voss chat`, `voss do`, `voss resume`) reads `VOSS.md`
once at boot and the bytes ride through `run_turn` as the head block of
`sys_prompt` before `cognition_text`. File absence degrades silently per D-08.

## voss_md.py Public API

| Symbol | Behavior |
|--------|----------|
| `FENCE_BEGIN`, `FENCE_HASH`, `FENCE_END` | Compiled regex constants (already set in Wave 0). |
| `Block(kind, id, body, recorded_hash)` | Frozen dataclass returned by `parse`. |
| `HashMismatch(fence_id, *, recorded, actual, on_disk)` | Exception with all four attributes populated; `__str__` truncates hashes to 16 chars. |
| `parse(text) -> list[Block]` | Line-by-line scan. Human runs accumulate between fences; machine fences capture id + optional hash header. Order preserved; no bytes dropped. |
| `read_and_inject(cwd) -> str \| None` | Returns `cwd/VOSS.md` bytes when present; `None` on absent / unreadable. Never raises. |
| `read_fence_body(path, *, fence_id) -> str \| None` | Returns body string when fence id present; raises `HashMismatch` when recorded hash != computed sha256; returns `None` when fence id absent. |
| `write_fence_body(path, *, fence_id, body) -> None` | Atomic write (temp + `os.replace`). Validates existing on-disk fence hash before replacement — raises `HashMismatch` on baseline drift. Appends new fully-formed fence at EOF when id absent. Hash header recomputed. |
| `machine_fence_path_or_marker(cwd, *, fence_id) -> Path` | Returns `cwd / "VOSS.md"`. Caller decides on absence. |
| `ensure_migrated(cwd) -> bool` | **Still NotImplementedError("M8-02")** — owned by Wave 3 (M8-02). |

## Wire Points Landed

- `voss/harness/cli.py::_run_repl` (~ cli.py:721): `voss_md_text = voss_md.read_and_inject(cwd)` after `cognition_mod.load`. Stored on `ReplContext.voss_md_text`. Passed through to `run_turn` inside the REPL loop.
- `voss/harness/cli.py::do_cmd` (~ cli.py:541): `voss_md_text = voss_md.read_and_inject(cwd)` after `cognition_mod.load`. Passed as kwarg to `run_turn`.
- `voss/harness/agent.py::run_turn`: new keyword-only param `voss_md_text: str | None = None`. `voss_md_block = f"# VOSS.md\n{voss_md_text}" if voss_md_text else ""` prepends the join tuple: `(voss_md_block, cognition_text, prior_context_text, PLAN_SYSTEM)`. Falsy empty-string drops cleanly via the existing `if s` filter.
- `voss resume` rides on `_run_repl` so it inherits the boot read automatically.

## Atomic-Write Strategy

`write_fence_body` writes to `<path>.tmp` then calls `os.replace(tmp, path)`.
On POSIX `os.replace` is atomic; on Windows it overwrites destination
atomically. No partial-write windows.

## Backward Compat Invariants

- `voss_md_text` defaults to `None` on `run_turn`. Existing callers (`tests/harness/test_agent_integration.py` `FakeProvider` cases, `voss_loop_parity`, compiled harness round-trip) are unbroken — verified by full harness regression green minus the two pre-existing diagnostics failures already flagged in M8-00.
- File absence path emits NO exception, NO log, NO section. `test_missing_file_degrades_silently` asserts the captured system message contains no `# VOSS.md` substring and stderr stays clean.
- The compiled harness `loop.voss` also accepts `voss_md_text = null` so `_resolve_run_turn` is happy whether it returns the Python or compiled `run_turn`. Tests `test_dog07_smoke` + `test_voss_loop_parity` stay green.

## Surface Ready for M8-02

`ensure_migrated` still raises `NotImplementedError("M8-02")` — the M8-02
plan owns the migration of `.voss/architecture.md` into the
`id=architecture` fence + the byte-identical archive (Req 2(a) sha256 gate).

`read_fence_body` and `write_fence_body` are live and consumed downstream by:
- M8-02 `ensure_migrated` (calls `write_fence_body` to seed the fence).
- M8-05 `cognition._load_arch_from_voss_md` (calls `read_fence_body`).
- M8-05 `skills/analyze.py` backup-and-restore (calls both).
- `memory_cli.memory_adopt_cmd` (M8-04, resolves `HashMismatch` by accepting on-disk body as new baseline).

## Tests

- `tests/harness/test_voss_md_fence.py` — 4 tests, all GREEN. Module-level skip removed. Covers human-only parse, mixed parse, hash-mismatch raise with attributes populated, write round-trip preserving human prose + hash recompute.
- `tests/harness/test_voss_md_injection.py` — 2 tests, all GREEN. Module-level skip removed. Drives `run_turn` with a `CapturingProvider` that records system messages; asserts presence/absence of `# VOSS.md\n<bytes>` head block.

## Acceptance Gate Status

| Gate | Result |
|------|--------|
| `pytest tests/harness/test_voss_md_fence.py -x` | green (4 passed) |
| `pytest tests/harness/test_voss_md_injection.py -x` | green (2 passed) |
| `pytest tests/harness/test_repl_slash.py -x` | green (no regression) |
| `python -c "from voss.harness.voss_md import parse; ..."` parse-human-only invariant | passes |
| `read_and_inject(Path('/nonexistent...'))` returns None | passes |
| `HashMismatch` 4-attribute construction | passes |
| `grep -c "NotImplementedError" voss/harness/voss_md.py` | 1 (only `ensure_migrated`) |
| `grep -nE "os\.replace\|\.rename\(" voss/harness/voss_md.py` | matches `os.replace` in `write_fence_body` |
| `grep -nc "voss_md_text" voss/harness/agent.py` | 2 (signature + assembly) |
| `grep -nc "voss_md.read_and_inject" voss/harness/cli.py` | 2 (`_run_repl` + `do_cmd`) |
| `grep -nc "voss_md_text=" voss/harness/cli.py` | 3 (ReplContext init + 2 `run_turn` call sites) |
| `inspect.signature(run_turn).parameters['voss_md_text'].default is None` | passes |
| Full `pytest tests/harness/ --ignore=test_diagnostics.py` | green, no regressions |

The plan acceptance line `grep -nE "^# VOSS\.md" voss/harness/agent.py` ≥ 1
match is an artifact of plan authoring — the literal `# VOSS.md` lives
inside an indented f-string (`f"# VOSS.md\n{voss_md_text}"`), not at line
start. The intent (presence of the literal `# VOSS.md` prefix in the
sys_prompt block construction) is satisfied at agent.py:298.

## Deviations from Plan

1. **Added `voss_md_text = null` parameter to `voss/harness/agent/loop.voss`.**
   Plan did not anticipate the compiled harness pathway needing matching
   signature. Without it `voss do` against the precompiled harness fixture
   (`test_dog07_smoke`) raised `TypeError: run_turn() got an unexpected
   keyword argument 'voss_md_text'`. One-line additive change consistent
   with plan intent — both backends accept the kwarg; compiled harness
   does not yet consume it (Python remains the canonical injection
   surface).

No other deviations.
