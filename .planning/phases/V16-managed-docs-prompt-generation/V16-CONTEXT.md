# Phase V16: Managed Docs & Prompt Generation (Jinja2 layout-aware doc sync) - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

`voss sync` (re)generates layout-aware workflow docs in `.voss/docs/`, a hash-verified workflow fence in VOSS.md, and project-editable reviewer/EM prompt copies — idempotently, so re-running on an unchanged project is a no-op.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**6 requirements are locked.** See `V16-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V16-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):** `voss sync` CLI command (idempotent regeneration); layout-context derivation module (derive-at-sync, deterministic); 3 generated workflow docs in `.voss/docs/` (machine-owned); VOSS.md workflow fence rendered from a single context struct (reuses voss_md machinery); synced reviewer/EM prompt copies with load-time override + hash-guard (stretch); new Jinja templates under `voss/templates/`.

**Out of scope (from SPEC.md):** templating for `.voss` language programs; multi-repo/monorepo orchestration; AGENTS.md/CLAUDE.md as managed targets; syncing the other 7 package prompts; persisted layout config / config-override of derived layout; `voss init` rework (init MAY call sync — planner decides).

</spec_lock>

<decisions>
## Implementation Decisions

### Project facts source
- **D-01:** Project facts (type, install/check commands, tools, review config) come from a new single `project:` block in the existing `.voss/config.yml`; missing keys auto-detected from the filesystem (pyproject → python, package.json → node, etc.). Config wins over detection.
- **D-02:** `project:` block shape mirrors the fence context struct 1:1: `{type, install_command, check_command, tools: [...], review: {enabled, reviewers}}`.
- **D-03:** Sync output reports auto-detected values explicitly (e.g. `project.type: python (detected)`) so users know what to pin in config when detection is wrong.
- **D-04:** Missing/undetectable facts are omitted gracefully via Jinja `{% if %}` blocks. The context struct always carries explicit values or absent-markers — StrictUndefined still catches genuine template bugs.
- **D-05:** "Enabled tools" = Voss capabilities active in this project (memory, conventions extraction, review board, eval), detected from config + `.voss/` dirs. Not external third-party tooling.

### Doc content & voice
- **D-06:** Cheatsheet is an agent operating guide: repo layout facts, where things live (`.voss/`, VOSS.md fences), active Voss capabilities, do/don't conventions. Terse, imperative, written for LLM consumption.
- **D-07:** Command reference covers only the project-relevant subset of voss commands, with layout-adjusted invocations (correct interpreter path, cwd prefixes). Not a full CLI dump.
- **D-08:** Review workflow doc is skipped entirely when `review.enabled` is false; the fence omits its link. Doc set is 2–3 files depending on config.
- **D-09:** Doc tone = imperative directives, CLAUDE.md-style ("Use X. Never Y. Run Z before W.").

### Hash-guard state
- **D-10:** Synced-prompt content hashes live in a sidecar manifest `.voss/sync-state.json` (path → sha256), written by sync. Prompt files stay clean plain text. The manifest is also the natural home for doc/fence bookkeeping.
- **D-11:** When the manifest is missing (fresh clone, deleted), existing prompt files are treated as edited: skip + warn, `--force` to re-adopt. Never clobber without hash evidence.
- **D-12:** `.voss/sync-state.json` is committed to the repo — content is deterministic (sync is idempotent), so no churn; edit-detection survives clones.

### Sync CLI UX
- **D-13:** Output = per-file status lines (`written` / `unchanged` / `skipped (edited)` / `fence-updated`) plus a detected-facts block and a trailing summary count. Greppable, CI-friendly.
- **D-14:** `voss sync --dry-run` ships this phase: prints would-be statuses, writes nothing (same diff pass as the real run).
- **D-15:** Exit code 0 for all non-error outcomes (changes, no-changes, skipped-edited). Only real failures (fence HashMismatch, IO errors) exit nonzero. Warnings ≠ failures.
- **D-16:** `--force` applies to synced prompts only. Fence HashMismatch resolution stays in its existing flow (`voss memory adopt` per voss_md semantics); docs are always regenerated regardless.

### Jinja integration
- **D-17:** All rendering is sync-time via the existing `render_package_template` ("voss" package, cached Environment, StrictUndefined). Sync builds one `SyncContext` dataclass (layout vars + project facts + capabilities), renders each artifact, diffs against disk, applies per-artifact write policy, updates the manifest. Fence body is rendered to a string then written through `voss_md.write_fence_body` — Jinja never touches VOSS.md structure.
- **D-18:** Runtime placeholders in synced prompts use distinct shell-style syntax: `${AGENT}`, `${PROJECT}`, `${WORKSPACE}` — filled by plain string replace at prompt-load time. No Jinja collision (no `{% raw %}` gymnastics), visually distinct: `{{ }}` = sync-time, `${}` = runtime.

### Claude's Discretion
- Fence id name (e.g. `id=workflow`), module layout (`voss/sync.py` vs harness placement), CLI registration wiring, exact detection probes per project type, manifest JSON schema details, prompt-loader override mechanics.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase requirements
- `.planning/phases/V16-managed-docs-prompt-generation/V16-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/seeds/managed-docs-generation.md` — Original seed: motivation, scope sketch, open questions (now resolved)

### Existing machinery (reuse, do not duplicate)
- `voss/template_render.py` — The single Jinja entrypoint (`render_package_template`); all V16 rendering goes through it
- `voss/harness/voss_md.py` — VOSS.md fence format owner: `write_fence_body`, `read_fence_body`, `HashMismatch` semantics (D-05/D-07/D-08 docstrings)
- `voss/cli.py` (`_scaffold_target`, ~line 444–495) — Existing init template-rendering pattern + CLI command registration style
- `voss/harness/conventions.py` (`_load_memory_config`) — Existing `.voss/config.yml` loading precedent for the new `project:` block
- `voss/templates/prompts/` — `reviewer_a_role.txt.jinja`, `reviewer_b_system.txt.jinja`, `em_system.txt.jinja` are the 3 prompts to sync; `voss/harness/agent.py` shows their current runtime render sites

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `render_package_template`: cached Jinja Environment per package (StrictUndefined, trim/lstrip blocks, keep_trailing_newline) — V16 adds templates, not machinery
- `voss_md.write_fence_body` / `read_fence_body`: marker + sha256 integrity + drift refusal — the managed-section engine already exists
- `.voss/config.yml` loader pattern in conventions.py: yaml.safe_load, never raises — extend for `project:` block

### Established Patterns
- Init rendering loop in `_scaffold_target`: template-name map → render → path-traversal guard → write. Sync's write loop should mirror it (plus diff/skip logic)
- voss_md philosophy: machine writes refuse on hash drift rather than silently overwriting — D-11's "treat missing state as edited" extends the same principle to prompts

### Integration Points
- New `voss sync` command registers on the unified `voss` click group (`voss/cli.py` `main`)
- Prompt-loader override hooks into `voss/harness/agent.py` render sites for the 3 synced prompts (project copy + `${}` substitution when present; package template path unchanged otherwise)
- Fence insertion must handle VOSS.md absent (create with fence) and present-without-fence (append fence) — coordinate with existing `ensure_migrated` behavior

</code_context>

<specifics>
## Specific Ideas

- Two-stage prompt rendering: sync-time Jinja bakes project facts into the synced prompt; runtime fills `${AGENT}`/`${PROJECT}`/`${WORKSPACE}` via string replace. Users edit synced prompts without knowing Jinja.
- Generated docs carry a "generated — do not edit" header; customization belongs in VOSS.md prose, not generated docs.
- Sync output doubles as detection feedback loop: derived facts printed so users can pin them in config.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: V16-managed-docs-prompt-generation*
*Context gathered: 2026-06-09*
