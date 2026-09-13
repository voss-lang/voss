---
phase: A1-voss-app-tauri-shell
plan: 04
type: execute
wave: 4
depends_on: ["A1-03"]
files_modified:
  - apps/voss-app/src-tauri/tauri.conf.json
autonomous: false
requirements: [SHL-05, SHL-06]
must_haves:
  truths:
    - "`pnpm tauri build` exits 0 and produces an unsigned macOS .app bundle artifact"
    - "The built .app launches (after xattr clear) and shows the same custom Variant B chrome as dev mode"
    - "The About panel / app menu shows the literal ship name 'Voss ADE' (not 'voss-app')"
    - "tauri.conf.json declares a restrictive CSP (no remote script origins)"
    - "Code-signing cert procurement is surfaced to the human as an out-of-band A10 long-pole (no signing wiring built here)"
  artifacts:
    - path: "apps/voss-app/src-tauri/tauri.conf.json"
      provides: "Restrictive CSP + confirmed unsigned-local bundle config"
      contains: "csp"
  key_links:
    - from: "apps/voss-app/src-tauri/tauri.conf.json"
      to: "Tauri bundler"
      via: "bundle.macOS.signingIdentity null + APPLE_SIGNING_IDENTITY=- ad-hoc"
      pattern: "signingIdentity"
---

<objective>
Prove the SHL-05 ship gate: `pnpm tauri build` produces a runnable **unsigned local** macOS artifact (smoke-test only — NOT a release artifact), the built app shows the "Voss ADE" ship name in the About panel (SHL-06), and the webview CSP is hardened. Surface the A10 code-signing certificate-procurement clock as a human-action note (cert procurement has weeks of external lead time and per CONCEPT §10 Q8 / CONTEXT deferred-ideas must START during A1, even though all signing/channel wiring lands in A10).

Purpose: SHL-05 (`pnpm tauri build` = unsigned local smoke artifact) and SHL-06 (About dialog uses "Voss ADE"). Explicitly NO release pipeline / signing / CI / Homebrew / npm work — that is consolidated into A10.

Output: A verified unsigned `.app` build, a hardened CSP, and a recorded human cert-procurement action item for A10.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md
@.planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md
@.planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md
@.planning/phases/A1-voss-app-tauri-shell/A1-03-SUMMARY.md

<interfaces>
<!-- tauri.conf.json was created in Plan A1-01. This plan makes ONE additive
     edit (add app.security.csp) and verifies the unsigned-build path. -->

From Plan A1-01 tauri.conf.json already has:
  productName "Voss ADE", title "Voss ADE", version "0.1.0",
  identifier "app.voss-ade", decorations false,
  bundle.active true, bundle.targets "all",
  bundle.macOS.signingIdentity null,
  bundle.icon [the scaffold icon set].

Unsigned local build (A1-RESEARCH.md "Pattern 4" note + Open Question 3 +
"## Human Action Note"): build with APPLE_SIGNING_IDENTITY="-" (ad-hoc sign;
no certificate; Gatekeeper will warn — clear with `xattr -cr` before launch).
Artifact path: apps/voss-app/src-tauri/target/release/bundle/macos/Voss ADE.app

About panel (A1-UI-SPEC.md "About Dialog Contract"): Tauri's native macOS
about panel auto-displays productName + version from tauri.conf.json — NO
custom dialog component needed in A1. Subtitle "Agentic Development
Environment" is contract copy; native panel showing "Voss ADE" + "0.1.0"
satisfies SHL-06.

NO release/CI/signing/Homebrew/npm work in this plan (CONTEXT hard boundary;
that is A10). The cert-procurement item is a NOTE to the human, not built work.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Harden webview CSP (additive tauri.conf.json edit)</name>
  <files>apps/voss-app/src-tauri/tauri.conf.json</files>
  <read_first>
    - apps/voss-app/src-tauri/tauri.conf.json (the file being edited — current config from Plan A1-01)
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("## Security Domain", "Anti-Patterns to Avoid" — no macosPrivateApi, opaque bg so no transparency)
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("Window Architecture Contract")
  </read_first>
  <action>
    Make ONE additive edit to `apps/voss-app/src-tauri/tauri.conf.json`: add `app.security.csp` with a restrictive policy so the webview cannot load remote/eval'd code. Use `default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'; connect-src 'self' ipc: http://ipc.localhost` (the `'unsafe-inline'` on style-src is required because the titlebar/components use inline `style=` attributes and `applyThemeOverrides` writes inline `:root` styles; no `'unsafe-eval'`, no remote origins, no `script-src` host allowances). Do NOT add `macosPrivateApi` (Variant B is opaque `--bg-0`, no transparency — RESEARCH anti-pattern). Do NOT change productName / title / version / decorations / signingIdentity (those are correct from Plan A1-01). This is the only file edit in this plan.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && node -e "const c=require('./apps/voss-app/src-tauri/tauri.conf.json'); const csp=c.app&&c.app.security&&c.app.security.csp||''; if(!csp) throw new Error('no csp'); if(/unsafe-eval/.test(csp)) throw new Error('unsafe-eval present'); if(/https?:\/\/(?!ipc\.localhost)/.test(csp)) throw new Error('remote origin in csp'); if(c.productName!=='Voss ADE') throw new Error('productName changed'); if(c.app.windows[0].decorations!==false) throw new Error('decorations changed'); console.log('csp ok:',csp)" && ! grep -q 'macosPrivateApi' apps/voss-app/src-tauri/tauri.conf.json</automated>
  </verify>
  <done>
    `tauri.conf.json` has `app.security.csp` with no `unsafe-eval` and no remote origins; productName/decorations/signingIdentity unchanged from Plan A1-01; no `macosPrivateApi`.
  </done>
