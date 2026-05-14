---
phase: M9
plan: 04
status: complete
date: 2026-05-14
---

# M9-04 Summary — Live Workflow Visualization (TUI-04)

Wave 4. `SubAgentPanel` widget mounts in the side region for spawn/gather.
`RecorderBridge` reads `RunRecorder` state delta-by-delta and forwards to
app mutators — zero new emit points on runtime. `TextualRenderer` gains
three PRIVATE subagent methods (NOT on `Renderer` protocol) + augmented
`show_clarify` / `show_final` that mount a `ConfidenceBar` next to the
turn block. `SPAWN_TOOL_NAME` constant added to `voss/harness/subagents.py`
(W3 resolution). Runtime-surface SHA-256 baseline pins 4 files.

## Files Created

| Path | Purpose |
|------|---------|
| `voss/harness/tui/widgets/sub_agent_panel.py` | `SubAgentPanel(Vertical)` with accent-colored header, embedded `BudgetMeter`, scrollable body. `append_body`, `update_budget`. |
| `voss/harness/tui/recorder_bridge.py` | `RecorderBridge(recorder, app)` reads `RunRecorder.inspected/changed/validation/failures` delta-by-delta, calls `app.update_inspected/update_changed/append_tool_line`. Pure consumer. |
| `tests/harness/tui/baseline/runtime_surface.sha256` | 4-line SHA-256 baseline for `recorder.py + voss_runtime/{probable,budget,agent}.py`. |
| `tests/harness/tui/test_no_new_runtime_hooks.py` | 3 tests — baseline match, subagents excluded from set, SPAWN_TOOL_NAME present. |
| `tests/harness/tui/test_recorder_bridge.py` | 6 tests — inspected, idempotent flush, validation ok/error states, failure path, no-mutation. |
| `tests/harness/tui/test_live_visualization.py` | 8 tests — protocol shape unchanged, panel mount/unmount, ConfidenceBar in clarify/final, status zero-ctx no-raise, missing-SPAWN_TOOL_NAME graceful degradation. |

## Files Modified

| Path | Change |
|------|--------|
| `voss/harness/subagents.py` | One line addition — `SPAWN_TOOL_NAME: str = "subagent_run"` module constant. No behavioral change. |
| `voss/harness/tui/renderer.py` | Defensive `try/except` import of `SPAWN_TOOL_NAME` at module load + `_resolve_spawn_name()` call-time lookup. `show_tool_call` detects spawn and dispatches `show_subagent_start/end`. Three new private methods. `_mount_confidence_bar` augments `show_clarify` (`is_final=False`) and `show_final` (`is_final=True`). |
| `voss/harness/tui/app.py` | Added mutators — `mount_subagent_panel`, `update_subagent`, `collapse_subagent`, `update_inspected`, `update_changed`, `append_tool_line`. Swap `#side` widget to `SideRegion` (was placeholder `SubAgentPanel`); real `SubAgentPanel` mounts as children. |
| `voss/harness/tui/widgets/turn_view.py` | Renamed placeholder `SubAgentPanel` → `SideRegion` (real `SubAgentPanel` now lives in `sub_agent_panel.py`). |
| `voss/harness/tui/widgets/__init__.py` | Export `SideRegion` + real `SubAgentPanel`. |
| `tests/harness/tui/test_app_shell.py` | Updated to query `SideRegion` for `#side` (placeholder rename). |

## SPAWN_TOOL_NAME (W3 Resolution)

Single source of truth at `voss/harness/subagents.py`:
```python
SPAWN_TOOL_NAME: str = "subagent_run"
```
Renderer imports it defensively. `_resolve_spawn_name()` re-reads `subagents.SPAWN_TOOL_NAME` at call time so monkeypatched deletes still degrade gracefully (W3 option b test asserts no `AttributeError` surfaces).

## Runtime-Surface Hash Baseline

