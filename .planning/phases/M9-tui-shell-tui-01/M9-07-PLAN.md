---
phase: M9
plan: 07
type: execute
wave: 7
depends_on: [M9-06]
files_modified:
  - voss/harness/cli.py
  - voss/harness/render.py
  - voss/harness/tui/renderer.py
  - voss/harness/tui/app.py
  - voss/harness/tui/glyphs.py
  - voss/harness/tui/capability.py
  - tests/harness/tui/test_cli_integration.py
  - tests/harness/tui/test_accent_allowlist_audit.py
  - tests/harness/tui/test_no_unicode_fallback.py
  - tests/harness/tui/test_windows_console_strategy.py
  - tests/harness/tui/test_plain_parity.py
autonomous: false
requirements: [TUI-09, TUI-10]
must_haves:
  truths:
    - "Default `voss chat` / `voss do` / `voss edit` / `voss resume` on a TTY uses TextualRenderer (live swap-in from the M9-02 force_tui path)."
    - "`--plain` stdout byte-output remains identical to the M9-01 baseline; test_plain_parity green after the wire-up."
    - "install_tui_permissions is called at all four CLI interactive entry points when the TextualRenderer is active."
    - "Auditor grep over the entire voss/harness/tui/ tree confirms accent color (`$accent` / `.accent` / `#5FAFFF`) appears only on the 6 UI-SPEC allow-list elements."
    - "When `--no-unicode` flag or `VOSS_NO_UNICODE=1` env is set, glyphs.py constants fall back to ASCII."
    - "Windows console detection picks one of {hard-block, soft-degrade, auto-plain} strategies and emits the UI-SPEC-locked notice copy; the strategy decision is grep-auditable."
    - "Phase-final human-verify checkpoint records UI-SPEC Acceptance Visual Checks 1, 8, 9 confirmation."
  artifacts:
    - path: "voss/harness/tui/glyphs.py"
      provides: "Adds `NO_UNICODE_FALLBACK` mapping + import-time check on `VOSS_NO_UNICODE=1`; constants flip to ASCII when set"
    - path: "voss/harness/tui/capability.py"
      provides: "Adds Windows-console detection branch to tui_should_activate (returns inactive with locked notice copy when win32 + no WT_SESSION)"
    - path: "tests/harness/tui/test_accent_allowlist_audit.py"
      provides: "Grep-based accent allow-list audit per UI-SPEC Acceptance Visual Check 3"
    - path: "tests/harness/tui/test_no_unicode_fallback.py"
      provides: "--no-unicode mode glyph fallback verification"
    - path: "tests/harness/tui/test_windows_console_strategy.py"
      provides: "Windows-console fallback decision: which strategy fires under which capability set"
  key_links:
    - from: "voss/harness/cli.py"
      to: "voss/harness/tui/app.py:VossTUIApp"
      via: "make_renderer default path now constructs VossTUIApp() and returns TextualRenderer(app) when capability says yes"
      pattern: "return TextualRenderer"
    - from: "voss/harness/cli.py"
      to: "voss/harness/tui/permissions_bridge.py:install_tui_permissions"
      via: "after gate construction, if renderer isinstance TextualRenderer call install_tui_permissions(gate, renderer.app)"
      pattern: "install_tui_permissions"
    - from: "voss/harness/tui/capability.py"
      to: "sys.platform + WT_SESSION"
      via: "Windows-console branch in tui_should_activate"
      pattern: "win32"
---

<objective>
Final integration wave (split from original M9-06 per checker B1). (1) Flip `make_renderer` default path so a TTY user gets the TextualRenderer by default while `--plain` and non-TTY still get PlainRenderer byte-identically. (2) Wire the TUI permissions bridge from M9-05 into cli.py at the four interactive entry points. (3) Land `--no-unicode` flag + `VOSS_NO_UNICODE` env + glyph fallback table in glyphs.py. (4) Add Windows-console strategy to capability.py. (5) Land the UI-SPEC Acceptance Visual Checks as automated audits: accent allow-list, --no-unicode fallback, Windows console strategy. (6) Phase-final human-verify checkpoint for UI-SPEC Acceptance Visual Checks 1, 8, 9.

Purpose: TUI-09 (full keymap + slash-palette + help-overlay wired to default user path), TUI-10 (--plain byte parity acceptance + Windows strategy + accent allow-list).

Output: cli.py wiring, render.py default flip, glyphs.py fallback, capability.py Windows branch, three audit test files, expanded test_plain_parity, and the final phase-level visual checkpoint. This plan is the only one in M9 with a checkpoint.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md
@.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md
@voss/harness/cli.py
@voss/harness/render.py
@voss/harness/permissions.py
@voss/harness/tui/capability.py
@voss/harness/tui/glyphs.py

