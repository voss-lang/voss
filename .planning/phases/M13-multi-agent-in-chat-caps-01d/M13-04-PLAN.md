---
phase: M13-multi-agent-in-chat-caps-01d
plan: 04
type: execute
wave: 2
depends_on: ["M13-02"]
files_modified:
  - voss/harness/tui/renderer.py
  - voss/harness/tui/app.py
  - voss/harness/tui/widgets/sub_agent_panel.py
  - voss/harness/tui/keymap.py
  - tests/harness/tui/test_keymap_baseline.py
autonomous: true
requirements: ["MAG-02", "MAG-07"]

must_haves:
  truths:
    - "A child run's SubAgentPanel BudgetMeter leaves the em-dash placeholder and the used value increments at least once before collapse"
    - "By default the SubAgentPanel body (per-step detail) is not rendered (display:none); steps still stream into backing state"
    - "Pressing the reveal binding toggles a detailed step view containing at least one streamed child step, then toggles it back"
    - "After gather, zero SubAgentPanel instances remain mounted and the side region pin/owner state matches the pre-spawn M9-08 contract"
    - "ctrl+c still resolves to the global interrupt action (unchanged)"
  artifacts:
    - path: "voss/harness/tui/renderer.py"
      provides: "show_subagent_progress dead seam confirmed live (caller supplied by M13-02 bridge contract); thread-model docstring clarified additively"
      contains: "show_subagent_progress"
    - path: "voss/harness/tui/app.py"
      provides: "action_toggle_subagent_detail + per-panel detail-visibility flip over query(SubAgentPanel)"
      contains: "def action_toggle_subagent_detail"
    - path: "voss/harness/tui/widgets/sub_agent_panel.py"
      provides: "body Vertical display:none by default; append_body still mounts captured steps"
      contains: "agent-body"
    - path: "voss/harness/tui/keymap.py"
      provides: "one additive ctrl+o main-context binding; ctrl+c row byte-unchanged"
      contains: "ctrl+o"
    - path: "tests/harness/tui/test_keymap_baseline.py"
      provides: "additive ctrl+o resolution assertion + ctrl+c interrupt assertion"
      contains: "toggle_subagent_detail"
  key_links:
    - from: "voss/harness/tui/keymap.py"
      to: "voss.harness.tui.app.VossTUIApp.action_toggle_subagent_detail"
      via: "KEYMAP main-context Binding row -> App action handler (same registry mechanism as action_fork_turn)"
      pattern: "ctrl\\+o.*main.*toggle_subagent_detail"
    - from: "voss/harness/tui/app.py"
      to: "voss/harness/tui/widgets/sub_agent_panel.py"
      via: "action iterates query(SubAgentPanel), flips #panel-body-{parent_id} Vertical .styles.display"
      pattern: "query\\(SubAgentPanel\\)"
    - from: "voss/harness/tui/renderer.py"
      to: "voss.harness.tui.app.VossTUIApp.update_subagent"
      via: "show_subagent_progress -> _post(app.update_subagent, ...) (dead seam, caller supplied by M13-02 PanelBridgeRenderer)"
      pattern: "show_subagent_progress"
---

<objective>
Wave 2B TUI bridge + reveal. Make the dead `show_subagent_progress` seam
(`renderer.py:203`) reachable, add a quiet-by-default reveal toggle for the
M9 `SubAgentPanel`, and bind it to `ctrl+o` — all additive, zero overlap
with M13-03's harness files.

Three deliverables:
1. Confirm the renderer dead seam is now a real, callable bridge entry point
   (the missing caller is supplied by M13-02's `PanelBridgeRenderer`; this
   plan owns the renderer-side contract + the stale thread-model docstring
   clarification, additive only).
2. Add `app.action_toggle_subagent_detail` + per-panel detail-visibility
   flip, and make `sub_agent_panel.py`'s body `Vertical` `display:none` by
   default (steps still stream into backing state — captured, not rendered).
3. Add exactly one `ctrl+o` `"main"`-context row to `keymap.py` (D-09;
   `ctrl+c` keymap.py:37 byte-unchanged), and prove `ctrl+o ->
   toggle_subagent_detail` resolves via an additive keymap-baseline
   assertion. A task action RESOLVES RESEARCH OQ-A3 (the `"main"`-context
   dispatch trace) before placing the binding.

