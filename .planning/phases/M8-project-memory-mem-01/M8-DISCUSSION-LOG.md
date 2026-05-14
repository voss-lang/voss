# Phase M8: Project Memory (MEM-01) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** M8-project-memory-mem-01
**Areas discussed:** Memory layout + chroma schema, VOSS.md sections + COG-02 rewrite, Conventions extraction UX, Concurrency + size cap eviction

---

## Memory layout + chroma schema

### Q1: `.voss/memory/` on-disk shape

| Option | Description | Selected |
|--------|-------------|----------|
| Per-source dirs of files | turns/`<session>`.jsonl + decisions/ + conventions/*.md + ledgers/*.jsonl; chroma alongside as index, not source of truth | ✓ |
| Single SQLite db | One `.voss/memory/store.sqlite` with unified entries + `source_type` column | |
| JSONL append-log per source | turns.jsonl / decisions.jsonl / conventions.jsonl / ledgers.jsonl | |

**Notes:** Matches existing `.voss/decisions/` + `.voss/sessions/` conventions. Greppable + diffable + git-friendly. Chroma is rebuildable from on-disk files.

### Q2: Chroma collection topology

| Option | Description | Selected |
|--------|-------------|----------|
| Single collection, source_type metadata | One `voss_memory` collection, tag-filtered queries | |
| Four collections (per source) | Hard partition per source type | |
| You decide | Claude picks based on Req 3 hit-rate requirements | ✓ |

**Notes:** Default = single collection unless Req 3 (≥ 80% top-3 with chroma) cannot be met. Document the chosen topology in the M8 plan output.

### Q3: Turn-content indexing granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Per-turn | One chroma entry per user/assistant turn | ✓ |
| Per-session rolling summary | `EpisodicMemory.summarize()` output as single entry | |
| Per-turn-window | Sliding 3-turn chunks | |

**Notes:** High fidelity for `/recall`. Maps 1:1 to existing `EpisodicMemory.Turn`.

### Q4: Entry ID convention

| Option | Description | Selected |
|--------|-------------|----------|
| Composite human-readable | `<source>:<locator>:<seq>` | ✓ |
| Content sha256 | Opaque hash | |
| ULID per entry | Sortable opaque | |

**Notes:** IDs surface verbatim in `/memory` dumps and `/forget` patterns; deterministic so re-indexing is idempotent.

---

## VOSS.md sections + COG-02 rewrite

### Q1: Machine vs human section demarcation

| Option | Description | Selected |
|--------|-------------|----------|
| HTML-comment fences | `<!-- voss:begin id=<slug> -->` ... `<!-- voss:end id=<slug> -->` | ✓ |
| Heading-anchor convention | Specific h2 anchors own machine blocks | |
| Single trailing machine region | `---` divider, everything after = machine | |

**Notes:** Multiple machine blocks via distinct `id` slugs. Invisible in rendered Markdown.

### Q2: Migration of pre-existing `.voss/architecture.md`

| Option | Description | Selected |
|--------|-------------|----------|
| Inside `voss:begin id=architecture` machine fence | Future COG-02 runs rewrite the same block | ✓ |
| Outside fences as human content | Treat migrated text as human-authored | |
| Split: machine summary + human notes appendix | Auto-split into regenerable + appendix | |

**Notes:** Archive original to `.voss/archive/architecture-YYYY-MM-DD.md` byte-identical (sha256 verified).

### Q3: Conflict handling on hash mismatch

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse + surface diff | `<!-- voss:hash <sha> -->` check, abort + diff on mismatch | ✓ |
| Silent overwrite | Machine fence fully machine-owned | |
| Three-way merge | Merge baseline + on-disk + new | |

**Notes:** User runs `voss memory adopt --id <slug>` (or equivalent) to accept human edits as new baseline.

### Q4: VOSS.md system-context injection

| Option | Description | Selected |
|--------|-------------|----------|
| Single labeled block, full bytes | `# VOSS.md\n<contents verbatim>` | ✓ |
| Two blocks (human + machine) | Split injection into separate system messages | |
| Only machine section | Skip human prose | |

**Notes:** Matches Req 1 acceptance ("bytes matching the on-disk file"). Absence degrades silently.

---

## Conventions extraction UX

### Q1: Extraction trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-filter by signal, then call | Cheap heuristic first; LLM only if ≥ 1 signal | ✓ |
| Always call on clean exit | Run extraction every session-end | |
| Manual trigger only | Add `/extract`; no auto-fire | |

**Notes:** Zero signals = skip the LLM call AND skip the prompt. Reduces token cost on chitchat sessions.

### Q2: Extraction-prompt output schema

| Option | Description | Selected |
|--------|-------------|----------|
| JSON list of `{statement, confidence, evidence_quote, evidence_turn_idx}` | Pydantic-validated | ✓ |
| Markdown bullets, parsed loosely | Brittle | |
| JSON + `category` field | Adds vocabulary planner must lock | |

**Notes:** Evidence quote + turn index persist into the conventions file per Req 4 acceptance.

### Q3: Candidate review UX

| Option | Description | Selected |
|--------|-------------|----------|
| Numbered list + space-separated indices | One round-trip; empty = persist none | ✓ |
| Per-candidate y/n loop | Walk one-by-one | |
| Render to file, edit in $EDITOR | Temp file, comment-out rejects | |

**Notes:** Non-interactive mode supports `--persist-conventions 1,3` flag; default = persist none.

### Q4: Extraction timeout

| Option | Description | Selected |
|--------|-------------|----------|
| 8s soft, skip silently on timeout | `asyncio.wait_for(timeout=8)` | ✓ |
| 30s hard | More tokens to think | |
| No timeout, SIGINT trap | Power-user friendly, unpredictable | |

**Notes:** Tunable via `memory.extraction_timeout_seconds` in `.voss/config.yml`. Disable entirely with `memory.extract_conventions: false`.

---

## Concurrency + size cap eviction

### Q1: Concurrent-session policy

| Option | Description | Selected |
|--------|-------------|----------|
| Advisory lockfile per source | `fcntl.flock` per `.voss/memory/.locks/<source>.lock` | ✓ |
| Append-only journal + late merge | Per-session pending file, reconcile on exit | |
| Last-writer-wins | Just overwrite | |

**Notes:** Non-blocking try-lock with bounded retry/backoff; loser logs warning and degrades to read-only for that source.

### Q2: Eviction granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Per-source quotas, oldest-first within source | turns 60% / ledgers 20% / decisions 10% / conventions 10% | ✓ |
| Global oldest-first | Single LRU across all sources | |
| Reject write + tell user to vacuum | No auto-eviction | |

**Notes:** Quotas configurable. Protects conventions (user-curated, scarce) from chatty turn logs.

### Q3: `/forget` mechanics

| Option | Description | Selected |
|--------|-------------|----------|
| Tombstone, physical delete on `voss memory vacuum` | `tombstoned=true` metadata + on-disk index removal | ✓ |
| Delete inline | Immediate physical delete | |
| Two-phase: tombstone, then `--confirm` second run | Two-run delete | |

**Notes:** Matches Req 6 acceptance — vacuum reports nonzero bytes reclaimed. `--yes` required in non-interactive mode (Req 5).

### Q4: Eviction trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Inline check on write, batch evict per source | Each write checks cached size; evict over quota | ✓ |
| Lazy: only at vacuum time | Writes always succeed | |
| Background thread evict | Worker reclaims async | |

**Notes:** Guarantees cap never exceeded after a write returns (Req 6 — "enforced on write").

---

## Claude's Discretion

- Chroma collection topology (single vs per-source) — default single; switch only if Req 3 hit rate forces it.
- Exact embedding model — reuse `SemanticMemory._embedding_function()`.
- `adopt` command name and flag surface (D-07).
- Slash-command argument parsing details and `/save` slug derivation.
- Signal set for the extraction pre-filter (D-09).
- Per-source size-counter implementation choice.
- `.voss/config.yml` schema additions (with planner verifying current shape).

## Deferred Ideas

- Hierarchical (root + per-dir) VOSS.md resolution (explicitly out per SPEC.md constraint).
- `/extract` manual-trigger slash command.
- Telemetry of memory ops (`voss doctor` recall hit-rates).
- Convention `category` taxonomy.
- Cross-project sharing, cloud sync, TUI memory browser (all out per SPEC.md).
- Encryption (deferred to OS-level FS encryption per SPEC.md).
- Background-thread eviction (rejected — threading hazards in a CLI tool).
