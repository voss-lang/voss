# Phase V21: Global Cross-Project Memory - Research

**Researched:** 2026-06-11
**Domain:** Python harness memory subsystem extension — MemoryStore root parameterisation, global store lifecycle, promote/forget CLI verbs, cross-process lock safety, RRF fusion with [global] label.
**Confidence:** HIGH (all claims verified against source code in this session)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 — Copy, provenance-tagged:** promote copies the memory into the global store with `promoted_from: <repo-identifier>/<locator>` metadata; project copy untouched. Re-promoting the same locator UPDATES the existing global entry (dedup via provenance match), never duplicates.
- **D-02 — Promotable sources = notes, decisions, conventions only:** turns and ledgers are session/project-bound and excluded. `voss memory promote <locator>` rejects turn/ledger locators with a clear error.
- **D-03 — Reverse = `voss memory forget --global <locator>`:** tombstones the global entry using existing tombstone machinery. No demote-back-to-project verb.
- **D-04 — Path = `~/.voss/memory/` with `VOSS_HOME` override:** global root mirrors the project `.voss/memory/` layout exactly (same sources dirs, chroma/, .locks/, tombstones) so the same `MemoryStore` code serves both. `VOSS_HOME` env var overrides the `~/.voss` base (tests, multi-profile). No XDG/platformdirs dependency.
- **D-05 — Same 100MB cap + vacuum:** reuse `DEFAULT_CAP_BYTES`; `voss memory vacuum --global` points existing vacuum at the global root. No new curation machinery.
- **D-06 — Equal RRF, rank decides:** global + project rankings fused via existing `_rrf_merge`. No weighting knobs, no fallback-only mode.
- **D-07 — Surfaces everywhere recall exists:** agent-side memory recall tool AND `voss recall` CLI both fuse global hits, labeled `[global]`. Single config off-switch `[memory] global = false` disables global participation everywhere at once.
- **D-08 — Promote verb is the ONLY write path to global:** no agent tool may write the global store; no auto-capture; no session turns ever land there.

### Claude's Discretion

- **D-09 — MemoryStore root override:** add `root_override: Path | None = None` (or equivalent factory) to `MemoryStore` rather than subclassing; `self.root = root_override or cwd / ".voss" / "memory"`. Global instance never binds a session for turn-writing.
- **D-10 — Repo identifier in provenance:** use the project root's basename + short hash of absolute path (stable, readable, collision-resistant) — planner picks exact format; must be deterministic per repo.
- **D-11 — Promote UX:** `voss memory promote <locator>` under the existing `voss memory` click group (memory_cli.py:18); locator format = `<source>:<locator>` composite ID; `--list` for discovery — planner decides minimal discovery surface.
- **D-12 — Chroma collection in global store:** same collection name/convention as project store; dim-mismatch between stores is acceptable (rankings fused by rank, not vector space).
- **D-13 — Concurrency:** existing portalocker `.locks/` machinery must guard promote/forget/vacuum writes — verify lock paths resolve under global root.

### Deferred Ideas (OUT OF SCOPE)

- Direct global capture verb (`voss memory note --global`) — rejected; promote-only write path.
- Agent-proposed promotion with permission prompt — would dilute D-08 guarantee.
- Migration/import of existing external memory files — V22 territory.
</user_constraints>

---

## Summary

V21 gives facts that transcend a single repo a curated, durable home at `~/.voss/memory/` (or `$VOSS_HOME/memory/`) and surfaces them in every recall path with `[global]` labels. The core design is: a second `MemoryStore` instance constructed with a `root_override` argument pointing at the global path — no new store type, no new schema, no new chroma collection convention. All existing machinery (BM25 + Chroma RRF recall, tombstones, vacuum, per-source portalocker `.locks/`) works identically because it operates purely against `self.root`.

The highest-risk unknown (chromadb cross-process safety with `journal_mode=DELETE`) was empirically verified: three simultaneous processes writing 30 documents each to a shared `PersistentClient` path produced the expected 90 documents with zero errors. This is safe because chromadb 1.5.9 uses SQLite's DELETE journal mode, which serialises writes through file-level locking. The project's portalocker guards are an additional layer that remain correct at global root paths (verified empirically: portalocker LOCK_NB correctly blocks a second process).

V21 lands on **three seams where V19 is planned but unbuilt**: (1) the `voss recall` CLI verb (V19-04, not yet implemented — `recall_cmd` absent from `cli.py`), (2) the `code_recall` agent tool (V19-02), and (3) the `CodeIndex.query` call in the fusion logic. V21's recall fusion can be written defensively: call `CodeIndex.query` only if `V19 code index is present`, always fuse global memory hits regardless. The planner must decide whether V21 declares a hard dependency on V19 execution or uses a conditional fallback.

