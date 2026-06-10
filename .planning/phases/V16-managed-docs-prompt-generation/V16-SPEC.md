# Phase V16: Managed Docs & Prompt Generation (Jinja2 layout-aware doc sync) — Specification

**Created:** 2026-06-09
**Ambiguity score:** 0.17 (gate: ≤ 0.20)
**Requirements:** 6 locked

## Goal

`voss sync` (re)generates layout-aware workflow docs in `.voss/docs/`, a hash-verified workflow fence in VOSS.md, and project-editable reviewer/EM prompt copies — idempotently, so re-running on an unchanged project is a no-op.

## Background

Voss already has the rendering and fence machinery this phase needs:

- `voss/template_render.py` — single Jinja2 entrypoint (`render_package_template`, StrictUndefined, PackageLoader, env cache).
- `voss/harness/voss_md.py` — VOSS.md managed fences: `<!-- voss:begin id=X -->` / `<!-- voss:hash <sha256> -->` / `<!-- voss:end id=X -->`, with `read_fence_body`/`write_fence_body` and drift refusal (`HashMismatch`).
- `voss init` (`voss/cli.py` `_scaffold_target`) renders only `templates/init/` (pyproject.toml, README.md, hello.voss) — scaffold, not docs.
- `voss/templates/prompts/` holds 10 prompt templates rendered package-internally at runtime (`voss/harness/agent.py`, reviewers, EM). None are synced into projects; users cannot tune them per-project.

What does NOT exist: any layout-variable derivation, any `voss sync` operation, any agent-facing workflow docs written into projects, any workflow fence content in VOSS.md, any project-level prompt override path.

## Requirements

1. **`voss sync` command**: New top-level CLI command that regenerates all managed artifacts in an existing project.
   - Current: No `sync` subcommand; `voss init` only scaffolds new projects.
   - Target: `voss sync` run from a project root generates/updates `.voss/docs/`, the VOSS.md workflow fence, and synced prompts. Running it twice in a row produces zero file changes on the second run (byte-identical output).
   - Acceptance: Test runs `voss sync` twice in a fixture project; second run reports no changes and `git status` (or mtime/content comparison) shows no modified files.

2. **Layout context derivation**: Layout variables are derived from git/fs at sync time — not persisted config.
   - Current: No layout detection exists anywhere.
   - Target: A layout-context provider derives (at minimum) project name, project root, repo layout (repo-root vs worktree), command invocation prefixes, and workspace paths by inspecting git and the filesystem at sync time. Derivation is deterministic for an unchanged tree.
   - Acceptance: Unit tests assert derived context values for at least two fixture layouts (plain repo root; worktree checkout), and the same tree always yields the same context.

3. **Workflow docs generation**: Sync renders 3 layout-aware docs into `.voss/docs/`, consumable by external CLI agents and Voss's own harness.
   - Current: No generated docs; `.voss/` holds only config/memory.
   - Target: `.voss/docs/` contains a harness workflow cheatsheet, a voss command reference (invocations adjusted by layout context), and a review workflow doc — all rendered from `voss/templates/` via `render_package_template`. Docs are machine-owned: every sync rewrites them; each carries a "generated — do not edit" header. Customization belongs in VOSS.md prose, not in generated docs.
   - Acceptance: After sync, the 3 files exist with the generated-header; a manual edit to any of them is overwritten by the next sync; rendered command invocations differ correctly between the two fixture layouts.

4. **VOSS.md workflow fence**: The managed instruction section is a new fence id in VOSS.md, written via existing `voss_md.write_fence_body` machinery.
   - Current: VOSS.md fences exist (e.g. `id=architecture`) but no workflow/cheatsheet fence; no rendered-from-project-context section.
   - Target: Sync renders a workflow fence body from a single context struct (project name/type, enabled tools, review config, install/check commands, generated doc list, layout vars) and writes it under a dedicated fence id using `write_fence_body`. Content outside the fence is never modified. If VOSS.md or the fence is absent, sync inserts it; hash integrity and drift refusal behave per existing voss_md semantics.
   - Acceptance: Tests confirm (a) fence inserted when absent, (b) regenerated in place when present, (c) human prose outside the fence byte-identical before/after sync, (d) hash drift in the fence triggers the existing HashMismatch refusal path rather than silent overwrite.

5. **Prompt sync with override** *(stretch within phase — core is R1–R4)*: Reviewer A, Reviewer B, and EM prompts sync into the project as editable copies that override package templates at load time.
   - Current: `reviewer_a_role`, `reviewer_b_system`, `em_system` render from package templates only; no project-level customization.
   - Target: Sync writes these 3 prompts as plain `.md`/`.txt` files (jinja suffix stripped) under a project prompts dir (e.g. `.voss/prompts/`). At runtime the prompt loader prefers the project copy when present, applying lightweight placeholder substitution (string replace, not full Jinja) for runtime variables. Other 7 prompts stay package-internal.
   - Acceptance: With a project copy present, the harness loads the project version (test asserts substituted content from the edited copy); with no project copy, behavior is unchanged from today.

