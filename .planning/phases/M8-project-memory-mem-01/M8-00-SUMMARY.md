---
phase: M8
plan: 00
status: complete
date: 2026-05-14
---

# M8-00 Summary — Wave 0 Scaffold

Wave 0 landed the module skeletons, test stubs, dependency, and `/save` rename
so subsequent waves (M8-01 through M8-06) can attach behavior without
dependency-resolution churn or pitfall replays.

## Files Created (4 modules)

| Path | Owner | Purpose |
|------|-------|---------|
| `voss/harness/voss_md.py` | M8-01 / M8-05 | VOSS.md fence parser, system-context injection, migration helpers |
| `voss/harness/memory_store.py` | M8-02 | Orchestrator over `voss_runtime.memory` + `.voss/memory/` FS mirror |
| `voss/harness/conventions.py` | M8-03 | Convention extraction service (D-09 signal + D-10 LLM + D-11 review) |
| `voss/harness/memory_cli.py` | M8-04 | `voss memory <vacuum|adopt|size>` Click subcommand group |

## Files Created (13 test stubs)

All 13 collect cleanly. 12 are SKIPPED at module level (`pytestmark = pytest.mark.skip`)
with the reason naming the owning plan. The 13th file ships with one real test
(grep gate, green) plus one skipped function:

- `tests/harness/test_voss_md_injection.py` — 2 tests, skipped (M8-05)
- `tests/harness/test_voss_md_migration.py` — 3 tests, skipped (M8-05)
- `tests/harness/test_voss_md_fence.py` — 4 tests, skipped (M8-01)
- `tests/harness/test_memory_store.py` — 3 tests, skipped (M8-02)
- `tests/harness/test_recall_eval.py` — 2 tests, skipped (M8-02)
- `tests/harness/test_conventions.py` — 5 tests, skipped (M8-03)
- `tests/harness/test_slash_recall.py` — 2 tests, skipped (M8-06)
- `tests/harness/test_slash_forget.py` — 2 tests, skipped (M8-06)
- `tests/harness/test_slash_memory.py` — 1 test, skipped (M8-06)
- `tests/harness/test_slash_save_note.py` — 2 tests, skipped (M8-06)
- `tests/harness/test_memory_eviction.py` — 3 tests, skipped (M8-04)
- `tests/harness/test_memory_vacuum.py` — 2 tests, skipped (M8-04)
- `tests/harness/test_memory_runtime_reuse.py` — 2 tests: **grep-gate green**, semantic-init skipped (M8-02)

Total: **30 new test ids** discovered by pytest collection. M8 prefix grep
returns **13 matching files**.

## Files Modified

| Path | Change |
|------|--------|
| `voss/harness/cli.py` | `_save` → `_save_session`; SlashCommand at cli.py:473 renamed to `/save-session`. Bare `/save` slot now unclaimed (reserved for M8-06 memory-note handler). |
| `pyproject.toml` | Added `portalocker>=2.8` to core dependencies (Pitfall 3 cross-platform locking). |
| `voss_runtime/memory/__init__.py` | Re-exported `Turn` from `.episodic` so `from voss_runtime.memory import Turn` works for M8-02 (plan-required import path). |
| `tests/harness/conftest.py` | Appended 5 M8 fixtures (see below). |
| `tests/harness/test_repl_slash.py` | Appended `test_memory_commands_not_yet_registered` skip placeholder for M8-06 future contract. |

## Pitfalls Resolved

- **Pitfall 1 (`/save` collision):** Existing snapshot-save handler renamed to
  `/save-session`. The bare `/save` name is unclaimed in the registry, ready
  for M8-06 to attach the memory-note handler. Acceptance gate
  `grep -cE 'SlashCommand\("/save"' voss/harness/cli.py` returns 0.
- **Pitfall 3 (cross-platform locking):** `portalocker>=2.8` added to core
  dependencies. Pure-Python, ~80KB, no Windows-specific code branch needed.
  M8-02 can `import portalocker` from any platform.

## Symbols Exposed for Downstream Waves

### `voss.harness.voss_md` (M8-01)

- Constants: `FENCE_BEGIN`, `FENCE_HASH`, `FENCE_END` (compiled regex; concrete).
- Types: `Block(kind, id, body, recorded_hash)` frozen dataclass; `HashMismatch` exception with `fence_id`, `recorded`, `actual`, `on_disk` attributes.
- Functions (stubs raising `NotImplementedError("M8-01")`): `parse`, `read_and_inject`, `ensure_migrated`, `read_fence_body`, `write_fence_body`, `machine_fence_path_or_marker`.

### `voss.harness.memory_store` (M8-02)

