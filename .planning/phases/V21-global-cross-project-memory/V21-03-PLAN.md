---
phase: V21
plan: 03
type: execute
wave: 2
depends_on: [V21-02]
files_modified:
  - voss/harness/memory_cli.py
autonomous: true
requirements: [VGMEM-03, VGMEM-04, VGMEM-05]
cross_phase_note: >
  V21 EXECUTES ONLY AFTER V19 SHIPS (hard dependency, RESEARCH Q1 RESOLVED).
  This plan only adds CLI verbs under the existing `voss memory` group and imports
  V21-02 helpers (make_global_store, _repo_id); it does not touch V19 code.
  Parallel with V21-04 in Wave 2 (no file overlap: this owns memory_cli.py, V21-04 owns tools.py+cli.py).
must_haves:
  truths:
    - "voss memory promote <locator> copies a project note/decision/convention into the global store with promoted_from provenance"
    - "promote rejects turn:/ledger: locators with exit 1 and a clear error (D-02)"
    - "re-promoting the same locator UPDATES the existing global entry — never duplicates (D-01 dedup via promoted_from)"
    - "voss memory promote --list prints promotable (note/decision/convention) locators only"
    - "voss memory forget <locator> defaults to project; --global tombstones the global store (D-03 dual-scope)"
    - "voss memory vacuum --global compacts the global store (D-05)"
    - "promote uses a BLOCKING lock so a concurrent promote waits rather than silently dropping the write (D-13)"
    - "every file written to the global store is chmod 0o600 (shared-machine EoP mitigation)"
  artifacts:
    - path: "voss/harness/memory_cli.py"
      provides: "promote command, forget command w/ --global, vacuum --global flag"
      contains: "def memory_promote_cmd"
  key_links:
    - from: "memory_promote_cmd"
      to: "make_global_store + _repo_id"
      via: "global store write with promoted_from=<repo_id>/<locator>"
      pattern: "promoted_from"
    - from: "memory_forget_cmd --global"
      to: "make_global_store().forget"
      via: "existing tombstone machinery on global root"
      pattern: "make_global_store"
---

<objective>
Add the ONLY write path to the global store (`voss memory promote` — D-08) plus the reverse
(`voss memory forget --global` — D-03) and `voss memory vacuum --global` (D-05) under the
existing `voss memory` click group. Promote copies a project note/decision/convention into
the global store, provenance-tagged `promoted_from: <repo_id>/<locator>`, dedup-on-repromote;
turns/ledgers are rejected (D-02). Reuse-not-rebuild: the existing tombstone + vacuum + lock
machinery operates on the global root via the V21-02 `make_global_store()` instance.

Purpose: curation by construction — promote is the sole write verb; no agent path, no
auto-capture. Output: three CLI verbs in `memory_cli.py`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md
@.planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md

<interfaces>
voss/harness/memory_store.py (existing + V21-02 additions):
  MemoryStore(cwd) / MemoryStore(home, root_override=root)
  make_global_store() -> MemoryStore | None        # V21-02
  _repo_id(cwd: Path) -> str                        # V21-02
  _global_memory_root() -> Path | None             # V21-02
  store.bind(*, session_id) -> MemoryStore         # creates layout dirs
  store.forget(pattern, *, confirm=False) -> int   # tombstone machinery
  store.vacuum() -> int
  store._lock(source)  # contextmanager; LOCK_NB (silent-skip) — promote must NOT use this variant
  store._locator_from_path(source_dir, path) -> str
  store._maybe_chroma() -> SemanticMemory | None   # chroma handle; .add(text, metadata, id), ._collection.get(where=...)
  make_id(source, locator, seq=None) -> str
  reserve_filename(dir, stem) / slug(text)  # from .cognition

voss/harness/memory_cli.py (existing, verified):
  @click.group("memory") memory_group               # L18
  memory_vacuum_cmd (L23-40) — copy shape; root-existence check + sys.exit(1)
  memory_size_cmd (L82-109) — iteration shape for --list
  imports: hashlib, sys, Path, click already present
</interfaces>