Purpose: greens MAG-02 (live quiet panels + reveal) and MAG-07 (post-gather
region clean) under the stub-provider TUI pilot.
Output: 4 modified source files + 1 modified test file; the M13-01 red
`tests/harness/tui/test_subagent_reveal.py` and the additive
`test_keymap_baseline.py` rows go green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-SPEC.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-CONTEXT.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-PATTERNS.md
@.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-VALIDATION.md

<dependency_note>
depends_on M13-02 only because M13-04's panel-reveal flow exercises the
`PanelBridgeRenderer` -> `show_subagent_progress` caller that M13-02 ships
in `voss/harness/multiagent.py`. M13-04 does NOT edit `multiagent.py` or
`agent.py`. Wave-2 sibling M13-03 owns `multiagent.py`(extend)+`agent.py`;
this plan owns `renderer.py`/`app.py`/`sub_agent_panel.py`/`keymap.py`/
`test_keymap_baseline.py`. The two file sets are disjoint -> M13-03 ∥ M13-04
in Wave 2 (verified: no path appears in both `files_modified` lists).
</dependency_note>

<interfaces>
<!-- Exact contracts the executor needs. Extracted + verified from live code 2026-05-18. -->
<!-- No codebase exploration required — these are the authoritative current shapes. -->

VERIFIED — `voss/harness/tui/renderer.py:194-207` (the dead seam this plan keeps live):
- `show_subagent_start(self, name, parent_id, budget_total=0)` -> `_post(self.app.mount_subagent_panel, panel)`
- `show_subagent_progress(self, parent_id, body_line, used=0)` -> `_post(self.app.update_subagent, parent_id, body_line, used)`  ← line 203-204, NEVER CALLED today; M13-02's PanelBridgeRenderer is the first caller
- `show_subagent_end(self, parent_id, n_results=0)` -> `_post(self.app.collapse_subagent, parent_id, n_results)`
- `_post` (renderer.py:55-70): main-thread -> direct call; off-loop -> `app.call_from_thread`; both already handled. Stale module docstring renderer.py:7 says "subagents run in worker threads" — RESEARCH Pitfall 3 confirms this is scoped to the M9-05 permissions modal, NOT the M13 asyncio-task fan-out path.

VERIFIED — `voss/harness/tui/app.py:169-207` (M9-04 mutators + M9-08 restore — REUSE UNCHANGED):
- `mount_subagent_panel(self, panel)` — DO NOT MODIFY
- `update_subagent(self, parent_id, body_line, used=0)` — iterates `self.query(SubAgentPanel)`, matches `parent_id`, calls `panel.append_body(body_line)` + `panel.update_budget(used)` — DO NOT MODIFY
- `collapse_subagent(self, parent_id, n_results=0)` — already performs the full M9-08 restore (CodeIntelPanel re-mount / hide per `self._side_pinned`/`self._side_owner`) and appends the `✓ gathered · N results` turn — DO NOT MODIFY. D-10 gets region restore for free.
- `action_fork_turn` (app.py:136) — the EXISTING precedent for a `"main"`-context action handler living on `VossTUIApp`. `action_toggle_subagent_detail` mirrors this placement exactly.

VERIFIED — `voss/harness/tui/app.py:39-43` (the BINDINGS filter — central to OQ-A3):
```
BINDINGS = [
    (b.key, b.action, b.description)
    for b in KEYMAP
    if b.context in ("global", "input", "modal")
]
```
`"main"` is excluded from the materialized Textual BINDINGS list.

VERIFIED — `voss/harness/tui/keymap.py:12-39`:
- `Binding` = frozen dataclass `(key, context, action, description)`; `context` ∈ `"global"|"input"|"main"|"modal"`.
- KEYMAP `"main"` rows (lines 29-36): j/k/ctrl+d/ctrl+u/g/G/f/ctrl+f -> actions `scroll_down`/`scroll_up`/`half_page_down`/`half_page_up`/`jump_top`/`jump_bottom`/`fork_turn`/`open_search`.
- Line 37: `Binding("ctrl+c", "global", "interrupt", "Interrupt turn; press again to exit")` — BYTE-UNCHANGED constraint.

