---
phase: M8
plan: 03
type: execute
wave: 2
depends_on: [M8-00]
files_modified:
  - voss/harness/memory_store.py
  - tests/harness/conftest.py
  - tests/harness/test_memory_store.py
  - tests/harness/test_recall_eval.py
  - tests/harness/test_memory_runtime_reuse.py
autonomous: true
requirements: [MEM-03, MEM-07]
tags: [memory, recall, chroma, keyword-fallback, runtime-reuse]
must_haves:
  truths:
    - "MemoryStore(cwd).bind(session_id=...) returns self with session bound; chromadb is NOT imported at this point (Pitfall 4 lazy invariant)"
    - "MemoryStore.recall(query) returns top-k Hit objects each tagged with source (turn|decision|convention|ledger|note), locator, score, excerpt, session_id"
    - "When chromadb is installed, recall() routes through voss_runtime.memory.SemanticMemory.retrieve()"
    - "When chromadb is absent (ModuleNotFoundError on first add/recall), MemoryStore transparently routes to keyword fallback — no ImportError escapes"
    - "Keyword fallback uses pathlib.Path.rglob across per-source dirs (turns, decisions, conventions, ledgers, notes) under .voss/memory/ and scores by case-insensitive substring count"
    - "Composite IDs follow D-04: turn:<session_id>:<seq>, decision:<path>, convention:<filename>, ledger:<run_id>:<seq>, note:<filename>"
    - "Req 3 acceptance — over a 5-session fake corpus, recall@top-3 ≥ 80% with chroma and ≥ 60% on keyword fallback"
    - "Req 7 acceptance — `grep -E '^class [A-Za-z_]+Memory\\b' voss/harness/` (excluding 'Store' suffix) returns zero matches outside voss_runtime/memory/"
    - "MemoryStore.write_turn / write_ledger / write_note / write_convention persist on-disk under .voss/memory/<source>/ AND add to chroma when available; each respects the per-source lockfile via portalocker"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "MemoryStore class with bind / recall / forget / write_turn / write_ledger / write_note / write_convention / vacuum / summary implementations; lazy chroma; keyword fallback; portalocker advisory locking; composite IDs"
    - path: "tests/harness/test_recall_eval.py"
      provides: "5-session fake corpus eval hitting ≥80% chroma top-3 and ≥60% keyword top-3 (Req 3)"
    - path: "tests/harness/test_memory_runtime_reuse.py"
      provides: "Grep-gate static test (already green from M8-00) + new test_semantic_memory_init_called_on_recall (mock-patch invariant)"
  key_links:
    - from: "voss/harness/memory_store.py::recall"
      to: "voss_runtime.memory.SemanticMemory.retrieve OR keyword_scan"
      via: "lazy chroma probe; ModuleNotFoundError -> fallback"
      pattern: "from voss_runtime\\.memory import .*SemanticMemory"
    - from: "voss/harness/memory_store.py::write_turn"
      to: ".voss/memory/turns/<session_id>.jsonl"
      via: "portalocker advisory lock + JSONL append + chroma add when available"
      pattern: "turns/.*\\.jsonl"
    - from: "voss/harness/memory_store.py::_keyword_scan"
      to: ".voss/memory/<source>/**"
      via: "pathlib.Path.rglob + substring scoring"
      pattern: "rglob"
---

<objective>
Land MEM-03 + MEM-07: the cross-session recall store. Implement MemoryStore on top of voss_runtime.memory primitives (no subclassing — composition only, Req 7 grep-gate enforced from M8-00). Indexed retrieval via chroma SemanticMemory when `voss[search]` is installed; degraded keyword scan over per-source on-disk files otherwise. Per-source advisory locking via portalocker (resolves Pitfall 3 cross-platform). Composite ID convention D-04 used as chroma ids[] and surfaced in /memory / /forget downstream.

Purpose: Without this plan, /recall has nowhere to query and /forget has nothing to tombstone. This is the engine that M8-04 (conventions), M8-05 (slash commands), and M8-06 (vacuum/eviction CLI) all dispatch into.
Output: Working memory_store.py with full method surface; 5-session fake corpus fixture body filled in; recall eval test green at both hit-rate floors; runtime-reuse mock test asserts SemanticMemory.__init__ is called on first recall when chroma present.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M8-project-memory-mem-01/M8-SPEC.md
@.planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md
@.planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md
@.planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md
@.planning/phases/M8-project-memory-mem-01/M8-00-SUMMARY.md
@voss/harness/memory_store.py
@voss/harness/recorder.py
@voss/harness/cognition.py
@voss_runtime/memory/semantic.py
@voss_runtime/memory/episodic.py

