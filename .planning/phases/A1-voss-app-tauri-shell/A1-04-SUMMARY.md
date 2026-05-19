---
phase: A1-voss-app-tauri-shell
plan: 04
subsystem: ui
tags: [tauri, csp, security, bundle, unsigned-build, ship-name, app-store-deferred]

requires:
  - phase: A1-03
    provides: custom 22px Variant B titlebar + macOS traffic-light controls + visual-only preset switcher + platform gate; App.tsx flex-column root over empty var(--bg-0) body
provides:
  - Hardened webview CSP in tauri.conf.json (default-src 'self'; no unsafe-eval; no remote script origins; style 'unsafe-inline' only for inline-style components + applyThemeOverrides)
  - Verified unsigned local macOS .app + .dmg artifact (APPLE_SIGNING_IDENTITY="-" ad-hoc) launching with full Variant B chrome
  - SHL-06 ship-name confirmed: built app About panel + Dock + window title = "Voss ADE" (internal slug voss-app / app.voss-ade never user-visible)
  - A10 code-signing cert-procurement long-pole surfaced + acknowledged (Apple Developer Program + Windows Authenticode clock started out-of-band; no cert/secret in repo)
affects: [A2, A3, A10]

tech-stack:
  added: []
  patterns:
    - "CSP contract: default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'; connect-src 'self' ipc: http://ipc.localhost. The 'unsafe-inline' on style-src is REQUIRED (titlebar/components use inline style= attrs + applyThemeOverrides writes inline :root style). No 'unsafe-eval', no remote origins, no script host allowances."
    - "Unsigned local smoke build = APPLE_SIGNING_IDENTITY=\"-\" pnpm tauri build (ad-hoc stub signature; no cert/key/Apple account). Real Developer ID signing + notarization is A10 only."

key-files:
  created: []
  modified:
    - apps/voss-app/src-tauri/tauri.conf.json (ONE additive edit: app.security.csp null -> restrictive policy string; productName/title/version/identifier/decorations/signingIdentity all unchanged from A1-01)

key-decisions:
  - CSP keeps `style-src 'unsafe-inline'` intentionally — every titlebar/App component uses inline `style=` and applyThemeOverrides writes inline `:root` custom properties. Removing it would break the theme seam. `script-src 'self'` with no `unsafe-eval` and no remote origin is the security-relevant hardening (T-A1-02 mitigation).
  - No `macosPrivateApi` (Variant B is opaque `--bg-0`; transparency/vibrancy not needed; private API blocks App Store — RESEARCH anti-pattern).
  - A1 ships an UNSIGNED smoke artifact by design (SHL-05). Distribution-grade signing/notarization/CI/Homebrew/npm = A10 hard boundary. Task 2 only STARTS the external Apple+Windows cert clock (multi-week CA lead time) so A10 is not blocked later.

patterns-established:
  - "tauri.conf.json security.csp is now the canonical CSP — later phases that add network calls (A6+ provider/agent surfaces) must widen connect-src deliberately, never loosen script-src."

requirements-completed: [SHL-05, SHL-06]

duration: ~20min (CSP edit + user-run unsigned build smoke + About-panel verify)
completed: 2026-05-18
---

# Phase A1, Plan 04: CSP Hardening + Unsigned Build Smoke + Ship-Name Verify Summary

**Hardened the webview CSP to `default-src 'self'` (no unsafe-eval, no remote origins), verified `APPLE_SIGNING_IDENTITY="-" pnpm tauri build` produces a runnable unsigned `Voss ADE.app` + `.dmg` that launches with the same Variant B chrome as dev mode and shows the "Voss ADE" ship name everywhere — A1 phase ship gate cleared.**

## Performance

- **Tasks:** 3 (Task 1 auto CSP edit; Task 2 blocking-human cert-clock ack; Task 3 blocking-human build smoke + About panel)
- **Files modified:** 1 (tauri.conf.json — single additive CSP edit)
- **Wave:** 4 (final A1 wave)

## Accomplishments