VERIFIED — `voss/harness/tui/widgets/sub_agent_panel.py:51-71`:
- `compose()` yields: `Static(agent-header)`, `BudgetMeter(... id=f"panel-budget-{parent_id}")`, `Vertical(id=f"panel-body-{parent_id}", classes="agent-body")` ← line 59 toggle target
- `append_body(line)` mounts `Static(line, markup=False)` into `#panel-body-{parent_id}` (still called even when body hidden — capture-not-render)
- `update_budget(used)` updates the embedded `BudgetMeter`; em-dash contract = BudgetMeter shows em-dash only when `budget_total <= 0` — UNCHANGED
- `DEFAULT_CSS` already defines `SubAgentPanel .agent-body { padding: 0 0; }` — add `display: none;` to that existing rule (no new widget class)

VERIFIED — `voss/harness/tui/widgets/turn_view.py:18-113`:
- `TurnView(RichLog)` has NO `BINDINGS` attribute and NO `action_*` methods.
- There are NO `action_scroll_down`/`action_jump_top`/`action_half_page_*`/`action_open_search` handlers anywhere in the tui package (grep-verified). The only `"main"`-row action with a live handler is `action_fork_turn` on `VossTUIApp`.

VERIFIED — `tests/harness/tui/test_keymap_baseline.py:9-42`:
- `test_keymap_size_at_least_14` asserts `len(KEYMAP) >= 14` (adding one row keeps this green).
- `test_keymap_includes_ui_spec_row` is a parametrized TABLE-MEMBERSHIP test: it asserts a `Binding` with matching `key` + `context` substring exists in the `KEYMAP` tuple. It is NOT a runtime key->action dispatch test.
- `test_every_binding_has_description_and_action` asserts every Binding has non-empty `action` + `description`.

VERIFIED — pilot analog `tests/harness/tui/test_live_visualization.py:25-49`:
`app = VossTUIApp(); async with app.run_test() as pilot: renderer = TextualRenderer(app=pilot.app); ...; await pilot.pause(); list(pilot.app.query(SubAgentPanel))`. `pyproject.toml` has `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed.
</interfaces>

<oq_a3_resolution>
<!-- RESEARCH Open Question A3 / Pitfall 6 / OQ2 — RESOLVED HERE for the executor. -->
<!-- Task 3's action re-states this; recorded here so the executor does not re-derive it. -->

QUESTION: Which dispatch table actually fires `"main"`-context keymap rows,
given `App.BINDINGS` (app.py:42) filters them out — and where must
`ctrl+o`'s handler live so the binding is not a silent no-op?

TRACE (grep + read verified against live code 2026-05-18):
1. `KEYMAP` (keymap.py:20-39) is the single-source-of-truth REGISTRY of all
   bindings across all four contexts (module docstring keymap.py:1-6).
2. `VossTUIApp.BINDINGS` (app.py:39-43) is the ONLY place KEYMAP is
   materialized into live Textual bindings, and it materializes ONLY
   `global|input|modal`. `"main"` rows are deliberately NOT promoted to
   Textual `App.BINDINGS`.
3. `TurnView` (turn_view.py) has NO `BINDINGS` and NO `action_*` methods.
   No other widget/screen re-materializes the `"main"` rows.
4. NO `action_scroll_down`/`action_jump_top`/`action_half_page_*`/
   `action_open_search` handler exists anywhere in `voss/harness/tui/`.
   The ONLY `"main"`-row action with a real handler is `action_fork_turn`
   on `VossTUIApp` (app.py:136) — and even `f` is filtered out of
   `App.BINDINGS`, so it is currently registry-declared, not key-live.
5. `test_keymap_baseline.py` proves only that the `"main"` rows EXIST in
   the KEYMAP tuple with an action+description (table membership), not that
   a keypress dispatches them.

CONCLUSION (the resolution the executor implements):
The `"main"` context is a DECLARATIVE registry tier in M9's locked
single-source keymap. M9's contract for a `"main"` row is: (a) the
`Binding(key,"main",action,desc)` row exists in `KEYMAP`, and (b) a
matching `action_<name>` handler exists on `VossTUIApp` (the
`action_fork_turn` precedent). The keymap-baseline test is the M9
acceptance contract for "this main key resolves". Therefore `ctrl+o` is
placed on EXACTLY that same mechanism:
  - add `Binding("ctrl+o","main","toggle_subagent_detail","Reveal/hide
    sub-agent step detail")` to `KEYMAP` (additive, T8 keymap-additive
    precedent — never a rewrite),
  - add `def action_toggle_subagent_detail(self) -> None:` on
    `VossTUIApp` (mirrors `action_fork_turn` placement exactly — the
    established `"main"`-action-on-App pattern),
  - prove resolution with an additive keymap-baseline assertion that
    `ctrl+o`'s Binding has `context=="main"` AND `action=="toggle_subagent_detail"`
    AND that `VossTUIApp` exposes a callable `action_toggle_subagent_detail`
    (the same dual contract every working M9 `"main"` row satisfies).
