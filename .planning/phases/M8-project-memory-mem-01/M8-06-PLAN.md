---
phase: M8
plan: 06
type: execute
wave: 5
depends_on: [M8-03, M8-05]
files_modified:
  - voss/harness/memory_store.py
  - voss/harness/memory_cli.py
  - voss/harness/cli.py
  - tests/harness/test_memory_eviction.py
  - tests/harness/test_memory_vacuum.py
autonomous: true
requirements: [MEM-06]
tags: [memory, cap, eviction, vacuum, cli-group]
must_haves:
  truths:
    - "MemoryStore inline eviction (_maybe_evict) replaces the no-op stub from M8-03 with the D-16 per-source quota check: on every write, if current_source_bytes + est_bytes > source_quota_bytes, evict oldest entries by source-tagged timestamp until under quota"
    - "_maybe_evict SKIPS source=\"decisions\" entirely: mirror under .voss/memory/decisions/ is read-only from eviction; canonical source under .voss/decisions/ is COG-06's domain (Warning 5 reconciliation)"
    - "Eviction quotas follow D-14 defaults: turns 60% / ledgers 20% / decisions 10% / conventions 10% of cap_bytes (100MB default)"
    - "Quotas are configurable via .voss/config.yml memory.quota_pct.{turns,ledgers,decisions,conventions} keys"
    - "Post-write store size <= cap (Req 6 acceptance — Seeding to 110% triggers eviction before write returns)"
    - "voss memory vacuum CLI subcommand: physically deletes tombstoned chroma rows + tombstoned on-disk whole-files (notes/conventions) + per-line JSONL compaction for turns/ledgers (atomic tmp + os.replace inside per-source portalocker lock); reports bytes reclaimed"
    - "voss memory adopt --id <slug> CLI subcommand: reads on-disk fence body of VOSS.md, recomputes hash, rewrites the hash header to match (D-07 user-accepts-human-edits flow)"
    - "voss memory size CLI subcommand: prints per-source byte counts + total + cap remaining"
    - "memory_group is registered into the main CLI group at cli.py:1263 AGENT_COMMANDS tuple"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "_maybe_evict implementation (was no-op in M8-03), vacuum implementation (was NotImplementedError), per-source size accounting helpers"
    - path: "voss/harness/memory_cli.py"
      provides: "memory_vacuum_cmd / memory_adopt_cmd / memory_size_cmd implementations (were NotImplementedError); memory_group registered with main CLI"
    - path: "voss/harness/cli.py"
      provides: "AGENT_COMMANDS tuple extended with memory_group import + registration"
  key_links:
    - from: "voss/harness/memory_store.py::_maybe_evict"
      to: "per-source quota check + oldest-first eviction"
      via: "called from every write_* method before write executes"
      pattern: "_maybe_evict\\(\""
    - from: "voss/harness/memory_cli.py::memory_vacuum_cmd"
      to: "MemoryStore.vacuum"
      via: "click subcommand dispatches to store API"
      pattern: "store\\.vacuum\\(\\)"
    - from: "voss/harness/cli.py::AGENT_COMMANDS"
      to: "voss.harness.memory_cli.memory_group"
      via: "tuple extension + register()"
      pattern: "memory_group"
---

<objective>
Land MEM-06: the 100MB cap with per-source quota eviction (D-14/D-16) AND the `voss memory vacuum` CLI subcommand (plus `voss memory adopt` for D-07 hash-mismatch resolution and `voss memory size` for inspection). Replace the no-op _maybe_evict stub left by M8-03 with the inline pre-write quota check; replace the NotImplementedError stubs in voss/harness/memory_cli.py with real Click subcommand bodies; register memory_group into the main CLI's AGENT_COMMANDS tuple.

