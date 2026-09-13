# Phase A1: voss-app Tauri Shell - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** A1-voss-app Tauri Shell
**Areas discussed:** Theme token architecture, Window decoration strategy, Workspace bootstrap scope, Config read scope for theme swap

---

## Pre-discussion: ROADMAP parser blocker (resolved)

A-phase detail headings used em-dash (`### Phase A1 — name`); GSD roadmap parser requires colon (`### Phase A1: name`). New phases with no `.planning/phases/` dir resolve only via the roadmap parser → A1 was undetectable (`phase_found:false`). User chose **Fix all A1–A10** (vs A1-only / abort). All ten detail headings normalized to colon, committed `14c7f6c`. Phase then resolved cleanly.

---

## Theme Token Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| CSS vars + Tailwind reads them | CSS custom properties on :root; tailwind theme.extend → var(--…); runtime-swappable, no rebuild | ✓ |
| Typed TS token module | tokens.ts typed object; Tailwind imports; runtime apply layer needed | |
| Tailwind config sole source | Theme only in tailwind.config; swap needs recompile | |

**User's choice:** CSS vars + Tailwind reads them (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Full Variant B taxonomy | Complete token set in A1 (color/type/border/focus/glyphs); later phases consume only | ✓ |
| Minimal palette only | bg/fg + mono now; expand per-phase | |
| Mirror sketch 001 exactly | 1:1 extract from index.html, no curation | |

**User's choice:** Full Variant B taxonomy (Recommended)
**Notes:** Token *values* still sourced from sketch 001 index.html; "full taxonomy" = curated complete set, not raw dump.

---

## Window Decoration Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| macOS overlay + native elsewhere | mac titleBarStyle Overlay keeps native traffic lights; linux/win decorations:false custom | |
| Fully custom all platforms | decorations:false everywhere; reimplement mac traffic lights + linux/win controls | ✓ |
| Native decorations + content titlebar | Keep OS decorations; project-name/preset in content strip | |

**User's choice:** Fully custom all platforms

| Option | Description | Selected |
|--------|-------------|----------|
| macOS fully, linux/win deferred | mac impl+verified; control abstraction built; linux/win stubbed until test targets | ✓ |
| All three platforms in A1 | impl+verify mac/linux/win now | |
| macOS only, no abstraction | hardcode mac; ignore linux/win until later phase | |

**User's choice:** macOS fully, linux/win deferred (Recommended)

---

## Workspace Bootstrap Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Add member to root workspace | Add crates/voss-app-core to existing root Cargo.toml members; frozen = no spike-source edits | ✓ |
| Separate workspace under apps/voss-app | Isolated Cargo workspace; root untouched; diverges from CONCEPT §8 | |
| Defer voss-app-core entirely | A1 = src-tauri standalone; core created in A2 | |

**User's choice:** Add member to root workspace (Recommended)
**Notes:** Tension surfaced explicitly — CONCEPT §8 "extend existing workspace" vs STATE.md "crates/ frozen, do not edit". Resolved: frozen = source, not membership.

| Option | Description | Selected |
|--------|-------------|----------|
| Full wiring, empty core | Root pnpm workspace + pkg.json; empty voss-app-core lib.rs; src-tauri path-dep wired now | ✓ |
| Full pnpm, no core dependency yet | pnpm + empty core, but no src-tauri→core dep until A2 | |
| Minimal: no root pnpm workspace | self-contained apps/voss-app pkg.json; defer §8 JS layout | |

**User's choice:** Full wiring, empty core (Recommended)
**Notes:** Tauri version left to Claude/researcher discretion — latest stable 2.x, confirm pin (SHL-01 "SPEC confirms", no SPEC exists).

---

## Config Read Scope for Theme Swap

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal theme-key read, baked fallback | Boot reads ~/.config/voss-app/settings.json theme object over baked Variant B; no UI/schema | ✓ |
| Bake Variant B only | No file read in A1; criterion 2 unmet | |
| Typed settings loader now | Full typed struct (theme+font+shell+keymap); A8 territory | |

**User's choice:** Minimal theme-key read, baked fallback (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Rust reads, JS applies | Tauri reads/parses → state; Solid sets CSS vars on :root at mount; I/O in Rust | ✓ |
| JS reads via Tauri fs plugin | Solid reads file directly; config I/O in webview; A8 likely rebuilds seam | |
| Rust reads + injects pre-paint | Rust injects resolved vars before first paint; zero theme flash; more plumbing | |

**User's choice:** Rust reads, JS applies (Recommended)

---

## Claude's Discretion

- Exact Tauri 2.x patch pin (researcher confirms current stable).
- `voss-app-core` placeholder content, crate metadata (inherit workspace).
- Solid tooling specifics (Vite template, tsconfig) within Solid+Tailwind lock.
- CSS-var token naming convention.

## Deferred Ideas

- linux/win custom window-control rendering + verification → A10 soak / CI matrix (abstraction built in A1).
- Code-signing cert procurement (REL-02) — wiring in A10, but human procurement clock should *start during A1* (CONCEPT §10 Q8). Flagged for planner as human-action note, not deferrable.
- Full settings system (font/shell/keymap/theme UI, typed loader) → A8; A1 lays Rust read seam only.
- Layout-preset switcher behavior → A4 (geometry) / L2 (semantics); A1 = visual placeholder only.