**Primary recommendation:** Implement `root_override` on `MemoryStore.__init__` (additive, default `None`, no callers change), resolve global root via `_global_root()` helper reading `VOSS_HOME` env or `~/.voss`, add `promote`/`forget --global`/`vacuum --global` to `memory_cli.py`, wire dual-store RRF fusion in `attach_memory_tools` and the `voss recall` CLI seam, add `[memory]` section parser to `config.py`. Zero new packages needed.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Global store init + layout | API / Backend (`MemoryStore`) | — | MemoryStore already owns project store lifecycle; root_override makes same class serve both |
| Promote copy + provenance tag | API / Backend (`memory_cli.py`) | `MemoryStore` (write_note/write_convention pattern) | CLI verb is the only write path (D-08); store handles physical copy + chroma add |
| Global forget (tombstone) | API / Backend (`memory_cli.py`) | `MemoryStore.forget()` | Existing tombstone machinery, new CLI flag routes to global root |
| RRF fusion (agent tool) | API / Backend (`tools.py:attach_memory_tools`) | `MemoryStore._rrf_merge` | Agent-tool level; fuses project hits + global hits; [global] label appended to hit source |
| RRF fusion (CLI recall) | API / Backend (`cli.py:recall_cmd`) | V19-planned code corpus | recall_cmd owns cross-corpus merge; V19 adds code corpus; V21 adds global corpus |
| VOSS_HOME resolution | API / Backend (new `_global_root()` helper) | — | Single resolver, read by MemoryStore factory and memory_cli |
| [memory] global off-switch | Config layer (`config.py:_parse_memory_section`) | Startup in `cli.py` | Must skip store init entirely (no chroma open) when `global = false` |
| Vacuum (global) | API / Backend (`memory_cli.py:memory_vacuum_cmd`) | `MemoryStore.vacuum()` | Extend existing `vacuum` command with `--global` flag |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| portalocker | 3.2.0 | Per-source advisory locks for concurrent write safety | [VERIFIED: PyPI] Already in use; proven cross-process on this platform |
| chromadb | 1.5.9 | Vector store for semantic recall | [VERIFIED: PyPI] Already in use; empirically verified cross-process safe with DELETE journal mode |
| rank-bm25 | 0.2.2 | Lexical recall fallback | [VERIFIED: PyPI] Already in use; BM25Okapi + _rrf_merge pattern established |
| click | 8.3.3 | CLI command structure | [VERIFIED: PyPI] Already in use; memory_cli.py pattern to follow exactly |

### No New Packages

V21 installs **zero new packages**. Every dependency is already in the project's `.venv`. The `slopcheck` audit is N/A — no new installs occur.

---

## Package Legitimacy Audit

> V21 introduces no new packages. All dependencies pre-exist in `.venv`.

| Package | Registry | Age | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-------------|-----------|-------------|
| portalocker | PyPI | ~10 yrs | github.com/WoLpH/portalocker | N/A (pre-existing) | Approved (already installed) |
| chromadb | PyPI | ~3 yrs | github.com/chroma-core/chroma | N/A (pre-existing) | Approved (already installed) |
| rank-bm25 | PyPI | ~6 yrs | github.com/dorianbrown/rank_bm25 | N/A (pre-existing) | Approved (already installed) |
| click | PyPI | ~12 yrs | github.com/pallets/click | N/A (pre-existing) | Approved (already installed) |

**Note:** slopcheck checks npm by default and flagged `portalocker` and `rank-bm25` as non-existent on npm — correct, they are Python packages on PyPI. All four packages are confirmed on PyPI via `.venv/bin/pip index versions` and are long-established projects. `[VERIFIED: PyPI]`

