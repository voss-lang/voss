# Phase M15: Skill / Plugin Marketplace (CAPS-01f) - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning
**Source:** Direct-from-SPEC (M15-SPEC.md — 6 requirements locked, ambiguity 0.15; discuss-phase skipped per standing preference)

<domain>
## Phase Boundary

Headless skill-bundle install path for the Voss harness. `voss skill add|list|remove|update` installs a third-party plugin **bundle dir** (TOML manifest + `.voss` program file(s) + optional assets) from a git URL, GitHub `owner/repo` shorthand, or local path/archive, **extending the existing `voss/harness/plugins.py` manifest + enablement machinery** (not a parallel system). Installs/updates are gated by detached-signature + pinned-key trust verification. An installed `.voss`-authored skill registers into the existing `skill_registry` and runs via the existing `.voss` runtime, confined at run time to its manifest-declared permission scopes enforced through the existing tool gate. Ships one signed example skill bundle as the end-to-end CI fixture.

Authoritative scope, requirements, boundaries, and acceptance criteria are locked in `M15-SPEC.md`. This CONTEXT layers HOW guidance + cross-cutting constraints from ROADMAP on top of those locked requirements — it does not relitigate WHAT.
</domain>

<decisions>
## Implementation Decisions

### Locked by M15-SPEC.md (one-way door — do not relitigate)
- **Artifact**: plugin **bundle dir** = TOML manifest + `.voss` program file(s) + optional assets. Extends `voss/harness/plugins.py` discovery + `~/.config/voss/plugins.toml` enablement — NOT a fork/parallel install system.
- **Sources (v0.2)**: git URL, GitHub `owner/repo` shorthand, local path, local archive. **No central index / `voss skill search` / network name resolution.**
- **Verbs**: `voss skill add`, `voss skill list`, `voss skill remove`, `voss skill update`. `update` re-fetches **and** re-verifies signature; verification failure leaves prior version intact and runnable.
- **Trust**: detached signature over the manifest, **minisign / ssh-sig family** (NOT GPG). `voss skill trust <key>` pins a key; first-add may TOFU-pin. Tampered manifest OR unknown/untrusted key → refuse, non-zero exit, install nothing.
- **`.voss` skill registration**: bundle manifest binds a skill id → `.voss` program; loads into `skill_registry`; runs via the **existing harness `.voss` runtime** (no new interpreter). Runnable via `/skill <id>` like built-ins.
- **Confinement**: manifest-declared permission scopes (tools / fs / net) enforced at skill run time by **reusing the existing tool gate / allowlist** — no second enforcement engine, **no OS-level sandbox** this phase. The limitation MUST be documented.
- **Surface**: headless only — top-level CLI + REPL slash. **No M9 TUI dependency** (deferred, M14-parity discipline).
- **Fixture**: ship one real signed `.voss` skill bundle in-repo (manifest + signature + declared scopes) exercising add → list → run → update → remove; CI runs the full cycle.

### Cross-cutting constraints (locked, from ROADMAP M15 section)
- **Sandbox/permission story is a hard prerequisite** — no third-party code path runs before scope-vs-gate enforcement exists. Highest-risk surface of the cycle; plan it first in the wave order.
- **Default-deny posture**: third-party skill default scope is read-only; mutating-tool scopes require explicit declared grant in the manifest (aligns with SPEC scope enforcement). Map declared scopes onto the **existing M1 permission tiers (`plan` / `edit` / `auto`)** in `voss/harness/permissions.py` rather than inventing a parallel tier vocabulary.
- **Audit trail**: every third-party skill invocation is logged through the existing M2 RunRecorder (`voss/harness/recorder.py`) — installs, scope grants/denials, and skill runs are recorded events.

### Claude's Discretion (HOW — resolve in planning)
- **Manifest filename/format detail**: SPEC locks "TOML, extends plugins.py"; ROADMAP headline mentioned a `voss-skill.yml`. SPEC wins — extend the existing TOML `PluginManifest` schema with the new fields (signature ref, declared scopes, `.voss` skill binding). Pick exact field names/layout in planning.
- **Signature library choice**: minisign vs ssh-sig (`ssh-keygen -Y`) — both satisfy the locked "detached sig + pinned key" mechanism. Choose based on dependency weight + availability; document the falsifiable behavior (tamper→refuse, unknown-key→refuse-until-pinned) regardless.
- **Scope grammar**: concrete shape of declared `tools/fs/net` scopes and how they bind to existing gate/allowlist predicates in `tools.py`/`sandbox.py`/`permissions.py`.
- **Fetch implementation**: git clone vs sparse fetch; cache/extraction location under the existing plugin dirs.
- **Trust store location/format**: where pinned keys live (under `~/.config/voss/`), file perms (mirror the existing `plugins.toml` chmod 0600 pattern).
- **Example skill content**: pick a small genuinely useful `.voss` skill for the fixture.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked spec (authority)
- `.planning/phases/M15-skill-plugin-marketplace-caps-01f/M15-SPEC.md` — 6 locked requirements (SKILL-01..06), boundaries, constraints, 10 acceptance criteria. The contract.

