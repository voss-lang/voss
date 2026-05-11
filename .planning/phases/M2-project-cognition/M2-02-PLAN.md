---
phase: M2
plan: 02
type: execute
wave: 1
depends_on: [M1, M2-00]
files_modified:
  - voss/harness/session.py
  - voss/harness/recorder.py
  - voss/harness/cli.py
  - tests/harness/test_session.py
  - tests/harness/test_session_redaction.py
  - tests/harness/test_recorder.py
autonomous: true
requirements:
  - COG-05
  - COG-08
tags:
  - harness
  - session
  - recorder
  - redaction

must_haves:
  truths:
    - "New sessions write to <cwd>/.voss/sessions/<id>.json — never to the legacy XDG path (D-10 hard cut)."
    - "list_sessions(cwd, include_legacy=False) returns only sessions whose JSON file lives under <cwd>/.voss/sessions; passing include_legacy=True also reads the legacy XDG dir read-only and tags each with _legacy=True."
    - "load(session_id_or_name, cwd) resolves first under the per-cwd dir then falls back to the legacy dir."
    - "Legacy sessions missing the runs field deserialize cleanly with runs=[]."
    - "RunRecord is a 16-field dataclass; asdict(run) has exactly those top-level keys; redaction CI test scans every RunRecord field for the six secret patterns."
    - "RunRecorder.observe captures inspected/changed/validation/failures from the M1 tool set; finalize(cwd, cost_usd) produces a RunRecord with diff_summary populated from `git diff --stat`."
  artifacts:
    - path: "voss/harness/session.py"
      provides: "_sessions_dir(cwd), _legacy_state_dir(), updated save/load/list_sessions/delete; SessionRecord.runs field; RunRecord dataclass; redaction-guarantee docstring extended"
      contains: "class RunRecord"
    - path: "voss/harness/recorder.py"
      provides: "RunRecorder dataclass with start()/observe()/absorb()/finalize() + INSPECT_TOOLS/CHANGE_TOOLS/VALIDATE_TOOLS sets"
      contains: "class RunRecorder"
    - path: "tests/harness/test_session.py"
      provides: "tests for per-cwd path, legacy fallback, legacy never written, runs backward-compat"
      contains: "def test_save_writes_per_cwd_path"
    - path: "tests/harness/test_session_redaction.py"
      provides: "extended pattern scan covers RunRecord fields + top-level keys allowlist for RunRecord"
      contains: "def test_run_record_no_secret_patterns"
    - path: "tests/harness/test_recorder.py"
      provides: "5 Wave-1 tests for mechanical capture (inspect/change/validation/failure/diff_summary)"
      contains: "def test_inspect_captures_fs_read"
  key_links:
    - from: "voss/harness/session.py::save"
      to: "<cwd>/.voss/sessions/"
      via: "_sessions_dir(Path(record.cwd))"
      pattern: "\\.voss/sessions"
    - from: "voss/harness/recorder.py::RunRecorder.finalize"
      to: "git diff --stat"
      via: "subprocess wrapped in try/except"
      pattern: "git.*diff.*--stat"
    - from: "tests/harness/test_session_redaction.py"
      to: "RunRecord field values"
      via: "json.dumps(asdict(rec)) full-text scan for 6 patterns"
      pattern: "sk-ant-\\|sk-proj-\\|Bearer \\|oauth_token\\|access_token\\|Authorization"
---

<objective>
Migrate session storage to per-cwd `.voss/sessions/` with a read-only legacy fallback (COG-05 hard cut, D-10/D-11/D-12), introduce the `RunRecord` dataclass + `RunRecorder` collaborator that captures the mechanical half of COG-08 from tool observations, and extend the M1 redaction CI test (D-17) to cover every RunRecord field plus a top-level allowlist assertion.

