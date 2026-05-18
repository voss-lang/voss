---
phase: M9
plan: 08
type: execute
wave: 8
depends_on: [M9-07]
files_modified:
  - .planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
  - .planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
  - voss/harness/tui/app.py
  - voss/harness/tui/renderer.py
  - voss/harness/tui/widgets/__init__.py
  - voss/harness/tui/widgets/code_intel_panel.py
  - voss/harness/tui/widgets/sub_agent_panel.py
  - voss/harness/tui/styles.tcss
  - tests/harness/tui/test_code_intel_panel.py
  - tests/harness/tui/test_code_intel_region_share.py
  - tests/harness/tui/test_no_new_runtime_hooks.py
autonomous: true
requirements: [CODE-07, TUI-04, TUI-09]
must_haves:
  truths:
    - "M9-08 is an amendment only; existing M9-01..M9-07 plans are not edited."
    - "CodeIntelPanel is the default side-region occupant when no sub-agent is active."
    - "SubAgentPanel takes precedence while any spawn is active; CodeIntelPanel state is preserved and restored after gather."
    - "Pinning either side-region panel suspends automatic switching until unpinned."
    - "M9-08 adds no backend code-intelligence service calls and does not depend on M10 source files."
    - "No new emit points are added to voss/harness/recorder.py or voss_runtime/{probable,budget,agent}.py."
  artifacts:
    - path: "voss/harness/tui/widgets/code_intel_panel.py"
      provides: "CodeIntelPanel widget with idle tree, results, and focused-excerpt display modes"
      exports: ["CodeIntelPanel"]
    - path: "voss/harness/tui/app.py"
      provides: "Side-region ownership state machine shared by CodeIntelPanel and SubAgentPanel"
    - path: "voss/harness/tui/renderer.py"
      provides: "TextualRenderer-private code-intel update methods; Renderer protocol remains unchanged"
    - path: ".planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md"
      provides: "M9 amendment record for CodeIntelPanel region-share behavior"
  goal_backward_verification:
    - "Start from CODE-07: the M10 side panel can only ship if M9 reserves a stable CodeIntelPanel surface first."
    - "If CodeIntelPanel cannot render without M10 services installed, this plan fails because the prerequisite would not be independently executable."
    - "If SubAgentPanel no longer wins during spawn, this plan fails because it regresses M9's visible primitive contract."
---

<objective>
Add the M9 prerequisite amendment required by M10 CODE-07. The executor must reserve and test the side-region contract for CodeIntelPanel without implementing M10's code-intelligence backend.

Purpose: M10 execution is blocked until this plan lands and passes. This plan keeps M9's existing SubAgentPanel behavior intact while adding a default CodeIntelPanel surface that M10 can later populate from project-index and slash results.

Output: CodeIntelPanel widget, side-region share state machine, TextualRenderer private update methods, M9 context/UI-SPEC amendment notes, and TUI tests for idle/results/focused states plus SubAgentPanel precedence.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@.planning/phases/M9-tui-shell-tui-01/M9-02-PLAN.md
@.planning/phases/M9-tui-shell-tui-01/M9-04-PLAN.md
@.planning/phases/M9-tui-shell-tui-01/M9-07-PLAN.md
@.planning/phases/M9-tui-shell-tui-01/M9-07-SUMMARY.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md

<interfaces>
CodeIntelPanel states:
- idle: module/file tree summary, no backend calls, accepts an in-memory list of nodes.
- results: list of file:line hits from /symbol or /refs, accepts plain dict/list payloads.
- focused: selected hit plus bounded file:line excerpt, supplied by M10 later.

Side-region ownership:
- default owner = "code_intel".
- if any spawn is active and no user pin overrides it, owner = "sub_agent".
- when all spawns gather, owner restores to "code_intel" and the previous CodeIntelPanel state remains visible.
- user pin owner in {"code_intel", "sub_agent", null}; pinning suspends automatic switching.

