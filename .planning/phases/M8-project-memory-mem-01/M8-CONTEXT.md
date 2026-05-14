# Phase M8: Project Memory (MEM-01) - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

M8 wires the existing `voss_runtime/memory/` primitives into the harness as a
persistent, cross-session project-memory layer with two user-visible surfaces:

1. **Root `VOSS.md`** — a human-editable + machine-managed project guide that
   replaces M2's auto-generated `.voss/architecture.md`. Loaded into the system
   context on every `voss chat` / `voss do` / `voss resume`.
2. **`.voss/memory/` cross-session recall store** — indexes four source types
   (prior-session turns, decisions, user-confirmed conventions, per-run
   changed-file ledgers) and exposes them through four slash commands
   (`/recall`, `/forget`, `/memory`, `/save`) plus a `voss memory vacuum` CLI.

M8 is **harness wiring**. No new runtime memory dataclasses; all persistence
and retrieval routes through `voss_runtime.memory.EpisodicMemory` and
`voss_runtime.memory.SemanticMemory`. Semantic backing via chroma is a soft
dependency (`voss[search]` extra) with a documented keyword-fallback hit-rate
floor.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**7 requirements are locked.** See `M8-SPEC.md` for full requirements,
boundaries, and acceptance criteria.

Downstream agents MUST read `M8-SPEC.md` before planning or implementing.
Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Root `VOSS.md` file convention, loader, and system-context injection.
- Migration of `.voss/architecture.md` content into `VOSS.md` with archive of the original.
- Rewire of COG-02 analyze-skill write path to update the machine section of `VOSS.md`.
- Cross-session recall store under `.voss/memory/` covering four source types: turns, decisions, conventions, changed-file ledgers.
- Auto-triggered conventions extraction at session end with user-confirmation prompt.
- Four new slash commands: `/recall`, `/forget`, `/memory`, `/save`.
- `voss memory vacuum` CLI subcommand.
- Hard size cap + eviction policy.
- Semantic backing via existing `SemanticMemory` (chroma) when `voss[search]` extra installed; keyword fallback otherwise.
- Configuration surface in `.voss/config.yml` for cap value and extraction toggle (`--no-extract` equivalent).

**Out of scope (from SPEC.md):**
- Cross-project memory sharing.
- Cloud-backed memory store.
- TUI browser for memory store (deferred to M9 TUI Shell).
- Multi-agent memory partitioning (deferred to M10).
- Promoting `voss[search]` to default install.
- New runtime memory primitives — M8 is harness wiring only.
- Migrating pre-M8 session JSON files to a new on-disk format — backward compat mandatory.
- Encryption of the memory store.

</spec_lock>

<decisions>
## Implementation Decisions

### Memory storage layout

- **D-01:** **On-disk source of truth = per-source dirs of files** under `.voss/memory/`:
  - `turns/<session_id>.jsonl` — one line per turn `{ts, role, content, turn_idx}`.
  - `decisions/` — symbolic-link or mirror of existing `.voss/decisions/*.md` (planner picks the cheapest pointer; no duplication).
  - `conventions/YYYY-MM-DD-<slug>.md` — user-accepted convention entries (Req 4).
  - `ledgers/<run_id>.jsonl` — COG-08 changed-file ledgers.
  - `notes/YYYY-MM-DD-<slug>.md` — `/save` manual notes.
  - Greppable, diffable, git-friendly; matches existing `.voss/decisions/` + `.voss/sessions/` conventions. Chroma persistence directory sits alongside (`.voss/memory/chroma/`) as an index, **not** the source of truth — chroma can be rebuilt from the on-disk files.

- **D-02:** **Chroma topology = Claude's discretion (default: single collection).** Default to one collection `voss_memory` with metadata `{source_type, session_id, path, ts, tombstoned}` and tag-filtered queries. Planner may split into per-source collections only if the Req 3 acceptance (≥ 80% top-3 with chroma) cannot be met with single-collection tuning. Document the chosen topology in the M8 plan output.

