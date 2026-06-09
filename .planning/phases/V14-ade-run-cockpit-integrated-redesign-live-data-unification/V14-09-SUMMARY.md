---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 09
subsystem: ui
tags: [solid-js, tauri, modal, model-prefs, pty, appearance-settings]

# Dependency graph
requires:
  - phase: V14-02
    provides: CapabilityTier type + roster/bridge context
  - phase: V14-08
    provides: handleLaunchAgent Bridge-B spawn (extended here for the Terminal preset)
provides:
  - Sparse premium AgentLaunchModal — 6 preset cards (Claude/Codex/Gemini/OpenCode/Aider/Terminal), no raw-command/effort/skip-perm/explainer
  - Real persisted per-CLI default-model source (src/agents/modelPrefs.ts) riding the existing appearance-settings store (one new field, no new Tauri command)
  - Blank Terminal preset spawning a plain shell (kind:'terminal' -> no agentConfig)
  - Honest managed-launch toggle surfacing tier B (agents) / tier C (terminal); no fake tier A, no cred injection
affects: [plan 11 managed-launch enforcement, RunCommandBar coexistence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Persist new app prefs as ONE field on the existing typed AppearanceSettings (TS + Rust struct) — rides existing load/save_appearance_settings, no new command"
    - "Honest model catalog: only hardcode verified-real ids (Claude aliases opus/sonnet/haiku); for other CLIs inject NO --model so a renamed model can't break the PTY launch"
    - "Blank-shell preset = split pane but skip agentConfigByPaneId -> PaneComponent.doSpawn plain branch"

key-files:
  created:
    - apps/voss-app/src/agents/modelPrefs.ts
    - apps/voss-app/src/agents/__tests__/modelPrefs.test.ts
  modified:
    - apps/voss-app/src/components/modal/AgentLaunchModal.tsx
    - apps/voss-app/src/components/modal/modal.css
    - apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx
    - apps/voss-app/src/App.tsx
    - apps/voss-app/src/appearance/types.ts
    - apps/voss-app/src/appearance/settings.ts
    - crates/voss-app-core/src/appearance.rs

key-decisions:
  - "Operator: build a REAL persisted model-prefs source (not hardcoded display) — implemented via one appearance-settings field, no new Tauri command"
  - "Operator: replace 'Custom' with a blank 'Terminal' preset (plain shell; run any CLI yourself)"
  - "Operator: all presets use the LOCAL CLI + local credentials; missing CLI errors naturally in the PTY; managed toggle surfaces tier B honestly (enforcement = plan 11)"
  - "Operator: pane placement surfaced in config only; App honoring it is a later follow-up"
  - "Only Claude model aliases (opus/sonnet/haiku) hardcoded as verified-real; codex/gemini/opencode/aider omit --model by default"

patterns-established:
  - "Sparse premium modal (D-09): preset cards, no raw-command escape hatch, no explainer paragraphs"
  - "Model-prefs honesty: verified-real vs advisory-override per CLI"

requirements-completed: [VCKP-11]

# Metrics
duration: 25min
completed: 2026-06-09
---

# Phase V14-09: Sparse Quick-Launch Modal + Real Model-Prefs Summary

**AgentLaunchModal refactored to sparse premium preset cards (Claude/Codex/Gemini/OpenCode/Aider/Terminal) backed by a real persisted per-CLI default-model source; raw-command + effort + skip-permissions + explainer removed; blank Terminal preset spawns a plain shell; managed toggle surfaces tier B honestly with no fake tier-A or credential injection.**

## Performance

- **Duration:** ~25 min (workflow: 4 agents — research/implement/test/verify — 24.9 min wall, 454k subagent tokens)
- **Completed:** 2026-06-09
- **Tasks:** 2 planned (+ operator-driven scope expansion; research phase)
- **Files modified:** 9 (2 created, 7 modified) — vs the plan's 2-file scope (see Deviations)

## Accomplishments
- **Sparse modal (D-09):** 6 preset cards; removed the raw-command Custom field, the `CLI_PROFILES` effort/reasoning matrices, the Skip-Permissions toggle + explainer, the interactive-mode placeholder, and the Voss panel (native runs → RunCommandBar, D-04). Kept the scaffold (backdrop/Esc/⌘↵/focus, segmented controls). Added an optional "what should it work on?" prompt, a working-dir input, Right/Below/New-tab placement, and a managed-launch toggle.
- **Real persisted model-prefs:** new `src/agents/modelPrefs.ts` holds the per-CLI catalog + default; persistence rides the **existing** appearance-settings store via one new field `cliDefaultModels` (Rust `appearance.rs` struct + TS `types.ts` + `settings.ts` parser) — **no new Tauri command, no new handler**. Selecting a model persists via the existing `save_appearance_settings`.
- **Model honesty:** only Claude aliases (`opus`/`sonnet`/`haiku`) are hardcoded as verified-real (default `sonnet`). Codex/Gemini/OpenCode/Aider inject **no** `--model` by default (local CLI uses its own default; a renamed model can't break the launch) and expose an optional override — matching the operator decision that Voss injects nothing.
- **Blank Terminal preset:** `kind:'terminal'` → App.handleLaunchAgent splits a pane but leaves `agentConfigByPaneId` unset → PaneComponent.doSpawn takes the plain `transport.spawn()` branch = bare login shell. Correctly excluded from the agent roster (re-detected if a known CLI is typed into it).
- **Tier surface:** managed toggle (default off) with honesty copy ("External agent — uses your local CLI & credentials; advisory scope; full management arrives later"). Agents emit tier **B**, Terminal tier **C**. No fake tier A; no enforcement (plan 11).
- **Bonus fix:** corrected the roster model-label parser (App.tsx) — see Deviations #3.
- **Verification:** adversarial agent pass, 9/9 checks, 0 blocking issues.

## Task Commits

Auto-committed during the session across several commits:

1. **modelPrefs catalog + persistence** — `52ea694` (feat)
2. **appearance cliDefaultModels field (Rust + TS)** — `255235e` (feat)
3. **AgentLaunchModal sparse refactor** — `4584c51` (feat)
4. **App.tsx preset/terminal migration** — `68a1d30` (refactor)
5. **roster model-label parser fix** — uncommitted at time of writing (see Deviations #3)

## Files Created/Modified
- `apps/voss-app/src/agents/modelPrefs.ts` *(new)* — per-CLI catalog (Claude verified-real; others omit `--model`) + load/save via appearance store.
- `apps/voss-app/src/agents/__tests__/modelPrefs.test.ts` *(new)* — 11 cases (catalog honesty, defaults, round-trip, persistence call shape, hydration).
- `apps/voss-app/src/components/modal/AgentLaunchModal.tsx` — sparse preset refactor.
- `apps/voss-app/src/components/modal/modal.css` — preset-card classes (token-only).
- `apps/voss-app/src/components/modal/__tests__/AgentLaunchModal.test.tsx` — rewritten (22 cases); old Voss/Antigravity/Custom-tab assertions removed.
- `apps/voss-app/src/App.tsx` — `handleLaunchAgent` widened for `kind:'terminal'` plain-shell branch + config fields; roster model-label parser fix.
- `apps/voss-app/src/appearance/types.ts` + `settings.ts` — `cliDefaultModels` field + validator.
- `crates/voss-app-core/src/appearance.rs` — `cli_default_models` struct field + Default.

## Decisions Made
See key-decisions frontmatter. The consequential ones were surfaced to and chosen by the operator before execution (real model-prefs source; Custom→Terminal; local-cred/error-if-missing; placement config-only).

## Deviations from Plan

The plan's `files_modified` listed only the modal + its test. The operator's answers to four scoping questions expanded this into a multi-surface build. All expansions were **operator-approved before execution**.

**1. Real persisted model-prefs source (operator: "build a real model-prefs source")**
- **Issue:** no per-CLI default-model store existed in voss-app; `profiles.ts` is appearance/theme only.
- **Fix:** new `src/agents/modelPrefs.ts` + one field (`cliDefaultModels`) on the existing AppearanceSettings (Rust `appearance.rs` + TS `types.ts`/`settings.ts`). Chose the lowest-friction REAL path — rides existing `load/save_appearance_settings`, **no new Tauri command**. `cargo check` clean.
- **Files beyond plan:** `modelPrefs.ts`, `appearance.rs`, `types.ts`, `settings.ts`.

**2. Blank Terminal preset (operator: replace Custom with a blank terminal) + tier/cred behavior**
- **Fix:** `kind:'terminal'` early-return in `handleLaunchAgent` (App.tsx) → plain shell; managed toggle tier-B/C honesty copy; no `--model` injection for non-Claude CLIs.
- **Files beyond plan:** `App.tsx`, `modal.css`.

**3. Roster model-label parser fix (correctness, mine — not the workflow's)**
- **Found during:** verification.
- **Issue:** `App.tsx` parsed the sidebar model label via `cliArgs.find(a=>a.startsWith('--model'))?.split('=')[1]`, but `--model` and its value are separate array elements → label always rendered `'default'`. Pre-existing (the old modal also emitted separate elements), but it is the display for the exact agents this plan launches.
- **Fix:** parse both `--model value` and `--model=value` forms. One self-contained expression; tsc + 244 tests green after.

---
**Total deviations:** 3 (2 operator-approved scope expansions, 1 correctness fix). **Impact:** necessary to deliver the operator's intent honestly; no fabricated model ids or fake capability claims. `placement`/`managed`/`tier` are surfaced-only (enforcement + placement-honoring are documented follow-ups / plan 11).

## Issues Encountered
- **Roster section label (non-blocking):** the plan's wording says agents appear under a section literally named "External Terminal Agents"; the actual `AgentSidebar` header is "AGENTS". The mechanism is genuinely present (config `kind:'agent'` + known `cliBinary` → `agentConfigByPaneId` → `agentListForSidebar` Source-1 filter `isKnownAgentCli`), so launched preset agents do appear in the roster; only the header string differs from the plan text. Left as-is (label wording is a copy decision, not in `files_modified`).

## Verification
- `npx tsc --noEmit` — clean.
- `npx vitest run src/__tests__ src/org src/components src/agents src/appearance` — **244 passed (33 files)** (full workflow sweep reported 660/660 across 73 files).
- `cargo check` (src-tauri) — clean (the one new Rust field).
- modal grep — no raw-command / Skip-Permissions / explainer / interactive-placeholder remnants.
- Adversarial verify — pass, 9/9 checks, 0 blocking.

## Next Phase Readiness
- Managed-launch tier-B surface is in place for plan 11 to wire real Rust enforcement.
- `placement` is in the launch config; App honoring right/below/newtab is a small follow-up on `handleLaunchAgent`.
- `modelPrefs` catalog can gain verified ids for codex/gemini/opencode/aider as they're confirmed, without touching persistence.

---
*Phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification*
*Completed: 2026-06-09*
