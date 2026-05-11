# Phase M2: Project Cognition - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

M2 makes Voss remember project facts across sessions. It introduces the durable `.voss/` project brain and the rebuildable `.voss-cache/` index, wires a `/analyze` slash command into the M1 REPL that produces those artifacts, persists per-turn run records (COG-08), moves session storage from the global `~/.local/state/voss/sessions/` to the per-project `.voss/sessions/`, and auto-injects a slice of the project brain into every agent turn so repeated sessions improve from stored context rather than starting cold.

**In scope:**
- New REPL slash command `/analyze` (compiled-in, Python — not yet `.voss`). Routes natural-language `analyze repo` to the same handler.
- Generate / refresh on `/analyze`:
  - `.voss/project.json` — project metadata (name, type, primary language, entry points).
  - `.voss/architecture.md` — compact human-readable digest (~1–2 pages) with git-hash watermark in frontmatter.
  - `.voss/constraints.yml`, `.voss/permissions.yml`, `.voss/validation.yml` — pydantic-validated config files with sane defaults.
  - `.voss-cache/repo.idx` — simple JSON file manifest (path/size/mtime/sha) via `git ls-files`.
  - `.voss/.gitignore` — pre-written to commit cognition + ignore sessions/cache.
- Per-turn run record persistence (COG-08) embedded in `SessionRecord.runs: list[RunRecord]`. Harness auto-captures mechanical fields; agent self-reports semantic fields.
- `decisions/*.md` mirror — when agent reports a decision in a RunRecord, harness also writes a standalone markdown file (timestamp-id + slug + YAML frontmatter linking back to session id).
- `plans/*.md` — when agent writes a plan (M1's `Plan` model surfaces it; M2 persists it on user accept/explicit save) using the same naming + frontmatter convention.
- Session storage hard cut to `.voss/sessions/<id>.json`. `voss sessions` lists current project; `voss sessions --all` (or `--global`) reads legacy `~/.local/state/voss/sessions/` read-only. No auto-migration.
- Cognition auto-injection: at every turn start, system prompt includes `architecture.md` digest + `constraints.yml` rules. Reserve fixed 6k tokens within the 60k turn budget for this. `voss resume <id>` additionally rehydrates full prior transcript (existing behavior) plus the most recent RunRecord as "prior context."
- Renderer surfaces cognition use: one-line dim status `cognition: architecture (1.2k) + 2 constraints` at turn start; NDJSON emits a `cognition_loaded` event.
- Drift detection: on REPL launch, compare git HEAD sha + file-count to `architecture.md` frontmatter snapshot; print `cognition stale — /analyze to refresh` hint when drift exceeds threshold. User decides; no auto re-analyze.
- `voss doctor` extends M1 checks to include `.voss/` existence + cognition staleness (informational warnings, not blockers).

**Out of scope (deferred to other phases):**
- `.voss` language samples and `voss check`/`voss run` validation — M3.
- Authoring `/analyze` (or any cognition skill) in `.voss` itself — M4. M2's `/analyze` is Python.
- Semantic search / embeddings index — M3+. M2 ships file manifest only with a versioned header so embeddings can land later without a schema break.
- Cross-session decision search / queryable cognition CLI — deferred (`cognition_search` tool considered, rejected for M2).
- Auto-migration of pre-M2 sessions from `~/.local/state/voss/sessions/` into per-project dirs — deferred. Legacy sessions stay readable in place via `voss sessions --all`.
- Dual-write to both old and new session paths — explicitly rejected.
- Eval / golden-task hooks — M5.

</domain>

<decisions>
## Implementation Decisions

### `/analyze` command + analysis lifecycle
- **D-01:** Repo analysis is triggered exclusively by a built-in REPL slash command `/analyze`. The natural-language router (M1's intent classifier inside `agent.py`) maps phrases like `analyze repo`, `analyze this project`, `update project memory` to the same handler. No auto-trigger on first launch; no agent-self-invocation mid-turn.
- **D-02:** `/analyze` is a compiled-in Python skill in M2 (lives at `voss/harness/skills/analyze.py` or similar). Dogfooding to `.voss` is M4's problem. The slash-command registry in `voss/harness/cli.py:_run_repl` gains a `/analyze` entry alongside M1's `/login`, `/model`, `/mode`.
- **D-03:** `.voss/architecture.md` is a **compact human-readable digest (~1–2 pages)**. Required sections (in order): project name/type, primary language(s), entry points, module map (5–10 dirs with one-line purpose each), key dependencies, testing approach. Concise enough to fit fully into the next system prompt. No exhaustive file listings, no appendix, no per-file dependency graph — those are deferred.
- **D-04:** Architecture.md YAML frontmatter MUST include `git_head: <sha>`, `analyzed_at: <ISO>`, `file_count: <int>`, `analyzer_version: 1`. Drift detection on REPL launch compares git HEAD + file count to frontmatter. Threshold: HEAD diverged by ≥20 commits OR file count drifted by ≥10% OR ≥7 days elapsed. On drift, REPL prints `cognition stale (HEAD +N commits, ±M files) — /analyze to refresh` and continues. No auto re-analyze, no blocking prompt.
- **D-05:** `.voss-cache/repo.idx` is a **simple JSON file manifest**: `{ "version": 1, "git_head": "<sha>", "files": [{"path", "size", "mtime", "sha"}, ...] }`. Built from `git ls-files` (falls back to walking cwd minus `.gitignore` when not a git repo). Rebuilds on `/analyze`. No embeddings, no symbol cache, no ctags/tree-sitter dependency for M2. Versioned header reserves room for future semantic index.

### Cognition file authorship + git tracking
- **D-06:** **Agent writes all cognition files** through the existing `fs_write` tool (subject to M1's permission gate). Bootstrapping happens during `/analyze`'s turn. Humans edit files in place between sessions; agent re-reads on next turn. No human-only-writable files in M2.
- **D-07:** `.voss/constraints.yml`, `.voss/permissions.yml`, `.voss/validation.yml` use **tight pydantic-validated schemas**:
  - `constraints.yml`: `rules: list[{forbid?: list[str], require_tests_for?: list[glob], max_file_size_lines?: int, custom?: str}]`.
  - `permissions.yml`: `tool_policy: {allow: list[str], deny: list[str]}`, `path_scopes: list[{glob: str, modes: list[plan|edit|auto]}]`. Layered on top of M1's `PermissionGate` — project-level rules join the session gate at REPL startup.
  - `validation.yml`: `commands: list[{name: str, run: str, on: [save|pre_apply|post_run]}]`. Replaces hardcoded `voss_check` triggers.
  - Malformed YAML fails loudly at REPL startup with a pointer to the offending file + line. No silent fallback.
- **D-08:** Plans + decisions use **timestamp-id + slug**, markdown with YAML frontmatter:
  - Filename: `plans/YYYY-MM-DD-<slug>.md`, `decisions/YYYY-MM-DD-<slug>.md`. Slug is kebab-case from the agent-supplied title.
  - Frontmatter fields (required): `id` (matches filename minus extension), `status` (`open`/`approved`/`done`/`abandoned` for plans; `active`/`superseded` for decisions), `related_session` (session id), `confidence` (0.0–1.0, from `ProbableValue`), `created_at`.
  - Body is agent-authored markdown. No fixed sections (free-form prose under the frontmatter).
  - On filename collision (same day, same slug), append `-2`, `-3`, etc.
- **D-09:** `.voss/.gitignore` is written by Voss on first `/analyze`. Contents:
  ```
  # voss session state and rebuildable cache
  sessions/
  ```
  Committed: `project.json`, `architecture.md`, `constraints.yml`, `permissions.yml`, `validation.yml`, `plans/`, `decisions/`. Ignored: `sessions/`. Project-root `.gitignore` gets `.voss-cache/` appended (idempotent; only if not already present).

### Session storage migration
- **D-10:** **Hard cut** to `.voss/sessions/<id>.json`. New sessions write only to the per-project path scoped to the cwd at session start. No dual-write. No auto-migration of legacy sessions.
- **D-11:** `voss sessions` (no flag) lists sessions whose `cwd` equals the current cwd (or lives under it) and resides under `.voss/sessions/`. New flag `voss sessions --all` (alias `--global`) additionally reads `~/.local/state/voss/sessions/*.json` and tags rows `[legacy]`. `voss resume <id>` resolves through both locations (legacy is read-only).
- **D-12:** Pre-M2 sessions remain in `~/.local/state/voss/sessions/` indefinitely, readable. Documented as a one-line note in `voss doctor` output if any are found: `legacy sessions detected at ~/.local/state/voss/sessions/ (read-only via voss sessions --all)`.

### Per-turn run ledger (COG-08)
- **D-13:** Per-run ledger is **embedded in the session JSON** as a new `runs: list[RunRecord]` field on `SessionRecord`. Each agent turn appends one `RunRecord`. No separate `.voss/runs/` directory. Decisions are additionally mirrored to standalone `decisions/*.md` (per D-08).
- **D-14:** `RunRecord` schema (dataclass, allowlist-serialized like `SessionRecord`):
  ```
  id: str                     # turn-uuid
  started_at: str
  ended_at: str
  goal: str                   # agent-reported
  plan: dict | None           # serialized Plan
  inspected: list[str]        # auto: paths from fs_read/fs_glob/fs_grep
  changed: list[str]          # auto: paths from fs_write/fs_edit
  avoided: list[{path: str, why: str}]  # agent-reported, explicit
  assumptions: list[str]      # agent-reported
  decisions: list[{title: str, body: str, confidence: float}]  # agent-reported; mirrors to decisions/*.md
  risks: list[str]            # agent-reported
  validation: list[{cmd: str, exit: int, summary: str}]  # auto: voss_check + shell_run results
  failures: list[{tool: str, error: str}]                 # auto: tool errors caught in run_turn
  diff_summary: str           # auto: git_diff stat at turn end
  follow_ups: list[str]       # agent-reported
  cost_usd: float
  ```
- **D-15:** Mechanical fields (`inspected`, `changed`, `validation`, `failures`, `diff_summary`, `cost_usd`, timestamps) are populated by the harness inside `run_turn` via a new `RunRecorder` collaborator that observes tool invocations. Semantic fields (`goal`, `plan`, `avoided`, `assumptions`, `decisions`, `risks`, `follow_ups`) are populated by the agent via a new mandatory `record_run` closing tool call that the planning prompt instructs the agent to make at turn end. If the agent fails to call `record_run`, the harness emits a warning and writes the RunRecord with mechanical fields only (semantic fields empty).
- **D-16:** `avoided` is an **explicit agent-reported field**, not inferred. Format: `[{path: str, why: str}]`. Free-form `why` (one short sentence). Mechanical inference from grep/glob hits not opened is deferred — proved too noisy to ship in M2.

### Cognition auto-injection
- **D-17:** Every turn auto-injects: **architecture.md (full)** + **constraints.yml (rendered as a bullet list of rules)** into the system prompt, prepended before `PLAN_SYSTEM`. Plans and decisions are NOT auto-loaded — agent reads via `fs_read` if needed.
- **D-18:** Token budget: reserve a **fixed 6,000 tokens** for cognition out of the 60,000 turn `ContextScope` budget. The 6k covers `PLAN_SYSTEM` + architecture digest + constraints rules. If the rendered cognition block exceeds 6k, the harness logs `cognition_overflow` and truncates the constraints list first (keeps architecture intact). User-visible hint surfaces: `architecture.md is X tokens (over 6k budget) — /analyze can rewrite a tighter digest`.
- **D-19:** `voss resume <id>` injects (in addition to baseline): full prior transcript (rehydrate `EpisodicMemory` — existing M1 behavior) AND a "Prior context" block in the system prompt containing the most recent `RunRecord`'s `goal`, `plan`, `decisions`, `follow_ups`, and `risks`. Agent picks up where it left off.
- **D-20:** Renderer prints a one-line dim status at turn start: `cognition: architecture (1.2k) + 2 constraints` (Tty/Plain renderers). NDJSON renderer emits a `cognition_loaded` event with `{architecture_tokens, constraints_count, plans_loaded: 0, decisions_loaded: 0}`. Behind `--quiet`, the Tty line is suppressed.

### Claude's Discretion
- Exact `/analyze` agent prompt + how the agent is instructed to keep architecture.md inside the 1–2 page budget — pick what reads well; iterate on real repos.
- Whether to expose a `--no-cognition` flag for `voss do` to skip injection (useful for benchmarking) — pick the simplest default; add if testing demands it.
- Concrete drift threshold tuning (the 20 commits / 10% file count / 7 days numbers in D-04) — start with these, adjust after dogfooding.
- `RunRecorder` API shape (collaborator object vs. context manager around `run_turn`) — pick what minimizes diff to existing `agent.py:run_turn`.
- Whether `record_run` is exposed in the public tool list visible to the agent vs. a privileged "closing" call dispatched by the harness — pick whichever yields more reliable semantic-field population.
- How aggressively to redact secrets that might surface in mechanical fields (e.g., paths containing tokens, validation command outputs) — extend M1's schema allowlist to `RunRecord`; same redaction guarantee, same test pattern as `tests/harness/test_session_redaction.py`.
- Backward-compat for `SessionRecord.runs` on legacy sessions (default to `[]` when absent in JSON) — straightforward; pick the obvious default.
- `.voss/permissions.yml` interaction with M1's session-scoped permission gate — design so project rules layer additively (deny wins over allow); spell out conflict precedence when implementing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v0.1 scope and product framing
- `.vscode/voss_v_0_1_scope_lock.md` §"2. Persistent Project Cognition", §"M2: Project Cognition" — Source of truth for `.voss/` vs `.voss-cache/` split and what cognition must include.
- `.planning/PROJECT.md` — Active requirements, key decisions (`.voss/` durable / `.voss-cache/` rebuildable), constraints.
- `.planning/REQUIREMENTS.md` §"Project Cognition" — Specifically COG-01..08 (the requirement IDs M2 owns).
- `.planning/ROADMAP.md` §"Phase M2: Project Cognition" — Phase goal, success criteria, cross-cutting constraints.
- `.planning/HARNESS-PLAN.md` §"M2: Project Cognition" — Original cognition outline; M2 implements the harness-led version.

### Prior phase decisions (carry forward)
- `.planning/phases/M1-harness-happy-path/M1-CONTEXT.md` — Specifically D-15 (M1 deferred session move to M2), D-16 (schema-allowlist redaction — extend to `RunRecord`), D-17 (redaction test pattern — extend to run records).
- `.planning/phases/M1-harness-happy-path/M1-DISCUSSION-LOG.md` — Background on why session move was deferred.

### Existing Python harness (parity contract to extend, not rewrite)
- `voss/harness/session.py` (113 LOC) — `SessionRecord`, `_state_dir`, `save`, `load`, `list_sessions`. M2 extends with `runs: list[RunRecord]` field, adds per-project path resolution, keeps allowlist serialization.
- `voss/harness/agent.py` (238 LOC) — `run_turn`, `Plan` schema. M2 wraps with `RunRecorder` for mechanical field capture, adds closing `record_run` tool dispatch.
- `voss/harness/cli.py` (484 LOC) — Click command surface + `_run_repl`. M2 adds `/analyze` slash command, extends `voss sessions` with `--all`/`--global`, extends `voss doctor`.
- `voss/harness/permissions.py` (126 LOC) — `PermissionGate` + persistence. M2 layers `.voss/permissions.yml` as a project-level rule source.
- `voss/harness/tools.py` (170 LOC) — Tool registry with `is_mutating: bool` (M1). M2 adds the `record_run` tool descriptor.
- `voss/harness/sandbox.py` (49 LOC) — cwd path jail. M2 reuses; `.voss-cache/` writes go through it.

### Existing tests (parity contract)
- `tests/harness/test_session.py` — Extend with run-record persistence tests + per-project path tests.
- `tests/harness/test_session_redaction.py` (M1) — Extend pattern scanner to scan `RunRecord` fields too.
- `tests/harness/test_cli.py` — Extend with `/analyze` and `voss sessions --all` cases.

### External, do not re-derive
- `git ls-files` semantics — used by `repo.idx` builder.
- Pydantic v2 model_validate behavior — used for YAML config validation.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`voss/harness/session.py:SessionRecord`** — already allowlist-serialized with `dataclasses.asdict`. M2 adds `runs: list[RunRecord] = field(default_factory=list)`. Same redaction invariant carries over.
- **`voss/harness/session.py:_state_dir`** — single function controls the storage path. M2 replaces it with `_sessions_dir(cwd: Path) -> Path` that returns `<cwd>/.voss/sessions` (and a fallback for legacy reads).
- **`voss/harness/agent.py:run_turn`** — already has tool-invocation loop and result aggregation. Natural insertion points for `RunRecorder` hooks: tool dispatch (`inspected`/`changed`/`validation`/`failures` capture) and turn end (closing `record_run` call + `git_diff` stat).
- **`voss/harness/agent.py:Plan`** — pydantic model. Per-turn plan persistence (`plans/*.md`) writes `Plan.model_dump_json()` plus markdown rationale.
- **`voss/harness/cli.py:_run_repl`** — slash-command registry pattern from M1 (`/login`, `/model`, `/mode`). `/analyze` slots in beside them; uses the same registry helper.
- **`voss/harness/sandbox.py`** — already path-jails writes. `.voss/` writes are inside cwd so they pass without new policy. `.voss-cache/` likewise.
- **`voss/harness/render.py`** — Tty/Plain/Ndjson renderers. Adding the `cognition: …` status line + `cognition_loaded` NDJSON event is a small extension; reuse existing dim-text + event helpers.

### Established Patterns
- **Schema-allowlist redaction** (M1 D-16/D-17) — `SessionRecord` only serializes declared fields; same applies to `RunRecord`. The CI redaction test (`tests/harness/test_session_redaction.py`) extends naturally to scan `RunRecord` fields for secret patterns.
- **Pure resolution functions** — `auth.py:resolve` style: pure function returns a dataclass, harness consumes the dataclass. Apply same shape to `cognition.load(cwd) -> CognitionBundle` (architecture text, constraints, permissions, validation rules).
- **Tool descriptor pattern** — every tool has `name/description/parameters/invoke/is_mutating`. `record_run` is a new tool; `is_mutating=True` (writes to session JSON + decisions/*.md).
- **Tight pydantic schemas with loud failure** — M1 chose strict tier mapping for permission modes (D-05). M2 mirrors that with strict pydantic YAML schemas (no silent fallback).

### Integration Points
- **`run_turn` → `RunRecorder`** — wrap the tool loop with an observer that captures mechanical fields. End-of-turn hook dispatches the `record_run` tool call (closing the turn).
- **`run_turn` → cognition injection** — load `architecture.md` + `constraints.yml` via `cognition.load(cwd)` at the start of `run_turn`, prepend to `PLAN_SYSTEM`. Renderer's pre-turn line reads from the loaded bundle.
- **`cli.py:_run_repl` → `/analyze`** — slash command spawns a special turn whose system prompt instructs the agent to produce architecture.md content. Uses existing `run_turn` plus a stricter response schema for the digest.
- **`cli.py:sessions_cmd` → per-project resolution** — replace `session_store.list_sessions()` callers with `list_sessions(cwd=...)`; add `--all` to merge legacy globs.
- **`doctor_cmd` → cognition checks** — extend the M1 traffic-light table with rows for `.voss/ initialized`, `cognition staleness`, `legacy sessions detected`. Same diagnose-and-suggest stance as M1 (D-13).
- **`voss init` (if exists in compiler CLI)** — if it scaffolds project files, it should NOT bootstrap `.voss/` in M2 — that's `/analyze`'s job. Keep verb separation clear.

</code_context>

<specifics>
## Specific Ideas

- **`/analyze` modeled on slash-command UX in M1** — same registry pattern as `/login`, `/model`, `/mode`. Discoverable from `/help`. Natural-language phrases route to the same handler so users can type either form.
- **Cognition is visible, not magical** — the renderer's one-line `cognition: architecture (1.2k) + 2 constraints` status (D-20) is the v0.1 transparency signal. Users see what's loading without `--verbose`. Loud-but-quiet.
- **Hard cut + read-old-via-flag** — preferred over dual-write or auto-migration. Cleaner mental model: `.voss/sessions/` is the truth from M2 on; legacy is reachable but never mutated.
- **Tight YAML schemas now, not later** — same M1 stance on permission tiers (strict over advisory). Catches malformed config at REPL startup instead of mid-turn.
- **Drift detection is a hint, not a gate** — REPL prints `cognition stale …` and continues. Never blocks the user. Mirrors M1's "doctor diagnose, don't fix."

</specifics>

<deferred>
## Deferred Ideas

- **Semantic search / embeddings index** — `repo.idx` ships as a flat manifest in M2 with a versioned header. Embeddings + `cognition_search` tool revisited in M3+ when language-driven workflows demand it.
- **`/analyze` authored in `.voss`** — explicitly M4. M2 ships Python; dogfooding the harness loop comes after cognition behavior is proven.
- **Auto-migration of legacy sessions** — rejected for M2. Risk of moving sessions for the wrong project. Manual `voss sessions --all` is sufficient.
- **Dual-write to old + new session paths** — rejected. Doubles disk and complicates resume semantics.
- **Auto-load decisions / open plans into every turn** — rejected for M2 budget reasons (would blow the 6k cognition reserve). Agent reads via `fs_read` when relevant.
- **Mechanical inference of `avoided` files** (diff `fs_grep`/`fs_glob` hits vs. `fs_read` opens) — rejected for M2. Too noisy. Explicit agent-reported only.
- **Auto-rebuild architecture.md on git change** — rejected. User runs `/analyze`. Drift hint only.
- **`voss doctor` triggers re-analyze inline** — rejected (mirrors M1 D-13: diagnose, don't fix).
- **Per-run `.voss/runs/<id>.json` separate files** — rejected. Embed in session JSON instead (D-13).
- **Plan persistence on every plan generation** — defer to a `--save-plan` flag or explicit user accept. M2 writes plans only when the user approves or the agent explicitly persists (via a tool call). Avoids `.voss/plans/` clutter from speculative plans.
- **`cognition_search` tool** — deferred to M3+ once cognition volume warrants search.
- **`--no-cognition` flag for `voss do`** — deferred unless benchmarking demands it.
- **Cross-project / portable cognition (export/import `.voss/`)** — out of scope; `.voss/` is per-repo by design.

</deferred>

---

*Phase: M2-project-cognition*
*Context gathered: 2026-05-10*
