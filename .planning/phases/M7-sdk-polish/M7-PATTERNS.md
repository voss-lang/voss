# M7 Reusable Patterns

Quick-reference for executor agents working on M7 plans. Every pattern is
sourced from existing in-tree code so the new public surface matches the
shape of code that already ships. File:line citations point at the canonical
example to mimic.

## Pattern 1 — Test-public-api drift entries

**Source:** `tests/packaging/test_public_api.py:14-43` (frozensets) and
`tests/packaging/test_public_api.py:60-107` (the four test functions).

`EXPECTED_RUNTIME_PUBLIC_API` and `EXPECTED_HARNESS_PUBLIC_API` are
`frozenset`s pinned at the top of the module. The four tests (`*_matches_contract`,
`*_symbols_importable`) compare these to the live `__all__`. Any drift
fails the test with a message instructing the human to update both the
frozenset AND `docs/sdk.md` in the same PR.

**M7 deltas (locked):**
- `EXPECTED_HARNESS_PUBLIC_API` gains 6 names: `NullRenderer`, `Renderer`,
  `RunView`, `SessionView`, `tool_entry_from_callable`, `view_session`.
  Final size 8 → 14.
- `EXPECTED_RUNTIME_PUBLIC_API` gains 1 name: `register_provider`.
  Final size 26 → 27.

## Pattern 2 — `@tool` decorator delegation for tool descriptors

**Source:** `voss_runtime/tools.py:65-102` (`tool` decorator) and
`voss_runtime/tools.py:19-38` (`_type_to_schema`).

The `@tool` decorator in `voss_runtime/tools.py` already implements:
- Name default from `f.__name__`
- Description default from first line of `f.__doc__`
- Parameter schema from `inspect.signature(f)` + `typing.get_type_hints(f)`
- Type mapping: `str→"string"`, `int→"integer"`, `float→"number"`,
  `bool→"boolean"`, `list[T]→{"type": "array", "items": _type_to_schema(T)}`,
  `dict→{"type": "object"}`, pydantic `BaseModel.model_json_schema()`,
  `Optional[T]/T | None → _type_to_schema(T) with nullable: True`.
- Default-presence controls `required`: a param without a default goes
  into `required`; a param with a default does not (and gets
  `"default": <value>"` in its schema).
- Fallback for exotic types: `{"type": "string"}` (silent — does NOT raise).

`tool_entry_from_callable` (SDK-02) DELEGATES to this decorator rather
than re-implementing inference. The factory body is ~10 LOC; reading the
existing `_type_to_schema` is the documentation for what gets inferred.

## Pattern 3 — Frozen dataclass projection types

**Source:** `voss/harness/tools.py:14-41` (`ToolEntry`).

`ToolEntry` is `@dataclass(frozen=True)` with field-level read-only
properties. `SessionView` and `RunView` (SDK-03) mirror this idiom:
`@dataclass(frozen=True)`, no methods (or one classmethod `from_record`
if needed). Tuple fields (not lists) for nested collections to enforce
structural immutability. Standard "Python read-only" pattern.

## Pattern 4 — `dataclasses.replace` for fluent config

**Source:** `voss_runtime/_config.py:26-30` (`configure`).

```python
def configure(**kwargs) -> RuntimeConfig:
    global _config
    with _lock:
        _config = replace(_config, **kwargs)
    return _config
```

`RuntimeConfig.from_toml` (SDK-04) uses the same idiom: start from `cls()`
defaults, `replace(defaults, **toml_data_for_known_keys)`, return the new
instance. Three-line implementation. `default()` chains two replaces:
defaults → TOML overlay → env overlay.

## Pattern 5 — `load_harness_config` template

**Source:** `voss/harness/config.py:30-39` (`load_harness_config`, regex-
based reader for the existing `[harness]` section).

The new `RuntimeConfig.from_toml(path)` follows the same "read file, parse
section, return typed object" shape, but uses `tomllib.loads` (stdlib,
3.11+) instead of the regex reader, and reads `[runtime]` instead of
`[harness]`. Different section, different parser, same overall pattern.
The two coexist in the same `~/.config/voss/config.toml` without
collision (`voss/harness/config.py:50` regex preserves siblings).

## Pattern 6 — `StubProvider` hermetic test driver

**Source:** `tests/integration/test_classify_example.py:8-25` and
`tests/examples/helpers.py:94-103` (`register_stub` ctxmgr).

