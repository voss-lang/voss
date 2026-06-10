---
phase: E5
slug: tui-voss-app-autonomous-driving
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-10
reviewed_at: 2026-06-10
medium: terminal-ui-and-desktop-e2e
---

# E5 UI Spec: TUI and voss-app Autonomous Driving

## Purpose

E5 proves that the existing TUI and voss-app surfaces can be driven end-to-end by automation. This is a preservation contract, not a redesign contract.

Success means tests and manual CI can operate real user-visible flows while the product still looks and behaves like the current Voss interfaces. Any new UI affordance must exist to make a real state observable, not to decorate or market the system.

## Assumptions

- Phase E5 does not have an `E5-SPEC.md`; trace UI decisions to `E5-CONTEXT.md`, `E5-RESEARCH.md`, and the inherited phase contracts listed below.
- TUI automation uses Textual Pilot in process. It must not introduce PTY-only behavior, screenshots as assertions, or testing-only visible copy.
- voss-app automation targets manual Linux CI with `tauri-driver`. It must not become a required pull-request gate in E5.
- Live model proof is limited to the TUI. Desktop e2e uses fake or local service seams only.

## Inherited Contracts

E5 must preserve these contracts unless a downstream implementation plan explicitly calls out and verifies a narrower exception:

| Surface | Source contract | E5 inheritance |
| --- | --- | --- |
| TUI shell | `.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md` | Keep the terminal-first, keyboard-first, Ignite-accented Textual shell. |
| TUI implementation | `voss/harness/tui/styles.tcss`, `widgets/input_bar.py`, `widgets/turn_view.py`, `renderer.py` | Preserve widget structure, copy, status areas, and modal behavior while adding stable automation hooks only where needed. |
| Desktop shell | `.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md` | Keep the dense desktop IDE surface, token-only styling, 4px spacing grid, and hand-rolled Solid/Tauri components. |
| Protocol/live pane | `.planning/phases/V15-live-plane-integration/V15-UI-SPEC.md` | Preserve honest live/snapshot labeling and existing protocol row density. |
| Theme tokens | `apps/voss-app/src/styles/variant-b.css`, `apps/voss-app/src/themes/bundled/voss-ignite.json` | Reuse existing CSS variables. No new palette, font, or radius system. |

## Scope

Allowed E5 UI-facing changes:

- Stable widget IDs, classes, `data-testid`, `data-tauri-e2e`, or `data-e2e-state` attributes that do not alter layout or presentation.
- Test-build seams that make native dialogs, fake turns, or local service state controllable under explicit test environment flags.
- Minimal state exposure needed for assertions, such as selected command, active theme, project-open result, stream lifecycle, or diff approval state.
- Workflow artifact labels, job summaries, and test output that identify hermetic, fake, skipped, or live proof runs.

Out of scope:

- New panes, navigation models, dashboards, landing pages, onboarding flows, or marketing copy.
- New visual themes, accent colors, typography stacks, icon systems, or component libraries.
- Replacing existing Textual widgets, Solid components, or Tauri shell behavior for test convenience.
- Showing provider credentials, model tokens, hidden prompts, or auth configuration in visible UI.

## Design System

### TUI

- Framework: Textual.
- Component model: existing `VossTUIApp`, `TranscriptView`, `InputBar`, `TurnView`, modal widgets, and renderer bridge.
- Styling source: `voss/harness/tui/styles.tcss` plus existing widget-local CSS.
- Accent: Voss Ignite orange `#ff5b1f` only where already used by the TUI contract.
- Icons and marks: existing ASCII logo and text glyphs only. Do not add emoji.
- Layout: preserve current terminal density and keyboard flow. Automation hooks must not add rows, banners, helper cards, or spacer elements.

### voss-app

- Framework: SolidJS in Tauri.
- Component model: existing hand-rolled components. Do not introduce shadcn/ui or another UI kit.
- Styling source: current CSS variables from Variant B and bundled themes.
- Icons: existing icon approach only. Do not add a new icon package for e2e work.
- Layout: preserve the desktop IDE feel, pane density, titlebar sizing, setup screen, command palette, and protocol pane rhythm.

## Spacing

TUI:

- Spacing is character-cell based and follows the existing Textual layout.
- New test hooks must not change row count, column alignment, scroll behavior, or modal size.
- If a new internal state marker is needed, expose it through an invisible/non-rendering property or test API instead of visible padding or labels.

voss-app:

- Use the existing 4px spacing grid.
- Preserve compact headers: `--titlebar-height`, `--pane-header-height`, and existing pane/header padding.
- Do not add card wrappers around existing panels.
- Do not use hover, focus, or loading states that resize rows, headers, palette items, or protocol entries.

## Typography

TUI:

- Use terminal font behavior. Do not add rich typography, emoji symbols, or new text art.
- Preserve current copy casing and terse command-line tone.

voss-app:

- Preserve the current bundled font stack and token-driven sizes.
- Keep the established minimums from A12/V15: 11px floor for labels and interactive text, with the existing 10px tertiary metadata exception where already established.
- Do not add viewport-scaled type or negative letter spacing.

## Color

TUI:

- Preserve the existing five-color contract from `styles.tcss`: `$accent`, `$dim`, `$good`, `$warn`, and `$error`.
- Do not add new raw hex colors except where the existing TUI files already hardcode the Ignite accent.
- Live, fake, skipped, success, warning, and error states must map to the existing status semantics.

voss-app:

- Use CSS variables only in component code.
- Do not add raw hex colors to Solid components.
- Do not create a new theme for E5.
- Preserve the meaning of focus, role, danger, warning, success, live, and snapshot states.

## Copywriting

Visible product copy must be preserved unless a downstream E5 implementation plan identifies an exact testability gap.

TUI strings to preserve:

- `type a message below to begin · / for commands`
- `[image attached · 1 image]`
- `current model has no vision — image not attached`
- Existing slash-command, diff approval, status, and transcript text.

voss-app strings to preserve:

- `Choose a project`
- `Open a folder or continue without one.`
- `Open layout or recent project`
- `Run command`
- Existing command palette empty-state and setup-window copy.

Automation output copy may be added to tests, CI summaries, or artifacts. It must be operational and explicit, for example `hermetic`, `fake-turn`, `live`, `skipped`, `no credentials`, or `manual workflow`.

## Interaction Contracts

### TUI Pilot Journeys

The Textual Pilot harness must drive real UI interactions:

- Boot the app, focus the prompt, submit a message, observe streamed assistant content, observe finalization, and quit.
- Exercise one edit/diff flow with both approve and reject paths.
- Exercise one slash-command flow, preferring `/cost` or `/models`.
- Assert visible transcript/status state plus internal completion state where needed.

Selectors:

- Prefer existing widget IDs and classes such as `#input`, `#input-textarea`, `#main`, `#status`, and `#header`.
- New IDs/classes are allowed only when tied to a stable semantic element.
- Do not select by fragile generated text if a semantic selector exists.

Live proof:

- Live-model TUI tests must be explicitly marked live and credential gated.
- Live proof must never print secrets, provider tokens, or auth headers.
- Each live journey must have a hermetic stub twin that runs without credentials.

### voss-app E2E Journeys

The E5 manual CI target is to unskip and prove a small, representative subset of existing desktop contracts. The recommended first subset is:

- Command palette.
- Project open/setup path.
- Themes.

Additional contracts may be promoted only when their assertions drive visible DOM, Tauri shell, or protocol state. Empty green tests are forbidden.

Selectors:

- Use existing `data-testid` values where present, such as `command-palette`, `palette-input`, `palette-empty`, `pane-session-title`, and `agent-cost`.
- Add `data-testid`, `data-tauri-e2e`, or `data-e2e-state` only for stable user-observable state.
- Test-only attributes must not affect CSS selectors used for production styling.

Native seams:

- Dialog/project-open seams must be gated by test environment flags and must not change normal user behavior.
- Fake turn serving must be gated by `VOSS_SERVE_FAKE_TURN=1` or an equivalent explicit test variable.
- CI must identify fake/local proof in artifacts and job summaries, not through permanent visible UI chrome.

## Honest Data Rules

- A live indicator can appear only while a real live stream is active.
- Snapshot, fake, and hermetic states must not be presented as live.
- Costs, model names, diff state, and protocol rows must either come from the active client/session state or be absent/dimmed according to the inherited contract.
- Tests must assert the distinction between live and fake/snapshot paths when that state is visible.

## Accessibility and Testability

- Preserve keyboard-first interaction for both surfaces.
- Focus rings, selected rows, modal focus, and palette input focus must remain visible.
- Do not add hidden buttons or invisible click targets solely for automation.
- Prefer deterministic state assertions over screenshots. Screenshots may be artifacts, not primary pass/fail evidence.
- CI artifacts should include test reports and, for desktop e2e, enough log output to diagnose whether Tauri, WebKitWebDriver, or the app service failed.

## Registry Safety

- shadcn/ui: prohibited for E5.
- New npm packages: prohibited unless a downstream plan proves the existing Playwright/Tauri stack cannot drive the required contract.
- New Python packages: prohibited for TUI driving; use Textual Pilot and pytest.
- New visual assets: prohibited.
- New fonts: prohibited.

## Checker Sign-Off

- Visual consistency: PASS. E5 preserves the M9 TUI and A12/V15 desktop contracts.
- Testability: PASS. Stable selectors and test-only seams are allowed with clear limits.
- Scope control: PASS. Redesign, new components, new themes, and new dependencies are out of scope.
- Accessibility: PASS. Keyboard-first flows and visible focus remain required.
- Honest-data safety: PASS. Live, fake, hermetic, skipped, and snapshot states are explicitly separated.
- Registry safety: PASS. shadcn/ui and new visual dependencies are prohibited.

Approved for E5 planning on 2026-06-10.
