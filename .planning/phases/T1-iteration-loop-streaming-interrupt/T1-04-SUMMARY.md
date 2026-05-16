---
phase: T1-iteration-loop-streaming-interrupt
plan: 04
status: complete
completed_at: 2026-05-15
commits:
  - b7237b0 — feat(T1-04): TurnView streaming entry points + agent.max_iterations knob
---

# T1-04 Summary — Streaming UI hook + iteration cap config

## Files changed

- `voss/harness/tui/widgets/turn_view.py` — added `stream_delta` + `finalize_stream` methods + `_streaming: bool` instance flag.
- `voss_runtime/_config.py` — added `RuntimeConfig.max_iterations: int = 8`.
- `voss/harness/config.py` — added `_AGENT_BLOCK` regex, `_parse_agent_section`, `load_agent_config`, `get_max_iterations`, `set_max_iterations`.
- `tests/harness/tui/test_turn_view_streaming.py` — 5 Pilot tests.
- `tests/harness/test_agent_config.py` — 11 tests across defaults, load, get-with-fallback, set, cross-section round-trip.
- `tests/harness/tui/baseline/runtime_surface.sha256` — refreshed to accept the T1-01 recorder.py additive changes (M9-04 baseline drift was caught here, not in T1-01).

## TurnView API additions

```python
def stream_delta(self, text: str) -> None: ...
def finalize_stream(
    self,
    *,
    role: str,
    confidence: float | None = None,
    cost_usd: float | None = None,
    timestamp: str | None = None,
) -> None: ...
```

Header placement contract: `finalize_stream` writes the role/cost/conf header AFTER the streamed body (RichLog has no insert-before-line API). Intentional divergence from `append_turn` — ITER-03's 500ms first-token target rules out waiting on cost/confidence to surface any text. CONTEXT.md "append-only via RichLog.write on every TextDelta. No in-place edits, no scroll jumps" is satisfied.

## RuntimeConfig field

```python
@dataclass
class RuntimeConfig:
    ...
    max_output_tokens: int = 4096
    max_iterations: int = 8   # T1-04 add
```

`get_config().max_iterations == 8` by default. `configure(max_iterations=N)` overrides.

## [agent] schema — locked choice

Picked `[agent]` over `[loop]`. Rationale: leaves room for future agent-loop neighbors (`agent.confidence_threshold`, `agent.timeout`, etc.) without renaming. The CONTEXT.md "Claude's Discretion" question is now resolved.

### Example TOML snippet

```toml
[harness]
preferred_model = "claude-sonnet-4-5"

[agent]
max_iterations = "16"
```

Note: values are quoted strings — matches the existing parser convention. `get_max_iterations()` coerces via `int()` and emits `RuntimeWarning` + falls back to default on parse failure.

## T1-05 consumes get_max_iterations()

Recommended boot-time wiring (left to T1-05): call `harness_config.get_max_iterations()` once at cli boot, then `voss_runtime.configure(max_iterations=N)` so the agent loop reads only `get_config().max_iterations` as a single source of truth. `set_max_iterations(N)` rewrites the TOML; loaders are independent of `set_*` so a runtime override does not mutate the on-disk file.

## Deviations from plan

- **Behavior bullet revised**: plan said `stream_delta("hel") + stream_delta("lo")` produces a single visible block containing "hello". RichLog writes one log line per `write()` call, so the result is two segments — "hel" + "lo" — within the same logical block, not the single joined string "hello". Test asserts both fragments are present; CONTEXT.md's "append-only, render every delta" invariant is honored. No behavior change vs. plan's intent.
- **M9-04 baseline refresh**: T1-01's additive recorder.py changes broke the M9-04 `runtime_surface.sha256` baseline. Baseline regenerated via `UPDATE_BASELINE=1` (per the test's documented procedure). T1-01 SUMMARY already covers the recorder changes; this baseline bump is its mechanical consequence.

## Verification

```
uv run pytest tests/harness/tui/test_turn_view_streaming.py \
              tests/harness/test_agent_config.py -x -q     # 16 passed

uv run pytest tests/harness/tui/ -x -q                     # 190 passed
uv run pytest tests/harness/ -k "config or turn_view" -x -q # 32 passed
```