<interfaces>
<!-- Wave-0 skeleton already defines (this plan fills behavior): -->
- Hit dataclass: source, locator, score, excerpt, session_id, ts
- SOURCE_QUOTAS = {"turns": 0.60, "ledgers": 0.20, "decisions": 0.10, "conventions": 0.10}
- DEFAULT_CAP_BYTES = 100 * 1024 * 1024
- make_id(source, locator, seq=None) -> str
- class MemoryStore.__init__(cwd, *, cap_bytes=DEFAULT_CAP_BYTES) — stores cwd, cap_bytes, self._chroma=None, self._size_cache, self._session_id (already in place from M8-00)
- All MemoryStore methods currently raise NotImplementedError("M8-02") — note: Wave 0 stubbed plan-ID is "M8-02" but actually owned by THIS plan (M8-03). Update the marker in passing OR ignore (replacement is total).

<!-- Existing primitives reused: -->
- voss_runtime.memory.SemanticMemory(persist_dir: str, collection_name: str = "memory") — __post_init__ raises ModuleNotFoundError when chromadb missing; .add(text, *, metadata, id) -> None; .retrieve(query, *, top_k=5) -> list[dict]
- voss_runtime.memory.EpisodicMemory and Turn (compose, do not subclass — Req 7)
- voss/harness/recorder.py write_decisions_md pattern (per-source markdown mirror)
- voss/harness/cognition.py: slug(title), reserve_filename(dir_, base, ext=".md"), voss_dir(cwd)
- portalocker (installed in M8-00): portalocker.Lock(path, flags=portalocker.LOCK_EX | portalocker.LOCK_NB) — cross-platform advisory lock

<!-- Eviction logic (D-14, D-16) is owned by M8-06 (vacuum CLI). This plan stubs the eviction call site as a NoOp helper `_maybe_evict(source)` that returns immediately; M8-06 replaces the body. -->