```python
stub = StubProvider(default_response="...")
voss_runtime.providers.register("__stub__", stub)
configure(default_model="__stub__")
```

`tests/packaging/test_sdk_embedding.py` (Wave 6) mirrors this pattern but
uses ONLY the new public names:

```python
from voss_runtime import StubProvider, configure, register_provider, RuntimeConfig
stub = StubProvider(default_response="...")
register_provider("test-stub", stub, replace=True)   # exercises SDK-05
configure(default_model="test-stub")
```

## Pattern 7 — Test-pattern for new test files

**Source:** `tests/packaging/test_entrypoint.py:1-106`.

The closest existing pattern for `tests/packaging/test_sdk_embedding.py`:
plain `def test_*` functions, `subprocess.run` only when the CLI surface
needs exercising, `tomllib.loads(Path("pyproject.toml").read_text())` for
static checks. The new file uses `@pytest.mark.asyncio` + `async def
test_*` for the `await run_turn(...)` path (pytest-asyncio already
configured in `pyproject.toml [tool.pytest.ini_options]`).

The "no private imports" gate is a top-of-file explicit import block:
if any of the listed names is missing from `voss.harness.__all__` or
`voss_runtime.__all__`, the test file fails to import → fail-loud.

## Pattern 8 — Sync-callable async shim (SDK-02 R-04)

**Source:** Inferred from `voss/harness/agent.py:430` (executor `await
entry.invoke(...)`) and existing `@tool`-decorated functions in
`voss/harness/tools.py:51-186` (all already `async def`).

The executor unconditionally `await`s `entry.invoke(**args)`. A plain
sync callable wrapped without an async shim crashes at runtime. The
factory wraps sync callables BEFORE constructing the descriptor:

```python
if not inspect.iscoroutinefunction(fn):
    async def _async_fn(**kwargs):
        return fn(**kwargs)
    _async_fn.__name__ = fn.__name__
    _async_fn.__doc__ = fn.__doc__
    _async_fn.__annotations__ = getattr(fn, "__annotations__", {})
    fn = _async_fn
```

This preserves the embedder ergonomic ("any callable works") while
satisfying the executor's contract. Confirmed in M7-RESEARCH §Q1 + Risk 2.

## Pattern 9 — `runs` is `list[dict]`, not `list[RunRecord]`

**Source:** `voss/harness/session.py:94` (field type) and
`voss/harness/cli.py:830` (`record.runs.append(asdict(result.run))`).

`SessionRecord.runs` stores `asdict(RunRecord)` dicts, not typed
`RunRecord` instances. `_hydrate` (`voss/harness/session.py:119`) does
NOT rehydrate them. `view_session` (SDK-03) MUST use defensive `.get()`
reads on each run dict — attribute access (`r.id`) raises
`AttributeError`. Confidence is nested: `r.get("plan", {}).get("confidence")`.

## Pattern 10 — `register_stub` ctxmgr is the single high-leverage audit target

**Source:** `tests/examples/helpers.py:94-103,106-118`.

The `register_stub` context manager and `_sitecustomize_source` helper
are reused by many integration tests. Updating these two to pass
`replace=True` (SDK-05 audit) covers the majority of downstream test
files. The 10 in-tree call sites identified in M7-RESEARCH §Q3 are:

| # | File:line | Audit action |
|---|-----------|--------------|
| 1 | `voss_runtime/providers/__init__.py:32` | No change — module-load, registry empty |
| 2 | `voss_runtime/providers/__init__.py:33` | No change — module-load, registry empty |
| 3 | `tests/test_agent.py:26,85,99,118` | Pass `replace=True` (4 distinct names) |
| 4 | `tests/eval/test_runner_options.py:58` | Pass `replace=True` |
| 5 | `tests/integration/test_classify_example.py:16,25` | Pass `replace=True` (× 2) |
| 6 | `tests/integration/test_research_example.py:20` | Pass `replace=True` |
| 7 | `tests/integration/test_support_example.py:50` | Pass `replace=True` |
| 8 | `tests/codegen/test_examples.py:107` | Pass `replace=True` |
| 9 | `tests/examples/helpers.py:98` | Pass `replace=True` (covers most downstream) |
| 10 | `tests/examples/helpers.py:113` | Update generated source string to pass `replace=True` |

All 10 updates land in the SAME wave as the SDK-05 default-flip; splitting
breaks CI on the intermediate commit.