DO NOT add a `TurnView.BINDINGS`, do NOT widen the app.py:39-43 filter to
include `"main"`, do NOT add `ctrl+o` as a `"global"` row (would collide
with input typing and break the M9 single-source tiering). Additive-only.
</oq_a3_resolution>

<tasks>

<task type="auto">
  <name>Task 1: Quiet-by-default panel body + renderer dead-seam contract</name>
  <files>voss/harness/tui/widgets/sub_agent_panel.py, voss/harness/tui/renderer.py</files>
  <read_first>
    - voss/harness/tui/widgets/sub_agent_panel.py (full — DEFAULT_CSS :17-34, compose :51-59, append_body :61-64, update_budget :66-71)
    - voss/harness/tui/renderer.py:1-9 (stale thread docstring) + :55-70 (_post) + :194-207 (the three subagent seams; :203 dead show_subagent_progress)
    - <interfaces> block above (sub_agent_panel + renderer VERIFIED shapes)
    - M13-PATTERNS.md §"sub_agent_panel.py" + §"renderer.py" (additive-display-toggle + supply-missing-caller rules)
    - M13-RESEARCH.md Pitfall 3 (renderer.py:7 docstring scoped to M9-05 modal, NOT M13 asyncio path) + Pattern 4 (PanelBridgeRenderer lives in multiagent.py — M13-02's, NOT this plan's, file)
  </read_first>
  <action>
    Two additive edits, no behavior removed.

    (1) sub_agent_panel.py — quiet by default (D-09). In the existing
    `DEFAULT_CSS` block, extend the EXISTING `SubAgentPanel .agent-body`
    rule (currently `{ padding: 0 0; }`) to also set `display: none;`. Do
    NOT add a new widget class, do NOT add a new CSS selector, do NOT
    change `compose`, `append_body`, or `update_budget`. The body
    `Vertical(id=f"panel-body-{parent_id}", classes="agent-body")` (line
    59) is the toggle target; `append_body` keeps mounting `Static` step
    lines into it while hidden (captured, not rendered) so a later reveal
    shows real streamed history. The `BudgetMeter` (mini-status) and
    header stay visible — the panel is compact, not invisible. Do NOT
    touch the BudgetMeter em-dash contract (`budget_total <= 0` only).

    (2) renderer.py — the dead `show_subagent_progress` seam (:203-204)
    becomes live because M13-02's `PanelBridgeRenderer` (in
    `voss/harness/multiagent.py` — NOT edited here) is its first caller via
    `step(line, used) -> show_subagent_progress`. This plan owns only the
    renderer-side contract correctness: do NOT rename/move
    `show_subagent_progress`, `show_subagent_start`, `show_subagent_end`,
    `_post`, or the `_SPAWN_TOOL_NAME` import — M13-02's bridge depends on
    these exact names/signatures. Make ONE additive clarification: append a
    single sentence to the module docstring (renderer.py:7-9) noting that
    for the M13 multi-agent fan-out path children run as asyncio tasks on
    the app loop (not worker threads) and `_post`'s main-thread branch
    already handles that — per RESEARCH Pitfall 3. Docstring-only; do NOT
    change `_post` logic, do NOT introduce threads, do NOT alter any seam
    body.
  </action>
  <verify>
    <automated>python -m py_compile voss/harness/tui/widgets/sub_agent_panel.py voss/harness/tui/renderer.py && grep -n "display: none" voss/harness/tui/widgets/sub_agent_panel.py | grep -q "" && grep -c "show_subagent_progress\|show_subagent_start\|show_subagent_end" voss/harness/tui/renderer.py | grep -qx "3" && git diff --stat voss/harness/tui/renderer.py | grep -Eq "renderer.py +\| +[1-9] "</automated>
  </verify>
  <done>`.agent-body` carries `display: none;` in the existing DEFAULT_CSS rule (no new class/selector); the three `show_subagent_*` seam names + `_post` are byte-stable in signature; renderer.py docstring gained one additive clarifying sentence; both files `py_compile` clean; M13-02 bridge contract (seam names/signatures) preserved.</done>
