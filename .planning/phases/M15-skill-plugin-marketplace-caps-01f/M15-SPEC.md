# Phase M15: Skill / Plugin Marketplace (CAPS-01f) — Specification

**Created:** 2026-05-19
**Ambiguity score:** 0.15 (gate: ≤ 0.20)
**Requirements:** 6 locked

## Goal

Voss gains a headless skill-bundle install path — `voss skill add|list|remove|update` installs a third-party plugin **bundle dir** (TOML manifest + `.voss` program file(s)) from a git URL, GitHub shorthand, or local path, extending the existing `plugins.py` manifest/enablement machinery; installs are gated by detached-signature + pinned-key trust verification, and an installed `.voss`-authored skill runs under the existing tool gate constrained to its manifest-declared permission scopes.

## Background

Skill/plugin infra today is local-only and built-in-only:

- `voss/harness/plugins.py` — `PluginManifest` loaded from `*.toml` in `~/.config/voss/plugins/` and `.voss/plugins/`. Manifests only **reference** existing built-in command/skill/agent IDs (unknown → `warnings`). Enablement persisted in `~/.config/voss/plugins.toml` (chmod 0600). No install, fetch, signing, sandbox, scopes, or remote source.
- `voss/harness/skill_registry.py` — in-process registry of **built-in Python-callable** skills only (`analyze`, `rename-symbol`, `voss-lint-as-skill`). No third-party / `.voss`-authored skill loading.
- `voss/harness/cli.py` — REPL slash `/plugins`, `/plugin enable|disable <id>`, `/skills`, `/skill <id>`. No top-level `voss skill` command, no registry/marketplace concept.

