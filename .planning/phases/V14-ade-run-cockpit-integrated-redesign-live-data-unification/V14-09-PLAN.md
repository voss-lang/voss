---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 09
type: execute
wave: 6
depends_on: ["V14-02"]
files_modified:
  - apps/voss-app/src/components/modal/AgentLaunchModal.tsx
  - apps/voss-app/src/components/modal/__tests__/agentLaunchModal.test.tsx
autonomous: true
requirements: [VCKP-11]
must_haves:
  truths:
    - "Launching from a preset spawns a PTY terminal agent in the chosen pane placement using the preset's resolved command (default model)"
    - "The modal exposes NO raw-command field and NO explainer paragraph (D-09)"
    - "Cmd+Enter launches; Esc/Cancel dismisses without spawning"
    - "The spawned agent appears under 'External Terminal Agents' in the roster"
    - "A managed-launch toggle surfaces capability tier A/B/C honestly (the Rust enforcement lands in plan 11; this is the UI surface)"
  artifacts:
    - path: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      provides: "Refactored sparse preset-card quick-launch modal"
      contains: "preset"
  key_links:
    - from: "apps/voss-app/src/components/modal/AgentLaunchModal.tsx"
      to: "apps/voss-app/src/pane/pty-ipc.ts"
      via: "preset spawn via spawnAgent"
      pattern: "spawnAgent|onLaunch"
---

<objective>
VCKP-11 (D-09): refactor `AgentLaunchModal` from config-heavy to sparse/premium. CLI preset cards (Claude/Codex/Gemini/OpenCode/Aider/Custom) each showing the user's default model, one optional "what should it work on?" prompt, working dir + pane placement (Right/Below/New tab). Remove the raw-command field and the explainer block. Add a managed-launch toggle that surfaces capability tier A/B/C (the actual enforcement is plan 11; this plan is the UI surface). Quick-Launch coexists with RunCommandBar (D-04).

Purpose: Sparse premium launch for ad-hoc terminal agents (Path 1, no cage).
Output: refactored modal, extended modal test.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-SPEC.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md

<interfaces>
From apps/voss-app/src/components/modal/AgentLaunchModal.tsx: KEEP scaffold — backdrop click-out (:158-162), Esc + ⌘↵ keymap (:164-173), focus-first-on-mount (:94-97), `modal-segmented` controls, `CLI_TABS` (:7-14), `binaryMap` idea (:124-129). REMOVE — raw-command Custom field (:336-356), effort/reasoning matrices (`CLI_PROFILES` :24-50, :233-250), Skip-Permissions toggle + explainer, task `<textarea>` placeholder explainer (:273). `onLaunch(buildConfig())` is the spawn callback (:155).
From apps/voss-app/src/components/modal/__tests__/agentLaunchModal.test.tsx: existing tests to extend.
Capability tier type `CapabilityTier = 'A'|'B'|'C'` from normalized.ts (plan 00/01).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Refactor modal to sparse preset cards (drop raw-command + explainer)</name>
  <files>apps/voss-app/src/components/modal/AgentLaunchModal.tsx</files>
  <read_first>
    - apps/voss-app/src/components/modal/AgentLaunchModal.tsx (the file — refactor in place; KEEP/REMOVE/ADD lists)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (AgentLaunchModal refactor pattern: exact KEEP/REMOVE/ADD line refs)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-CONTEXT.md (D-09 sparse modal, D-13 tier surface)
  </read_first>
  <action>
    Refactor `AgentLaunchModal.tsx`: KEEP the modal scaffold (backdrop/Esc/⌘↵/focus, segmented control, CLI list). REMOVE the raw-command Custom field, the effort/reasoning matrices, the Skip-Permissions toggle + explainer copy, and the task-textarea explainer placeholder (D-09). ADD CLI preset cards each showing the user's default model (e.g. "Claude Code · sonnet-4-6") resolved via the existing `binaryMap` idea, one optional "what should it work on?" prompt, working-dir input, and pane placement (Right/Below/New tab). ADD a managed-launch toggle that displays the capability tier A/B/C for the selected CLI (non-hook CLI → B; hook-capable → A; the toggle's actual Rust enforcement is plan 11 — here, surface the tier label honestly and pass a `managed: boolean` + `tier` field in the launch config). `buildConfig()` now returns `{cliBinary, cliArgs (resolved from preset+model), taskPrompt, placement, managed, tier}`.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | grep -E "AgentLaunchModal" || echo "clean" ; grep -n "raw-command\|Skip.Permissions\|explainer" src/components/modal/AgentLaunchModal.tsx && echo "FAIL remnant" || echo "stripped"</automated>
  </verify>
  <acceptance_criteria>
    - Modal renders preset cards with default model + pane placement; no raw-command field, no explainer paragraph (grep returns nothing).
    - `buildConfig` returns the resolved preset command + placement + managed/tier fields.
    - Scaffold (Esc/⌘↵/backdrop/focus) preserved.
  </acceptance_criteria>
  <done>Sparse premium preset modal; raw-command + explainer removed; tier surfaced.</done>
</task>

<task type="auto">
  <name>Task 2: Modal test — preset spawn, no raw-command, keymaps, roster placement</name>
  <files>apps/voss-app/src/components/modal/__tests__/agentLaunchModal.test.tsx</files>
  <read_first>
    - apps/voss-app/src/components/modal/__tests__/agentLaunchModal.test.tsx (existing tests to extend)
    - apps/voss-app/src/components/modal/AgentLaunchModal.tsx (task 1 — unit under test)
  </read_first>
  <action>
    Extend `agentLaunchModal.test.tsx`: assert launching from a preset calls `onLaunch` with the preset's resolved command + chosen pane placement; assert there is NO raw-command input and NO explainer paragraph in the rendered DOM; assert ⌘↵ triggers launch and Esc/Cancel dismisses WITHOUT calling `onLaunch`; assert the launched agent's config marks it for the "External Terminal Agents" roster section. Assert the managed-launch toggle shows tier B for a non-hook CLI (no per-tool promise, no error).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/components/modal/__tests__/agentLaunchModal.test.tsx</automated>
  </verify>
  <acceptance_criteria>
    - Preset launch calls onLaunch with resolved command + placement.
    - No raw-command field, no explainer paragraph in the DOM.
    - ⌘↵ launches; Esc/Cancel does not spawn.
    - Managed toggle shows tier B for a non-hook CLI without error.
  </acceptance_criteria>
  <done>Modal behavior verified per VCKP-11 acceptance.</done>
</task>

</tasks>

<verification>
- `npx vitest run src/components/modal` green; `npx tsc --noEmit` clean.
- Quick-Launch coexists with RunCommandBar (D-04 — not removed).
</verification>

<success_criteria>
Sparse preset quick-launch modal spawns a PTY agent from a default-model preset with no raw-command/explainer; ⌘↵/Esc behave; tier surfaced honestly.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-09-SUMMARY.md` when done.
</output>
