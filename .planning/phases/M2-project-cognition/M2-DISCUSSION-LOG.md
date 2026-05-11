# Phase M2: Project Cognition - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-10
**Phase:** M2-project-cognition
**Areas discussed:** Analyze + index lifecycle, Cognition file schemas, Session move + per-run ledger, Context injection on resume

---

## Analyze + index lifecycle

### How does repo analysis get triggered + invoked?

| Option | Description | Selected |
|--------|-------------|----------|
| Built-in `/analyze` slash command | REPL `/analyze` skill; natural-language `analyze repo` routes to it. No auto-trigger. | ✓ |
| Auto on first session + `/analyze` refresh | Bootstrap on first launch with no `.voss/`; refresh via `/analyze`. | |
| Pure natural-language, agent self-decides | Agent reads architecture.md; writes/updates as part of normal turn. | |
| `.voss` workflow file | Analyze is a `.voss` program (`voss/skills/analyze.voss`) the harness runs. | |

**User's choice:** Built-in `/analyze` slash command.
**Notes:** User clarified that bare `voss` launches a Claude-Code-style REPL. `analyze` is a natural-language request inside the REPL, not a separate CLI verb. The `.voss` language is the long-term control plane (M4) but M2 ships Python. Original question (auto vs explicit vs doctor-hint) was reframed accordingly.

### What `.voss/architecture.md` should contain after `/analyze`?

| Option | Description | Selected |
|--------|-------------|----------|
| Compact human-readable digest (~1–2 pages) | Project name/type, language, entry points, module map, deps, testing. Loads fully into next system prompt. | ✓ |
| Layered — short summary + appendix | Digest plus full module tree, dep graph, file counts as appendix. | |
| Free-form agent prose | Agent decides shape per repo. | |
| Strict schema sections | Fixed H2 sections agent fills. | |

**User's choice:** Compact human-readable digest.
**Notes:** None.

### How does Voss detect stale architecture.md + how rebuild?

| Option | Description | Selected |
|--------|-------------|----------|
| Git-hash watermark + REPL hint | Frontmatter stores git HEAD sha + file-count; REPL prints `cognition stale — /analyze to refresh`. User decides. | ✓ |
| Agent self-check at turn start | Every turn does drift check; agent volunteers to re-run analyze. | |
| Doctor-only check | `voss doctor` reports staleness; no REPL nag. | |
| No detection — user owns it | Cognition is a snapshot; treat like README. | |

**User's choice:** Git-hash watermark + REPL hint.
**Notes:** None.

### What shape should `.voss-cache/repo.idx` take?

| Option | Description | Selected |
|--------|-------------|----------|
| Simple JSON file manifest | path/size/mtime/sha via `git ls-files`. No semantic search. | ✓ |
| Manifest + ripgrep symbol cache | Adds per-file symbol index via ctags/tree-sitter. | |
| Skip index for M2 | Tools use `git ls-files` + ripgrep live each call. | |
| Manifest now, embeddings later | Versioned header reserves space for semantic index. | |

**User's choice:** Simple JSON file manifest.
**Notes:** CONTEXT.md preserves the versioned-header idea anyway so M3+ embeddings won't require a schema break.

---

## Cognition file schemas

### Who writes which cognition files?

| Option | Description | Selected |
|--------|-------------|----------|
| Agent writes everything, human edits in place | Agent bootstraps + updates all files via fs_write. | ✓ |
| Agent writes outputs, human owns config | Agent: architecture/plans/decisions/sessions. Human: project.json + 3 YAMLs. | |
| `voss init` scaffolds, agent appends only | `voss init` lays defaults; agent only appends. | |
| Human authors all, agent reads only | Pure config model. | |

**User's choice:** Agent writes everything, human edits in place.
**Notes:** None.

### Schema for the three config YAMLs?

| Option | Description | Selected |
|--------|-------------|----------|
| Tight schemas, validated on load | Pydantic-validated; fails loudly on malformed config. | ✓ |
| Loose key/value, agent interprets | Free-form maps. | |
| Tight + agent-extensible | Core fields validated; agent can add `notes:` block. | |
| Defer schemas, ship empty files | Stubs only, pin schemas in M3. | |

**User's choice:** Tight schemas, validated on load.
**Notes:** None.

### Naming + structure for plans/ and decisions/?

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp-id + slug, markdown w/ frontmatter | `plans/2026-05-10-add-github-oauth.md` w/ id/status/related_session/confidence. | ✓ |
| Numbered ADR-style | `decisions/0001-use-keychain.md`. | |
| Hash id, no slug | `plans/p_a1b2c3.md`. | |
| Single rolling files | Append-only `PLANS.md` / `DECISIONS.md`. | |

**User's choice:** Timestamp-id + slug.
**Notes:** None.

### Git tracking for `.voss/` — what's committed vs ignored?

| Option | Description | Selected |
|--------|-------------|----------|
| Commit cognition, ignore sessions/cache | Committed: project.json, architecture.md, 3 YAMLs, plans/, decisions/. Ignored: sessions/, cache. | ✓ |
| Commit only configs + architecture | Plans/decisions stay private until promoted. | |
| Ignore everything in `.voss/` | Cognition is per-user. | |
| User decides, Voss writes neither | No automation. | |

**User's choice:** Commit cognition, ignore sessions/cache.
**Notes:** None.

---

## Session move + per-run ledger

### Sessions location migration