</task>

<task type="checkpoint:human-action" gate="blocking-human">
  <name>Task 2: A10 code-signing cert procurement clock (out-of-band human action)</name>
  <files>(none — out-of-band external action; no repo files created or modified, and explicitly NO cert/secret committed)</files>
  <read_first>
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("## Human Action Note (Deferred — flagged for planner)")
    - .planning/phases/A1-voss-app-tauri-shell/A1-CONTEXT.md ("<deferred>" — the "⚠ Cross-phase action, not deferrable" bullet)
  </read_first>
  <action>Pause for the human to START the external code-signing certificate-procurement clock for A10 (Apple Developer Program enrollment + Developer ID Application cert; Windows Authenticode EV cert) per &lt;how-to-verify&gt;. This is purely "start the clock" — NO signing is built or used in A1 and NO cert/secret is committed. This gate is informational: A1 proceeds to an UNSIGNED build (Task 3) regardless of cert status.</action>
  <verify>Human types "acknowledged" confirming the A10 cert-procurement long-pole is started (or already in hand) and that no cert/secret will be committed to the repo in A1.</verify>
  <done>Human acknowledged the A10 cert long-pole and started (or confirmed already-have) Apple + Windows cert procurement; no cert/secret added to repo; A1 continues to unsigned build.</done>
  <what-built>
    Nothing is built for signing in A1 (all signing/channel/version-sync wiring is A10 per CONTEXT hard boundary). This checkpoint exists ONLY to start the external procurement clock: code-signing certificates have multi-week CA / Apple lead times, and CONCEPT §10 Q8 + CONTEXT deferred-ideas explicitly require procurement to START during A1 so A10 is not blocked waiting on a CA.
  </what-built>
  <how-to-verify>
    This is a human out-of-band action item — acknowledge and start it; it does not gate the A1 build (Task 3 runs unsigned). Items to begin now:
    1. Apple: enroll in the Apple Developer Program ($99/yr) at developer.apple.com if not already enrolled; plan to generate a "Developer ID Application" certificate (used by A10 notarization).
    2. Windows: begin procuring a Windows Authenticode certificate (EV cert recommended) from a trusted CA — allow 1-4 weeks for CA validation.
    3. Record where the certs/credentials will live so A10 can wire them (do NOT commit any cert/secret to the repo).
    No certificate is installed or used in A1. This is purely "start the clock".
  </how-to-verify>
  <resume-signal>Type "acknowledged" (cert procurement started or already in hand) to proceed to the unsigned build. This does NOT require certs to exist — only acknowledgement that the A10 clock is started.</resume-signal>
  <acceptance_criteria>
    - Human has acknowledged the A10 cert-procurement long-pole and started (or confirmed already-have) Apple Developer enrollment + Windows Authenticode procurement
    - No certificate/secret material is added to the repo in A1
    - A1 proceeds to an UNSIGNED build regardless of cert status (this gate is informational, not a signing dependency)
  </acceptance_criteria>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Unsigned build smoke + About panel ship-name verification</name>
  <files>(none — verification-only checkpoint; produces a build artifact under target/ which is git-ignored, no tracked repo files modified)</files>
  <read_first>
    - .planning/phases/A1-voss-app-tauri-shell/A1-RESEARCH.md ("Open Question 3 — APPLE_SIGNING_IDENTITY", "Pitfall 7 — missing icons", "## Validation Architecture" full suite command)
    - .planning/phases/A1-voss-app-tauri-shell/A1-UI-SPEC.md ("About Dialog Contract", "Copywriting Contract" — internal slugs must NOT appear)
    - .planning/phases/A1-voss-app-tauri-shell/A1-VALIDATION.md ("Manual-Only Verifications" SHL-05/06 rows, "Validation Sign-Off")
  </read_first>
  <action>Pause for the human to run `APPLE_SIGNING_IDENTITY="-" pnpm tauri build`, confirm exit 0 + the unsigned `Voss ADE.app` artifact, `xattr -cr` + launch it, and verify the built app shows the same Variant B chrome plus the "Voss ADE" / "0.1.0" About panel per &lt;how-to-verify&gt;. No tracked repo files are written; the build artifact lands under git-ignored target/. This is the A1 phase ship gate (SHL-05 + SHL-06).</action>
  <verify>Human types "approved" after confirming the unsigned build exits 0, the .app launches with correct chrome, and the About panel shows literal "Voss ADE" / "0.1.0" with no internal slug user-visible.</verify>
  <done>Unsigned build smoke + About-panel ship-name confirmed by the human; A1 boundary held (no release/CI/signing/Homebrew/npm artifacts); explicit approval recorded.</done>
  <what-built>
    The full A1 scaffold (monorepo, Variant B tokens, theme seam, custom titlebar) plus the hardened CSP. This is the phase ship gate: an unsigned local `.app` is produced and launched to confirm the built artifact behaves like dev mode and shows the "Voss ADE" ship name.
  </what-built>
  <how-to-verify>
    1. From `apps/voss-app/`: `APPLE_SIGNING_IDENTITY="-" pnpm tauri build` (ad-hoc unsigned — RESEARCH Open Question 3). Confirm it exits 0. If it errors on missing icons, run `pnpm tauri icon <source.png>` and rebuild (RESEARCH Pitfall 7).
    2. Confirm the artifact exists at `apps/voss-app/src-tauri/target/release/bundle/macos/Voss ADE.app`.
    3. Clear the quarantine attribute so Gatekeeper allows the unsigned app: `xattr -cr "apps/voss-app/src-tauri/target/release/bundle/macos/Voss ADE.app"`. Double-click to launch (or `open` it).
    4. Confirm the launched app shows the SAME custom chrome as dev mode: 22px Variant B titlebar, traffic-light controls functional, empty `#0a0b0e` body, no native decorations.
    5. With the app focused, open the macOS app menu → "About Voss ADE" (Tauri native about panel). Confirm it shows "Voss ADE" and version "0.1.0" — NOT "voss-app" and NOT "app.voss-ade".
    6. Confirm the internal slug `voss-app` / `app.voss-ade` does NOT appear anywhere user-visible (window title, About, Dock label all say "Voss ADE").
    7. Quit the app.
  </how-to-verify>
  <resume-signal>Type "approved" if the unsigned build succeeds, launches with the correct chrome, and the About panel shows "Voss ADE" / "0.1.0" — or describe the failure.</resume-signal>
  <acceptance_criteria>
    - `APPLE_SIGNING_IDENTITY="-" pnpm tauri build` exits 0 and produces `target/release/bundle/macos/Voss ADE.app` (SHL-05)
    - The built (xattr-cleared) app launches and renders the same custom Variant B chrome as dev mode
    - macOS About panel shows literal "Voss ADE" + "0.1.0"; internal slug `voss-app`/`app.voss-ade` never appears user-visible (SHL-06)
    - No release/CI/signing/Homebrew/npm artifacts were created (A1 boundary held — A10 owns that)
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Bundled webview assets ↔ network | CSP governs what the packaged webview may load/execute |
| Unsigned artifact ↔ macOS Gatekeeper | Ad-hoc-signed app requires manual quarantine clear (dev-only smoke) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A1-02 | Tampering | Webview loads remote/eval'd code | mitigate | `app.security.csp` set to `default-src 'self'` with no `unsafe-eval` and no remote origins; bundled `frontendDist` is local only. Verified by Task 1 CSP assertion |
| T-A1-05 | Spoofing / Tampering | Unsigned artifact distribution | accept | The unsigned `.app` is an explicit local smoke-test artifact, NOT a release (SHL-05). It is never distributed; Gatekeeper warning + manual `xattr -cr` is the expected friction. Real signing/notarization is A10 — its cert-procurement long-pole is surfaced as the Task 2 human action |
| T-A1-06 | Information Disclosure | Cert/secret material committed during procurement | mitigate | Task 2 acceptance criteria explicitly forbids adding any cert/secret to the repo in A1; procurement is out-of-band and recorded externally for A10 wiring |
</threat_model>

<verification>
- `tauri.conf.json` has a restrictive `app.security.csp` (no `unsafe-eval`, no remote origins); productName/decorations/signingIdentity unchanged; no `macosPrivateApi`.
- Human checkpoint: `APPLE_SIGNING_IDENTITY="-" pnpm tauri build` exits 0; `Voss ADE.app` exists at the bundle path; launches with correct chrome; About panel shows "Voss ADE" / "0.1.0"; no internal slug user-visible.
- Human action: A10 cert-procurement clock acknowledged/started; no certs committed.
- A1 boundary held: no release/CI/signing/Homebrew/npm artifacts.
</verification>

<success_criteria>
- `pnpm tauri build` produces a runnable unsigned local macOS artifact (SHL-05).
- About panel / app menu shows "Voss ADE" ship name; internal slug never user-visible (SHL-06).
- Webview CSP hardened against remote/eval code.
- A10 code-signing procurement clock surfaced and started by the human (no signing wiring built — that is A10).
</success_criteria>

<output>
Create `.planning/phases/A1-voss-app-tauri-shell/A1-04-SUMMARY.md` when done.
</output>