</task>

<task type="auto">
  <name>Task 2: app.action_toggle_subagent_detail + per-panel detail flip</name>
  <files>voss/harness/tui/app.py</files>
  <read_first>
    - voss/harness/tui/app.py:37-43 (BINDINGS filter), :110-163 (action_redraw/interrupt/fork_turn — the existing action-handler region; action_fork_turn :136 = the "main"-action-on-App precedent), :169-207 (mount/update/collapse_subagent — REUSE UNCHANGED, M9-08 restore is automatic)
    - voss/harness/tui/widgets/sub_agent_panel.py:51-59 (body Vertical id scheme `#panel-body-{parent_id}`, classes="agent-body")
    - <interfaces> + <oq_a3_resolution> blocks above
    - M13-PATTERNS.md §"app.py" (ADD only action_toggle_subagent_detail + per-panel state; DO NOT modify mount/update/collapse/_side_*)
    - M13-VALIDATION.md MAG-02 row (body display==none default; after action_toggle_subagent_detail contains >=1 streamed step) + MAG-07 row (post-gather zero panels + _side_owner/_side_pinned match)
  </read_first>
  <action>
    Add EXACTLY ONE new method to `VossTUIApp`, placed alongside the
    existing action handlers (near `action_fork_turn`/`action_redraw`,
    app.py:110-163 region — the established `"main"`-context-action
    location):

    `def action_toggle_subagent_detail(self) -> None:` — iterate
    `self.query(SubAgentPanel)`; for each panel, query its body via
    `panel.query_one(f"#panel-body-{panel.parent_id}", Vertical)` and flip
    that body's `.styles.display` between `"none"` and `"block"`. Drive the
    flip from a single app-level boolean instance attribute (initialize it
    `False` in `__init__` next to the existing `self.focused_turn_index`
    init at app.py:65, additive — this is the "per-panel detail-visibility
    state" the project rule requires; one app-scoped toggle applied
    uniformly across all mounted panels, NOT per-panel divergent state, NOT
    a new widget). Toggling flips the boolean then applies the resulting
    display value to every panel body so newly-revealed panels and panels
    mounted-while-revealed stay consistent. Wrap each per-panel query in a
    defensive `try/except` (a panel mid-mount may not have its body yet —
    mirror the `except Exception: pass` style already used in
    `collapse_subagent` / `action_fork_turn`'s status `noqa: BLE001`
    pattern). Import `Vertical` from `textual.containers` if not already
    imported in app.py.

    HARD CONSTRAINTS (project rule): do NOT modify `mount_subagent_panel`,
    `update_subagent`, `collapse_subagent`, or any `_side_owner`/
    `_side_pinned`/`show_subagent_panel`/`pin_side_panel`/
    `restore_code_intel_panel` logic — D-10's M9-08 region restore on
    gather is already correct and is owned by M13-03's gather tool calling
    the unmodified `collapse_subagent`. This task adds the reveal toggle
    ONLY. Do NOT touch the app.py:39-43 BINDINGS filter.
  </action>
  <verify>
    <automated>python -m py_compile voss/harness/tui/app.py && grep -q "def action_toggle_subagent_detail" voss/harness/tui/app.py && grep -q "query(SubAgentPanel)" voss/harness/tui/app.py && python -c "import ast,sys; t=ast.parse(open('voss/harness/tui/app.py').read()); cls=[n for n in ast.walk(t) if isinstance(n,ast.ClassDef) and n.name=='VossTUIApp'][0]; names={n.name for n in cls.body if isinstance(n,ast.FunctionDef)}; assert 'action_toggle_subagent_detail' in names and {'mount_subagent_panel','update_subagent','collapse_subagent'} <= names, 'missing/renamed methods'; print('ok')" && git diff -U0 voss/harness/tui/app.py | grep -E '^\-' | grep -Eqv '^\-\-\-' && ! git diff -U0 voss/harness/tui/app.py | grep -E '^\-' | grep -v '^\-\-\-' | grep -E 'mount_subagent_panel|collapse_subagent|_side_owner|_side_pinned|def update_subagent' </automated>
  </verify>
  <done>`action_toggle_subagent_detail` exists on `VossTUIApp`, iterates `query(SubAgentPanel)` and flips each body `Vertical` `.styles.display`; an app-level boolean detail-visibility attribute is initialized additively; `mount_subagent_panel`/`update_subagent`/`collapse_subagent`/`_side_*` are unmodified (no deleted line touches them); app.py `py_compile` clean.</done>
