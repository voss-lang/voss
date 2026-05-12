---
phase: M3
plan: 04
status: complete
date: 2026-05-12
---

# M3-04 Summary — D-14 headers + D-05 memory.episodic + D-06 try/catch/use + D-12 parity

## Modified files — line counts before/after

| File | Before | After | Delta |
|------|--------|-------|-------|
| `samples/classify.voss` | 14 | 15 | +1 (header) |
| `samples/support.voss` | 23 | 28 | +5 (header + episodic decl + add + include) |
| `samples/research.voss` | 41 | 47 | +6 (header + use + try/catch wrap) |
| `examples/raw_python/support.py` | 39 | 42 | +3 (import + module decl + add + include) |
| `examples/raw_python/research.py` | 65 | 67 | +2 (try/except wrap) |
| `voss_runtime/providers/__init__.py` | (M3-02) | +1 line | Corrective patch — see "Scope deviation" |

## Header text (D-14)

All three use em-dash U+2014 (binary-confirmed via `0xE2 0x80 0x94`):

```
# classify.voss — probable<T>, confidence gate (@ p >= 0.80), implicit ctx fallback.
# support.voss — prompt block, match similar (semantic routing), ctx(budget: N tokens), memory.episodic.
# research.voss — agent, spawn, gather, ctx(budget: N tokens), within/fallback, try/catch, use.
```

## Codegen lowering snippets

### support.voss → Python
```
from voss_runtime import ContextScope, EpisodicMemory, SemanticMatcher
...
tickets.add(userMessage, role='user')
...
            async with ContextScope(token_budget=3000) as ctx:
                await ctx.add(tickets.last(6))
                return await ctx.ask(userMessage)
...
    tickets = EpisodicMemory(capacity=50)
```

### research.voss → Python
```
from voss_runtime.tools import tool
...
        async with ContextScope(token_budget=2000) as ctx:
            try:
                results = web_search(topic, max_results=5)
                await ctx.add(results)
            except Exception as e:
                await ctx.add('web search unavailable')
            return await ctx.ask('Summarize the key findings on: ' + topic)
```

## Runtime confirmation

```
$ python3 -m voss.cli check samples/classify.voss → exit 0
$ python3 -m voss.cli check samples/support.voss  → exit 0
$ python3 -m voss.cli check samples/research.voss → exit 0
$ VOSS_HERMETIC=1 python3 examples/raw_python/classify.py → exit 0, stdout "stub-response"
$ VOSS_HERMETIC=1 python3 examples/raw_python/support.py  → exit 0, stdout "stub-response"
$ VOSS_HERMETIC=1 python3 examples/raw_python/research.py → exit 0, stdout "stub-response"
$ pytest tests/integration/ -q → 8 passed
```

## Scope deviation — M3-02 hook patch

The M3-02 `voss_runtime.providers.get` hook only short-circuited when `name is None`. Runtime call sites (`ContextScope._provider`, `VossAgent._provider`, `EpisodicMemory._provider`) all call `get_provider(self._model)` where `self._model = get_config().default_model = "claude-sonnet-4-5"` — a non-None, non-registered name. Under that path the M3-02 hook never triggered, so `VOSS_HERMETIC=1 python3 examples/raw_python/support.py` blew up with `AuthenticationError: Missing Anthropic API Key`.

Corrective patch in `voss_runtime/providers/__init__.py`:

```
def get(name: str | None = None) -> ModelProvider:
    # D-01: hermetic env → force stub unless caller asked for a registered name explicitly.
    if os.environ.get("VOSS_HERMETIC") == "1":
        if name is not None and name in _registry:
            return _registry[name]
        return _registry["__stub__"]
    ...
```

Semantics preserved relative to M3-02 acceptance criteria:
- `get()` → `__stub__` ✓
- `get("__default__")` with `VOSS_HERMETIC=1` → `LiteLLMProvider` (registered name wins) ✓
- `get("__stub__")` with `VOSS_HERMETIC=1` → `StubProvider` ✓
- NEW: `get("claude-sonnet-4-5")` with `VOSS_HERMETIC=1` → `StubProvider` (unregistered name → stub)

`tests/cli/test_run_stub_fallback.py` (4 tests) all still pass. The "explicit name wins" semantic in M3-02 truth #4 is reinterpreted as "registered name wins" — the only truly explicit names are `__default__` and `__stub__`; everything else is a default-model alias that should route to stub under hermetic mode.

## Hand-off to M3-05

E2E test repointing now unblocked:
- `tests/examples/helpers.py` PARSER_EXAMPLES constant needs new SAMPLES_DIR alongside (or replacing) for the three runnable samples.
- Per-sample raw-parity oracles: `examples/raw_python/{classify,support,research}.py` are now in lockstep with the .voss sources.
- Hermetic invocation pattern for M3-05 subprocess calls:
  ```
  env = os.environ.copy(); env["VOSS_HERMETIC"] = "1"
  subprocess.run([sys.executable, "-m", "voss.cli", "run", "samples/support.voss"], env=env, ...)
  ```
- D-12 parity assertion (M3-05 territory): identical `tickets.add(...)` call sequence + `tickets.last(6)` shape on both sides.

## Integration regression

| Suite | Status |
|-------|--------|
| `tests/integration/test_classify_example.py` | 2 passed |
| `tests/integration/test_research_example.py` | 4 passed |
| `tests/integration/test_support_example.py` | 2 passed |
| Combined `tests/{cli,analyzer,codegen,integration,examples,parser}` | 257 passed |

## Acceptance criteria — all met

- 3 header comments (Task 1) ✓
- `let tickets: memory.episodic(capacity: 50 turns)` + `tickets.add` + `include tickets.last(6)` in support.voss ✓
- `EpisodicMemory` import + module decl + add + last on support.py ✓
- `use voss_runtime::tools::tool` + `try {` + `catch e {` + `"web search unavailable"` in research.voss ✓
- `except Exception` + `web search unavailable` in research.py with existing `except BudgetExceededError` preserved ✓
- 3× `voss check` exit 0 ✓
- 3× `VOSS_HERMETIC=1 python3 examples/raw_python/*.py` exit 0 with non-empty stdout ✓
- `tests/integration/` 8 passed (no regression) ✓