<interfaces>
<!-- cli.py entry-point call sites that need plain= + force_tui= plumbing finalized: -->
- do_cmd line 538: renderer = make_renderer(json_mode=json_mode)         → add plain=plain
- _run_repl line 701: renderer = make_renderer(json_mode=json_mode)       → add plain=plain
- resume_cmd line ~970 (passes plain via _run_repl)
- edit_cmd line ~676 (passes plain via _run_repl)

<!-- UI-SPEC accent allow-list (the only 6 elements that may carry `.accent` / `$accent` / `#5FAFFF`): -->
1. The user-input glyph `▌` at input bar (input_bar.py).
2. The session id in the header (header.py).
3. The current model name in the status line (status_line.py).
4. The active sub-agent name banner in the side panel header (sub_agent_panel.py).
5. The current selection in the slash palette (combined with reverse-video) (slash_palette.py).
6. Confidence bars at the agent's FINAL confidence value (confidence_bar.py is_final path).

<!-- glyphs.py fallback table — added in this plan: -->
NO_UNICODE_FALLBACK = {
    "PROMPT": "|",
    "USER_INPUT": ">",
    "TOOL_CALL": ">",
    "WARN": "!",
    "BAR_FILL": "#",
    "BAR_EMPTY": ".",
    "BUDGET_FILL": "=",
    "BUDGET_EMPTY": "-",
    "NEST_LAST": "+-",
    "NEST_MID": "+-",
    "FORK": "+",
}