<!-- Slash command wiring (D-15 /forget semantics) is owned by M8-05. This plan implements MemoryStore.forget(pattern, confirm) such that it tombstones (sets a flag in an on-disk tombstones index OR adds tombstoned=True chroma metadata) — slash command UX lives in M8-05. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement MemoryStore.bind + write_turn/ledger/note/convention + composite IDs + per-source locking</name>
  <files>voss/harness/memory_store.py, tests/harness/conftest.py, tests/harness/test_memory_store.py</files>
  <read_first>
    - voss/harness/memory_store.py (Wave-0 skeleton; replace NotImplementedError bodies)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/memory_store.py" (full — composition idiom + JSONL append + chmod 0o600 + composite ID)
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §"Pattern 2" + §"Pattern 3" + §Pitfall 3 (portalocker) + §Pitfall 4 (lazy chroma)
    - .planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md §D-01..D-04, §D-13
    - voss/harness/recorder.py:135-167 (write_decisions_md per-source markdown mirror template)
    - voss/harness/cognition.py:354-367 (slug + reserve_filename — reuse verbatim)
    - voss_runtime/memory/semantic.py (full; especially __post_init__ ModuleNotFoundError pattern and add/retrieve signatures)
    - tests/harness/test_memory_store.py (Wave-0 skipped stub)
    - tests/harness/conftest.py (fake_session_corpus fixture currently a SHAPE-only placeholder; fill body in this task)
  </read_first>
  <behavior>
    - MemoryStore(cwd).bind(session_id="abc-123") returns self with self._session_id == "abc-123"; chromadb is NOT yet imported (Pitfall 4 lazy invariant). Verifiable via `"chromadb" not in sys.modules` AFTER bind.
    - make_id("turn", "abc-123", seq=42) == "turn:abc-123:042"
    - make_id("decision", ".voss/decisions/2026-05-14-foo.md") == "decision:.voss/decisions/2026-05-14-foo.md"
    - make_id("convention", "2026-05-14-naming") == "convention:2026-05-14-naming"
    - write_turn(role="user", content="hello", session_id="s1", turn_idx=3) appends one JSON line `{"ts": "<iso>", "role": "user", "content": "hello", "turn_idx": 3}` to .voss/memory/turns/s1.jsonl; file mode = 0o600; when chroma is available, also calls SemanticMemory.add(text="hello", metadata={"source_type": "turn", "session_id": "s1", "path": "<abs path to jsonl>", "ts": "<iso>", "tombstoned": False}, id="turn:s1:003").
    - write_ledger(run, session_id="s1") where run has attributes/keys like .changed, .inspected, .avoided, decisions (a dict-like RunRecord) — serializes to one JSON line under .voss/memory/ledgers/<run_id>.jsonl with composite ID `ledger:<run_id>:<seq>` keyed off run.id (or a generated ULID if run.id missing).
    - write_note("user note", session_id="s1") creates .voss/memory/notes/YYYY-MM-DD-<slug>.md (slug derived from first 40 chars of text via cognition.slug + reserve_filename), frontmatter {id, session_id, created_at} + body text; chmod 0o600; chroma add with source_type="note" when available; returns the Path.
    - write_convention(candidate, session_id="s1") where candidate is a ConventionCandidate (pydantic from M8-00) — creates .voss/memory/conventions/YYYY-MM-DD-<slug>.md with frontmatter {id, status: active, related_session, evidence_turn_idx, confidence, created_at} + body "# <statement>\n\n## Evidence\n\n> <evidence_quote>\n"; chroma add with source_type="convention" when available; returns Path.
    - All writes acquire the per-source advisory lock at .voss/memory/.locks/<source>.lock via portalocker.Lock(LOCK_EX | LOCK_NB); on LockException, log a stderr one-liner ("memory.<source> busy — skipping write") and return without raising (D-13 degrade-not-die).
    - The conftest fake_session_corpus fixture seeds .voss/memory/ with 5 sessions × known content: each session has 3 turns (one user, two assistant), 1 decision (mirrored under .voss/memory/decisions/), 1 convention, 1 ledger; the fixture returns a dict of 8-10 known-answer queries -> expected composite IDs covering all four source types.
  </behavior>
  <action>
    (a) In voss/harness/memory_store.py replace the Wave-0 stubs with full implementations:
    - Imports: add `import json`, `import os`, `import sys`, `import hashlib` (for id digests if needed), `from datetime import datetime, timezone`, `from contextlib import contextmanager`, `import portalocker` (M8-00 dep). Local imports inside methods for `from voss_runtime.memory import SemanticMemory` (deferred — Pitfall 4) and `from voss.harness.cognition import slug, reserve_filename` (avoid circular imports).
    - make_id: simple f-string per D-04; if seq is None, emit `<source>:<locator>`; else `<source>:<locator>:{seq:03d}`.
    - MemoryStore.bind(self, *, session_id): set self._session_id = session_id; ensure directory layout self.root.mkdir(parents=True, exist_ok=True) and subdirs turns/ledgers/decisions/conventions/notes/chroma/.locks; create .voss/memory/.gitignore via preserve-if-exists with content "chroma/\nturns/\nledgers/\n.locks/\n" (per RESEARCH §"Preserve-if-exists `.voss/` write" — copy from cognition.py:597-604 idiom). Return self.
    - Add a private helper `def _maybe_chroma(self) -> "SemanticMemory | None":` that lazily instantiates SemanticMemory on first call and caches on self._chroma. Catch ModuleNotFoundError from voss_runtime.memory.semantic.__post_init__ -> set self._chroma = None permanently; also catch top-level `from voss_runtime.memory import SemanticMemory` ImportError. Subsequent calls return cached.
    - Add a private context manager `_lock(source)` using portalocker.Lock with LOCK_EX | LOCK_NB; on portalocker.LockException, yield None and log stderr "memory.<source> busy — skipping write"; caller checks `if lock is None: return`.
    - Add a private helper `def _maybe_evict(self, source: str) -> None: return` — STUB for M8-06 inline eviction. Docstring: "M8-06: replace body with per-source quota check + oldest-first eviction per D-14/D-16. Currently a no-op; M8-03 establishes the call site contract."
    - write_turn: compute path = self.root / "turns" / f"{session_id}.jsonl"; ts = datetime.now(timezone.utc).isoformat(timespec="seconds"); composite_id = make_id("turn", session_id, seq=turn_idx); enter _lock("turns") -> if None return; _maybe_evict("turns"); append json line to path; chmod 0o600 (idempotent); chroma_obj = self._maybe_chroma(); if chroma_obj is not None: chroma_obj.add(text=content, metadata={"source_type": "turn", "session_id": session_id, "path": str(path), "ts": ts, "tombstoned": False}, id=composite_id).
    - write_ledger: similar shape, path = self.root / "ledgers" / f"{run_id}.jsonl"; ledger content = serialized snapshot of run (changed/inspected/avoided/decisions); composite_id = make_id("ledger", run_id, seq=0). If run is a dataclass use dataclasses.asdict; if it's a dict use it directly; tolerate both.
    - write_note: text param; path = reserve_filename(self.root / "notes", slug(text[:40])); content = "---\nid: ...\nrelated_session: ...\ncreated_at: ...\n---\n\n" + text + "\n"; path.write_text(content); path.chmod(0o600); composite_id = make_id("note", path.stem); chroma add with source_type="note".
    - write_convention: candidate has fields statement, confidence, evidence_quote, evidence_turn_idx; path = reserve_filename(self.root / "conventions", slug(candidate.statement[:40])); frontmatter and body per recorder.py:135-167 template (see PATTERNS.md analog); chmod 0o600; chroma add with source_type="convention" and metadata including evidence_turn_idx + confidence.

    (b) In tests/harness/conftest.py: replace the SHAPE-only fake_session_corpus body (from M8-00) with a real implementation:
    - Build a MemoryStore against tmp_voss_repo; iterate 5 session ids ("s1".."s5"); for each session call bind(session_id=...), then write_turn 3 times with deterministic content tied to a known query (e.g. session s1 turn 0 user content = "always use snake_case in Python"; session s2 turn 0 user content = "the auth bug was in jwt token refresh", etc.); write_ledger once per session with a fake run; write_note once per session with a recognizable phrase; write a decision file directly via Path.write_text under .voss/memory/decisions/ since decisions/ is a pointer/mirror dir.
    - Return a dict mapping known-answer queries to expected composite IDs, e.g. {"snake_case": "turn:s1:000", "jwt token refresh": "turn:s2:000", "rate limiter": "note:2026-05-14-rate-limiter-tip", ...}. Provide at least 10 query→id pairs covering all four source types (turn / decision / convention / note + at least 1 ledger).

    (c) In tests/harness/test_memory_store.py remove the module-level pytestmark.skip. Fill in tests:
    - test_recall_hits_tagged_with_source: bind, write_turn one entry, write_note one entry, write_convention one entry, write a fake decision directly; call store.recall("known phrase"); assert each Hit has non-empty .source field; assert sources include at least 2 distinct values across the result set.
    - test_no_chroma_no_import_error: use chroma_disabled_env fixture; bind; write_turn x3; call recall("query"); assert no ImportError raised; assert recall returns a list[Hit] (may be empty, but no exception).
    - test_lazy_chroma_init_no_eager_import: in a fresh Python subprocess (via subprocess.run with sys.executable), import voss.harness.memory_store and call MemoryStore(Path("/tmp")).bind(session_id="x"); assert "chromadb" not in sys.modules. This pins Pitfall 4.
  </action>
  <verify>
    <automated>pytest tests/harness/test_memory_store.py -x -q && python -c "from voss.harness.memory_store import MemoryStore, make_id; from pathlib import Path; import sys; assert 'chromadb' not in sys.modules; s = MemoryStore(Path('.')).bind(session_id='x'); assert s._session_id == 'x'; assert 'chromadb' not in sys.modules; assert make_id('turn', 'sid', 42) == 'turn:sid:042'"</automated>
  </verify>
  <acceptance_criteria>
    - test_memory_store.py — all 3 tests GREEN.
    - `grep -v '^#' voss/harness/memory_store.py | grep -c "NotImplementedError"` returns at most 2 (vacuum + forget stubs remain — vacuum owned by M8-06, forget owned by M8-05+M8-06).
    - `grep -v '^#' voss/harness/memory_store.py | grep -cE "^class [A-Za-z_]+Memory\\b"` returns 0 (Req 7 grep-gate still holds; MemoryStore ends in "Store", not "Memory").
    - `grep -nE "portalocker\\.Lock" voss/harness/memory_store.py` returns ≥ 1 match (per-source lock idiom landed).
    - `grep -nE "chmod\\(0o600\\)" voss/harness/memory_store.py` returns ≥ 4 matches (one per persistent write site — turns, ledgers, notes, conventions).
    - `python -c "import sys; from pathlib import Path; from voss.harness.memory_store import MemoryStore; s = MemoryStore(Path('.')); s.bind(session_id='x'); assert 'chromadb' not in sys.modules"` succeeds (Pitfall 4 invariant).
  </acceptance_criteria>
  <done>
    MemoryStore.bind + 4 write methods + composite IDs + portalocker locking are live. Chroma stays unimported until first recall/add. fake_session_corpus fixture has real seeded content for downstream eval.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement MemoryStore.recall + keyword fallback + summary; hit-rate eval; runtime-reuse mock test</name>
  <files>voss/harness/memory_store.py, tests/harness/test_memory_store.py, tests/harness/test_recall_eval.py, tests/harness/test_memory_runtime_reuse.py</files>
  <read_first>
    - voss/harness/memory_store.py (Task 1 of this plan filled; recall + summary + forget still stub-ish)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/memory_store.py" §"Chroma add/retrieve with metadata"
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §"Pattern 2: SemanticMemory with keyword fallback" + §"Open Question 1" (forget mechanics — tombstones)
    - .planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md §D-15 (forget tombstones)
    - voss_runtime/memory/semantic.py (retrieve signature returns list[dict] — verify return shape and metadata access)
    - tests/harness/test_recall_eval.py + tests/harness/test_memory_runtime_reuse.py (Wave-0 stubs)
  </read_first>
  <behavior>
    - recall("snake_case", top_k=3) on the fake_session_corpus returns ≥ 1 Hit with .locator containing "turn:s1:" and high score (top result for that query); the corpus has ≥ 10 queries and recall@top-3 ≥ 80% (8/10 queries find their expected id in top-3) under chroma path.
    - Under chroma_disabled_env, recall("snake_case", top_k=3) returns Hits via keyword scan; recall@top-3 ≥ 60% (6/10) — keyword path is allowed to be worse.
    - recall(..., source="turn") filters Hits to source == "turn" only; both chroma and keyword paths honor the filter (chroma via metadata where-clause; keyword via per-source-dir scan only).
    - summary() returns a markdown string containing the substring "Memory store contents" and per-source counts (e.g. "turns: 15", "decisions: 3", "conventions: 2") and total bytes on disk.
    - forget("turn:s1:*") sets a tombstoned=True marker for matching composite IDs: writes a line to .voss/memory/.tombstones.jsonl with {id, tombstoned_at}; if chroma is available, also calls chroma_obj.update or upsert with metadata tombstoned=True for the matching ids (use the existing SemanticMemory API — if .update is not exposed, use the underlying ._collection.update directly with a comment "M8-06 vacuum will physically delete"); returns count of matched ids. Physical deletion is owned by M8-06 vacuum.
    - On first recall() invocation with chromadb installed, voss_runtime.memory.SemanticMemory.__init__ is called exactly once (Req 7 acceptance — mockable via unittest.mock.patch.object on SemanticMemory).
  </behavior>
  <action>
    (a) In voss/harness/memory_store.py:
    - recall(self, query, *, top_k=5, source=None): chroma_obj = self._maybe_chroma(); if chroma_obj is not None: build where = {"tombstoned": False}; if source: where["source_type"] = source; call chroma_obj._collection.query(query_texts=[query], n_results=top_k, where=where) (or SemanticMemory.retrieve(query, top_k=top_k) if it exposes the where filter; if not, call ._collection.query directly — verify by reading semantic.py for the public surface). Map results into Hit objects: Hit(source=meta["source_type"], locator=id, score=1.0 - distance, excerpt=doc[:200], session_id=meta.get("session_id"), ts=meta.get("ts")). Else fall back to self._keyword_scan(query, top_k=top_k, source=source).
    - _keyword_scan(self, query, *, top_k, source): terms = [t.lower() for t in query.split() if t]; iterate over [(name, dir) for name in ("turns","decisions","conventions","ledgers","notes") if source is None or source == name]; for each path in (self.root/name).rglob("*") if path.is_file() and not path.name.startswith(".tombstones"): text = path.read_text(errors="ignore").lower(); score = sum(text.count(t) for t in terms); if score > 0: append (score, Hit(source=name, locator=str(path.relative_to(self.root)), score=float(score), excerpt=text[:200], session_id=None, ts=None)); sort by score descending; filter out tombstoned ids (load .tombstones.jsonl set once); return top top_k Hits.
    - summary(self, *, source=None): iterate per-source dirs; count files; sum total bytes via sum(p.stat().st_size for p in dir.rglob("*") if p.is_file()); render markdown with per-source rows + total + tombstone count; return string.
    - forget(self, pattern, *, confirm=False): if not confirm and pattern looks dangerous (contains "*" wildcard matching all sources): return 0 (paranoid default — slash command UX layer in M8-05 enforces --yes for non-interactive). For each candidate composite ID matched by fnmatch.fnmatchcase(pattern, "<id>") across (a) listed chroma ids, (b) on-disk file paths under per-source dirs: append a JSONL line to .voss/memory/.tombstones.jsonl with {"id": <id>, "tombstoned_at": iso ts}; if chroma_obj is not None call chroma_obj._collection.update(ids=[matched_id], metadatas=[{"tombstoned": True}]) for each. Return count of matched ids. Acquire _lock("forget") around the full operation.

    (b) In tests/harness/test_recall_eval.py: remove module-level pytestmark.skip. Implement parametrized test with two parameters (chroma_enabled=True/False — when False use chroma_disabled_env). Iterate the fake_session_corpus dict; for each (query, expected_id) call store.recall(query, top_k=3); count hits where expected_id is in [h.locator for h in result]; compute hit_rate = hits/total. Assert hit_rate >= 0.80 when chroma_enabled else >= 0.60. Use pytest.skip("voss[search] not installed") inside the chroma_enabled=True case if voss_runtime.memory.SemanticMemory import fails at runtime (so CI without chroma still passes the keyword half).

    (c) In tests/harness/test_memory_runtime_reuse.py: keep the existing grep-gate test from M8-00 (still green). Add test_semantic_memory_init_called_on_recall: use unittest.mock.patch.object(voss_runtime.memory, "SemanticMemory") with a sentinel that records __init__ calls; bind a MemoryStore in a tmp_voss_repo; call recall("anything"); assert SemanticMemory was constructed at least once (the lazy probe). If chromadb is genuinely missing from the env, mock the import path to NOT raise ModuleNotFoundError so the mock fires.

    (d) Extend test_memory_store.py with one additional test test_recall_source_filter: write one turn + one decision; call recall("query", source="turn"); assert all returned Hits have .source == "turn".
  </action>
  <verify>
    <automated>pytest tests/harness/test_memory_store.py tests/harness/test_recall_eval.py tests/harness/test_memory_runtime_reuse.py -x -q && pytest tests/harness/ -x --timeout=120 -q</automated>
  </verify>
  <acceptance_criteria>
    - test_memory_store.py — 4 tests GREEN (3 from Task 1 + test_recall_source_filter).
    - test_recall_eval.py — both parametrizations GREEN (chroma path ≥80%, keyword path ≥60%); the chroma path may pytest.skip when voss[search] is uninstalled.
    - test_memory_runtime_reuse.py — both tests GREEN (grep-gate from M8-00 + new init-mock test).
    - `grep -v '^#' voss/harness/memory_store.py | grep -c "NotImplementedError"` returns at most 1 (only vacuum remains; owned by M8-06).
    - `grep -nE "rglob" voss/harness/memory_store.py` returns ≥ 1 (keyword scan uses rglob).
    - `grep -nE "_keyword_scan|_maybe_chroma" voss/harness/memory_store.py` returns ≥ 2 matches (private helpers defined).
    - `grep -v '^#' voss/harness/memory_store.py | grep -cE "^class [A-Za-z_]+Memory\\b"` returns 0 (Req 7 grep-gate locked).
    - Full harness suite green (`pytest tests/harness/ -x --timeout=120`).
  </acceptance_criteria>
  <done>
    MEM-03 acceptance hit-rate floors verified. MEM-07 grep-gate locked and runtime-reuse provably exercised via mock-patched __init__. recall/forget/summary all live; vacuum stubbed for M8-06.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user-typed slash arg -> MemoryStore.forget(pattern) | pattern is fnmatch-glob; not shell-interpreted; no path traversal possible (pattern matches against composite IDs and on-disk RELATIVE paths only) |