The CAPS-01 seed (`seeds/agent-capability-surface.md`, item 6) defines this as the last capability — "needs trust/sandbox story first"; registry "GitHub-based likely for v0.2; central registry later". M15 builds the install + trust + scope-enforcement path on top of the existing plugin machinery, headless-only (matching M14's headless-only discipline).

## Requirements

1. **`voss skill add` bundle install**: A top-level CLI installs a third-party skill bundle from a git URL, GitHub `owner/repo` shorthand, or local path/archive.
   - Current: No `voss skill` CLI; plugins are hand-placed `.toml` files; no fetch path
   - Target: `voss skill add <git-url | owner/repo | ./local-path>` fetches and installs a bundle dir (TOML manifest + `.voss` file(s) + optional assets) into the existing plugin dir, extending `plugins.py` discovery/enablement — not a parallel system
   - Acceptance: `voss skill add ./<example-bundle>` and `voss skill add <github-shorthand>` each install a bundle that `voss skill list` then shows; no central index/network search is contacted

2. **`.voss`-authored skill registration**: An installed bundle's manifest registers its `.voss` program as a runnable skill alongside built-ins.
   - Current: `skill_registry` holds only built-in Python callables; no `.voss`-backed skill can be registered
   - Target: A bundle manifest binds a skill id to a `.voss` program; the skill loads into the registry and executes via the existing harness `.voss` runtime (no new interpreter)
   - Acceptance: After install, `/skill <id>` resolves the third-party id and running it produces the skill's declared effect; before install that id does not resolve

3. **Detached-signature + pinned-key trust gate**: Install and update are refused unless the bundle manifest carries a valid detached signature from a trusted (pinned) key.
   - Current: No signing or trust concept anywhere; any local `.toml` is loaded
   - Target: A detached signature (minisign / ssh-sig family) over the manifest is verified against a pinned trusted key; `voss skill trust <key>` pins a key; first-add may TOFU-pin; a tampered manifest or unknown/untrusted key refuses the operation with non-zero exit and installs nothing
   - Acceptance: Installing a bundle with a tampered manifest fails (sig mismatch, nothing installed); installing one signed by an unknown key fails until `voss skill trust <key>` is run, after which the same install succeeds

4. **Manifest-declared permission scopes enforced at the gate**: A third-party skill is confined at run time to the tool/fs/net scopes its manifest declares, enforced through the existing tool gate.
   - Current: No per-skill scoping; the tool gate/allowlist is global; third-party skills cannot run at all
   - Target: The manifest declares permission scopes (tools / fs / net); at skill run time those scopes are enforced by reusing the existing tool gate/allowlist — no new enforcement engine, no OS sandbox
   - Acceptance: A skill attempting a tool/fs/net action outside its declared scopes is blocked by the gate (operation denied, run does not perform the out-of-scope action); an in-scope action of the same kind is permitted

5. **Lifecycle verbs (list / remove / update)**: The install path supports enumeration, uninstall, and signature-re-verifying update.
   - Current: No uninstall/update; `/plugins` only lists built-in-referencing manifests
   - Target: `voss skill list` enumerates installed third-party skills; `voss skill remove <id>` uninstalls it; `voss skill update <id>` re-fetches and re-verifies the signature, leaving the prior version intact on verification failure
   - Acceptance: After `remove <id>`, `list` omits it and `/skill <id>` no longer resolves; `update <id>` against a now-tampered upstream fails and the previously installed version still resolves and runs

6. **Shipped signed example skill bundle**: The phase ships a real signed `.voss` skill bundle in-repo used as the end-to-end acceptance fixture.
   - Current: No example or fixture skill bundle exists
   - Target: A small, useful signed `.voss` skill bundle is committed in-repo with manifest, signature, and declared scopes, exercising the full add → list → run → update → remove path
   - Acceptance: CI runs the full add → list → run → remove cycle against the shipped example bundle and it passes; the example's signature verifies against its committed trusted key

## Boundaries

**In scope:**
- `voss skill add <git-url | owner/repo | ./local-path | local archive>` — fetch + install
- Bundle layout: TOML manifest + `.voss` program file(s) + optional assets, extending `plugins.py` dirs/enablement
- `.voss`-authored skill registered into `skill_registry`, runnable via `/skill <id>` like built-ins, via the existing `.voss` runtime
- Detached-signature verification (minisign / ssh-sig family) + pinned-key trust; `voss skill trust <key>`; TOFU pin on first add
- Manifest-declared permission scopes (tools / fs / net) enforced via the existing tool gate at run time
- `voss skill list` / `voss skill remove` / `voss skill update`
- One shipped signed example skill bundle as the e2e CI fixture
- Headless surface only: top-level CLI + REPL slash

**Out of scope:**
- Central/hosted registry + `voss skill search` / name index — deferred ("central registry later", seed item 6)
- OS-level sandbox (subprocess isolation, seccomp, containers) — deferred; v0.2 confinement is signature + manifest-scope-vs-gate only, an accepted documented trust limitation
- M9 TUI marketplace / install panel — deferred (headless-only, matching M14 discipline)
- GPG keyring trust path — minisign/ssh-sig family chosen instead (lighter key UX)
- Skill authoring/publishing toolchain (`voss skill publish`, bundle scaffolding) — not this phase
- Inter-skill dependency / version resolution — out; single self-contained bundle, no skill→skill deps
- Auto-update / background refresh — `update` is explicit and manual only

## Constraints

- MUST extend the existing `voss/harness/plugins.py` manifest + enablement machinery — not a fork or parallel install system.
- Permission-scope enforcement MUST reuse the existing tool gate/allowlist — no second enforcement engine.
- Trust mechanism MUST be detached-signature + pinned-key (minisign or ssh-sig family). The exact library is a discuss-phase HOW decision; the SPEC requirement is falsifiable as "tampered manifest → refuse" and "unknown/untrusted key → refuse until pinned".
- No OS sandbox this phase: an installed `.voss` skill's only confinement is its manifest-declared scopes enforced at the gate — this limitation MUST be documented.
- `.voss` skill execution MUST reuse the existing harness `.voss` runtime — no new interpreter or execution path.
- Headless-only — MUST NOT introduce an M9 TUI dependency.

## Acceptance Criteria

- [ ] `voss skill add ./<example-bundle>` installs the bundle and `voss skill list` shows it
- [ ] `voss skill add <github-shorthand>` resolves and installs from GitHub (git fetch path)
- [ ] An installed `.voss` skill registers and runs via `/skill <id>`, producing its declared effect
- [ ] Install of a bundle with a tampered manifest (signature mismatch) is refused, exits non-zero, installs nothing
- [ ] Install signed by an unknown/untrusted key is refused until `voss skill trust <key>` pins it, then succeeds
- [ ] At run time, a skill action outside its manifest-declared tool/fs/net scopes is blocked by the existing gate; an in-scope action of the same kind is permitted
- [ ] `voss skill remove <id>` uninstalls; subsequent `voss skill list` omits it and `/skill <id>` no longer resolves
- [ ] `voss skill update <id>` re-fetches and re-verifies the signature; a tampered upstream fails update and leaves the prior installed version intact and runnable
- [ ] The shipped signed example skill bundle passes the full add → list → run → remove cycle in CI; its signature verifies against its committed trusted key
- [ ] No central registry/search, OS sandbox, or M9 TUI code is introduced

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Bundle dir + 4 verbs + minisign-style sig + scope-vs-gate    |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Central index / OS sandbox / TUI / GPG explicitly out        |
| Constraint Clarity | 0.78  | 0.65 | ✓      | Extends plugins.py; reuses gate; exact sig lib = HOW detail   |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 10 pass/fail criteria; example fixture anchors e2e            |
| **Ambiguity**      | 0.15  | ≤0.20| ✓      |                                                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective           | Question summary                          | Decision locked                                                                 |
|-------|-----------------------|-------------------------------------------|---------------------------------------------------------------------------------|
| 1     | Researcher            | What IS a third-party skill artifact?     | Plugin bundle dir extending plugins.py; skill = `.voss` registered by manifest   |
| 1     | Researcher            | Registry/source scope for v0.2?           | git URL + GitHub shorthand + local path/file; no central index/search           |
| 1     | Researcher            | Sandbox/trust boundary?                   | Manifest-declared scopes enforced vs existing gate; sig gates install; no OS sbx |
| 2     | Researcher/Simplifier | Concrete signing mechanism?               | Detached sig + pinned key (minisign/ssh-sig); `voss skill trust`; TOFU first-add |
| 2     | Simplifier            | Lifecycle verbs this phase?               | add + list + remove + update (update re-verifies signature)                      |
| 2     | Simplifier            | Surface + verification anchor?            | Headless-only (defer M9 TUI); ship signed example skill bundle as e2e fixture    |

---

*Phase: M15-skill-plugin-marketplace-caps-01f*
*Spec created: 2026-05-19*
*Next step: /gsd:discuss-phase M15 — implementation decisions (sig library, bundle manifest schema, scope grammar, fetch impl)*
