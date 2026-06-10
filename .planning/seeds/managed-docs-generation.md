---
title: Managed Docs & Prompt Generation (Jinja2 layout-aware doc sync)
trigger_condition: voss init/sync needs to emit per-project agent docs, OR a managed AGENTS.md/CLAUDE.md section is needed, OR reviewer/agent prompts need per-project customization.
planted_date: 2026-06-09
related: [[agent-capability-surface]], [[project-memory-voss-md]]
---

## Summary

Extend Voss's existing Jinja2 template infrastructure (`voss/template_render.py`, `voss/templates/`) into a full doc/prompt generation system: layout-aware workflow docs written into projects at init/sync time, an idempotent managed section in the project's agent instruction file, and runtime-substituted agent/reviewer prompt templates.

## Why

Voss already renders `templates/init/*` during `voss init`, but there is no story for (a) keeping generated docs in sync with project layout after init, (b) owning a regenerable block inside AGENTS.md/CLAUDE.md without clobbering user content, (c) parameterizing agent/reviewer prompts per project. These are the glue that makes Voss feel installed-into a project rather than run-against it.

## Scope sketch (not a plan — for trigger-time scoping)

Four parts:

1. **Template rendering core** — already exists (`render_package_template`, StrictUndefined, PackageLoader). Extend as needed; keep single entrypoint.
2. **Layout-aware workflow docs** — templates compiled with a layout-variables context (repo-root vs worktree layout, command prefixes, workspace paths) and written into the project (e.g. `.agents/voss/*.md` or equivalent) during init and a new `voss sync` operation. Sync is idempotent: re-running regenerates from current config.
3. **Managed section in agent instruction file** — marker-delimited block (`<!-- voss:managed-start/end -->`) in AGENTS.md/CLAUDE.md, regenerated from a single context struct: project name/type, enabled companion tools, review config, install/check commands, generated doc list, layout vars. Never touches content outside markers; inserts block if absent.
4. **Agent/reviewer prompt templates** — synced into the project as plain `.md` (jinja suffix stripped), then lightweight runtime placeholder substitution (`{{ AGENT }}`, `{{ PROJECT }}`, `{{ WORKSPACE }}`) via simple string replace before prompt delivery to the LLM. Deliberately not full Jinja at runtime — users can edit synced prompts without knowing Jinja.

Voss-native architecture throughout: Python + Jinja2, one context dataclass, no external tool references.

## Non-goals (at trigger time)

- Templating for `.voss` language programs (separate concern).
- Multi-repo / monorepo workspace orchestration.

## Open questions

- Where does the layout context come from — derive from git/fs at sync time, or persist in voss config?
- AGENTS.md vs CLAUDE.md vs both: detect existing file, or config-driven target?
- Does `voss sync` become a new CLI command or fold into `voss init --sync`?
- Do prompt placeholders stay String.replace-simple, or reuse Jinja with a restricted env?

## Breadcrumbs

- `voss/template_render.py` — existing Jinja2 entrypoint (Environment cache, StrictUndefined).
- `voss/cli.py:458-471` — `voss init` already iterates `templates/init/*` through `render_package_template`.
- `voss/templates/` — 11 existing template categories incl. `prompts/`, `agent/`, `init/`.
- `voss/harness/conventions.py` — likely home for layout/convention detection.

## Promotion path

When trigger fires: `/gsd-spec-phase` → CONTEXT.md direct from SPEC (per [[gsd-spec-then-context-direct]]) → `/gsd-plan-phase`. Likely single phase; managed-section idempotency tests are the verification anchor.