- `app.security.csp` set to the restrictive contract policy; assertion passed (no `unsafe-eval`, no remote origins, productName/decorations/signingIdentity unchanged, no `macosPrivateApi`).
- Unsigned ad-hoc build exited 0 — produced `src-tauri/target/release/bundle/macos/Voss ADE.app` + `.dmg` installer.
- Built app launched (post Gatekeeper bypass) showing the full A1 Variant B chrome: 22px titlebar, functional traffic lights, `Voss ADE` placeholder, `pipeline`-default preset switcher, empty `#0a0b0e` body, sharp corners.
- About panel / Dock / window title all show literal `Voss ADE` — internal slug `voss-app` / `app.voss-ade` never user-visible (SHL-06).
- Icon padding regression (flagged in A1-01/A1-02) confirmed fixed in the built artifact — Big Sur squircle renders with correct safe-area margins (no longer oversized vs Dock peers).
- A10 cert-procurement long-pole acknowledged + clock started (Apple Developer Program + Windows Authenticode); no cert/secret committed.

## Verify Output

### Task 1 automated (CSP assertion)
```
csp ok: default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'; connect-src 'self' ipc: http://ipc.localhost
no macosPrivateApi OK
```

### Task 2 human-action
`acknowledged` — A10 Apple + Windows cert procurement clock started out-of-band; no cert/secret added to repo; A1 proceeds unsigned (informational gate, not a signing dependency).

### Task 3 human-verify (unsigned build smoke + About)
- `APPLE_SIGNING_IDENTITY="-" pnpm tauri build` exited 0; `.app` + `.dmg` produced.
- Gatekeeper bypassed (right-click Open / `xattr -cr`).
- Launched app = identical Variant B chrome to dev mode (screenshot confirmed: traffic lights + `Voss ADE` + fanout/pipeline/swarm/watchers + empty dark body).
- About panel showed `Voss ADE` / `0.1.0`; no internal slug user-visible.
- Operator `approved`.

## A1 Boundary Held

No release / CI / signing / Homebrew / npm artifacts created. All distribution wiring stays in A10. The only build output is the git-ignored `target/` smoke artifact.

## Phase A1 — COMPLETE

All 4 plans executed + human-verified:
| Plan | Delivered | Reqs |
|------|-----------|------|
| A1-01 | Tauri+Solid+Tailwind scaffold + Cargo/pnpm monorepo wiring + pinned versions + icon set | SHL-01, SHL-06 |
| A1-02 | Variant B token taxonomy + @theme inline + get_theme_overrides theme seam (3-path verified) | SHL-02 |
| A1-03 | 22px custom titlebar + macOS traffic lights + platform gate + visual-only preset switcher + drag | SHL-03, SHL-04 |
| A1-04 | Hardened CSP + unsigned build smoke + ship-name verify + A10 cert clock | SHL-05, SHL-06 |

SHL-01..06 all satisfied. voss-app desktop shell foundation ready for A2 (grid/PTY).

## Carried-Forward Notes (for A2+ / A10)

- **11px JetBrains Mono Retina legibility** (UI-SPEC HiDPI Dimension-4 note): user flagged uncertainty in A1-03; deferred to A2 once body text renders. variant-b.css holds both 11px/11.5px as named tokens — adjustable if illegible.
- **drag-region count = 3** (A1-03 in-flight fix): plan's "exactly 2" verify guard is over-strict; future plan-checker rule should be ">= 2 AND outer container never carries the attr". Title-text drag is a deliberate macOS-convention addition.
- **App.tsx plan-defect** (A1-02): App.tsx was not in A1-02 files_modified but required the `var(--bg-0)` swap for the theme seam to be visually verifiable. Patched in flight; future plans touching the paint surface must list App.tsx explicitly.
- **A10 long-pole**: Apple Developer Program + Windows Authenticode cert procurement clock STARTED 2026-05-18. A10 must wire signing/notarization once certs land (allow 1-4 weeks CA validation).
- **Multi-monitor** window-control verification: not exercised (single-display dev). Opportunistic re-check when a 2nd display is available.
