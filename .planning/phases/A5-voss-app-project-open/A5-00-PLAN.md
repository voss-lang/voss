---
phase: A5-voss-app-project-open
plan: 00
type: execute
wave: 0
depends_on: [A4-05]
files_modified:
  - Cargo.toml
autonomous: false
requirements: [WS-01, WS-02, WS-03, WS-04, WS-05, WS-06, WS-07]
must_haves:
  truths:
    - "A5 does not start until A4-04 layout persistence + A4-05 acceptance are merged and green"
    - "Workspace MSRV is high enough to build tauri-plugin-dialog 2.4.2 (>=1.77.2)"
    - "A3-06 grid integration is mounted; A4-04 callable layout seam exists in App.tsx"
    - "Existing layout tests (cargo + vitest) still green before A5 touches anything"
  artifacts:
    - path: "Cargo.toml"
      provides: "Workspace rust-version sufficient for tauri-plugin-dialog 2.4.2"
      contains: "rust-version"
    - path: "apps/voss-app/src/App.tsx"
      provides: "A4-04 callable layout seam (saveCurrentLayout, loadLayoutByName, applyDefaultLayout) already wired"
      contains: "applyDefaultLayout"
    - path: "crates/voss-app-core/src/layouts.rs"
      provides: "A4-03 lazy .voss/ + LayoutError UI-string pattern A5's ProjectError must mirror"
      contains: "LayoutError"
---

<objective>
Block A5 execution until (a) the A4 substrate is fully merged and green, and (b) the workspace MSRV is high enough to build `tauri-plugin-dialog` 2.4.2. This plan never edits A5 code; it gates the wave.

Purpose: A5's Rust core (A5-01) depends on the A4-03 lazy `.voss/` rule and `LayoutError` UI-string pattern. A5's frontend (A5-05) depends on the A4-04 callable `applyDefaultLayout` seam in `App.tsx`. A5's `tauri-plugin-dialog` requires Rust >=1.77.2 (RESEARCH Pitfall 7 / Q1), but the workspace is currently pinned at `rust-version = "1.75"`. If we add the plugin before fixing MSRV, `cargo build` breaks before any test can run.
Output: A substrate checklist signed off by the human; MSRV bumped to `1.77.2` if required.
</objective>

