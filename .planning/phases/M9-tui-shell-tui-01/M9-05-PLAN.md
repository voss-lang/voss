---
phase: M9
plan: 05
type: execute
wave: 5
depends_on: [M9-04]
files_modified:
  - voss/harness/tui/widgets/diff_modal.py
  - voss/harness/tui/widgets/permission_modal.py
  - voss/harness/tui/widgets/budget_modal.py
  - voss/harness/tui/widgets/__init__.py
  - voss/harness/tui/permissions_bridge.py
  - voss/harness/tui/renderer.py
  - voss/harness/tui/app.py
  - voss/harness/permissions.py
  - tests/harness/tui/test_diff_modal.py
  - tests/harness/tui/test_permission_modal.py
  - tests/harness/tui/test_budget_modal.py
  - tests/harness/tui/test_permissions_bridge.py
autonomous: true
requirements: [TUI-06, TUI-07]
must_haves:
  truths:
    - "Every fs_write / fs_edit goes through DiffModal per-hunk approval when the renderer is the TextualRenderer."
    - "PermissionGate.prompt_fn / scope_prompt_fn are dependency-injection points; the TUI bridge swaps them for modal-driven futures without modifying permissions.py logic."
    - "PermissionGate.check() returns the same (allowed, reason) shape post-bridge as pre-bridge."
    - "Budget-exhausted condition opens a modal with the three locked buttons (Continue +2000 / End turn / Cancel)."
    - "Esc on any modal denies / cancels per UI-SPEC destructive-actions inventory."
    - "Rejecting all diff hunks signals the agent with `out-of-scope denied`-equivalent reason; agent does not silently apply the proposed edit."
  artifacts:
    - path: "voss/harness/tui/widgets/diff_modal.py"
      provides: "DiffModal — per-hunk review with [y/n/s/a/q/Esc] keys + accent-colored selection"
      exports: ["DiffModal", "Hunk", "DiffDecision"]
    - path: "voss/harness/tui/widgets/permission_modal.py"
      provides: "PermissionModal — three-button [a/A/d/Esc] choice"
      exports: ["PermissionModal", "PermissionChoice"]
    - path: "voss/harness/tui/widgets/budget_modal.py"
      provides: "BudgetExhaustedModal — Continue +2000 / End turn / Cancel"
      exports: ["BudgetExhaustedModal", "BudgetChoice"]
    - path: "voss/harness/tui/permissions_bridge.py"
      provides: "Installs TUI-modal-backed prompt_fn and scope_prompt_fn into a PermissionGate; intercepts fs_write/fs_edit to drive DiffModal before the existing diff-preview stderr path"
      exports: ["install_tui_permissions"]
  key_links:
    - from: "voss/harness/tui/permissions_bridge.py"
      to: "voss/harness/permissions.py:PermissionGate"
      via: "install_tui_permissions(gate, app) sets gate.prompt_fn and gate.scope_prompt_fn to callables that run a modal on the app event loop and block until the user decides"
      pattern: "gate.prompt_fn ="
    - from: "voss/harness/tui/renderer.py:TextualRenderer"
      to: "voss/harness/tui/widgets/diff_modal.py"
      via: "TextualRenderer.show_diff_modal(hunks) returns a DiffDecision; called by the bridge"
      pattern: "show_diff_modal"
---

<objective>
Replace stderr-based permission prompts and the inline diff preview with full-screen modal dialogs for the TUI path. PermissionGate already exposes `prompt_fn` and `scope_prompt_fn` injection points (lines 113-115 of permissions.py) — this plan does NOT change the gate's logic; it ships a TUI bridge that installs modal-driven callables. Diff approval becomes per-hunk; permission prompts become three-button modals; budget exhaustion becomes its own modal with the UI-SPEC locked buttons.

Purpose: TUI-06 (per-hunk diff) and TUI-07 (permission + budget modals). Both are required for "feels like Claude Code / Aider depth" and for the destructive-action confirmation inventory in UI-SPEC.

Output: 3 modal widgets + 1 bridge module + extended TextualRenderer + 4 test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@voss/harness/permissions.py
@voss/harness/render.py

