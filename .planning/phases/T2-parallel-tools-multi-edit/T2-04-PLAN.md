---
phase: T2-parallel-tools-multi-edit
plan: 04
type: execute
wave: 3
depends_on: [T2-03]
files_modified:
  - voss/harness/tools.py
  - tests/harness/tools/test_fs_edit_many.py
autonomous: true
requirements: [PAR-03]
must_haves:
  truths:
    - "New tool fs_edit_many(path: str, edits: list[dict]) -> str is registered in make_toolset with is_mutating=True"
    - "Validation phase reads the file once into a snapshot string, walks edits left-to-right, validates each `old` matches uniquely in the CURRENT working buffer (not the original snapshot); on any failure aborts before showing the modal"
    - "On any validation failure, the tool returns `<error: batch rejected at index {i}: {reason}>` and the file is byte-for-byte unchanged on disk"
    - "On all-edits-pass, the tool builds list[Hunk] (one Hunk per edit), calls renderer.show_diff_modal(hunks, timeout_s=300.0), and inspects the returned DiffDecision list"
    - "Any hunk decision == 'reject' returns `<denied: hunk N rejected>` and writes nothing (atomicity invariant)"
    - "Any hunk decision == 'skip' is treated as STRICT REJECTION (resolves RESEARCH.md Open Question 1 per the recommendation: skip → batch denied)"
    - "Empty decisions list (modal cancelled or timed out) returns `<denied: modal cancelled or timed out>` and writes nothing"
    - "On all-accept, the tool writes the buffer once to disk and returns `edited {path} ({sign}{delta} lines, {n} hunks)`"
    - "fs_edit (the single-edit tool) is preserved unchanged per D-10 — both fs_edit and fs_edit_many register"
    - "make_toolset signature extends to make_toolset(cwd, *, renderer=None); fs_edit_many uses the closure-captured renderer; when renderer is None (test mode without TUI), the modal step is skipped and the tool writes after validation"
    - "PermissionGate.check fires ONCE for the whole fs_edit_many call (per SPEC PAR-03); per-hunk approval lives inside the modal, not the gate (D-01)"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "fs_edit_many @tool decorated function + ToolEntry(descriptor=fs_edit_many, is_mutating=True) registration in make_toolset"
      contains: "def fs_edit_many\\|fs_edit_many.*is_mutating=True"
    - path: "voss/harness/tools.py"
      provides: "make_toolset signature extended with renderer kwarg threaded into fs_edit_many closure"
      contains: "renderer=None"
    - path: "tests/harness/tools/test_fs_edit_many.py"
      provides: "4 SPEC PAR-03 acceptance fixtures: all-pass / non-unique / not-found / modal-reject + additional skip/cancelled/binary/missing-file/dir/empty-old edge cases"
      contains: "test_all_match_writes\\|test_ambiguous_rejected\\|test_missing_rejected\\|test_modal_reject_denies"
  key_links:
    - from: "voss/harness/tools.py:fs_edit_many"
      to: "voss/harness/tui/renderer.py:Renderer.show_diff_modal"
      via: "renderer.show_diff_modal(hunks, timeout_s=300.0) when renderer is not None"
      pattern: "show_diff_modal\\(.*hunks"
    - from: "voss/harness/tools.py:fs_edit_many"
      to: "voss/harness/tui/widgets/diff_modal.py:Hunk"
      via: "constructs list[Hunk] from validated edits (one Hunk per edit)"
      pattern: "Hunk\\(file="
    - from: "voss/harness/tools.py:fs_edit_many"
      to: "voss/harness/sandbox.py:jail_path"
      via: "path argument runs through jail_path(cwd, path) before file IO"
      pattern: "jail_path\\(cwd"
---