| Option | Description | Selected |
|--------|-------------|----------|
| Hard cut to `.voss/sessions/`, old sessions stay readable | Per-project new path; `voss sessions --all` reads legacy read-only. No auto-migration. | ✓ |
| Dual-write transition | Sessions write to both locations until v0.2. | |
| One-time migration on first `/analyze` | Move matching-cwd sessions automatically. | |
| Per-project from now on, global frozen | Legacy via `voss sessions --legacy`; no auto-migration ever. | |

**User's choice:** Hard cut, old sessions stay readable.
**Notes:** None.

### Where does the COG-08 per-run ledger live?

| Option | Description | Selected |
|--------|-------------|----------|
| Embedded in session JSON as `runs` field | `SessionRecord.runs: list[RunRecord]`. Decisions also mirrored to `decisions/*.md`. | ✓ |
| Separate `.voss/runs/<session>-<turn>.json` files | One file per turn. | |
| Session JSON + decisions/ only | Same as selected option (duplicate). | |
| Markdown-only run summary | `.voss/runs/2026-05-10-<slug>.md`. | |

**User's choice:** Embedded in session JSON as `runs` field.
**Notes:** None.

### How is the run record populated each turn?

| Option | Description | Selected |
|--------|-------------|----------|
| Harness tracks mechanical, agent fills semantic fields | Harness auto-captures inspected/changed/validation/failures/diff. Agent self-reports goal/plan/avoided/assumptions/decisions/risks/follow-ups. | ✓ |
| Agent fills everything in a closing `record_run` tool call | Full discretion to agent. | |
| Harness mechanical, semantic optional | Mechanical always; semantic if agent volunteers. | |
| Plan schema extension | Extend Plan pydantic model with COG-08 fields. | |

**User's choice:** Harness mechanical, agent semantic.
**Notes:** CONTEXT.md notes the agent still uses a `record_run` closing tool call to deliver semantic fields — chosen option is the split, not the abolition of the closing call.

### How does agent declare "avoided" files?

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit `avoided` field in run record | Agent self-reports with optional `why` per entry. | ✓ |
| Inferred from grep/glob hits not read | Mechanical diff of seen-vs-opened. | |
| Both — inferred + explicit override | Mechanical baseline + agent additions. | |
| Drop the field for M2 | Defer COG-08 partial compliance. | |

**User's choice:** Explicit field in run record.
**Notes:** None.

---

## Context injection on resume

### What auto-loads into the agent's context at every turn?

| Option | Description | Selected |
|--------|-------------|----------|
| architecture.md digest only | Full digest + constraints.yml every turn. Decisions/plans on demand via fs_read. | ✓ |
| Architecture + last 3 decisions + open plans | Adds ~2–3k tokens per turn. | |
| Architecture + tool-accessible cognition | Lazy `cognition_search` tool. | |
| Nothing auto — agent must read files | Pure; risks agent forgetting cognition exists. | |

**User's choice:** architecture.md digest only.
**Notes:** None.

### What additional context does `voss resume <id>` inject?

| Option | Description | Selected |
|--------|-------------|----------|
| Full prior session transcript + last run record | Rehydrate EpisodicMemory + inject most recent RunRecord. | ✓ |
| Just follow-ups + open decisions | Drop transcript; rely on cognition. | |
| Transcript + full run history | All RunRecords. Risk: context budget blowout. | |
| User picks at resume time | Prompt at `voss resume`. | |

**User's choice:** Full prior transcript + last run record.
**Notes:** None.

### Token budget shape for cognition injection?

| Option | Description | Selected |
|--------|-------------|----------|
| Reserve fixed 6k for cognition out of 60k turn budget | 6k for system prompt + architecture + constraints. Overflow hint surfaces. | ✓ |
| Dynamic — trim architecture to fit | Trim appendix sections in header order. | |
| No reservation; agent gets whatever fits | Cheap; surfaces oversized cognition immediately. | |
| Configurable in validation.yml | User tunes per project. | |

**User's choice:** Fixed 6k reservation.
**Notes:** None.

### How does agent surface cognition use?

| Option | Description | Selected |
|--------|-------------|----------|
| Renderer shows `cognition: architecture (1.2k) + 2 constraints` line at turn start | One dim line; NDJSON `cognition_loaded` event. | ✓ |
| Only on `--verbose` or `/why` | Quiet default. | |
| Plan rationale references cognition explicitly | In-plan provenance. | |
| Defer transparency to M3+ | Reduce scope. | |

**User's choice:** Renderer one-line status.
**Notes:** None.

---

## Claude's Discretion

- Exact `/analyze` agent prompt + how the agent is instructed to keep architecture.md inside the 1–2 page budget.
- Whether to expose `--no-cognition` flag on `voss do` for benchmarking.
- Concrete drift threshold tuning (20 commits / 10% file count / 7 days starting values).
- `RunRecorder` API shape (collaborator vs context manager around `run_turn`).
- Whether `record_run` is a publicly listed tool vs a privileged closing call.
- Extending M1's schema-allowlist redaction guarantee to `RunRecord`.
- Backward-compat for `SessionRecord.runs` on legacy sessions.
- `.voss/permissions.yml` precedence rules vs M1's session-scoped permission gate.

## Deferred Ideas

- Semantic search / embeddings index (M3+).
- `/analyze` authored in `.voss` (M4).
- Auto-migration of legacy sessions.
- Dual-write to old + new session paths.
- Auto-load decisions/plans into every turn.
- Mechanical inference of `avoided` files.
- Auto-rebuild architecture.md on git change.
- `voss doctor` triggers re-analyze inline.
- Per-run `.voss/runs/<id>.json` separate files.
- Plan persistence on every plan generation (gate behind explicit accept).
- `cognition_search` tool.
- `--no-cognition` flag.
- Cross-project portable cognition (export/import `.voss/`).