<interfaces>
<!-- PermissionGate hooks (extracted from voss/harness/permissions.py lines 108-117): -->
```python
@dataclass
class PermissionGate:
    mode: Mode = "edit"
    store: PermissionStore | None = None
    auto_yes: bool = False
    prompt_fn: Optional[Callable] = None         # signature: (tool_name: str, args: dict) -> str   ('a'|'A'|'d')
    edit_scope: Optional["EditScope"] = None
    scope_prompt_fn: Optional[Callable] = None    # signature: (target: str) -> str                  ('once'|'always'|'n')
    project_policy: Optional[PermissionsConfig] = None
```

<!-- Existing default prompts (permissions.py lines 230-256) write to stderr and read stdin. -->
<!-- This plan does NOT modify those defaults. It ships modal-backed replacements that the bridge installs at runtime. -->

<!-- Diff-preview behavior (permissions.py lines 177-216): _render_diff_preview already computes the unified diff for fs_write/fs_edit and writes to stderr. -->
<!-- For the TUI path we need to intercept BEFORE the stderr write and route the diff into DiffModal. The cleanest minimal change to permissions.py is to extract the diff computation into a callable that returns the diff text without writing, and have _render_diff_preview call it for the stderr path; the bridge calls it directly for the modal path. -->

<!-- UI-SPEC locked button labels: -->
- Diff hunk: [y] Accept · [n] Reject · [s] Skip · [a] Accept all · [q] Reject all · [Esc] Cancel review
- Permission: [a] Allow once · [A] Allow always · [d] Deny · [Esc] Deny
- Budget exhausted: [c] Continue +2000 · [e] End turn · [Esc] Cancel
- Heading copy verbatim from UI-SPEC Copywriting Contract.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extract _render_diff_preview computation; build DiffModal, PermissionModal, BudgetExhaustedModal widgets</name>
  <files>voss/harness/permissions.py, voss/harness/tui/widgets/diff_modal.py, voss/harness/tui/widgets/permission_modal.py, voss/harness/tui/widgets/budget_modal.py, voss/harness/tui/widgets/__init__.py, tests/harness/tui/test_diff_modal.py, tests/harness/tui/test_permission_modal.py, tests/harness/tui/test_budget_modal.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/permissions.py (full file; lines 177-216 _render_diff_preview is where the minimal extraction happens)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md (Copywriting Contract — diff modal heading verbatim, permission prompt copy verbatim, budget-exhausted copy verbatim, Destructive actions inventory)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/glyphs.py (M9-02 — diff marker glyphs `+`, `-`, `~` are NOT in glyphs.py because they are ASCII; add a comment in DiffModal noting they are bare ASCII to keep --no-unicode fallback identical)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (M9-02 — modals mount via app.push_screen)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/permissions.py lines 49-65 (mode_allows) — modals never bypass mode-tier denial; modal only fires when the gate would otherwise prompt
  </read_first>
  <behavior>
    - Test: existing PermissionGate behavior — `permissions.py` test suite (`tests/harness/test_permissions_modes.py`) still passes byte-identically after the diff-extraction refactor (no logic change).
    - Test: new module-level function `compute_diff_text(tool_name, args, base_dir) -> str` returns the same unified diff string that `_render_diff_preview` previously wrote to stderr. The original `_render_diff_preview` now delegates to it then writes to stderr — pure refactor.
    - Test (test_diff_modal): mount DiffModal with hunks=[Hunk(file="a.py", start=10, lines=["-old", "+new"]), Hunk(file="b.py", start=5, lines=["+added"])] inside `async with app.run_test() as pilot`. Heading text exactly matches UI-SPEC: `Review changes · 2 hunks · 2 files`.
    - Test: pressing `y` records DiffDecision(hunk_idx=0, decision="accept") and advances to hunk 1. Pressing `n` records reject. Pressing `s` skip. Pressing `a` auto-accepts all REMAINING. Pressing `q` auto-rejects all remaining. Pressing `escape` returns DiffDecision.cancel with empty acceptances. After last hunk decided, modal posts `DiffSubmitted(decisions)` and dismisses.
    - Test (test_permission_modal): mount PermissionModal(tool_name="shell_run", action_verb="run", target="ls -la") — body text contains the UI-SPEC copy `Tool shell_run wants to run ls -la.`. Pressing `a` returns 'a'; `A` returns 'A'; `d` returns 'd'; `escape` returns 'd'. Decision posted as PermissionDecision message.
    - Test (test_budget_modal): mount BudgetExhaustedModal(tokens_used=4000, tokens_limit=4000). Heading exactly `Budget exhausted`. Body contains the UI-SPEC copy `Turn stopped at 4000 / 4000 tokens. Continue with a new budget, or end the turn.`. Pressing `c` returns "continue"; `e` returns "end"; `escape` returns "cancel".
    - Test: every modal title row uses `class="modal-title"` and the locked accent color is NOT applied to titles (UI-SPEC accent allow-list does NOT include modal titles — guard against drift).
  </behavior>
  <action>
    Refactor `voss/harness/permissions.py` to extract diff-text computation:
      - Add module-level `def compute_diff_text(tool_name: str, args: dict, base_dir: Path) -> str` that contains the body of the current `_render_diff_preview` minus the stderr write. Returns the diff string (may be empty).
      - Change `_render_diff_preview(self, tool_name, args)` to call `compute_diff_text(tool_name, args, self.edit_scope.cwd if self.edit_scope else Path("."))` and then write the result to stderr exactly as before. Net behavior change: zero.
      - This is the only edit to permissions.py logic in this plan. No new fields, no new methods on PermissionGate.

    Create `voss/harness/tui/widgets/diff_modal.py`:
      - `@dataclass(frozen=True) class Hunk: file: str; start: int; lines: list[str]`
      - `@dataclass(frozen=True) class DiffDecision: file: str; decision: str  # 'accept' | 'reject' | 'skip'`
      - `class DiffModal(ModalScreen)` with BINDINGS `[("y","accept_one"),("n","reject_one"),("s","skip_one"),("a","accept_all"),("q","reject_all"),("escape","cancel")]`. State: list of Hunks + current index + accumulated decisions. compose() renders heading per UI-SPEC, a Static for each hunk preview using `+` `-` `~` markers (ASCII; intentional — matches `--no-unicode` fallback), and a Footer with the action label string from UI-SPEC verbatim.
      - On any terminal action, append the decision and either advance (`accept_one`/`reject_one`/`skip_one`) or terminate (`accept_all`/`reject_all` fill remaining, `cancel` empties). Post `DiffSubmitted(decisions: list[DiffDecision], cancelled: bool)` and dismiss.

    Create `voss/harness/tui/widgets/permission_modal.py`:
      - `PermissionChoice = Literal["a", "A", "d"]`
      - `class PermissionModal(ModalScreen)` BINDINGS `[("a","once"),("A","always"),("d","deny"),("escape","deny")]`. compose() renders heading `Permission required`, body `Tool {tool_name} wants to {action_verb} {target}.`, button-label footer per UI-SPEC. Post `PermissionDecision(choice)` and dismiss.

    Create `voss/harness/tui/widgets/budget_modal.py`:
      - `BudgetChoice = Literal["continue", "end", "cancel"]`
      - `class BudgetExhaustedModal(ModalScreen)` BINDINGS `[("c","continue"),("e","end"),("escape","cancel")]`. compose() renders heading `Budget exhausted`, body per UI-SPEC, footer.

    Re-export from `voss/harness/tui/widgets/__init__.py`: DiffModal, Hunk, DiffDecision, PermissionModal, PermissionChoice, BudgetExhaustedModal, BudgetChoice.

    Tests: one file per modal (3 files, 4-6 tests each) + a small targeted test asserting `compute_diff_text` returns the same string the pre-refactor `_render_diff_preview` produced via captured stderr (use capsys).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_permissions_modes.py tests/harness/tui/test_diff_modal.py tests/harness/tui/test_permission_modal.py tests/harness/tui/test_budget_modal.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.permissions import compute_diff_text, PermissionGate; print('ok')"` exits 0.
    - `python -c "from voss.harness.tui.widgets import DiffModal, Hunk, DiffDecision, PermissionModal, BudgetExhaustedModal; print('ok')"` exits 0.
    - `grep -c "Review changes · " voss/harness/tui/widgets/diff_modal.py` returns >= 1 (UI-SPEC locked heading).
    - `grep -c "Tool {tool_name} wants to {action_verb} {target}" voss/harness/tui/widgets/permission_modal.py` returns >= 1.
    - `grep -c "Budget exhausted" voss/harness/tui/widgets/budget_modal.py` returns >= 1.
    - `git diff --stat voss/harness/permissions.py | grep "files changed"` shows 1 file changed; the actual permission-check logic block (lines ~133-175 `def check`) is UNCHANGED (grep before/after).
    - All existing permissions tests pass; new modal tests pass.
  </acceptance_criteria>
  <done>Three modal widgets exist with UI-SPEC-locked copy + keymaps. permissions.py has compute_diff_text extracted; original behavior preserved. PermissionGate.check() unchanged.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: TUI permissions bridge + TextualRenderer modal-aware show_diff/show_permission paths</name>
  <files>voss/harness/tui/permissions_bridge.py, voss/harness/tui/renderer.py, tests/harness/tui/test_permissions_bridge.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/widgets/diff_modal.py, permission_modal.py, budget_modal.py (Task 1)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/permissions.py (full file post-refactor; confirm PermissionGate.prompt_fn / scope_prompt_fn signatures)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/renderer.py (M9-02 + M9-04; show_tool_call already exists; add a modal-aware diff path)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (lines 540-555 + 722-727 — gate construction sites; the bridge attaches AFTER gate construction at the cli.py level, but cli.py wiring lands in M9-06; this plan only ships the bridge function and its tests)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (M9-02 + M9-04 — extend with `push_modal_and_wait(modal) -> Future` helper)
  </read_first>
  <behavior>
    - Test (test_permissions_bridge): `install_tui_permissions(gate, app)` sets `gate.prompt_fn` and `gate.scope_prompt_fn` to non-None callables. Calling `gate.prompt_fn("shell_run", {"cmd":"ls"})` from a test thread blocks until the modal returns a choice; result is one of 'a' / 'A' / 'd'.
    - Test: with `app.run_test()` running a fake user that presses `a`, `gate.check("shell_run", {"cmd":"ls"})` returns `(True, "allowed once")`. Pressing `A` returns `(True, "allowed always")`. Pressing `d` returns `(False, "denied")`. Esc returns `(False, "denied")`.
    - Test: scope_prompt_fn — pressing `a` in an "expand scope?" modal returns "always", `y` returns "once", `n` / Esc returns "n". These map back through PermissionGate._prompt_expand into `out-of-scope: always` / `out-of-scope: once` / `out-of-scope denied`.
    - Test (TextualRenderer diff intercept): when TextualRenderer is wired and tool_name in {fs_write, fs_edit}, calling `renderer.show_diff_modal(hunks)` opens DiffModal, blocks until DiffSubmitted, returns list[DiffDecision]. If all rejected, the bridge translates this into a gate denial; cli.py wiring is in M9-06.
    - Test: when ANY diff hunk is accepted, the gate allows the write to proceed with the accepted-hunks list attached to the args dict under key `_tui_accepted_hunks` (the agent's apply step is unchanged — this metadata is advisory; the TUI's actual hunk-application is also out of scope for this plan because writes are still atomic at the fs_write/fs_edit tool level. The acceptance criterion is therefore: "user reviewed N hunks and approved the file as a whole"; per-hunk SURGICAL apply is logged as a follow-up in the M9 summary).
    - Test: when ALL hunks rejected, gate.check returns (False, "denied by diff review").
  </behavior>
  <action>
    Create `voss/harness/tui/permissions_bridge.py`:
      ```python
      from concurrent.futures import Future
      from voss.harness.permissions import PermissionGate
      from voss.harness.tui.widgets import PermissionModal, DiffModal, BudgetExhaustedModal

      def install_tui_permissions(gate: PermissionGate, app) -> None:
          """Replace the gate's stderr/stdin prompt functions with modal-driven futures."""
          def prompt(tool_name: str, args: dict) -> str:
              fut: Future = Future()
              def _on_decision(msg):
                  fut.set_result(msg.choice)
              app.call_from_thread(app.push_modal_and_wait,
                                   PermissionModal(tool_name=tool_name,
                                                   action_verb=_verb_for(tool_name),
                                                   target=_short_target(args)),
                                   _on_decision)
              return fut.result(timeout=300)  # 5 min hard cap on user inattention
          def scope_prompt(target: str) -> str:
              fut: Future = Future()
              app.call_from_thread(app.push_modal_and_wait,
                                   ScopeExpandModal(target=target),
                                   lambda msg: fut.set_result(msg.choice))
              return fut.result(timeout=300)
          gate.prompt_fn = prompt
          gate.scope_prompt_fn = scope_prompt
      ```
      Add a small `ScopeExpandModal` to permission_modal.py (or a new file) with [y/a/n/Esc] returning "once"/"always"/"n" to match the existing `_interactive_expand_prompt` contract on lines 244-255 of permissions.py.

    Extend `voss/harness/tui/renderer.py` with `show_diff_modal(hunks: list[Hunk]) -> list[DiffDecision]` that pushes DiffModal and blocks via Future. Provide `show_budget_modal(used, limit) -> str`.

    Extend `voss/harness/tui/app.py` with `push_modal_and_wait(modal, on_decision_callback) -> None` that calls `self.push_screen(modal, callback=on_decision_callback)`.

    Create `tests/harness/tui/test_permissions_bridge.py` with 6 tests using a real PermissionGate and a Textual `app.run_test()` pilot that presses keys to drive the modal.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/tui/test_permissions_bridge.py tests/harness/test_permissions_modes.py tests/harness/test_edit_scope.py tests/harness/tui/test_diff_modal.py tests/harness/tui/test_permission_modal.py tests/harness/tui/test_budget_modal.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from voss.harness.tui.permissions_bridge import install_tui_permissions; from voss.harness.permissions import PermissionGate; g = PermissionGate(); print(g.prompt_fn)"` prints `None` before install (sanity).
    - `grep -c "gate.prompt_fn" voss/harness/tui/permissions_bridge.py` returns >= 1.
    - `grep -c "gate.scope_prompt_fn" voss/harness/tui/permissions_bridge.py` returns >= 1.
    - `grep -rn "prompt_fn\\|scope_prompt_fn" voss/harness/permissions.py | grep -v '^#'` shows the signature lines are unchanged from pre-M9 (no new fields on PermissionGate).
    - All permission-related tests pass (pre-existing + new).
  </acceptance_criteria>
  <done>install_tui_permissions(gate, app) swaps modal-driven callables into the gate. PermissionGate logic unchanged. Bridge sits in voss/harness/tui/, not in permissions.py.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| modal Future timeout | user inattention → modal blocks indefinitely; mitigation timeout. |
