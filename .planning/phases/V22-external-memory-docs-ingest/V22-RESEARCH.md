# Phase V22: External Memory & Docs Ingest — Research

**Researched:** 2026-06-13
**Domain:** Python / Chroma vector index / markdown chunking / TOML config / BM25 RRF
**Confidence:** HIGH (all key claims verified against live codebase; confirmed file:line citations throughout)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Source declaration:**
- **D-01 — Explicit-only:** every source declared in `[[recall.sources]]` (name/path/glob). No zero-config repo-docs default, no auto-discovery. Repo docs is an ordinary declared source.
- **D-02 — Array-of-tables config:** `[[recall.sources]]` TOML array-of-tables; V22 adds a stdlib `tomllib` parse path for this section (existing regex parser cannot read array-of-tables). Existing regex-parsed sections untouched.
- **D-03 — Reserved-name + duplicate rejection:** names `code`/`memory`/`global` rejected at config load with clear error; duplicate names across entries rejected.
- **D-04 — Markdown only:** ingest filters to `.md`/`.markdown`; non-md under the glob skipped.

**Index mechanics:**
- **D-05 — Per-source isolation:** each source = own Chroma collection + own `semantic-manifest.json` under `.voss-cache/recall/<name>/`; one source rebuilding never invalidates another. Derived cache, rm-safe, rebuildable.
- **D-06 — Section-boundary chunking:** chunk on markdown heading boundaries (section = heading → next same-or-higher heading); preamble = own chunk; heading-less file = one chunk; oversize regions sub-split via existing `_MAX_CHUNK_CHARS` guard.
- **D-07 — Incremental never-full:** hash-skip unchanged files (zero embeds); changed file re-embeds only its chunks (stale ids deleted); deleted source file purges its chunks.
- **D-08 — Background daemon, read-only:** CodeIndexService-pattern daemon build off session-start path; degrade-until-ready; zero writes/renames/deletes under any source path.

**Recall blending:**
- **D-09 — Both surfaces, RRF, `[<name>]` labels:** external hits fuse via `MemoryStore._rrf_merge` into BOTH the agent recall tool AND `voss recall` CLI; `[<name>]` in plain output, `source` field in `--json`; chromadb-absent degrades to BM25-only without error.

**Verification:**
- **D-10 — Golden-query gate:** committed fixture vault under `tests/` + ~8–12 golden queries; runs in CI without network/OpenAI key; passes with and without chromadb.

### Claude's Discretion