<objective>
Land `fs_edit_many(path, edits=[{old, new}, ...])` — the atomic single-file
multi-edit primitive per SPEC PAR-03. Validate-then-write-once semantics:
read snapshot, walk edits left-to-right against the working buffer, abort
the entire batch on any uniqueness or not-found failure (file unchanged),
build list[Hunk] from validated edits, show the M9-05 DiffModal, treat any
"reject" or "skip" decision as batch denial (atomicity invariant), and on
all-accept write the buffer once. Register with `is_mutating=True`. Keep
`fs_edit` registered alongside per D-10.

Purpose: SPEC PAR-03 + 4 acceptance criteria locked. CONTEXT.md D-01/D-02/D-03
lock the modal wiring (tool owns its UX surface; PermissionGate stays narrow).
RESEARCH.md Open Question 1 ("skip" semantics) is resolved HERE per the
research recommendation: STRICT (skip → batch denied). Rationale: atomicity
invariant favors safety; if the user wanted per-hunk acceptance they would
have called fs_edit per hunk.

This plan depends on T2-03 (Wave 2): the scheduler must dispatch the new
mutating tool as a singleton (NOT inside a multi-step batch — partition
classifier already excludes it via is_mutating=True). T2-03 also delivers
the BatchInvariantError safety net if a future bug ever mis-classifies it.

Output: fs_edit_many tool + registration; 4 SPEC acceptance fixtures + edge
case coverage; documentation of the skip-is-strict decision in the SUMMARY.
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
@.planning/phases/T2-parallel-tools-multi-edit/T2-03-PLAN.md
@voss/harness/tools.py
@voss/harness/tui/widgets/diff_modal.py
@voss/harness/tui/renderer.py
@voss/harness/sandbox.py
</context>

<interfaces>
Existing single-edit pattern (voss/harness/tools.py:107-128, copy as analog):
```
@tool(
    name="fs_edit",
    description=(
        "Replace exact `old` text with `new` in a file. `old` must appear "
        "exactly once. Returns line count delta."
    ),
)
async def fs_edit(path: str, old: str, new: str) -> str:
    p = jail_path(cwd, path)
    if not p.exists():
        return f"<error: not found: {path}>"
    text = p.read_text()
    count = text.count(old)
    if count == 0:
        return f"<error: `old` not found in {path}>"
    if count > 1:
        return f"<error: `old` matches {count} times, must be unique>"
    new_text = text.replace(old, new, 1)
    p.write_text(new_text)
    delta = new_text.count("\n") - text.count("\n")
    sign = "+" if delta >= 0 else ""
    return f"edited {path} ({sign}{delta} lines)"
```

Hunk/DiffDecision shapes (voss/harness/tui/widgets/diff_modal.py:21-32):
```
@dataclass(frozen=True)
class Hunk:
    file: str
    start: int
    lines: list[str]

@dataclass(frozen=True)
class DiffDecision:
    file: str
    decision: str  # 'accept' | 'reject' | 'skip'
```

Modal call surface (voss/harness/tui/renderer.py:306-323):
```
def show_diff_modal(self, hunks: list[Hunk], *, timeout_s: float = 300.0) -> list[DiffDecision]:
    # Blocks on a Future; returns [] on cancel/timeout.
```

make_toolset current signature (voss/harness/tools.py:44): `def make_toolset(cwd) -> dict[str, ToolEntry]:`

EXTENSION: make_toolset(cwd, *, renderer=None) — keyword-only renderer
default None. fs_edit_many's body uses the closure-captured renderer; when
None, the modal step is skipped (test-friendly path; the tool still
performs validation + write but bypasses UI confirmation). Production
callers of make_toolset get renderer=renderer via the agent.py construction
site. Locate call sites: `grep -rn "make_toolset(" voss/ voss_runtime/ tests/`
and update each.

Skip-decision semantics LOCKED HERE: skip → batch denied (STRICT, per
RESEARCH.md Open Question 1 recommendation). Document in SUMMARY. The
inner loop in fs_edit_many: `if d.decision in ("reject", "skip"):`
returns the deny path.