- **D-03:** **Turn-content indexing granularity = per-turn.** Each user/assistant turn = one chroma entry. High fidelity for `/recall` so the top-N can point at a specific moment. EpisodicMemory.Turn maps 1:1.

- **D-04:** **Entry ID convention = composite human-readable.** Format: `<source>:<locator>:<seq>` (e.g. `turn:01HX...session...:042`, `decision:.voss/decisions/2026-05-14-foo.md`, `convention:2026-05-14-naming`, `ledger:<run_id>:042`). Used as chroma `ids[]` and surfaced verbatim in `/memory` dumps + `/forget` patterns. Deterministic so re-indexing is idempotent.

### VOSS.md sections + COG-02 rewrite

- **D-05:** **Machine vs human sections = HTML-comment fences.** Format:
  ```markdown
  <!-- voss:begin id=<slug> -->
  <!-- voss:hash <sha256-of-block-content> -->
  ...machine-managed content...
  <!-- voss:end id=<slug> -->
  ```
  Multiple machine blocks supported by distinct `id` slugs. Anything outside a fence is human-owned and never touched by automated writers.

- **D-06:** **Migration of pre-existing `.voss/architecture.md`:** content lands **inside** a `voss:begin id=architecture` machine fence in the new `VOSS.md`. The original `.voss/architecture.md` is moved to `.voss/archive/architecture-YYYY-MM-DD.md` byte-identical (sha256 of archive == sha256 of pre-migration original). Re-running COG-02 analyze writes into the same `id=architecture` fence.

- **D-07:** **Conflict handling on hash mismatch = refuse + diff.** When COG-02 wants to rewrite a fence: read `<!-- voss:hash <sha> -->` line, recompute sha256 of the on-disk fence body. If they differ (= human edited inside the fence), abort the write, print a diff between recorded-baseline ↔ on-disk ↔ proposed-new, and tell the user to run `voss memory adopt --id <slug>` (exact command name = planner discretion) to accept the on-disk human edits as the new machine-baseline. Never silently overwrite.

- **D-08:** **VOSS.md system-context injection = single labeled block, full bytes.** Inject `# VOSS.md\n<file contents verbatim>` as a system message before the first user turn on every `voss chat` / `voss do` / `voss resume`. No selective inclusion of just machine vs human — agent reads what the human reads. Matches Req 1 acceptance ("bytes matching the on-disk file"). Absence of file degrades silently (no error, no section).

### Conventions extraction UX

- **D-09:** **Trigger = signal pre-filter, then call.** On clean session exit, run a cheap heuristic over the turn log (corrective phrasing, repeated user edits in the same direction, explicit style statements). If ≥ 1 signal hits, fire the extraction LLM. Zero signals = skip the LLM call AND skip the candidate prompt entirely (matches Req 4 acceptance — "zero candidates skips the prompt entirely"). Planner specifies the signal set; recommended starters: regex for "no,? use|always|never|prefer|let's|don't" in user turns, plus repeat-edit-same-target detection from the run-record `changed` list.

- **D-10:** **Extraction-prompt output schema = strict JSON.**
  ```json
  [{"statement": "<declarative form>", "confidence": 0.0-1.0,
    "evidence_quote": "<verbatim user quote>", "evidence_turn_idx": <int>}, ...]
  ```
  Pydantic-validated. Statement is the declarative form (e.g., "Use 2-space indentation in Python"). Evidence quote + turn index drive the review UI and persist into the conventions file (matches Req 4 acceptance — "contents include both the convention statement and the evidence snippet").