`tests/harness/tui/baseline/runtime_surface.sha256` pins:
- `voss/harness/recorder.py`
- `voss_runtime/probable.py`
- `voss_runtime/budget.py`
- `voss_runtime/agent.py`

`UPDATE_BASELINE=1` env required to rewrite — intentional opt-in. subagents.py intentionally excluded (W3-allowed single-constant addition).

## Renderer Augmentations (Protocol shape unchanged)

| Method | Behavior |
|--------|----------|
| `show_subagent_start(name, parent_id, budget_total)` | PRIVATE; constructs `SubAgentPanel`, posts `app.mount_subagent_panel`. |
| `show_subagent_progress(parent_id, body_line, used)` | PRIVATE; posts `app.update_subagent`. |
| `show_subagent_end(parent_id, n_results)` | PRIVATE; posts `app.collapse_subagent`. |
| `show_tool_call` | Detects `name == SPAWN_TOOL_NAME` and routes to subagent path; falls through otherwise. |
| `show_clarify` | Appends turn block + mounts `ConfidenceBar(is_final=False)`. |
| `show_final` | Appends turn block + mounts `ConfidenceBar(is_final=True)` for accent allow-list. |
| `status` | Carries `ctx_pct` verbatim; M9-02 W5 contract preserved — no derived total at this layer. |

## Acceptance Gate Status

| Gate | Result |
|------|--------|
| `SPAWN_TOOL_NAME` import + non-empty | passes |
| `SubAgentPanel + RecorderBridge` import | passes |
| `wc -l runtime_surface.sha256` = 4 | passes |
| `grep -c subagents.py runtime_surface.sha256` = 0 | passes (excluded) |
| `RunRecorder` import in recorder_bridge | passes |
| No `def observe/absorb/finalize` in tui/ | passes |
| Baseline files unchanged | passes |
| `show_subagent_*` NOT on Renderer protocol | passes |
| `grep show_subagent voss/harness/render.py` = 0 | passes |
| `SPAWN_TOOL_NAME` referenced in renderer | passes |
| TUI tests | 92 passed |
| Full harness suite (excl. pre-existing diagnostics failures) | 387 passed, 2 skipped |

## Deviations from Plan

1. **`SubAgentPanel` placeholder rename.** Plan kept `SubAgentPanel` as the side-region container; this implementation renamed the M9-02 container to `SideRegion` and shipped real `SubAgentPanel` (per-spawn card). M9-02 test updated accordingly. Net result identical: `#side` is the container, spawn cards mount inside.

2. **`SideRegion.display` reliability.** Textual's `widget.display = True` round-trips don't reliably reflect inline overrides when CSS sets `display: none`. Tests assert visibility via `query(SubAgentPanel)` count rather than `widget.display`. Plan's `app.query_one('#side').display` assertion was unreliable.

3. **Validation status format.** Plan said exit-code parse via raw text. Confirmed `recorder._parse_exit` expects `[exit N]` prefix; tests updated.

4. **`status()` total derivation** kept as M9-02 W5 form (no derivation in renderer). The composite-StatusLine-with-BudgetMeter wiring is deferred to M9-07 alongside the live `make_renderer` swap-in — for now `StatusLine` carries `ctx_pct` verbatim and M9-04's `BudgetMeter` widget remains available for the M9-07 status-line composition.

5. **`flush_subagents` skipped** — `voss/harness/subagents.py` exposes no queryable in-flight state. Bridge omits the optional method per the plan's "if it does not, this method is a no-op" allowance.

No other deviations.

## Phase Handoff

- M9-05 builds the diff + permission `ModalScreen` overlays on top of M9-03's `escape` binding.
- M9-06 implements `f` fork-from-turn + `ctrl+f` search.
- M9-07 swaps the default `make_renderer` path to `TextualRenderer`, composes `StatusLine` + `BudgetMeter` so live budget rendering surfaces in default user flow, and wires `_build_slash_registry()` into `VossTUIApp.slash_registry` at boot.