| agent thread → app event loop | bridge uses call_from_thread for thread safety. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M9-05-01 | DoS | User walks away mid-modal | mitigate | Bridge Future has `fut.result(timeout=300)` (5 min). On timeout, gate gets `'d'` denial and the agent unwinds gracefully. Verified by test that does NOT press anything and asserts denial after timeout (test uses monkeypatched short timeout). |
| T-M9-05-02 | Elevation | Modal returns wrong choice | mitigate | Modal `BINDINGS` map keys to actions 1-to-1 with constant strings. No user input parsing. |
| T-M9-05-03 | Confused-deputy | Per-hunk decision metadata `_tui_accepted_hunks` misread by fs_write | accept | fs_write does NOT consume that metadata in this plan; per-hunk surgical apply is logged as follow-up. The user has reviewed every hunk before the gate allowed the write; that is the security gate (not surgical apply). |
| T-M9-05-04 | Information disclosure | Diff modal shows file contents to attacker shoulder-surfing | accept | Same risk as the pre-M9 stderr diff preview; no new exposure. |
</threat_model>

<verification>
- 4 modal test files + 1 bridge test file + existing permissions tests all green.
- compute_diff_text refactor preserves byte-identical stderr output for non-TUI paths.
- PermissionGate fields unchanged (grep confirmed).
</verification>

<success_criteria>
1. DiffModal opens per-hunk for fs_write/fs_edit when TUI is active.
2. PermissionModal opens for shell_run / out-of-scope writes when gate.prompt_fn is the TUI version.
3. BudgetExhaustedModal opens with the three locked choices.
4. install_tui_permissions(gate, app) is the ONE entry point; cli.py wiring deferred to M9-06.
5. permissions.py PermissionGate logic block (def check) is byte-unchanged.
6. Esc on any modal denies/cancels per UI-SPEC destructive-actions inventory.
</success_criteria>

<output>
After completion, create `.planning/phases/M9-tui-shell-tui-01/M9-05-SUMMARY.md`.
</output>