- **D-11:** **Candidate review UX = numbered list + space-separated indices.** Print as:
  ```
  Candidate conventions from this session:
  [1] Use 2-space indentation in Python  (conf 0.82)
      evidence: "no use 2 spaces" (turn 14)
  [2] Prefer pathlib over os.path  (conf 0.74)
      evidence: "...path-lib here too please" (turn 22)
  Persist which? (e.g. "1 3", or empty for none):
  ```
  Empty input = persist none (Req 4 — "declining all candidates writes nothing"). Each persisted entry writes one `.voss/memory/conventions/YYYY-MM-DD-<slug>.md` with frontmatter `{session_id, evidence_turn_idx, confidence}` plus the statement and the evidence snippet as body. Non-interactive sessions (`--no-input` / piped stdin) skip the review and persist none unless `--persist-conventions 1,3` is passed.

- **D-12:** **Extraction timeout = 8 seconds soft, then skip silently.** Wrap the LLM call in `asyncio.wait_for(timeout=8)`. On timeout: log to session record and skip review entirely (no error, no partial candidates). Tunable as `memory.extraction_timeout_seconds` in `.voss/config.yml`. Disable entirely with `memory.extract_conventions: false` (Req 4 constraint — "default-on but skippable").

### Concurrency + size cap eviction

- **D-13:** **Concurrency = advisory lockfile per source.** `.voss/memory/.locks/<source>.lock` acquired via `fcntl.flock(LOCK_EX | LOCK_NB)` before writes to that source's files + chroma rows. Non-blocking try-lock with bounded retry/backoff (e.g., 5 retries with 200ms exponential backoff — planner finalizes). If still held, the loser logs a one-line warning ("memory.<source> busy — skipping write for this turn") and degrades that source to read-only for the remainder of the run. Per-source granularity avoids serializing unrelated writes (turn-append vs ledger-write). Lock files are kept under `.locks/` so they're easy to .gitignore.

- **D-14:** **Eviction granularity = per-source quotas, oldest-first within source.** Default 100 MB cap is split: turns 60% / ledgers 20% / decisions 10% / conventions 10%. Conventions are user-curated and expensive — chatty turn logs must not be allowed to evict them. Quotas configurable in `.voss/config.yml` under `memory.quota_pct.{turns,ledgers,decisions,conventions}` (must sum to ≤ 100).

- **D-15:** **`/forget` mechanics = tombstone now, physical delete on `voss memory vacuum`.** `/forget <pattern>` matches against composite IDs (D-04) and on-disk file paths (glob), sets `tombstoned=true` in chroma metadata, removes the entries from the on-disk file's active-index (planner picks the exact mechanism — comment them out vs move to a tombstone subdir vs separate index file). Chroma rows physically present until vacuum compacts. Matches Req 6 acceptance — "vacuum reports nonzero bytes reclaimed and tombstoned entries are physically gone". `/forget` requires `--yes` in non-interactive mode (Req 5 acceptance).

- **D-16:** **Eviction trigger = inline check on write, batch evict per source.** Each write to a source first calls a cheap cached size check; if over the source's quota, evict oldest entries (by source-tagged timestamp) until under. Size counter is maintained in-process per source and refreshed on `voss memory vacuum`. Guarantees the cap is never exceeded after a write returns — matches Req 6 acceptance ("post-write size ≤ cap").

### Claude's Discretion

The following details are left to the planner / executor:

