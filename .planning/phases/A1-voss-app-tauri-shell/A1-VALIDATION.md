---
phase: A1
slug: voss-app-tauri-shell
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-17
---

# Phase A1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> A1 is a greenfield visual/build scaffold phase — validation is smoke builds + observable success criteria + manual visual checklists, NOT automated unit tests. See A1-RESEARCH.md "## Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual smoke + build verification (no unit test framework for A1 pure-scaffold) |
| **Config file** | none — A1 has no Rust unit tests or frontend component tests |
| **Quick run command** | `cd apps/voss-app && cargo check --manifest-path src-tauri/Cargo.toml && pnpm -C apps/voss-app build` (type/compile check) |
| **Full suite command** | `pnpm -C apps/voss-app tauri build` (unsigned local artifact) then launch the produced `.app` |
| **Estimated runtime** | ~30–120 s (first build slower; incremental `cargo check` ~5–15 s) |

---

## Sampling Rate

- **After every task commit:** Run `cargo check` (Rust, src-tauri) + `pnpm build` (TS type-check)
- **After every plan wave:** `pnpm tauri dev` → manual visual inspection checklist (titlebar, tokens, controls)
- **Before `/gsd:verify-work`:** `pnpm tauri build` exits 0, app launches, all SHL-01..06 pass
- **Max feedback latency:** ~120 s (full unsigned build); ~15 s for per-commit compile check

---

## Per-Task Verification Map

> Task IDs assigned by the planner. Mapped here by requirement until plans exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| A1-0x-xx | TBD | 0 | (workspace) | — | N/A | smoke | `cargo metadata --no-deps \| grep voss-app-core` + `pnpm -w ls` | ❌ W0 | ⬜ pending |
| A1-0x-xx | TBD | 1 | SHL-01 | — | N/A | smoke | `grep -E '^name = "tauri"' -n apps/voss-app/src-tauri/Cargo.lock` and `node -e "require('./apps/voss-app/package.json')"` shows pinned 2.x | ❌ W0 | ⬜ pending |
| A1-0x-xx | TBD | 1 | SHL-02 | — | N/A | visual | `pnpm tauri dev` → DevTools `:root` shows Variant B `--` vars; Tailwind utilities resolve to `var(--…)` | ❌ W0 | ⬜ pending |
| A1-0x-xx | TBD | 2 | SHL-03 | — | titlebar exposes no cost-meter slot | visual | `pnpm tauri dev` → titlebar shows project-name placeholder + visual preset switcher; no `$` cost element in DOM | ❌ W0 | ⬜ pending |
| A1-0x-xx | TBD | 2 | SHL-04 | — | window controls only act on own window | manual | `pnpm tauri dev` → close/minimize/maximize/fullscreen each work; multi-monitor + zoom OK (macOS) | ❌ W0 | ⬜ pending |
| A1-0x-xx | TBD | 3 | SHL-05 | — | N/A | smoke | `pnpm -C apps/voss-app tauri build` exit 0 + artifact at `target/release/bundle/macos/` | ❌ W0 | ⬜ pending |
| A1-0x-xx | TBD | 2 | SHL-06 | — | N/A | visual | window title + About dialog render literal string `Voss ADE` | ❌ W0 | ⬜ pending |
| A1-0x-xx | TBD | 3 | D-01/D-09 | T-A1-01 | malformed/absent settings.json → safe baked fallback, no crash, no path traversal | manual | write `~/.config/voss-app/settings.json` `{ "theme": {…} }` → relaunch → CSS vars change; `rm` file → relaunch → pure Variant B, no console error | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] No pre-existing test files — voss-app is greenfield; A1 establishes the project, not a test suite.
- [ ] Token-value grep script (post-Wave 1): `grep -F "<variant-b hex>" apps/voss-app/src/**/variant-b.css` confirms sketch-001 values verbatim.
- [ ] Compile smoke available once scaffold exists: `cargo check` (src-tauri) + `pnpm build` (Vite/TS).
- [ ] Titlebar visual reference screenshot saved after Wave 2 (manual baseline for later phases).

*Existing infrastructure does not cover A1 — it is the first code in `apps/voss-app/`. Validation is smoke build + visual checklist by design (RESEARCH.md confirms automated unit tests are not warranted for a window-open scaffold).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Window decorations render correctly (no native chrome, custom controls, 0-radius) | SHL-03/04 | Visual chrome correctness can't be asserted in a unit test for a `decorations:false` window | `pnpm tauri dev` → confirm no OS title bar; custom close/min/max/fullscreen present + functional; drag region works (drag empty titlebar area moves window) |
| Variant B token fidelity | SHL-02 | Pixel/token visual fidelity vs sketch 001 is a human judgement | `pnpm tauri dev` → DevTools compare computed `:root` vars against sketch 001 index.html values |
| Runtime theme swap via config file | D-01 | Requires file mutation + app relaunch + visual diff | Create `~/.config/voss-app/settings.json` with a `theme` override → relaunch → confirm color changes without rebuild |
| Ship-name string | SHL-06 | String-in-UI presence | Inspect window title bar + Help→About show `Voss ADE` (not `voss-app`) |
| Unsigned build launches | SHL-05 | macOS Gatekeeper / `xattr` first-launch behavior | `pnpm tauri build` → `xattr -cr` the `.app` → double-click launches |

---

## Validation Sign-Off

- [ ] All tasks have a smoke/manual verification or explicit Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without a compile/smoke check
- [ ] Wave 0 covers all MISSING references (greenfield — establishes baseline)
- [ ] No watch-mode flags
- [ ] Feedback latency < 120 s
- [ ] `nyquist_compliant: true` set in frontmatter (set by planner/checker once per-task map filled)

**Approval:** pending