Purpose: M1-03 froze the redaction guarantee for `SessionRecord`. M2 widens the surface to include `runs: list[RunRecord]` per turn — same guarantee must extend cleanly or the contract is silently broken. Per-cwd session storage and the recorder are the two structural changes that everything else in M2 (auto-injection, /analyze post-turn write, decisions mirror) sits on top of. Wave 1 ships them with mechanical-only behavior; the semantic half (record_run privileged closing call + decisions/*.md mirror) lands in M2-03.

Output:
- `voss/harness/session.py` — `_sessions_dir(cwd)` + `_legacy_state_dir()` split, updated save/load/list_sessions/delete signatures, `RunRecord` dataclass, `SessionRecord.runs` field, extended docstring.
- `voss/harness/recorder.py` — `RunRecorder` collaborator with mechanical observation.
- `tests/harness/test_session.py` extended with 6 new tests for COG-05.
- `tests/harness/test_session_redaction.py` extended with `test_run_record_top_level_keys` and `test_run_record_no_secret_patterns`.
- `tests/harness/test_recorder.py` — 5 Wave-1 tests flipped from skip to live.

NOTE: RunRecorder semantic-field population via `record_run` privileged closing call is OUT of scope for this plan; it lands in M2-03. This plan defines `RunRecorder.absorb(semantics, plan)` as a stub that simply assigns fields; M2-03 wires the actual provider call.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M2-project-cognition/M2-CONTEXT.md
@.planning/phases/M2-project-cognition/M2-RESEARCH.md
@.planning/phases/M2-project-cognition/M2-PATTERNS.md
@.planning/phases/M1-harness-happy-path/M1-03-PLAN.md
@voss/harness/session.py
@voss/harness/permissions.py
@voss/harness/tools.py
@tests/harness/test_session.py
@tests/harness/test_session_redaction.py

<interfaces>
Current voss/harness/session.py public surface (must preserve all callers):
    SessionRecord (dataclass with 8 fields), .new(cwd, model, name="") classmethod, .first_task()
    session_path(session_id: str) -> Path           # CHANGES — now needs cwd
    save(record: SessionRecord, history: EpisodicMemory) -> Path
    load(session_id_or_name: str) -> tuple[SessionRecord, EpisodicMemory]   # CHANGES — adds optional cwd
    list_sessions() -> list[SessionRecord]          # CHANGES — adds (cwd, *, include_legacy=False)
    delete(session_id: str) -> bool

Callers to update (find via grep):
    voss/harness/cli.py: chat_cmd (line 220) creates SessionRecord; sessions_cmd (line 389) calls list_sessions; resume_cmd (line 425) calls load
    voss/harness/cli.py _run_repl saves via session_store.save(record, history)
    tests/harness/test_session.py — entire file
    tests/harness/test_session_redaction.py — fixture state_dir

From M1-03 plan §interfaces:
    SessionRecord fields: id, name, cwd, model, started_at, updated_at, total_cost_usd, turns
    M2 adds: runs (list[dict], default_factory=list)

RunRecord schema (D-14, 16 declared keys — authoritative count):
    id, started_at, ended_at, goal, plan, inspected, changed, avoided,
    assumptions, decisions, risks, validation, failures, diff_summary,
    follow_ups, cost_usd
    Exactly 16 fields. The redaction test must assert len(dataclasses.fields(RunRecord)) == 16.

From M1-03 secret patterns (D-17):
    ("sk-ant-", "sk-proj-", "Bearer ", "oauth_token", "access_token", "Authorization")
    NOT "sk-" (too broad — would match user prompts like "sk-test-...").

From voss/harness/tools.py:58 — shell_run result format:
    f"[exit {proc.returncode}]\n{text}"
    RunRecorder._parse_exit(result) must read "[exit N]" prefix and return N as int.

From voss/harness/permissions.py:21-23 (tool-classification constants — DO NOT redefine; import or mirror exactly):
    READ_ONLY = {"fs_read", "fs_glob", "fs_grep", "git_status", "git_diff", "voss_check"}
    WRITE = {"fs_write", "fs_edit"}
    SHELL = {"shell_run"}

RunRecorder corresponding sets (M2-PATTERNS.md confirms — note these differ from permissions.py because cognition classifies fs_grep/fs_glob/fs_read as "inspect" but git_status/git_diff as not-inspected; voss_check is "validate", not "inspect"):
    INSPECT_TOOLS = {"fs_read", "fs_glob", "fs_grep"}
    CHANGE_TOOLS = {"fs_write", "fs_edit"}
    VALIDATE_TOOLS = {"shell_run", "voss_check"}

git diff --stat: subprocess call returning stdout text; on non-git or empty diff returns "".
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Migrate session.py to per-cwd storage with legacy fallback + add RunRecord dataclass + extend redaction docstring</name>
  <files>voss/harness/session.py, voss/harness/cli.py, tests/harness/test_session.py, tests/harness/test_session_redaction.py</files>
  <read_first>
    - voss/harness/session.py (entire file — 113 LOC; current save/load/list_sessions implementation)
    - .planning/phases/M2-project-cognition/M2-CONTEXT.md (§D-10, D-11, D-12 hard-cut + legacy fallback; §D-13, D-14 runs field + RunRecord schema)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§voss/harness/session.py MODIFIED — code-level patterns)
    - .planning/phases/M2-project-cognition/M2-RESEARCH.md (§Pitfall 5, 7 — resume fallback ordering, runs backward-compat)
    - .planning/phases/M1-harness-happy-path/M1-03-PLAN.md (entire file — the redaction docstring it added + test conventions)
    - voss/harness/cli.py (lines 215-235 chat_cmd, 245-300 _run_repl save line, 389-445 sessions_cmd + resume_cmd — all callers to update)
    - tests/harness/test_session.py (existing patterns + the inline isolated_state fixture)
    - tests/harness/test_session_redaction.py (M1-03 ships this; we extend it)
  </read_first>
  <behavior>
    Session.py public API behaviors (after migration):
    - test_save_writes_per_cwd_path: SessionRecord.new(cwd=tmp_path, model="m"); save(record, history) writes to `tmp_path/.voss/sessions/<id>.json`; file exists, mode 0o600, JSON parseable. Legacy XDG path NOT written.
    - test_legacy_path_never_written: monkeypatch XDG_STATE_HOME to a tmp dir; save a record; verify XDG path has no files.
    - test_load_falls_back_to_legacy: write a JSON file directly to the legacy XDG dir with a known id; call `load("<id>", cwd=tmp_path_without_voss_dir)` — returns the legacy record + history.
    - test_load_legacy_without_runs_field: write a legacy-shaped JSON missing the `runs` key; load it; record.runs == [].
    - test_list_sessions_cwd_scoped: write 2 sessions under cwd_A/.voss/sessions and 1 under cwd_B/.voss/sessions; list_sessions(cwd=cwd_A) returns exactly the 2.
    - test_list_sessions_include_legacy: write 1 session under cwd/.voss/sessions and 1 under legacy XDG dir; list_sessions(cwd=cwd, include_legacy=True) returns 2; the legacy one has attribute `_legacy == True` (or equivalent marker accessible via getattr).

    Redaction test behaviors (extension of test_session_redaction.py):
    - test_run_record_top_level_keys: build a RunRecord(id="t", started_at="t0", ended_at="t1"); asdict(rec) keys equal a frozen set whose size equals len(dataclasses.fields(RunRecord)). Names: id, started_at, ended_at, goal, plan, inspected, changed, avoided, assumptions, decisions, risks, validation, failures, diff_summary, follow_ups, cost_usd. Assert NO extra keys (allowlist guarantee).
    - test_run_record_no_secret_patterns: build SessionRecord, append a clean RunRecord(id="t1", started_at="t0", ended_at="t1", goal="summarize", inspected=["src/a.py"]) to record.runs (as asdict), save via session.save, read JSON text, assert none of the six secret patterns from M1-03 appear.
  </behavior>
  <action>
    1. Edit voss/harness/session.py.
    2. Module docstring update: replace storage-location prose with a description of the per-cwd layout and the legacy fallback. Extend the existing "Redaction guarantee" stanza (M1-03) by appending after it: "RunRecord follows the same fixed-field allowlist. Adding a RunRecord field that could carry creds is a breaking change and must be paired with an explicit redaction step. The invariant is enforced by tests/harness/test_session_redaction.py over both SessionRecord and RunRecord field values." Keep "Storage location" wording updated: "Sessions live at <cwd>/.voss/sessions/<id>.json. Legacy pre-M2 sessions remain readable in place at $XDG_STATE_HOME/voss/sessions/ but are never written to."
    3. Delete `_state_dir()`. Add two functions:
       - `_sessions_dir(cwd: Path) -> Path` returning `(cwd / ".voss" / "sessions").resolve()`.
       - `_legacy_state_dir() -> Path` returning `Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "voss" / "sessions"`.
    4. Add `RunRecord` dataclass (above SessionRecord). Fields in order: id (str), started_at (str), ended_at (str), goal (str = ""), plan (dict | None = None), inspected (list[str] = field(default_factory=list)), changed (list[str] = field(default_factory=list)), avoided (list[dict] = field(default_factory=list)), assumptions (list[str] = field(default_factory=list)), decisions (list[dict] = field(default_factory=list)), risks (list[str] = field(default_factory=list)), validation (list[dict] = field(default_factory=list)), failures (list[dict] = field(default_factory=list)), diff_summary (str = ""), follow_ups (list[str] = field(default_factory=list)), cost_usd (float = 0.0). Count fields and update the redaction test's expected size accordingly.
    5. Extend SessionRecord: add `runs: list[dict] = field(default_factory=list)` as the LAST field (after `turns`). Keep all other fields and `.new`/`.first_task()` unchanged.
    6. Change `session_path(session_id, cwd: Path | None = None)` to accept cwd; if cwd is None default to `Path.cwd()` only as a safety net for legacy callers (and emit DeprecationWarning). Real callers (save, load) pass cwd explicitly. Path returned: `_sessions_dir(cwd) / f"{session_id}.json"`.
    7. save(record, history) → derive cwd from `Path(record.cwd)` (record stores it on .new). Compute path via `_sessions_dir(Path(record.cwd)) / f"{record.id}.json"`. Keep `path.parent.mkdir(parents=True, exist_ok=True)`, `chmod(0o600)`. Serialize via `json.dumps(asdict(record), indent=2)`. No changes to serialization logic.
    8. load(session_id_or_name, cwd: Path | None = None):
       - If cwd is provided: scan `_sessions_dir(cwd).glob("*.json")` first.
       - Always also scan `_legacy_state_dir().glob("*.json")` and tag those candidates as legacy.
       - Match by `data["id"].startswith(session_id_or_name)` OR `data.get("name") == session_id_or_name`.
       - If multiple matches: keep prior `ValueError("ambiguous session id; candidates: ...")` behavior. If only legacy matches, raise no error — return the legacy record (read-only).
       - Hydrate using helper `_hydrate(data)` that does:
           kept = {k: v for k, v in data.items() if k in _SESSION_FIELDS}
           kept.setdefault("turns", []); kept.setdefault("runs", [])
           return SessionRecord(**kept)
         where `_SESSION_FIELDS = {f.name for f in dataclasses.fields(SessionRecord)}`.
       - For legacy hits: set `record._legacy = True` (use object.__setattr__ if dataclass is frozen; it isn't, so direct assignment works).
       - Rehydrate EpisodicMemory same as today.
    9. list_sessions(cwd: Path, *, include_legacy: bool = False) -> list[SessionRecord]:
       - Collect from `_sessions_dir(cwd)` first.
       - If include_legacy: extend with `_legacy_state_dir()` entries, mark each `_legacy = True`.
       - Sort by updated_at desc.
       - If neither dir exists, return [].
    10. delete(session_id: str, cwd: Path | None = None) -> bool: scan per-cwd dir for matching file, unlink. Refuses to delete legacy files (returns False if found only in legacy and prints DeprecationWarning).
    11. Update voss/harness/cli.py callers:
        - chat_cmd / resume_cmd: pass cwd= when calling `session_store.load(...)`.
        - sessions_cmd currently calls `session_store.list_sessions()` with no args — update to `session_store.list_sessions(cwd=Path.cwd())`. (The --all flag itself is added in M2-04; this plan keeps the M1 behavior — only the call shape changes.)
        - The save call inside _run_repl (line ~298) needs no signature change — save reads cwd from record.cwd internally.
    12. Update tests/harness/test_session.py:
        - Remove the inline `isolated_state` fixture (now provided by conftest.py from M2-00; pytest will pick up the conftest version automatically).
        - Add 6 new tests in their own classes matching the names in the <behavior> section. Use `tmp_path` directly for the per-cwd dir; use the conftest `isolated_state` to control XDG_STATE_HOME for legacy reads.
        - Update existing TestSessionRoundtrip tests to call `list_sessions(cwd=tmp_path)` and `load(session_id, cwd=tmp_path)` per the new signature.
    13. Update tests/harness/test_session_redaction.py:
        - Add `class TestRunRecordRedaction` with two tests: `test_run_record_top_level_keys` and `test_run_record_no_secret_patterns` per the <behavior> section.
        - Existing M1 tests stay green (their state_dir fixture is now redundant with conftest but harmless; leave or remove based on what passes).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_session.py tests/harness/test_session_redaction.py tests/harness/test_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^class RunRecord" voss/harness/session.py` returns 1.
    - `grep -c "^def _sessions_dir\\|^def _legacy_state_dir" voss/harness/session.py` returns 2.
    - `grep -c "_state_dir" voss/harness/session.py` returns 0 (old helper deleted).
    - `grep -c "runs: list\\[dict\\]" voss/harness/session.py` returns at least 1 (SessionRecord.runs field added).
    - `grep -c "Redaction guarantee" voss/harness/session.py` returns at least 1 (M1-03 docstring preserved).
    - `grep -c "RunRecord follows the same" voss/harness/session.py` returns 1 (M2 extension to the docstring).
    - `python -c "from dataclasses import fields; from voss.harness.session import RunRecord; print(len(fields(RunRecord)))"` prints exactly 16 (D-14 authoritative count).
    - `pytest tests/harness/test_session.py -v` reports the 6 new tests passing alongside existing M1 tests.
    - `pytest tests/harness/test_session_redaction.py -v` reports M1 tests + 2 new TestRunRecordRedaction tests passing.
    - `pytest tests/harness/test_cli.py -x` exits 0 (no regression from session-API signature change).
  </acceptance_criteria>
  <done>Sessions are per-cwd with read-only legacy fallback; RunRecord is in the redaction allowlist; existing redaction CI extended to cover it.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement RunRecorder collaborator with mechanical capture + unskip 5 recorder tests</name>
  <files>voss/harness/recorder.py, tests/harness/test_recorder.py</files>
  <read_first>
    - .planning/phases/M2-project-cognition/M2-CONTEXT.md (§D-14, D-15 mechanical vs semantic split)
    - .planning/phases/M2-project-cognition/M2-RESEARCH.md (§Pattern 3 — RunRecorder dataclass body)
    - .planning/phases/M2-project-cognition/M2-PATTERNS.md (§voss/harness/recorder.py — INSPECT/CHANGE/VALIDATE tool sets; observer-as-dataclass pattern)
    - voss/harness/permissions.py (lines 21-23 — adjacent READ_ONLY/WRITE/SHELL constants to keep in mental sync)
    - voss/harness/tools.py (line 58 — `[exit N]\n…` shell_run result format to parse)
    - voss/harness/session.py (just-modified RunRecord dataclass — recorder.finalize returns this)
    - tests/harness/test_recorder.py (5 skipped stubs from M2-00 — exact names to unskip)
  </read_first>
  <behavior>
    - test_inspect_captures_fs_read: rec = RunRecorder.start(); rec.observe("fs_read", {"path": "src/a.py"}, "contents", ok=True); rec.inspected == ["src/a.py"].
    - test_change_captures_fs_write: rec.observe("fs_write", {"path": "out.md", "content": "x"}, "wrote 1 bytes to out.md", ok=True); rec.changed == ["out.md"].
    - test_validation_captures_exit_code: rec.observe("shell_run", {"cmd": "pytest"}, "[exit 1]\nfailed assertion", ok=True); rec.validation[0]["exit"] == 1; rec.validation[0]["cmd"] == "pytest"; rec.validation[0]["summary"] is a non-empty string ≤ 160 chars.
    - test_failure_captures_tool_error: rec.observe("fs_write", {"path": "/etc/passwd", "content": "x"}, "<error: path escapes cwd>", ok=False); rec.failures[0] == {"tool": "fs_write", "error": "<error: path escapes cwd>"} (or the error truncated to ≤200 chars).
    - test_diff_summary_from_git: using git_repo fixture, modify README.md after the initial commit; rec.finalize(git_repo, cost_usd=0.01).diff_summary contains "README.md" (or " 1 file changed" — accept whichever git --stat returns; the test asserts non-empty + that the path appears).
  </behavior>
  <action>
    1. Create voss/harness/recorder.py. Module docstring: "Per-turn mechanical observation collaborator (COG-08 D-15). Wraps run_turn's tool dispatch loop to capture inspected/changed/validation/failures without changing the agent surface. Semantic fields (goal/decisions/risks/follow_ups/assumptions/avoided) are populated by a separate privileged record_run closing call dispatched in M2-03."
    2. Imports: from __future__ import annotations; import subprocess, uuid; from dataclasses import dataclass, field; from datetime import datetime, timezone; from pathlib import Path; from .session import RunRecord.
    3. Module-level constants (mirror permissions.py shape):
       INSPECT_TOOLS = {"fs_read", "fs_glob", "fs_grep"}
       CHANGE_TOOLS = {"fs_write", "fs_edit"}
       VALIDATE_TOOLS = {"shell_run", "voss_check"}
       FAILURE_TRUNC = 200
       SUMMARY_TRUNC = 160
    4. RunRecorder dataclass fields:
       id (str), started_at (str),
       inspected (list[str] = field(default_factory=list)),
       changed (list[str] = field(default_factory=list)),
       validation (list[dict] = field(default_factory=list)),
       failures (list[dict] = field(default_factory=list)),
       cost_usd (float = 0.0),
       diff_summary (str = ""),
       # semantic fields (populated by absorb() in M2-03):
       goal (str = ""),
       plan (dict | None = None),
       avoided (list[dict] = field(default_factory=list)),
       assumptions (list[str] = field(default_factory=list)),
       decisions (list[dict] = field(default_factory=list)),
       risks (list[str] = field(default_factory=list)),
       follow_ups (list[str] = field(default_factory=list)).
    5. RunRecorder.start() classmethod: id = uuid.uuid4().hex[:12], started_at = datetime.now(timezone.utc).isoformat(timespec="seconds").
    6. RunRecorder.observe(tool_name, args, result, ok):
       - If not ok: append {"tool": tool_name, "error": str(result)[:FAILURE_TRUNC]} to failures; return.
       - If tool_name in INSPECT_TOOLS: extract path = args.get("path") or args.get("pattern") or ""; if path → inspected.append(path).
       - elif tool_name in CHANGE_TOOLS: path = args.get("path", ""); if path → changed.append(path).
       - elif tool_name in VALIDATE_TOOLS: parse exit via `_parse_exit(result)`; summary = result.splitlines()[0] if result else ""; cmd = args.get("cmd") or f"{tool_name}({args})"; validation.append({"cmd": cmd, "exit": exit_code, "summary": summary[:SUMMARY_TRUNC]}).
       - Otherwise (git_status, git_diff, unknown): no-op.
    7. RunRecorder.absorb(semantics, plan): stub that copies semantics.goal → self.goal, semantics.avoided → self.avoided, semantics.assumptions → self.assumptions, semantics.decisions → self.decisions, semantics.risks → self.risks, semantics.follow_ups → self.follow_ups; if plan is not None → self.plan = plan.model_dump() (pydantic v2). M2-03 will call this; M2-02 just defines the signature so M2-03 has somewhere to land.
    8. RunRecorder.finalize(cwd, cost_usd) -> RunRecord:
       - self.cost_usd = cost_usd
       - self.diff_summary = `_git_diff_stat(cwd)` (subprocess `git diff --stat`, try/except OSError/SubprocessError, return "" on failure, truncate to 4096 chars).
       - Return RunRecord(id=self.id, started_at=self.started_at, ended_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), goal=self.goal, plan=self.plan, inspected=list(self.inspected), changed=list(self.changed), avoided=list(self.avoided), assumptions=list(self.assumptions), decisions=list(self.decisions), risks=list(self.risks), validation=list(self.validation), failures=list(self.failures), diff_summary=self.diff_summary, follow_ups=list(self.follow_ups), cost_usd=self.cost_usd).
    9. Helper `_parse_exit(result)` -> int: if result starts with "[exit " find the closing "]" then `int(result[6:close])`. On parse failure return 0.
    10. Helper `_git_diff_stat(cwd)` -> str: subprocess.run(["git", "diff", "--stat"], cwd=str(cwd), capture_output=True, text=True, timeout=5); on nonzero exit or exception return ""; else return stdout truncated to 4096 chars.
    11. In tests/harness/test_recorder.py: unskip the 5 Wave-1 tests listed in this task's <behavior>. Use the git_repo fixture (from conftest.py M2-00) for the diff_summary test. No mocking — the recorder is observation-only, so direct unit tests work. Leave `test_decisions_mirror_to_markdown` skipped (M2-03 owns it).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/harness/test_recorder.py tests/harness/test_session.py tests/harness/test_session_redaction.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^class RunRecorder" voss/harness/recorder.py` returns 1.
    - `grep -c "INSPECT_TOOLS\\|CHANGE_TOOLS\\|VALIDATE_TOOLS" voss/harness/recorder.py` returns at least 3.
    - `grep -c "def observe\\|def finalize\\|def absorb\\|def start" voss/harness/recorder.py` returns at least 4.
    - `pytest tests/harness/test_recorder.py -v` reports 5 passing tests (one Wave-2 still skipped).
    - `python -c "from voss.harness.recorder import RunRecorder; r=RunRecorder.start(); r.observe('fs_read', {'path':'a.py'}, 'x', ok=True); assert r.inspected==['a.py']"` exits 0.
    - `python -c "from voss.harness.recorder import RunRecorder; r=RunRecorder.start(); r.observe('shell_run', {'cmd':'pytest'}, '[exit 1]\\nbad', ok=True); assert r.validation[0]['exit']==1"` exits 0.
  </acceptance_criteria>
  <done>RunRecorder captures the 4 mechanical-field categories from M1 tool results; tests prove the contract.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/ -x` exits 0 (no regression; new tests green; previously-skipped Wave-1 stubs flipped to live).
- `grep -c "Redaction guarantee\\|RunRecord follows the same" voss/harness/session.py` returns at least 2.
- `python -c "from voss.harness.session import SessionRecord, RunRecord, _sessions_dir, _legacy_state_dir"` exits 0.
- `python -c "from voss.harness.recorder import RunRecorder, INSPECT_TOOLS, CHANGE_TOOLS, VALIDATE_TOOLS"` exits 0.
</verification>

<success_criteria>
- COG-05 hard cut complete: new sessions land under `<cwd>/.voss/sessions/`; legacy XDG path is read-only and reachable via the new `include_legacy` flag.
- COG-08 mechanical half complete: RunRecorder captures inspected/changed/validation/failures/diff_summary deterministically from M1 tool result shapes.
- Redaction CI test extended (D-17) — RunRecord schema-allowlist + secret-pattern scan locked in tests/harness/test_session_redaction.py.
- M1-03 docstring contract preserved; M2 extension explicit and grep-able.
- Backward-compat: legacy sessions missing `runs` field load with `runs=[]` (Pitfall 7).
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| tool result text → RunRecord.validation/failures | mechanical capture is verbatim from M1 tool output strings |
| disk → load() | legacy JSON files of unknown shape parse into SessionRecord |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M2-05 | Information Disclosure | secret env var echoed by shell_run leaks into RunRecord.validation[].summary or failures[].error | mitigate | Schema-allowlist (M1 D-16) extended to RunRecord; extended `test_run_record_no_secret_patterns` scans 6 patterns across the full serialized session JSON; truncation at SUMMARY_TRUNC (160 chars) reduces but does not eliminate leak surface — the redaction test is the structural guarantee. |
| T-M2-06 | Tampering | malformed legacy session JSON crashes `voss resume` | mitigate | `load()` wraps json.loads in try/except (continue past bad files); `_hydrate()` accepts missing `runs` via setdefault. |
| T-M2-07 | Information Disclosure | new `runs` field accidentally widens what gets serialized beyond allowlist | mitigate | `runs: list[dict]` items are themselves serialized via `asdict(RunRecord(...))` whose own field set is enforced by `test_run_record_top_level_keys`. |
| T-M2-08 | Denial of Service | `git diff --stat` hangs at end of every turn | mitigate | `_git_diff_stat` subprocess has `timeout=5`; on TimeoutExpired returns "" rather than blocking the turn. |
</threat_model>

<output>
After completion, create `.planning/phases/M2-project-cognition/M2-02-SUMMARY.md` documenting: (1) new session.py public API surface incl. signature changes, (2) RunRecord field roster + count, (3) the legacy-fallback resolution order in load(), (4) RunRecorder observation rules per tool category, (5) the extended redaction test coverage (which RunRecord paths are scanned).
</output>