- **Chroma topology** — single vs per-source collections (D-02). Default single; switch only if eval forces it.
- **Exact embedding model** — reuse `SemanticMemory._embedding_function()` logic (already handles OpenAI + sentence-transformers fallback). Planner confirms it works for the four source types or proposes an override.
- **`adopt` command surface** — exact name and flags for the human-edits-accepted command surfaced when a `voss:hash` mismatch occurs (D-07). Recommended: `voss memory adopt --id <slug>`. Planner may bundle this with `voss memory` subcommand group.
- **Slash-command argument parsing** — `/recall <query> [--top N] [--source turn|decision|convention|ledger]`, `/forget <pattern> [--yes]`, `/memory [--source <s>]`, `/save <note>` slug derivation from first 40 chars + ts. Stick to `shlex.split` (already used in `voss/harness/slash.py:56`).
- **Signal set for D-09 pre-filter** — Recommended starters above; planner finalizes the exact regex/heuristic list.
- **Per-source size-counter implementation** — in-memory dict, on-disk JSON, or a chroma metadata aggregate. Pick the cheapest that survives a process crash without going off cap.
- **`.voss/config.yml` schema** — extend the existing config file (planner verifies path; if it doesn't exist, planner picks creation policy — first-run scaffold vs lazy default).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract (mandatory)

- `.planning/phases/M8-project-memory-mem-01/M8-SPEC.md` — Locked requirements (7), boundaries, acceptance criteria, ambiguity report. Read FIRST.
- `.planning/ROADMAP.md` §"Phase M8: Project Memory (MEM-01)" — phase goal + canonical refs from roadmap.
- `.planning/REQUIREMENTS.md` — MEM-01 requirements line items.
- `.planning/PROJECT.md` — overall v0.1 framing (Python harness, local-first, `.voss/` durable state).

### Runtime memory primitives (reuse mandatory per Req 7)

- `voss_runtime/memory/__init__.py` — public exports.
- `voss_runtime/memory/episodic.py` — `Turn`, `EpisodicMemory` (capacity, summary, summarize/maybe_summarize, render). Used today for in-session history; M8 reuses for turn-source capture.
- `voss_runtime/memory/semantic.py` — `SemanticMemory` (chroma PersistentClient, get_or_create_collection, embedding-function fallback, add/retrieve). M8 instantiates this for cross-session recall.
- `voss_runtime/memory/working.py` — `WorkingMemory`. Available but no current M8 use.

### Harness integration points

- `voss/harness/slash.py` — `SlashCommand` + `SlashRegistry`. The four new commands register here; `dispatch()` uses `shlex.split` and resolves by name+aliases.
- `voss/harness/session.py` — `load()` at line 162 currently rehydrates one `EpisodicMemory` per session from JSON turns. M8 layer wraps this without changing the on-disk session JSON format (backward-compat constraint).
- `voss/harness/cognition.py` — `bootstrap_prompt()` at line 607 + write path that produces `.voss/architecture.md`. M8 rewires this to write into the `id=architecture` machine fence of root `VOSS.md`.
- `voss/harness/skills/analyze.py` — the single-fs_write skill that drives COG-02; its target moves from `.voss/architecture.md` to the VOSS.md machine fence.
- `voss/harness/recorder.py` — RunRecord persistence (line 136 mirrors decisions to `.voss/decisions/`); M8 reads from the same dir for the `decisions` recall source.

### Prior-phase context (relevant carry-overs)

- `.planning/phases/M2-project-cognition/` — COG-02 / COG-08 work (`.voss/` layout, architecture.md, per-run ledger, decisions/).
- `.planning/phases/M7-sdk-polish/M7-CONTEXT.md` — public-surface decisions; M8 must not introduce private types into the public SDK surface accidentally.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `voss_runtime.memory.EpisodicMemory` — already has `add(role, content)`, `last(n)`, and `render()`. M8 turn-source capture wraps this; do not subclass — instantiate per-session and persist outputs to `turns/<session>.jsonl`.
- `voss_runtime.memory.SemanticMemory` — already handles chroma installation check with a friendly error pointing to `voss[search]`. The M8 cross-session recall path catches the same `ModuleNotFoundError` and routes to the keyword fallback (Req 3).
- `voss_runtime.memory.SemanticMemory._embedding_function()` — env-aware OpenAI/sentence-transformer selection. M8 reuses verbatim; no new embedding logic.
- `voss/harness/slash.SlashRegistry` — existing slash-command mechanism. Pattern from existing registered commands: `SlashCommand(name="/foo", help="...", handler=fn, mutating=bool)`. `/forget` sets `mutating=True`.
- `voss/harness/session.SessionRecord` + `_hydrate()` — pre-M8 session JSON shape stays untouched. M8 indexer reads the same JSON files post-session to populate `turns/<session_id>.jsonl` and feed chroma.
- `voss/harness/cognition.write_voss_gitignore` (line 597) — existing pattern of preserve-if-exists writes under `.voss/`. M8 follows the same idiom for `.voss/memory/.gitignore` (gitignore `chroma/`, `.locks/`, but track `decisions/`, `conventions/`, `notes/` by default).

### Established Patterns

- **Filesystem layout**: durable state under `.voss/` (gitignored: `sessions/`, machine state); rebuildable cache under `.voss-cache/`. M8 puts the chroma persist dir under `.voss/memory/chroma/` and gitignores it; per-source files under `.voss/memory/<source>/` are git-trackable.
- **Single-fs_write skill** (analyze.py): COG-02 currently emits exactly one `fs_write`. M8 keeps the one-write contract — the new target is just a fenced region of `VOSS.md`, not a separate file.
- **Slash dispatch**: `shlex.split` parses arguments; handlers receive `(ctx, args, raw_line)`. M8 commands follow this signature.
- **Provider-aware optional features**: `SemanticMemory.__post_init__` raises `ModuleNotFoundError` with a friendly install hint when `chromadb` is missing. M8 catches at the recall layer, not at instantiation.
- **Soft dependency narrative**: chroma is `voss[search]`-gated; keyword fallback must produce comparable (if degraded) output, not raise.

### Integration Points

- `voss chat` / `voss do` / `voss resume` entrypoints (in `voss/cli.py` and `voss/harness/session.py`) all need a single hook: read `./VOSS.md` if present and inject it as system context before the first turn (D-08).
- `voss/harness/cognition.py` analyze write path → switch from `.voss/architecture.md` to VOSS.md `id=architecture` fence with D-07 conflict guard.
- `voss/harness/session.py` session-end hook → fire extraction (D-09) on clean exit; skip on error termination per Req 4.
- New CLI subcommand group `voss memory` (vacuum, possibly adopt) registered in `voss/cli.py`. Follows the existing subcommand registration pattern.
- `.voss/config.yml` — extend with `memory.{cap_bytes, extract_conventions, extraction_timeout_seconds, quota_pct.{...}}`.

</code_context>

<specifics>
## Specific Ideas

- Per-source dirs of files matters because it keeps the M2 conventions intact — humans and grep can read the memory store directly, no opaque sqlite.
- HTML-comment fences with explicit `id=<slug>` chosen over heading anchors so future machine blocks (beyond architecture) drop in without renaming risk.
- The `<!-- voss:hash <sha> -->` line inside each fence is the integrity check. Recompute on every COG-02 write; mismatch = refuse + diff.
- Pre-filter for conventions extraction matters because most sessions don't warrant an LLM call at exit — auto-running burns tokens and trains the user to ignore the prompt.
- Per-source eviction quotas exist specifically to protect conventions (user-curated, scarce, expensive to reproduce) from being evicted by chatty turn logs.

</specifics>

<deferred>
## Deferred Ideas

- **Hierarchical VOSS.md resolution** (root + per-directory). Explicitly deferred by SPEC.md constraint; not added speculatively.
- **`/extract` manual trigger slash command** for re-running conventions extraction after the fact. Not in Req 5's surface. Capture as a future M8.x or M9 polish.
- **Telemetry of memory ops** (recall hit rates, eviction counts in `voss doctor` output). Useful for tuning Req 3 hit-rate but not in M8 scope.
- **Convention categories** (`style|naming|workflow|tooling`). Could improve `/memory` grouping; deferred — adds a vocabulary the planner must lock and changes the JSON schema for D-10.
- **Cross-project memory sharing**, **cloud sync**, **TUI memory browser** — all explicitly out of scope per SPEC.md.
- **Encryption of memory store** — handled by OS-level filesystem encryption per SPEC.md.
- **Background-thread eviction** — rejected during discussion; introduces threading hazards into a CLI tool.

</deferred>

---

*Phase: M8-project-memory-mem-01*
*Context gathered: 2026-05-14*
