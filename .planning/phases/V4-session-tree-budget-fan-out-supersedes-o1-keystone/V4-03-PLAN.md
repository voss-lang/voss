---
phase: V4-session-tree-budget-fan-out-supersedes-o1-keystone
plan: 03
type: execute
wave: 3
depends_on: ["V4-01", "V4-02"]
files_modified:
  - voss/harness/session_tree.py
  - voss/harness/cli.py
  - tests/harness/test_session_tree.py
autonomous: true
requirements: [VTREE-10, VTREE-09, VTREE-03]
must_haves:
  truths:
    - "export_tree(root_id, cwd) returns one JSON-serializable dict per root with every node, parent linkage, envelope, terminal_state, scope, role"
    - "The export round-trips the persisted tree (each node dict re-hydrates via _hydrate_node)"
    - "export_tree raises SessionTreeNotFoundError for an unknown/empty root"
    - "voss session tree <root_id> exits 0 and prints the node tree for a known root"
    - "voss session tree <unknown_root> exits non-zero with a stderr message"
    - "voss session tree <root_id> --json emits the machine-readable export"
    - "Spawning N children yields N node files; the full tree reconstructs from disk alone (no chat transcript)"
  artifacts:
    - path: "voss/harness/session_tree.py"
      provides: "SessionTreeNotFoundError + export_tree(root_id, cwd) aggregating glob *.json"
      contains: "def export_tree"
    - path: "voss/harness/cli.py"
      provides: "session_group + session tree subcommand, registered in AGENT_COMMANDS"
      contains: "session_group"
    - path: "tests/harness/test_session_tree.py"
      provides: "TestExport + TestCLI test classes"
      contains: "TestExport"
  key_links:
    - from: "voss/harness/cli.py::session_tree_cmd"
      to: "session_tree.export_tree"
      via: "import + call inside the click command"
      pattern: "export_tree\\("
    - from: "voss/harness/cli.py::AGENT_COMMANDS"
      to: "session_group"
      via: "tuple membership → register() add_command"
      pattern: "session_group,"
---

<objective>
Make the tree inspectable and machine-readable. Add a pure `export_tree(root_id, cwd)` in `session_tree.py` that aggregates the per-node JSON files into one document (carrying scope/role from V4-01), plus a `voss session tree <root_id>` CLI subgroup that prints the tree and, with `--json`, emits the export. This is the substrate every later V-phase (V11 ADE) renders off — V4 ships the data only.

Purpose: VTREE-10 (consolidated export) + VTREE-09 (CLI). Also verifies VTREE-03 (tree reconstructs from disk alone). Depends on V4-01 (export must carry scope/role) and V4-02 (shares the test file; sequenced after the keystone wiring).

Output: `export_tree` + `SessionTreeNotFoundError`; `session_group`/`session tree` CLI registered in `AGENT_COMMANDS`; TestExport + TestCLI green.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-SPEC.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-RESEARCH.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-01-SUMMARY.md

<interfaces>
<!-- The disk format IS the export format. export_tree mirrors the test helper
     _load_nodes_from_disk (glob *.json + json.loads). The CLI mirrors principles_group
     (most recent group analog) for registration + error conventions. -->

From voss/harness/session_tree.py (V4-01 state):
- per-node files at <cwd>/.voss/sessions/<root_id>/<node_id>.json (0o600), root file id==root_id, parent_run_id==null
- _hydrate_node(data) round-trips a node dict back to SessionTreeNode (now incl scope/role)
- existing exception class style: `class BudgetAllocationError(Exception): ...` (minimal body) — mirror for SessionTreeNotFoundError
- __all__ list — add "SessionTreeNotFoundError" and "export_tree"

From voss/harness/cli.py:
- principles_group pattern (lines 3740-3774): @click.group("principles"); @principles_group.command("show")
  with --cwd (cwd_str, click.Path(file_okay=False)), --json (json_mode, is_flag=True),
  local imports in body, `click.echo(f"<error: {e}>", err=True); raise click.exceptions.Exit(1)`