<context>
@.planning/phases/A5-voss-app-project-open/A5-SPEC.md
@.planning/phases/A5-voss-app-project-open/A5-CONTEXT.md
@.planning/phases/A5-voss-app-project-open/A5-RESEARCH.md
@.planning/phases/A5-voss-app-project-open/A5-PATTERNS.md
@.planning/phases/A4-voss-app-layout-presets/A4-04-PLAN.md
@.planning/phases/A4-voss-app-layout-presets/A4-05-PLAN.md
@Cargo.toml
@apps/voss-app/src/App.tsx
@apps/voss-app/src-tauri/src/lib.rs
@crates/voss-app-core/src/layouts.rs
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Build toolchain | rustc MSRV vs. plugin MSRV — mismatch breaks downstream waves silently if not caught first |
| Prior-phase substrate | A4-04 frontend layout seam is the integration target for D-12; without it the project-open default-layout hook has nowhere to call |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A5-00-MSRV | Tampering (build env drift) | workspace Cargo.toml `rust-version` | mitigate | Bump to `1.77.2` before A5-01 lands so `cargo add tauri-plugin-dialog@^2` cannot poison `cargo build` for downstream waves |
| T-A5-00-A4 | Repudiation (carry-forward) | A4-04 / A4-05 callable seam | mitigate | Block on grep evidence (`applyDefaultLayout` closure present in App.tsx, `load_default_layout` registered in lib.rs) before A5-01 starts |
| T-A5-00-PKG | Tampering (supply chain) | tauri-plugin-dialog, @tauri-apps/plugin-dialog, git2 | accept | A5-RESEARCH Package Legitimacy Audit ran 2026-05-19, all three [OK]; checkpoint surfaces audit lines for human re-confirmation before installs (A5-01 / A5-02). No `[SLOP]` / `[SUS]` packages — no separate package gate task required. |
</threat_model>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Verify A4 substrate green, bump workspace MSRV if needed, and re-confirm A5 package audit</name>
  <files>Cargo.toml</files>
  <read_first>
    - Cargo.toml — workspace `rust-version` line (currently `1.75`)
    - .planning/phases/A4-voss-app-layout-presets/A4-05-PLAN.md — A4 acceptance gates
    - apps/voss-app/src/App.tsx — A4-04 `saveCurrentLayout` / `loadLayoutByName` / `applyDefaultLayout` closures
    - apps/voss-app/src-tauri/src/lib.rs — A4-03 `save_layout` / `load_layout` / `load_default_layout` / `list_layouts` registered in `tauri::generate_handler!`
    - crates/voss-app-core/src/layouts.rs — A4-03 `LayoutError` UI-string pattern (A5's `ProjectError` must mirror it byte-for-byte for the future A11 setup-error UI)
    - .planning/phases/A5-voss-app-project-open/A5-RESEARCH.md `## Package Legitimacy Audit` — 3 packages slopchecked 2026-05-19 (`tauri-plugin-dialog`, `@tauri-apps/plugin-dialog`, `git2`); all `[OK]`. The MEMORY note `gsd-scaffold-fictional-api` is the cross-check: every API surface A5-01..A5-05 will call must trace to a doc.rs/v2.tauri.app citation in RESEARCH §Sources, not to invention.
  </read_first>
  <action>
    Walk the substrate gate before any A5 code wave fires:

    1. **A4 green:** Confirm `.planning/phases/A4-voss-app-layout-presets/A4-05-SUMMARY.md` exists and shows A4-05 completed (the `A4_FULL_GREEN` tag in its verify output). If A4-05 is not green, stop and run `/gsd:execute-phase A4` first.

    2. **A4-04 callable seam present:** Confirm `apps/voss-app/src/App.tsx` defines an `applyDefaultLayout(workspacePath)` closure (D-12's call site) AND that `saveCurrentLayout` / `loadLayoutByName` are still referenced (the A4-04 unused-suppression `void` lines must not have been collapsed away during A4 cleanup). A5-05 will REMOVE the `void applyDefaultLayout;` line but must keep `void saveCurrentLayout;` and `void loadLayoutByName;` per PATTERNS Landmine #2.

    3. **A4-03 Rust seam present:** Confirm `apps/voss-app/src-tauri/src/lib.rs` registers `save_layout`, `load_layout`, `list_layouts`, `load_default_layout` in `tauri::generate_handler!` and that `LayoutError` Display strings live in `crates/voss-app-core/src/layouts.rs`.

    4. **MSRV check:** Read the workspace `[workspace.package]` `rust-version` value in `Cargo.toml`. Per A5-RESEARCH Pitfall 7 + Open Question Q1, `tauri-plugin-dialog` 2.4.2 requires Rust >=1.77.2. If the floor is `1.75` (current state at planning time), bump it to `"1.77.2"` and run `cargo check --workspace` to confirm the toolchain on the dev machine can satisfy the new floor. Do not bump higher than necessary; do not change anything else in `Cargo.toml`.

    5. **Package audit re-confirm:** Read A5-RESEARCH §Package Legitimacy Audit. All three packages must remain `[OK]`. No package is `[ASSUMED]` or `[SUS]` at this audit time, so no separate `<task gate="blocking-human">` is required before A5-01 / A5-02 installs — but if the audit drifts in the future (e.g. researcher re-runs and one slips to `[ASSUMED]`), a `gate="blocking-human"` checkpoint MUST be inserted before installs.

    6. **Baseline green:** Run `cargo test -p voss-app-core --quiet` and `pnpm --dir apps/voss-app test -- --run` once to capture a pre-A5 baseline. Record the test counts in the A5-00 checkpoint resume notes.

    Resume signal: "approved — A4 substrate green, MSRV=1.77.2 (or unchanged), packages still [OK], baselines captured" or describe the failing gate.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && test -f .planning/phases/A4-voss-app-layout-presets/A4-05-SUMMARY.md && grep -q 'applyDefaultLayout' apps/voss-app/src/App.tsx && grep -q 'load_default_layout' apps/voss-app/src-tauri/src/lib.rs && grep -q 'LayoutError' crates/voss-app-core/src/layouts.rs && awk -F'"' '/^rust-version[[:space:]]*=/{print $2; found=1} END{exit found?0:1}' Cargo.toml | awk -F'.' '{ if (($1*100 + $2) >= 177) exit 0; else exit 1 }' && cargo check --workspace --quiet 2>&1 | tail -5 && cargo test -p voss-app-core --quiet 2>&1 | tail -3 && echo A5_SUBSTRATE_READY</automated>
  </verify>
  <acceptance_criteria>
    - `A5_SUBSTRATE_READY` prints from the automated command.
    - `Cargo.toml` workspace `rust-version` is >= `1.77.2` (numeric comparison, not string).
    - `cargo check --workspace` exits 0 after any MSRV bump.
    - `cargo test -p voss-app-core` exits 0 (pre-A5 baseline).
    - `applyDefaultLayout` appears in `apps/voss-app/src/App.tsx` (A4-04 seam intact).
    - `load_default_layout` is registered in `apps/voss-app/src-tauri/src/lib.rs` (A4-03 seam intact).
    - `LayoutError` is defined in `crates/voss-app-core/src/layouts.rs` (UI-string pattern A5 will mirror).
    - A5-RESEARCH Package Legitimacy Audit reviewed and all three new packages still `[OK]`.
  </acceptance_criteria>
  <done>A5 substrate is verified, MSRV is sufficient, baselines are captured, and A5-01 can land Rust dependency additions without breaking the workspace build.</done>
</task>

</tasks>

<verification>
Run the task verify command. Continue to A5-01 only if it prints `A5_SUBSTRATE_READY`. If the MSRV bump is the only edit, commit it on the A5 branch as `chore(A5-00): bump workspace MSRV to 1.77.2 for tauri-plugin-dialog`.
</verification>

<success_criteria>
- A5 does not proceed on an unmounted grid, an absent A4-04 seam, or a pre-1.77 toolchain.
- The MSRV bump (if required) is the smallest possible Cargo.toml change.
- The package legitimacy audit is re-affirmed in writing before any `cargo add` or `pnpm add` runs in later waves.
</success_criteria>

<output>
Create `.planning/phases/A5-voss-app-project-open/A5-00-SUMMARY.md` recording: A4-05 green status, MSRV before/after, baseline test counts, package audit confirmation timestamp.
</output>
