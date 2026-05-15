---
phase: T2-parallel-tools-multi-edit
plan: 05
type: execute
wave: 4
depends_on: [T2-04]
files_modified:
  - voss/harness/tools.py
  - tests/harness/tools/test_fs_read_many.py
autonomous: true
requirements: [PAR-04]
must_haves:
  truths:
    - "New tool fs_read_many(paths: list[str]) -> str is registered in make_toolset with is_mutating=False"
    - "fs_read_many returns a single bundled string in the locked format: each section is `=== {path} ===\\n{content_or_error}\\n` joined by newline"
    - "Per-path errors are inline in their slot (never abort the whole call); call itself never raises a Python exception attributable to a bad path"
    - "jail_path is called per-path inside try/except SandboxError; jail violation becomes `<error: path outside cwd: {path}>` in that slot"
    - "Per-file size cap of 30KB (30720 bytes); truncated content uses the exact format `<truncated, total {N} bytes>` borrowed from shell_run convention"
    - "Empty paths list returns the sentinel `<no paths requested>`"
    - "Duplicate paths in the input list are NOT deduped — both slots filled (deterministic order)"
    - "fs_read (single-path) preserved unchanged"
    - "Read errors per slot use the existing fs_read error envelopes: not found, is a directory, binary file — plus the new path-outside-cwd envelope"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "fs_read_many @tool decorated function + ToolEntry(descriptor=fs_read_many, is_mutating=False) registration in make_toolset + _read_one_for_bundle helper"
      contains: "def fs_read_many\\|fs_read_many.*is_mutating=False\\|_read_one_for_bundle"
    - path: "tests/harness/tools/test_fs_read_many.py"
      provides: "4 SPEC PAR-04 acceptance fixtures + jail/binary/dir/truncation/empty/duplicate edge cases"
      contains: "test_bundle_format\\|test_partial_result\\|test_duplicate_paths\\|test_empty_paths"
  key_links:
    - from: "voss/harness/tools.py:fs_read_many"
      to: "voss/harness/sandbox.py:jail_path"
      via: "per-path jail_path inside try/except SandboxError; violations become inline error envelopes"
      pattern: "jail_path\\(cwd"
    - from: "voss/harness/tools.py:fs_read_many"
      to: "voss/harness/tools.py:_read_one_for_bundle"
      via: "module-scope helper for per-slot read; mirrors _shell_capture pattern"
      pattern: "_read_one_for_bundle"
---

<objective>
Land `fs_read_many(paths)` — the bundled multi-file read primitive per
SPEC PAR-04. Returns one deterministic bundle string `=== {path} ===\n
{content_or_error}\n` per slot. Per-path errors are INLINE (the call
itself never aborts for a bad path). Each file capped at 30KB with the
existing `<truncated, total {N} bytes>` marker. Path jailing per slot;
jail violations become inline `<error: path outside cwd: ...>`. Empty
paths list returns `<no paths requested>` sentinel. Duplicates NOT
deduped (deterministic slot fill). Register with `is_mutating=False`
so the partition scheduler treats fs_read_many as parallelizable.

Purpose: SPEC PAR-04 + 4 acceptance criteria locked. CONTEXT.md D-12/D-13/D-14
lock the bundle format, 30KB cap, and per-path jail semantics. RESEARCH.md
Pattern 6 + Code Example 4 + Pitfall 6 fully spec the implementation.
PATTERNS.md identifies the exact analogs (fs_read error envelopes, shell_run
truncation marker).

This plan depends on T2-04 (Wave 3) because both modify `voss/harness/tools.py`
and same-wave file overlap forces sequential ordering. T2-04 ships the
make_toolset signature extension + fs_edit_many; T2-05 extends the same dict
with one more entry + the new fs_read_many tool body. No content conflict —
the two changes layer cleanly — but the planner respects the "zero
files_modified overlap per wave" invariant.

Output: fs_read_many tool + _read_one_for_bundle helper + registration;
4 SPEC acceptance fixtures + edge cases for truncation, jail, binary,
directory, missing, duplicate, and empty paths.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-RESEARCH.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-04-PLAN.md
@voss/harness/tools.py
@voss/harness/sandbox.py
</context>