Renderer protocol:
- Do not add CodeIntelPanel methods to voss.harness.render.Renderer.
- Add TextualRenderer-private methods only, for example show_code_intel_tree, show_code_intel_results, show_code_intel_focus.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Record the M9 CodeIntelPanel amendment and add the standalone widget</name>
  <requirements>[CODE-07, TUI-04]</requirements>
  <files>.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md, .planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md, voss/harness/tui/widgets/code_intel_panel.py, voss/harness/tui/widgets/__init__.py, voss/harness/tui/styles.tcss, tests/harness/tui/test_code_intel_panel.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-02-PLAN.md
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md (Requirement 7 only)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/widgets/sub_agent_panel.py
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/widgets/turn_view.py
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/glyphs.py
  </read_first>
  <action>
    Update M9-CONTEXT.md and M9-UI-SPEC.md with a short "M9-08 amendment" note only. Do not edit M9-01..M9-07 plan files. The note must state that CodeIntelPanel is the side-region default for M10 and that SubAgentPanel keeps precedence during active spawn/gather visualization.

    Create voss/harness/tui/widgets/code_intel_panel.py. Implement a Textual widget with three explicit setters: set_tree(nodes), set_results(query, hits), and set_focus(hit, excerpt_lines). The widget must render without importing voss.harness.code or any M10 backend module. Keep payloads simple: dictionaries/lists are enough at this layer.

    Export CodeIntelPanel from widgets/__init__.py. Add any minimal styles needed to styles.tcss using existing M9 palette tokens only. Do not introduce new colors, glyphs, or copy tone. Tests must mount the widget directly and assert idle, results, and focused modes render stable text.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/tui/test_code_intel_panel.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "M9-08 amendment|CodeIntelPanel|SubAgentPanel" .planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md .planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m py_compile voss/harness/tui/widgets/code_intel_panel.py</automated>
  </verify>
  <acceptance_criteria>
    - M9-CONTEXT.md and M9-UI-SPEC.md each contain "M9-08 amendment" and name CodeIntelPanel plus SubAgentPanel precedence.
    - Import succeeds: `python3 -c "from voss.harness.tui.widgets import CodeIntelPanel; print(CodeIntelPanel.__name__)"`.
    - CodeIntelPanel tests cover idle tree, results pane, focused excerpt, empty result, and bounded excerpt rendering.
    - `rg -n "from voss\\.harness\\.code|CodeIntelService" voss/harness/tui/widgets/code_intel_panel.py` returns no matches.
    - Existing M9 accent allow-list audit still passes; no new palette token is introduced.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Add side-region share state machine and renderer-private update methods</name>
  <requirements>[CODE-07, TUI-04, TUI-09]</requirements>
  <files>voss/harness/tui/app.py, voss/harness/tui/renderer.py, voss/harness/tui/widgets/sub_agent_panel.py, tests/harness/tui/test_code_intel_region_share.py, tests/harness/tui/test_no_new_runtime_hooks.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/renderer.py
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/widgets/sub_agent_panel.py
    - /Users/benjaminmarks/Projects/Voss/tests/harness/tui/test_live_visualization.py
    - /Users/benjaminmarks/Projects/Voss/tests/harness/tui/test_no_new_runtime_hooks.py
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-04-PLAN.md
  </read_first>
  <action>
    Mount CodeIntelPanel in the side region by default. Add a small side-region owner state machine to VossTUIApp with methods such as show_code_intel_panel(), show_subagent_panel(), pin_side_panel(owner), unpin_side_panel(), and restore_code_intel_panel(). Keep names consistent with existing app mutator style.

    Update the existing sub-agent mount/collapse paths so active spawn switches the visible side region to SubAgentPanel unless the user has pinned CodeIntelPanel. On final gather, restore CodeIntelPanel with its previous tree/results/focus state. Pinning SubAgentPanel is allowed only while a sub-agent exists; when no panel exists, unpin and show CodeIntelPanel.

    Add TextualRenderer-private methods for M10 to call later: show_code_intel_tree(nodes), show_code_intel_results(query, hits), and show_code_intel_focus(hit, excerpt_lines). These must not be added to Renderer in voss/harness/render.py and must not affect PlainRenderer, JsonRenderer, or TtyRenderer.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/tui/test_code_intel_panel.py tests/harness/tui/test_code_intel_region_share.py tests/harness/tui/test_live_visualization.py tests/harness/tui/test_no_new_runtime_hooks.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "show_code_intel_(tree|results|focus)" voss/harness/tui/renderer.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! rg -n "show_code_intel_(tree|results|focus)" voss/harness/render.py</automated>
  </verify>
  <acceptance_criteria>
    - Launching VossTUIApp in a test pilot shows CodeIntelPanel in the side region when no spawn is active.
    - A simulated spawn switches visible side-region ownership to SubAgentPanel; final gather restores the same CodeIntelPanel state.
    - Pin/unpin tests prove auto-switching is suspended while pinned and resumes when unpinned.
    - `tests/harness/tui/test_no_new_runtime_hooks.py` remains green without updating the recorder/runtime baseline.
    - `rg -n "def observe|def absorb|def finalize" voss/harness/tui/` still does not show any recorder API wrapper added for this panel.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## ASVS L1 Gate

Security enforcement is on. Any high-severity issue introduced by this amendment blocks completion.

| Threat ID | Category | Component | Risk | Mitigation |
|-----------|----------|-----------|------|------------|
| T-M9-08-01 | Tampering | Side-region state | A panel switch could hide active sub-agent state. | SubAgentPanel wins by default during active spawn; tests assert precedence and restoration. |
| T-M9-08-02 | Information disclosure | Focused excerpt UI | Future M10 snippets could render too much source. | Widget supports bounded excerpts only; M10 owns redaction and snippet limits before calling renderer methods. |
| T-M9-08-03 | DoS | TUI redraw | Large result lists could flood the side panel. | CodeIntelPanel accepts bounded hit lists; tests include truncation marker behavior. |
| T-M9-08-04 | Integrity | Runtime hooks | The amendment could extend recorder/runtime emit surfaces. | Existing no-new-runtime-hooks baseline must pass unchanged. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/tui/test_code_intel_panel.py tests/harness/tui/test_code_intel_region_share.py tests/harness/tui/test_live_visualization.py tests/harness/tui/test_no_new_runtime_hooks.py -q`
- `python3 -m py_compile voss/harness/tui/widgets/code_intel_panel.py`
- `rg -n "M9-08 amendment|CodeIntelPanel|SubAgentPanel" .planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md .planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md`
- `! rg -n "show_code_intel_(tree|results|focus)" voss/harness/render.py`
- `git diff --check -- .planning/phases/M9-tui-shell-tui-01/M9-08-PLAN.md .planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md .planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md voss/harness/tui tests/harness/tui`
</verification>

<success_criteria>
- CodeIntelPanel is a tested, importable M9 widget independent of M10 backend code.
- The side region defaults to CodeIntelPanel and switches to SubAgentPanel only under the locked active-spawn precedence rule.
- TextualRenderer exposes private CodeIntelPanel update methods without changing the public Renderer protocol.
- M9 documentation records the amendment without editing M9-01..M9-07 plans.
- Runtime-surface baseline stays green.
</success_criteria>