Purpose: Without this plan, the memory store grows unbounded — chatty turn logs would eventually consume gigabytes. With it, every write is bounded by a per-source quota and the user has a CLI surface for vacuum/adopt/size operations.
Output: 3 CLI subcommands working, eviction policy active on every write, vacuum reclaims bytes, adopt unblocks D-07 hash drift, 5 eviction+vacuum tests green.
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
@.planning/phases/M8-project-memory-mem-01/M8-03-SUMMARY.md
@voss/harness/memory_store.py
@voss/harness/memory_cli.py
@voss/harness/cli.py
@voss/harness/voss_md.py

<interfaces>
<!-- M8-00 already delivered (skeletons): -->
- voss/harness/memory_cli.py: memory_group, memory_vacuum_cmd, memory_adopt_cmd, memory_size_cmd (Click group + 3 commands, bodies NotImplementedError)
- All 3 CLI commands accept --cwd flag (default ".")

<!-- M8-03 already delivered: -->
- MemoryStore.write_turn/write_ledger/write_note/write_convention all call self._maybe_evict(source) before writing — this plan fills the stub body
- MemoryStore.vacuum stub (NotImplementedError) — this plan implements
- MemoryStore.forget writes to .voss/memory/.tombstones.jsonl AND sets chroma metadata tombstoned=True

<!-- M8-01 delivered: -->
- voss_md.parse, voss_md.write_fence_body — used by memory_adopt_cmd to rewrite the hash header