### Existing infra to extend (NOT fork)
- `voss/harness/plugins.py` — `PluginManifest`, `user_plugin_dir()`/`project_plugin_dir()`, `plugins.toml` enablement (chmod 0600), `load_plugins()`, `_read_manifest()`. M15 extends this.
- `voss/harness/skill_registry.py` — `SkillRegistry` / `SkillEntry` / `default_skill_registry()`. Currently built-in Python callables only; M15 adds `.voss`-backed registration.
- `voss/harness/cli.py` — REPL slash `/plugins`, `/plugin enable|disable`, `/skills`, `/skill <id>`; top-level CLI command surface for the new `voss skill` group.

### Enforcement / audit substrate to reuse
- `voss/harness/permissions.py` — M1 permission tiers (`plan`/`edit`/`auto`); declared scopes map onto these.
- `voss/harness/sandbox.py` — existing sandbox/confinement helpers; reuse, do not add an OS sandbox.
- `voss/harness/tools.py` — tool gate / allowlist; scope enforcement reuses this predicate path.
- `voss/harness/recorder.py` — M2 RunRecorder; install/grant/deny/run events recorded here.

### Prior art
- `voss/harness/mcp/server_skills.py` — existing "expose harness skills" surface; reference for skill-binding patterns.
- `.planning/phases/M14-*/M14-SPEC.md` + plans — headless-only discipline + lifecycle-reuse precedent this phase mirrors.
- `.planning/seeds/agent-capability-surface.md` (capability 6) — origin seed; trust/sandbox-first sequencing rationale.

### Roadmap
- `.planning/ROADMAP.md` Phase M15 section — cross-cutting constraints (M1 tier coordination, M2 audit, default-deny) + roadmap-level out-of-scope.
</canonical_refs>

<specifics>
## Specific Ideas

- Scope-vs-gate enforcement and signature trust MUST be implemented and provable **before** any third-party `.voss` code is executed — wave-1 work, ahead of `add`/registration.
- Reuse the `plugins.toml` chmod-0600 pattern for the trust/key store.
- `update` failure path is a first-class requirement: tampered upstream → update fails, prior installed version still resolves and runs (acceptance criterion, not an edge note).
- The shipped example bundle is the CI acceptance anchor for SKILL-01..06 — it must be a real signed bundle, not an ad-hoc test stub.
- Scope grammar should express declared scopes in terms of existing gate predicates so enforcement is a binding, not a reimplementation.
</specifics>

<deferred>
## Deferred Ideas

- Central/hosted registry + `voss skill search` / name index — explicitly "central registry later" (seed + SPEC out-of-scope).
- OS-level sandbox (subprocess isolation, seccomp, containers) — deferred; v0.2 confinement = signature + manifest-scope-vs-gate only (documented limitation).
- M9 TUI marketplace / install panel — deferred (headless-only).
- GPG keyring trust path — minisign/ssh-sig chosen instead.
- Skill authoring/publishing toolchain (`voss skill publish`, scaffolding) — not this phase.
- Inter-skill dependency / version resolution — out (single self-contained bundle).
- Auto-update / background refresh; hot-reload mid-session — `update` is manual/explicit only.
- Paid skills, cross-org discovery — ROADMAP out-of-scope (post-v0.2).
</deferred>

<scope_fence>
## Scope Fence

**Touch:** `voss/harness/plugins.py`, `voss/harness/skill_registry.py`, `voss/harness/cli.py`, new `voss skill` CLI module, new signature/trust + scope-enforcement modules under `voss/harness/`, the shipped example bundle + its CI test.

**Do NOT touch / introduce:** central registry or search backend; any OS sandbox (subprocess/seccomp/container) mechanism; M9 TUI code; GPG; a parallel manifest/enablement system separate from `plugins.py`; a second permission/gate enforcement engine separate from `permissions.py`/`tools.py`/`sandbox.py`; new `.voss` interpreter/runtime.
</scope_fence>

---

*Phase: M15-skill-plugin-marketplace-caps-01f*
*Context gathered: 2026-05-19 via direct-from-SPEC (discuss-phase skipped per standing preference)*
