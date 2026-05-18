---
phase: T8-input-bar-ergonomics-v0-2
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - pyproject.toml
  - tests/harness/tui/conftest.py
  - tests/harness/tui/test_input_bar_textarea.py
  - tests/harness/tui/test_prefix_dispatch.py
  - tests/harness/tui/test_reverse_search.py
  - tests/harness/tui/test_paste_image.py
  - tests/harness/tui/snapshots/__init__.py
  - tests/harness/tui/test_slash_palette.py
  - tests/harness/tui/test_full_flow_pilot.py
autonomous: true
requirements: [INPUT-01, INPUT-02, INPUT-03, INPUT-04, INPUT-05]
user_setup: []

must_haves:
  truths:
    - "pytest-textual-snapshot is installed and snap_compare fixture importable in the dev env"
    - "Hermetic episodic-seed fixture and stub-provider fixture exist and are usable by all four T8 test modules"
    - "Existing TUI tests that referenced InputBar.value still collect (migrated to a .text-tolerant access)"
    - "Four T8 test modules collect (red/xfail allowed) — no ImportError, no collection error"
  artifacts:
    - path: "tests/harness/tui/conftest.py"
      provides: "seeded_history + stub_provider + snapshot helper fixtures"
      contains: "def seeded_history"
    - path: "tests/harness/tui/test_input_bar_textarea.py"
      provides: "INPUT-01 red scaffold (TextArea swap + autogrow + slash guard)"
    - path: "tests/harness/tui/test_prefix_dispatch.py"
      provides: "INPUT-02/03 red scaffold (recorder R1/R2 asserts)"
    - path: "tests/harness/tui/test_reverse_search.py"
      provides: "INPUT-04 red scaffold (corpus + search-mode)"
    - path: "tests/harness/tui/test_paste_image.py"
      provides: "INPUT-05 red scaffold (clipboard probe + vision gate)"
    - path: "pyproject.toml"
      provides: "pytest-textual-snapshot dev dependency"
      contains: "pytest-textual-snapshot"
  key_links:
    - from: "tests/harness/tui/conftest.py"
      to: "voss_runtime.memory.episodic.EpisodicMemory"
      via: "seeded_history fixture constructs EpisodicMemory + .add(role='user')"
      pattern: "EpisodicMemory\\("
    - from: "tests/harness/tui/test_*.py"
      to: "pytest_textual_snapshot.snap_compare"
      via: "snapshot tests import the fixture"
      pattern: "snap_compare"
---

<objective>
Establish the T8 test substrate BEFORE any behavior work: install `pytest-textual-snapshot`, create hermetic episodic-seed + stub-provider fixtures, migrate the two existing tests that read `InputBar.value` (which disappears after the TextArea swap), and lay down four red/xfail scaffold test modules so Waves 1-3 have a Nyquist-compliant landing zone.

Purpose: RESEARCH.md Wave-0 Gap + Pitfall 3 + Pitfall 8 — snapshot tests fail until a baseline exists and `.value` references break the moment `input_bar.py` swaps to TextArea. Front-loading this prevents Wave 1 from going dark on verification.
Output: pyproject dev-dep entry, conftest fixtures, 4 scaffold test files, snapshots package dir, 2 migrated existing tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-RESEARCH.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-PATTERNS.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-UI-SPEC.md
@.planning/phases/T8-input-bar-ergonomics-v0-2/T8-VALIDATION.md

<interfaces>
From voss_runtime/memory/episodic.py (VERIFIED):
- `class Turn: role: str  # "user" | "assistant" | "system"`, `content: str`
- `class EpisodicMemory: capacity: int = 20`; `.turns: list[Turn]`; `.add(content: str, *, role: str = "user") -> None`

From tests/harness/tui/test_recorder_bridge.py (analog for recorder mock):
- `def _bridge_with_app() -> tuple[RecorderBridge, MagicMock]` — `RunRecorder.start()` + `MagicMock()` app

pyproject.toml dev block (lines 36-46): list under `[project.optional-dependencies] dev = [...]`; current entries pinned with `>=`. asyncio_mode = "auto" (line 68). testpaths = ["tests"] (line 75).