| LLM-generated turn content -> .voss/memory/turns/<session>.jsonl | content is user-prompt-derived; treated as sensitive (chmod 0o600 mandatory) |
| chromadb metadata where-clause -> SemanticMemory.retrieve | only filter on internal source_type/session_id/tombstoned keys; no user input flows directly into the where-clause as a key |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M8-03-01 | Information Disclosure | turns/notes/ledgers files readable by other local users | mitigate | every write site calls path.chmod(0o600); grep-gate verifies count ≥ 4 in acceptance |
| T-M8-03-02 | Tampering | concurrent sessions corrupt .voss/memory/turns/*.jsonl during append | mitigate | portalocker.Lock per-source advisory; LOCK_EX | LOCK_NB; degrade-not-die on contention (D-13) |
| T-M8-03-03 | Denial of Service | malformed query crashes keyword scan or chroma query | mitigate | _keyword_scan reads with errors="ignore"; chroma query in try/except routing fallback path |
| T-M8-03-04 | Information Disclosure | tombstoned content visible until vacuum | accept | D-15 explicit; documented in summary() output; vacuum (M8-06) physically removes |
| T-M8-03-05 | Information Disclosure | chromadb persist_dir leaks across repos | accept | persist_dir scoped to cwd/.voss/memory/chroma; per-project isolation by directory layout |
| T-M8-03-06 | Tampering | path traversal via user-typed note text causing slug to escape notes/ | mitigate | cognition.slug() existing implementation strips non-alphanumeric and bounds length; reserve_filename always rooted at notes/; tests don't exercise this here but slug() is tested elsewhere |
| T-M8-03-07 | Denial of Service | runaway recall on huge keyword corpus | accept | v0.1 acceptance is 5-session corpus; for now no hard limit; cap_bytes guard (M8-06) bounds total store size |
</threat_model>

<verification>
- `pytest tests/harness/test_memory_store.py tests/harness/test_recall_eval.py tests/harness/test_memory_runtime_reuse.py -x` (MEM-03 + MEM-07 acceptance)
- `pytest tests/harness/ -x --timeout=120` (no regression)
- `grep -v '^#' voss/harness/memory_store.py | grep -cE "^class [A-Za-z_]+Memory\\b"` returns 0 (Req 7 grep-gate)
- Lazy-chroma invariant: `python -c "import sys; from pathlib import Path; from voss.harness.memory_store import MemoryStore; s = MemoryStore(Path('.')).bind(session_id='x'); assert 'chromadb' not in sys.modules"`
</verification>

<success_criteria>
- MemoryStore.bind / recall / forget / write_turn / write_ledger / write_note / write_convention / summary all implemented.
- vacuum remains NotImplementedError (owned by M8-06).
- chroma lazy-init invariant holds (Pitfall 4).
- Keyword fallback returns Hits without raising when chromadb is absent.
- Recall hit-rate floors met: ≥80% top-3 with chroma, ≥60% top-3 keyword (Req 3 acceptance).
- Req 7 grep-gate holds: no `^class [A-Za-z_]+Memory$` declarations in voss/harness/ (MemoryStore ends in "Store").
- SemanticMemory.__init__ provably called via mock patch on first recall (Req 7 second acceptance).
- Per-source portalocker advisory locking on every write site.
- All write sites chmod 0o600.
- Full harness suite green; no M2 cognition regression.
</success_criteria>

<output>
After completion, create `.planning/phases/M8-project-memory-mem-01/M8-03-SUMMARY.md` summarizing:
- MemoryStore public surface delivered (8 methods + composite ID helper)
- Lazy-chroma + keyword-fallback contract
- Per-source portalocker locking choice (resolves Pitfall 3 cross-platform)
- Composite ID format D-04 in active use
- Hit-rate measurements from test_recall_eval.py (actual % on fake corpus)
- Grep-gate enforcement evidence
- Remaining stubs: vacuum (M8-06 fills); /forget slash UX (M8-05 wraps store.forget)
- Deviations from plan
</output>