</task>

<task type="auto">
  <name>Task 3: ctrl+o keymap row (OQ-A3) + keymap-baseline assertion</name>
  <files>voss/harness/tui/keymap.py, tests/harness/tui/test_keymap_baseline.py</files>
  <read_first>
    - voss/harness/tui/keymap.py (full — Binding dataclass :12-17, KEYMAP :20-39, "main" rows :29-36, ctrl+c :37 UNCHANGED)
    - voss/harness/tui/app.py:39-43 (BINDINGS filter) + :136 (action_fork_turn precedent)
    - tests/harness/tui/test_keymap_baseline.py (full — :9 size>=14, :13-35 parametrized table-membership, :38-42 action/description)
    - <oq_a3_resolution> block above (the FULL resolved trace — re-state it in the SUMMARY)
    - M13-RESEARCH.md Pitfall 6 / Open Question 2 / Assumption A3 (the UNRESOLVED item this task closes)
    - M13-PATTERNS.md §"keymap.py" + §"test_keymap_baseline.py" (one additive row; additive parametrize)
    - M13-CONTEXT.md D-09 (ctrl+o reveal, ctrl+c stays interrupt, keymap additive-only T8 precedent)
  </read_first>
  <action>
    RESOLVE RESEARCH OQ-A3 IN THIS ACTION (do not defer): The trace is
    complete and recorded in this plan's <oq_a3_resolution> block — the
    executor MUST re-state the resolved conclusion in the SUMMARY's
    decisions section. Resolution: `KEYMAP` is M9's single-source
    declarative registry; `App.BINDINGS` (app.py:39-43) materializes only
    `global|input|modal` into live Textual bindings; `"main"` is a
    registry tier whose M9 contract is "(a) Binding row in KEYMAP + (b)
    matching `action_<name>` on `VossTUIApp`" (the `action_fork_turn`
    precedent, app.py:136); `test_keymap_baseline.py` is that contract's
    acceptance test. `ctrl+o` is therefore placed on exactly that
    mechanism — NOT a new `TurnView.BINDINGS`, NOT a widened app.py:39-43
    filter, NOT a `"global"` row.

    (1) keymap.py — add EXACTLY ONE row to the `KEYMAP` tuple (T8
    keymap-additive precedent; never a rewrite). Place it among the
    `"main"` rows (after the existing `Binding("ctrl+f","main",
    "open_search",...)` line 36, before the `ctrl+c` line 37):
    `Binding("ctrl+o", "main", "toggle_subagent_detail", "Reveal/hide
    sub-agent step detail")`. Do NOT touch line 37
    (`Binding("ctrl+c","global","interrupt",...)`) — byte-unchanged. Do
    NOT reorder or edit any other row.

    (2) test_keymap_baseline.py — additive only. (a) Add `("ctrl+o",
    "main")` to the `test_keymap_includes_ui_spec_row` parametrize list
    (proves the row exists in KEYMAP with the right context). (b) Add ONE
    new test function asserting the full M9 `"main"`-row resolution
    contract for `ctrl+o`: find the KEYMAP Binding with `key=="ctrl+o"`,
    assert `b.context=="main"` and `b.action=="toggle_subagent_detail"`,
    AND assert `VossTUIApp` has a callable attribute
    `action_toggle_subagent_detail` (the same dual contract every working
    M9 `"main"` row — e.g. `f -> action_fork_turn` — satisfies). (c) Add
    one assertion (in the same new function or a sibling) that the
    `ctrl+c` Binding still has `context=="global"` and
    `action=="interrupt"` (proves D-09: ctrl+c unchanged = interrupt). Keep
    every existing test and parametrize row intact;
    `test_keymap_size_at_least_14` stays green (16 -> 17 rows).
  </action>
  <verify>
    <automated>python -m py_compile voss/harness/tui/keymap.py && python -c "from voss.harness.tui.keymap import KEYMAP; o=[b for b in KEYMAP if b.key=='ctrl+o']; c=[b for b in KEYMAP if b.key=='ctrl+c']; assert o and o[0].context=='main' and o[0].action=='toggle_subagent_detail', 'ctrl+o row wrong'; assert c and c[0].context=='global' and c[0].action=='interrupt', 'ctrl+c changed'; assert len(KEYMAP)>=17; from voss.harness.tui.app import VossTUIApp; assert callable(getattr(VossTUIApp,'action_toggle_subagent_detail',None)), 'no app handler'; print('ok')" && pytest tests/harness/tui/test_keymap_baseline.py -x -q</automated>
  </verify>
  <done>`KEYMAP` has exactly one new `ctrl+o`/`main`/`toggle_subagent_detail` row; `ctrl+c` line is byte-unchanged (`global`/`interrupt`); `VossTUIApp.action_toggle_subagent_detail` is callable; `test_keymap_baseline.py` passes including the new `ctrl+o` resolution assertion + the `ctrl+c`-still-interrupt assertion; OQ-A3 resolution recorded for the SUMMARY.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| child agent step text -> SubAgentPanel body | LLM-emitted (untrusted) child step lines mounted as `Static` into `#panel-body-{parent_id}` |
