---
phase: T2-parallel-tools-multi-edit
plan: 02
type: summary
---

# T2-02 Summary — `[agent] max_parallel_reads` config knob (PAR-05)

## Goal achieved

Landed PAR-05 config knob with default 8, range 1–32, RuntimeWarning
fallback on bad values. `RuntimeConfig.max_parallel_reads` is the live
singleton field T2-03's scheduler will read. `cli.py` bootstrap wires
both `max_iterations` (T1-04) and `max_parallel_reads` (T2-02) through
a single `configure(...)` call at module import.

This plan also absorbed the cli.py bootstrap site that T1-04 specified
but did not ship — the new `_bootstrap_runtime_config()` helper covers
both keys at once.

## Code locations

| Symbol | File | Line |
|--------|------|------|
| `RuntimeConfig.max_parallel_reads: int = 8` | `voss_runtime/_config.py` | 24 |
| `get_max_parallel_reads()` | `voss/harness/config.py` | 89 |
| `_bootstrap_runtime_config()` helper | `voss/harness/cli.py` | 51 |
| `configure(max_iterations=..., max_parallel_reads=...)` call | `voss/harness/cli.py` | 62-65 |
| Module-level bootstrap invocation | `voss/harness/cli.py` | 68 |

## Loader semantics (PAR-05 locked)

| Input | Result | Side effect |
|-------|--------|-------------|
| no config.toml | `8` | silent |
| `[agent]` block without key | `8` | silent |
| `"1"` … `"32"` | parsed int | silent |
| `"0"` / `"33"` / `"100"` | `8` | `RuntimeWarning("[agent] max_parallel_reads = N out of range 1-32; falling back to default 8")` |
| `"foo"` / `""` | `8` | `RuntimeWarning("[agent] max_parallel_reads = '<raw>' is not an integer; falling back to default 8")` |

Range validation is `1 <= n <= 32` inclusive (boundaries pass).
Default sourced from `get_config().max_parallel_reads` per plan key_link.

## Tests

`tests/harness/test_agent_config.py` (extended, 13 new tests):

1. `TestRuntimeConfigMaxParallelReadsField::test_default_is_8`
2. `TestRuntimeConfigMaxParallelReadsField::test_configure_then_reset_round_trips`
3. `TestGetMaxParallelReadsDefault::test_no_config_file_returns_default`
4. `TestGetMaxParallelReadsDefault::test_config_without_key_returns_default`
5. `TestGetMaxParallelReadsValid::test_override_16`
6. `TestGetMaxParallelReadsValid::test_min_boundary_1`
7. `TestGetMaxParallelReadsValid::test_max_boundary_32`
8. `TestGetMaxParallelReadsOutOfRange::test_zero_warns_and_falls_back`
9. `TestGetMaxParallelReadsOutOfRange::test_thirty_three_warns_and_falls_back`
10. `TestGetMaxParallelReadsOutOfRange::test_one_hundred_warns_and_falls_back`
11. `TestGetMaxParallelReadsNonInt::test_string_value_warns_and_falls_back`
12. `TestGetMaxParallelReadsNonInt::test_empty_value_warns_and_falls_back`
13. `TestBothAgentKeysRoundtrip::test_both_keys_in_one_block`

`tests/harness/test_cli_bootstrap.py` (new, 4 subprocess tests):

1. `test_bootstrap_default_no_config` — no config.toml → `8|8`
2. `test_bootstrap_reads_max_parallel_reads_override` — `[agent] max_parallel_reads = "16"` → `8|16`
3. `test_bootstrap_reads_both_agent_keys` — both keys → `12|20`
4. `test_bootstrap_out_of_range_falls_back_to_default` — `"100"` → `8|8` (silent in subprocess; warning still emitted to stderr)

Each subprocess uses `sys.executable -c` with a probe that imports
`voss.harness.cli` (triggering `_bootstrap_runtime_config()`) and prints
`f"{max_iterations}|{max_parallel_reads}"`. Subprocess isolation prevents
RuntimeConfig singleton contamination across tests.

## Pytest output

```
$ uv run pytest tests/harness/test_agent_config.py -x -q
........................                                                 [100%]
$ uv run pytest tests/harness/test_cli_bootstrap.py -x -q
....                                                                     [100%]
```

Regression batch:

```
$ uv run pytest tests/harness/ -k "cli or bootstrap or agent_config or harness_config or session_roundtrip or recorder" -x -q
...............................................................s........ [ 69%]
...............................                                          [100%]
```

(105 passed, 1 skipped — single skip pre-dates T2 in `test_recorder.py`.)

## Acceptance grep gates (all pass)

```
$ grep -n "max_parallel_reads: int" voss_runtime/_config.py
24:    max_parallel_reads: int = 8

$ grep -n "def get_max_parallel_reads" voss/harness/config.py
89:def get_max_parallel_reads() -> int:

$ grep -nE "max_parallel_reads=get_max_parallel_reads" voss/harness/cli.py
64:        max_parallel_reads=get_max_parallel_reads(),

$ python -c "from voss_runtime import get_config, reset_config; reset_config(); print(get_config().max_parallel_reads)"
8
```

`configure(` appears 9 times in cli.py — the new T2-02 call extends in
place via the `_bootstrap_runtime_config()` helper (one call, both keys);
no double-bootstrap. Existing 8 configure() calls are model-switching
paths unrelated to agent-loop knobs.

## Threat model verification

- **T-T2-02-01** (DoS via malformed value): mitigated — `int()` cast +
  `1 <= n <= 32` range check both fall back to default 8 with
  `RuntimeWarning`; no exception escapes `_bootstrap_runtime_config()`,
  so cli.py import never crashes on a bad config.
- **T-T2-02-02** (Tampering, edit race): accepted — config read once at
  bootstrap; mid-run edits do not affect the running session.
- **T-T2-02-03** (InfoDisclosure in warning): accepted — `{raw!r}` /
  `{n}` are integer-shaped values, no PII or credential leakage.

## Wave 1 handoff to T2-03

The partition scheduler can now read the cap via:

```python
from voss_runtime import get_config

sem = asyncio.Semaphore(get_config().max_parallel_reads)
```

No further config or bootstrap work required for downstream T2 plans.
