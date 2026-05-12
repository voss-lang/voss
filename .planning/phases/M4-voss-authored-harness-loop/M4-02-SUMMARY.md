---
phase: M4
plan: 02
status: complete
date: 2026-05-12
---

# M4-02 Summary - directory walk + harness cache

## Change locations

### `voss/harness/sandbox.py`

- Added `write_cache(project_root, relpath, text)`.
- Writes under `project_root/.voss-cache/`.
- Uses `jail_path` for both the cache root and the requested relative path.
- Writes via temp file then `replace`.

### `voss/harness/cache.py`

- New manifest helper module.
- Defines `ManifestEntry`, `sha256_text`, `compute_source_shas`, `write_manifest`, `load_manifest`, and `assert_fresh`.
- Manifest constants:
  - `MANIFEST_VERSION = 1`
  - `HARNESS_AGENT_DIR = "voss/harness/agent"`
  - `CACHE_HARNESS_DIR = ".voss-cache/harness"`
  - `MANIFEST_NAME = "_manifest.json"`

### `voss/harness/diagnostics.py`

- Added `StaleHarnessCacheError(VossError)`.

### `voss/cli.py`

- Added `_walk_voss_sources(source)`.
- `voss check <dir>` now walks `*.voss` files recursively, preserves `emit_indexes=False`, prints per-file diagnostics, and emits a summary for multi-file checks.
- `voss compile <dir>` now emits per-file artifacts under `.voss-cache/harness/`.
- `voss compile voss/harness/agent/` writes `.voss-cache/harness/_manifest.json`.
- Single-file compile/check behavior is preserved.

## Manifest Schema

Example emitted shape:

```json
{
  "version": 1,
  "voss_version": "0.1.0",
  "compiled_at": "2026-05-12T15:06:53.538561+00:00",
  "sources": {
    "loop.voss": {
      "sha256": "e66a5e4ed21668e45cc33a630dba7ed8988421d01d8c829885a0cb6acdbcb591",
      "lines": 2
    }
  }
}
```

## Tests Added

- `tests/harness/test_cache_freshness.py`
- `tests/harness/test_voss_check_dir.py`
- `tests/harness/test_voss_compile_dir.py`

## Verification

```bash
pytest tests/harness/test_voss_check_dir.py tests/harness/test_voss_compile_dir.py tests/harness/test_cache_freshness.py -q
```

Result: 15 passed.

```bash
pytest tests/cli/ -q
```

Result: passed.

```bash
pytest tests/harness/ -q -m "not live"
```

Result: passed with existing skips.

Acceptance checks:

- `_walk_voss_sources` is defined and used by `check` and `compile`.
- `emit_indexes=False` remains in the `check` directory walk path.
- `source.name == "agent"` is the manifest emission heuristic.
- `StaleHarnessCacheError` subclasses `VossError`.
- `write_cache` writes under `.voss-cache/` and rejects `../` escapes.
- A temp-project `voss compile <agent-dir> --project-root <tmp>` emitted both per-file artifacts and `_manifest.json`.

## Deviations

- The canonical stale-cache message is centralized as `STALE_CACHE_MESSAGE` in `voss/harness/cache.py` rather than repeated at each raise site. This keeps every raise path byte-identical while avoiding duplicated string literals.
- The new test count is 15 rather than the plan's nominal 10 because cache helper and sandbox edge cases are split into smaller tests.

## Hand-off

M4 Wave 1 is complete. M4-03 can now author `voss/harness/agent/{loop,router,planner,executor,reviewer}.voss` and compile them into `.voss-cache/harness/`.
