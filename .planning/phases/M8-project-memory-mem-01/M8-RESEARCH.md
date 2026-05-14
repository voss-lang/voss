# Phase M8: Project Memory (MEM-01) — Research

**Researched:** 2026-05-14
**Domain:** Harness wiring of persistent project memory atop existing `voss_runtime/memory/` primitives
**Confidence:** HIGH

## Summary

M8 is a **harness-side wiring phase** over already-built runtime primitives. There is little library research to do; the primitives (`EpisodicMemory`, `SemanticMemory`, `WorkingMemory`) exist and are stable in `voss_runtime/memory/`. The research effort is overwhelmingly **codebase reconnaissance** — finding the exact line where each new wire attaches — plus three small external research items (chroma metadata-filter delete semantics, cross-platform file locking, embedding-model size on disk).

The SPEC + CONTEXT.md together already lock 16 implementation decisions (D-01..D-16); RESEARCH adds (a) confirmed wire points and signatures, (b) three discovered pitfalls the planner must defend against (`/save` name collision, Windows lockfile, cognition.py architecture-frontmatter reader rewire), and (c) test-architecture mapping for each of the seven requirements.

**Primary recommendation:** Plan the phase as a small number of additive harness modules — `voss/harness/voss_md.py` (loader + fence parser), `voss/harness/memory_store.py` (thin orchestrator over `voss_runtime/memory` + `.voss/memory/` layout), `voss/harness/conventions.py` (extraction prompt + review UX), and a `voss memory` CLI subcommand group — wired into the four existing seams: `_run_repl()` bootstrap, `run_turn()` system prompt assembly, `skills/analyze.py` write target, and `_build_slash_registry()`. **Do not subclass runtime types; instantiate and persist around them.**

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Memory storage layout:**
- **D-01:** On-disk source of truth = per-source dirs of files under `.voss/memory/` — `turns/<session_id>.jsonl`, `decisions/` (pointer to `.voss/decisions/*.md`, no duplication), `conventions/YYYY-MM-DD-<slug>.md`, `ledgers/<run_id>.jsonl`, `notes/YYYY-MM-DD-<slug>.md`. Chroma persistence under `.voss/memory/chroma/` is an **index, not the source of truth** — rebuildable from on-disk files.
- **D-02:** Chroma topology = **Claude's discretion (default: single collection)** `voss_memory` with metadata `{source_type, session_id, path, ts, tombstoned}` and tag-filtered queries. Document chosen topology in M8 plan.
- **D-03:** Turn-content indexing granularity = **per-turn**. Each user/assistant turn = one chroma entry; maps 1:1 to `EpisodicMemory.Turn`.
- **D-04:** Entry ID convention = **composite human-readable** `<source>:<locator>:<seq>` (e.g. `turn:01HX...session...:042`, `decision:.voss/decisions/2026-05-14-foo.md`, `convention:2026-05-14-naming`, `ledger:<run_id>:042`). Used as chroma `ids[]`, surfaced verbatim in `/memory` + `/forget`. Deterministic so re-indexing is idempotent.

**VOSS.md sections + COG-02 rewrite:**
- **D-05:** Machine vs human sections = **HTML-comment fences** — `<!-- voss:begin id=<slug> -->`, `<!-- voss:hash <sha256-of-block-content> -->`, `<!-- voss:end id=<slug> -->`. Multiple machine blocks via distinct `id` slugs. Anything outside a fence is human-owned and never touched.
- **D-06:** Migration of pre-existing `.voss/architecture.md` → content lands **inside** a `voss:begin id=architecture` machine fence in new `VOSS.md`. Original moved to `.voss/archive/architecture-YYYY-MM-DD.md` byte-identical (sha256 of archive == sha256 of pre-migration original). Future COG-02 writes into same `id=architecture` fence.
- **D-07:** Conflict handling on hash mismatch = **refuse + diff**. Recompute sha256 of on-disk fence body, compare to recorded `<!-- voss:hash -->`. If differ (human edited), abort write, print 3-way diff (recorded-baseline ↔ on-disk ↔ proposed-new), tell user to run `voss memory adopt --id <slug>` (exact name = planner discretion) to accept on-disk human edits as new baseline. Never silently overwrite.
- **D-08:** VOSS.md system-context injection = **single labeled block, full bytes**. Inject `# VOSS.md\n<file contents verbatim>` as system message before first user turn on every `voss chat` / `voss do` / `voss resume`. No selective inclusion. Absence of file degrades silently.

**Conventions extraction UX:**
- **D-09:** Trigger = **signal pre-filter, then call**. Cheap heuristic over turn log first (recommended starters: regex for "no,? use|always|never|prefer|let's|don't" in user turns, plus repeat-edit-same-target detection from run-record `changed` list). If ≥ 1 signal hits, fire extraction LLM. Zero signals = skip LLM AND skip candidate prompt entirely.
- **D-10:** Extraction-prompt output schema = **strict JSON, pydantic-validated** — `[{statement, confidence (0..1), evidence_quote, evidence_turn_idx}, ...]`. Statement is declarative form. Evidence quote + turn index persist into the conventions file.
- **D-11:** Candidate review UX = **numbered list + space-separated indices** (e.g. `1 3`). Empty input = persist none. Each persisted entry writes one `.voss/memory/conventions/YYYY-MM-DD-<slug>.md` with frontmatter `{session_id, evidence_turn_idx, confidence}` plus statement + evidence body. Non-interactive mode (`--no-input` / piped stdin) skips review unless `--persist-conventions 1,3` passed.
- **D-12:** Extraction timeout = **8s soft, then skip silently**. `asyncio.wait_for(timeout=8)`. On timeout: log to session record, skip review entirely. Tunable via `memory.extraction_timeout_seconds` in `.voss/config.yml`. Disable entirely with `memory.extract_conventions: false`.

**Concurrency + size cap eviction:**
- **D-13:** Concurrency = **advisory lockfile per source**. `.voss/memory/.locks/<source>.lock` via `fcntl.flock(LOCK_EX | LOCK_NB)`. Non-blocking try-lock with bounded retry/backoff (5 retries / 200ms exponential — planner finalizes). Loser logs one-line warning + degrades that source to read-only for the remainder of the run. Per-source granularity.
- **D-14:** Eviction granularity = **per-source quotas, oldest-first within source**. Default 100 MB cap = turns 60% / ledgers 20% / decisions 10% / conventions 10%. Configurable in `.voss/config.yml` under `memory.quota_pct.{turns,ledgers,decisions,conventions}` (must sum to ≤ 100).
- **D-15:** `/forget` mechanics = **tombstone now, physical delete on `voss memory vacuum`**. `/forget <pattern>` matches against composite IDs (D-04) and on-disk file paths (glob), sets `tombstoned=true` in chroma metadata, removes entries from active-index (planner picks exact mechanism). Chroma rows physically present until vacuum compacts. `--yes` required in non-interactive mode.
- **D-16:** Eviction trigger = **inline check on write, batch evict per source**. Each write first calls cheap cached size check; if over source's quota, evict oldest entries until under. Size counter maintained in-process per source, refreshed on `voss memory vacuum`. Cap never exceeded after a write returns.

### Claude's Discretion

- Chroma collection topology — single vs per-source collections (default single; switch only if Req 3 eval forces it).
- Exact embedding model — reuse `SemanticMemory._embedding_function()` (already env-aware OpenAI/sentence-transformer fallback).
- `adopt` command surface — exact name and flags for hash-mismatch resolution. Recommended `voss memory adopt --id <slug>`.
- Slash-command argument parsing — `/recall <query> [--top N] [--source turn|decision|convention|ledger]`, `/forget <pattern> [--yes]`, `/memory [--source <s>]`, `/save <note>` slug derivation. Stick to `shlex.split`.
- Signal set for D-09 pre-filter — recommended starters above; planner finalizes regex/heuristic list.
- Per-source size-counter implementation — in-memory dict / on-disk JSON / chroma metadata aggregate.
- `.voss/config.yml` schema additions — extend existing config OR create new YAML if path doesn't exist. **Note (R-01 below): `.voss/config.yml` does NOT currently exist; only `.voss/constraints.yml`, `.voss/permissions.yml`, `.voss/validation.yml` exist. Planner picks creation policy (first-run scaffold vs lazy default).**