6. **Prompt edit safety (hash-guard)**: Sync never silently clobbers a user-edited prompt.
   - Current: N/A (no synced prompts).
   - Target: Sync records a content hash for each synced prompt. On re-sync, an unedited prompt (hash matches) may be regenerated; an edited prompt (hash drift) is skipped with a warning naming the file; `voss sync --force` overwrites edited prompts.
   - Acceptance: Test edits a synced prompt, re-runs sync → file unchanged + warning emitted; re-runs with `--force` → file regenerated.

## Boundaries

**In scope:**
- `voss sync` CLI command (idempotent regeneration)
- Layout-context derivation module (derive-at-sync, deterministic)
- 3 generated workflow docs in `.voss/docs/` (machine-owned)
- VOSS.md workflow fence rendered from a single context struct (reuses voss_md machinery)
- Synced reviewer/EM prompt copies with load-time override + hash-guard (stretch)
- New Jinja templates under `voss/templates/` for docs and fence body

**Out of scope:**
- Templating for `.voss` language programs — separate concern, unrelated to project docs
- Multi-repo / monorepo workspace orchestration — layout context covers single project only
- AGENTS.md / CLAUDE.md as managed targets — VOSS.md fence is the single managed instruction surface this phase; external-CLI consumption happens via `.voss/docs/` + VOSS.md
- Syncing the other 7 package prompts — smaller drift surface; revisit if demand appears
- Persisted layout config / config-override of derived layout — derive-only this phase; add overrides only if derivation proves wrong somewhere
- `voss init` rework — init keeps scaffolding; sync is the regeneration surface (init MAY call sync, decided at discuss/plan)

## Constraints

- All template rendering goes through `render_package_template` — no second Jinja environment, no ad-hoc `Template(...)` construction.
- Fence writes go through `voss_md.write_fence_body` — no parallel marker system, no regex surgery on VOSS.md.
- Runtime prompt substitution is plain string replacement of named placeholders — deliberately NOT Jinja at runtime, so users can edit synced prompts without Jinja knowledge and StrictUndefined can't detonate on user edits.
- Layout derivation must be deterministic for an unchanged tree (idempotency depends on it).
- Generated docs carry a "generated — do not edit" header comment.

## Acceptance Criteria

- [ ] `voss sync` exists; second consecutive run on unchanged project modifies zero files
- [ ] Layout context derived correctly for repo-root and worktree fixture layouts; deterministic across runs
- [ ] `.voss/docs/` contains cheatsheet, command reference, review workflow — all with generated header
- [ ] Manual edit to a generated doc is overwritten by next sync (machine-owned)
- [ ] VOSS.md workflow fence: inserted when absent, regenerated when present, prose outside fence untouched, drift hits HashMismatch path
- [ ] Synced prompt project copy overrides package template at load time; absent copy = unchanged behavior
- [ ] Edited synced prompt: skipped with warning on sync; overwritten with `--force`
- [ ] All rendering routed through `render_package_template`; all fence writes through `write_fence_body`

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                          |
|--------------------|-------|------|--------|------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Sync + fence + docs core; prompts stretch      |
| Boundary Clarity   | 0.82  | 0.70 | ✓      | VOSS.md only; 3 prompts only; derive-only      |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Single Jinja env; voss_md reuse; no runtime Jinja |
| Acceptance Criteria| 0.80  | 0.70 | ✓      | 8 pass/fail criteria; idempotency anchor       |
| **Ambiguity**      | 0.17  | ≤0.20| ✓      |                                                |

## Interview Log

| Round | Perspective              | Question summary                                | Decision locked                                                        |
|-------|--------------------------|------------------------------------------------|------------------------------------------------------------------------|
| 1     | Researcher               | Managed section target file?                   | VOSS.md fence (new id) — reuse voss_md hash machinery                  |
| 1     | Researcher               | Who consumes generated docs?                   | External CLIs + Voss harness — discoverable `.voss/docs/`              |
| 1     | Researcher               | Layout context source of truth?                | Derive from git/fs at sync time (deterministic; no stale config)       |
| 2     | Researcher               | CLI surface?                                   | New `voss sync` command (init stays scaffold-only)                     |
| 2     | Researcher               | Prompt sync scope?                             | Reviewer A/B + EM only; project copy overrides at load                 |
| 2     | Simplifier               | Irreducible core?                              | Sync + fence + docs; prompt sync = stretch within phase                |
| 3     | Boundary Keeper          | Concrete doc set?                              | 3 docs: cheatsheet, command reference, review workflow                 |
| 3     | Boundary Keeper          | User-edited prompt vs re-sync?                 | Hash-guard: skip + warn; `--force` overwrites                          |
| 3     | Boundary Keeper          | Generated docs edit policy?                    | Machine-owned, always regenerated, "do not edit" header                |

---

*Phase: V16-managed-docs-prompt-generation*
*Spec created: 2026-06-09*
*Next step: /gsd-discuss-phase V16 — implementation decisions (module layout, context struct shape, fence id name, loader override mechanics)*
