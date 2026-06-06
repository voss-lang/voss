---
phase: V5-board-state-machine-supersedes-o3
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/harness/board/test_card_fields_v5.py
  - tests/harness/board/test_self_done_guard.py
  - tests/harness/board/test_board_cli.py
autonomous: true
requirements: [VBOARD-03, VBOARD-07, VBOARD-10]
must_haves:
  truths:
    - "Three new RED test files encode VBOARD-03/07/10 acceptance and fail against the un-implemented API (not a fake API)"
    - "The scaffold tests import the REAL planned symbols (Card new fields, card_status/card_budget, board_cmd) so they go GREEN only after V5-02/V5-03 implement them"
    - "No xfail(strict=False) masking; failures are genuine ImportError/AttributeError/AssertionError"
  artifacts:
    - path: "tests/harness/board/test_card_fields_v5.py"
      provides: "VBOARD-03 RED suite: new Card fields default to '', frozen invariant, back-compat construction, card_status/card_budget helpers"
      contains: "class TestCardFieldsV5"
    - path: "tests/harness/board/test_self_done_guard.py"
      provides: "VBOARD-07 RED suite: reviewer=None Done raises BoardGateError(no-reviewer), valid reviewer permits Done, no verdict-injection path"
      contains: "class TestSelfDoneGuard"
    - path: "tests/harness/board/test_board_cli.py"
      provides: "VBOARD-10 RED suite: latest/named root render exit 0, unknown root non-zero+stderr, path-traversal rejected, no-sessions non-zero"
      contains: "class TestBoardCLI"
  key_links:
    - from: "tests/harness/board/test_card_fields_v5.py"
      to: "voss.harness.board.machine.card_status / card_budget"
      via: "import of planned helpers (RED until V5-02)"
      pattern: "card_status|card_budget"
    - from: "tests/harness/board/test_board_cli.py"
      to: "voss.harness.cli.board_cmd"
      via: "CliRunner invoke of planned command (RED until V5-03)"
      pattern: "board_cmd"
---

<objective>
Stand up the Wave-0 RED scaffolds for V5: three new test files that encode the VBOARD-03/07/10 acceptance criteria and fail today, then go GREEN once V5-02 (machine.py) and V5-03 (CLI) land. This is the project's established Wave-0 pattern (STATE M13/T6 precedent).

Purpose: Lock the acceptance contract in executable form BEFORE implementation, so V5-02/V5-03 are written against a fixed bar. Each test drives the REAL planned API surface (the exact field names, helper signatures, and CLI command pinned in V5-RESEARCH/V5-PATTERNS) — NOT an ad-libbed fake API. This avoids the `gsd-scaffold-fictional-api` failure (memory): scaffold bodies that invent a non-existent API which `xfail(strict=False)` then masks as permanent false-green.

Output: 3 new test files under `tests/harness/board/`, all collectable, all RED for the right reason (missing real symbols / missing real behavior).
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
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-VALIDATION.md
@.planning/phases/V5-board-state-machine-supersedes-o3/V5-PATTERNS.md

<interfaces>
<!-- The REAL planned symbols these RED tests must drive. Extracted from V5-PATTERNS/V5-RESEARCH. -->
<!-- Tests import these; they are RED until V5-02/V5-03 implement them. Do NOT invent alternate names. -->

Card (voss/harness/board/machine.py) AFTER V5-02 — current fields plus four additive defaults:
  node_id: str ; column: Column ; risk_tier: RiskTier ; retry_count: int ; deadline: float
  scope: Optional[TeamRoleScope] = None ; artifact: Optional[object] = None ; eval_threshold: float = 1.0
  idea: str = "" ; role: str = "" ; acceptance_criteria: str = "" ; verification_requirement: str = ""

Planned module-level helpers (voss/harness/board/machine.py, NOT @property):
  def card_status(card: "Card") -> str           # returns card.column
  def card_budget(node_envelope: dict) -> tuple[int, int]   # (spent, limit) from envelope dict