| keymap registry -> live key dispatch | KEYMAP row tier semantics (`global` materialized vs `main` registry-declared) — a mis-tiered binding is a silent no-op or an input-collision |
| renderer bridge thread context -> Textual widget mutation | child push path crossing into the app event loop |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M13-04-01 | Tampering / Information Disclosure | `SubAgentPanel.append_body` rendering child step text | mitigate | Reuse existing `Static(line, markup=False)` (sub_agent_panel.py:64) — untrusted child output stays literal, no markup/ANSI injection into the panel; this plan adds NO new render path, only a `display` toggle on already-captured content |
| T-M13-04-02 | Tampering (silent-no-op / input collision) | `ctrl+o` keymap placement vs app.py:39-43 filter (OQ-A3) | mitigate | Trace fully resolved (`<oq_a3_resolution>`): `ctrl+o` placed on the exact M9 `"main"`-tier mechanism (KEYMAP row + `action_<name>` on App, `action_fork_turn` precedent); proven by an additive keymap-baseline resolution assertion. Explicitly NOT a `"global"` row (would collide with input typing) and NOT a widened filter |
| T-M13-04-03 | Tampering | Ctrl+C interrupt contract (keymap.py:37) | mitigate | keymap.py:37 byte-unchanged; additive test asserts `ctrl+c` still `global`/`interrupt`; ctrl+o is a separate additive row |
| T-M13-04-04 | Tampering (cross-thread UI corruption) | renderer bridge -> Textual widget mutation | accept (already mitigated upstream) | `_post` (renderer.py:55-70) already main-thread/off-loop safe; M13 children are asyncio tasks on the app loop (RESEARCH Pitfall 3, verified no `to_thread`/`Thread` in dispatch). This plan introduces no threads and only adds a docstring clarification — blast radius unchanged |
| T-M13-04-05 | Denial of Service (orphan panels after gather) | post-gather side-region state | accept (owned by M13-03 via unmodified collapse_subagent) | `collapse_subagent` (app.py:184-207) already does full M9-08 restore + zero-panel teardown; this plan does NOT modify it; MAG-07 pilot assertion (post-gather `query(SubAgentPanel)==0` + `_side_owner`/`_side_pinned` match) is the verifying seam |
| T-M13-04-SC | Tampering | npm/pip/cargo installs | n/a | This plan adds NO package-manager installs (no new deps). Pytest/Textual already pinned (pyproject.toml). No legitimacy gate required for this plan |