The PermissionGate is unmodified — it fires once per step (the whole
fs_edit_many call IS one step from the gate's POV). The modal is an
ADDITIONAL UI layer inside the tool function, NOT a gate concern (D-01).
`PermissionGate._render_diff_preview` stays single-edit-only (no extension
to recognize the edits list).
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: fs_edit_many tool + registration + make_toolset signature extension</name>
  <files>voss/harness/tools.py, tests/harness/tools/test_fs_edit_many.py</files>
  <read_first>
    - .planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md (PAR-03 + 4 acceptance fixtures lines 39-46)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md (D-01, D-02, D-03, D-10)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-RESEARCH.md (Pattern 4, Pattern 5, Code Example 3, Pitfall 5, Open Question 1)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md (section "voss/harness/tools.py — fs_edit_many")
    - voss/harness/tools.py (entire file — lines 44-207; locate make_toolset signature, fs_edit at line 107-128, the registration dict at line 196-207)
    - voss/harness/tui/widgets/diff_modal.py (Hunk + DiffDecision dataclasses at lines 21-32; DiffModal class at line 34 for context)
    - voss/harness/tui/renderer.py (show_diff_modal at line 306)
    - voss/harness/sandbox.py (jail_path at line 29-40; SandboxError at line 25)
    - tests/harness/tools/ directory (look for existing tool tests; otherwise create dir + __init__.py)
  </read_first>
  <behavior>
    HAPPY PATH:
    - fs_edit_many(path="foo.py", edits=[{"old":"a","new":"x"}, {"old":"b","new":"y"}, {"old":"c","new":"z"}]) where all three `old` strings appear exactly once each AND modal returns [accept, accept, accept]:
        - File written ONCE with all 3 replacements applied
        - Return string contains "edited foo.py" + line delta in format "(+N lines, 3 hunks)" or "(-N lines, 3 hunks)" or "(+0 lines, 3 hunks)"
        - File mtime is touched (verify single write via os.stat before+after)

    UNIQUENESS REJECTION (acceptance fixture b):
    - edits=[{"old":"a","new":"x"}, {"old":"FOO","new":"BAR"}, {"old":"c","new":"z"}] where "FOO" appears twice in the file:
        - Return `<error: batch rejected at index 1: \`old\` matches 2 times>` (offending index = 1)
        - File byte-for-byte unchanged on disk (compare via Path.read_text() before+after)
        - Modal NEVER shown (verify via a Recording renderer with show_diff_modal call counter == 0)

    NOT-FOUND REJECTION (acceptance fixture c):
    - edits=[{"old":"a","new":"x"}, {"old":"b","new":"y"}, {"old":"NOPE","new":"z"}] where "NOPE" doesn't appear:
        - Return `<error: batch rejected at index 2: \`old\` not found>`
        - File unchanged
        - Modal not shown

    MODAL REJECTION (acceptance fixture d):
    - All 3 edits validate. Renderer's show_diff_modal returns [accept, reject, accept]:
        - Return `<denied: hunk 1 rejected>`
        - File unchanged
        - Modal called exactly once

    SKIP REJECTION (RESEARCH.md Open Question 1 — STRICT):
    - All 3 edits validate. show_diff_modal returns [accept, skip, accept]:
        - Return `<denied: hunk 1 rejected>` (skip treated identically to reject)
        - File unchanged

    MODAL CANCELLATION:
    - All 3 edits validate. show_diff_modal returns [] (empty list — modal cancelled or timed out):
        - Return `<denied: modal cancelled or timed out>`
        - File unchanged

    LEFT-TO-RIGHT BUFFER PROPAGATION (Pitfall 5):
    - edits=[{"old":"FooBar","new":"BarBaz"}, {"old":"BarBaz","new":"Done"}] where "FooBar" appears once and "BarBaz" originally appears ZERO times but appears ONCE after edit #1:
        - Both edits validate (against the working buffer, not the snapshot)
        - File written with final content reflecting "Done" (transitive replacement)
        - Return reports 2 hunks applied

    EDGE: edit #2 ambiguity AFTER edit #1:
    - edits=[{"old":"x","new":"y"}, {"old":"y","new":"z"}] where the original file has 0 occurrences of "y" but 1 of "x", AND the file has 1 existing "y" elsewhere:
        - After edit #1 the working buffer has TWO "y" occurrences (the original + the new one from x→y)
        - edit #2 fails uniqueness against the working buffer
        - Return `<error: batch rejected at index 1: \`old\` matches 2 times>`
        - File unchanged (no partial write)

    EMPTY EDITS LIST:
    - fs_edit_many(path, edits=[]) returns either a friendly empty message OR errors at index 0 with "empty edits list" — pick STRICT: return `<error: empty edits list>` and do not write/modal

    EMPTY OLD STRING:
    - edits=[{"old":"","new":"x"}] returns `<error: batch rejected at index 0: empty \`old\`>` (defends against accidental no-op edits matching everywhere)

    MISSING / DIR / BINARY:
    - Non-existent path: `<error: not found: {path}>`
    - Directory path: `<error: is a directory: {path}>`
    - Binary file (UnicodeDecodeError): `<error: binary file: {path}>`

    JAIL VIOLATION:
    - Path outside cwd (e.g., "../../etc/passwd"): jail_path raises SandboxError; the error propagates (fs_edit_many does NOT swallow into a slot like fs_read_many does — single-file primitive, whole-call failure)

    is_mutating REGISTRATION:
    - make_toolset()["fs_edit_many"].is_mutating == True
    - make_toolset()["fs_edit"].is_mutating == True (preserved, not removed per D-10)
    - Both tools coexist in the returned dict

    RENDERER=None TEST PATH:
    - fs_edit_many called via a tools dict produced by make_toolset(cwd, renderer=None) bypasses the modal step entirely; on all-edits-pass it writes the file directly. This is the test-friendly path; the modal is the production UI layer.
  </behavior>
  <action>
    Edit `voss/harness/tools.py`:

    1. Imports: add `Hunk` and `DiffDecision` from
       `voss.harness.tui.widgets.diff_modal` near the top (after the
       existing tool/sandbox imports). Add `SandboxError` from
       `voss.harness.sandbox` if not already imported.

    2. Extend `make_toolset` signature:
       ```
       def make_toolset(cwd, *, renderer=None) -> dict[str, ToolEntry]:
       ```
       The `renderer` kwarg is captured by the inner @tool-decorated
       closures. Document via docstring: "When renderer is None, fs_edit_many
       skips the diff modal (test-friendly path); production callers pass
       the agent's Renderer instance."

    3. Add `fs_edit_many` body INSIDE `make_toolset` (so it closes over
       cwd and renderer). Code shape (lift from PATTERNS.md "voss/harness/
       tools.py — fs_edit_many" + RESEARCH.md Code Example 3, with the
       skip→deny semantics LOCKED here):

       ```
       @tool(
           name="fs_edit_many",
           description=(
               "Atomically apply N edits to one file. Each `edits` entry is "
               "{old, new}; each `old` must match uniquely in the working "
               "buffer (left-to-right). Routes through the diff modal with "
               "one Hunk per edit. Rejecting OR skipping any hunk cancels "
               "the whole batch — file unchanged on disk."
           ),
       )
       async def fs_edit_many(path: str, edits: list[dict]) -> str:
           if not edits:
               return "<error: empty edits list>"
           p = jail_path(cwd, path)
           if not p.exists():
               return f"<error: not found: {path}>"
           if p.is_dir():
               return f"<error: is a directory: {path}>"
           try:
               snapshot = p.read_text()
           except UnicodeDecodeError:
               return f"<error: binary file: {path}>"

           # Phase 1: validate-then-build hunks against the current working buffer.
           buf = snapshot
           hunks: list[Hunk] = []
           for i, e in enumerate(edits):
               old, new = e.get("old", ""), e.get("new", "")
               if not old:
                   return f"<error: batch rejected at index {i}: empty `old`>"
               count = buf.count(old)
               if count == 0:
                   return f"<error: batch rejected at index {i}: `old` not found>"
               if count > 1:
                   return f"<error: batch rejected at index {i}: `old` matches {count} times>"
               idx = buf.find(old)
               line_start = buf.count("\n", 0, idx) + 1
               old_lines = [f"- {l}" for l in (old.splitlines() or [""])]
               new_lines = [f"+ {l}" for l in (new.splitlines() or [""])]
               hunks.append(Hunk(file=path, start=line_start, lines=old_lines + new_lines))
               buf = buf[:idx] + new + buf[idx + len(old):]

           # Phase 2: show modal (skipped when renderer is None — test mode).
           if renderer is not None:
               decisions = renderer.show_diff_modal(hunks, timeout_s=300.0)
               if not decisions:
                   return "<denied: modal cancelled or timed out>"
               for i, d in enumerate(decisions):
                   # STRICT semantics: skip is treated as reject (resolves
                   # RESEARCH.md Open Question 1 per the recommendation).
                   if d.decision in ("reject", "skip"):
                       return f"<denied: hunk {i} rejected>"

           # Phase 3: atomic write.
           p.write_text(buf)
           delta = buf.count("\n") - snapshot.count("\n")
           sign = "+" if delta >= 0 else ""
           return f"edited {path} ({sign}{delta} lines, {len(edits)} hunks)"
       ```

    4. Add registration to the dict returned by make_toolset (after the
       existing fs_edit entry at line ~200):
       ```
       "fs_edit_many": ToolEntry(descriptor=fs_edit_many, is_mutating=True),
       ```
       fs_edit registration REMAINS in place (D-10: both tools coexist).

    5. Update every call site of `make_toolset(`. Locate via:
       `grep -rn "make_toolset(" voss/ voss_runtime/ tests/`
       Each production call should pass `renderer=renderer` (the agent's
       Renderer instance) using the new keyword-only signature. Test
       call sites can omit renderer (default None).

    Write `tests/harness/tools/test_fs_edit_many.py` (create the
    `tests/harness/tools/` directory + empty `__init__.py` if missing).

    Required test fixtures (one test function per behavior bullet — 16+ tests):
    - test_all_match_writes (acceptance fixture a)
    - test_ambiguous_rejected (acceptance fixture b)
    - test_missing_rejected (acceptance fixture c)
    - test_modal_reject_denies (acceptance fixture d)
    - test_modal_skip_denies_strict (Open Question 1 resolution)
    - test_modal_cancelled_empty_denies (empty decisions list)
    - test_buffer_propagation_left_to_right (transitive replacement)
    - test_buffer_propagation_creates_new_ambiguity (edit #1 makes edit #2 ambiguous)
    - test_empty_edits_list
    - test_empty_old_string
    - test_not_found
    - test_is_directory
    - test_binary_file
    - test_jail_violation_raises (use pytest.raises(SandboxError))
    - test_registered_with_is_mutating_true (assert ToolEntry shape)
    - test_fs_edit_still_registered (D-10 — both coexist)
    - test_renderer_none_skips_modal (test-friendly path)

    Test scaffolding: use a FakeRenderer pattern from PATTERNS.md section
    "tests/harness/test_fs_edit_many.py (NEW)":
    ```
    class _FakeRenderer:
        def __init__(self, decisions): self._decisions = decisions; self.call_count = 0
        def show_diff_modal(self, hunks, *, timeout_s=300.0):
            self.call_count += 1
            return self._decisions
        def show_tool_call(self, *a, **kw): pass  # no-op
    ```

    Use `tmp_path` for fixture files. For the "file unchanged on disk"
    assertions, capture `Path.read_bytes()` (NOT read_text — catches
    encoding round-trips) before the call and assert equality after.
    Also use `os.stat(p).st_mtime_ns` to confirm the file wasn't touched
    when rejection occurs (write OR rejection both touch the snapshot
    read; the assertion is on file content, not mtime).

    Build hunks-list assertion: capture the hunks argument passed to
    show_diff_modal via a Recording renderer. Assert len(hunks) ==
    len(edits) on the happy path; assert each Hunk has file=path,
    start=line_number (positive int), lines containing "- " and "+ "
    prefixed lines.

    Do NOT modify fs_edit. Do NOT modify PermissionGate or its
    _render_diff_preview. Do NOT modify DiffModal or show_diff_modal.
    Do NOT introduce a multi-file edits variant (single-file per call
    only per SPEC Boundaries).
  </action>
  <verify>
    <automated>uv run pytest tests/harness/tools/test_fs_edit_many.py -x -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "async def fs_edit_many" voss/harness/tools.py` returns 1 match
    - source assertion: `grep -nE 'fs_edit_many.*is_mutating=True' voss/harness/tools.py` returns 1 match (registration line)
    - source assertion: `grep -n "fs_edit\"" voss/harness/tools.py | head` shows fs_edit still registered (D-10 preservation)
    - source assertion: `grep -n "renderer=None" voss/harness/tools.py` returns >= 1 match (make_toolset signature)
    - source assertion: `grep -n 'd.decision in ("reject", "skip")' voss/harness/tools.py` returns 1 match (skip-is-strict locked)
    - source assertion: `grep -F "batch rejected at index" voss/harness/tools.py` returns >= 3 matches (empty/not-found/non-unique error envelopes)
    - source assertion: `grep -F "denied: hunk" voss/harness/tools.py` returns 1 match
    - source assertion: `grep -F "denied: modal cancelled" voss/harness/tools.py` returns 1 match
    - registration assertion: `python -c "from voss.harness.tools import make_toolset; t = make_toolset('.'); print(t['fs_edit_many'].is_mutating, t['fs_edit'].is_mutating)"` prints `True True`
    - acceptance-fixture-a assertion: pytest test_all_match_writes PASSES (3 edits, all-pass, file written once, return string contains "hunks")
    - acceptance-fixture-b assertion: pytest test_ambiguous_rejected PASSES (file unchanged byte-for-byte, error names index 1)
    - acceptance-fixture-c assertion: pytest test_missing_rejected PASSES (file unchanged, error names index 2)
    - acceptance-fixture-d assertion: pytest test_modal_reject_denies PASSES (file unchanged, return "<denied: hunk 1 rejected>")
    - skip-strict assertion: pytest test_modal_skip_denies_strict PASSES
    - propagation assertion: pytest test_buffer_propagation_left_to_right PASSES (transitive replacement works)
    - propagation-ambiguity assertion: pytest test_buffer_propagation_creates_new_ambiguity PASSES (edit #1 making edit #2 ambiguous correctly rejects)
    - regression assertion: `uv run pytest tests/harness/tools/ tests/harness/test_partition_scheduler.py -x -q` passes (no T2-03 regression; new tools dir test-discoverable)
    - test command: `uv run pytest tests/harness/tools/test_fs_edit_many.py -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>fs_edit_many tool registered with is_mutating=True; both fs_edit and fs_edit_many coexist (D-10); validate-then-write-once atomicity; left-to-right working-buffer propagation; skip-is-strict locked (Open Question 1 resolved); make_toolset(cwd, *, renderer=None) signature; all production make_toolset call sites updated; 16+ test fixtures cover SPEC acceptance + edge cases.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM-generated `edits` list-of-dicts → on-disk file mutation | Each edit's `old` and `new` strings are model-authored text; the tool must validate uniqueness, jail the path, and pass through the human-approved diff modal before any disk write |
| renderer.show_diff_modal verdict → atomic batch outcome | Modal returns per-hunk decisions; any reject/skip cancels the entire batch (atomicity invariant); empty result (cancel/timeout) cancels too |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T2-04-01 | Tampering | partial write on mid-batch validation failure | mitigate | Validate ALL edits against working buffer BEFORE any disk write (Phase 1/2/3 separation in body); file only written in Phase 3 after all edits validate AND modal accepts all hunks; tests `test_ambiguous_rejected` / `test_missing_rejected` assert file byte-for-byte unchanged after rejection |
| T-T2-04-02 | Tampering | path-jail bypass via malformed path | mitigate | `jail_path(cwd, path)` called once at function entry; SandboxError propagates (whole-call failure for single-file primitive); tested via test_jail_violation_raises |
| T-T2-04-03 | Spoofing | model bypasses diff modal by relying on renderer=None test path | mitigate | renderer=None is ONLY accessible to in-process test callers (make_toolset(renderer=None)); production agent.py always passes renderer=renderer; the LLM agent NEVER controls the make_toolset kwarg |
| T-T2-04-04 | Repudiation | modal "skip" decision interpreted permissively allows surprise writes | mitigate | LOCKED: skip → batch denied (STRICT per RESEARCH.md Open Question 1 recommendation); explicit `d.decision in ("reject", "skip")` test in body; covered by test_modal_skip_denies_strict |
| T-T2-04-05 | Tampering | left-to-right buffer drift makes edit #N validate against the wrong text | mitigate | Pitfall 5 — validation uses the propagated `buf` variable (not the original `snapshot`); tested via test_buffer_propagation_creates_new_ambiguity which plants an edit that becomes ambiguous after a prior edit and asserts rejection |
| T-T2-04-06 | Information Disclosure | edits list args leaked unredacted in tool.call telemetry | mitigate | Existing `telemetry.redact_tool_args` covers `old`/`new` keys; if redaction doesn't recurse into list-of-dicts, RESEARCH.md "Redaction" section flags this for follow-up — verify during execution via a redaction unit test on `redact_tool_args({"edits": [{"old": "secret", "new": "x"}]})` and extend redaction if the secret leaks |
| T-T2-04-SC | Tampering | npm/pip/cargo installs | accept | No new third-party packages in this plan (RESEARCH.md "Package Legitimacy Audit" — none) |
</threat_model>

<verification>
- `uv run pytest tests/harness/tools/test_fs_edit_many.py -x -q` passes
- `grep -n "async def fs_edit_many" voss/harness/tools.py` returns 1 match
- `grep -n 'd.decision in ("reject", "skip")' voss/harness/tools.py` returns 1 match
- make_toolset returns both fs_edit and fs_edit_many with correct is_mutating flags
- 4 SPEC PAR-03 acceptance fixtures (a/b/c/d) all pass
- Skip-is-strict locked + tested
- Left-to-right buffer propagation tested (transitive + ambiguity-creation cases)
- File byte-for-byte unchanged on every rejection path
- jail violation propagates SandboxError
- No T2-03 regression in partition scheduler tests
</verification>

<success_criteria>
- fs_edit_many registered with is_mutating=True (PAR-03 acceptance: tool appears in make_toolset)
- Acceptance fixture a (all-pass): file written once with 3 edits applied; return reports line delta + hunks count
- Acceptance fixture b (non-unique): batch rejected, file unchanged, error names offending index
- Acceptance fixture c (not-found): batch rejected, file unchanged, error names offending index
- Acceptance fixture d (modal reject): batch denied, file unchanged
- Bonus: skip-is-strict semantics locked + tested (Open Question 1 resolved)
- fs_edit preserved unchanged (D-10)
- make_toolset(cwd, *, renderer=None) signature; production call sites updated
</success_criteria>

<output>
Create `.planning/phases/T2-parallel-tools-multi-edit/T2-04-SUMMARY.md` when done with: line numbers of fs_edit_many definition + registration + make_toolset signature change; ALL call sites of make_toolset and their renderer kwarg state; explicit documentation that skip-is-strict resolves RESEARCH.md Open Question 1; pytest output showing all 16+ tests passing; any redaction follow-up noted.
</output>
