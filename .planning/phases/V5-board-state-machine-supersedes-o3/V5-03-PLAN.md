---
phase: V5-board-state-machine-supersedes-o3
plan: 03
type: execute
wave: 2
depends_on: [V5-01]
files_modified:
  - voss/harness/board/cli_view.py
  - voss/harness/cli.py
autonomous: true
requirements: [VBOARD-10]
must_haves:
  truths:
    - "voss board (no arg) renders the most-recent root's 6 columns + cards (id/role/risk/status/budget spent-limit) read-only from persisted node JSON and exits 0"
    - "voss board <root_id> renders that named root and exits 0"
    - "An unknown root, a missing sessions dir, and a path-traversal root_id each exit non-zero with a stderr message"
    - "Most-recent root is selected by directory mtime (NOT lexical root_id ordering)"
  artifacts:
    - path: "voss/harness/board/cli_view.py"
      provides: "read-only board renderer: root selection (mtime), node-JSON read, column derivation (mirrors audit/load.py), budget from envelope, 6-column table, return code"
      contains: "def render_board"
    - path: "voss/harness/cli.py"
      provides: "board_cmd standalone click command registered in AGENT_COMMANDS"
      contains: "board_cmd"
  key_links:
    - from: "voss.harness.cli.board_cmd"
      to: "tests/harness/board/test_board_cli.py"
      via: "CliRunner invoke of the planned command (greens the RED scaffold)"
      pattern: "board_cmd"
    - from: "voss.harness.cli.board_cmd"
      to: "voss.harness.board.cli_view.render_board"
      via: "deferred import + raise click.exceptions.Exit(code=rc)"
      pattern: "render_board"
---

<objective>
Implement the VBOARD-10 `voss board [root_id]` read-only CLI: a new `voss/harness/board/cli_view.py` renderer (analog of `audit/load.py`) plus a `board_cmd` standalone command registered in `voss/harness/cli.py`. This greens the third V5-01 RED scaffold (`test_board_cli.py`).

Purpose: Make the shipped board inspectable from the CLI without constructing a live `Board`/`SessionTreeManager` — reading directly from persisted `.voss/sessions/<root>/<node>.json` files.

Output: `cli_view.py` (`render_board`) + `board_cmd` wired into `AGENT_COMMANDS`. Independent of V5-02 (no machine.py changes; both depend only on V5-01).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-SPEC.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-RESEARCH.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-PATTERNS.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-01-PLAN.md

<interfaces>
<!-- The EXACT symbols the V5-01 RED scaffold imports + the persisted node JSON shape the test fixtures write. -->

Planned CLI command (voss/harness/cli.py) — standalone, NOT a group:
  board_cmd = click.command("board")
    @click.argument("root_id", required=False, default=None)
    @click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
    body: deferred `from voss.harness.board.cli_view import render_board`; resolve cwd;
          rc = render_board(cwd, root_id=root_id); raise click.exceptions.Exit(code=rc)
  Registered by adding board_cmd to the AGENT_COMMANDS tuple (cli.py ~line 3917); register() already iterates it.

Planned renderer (voss/harness/board/cli_view.py — new):
  def render_board(cwd: Path, root_id: str | None = None) -> int
    returns 0 on successful render (stdout), non-zero (e.g. 1) on: no sessions dir, unknown root,
    path-traversal/separator-bearing root_id — with a click.echo(..., err=True) stderr message.

Persisted node JSON shape the test fixtures write (REAL shape, from session_tree.py + audit/load.py):
  { "id": <node_id>, "root_id": <root_id>, "transitions": [ {"kind": "board.transition", "to": "<Column>"} , ... ],
    "envelope": {"spent": <int>, "limit": <int>}, "terminal_state": null | {"exit_reason": "..."} }
  Path: <cwd>/.voss/sessions/<root_id>/<node_id>.json

Column derivation (mirror audit/load.py lines 206-220 EXACTLY): start "Backlog"; for each transition with
  kind=="board.transition" set column=t.get("to", column); then if terminal_state present, exit_reason in
  ("timeout","killed") → "Blocked", "done" → "Done".