- inspect_group (lines 2757-2788): shows @click.argument("...") pattern for positional root_id
- AGENT_COMMANDS tuple (lines 3777-3808) ends with `principles_group,` then `register()` loops add_command

From tests/harness/test_session_tree.py:
- _load_nodes_from_disk(cwd, root_id) helper (glob *.json) — the aggregation pattern export_tree mirrors
- click.testing.CliRunner for CLI tests (new import)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: export_tree + SessionTreeNotFoundError in session_tree.py</name>
  <files>voss/harness/session_tree.py, tests/harness/test_session_tree.py</files>
  <read_first>
    - voss/harness/session_tree.py (full read — __all__, exception class style lines 30-44, _hydrate_node, _write_node_file lines 97-102; the disk layout export_tree aggregates)
    - tests/harness/test_session_tree.py (lines 43-57 — _load_nodes_from_disk glob pattern to mirror; TestTreePersistence for round-trip conventions)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md ("No Analog Found" section — SessionTreeNotFoundError + export_tree construction)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-RESEARCH.md (Focus Area 5 — export function shape, Pitfall 6 open-node export)
  </read_first>
  <behavior>
    - export_tree(root_id, cwd) for a root with 1 root + N children returns {"root_id": root_id, "nodes": [...]} with N+1 node dicts.
    - Every node dict contains id, root_id, parent_run_id, envelope, terminal_state, created_at, ended_at, scope, role (parent linkage + envelope + terminal + scope/role present).
    - Round-trip: _hydrate_node(node_dict) for each node dict yields a SessionTreeNode with matching id/envelope/scope/role.
    - export_tree raises SessionTreeNotFoundError when the <cwd>/.voss/sessions/<root_id> directory does not exist OR contains no *.json files.
    - An open (unfinalized) node exports with terminal_state == null (valid live-tree state — Pitfall 6).
  </behavior>
  <action>
    In voss/harness/session_tree.py: add `class SessionTreeNotFoundError(Exception):` with a minimal body and a one-line docstring (mirror BudgetAllocationError's style). Add a pure function `export_tree(root_id: str, cwd: Path) -> dict`: resolve `tree_dir = cwd / ".voss" / "sessions" / root_id`; if not `tree_dir.is_dir()` raise `SessionTreeNotFoundError(root_id)`; iterate `sorted(tree_dir.glob("*.json"))`, `json.loads(path.read_text())` each into a `nodes` list (the on-disk dict IS the export form — do NOT re-serialize via to_dict; preserve exactly what was persisted, including scope/role and null terminal_state for open nodes); if `nodes` is empty raise `SessionTreeNotFoundError(root_id)`; return `{"root_id": root_id, "nodes": nodes}`. Add both `"SessionTreeNotFoundError"` and `"export_tree"` to `__all__`. Do NOT change any existing function. The export is read-only — no chmod, no writes.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestExport -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `grep -n "class SessionTreeNotFoundError" voss/harness/session_tree.py` and `grep -n "def export_tree" voss/harness/session_tree.py` both return a line.
    - Source assertion: `grep -c "SessionTreeNotFoundError\|export_tree" voss/harness/session_tree.py | head -1` confirms both are also in __all__ (grep `__all__` block).
    - Behavior: `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestExport -x -q` passes — export contains all nodes with scope/role + parent linkage, round-trips via _hydrate_node, and raises SessionTreeNotFoundError on unknown root.
    - VTREE-03: a TestExport test spawns N children, asserts `len(glob *.json) == N+1`, and reconstructs the tree purely from export_tree (no transcript).
  </acceptance_criteria>
  <done>export_tree returns one JSON-serializable dict per root with all nodes + linkage + envelope + terminal + scope/role; round-trips; raises on unknown root; tree reconstructs from disk alone.</done>
</task>

<task type="auto">
  <name>Task 2: voss session tree CLI subgroup + AGENT_COMMANDS registration</name>
  <files>voss/harness/cli.py, tests/harness/test_session_tree.py</files>
  <read_first>
    - voss/harness/cli.py (lines 3740-3774 principles_group — the exact pattern to mirror; lines 2757-2788 inspect_group @click.argument; lines 3777-3813 AGENT_COMMANDS + register)
    - voss/harness/session_tree.py (export_tree + SessionTreeNotFoundError from Task 1)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md (cli.py sections 1-3 — principles_group mirror, error pattern, AGENT_COMMANDS append)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-RESEARCH.md (Focus Area 4 — Option A non-breaking, exit-code semantics)
  </read_first>
  <action>
    DECISION RECORDED (resolves RESEARCH Focus Area 4 CLI taxonomy): use Option A — add a NEW `session_group` ALONGSIDE the existing flat `sessions_cmd` (non-breaking; `voss sessions` keeps working, `voss session tree` is new). Do NOT move/demote sessions_cmd (Option B is a larger refactor outside VTREE-09 scope). In voss/harness/cli.py: add `@click.group("session")` named `session_group` with a docstring; add `@session_group.command("tree")` named `session_tree_cmd` with `@click.argument("root_id")`, `@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))`, and `@click.option("--json", "json_mode", is_flag=True, help="Machine-readable JSON export.")`. In the body (mirror principles_group): local imports `import json as json_lib` and `from .session_tree import SessionTreeNotFoundError, export_tree`; `cwd = Path(cwd_str).resolve()`; `try: tree = export_tree(root_id, cwd)` `except SessionTreeNotFoundError:` `click.echo(f"<error: no session tree for root_id {root_id!r}>", err=True)` then `raise click.exceptions.Exit(1)`. If `json_mode`: `click.echo(json_lib.dumps(tree, indent=2))` and return. Else render a text tree: one line per node in `tree["nodes"]` with id, parent (parent_run_id or "—"), `limit=.../spent=...` from envelope, state (terminal_state["exit_reason"] if terminal_state else "open"), scope, role (use "—" for None) — indent children (parent_run_id set) by two spaces. Append `session_group,` to the `AGENT_COMMANDS` tuple immediately after `principles_group,` (register() add_command loop wires it automatically).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestCLI -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `grep -n "@click.group(\"session\")" voss/harness/cli.py` and `grep -n "session_group.command(\"tree\")" voss/harness/cli.py` both return a line.
    - Source assertion: `grep -c "session_group," voss/harness/cli.py` returns at least 1 (AGENT_COMMANDS membership).
    - Non-breaking: `grep -n "sessions_cmd," voss/harness/cli.py` still present (flat command untouched).
    - Behavior (known root): TestCLI uses click.testing.CliRunner to invoke session_group on a spawned tree → exit_code == 0 and output contains the root id.
    - Behavior (unknown root): CliRunner invoke with a bogus root_id → exit_code != 0 and the stderr/error output is non-empty.
    - Behavior (--json): CliRunner invoke with --json → exit_code 0 and stdout parses as JSON with a "nodes" key.
  </acceptance_criteria>
  <done>voss session tree <root_id> exits 0 + prints the tree for a known root; unknown root exits non-zero with a stderr message; --json emits the export; sessions_cmd unaffected.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: TestExport + TestCLI classes + full-suite regression gate</name>
  <files>tests/harness/test_session_tree.py</files>
  <read_first>
    - tests/harness/test_session_tree.py (full read — imports lines 1-40, async/sync class conventions, _load_nodes_from_disk/_node_path helpers)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md (test patterns — new imports needed: click.testing.CliRunner, session_group, export_tree, SessionTreeNotFoundError)
    - voss/harness/session_tree.py (export_tree from Task 1) and voss/harness/cli.py (session_group from Task 2)
  </read_first>
  <behavior>
    - TestExport: export round-trips a spawned tree (all node ids present, parent linkage intact, scope/role present), reconstructs from disk alone (VTREE-03), and raises SessionTreeNotFoundError on an unknown root.
    - TestCLI: known root → exit 0 + output contains node ids; unknown root → exit !=0 + non-empty error output; --json → parseable JSON with "nodes".
  </behavior>
  <action>
    Author `TestExport` and `TestCLI` classes in tests/harness/test_session_tree.py (if Task 1/Task 2 already stubbed minimal versions to satisfy their own verify, complete them here to cover the full behavior set above — do not duplicate). Add the new imports near the top: `from click.testing import CliRunner`, `from voss.harness.cli import session_group`, and extend the session_tree import with `SessionTreeNotFoundError, export_tree`. Use the existing `tmp_path` fixture and `_load_nodes_from_disk`/`_node_path` helpers. For TestCLI, build a tree under tmp_path (create_root + allocate_child), then `CliRunner().invoke(session_group, ["tree", root_id, "--cwd", str(tmp_path)])` and assert exit_code/output; for the unknown-root case pass a fabricated id. Follow the established class-based conventions (async only where awaiting allocate_child; asyncio_mode=auto, no decorator). Then run the FULL test_session_tree.py file plus the redaction gate as the phase-closing regression.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q && .venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `grep -n "class TestExport\|class TestCLI" tests/harness/test_session_tree.py` returns both classes.
    - Source assertion: `grep -n "from click.testing import CliRunner" tests/harness/test_session_tree.py` confirms the CLI test import.
    - Behavior: `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestExport tests/harness/test_session_tree.py::TestCLI -x -q` passes.
    - Phase regression: `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q` green (all V4-01/02/03 classes coexist).
    - Schema freeze: `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q` passes UNMODIFIED.
  </acceptance_criteria>
  <done>TestExport + TestCLI prove the export round-trip and CLI exit-code/stderr contract; whole test_session_tree.py green; redaction test unmodified and green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| root_id (CLI arg) ↔ filesystem path | root_id composes a path under .voss/sessions/; a traversal here could read outside the tree dir |
| node JSON files ↔ export consumer (ADE/CLI) | the export is the machine-readable budget/finalization record downstream phases trust |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V4-20 | Tampering | path traversal via root_id in export_tree / CLI | mitigate | root_id is produced as `uuid4().hex[:12]` (no user-controlled separators in normal flow); export_tree scopes to `cwd / ".voss" / "sessions" / root_id` and globs only `*.json` within it. Acceptance: unknown/garbage root_id yields SessionTreeNotFoundError, not a read elsewhere. (Note: a hostile literal root_id like "../x" would resolve under sessions/ as a child path; glob still confines to that dir's *.json — no escalation in V4's local-CLI threat model) |
| T-V4-21 | Information Disclosure | export surfaces scope/role + envelope | accept | scope/role/envelope are non-secret operational labels; node files remain 0o600; export is read-only and locally invoked. No credentials in node schema (redaction invariant holds — RunRecord/SessionRecord untouched) |
| T-V4-22 | Tampering | export of an active (open) node mid-run | accept | export is a point-in-time snapshot; open nodes export terminal_state=null (valid live state, Pitfall 6). ADE rendering (V11) handles null; no fix in V4 |
| T-V4-SC | Tampering | npm/pip/cargo installs | n/a | Zero third-party installs in V4 |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q` — full file green (export + CLI + all prior V4 classes).
- `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q` — UNMODIFIED, green.
- `.venv/bin/python -m pytest tests/harness/ -q` — full harness suite green (phase gate).
- `git diff -- voss/harness/session_tree.py voss/harness/cli.py` — only additive export_tree/exception + session_group; no existing function changed; sessions_cmd intact.
</verification>

<success_criteria>
- export_tree returns one JSON object per root with all nodes + parent linkage + envelope + terminal_state + scope/role; round-trips; raises on unknown root (VTREE-10).
- voss session tree <root_id> exits 0 + prints the tree for a known root; unknown root exits non-zero with stderr; --json emits the export (VTREE-09).
- Tree reconstructs from disk alone; N children → N node files (VTREE-03).
- sessions_cmd unaffected (non-breaking Option A).
- test_session_redaction.py unmodified; full harness suite green.
</success_criteria>

<output>
Create `.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-03-SUMMARY.md` when done. Record the Option-A non-breaking CLI decision and confirm the full harness suite + redaction gate are green (phase close).
</output>
