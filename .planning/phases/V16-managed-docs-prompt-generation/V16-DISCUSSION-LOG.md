# Phase V16: Managed Docs & Prompt Generation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** V16-managed-docs-prompt-generation
**Areas discussed:** Project facts source, Doc content & voice, Hash-guard state, Sync CLI UX, Jinja integration (user-raised)

---

## Project facts source

| Option | Description | Selected |
|--------|-------------|----------|
| Config + detect fallback | New section in .voss/config.yml; missing keys auto-detected | ✓ |
| Pure auto-detect | Everything probed from fs; wrong guesses unfixable | |
| Pure config | All facts declared; sync errors if missing | |

**User's choice:** Config + detect fallback

Follow-ups:
- Config shape: **single `project:` block** (vs split sections / you-decide) — mirrors fence context struct 1:1
- Detect visibility: **report derived values** in sync output (vs silent)
- Missing fact: **omit section gracefully** via jinja conditionals (vs TODO placeholder / fail sync)
- Tools list semantics: **Voss capabilities** (memory, conventions, review board, eval) (vs external companions / both)

---

## Doc content & voice

| Option | Description | Selected |
|--------|-------------|----------|
| Agent operating guide | Repo facts, .voss/ map, capabilities, do/don't — LLM-targeted | ✓ |
| Human onboarding doc | Prose for developers, agents secondary | |
| Hybrid sections | Half agent, half human | |

**User's choice:** Agent operating guide (cheatsheet)

Follow-ups:
- Command ref: **project-relevant subset**, layout-adjusted invocations (vs full CLI dump)
- Review doc when disabled: **skip file entirely**, fence omits link (vs always render)
- Tone: **imperative directives**, CLAUDE.md-style (vs neutral reference)

---

## Hash-guard state

| Option | Description | Selected |
|--------|-------------|----------|
| Sidecar manifest | .voss/sync-state.json path→sha256; prompt files stay clean | ✓ |
| In-file hash comment | voss_md-style header line per prompt | |
| Git-based detection | Compare vs last sync commit | |

**User's choice:** Sidecar manifest

Follow-ups:
- Manifest missing: **treat existing prompts as edited** — skip + warn, --force re-adopts (vs compare-vs-template-render)
- Manifest VCS: **committed** — deterministic, survives clones (vs gitignored)

---

## Sync CLI UX

| Option | Description | Selected |
|--------|-------------|----------|
| Per-file status lines | written/unchanged/skipped(edited)/fence-updated + facts block + summary | ✓ |
| Summary only | Terse counts | |
| Quiet unless changes | No-op prints nothing | |

**User's choice:** Per-file status lines

Follow-ups:
- `--dry-run`: **yes, this phase** (vs defer)
- Exit codes: **0 unless real error**; warnings ≠ failures (vs distinct code for skips)
- `--force` scope: **prompts only**; fence HashMismatch keeps its own flow, docs always regen (vs everything)

---

## Jinja integration (user-raised via free text)

User asked: "how is Jinja integrated into the implementation of the plan?"

Explained: single sync-time render path through existing `render_package_template` + `SyncContext` dataclass; fence body rendered to string then `write_fence_body`; runtime = string replace only.

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct syntax ${AGENT} | Shell-style runtime tokens; no Jinja collision | ✓ |
| Keep {{ AGENT }} via raw | Brain-dump style; {% raw %} wrapping, two meanings of {{ }} | |
| You decide | Claude picks at plan time | |

**User's choice:** Distinct syntax `${AGENT}` / `${PROJECT}` / `${WORKSPACE}`

---

## Claude's Discretion

- Fence id name (e.g. `id=workflow`)
- Module layout (`voss/sync.py` vs harness placement) + CLI registration wiring
- Exact detection probes per project type
- Manifest JSON schema details
- Prompt-loader override mechanics

## Deferred Ideas

None — discussion stayed within phase scope.
