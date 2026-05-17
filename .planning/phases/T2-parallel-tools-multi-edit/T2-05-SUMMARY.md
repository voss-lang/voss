---
phase: T2-parallel-tools-multi-edit
plan: 05
type: summary
---

# T2-05 Summary — `fs_read_many` bundled multi-file read (PAR-04)

## Goal achieved

`fs_read_many(paths: list[str]) -> str` lands as non-mutating tool.
Returns deterministic bundle of `=== {path} ===\n{body}\n` sections
joined by `"\n"`. Per-path errors inline (call never raises for bad
paths). `jail_path` per-slot inside `try/except SandboxError`; jail
violation → `<error: path outside cwd: {path}>`. 30KB per-file cap
with `<truncated, total {N} bytes>` marker (N = original byte length).
Empty paths → literal `<no paths requested>` sentinel. Duplicates NOT
deduped. Registered with `is_mutating=False` so T2-03 partition
scheduler may run it inside parallel read batches alongside fs_read,
fs_glob, fs_grep, git_status, git_diff, voss_check.

## Code locations

| Symbol | File | Line |
|--------|------|------|
| `_read_one_for_bundle` (module-scope helper) | `voss/harness/tools.py` | 45 |
| `@tool` decorator + `fs_read_many` definition | `voss/harness/tools.py` | 92–107 |
| `"fs_read_many"` registration | `voss/harness/tools.py` | 313 |

## Bundle format byte-sample

From `test_three_readable_bundle_format` — 3 files each containing one word + newline:

```
a.txt   ← contents: "alpha\n"
b.txt   ← contents: "beta\n"
c.txt   ← contents: "gamma\n"
```

Bundle string (literal, with `\n` for newlines):

```
=== a.txt ===\nalpha\n\n\n=== b.txt ===\nbeta\n\n\n=== c.txt ===\ngamma\n\n
```

Breakdown:
- Each section = `f"=== {path} ===\n{body}\n"`; when body already ends with `\n`, section ends with `\n\n`.
- Sections joined by `"\n"` → adjacent sections separated by `\n\n\n` total (body trailing `\n` + section trailing `\n` + join `\n`).
- Final section has no trailing join `\n`.

## SPEC acceptance fixture → test mapping

| Fixture | Behavior | Test |
|---------|----------|------|
| a | 3 readable paths → bundle in request order | `test_three_readable_bundle_format`, `test_bundle_format_exact` |
| b | 1 missing + 2 readable → inline `<error: not found: ...>` slot 1 | `test_missing_slot_inline_error` |
| c | duplicates → 2 slots, no dedup | `test_duplicate_paths_no_dedup` |
| d | empty paths → `<no paths requested>` sentinel | `test_empty_paths_returns_sentinel` |
| D-13 | 30KB cap with `<truncated, total {N} bytes>` marker | `test_truncation_30kb`, `test_exactly_30kb_not_truncated`, `test_just_over_30kb_truncated` |
| D-14 | jail violation → inline envelope; no raise | `test_jail_violation_inline_error` |
| — | dir / binary / missing envelopes | `test_directory_inline_error`, `test_binary_file_inline_error` |
| — | is_mutating=False registration | `test_registered_with_is_mutating_false` |
| — | fs_read preserved | `test_fs_read_still_registered` |
| — | deterministic byte-identical output | `test_deterministic_output` |

## Pytest output

```
$ uv run pytest tests/harness/tools/test_fs_read_many.py -x -q
..............                                                           [100%]
14 passed
```

Regression (T2-04 + T2-03 + tools surface):

```
$ uv run pytest tests/harness/tools/ tests/harness/test_partition_scheduler.py tests/harness/test_tools.py -x -q
........................................................................ [ 97%]
..                                                                       [100%]
74 passed
```

## test_tools.py count adjustment

`tests/harness/test_tools.py::test_mutating_count` updated for T2-05's
additive non-mutating tool:

- Mutating count: still **5** (fs_write, fs_edit, fs_edit_many, shell_run, record_run)
- Non-mutating count: **6 → 7** (added fs_read_many)

Comment in source notes the T2-05 adjustment explicitly.

## Acceptance grep gates (all pass)

```
$ grep -n "async def fs_read_many\|def _read_one_for_bundle" voss/harness/tools.py
45:def _read_one_for_bundle(cwd: Path, path: str) -> str:
100:    async def fs_read_many(paths: list[str]) -> str:

$ grep -nE 'fs_read_many.*is_mutating=False' voss/harness/tools.py
313:        "fs_read_many": ToolEntry(descriptor=fs_read_many, is_mutating=False),

$ grep -F "30720" voss/harness/tools.py | head -2
    if len(text) > 30720:  # 30KB cap (T2-CONTEXT.md D-13)
        text = text[:30720] + f"\n<truncated, total {len(text)} bytes>"

$ grep -F "<no paths requested>" voss/harness/tools.py
            return "<no paths requested>"

$ grep -F "path outside cwd" voss/harness/tools.py
        return f"<error: path outside cwd: {path}>"

$ grep -F '=== {path} ===' voss/harness/tools.py
            "`=== {path} ===`. Per-path errors are inline (other paths "
            sections.append(f"=== {path} ===\n{body}\n")

$ python -c "from voss.harness.tools import make_toolset; t = make_toolset('.'); print(t['fs_read_many'].is_mutating)"
False
```

## Threat model verification

- **T-T2-05-01** (path-traversal slot escape): mitigated — `jail_path` wrapped in `try/except SandboxError`; violations return inline envelope without ever calling `read_text` on the resolved path. `test_jail_violation_inline_error` confirms the call does not raise and other slots still resolve.
- **T-T2-05-02** (greedy file fills context): mitigated — per-file 30720-byte cap with truncation marker; boundaries (==30720, ==30721, >>30720) all tested.
- **T-T2-05-03** (per-slot error aborts whole call): mitigated — `_read_one_for_bundle` has zero raise sites; every IO path returns an error envelope string. Tested via `test_missing_slot_inline_error` (call returns, slot has inline error).
- **T-T2-05-04** (binary bytes leak via decode error): mitigated — `UnicodeDecodeError` caught; slot returns `<error: binary file: {path}>` without raw bytes. `test_binary_file_inline_error` covers.
- **T-T2-05-05** (duplicate cache-bust): accepted — no caching layer; duplicates fill both slots deterministically per spec.
- **T-T2-05-SC**: accepted — no new third-party deps.

## Wave 4 handoff to T2-06

Schedule + tools complete. T2-06 dogfood benchmark can:
- Call `fs_read_many(paths=[...])` directly as a singleton, OR
- Plan N separate `fs_read` calls that the partition scheduler will batch together; both paths exercise PAR-05 cap via the same Semaphore.

`is_mutating=False` registration allows `fs_read_many` to coexist with other non-mutating reads inside a single multi-step batch, which the dogfood micro-benchmark in T2-06 will measure against the M2 serial baseline (target ≥40% wall-clock drop on 6-read workload).