Planned CLI command (voss/harness/cli.py) AFTER V5-03:
  board_cmd = click.command("board")
    argument root_id (optional, default None) ; option --cwd (default ".")
    exit 0 on render ; non-zero + stderr on unknown root / no sessions / path-traversal

board package exports already available (import from voss.harness.board):
  Board, BoardGateError, Card ; voss.harness.board.stub.DeterministicReviewerStub

Existing conftest fixtures (tests/harness/board/conftest.py): tmp_recorder -> (SessionTreeManager, cwd: Path) ; stub_reviewer ; build_test_team() (function) ; artifact_passing/artifact_failing ; fake_clock
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: RED scaffold for VBOARD-03 (Card fields) + VBOARD-07 (self-Done guard)</name>
  <files>tests/harness/board/test_card_fields_v5.py, tests/harness/board/test_self_done_guard.py</files>
  <read_first>
    - tests/harness/board/test_card_node_wiring.py (analog for test_card_fields_v5.py — class-based pytest, fixture injection)
    - tests/harness/board/test_stub_full_lifecycle.py (analog for test_self_done_guard.py — drive card Backlog→InReview→Done via DeterministicReviewerStub)
    - tests/harness/board/conftest.py (available fixtures: tmp_recorder, stub_reviewer, build_test_team, artifact_passing/failing, fake_clock)
    - voss/harness/board/machine.py lines 80-94 (current Card def — confirm the four new fields do NOT yet exist) and lines 336-365 (Board.move — confirm no `no-reviewer` guard yet)
    - V5-PATTERNS.md §"test_card_fields_v5.py" and §"test_self_done_guard.py" (exact class/test skeletons)
    - V5-RESEARCH.md §"Research Focus 1" and §"Research Focus 2" (independence model; field defaults)
  </read_first>
  <action>
    Create `test_card_fields_v5.py` with `class TestCardFieldsV5`, `class TestCardStatus`, `class TestCardBudget`. Drive the REAL planned API:
    - TestCardFieldsV5.test_new_fields_have_defaults: construct `Card(node_id="n1", column="Backlog", risk_tier="med", retry_count=0, deadline=999.0)` and assert `idea == "" and role == "" and acceptance_criteria == "" and verification_requirement == ""`. (RED now: Card has no such fields → AttributeError on access; the construct itself succeeds but the asserts fail.)
    - TestCardFieldsV5.test_card_is_still_frozen: assert assigning `card.idea = "x"` raises `dataclasses.FrozenInstanceError`.
    - TestCardFieldsV5.test_old_construction_paths_unchanged: construct a Card with `idea="test idea"`, `dataclasses.replace(card, column="Planned")`, assert `idea` carries through. (RED now: `idea` is an unexpected keyword.)
    - TestCardStatus.test_card_status_returns_column: `from voss.harness.board.machine import card_status` then assert `card_status(Card(...InProgress...)) == "InProgress"`. (RED now: ImportError — helper does not exist.)
    - TestCardBudget.test_card_budget_reads_envelope: `from voss.harness.board.machine import card_budget` then `card_budget({"spent": 100, "limit": 1000}) == (100, 1000)`; also assert `card_budget({}) == (0, 0)` (missing-keys default). (RED now: ImportError.)
    Create `test_self_done_guard.py` with `class TestSelfDoneGuard`. Use `tmp_recorder`, `Board.from_team_config(build_test_team(), recorder=manager, reviewer=..., cwd=cwd)`, and drive a card to InReview with a passing artifact (mirror test_stub_full_lifecycle: set `artifact=SimpleNamespace(tests_passed=True, scope_violations=())` via `dataclasses.replace` and re-bind in `board._cards`):
    - test_reviewer_none_raises_board_gate_error: build Board with `reviewer=None`, drive to InReview, then `pytest.raises(BoardGateError)` on `board.move(card, to="Done")`; assert `"no-reviewer" in exc.value.failing_clauses`. (RED now: current code fails with `["conf"]`, NOT `["no-reviewer"]` — the explicit guard is missing.)
    - test_valid_reviewer_allows_done: build Board with `DeterministicReviewerStub(conf=0.99, verdict="pass")`, drive to InReview with passing artifact, assert `board.move(card, to="Done").column == "Done"`. (Should already pass with stub — keep it; it pins the positive path and must stay GREEN after V5-02.)
    - test_no_verdict_injection_path: documents the structural guarantee (T-V5-02 Spoofing) — assert that `Board.move` constructs its own `GateContext` (e.g. there is no `move(card, to, verdict=...)` parameter); a minimal form is asserting `move` signature has no `verdict` kwarg via `inspect.signature(board.move)`. Keep this assertion true today (it is structural) — it is a regression tripwire, not a RED-until-impl test.
    Add a module docstring to each file naming the requirement (VBOARD-03 / VBOARD-07) and "Wave 0 RED scaffold — drives REAL planned API". Do NOT use `xfail`, `xfail(strict=False)`, or `skip`. Failures must be genuine.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_card_fields_v5.py tests/harness/board/test_self_done_guard.py --collect-only -q && .venv/bin/python -m pytest tests/harness/board/test_card_fields_v5.py tests/harness/board/test_self_done_guard.py -q --tb=line; test $? -ne 0</automated>
  </verify>
  <acceptance_criteria>
    - `--collect-only` lists `TestCardFieldsV5`, `TestCardStatus`, `TestCardBudget`, `TestSelfDoneGuard` (collection succeeds — no import-time crash that prevents collection).
    - Running the two files exits NON-zero (RED) because: `card_status`/`card_budget` ImportError; Card has no `idea/role/acceptance_criteria/verification_requirement`; `move(card,"Done")` with `reviewer=None` does not yet carry `"no-reviewer"` in `failing_clauses`.
    - `grep -n "xfail\|@pytest.mark.skip" tests/harness/board/test_card_fields_v5.py tests/harness/board/test_self_done_guard.py` returns NOTHING (no masking).
    - `test_valid_reviewer_allows_done` and `test_no_verdict_injection_path` are written to be GREEN already (positive path + structural tripwire).
  </acceptance_criteria>
  <done>Both files collect cleanly and the suite is RED for the right reasons (missing real symbols/behavior); zero xfail/skip masking; positive-path and injection-tripwire tests are GREEN.</done>