6 columns order: ("Backlog","Planned","InProgress","InReview","Blocked","Done").
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: cli_view.py read-only board renderer (VBOARD-10)</name>
  <files>voss/harness/board/cli_view.py</files>
  <read_first>
    - voss/harness/audit/load.py lines 35-48 (`_read_node_file` defensive JSON reader to mirror) and lines 206-220 (the EXACT column-derivation rule — copy verbatim, no deviation) and lines 250-263 (root enumeration — audit uses LEXICAL sort; cli_view must use mtime instead per Pitfall 3)
    - voss/harness/session_tree.py lines 97-101 (sessions dir layout `<cwd>/.voss/sessions/<root_id>/<node_id>.json`)
    - voss/harness/board/machine.py lines 51-53 (the 6-column order constant — REDECLARE locally in cli_view.py; do NOT import from machine.py to avoid pulling its import chain)
    - voss/harness/cli.py lines 3815-3850 area (principles_show_cmd error-exit pattern: `click.echo(..., err=True)` then `raise click.exceptions.Exit(1)`)
    - V5-PATTERNS.md §"voss/harness/board/cli_view.py — New read-only board renderer" (imports, _read_node_file, column rule, mtime root selection, budget-from-envelope, error exit, local _COLUMNS)
    - V5-RESEARCH.md §"Research Focus 3" (root selection rule, exit codes, role falls back to "" for legacy nodes) and §"Security Domain" T-V5-03 (path traversal: reject root_id containing "/" or ".."; resolved path must stay under .voss/sessions/)
    - tests/harness/board/test_board_cli.py (the RED scaffold this task + Task 2 green — confirm the node-JSON fixture shape and the six expected exit-code/stderr behaviors, including test_default_latest_picks_most_recent and test_path_traversal_rejected)
  </read_first>
  <behavior>
    - render_board(cwd) with no .voss/sessions dir → returns non-zero, writes a stderr message.
    - render_board(cwd, root_id="does-not-exist") with a valid other root present → returns non-zero + stderr.
    - render_board(cwd) with one valid root → returns 0, prints the 6 columns with each card's id/role/risk/status/budget.
    - render_board(cwd, root_id=<existing>) → returns 0.
    - render_board(cwd) with two roots where the second has a newer mtime → renders the newer root (selected by mtime, not lexical name).
    - render_board(cwd, root_id="../../etc") or a root_id containing "/" → returns non-zero + stderr (path-traversal rejected), never resolves outside .voss/sessions/.
  </behavior>
  <action>
    Create `voss/harness/board/cli_view.py` with stdlib-only imports (`from __future__ import annotations`, `json`, `pathlib.Path`, `typing`) plus `click` for output. Do NOT construct a live `Board` or `SessionTreeManager`. Redeclare the 6-column order as a local `_COLUMNS` tuple (`"Backlog","Planned","InProgress","InReview","Blocked","Done"`). Implement a defensive node reader mirroring `audit/load.py._read_node_file` (tolerate/skip unreadable or non-dict JSON rather than crash). Implement column derivation by copying the `audit/load.py` lines 206-220 rule VERBATIM (transitions loop + terminal_state override). Implement `render_board(cwd, root_id=None) -> int`: locate `cwd/.voss/sessions`; if missing → emit stderr and return non-zero. Validate root_id FIRST for traversal — reject any root_id containing a path separator or ".." before touching the filesystem, and confirm the resolved candidate path is a child of the sessions dir (T-V5-03); on violation emit stderr + return non-zero. Root selection: named root_id → `sessions_dir / root_id` if it exists else stderr + non-zero; default (None) → choose the directory with the greatest `st_mtime` via `sorted(..., key=lambda d: d.stat().st_mtime, reverse=True)[0]` (mtime, NOT lexical — Pitfall 3); empty sessions dir → stderr + non-zero. For the selected root, read each `<node>.json`, derive column, read budget as `(envelope.get("spent",0), envelope.get("limit",0))`, role from the node's `role`/Card field falling back to `""`, risk from the node ticket falling back to `"med"`, status == derived column. Bucket cards into the 6 columns and render with `click.echo` fixed-width formatting (id, role, risk, status, budget spent/limit). Return 0 on successful render. Use `click.echo(msg, err=True)` for all error messages; the function returns the non-zero code (the command translates it to Exit).
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.board.cli_view import render_board; print('import-ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/board/cli_view.py` exists and exports `render_board`; importing it does not import `voss.harness.board.machine` (`grep -n "import" voss/harness/board/cli_view.py` shows no `from .machine`/`from voss.harness.board.machine` import; `_COLUMNS` is redeclared locally).
    - The column-derivation block matches `audit/load.py` 206-220 (`grep -n "board.transition\|terminal_state\|timeout\|killed\|done" voss/harness/board/cli_view.py` shows the same override branches).
    - Root selection uses mtime: `grep -n "st_mtime" voss/harness/board/cli_view.py` is present; no lexical-only `sorted(...iterdir())` is used for "latest".
    - Path-traversal rejection present: `grep -n '\.\.\|sep\|/' voss/harness/board/cli_view.py` shows a root_id separator/".." guard before any path build.
    - No live Board/Manager: `grep -n "SessionTreeManager\|Board(" voss/harness/board/cli_view.py` returns NOTHING.
    - Import smoke passes (the automated verify above).
  </acceptance_criteria>
  <done>cli_view.py renders read-only from persisted node JSON, mirrors the audit column rule, selects latest root by mtime, rejects path traversal, never constructs a live Board, and imports cleanly without pulling machine.py.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Register board_cmd in cli.py and green the CLI scaffold (VBOARD-10)</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py lines 2301-2320 (`doctor_cmd` — the standalone `click.command` + `--cwd` option pattern to copy)
    - voss/harness/cli.py lines 3811-3850 (`principles_group` + the error-exit / `click.exceptions.Exit` pattern)
    - voss/harness/cli.py lines 3917-3955 (`AGENT_COMMANDS` tuple ~3917 and `register()` ~3952 — add `board_cmd` to the tuple; register() already iterates it, no change needed there)
    - V5-PATTERNS.md §"voss/harness/cli.py — Register board_cmd in AGENT_COMMANDS" (exact board_cmd body: deferred import of render_board, resolve cwd, raise Exit(code=rc); add to AGENT_COMMANDS)
    - V5-RESEARCH.md §"Pattern 5: CLI command registration" and Open Question 2 (standalone `click.command("board")`, NOT a group, for V5)
    - tests/harness/board/test_board_cli.py (the RED scaffold both tasks green — confirm it imports `from voss.harness.cli import board_cmd` and the six CliRunner cases)
  </read_first>
  <behavior>
    - `from voss.harness.cli import board_cmd` succeeds (command exists at module scope).
    - CliRunner().invoke(board_cmd, ["--cwd", <empty tmp>]) → exit_code != 0 (no sessions).
    - CliRunner(mix_stderr=False).invoke(board_cmd, ["does-not-exist", "--cwd", <tmp-with-one-root>]) → exit_code != 0 and result.stderr non-empty.
    - CliRunner().invoke(board_cmd, ["--cwd", <tmp-with-root>]) → exit_code == 0.
    - CliRunner().invoke(board_cmd, [<root_id>, "--cwd", <tmp-with-root>]) → exit_code == 0.
    - The two-roots-newer-mtime case renders the newer root; the path-traversal case exits non-zero.
  </behavior>
  <action>
    Add a standalone `board_cmd` to `voss/harness/cli.py` using the `doctor_cmd` pattern: decorate with `@click.command("board")`, `@click.argument("root_id", required=False, default=None)`, and `@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))`. In the body, DEFER the import (`from voss.harness.board.cli_view import render_board`), resolve `cwd = Path(cwd_str).resolve()`, call `rc = render_board(cwd, root_id=root_id)`, then `raise click.exceptions.Exit(code=rc)`. Add `board_cmd` to the `AGENT_COMMANDS` tuple (last position is fine). Do NOT modify `register()`. Use `click.command` (standalone), NOT `click.group` — no sub-commands in V5.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_board_cli.py -x -q --tb=short</automated>
  </verify>
  <acceptance_criteria>
    - `test_board_cli.py` (TestBoardCLI, all six methods incl. test_default_latest_picks_most_recent and test_path_traversal_rejected) is GREEN: exit 0.
    - `grep -n "board_cmd" voss/harness/cli.py` shows the command definition AND its presence in the AGENT_COMMANDS tuple.
    - `grep -n "click.command(\"board\")" voss/harness/cli.py` confirms standalone command (not a group).
    - `from voss.harness.cli import board_cmd` import smoke succeeds.
    - `voss board --help` style invocation works: `.venv/bin/python -c "from click.testing import CliRunner; from voss.harness.cli import board_cmd; r=CliRunner().invoke(board_cmd, ['--help']); print(r.exit_code)"` prints `0`.
  </acceptance_criteria>
  <done>board_cmd is a standalone click command wired into AGENT_COMMANDS, delegates to render_board, and test_board_cli.py is fully GREEN.</done>
</task>

</tasks>

<verification>
- CLI scaffold green: `.venv/bin/python -m pytest tests/harness/board/test_board_cli.py -q --tb=short` → exit 0 (all six cases incl. mtime-latest and path-traversal).
- No regression on the shipped board surface beyond the known pre-existing failure: `.venv/bin/python -m pytest tests/harness/board/ -q --tb=line` shows the SAME single pre-existing failure (`test_exit_reasons_is_sorted_superset_of_pre_o3`, fixed in V5-04) and no previously-green test flipped to red.
- Frozen-schema guard: `git diff --name-only` shows changes ONLY to voss/harness/board/cli_view.py (new) and voss/harness/cli.py — no session.py, session_tree.py, voss_runtime, machine.py, verdict.py.
</verification>

<success_criteria>
- VBOARD-10: `voss board` renders the latest root's 6 columns + cards from persisted JSON and exits 0; `voss board <root_id>` renders that root; unknown root / missing sessions / path-traversal exit non-zero with stderr; latest root chosen by mtime.
- Read-only: no live Board/SessionTreeManager constructed; column rule mirrors audit/load.py exactly.
- test_board_cli.py is GREEN; only cli_view.py (new) and cli.py changed.
</success_criteria>

<output>
Create `.planning/phases/V5-board-state-machine-supersedes-o3/V5-03-SUMMARY.md` when done.
</output>