<interfaces>
After T2-04 ships, `voss/harness/tools.py` has:
- make_toolset(cwd, *, renderer=None) signature
- fs_edit_many registered with is_mutating=True
- fs_edit unchanged

Existing fs_read pattern (voss/harness/tools.py:51-61) — error envelope source:
```
@tool(name="fs_read", description="Read a UTF-8 text file from the project. Path must be inside cwd.")
async def fs_read(path: str) -> str:
    p = jail_path(cwd, path)
    if not p.exists():
        return f"<error: not found: {path}>"
    if p.is_dir():
        return f"<error: is a directory: {path}>"
    try:
        return p.read_text()
    except UnicodeDecodeError:
        return f"<error: binary file: {path}>"
```

Existing truncation marker pattern (voss/harness/tools.py:96-97 — shell_run):
```
if len(text) > 4096:
    text = text[:4096] + f"\n<truncated, total {len(out)} bytes>"
```

Bundle format LOCKED (SPEC PAR-04 + D-12):
```
=== {path} ===
{content or error string}

=== {path} ===
{content or error string}
```
Each section is `=== {path} ===\n{body}\n`; sections joined by `\n`. Final
trailing newline behavior: the join produces a trailing `\n` after the last
section's body and no double newline at the very end (consistent with the
"\n".join pattern in RESEARCH.md Code Example 4).

Per-path size cap: 30720 bytes (30KB). When file content exceeds the cap,
truncate to 30720 bytes and append `\n<truncated, total {N} bytes>` where N
is the ORIGINAL byte length (mirror shell_run's "total" semantic — N is the
pre-truncation size, not the post-truncation size). LOCKED per D-13.

Jail violation handling differs from fs_edit_many: fs_read_many wraps
jail_path in try/except SandboxError to keep partial-result semantics
(other slots still readable). fs_edit_many (whole-call primitive) lets
SandboxError propagate.

Empty input: `paths=[]` → return the literal string `<no paths requested>`.
Single sentinel, not a bundle. LOCKED per SPEC PAR-04 acceptance fixture (d).

Duplicate behavior: `paths=["a.txt", "a.txt"]` → bundle with TWO sections,
both containing a.txt's content. NOT deduped. The "list of paths" abstraction
is positional, not set-like.

