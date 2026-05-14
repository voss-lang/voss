---
phase: M8
plan: 02
type: execute
wave: 2
depends_on: [M8-00, M8-01]
files_modified:
  - voss/harness/voss_md.py
  - voss/harness/cognition.py
  - voss/harness/skills/analyze.py
  - tests/harness/test_voss_md_migration.py
autonomous: true
requirements: [MEM-02]
tags: [memory, migration, cog-02-rewire]
must_haves:
  truths:
    - "voss_md.ensure_migrated(cwd) is idempotent: first call migrates pre-existing .voss/architecture.md into VOSS.md id=architecture fence and archives the original byte-identically; subsequent calls no-op"
    - "Archive file sha256 equals pre-migration .voss/architecture.md sha256 (Req 2(a) acceptance)"
    - "VOSS.md fence body contains the original architecture.md frontmatter + body verbatim (head of fence body still matches cognition.py FRONTMATTER_RE)"
    - "cognition.py::_load_arch reads fence body from VOSS.md via voss_md.read_fence_body(cwd/VOSS.md, fence_id='architecture') instead of .voss/architecture.md (Pitfall 2 read-path rewire)"
    - "skills/analyze.py writes to the id=architecture fence body of VOSS.md via voss_md.write_fence_body, not to .voss/architecture.md"
    - "Re-running analyze on a VOSS.md with a human-edited block preserves the human block; only the machine fence is overwritten (Req 2(c) acceptance)"
    - "ensure_migrated is invoked at REPL boot in _run_repl AND in do_cmd before cognition_mod.load() so the read path never sees a half-migrated state"
  artifacts:
    - path: "voss/harness/voss_md.py"
      provides: "ensure_migrated implementation (read+archive+fence-fold)"
    - path: "voss/harness/cognition.py"
      provides: "_load_arch read-path rewire — sources fence body from VOSS.md instead of .voss/architecture.md (Pitfall 2)"
    - path: "voss/harness/skills/analyze.py"
      provides: "arch_path/arch_backup logic switched to voss_md.read_fence_body/write_fence_body; single-fs_write contract preserved by post-skill fence-fold"
  key_links:
    - from: "voss/harness/cli.py::_run_repl (M8-01 boot)"
      to: "voss_md.ensure_migrated"
      via: "boot-time idempotent migration call inserted after voss_md.read_and_inject"
      pattern: "voss_md\\.ensure_migrated\\(cwd\\)"
    - from: "voss/harness/cognition.py::_load_arch"
      to: "voss_md.read_fence_body"
      via: "read fence body, retain FRONTMATTER_RE match on head of body"
      pattern: "voss_md\\.read_fence_body"
    - from: "voss/harness/skills/analyze.py"
      to: "voss_md.write_fence_body"
      via: "post-fs_write fold of agent output into id=architecture fence"
      pattern: "voss_md\\.write_fence_body"
---

<objective>
Land MEM-02: archive pre-existing `.voss/architecture.md` byte-identical, fold its content into a new root `VOSS.md` under an `id=architecture` machine fence, and rewire the COG-02 read/write paths to operate on the fence body instead of the standalone `.voss/architecture.md` file. This resolves RESEARCH Pitfall 2 (cognition loader reads stale architecture.md after migration) by editing BOTH the write path (skills/analyze.py) AND the read path (cognition.py::_load_arch) in the same plan.

Purpose: Without this plan, the migration is one-sided — analyze writes to VOSS.md but cognition.py keeps looking for `.voss/architecture.md` (now archived) and reports cognition uninitialized. This plan delivers a coherent one-shot data migration + symmetric read/write rewire.
Output: ensure_migrated implementation (replaces last NotImplementedError stub in voss_md.py), cognition.py::_load_arch sources from VOSS.md fence, skills/analyze.py writes through voss_md.write_fence_body, 3 migration tests green, boot-time ensure_migrated wired into both _run_repl and do_cmd.
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
@.planning/phases/M8-project-memory-mem-01/M8-01-SUMMARY.md
@voss/harness/voss_md.py
@voss/harness/cognition.py
@voss/harness/skills/analyze.py
@voss/harness/cli.py