pytest-textual-snapshot 1.1.0 API (VERIFIED via Textualize GitHub):
- `snap_compare(app, *, press=[...], run_before=async_fn, terminal_size=(cols, rows))` — `app` is a non-running App instance OR a file path string; first run with `--snapshot-update` writes baseline SVGs under a `__snapshots__` dir adjacent to the test file.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add pytest-textual-snapshot to dev deps</name>
  <read_first>
    - pyproject.toml lines 26-46 (the `[project.optional-dependencies] dev = [...]` list — the file being modified)
    - T8-PATTERNS.md §"Snapshot Tests" (Wave 0 step 1: add `"pytest-textual-snapshot>=1.1.0"` after line 40)
    - T8-RESEARCH.md §"Package Legitimacy Audit" (pytest-textual-snapshot APPROVED, first-party Textualize, syrupy pulled transitively APPROVED)
  </read_first>
  <action>Add `"pytest-textual-snapshot>=1.1.0"` as a new entry in the `dev = [...]` list in `pyproject.toml` (alongside the existing `pytest-mock`/`respx`/`vcrpy` entries, before the trailing `chromadb`/`sentence-transformers` block). Do NOT add it to the prod `dependencies` list or the `search` extra. `syrupy` is pulled transitively by pytest-textual-snapshot — do not pin it separately. Then run `python -m pip install -e '.[dev]'` to install it into the active venv. Both packages are APPROVED in the Package Legitimacy Audit — no human checkpoint required.</action>
  <verify>
    <automated>python -c "import pytest_textual_snapshot; from pytest_textual_snapshot import snap_compare; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -v '^#' pyproject.toml | grep -c 'pytest-textual-snapshot'` returns ≥ 1
    - `python -c "import pytest_textual_snapshot"` exits 0
    - `pytest-textual-snapshot` appears only inside the `dev` list, not in `dependencies` (line ~13-24) — `python -c "import tomllib,sys; d=tomllib.load(open('pyproject.toml','rb')); assert 'pytest-textual-snapshot' not in ' '.join(d['project']['dependencies'])"` exits 0
  </acceptance_criteria>
  <done>pytest-textual-snapshot importable in venv; declared only under dev extra.</done>
</task>

