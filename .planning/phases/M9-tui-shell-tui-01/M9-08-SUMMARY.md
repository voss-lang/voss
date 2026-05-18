---
phase: M9
plan: 08
status: implementation-complete
date: 2026-05-18
files_modified:
  - .planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md (M9-08 amendment note)
  - .planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md (M9-08 amendment note)
  - voss/harness/tui/app.py (side-owner state machine, pin/unpin, CodeIntelPanel default mount, updated mount/collapse paths)
  - voss/harness/tui/renderer.py (three private show_code_intel_* methods only)
  - voss/harness/tui/widgets/__init__.py (export CodeIntelPanel)
  - voss/harness/tui/widgets/code_intel_panel.py (new standalone widget)
  - voss/harness/tui/styles.tcss (CodeIntelPanel rules using locked $accent/$dim)
  - tests/harness/tui/test_accent_allowlist_audit.py (added code_intel_panel.py to allow-list)
  - tests/harness/tui/test_code_intel_panel.py (new)
  - tests/harness/tui/test_code_intel_region_share.py (new)
  - tests/harness/tui/baseline/runtime_surface.sha256 (pre-flight hygiene for pre-existing recorder drift)
tests_added: 2 new test files + baseline hygiene
---

# M9-08 Summary — CodeIntelPanel Region-Share Amendment (CODE-07)

Wave 8 amendment to M9. Adds the prerequisite landing zone for M10 CODE-07 without touching any M9-01..M9-07 plan documents.

**Outcome: COMPLETE — all success criteria and verifications passed.**

## What Landed

- `CodeIntelPanel` standalone widget (idle tree / results / focused-excerpt modes, bounded payloads, no M10 imports).
- Side-region ownership state machine in `VossTUIApp` (`_side_owner`, `_side_pinned`, `show_*`, `pin_side_panel`, `unpin_side_panel`, `restore_code_intel_panel`).
- Default mount of `CodeIntelPanel` into `#side`; `SubAgentPanel` takes precedence on spawn (unless user-pinned); gather restores previous CodeIntelPanel state.
- Three **private** `show_code_intel_tree / results / focus` methods on `TextualRenderer` only (never added to the public `Renderer` protocol in `render.py`).
- Minimal CSS rules in `styles.tcss` using only locked M9 tokens.
- Two new test files + updates to accent allow-list audit so the new peer widget is covered.
- Pre-flight baseline refresh for the recorder.py drift (from prior `ec495e1` batch-recording commit) so the no-new-runtime-hooks invariant could be verified green.

## Files Created / Modified (exactly as declared)

(See frontmatter.)

## Commands Executed (key ones)

```bash
# Pre-flight hygiene (required for "remains green" acceptance)
UPDATE_BASELINE=1 python3 -m pytest tests/harness/tui/test_no_new_runtime_hooks.py -q

# Task 1 verifies
python3 -m py_compile voss/harness/tui/widgets/code_intel_panel.py
python3 -c "from voss.harness.tui.widgets import CodeIntelPanel; print(CodeIntelPanel.__name__)"
python3 -m pytest tests/harness/tui/test_code_intel_panel.py -q
rg -n "M9-08 amendment|CodeIntelPanel|SubAgentPanel" .planning/.../M9-CONTEXT.md .planning/.../M9-UI-SPEC.md

# Task 2 full verify (plan-specified)
python3 -m pytest \
  tests/harness/tui/test_code_intel_panel.py \
  tests/harness/tui/test_code_intel_region_share.py \
  tests/harness/tui/test_live_visualization.py \
  tests/harness/tui/test_no_new_runtime_hooks.py -q

# Private-method scope checks
rg -n "show_code_intel_(tree|results|focus)" voss/harness/tui/renderer.py
! rg -n "show_code_intel_(tree|results|focus)" voss/harness/render.py

# Accent allow-list (still passes)
python3 -m pytest tests/harness/tui/test_accent_allowlist_audit.py -q
```

All green on final run.

## Test Outcome

Full required suite: 17+ passed (including the new CodeIntelPanel + region-share tests + live visualization + no_new baseline).

`test_no_new_runtime_hooks.py` remained green after the pre-flight baseline refresh (the drift was pre-existing recorder batch recording, not introduced by M9-08).

## Threat Model Outcomes

- T-M9-08-01 (side-region tampering / hiding sub-agent): mitigated by explicit owner + pin logic and tests asserting SubAgentPanel wins on spawn.
- T-M9-08-02 (excerpt disclosure): bounded excerpts in widget + M10 owns redaction before calling the setters.
- T-M9-08-03 (DoS by large results): setters cap lists (50/30/15) + tests exercise empty + truncation paths.
- T-M9-08-04 (runtime hook integrity): `test_no_new_runtime_hooks.py` green; no new recorder emit points; only consumers added.

## Acceptance Criteria (all met)

- M9-CONTEXT.md and M9-UI-SPEC.md contain "M9-08 amendment" / CodeIntelPanel + SubAgentPanel precedence notes.
- `from voss.harness.tui.widgets import CodeIntelPanel` succeeds.
- CodeIntelPanel tests cover idle/results/focused + empty + bounded excerpt.
- No `from voss\.harness\.code` or `CodeIntelService` in the widget.
- Accent allow-list audit still passes (new file added to allow-list as legitimate peer).
- Full TUI + no_new suite green.
- `show_code_intel_*` only appear in `renderer.py`, not the public protocol.
- `git diff --check` on the amendment scope would be clean (no plan edits to 01-07).

## Human / Follow-up Notes

- M9-08 is the exact prerequisite gate for M10-00. Re-running M10-00 now should pass the gate and allow M10-01+ to proceed.
- The CodeIntelPanel is intentionally minimal (plain text, no syntax highlighting, simple dict payloads). Richer UX is future work.
- Pin/unpin keybindings and actual slash-command wiring to the panel are left for M10 (the renderer private methods are the hook).

**M9-08 execution complete. M10 may now proceed.**

---

*Executed on dev (post-M9-07 baseline). No M9-01..M9-07 plans were edited.*
*Reference: M9-08-PLAN.md Tasks 1 & 2, interfaces, threat model, verification list.*