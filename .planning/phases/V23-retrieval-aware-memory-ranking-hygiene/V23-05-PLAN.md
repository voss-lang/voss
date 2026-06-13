---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 05
type: execute
wave: 4
depends_on: ["V23-02"]
files_modified:
  - voss/harness/memory_store.py
autonomous: true
requirements: [VRNK-04, VRNK-05]

must_haves:
  truths:
    - "Over-quota eviction removes a never-retrieved newer file before an old-but-recently-retrieved file"
    - "With no .retrieval.jsonl sidecar, eviction ordering degrades to current mtime behavior"
    - "Pinned locators are exempt from quota eviction and vacuum"
    - "reindex --check exits 1 + lists stale locators on hand-edit drift; exits 0 when clean"
    - "Bare reindex re-embeds only stale/missing entries via chroma upsert and returns the count"
    - "Chroma absent: reindex/check return a clean no-op (exit 0 with notice)"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "_eviction_key, _load_pins/_save_pins, reindex store method, manifest helpers, file-based source walk"
      contains: "def reindex"
  key_links:
    - from: "MemoryStore._maybe_evict"
      to: "_eviction_key + _load_pins"
      via: "pin-exempt filter then sidecar-aware sort"
      pattern: "_eviction_key"
    - from: "MemoryStore.reindex"
      to: ".reindex-manifest.json + chroma upsert"
      via: "sha256 compare → upsert stale"
      pattern: "_reindex_manifest_path"
---

<objective>
Implement VRNK-04 retrieval-aware eviction and VRNK-05 chroma reindex/drift gate as MemoryStore methods. Eviction prefers never-retrieved then stale-retrieved over merely-old, exempts pinned rows, and falls back to mtime when the sidecar is absent. Reindex tracks a sha256 manifest of file-based sources; `--check` mirrors the `voss sync --check` exit contract; bare reindex re-embeds only stale/missing entries via chroma upsert.

Purpose: Hot memories survive purges; hand-edited mirror files stop serving stale embeddings. This plan also lands the `_load_pins`/`_save_pins` store primitives that VRNK-06 injection and VRNK-07 CLI verbs both consume.
Output: `_eviction_key`, pin primitives, reindex method + manifest helpers + file-based source walk — all core logic in the store; CLI surfacing comes in V23-07.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-SPEC.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-CONTEXT.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-PATTERNS.md

<interfaces>
From voss/harness/memory_store.py (confirmed):
- def _maybe_evict(self, source, *, est_bytes=0) -> None  # line 151; decisions/ guard at 161; files.sort by st_mtime at 183
- def _locator_from_path(self, source_dir: str, path: Path) -> str  # line 628 — locator vocabulary for pins/eviction
- def _maybe_chroma(self) -> "SemanticMemory | None"  # line 113 — None when chroma unavailable
- def vacuum(self) -> int  # line 720
- def _load_telemetry_compacted(self) -> dict  # V23-02 → {locator: {count, last_retrieved}}
- self.root  # cwd/.voss/memory
- `import hashlib` (add — stdlib)

From voss/harness/code/semantic_index.py:92-124 — V19 manifest pattern (_file_hash sha256, _load_manifest, _save_manifest with json.dumps indent=0 sort_keys=True)

From voss/cli.py:519-522 — sync --check exit contract (echo drift count; raise SystemExit(1); else echo in-sync)