<!-- Windows-console strategy (decided here per checker B4): -->
- sys.platform == "win32" AND WT_SESSION env NOT set → TUIDecision(activate=False, reason="Windows console missing capability")
- sys.platform == "win32" AND WT_SESSION env SET (Windows Terminal) → proceed with normal capability check
- Other platforms → unchanged
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: cli.py wiring + make_renderer default flip + install_tui_permissions invocation + --no-unicode flag/env + Windows-console branch + audit tests</name>
  <files>voss/harness/cli.py, voss/harness/render.py, voss/harness/tui/renderer.py, voss/harness/tui/app.py, voss/harness/tui/glyphs.py, voss/harness/tui/capability.py, tests/harness/tui/test_cli_integration.py, tests/harness/tui/test_accent_allowlist_audit.py, tests/harness/tui/test_no_unicode_fallback.py, tests/harness/tui/test_windows_console_strategy.py, tests/harness/tui/test_plain_parity.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (lines 511-575 do_cmd; 599-620 chat_cmd; 647-685 edit_cmd; 955-981 resume_cmd; 688-740 _run_repl)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/render.py (M9-02 make_renderer; default path currently still returns TtyRenderer when TTY+no-plain+no-force_tui — flip this so the default becomes TextualRenderer)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/permissions_bridge.py (M9-05 — install_tui_permissions hook to wire)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/styles.tcss (M9-02 — accent variable lives here)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/glyphs.py (M9-02 — add NO_UNICODE_FALLBACK dict mapping each glyph to ASCII + an import-time env check)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/capability.py (M9-01 — extend tui_should_activate with Windows-console branch)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md (Acceptance Visual Checks 1-10 — they are the audit checklist for this task; "Color Contract" Monochrome row; "Windows console limitation hit" copy)
  </read_first>
  <behavior>
    - Test (test_cli_integration): `CliRunner().invoke(do_cmd, ["x"])` (default, no --plain, CliRunner stdout is non-TTY) → uses PlainRenderer (auto non-TTY rule); stdout matches the M9-01 baseline byte-for-byte.
    - Test: `CliRunner().invoke(do_cmd, ["x"], env={"FORCE_TUI":"1"})` → uses TextualRenderer (force_tui hook from M9-01).
    - Test: with monkeypatched `sys.stdout.isatty=lambda:True`, `shutil.get_terminal_size=(100,30)`, non-win32 platform: make_renderer default path returns a TextualRenderer instance.
    - Test (install_tui_permissions wiring): when TextualRenderer is active, `gate.prompt_fn is not None` AND `gate.scope_prompt_fn is not None` after CLI setup; when PlainRenderer is active, both remain unmodified (defaults).
    - Test (test_accent_allowlist_audit): walk voss/harness/tui/, grep every occurrence of `accent`, `#5FAFFF`, or `$accent` (case-insensitive). For each match, classify by file basename. Assert basenames are exactly the 6 UI-SPEC allow-list set: input_bar.py, header.py, status_line.py, sub_agent_panel.py, slash_palette.py, confidence_bar.py — plus styles.tcss for the design-token definitions (the canonical declaration site). Any other file containing accent → test fails with the offending location.
    - Test (test_no_unicode_fallback, env path): set env `VOSS_NO_UNICODE=1`. Subprocess invocation of `python -c "from voss.harness.tui import glyphs; print(glyphs.PROMPT)"` with the env set; assert stdout is `|`. Without env, assert `▌`. Cover all 11 fallback entries.
    - Test (test_no_unicode_fallback, flag path): `CliRunner().invoke(chat_cmd, ["--no-unicode"], env={...})` → glyphs module ends up in fallback mode for the run; `voss.harness.tui.glyphs.PROMPT == "|"` for the duration of the command.
    - Test (test_windows_console_strategy, hard-block): monkeypatch `sys.platform="win32"` and `os.environ.pop("WT_SESSION", None)`. `tui_should_activate()` returns `TUIDecision(activate=False, reason="Windows console missing capability")`. The CLI emits the UI-SPEC locked stderr notice `voss: Windows console missing capability · using --plain mode` and auto-falls back to PlainRenderer.
    - Test (test_windows_console_strategy, allow-list): monkeypatch `sys.platform="win32"` and `os.environ["WT_SESSION"]="abc"` (Windows Terminal). `tui_should_activate()` proceeds to other capability checks (does NOT short-circuit on Windows).
    - Test (test_plain_parity, expanded): the M9-01 baseline still passes byte-for-byte after the default-path flip (sanity gate — Wave 7 must NOT regress --plain).
  </behavior>
  <action>
    Edit `voss/harness/render.py` `make_renderer`:
      - When `json_mode=True` → JsonRenderer (unchanged).
      - Else compute `decision = tui_should_activate(plain=plain, ...)`.
      - If `decision.activate is True`: `from .tui.app import VossTUIApp; from .tui.renderer import TextualRenderer; app = VossTUIApp(); return TextualRenderer(app=app)` AND mark the app to start asynchronously when the first render call lands (or expose a `start()` method the CLI calls before run_turn).
      - Else if `sys.stdout.isatty()` and NOT plain: emit the locked Windows notice (when decision.reason starts with "Windows console") to stderr, then `return PlainRenderer()`. Otherwise return `TtyRenderer()` (preserves the legacy non-Textual TTY path for non-Windows fallbacks).
      - Else: `return PlainRenderer()`.

    Edit `voss/harness/cli.py`:
      - For each of `do_cmd`, `chat_cmd`, `edit_cmd`, `resume_cmd`, `_run_repl`: add a `--no-unicode` Click flag (mirroring the `--plain` flag from M9-01). The flag sets `os.environ["VOSS_NO_UNICODE"] = "1"` BEFORE `make_renderer` is called.
      - For each of `do_cmd`, `_run_repl`: after gate construction (lines ~541-555 do_cmd, ~722-727 _run_repl), check `isinstance(renderer, TextualRenderer)` (use deferred import to avoid coupling); if yes, call `install_tui_permissions(gate, renderer.app)`. This is the only cli.py logic addition beyond the flag.
      - Make sure the app is started/stopped around the asyncio.run(run_turn(...)) block — Textual's typical pattern is `await app.run_async()` in the same loop. The exact API call depends on Textual's `run_async` / `_run_pilot` surface; use Context7 for `textual app run async` if unsure.

    Edit `voss/harness/tui/glyphs.py` (additive — does NOT change the existing locked values when the env is unset):
      - Add a module-level `NO_UNICODE_FALLBACK` dict (the 11-entry mapping above).
      - At import time, if `os.environ.get("VOSS_NO_UNICODE") == "1"`, replace each module-level constant's value with its NO_UNICODE_FALLBACK entry. Otherwise keep the locked Unicode codepoints.
      - The `__getattr__` allow-list (from M9-02) is unchanged.

    Edit `voss/harness/tui/capability.py` (M9-01) — add the Windows-console branch to `tui_should_activate` BEFORE the size/textual_available checks:
      ```python
      if sys.platform == "win32":
          if not (env or os.environ).get("WT_SESSION"):
              return TUIDecision(activate=False, reason="Windows console missing capability")
      ```
      Update the locked notice copy when make_renderer encounters this reason and emits to stderr: `voss: Windows console missing capability · using --plain mode`.

    Create three audit test files:
      - test_accent_allowlist_audit.py: walk `voss/harness/tui/` with `Path.rglob("*.py")` + `.tcss`; for each file, grep matches; assert file basename ∈ the allow-list set.
      - test_no_unicode_fallback.py: subprocess invocation of `python -c "from voss.harness.tui import glyphs; print(glyphs.PROMPT)"` with `VOSS_NO_UNICODE=1` in env; assert stdout is `|`. Without env, assert `▌`. Repeat for all 11 glyphs.
      - test_windows_console_strategy.py: monkeypatch `sys.platform`, `os.environ`, call `tui_should_activate`, assert reason string.

    Update `tests/harness/tui/test_plain_parity.py` to ALSO assert the post-flip default path (no --plain, no FORCE_TUI, CliRunner non-TTY): still byte-identical to baseline.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/tui/ tests/harness/test_cli.py tests/harness/test_permissions_modes.py tests/harness/test_session.py tests/harness/test_session_redaction.py tests/harness/test_happy_path_integration.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "install_tui_permissions" voss/harness/cli.py` returns >= 2 (do_cmd + _run_repl).
    - `grep -c "return TextualRenderer" voss/harness/render.py` returns >= 1 (default path now constructs the TUI renderer).
    - `grep -c "VOSS_NO_UNICODE" voss/harness/tui/glyphs.py` returns >= 1 (env check at import time).
    - `grep -c "NO_UNICODE_FALLBACK" voss/harness/tui/glyphs.py` returns >= 1 (fallback table defined).
    - `grep -c "win32" voss/harness/tui/capability.py` returns >= 1 (Windows console branch present).
    - `grep -c "Windows console missing capability" voss/harness/tui/capability.py voss/harness/render.py` returns >= 1 (locked notice copy present).
    - `grep -c "no-unicode" voss/harness/cli.py` returns >= 4 (one Click flag per interactive command).
    - test_accent_allowlist_audit passes — confirms accent appears ONLY in the 6 allow-listed widget files + styles.tcss.
    - test_no_unicode_fallback passes for both env states.
    - test_windows_console_strategy passes for both Windows console and Windows Terminal.
    - test_plain_parity passes (M9-01 contract intact through Wave 7).
    - Full test suite green: `pytest tests/ -x -q` exit code 0.
  </acceptance_criteria>
  <done>Default TTY user gets the Textual TUI. --plain user gets byte-identical plain output. Permissions bridge installed at all 4 entry points. UI-SPEC accent allow-list, --no-unicode fallback, and Windows console strategy are automated gates. M9-04 W3 SPAWN_TOOL_NAME and M9-02 W5 zero-total contract are still green.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Phase-final human verification of UI-SPEC Acceptance Visual Checks 1, 8, 9</name>
  <what-built>
    The full M9 TUI shell is live. `voss chat` on a TTY opens a Textual full-screen app with header / main / status / input regions; the side panel appears when subagents spawn; slash palette opens on `/`; `?` opens help; diff approval, permission prompts, and budget exhaustion are modals; fork-from-turn (`f`) creates a backward-compat-additive new session; `--plain` and non-TTY paths are byte-identical to pre-M9 output; `/save` is now an alias to `/snapshot` with a deprecation warning (frees `/save` for M8 reservation).

    Automated audits cover Acceptance Visual Checks 2 (glyph vocabulary), 3 (accent allow-list), 4 (--plain parity), 5 (NO_COLOR / --no-unicode), 6 (no new runtime hooks on baseline set), 7 (destructive confirmations present), 10 (reserved slash names including `/save`).

    Checks 1 (80x24 minimum honored), 8 (empty states render), and 9 (help overlay reachable) need a human eye on a real terminal because they involve visual layout judgment.
  </what-built>
  <how-to-verify>
    Run each of the following in a separate terminal. Take a screenshot or visual note for each; no need to commit screenshots.

    1. Min-size guard (Acceptance Visual Check 1):
       a. Resize your terminal to 79 cols × 24 rows. Run `voss chat`. Expected: exits with code 2 and stderr message `voss: terminal must be at least 80×24 (current: 79×24). Resize or use --plain.`.
       b. Resize to 80 × 24 exactly. Run `voss chat`. Expected: app mounts, all four regions visible, no truncation of header glyphs or status fields.
    2. Empty states (Acceptance Visual Check 8):
       a. Run `voss chat` in a fresh repo (no prior sessions). Expected: main pane shows `No turns yet` heading + `Type a task below to start. Use / for commands, ? for help.` body.
       b. Press `/` then type `sessions` and Enter (or type `/sessions`). Expected: empty session list shows `No sessions in this repo` heading + `Run voss do "<task>" to create one.` body.
       c. With no active spawn, the side panel is collapsed to 0 columns (no placeholder copy visible).
    3. Help overlay reachable (Acceptance Visual Check 9):
       a. From the main pane (or input bar — `?` is global), press `?`. Expected: HelpOverlay opens with heading `voss tui · keys + commands`, lists every keybinding and every visible slash command (including `/snapshot` and the deprecated-aliased `/save`). Press `Esc`. Expected: overlay dismisses.
    4. Sanity check on a real model:
       a. `voss do --plain "summarize this repo"` — output should look identical to pre-M9 plain stream.
       b. `voss chat` (TUI), type `/help`, press Enter — slash should dispatch through the registry, output appears in main pane.
       c. `voss chat`, type `/save` then Enter — expected: stderr shows the deprecation line; persistence side-effect still runs.
       d. `voss chat`, type `/snapshot` then Enter — expected: no deprecation warning; persistence runs.
       e. (Optional) `voss chat`, type `summarize this repo`, observe the live BudgetMeter and ConfidenceBar render at each step.
    5. --no-unicode fallback (Acceptance Visual Check 5):
       a. Run `voss chat --no-unicode`. Expected: input bar glyph is `|`, tool-call marker is `>`, confidence bar uses `#`/`.`, budget bar uses `=`/`-`.
  </how-to-verify>
  <resume-signal>
    Type one of:
    - `approved` — Acceptance Visual Checks 1, 8, 9 all confirmed; phase complete.
    - `gap: <description>` — A specific check failed; describe what you saw vs UI-SPEC. The phase-checker will route this to a gap-closure plan.
  </resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user CLI flags → make_renderer | --plain / --no-unicode / FORCE_TUI env all converge in capability.py. |