<!-- D-01/D-10 provenance: promoted_from = f"{_repo_id(cwd)}/{locator}". Dedup: global chroma ._collection.get(where={"promoted_from": that}) — if hit, delete old id then add (UPDATE not append). -->
<!-- D-02 source restriction: reject locator whose prefix is turn/ledger BEFORE any store work, exit 1. -->
<!-- RESEARCH Pitfall (promote lock): use portalocker.Lock(..., flags=portalocker.LOCK_EX, timeout=5) — blocking, NOT LOCK_NB. -->
<!-- chmod 0o600 on every file written to global store (write_note analog, memory_store.py L343). -->
<!-- Promotable locator → file resolution (RESEARCH Pattern 4): note:<stem>→notes/<stem>.md; convention:<stem>→conventions/<stem>.md; decision:<rel>→root.parent/<rel>. -->
<!-- BM25-only env (chroma disabled): _maybe_chroma() returns None. EVERY chroma touch (dedup get AND final add) MUST be guarded `if chroma is not None:` — mirror write_note's _maybe_chroma() pattern (memory_store.py L322-357) so a chroma-less env never AttributeErrors. -->
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: voss memory promote — copy + provenance + dedup + source restriction + --list</name>
  <read_first>
    - voss/harness/memory_cli.py (lines 1-19 imports + group; 23-40 vacuum command shape; 82-109 size command iteration for --list)
    - voss/harness/memory_store.py (lines 322-357 write_note: file body frontmatter + chmod 0o600 + chroma.add metadata + the `chroma = self._maybe_chroma(); if chroma is not None:` guard shape; 128-144 _lock; 623-636 _locator_from_path; 56-60 make_id)
    - tests/harness/test_memory_global.py (test_promote_copies_with_provenance, test_promote_dedup_on_repromote, test_promote_rejects_turn_ledger, test_promote_list — implement to make GREEN)
    - .planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md (memory_cli.py promote skeleton + --list iteration — lines 277-306)
    - .planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md (Pattern 4 promote mechanics: 8-step algorithm + dedup-via-chroma-where + _repo_id)
  </read_first>
  <files>voss/harness/memory_cli.py</files>
  <behavior>
    - test_promote_rejects_turn_ledger: subprocess `voss memory promote turn:s1:000` → returncode 1, stderr contains "cannot be promoted"
    - test_promote_copies_with_provenance: promote a project note → global store has the file + chroma entry with metadata promoted_from == f"{_repo_id(cwd)}/{locator}"
    - test_promote_dedup_on_repromote: promote same locator twice → exactly one global entry with that promoted_from (UPDATE not duplicate)
    - test_promote_list: `--list` prints note/decision/convention locators; never turns/ledgers
    - (chroma-disabled env): promote of a valid locator still copies the file and exits 0 — no AttributeError when `_maybe_chroma()` returns None
  </behavior>
  <action>Add `@memory_group.command("promote")` named `memory_promote_cmd` with `@click.argument("locator")`, `@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))`, `@click.option("--list", "list_only", is_flag=True)`. Body: resolve `cwd = Path(cwd_str).resolve()`. If `list_only`: build `store = MemoryStore(cwd)`; iterate ONLY `("notes", "decisions", "conventions")` (D-02 excludes turns/ledgers); for each `*.md` under the source dir, compute `loc = store._locator_from_path(source, p)`, read first non-frontmatter line as an ≤80-char excerpt, `click.echo(f"{loc}: {excerpt}")`; return. Otherwise: `source_prefix = locator.split(":")[0]`; if `source_prefix in ("turn", "ledger")`: `click.echo(f"error: turns and ledgers cannot be promoted (got: {source_prefix})", err=True); sys.exit(1)` (D-02). Resolve the project file path from the locator (note:<stem>→cwd-store/notes/<stem>.md; convention:<stem>→conventions/<stem>.md; decision:<rel>→project root.parent/<rel> per RESEARCH Pattern 4); if the file does not exist, echo a clear error to stderr and `sys.exit(1)`. Read its content. Build `gstore = make_global_store()`; if None, echo "global store disabled or unavailable" + `sys.exit(1)`; `gstore.bind(session_id="promote")` to ensure layout dirs. Compute `provenance = f"{_repo_id(cwd)}/{locator}"`. Obtain the chroma handle ONCE: `chroma = gstore._maybe_chroma()` (may be None in a BM25-only env). DEDUP (D-01) — gate on chroma presence: `if chroma is not None:` `existing = chroma._collection.get(where={"promoted_from": provenance})`; if existing ids non-empty, delete those ids first (UPDATE semantics). COPY (always runs, chroma or not): write the file into the global store's matching source dir using `reserve_filename` for collision-free stem; `path.write_text(body)`; `path.chmod(0o600)` (EoP mitigation). Wrap the file write + the chroma write in a BLOCKING lock — `with portalocker.Lock(str(gstore.root / ".locks" / f"{source}.lock"), mode="a", flags=portalocker.LOCK_EX, timeout=5)` (NOT LOCK_NB — concurrent promote must wait, D-13/RESEARCH Pitfall). CHROMA ADD — explicitly gate the final add the same way write_note does: `if chroma is not None:` `chroma.add(text=content, metadata={"source_type": source, "promoted_from": provenance, "ts": <iso>, "path": str(path), "tombstoned": False}, id=make_id(source, path.stem))`. In a chroma-less env BOTH the dedup get and the final add are skipped — the file copy + 0o600 + echo still complete and the command exits 0 (mirror write_note's `_maybe_chroma()` None-tolerant pattern). Echo `promoted: {locator} -> global:{path.stem}`. Add `import portalocker` and a datetime import if not already present.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_memory_global.py -x -q -k "promote" 2>&1 | tail -15; .venv/bin/python -m voss.cli memory promote --help 2>&1 | head -8; grep -n "if chroma is not None" voss/harness/memory_cli.py</automated>
  </verify>
  <acceptance_criteria>
    - `voss memory promote turn:x` and `... ledger:x` exit 1 with stderr "cannot be promoted" (test_promote_rejects_turn_ledger)
    - promote copies the project file into the global store source dir and chroma metadata carries `promoted_from = <repo_id>/<locator>` (test_promote_copies_with_provenance)
    - re-promoting the same locator yields exactly one global entry (test_promote_dedup_on_repromote) — old chroma id deleted before re-add
    - `--list` prints only note/decision/convention locators (test_promote_list); turns/ledgers never appear
    - both the dedup `._collection.get` AND the final `chroma.add` are inside `if chroma is not None:` guards (grep ≥2 `if chroma is not None` occurrences in memory_cli.py); a BM25-only env (chroma disabled) copies the file and exits 0 with no AttributeError
    - global file written with mode 0o600 (`oct(path.stat().st_mode)[-3:] == '600'`) — assert in test or source review
    - promote uses `LOCK_EX` blocking lock (grep `LOCK_EX` in memory_cli.py; NO `LOCK_NB` on the promote path)
  </acceptance_criteria>
  <done>promote verb: copy + provenance + dedup + turn/ledger rejection + --list + 0o600 + blocking lock + chroma-None-guarded add; promote tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: voss memory forget --global (dual-scope) + vacuum --global flag</name>
  <read_first>
    - voss/harness/memory_cli.py (lines 23-40 vacuum command — extend with --global flag; existing forget handler if present, else add new command)
    - voss/harness/memory_store.py (forget L642 + vacuum L715 — both operate on self.root, unchanged)
    - tests/harness/test_memory_global.py (test_forget_global_tombstones_global, test_forget_project_default, test_vacuum_global, test_concurrent_promote_lock — implement to make GREEN)
    - .planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md (memory_cli.py forget + vacuum --global skeletons — lines 256-328)
    - .planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md (Open Questions Q2 RESOLVED: forget is dual-scope, project default + --global flag)
  </read_first>
  <files>voss/harness/memory_cli.py</files>
  <behavior>
    - test_forget_project_default: `voss memory forget <loc>` (no flag) tombstones the PROJECT store
    - test_forget_global_tombstones_global: `voss memory forget <loc> --global --yes` tombstones the GLOBAL store; project store untouched
    - test_vacuum_global: `voss memory vacuum --global` reclaims bytes from the global root
    - test_concurrent_promote_lock: two concurrent promote subprocesses — the second waits on the blocking lock (no lost write); both writes land
  </behavior>
  <action>Extend the existing `memory_vacuum_cmd` with `@click.option("--global", "use_global", is_flag=True, help="Compact global store (~/.voss/memory/).")`: when `use_global`, `from .memory_store import make_global_store`; `store = make_global_store()`; if None echo "global store disabled or unavailable" + `sys.exit(1)`; else keep the existing project path (root-existence check + `sys.exit(1)`). `store.bind(session_id="vacuum")`; `reclaimed = store.vacuum()`; echo reclaimed bytes (unchanged tail). Add `@memory_group.command("forget")` named `memory_forget_cmd` with `@click.argument("locator")`, `@click.option("--global", "use_global", is_flag=True)`, `@click.option("--yes", "confirm", is_flag=True)`, `@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))` (Q2 RESOLVED: dual-scope, project default). Body: if `use_global`: `store = make_global_store()`; if None echo "global store disabled or unavailable" + `sys.exit(1)`; `store.root.mkdir(parents=True, exist_ok=True)` so layout exists before forget. Else: `store = MemoryStore(Path(cwd_str).resolve())`. `n = store.forget(locator, confirm=confirm)`; echo `tombstoned: {n} entries`. (forget/vacuum may keep the existing LOCK_NB behavior — user can retry; only promote needs the blocking lock.)</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_memory_global.py -x -q -k "forget or vacuum_global or concurrent_promote" 2>&1 | tail -15; .venv/bin/python -m voss.cli memory forget --help 2>&1 | grep -- "--global" && .venv/bin/python -m voss.cli memory vacuum --help 2>&1 | grep -- "--global"</automated>
  </verify>
  <acceptance_criteria>
    - `voss memory forget` defaults to project scope; `--global` routes to `make_global_store()` (test_forget_project_default + test_forget_global_tombstones_global both green)
    - forget --global tombstones the global store and leaves the project store untouched (test asserts project entry survives)
    - `voss memory vacuum --global` reclaims bytes from the global root (test_vacuum_global green)
    - two concurrent promotes both land (test_concurrent_promote_lock green) — blocking lock from Task 1 serializes them
    - both `forget` and `vacuum` show `--global` in `--help` output (grep)
  </acceptance_criteria>
  <done>forget dual-scope (--global) + vacuum --global landed; forget/vacuum/concurrency tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator CLI args (locator) → store resolution | untrusted locator string crosses into file-path + chroma-where construction |