<interfaces>
<!-- M8-01 delivered (now usable here): -->
- voss_md.parse(text) -> list[Block]
- voss_md.read_and_inject(cwd) -> str | None
- voss_md.read_fence_body(path, *, fence_id) -> str | None (raises HashMismatch on drift)
- voss_md.write_fence_body(path, *, fence_id, body) -> None (atomic temp+rename; raises HashMismatch when overwriting drifted baseline)
- voss_md.machine_fence_path_or_marker(cwd, *, fence_id) -> Path  (returns cwd/VOSS.md)
- HashMismatch with fence_id, recorded, actual, on_disk attributes

<!-- Existing patterns reused in this plan: -->
- voss/harness/cognition.py FRONTMATTER_RE at cognition.py:38 (re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL))
- voss/harness/cognition.py::_load_arch at cognition.py:101-114 — never-raises loader signature returns (body, frontmatter_obj | None)
- voss/harness/cognition.py::voss_dir(cwd) helper
- voss/harness/skills/analyze.py:36-80 — arch_path resolution + arch_backup read + post-skill schema check + rollback pattern
- voss/harness/cli.py M8-01 wires: _run_repl around cli.py:717 and do_cmd around cli.py:540 already call voss_md.read_and_inject(cwd)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement voss_md.ensure_migrated with byte-identical archive + fence fold</name>
  <files>voss/harness/voss_md.py, voss/harness/cli.py, tests/harness/test_voss_md_migration.py</files>
  <read_first>
    - voss/harness/voss_md.py (M8-01 delivered parse / read_fence_body / write_fence_body — use these)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/voss_md.py" §"Archive byte-identity pattern"
    - .planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md §D-06 (migration contract)
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §"Runtime State Inventory" + §Pitfall 2
    - voss/harness/cognition.py:38 (FRONTMATTER_RE) — verify the regex match invariant after migration
    - voss/harness/cli.py (M8-01 boot wires for _run_repl + do_cmd; ensure_migrated must slot in adjacent to read_and_inject)
    - tests/harness/test_voss_md_migration.py (Wave-0 skipped stub — remove module-level skip)
  </read_first>
  <behavior>
    - ensure_migrated(cwd) where cwd/.voss/architecture.md exists and cwd/VOSS.md does NOT exist: creates cwd/VOSS.md containing an `id=architecture` fence whose body equals the verbatim bytes of architecture.md; creates cwd/.voss/archive/architecture-YYYY-MM-DD.md with bytes identical to the pre-migration architecture.md (sha256 equality); removes the original cwd/.voss/architecture.md; returns True.
    - ensure_migrated(cwd) where cwd/VOSS.md already exists: returns False without modifying any file (idempotent — second-run safety).
    - ensure_migrated(cwd) where neither architecture.md nor VOSS.md exists: returns False without creating either; no exception.
    - ensure_migrated(cwd) where VOSS.md does not exist but architecture.md does exist AND an archive at .voss/archive/architecture-YYYY-MM-DD.md already exists for today's date: appends a numeric suffix (`-2`, `-3`, ...) following the cognition.reserve_filename convention, OR uses a millisecond suffix; never overwrites an existing archive file.
    - Post-migration: cognition.py::FRONTMATTER_RE still matches when applied to the fence body (frontmatter `---\n...\n---\n` lives at the head of the fence body verbatim).
    - Archive sha256 invariant: hashlib.sha256(cwd/.voss/archive/architecture-<date>.md bytes).hexdigest() == hashlib.sha256(pre-migration cwd/.voss/architecture.md bytes).hexdigest()
  </behavior>
  <action>
    (a) Replace the NotImplementedError stub of ensure_migrated in voss/harness/voss_md.py with the migration logic:
    - Import datetime, hashlib, shutil from stdlib; import cognition.voss_dir + cognition.reserve_filename (no circular import — cognition.py imports from voss_md is the only direction; this import inside voss_md goes outward, so verify direction with a grep and if circular use a deferred local import inside the function).
    - Compute arch_path = cognition.voss_dir(cwd) / "architecture.md"; voss_md_path = cwd / "VOSS.md".
    - If voss_md_path.exists(): return False immediately.
    - If not arch_path.exists(): return False immediately.
    - Read arch_bytes = arch_path.read_bytes(); record arch_sha = hashlib.sha256(arch_bytes).hexdigest().
    - Compute archive_dir = cognition.voss_dir(cwd) / "archive"; archive_dir.mkdir(parents=True, exist_ok=True).
    - Compute today = datetime.now(timezone.utc).strftime("%Y-%m-%d"); candidate = archive_dir / f"architecture-{today}.md"; if candidate.exists(), suffix the filename with `-2`, `-3`, ... (use cognition.reserve_filename-style numeric suffix loop) until a non-colliding path is found.
    - archive_path.write_bytes(arch_bytes); assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == arch_sha (raise RuntimeError on inequality — corruption signal).
    - Compute fence_body = arch_bytes.decode("utf-8") — keep frontmatter at head; if decode fails (extremely unlikely for markdown) fall back to errors="replace" with a stderr warning.
    - Call voss_md.write_fence_body(voss_md_path, fence_id="architecture", body=fence_body) — this creates VOSS.md (since it didn't exist) and writes the fence atomically via M8-01's atomic temp+rename.
    - arch_path.unlink() to remove the source file (the archive is now the source of truth for the original bytes).
    - Return True.

    (b) In voss/harness/cli.py: extend the M8-01 boot wires. In _run_repl (around the read_and_inject insertion from M8-01), add `voss_md.ensure_migrated(cwd)` BEFORE `bundle = cognition_mod.load(cwd, ...)` — order matters because cognition_mod.load reads the fence body and needs the migration to have run first. In do_cmd (around cli.py:540), insert the same `voss_md.ensure_migrated(cwd)` call before `do_bundle = cognition_mod.load(cwd)`.

    (c) In tests/harness/test_voss_md_migration.py: remove the module-level pytestmark.skip. Implement the three tests using the `pre_m8_architecture_md` fixture from M8-00 conftest:
    - test_archive_sha256_matches_pre_migration: setup writes a known .voss/architecture.md with bytes `B`; capture sha256(B); call voss_md.ensure_migrated(tmp_voss_repo); locate the archive file under .voss/archive/ (glob `architecture-*.md`); assert sha256(archive bytes) == sha256(B); assert original .voss/architecture.md no longer exists; assert ensure_migrated returned True.
    - test_voss_md_contains_pre_migration_content: same setup; after ensure_migrated, call voss_md.read_fence_body(tmp_voss_repo / "VOSS.md", fence_id="architecture"); assert returned body equals B.decode("utf-8"). Also assert cognition.FRONTMATTER_RE.match(body) is truthy (Pitfall 2 invariant — frontmatter still parseable at head of fence body).
    - test_re_analyze_preserves_human_sections: setup writes .voss/architecture.md with body B; call ensure_migrated; then manually edit VOSS.md to APPEND a human paragraph after the closing fence marker (use file.write_text with original-fence + "\n\n## Human notes\n\nhand-written content\n"); then call voss_md.write_fence_body(VOSS.md, fence_id="architecture", body="UPDATED machine content") to simulate a re-analyze write; re-read VOSS.md; assert "hand-written content" substring still present; assert read_fence_body returns "UPDATED machine content".
  </action>
  <verify>
    <automated>pytest tests/harness/test_voss_md_migration.py -x -q && pytest tests/harness/test_voss_md_fence.py tests/harness/test_voss_md_injection.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - All 3 tests in test_voss_md_migration.py GREEN.
    - `grep -v '^#' voss/harness/voss_md.py | grep -c "NotImplementedError"` returns 0 (all stubs replaced).
    - `grep -n "voss_md.ensure_migrated" voss/harness/cli.py` returns ≥ 2 matches (one in _run_repl, one in do_cmd).
    - `python -c "from pathlib import Path; from voss.harness.voss_md import ensure_migrated; assert ensure_migrated(Path('/nonexistent-zzz')) is False"` succeeds (returns False on missing cwd).
    - Pre-existing tests still green: `pytest tests/harness/test_voss_md_fence.py tests/harness/test_voss_md_injection.py -x` is GREEN.
  </acceptance_criteria>
  <done>
    Migration is byte-identical, idempotent, and wired into both REPL/one-shot boot paths so the read path (Task 2 below) never sees a half-state. The last NotImplementedError stub in voss_md.py is gone.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewire cognition._load_arch read path + skills/analyze.py write path</name>
  <files>voss/harness/cognition.py, voss/harness/skills/analyze.py, tests/harness/test_voss_md_migration.py</files>
  <read_first>
    - voss/harness/cognition.py lines 38 (FRONTMATTER_RE) + 101-134 (_load_arch) + 207-229 (load() call site that invokes _load_arch)
    - voss/harness/skills/analyze.py (full — single-fs_write skill; arch_path/arch_backup/post-schema-check rollback)
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md §"voss/harness/cognition.py (MODIFIED)" + §"voss/harness/skills/analyze.py (MODIFIED)" + §"Pattern E: Backup-and-restore"
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §Pitfall 2 (cognition loader rewire — write path AND read path must both be redirected in the same plan)
    - voss/harness/voss_md.py (now fully implemented after Task 1 of this plan)
  </read_first>
  <behavior>
    - After Task 1 migrates a repo, cognition.load(cwd) returns a bundle whose architecture_md attribute is non-empty and whose parsed frontmatter is correctly populated (git_head, analyzed_at, file_count, analyzer_version) — proving _load_arch successfully read the fence body and that FRONTMATTER_RE matched.
    - In a repo where VOSS.md exists with NO id=architecture fence (e.g. user hand-wrote VOSS.md from scratch before running analyze), cognition.load returns a bundle with architecture_md = None (no error, no crash) — matches the existing "never-raises loader" contract.
    - After the analyze skill runs in a repo with an existing VOSS.md, the agent's fs_write target produces content that is folded into the id=architecture fence; subsequent calls to voss_md.read_fence_body(VOSS.md, fence_id="architecture") return the new body; the body still passes FRONTMATTER_RE at the head.
    - If the agent's fs_write produces malformed output (no frontmatter at head, doesn't match FRONTMATTER_RE), analyze.py rolls back to arch_backup (existing rollback semantics preserved — Pattern E).
    - HashMismatch from voss_md.read_fence_body (signaling drift between recorded hash and current body) is NOT raised here in production read paths: analyze.py reads via read_fence_body wrapped in a try/except that treats HashMismatch as "use the on-disk body as baseline" (D-07 says the user must run `voss memory adopt` to formally accept human edits — but analyze.py's RESTORE path needs the bytes regardless, so we catch and use e.on_disk as the backup body).
  </behavior>
  <action>
    (a) In voss/harness/cognition.py: locate _load_arch (cognition.py:101-114) and its caller in load() (cognition.py:209-227). Rewire:
    - Create a NEW helper `def _load_arch_from_voss_md(cwd: Path, errors: list[str]):` adjacent to _load_arch (keep the old _load_arch function in place but mark its docstring as "DEPRECATED: post-M8 read path is _load_arch_from_voss_md").
    - The new helper: import voss_md locally inside the function to avoid circular import; compute voss_md_path = cwd / "VOSS.md"; if not voss_md_path.exists(): return None, None.
    - Wrap `body = voss_md.read_fence_body(voss_md_path, fence_id="architecture")` in try/except: catch voss_md.HashMismatch as exc and set body = exc.on_disk (the human-edited content is still usable for read purposes; D-07 adopt is a separate user-driven flow).
    - Catch (OSError, UnicodeDecodeError) as e: errors.append(f"{voss_md_path}: read error: {e}"); return None, None.
    - If body is None (fence id absent): return None, None.
    - Run FRONTMATTER_RE.match(body) — preserve the existing logic for splitting frontmatter from body and returning (body_str_without_frontmatter, ArchitectureFrontmatter | None). Re-use the existing FRONTMATTER_RE + pydantic schema parse code from the old _load_arch — copy the same parse-validate flow so the return shape is identical.
    - In load() (cognition.py:207-227), replace the existing `_load_arch(root / "architecture.md", errors)` call with `_load_arch_from_voss_md(cwd, errors)`. Make sure `cwd` is in scope — if the surrounding function only has `root` (== voss_dir(cwd)), thread cwd through as well (it's already a parameter to load() per cognition.py signature).

    (b) In voss/harness/skills/analyze.py: rewrite the arch_path/arch_backup block (analyze.py:36-80):
    - Replace `arch_path = cognition.voss_dir(cwd) / "architecture.md"` with `voss_md_path = cwd / "VOSS.md"; fence_id = "architecture"`.
    - Replace the `arch_backup = arch_path.read_text()` read with: try `arch_backup = voss_md.read_fence_body(voss_md_path, fence_id=fence_id)` except (OSError, UnicodeDecodeError) as e: arch_backup = None; except voss_md.HashMismatch as e: arch_backup = e.on_disk. Add `from .. import voss_md` to the analyze.py imports.
    - The single-fs_write contract is preserved by NOT changing what the agent writes — the agent still emits exactly one fs_write to a path the planner picks. Use a temp staging path: stage_path = cognition.voss_dir(cwd) / ".analyze.staging.md". After the agent run completes (analyze.py:44-57), read stage_path.read_text() into a staged variable. (If stage_path doesn't exist after the agent run, the agent never wrote anything — treat as failure, restore arch_backup.)
    - Post-write schema check (analyze.py:59-80): apply cognition.FRONTMATTER_RE.match(staged) check on the staged content. If it matches, fold via `voss_md.write_fence_body(voss_md_path, fence_id=fence_id, body=staged)`. If FRONTMATTER_RE does not match: emit the existing warning to stderr and restore via `voss_md.write_fence_body(voss_md_path, fence_id=fence_id, body=arch_backup)` ONLY if arch_backup is not None (otherwise leave VOSS.md untouched).
    - Update the agent's tool-call prompt (the section of analyze.py that describes the target path to the agent) to instruct the agent to write to the staging path (`.voss/.analyze.staging.md`) instead of `.voss/architecture.md`. The agent does not need to know about the fence — the harness folds afterward. Leave the agent prompt content otherwise unchanged.
    - Delete stage_path after folding (success or rollback) via stage_path.unlink(missing_ok=True).
    - Update HashMismatch import: `from ..voss_md import HashMismatch` (locally inside the function or top-level — match analyze.py's existing import style).

    (c) Extend tests/harness/test_voss_md_migration.py with one additional assertion inside test_re_analyze_preserves_human_sections (already exists from Task 1 of this plan): after the simulated re-analyze write, call cognition.load(tmp_voss_repo) and assert the returned bundle.architecture_md attribute is non-empty AND contains "UPDATED machine content". This proves the READ path rewire (Task 2(a)) actually picks up writes from the WRITE path (Task 2(b) — but here we simulate it via voss_md.write_fence_body since invoking the real skill requires a provider; the symmetry of read and write through the same voss_md API is what we're pinning).
  </action>
  <verify>
    <automated>pytest tests/harness/test_voss_md_migration.py tests/harness/test_voss_md_fence.py tests/harness/test_voss_md_injection.py -x -q && pytest tests/harness/ -x -q --timeout=60</automated>
  </verify>
  <acceptance_criteria>
    - All 3 tests in test_voss_md_migration.py GREEN, including the extended cognition.load assertion in test_re_analyze_preserves_human_sections.
    - `grep -nE "_load_arch_from_voss_md|voss_md\\.read_fence_body" voss/harness/cognition.py` returns ≥ 2 matches.
    - `grep -nE "voss_md\\.(read|write)_fence_body" voss/harness/skills/analyze.py` returns ≥ 2 matches.
    - `grep -nE 'arch_path = cognition\\.voss_dir\\(cwd\\) / "architecture\\.md"' voss/harness/skills/analyze.py` returns 0 (old write target gone).
    - `grep -nE 'root / "architecture\\.md"' voss/harness/cognition.py` returns 0 inside the `load()` body (old read target gone in production path; the old _load_arch helper may remain as deprecated).
    - Full harness suite (`pytest tests/harness/ -x --timeout=60`) is GREEN — no regression in M2 cognition tests.
  </acceptance_criteria>
  <done>
    Read path (cognition.py::_load_arch_from_voss_md) and write path (skills/analyze.py via voss_md.write_fence_body) are symmetric — both operate on the id=architecture fence of cwd/VOSS.md. Pitfall 2 resolved. Single-fs_write skill contract preserved (agent writes to staging, harness folds). Backward-compat: cognition.load on a repo with no VOSS.md returns architecture_md=None without crashing.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .voss/architecture.md bytes -> .voss/archive/architecture-YYYY-MM-DD.md | one-shot copy must be byte-identical; corruption here loses M2 work permanently |
| agent fs_write -> .voss/.analyze.staging.md -> voss_md.write_fence_body | staging buffer + fold guards against malformed agent output corrupting VOSS.md |
| existing .voss/architecture.md trusted prior content -> VOSS.md fence | migration crosses a format boundary but content is user-owned, trusted |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M8-02-01 | Tampering | partial write of archive corrupts pre-M8 data | mitigate | ensure_migrated reads bytes -> writes archive -> asserts sha256 equality before unlinking original; on inequality raise RuntimeError to abort migration (original .voss/architecture.md remains intact) |
| T-M8-02-02 | Tampering | concurrent ensure_migrated calls race on archive filename | mitigate | numeric-suffix reserve_filename loop (no overwrite); since ensure_migrated is called at boot it can race with a concurrent voss session — accept rare race as second call returns False due to VOSS.md existence check |
| T-M8-02-03 | Denial of Service | malformed agent fs_write corrupts VOSS.md (loses M2 architecture content) | mitigate | analyze.py reads arch_backup via voss_md.read_fence_body BEFORE the skill runs; on FRONTMATTER_RE check failure rolls back via voss_md.write_fence_body(body=arch_backup); rollback covered by existing Pattern E and preserved |
| T-M8-02-04 | Information Disclosure | archive file under .voss/archive/ committed to git accidentally | accept | .voss/archive/ inherits .voss/ gitignore policy from M2; M8-03 will extend .voss/.gitignore but archive directory is under the existing .voss/ prefix already gitignored for sessions |
| T-M8-02-05 | Tampering | HashMismatch on read in cognition._load_arch (user hand-edited fence body) | mitigate | catch HashMismatch and use e.on_disk as body — preserves read path; D-07 adopt remains the formal accept path; user-edited content is treated as truth for read purposes only, not for forwarding into a new machine write without adopt |
</threat_model>

<verification>
- `pytest tests/harness/test_voss_md_migration.py -x` (3 migration tests green)
- `pytest tests/harness/ -x --timeout=60` (no M2 cognition regression)
- `grep -nE "_load_arch_from_voss_md" voss/harness/cognition.py` (rewire landed)
- `grep -nE "voss_md\\.write_fence_body" voss/harness/skills/analyze.py` (write path rewire landed)
- `grep -v '^#' voss/harness/voss_md.py | grep -c "NotImplementedError"` == 0 (all stubs filled)
</verification>

<success_criteria>
- ensure_migrated implements idempotent, byte-identical-archive migration.
- _run_repl AND do_cmd both call ensure_migrated before cognition_mod.load.
- cognition._load_arch_from_voss_md is the new read path; cognition.load uses it.
- skills/analyze.py writes to VOSS.md fence via voss_md.write_fence_body (with stage-and-fold to preserve single-fs_write contract).
- 3 migration tests + extended cognition.load read-back assertion all GREEN.
- Pre-existing M2 cognition tests unchanged (no regression).
- The bare .voss/architecture.md file path is no longer referenced as a production read or write target in cognition.py::load or skills/analyze.py.
- Pitfall 2 closed: post-migration cognition.load returns non-empty architecture_md.
</success_criteria>

<output>
After completion, create `.planning/phases/M8-project-memory-mem-01/M8-02-SUMMARY.md` summarizing:
- Migration semantics (idempotent, byte-identical archive, fence fold)
- Symmetric read/write rewire: cognition._load_arch_from_voss_md ↔ skills/analyze.py write via voss_md.write_fence_body
- Pitfall 2 resolution
- Backward-compat note (cognition.load with no VOSS.md returns architecture_md=None)
- Atomic-write inheritance (write_fence_body's temp+rename, ensure_migrated chains through it)
- Files touched (3)
- Deviations from plan
</output>