<!-- Existing CLI patterns reused: -->
- voss/harness/cli.py:1263-1285 AGENT_COMMANDS tuple + register(group) helper pattern
- Existing Click commands accept --cwd via the same idiom (doctor_cmd, do_cmd, chat_cmd)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement MemoryStore._maybe_evict + vacuum + per-source size accounting</name>
  <files>voss/harness/memory_store.py, tests/harness/test_memory_eviction.py, tests/harness/test_memory_vacuum.py</files>
  <read_first>
    - voss/harness/memory_store.py (M8-03 delivered; _maybe_evict is a no-op stub; vacuum is NotImplementedError)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"Pattern 3: Inline pre-write eviction" (D-16)
    - .planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md §D-14, §D-15, §D-16
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §"Don't Hand-Roll" §"Tombstoned-record deletion" (collection.delete with where filter)
    - voss_runtime/memory/semantic.py (verify chroma collection.delete API surface — accept where dict filter)
    - tests/harness/test_memory_eviction.py + test_memory_vacuum.py (Wave-0 stubs)
  </read_first>
  <behavior>
    - _maybe_evict("turns") computes current_bytes = sum(p.stat().st_size for p in (self.root/"turns").rglob("*") if p.is_file()) (cached on self._size_cache["turns"] after first computation, refreshed on every nth write or on vacuum); reads quota_pct from .voss/config.yml if present (memory.quota_pct.turns) else falls back to SOURCE_QUOTAS["turns"]; quota_bytes = int(self.cap_bytes * quota_pct).
    - When current_bytes + est_bytes > quota_bytes, _maybe_evict iterates the source's on-disk files sorted by mtime ascending (oldest first), deletes one at a time, refreshes the size cache, and continues until current_bytes + est_bytes <= quota_bytes OR no files remain.
    - For turns/ledgers (JSONL format): eviction operates at file granularity (one .jsonl file = one session's turns or one run's ledger; oldest session/run evicted first).
    - For conventions/notes (one .md file = one entry): eviction also at file granularity.
    - For decisions/: SKIPPED entirely by _maybe_evict. The on-disk mirror under .voss/memory/decisions/ is treated as read-only by eviction; the canonical source under .voss/decisions/ is COG-06's domain (recorder.py owns those writes). Chroma rows tagged source_type="decision" are NOT evicted by inline _maybe_evict — they are pruned only by `voss memory vacuum` when explicitly tombstoned via /forget. This protects M2's COG-06 invariants from being silently mutated by chatty turn-log growth pressure.
    - If chroma is available, each evicted file also triggers chroma_obj._collection.delete(where={"path": str(evicted_path)}) to drop matching index rows.
    - est_bytes can be estimated as len(content.encode()) for the upcoming write; if unknown pass est_bytes=0 (still triggers eviction when current >= quota even without the new write).
    - vacuum() returns int bytes_reclaimed = (bytes_before_vacuum - bytes_after_vacuum). Vacuum performs THREE physical-delete passes inside a per-source advisory lock:
      (i) JSONL line-level compaction for turns/ and ledgers/ — for each .jsonl file, acquire portalocker _lock("turns") (resp. "ledgers"); read all lines; parse each line as JSON; filter out lines whose composite id (computed via make_id("turn", session_id, seq=turn_idx) for turns, or make_id("ledger", run_id, seq=turn_idx) for ledgers) is in the tombstoned set; write surviving lines to a `<file>.tmp` sibling; atomic os.replace(tmp, final) to swap; chmod 0o600 on the new file. If after compaction the file is empty, unlink it.
      (ii) Whole-file deletion for notes/ and conventions/ — for each tombstoned composite id matching `note:<filename>` or `convention:<filename>`, resolve path = self.root / source / "<filename>" (with .md suffix when applicable) and call path.unlink(missing_ok=True).
      (iii) Chroma row deletion — chroma_obj._collection.delete(where={"tombstoned": True}) (best-effort try/except; log to stderr on failure).
    - After all three passes, truncate .voss/memory/.tombstones.jsonl (write empty string; do not delete the file — keeps the dir layout stable).
    - bytes_reclaimed counter = bytes_before - bytes_after across the entire .voss/memory/ subtree (covers JSONL line compaction shrinkage + whole-file deletion + tombstones file truncation). Chroma row reclaim is NOT counted in bytes_reclaimed (chroma file accounting is opaque); document this in the docstring.
    - vacuum is idempotent: calling twice with no new tombstones returns 0 on the second call.
  </behavior>
  <action>
    (a) In voss/harness/memory_store.py replace the no-op _maybe_evict stub:
    - Defensive guard FIRST: `if source == "decisions": return` — eviction never touches decisions/ (Warning 5 reconciliation: mirror is read-only from eviction's perspective; canonical decisions live under .voss/decisions/ owned by COG-06/recorder.py). Document inline: `# decisions/ is a mirror of COG-06 output; eviction stays out — see M8-06 plan Warning 5.`
    - Read config: try cwd / ".voss/config.yml"; defensive yaml.safe_load -> {}; quota_pct_map = cfg.get("memory", {}).get("quota_pct", {}); quota_pct = quota_pct_map.get(source, SOURCE_QUOTAS.get(source, 0.0)); if quota_pct <= 0: return.
    - quota_bytes = int(self.cap_bytes * quota_pct).
    - source_dir = self.root / source; if not source_dir.exists(): return.
    - current_bytes = sum(p.stat().st_size for p in source_dir.rglob("*") if p.is_file()).
    - if current_bytes + est_bytes <= quota_bytes: self._size_cache[source] = current_bytes; return.
    - Build sorted file list by mtime ascending: files = sorted((p for p in source_dir.rglob("*") if p.is_file()), key=lambda p: p.stat().st_mtime).
    - For each oldest_path: chroma_obj = self._maybe_chroma(); if chroma_obj is not None: try: chroma_obj._collection.delete(where={"path": str(oldest_path)}); except Exception: pass (best-effort). current_bytes -= oldest_path.stat().st_size; oldest_path.unlink(missing_ok=True); if current_bytes + est_bytes <= quota_bytes: break.
    - self._size_cache[source] = current_bytes. Update _maybe_evict's signature: accept optional est_bytes param defaulting to 0; pass est_bytes from each write_* method (compute as len(content.encode()) for write_turn; len(json.dumps(...).encode()) for write_ledger; etc.).

    (b) Update each write_* method in memory_store.py to pass est_bytes into _maybe_evict before writing.

    (c) Replace vacuum stub with full implementation per the THREE-pass contract above:
    - bytes_before = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file()).
    - Read tombstones_path = self.root / ".tombstones.jsonl"; if exists: tombstoned_ids = {json.loads(line)["id"] for line in tombstones_path.read_text().splitlines() if line.strip()}; else tombstoned_ids = set(). Convert to a frozenset for O(1) membership.
    - Partition tombstoned_ids by source via parsing each composite id (split on first ":"): turn_ids, ledger_ids, note_ids, convention_ids.

    Pass (i) — JSONL compaction for turns/ and ledgers/:
    - For each (source, id_set, id_factory) in [("turns", turn_ids, lambda session_id, turn_idx: make_id("turn", session_id, seq=turn_idx)), ("ledgers", ledger_ids, lambda run_id, turn_idx: make_id("ledger", run_id, seq=turn_idx))]:
      - if not id_set: continue.
      - Enter `with self._lock(source) as lock:` (portalocker per-source advisory). If lock is None (contention): emit stderr warning "vacuum: <source> busy; skipping JSONL compaction this pass" and continue to next source.
      - For each jsonl_path in (self.root / source).rglob("*.jsonl"):
        - lines = jsonl_path.read_text().splitlines().
        - Identify the file's owning session/run by stem: session_id_or_run_id = jsonl_path.stem.
        - kept = []. For each line: try entry = json.loads(line); turn_idx = entry.get("turn_idx", 0); composite = id_factory(session_id_or_run_id, turn_idx); if composite not in id_set: kept.append(line); except json.JSONDecodeError: kept.append(line) (preserve malformed lines defensively — do not silently drop).
        - if len(kept) == len(lines): continue (no changes for this file; skip the write).
        - if not kept: jsonl_path.unlink(); continue.
        - tmp_path = jsonl_path.with_suffix(jsonl_path.suffix + ".tmp"); tmp_path.write_text("\n".join(kept) + ("\n" if kept else "")); tmp_path.chmod(0o600); os.replace(tmp_path, jsonl_path).

    Pass (ii) — Whole-file deletion for notes/ and conventions/:
    - For each id in note_ids | convention_ids: parse via composite split → source = "note" or "convention", locator = the filename stem. Resolve path = self.root / (source + "s") / f"{locator}.md" (notes/ + conventions/ store .md files). If path.exists(): path.unlink(missing_ok=True).

    Pass (iii) — Chroma row deletion:
    - chroma_obj = self._maybe_chroma(); if chroma_obj is not None: try: chroma_obj._collection.delete(where={"tombstoned": True}); except Exception as exc: click.echo(f"vacuum: chroma delete failed: {exc}", err=True) (or sys.stderr.write — match existing stderr idiom in memory_store.py).

    Finally:
    - tombstones_path.write_text("") (truncate; do not unlink — keeps layout stable).
    - Refresh self._size_cache for all sources after vacuum (sum once per source dir).
    - bytes_after = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file()); return max(0, bytes_before - bytes_after).

    Atomic-write invariants: every tmp+replace pair is the only path that mutates an existing jsonl file. No partial writes possible (matches voss_md.write_fence_body atomic idiom from M8-01).

    (d) In tests/harness/test_memory_eviction.py remove module-level pytestmark.skip. Implement 3 tests:
    - test_inline_evict_when_source_over_quota: use tmp_voss_repo with a MemoryStore with cap_bytes=4096 (small for test); fill turns dir with files until total > quota (turns quota = 0.60 * 4096 = ~2457 bytes); call write_turn one more time; assert oldest file is gone after the write returns AND post-write total bytes <= turns_quota.
    - test_post_write_size_under_cap (Req 6 main acceptance): same setup but seed at 110% of cap (cap_bytes=10240, seed turns/ to 11264 bytes total); call write_turn; assert sum-of-sizes across .voss/memory/ <= cap_bytes after the write returns.
    - test_oldest_evicted_first_within_source: write 3 files via write_turn to different session ids over 3 mtimes (use os.utime to backdate file 1); fill until quota exceeded; assert file 1 (oldest mtime) is deleted FIRST while file 2 and file 3 remain.

    (e) In tests/harness/test_memory_vacuum.py remove module-level pytestmark.skip. Implement 2 tests:
    - test_vacuum_reclaims_tombstoned_bytes: seed memory store with 3 notes; call store.forget("note:*", confirm=True); assert .tombstones.jsonl contains 3 entries; call store.vacuum(); assert returned bytes_reclaimed > 0; assert post-vacuum notes/ has 0 files.
    - test_vacuum_deletes_tombstoned_files: same setup; after vacuum, .voss/memory/notes/ should be empty; .tombstones.jsonl should be empty (truncated).
    - test_vacuum_compacts_jsonl_turn_lines (NEW — Blocker 2 acceptance): bind store with session_id="s1"; write 5 turns via write_turn (turn_idx 0..4); manually inspect .voss/memory/turns/s1.jsonl has 5 lines; call store.forget("turn:s1:002", confirm=True) to tombstone the middle turn only; call store.vacuum(); re-read .voss/memory/turns/s1.jsonl; assert it has exactly 4 lines; assert NONE of the remaining lines has turn_idx == 2; assert all four other turn_idx values (0, 1, 3, 4) are still present; assert the file's mode is 0o600 (preserved across atomic replace).
    - test_vacuum_removes_empty_jsonl_after_full_tombstone (NEW — Blocker 2 acceptance): bind store with session_id="s2"; write 2 turns; forget("turn:s2:*", confirm=True); vacuum(); assert .voss/memory/turns/s2.jsonl does NOT exist (file unlinked after all lines removed).
  </action>
  <verify>
    <automated>pytest tests/harness/test_memory_eviction.py tests/harness/test_memory_vacuum.py -x -q && pytest tests/harness/ -x --timeout=120 -q</automated>
  </verify>
  <acceptance_criteria>
    - All 3 eviction tests + 4 vacuum tests GREEN (2 existing + 2 NEW per-line JSONL compaction tests per Blocker 2).
    - `grep -v '^#' voss/harness/memory_store.py | grep -c "NotImplementedError"` returns 0 (final stub eliminated).
    - `grep -nE "self\\._maybe_evict\\(" voss/harness/memory_store.py` returns ≥ 4 matches (one per write_* method).
    - `grep -nE 'if source == ["\\']decisions["\\']: return' voss/harness/memory_store.py` returns ≥ 1 match in _maybe_evict body (Warning 5 decisions-skip guard in place).
    - `grep -nE "bytes_reclaimed" voss/harness/memory_store.py` returns ≥ 1 match (vacuum returns this).
    - `grep -nE "where=\\{\"tombstoned\": True\\}" voss/harness/memory_store.py` returns ≥ 1 (chroma vacuum integration).
    - `grep -nE "os\\.replace|\\.with_suffix\\([\"\']\\..+\\.tmp[\"\']" voss/harness/memory_store.py` returns ≥ 1 match in vacuum (per-line JSONL compaction uses tmp + os.replace atomic swap).
    - `grep -nE "self\\._lock\\([\"\']turns[\"\']|self\\._lock\\([\"\']ledgers[\"\']" voss/harness/memory_store.py` returns ≥ 1 (vacuum acquires per-source lock during JSONL compaction).
    - Full harness suite green: `pytest tests/harness/ -x --timeout=120`.
  </acceptance_criteria>
  <done>
    Inline eviction lands on every write; vacuum reclaims tombstoned bytes via per-line JSONL compaction (turns + ledgers) PLUS whole-file deletion (notes + conventions) PLUS chroma where-filter delete — all three passes wrapped in per-source portalocker locks with atomic tmp+os.replace. Post-write size <= cap invariant holds (Req 6 main acceptance).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement memory_cli subcommand bodies + register memory_group with main CLI</name>
  <files>voss/harness/memory_cli.py, voss/harness/cli.py</files>
  <read_first>
    - voss/harness/memory_cli.py (M8-00 Click skeleton — 3 commands with NotImplementedError bodies)
    - voss/harness/cli.py lines 1064-1130 (existing plugin_group / skill_group / agent_group patterns)
    - voss/harness/cli.py lines 1263-1285 (AGENT_COMMANDS tuple + register helper)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/memory_cli.py" §"Pattern F: Click subcommand group"
    - voss/harness/voss_md.py (parse + write_fence_body for memory_adopt_cmd)
  </read_first>
  <behavior>
    - `voss memory vacuum --cwd <path>` prints "reclaimed: <N> bytes" where N is the integer returned by MemoryStore.vacuum().
    - `voss memory size --cwd <path>` prints a multi-line summary: per-source bytes (turns/ledgers/decisions/conventions/notes), total bytes, cap, remaining cap.
    - `voss memory adopt --id <fence_id> --cwd <path>` reads cwd/VOSS.md, locates the fence with matching id, recomputes sha256 of the current (possibly human-edited) body, rewrites the `<!-- voss:hash <new_hash> -->` header line; if no fence with that id exists, prints error and exits non-zero; on success prints "adopted: id=<fence_id> hash=<short>".
    - All three commands exit 0 on success, non-zero on error (use click.ClickException or sys.exit(1)).
    - memory_group is registered in the main CLI's AGENT_COMMANDS tuple so `voss memory --help` lists the 3 subcommands.
  </behavior>
  <action>
    (a) In voss/harness/memory_cli.py replace the 3 NotImplementedError bodies:

    memory_vacuum_cmd(cwd_str):
    - cwd = Path(cwd_str).resolve(); store = MemoryStore(cwd); store.bind(session_id="vacuum") (session_id is required by bind; "vacuum" is a sentinel — verify M8-03 bind doesn't write any session-specific files until first write_*; if it does, factor out a "no-session" mode); reclaimed = store.vacuum(); click.echo(f"reclaimed: {reclaimed} bytes").
    - Defensive: if store.root doesn't exist, click.echo("no memory store at {cwd}/.voss/memory/", err=True); raise click.exceptions.Exit(1) or sys.exit(1).
    - Add `from .memory_store import MemoryStore` import to memory_cli.py if not present (M8-00 may have only imported click + Path).

    memory_size_cmd(cwd_str):
    - cwd = Path(cwd_str).resolve(); store = MemoryStore(cwd); root = store.root; if not root.exists(): click.echo("no memory store", err=True); sys.exit(1).
    - Compute per-source: for source in ("turns","ledgers","decisions","conventions","notes"): src_dir = root / source; size = sum(p.stat().st_size for p in src_dir.rglob("*") if p.is_file()) if src_dir.exists() else 0; click.echo(f"  {source}: {size:>10} bytes").
    - Total + cap row: total = sum-of-all; click.echo(f"  TOTAL: {total} / {store.cap_bytes} bytes ({100*total/max(1,store.cap_bytes):.1f}%)").

    memory_adopt_cmd(cwd_str, fence_id):
    - cwd = Path(cwd_str).resolve(); voss_md_path = cwd / "VOSS.md"; if not voss_md_path.exists(): click.echo("VOSS.md not found", err=True); sys.exit(1).
    - text = voss_md_path.read_text(); blocks = voss_md.parse(text); target = next((b for b in blocks if b.kind == "machine" and b.id == fence_id), None); if target is None: click.echo(f"fence id={fence_id} not found", err=True); sys.exit(1).
    - new_hash = hashlib.sha256(target.body.encode()).hexdigest(); voss_md.write_fence_body(voss_md_path, fence_id=fence_id, body=target.body) — note: write_fence_body's behavior was defined in M8-01 to RAISE HashMismatch when recorded != current; adopt needs a bypass-and-rewrite mode. Add an `adopt: bool = False` kwarg to voss_md.write_fence_body if not present; when adopt=True, skip the hash-equality precondition and just write the new hash. Or implement adopt via a small inline helper that re-renders the fence with the new hash header directly (parse blocks -> rewrite the target block in-place with new_hash -> serialize via voss_md._render). Choose the smaller surface change.
    - click.echo(f"adopted: id={fence_id} hash={new_hash[:16]}...").
    - Add `from . import voss_md` and `import hashlib`, `import sys` imports.

    (b) In voss/harness/cli.py register memory_group in AGENT_COMMANDS tuple (around cli.py:1263):
    - Add `from .memory_cli import memory_group` to top-of-file imports.
    - Locate the AGENT_COMMANDS tuple (cli.py:1263-1285); append `memory_group` to the tuple alongside existing plugin_group/skill_group/agent_group.
    - The existing register(group) function (cli.py:1282-ish) iterates AGENT_COMMANDS and calls group.add_command — no change needed; the tuple extension is sufficient.

    (c) If voss_md.write_fence_body needs an adopt kwarg (per Task 2 action a above), update voss/harness/voss_md.py:
    - Signature: `def write_fence_body(path: Path, *, fence_id: str, body: str, adopt: bool = False) -> None:`.
    - When adopt=False (default — existing behavior): if the recorded hash differs from sha256(current body), raise HashMismatch (existing contract).
    - When adopt=True: bypass the hash-equality precondition; recompute new_hash = sha256(body); write the rewritten fence with the new hash header; do not raise HashMismatch. Document the adopt semantics in the docstring: "Used by `voss memory adopt` to accept human edits as the new machine baseline; bypasses the drift guard."
    - Update memory_adopt_cmd to call `voss_md.write_fence_body(voss_md_path, fence_id=fence_id, body=target.body, adopt=True)`.
  </action>
  <verify>
    <automated>python -m voss.cli memory --help 2>&1 | grep -E "vacuum|adopt|size" | wc -l | awk '$1 >= 3 { exit 0 } { exit 1 }' && python -c "from voss.harness.memory_cli import memory_group, memory_vacuum_cmd, memory_adopt_cmd, memory_size_cmd; import click; assert isinstance(memory_group, click.Group); assert len(memory_group.commands) == 3" && pytest tests/harness/test_memory_vacuum.py tests/harness/test_memory_eviction.py -x -q && pytest tests/harness/ -x --timeout=120 -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -m voss.cli memory --help` (or equivalent invocation per project's main entry) lists vacuum, adopt, size subcommands.
    - `python -c "from voss.harness.memory_cli import memory_group; import click; assert len(memory_group.commands) == 3"` succeeds.
    - `grep -nE "memory_group" voss/harness/cli.py` returns ≥ 2 matches (import + AGENT_COMMANDS membership).
    - `grep -v '^#' voss/harness/memory_cli.py | grep -c "NotImplementedError"` returns 0.
    - `grep -v '^#' voss/harness/voss_md.py | grep -c "NotImplementedError"` returns 0.
    - All M8 phase tests green: `pytest tests/harness/test_voss_md_fence.py tests/harness/test_voss_md_injection.py tests/harness/test_voss_md_migration.py tests/harness/test_memory_store.py tests/harness/test_memory_runtime_reuse.py tests/harness/test_memory_eviction.py tests/harness/test_memory_vacuum.py tests/harness/test_conventions.py tests/harness/test_slash_recall.py tests/harness/test_slash_forget.py tests/harness/test_slash_memory.py tests/harness/test_slash_save_note.py tests/harness/test_repl_slash.py tests/harness/test_recall_eval.py -x --timeout=120`.
    - Full harness suite green: `pytest tests/harness/ tests/memory/ -x --timeout=120`.
  </acceptance_criteria>
  <done>
    `voss memory vacuum/adopt/size` all work end-to-end. memory_group is the third Click subgroup in the CLI alongside plugin_group + skill_group + agent_group. voss_md.write_fence_body gains an opt-in adopt mode for D-07 resolution. M8 phase implementation complete.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user-invoked `voss memory adopt --id <slug>` -> voss_md.write_fence_body(adopt=True) | bypasses drift guard intentionally; user is explicit about accepting on-disk edits as new baseline; CLI flow makes the decision visible |
| eviction selects which files to delete by mtime ordering | mtime-based ordering is a heuristic; no security boundary, but eviction is irreversible — Pattern: only operates on data within .voss/memory/ which is harness-owned |
| vacuum's chroma collection.delete(where=...) | where-clause is a fixed dict {"tombstoned": True}; user input never flows into the where-clause |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M8-06-01 | Tampering | adopt without explicit fence_id wipes the wrong baseline | mitigate | --id is a required Click option (M8-00 skeleton); subcommand exits non-zero if fence_id not found; user must name the fence explicitly |
| T-M8-06-02 | Denial of Service | eviction loop deletes a file that's currently locked by a concurrent session | mitigate | per-source advisory lock (M8-03 portalocker) wraps the write path; eviction runs INSIDE the lock; concurrent sessions degrade-not-die per D-13 |
| T-M8-06-03 | Information Disclosure | turn/ledger tombstoned lines remain on disk until vacuum runs | mitigate | vacuum performs per-line JSONL compaction inside per-source portalocker lock via atomic tmp + os.replace; tombstoned lines physically absent after vacuum; tests test_vacuum_compacts_jsonl_turn_lines + test_vacuum_removes_empty_jsonl_after_full_tombstone pin the invariant |
| T-M8-06-04 | Tampering | adopt accepts a fence body that was maliciously edited by a third party with disk access | accept | local disk integrity is outside Voss's threat model; matches existing trust posture for .voss/ contents |
| T-M8-06-05 | DoS | eviction with cap_bytes=0 deletes everything | mitigate | _maybe_evict returns early when quota_pct <= 0 OR cap_bytes <= 0; defensive guard added |
| T-M8-06-06 | Repudiation | bytes_reclaimed value disagrees with on-disk reality | accept | reclaim_bytes is computed by stat diff before/after; chroma deletion is best-effort try/except; documented as estimate |
</threat_model>

<verification>
- `pytest tests/harness/test_memory_eviction.py tests/harness/test_memory_vacuum.py -x` (Req 6 acceptance)
- `python -c "from voss.harness.memory_cli import memory_group; assert len(memory_group.commands) == 3"` (CLI surface)
- `pytest tests/harness/ tests/memory/ -x --timeout=120` (full regression — final phase gate)
- `grep -v '^#' voss/harness/memory_store.py voss/harness/memory_cli.py voss/harness/voss_md.py voss/harness/conventions.py | grep -c "NotImplementedError"` returns 0 (all M8 stubs eliminated)
- `grep -nE "memory_group" voss/harness/cli.py` (registered)
</verification>

<success_criteria>
- _maybe_evict implements D-14/D-16: per-source quota, oldest-first, post-write size <= cap.
- vacuum reclaims tombstoned bytes (whole-file source types) AND deletes chroma rows where tombstoned=True.
- voss memory vacuum / adopt / size all work end-to-end via CLI.
- memory_group registered in AGENT_COMMANDS tuple.
- voss_md.write_fence_body gains adopt=True mode for D-07 resolution.
- All M8 phase tests + full harness suite GREEN.
- All M8 modules report 0 NotImplementedError grep matches (full phase implementation complete).
</success_criteria>

<output>
After completion, create `.planning/phases/M8-project-memory-mem-01/M8-06-SUMMARY.md` summarizing:
- _maybe_evict implementation (per-source quota + oldest-first + chroma where-filter delete on eviction)
- vacuum semantics (per-line JSONL compaction for turns+ledgers via tmp+os.replace under portalocker; whole-file deletion for notes+conventions; chroma where=tombstoned delete; all three passes serialized)
- 3 CLI subcommands (vacuum, adopt, size) with --cwd flag
- memory_group registered into AGENT_COMMANDS tuple
- voss_md.write_fence_body gains adopt=True opt-in
- All M8 NotImplementedError stubs eliminated
- Phase-complete handoff: full M8 SPEC acceptance criteria (12 bullets in SPEC.md) covered across plans 00-06
- Deviations from plan
</output>