- Constants: `SOURCE_QUOTAS = {"turns": 0.60, "ledgers": 0.20, "decisions": 0.10, "conventions": 0.10}` (D-14); `DEFAULT_CAP_BYTES = 100 * 1024 * 1024`.
- Types: `Hit(source, locator, score, excerpt, session_id, ts)` dataclass; `MemoryStore` class.
- Constructor: `MemoryStore(cwd: Path, *, cap_bytes=DEFAULT_CAP_BYTES)` — lazy chroma (Pitfall 4 invariant verified by acceptance gate).
- Methods (stubs raising `NotImplementedError("M8-02")`): `bind`, `recall`, `forget`, `write_turn`, `write_ledger`, `write_note`, `write_convention`, `vacuum`, `summary`.
- Function `make_id(source, locator, seq=None)` — D-04 composite ID stub.

### `voss.harness.conventions` (M8-03)

- Constants: `_SIGNAL_RE` (compiled regex covering "no use", "always", "never", "prefer", "let's", "don't" — IGNORECASE, word-bounded); `DEFAULT_EXTRACTION_TIMEOUT_SECONDS = 8.0` (D-12).
- Types: `ConventionCandidate` (pydantic BaseModel, **fully implemented**) with fields `statement` (str, 1–500), `confidence` (float, 0.0–1.0), `evidence_quote` (str, ≥1), `evidence_turn_idx` (int, ≥0).
- Functions (stubs raising `NotImplementedError("M8-03")`): `has_signal`, `extract_conventions`, `review_candidates`, `run_on_clean_exit`.

### `voss.harness.memory_cli` (M8-04)

- `memory_group` — Click group with name `"memory"` (concrete).
- `memory_vacuum_cmd`, `memory_adopt_cmd` (with `--id` required), `memory_size_cmd` — Click command shells with `--cwd` option (concrete); bodies raise `NotImplementedError("M8-04")`.

## Fixture Catalog (added to `tests/harness/conftest.py`)

| Fixture | Consumers |
|---------|-----------|
| `tmp_voss_repo(tmp_path)` | Reqs 3/4/5/6/7. Creates `.voss/memory/{turns,ledgers,decisions,conventions,notes,chroma,.locks}/`. |
| `pre_m8_architecture_md(tmp_voss_repo)` | M8-05 migration tests (Req 2(a) sha256 gate). Writes realistic frontmatter. |
| `pre_m8_session_json(tmp_voss_repo)` | Pitfall 6 backward-compat tests. Writes M2 SessionRecord shape with NO memory_* fields. |
| `fake_session_corpus(tmp_voss_repo)` | M8-02 recall eval. Shape-only stub in Wave 0; M8-02 fills with seeded turns/ledgers/decisions/conventions + hit-rate queries. |
| `chroma_disabled_env(monkeypatch)` | Req 3 + Pitfall 4 fallback tests. Monkeypatches `sys.modules["chromadb"] = None`, reloads `voss_runtime.memory.semantic`. |

## Verification Results

- `pytest tests/harness/test_repl_slash.py -x` → green (9 passed, 1 skipped).
- `python -c "from voss.harness import voss_md, memory_store, conventions, memory_cli"` → succeeds.
- `python -c "from pathlib import Path; from voss.harness.memory_store import MemoryStore; MemoryStore(Path('.'))"` → succeeds without chroma instantiation (Pitfall 4 lazy invariant confirmed).
- `python -c "from voss.harness.conventions import ConventionCandidate; ConventionCandidate(statement='x', confidence=0.5, evidence_quote='y', evidence_turn_idx=0)"` → succeeds (pydantic model concrete).
- `python -c "from voss.harness.voss_md import parse; parse('test')"` → raises `NotImplementedError: M8-01` (skeleton invariant).
- `pytest tests/harness/ --collect-only` → 13 M8 file ids collected, no ImportError.
- `pytest tests/harness/test_memory_runtime_reuse.py::test_no_harness_memory_class_definitions_outside_runtime -x` → green (Req 7 grep gate active from Wave 0).
- `pytest --fixtures tests/harness/` → 5 new M8 fixtures discoverable.
- `pip install -e .` succeeds; `python -c "import portalocker"` succeeds (3.2.0 installed).
- `grep -nE 'SlashCommand\("/save"' voss/harness/cli.py` → 0 matches (bare `/save` slot free).
- `grep -n "/save-session" voss/harness/cli.py` → matches at cli.py:473.

## Pre-existing Failures (Unrelated)

`tests/harness/test_diagnostics.py::TestDoctorCmd::test_warn_only_surfaces_stderr_summary`
and `test_all_ok_no_stderr_summary` fail in baseline (confirmed by stashing all
M8-00 changes and re-running). Root cause: `click.testing.Result.stderr` API
expects `mix_stderr=False`. Out of scope for this plan; flag for separate fix.

## Deviations from Plan

1. **`Turn` export added to `voss_runtime/memory/__init__.py`.** Plan task 2(b)
   requires `from voss_runtime.memory import EpisodicMemory, SemanticMemory, Turn`
   in `memory_store.py`. `Turn` was only available at
   `voss_runtime.memory.episodic`; re-exporting from the package init keeps
   the plan-specified import path while leaving runtime semantics unchanged.
   Pure additive scaffold consistent with plan intent.

No other deviations. All other plan acceptance criteria satisfied as written.