</task>

<task type="auto">
  <name>Task 2: RED scaffold for VBOARD-10 (voss board CLI)</name>
  <files>tests/harness/board/test_board_cli.py</files>
  <read_first>
    - tests/harness/test_diagnostics.py (CliRunner pattern: `CliRunner().invoke(cmd, ["--cwd", str(tmp_path)])`; `mix_stderr=False` for stderr inspection; exit_code asserts)
    - tests/cli/test_help.py (isolated_filesystem pattern, if needed)
    - voss/harness/audit/load.py lines 200-265 (the EXACT column-derivation + root-enumeration the CLI must mirror — the node JSON shape the test fixtures must write: `id`, `transitions[]` with `kind=="board.transition"`/`to`, `terminal_state`, `envelope{spent,limit}`)
    - voss/harness/session_tree.py lines 97-101 (sessions dir layout `<cwd>/.voss/sessions/<root_id>/<node_id>.json`)
    - V5-PATTERNS.md §"test_board_cli.py" (exact CLI test skeleton + sample node JSON) and §"cli_view.py" (planned render_board return-code contract)
    - V5-RESEARCH.md §"Research Focus 3" (root selection, exit codes) and §"Security Domain" (T-V5-03 path traversal)
  </read_first>
  <action>
    Create `test_board_cli.py` with `class TestBoardCLI`, importing `from voss.harness.cli import board_cmd` (RED now: `board_cmd` does not exist → ImportError at the test method scope; import inside each test method so collection still succeeds, mirroring V5-PATTERNS skeleton which does the import inside methods). Write a small helper that materializes a minimal persisted tree under `tmp_path/.voss/sessions/<root_id>/<node_id>.json` with the real node shape: `{"id": <node>, "root_id": <root>, "transitions": [], "envelope": {"spent": 0, "limit": 100}, "terminal_state": null}`. Tests:
    - test_no_sessions_dir_exits_nonzero: invoke `board_cmd ["--cwd", str(tmp_path)]` with no `.voss` → assert `exit_code != 0`.
    - test_unknown_root_exits_nonzero_with_stderr: create one valid root, invoke `["does-not-exist", "--cwd", str(tmp_path)]` with `CliRunner(mix_stderr=False)` → assert `exit_code != 0` and `result.stderr` non-empty.
    - test_default_latest: materialize a root, invoke `["--cwd", str(tmp_path)]` → assert `exit_code == 0` (use `result.output` in the assert message).
    - test_named_root: invoke `[<root_id>, "--cwd", str(tmp_path)]` → assert `exit_code == 0`.
    - test_default_latest_picks_most_recent: materialize TWO roots; bump the mtime of the second (e.g. `os.utime`); invoke with no root arg → assert exit 0 and that the rendered output references the newer root (assert the newer root_id appears in `result.output`, or that a card unique to the newer root is shown). This pins the mtime-not-lexical rule (V5-RESEARCH Pitfall 3).
    - test_path_traversal_rejected: invoke `["../../etc", "--cwd", str(tmp_path)]` (and a `root_id` containing `/`) → assert `exit_code != 0` (T-V5-03). Do NOT assert a specific message beyond non-empty stderr.
    Module docstring names VBOARD-10 and "Wave 0 RED scaffold". No `xfail`/`skip`.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_board_cli.py --collect-only -q && .venv/bin/python -m pytest tests/harness/board/test_board_cli.py -q --tb=line; test $? -ne 0</automated>
  </verify>
  <acceptance_criteria>
    - `--collect-only` lists `TestBoardCLI` with all six test methods (collection succeeds; `board_cmd` import is inside methods so it does not break collection).
    - Running the file exits NON-zero (RED) because `voss.harness.cli.board_cmd` does not exist yet.
    - Node-JSON fixtures use the REAL shape (`transitions`, `envelope{spent,limit}`, `terminal_state`) — `grep -n "envelope\|transitions\|terminal_state" tests/harness/board/test_board_cli.py` shows all three.
    - `grep -n "xfail\|@pytest.mark.skip" tests/harness/board/test_board_cli.py` returns NOTHING.
    - A path-traversal test (`../..` and a `/`-containing root_id) is present.
  </acceptance_criteria>
  <done>test_board_cli.py collects cleanly, is RED on missing `board_cmd`, fixtures use the real persisted-node shape, path-traversal and mtime-latest cases are encoded, zero masking.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/ --collect-only -q` succeeds (all three new files collect alongside existing suite).
- The three new files are RED for genuine missing-symbol / missing-behavior reasons; no `xfail`/`skip`.
- Existing board suite is unchanged by this plan (only new files added): `.venv/bin/python -m pytest tests/harness/board/ -q --tb=line` still shows the SAME pre-existing single failure baseline (`test_exit_reasons_is_sorted_superset_of_pre_o3`) plus the new RED tests — and NO other previously-green test flips to red.
</verification>

<success_criteria>
- 3 new test files exist under `tests/harness/board/`, collectable, RED for the right reasons, importing the REAL planned symbols (Card new fields, `card_status`/`card_budget`, `board_cmd`).
- Positive-path tests (`test_valid_reviewer_allows_done`) and structural tripwires (`test_no_verdict_injection_path`) are GREEN now and pin invariants.
- Zero `xfail(strict=False)` or `skip` masking anywhere in the new files.
</success_criteria>

<output>
Create `.planning/phases/V5-board-state-machine-supersedes-o3/V5-01-SUMMARY.md` when done.
</output>