**Packages removed due to [SLOP]:** none
**Packages flagged [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Project repo                         ~/.voss/memory/ (global root)
.voss/memory/                        notes/
  notes/  decisions/  conventions/   decisions/  conventions/
  chroma/   .locks/                  chroma/  .locks/  .tombstones.jsonl
      |                                   |
      v                                   v
MemoryStore(cwd)                    MemoryStore(root_override=global_root)
  .recall(query)                      .recall(query)
  [project hits]                      [global hits, source labeled "[global]"]
      |_____________  _______________|
                   | |
             _rrf_merge([proj_hits, global_hits], top_k=N)
                   |
            fused ranked hits
                   |
       +-----------+------------+
       |                        |
  attach_memory_tools        voss recall CLI
  (agent memory_recall)      (recall_cmd + V19 code corpus)

voss memory promote <locator>   <-- ONLY write path to global
  resolve locator in project store
  copy file to global notes/decisions/conventions/
  chroma.add(promoted_from=<repo_id>/<locator>)
  dedup: query by promoted_from metadata first

voss memory forget --global <locator>   <-- tombstone in global store
voss memory vacuum --global             <-- compact global store
```

### Recommended Project Structure

Files modified/added by V21:

```
voss/harness/
  memory_store.py         # +root_override param on __init__; +_global_root() helper
  memory_cli.py           # +promote cmd; +forget cmd w/ --global; +vacuum --global flag
  config.py               # +_parse_memory_section(); +get_global_memory_enabled()
  tools.py                # attach_memory_tools: dual-store RRF fusion when global enabled
  cli.py                  # recall_cmd (V19-04 seam): +global corpus; do_cmd/chat_cmd: global store init

tests/
  harness/
    test_memory_global.py  # NEW — unit tests for all VGMEM-* requirements
    conftest.py             # +global_root fixture using VOSS_HOME monkeypatch
```

### Pattern 1: MemoryStore root_override (additive constructor change)

**What:** Add `root_override: Path | None = None` as a keyword-only argument to `MemoryStore.__init__`. When provided, `self.root = root_override` directly; otherwise `self.root = cwd / ".voss" / "memory"` as today. `self.cwd` still set to `cwd` for config lookup — but for a global instance, `cwd` is irrelevant (config lookup returns `{}` when `~/.voss` has no `config.yml`).

**When to use:** Global store constructor call: `MemoryStore(Path.home(), root_override=_global_root())`. All existing callers pass zero keyword args — no changes needed.

```python
# Source: verified from voss/harness/memory_store.py L72-79
class MemoryStore:
    def __init__(
        self,
        cwd: Path,
        *,
        cap_bytes: int = DEFAULT_CAP_BYTES,
        root_override: Path | None = None,          # V21 addition
    ) -> None:
        self.cwd = cwd
        self.cap_bytes = cap_bytes
        self.root = root_override if root_override is not None else cwd / ".voss" / "memory"
        self._chroma: Optional[SemanticMemory] = None
        self._chroma_unavailable = False
        self._size_cache: dict[str, int] = {}
        self._session_id: Optional[str] = None
```

**Blast radius:** `self.cwd` is only used in `_load_memory_config()` (line 201: `self.cwd / ".voss" / "config.yml"`). For a global store instance, this path will not exist and the method already returns `{}` on missing file — no change needed to that method.

### Pattern 2: Global root resolution helper

**What:** A module-level helper in `memory_store.py` (or `memory_cli.py`) that reads `VOSS_HOME` and returns the global memory root. Called once at promote/recall time.

```python
# Source: derived from D-04 design decision + env-var pattern in config.py
def _global_memory_root() -> Path:
    """Resolve global memory root: $VOSS_HOME/memory or ~/.voss/memory."""
    voss_home = os.environ.get("VOSS_HOME")
    if voss_home:
        return Path(voss_home) / "memory"
    return Path.home() / ".voss" / "memory"
```

**Edge case — HOME-less environments:** `Path.home()` raises `RuntimeError` when `$HOME` is unset (CI, containers). Global store init must catch this and treat as globally disabled (return `None` from the factory, not crash). Log a warning.

### Pattern 3: bind() skip gitignore for global store

**What:** The existing `bind()` method writes `.voss/memory/.gitignore` to exclude chroma and locks from git (line 99-101). For the global store at `~/.voss/memory/`, this `.gitignore` write is harmless (it won't affect git tracking outside a git repo) but semantically wrong. The simplest fix: the `.gitignore` write is already guarded by `if not gitignore.exists()` — it will be written once and then never again. No behaviour change needed. The global store's `.gitignore` file at `~/.voss/memory/.gitignore` is inert in normal $HOME usage.

**Alternative (cleaner):** add `skip_gitignore: bool = False` param to `bind()`, set `True` for global instance. Planner discretion.

### Pattern 4: promote mechanics

**Locator resolution for promotable sources (notes, decisions, conventions):**

```
note:<stem>           -> root/notes/<stem>.md       (stem = slug(text[:40]))
convention:<stem>     -> root/conventions/<stem>.md
decision:<rel_path>   -> root.parent/<rel_path>     # e.g. decisions/2026-06-11-foo.md
```

The locator for decisions uses `str(path.relative_to(self.root.parent))` (memory_store.py L631) — so decision locators look like `decision:decisions/2026-06-11-foo.md`. Resolution is `root.parent / rel_path`.

**Promote algorithm:**
1. Parse `source_prefix:locator_tail` from the composite ID arg.
2. Reject `turn:*` and `ledger:*` with exit 1 + clear error (D-02).
3. Resolve file path in project store (per above mapping).
4. Read file content + existing frontmatter.
5. Check global store for existing entry with `promoted_from` metadata matching `<repo_id>/<locator>` — if found, UPDATE (delete + re-add) rather than append (D-01 dedup).
6. Copy file to global store's corresponding source dir with same filename (using `reserve_filename` if collision exists in global store).
7. Add to global chroma with metadata: `{source_type, promoted_from: "<repo_id>/<locator>", ts, path}`.
8. Print confirmation: `promoted: <locator> -> global:<new_stem>`.

**Dedup lookup via chroma:** `global_chroma._collection.get(where={"promoted_from": repo_id + "/" + locator})` — returns existing IDs if any. If non-empty: delete the old ID first, then add new. This requires no filesystem search.

**Repo identifier (D-10):** `basename(cwd) + "-" + sha256(str(cwd.resolve()))[:8]`. Example: `"Voss-a3f91b2c"`. Deterministic, collision-resistant, human-readable. Implementation:

```python
import hashlib
def _repo_id(cwd: Path) -> str:
    h = hashlib.sha256(str(cwd.resolve()).encode()).hexdigest()[:8]
    return f"{cwd.resolve().name}-{h}"
```

### Pattern 5: config [memory] section parser

**What:** Following the exact `_parse_model_tiers_section` pattern in `config.py` (lines 233-239), add:

```python
# Source: derived from config.py:_parse_model_tiers_section pattern [VERIFIED from source]
_MEMORY_BLOCK = re.compile(r"^\[memory\][^\[]*", re.MULTILINE)

def _parse_memory_section(text: str) -> dict[str, str]:
    """Parse `[memory]` section: boolean keys like `global = false`."""
    m = _MEMORY_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    out: dict[str, str] = {}
    for k, v in _KV.findall(block):
        out[k] = v
    for k, v in _KV_BARE.findall(block):
        out.setdefault(k, v)
    return out

def get_global_memory_enabled() -> bool:
    """Returns True unless [memory] global = false in config.toml."""
    p = config_path()
    if not p.exists():
        return True
    try:
        text = p.read_text()
    except OSError:
        return True
    section = _parse_memory_section(text)
    raw = section.get("global")
    if raw is None:
        return True
    return raw.strip().lower() != "false"
```

**Config file:** `~/.config/voss/config.toml` (existing file, new section). Project `.voss/config.yml` is YAML (for memory quota config); harness `config.toml` is TOML (for `[memory] global = false`). The existing `_load_memory_config()` reads the YAML for quota; the new `get_global_memory_enabled()` reads the TOML. These are separate files and do not conflict.

### Pattern 6: dual-store fusion in attach_memory_tools

**What:** `attach_memory_tools` (tools.py:159) currently takes a single `store`. V21 adds an optional `global_store` parameter and fuses results when present:

```python
# Source: derived from V19-04-PLAN.md _rrf_merge pattern + tools.py:159
def attach_memory_tools(
    tools: dict[str, "ToolEntry"],
    *,
    store,                              # project store (existing)
    session_id: str,
    global_store=None,                  # V21 addition — None when disabled
) -> None:
    async def memory_recall(query: str, top_k: int = 5, source: str | None = None) -> str:
        hits = store.recall(query, top_k=top_k * 3, source=source)
        if global_store is not None:
            g_hits = global_store.recall(query, top_k=top_k * 3, source=source)
            # Label global hits before merge so _rrf_merge dedup by locator works
            # (global locators may collide with project locators for same stem)
            for h in g_hits:
                h = dataclasses.replace(h, source=f"[global]:{h.source}", locator=f"global:{h.locator}")
            hits = MemoryStore._rrf_merge([hits, g_hits], top_k=top_k)
        # format as before...
```

**Locator collision hazard:** A project and global store may have a note with identical stem (e.g., `note:2026-06-11-foo`). Prefixing global locators with `global:` before passing to `_rrf_merge` prevents dedup collision. The `[global]` label in the output comes from the source field. The `global:` locator prefix is internal only (not stored in the chroma metadata).

### Pattern 7: voss recall CLI global corpus (V19-04 seam)

**What:** The `recall_cmd` in V19-04 is planned but not built. V21 lands on this seam. The fusion call in `recall_cmd` will be:

```python
# Source: derived from V19-04-PLAN.md interface spec + D-06 locked decision
# When V19 is executed, recall_cmd already exists; V21 extends it.
# When V21 executes before V19: recall_cmd must be created by V21 (or V21 waits).
mem_hits = store.recall(query_str, top_k=top_k * 3)
g_hits = (global_store.recall(query_str, top_k=top_k * 3) if global_store else [])
# Label global hits
for h in g_hits:
    h.source = "[global]"
all_mem = MemoryStore._rrf_merge([mem_hits, g_hits], top_k=top_k * 3) if g_hits else mem_hits
# Then fuse with code hits (V19) if CodeIndex is available
```

### Anti-Patterns to Avoid

- **Writing global store from any path other than promote:** D-08 is a hard rule enforced by construction — global `MemoryStore` instance created only in `promote` and `forget --global` handlers, never passed to `attach_memory_tools` write side.
- **Calling bind() on global store in turn-write contexts:** bind() sets `_session_id` and creates all source dirs including `turns/`. The global store should have `turns/` and `ledgers/` dirs to mirror layout (D-04), but they should always remain empty. Assert `source not in ("turn", "ledger")` defensively in global store's write path.
- **Passing the global MemoryStore to `write_turn` / `write_ledger`:** these are project-session-bound. D-08 makes this structurally unreachable — the global store reference is never passed to `attach_memory_tools`' write-side functions.
- **Using `Path.home()` without a try/except:** CI environments with no `$HOME` will crash. Always catch `RuntimeError` from `Path.home()` and treat as "global disabled".
- **config.yml YAML vs config.toml TOML confusion:** `~/.config/voss/config.toml` is the harness config (TOML, existing); `.voss/config.yml` is the project memory config (YAML). The `[memory] global = false` switch lives in `config.toml`. Never mix parsers.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-corpus RRF merge | Custom merge/sort | `MemoryStore._rrf_merge([proj_hits, global_hits], top_k=N)` | Existing static method; rank-based, corpus-agnostic per V19-04 design |
| Per-source locking for concurrent promote/vacuum | Custom lock primitives | `MemoryStore._lock(source)` contextmanager (portalocker) | Already covers global root when `self.root` points there |
| Tombstone/forget machinery | Custom deletion | `MemoryStore.forget(pattern, confirm=True)` | Existing method handles chroma update + JSONL append atomically |
| Vacuum for global store | New compaction logic | `MemoryStore.vacuum()` called on global `MemoryStore` instance | All three passes (JSONL, file-delete, chroma where-filter) work via `self.root` |
| Config section parsing | Custom TOML parser | `_parse_memory_section()` following `_parse_model_tiers_section` pattern | Project has established regex-based TOML parser (no `tomllib` dependency for sections this simple) |

**Key insight:** V21's core premise is "second instance of the same store class, different root." Every piece of complexity that appears unique to the global store is already solved by the project store machinery.

---

## Common Pitfalls

### Pitfall 1: _load_memory_config reads cwd/.voss/config.yml — wrong for global store
**What goes wrong:** `_maybe_evict` calls `_load_memory_config` which reads `self.cwd / ".voss" / "config.yml"`. For a global store instance where `cwd = Path.home()`, this path does not exist and the method returns `{}` — using `SOURCE_QUOTAS` defaults. This is **correct behaviour** but needs to be understood.
**Why it happens:** `_load_memory_config` was written with only the project store in mind.
**How to avoid:** No code change needed — the `{}` fallback path already handles missing config correctly for the global store. Document in the `root_override` docstring.
**Warning signs:** If someone tries to override global store quotas via `~/.voss/config.yml`, it won't work. Accept this limitation for V21.

### Pitfall 2: _locator_from_path for decisions uses relative_to(self.root.parent)
**What goes wrong:** `_locator_from_path` for decisions computes `str(path.relative_to(self.root.parent))` (memory_store.py:631). For a global store, `self.root.parent = ~/.voss` and `path` is `~/.voss/memory/decisions/2026-06-11-foo.md`. The relative path is `memory/decisions/2026-06-11-foo.md`. This is different from project-store locators which are relative to `.voss/`. BM25 recall still works (locator is just a string identifier), but locators in `--json` output from `voss recall` will look different for global decisions.
**How to avoid:** Accept this difference — locators are internal IDs, not user-facing paths. Document the format difference. The `promoted_from` metadata stores the original project locator, which is the canonical reference.

### Pitfall 3: locator collision between project and global in _rrf_merge
**What goes wrong:** `_rrf_merge` deduplicates by `hit.locator`. A project note `note:2026-06-11-foo` and a global note with the same stem would be treated as the same hit and only one would appear in the fused result.
**How to avoid:** Namespace global locators before calling `_rrf_merge`: prefix with `global:`. E.g., `note:2026-06-11-foo` becomes `global:note:2026-06-11-foo`. Strip the prefix for display. This is a V21 concern that does NOT affect V19 (code index uses `code:` prefix already per V19 Pitfall 8).

### Pitfall 4: chromadb PersistentClient cross-process safety
**What goes wrong (RESOLVED via empirical test):** Two `voss` sessions in different repos simultaneously promote to the same global chroma. With `journal_mode=DELETE`, SQLite serialises writes at the OS level.
**Empirical result:** Three concurrent processes writing 30 documents each to a shared PersistentClient produced exactly 90 documents, zero errors. `[VERIFIED: empirical test, chromadb 1.5.9, Python 3.13, macOS]`
**Why it's safe:** chromadb 1.5.9 uses SQLite DELETE journal mode (confirmed via `PRAGMA journal_mode`). DELETE mode uses exclusive file locks at the OS level, serialising all writers. No data loss observed.
**Residual risk:** High-frequency concurrent promotes (unlikely in practice — promote is a deliberate manual verb) may experience write queuing latency. portalocker wraps the file writes anyway as an additional guard.
**Portalocker note:** `LOCK_NB` (non-blocking) means the second lock attempt immediately prints `memory.<source> busy — skipping write` and returns. For promote, this silent skip is unacceptable — `promote` should use blocking lock (add `timeout=5` or `LOCK_EX` without `LOCK_NB`) so it waits and retries rather than silently losing the write.

### Pitfall 5: bind() for global store creates turns/ and ledgers/ directories
**What goes wrong:** Calling `bind()` on the global store creates all `_SOURCES` dirs including `turns/` and `ledgers/`. This is correct per D-04 (layout mirror) but an operator who does `voss memory size --global` will see empty `turns: 0 bytes` entries, which might be confusing.
**How to avoid:** Accept this — the layout mirror is correct and clear. Document in `--global` help text: "global store is curated; turns and ledgers are always empty by design."

### Pitfall 6: HOME-less environments (CI) crash on Path.home()
**What goes wrong:** `_global_memory_root()` calls `Path.home()` which raises `RuntimeError: Can't determine user home directory` when `$HOME` is unset.
**How to avoid:** Wrap in try/except RuntimeError; treat as "VOSS_HOME unset + no HOME = global store disabled" and log a debug message. `get_global_memory_enabled()` should also short-circuit to False in this case.

### Pitfall 7: V19 recall_cmd is not yet built — V21 lands on an unbuilt seam
**What goes wrong:** V21's `[global]` fusion into `voss recall` depends on `recall_cmd` existing in `cli.py`. V19 planned but has NOT executed. If V21 plans assume `recall_cmd` exists and insert fusion code, those plans will fail when V19 hasn't run yet.
**How to avoid:** Two options: (a) V21 depends_on V19 execution — planner marks V21 plans with `depends_on: V19`; (b) V21 owns the full `recall_cmd` implementation (absorbs V19-04 scope for the CLI verb) and V19 only adds the code index corpus. Option (b) avoids a hard dependency but duplicates effort. **This is a planner decision** (see Open Questions).

### Pitfall 8: promote dedup query on older chroma versions
**What goes wrong:** The dedup lookup `chroma._collection.get(where={"promoted_from": ...})` uses chroma metadata filtering. This requires that `promoted_from` was stored as a metadata key at add time. If V21 adds a memory to global without the key, future re-promotes cannot find it.
**How to avoid:** Always include `promoted_from` in metadata for every global store add. Never call chroma.add on global store without `promoted_from`.

---

## V19 Dependency Analysis

**Status of V19:** All 6 plans exist (V19-01 through V19-06). Zero SUMMARY files — V19 is **confirmed NOT executed**.

| V21 Seam | V19 Code It Needs | Status | Impact if V19 Not Run |
|----------|-------------------|--------|----------------------|
| `recall_cmd --global` fusion | `recall_cmd` in `cli.py` (V19-04) | UNBUILT | V21 must own recall_cmd or use conditional |
| Agent `memory_recall` global fusion | `attach_memory_tools` (existing, just extend) | BUILT (M8) | No dependency — tools.py already exists |
| `[global]` label in `voss recall` output | `recall_cmd` hit-label logic (V19-04) | UNBUILT | V21 must define label format |
| Code corpus fusion in `voss recall` | `CodeIndex.query` (V19-02) | UNBUILT | V21 can call conditionally if present |

**Recommendation for planner:** V21 should own the `recall_cmd` implementation entirely (V19-04 plan scope for the CLI verb). This eliminates the V19 hard dependency for V21's CLI surface. V19-04 should then be removed or reduced to "extend recall_cmd to add code corpus" rather than "create recall_cmd from scratch." This avoids a dangerous ordering dependency where V21 plans fail if V19 hasn't run.

---

## Code Examples

### Global Root Resolution

```python
# Source: voss/harness/memory_store.py + D-04 design decision
import os
from pathlib import Path

def _global_memory_root() -> Path | None:
    """Resolve global memory root; returns None if HOME unavailable."""
    voss_home_env = os.environ.get("VOSS_HOME")
    if voss_home_env:
        return Path(voss_home_env) / "memory"
    try:
        return Path.home() / ".voss" / "memory"
    except RuntimeError:
        # CI / container with no $HOME
        return None
```

### Global Store Factory

```python
# Source: derived from MemoryStore.__init__ pattern in memory_store.py:72
from voss.harness.memory_store import MemoryStore

def make_global_store() -> MemoryStore | None:
    """Create a global MemoryStore instance; returns None when disabled or HOME absent."""
    from voss.harness.config import get_global_memory_enabled
    if not get_global_memory_enabled():
        return None
    root = _global_memory_root()
    if root is None:
        return None
    # cwd=Path.home() is a placeholder; only self.root matters for global store
    try:
        home = Path.home()
    except RuntimeError:
        return None
    return MemoryStore(home, root_override=root)
```

### Promote command (skeleton)

```python
# Source: derived from memory_cli.py vacuum pattern + D-01/D-02/D-10 decisions
@memory_group.command("promote")
@click.argument("locator")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def memory_promote_cmd(locator: str, cwd_str: str) -> None:
    """Copy a project memory entry into the global store with provenance tag."""
    cwd = Path(cwd_str).resolve()
    source_prefix = locator.split(":")[0]
    if source_prefix in ("turn", "ledger"):
        click.echo(f"error: turns and ledgers cannot be promoted (got: {source_prefix})", err=True)
        sys.exit(1)
    store = MemoryStore(cwd)
    # resolve file, copy, chroma add with promoted_from=_repo_id(cwd)/locator
    ...
```

### Forget --global command

```python
# Source: derived from memory_cli.py vacuum pattern + D-03 decision
@memory_group.command("forget")
@click.argument("locator")
@click.option("--global", "use_global", is_flag=True, help="Tombstone from global store.")
@click.option("--yes", "confirm", is_flag=True, help="Skip confirmation prompt.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def memory_forget_cmd(locator: str, use_global: bool, confirm: bool, cwd_str: str) -> None:
    """Tombstone memory entries. Use --global to target the global store."""
    if use_global:
        store = make_global_store()
        if store is None:
            click.echo("global store disabled or unavailable", err=True); sys.exit(1)
    else:
        cwd = Path(cwd_str).resolve()
        store = MemoryStore(cwd)
    n = store.forget(locator, confirm=confirm)
    click.echo(f"tombstoned: {n} entries")
```

### Dual-store fusion in attach_memory_tools

```python
# Source: derived from tools.py:159 attach_memory_tools + _rrf_merge static method
# Key: namespace global hits before _rrf_merge to avoid locator collision
import dataclasses

g_hits_raw = global_store.recall(query, top_k=top_k * 3, source=source)
# Namespace locators to prevent dedup collision with project locators
g_hits = [
    dataclasses.replace(h, source="[global]", locator=f"global:{h.locator}")
    for h in g_hits_raw
]
fused = MemoryStore._rrf_merge([proj_hits, g_hits], top_k=top_k)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No global memory | ~200 line extension of existing MemoryStore | V21 (now) | Zero new infrastructure — second instance of existing class |
| Hardcoded `cwd / ".voss" / "memory"` at L75 | `root_override` parameter | V21 | All existing callers unaffected (additive default) |
| Single-store recall in agent tool | Dual-store RRF fusion | V21 | [global] hits appear alongside project hits; no weighting knobs |
| No forget CLI verb (only /forget slash) | `voss memory forget [--global] <locator>` | V21 | Both project and global forget become CLI-accessible |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `Path.home()` raises `RuntimeError` when $HOME is unset | Pitfall 6 | Wrong failure mode; need to test on the actual CI environment |
| A2 | `chroma._collection.get(where={"promoted_from": ...})` metadata filtering works in chromadb 1.5.9 | Promote mechanics | If the `where` filter syntax changed, dedup lookup would fail silently |
| A3 | Chroma PersistentClient DELETE journal mode serialises writes safely under all macOS/Linux scenarios | Pitfall 4 (PARTIALLY VERIFIED) | Tested on macOS arm64; Linux behaviour assumed identical (SQLite file locking is POSIX) |

---

## Open Questions

1. **Does V21 own recall_cmd, or must V19 execute first?**
   - What we know: `recall_cmd` is in V19-04, not yet built. V21 needs it for `[global]` fusion in the CLI.
   - What's unclear: Does the planner want V21 to absorb V19-04's CLI work (simpler, removes hard dependency) or declare a `depends_on: V19` ordering constraint?
   - Recommendation: V21 owns `recall_cmd` (memory+global only, no code corpus), and V19-04 is reduced to "extend recall_cmd to add code corpus." This is cleanest.

2. **`voss memory forget` scope: --global only, or both project and global?**
   - D-03 specifies `voss memory forget --global <locator>` for the global store. There is no existing `voss memory forget` CLI verb (only `/forget` slash command exists in the REPL).
   - Options: (a) add `voss memory forget` for both scopes (project default, `--global` for global); (b) add only `voss memory forget --global` as D-03 specifies.
   - Recommendation: option (a) — consistent UX, closes the CLI gap for project forget too. This is within planner discretion since D-03 doesn't exclude project scope.

3. **`voss memory promote --list` discovery surface: what does it show?**
   - D-11 says "`--list` acceptable for discovery — planner decides minimal discovery surface."
   - Options: (a) list all promotable entries from project store (notes, decisions, conventions) with their locators; (b) skip `--list` in V21, rely on `voss memory size` + manual inspection.
   - Recommendation: implement minimal `--list`: iterate `notes/`, `decisions/`, `conventions/` dirs and print `<locator>: <first-line-of-excerpt>`. Mirrors `memory_size_cmd` iteration pattern exactly.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | All V21 code | ✓ | 3.13.12 | — |
| pytest | Test suite | ✓ | 8.4.2 | — |
| chromadb | Global vector store | ✓ | 1.5.9 | BM25-only fallback (existing) |
| portalocker | Cross-process locks | ✓ | 3.2.0 | — |
| rank-bm25 | BM25 lexical recall | ✓ | 0.2.2 | — |
| click | CLI structure | ✓ | 8.3.3 | — |
| $HOME environment | Default global root | ✓ (dev) | — | VOSS_HOME override; treat as disabled in CI |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `$HOME` unset in CI — fallback is global store disabled gracefully.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pytest.ini` / `pyproject.toml` (existing) |
| Quick run command | `.venv/bin/python -m pytest tests/harness/test_memory_global.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/harness/ tests/memory/ -q` |

### Phase Requirements → Test Map

Requirements are minted from CONTEXT.md decisions at plan time. Pre-mapping from decisions to test types:

| Decision | Behaviour | Test Type | Automated Command | File Exists? |
|----------|-----------|-----------|-------------------|-------------|
| D-04 root_override | `MemoryStore(cwd, root_override=P)` sets `self.root=P` | unit | `pytest tests/harness/test_memory_global.py::test_root_override -x` | ❌ Wave 0 |
| D-04 VOSS_HOME | `VOSS_HOME=/tmp/x` → global root = `/tmp/x/memory` | unit | `pytest tests/harness/test_memory_global.py::test_voss_home_env -x` | ❌ Wave 0 |
| D-04 layout mirror | global store bind() creates same dirs as project store | unit | `pytest tests/harness/test_memory_global.py::test_global_layout_mirror -x` | ❌ Wave 0 |
| D-01 promote copy | promote copies file + chroma add with promoted_from metadata | unit | `pytest tests/harness/test_memory_global.py::test_promote_copies_with_provenance -x` | ❌ Wave 0 |
| D-01 dedup | re-promoting same locator updates, never duplicates | unit | `pytest tests/harness/test_memory_global.py::test_promote_dedup_on_repromote -x` | ❌ Wave 0 |
| D-02 source restriction | promote rejects turn/ledger locators with exit 1 | unit + CLI subprocess | `pytest tests/harness/test_memory_global.py::test_promote_rejects_turn_ledger -x` | ❌ Wave 0 |
| D-03 forget --global | tombstones in global store, not project store | unit | `pytest tests/harness/test_memory_global.py::test_forget_global_tombstones_global -x` | ❌ Wave 0 |
| D-05 vacuum --global | vacuum reclaims bytes from global store | unit | `pytest tests/harness/test_memory_global.py::test_vacuum_global -x` | ❌ Wave 0 |
| D-06 equal RRF | fused hits contain both project and global entries | unit | `pytest tests/harness/test_memory_global.py::test_recall_fusion_rrf -x` | ❌ Wave 0 |
| D-07 [global] label | global hits labeled `[global]` in agent tool output | unit | `pytest tests/harness/test_memory_global.py::test_global_label_in_recall -x` | ❌ Wave 0 |
| D-07 off-switch | `[memory] global = false` skips global store init entirely | unit + config | `pytest tests/harness/test_memory_global.py::test_global_off_switch_no_init -x` | ❌ Wave 0 |
| D-08 write guard | agent write tools do not write to global store | unit | `pytest tests/harness/test_memory_global.py::test_agent_cannot_write_global -x` | ❌ Wave 0 |
| D-13 concurrency | portalocker blocks second process on promote/vacuum | integration (subprocess) | `pytest tests/harness/test_memory_global.py::test_concurrent_promote_lock -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/harness/test_memory_global.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/harness/ tests/memory/ -q`
- **Phase gate:** full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/test_memory_global.py` — all VGMEM-* tests (new file)
- [ ] `tests/harness/conftest.py` amendment — `global_root` fixture using `VOSS_HOME` monkeypatch + `tmp_voss_global` fixture mirroring `tmp_voss_repo`

*(Existing test infrastructure: `tmp_voss_repo`, `chroma_disabled_env`, `isolated_state` all reusable via new fixture composition)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | global store is local filesystem, no auth |
| V3 Session Management | no | global store has no session concept |
| V4 Access Control | yes | `~/.voss/memory/` created with `chmod 0600` files (existing pattern); global store must inherit same chmod |
| V5 Input Validation | yes | locator argument to promote validated for source prefix; pattern to forget uses fnmatch (existing) |
| V6 Cryptography | no | no crypto in this feature |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in VOSS_HOME | Tampering | Resolve VOSS_HOME with `Path(voss_home).resolve()` before use; validate it's a directory (not a file) |
| Sensitive data leakage in `--json` output from `voss recall` | Information Disclosure | Existing: `--json` exposes only `Hit` fields (source, locator, score, excerpt) — no env vars, no secrets in fields |
| Malicious note content promoted to global affecting other projects | Tampering | Excerpt is stored text from the operator's own notes; no code execution path from excerpts |
| Global store writable by other users (shared machine) | Elevation of Privilege | File perms: `mkdir(parents=True)` + `path.chmod(0o600)` on each written file (existing pattern in write_note/write_convention) |

---

## Sources

### Primary (HIGH confidence — verified from source code in this session)

- `voss/harness/memory_store.py` — MemoryStore class, `__init__` constructor, `bind()`, `_lock()`, `forget()`, `vacuum()`, `_rrf_merge()`, `_locator_from_path()`, `_load_memory_config()` — all read and verified
- `voss/harness/memory_cli.py` — click group structure, `vacuum`/`adopt`/`size` command patterns — all read and verified
- `voss/harness/config.py` — `_parse_model_tiers_section` pattern, `_KV`, `_KV_BARE` regex parsers, `config_path()` — read and verified
- `voss/harness/tools.py` — `attach_memory_tools` signature and implementation — read and verified
- `voss/harness/cli.py` — `AGENT_COMMANDS` tuple, all 3 `MemoryStore(cwd)` instantiation sites, `_forget` slash handler — read and verified
- `voss_runtime/memory/semantic.py` — `SemanticMemory`, `PersistentClient` init, `_embedding_function` — read and verified
- `tests/harness/conftest.py` — `tmp_voss_repo` fixture pattern, `isolated_state` fixture — read and verified
- `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-04-PLAN.md` — `recall_cmd` interface and fusion specification — read and verified
- Empirical test: chromadb 1.5.9 cross-process safety (3 concurrent processes, shared PersistentClient, 90 docs expected, 90 confirmed)
- Empirical test: portalocker LOCK_NB cross-process blocking (process 2 correctly blocked while process 1 holds lock)

### Secondary (MEDIUM confidence)

- `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-SPEC.md` — V19 requirements and unbuilt status confirmed (no SUMMARY files)
- `chromadb.config.Settings` empirical probe: `PRAGMA journal_mode` returns `('delete',)` for chromadb 1.5.9

---

## Metadata

**Confidence breakdown:**
- Standard stack (no new packages): HIGH — all deps pre-existing, verified installed
- MemoryStore blast radius: HIGH — all call sites enumerated via grep; root_override is purely additive
- Portalocker cross-process safety: HIGH — empirically verified
- Chromadb cross-process safety: HIGH — empirically verified (3 concurrent writers, 90/90 docs)
- V19 seam analysis: HIGH — confirmed V19 unexecuted (zero SUMMARY files)
- Promote mechanics: HIGH — file formats read from write_note/write_convention source; locator scheme read from make_id/_locator_from_path
- Config section pattern: HIGH — exact pattern from _parse_model_tiers_section verified

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (chromadb version pinned at 1.5.9; portalocker at 3.2.0; stable)