Chroma upsert (chroma 1.5.9): chroma._collection.upsert(ids=[locator], documents=[text], metadatas=[meta]) — idempotent; use upsert NOT add (add raises DuplicateIDError)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pin primitives + retrieval-aware eviction key (VRNK-04)</name>
  <read_first>
    - voss/harness/memory_store.py:151-204 (_maybe_evict full body — decisions/ guard at 161, files.sort st_mtime at 183), :628-641 (_locator_from_path — locator vocabulary)
    - V23-RESEARCH.md:359-401 (Pattern 4 retrieval-aware eviction — _eviction_key buckets, sidecar-absent fallback, pin exemption), :601-606 (Pitfall 6: pin locator must match _locator_from_path)
    - V23-PATTERNS.md:132-149 (_maybe_evict replacement at line 183), :488-499 (_load_pins shape), :578-584 (decisions/ exemption — preserve, pin exemption goes AFTER it)
    - V23-CONTEXT.md D-02 (.pins.json COMMITTED — not gitignored), D-15 (eviction tie-break = mtime ascending within bucket), VRNK-06 acceptance (pinned survives over-quota eviction)
    - tests/harness/test_memory_eviction.py (os.utime mtime seeding analog)
  </read_first>
  <behavior>
    - _load_pins() returns set of locators from .voss/memory/.pins.json (json {"pins":[{locator, pinned_at}]}); {} / missing / corrupt → empty set (try/except)
    - _save_pins(set or list) persists the committed .pins.json format
    - _eviction_key(path, telemetry): never-retrieved → bucket 0; has telemetry but no last_retrieved → bucket 0; stale-retrieved → bucket 1 keyed by ascending last_retrieved; tie-break mtime ascending within bucket
    - _maybe_evict with telemetry present: over-quota source evicts never-retrieved file before old-but-recently-retrieved file
    - _maybe_evict with NO sidecar (_load_telemetry_compacted == {}): all files bucket 0 → sort degrades to mtime ascending → identical to pre-V23 ordering
    - Pinned locator filtered out of the eviction candidate list (never deleted), even when over quota
    - decisions/ source still early-returns (existing exemption preserved)
  </behavior>
  <action>
    In voss/harness/memory_store.py:
    1. Add `@property _pins_path(self) -> Path` → `self.root / ".pins.json"`.
    2. Add `_load_pins(self) -> set[str]`: read `.pins.json`, return `{p["locator"] for p in data.get("pins", []) if "locator" in p}`; try/except (OSError, json.JSONDecodeError) → empty set. Format is committed (D-02) — do NOT add to gitignore.
    3. Add `_save_pins(self, pins: list[dict]) -> None` (or accept the set + preserve pinned_at): write `{"pins": [...]}` with json.dumps; mkdir parents. Keep the on-disk schema `{"pins":[{"locator":..., "pinned_at": ISO}]}` so VRNK-07 list/show can render pinned_at. (V23-07 calls these to toggle pins.)
    4. Add `_eviction_key(self, path: Path, telemetry: dict) -> tuple`: compute `mtime = path.stat().st_mtime`; `locator = self._locator_from_path(<source>, path)` — derive source from `path.parent.name` or thread it in; entry = telemetry.get(locator); if entry is None or no `last_retrieved` → `(0, mtime)`; else `(1, entry["last_retrieved"], mtime)` (stale ascending, mtime tie-break). Keep tuple shapes comparable (pad bucket-0 tuple so comparisons don't error — e.g. always 3-tuple `(bucket, sort_ts_or_empty, mtime)`).
    5. In `_maybe_evict`, AFTER the existing `if source == "decisions": return` guard and after building `files`, replace `files.sort(key=lambda p: p.stat().st_mtime)` (line ~183) with: `telemetry = self._load_telemetry_compacted(); pins = self._load_pins(); files = [f for f in files if self._locator_from_path(source, f) not in pins]; files.sort(key=lambda p: self._eviction_key(p, telemetry))`. Recompute current_bytes if the pin filter removed candidates? No — quota check stays on the full source; pins just can't be chosen as eviction victims (they remain on disk and count toward bytes). Ensure the eviction loop still terminates if all remaining files are pinned (loop over filtered `files` only).
    6. Pitfall 6: pin locators MUST be stored using the exact `_locator_from_path` output so the exemption fires. Document this in _save_pins/_load_pins docstrings; VRNK-07 pin verb resolves locators through the same vocabulary.
    Add `import hashlib` to imports (used by Task 2). Do not touch recall().
  </action>
  <acceptance_criteria>
    - `grep -c 'def _eviction_key\|def _load_pins\|def _save_pins' voss/harness/memory_store.py` == 3
    - `.pins.json` NOT in `_VOSS_MEMORY_GITIGNORE` (grep the constant line — no `.pins.json`)
    - Retrieval-aware eviction + mtime-fallback tests pass: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k evict -q` GREEN
    - Existing eviction suite stays green: `.venv/bin/python -m pytest tests/harness/test_memory_eviction.py -q` GREEN
    - decisions/ early-return preserved (grep: `grep -n 'if source == "decisions"' voss/harness/memory_store.py` still present in _maybe_evict)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k evict -q tests/harness/test_memory_eviction.py -q 2>&1 | tail -6</automated>
  </verify>
  <done>Pin primitives + retrieval-aware eviction land; never-retrieved evicts first; mtime fallback intact; pinned rows exempt; existing eviction suite green; all VRNK-04 tests GREEN.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: reindex method + drift manifest (VRNK-05)</name>
  <read_first>
    - voss/harness/memory_store.py:113-131 (_maybe_chroma — None when unavailable), :720-788 (vacuum — chroma collection access pattern)
    - voss/harness/code/semantic_index.py:92-124 (V19 manifest: _file_hash, _load_manifest, _save_manifest — copy verbatim shape)
    - voss/cli.py:519-522 (sync --check exit contract to mirror)
    - V23-RESEARCH.md:403-470 (Pattern 5 reindex — manifest helpers, file-based sources, chroma upsert vs add, chroma-absent exit 0, exit contract), :577-581 (Pitfall 2: no clear_system_cache in chroma 1.5.9)
    - V23-PATTERNS.md:236-273 (manifest adaptation to instance methods + file-based source walk), :562-571 (chroma optional degradation)
    - V23-CONTEXT.md D-10 (file-based sources only: notes/decisions/conventions — turns/ledgers excluded), D-11 (.reindex-manifest.json gitignored, sha256 per relative path, missing manifest ⇒ everything stale), D-12 (--global flag, project default — CLI concern, store method takes the resolved store)
  </read_first>
  <behavior>
    - _file_based_sources() returns files under notes/ decisions/ conventions/ only (turns/ledgers excluded, D-10)
    - reindex(check=True): compares current sha256 of each file-based source against .reindex-manifest.json; returns the stale/missing locator list (drift). Missing manifest ⇒ all stale (D-11)
    - reindex(check=False): re-embeds stale/missing via chroma upsert (NOT add), updates manifest, returns re-embedded count
    - chroma absent (_maybe_chroma None): reindex is a clean no-op — check returns empty drift (or a sentinel the CLI maps to exit 0 + notice); bare reindex returns 0 with notice. Never raises.
    - After a hand-edit + reindex(check=False), reindex(check=True) returns empty drift (clean)
    - Does NOT import clear_system_cache (Pitfall 2)
  </behavior>
  <action>
    In voss/harness/memory_store.py:
    1. Add `@property _reindex_manifest_path(self) -> Path` → `self.root / ".reindex-manifest.json"`; `_load_reindex_manifest(self) -> dict` (try/except → {} on missing/corrupt — missing ⇒ everything stale per D-11); `_save_reindex_manifest(self, data: dict) -> None` (json.dumps indent=0 sort_keys=True, mkdir parents). Mirror V19 semantic_index shape exactly.
    2. Add `_file_based_sources(self) -> list[Path]`: rglob files under `notes/`, `decisions/`, `conventions/` only (D-10). Use relative path (relative to self.root) as the manifest key for stability.
    3. Add `reindex(self, *, check: bool = False) -> ...`: design the return so the CLI (V23-07) can implement the exit contract. Recommended: return a result object/tuple carrying `stale: list[str]` (stale/missing locators), `reembedded: int`, and `chroma_available: bool`. Logic:
       - `chroma = self._maybe_chroma()`; if None → return a result with `chroma_available=False`, empty stale, reembedded 0 (CLI prints notice + exit 0).
       - Build current hash map: for each file in `_file_based_sources()`, `_file_hash(path.read_text(errors="ignore"))`.
       - Compare to `_load_reindex_manifest()`. Stale/missing = files whose hash differs or absent from manifest. Map each stale file to its locator via `_locator_from_path(source_dir, path)`.
       - If `check`: return stale list WITHOUT re-embedding or writing the manifest (read-only check).
       - If not check: for each stale file, `chroma._collection.upsert(ids=[locator], documents=[text], metadatas=[{"source_type": src, "path": str(path), "tombstoned": False}])` (upsert — idempotent, NOT add — Pitfall/anti-pattern). Then write the updated full hash map to the manifest. Return reembedded count.
       - Wrap chroma calls in try/except so a single bad embed does not abort the whole pass (BLE001); count only successful upserts.
    Do NOT import clear_system_cache (Pitfall 2). Do NOT touch BM25 (reads files live — drift is chroma-only). The CLI verb + --global flag + exit-code wiring is V23-07; this task is the store method only.
  </action>
  <acceptance_criteria>
    - `grep -c 'def reindex\|def _file_based_sources\|_reindex_manifest_path' voss/harness/memory_store.py` >= 3
    - `grep -c 'clear_system_cache' voss/harness/memory_store.py` == 0 (Pitfall 2)
    - `grep -c '_collection.upsert' voss/harness/memory_store.py` >= 1 AND no new `_collection.add(` for reindex
    - reindex drift/repair/chroma-absent tests pass: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "reindex or drift" -q` GREEN
    - `.reindex-manifest.json` is in `_VOSS_MEMORY_GITIGNORE` (added in V23-02; confirm present)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "reindex or drift" -q 2>&1 | tail -5</automated>
  </verify>
  <done>reindex store method detects drift via sha256 manifest, re-embeds stale via upsert, no-ops cleanly when chroma absent, file-based sources only; all VRNK-05 store-level tests GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| hand-edited mirror file → chroma re-embed | operator-edited memory text re-embedded into the local chroma collection |
| .pins.json → eviction exemption | committed pin file controls which rows survive purge |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V23-05-01 | Tampering | corrupt .pins.json breaks eviction (exempts nothing / crashes) | mitigate | _load_pins try/except → empty set; eviction proceeds with mtime/telemetry ordering |
| T-V23-05-02 | Tampering | reindex re-embeds attacker-controlled file content | accept | reindex only re-embeds files already written by the project's own write paths (RESEARCH security domain); no external input |
| T-V23-05-03 | Denial of Service | reindex full-collection rebuild on large stores | mitigate | re-embed only stale/missing entries (manifest diff), not full rebuild |
| T-V23-05-04 | Tampering | chroma 1.5.9 clear_system_cache ImportError crash | mitigate | acceptance forbids clear_system_cache import (Pitfall 2) |
| T-V23-05-SC | Tampering | npm/pip/cargo installs | accept | No installs; hashlib stdlib (RESEARCH audit) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "evict or reindex or drift" -q` GREEN
- `.venv/bin/python -m pytest tests/harness/test_memory_eviction.py tests/harness/test_memory_vacuum.py -q` GREEN (no regression)
</verification>

<success_criteria>
VRNK-04 + VRNK-05 store logic GREEN; pin primitives available for V23-06/07; reindex degrades cleanly without chroma; mtime fallback preserved; existing eviction/vacuum suites green.
</success_criteria>

<output>
Create `.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-05-SUMMARY.md` when done.
</output>