### Deferred Ideas (OUT OF SCOPE)

- Hierarchical (root + per-dir) `VOSS.md` resolution.
- `/extract` manual-trigger slash command for re-running conventions extraction.
- Telemetry of memory ops (recall hit rates, eviction counts in `voss doctor`).
- Convention `category` taxonomy.
- Cross-project sharing, cloud sync, TUI memory browser.
- Encryption of memory store.
- Background-thread eviction.
- New runtime memory primitives.
- Migrating pre-M8 session JSON files to a new on-disk format (backward compat mandatory).
- Promoting `voss[search]` to default install.
</user_constraints>

<phase_requirements>
## Phase Requirements

SPEC.md uses positional numbering 1–7 (no MEM-XX prefix yet — planner may assign or treat positional numbers as canonical).

| ID | Description | Research Support |
|----|-------------|------------------|
| **1** | VOSS.md loader + injection on every `voss chat` / `voss do` / `voss resume` | Single attach point: `_run_repl()` in `voss/harness/cli.py:688` (covers chat + resume + edit) + `run_turn()` system-prompt composition in `voss/harness/agent.py:236-318`. New helper `voss/harness/voss_md.py::read_and_inject()` reads `./VOSS.md`, returns string-or-None; `_run_repl` passes through into `run_turn`'s `sys_prompt` assembly (line 297). `voss do` (cli.py:511) calls `run_turn` directly so same hook fires. Absence = return None, no section. |
| **2** | architecture.md → VOSS.md migration + COG-02 rewire | Three concrete edits — (a) new `voss/harness/voss_md.py::ensure_migrated(cwd)` runs at REPL boot before cognition.load; (b) `voss/harness/skills/analyze.py:36` changes `arch_path = cognition.voss_dir(cwd) / "architecture.md"` to `voss_md.machine_fence_path(cwd, id="architecture")` plus a new write-helper that updates a fence body with hash-check; (c) `voss/harness/cognition.py:209-227` `_load_arch()` rewires to read fence body from VOSS.md instead of `.voss/architecture.md`. **Frontmatter remains the first 6 lines of the fence body** so `FRONTMATTER_RE` (cognition.py:38) still matches. Archive path: `.voss/archive/architecture-YYYY-MM-DD.md`. |
| **3** | Cross-session recall store under `.voss/memory/`, 4 source types | New `voss/harness/memory_store.py` orchestrator. Reuses `voss_runtime.memory.EpisodicMemory` for turn capture (just append `Turn` objects to `turns/<session_id>.jsonl`; do NOT subclass), instantiates `voss_runtime.memory.SemanticMemory(persist_dir=str(cwd/".voss/memory/chroma"), collection_name="voss_memory")` for indexed retrieval (catches `ModuleNotFoundError` from semantic.py:25 — falls back to keyword/grep recall). Source-tagging via chroma metadata `{source_type: turn|decision|convention|ledger, session_id, path, ts, tombstoned}`. Keyword fallback = `pathlib.Path.rglob` + substring scoring over on-disk files. |
| **4** | Conventions extraction at session end with user confirmation | Hook = `_run_repl()` end-of-loop after the `while True: ... return` block (cli.py:773-778, the `EOFError/KeyboardInterrupt` exit path). New `voss/harness/conventions.py` runs the D-09 pre-filter against `ctx.history.turns` + `record.runs[*].changed`, then (if signals) `asyncio.run(asyncio.wait_for(extract_conventions(history, provider), timeout=8))`. Returns `list[ConventionCandidate]` (pydantic), prints numbered list per D-11, reads stdin one line, writes selected entries to `.voss/memory/conventions/YYYY-MM-DD-<slug>.md`. Skips entirely on error-exit (separate code path for exceptions). |
| **5** | Four slash commands `/recall`, `/forget`, `/memory`, `/save` | Add to `_build_slash_registry()` in cli.py:464-483. **NAMING COLLISION:** `/save` is already registered at cli.py:473 ("persist session snapshot"). Planner MUST resolve — see Pitfall 1 below. `/recall <query> [--top N] [--source ...]` → `memory_store.recall(query, top_k, source_type)`. `/forget <pattern> [--yes]` → `memory_store.forget(pattern, confirm=...)`, `mutating=True`. `/memory [--source <s>]` → render markdown summary (counts per source, recent entries, store size). All four use `shlex.split` (slash.py:56) — pattern matches existing slash commands. Each gets `--help` via the `help` field on `SlashCommand`. |
| **6** | 100 MB cap + `voss memory vacuum` CLI | New CLI subcommand group `voss memory` (planner picks shape; recommended `click.Group` registered via `voss.harness.cli.register(main)` at cli.py:1282 pattern). Subcommands: `voss memory vacuum`, `voss memory adopt --id <slug>` (D-07), maybe `voss memory size`. Eviction: D-16 inline check using per-source size counter (initial implementation = `sum(p.stat().st_size for p in dir.rglob("*"))` cached after each write). Vacuum: `chroma_collection.delete(where={"tombstoned": True})` (verified API per chroma docs) + delete tombstoned on-disk files, report bytes reclaimed via stat-diff. |
| **7** | Runtime-primitive reuse (no parallel store) | Acceptance grep enforced: `grep -rn "^class .*Memory" voss/harness/` returns zero matches. All M8 harness modules import `from voss_runtime.memory import EpisodicMemory, SemanticMemory` and instantiate, never subclass. Recall pipeline test patches `voss_runtime.memory.SemanticMemory.__init__` to assert it's invoked. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| VOSS.md file convention + fence parser | Harness (`voss/harness/voss_md.py`) | — | File-format owner. Pure string manipulation; no runtime dep. |
| VOSS.md system-context injection | Harness (`run_turn` sys_prompt assembly) | — | Composes provider call payload; lives next to `_compose_cognition_prompt` (agent.py:52). |
| Architecture migration + archive | Harness (one-shot at REPL boot, `voss_md.ensure_migrated`) | Filesystem | Touches `.voss/`; no runtime API surface. |
| COG-02 analyze write path | Harness skill (`skills/analyze.py`) | Harness fence-writer | Skill emits fs_write into VOSS.md fence; the fence writer is the trusted machine-side that enforces D-07 hash guard. |
| Turn capture | Runtime (`EpisodicMemory.add`) → Harness (jsonl persistence) | — | Runtime owns the Turn model; harness owns the on-disk JSONL append. |
| Cross-session semantic recall | Runtime (`SemanticMemory.add/retrieve`) | Harness (keyword fallback when chroma absent) | Runtime owns chroma; harness owns the fallback path + source-tagging logic. |
| Decisions/ledger/notes mirroring | Harness (file-only) | — | Plain markdown / JSONL; no runtime touched. |
| Conventions extraction prompt | Harness (`conventions.py`) | Runtime provider (`provider.complete`) | LLM call goes through existing provider abstraction; prompt design + parsing is harness. |
| Slash commands `/recall /forget /memory /save` | Harness (slash registry) | Harness memory_store | Pure UI; delegates to memory_store. |
| `voss memory` CLI subgroup | Harness (`voss/harness/cli.py` Click group) | Harness memory_store | Same pattern as existing `voss config`, `voss tools`, `voss doctor`. |
| Size cap + eviction | Harness (`memory_store.py`) | — | Filesystem accounting; runtime has no notion of caps. |
| Concurrency lockfiles | Harness (`memory_store.py`) | — | `fcntl.flock` is harness-local. **Cross-platform caveat: see Pitfall 3.** |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `voss_runtime.memory.EpisodicMemory` | in-repo | Per-session turn buffer (existing) | Already in use at `voss/harness/cli.py:616`; reused per Req 7 [VERIFIED: codebase grep] |
| `voss_runtime.memory.SemanticMemory` | in-repo | Chroma-backed semantic recall (existing) | Already designed with `ModuleNotFoundError` fallback path at semantic.py:25 [VERIFIED: read semantic.py] |
| `chromadb` | `>=0.5.0` (pyproject `[search]` extra) | Vector store backing | Pinned in pyproject.toml line 29 + 38 [VERIFIED: read pyproject.toml]. PyPI current ≥ 1.5 (May 2026) [VERIFIED: pip index versions chromadb returned 1.5.9; npm view returned 3.4.3 for a JS variant — Python `>=0.5.0` lower bound covers a wide range and stays correct] |
| `pydantic` | `>=2.6,<3.0` | D-10 strict-JSON convention schema | Already core dep [VERIFIED: pyproject.toml] |
| `pyyaml` | `>=6.0` | `.voss/config.yml` parsing (if planner picks YAML) | Already core dep [VERIFIED: pyproject.toml] |
| `click` | `>=8.1.0` | `voss memory` subcommand group | Pattern matches existing groups [VERIFIED: voss/harness/cli.py imports click] |
| `fcntl` (stdlib) | builtin | POSIX advisory locking per D-13 | Standard for non-blocking flock. **Windows-incompatible** — see Pitfall 3. |
| `hashlib` (stdlib) | builtin | sha256 for fence-hash + archive byte-equality | D-06, D-07 acceptance gates |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sentence-transformers` | `>=2.7.0` (pyproject `[search]` extra) | Local embedding fallback when no `OPENAI_API_KEY` | Already wired in `SemanticMemory._embedding_function()` semantic.py:55. M8 inherits this. |
| `asyncio.wait_for` | stdlib | D-12 8-second extraction timeout | Standard idiom; matches existing `asyncio.run(...)` pattern in skills/analyze.py:44. |
| `shlex.split` | stdlib | Slash command argument parsing | Already used in `slash.py:56`. Match this for new commands. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| chromadb | sqlite-vss / lancedb | Voss runtime already commits to chroma (pyproject `[search]` extra, `SemanticMemory` impl). Req 7 forbids parallel store. Out per CONTEXT.md. |
| Per-source dirs (D-01) | Single SQLite DB | Rejected at discuss-phase (DISCUSSION-LOG Q1) — greppable/diffable wins. |
| fcntl-only (POSIX) | `portalocker` (cross-platform 3rd-party) | M6 supports Windows; planner may need to add `portalocker>=2.8` OR document Windows-skip behavior with a guarded import. **Strongly recommend portalocker** — adds one tiny pure-Python dep, removes a platform gap. See Pitfall 3. |

**Installation:** No new dependencies if the planner accepts POSIX-only locking. If portalocker is adopted: `pip install portalocker>=2.8` added to core deps.

**Version verification (2026-05-14):**
- `chromadb>=0.5.0` pinned in pyproject.toml [VERIFIED: file read]. PyPI latest seen at 1.5.9 (Python) / 3.4.3 (separate JS pkg via npm) [VERIFIED: pip/npm tool runs]. Range still compatible.
- `pydantic>=2.6,<3.0` pinned [VERIFIED: pyproject.toml].
- `voss_runtime/memory/` exports unchanged since M2; no version bump needed [VERIFIED: read __init__.py].

## Architecture Patterns

### System Architecture Diagram

```
                       voss chat / voss do / voss resume (CLI entry)
                                          │
                                          ▼
                              _run_repl() / do_cmd()
                                          │
                  ┌───────────────────────┼─────────────────────────────────┐
                  │                       │                                 │
                  ▼                       ▼                                 ▼
       voss_md.read_and_inject     cognition_mod.load()        memory_store.bind(cwd, session_id)
       (read VOSS.md verbatim)     (load .voss/*.yml)          (init chroma | keyword fallback)
                  │                       │                                 │
                  └────────────┬──────────┘                                 │
                               ▼                                            │
                       run_turn(sys_prompt=                                  │
                         "# VOSS.md\n<bytes>"                                │
                         + cognition_block                                   │
                         + prior_context_block                               │
                         + PLAN_SYSTEM)                                      │
                               │                                            │
                  ┌────────────┼─────────────────────────┐                   │
                  ▼            ▼                         ▼                   │
            provider.complete  history.add()       run-record assembly      │
            (LLM)              (EpisodicMemory)    (RunRecorder)            │
                                  │                       │                  │
                                  └──── per-turn append ──┼──── per-run ────┘
                                                          │
                                                          ▼
                                         memory_store.write(turn|ledger)
                                         │  ├─ acquire .locks/<source>.lock (fcntl/portalocker)
                                         │  ├─ append to .voss/memory/<source>/...
                                         │  ├─ add to chroma collection w/ source metadata
                                         │  └─ inline size check → evict if over quota (D-16)
                                         ▼
                                  /recall ─► SemanticMemory.retrieve (chroma)
                                            └─► fallback: keyword scan of on-disk dirs
                                  /forget ─► set tombstoned=True (chroma) + index-strip
                                  /memory ─► render markdown summary
                                  /save N ─► append .voss/memory/notes/<slug>.md

                       REPL exit (clean) ─► conventions.extract():
                                            ├─ D-09 signal pre-filter
                                            ├─ asyncio.wait_for(LLM, 8s)
                                            ├─ render numbered candidate list
                                            └─ persist user-selected to conventions/

                       voss memory vacuum (CLI) ─► chroma.delete(where=tombstoned)
                                                  + rm tombstoned files
                                                  + report bytes reclaimed
```

### Recommended Project Structure
```
voss/harness/
├── voss_md.py        # NEW — VOSS.md loader, fence parse, migration, hash guard
├── memory_store.py   # NEW — orchestrator over voss_runtime.memory + .voss/memory/ FS
├── conventions.py    # NEW — D-09 prefilter, D-10 schema, D-11 review UX, D-12 timeout
├── memory_cli.py     # NEW — `voss memory vacuum/adopt/size` Click group
├── slash.py          # EXISTING — registry pattern; M8 adds 4 commands via cli.py
├── cli.py            # MODIFIED — _build_slash_registry() gains 4 commands; _run_repl()
│                     #            calls voss_md.read_and_inject + memory_store.bind +
│                     #            conventions.run_on_exit; new Click group registered
├── agent.py          # MODIFIED — run_turn() sys_prompt prepends VOSS.md block; per-turn
│                     #            hook calls memory_store.write_turn after history.add
├── cognition.py      # MODIFIED — _load_arch() reads VOSS.md fence body instead of
│                     #            .voss/architecture.md (frontmatter still in fence head)
└── skills/analyze.py # MODIFIED — fs_write target = VOSS.md id=architecture fence body;
                      #            arch_backup logic adapts to fence-body restore

.voss/                # ON-DISK (per project)
├── memory/
│   ├── chroma/                       # gitignored — rebuildable index
│   ├── turns/<session_id>.jsonl      # gitignored (mirrors sessions/ policy)
│   ├── decisions/                    # pointer/symlink to .voss/decisions/ (D-01)
│   ├── conventions/                  # git-tracked (user-curated)
│   ├── ledgers/<run_id>.jsonl        # gitignored
│   ├── notes/                        # git-tracked
│   ├── .locks/                       # gitignored
│   └── .gitignore                    # M8 writes this preserve-if-exists
└── archive/
    └── architecture-YYYY-MM-DD.md    # M8 migration artifact (byte-identical to pre-M8)

VOSS.md               # NEW root-level file — human-editable + machine fences
```

### Pattern 1: VOSS.md fence parse + hash guard

**What:** Parse `VOSS.md` into a list of `Block(kind, id, body, recorded_hash)` and detect drift before machine writes.

**When to use:** Every COG-02 analyze write; every `voss memory adopt`.

**Example:**
```python
# Source: synthesized from D-05/D-06/D-07 + cognition.py FRONTMATTER_RE pattern
import hashlib, re
from dataclasses import dataclass

FENCE_BEGIN = re.compile(r"<!-- voss:begin id=([\w-]+) -->")
FENCE_HASH  = re.compile(r"<!-- voss:hash ([0-9a-f]{64}) -->")
FENCE_END   = re.compile(r"<!-- voss:end id=([\w-]+) -->")

@dataclass
class Block:
    kind: str         # "human" | "machine"
    id: str | None
    body: str
    recorded_hash: str | None

def parse(text: str) -> list[Block]:
    blocks, i, lines = [], 0, text.splitlines(keepends=True)
    while i < len(lines):
        m = FENCE_BEGIN.match(lines[i].strip())
        if not m:
            # accumulate human lines until next fence-begin or EOF
            start = i
            while i < len(lines) and not FENCE_BEGIN.match(lines[i].strip()):
                i += 1
            blocks.append(Block("human", None, "".join(lines[start:i]), None))
            continue
        fence_id = m.group(1)
        # next line should be the hash header
        hash_match = FENCE_HASH.match(lines[i+1].strip())
        recorded = hash_match.group(1) if hash_match else None
        body_start = i + 2 if hash_match else i + 1
        # scan to end-fence
        j = body_start
        while j < len(lines):
            end = FENCE_END.match(lines[j].strip())
            if end and end.group(1) == fence_id:
                break
            j += 1
        body = "".join(lines[body_start:j])
        blocks.append(Block("machine", fence_id, body, recorded))
        i = j + 1
    return blocks

def write_machine_fence(text: str, fence_id: str, new_body: str) -> str:
    """Write new_body into id=<fence_id>. Raises HashMismatch if recorded != current."""
    blocks = parse(text)
    for b in blocks:
        if b.kind == "machine" and b.id == fence_id:
            if b.recorded_hash is not None:
                actual = hashlib.sha256(b.body.encode()).hexdigest()
                if actual != b.recorded_hash:
                    raise HashMismatch(fence_id, recorded=b.recorded_hash,
                                       actual=actual, on_disk=b.body)
            # rewrite this block; recompute hash for the new body
            return _render(blocks, fence_id, new_body)
    # Fence doesn't exist — append it.
    return text + _render_fence(fence_id, new_body)
```

### Pattern 2: SemanticMemory with keyword fallback

**What:** Try chroma; on `ModuleNotFoundError`, fall back to deterministic keyword scoring over on-disk dirs.

**When to use:** All `/recall` paths. Mandated by Req 3 + SPEC constraint "must degrade to a keyword/grep path... not raise an import error."

**Example:**
```python
# Source: synthesized from voss_runtime/memory/semantic.py:21-31 fallback pattern + Req 3 hit-rate floors
from pathlib import Path

class MemoryStore:
    def __init__(self, cwd: Path):
        self.root = cwd / ".voss" / "memory"
        self._chroma = None
        try:
            from voss_runtime.memory import SemanticMemory
            self._chroma = SemanticMemory(
                persist_dir=str(self.root / "chroma"),
                collection_name="voss_memory",
            )
        except ModuleNotFoundError:
            self._chroma = None  # keyword fallback engaged

    def recall(self, query: str, *, top_k: int = 5, source: str | None = None) -> list[Hit]:
        if self._chroma is not None:
            where = {"tombstoned": False, **({"source_type": source} if source else {})}
            # chroma .query exposes where; if SemanticMemory doesn't pass it through,
            # call self._chroma._collection.query directly. Document this in the plan.
            return [...]
        return self._keyword_scan(query, top_k=top_k, source=source)

    def _keyword_scan(self, query: str, *, top_k: int, source: str | None) -> list[Hit]:
        terms = [t.lower() for t in query.split() if t]
        candidates: list[tuple[float, Hit]] = []
        for src in ("turns", "decisions", "conventions", "ledgers", "notes"):
            if source and src != source:
                continue
            for path in (self.root / src).rglob("*"):
                if not path.is_file():
                    continue
                text = path.read_text(errors="ignore").lower()
                score = sum(text.count(t) for t in terms)
                if score:
                    candidates.append((score, Hit(source=src, path=path, score=score)))
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [h for _, h in candidates[:top_k]]
```

### Pattern 3: Inline pre-write eviction (D-16)

**What:** Before every memory-store write, check the source's quota; if over, evict oldest until under.

**When to use:** All four source writes — turns, decisions, conventions, ledgers, notes.

**Example:**
```python
# Source: synthesized from D-14/D-16
SOURCE_QUOTAS = {"turns": 0.60, "ledgers": 0.20, "decisions": 0.10, "conventions": 0.10}

def write_with_quota(self, source: str, write_fn, *, est_bytes: int) -> None:
    quota_bytes = int(self.cap_bytes * SOURCE_QUOTAS[source])
    current = self._size_cache[source]
    while current + est_bytes > quota_bytes:
        evicted = self._evict_oldest(source)
        if evicted == 0:
            raise StoreFull(source, quota_bytes)
        current = self._size_cache[source]
    write_fn()
    self._size_cache[source] = current + est_bytes
```

### Anti-Patterns to Avoid

- **Subclassing `EpisodicMemory` or `SemanticMemory`.** Req 7 acceptance forbids it (grep gate). Instantiate + compose, never subclass. Harness adds persistence and source-tagging *around* runtime types, not *underneath* them.
- **Writing to `.voss/memory/` from inside a tool call.** Defeats the lockfile model — tool calls run inside `run_turn` and the writer must own the lock. Memory writes are post-turn (run_turn returns → harness writes ledger; convention extraction runs at REPL exit; user-confirmed conventions write from the slash dispatcher, not inside `run_turn`).
- **Treating chroma as the source of truth.** D-01 is explicit: on-disk files are canonical; chroma rebuilds. Any `/forget` or vacuum logic that ONLY updates chroma loses durability.
- **Silent overwrite of human fence edits.** D-07 mandates refuse + diff. Tempting to "just rewrite if hash differs because the machine knows best" — don't.
- **Loading VOSS.md inside `run_turn` per turn.** Read once at REPL boot (`_run_repl()`), pass through; otherwise every turn does redundant I/O and risks injecting stale-on-disk if user edited during session.
- **Conventions extraction running on error-exit.** SPEC Req 4 explicit: "On clean session exit." Wrap the trigger in `try/finally` only for *clean* exits — exception paths skip it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector embedding fallback (OpenAI ↔ sentence-transformers) | New embedding selector | Reuse `SemanticMemory._embedding_function()` (semantic.py:44-57) | Already env-aware; reinvention would diverge from runtime tests. |
| Chroma client lifecycle | Custom `PersistentClient` wrapper | Reuse `SemanticMemory.__post_init__` (semantic.py:21-42) | Already handles get_or_create_collection + Settings(anonymized_telemetry=False) + ModuleNotFoundError hint. |
| Tombstoned-record deletion | Manual id-collection scan | `collection.delete(where={"tombstoned": True})` | Chroma supports `where` filter on `.delete` natively. [CITED: https://docs.trychroma.com/docs/collections/delete-data] |
| Slash command argument parsing | Hand-rolled tokenizer | `shlex.split` (slash.py:56) | Existing pattern; handles quoted args; rejects malformed input with ValueError. |
| Frontmatter parsing | New YAML lexer | Existing `FRONTMATTER_RE` (cognition.py:38) | After migration the frontmatter sits at the head of the fence body — same regex still matches. |
| Cross-platform file locking | Hand-rolled retry loop | `portalocker>=2.8` (or document POSIX-only) | One small pure-Python dep; sidesteps fcntl-vs-msvcrt branch. See Pitfall 3. |
| Atomic file write | `open().write()` | Pattern from `voss/harness/sandbox.py::write` (atomic temp + rename, if present — planner verifies) | Concurrent-session safety constraint demands no partial writes. |
| Slug derivation | New regex | Existing `cognition.slug()` + `reserve_filename()` (cognition.py — used by recorder.py:151) | Already produces YYYY-MM-DD-<slug>.md paths matching decisions/ layout. |

**Key insight:** M8 is overwhelmingly composition over existing primitives. The pattern from M2 (cognition.py preserve-if-exists scaffold writes, recorder.py decisions mirror, analyze.py one-fs_write skill) is the template — M8 replicates it for memory.

## Runtime State Inventory

> Phase M8 is mostly additive (creates `VOSS.md`, `.voss/memory/`) but **does include a one-shot migration** of `.voss/architecture.md`. Inventory below.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `.voss/architecture.md` exists in any repo that ran M2 `/analyze`. Frontmatter (cognition.py:38 `FRONTMATTER_RE`) + body. | **One-shot data migration** at first M8-session boot: copy file → archive byte-identical → fold into `VOSS.md` `id=architecture` fence. Idempotent (skip if `VOSS.md` exists OR archive already present). |
| Live service config | None — no external services. | None. |
| OS-registered state | None — no daemons, systemd units, Windows tasks, or cron. | None. |
| Secrets/env vars | `OPENAI_API_KEY` (already used by `SemanticMemory._embedding_function`, semantic.py:49). M8 inherits — no new key. | None. |
| Build artifacts | None — pure Python source; no compiled deliverables touched. (`.voss-cache/harness/` from M4 unaffected.) | None. |

**Architecture migration is the only runtime state event in M8.** Acceptance gate Req 2(a) verifies `sha256(archive) == sha256(pre-migration)` to catch corruption.

## Common Pitfalls

### Pitfall 1: `/save` SLASH COMMAND NAME COLLISION

**What goes wrong:** SPEC Req 5 specifies `/save <note>` to append manual notes to memory. But `/save` is **already registered** in `voss/harness/cli.py:473` for "persist session snapshot."

**Why it happens:** The existing `/save` was added in M1 (REPL slash registry baseline). SPEC was written treating `/save` as a new name; the conflict wasn't caught in the discuss-phase Q3 (Slash Commands).

**How to avoid:** **Planner MUST choose one of three resolutions and document the choice:**
1. **Rename existing `/save` → `/save-session`** (matches the existing `/save-plan` convention at cli.py:475). New `/save <note>` takes the bare name. **Recommended** — preserves the SPEC's `/save <note>` ergonomics.
2. **Rename new memory `/save` → `/note`** (or `/save-note`). Existing snapshot behavior preserved.
3. **Polymorphic `/save`** — `/save` (no args) = session snapshot, `/save <note>` (args present) = memory note. Confusing — rejected.

**Warning signs:** A test of `/save foo bar` writes a memory note today's date file `notes/...-foo-bar.md` BUT ALSO renames the session to "foo bar" via the existing handler (cli.py:412-417: `ctx.record.name = " ".join(args).strip()`). Both effects fire — silent data corruption.

### Pitfall 2: Cognition loader reads stale `.voss/architecture.md` after migration

**What goes wrong:** After Req 2 migration, `.voss/architecture.md` no longer exists (archived). But `voss/harness/cognition.py:209` (`if not (root / "architecture.md").exists(): ...`) — if planner only rewires `skills/analyze.py` write path and forgets the cognition LOAD path, every subsequent session would report cognition uninitialized (since architecture.md gone), losing the in-context architecture block.

**Why it happens:** The COG-02 plumbing has TWO sides: a write path (analyze.py creates the file) AND a read path (cognition.py:215 `_load_arch` extracts body + frontmatter for `bundle.architecture_md`). The discuss-phase only explicitly mentioned the write path in D-06.

**How to avoid:** `voss/harness/cognition.py::_load_arch` must read the `id=architecture` fence body from VOSS.md instead. The frontmatter regex (`FRONTMATTER_RE`, line 38) still works **if the fence body keeps the frontmatter at the top** — confirm in the analyze prompt rewrite (cognition.py:647-656). Don't drop the frontmatter when migrating; copy it verbatim into the fence body head.

**Warning signs:** `voss doctor` reports cognition uninitialized after upgrade despite `VOSS.md` existing. Integration test should boot a fresh REPL post-migration and assert `bundle.architecture_md` is non-empty + frontmatter parsed.

### Pitfall 3: `fcntl` is POSIX-only — Windows breaks D-13

**What goes wrong:** `fcntl.flock(LOCK_EX | LOCK_NB)` (D-13) raises `ModuleNotFoundError` on Windows. M6 npm wrapper lists `win32-x64` as a supported platform (NPM-02 / ROADMAP M6). A Windows user running `voss chat` would crash on first memory write.

**Why it happens:** `fcntl` is a Unix-only stdlib module. CONTEXT.md D-13 names it explicitly without flagging the constraint.

**How to avoid:** **Three options for the planner:**
1. Add `portalocker>=2.8` to core deps. ~80KB pure-Python, cross-platform `Lock` context manager. **Recommended.**
2. Guarded import: `try: import fcntl except ImportError: fcntl = None` + Windows path uses `msvcrt.locking(fd, msvcrt.LK_NBLCK, length)`. More code, no new dep.
3. Drop Windows support for M8 features (gate the write paths on `platform.system() != "Windows"` and degrade to "no concurrent-session safety on Windows" with a doctor warning). Existing pattern: `voss/harness/auth.py` already has 3 `platform.system() != "Darwin"` branches at lines 66, 85, 142 [VERIFIED: grep]. Precedent for selective platform support.

**Warning signs:** No CI matrix entry for Windows on the memory subsystem. M6 packaging smoke verifies `voss --help / voss doctor` but does NOT exercise `/recall` or memory writes [VERIFIED: M6 plan reading]. Planner must add at least a "is the lock acquirable" smoke test gated on platform.

### Pitfall 4: `chromadb` import cost on cold start

**What goes wrong:** First chroma import takes 2–5s on macOS (transitively imports torch / numpy / onnxruntime). If `memory_store.bind()` runs at every REPL boot synchronously, M6's bundled-Python startup-latency budget is blown.

**Why it happens:** `voss[search]` extra is opt-in but `dev` extra pulls it in (pyproject.toml line 38); CI + dogfood always hits the cost. Even when `voss[search]` is installed, the import is deferred today inside `SemanticMemory.__post_init__` — instantiating eagerly at REPL boot pulls it forward.

**How to avoid:** Lazy-init `SemanticMemory`. `memory_store.bind()` only records the cwd; chroma client only instantiates on first `recall()` / `add()` call. Matches existing semantic.py pattern. Document the deferral in the plan.

**Warning signs:** `voss chat` cold-start time regresses after M8 lands. Doctor row for "memory: ready" appearing before any memory operation is a sign of premature init.

### Pitfall 5: Conventions extraction LLM call on every clean exit burns tokens silently

**What goes wrong:** D-09 pre-filter is supposed to skip the LLM on chatty sessions — but if the regex hits any user turn containing "no" or "use" or "always", every session fires an extraction call (~500–2000 tokens depending on history length). Over a week of dogfood, this is meaningful cost the user doesn't see.

**Why it happens:** The recommended starter regex `no,? use|always|never|prefer|let's|don't` is very loose. Plus repeat-edit detection from `record.runs[*].changed` triggers on any session with > 1 turn modifying the same file (common in real coding sessions).

**How to avoid:** Tighten the signal threshold. Recommended: require ≥ 2 distinct signal types OR confidence ≥ 0.7 in any single signal. Surface signal count + estimated token cost in a doctor row OR in `/memory` summary so the user can SEE what extraction is costing them. Make `memory.extraction_token_budget` configurable (e.g., abort if estimated > 4k tokens).

**Warning signs:** User reports "every session ends with a 'persist which?' prompt I always answer empty." That's the LLM call firing AND nothing useful coming back — both signals are too loose AND the extraction prompt is over-eager.

### Pitfall 6: Backward-compat trap on `voss resume <pre-M8-id>`

**What goes wrong:** SPEC acceptance Req 6 last bullet: "`voss resume <pre-M8-session-id>` rehydrates without crash on a v0.1 session JSON fixture." But the rehydrate path in `session.load` (session.py:162-196) builds an `EpisodicMemory(capacity=40)` from `record.turns`. If M8 introduces a SessionRecord schema field expected by memory_store (e.g., `record.memory_session_id`), pre-M8 sessions don't have it.

**Why it happens:** `_hydrate` at session.py:119 already filters unknown fields, but new code expecting `record.memory_*` must defend with `getattr(record, "...", default)`.

**How to avoid:** Treat the session record as forward-compat by reading only via `getattr(...)` with defaults. Memory store derives the session_id from `record.id` only (which is already present). Don't add new required fields to `SessionRecord` — backward-compat is mandated.

**Warning signs:** Integration test must include a fixture pre-M8 SessionRecord JSON (no memory fields) → `voss resume` → assert no AttributeError, no KeyError.

## Code Examples

Verified patterns from the existing codebase that M8 should reuse:

### Preserve-if-exists `.voss/` write
```python
# Source: voss/harness/cognition.py:597-604 (write_voss_gitignore)
def write_memory_gitignore(cwd: Path) -> bool:
    target = cwd / ".voss" / "memory" / ".gitignore"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return False
    target.write_text(
        "# voss memory store — index + locks are rebuildable / per-machine\n"
        "chroma/\n"
        "turns/\n"
        "ledgers/\n"
        ".locks/\n"
    )
    return True
```

### Mirror to per-source dir (decisions pattern → conventions)
```python
# Source: voss/harness/recorder.py:135-167 (write_decisions_md)
def write_convention_md(cwd: Path, candidate: ConventionCandidate, session_id: str) -> Path:
    from .cognition import reserve_filename, slug
    conv_dir = cwd / ".voss" / "memory" / "conventions"
    conv_dir.mkdir(parents=True, exist_ok=True)
    path = reserve_filename(conv_dir, slug(candidate.statement[:40]))
    id_str = path.stem
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    content = (
        "---\n"
        f"id: {id_str}\n"
        "status: active\n"
        f"related_session: {session_id}\n"
        f"evidence_turn_idx: {candidate.evidence_turn_idx}\n"
        f"confidence: {candidate.confidence:.2f}\n"
        f"created_at: {created_at}\n"
        "---\n\n"
        f"# {candidate.statement}\n\n"
        f"## Evidence\n\n> {candidate.evidence_quote}\n"
    )
    path.write_text(content)
    return path
```

### Soft-dependency catch (chroma fallback)
```python
# Source: voss_runtime/memory/semantic.py:21-31 + Req 3 fallback constraint
def _try_chroma(cwd: Path):
    try:
        from voss_runtime.memory import SemanticMemory
    except ModuleNotFoundError:
        return None
    try:
        return SemanticMemory(
            persist_dir=str(cwd / ".voss" / "memory" / "chroma"),
            collection_name="voss_memory",
        )
    except ModuleNotFoundError:  # raised inside __post_init__ when chromadb absent
        return None
```

### Slash command registration with mutating flag
```python
# Source: voss/harness/cli.py:464-483 — add 4 commands inside _build_slash_registry()
SlashCommand("/recall", "search memory (top-N hits across sources)", _recall),
SlashCommand("/forget", "delete memory entries matching <pattern>", _forget, mutating=True),
SlashCommand("/memory", "summarize current memory store", _memory),
SlashCommand("/save",   "append a manual note to memory", _save_note, mutating=True),
# Note: existing "/save" handler renames or repurposed per Pitfall 1.
```

## State of the Art

This is a phase-internal capability with no rapidly-changing external state. The relevant facts:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `.voss/architecture.md` as standalone auto-generated file | `VOSS.md` machine fence + human prose hybrid | M8 (this phase) | Replaces M2 COG-02 write target. |
| Per-session-only `EpisodicMemory` | Cross-session memory store atop `EpisodicMemory` JSONL persistence + `SemanticMemory` | M8 | Episodic unchanged; semantic gains a harness consumer (previously unused at harness layer). |
| Decisions only mirrored to `.voss/decisions/*.md` | Decisions also indexed in memory store via pointer (D-01) | M8 | No file move; just a new index entry per decision write. |

**Deprecated/outdated:**
- `.voss/architecture.md` standalone file — archived to `.voss/archive/architecture-YYYY-MM-DD.md`; future writes go into VOSS.md.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Existing `/save` handler at cli.py:473 still has "session snapshot" semantics in M8 timeframe (no intervening phase changed it) | Pitfall 1 | If `/save` already moved to something else, naming collision shape changes; planner picks a different resolution. Verified at HEAD 2026-05-14 by direct grep. |
| A2 | `_run_repl()` is the single REPL entry shared by `chat`, `resume`, `edit` | Req 1 wire point | If `resume_cmd` has its own path that bypasses `_run_repl`, the VOSS.md injection misses one of three entry points. Verified at cli.py:612, 676, 972 — all three call `_run_repl`. |
| A3 | `do_cmd` calls `run_turn` directly (not via `_run_repl`) | Req 1 wire point for `voss do` | If wrong, the injection needs to happen inside `run_turn` instead of at REPL boot. Confirmed by reading cli.py:511-547 — `do_cmd` calls `run_turn` directly. So the VOSS.md prepend must live in BOTH `_run_repl` (for chat/resume/edit, passed through as a kwarg) AND `do_cmd` (also passed as kwarg to run_turn). Alternative: prepend inside `run_turn` itself, gated on a `voss_md_text: str | None = None` kwarg supplied by the caller. **Recommended: do the read in the caller, pass the string in.** |
| A4 | `voss[search]` extra is the ONLY install path for chromadb in M6 npm wrapper users | Pitfall 4 | M6 ships base wheel without chroma per pyproject `[search]` extra design. Verified pyproject.toml lines 22-32. |
| A5 | `.voss/config.yml` does not currently exist (M8 creates it OR planner picks a different path) | User Constraints | If a config.yml file appears in a later phase, M8 plan needs to coexist. Verified — only constraints.yml/permissions.yml/validation.yml exist per cognition.py:573-583. |
| A6 | Conventions extraction does NOT need to run during one-shot `voss do` (only chat REPL) | Req 4 wire point | SPEC says "On clean session exit (any non-error termination of `voss chat` / `voss do`)" — so YES, `voss do` also needs the hook. Re-check: it should fire at `do_cmd` return path too, not only REPL exit. Planner: add the hook in BOTH places. **A6 RESOLVED — SPEC is explicit; both paths.** |
| A7 | `portalocker` is acceptable as a new core dep | Don't Hand-Roll table | If the planner rejects new deps, fall back to the `fcntl`/`msvcrt` guarded import. Pure Pitfall-3 cost question. |
| A8 | Frontmatter inside the `id=architecture` fence body still parses through existing `FRONTMATTER_RE` | Pitfall 2 | If the fence header (`<!-- voss:begin -->\n<!-- voss:hash -->`) is followed by `---\n` frontmatter, regex matches starting at body line 0. Verified by reading regex: `re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)` — works as long as fence body starts with `---`. |

## Open Questions

1. **Should `/forget` glob match against composite IDs OR file paths?**
   - What we know: D-15 says "composite IDs (D-04) and on-disk file paths (glob)" — both.
   - What's unclear: When a user types `/forget turn:*session*` does that delete *only* the chroma index entries for those turns, OR also `.voss/memory/turns/<session>.jsonl`?
   - Recommendation: Both. The on-disk JSONL file is the source of truth per D-01; tombstoning means an in-memory "skip this ID" filter applied on read PLUS a tombstone marker file (e.g. `turns/<session>.tombstone`). Vacuum physically removes both.

2. **What's the chroma metadata schema mapping for `decisions` source?**
   - What we know: D-01 says decisions/ is a "pointer or symlink" to `.voss/decisions/*.md` — no duplication.
   - What's unclear: But chroma needs the document content to embed. Does the indexer READ `.voss/decisions/*.md` and write the body into chroma with metadata `{source_type: "decision", path: "<absolute>", ts: <mtime>}`?
   - Recommendation: Yes — chroma stores the body for vector search, the `path` metadata points back to the canonical file. `/forget decision:.voss/decisions/foo.md` tombstones the chroma row but does NOT delete the underlying decision file (which is a COG-06 artifact owned by recorder.py, not memory_store).

3. **Top-N=5 default for `/recall` — is there an existing surface to align with?**
   - What we know: `SemanticMemory.retrieve(query, top_k=5)` at semantic.py:88 — default 5 matches SPEC Req 5.
   - What's unclear: None — aligned.
   - Recommendation: Use 5. Document the alignment in the M8 plan.

4. **Where does the chroma collection live for the `voss memory vacuum` CLI subcommand when no session is active?**
   - What we know: CLI subcommand needs a `cwd` to find `.voss/memory/chroma/`.
   - What's unclear: Does `voss memory vacuum` accept `--cwd` (matching other Click commands) or default to `.`?
   - Recommendation: `--cwd` flag with default `.`, matching the existing convention at chat_cmd / do_cmd / doctor_cmd.

5. **Should conventions extraction run for `voss do` (one-shot, no REPL)?**
   - What we know: SPEC Req 4 says "any non-error termination of `voss chat` / `voss do`."
   - What's unclear: A `voss do "summarize"` call typically has 1 turn; the D-09 pre-filter would almost never fire.
   - Recommendation: Hook BOTH paths. Pre-filter will correctly skip most `do` invocations. No additional logic needed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.11+ per pyproject | — |
| `chromadb` | SemanticMemory recall | ✓ in dev env | 1.5.9 (Python) | Keyword recall (Req 3 ≥ 60% top-3 floor) |
| `pydantic>=2.6` | Convention candidate schema | ✓ | core dep | — |
| `pyyaml>=6.0` | Config file parsing | ✓ | core dep | — |
| `fcntl` (stdlib POSIX) | Lockfile (D-13) | ✓ on macOS/Linux | builtin | `msvcrt.locking` on Windows OR `portalocker` cross-platform |
| `OPENAI_API_KEY` | OpenAI embeddings | env-dependent | — | `sentence-transformers` local model |
| `sentence-transformers` | Local embedding when no API key | ✓ in `[search]` extra | 2.7.0+ | Error path documented in semantic.py |

**Missing dependencies with no fallback:** None — every dep has a documented fallback.

**Missing dependencies with fallback:**
- `chromadb` not installed → keyword/grep recall (Req 3 ≥ 60% floor).
- `OPENAI_API_KEY` absent → sentence-transformers local model (already wired in `SemanticMemory._embedding_function()`).
- `fcntl` absent (Windows) → see Pitfall 3 resolution.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio (asyncio_mode=auto) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/harness/test_memory_<module>.py -x` (per-module quick gate) |
| Full suite command | `pytest tests/harness/ tests/memory/ -x` |
| Existing test dir | `tests/harness/` (28 files) + `tests/memory/` (already exists for runtime memory tests) |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|--------------|
| 1 | VOSS.md loaded + injected on chat/do/resume | integration | `pytest tests/harness/test_voss_md_injection.py -x` | ❌ Wave 0 |
| 1 | Absence of VOSS.md degrades silently | unit | `pytest tests/harness/test_voss_md_injection.py::test_missing_file_degrades -x` | ❌ Wave 0 |
| 2(a) | Archive byte-identical to pre-migration (sha256) | unit | `pytest tests/harness/test_voss_md_migration.py::test_archive_sha256 -x` | ❌ Wave 0 |
| 2(b) | VOSS.md contains pre-migration content under deterministic anchor | unit | `pytest tests/harness/test_voss_md_migration.py::test_fence_contains_original -x` | ❌ Wave 0 |
| 2(c) | Re-running analyze updates machine fence, preserves human edits | integration | `pytest tests/harness/test_voss_md_migration.py::test_re_analyze_preserves_human -x` | ❌ Wave 0 |
| 3 | Recall ≥ 80% top-3 with chroma, ≥ 60% on keyword fallback over 5-session fixture | integration (eval) | `pytest tests/harness/test_recall_eval.py -x` (parametrized: chroma vs keyword) | ❌ Wave 0 |
| 3 | Source-type tag present on each hit | unit | `pytest tests/harness/test_memory_store.py::test_recall_hits_tagged -x` | ❌ Wave 0 |
| 4 | Convention extraction surfaces ≥ 1 candidate on signal-bearing session | integration | `pytest tests/harness/test_conventions.py::test_scripted_signal_session -x` | ❌ Wave 0 |
| 4 | Declining all candidates writes nothing | unit | `pytest tests/harness/test_conventions.py::test_decline_writes_nothing -x` | ❌ Wave 0 |
| 4 | Accepting writes one file with statement + evidence | unit | `pytest tests/harness/test_conventions.py::test_accept_writes_file -x` | ❌ Wave 0 |
| 5 | All four slash commands registered with --help line | unit | `pytest tests/harness/test_repl_slash.py::test_memory_commands_registered -x` | ✓ (file exists, add tests) |
| 5 | Each command has integration test asserting file/stdout effect | integration | `pytest tests/harness/test_slash_recall.py tests/harness/test_slash_forget.py tests/harness/test_slash_memory.py tests/harness/test_slash_save_note.py -x` | ❌ Wave 0 (4 new files) |
| 5 | `/forget` requires --yes in non-interactive mode | unit | `pytest tests/harness/test_slash_forget.py::test_requires_yes_noninteractive -x` | ❌ Wave 0 |
| 6 | Seeding store to 110% triggers eviction; post-write size ≤ cap | unit | `pytest tests/harness/test_memory_eviction.py::test_inline_evict_on_overage -x` | ❌ Wave 0 |
| 6 | `voss memory vacuum` reports nonzero bytes reclaimed on tombstoned store | integration | `pytest tests/harness/test_memory_vacuum.py::test_vacuum_reclaims_tombstones -x` | ❌ Wave 0 |
| 7 | `grep -rn "^class .*Memory" voss/harness/` returns zero matches | static / lint | `pytest tests/harness/test_memory_runtime_reuse.py::test_no_harness_memory_subclasses -x` | ❌ Wave 0 |
| 7 | Recall pipeline calls `voss_runtime.memory.SemanticMemory.__init__` | integration | `pytest tests/harness/test_memory_runtime_reuse.py::test_semantic_memory_instantiated -x` (mock-patch init) | ❌ Wave 0 |
| Constraint | `voss resume <pre-M8-id>` rehydrates without crash | integration | `pytest tests/harness/test_session.py::test_resume_pre_m8_no_crash -x` (existing file, add fixture) | ✓ partial |
| Constraint | Recall degrades to keyword without ImportError when chromadb uninstalled | integration | `pytest tests/harness/test_memory_store.py::test_no_chroma_no_import_error -x` (uninstall via venv fixture OR sys.modules patch) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/harness/test_memory_<module>.py -x` (the file owned by that task)
- **Per wave merge:** `pytest tests/harness/ -x -k "memory or voss_md or conventions"` (full M8 test surface, ~3 min)
- **Phase gate:** `pytest tests/harness/ tests/memory/ -x` (full harness + runtime memory regressions)

### Wave 0 Gaps

The following test files do not exist and must be created in Wave 0 before any implementation task:

- [ ] `tests/harness/test_voss_md_injection.py` — Req 1 acceptance
- [ ] `tests/harness/test_voss_md_migration.py` — Req 2 acceptance (3 tests: archive sha256, fence content, re-analyze preservation)
- [ ] `tests/harness/test_voss_md_fence.py` — Pattern 1 parser unit tests (fence parse, hash mismatch, write round-trip)
- [ ] `tests/harness/test_memory_store.py` — Req 3 + Req 7 (recall hits tagged, no-chroma fallback, source-type filter)
- [ ] `tests/harness/test_recall_eval.py` — Req 3 hit-rate floors (parametrized chroma vs keyword)
- [ ] `tests/harness/test_conventions.py` — Req 4 (signal pre-filter, accept/decline, timeout)
- [ ] `tests/harness/test_slash_recall.py` — Req 5
- [ ] `tests/harness/test_slash_forget.py` — Req 5 + Req 6 (tombstone semantics, --yes gate)
- [ ] `tests/harness/test_slash_memory.py` — Req 5 (summary rendering)
- [ ] `tests/harness/test_slash_save_note.py` — Req 5 (note append; collision resolution test)
- [ ] `tests/harness/test_memory_eviction.py` — Req 6 inline eviction
- [ ] `tests/harness/test_memory_vacuum.py` — Req 6 vacuum CLI
- [ ] `tests/harness/test_memory_runtime_reuse.py` — Req 7 (grep gate + init mock)
- [ ] `tests/harness/conftest.py` additions — fixtures for: 5-session seeded corpus (recall eval), VOSS.md migration fixture (pre-M8 architecture.md), scripted-signal session for conventions, tombstoned store
- [ ] `tests/harness/test_session.py` — extend with `test_resume_pre_m8_no_crash` (existing file)

**Existing file to extend:** `tests/harness/test_repl_slash.py` — add `test_memory_commands_registered`.

## Security Domain

Per `.planning/config.json` (no `security_enforcement` key present → treat as enabled per default).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | M8 introduces no new auth surface; uses existing provider auth. |
| V3 Session Management | yes (lightly) | Memory entries are tagged by `session_id` (existing M2 uuid4-derived id). No new session-token surface. |
| V4 Access Control | yes | Path jail under `--cwd` (existing CTRL-06) applies to all `.voss/memory/` writes. Memory writer must use existing sandbox helpers. |
| V5 Input Validation | yes | Pydantic-validated D-10 conventions schema. `/forget` pattern input passes through `shlex.split` and a glob matcher; no shell interpretation. `/save <note>` arbitrary text is written to file (slug-derived path only; planner verifies slug escapes path-traversal). |
| V6 Cryptography | yes | `hashlib.sha256` (stdlib) for D-06/D-07 fence-hash integrity and archive byte-equality. Standard, not hand-rolled. |
| V7 Error handling | yes | `ModuleNotFoundError` fallback paths (chroma absent) must not leak stack traces. Existing pattern: friendly message + degraded behavior. |
| V8 Data protection | yes | `.voss/memory/turns/*.jsonl` and `notes/*.md` may capture sensitive user prompts. Existing `SessionRecord` redaction guarantee (session.py:14-35) only covers harness-attached fields; user-typed content is allowed (mirrors `EpisodicMemory.content` policy). **Document this in `/memory` output so user sees what's persisted.** Filesystem permission: existing `path.chmod(0o600)` pattern on session writes (session.py:144) should apply to memory writes. |
| V10 Malicious code | yes | `/save <note>` and conventions/notes file paths derive from slug — verify slug strips `..` and shell-special chars (existing `cognition.slug()` already does this — confirm in plan). |
| V12 File and Resources | yes | Path traversal prevention: all memory writes must resolve through `cwd / ".voss" / "memory" / ...` and reject paths escaping. fs_write tool already enforces sandbox; M8 writers should reuse `sandbox.write_*` helpers (if they exist; planner verifies). |

### Known Threat Patterns for Python harness + filesystem store

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `/save ../../etc/foo` | Tampering | `slug()` + `reserve_filename()` constrain output path; reject names containing path separators. |
| Hash-collision spoofing of fence baseline | Tampering | sha256 (256-bit) is sufficient for integrity; not a security boundary (no adversary model — local file edits assumed trusted). Document this is integrity-not-authenticity. |
| Lockfile races (TOCTOU on size check + write) | DoS / Tampering | `fcntl.flock(LOCK_EX | LOCK_NB)` is atomic; size-check inside the lock. D-13 explicit. |
| Embedding API key exfiltration via stored memory | Information disclosure | `OPENAI_API_KEY` lives in env vars, never in memory store content. Existing redaction invariant (session.py:14-35) extends to memory store: fixed-field allowlist on the writers. |
| Tombstoned content readable until vacuum | Information disclosure | Acceptable per D-15; `/memory` summary must not surface tombstoned entries. Document in `/memory` output. |
| Concurrent session corrupting on-disk index | DoS | Per-source advisory lockfile (D-13). Non-blocking + degraded-read fallback. |

## Project Constraints (from CLAUDE.md)

`./CLAUDE.md` does not exist in this repo. Global `~/.claude/CLAUDE.md` (QuadFlow integration + SecondBrain memory sidecar) is user-environment, not project-binding. No project-level directives override M8 plan.

## Sources

### Primary (HIGH confidence)
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M8-project-memory-mem-01/M8-SPEC.md` — 7 locked requirements + boundaries + acceptance criteria.
- `/Users/benjaminmarks/Projects/Voss/.planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md` — 16 implementation decisions D-01..D-16.
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/memory/episodic.py` — EpisodicMemory full API.
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/memory/semantic.py` — SemanticMemory full API + chroma fallback pattern.
- `/Users/benjaminmarks/Projects/Voss/voss_runtime/memory/working.py` — WorkingMemory full API.
- `/Users/benjaminmarks/Projects/Voss/voss/harness/session.py` — SessionRecord schema + load/save + backward-compat reader.
- `/Users/benjaminmarks/Projects/Voss/voss/harness/slash.py` — SlashCommand + SlashRegistry pattern.
- `/Users/benjaminmarks/Projects/Voss/voss/harness/cli.py` — `_build_slash_registry()`, `_run_repl()`, `chat_cmd`, `do_cmd`, `resume_cmd` — all wire points.
- `/Users/benjaminmarks/Projects/Voss/voss/harness/agent.py` — `run_turn`, `_compose_cognition_prompt`, sys_prompt assembly.
- `/Users/benjaminmarks/Projects/Voss/voss/harness/cognition.py` — `bootstrap_prompt`, `_load_arch`, `FRONTMATTER_RE`, preserve-if-exists writers.
- `/Users/benjaminmarks/Projects/Voss/voss/harness/skills/analyze.py` — COG-02 write path target.
- `/Users/benjaminmarks/Projects/Voss/voss/harness/recorder.py` — `write_decisions_md` template for conventions mirror.
- `/Users/benjaminmarks/Projects/Voss/pyproject.toml` — dependency pins + `[search]` extra design.

### Secondary (MEDIUM confidence)
- `https://docs.trychroma.com/docs/collections/delete-data` — `collection.delete(where={...})` API (cross-verified via WebSearch result).
- `pip index versions chromadb` (Python) returned 1.5.9 latest (2026-05-14 run).
- `npm view chromadb version` returned 3.4.3 — different JS package, noted only for disambiguation.

### Tertiary (LOW confidence)
- None — all critical claims are verified against codebase or official docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already pinned in pyproject; no new external research needed beyond chroma delete-where API.
- Architecture: HIGH — wire points verified by file:line grep; decisions D-01..D-16 cover topology.
- Pitfalls: HIGH — pitfalls 1, 2, 3 verified by direct code reading + cross-platform fact-checking. Pitfalls 4, 5, 6 are reasoned-not-verified but grounded in identified code paths.
- Validation architecture: HIGH — every SPEC acceptance criterion mapped to a named test file with an explicit command.

**Research date:** 2026-05-14
**Valid until:** 2026-06-14 (30 days — stable codebase, no rapidly-moving external deps)