No is_mutating bit flip: fs_read_many is is_mutating=False, so the partition
scheduler in T2-03 may run it INSIDE a multi-step batch alongside other
reads (fs_read, fs_glob, fs_grep, git_status, git_diff, voss_check).
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: fs_read_many tool + _read_one_for_bundle helper + registration</name>
  <files>voss/harness/tools.py, tests/harness/tools/test_fs_read_many.py</files>
  <read_first>
    - .planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md (PAR-04 + 4 acceptance fixtures lines 48-58)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md (D-12, D-13, D-14)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-RESEARCH.md (Pattern 6, Code Example 4, Pitfall 6)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md (section "voss/harness/tools.py — fs_read_many")
    - voss/harness/tools.py (after T2-04 — locate make_toolset signature with renderer kwarg; fs_read at 51-61; shell_run truncation at 96-97; registration dict around 196-207)
    - voss/harness/sandbox.py (jail_path + SandboxError)
  </read_first>
  <behavior>
    HAPPY PATH (acceptance fixture a):
    - fs_read_many(paths=["a.txt", "b.txt", "c.txt"]) with all three files existing and readable:
        - Returns a bundle with 3 sections in REQUEST ORDER
        - Each section starts with "=== {path} ===\n"
        - Each section ends with "\n" before the next section's "===" header
        - Section bodies match the file contents byte-for-byte (unless capped)

    PARTIAL RESULT (acceptance fixture b):
    - paths=["a.txt", "missing.txt", "c.txt"] where "missing.txt" doesn't exist:
        - Returns a 3-section bundle (call does NOT raise)
        - Slot 1 (missing.txt) contains "<error: not found: missing.txt>"
        - Slots 0 and 2 contain real file contents
        - Section order preserved (request order, not failure-last)

    DUPLICATES (acceptance fixture c):
    - paths=["a.txt", "a.txt"]:
        - Bundle has 2 sections, both with a.txt's content
        - No dedup, no warning

    EMPTY PATHS (acceptance fixture d):
    - fs_read_many(paths=[]) returns the literal string `<no paths requested>`
    - NOT a bundle, no `=== ===` header

    SIZE CAP (D-13 — 30KB):
    - File with 100KB of UTF-8 text: bundle section contains the first 30720 bytes followed by `\n<truncated, total 102400 bytes>` (or whatever the original byte length is)
    - File with exactly 30720 bytes: NOT truncated (the cap is exclusive on equality — `if len(text) > 30720:`)
    - File with 30721 bytes: truncated

    JAIL VIOLATION (D-14):
    - paths=["valid.txt", "../../etc/passwd", "other.txt"]:
        - Bundle has 3 sections; slot 1 contains `<error: path outside cwd: ../../etc/passwd>`
        - Slots 0 and 2 readable normally
        - The call does NOT raise SandboxError (per-slot envelope per D-14)

    OTHER ERROR ENVELOPES (existing fs_read conventions):
    - Directory in paths list: slot contains `<error: is a directory: {path}>`
    - Binary file (UnicodeDecodeError): slot contains `<error: binary file: {path}>`
    - Missing file: slot contains `<error: not found: {path}>`

    REGISTRATION:
    - make_toolset()["fs_read_many"].is_mutating == False
    - make_toolset()["fs_read"].is_mutating == False (unchanged)

    DETERMINISM:
    - Two consecutive calls with the same paths list return byte-identical bundles (deterministic ordering, no caching surprises)
  </behavior>
  <action>
    Edit `voss/harness/tools.py`:

    1. Add `_read_one_for_bundle` helper at module scope (mirrors
       `_shell_capture` at line ~210 — module-level helper used by a tool
       function). Place it ABOVE `make_toolset` so it's importable for
       tests:
       ```
       def _read_one_for_bundle(cwd: Path, path: str) -> str:
           """Per-slot reader for fs_read_many. Never raises; returns content OR error envelope.

           - Jail violations -> '<error: path outside cwd: {path}>'
           - Missing -> '<error: not found: {path}>'
           - Directory -> '<error: is a directory: {path}>'
           - Binary -> '<error: binary file: {path}>'
           - Content over 30KB -> truncated with '<truncated, total {N} bytes>' suffix (N = original byte length)
           """
           try:
               p = jail_path(cwd, path)
           except SandboxError:
               return f"<error: path outside cwd: {path}>"
           if not p.exists():
               return f"<error: not found: {path}>"
           if p.is_dir():
               return f"<error: is a directory: {path}>"
           try:
               text = p.read_text()
           except UnicodeDecodeError:
               return f"<error: binary file: {path}>"
           if len(text) > 30720:  # 30KB cap (T2-CONTEXT.md D-13)
               text = text[:30720] + f"\n<truncated, total {len(text)} bytes>"
           return text
       ```

       Imports needed at module level: `from voss.harness.sandbox import jail_path, SandboxError` (if SandboxError isn't already imported alongside jail_path, add it). `Path` is already imported (line ~6).

    2. Add `fs_read_many` body INSIDE `make_toolset` (closes over cwd).
       Code shape (lift from PATTERNS.md "voss/harness/tools.py — fs_read_many"
       + RESEARCH.md Code Example 4):
       ```
       @tool(
           name="fs_read_many",
           description=(
               "Read N files as one bundle. Returns sections separated by "
               "`=== {path} ===`. Per-path errors are inline (other paths "
               "still readable). Each file capped at 30KB."
           ),
       )
       async def fs_read_many(paths: list[str]) -> str:
           if not paths:
               return "<no paths requested>"
           sections: list[str] = []
           for path in paths:
               body = _read_one_for_bundle(cwd, path)
               sections.append(f"=== {path} ===\n{body}\n")
           return "\n".join(sections)
       ```

    3. Add registration to the dict returned by make_toolset (alongside
       fs_read at the top of the returned dict for visual co-location):
       ```
       "fs_read_many": ToolEntry(descriptor=fs_read_many, is_mutating=False),
       ```

    Write `tests/harness/tools/test_fs_read_many.py` (the `tests/harness/
    tools/` directory should already exist from T2-04; reuse).

    Required tests (one per behavior bullet + acceptance fixtures):
    - test_three_readable_bundle_format (acceptance fixture a — 3 readable, request order, exact format)
    - test_missing_slot_inline_error (acceptance fixture b — 1 missing + 2 readable)
    - test_duplicate_paths_no_dedup (acceptance fixture c)
    - test_empty_paths_returns_sentinel (acceptance fixture d)
    - test_truncation_30kb (file > 30720 bytes truncated with marker)
    - test_exactly_30kb_not_truncated (boundary: len == 30720 NOT truncated)
    - test_just_over_30kb_truncated (boundary: len == 30721 IS truncated)
    - test_jail_violation_inline_error (path-outside-cwd in slot)
    - test_directory_inline_error
    - test_binary_file_inline_error
    - test_registered_with_is_mutating_false
    - test_fs_read_still_registered
    - test_deterministic_output (two consecutive calls produce byte-identical bundles)
    - test_bundle_format_exact (check the exact equals-sign pattern + newline pattern via regex or substring)

    Test scaffolding:
    - Use `tmp_path` to plant fixture files
    - For the "exact byte format" test, check that `result.startswith("=== a.txt ===\n")` and `"\n=== b.txt ===\n" in result` (or use a regex)
    - For truncation test, create a file with `tmp_path / "big.txt").write_text("x" * 50000)` (50KB of x's), call fs_read_many, then assert:
        * The bundle contains "x" repeated up to 30720 times in a row
        * The bundle contains `<truncated, total 50000 bytes>`
    - For jail violation test, use a path with `../../` traversal; assert the result has the inline error AND the file at the resolved location was NOT actually accessed (verify via path that doesn't exist)
    - For determinism, run fs_read_many twice with the same paths list and assert `result1 == result2` byte-for-byte

    fs_read_many is async, so tests need `async def test_*` (project has
    `asyncio_mode = "auto"`). Call directly via `await fs_read_many(paths=...)`
    where fs_read_many is obtained from `make_toolset(cwd)["fs_read_many"].invoke`.

    Do NOT modify fs_read. Do NOT touch shell_run's existing 4KB cap.
    Do NOT introduce a per-call total-bundle size cap (D-13 explicitly
    rejected the 100KB total cap; only per-file cap applies).
  </action>
  <verify>
    <automated>uv run pytest tests/harness/tools/test_fs_read_many.py -x -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "async def fs_read_many\|def _read_one_for_bundle" voss/harness/tools.py` returns 2 matches
    - source assertion: `grep -nE 'fs_read_many.*is_mutating=False' voss/harness/tools.py` returns 1 match
    - source assertion: `grep -n "fs_read\"" voss/harness/tools.py` shows fs_read still registered
    - source assertion: `grep -F "30720" voss/harness/tools.py` returns >= 1 match (the cap constant)
    - source assertion: `grep -F "<no paths requested>" voss/harness/tools.py` returns 1 match
    - source assertion: `grep -F "path outside cwd" voss/harness/tools.py` returns 1 match (D-14 envelope)
    - source assertion: `grep -F "=== {path} ===" voss/harness/tools.py` returns 1 match (bundle separator format) (use grep -F or escaped if shell quotes interfere)
    - registration assertion: `python -c "from voss.harness.tools import make_toolset; t = make_toolset('.'); print(t['fs_read_many'].is_mutating)"` prints `False`
    - acceptance-a assertion: pytest test_three_readable_bundle_format PASSES
    - acceptance-b assertion: pytest test_missing_slot_inline_error PASSES
    - acceptance-c assertion: pytest test_duplicate_paths_no_dedup PASSES
    - acceptance-d assertion: pytest test_empty_paths_returns_sentinel PASSES
    - truncation assertion: pytest test_truncation_30kb + test_exactly_30kb_not_truncated + test_just_over_30kb_truncated PASS
    - jail assertion: pytest test_jail_violation_inline_error PASSES
    - determinism assertion: pytest test_deterministic_output PASSES
    - regression assertion: `uv run pytest tests/harness/tools/ tests/harness/test_partition_scheduler.py -x -q` passes (no T2-03/T2-04 regression)
    - test command: `uv run pytest tests/harness/tools/test_fs_read_many.py -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>fs_read_many tool registered with is_mutating=False; _read_one_for_bundle helper at module scope; bundle format locked per D-12; 30KB cap per D-13 with shell_run-style truncation marker; jail-violation produces inline error envelope per D-14; empty paths returns sentinel; duplicates NOT deduped; 14+ tests cover SPEC acceptance + edge cases.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM-generated paths list → per-slot file reads | Each path is model-authored text; each must be jailed independently and any escape becomes an inline error envelope, not a propagated SandboxError |
| Bundle string → LLM context window | Per-file 30KB cap and truncation marker keep one greedy path from exhausting the model's context |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T2-05-01 | Information Disclosure | path-traversal slot escape leaks files outside cwd | mitigate | jail_path called per-slot inside try/except SandboxError; violations produce `<error: path outside cwd: {path}>` in that slot WITHOUT reading the resolved path (Pitfall 6 from RESEARCH.md); covered by test_jail_violation_inline_error which asserts the file at the resolved location was NOT accessed |
| T-T2-05-02 | Denial of Service | one greedy file fills model context | mitigate | Per-file 30KB cap (30720 bytes) with `<truncated, total {N} bytes>` marker; tested at boundaries (==30720, ==30721, >>30720); NO per-call total-bundle cap (deferred per D-13 — re-tune after benchmark) |
| T-T2-05-03 | Denial of Service | per-slot read raises and aborts the whole call | mitigate | _read_one_for_bundle wraps every IO path in try/except returning error envelope strings; the call body has zero raise sites; tested via test_missing_slot_inline_error and test_jail_violation_inline_error |
| T-T2-05-04 | Information Disclosure | binary file content (e.g., compiled secret) bytes leaked via UnicodeDecodeError fallback | mitigate | UnicodeDecodeError catches non-UTF-8 reads and returns `<error: binary file: {path}>` WITHOUT the raw bytes; covered by test_binary_file_inline_error |
| T-T2-05-05 | Tampering | duplicate paths leveraged for cache-busting attack on slow disks | accept | Duplicate fills are deterministic per the request list; no caching mechanism; "no dedup" is a deliberate spec decision (positional API); not a security threat in current scope |
| T-T2-05-SC | Tampering | npm/pip/cargo installs | accept | No new third-party packages (RESEARCH.md "Package Legitimacy Audit" — none) |
</threat_model>

<verification>
- `uv run pytest tests/harness/tools/test_fs_read_many.py -x -q` passes
- `grep -n "async def fs_read_many\|def _read_one_for_bundle" voss/harness/tools.py` returns 2 matches
- make_toolset returns fs_read_many with is_mutating=False
- 4 SPEC PAR-04 acceptance fixtures all pass
- Truncation at exactly the 30720-byte boundary tested
- Jail violation produces inline error without aborting the call
- Empty paths returns the sentinel
- Duplicates fill both slots deterministically
- No T2-03/T2-04 regression
</verification>

<success_criteria>
- fs_read_many registered with is_mutating=False (PAR-04 acceptance: appears in make_toolset)
- Acceptance fixture a: 3 readable paths → bundle with 3 sections in request order
- Acceptance fixture b: 1 missing + 2 readable → 3-section bundle with inline `<error: not found: ...>` in slot 1
- Acceptance fixture c: duplicate paths → both slots filled, no dedup
- Acceptance fixture d: empty paths → `<no paths requested>` sentinel
- 30KB cap enforced with shell_run-style truncation marker (D-13)
- Per-path jail check produces inline envelope (D-14)
- fs_read preserved unchanged
</success_criteria>

<output>
Create `.planning/phases/T2-parallel-tools-multi-edit/T2-05-SUMMARY.md` when done with: line numbers of fs_read_many definition + _read_one_for_bundle helper + registration; explicit bundle-format byte sample from a test fixture; pytest output showing all 14+ tests passing.
</output>