No new secret material, no network egress, no persisted data. Blast radius
= in-memory TUI state + a display toggle only.
</threat_model>

<verification>
- `pytest tests/harness/tui/test_subagent_reveal.py -x -q` — green (MAG-02 quiet-by-default + ctrl+o reveal contains >=1 streamed step + BudgetMeter leaves em-dash + increments; MAG-07 post-gather zero panels + `_side_owner`/`_side_pinned` match pre-spawn snapshot). NOTE: this file is created red by M13-01; M13-04 makes it green.
- `pytest tests/harness/tui/test_keymap_baseline.py -x -q` — green incl. new `ctrl+o` resolution + `ctrl+c`-still-interrupt assertions.
- `pytest tests/harness/ tests/harness/tui/ -x -q` — no regression; in particular `tests/harness/test_subagent_recursion.py` stays green unmodified (this plan touches no harness/agent files).
- `git diff -U0 voss/harness/tui/app.py` — no deleted line intersects `mount_subagent_panel`/`update_subagent`/`collapse_subagent`/`_side_*`.
- `python -c "from voss.harness.tui.keymap import KEYMAP; assert [b for b in KEYMAP if b.key=='ctrl+c'][0].action=='interrupt'"` — Ctrl+C interrupt contract intact.
</verification>

<success_criteria>
- [ ] `sub_agent_panel.py` body `.agent-body` is `display: none` by default via the existing DEFAULT_CSS rule (no new widget class/selector); `append_body`/`update_budget`/`compose` unchanged; BudgetMeter em-dash contract unchanged.
- [ ] `renderer.py` `show_subagent_progress`/`show_subagent_start`/`show_subagent_end`/`_post`/`_SPAWN_TOOL_NAME` import are signature/name byte-stable (M13-02 bridge contract preserved); one additive docstring sentence added; no thread introduced.
- [ ] `VossTUIApp.action_toggle_subagent_detail` exists, iterates `query(SubAgentPanel)`, flips each body `Vertical` `.styles.display`; driven by an additively-initialized app-level boolean; `mount_subagent_panel`/`update_subagent`/`collapse_subagent`/`_side_*` unmodified.
- [ ] `keymap.py` has exactly one additive `Binding("ctrl+o","main","toggle_subagent_detail",…)`; line 37 ctrl+c byte-unchanged.
- [ ] OQ-A3 resolved in-task and recorded in SUMMARY: `"main"` is M9's declarative registry tier; `ctrl+o` placed on the KEYMAP-row + App-`action_`-handler mechanism (`action_fork_turn` precedent); proven by the additive keymap-baseline resolution assertion.
- [ ] `test_keymap_baseline.py` extended additively (new parametrize row + resolution test + ctrl+c-interrupt assertion); all existing rows/tests intact; `len(KEYMAP) >= 17`.
- [ ] M13-01's `test_subagent_reveal.py` and the new keymap-baseline assertions go green; `test_subagent_recursion.py` green unmodified; zero file overlap with M13-03.
</success_criteria>

<output>
Create `.planning/phases/M13-multi-agent-in-chat-caps-01d/M13-04-SUMMARY.md` when done.
The SUMMARY MUST record the resolved OQ-A3 trace (the `<oq_a3_resolution>`
conclusion) in its decisions section — downstream M13-06 e2e + any future
keymap work depends on knowing `"main"` is the declarative-registry tier.
</output>
