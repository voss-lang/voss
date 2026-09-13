# Phase A1: voss-app Tauri Shell - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

A1 delivers an **empty Tauri + Solid desktop window that builds and runs locally on macOS** (the dev's platform), with a fully custom titlebar, the complete Variant B theme-token system applied, and a minimal config-file theme override. It is pure window scaffolding.

**In scope:** Tauri shell + Solid/Tailwind UI scaffold, Variant B token system, custom window decorations (mac), custom-control abstraction for linux/win, project-name placeholder + visual-only layout-preset switcher in titlebar, `pnpm tauri dev` run + unsigned `pnpm tauri build` local smoke artifact, "Voss ADE" ship-name strings, minimal `~/.config/voss-app/settings.json` theme read, monorepo/workspace bootstrap (pnpm + Cargo member).

**Out of scope (hard boundaries):** No xterm, no PTY, no grid, no panes (A2/A3). No release pipeline / signing / channels / auto-update / version-sync (→ A10). No settings UI (→ A8). No cost-meter slot (Q6, removed from L1). No Voss/agent/`.voss` code or UI strings. No JSONL IPC. linux/win window-control *rendering verification* deferred (abstraction built now).

</domain>

<decisions>
## Implementation Decisions

### Theme Token Architecture
- **D-01:** CSS custom properties are the single source of truth. Tokens defined as `--…` vars (e.g. `:root` in a `variant-b.css`). `tailwind.config` `theme.extend` references `var(--…)`. Components use Tailwind utility classes only — no raw values, no token indirection in component code. This makes themes runtime-swappable with **zero rebuild** (directly enables success criterion 2).
- **D-02:** A1 ships the **full Variant B token taxonomy**, not a minimal palette: color (bg / surface / border / fg / muted / accent), typography (mono font stack, 22px header size, body + line metrics), border/radius (1px borders, 0 radius), focus (inset-shadow ring), glyph chars (`❯` user prefix, `⏵` output prefix). Token *values* sourced from sketch 001 Variant B (`index.html`). A2–A9 **consume** these tokens; they must never re-define or re-litigate the locked aesthetic.

### Window Decoration Strategy
- **D-03:** `decorations: false` on **all** platforms. Custom titlebar + window controls everywhere: reimplement the macOS traffic-light cluster and provide custom close/min/max on linux/win. Goal = pixel-identical chrome cross-platform (consistent with Variant B "mono everywhere, thin-border" ethos). Trade-off accepted: voss-app owns window-control behavior (hover, fullscreen affordance) on mac.
- **D-04:** A1 implements and **verifies macOS fully**. Build a **platform-control abstraction** so linux/win is a fill-in, not a rewrite. linux/win control *rendering* is stubbed in A1 and completed when those become real test targets (A10 soak / CI). Keeps A1 a true scaffold; success criterion is "launches on the dev's platform" (macOS).

### Workspace / Monorepo Bootstrap
- **D-05:** Add `crates/voss-app-core` to the **existing root `Cargo.toml` `[workspace].members`**. "Frozen-spike" (STATE.md) is interpreted as *do not edit the spike crates' source*; adding a new sibling member + new crate directory does not touch frozen code. One workspace, shared lockfile + target dir. Matches CONCEPT §8 ("extend existing Cargo workspace") literally.
- **D-06:** Full JS/workspace wiring in A1: create root `pnpm-workspace.yaml` + root `package.json`; `apps/voss-app` is a pnpm workspace member. `crates/voss-app-core` is created with an **empty `lib.rs`** (placeholder comment, compiles clean). `apps/voss-app/src-tauri` declares the `voss-app-core` **path dependency now** (wired but unused) so A2 only fills the crate body. Matches roadmap "consuming `crates/voss-app-core` (created empty here)".
- **D-07:** Tauri version = Claude/researcher discretion: **latest stable Tauri 2.x**, pinned. SHL-01 says "2.x recommended; SPEC confirms" — researcher confirms the exact pin (no SPEC.md exists yet for A1).

### Config Read for Theme Swap
- **D-08:** Minimal config read. On boot, read `~/.config/voss-app/settings.json` if it exists; consume **only** an optional `theme` object (CSS-var overrides) merged over baked Variant B defaults. Absent file → pure Variant B. No write, no schema validation, no settings UI in A1 (~30 LOC). A8 builds the full settings system on this seam.
- **D-09:** Read seam: **Rust/Tauri side** reads + parses `settings.json` at startup and exposes it to the webview via a Tauri command/state. Solid reads the `theme` object once on mount and sets the `--…` vars on `:root`. File I/O stays in Rust (where A8's settings system will live); the webview stays sandboxed. Clean A1→A8 seam.

### Claude's Discretion
- Exact Tauri 2.x patch pin (D-07), researcher to confirm against current stable.
- `voss-app-core` placeholder content wording, crate metadata (edition/rust-version inherit workspace).
- Solid project tooling specifics (Vite template, TS config) within "Solid + Tailwind" lock.
- Token naming convention for CSS vars (follow a consistent documented scheme).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Concept & Locked Decisions (authority — supersedes assumptions)
- `apps/voss-app/CONCEPT.md` — full concept. **§6 Locked Decisions (cross-layer)** (Tauri / Solid / Tailwind / xterm / portable-pty / monorepo path / build = pnpm workspace + Cargo workspace) and **§10 Decisions Log closed 2026-05-16** (Q1 ship name "Voss ADE"; Q6 cost meter hidden in L1; Q8 release → A10; Q9 telemetry off) are LOCKED — do not re-litigate. **§8 Monorepo Layout** is the directory contract. **§2 v0 scope** + **§9 build order** define A1 boundary.
- `apps/voss-app/FEATURES.md` — feature catalog mapped to L1/L2/L3 (read for A1 L1 feature membership; not yet inspected in discussion — researcher should read).

### Requirements
- `.planning/ROADMAP.md` "### Phase A1: voss-app Tauri Shell" (~line 1025) — SHL-01..SHL-06 requirement list + proposed success criteria + cross-cutting constraints.
- `.planning/ROADMAP.md` "## A-prefixed phases: voss-app Desktop ADE" preamble (~line 1004) — A-track layering, cross-A constraints, Variant B token sharing rule, project-wide closed questions pointer.
- No `A1-SPEC.md` exists. Requirements are roadmap-listed + CONCEPT-locked, not SPEC-locked. (Optionally run `/gsd:spec-phase A1` before planning if tighter requirement locking is wanted.)

### Reference Design (locked aesthetic — token value source)
- `.planning/sketches/001-voss-grid-shell/README.md` — Variant B = winner ("Minimal Tile": tmux density, thin 1px borders, no rounding, 22px headers, glyph prefixes).
- `.planning/sketches/001-voss-grid-shell/index.html` — extract Variant B token *values* (colors, type sizes, focus shadow) for D-02. L1 panes = same chrome minus agent-HUD elements (no model/iter/cost).

### Existing Code (context, mostly untouched in A1)
- `Cargo.toml` (root) — existing `[workspace]` with 7 frozen-spike crates; D-05 adds `crates/voss-app-core` as a new member here.
- `voss/harness/...` — Python harness, **untouched in L1** (integrated only at L2).
- `crates/` (voss-cli, voss-agent, voss-providers, voss-auth, voss-tools, voss-render, voss-bridge) — frozen Rust spike, reference-only for PTY/IPC choices when L2 starts; **do not edit source**.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **None for UI** — `apps/voss-app/` contains only `CONCEPT.md` + `FEATURES.md`. No Solid/Tauri/Tailwind code exists yet. A1 is greenfield within `apps/voss-app/`.
- Root **Cargo workspace** already exists (`resolver = "2"`, `[workspace.package]` version 0.1.0 / edition 2021 / rust-version 1.75) — `voss-app-core` should inherit workspace package metadata.

### Established Patterns
- Frozen Rust spike crates are kept in source control but off the v0.1 ship path (STATE.md: "do not edit. Resurrect on dogfood signal only"). A1 adds alongside, never modifies them.
- No root `package.json` / `pnpm-workspace.yaml` yet — A1 introduces the JS monorepo root (D-06).
- `~/.config/voss-app/` does not exist on the dev machine — absent-file path (pure Variant B fallback) is the default boot path to verify (D-08).

### Integration Points
- Root `Cargo.toml` `[workspace].members` — add `crates/voss-app-core` (D-05).
- New: root `pnpm-workspace.yaml` + root `package.json` → `apps/voss-app` member (D-06).
- `apps/voss-app/src-tauri` → path-dependency on `crates/voss-app-core` (D-06).
- Tauri command/state boundary → Solid mount-time CSS-var application (D-09).

</code_context>

<specifics>
## Specific Ideas

- Aesthetic is **not** open: Variant B from sketch 001 verbatim — 22px headers, 1px borders, no radius, mono everywhere, `❯`/`⏵` glyph prefixes, inset-shadow focus. Pull values from `sketch 001 index.html`.
- Competitor bar: Wezterm + grid (fast, config-driven) is the closest reference; the window must feel like a power-user terminal shell, not a chat/editor app, even while empty.
- Branding: "**Voss ADE**" is the user-facing string everywhere it appears in A1 (window title, About). `voss-app` stays internal slug only (repo dir, package name).
- `.voss/` is **not** created or referenced by A1 (lazy creation, Q7 — first relevant in A5).

</specifics>

<deferred>
## Deferred Ideas

- **linux/win custom window-control rendering + verification** — abstraction built in A1 (D-04), concrete linux/win rendering + manual verification deferred until those are real test targets (A10 24hr soak / CI matrix).
- **⚠ Cross-phase action, not deferrable — flag for researcher/planner:** Code-signing **cert procurement (REL-02:** macOS Developer ID + notarization, Windows Authenticode) is the release long-pole. CONCEPT §10 Q8 + scope alerts say *start procurement during A1* even though all signing/channel/version-sync **wiring lands in A10**. A1 builds no release pipeline, but the human cert-procurement clock should start now. Surface this as a human-action note in the A1 plan.
- **Full settings system** (font / shell / keymap / theme UI, typed loader, validation) → A8. A1 only lays the Rust-side read seam (D-09).
- **Layout-preset switcher behavior** — A1 titlebar shows it visually only (no behavior); pure-visual templates in L1 (Q4), real geometry in A4, semantics at L2.

</deferred>

---

*Phase: A1-voss-app-tauri-shell*
*Context gathered: 2026-05-17*