| promote write → global store on shared machine | written files persist under ~/.voss readable by the OS user |
| concurrent voss sessions (different repos) → one global chroma/locks | cross-process writes to a shared store |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V21-03-01 | Tampering / Input Validation | locator source prefix | mitigate | promote validates `source_prefix not in (turn, ledger)` BEFORE any store work; non-resolving file → exit 1 (ASVS V5, D-02) |
| T-V21-03-02 | Elevation of Privilege | global file perms on shared machine | mitigate | every promoted file `path.chmod(0o600)` (write_note analog); dirs via existing mkdir (ASVS V4) |
| T-V21-03-03 | Tampering | concurrent promote lost-write | mitigate | promote uses `portalocker.Lock(..., LOCK_EX, timeout=5)` blocking — concurrent promote waits, no silent drop (D-13; chromadb DELETE-journal serialization empirically verified) |
| T-V21-03-04 | Spoofing | dedup collision on re-promote | mitigate | dedup keyed on exact `promoted_from = <repo_id>/<locator>` via chroma where-filter; old id deleted before re-add (D-01) |
| T-V21-03-05 | Tampering | malicious note content promoted to global affecting other repos | accept | excerpt is operator's own note text; stored/printed as text, never executed (RESEARCH security domain) |
| T-V21-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: zero new deps) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q -k "promote or forget or vacuum_global or concurrent" 2>&1 | tail -8` — all green
- Coherence guard: `.venv/bin/python -m voss.cli memory --help 2>&1 | grep -E "promote|forget|vacuum"` — all three verbs registered
- Coherence guard: `.venv/bin/python -m pytest tests/harness/ tests/memory/ -q 2>&1 | tail -5` — existing memory suite unaffected
</verification>

<success_criteria>
- promote is the only global write path; copy + provenance + dedup + turn/ledger rejection + --list
- forget dual-scope (project default, --global); vacuum --global
- 0o600 file perms; blocking lock on promote; chroma touches None-guarded; no new packages
</success_criteria>

<output>
Create `.planning/phases/V21-global-cross-project-memory/V21-03-SUMMARY.md` when done
</output>
</content>