| sys.platform / WT_SESSION → capability | Platform detection is read-only; no privilege escalation possible. |
| TextualRenderer.app → install_tui_permissions | Bridge only sets prompt_fn / scope_prompt_fn on the gate; no other state mutation. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M9-07-01 | Confused-deputy | TUI permissions bridge bypass via mis-wiring | mitigate | install_tui_permissions only sets prompt_fn / scope_prompt_fn. mode_allows tier check (permissions.py:49) runs BEFORE prompt_fn regardless. Test verifies `mode="plan"` still denies fs_write even with TUI active. |
| T-M9-07-02 | Tampering | --no-unicode env smuggled into a piped invocation | accept | VOSS_NO_UNICODE only affects display glyphs, not on-disk session data or stdout-piped JSON. No security impact. |
| T-M9-07-03 | DoS | Windows console hard-block leaves user without fallback | mitigate | When tui_should_activate returns Windows-inactive, make_renderer falls back to PlainRenderer with the locked stderr notice. User can still use voss. |
| T-M9-07-04 | Info disclosure | Accent allow-list audit greps test repo paths into stderr | accept | Audit test runs in CI/local only; offending paths are intentional output. |
</threat_model>

<verification>
- 9 new tests across 4 files + expanded test_plain_parity green.
- Full repo test suite green.
- Phase-final human-verify checkpoint approved.
- Accent allow-list, no-unicode fallback, Windows console strategy all automated gates.
- M9-01 plain-parity baseline intact through the default-path flip.
</verification>

<success_criteria>
1. `voss chat` on a TTY ≥ 80×24 (non-Windows or Windows Terminal) opens the Textual TUI by default.
2. `voss chat --plain` and piped invocations stay byte-identical to the M9-01 baseline.
3. `voss chat --no-unicode` swaps glyphs to ASCII fallback for the run.
4. Windows console (no WT_SESSION) auto-falls back to PlainRenderer with locked stderr notice.
5. install_tui_permissions wires DiffModal, PermissionModal, BudgetExhaustedModal into PermissionGate at all four interactive entry points.
6. test_accent_allowlist_audit, test_no_unicode_fallback, test_windows_console_strategy all green.
7. UI-SPEC Acceptance Visual Checks 1, 8, 9 confirmed by human-verify checkpoint.
</success_criteria>

<output>
After completion, create `.planning/phases/M9-tui-shell-tui-01/M9-07-SUMMARY.md` AND `.planning/phases/M9-tui-shell-tui-01/M9-PHASE-SUMMARY.md` (phase-level aggregate; lists which CONTEXT decisions and UI-SPEC checks landed, which were deferred to follow-up, per-hunk surgical diff apply follow-up noted from M9-05, and `/save` → `/snapshot` rename + M8 handoff).
</output>
</content>
</invoke>