- **D-11 — Module placement:** new `voss/harness/recall/` package or `voss/harness/external_index.py`; `ExternalSource`/`ExternalSourceIndex` + `ExternalRecallService` daemon wrapper. Mirror CodeIndex/CodeIndexService shape.
- **D-12 — Collection naming:** `voss_recall_<name>` (sanitized), distinct from `voss_code`/`voss_semantic`.
- **D-13 — Chunk id convention:** `<name>:<rel_path>:<seq>` composite.
- **D-14 — Heading-boundary extraction:** ATX headings (#..######); setext optional; reuse `_split_oversize` verbatim.
- **D-15 — Manifest shape:** reuse CodeIndex manifest schema — `{embedding_model, files: {rel_path: {hash, chunk_ids}}}`.
- **D-16 — Recall fan-out:** extend `_rrf_merge([code_hits, mem_hits, *external_hits_per_source])`.
- **D-17 — Off-switch:** absent `[[recall.sources]]` = zero sources/zero I/O.
- **D-18 — Service lifecycle:** spawn from same session-start hook that starts `CodeIndexService`.
- **D-19 — Path resolution:** absolute or `~`-expanded; relative resolves against cwd; non-existent path → skip cleanly.

### Deferred Ideas (OUT OF SCOPE)

- Retrieval ranking / telemetry / quality-floor over fused results → V23
- Non-markdown formats (PDF/HTML/`.txt`/`.rst`)
- Write-back / sync to external sources
- Tiered-routing enrichment (VSEM-07/08) of markdown chunks
- voss-app/TUI panel over external-source hits
- `.planning/` GSD artifacts as a source (opt-in only as an ordinary declared source; never default)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VXMEM-01 | `[[recall.sources]]` array-of-tables parses to ordered `{name, path, glob}` records; absent section → zero sources, zero I/O | `tomllib` confirmed available (Python 3.13.12 on this machine, floor ≥3.11 in pyproject.toml). tomllib parse path cleanly isolated from regex parser. |
| VXMEM-02 | Reserved names `code`/`memory`/`global` and duplicate names rejected at config load | No existing name-namespace mechanism; added in `get_recall_sources()` accessor function. |
| VXMEM-03 | Per-source derived index under `.voss-cache/recall/<name>/`; rm-safe; content-hash manifest | Direct port of CodeIndex manifest schema (`semantic_index.py:L109-124`); `_load/_save_manifest` pattern reused verbatim. |
| VXMEM-04 | Section-boundary markdown chunking (`.md`/`.markdown` only); oversize subsplit | `_split_oversize` from `semantic_index.py:L36-50` reused verbatim; new `extract_md_chunks` function replaces M10-SQLite-dependent `extract_chunks`. |
| VXMEM-05 | Incremental never-full reindex: hash-skip unchanged, stale-chunk delete, deleted-file purge | CodeIndex `build()` pattern at `semantic_index.py:L186-283` ports directly; no M10 SQLite dependency in the incremental path. |
| VXMEM-06 | Background daemon, non-blocking, read-only ingest | `CodeIndexService` pattern at `semantic_index.py:L533-594`; spawn hook confirmed at `service.py:L123-132`. |
| VXMEM-07 | RRF fusion + `[<name>]` labels on both agent recall tool AND `voss recall` CLI | Two seams confirmed: `tools.py:L159` (`memory_recall` tool) and `cli.py:L4805` (`recall_cmd`). Both require extension. `_recall_hit_fields` at `cli.py:L4786` must be updated for external sources. |
| VXMEM-08 | Golden-query pytest gate over committed fixture vault; CI without network or OpenAI key | Fixture pattern established in `tests/code_recall/conftest.py`; `fake_embed_fn` + `DefaultEmbeddingFunction` already proven. Fixture vault under `tests/fixtures/recall_vault/`. |

</phase_requirements>

---

## Summary

V22 is a targeted port of the V19 `CodeIndex` pattern (`voss/harness/code/semantic_index.py`) to config-declared external markdown corpora. The reuse surface is large: `_split_oversize` (verbatim), the manifest schema and `_load/_save_manifest` helpers, `CodeIndexService`'s daemon-thread pattern, `SemanticMemory` as the Chroma wrapper, `MemoryStore._rrf_merge` for N-corpus fusion, and the `fake_embed_fn` test fixture. What changes is (a) the source-discovery mechanism (glob over arbitrary dirs instead of `_discover_files` git-walk), (b) the chunking algorithm (ATX heading boundaries instead of M10 SQLite symbol boundaries), (c) the config parse path (`tomllib` for `[[recall.sources]]` array-of-tables), and (d) the fusion fan-out sites (two: CLI `recall_cmd` and agent `memory_recall` tool).

There are two critical integration seams. The first is the agent-side `memory_recall` tool in `tools.py:L159-215` — it currently calls `store.recall(...)` against a single project-scoped `MemoryStore`. To wire external-source hits, V22 must either extend `attach_memory_tools` to accept an `ExternalRecallService` argument and fan out RRF there, or add a parallel `attach_external_recall_tool` call at the same `do_cmd`/`chat_cmd` sites where `attach_memory_tools` is called. The second seam is `recall_cmd` in `cli.py:L4805-4858` which currently does `_rrf_merge([code_hits, mem_hits])` — extend to `_rrf_merge([code_hits, mem_hits, *external_hits_per_source])`.

The V21 global memory is NOT currently fused into `recall_cmd` (the CLI). The `recall_cmd` only merges `code_hits` + `MemoryStore(cwd).recall(...)`. V21's `make_global_store()` is only surfaced in `memory_cli.py`. This is a gap to be aware of: V22 should not assume global hits are already in the CLI — but it also doesn't need to fix that (it's out of scope for V22). The agent's `memory_recall` tool also calls only a single bound `MemoryStore`. VXMEM-07 "both surfaces" means V22 adds external hits but does not need to also backfill global-memory hits.

**Primary recommendation:** Place `ExternalSourceIndex` + `ExternalRecallService` in `voss/harness/recall/external_index.py` (new file, mirroring `code/semantic_index.py` shape). Add `get_recall_sources()` to `config.py`. Extend `recall_cmd` and `attach_memory_tools` (or add `attach_external_recall_tool`). Reuse `_split_oversize` verbatim from `semantic_index.py` — import it, do not copy.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Config parse (`[[recall.sources]]`) | `voss/harness/config.py` | `~/.config/voss/config.toml` | Mirrors existing `get_code_recall_config()` accessor pattern |
| Reserved-name / duplicate validation | `config.py:get_recall_sources()` | — | Fail at load, not at ingest time |
| Per-source Chroma collection + manifest | `voss/harness/recall/external_index.py` | `.voss-cache/recall/<name>/` (disk) | Derived cache beside code index — same tier as `code/semantic_index.py` |
| Heading-boundary chunk extraction | `external_index.py:extract_md_chunks()` | `_split_oversize` (imported from `semantic_index.py`) | New chunking algorithm; oversize guard reused |
| Embedding function selection | `SemanticMemory._embedding_function()` (reused) | `voss_runtime/memory/semantic.py` | Do not duplicate; same model selection logic |
| Background daemon build | `ExternalRecallService` in `external_index.py` | `threading.Thread(daemon=True)` | Mirrors `CodeIndexService` exactly |
| Session-start daemon spawn | `voss/harness/code/service.py:_get_code_index_service()` pattern | Same hook site in `make_toolset()` | `tools.py:L902-916` is the existing hook; ExternalRecallService spawns from the same `make_toolset()` call |
| RRF fan-out (CLI surface) | `voss/harness/cli.py:recall_cmd` (L4841) | `MemoryStore._rrf_merge` | Extend list from 2 to N corpora |
| RRF fan-out (agent tool surface) | `voss/harness/tools.py:attach_memory_tools` or new `attach_external_recall_tool` | `MemoryStore._rrf_merge` | Must wire at same sites as `attach_memory_tools` calls |
| `[<name>]` label rendering | `cli.py:_recall_hit_fields()` + tool string formatter | `Hit.source` field | `_recall_hit_fields` at L4786 currently hardcodes `"code"` vs `"memory"` — must generalize |
| Golden gate fixture vault | `tests/fixtures/recall_vault/` (committed) | `tests/external_recall/` (test files) | Mirrors V19's `tests/code_recall/` structure |

---

## Standard Stack

### Core (all pre-installed — zero new dependencies)

| Library | Version (verified) | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| `chromadb` | 1.5.9 [VERIFIED: .venv] | Chroma vector collection per source + PersistentClient | Already the `voss[search]` backend; `SemanticMemory` wraps it |
| `sentence-transformers` | 5.5.0 [VERIFIED: .venv] | `all-MiniLM-L6-v2` embedding (384-dim, 256 token window) | Already the default in `semantic.py._embedding_function()` |
| `rank-bm25` | (installed in venv) [VERIFIED: `memory_store.py:L22`] | BM25 lexical side for degradation | Already used in `memory_store.py`; `BM25Okapi` |
| `tomllib` | stdlib (Python ≥3.11) [VERIFIED: Python 3.13.12 in .venv] | Parse `[[recall.sources]]` array-of-tables | stdlib; no install needed; floor confirmed `pyproject.toml:L9` |

### No New Dependencies Required

V22 adds zero new pip dependencies. All required libraries are already in `voss[search]` or the standard library. This mirrors V19's dependency profile exactly. [VERIFIED: .venv pip list]

---

## Package Legitimacy Audit

No new packages are installed by this phase. All dependencies (`chromadb`, `sentence-transformers`, `rank-bm25`, `tomllib`) are either existing `voss[search]` extra dependencies already present in the venv, or Python stdlib.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
**Slopcheck run:** SKIPPED — no new packages being added.

---

## Research Questions — Concrete Answers

### Q1: Agent-Side Recall Tool Registration (VXMEM-07 "both surfaces")

**This is the least-mapped seam.** The full chain is:

1. **Tool registration function:** `attach_memory_tools(tools, *, store, session_id)` at `voss/harness/tools.py:L159`
   - Registers `memory_recall` (L169-194) and `memory_remember` (L196-215) into `tools` dict.
   - `memory_recall` calls `store.recall(query, top_k=top_k, source=source)` at L183.
   - The `store` is a single project-scoped `MemoryStore` — it does NOT fan out to global memory or code index.

2. **Where `attach_memory_tools` is called (three sites in `cli.py`):**
   - `do_cmd`: `cli.py:L1939` — `attach_memory_tools(tools, store=do_memory_store, session_id=do_record.id)`
   - `chat_cmd` (via `_build_chat_ctx`): `cli.py:L2249` — `attach_memory_tools(tools, store=ctx.memory_store, session_id=record.id)`
   - `_extension_context` (serve/watch): `cli.py:L3466-3470` — `attach_memory_tools(tools, store=MemoryStore(cwd).bind(session_id=ctx.record.id), session_id=ctx.record.id)`

3. **Code recall tool registration (V19 parallel):** `attach_code_recall_tool(result, code_index_service=_code_index_service)` at `tools.py:L916`, called from `make_toolset()` at L902-916. This is called from `make_toolset()` which is invoked at `cli.py:L1908` (do_cmd) and `cli.py:L2181` (chat_cmd).

4. **The planner's wiring decision (D-16):** V22 should add an `attach_external_recall_tool` function analogous to `attach_code_recall_tool`. It is called at the same sites as `attach_code_recall_tool` — inside `make_toolset()` after the code recall tool block (`tools.py:L898-916`). The `ExternalRecallService` is passed as an argument.

   Alternatively: extend `memory_recall` inside `attach_memory_tools` to also fan out to external hits and fuse via `_rrf_merge`. This is more surgical but couples memory-tool and external-index concerns.

   **Recommendation:** New `attach_external_recall_tool` (parallel to `attach_code_recall_tool`) called from `make_toolset()` at `tools.py:L916`. This keeps the fan-out at the tool level and mirrors the proven V19 pattern exactly.

5. **`memory_recall` tool output format at L190:** `f"[{h.source}] {h.locator} (score {h.score:.2f})"` — the `[<name>]` label comes from `h.source`, so as long as external `Hit` objects carry `source=<name>`, the existing format works without change.

### Q2: Session-Start Daemon Spawn Site (VXMEM-06 / D-18)

The CodeIndexService is spawned at **two locations** — planner must wire ExternalRecallService at both:

1. **`code/service.py:L123-132` — `_get_code_index_service()` method on `CodeIntelService`:**
   ```python
   def _get_code_index_service(self):
       if not hasattr(self, "_code_index_service") or self._code_index_service is None:
           from .semantic_index import CodeIndexService
           self._code_index_service = CodeIndexService(self.cwd, session_id=self.session_id)
           self._code_index_service.ensure_background_build()
       return self._code_index_service
   ```
   This is the lazy construction site on `CodeIntelService`. Called from `make_toolset()` at `tools.py:L908-910`:
   ```python
   _code_index_service = _CodeIntelService(cwd, session_id=session_id)._get_code_index_service()
   ```

2. **`cli.py:L789-800` — `_get_code_recall_service()` function (injection path):**
   ```python
   def _get_code_recall_service(cwd: Path, session_id: str | None = None):
       svc = CodeIndexService(cwd, session_id=session_id)
       svc.ensure_background_build()
       return svc
   ```
   Called from `_render_code_recall_text()` at `cli.py:L816` for the context-injection path (V19-05/06).

   **V22 does NOT need a context-injection path** (tiered-routing enrichment is out of scope). So V22 only needs to spawn from location 1 (the `make_toolset()` path). The `cli.py:L789` path is injection-only and is not relevant.

**Conclusion for planner:** Spawn `ExternalRecallService.ensure_background_build()` from `make_toolset()` in `tools.py`, near the existing code at L898-916. The `ExternalRecallService` reads `get_recall_sources()` from config; if zero sources, it is a no-op.

### Q3: tomllib Parse Path (VXMEM-01 / D-02)

**Existing regex parser mechanics:**
- `config.py` has zero `import tomllib` anywhere [VERIFIED: full read].
- Each section is parsed with a compiled regex, e.g. `_HARNESS_BLOCK = re.compile(r"^\[harness\][^\[]*", re.MULTILINE)` at `config.py:L25`.
- `_KV = re.compile(r'^\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"`, re.MULTILINE)` extracts key-value pairs within the block.
- Array-of-tables (`[[recall.sources]]`) is syntactically impossible to parse with this regex approach — `[^\[]*` stops at the first `[`, so `[[recall.sources]]` entries would each be parsed as separate matches and the multi-entry structure would be lost.

**Clean tomllib integration:**
```python
# Add to config.py — isolated path, does not touch regex parser
import tomllib

_RESERVED_SOURCE_NAMES = frozenset({"code", "memory", "global"})

def get_recall_sources() -> list[dict]:
    """Return ordered list of {name, path, glob} from [[recall.sources]].

    Uses tomllib for correct array-of-tables parsing. Falls back to []
    on missing file / section / parse error. Validates reserved names
    and duplicate names at load time.
    """
    p = config_path()
    if not p.exists():
        return []
    try:
        with open(p, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return []
    sources_raw = data.get("recall", {}).get("sources", [])
    if not isinstance(sources_raw, list):
        return []
    seen_names: set[str] = set()
    sources: list[dict] = []
    for entry in sources_raw:
        name = entry.get("name", "")
        if name in _RESERVED_SOURCE_NAMES:
            raise ValueError(
                f"[recall.sources] name {name!r} is reserved "
                "(code/memory/global are built-in corpus labels)"
            )
        if name in seen_names:
            raise ValueError(f"[recall.sources] duplicate name {name!r}")
        seen_names.add(name)
        sources.append({
            "name": name,
            "path": entry.get("path", ""),
            "glob": entry.get("glob", "**/*.md"),
        })
    return sources
```

**Key safety property:** `tomllib.load()` reads the entire file with a proper TOML parser, so `[[recall.sources]]` is parsed correctly. The existing regex sections (`[harness]`, `[agent]`, etc.) continue to be parsed by the existing regex functions — there is NO conflict because `get_recall_sources()` is a completely separate function that reads the same file independently. The regex functions never see `[[recall.sources]]` entries as anything other than unmatched noise (the `[^\[]*` regex stops before `[[`), which is the correct behavior.

**Pitfall:** If the config file has a TOML syntax error (which the regex parser silently ignores by matching partial blocks), `tomllib.load()` will raise `TOMLDecodeError`. The function above catches and returns `[]`. The planner should add a warning log in this case so the operator knows why sources aren't loading.

### Q4: Heading-Boundary Chunking (VXMEM-04 / D-06, D-14)

**Precise algorithm for `extract_md_chunks(content: str) -> list[tuple[int, int, str]]`:**

```
lines = content.splitlines(keepends=True)
total_lines = len(lines)
if total_lines == 0:
    return []

# Find ATX heading lines: ^#{1,6}\s (NOT inside code fences)
# Track in-fence state to skip # inside ```...``` blocks
in_fence = False
heading_lines: list[tuple[int, int]] = []  # (line_number_1based, level)
for i, line in enumerate(lines, start=1):
    stripped = line.rstrip('\n').rstrip('\r')
    if stripped.startswith('```') or stripped.startswith('~~~'):
        in_fence = not in_fence
    if in_fence:
        continue
    m = re.match(r'^(#{1,6})\s', stripped)
    if m:
        heading_lines.append((i, len(m.group(1))))

# Build section boundaries
# Section = [heading_line, next heading of same-or-higher level (lower number) or EOF]
if not heading_lines:
    # Heading-less file: one whole-file chunk (with oversize subsplit)
    return _split_oversize(1, total_lines, lines)

# Preamble: lines before first heading
chunks = []
if heading_lines[0][0] > 1:
    chunks.extend(_split_oversize(1, heading_lines[0][0] - 1, lines))

# Section for each heading
for idx, (hline, hlevel) in enumerate(heading_lines):
    # Find end of section: next heading at same or higher level (<=hlevel)
    section_end = total_lines
    for (next_hline, next_hlevel) in heading_lines[idx + 1:]:
        if next_hlevel <= hlevel:
            section_end = next_hline - 1
            break
        # Next heading is deeper (higher level number) — still part of this section
    chunks.extend(_split_oversize(hline, section_end, lines))

return chunks
```

**Edge cases that must be handled:**

1. **Code fences containing `#` lines:** The fence-tracking state above handles ```` ``` ```` and `~~~` fences. A `#` inside a code fence must NOT produce a heading boundary. [ASSUMED — standard markdown behavior; verified against spec intent]

2. **Setext headings (`===`/`---` underlines):** D-14 says "setext headings optional — planner decides; ATX is the floor." Recommendation: skip setext headings in V22. Setext headings are uncommon in documentation vaults, and supporting them adds complexity (requires lookahead at the next line). Leave as a future enhancement.

3. **Front-matter (YAML/TOML `---` blocks):** A file starting with `---` before any content triggers the fence-tracking if we use `---` as a fence delimiter. However, front-matter is typically delimited by `---...---` and the content inside is not markdown. Recommendation: treat leading `---` as a fence (skip its contents for heading detection) — the preamble chunk includes the front-matter text verbatim, which is correct for embedding (it usually contains useful metadata).

4. **Nested same-level sections:** The algorithm above is a "same-or-higher level terminates" rule, which means `## A` followed by `## B` at the same level splits at `## B`. This is the standard interpretation. A section like `# Top\n## Sub1\n## Sub2` produces: `Top section = line 1 to end of Sub2`, and `Sub1 section = line 2 to line before Sub2`, and `Sub2 section = line to EOF`. Wait — this would cause Sub1 and Sub2 to be their own chunks (higher-level heading terminates at same-level), but the `# Top` section would be just its own heading line (since `## Sub1` terminates it at the next heading of lower level). The algorithm as written is correct: `# Top` terminates at `## Sub1` (since level 2 > level 1, it does NOT terminate at the same-or-higher rule... wait — `##` is level 2, `#` is level 1; `##` is LOWER level numerically in terms of hierarchy). **Clarification needed on the level comparison:**

   - "same-or-higher heading" in the spec means "a heading that closes the current section" = a heading whose level number is <= the current heading's level number (e.g., `##` section closes at the next `#` or `##`, but NOT at `###`).
   - So `# Top` (level 1) terminates at next `#` (level ≤ 1). It does NOT terminate at `## Sub1` (level 2 > 1).
   - `## Sub1` (level 2) terminates at next `##` or `#` (level ≤ 2). So `## Sub2` terminates `## Sub1`.
   - Result: `# Top` section = lines from `# Top` through EOF (includes Sub1 and Sub2 content). Sub1 and Sub2 are ALSO their own chunks (spanning their own content). This means content is double-indexed.

   **This is the correct behavior** — it matches how CodeIndex chunks overlap (symbol chunks can overlap with preamble). The double-indexing of sub-sections under their parent section is fine for recall (it increases retrieval surface).

   Actually, the simpler and more standard interpretation is: each heading starts a chunk that runs until the NEXT heading at ANY level. This is the "flat" approach. The spec says "same-or-higher level" which implies hierarchical. The planner should choose one and be consistent. **Recommendation: use the "next heading at same-or-higher level" approach** as specified in D-06. It creates larger parent-section chunks that include sub-section content, plus smaller sub-section chunks. This is good for recall — a query about a topic will match both the subsection and the broader section.

5. **Single-line heading with no body:** A heading immediately followed by another heading of any level produces an empty section body. `_split_oversize` returns `[(hline, hline, text_of_heading_line)]` — a chunk containing just the heading text. This is acceptable for embedding (heading alone is still informative).

6. **Empty file:** `total_lines == 0` → `return []`. [VERIFIED: `_split_oversize` base case handles `end <= start`]

**`_split_oversize` reuse:** Import verbatim from `semantic_index.py`:
```python
from voss.harness.code.semantic_index import _split_oversize
```
The function is content-agnostic — it takes `(start, end, lines, max_chars)` and splits by line count. It handles the single-line oversize base case (`end <= start` → return whole even if oversize). [VERIFIED: `semantic_index.py:L36-50`]

### Q5: Per-Source Collection + Manifest Isolation (VXMEM-03 / D-05, D-12, D-15)

**Collection layout (per source):**
```
.voss-cache/recall/<name>/
├── chroma/          # PersistentClient persist_dir
└── semantic-manifest.json  # {embedding_model, files: {rel_path: {hash, chunk_ids}}}
```

**Manifest schema (direct port of CodeIndex):**
```json
{
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "files": {
    "docs/api.md": {
      "hash": "sha256hex",
      "chunk_ids": ["docs:docs/api.md:000", "docs:docs/api.md:001"]
    }
  }
}
```

**Key differences from CodeIndex manifest:**
- `rel_path` is relative to the declared `path` in `[[recall.sources]]` (not relative to cwd). This matters for absolute external paths — the rel_path in the manifest should be the glob-match path relative to the source root, not the full absolute path.
- Chunk ids use `<name>:<rel_path>:<seq>` (D-13), not `code:<rel_path>:<seq>`.

**Embedding-model-swap drop (Pitfall 1 parity):**
```python
manifest = self._load_manifest()
current_model = _effective_embedding_model()
if manifest.get("embedding_model") and manifest["embedding_model"] != current_model:
    if sem is not None:
        sem._client.delete_collection(self._collection_name)
    manifest = {}  # every hash invalid → full re-embed
```
Port verbatim from `semantic_index.py:L200-209`. [VERIFIED: `semantic_index.py:L200-209`]

**Collection name sanitization (D-12):** `voss_recall_<name>` where `<name>` is already validated (no reserved names, no duplicates). Additional sanitization for Chroma collection name rules: lowercase, alphanumeric + underscores only, 3-63 chars. Apply `re.sub(r'[^a-z0-9_]', '_', name.lower())` before prefixing.

**Per-source isolation guarantee:** Each source gets its own `PersistentClient` pointing to `.voss-cache/recall/<name>/chroma/`. This avoids Pitfall 3 (single-client-per-path rule) because each source has its own path. Multiple source collections can coexist in different directories without SQLite lock contention. [VERIFIED: Chroma 1.5.9 SQLite DELETE journal mode — `V19-RESEARCH.md:Pitfall 3`]

**rm-safe property:** Deleting `.voss-cache/recall/` (or `.voss-cache/recall/<name>/`) and re-running `ExternalRecallService.ensure_background_build()` reproduces a working index from the source files alone. The source files are never touched (read-only ingest).

### Q6: Cross-Corpus RRF Fan-Out (VXMEM-07 / D-16)

**`_rrf_merge` accepts N rankings:** `MemoryStore._rrf_merge(rankings: list[list[Hit]], *, top_k: int, k: int = 60)` at `memory_store.py:L472`. It takes a `list[list[Hit]]` of arbitrary length. [VERIFIED: `memory_store.py:L472-486`]

**Current `recall_cmd` fan-out** (needs extension):
```python
# cli.py:L4841 — current:
fused = MemoryStore._rrf_merge([code_hits, mem_hits], top_k=top_k)

# V22 extension:
external_hits_per_source = []
ext_svc = _get_external_recall_service(cwd)  # new accessor
if ext_svc is not None:
    for hits in ext_svc.query_all(query_str, top_k=recall_k):
        external_hits_per_source.append(hits)
fused = MemoryStore._rrf_merge([code_hits, mem_hits, *external_hits_per_source], top_k=top_k)
```

**Chunk-id prefix collision safety:** External sources use `<name>:<rel_path>:<seq>` prefix. The reserved-name check at config load (VXMEM-02) ensures `name` is never `"code"`, `"memory"`, or `"global"`. Memory store IDs use prefixes `turn:`, `note:`, `ledger:`, `decision:`, `convention:`. Code chunks use `code:`. Global memory chunks use the same `turn:`, `note:` prefixes but from a different path. Therefore external chunk IDs with user-defined names (e.g. `docs:api.md:000`) cannot collide with any existing ID namespace. [VERIFIED: `memory_store.py:L62-66`, `semantic_index.py:L31-33`]

**`_recall_hit_fields` in `cli.py:L4786-4802` must be updated:**
```python
def _recall_hit_fields(hit) -> dict:
    is_code = (hit.source or "").startswith("code")
    # Current: hardcodes "code" vs "memory" in output "source" field
    # V22 must: pass hit.source directly (not normalize to "memory")
```
The current function forces `"source": "code" if is_code else "memory"` — this means external hits would be labeled `"memory"` in `--json` output. Must be changed to `"source": hit.source` for V22 compliance. Similarly, the plain-text display at `cli.py:L4852-4856` checks `fields["source"] == "code"` for path display — external sources should display their `locator` (not a path:line format), like memory hits do. [VERIFIED: `cli.py:L4786-4858`]

**Degradation contract when chromadb absent:** Each `ExternalSourceIndex._maybe_semantic()` follows the same lazy probe as CodeIndex (try to construct `SemanticMemory`, catch `ModuleNotFoundError`/`ImportError`, set `_unavailable = True`). When unavailable, `query()` returns BM25-only hits labeled `<name>[degraded]` (or just `<name>` without the degraded suffix for cleaner output — planner decides). The RRF fan-out still works because BM25 hits are valid `Hit` objects. [VERIFIED: `semantic_index.py:L145-163`, `L492-507`]

---

## Architecture Patterns

### System Architecture Diagram

```
[session start → make_toolset()]
      │
      ├── CodeIndexService.ensure_background_build()   [V19, unchanged]
      │
      └── ExternalRecallService.ensure_background_build()   [V22 NEW]
                │
                ├── sources = get_recall_sources()  ← config.py tomllib parse
                │   [absent [[recall.sources]] → zero sources → no-op]
                │
                └── for each source:
                       Thread(daemon=True)
                         │
                         ▼
                    ExternalSourceIndex.build(source)
                         │
                         ├── glob(source.path, source.glob) → .md/.markdown files only
                         ├── diff vs .voss-cache/recall/<name>/semantic-manifest.json
                         ├── skip unchanged (hash match → zero embeds)
                         ├── extract_md_chunks(content)  [heading-boundary + _split_oversize]
                         ├── sem._collection.upsert(chunks)    [or delete stale + upsert changed]
                         ├── purge chunks of deleted source files
                         └── save manifest
                                │
                                ▼
                          ready_event.set()

[voss recall <query>]
      │
      ├── code_hits    ← CodeIndex.query()
      ├── mem_hits     ← MemoryStore(cwd).recall()
      └── ext_hits[]   ← ExternalRecallService.query_all()  [one list per source]
               │
               ▼
          _rrf_merge([code_hits, mem_hits, *ext_hits], top_k=top_k)
               │
               ├── plain: "[docs] docs/api.md:5 (score 0.42)"
               └── --json: {"source": "docs", "locator": "docs:docs/api.md:000", ...}

[agent memory_recall tool / attach_external_recall_tool]
      │
      ├── store.recall()      [project memory]
      └── ext_svc.query_all() [external sources, same fan-out]
               │
               ▼
          _rrf_merge([mem_hits, *ext_hits], top_k=top_k)
               │
               └── "[docs] docs/api.md (score 0.42)\n  excerpt..."
```

### Recommended Project Structure

```
voss/harness/recall/
├── __init__.py          # exports ExternalSourceIndex, ExternalRecallService
└── external_index.py    # new — mirror of code/semantic_index.py

voss/harness/config.py   # add get_recall_sources(), import tomllib at top

voss/harness/tools.py    # add attach_external_recall_tool(); call from make_toolset()

voss/harness/cli.py      # extend recall_cmd fan-out; fix _recall_hit_fields()

tests/external_recall/
├── __init__.py
├── conftest.py              # fixture vault + fake_embed_fn (reuse pattern from code_recall/conftest.py)
├── test_config.py           # VXMEM-01, VXMEM-02
├── test_chunker.py          # VXMEM-04 heading-boundary + oversize
├── test_incremental.py      # VXMEM-05 hash-skip, stale-purge, deleted-file
├── test_background.py       # VXMEM-06 daemon + non-blocking + read-only
├── test_recall_cli.py       # VXMEM-07 CLI [<name>] labels + --json
├── test_agent_tool.py       # VXMEM-07 agent recall tool external hits
└── test_golden_queries.py   # VXMEM-08 golden gate

tests/fixtures/recall_vault/
├── getting-started.md       # Has preamble + multiple headings
├── api-reference.md         # Has nested headings
├── concepts/
│   └── chunking.md          # Distinct vocabulary for golden queries
└── changelog.md             # Heading-heavy; tests oversize subsplit
```

### Pattern 1: ExternalSourceIndex — per-source class

**What:** One `ExternalSourceIndex` instance per declared source. Has `_maybe_semantic()` (lazy Chroma init), `build()` (incremental with manifest), `query()` (RRF or BM25-only), BM25 corpus.
**Reuse:** Import `_split_oversize` from `semantic_index.py`. Import `_effective_embedding_model`, `_file_hash` from `semantic_index.py` (they are module-level functions, not class methods).
**Example:**
```python
# Source: voss/harness/code/semantic_index.py (port pattern)
from voss.harness.code.semantic_index import _split_oversize, _effective_embedding_model, _file_hash

class ExternalSourceIndex:
    def __init__(self, cwd: Path, source: dict) -> None:
        self.cwd = cwd
        self.source = source  # {name, path, glob}
        self._name = source["name"]
        self._cache_dir = cwd / ".voss-cache" / "recall" / self._name
        self._collection_name = f"voss_recall_{re.sub(r'[^a-z0-9_]', '_', self._name.lower())}"
        self._sem: SemanticMemory | None = None
        self._unavailable = False
        self._bm25 = None
        self._bm25_chunks: list[tuple[str, str, str, int, int]] = []
```
[VERIFIED: mirrors `semantic_index.py:L127-141`]

### Pattern 2: Heading-Boundary Chunker

**What:** `extract_md_chunks(content: str) -> list[tuple[int, int, str]]` — heading-boundary version of `extract_chunks`. No SQLite dependency.
**Example:**
```python
import re

_ATX_HEADING = re.compile(r'^(#{1,6})\s')
_FENCE_START = re.compile(r'^(?:```|~~~)')

def extract_md_chunks(content: str) -> list[tuple[int, int, str]]:
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)
    if total_lines == 0:
        return []

    in_fence = False
    heading_positions: list[tuple[int, int]] = []  # (1-based line, level)
    for i, line in enumerate(lines, start=1):
        stripped = line.rstrip()
        if _FENCE_START.match(stripped):
            in_fence = not in_fence
        if in_fence:
            continue
        m = _ATX_HEADING.match(stripped)
        if m:
            heading_positions.append((i, len(m.group(1))))

    if not heading_positions:
        return _split_oversize(1, total_lines, lines)

    chunks: list[tuple[int, int, str]] = []
    # Preamble before first heading
    if heading_positions[0][0] > 1:
        chunks.extend(_split_oversize(1, heading_positions[0][0] - 1, lines))
    # Each heading's section runs to the next heading of same-or-higher level
    for idx, (hline, hlevel) in enumerate(heading_positions):
        section_end = total_lines
        for next_hline, next_hlevel in heading_positions[idx + 1:]:
            if next_hlevel <= hlevel:
                section_end = next_hline - 1
                break
        chunks.extend(_split_oversize(hline, section_end, lines))
    return chunks
```
[ASSUMED — algorithm derived from spec D-06/D-14; needs test coverage to confirm edge cases]

### Pattern 3: tomllib Config Parse (safe isolation)

**What:** `get_recall_sources()` in `config.py` — reads `[[recall.sources]]` with `tomllib`, validates names, returns list. Does NOT touch existing regex-parsed sections.
**Safety:** Completely isolated function; existing `_parse_harness_section()` etc. are unchanged.
**Example:** See Q3 above for full implementation.
[VERIFIED: `tomllib` stdlib confirmed; `config_path()` reused at `config.py:L20-23`]

### Pattern 4: ExternalRecallService — multi-source daemon wrapper

**What:** Wraps N `ExternalSourceIndex` instances, one per declared source. Spawns one daemon thread per source (or one thread for all — planner decides; one-per-source is simpler and avoids cross-source blocking).
**Recommendation:** One daemon thread total that iterates all sources sequentially. Simpler; avoids N concurrent Chroma clients at startup.
```python
class ExternalRecallService:
    def __init__(self, cwd: Path, session_id: str | None = None) -> None:
        from voss.harness.config import get_recall_sources
        sources = get_recall_sources()
        self._indices = [ExternalSourceIndex(cwd, s) for s in sources]
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    def ensure_background_build(self) -> None:
        if not self._indices or self._thread is not None:
            return
        t = threading.Thread(target=self._build_loop, daemon=True)
        self._thread = t
        t.start()

    def _build_loop(self) -> None:
        try:
            for idx in self._indices:
                idx.build()
        except Exception as exc:
            print(f"external recall: background build failed ({exc})", file=sys.stderr)
        finally:
            self._ready.set()

    def query_all(self, query: str, top_k: int = 5) -> list[list[Hit]]:
        """Return one Hit list per source (empty list if not ready/no results)."""
        if not self._ready.is_set():
            return [idx._bm25_query(query, top_k) for idx in self._indices]
        return [idx.query(query, top_k=top_k) for idx in self._indices]
```
[VERIFIED: mirrors `CodeIndexService` at `semantic_index.py:L533-594`]

### Anti-Patterns to Avoid

- **Using `_discover_files` from `code/index.py` for external sources:** `_discover_files` is git-aware and repo-scoped. External paths may be outside the git repo entirely. Use `pathlib.Path.rglob(glob_pattern)` filtered to `.md`/`.markdown` suffixes.
- **Relative chunk `rel_path` in manifest using cwd:** For external sources with absolute paths, `rel_path` must be relative to the declared source `path`, not to `cwd`. Otherwise manifests break when the user moves their repo.
- **Importing `sentence-transformers` on the session thread:** Same as Pitfall 2 in V19. ExternalRecallService construction must be lazy — `_maybe_semantic()` is only called inside the daemon thread.
- **Two PersistentClient instances to the same `.voss-cache/recall/<name>/chroma/` path:** One client per source index. Since each source has its own directory, there is no cross-source lock contention. But ensure the `ExternalSourceIndex` instance holding the client is the same instance used for both build and query.
- **Calling `query_all()` before sources are declared:** `get_recall_sources()` may raise `ValueError` on invalid config. Catch at service construction time and log; return zero indices (no-op service). This prevents a bad config from crashing session start.
- **Passing absolute source `path` directly as `rel_path` in chunk ids:** Chunk ids must use relative paths (for human readability in `--json` output and for manifest portability). Apply `Path(abs_file).relative_to(source_root)` to get the relative path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RRF fusion across N ranked lists | Custom score normalization | `MemoryStore._rrf_merge` (static, corpus-agnostic) | Already handles dedup, top-k, N inputs; `list[list[Hit]]` is the API |
| Embedding function selection | New embedding dispatch | `SemanticMemory._embedding_function()` (reused) | Handles MiniLM / OpenAI key detection / config model; do not duplicate |
| Chroma client init | Direct `chromadb.PersistentClient` | `SemanticMemory(persist_dir=..., collection_name=...)` | Wraps `Settings(anonymized_telemetry=False)`; handles import errors |
| BM25 tokenizer | Custom tokenizer | `_bm25_tokenize` from `memory_store.py:L103` | Handles camelCase, snake_case, dots, slashes; code-aware |
| Oversize chunk subsplit | Custom recursive splitter | `_split_oversize` from `semantic_index.py:L36-50` (import verbatim) | Handles single-line base case; avoids infinite recursion |
| Content hash | Custom hash scheme | `_file_hash` from `semantic_index.py:L92-94` (sha256 utf-8) | Identical to M10 `build_index()` — consistent across codebase |
| Embedding model name tracking | Custom versioning | `_effective_embedding_model()` from `semantic_index.py:L97-107` (import verbatim) | Handles OpenAI key detection; model-swap drop already coded there |

**Key insight:** The target module `semantic_index.py` already contains the exact helper functions V22 needs as module-level callables. Import them directly rather than copying.

---

## Common Pitfalls

### Pitfall 1: `_discover_files` is git-scoped — cannot be reused for external paths

**What goes wrong:** Planner uses `_discover_files(cwd)` from `code/index.py` for external source file discovery. This function uses `git ls-files` and falls back to `os.walk`, but it is scoped to the git repo cwd and respects `.gitignore`. An external vault at `~/SecondBrain` is not inside the repo and may not be a git repo at all.
**Why it happens:** `extract_chunks` in V19 depends on `_discover_files`; a planner reading the V19 code might assume the same function is reused.
**How to avoid:** For external sources, use `Path(resolved_source_path).rglob(glob_pattern)` directly, filtered to `.md`/`.markdown`. No git dependency.
**Warning signs:** `_discover_files` returns zero files for an absolute path outside the git repo.

### Pitfall 2: `rel_path` in manifest and chunk ids must be source-relative, not cwd-relative

**What goes wrong:** A source declares `path = "/Users/ben/SecondBrain"`. The ingested file is `/Users/ben/SecondBrain/wiki/projects/Voss/log.md`. If `rel_path` is computed as `Path(file).relative_to(cwd)`, it raises `ValueError` (not a subpath). If stored as an absolute path, the manifest is non-portable.
**How to avoid:** `rel_path = str(Path(abs_file).relative_to(Path(source["path"]).expanduser().resolve()))`. This produces `wiki/projects/Voss/log.md` — readable and portable within the source's directory tree.
**Warning signs:** `ValueError: '/Users/ben/SecondBrain/...' is not relative to '...'` during build; chunk ids containing absolute paths.

### Pitfall 3: Code-fence `#` lines treated as headings

**What goes wrong:** A markdown file contains:
```
## Usage

```python
# This is a comment
import foo
```
```
If the code fence tracking is wrong, `# This is a comment` produces a spurious heading boundary, splitting the code block across chunks.
**Why it happens:** Simple `re.match(r'^#+\s', line)` without fence awareness.
**How to avoid:** Track `in_fence` state with a toggle on ` ``` ` or `~~~` prefix lines. Reset on the matching closing fence. The algorithm in Q4 above handles this.
**Warning signs:** Golden query tests fail because expected file content is split at code comment lines; fixture files with code blocks in test chunker produce unexpected chunk counts.

### Pitfall 4: `_recall_hit_fields` hardcodes source as "code" or "memory"

**What goes wrong:** External hits have `source="docs"`, but `_recall_hit_fields()` at `cli.py:L4795` returns `"source": "code" if is_code else "memory"`, so external hits become `"memory"` in `--json` output.
**Why it happens:** The current function was written when only two sources existed. The V21 `[global]` source was never wired into `recall_cmd`, so this gap was never surfaced.
**How to avoid:** Change `_recall_hit_fields` to pass `hit.source` directly in the returned dict. Also update the plain-text display loop at `L4851-4858` to handle non-code, non-memory sources gracefully (show `hit.locator` as display, not a path:line format).
**Warning signs:** Golden CLI test asserts `"source": "docs"` in JSON output but gets `"source": "memory"`.

### Pitfall 5: Large external vault blocks the daemon thread for minutes

**What goes wrong:** A user declares `path = "~/SecondBrain"` with 50,000 markdown files. The first build embeds all files sequentially, taking 20-60 minutes. The daemon thread holds a Chroma write lock for that entire duration. Subsequent queries may return stale/empty results until the thread finishes.
**Why it happens:** No size guard; first build is always a full scan on cold start.
**How to avoid:** The manifest hash-skip means only NEW files get embedded on subsequent runs — the problem is only the first build. For V22, document the expectation (first build may be slow for large vaults) and ensure `is_ready()` returns `False` (BM25-only degradation) until the full build completes. Consider logging progress to stderr. Do NOT add a size limit in V22 (out of scope for now).
**Warning signs:** `voss recall` on a fresh session with a large vault returns `[docs[degraded]]` hits for an extended period.

### Pitfall 6: Glob pattern resolves to zero files on non-existent source path

**What goes wrong:** User declares `path = "docs"` (relative), repo has no `docs/` directory. `Path(source_path).rglob("**/*.md")` raises `OSError` or returns no files. Build proceeds with zero chunks, manifest is written as empty. The user gets no hint that the source is misconfigured.
**Why it happens:** No existence check before globbing.
**How to avoid:** At build time, check `Path(resolved_source_path).exists()`. If not: log a warning to stderr, skip this source entirely (no manifest written), set the source's `is_ready` to True (nothing to do). D-19 says "skip cleanly, log degraded."
**Warning signs:** Empty recall results with no error message; manifest exists but is empty.

### Pitfall 7: symlinks under source path that escape to write-capable directories

**What goes wrong:** A vault has symlinks to directories outside the declared path. Following them during `rglob` could land on write-capable directories (e.g., `~/SecondBrain/raw-sources -> /Volumes/nas/raw/`). The ingest opens files read-only, but the glob could enumerate unexpectedly large trees.
**Why it happens:** `Path.rglob()` follows symlinks by default in Python 3.
**How to avoid:** Use `follow_symlinks=False` in `rglob` (Python 3.13+ supports this), or after resolving each discovered file, check that `resolved_file.is_relative_to(resolved_source_root)` before processing. Log and skip files outside the declared root.
**Warning signs:** Ingest walks unexpected directories; extraordinarily large file counts; SecondBrain raw-sources being enumerated.

### Pitfall 8: Duplicate locator collision between sources with same file structure

**What goes wrong:** Two sources both have a file `README.md`. Their chunk IDs are `docs:README.md:000` and `notes:README.md:000`. Since the chunk id prefix is the source name (D-13), these are distinct — no collision. BUT if two sources declare the same `name` (which D-03 forbids at config load), they would collide.
**How to avoid:** D-03 reserved-name + duplicate validation at config load. The `get_recall_sources()` function raises `ValueError` on duplicates before any index I/O occurs.
**Warning signs:** RRF fusion drops hits because `_rrf_merge` deduplicates by `hit.locator`.

---

## Code Examples

### `get_recall_sources()` in config.py

```python
# Source: config.py — new function, tomllib isolated parse path
import tomllib  # stdlib, Python >=3.11 [VERIFIED: Python 3.13.12]

_RESERVED_SOURCE_NAMES = frozenset({"code", "memory", "global"})

def get_recall_sources() -> list[dict]:
    """Read [[recall.sources]] array-of-tables via tomllib.

    Returns ordered list of {name, path, glob} dicts.
    Raises ValueError on reserved names or duplicates.
    Returns [] on missing file / missing section / parse error.
    """
    p = config_path()
    if not p.exists():
        return []
    try:
        with open(p, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        import warnings
        warnings.warn(f"config.toml parse error (tomllib): {exc}", RuntimeWarning, stacklevel=2)
        return []
    sources_raw = data.get("recall", {}).get("sources", [])
    if not isinstance(sources_raw, list):
        return []
    seen_names: set[str] = set()
    out: list[dict] = []
    for entry in sources_raw:
        name = entry.get("name", "")
        if name in _RESERVED_SOURCE_NAMES:
            raise ValueError(
                f"[recall.sources] name {name!r} is reserved "
                f"({', '.join(sorted(_RESERVED_SOURCE_NAMES))} are built-in corpus labels)"
            )
        if name in seen_names:
            raise ValueError(f"[recall.sources] duplicate name {name!r}")
        seen_names.add(name)
        out.append({
            "name": name,
            "path": entry.get("path", ""),
            "glob": entry.get("glob", "**/*.md"),
        })
    return out
```
[VERIFIED: `config_path()` at `config.py:L20-23`; `tomllib` stdlib confirmed available]

### Manifest path helper (per-source)

```python
# Source: mirrors semantic_index.py:L109-124
def _manifest_path(cwd: Path, name: str) -> Path:
    return cwd / ".voss-cache" / "recall" / name / "semantic-manifest.json"

def _load_manifest(cwd: Path, name: str) -> dict:
    path = _manifest_path(cwd, name)
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}

def _save_manifest(cwd: Path, name: str, data: dict) -> None:
    path = _manifest_path(cwd, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=0, sort_keys=True))
```
[VERIFIED: mirrors `semantic_index.py:L109-124` exactly]

### Fake embedding fixture for tests (reuse V19 pattern)

```python
# Source: tests/code_recall/conftest.py:L73-88 (existing pattern)
@pytest.fixture
def fake_embed_fn(monkeypatch):
    try:
        from chromadb.utils import embedding_functions
    except Exception:
        pytest.skip("chromadb unavailable")
    fn = embedding_functions.DefaultEmbeddingFunction()
    from voss_runtime.memory.semantic import SemanticMemory
    monkeypatch.setattr(SemanticMemory, "_embedding_function", lambda self: fn)
    return fn
```
[VERIFIED: `tests/code_recall/conftest.py:L73-88`]

---

## Landmine Inventory: What in CodeIndex Does NOT Port Cleanly

| CodeIndex Feature | V22 Status | Notes |
|------------------|------------|-------|
| `_discover_files(cwd)` (git-aware) | **REPLACE** with `Path.rglob(glob)` | git-scope is repo-only; external vaults may be outside git |
| `extract_chunks(db_path, file_path, content)` (M10 SQLite) | **REPLACE** with `extract_md_chunks(content)` | No M10 symbol DB for external markdown |
| `_chunk_id(rel_path, seq)` → `code:<rel_path>:<seq>` | **ADAPT** → `<name>:<rel_path>:<seq>` | Prefix = source name, not `"code"` |
| Manifest at `.voss-cache/code/` | **ADAPT** → `.voss-cache/recall/<name>/` | Per-source isolation; distinct directory per source |
| `_run_enrichment()` (VSEM-07/08 enrichment) | **OMIT** | V22 explicitly defers tiered-routing enrichment |
| `queue_rehash(path)` (targeted re-hash on file mutation) | **OMIT** for V22 | External source files are read-only; no write-hook needed |
| `_manifest_path(cwd)` using fixed `code/` path | **ADAPT** → parameterized by source name | See manifest helper above |
| `CodeIndex._maybe_semantic()` collection name `voss_code` | **ADAPT** → `voss_recall_<name>` | Per-source collection name |
| `_drop_collection("voss_code")` on model swap | **ADAPT** → `_drop_collection(self._collection_name)` | Collection name is source-specific |
| `_ensure_bm25()` lazily re-scans files for BM25-before-build | **PORT** but with glob scan, not `_discover_files` | Same concept; different discovery mechanism |
| `_file_hash`, `_effective_embedding_model` | **IMPORT verbatim** from `semantic_index.py` | Module-level functions, not class methods; safe to import |
| `_split_oversize` | **IMPORT verbatim** from `semantic_index.py` | Completely content-agnostic; reuse directly |

### Path-Outside-Repo Permission Issues

- `pathlib.Path.rglob()` on an absolute path outside the repo requires read permission on the declared directory. If the directory is not readable (e.g., `/root/docs`), `rglob` raises `PermissionError`. Wrap in `try/except OSError` and skip + log.
- `symlinks` under an external vault can escape to arbitrary filesystem locations. Use symlink-aware path validation (see Pitfall 7 above).
- External paths may be on network mounts or slow filesystems. The daemon thread naturally handles this (session start does not block), but a slow network mount can make the first build take arbitrarily long.

### Large-Vault Performance

- A SecondBrain with 10,000+ markdown files will take significant time on first build (embedding 10K files × ~1s each = hours without GPU). The incremental manifest hash-skip means subsequent builds are fast (only changed files). Document the first-run expectation.
- BM25 corpus rebuild: `BM25Okapi([_bm25_tokenize(text) for ...])` on 10K chunks may use significant memory (V19 measured ~419MB for MiniLM; BM25 in-memory corpus for 10K docs is additional). For very large vaults, consider streaming or chunked BM25 construction in a future phase.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, `pyproject.toml:L112`) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/external_recall/ -q -x` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q --ignore=tests/eval/golden --ignore=tests/eval/matrix` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VXMEM-01 | Two `[[recall.sources]]` entries parse to exactly two records with correct name/path/glob | unit | `.venv/bin/python -m pytest tests/external_recall/test_config.py::test_parse_two_sources -x -q` | ❌ Wave 0 |
| VXMEM-01 | Config with no `[[recall.sources]]` section yields zero sources and zero index I/O | unit | `.venv/bin/python -m pytest tests/external_recall/test_config.py::test_no_section_zero_sources -x` | ❌ Wave 0 |
| VXMEM-02 | Config with `name="code"` raises ValueError with "code" in message | unit | `.venv/bin/python -m pytest tests/external_recall/test_config.py::test_reserved_name_rejected -x` | ❌ Wave 0 |
| VXMEM-02 | Config with two entries both `name="docs"` raises ValueError on duplicate | unit | `.venv/bin/python -m pytest tests/external_recall/test_config.py::test_duplicate_name_rejected -x` | ❌ Wave 0 |
| VXMEM-03 | Ingest fixture vault, `rm -rf .voss-cache/recall/`, re-ingest, assert working index | integration (fake embed) | `.venv/bin/python -m pytest tests/external_recall/test_incremental.py::test_derived_cache_rm_safe -x` | ❌ Wave 0 |
| VXMEM-03 | Manifest contains one entry per ingested file with content hash | unit (fake embed) | `.venv/bin/python -m pytest tests/external_recall/test_incremental.py::test_manifest_has_hash_per_file -x` | ❌ Wave 0 |
| VXMEM-04 | Multi-heading fixture file splits on heading boundaries (known chunk count) | unit | `.venv/bin/python -m pytest tests/external_recall/test_chunker.py::test_heading_boundary_split -x` | ❌ Wave 0 |
| VXMEM-04 | Heading-less fixture file yields exactly one chunk | unit | `.venv/bin/python -m pytest tests/external_recall/test_chunker.py::test_headingless_one_chunk -x` | ❌ Wave 0 |
| VXMEM-04 | Oversize section sub-splits (section > 800 chars produces >1 chunk) | unit | `.venv/bin/python -m pytest tests/external_recall/test_chunker.py::test_oversize_subsplit -x` | ❌ Wave 0 |
| VXMEM-04 | `.txt` file under the glob is NOT ingested | unit | `.venv/bin/python -m pytest tests/external_recall/test_chunker.py::test_non_md_skipped -x` | ❌ Wave 0 |
| VXMEM-04 | `#` inside code fence does NOT produce heading boundary | unit | `.venv/bin/python -m pytest tests/external_recall/test_chunker.py::test_code_fence_heading_ignored -x` | ❌ Wave 0 |
| VXMEM-05 | Touch one file: exactly that file's chunks re-embed (embed call counter) | unit (fake embed + counter) | `.venv/bin/python -m pytest tests/external_recall/test_incremental.py::test_touch_one_file_reembeds_only_it -x` | ❌ Wave 0 |
| VXMEM-05 | Full re-embed on unchanged vault is a test FAILURE (zero embed calls expected) | unit | `.venv/bin/python -m pytest tests/external_recall/test_incremental.py::test_unchanged_zero_embeds -x` | ❌ Wave 0 |
| VXMEM-05 | Deleted source file purges its chunks on next build | unit (fake embed) | `.venv/bin/python -m pytest tests/external_recall/test_incremental.py::test_deleted_file_purges_chunks -x` | ❌ Wave 0 |
| VXMEM-06 | Session on fixture-vault repo: first prompt round-trip completes without blocking on ingest | unit (threading.Event mock) | `.venv/bin/python -m pytest tests/external_recall/test_background.py::test_session_does_not_block -x` | ❌ Wave 0 |
| VXMEM-06 | Before-ready query returns degraded/BM25 hits, not error | unit | `.venv/bin/python -m pytest tests/external_recall/test_background.py::test_degraded_before_ready -x` | ❌ Wave 0 |
| VXMEM-06 | Source file mtimes/contents byte-identical before and after full ingest + recall cycle | unit (snapshot mtimes) | `.venv/bin/python -m pytest tests/external_recall/test_background.py::test_source_files_readonly -x` | ❌ Wave 0 |
| VXMEM-07 | `voss recall <q>` with populated fixture vault shows `[<name>]`-labeled hits in plain output | CLI subprocess | `.venv/bin/python -m pytest tests/external_recall/test_recall_cli.py::test_plain_labeled_hits -x` | ❌ Wave 0 |
| VXMEM-07 | `voss recall <q> --json` includes `source` field with correct name | CLI subprocess | `.venv/bin/python -m pytest tests/external_recall/test_recall_cli.py::test_json_source_field -x` | ❌ Wave 0 |
| VXMEM-07 | chromadb uninstalled: recall degrades to BM25-only without error | unit (chromadb disabled) | `.venv/bin/python -m pytest tests/external_recall/test_recall_cli.py::test_degradation_no_chromadb -x` | ❌ Wave 0 |
| VXMEM-07 | Agent recall tool returns external hits alongside memory hits | unit (agent tool call) | `.venv/bin/python -m pytest tests/external_recall/test_agent_tool.py::test_agent_gets_external_hits -x` | ❌ Wave 0 |
| VXMEM-08 | Golden-query gate: ~10 queries each return expected `[<name>]`-labeled hit in top-5 | integration | `.venv/bin/python -m pytest tests/external_recall/test_golden_queries.py -x -q` | ❌ Wave 0 |
| VXMEM-08 | Golden gate passes with chromadb uninstalled (BM25 degradation) | integration (chromadb disabled) | `.venv/bin/python -m pytest tests/external_recall/test_golden_queries.py -x -k "bm25"` | ❌ Wave 0 |

### Fixture Vault Design (for VXMEM-08 golden queries)

The fixture vault at `tests/fixtures/recall_vault/` must have deterministic, distinct vocabulary per file. Suggested structure:

```
tests/fixtures/recall_vault/
├── getting-started.md      # keywords: "installation", "quickstart", "setup"
│   # Structure: preamble + ## Installation + ## Configuration + ## First Steps
├── api-reference.md        # keywords: "endpoint", "authentication", "rate limit"
│   # Structure: ## Overview + ### GET /users + ### POST /notes
├── concepts/
│   └── chunking.md         # keywords: "chunk", "boundary", "embedding", "heading"
│   # Structure: # Chunking Algorithm + ## ATX Headings + ## Oversize Guard
└── changelog.md            # keywords: "2026", "release", "breaking change"
    # Structure: # v2.0 + ## Breaking Changes + ## New Features + # v1.9
```

Golden queries (10+ examples):
1. "how do I install voss" → expects hit in `getting-started.md` (Installation section)
2. "what is the API rate limit" → expects hit in `api-reference.md`
3. "how does chunking work" → expects hit in `concepts/chunking.md`
4. "what changed in version 2.0" → expects hit in `changelog.md`
5. "setup configuration" → expects hit in `getting-started.md`
6. "endpoint authentication" → expects hit in `api-reference.md`
7. "ATX heading boundaries" → expects hit in `concepts/chunking.md`
8. "breaking changes" → expects hit in `changelog.md`
9. "first steps quickstart" → expects hit in `getting-started.md`
10. "oversize guard embedding window" → expects hit in `concepts/chunking.md`

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/external_recall/ -q -x --ignore=tests/external_recall/test_golden_queries.py`
- **Per wave merge:** `.venv/bin/python -m pytest tests/external_recall/ tests/code_recall/ tests/memory/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`; golden query gate must pass

### Wave 0 Gaps

- [ ] `voss/harness/recall/__init__.py` — new package
- [ ] `voss/harness/recall/external_index.py` — `ExternalSourceIndex`, `ExternalRecallService`, `extract_md_chunks`
- [ ] `tests/external_recall/__init__.py` — new test package
- [ ] `tests/external_recall/conftest.py` — `fake_embed_fn` (copy from `code_recall/conftest.py`), `fixture_vault_path`, `indexed_fixture_vault`, `chroma_disabled_env`
- [ ] `tests/external_recall/test_config.py` — VXMEM-01, VXMEM-02
- [ ] `tests/external_recall/test_chunker.py` — VXMEM-04
- [ ] `tests/external_recall/test_incremental.py` — VXMEM-03, VXMEM-05
- [ ] `tests/external_recall/test_background.py` — VXMEM-06
- [ ] `tests/external_recall/test_recall_cli.py` — VXMEM-07 (CLI)
- [ ] `tests/external_recall/test_agent_tool.py` — VXMEM-07 (agent tool)
- [ ] `tests/external_recall/test_golden_queries.py` — VXMEM-08
- [ ] `tests/fixtures/recall_vault/` — committed fixture markdown corpus (5-6 files, ~800 lines total)
- [ ] `tests/fixtures/recall_vault/getting-started.md`
- [ ] `tests/fixtures/recall_vault/api-reference.md`
- [ ] `tests/fixtures/recall_vault/concepts/chunking.md`
- [ ] `tests/fixtures/recall_vault/changelog.md`

*(V19's `slow` marker already registered in `pyproject.toml:L114` — no addition needed)*

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ATX heading-boundary chunking algorithm in Q4 correctly handles all edge cases (fence tracking, preamble, oversize) | Q4 / Pattern 2 | Wrong chunk boundaries → golden query misses; fix by updating `extract_md_chunks` test-first |
| A2 | `pathlib.Path.rglob(glob)` with `follow_symlinks=False` is available in Python 3.13 for symlink safety | Pitfall 7 | If `follow_symlinks` not supported, use `os.walk` with manual symlink check |
| A3 | The agent's `memory_recall` tool at `tools.py:L178-194` does not currently fuse global memory (V21) — confirmed by reading `memory_store.py:L87-100` and tracing callers | Q1 / Architecture | If wrong: V22 must not accidentally break or duplicate global memory hits |
| A4 | `_recall_hit_fields()` at `cli.py:L4786` must be updated to pass `hit.source` directly rather than normalizing to "code"/"memory" | Q6 / Pitfall 4 | If not updated: external hits labeled "memory" in `--json` — VXMEM-07 acceptance test fails |
| A5 | The current `recall_cmd` at `cli.py:L4805` does NOT fuse global memory hits (only code + project memory) | Q6 / Architecture | If wrong: V22 fan-out must avoid double-counting global hits |
| A6 | One daemon thread iterating all sources sequentially is sufficient (vs one thread per source) | Pattern 4 | If a large source blocks others: switch to per-source threads with one `_ready` event per source |

---

## Open Questions

1. **Agent tool: new `attach_external_recall_tool` vs extend `memory_recall`**
   - What we know: `memory_recall` at `tools.py:L178` calls `store.recall()` against one MemoryStore.
   - Options: (A) add `attach_external_recall_tool(tools, *, ext_service)` called from `make_toolset()` — separate tool the agent can call; (B) extend `memory_recall` to also fan out to external sources internally, fusing via `_rrf_merge`.
   - Recommendation: Option A (new tool, parallel to `attach_code_recall_tool`). Keeps tools composable; the agent can choose to search code, memory, or external sources independently. But VXMEM-07 says "both surfaces" — if the agent only uses `memory_recall`, they won't see external hits unless both tools are called. Consider extending `memory_recall` (Option B) so the agent gets external hits without knowing to call a different tool.
   - **Planner decision required.**

2. **`voss recall --refresh` and external sources**
   - What we know: `--refresh` at `cli.py:L4823-4830` triggers `code_index.build()`. D-18 says `--refresh` rebuilds external sources alongside the code index.
   - Gap: `recall_cmd` currently has no `ExternalRecallService` reference at the `--refresh` path.
   - Recommendation: Instantiate a fresh `ExternalRecallService`, call `.build()` synchronously (not background) during `--refresh`, then query.

3. **`_recall_hit_fields` source field normalization for external vs memory hits**
   - What we know: Current function hardcodes `"code"` vs `"memory"` in the JSON output `source` field. External hits need `source=<name>`.
   - Risk: Changing this field breaks existing consumers of `voss recall --json`. But the spec (VXMEM-07) explicitly requires the `source` field to carry the name.
   - Recommendation: Change `_recall_hit_fields` to use `hit.source` directly for all non-code sources. Document in CHANGELOG that the `source` field now returns the corpus name (e.g., `"memory"`, `"docs"`, `"global"`) rather than always `"memory"` for non-code hits.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `chromadb` | VXMEM-03..08 | ✓ | 1.5.9 [VERIFIED: .venv] | BM25-only degradation (F2 contract) |
| `sentence-transformers` | VXMEM-03 (embeddings) | ✓ | 5.5.0 [VERIFIED: .venv] | Chroma `DefaultEmbeddingFunction` (ONNX, tests only) |
| `all-MiniLM-L6-v2` (HF model) | VXMEM-08 (golden gate) | ✓ (cached) | — | `DefaultEmbeddingFunction` for non-live tests |
| `rank-bm25` | BM25 fallback | ✓ [VERIFIED: memory_store.py:L22] | — | No fallback needed — core dep |
| `tomllib` | VXMEM-01 | ✓ | stdlib (Python 3.13.12) [VERIFIED] | N/A — stdlib |
| Python ≥3.11 | `tomllib` stdlib | ✓ | 3.13.12 [VERIFIED: .venv] | N/A |

**Missing dependencies with no fallback:** none.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — local-only index cache; external paths are operator-declared |
| V3 Session Management | no | N/A |
| V4 Access Control | partial | Source paths are operator-declared in `config.toml` (user-owned); `.voss-cache/recall/` is user-local. Symlink escape risk addressed in Pitfall 7. |
| V5 Input Validation | yes | Chunk text is raw markdown — stored as embedding input, never executed. Source name sanitized for Chroma collection name. |
| V6 Cryptography | no | sha256 for content hash (integrity only) |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via source `path` config | Tampering | `path` is operator-declared in user's own config; no user-input from agents. Non-existent path → skip cleanly. |
| Symlink escape from declared source path | Information Disclosure | Validate resolved file path is under resolved source root before reading (see Pitfall 7) |
| Chunk text containing secrets ingested into searchable index | Information Disclosure | Source is operator-declared; operator controls what goes in. No mitigation beyond operator awareness. `_redact_recall_text` in `recall_cmd` already redacts secret-pattern strings from recall output. |
| Source files mutated via `_ingest_source` legacy path | Tampering | `_ingest_source` in `semantic.py` is NOT used by V22; external index opens files read-only only. Read-only assertion test (VXMEM-06 acceptance) enforces this. |

**Read-only by construction:** All file access in `ExternalSourceIndex.build()` uses `Path.read_text()` (read-only). The `rglob()` scan is read-only. No `open(..., 'w')` call is permitted anywhere under the declared source path. The VXMEM-06 mtime/hash snapshot test enforces this assertion.

---

## Sources

### Primary (HIGH confidence — verified against live codebase)

- `voss/harness/code/semantic_index.py` — Full read; CodeIndex/CodeIndexService pattern; `_split_oversize` (L36-50), manifest helpers (L109-124), `build()` (L186-283), `_maybe_semantic()` (L145-163), `_drop_collection()` (L173-182), `CodeIndexService` (L533-594), 7 Pitfall comments
- `voss/harness/cli.py:L4786-4858` — `_recall_hit_fields()`, `recall_cmd`; also L4823-4830 (`--refresh` path), L1939/L2249/L3466 (`attach_memory_tools` call sites)
- `voss/harness/memory_store.py:L41-54` — `Hit` dataclass; `L76-100` — `make_global_store()`; `L452-486` — `MemoryStore.recall()` + `_rrf_merge()`; `L103` — `_bm25_tokenize`
- `voss/harness/config.py` — Full read; all regex section parsers; `config_path()` at L20-23; confirmed zero `tomllib` import; `get_global_memory_enabled()` at L337
- `voss_runtime/memory/semantic.py` — Full read; `SemanticMemory.__post_init__`, `_embedding_function()` (L44-57), `_ingest_source` (L59-71)
- `voss/harness/tools.py:L159-258` — `attach_memory_tools()`, `attach_code_recall_tool()`, `make_toolset()` L898-916 (CodeIndexService spawn path)
- `voss/harness/code/service.py:L122-132` — `_get_code_index_service()` — only construction site for CodeIndexService, calls `ensure_background_build()`
- `tests/code_recall/conftest.py` — `fake_embed_fn`, `indexed_fixture_repo`, `chroma_disabled_env` fixtures (verified existing)
- `pyproject.toml:L9` — `requires-python = ">=3.11"` [VERIFIED]
- Python 3.13.12 in `.venv`; `tomllib ok` confirmed [VERIFIED: bash]
- V19-RESEARCH.md — precedent research; Pitfalls 1-8; environment availability table

### Secondary (MEDIUM confidence)

- `voss/harness/memory_cli.py:L18,112,222,280` — `make_global_store` callers confirm global memory is NOT wired into `recall_cmd` or `memory_recall` tool

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified live in .venv, confirmed versions
- Architecture / reuse seams: HIGH — all file:line citations verified by direct read
- Chunking algorithm: MEDIUM — algorithm derived from spec + markdown conventions; needs test coverage to confirm all edge cases
- Pitfalls: HIGH (P1-P4, P6-P8 from codebase evidence) / MEDIUM (P5 large-vault perf — estimated, not measured)

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (30 days; chromadb 1.5.x / sentence-transformers 5.5.x are stable; Python stdlib tomllib is stable)

---

## RESEARCH COMPLETE

**Phase:** V22 - External Memory & Docs Ingest
**Confidence:** HIGH

### Key Findings

1. **Zero new dependencies.** All required components exist: `tomllib` (stdlib, Python ≥3.11 confirmed), `chromadb` 1.5.9, `sentence-transformers` 5.5.0, `rank-bm25`. V22 mirrors V19 exactly in this respect.

2. **Two critical seams for VXMEM-07 "both surfaces."** Agent tool at `tools.py:L159` (`memory_recall` / `attach_memory_tools`) and CLI at `cli.py:L4841` (`recall_cmd` fan-out). Both require extension. `_recall_hit_fields()` at `cli.py:L4786` must be changed to pass `hit.source` directly (currently hardcodes "code"/"memory").

3. **Daemon spawn site is `tools.py:make_toolset() L898-916`.** `ExternalRecallService.ensure_background_build()` should be called there, parallel to the existing CodeIndexService spawn at `service.py:L131`. No second daemon needed for the injection path (V22 has no context-injection requirement).

4. **`tomllib` parse path is fully isolated from existing regex parser.** New `get_recall_sources()` function reads the entire file with `tomllib.load()` and extracts `data["recall"]["sources"]`. Existing regex functions are unaffected.

5. **Heading chunker replaces M10 SQLite dependency entirely.** `extract_md_chunks(content)` takes only the file content string; no SQLite needed. `_split_oversize` is imported verbatim from `semantic_index.py`. Key edge case: `#` inside code fences must not produce heading boundaries — requires fence-tracking state.

6. **V21 global memory is NOT currently in `recall_cmd` or `memory_recall` tool.** `make_global_store()` is only used in `memory_cli.py`. V22 need not fix this gap, but must not accidentally overwrite it.

### File Created

`.planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard stack | HIGH | All packages verified in .venv; tomllib confirmed stdlib |
| Reuse seams (file:line) | HIGH | All citations verified by direct read of live source |
| Chunking algorithm | MEDIUM | Derived from spec; fence-tracking edge cases need test coverage |
| Pitfalls | HIGH | Majority verified from codebase evidence or V19 precedent |

### Open Questions for Planner

1. Agent tool: new `attach_external_recall_tool` vs extend `memory_recall` internally — planner must decide before implementing VXMEM-07 agent surface.
2. `voss recall --refresh` path for external sources — currently has no `ExternalRecallService` reference; planner must add synchronous rebuild there.
3. `_recall_hit_fields()` source field change (from "code"/"memory" normalization to raw `hit.source`) — this changes the `--json` output schema for existing consumers; planner must note as a minor breaking change.

### Ready for Planning

Research complete. Planner can create PLAN.md files.