<task type="auto">
  <name>Task 2: Hermetic fixtures + migrate existing .value tests</name>
  <read_first>
    - tests/harness/tui/test_recorder_bridge.py lines 1-50 (recorder-mock analog: `RunRecorder.start()` + `MagicMock()`)
    - tests/harness/tui/test_slash_palette.py lines 115-125 (the `input_bar.value` reference that breaks — Pitfall 3)
    - tests/harness/tui/test_full_flow_pilot.py lines 60-72 (the `getattr(input_bar, "value", None)` reference — Pitfall 3)
    - T8-RESEARCH.md Pitfall 3 (TextArea has no `.value`), Pitfall 7 (EpisodicMemory is in-memory only — seed via `.add(role="user")`), §"Validation Architecture > Wave 0 Gaps"
    - T8-PATTERNS.md §"test_reverse_search.py" (`_seeded_history(*user_prompts)` pattern), §"Shared Patterns > pytest.mark.asyncio + app.run_test()"
  </read_first>
  <action>Create `tests/harness/tui/conftest.py` with three fixtures: (1) `seeded_history` — factory returning a function that builds an `EpisodicMemory(capacity=40)` and calls `.add(p, role="user")` for each given prompt (deterministic, in-memory; covers INPUT-04 corpus seeding); (2) `stub_provider` — a minimal object satisfying the provider surface used by recorder-assert tests (T7 stub-provider precedent — no network, no creds), returning a fixed completion; (3) `mock_recorder_bridge` — a `MagicMock()` standing in for `RecorderBridge` with an `emit` attribute, for R1/R2 assertions. Then migrate the two existing breakage sites: in `test_slash_palette.py` change the `input_bar.value` read/write to a helper that prefers `.text` and falls back to `.value` (so the test passes both pre- and post-swap — `getattr` with the new attribute first); in `test_full_flow_pilot.py` change `getattr(input_bar, "value", None)` to also accept `.text`. Do NOT change any other assertion semantics in those two files — surgical edits only, traceable to Pitfall 3.</action>
  <verify>
    <automated>pytest tests/harness/tui/test_slash_palette.py tests/harness/tui/test_full_flow_pilot.py -q -x</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/tui/conftest.py` exists and `grep -c 'def seeded_history' tests/harness/tui/conftest.py` returns 1
    - `pytest tests/harness/tui/test_slash_palette.py tests/harness/tui/test_full_flow_pilot.py -q` exits 0 (both still green against the CURRENT Input-based widget — proving the migration is backward-compatible)
    - `python -c "import ast,sys; ast.parse(open('tests/harness/tui/conftest.py').read())"` exits 0
  </acceptance_criteria>
  <done>conftest fixtures available; both formerly-`.value` tests pass and will keep passing post-TextArea-swap.</done>
</task>

<task type="auto">
  <name>Task 3: Red scaffold test modules + snapshots package</name>
  <read_first>
    - T8-RESEARCH.md §"Validation Architecture > Phase Requirements → Test Map" (the full 17-row map: which anchor/recorder assertion maps to which wave/file)
    - T8-UI-SPEC.md §"Snapshot-Test Anchors" (11 anchors + R1/R2 recorder-event assertions — the acceptance surface)
    - T8-PATTERNS.md §"test_input_bar_textarea.py", §"test_prefix_dispatch.py", §"test_reverse_search.py", §"test_paste_image.py" (per-file analogs + assertion patterns)
    - T8-RESEARCH.md Pitfall 8 (snapshot tests are red until `--snapshot-update`; baseline generated per-wave by the implementing plan, NOT here)
  </read_first>
  <action>Create the four test modules as RED scaffolds (collect cleanly, fail/xfail on assertion): `test_input_bar_textarea.py` (INPUT-01: TextArea swap, Enter=submit/Shift+Enter=newline, autogrow 1-5 rows, slash guard — anchors 1-4), `test_prefix_dispatch.py` (INPUT-02/03: `!cmd` exit-0/non-zero local block, `#note` confirmation, recorder R1 `shell.local` + R2 `memory.note` with payload-field asserts — anchors 5-7), `test_reverse_search.py` (INPUT-04: `_build_corpus` pure-logic dedup/role-filter/recency + Ctrl-R search-mode prompt — anchors 8-9, uses `seeded_history`), `test_paste_image.py` (INPUT-05: `_probe_clipboard_image` None-on-NotImplementedError, `_model_supports_vision` name-gate truth table, no-vision notice + attach indicator — anchors 10-11). Each test references the exact symbol it will exercise and is marked `@pytest.mark.xfail(reason="T8 Wave N — not yet implemented", strict=False)` so the suite stays collectable and the Nyquist sampling map has concrete targets. Create `tests/harness/tui/snapshots/__init__.py` (empty) so the snapshot dir is a package. Do NOT generate baseline SVGs here — each behavior plan runs `--snapshot-update` for its own anchors (Pitfall 8).</action>
  <verify>
    <automated>pytest tests/harness/tui/test_input_bar_textarea.py tests/harness/tui/test_prefix_dispatch.py tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py -q --co</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/tui/test_input_bar_textarea.py tests/harness/tui/test_prefix_dispatch.py tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py --co -q` exits 0 (all four collect, no ImportError/collection error)
    - Running the four files (`pytest <four files> -q`) shows xfail/xpass only — zero `error` outcomes (red is expected, broken is not)
    - `tests/harness/tui/snapshots/__init__.py` exists
    - `grep -l 'seeded_history' tests/harness/tui/test_reverse_search.py` matches (INPUT-04 module wires the corpus fixture)
  </acceptance_criteria>
  <done>Four scaffold modules collect green; all behavior tests present as xfail with concrete target symbols; snapshots package exists.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| dev-dependency install | new package pulled from PyPI into the venv |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T8-01 | Tampering | pytest-textual-snapshot / syrupy install | mitigate | RESEARCH.md Package Legitimacy Audit verified both APPROVED (first-party Textualize, syrupy well-known) via PyPI direct check; pinned `>=1.1.0`; dev-only, never in prod `dependencies` |
| T-T8-02 | Tampering | conftest stub_provider | accept | stub returns a fixed in-process completion; no network, no creds, no shell — zero attack surface (T7 hermetic precedent) |
| T-T8-SC | Tampering | pip install in Task 1 | mitigate | both packages APPROVED in audit table — no `[ASSUMED]`/`[SUS]` packages, no blocking-human checkpoint required; slopcheck false-positive documented in RESEARCH.md (crates.io probe inapplicable to PyPI) |
</threat_model>

<verification>
- `python -c "import pytest_textual_snapshot"` exits 0
- `pytest tests/harness/tui/ -q --co` collects with zero collection errors
- `pytest tests/harness/tui/test_slash_palette.py tests/harness/tui/test_full_flow_pilot.py -q` exits 0 (backward-compatible migration)
</verification>

<success_criteria>
- pytest-textual-snapshot importable; declared dev-only
- conftest exposes seeded_history + stub_provider + mock_recorder_bridge
- Four T8 scaffold modules collect; behavior tests are xfail with concrete targets
- Two formerly-`.value` tests still pass (and will survive the TextArea swap)
</success_criteria>

<output>
Create `.planning/phases/T8-input-bar-ergonomics-v0-2/T8-01-SUMMARY.md` when done
</output>
