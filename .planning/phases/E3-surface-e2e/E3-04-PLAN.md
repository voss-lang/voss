---
phase: E3-surface-e2e
plan: 04
type: execute
wave: 4
depends_on: [E3-03]
files_modified:
  - voss/eval/suite.py
  - voss/eval/runner.py
  - tests/eval/surfaces/01-do-add-function/task.toml
  - tests/eval/surfaces/01-do-add-function/fixture/calc.py
  - tests/eval/surfaces/02-chat-explain/task.toml
  - tests/eval/surfaces/02-chat-explain/fixture/calc.py
  - tests/eval/surfaces/03-edit-add-method/task.toml
  - tests/eval/surfaces/03-edit-add-method/fixture/calc.py
  - tests/eval/surfaces/04-serve-write-file/task.toml
  - tests/eval/surfaces/04-serve-write-file/fixture/.gitkeep
  - tests/eval/surfaces/05-serve-permission-allow/task.toml
  - tests/eval/surfaces/05-serve-permission-allow/fixture/.gitkeep
  - tests/eval/surfaces/06-serve-permission-deny/task.toml
  - tests/eval/surfaces/06-serve-permission-deny/fixture/.gitkeep
  - tests/eval/test_surface_suite_load.py
  - tests/eval/test_task_spec.py
autonomous: false
requirements: [EVSRF-05, EVSRF-06]
must_haves:
  truths:
    - "tests/eval/surfaces/ holds <=6 scenarios covering every surface: cli:do, cli:chat, cli:edit, serve (basic auto-mode turn + permission Allow + permission Deny)"
    - "Each scenario task.toml has a surface field, a rubric, and at least one FALSIFIABLE deterministic [[checks]] entry (no check passes by fixture construction alone)"
    - "run_suite writes the captured final output to .voss-eval-final.txt in the fixture cwd AFTER _file_diff and BEFORE _run_checks, so model output is check-addressable for every surface"
    - "`voss eval --suite surfaces` loads and dispatches all scenarios (proven by a suite-load test, no live model)"
    - "The serve permission Deny scenario drives the driver with choice 'd' via an additive permission_choice field on TaskSpec"
    - "A documented live run on codex auth records >=80% gate_pass, 0 capped, with the permission Allow scenario among the passers (human checkpoint)"
  artifacts:
    - path: "tests/eval/surfaces/05-serve-permission-allow/task.toml"
      provides: "serve scenario that hits an fs_write permission gate and Allows (the marquee proof)"
      contains: "surface = \"serve\""
    - path: "tests/eval/test_surface_suite_load.py"
      provides: "load_suite(surfaces) finds all scenarios + asserts spec.surface values; offline"
      contains: "surfaces"
    - path: "voss/eval/suite.py"
      provides: "additive permission_choice field on TaskSpec for serve Deny scenarios"
      contains: "permission_choice"
    - path: "voss/eval/runner.py"
      provides: "final-output artifact write (.voss-eval-final.txt) between diff and checks"
      contains: "voss-eval-final"
  key_links:
    - from: "voss/eval/runner.py _drive_task serve branch"
      to: "spec.permission_choice"
      via: "await _drive_serve(spec, cwd, permission_choice=spec.permission_choice)"
      pattern: "permission_choice"
    - from: "voss/eval/runner.py run_suite loop"
      to: ".voss-eval-final.txt in fixture cwd"
      via: "write_text(final) after _file_diff, before _run_checks"
      pattern: "voss-eval-final"
    - from: "tests/eval/surfaces/**/task.toml"
      to: "voss eval --suite surfaces"
      via: "load_suite finds dirs with task.toml; runner dispatches by surface"
      pattern: "surface ="
---

<objective>
Author the surfaces suite — <=6 scenarios under `tests/eval/surfaces/` covering every surface at least once (D-01, D-03, EVSRF-05): cli:do, cli:chat, cli:edit, serve-basic (auto mode, genuinely gate-free), serve-permission-Allow (the marquee D-09 proof), serve-permission-Deny. Add the additive `permission_choice` field to TaskSpec so the Deny scenario drives the driver with choice "d", and a final-output artifact write in run_suite so every scenario's checks can assert on model output (gate_pass falsifiable for every scenario per D-11). Prove the suite loads and dispatches offline with a suite-load test. Then run the documented live proof on codex subscription auth (EVSRF-06, D-11) as a human checkpoint — >=80% gate_pass, 0 capped, permission Allow scenario passing — with artifacts recorded in the SUMMARY.

Purpose: The phase's closing act — every runtime entry point proven end-to-end with a real model, hybrid-scored.
Output: 6 scenario dirs (task.toml + fixtures), permission_choice field, final-output artifact write, suite-load test, live-proof checkpoint.

HARD PRECONDITION: E1-03/E1-04 merged; E3-01/02/03 (schema + all four drivers) merged. Wave 4 guarantees this.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E3-surface-e2e/E3-CONTEXT.md
@.planning/phases/E3-surface-e2e/E3-RESEARCH.md
@.planning/phases/E3-surface-e2e/E3-PATTERNS.md
@.planning/phases/E3-surface-e2e/E3-03-SUMMARY.md

<interfaces>
Scenario analog (tests/eval/golden/03-approved-edit/task.toml lines 1-30): prompt, mode, rubric, judge_inputs,
auto_approve_edits, plus [[checks]] tables {type="file_contains",path=...,text=...} / {type="cmd",run=...} / {type="file_exists",path=...}.

TaskSpec now has (from E3-01): surface Literal[...], target_file str|None. This plan adds:
  permission_choice: Literal["a","A","d"] = "a"   # serve-only; default Allow; "d" for the Deny scenario

Fixture prep: _prepare_fixture (runner.py:50-70) copies the fixture dir into a temp git dir and git-inits it.
A fixture needs only its seed files; a serve scenario that writes a NEW file ships an empty fixture (a .gitkeep
so the dir exists and is copied). cli:edit ships the target_file (e.g. calc.py).

Final-output artifact (this plan adds): in run_suite, AFTER `diff = _file_diff(cwd)` and BEFORE
`_run_checks(spec.checks, cwd)`, write the captured final text to `cwd / ".voss-eval-final.txt"`.
Ordering matters: written after diff so it never pollutes the judge's file_diff input; written before
checks so file_contains/cmd checks can assert on model output for ANY surface (incl. read-only cli:chat).

load_suite (suite.py:62-70): returns [(dir_basename, spec)] for every subdir of tests/eval/<suite> that has a task.toml.
`voss eval --suite surfaces` → suite_root = tests/eval/surfaces.

serve permission gating — pinned from source (app.py:186): the server hardcodes
`PermissionGate(mode=mode, auto_yes=False)`; CreateSessionBody has NO auto_approve field, so the task.toml
`auto_approve_edits` key is a NO-OP on the serve surface. Gating is decided by mode alone:
mode="plan" gates fs_write (permission.updated fires; driver replies via /permission with spec.permission_choice);
mode="auto" does not gate (no permission event — genuinely gate-free turn).

D-11 live proof: `VOSS_DEV=1 voss eval --suite surfaces --auth codex` → inspect .voss/eval/<ts>/runs.jsonl + summary.md.
Mirrors E1-05's operator-creds checkpoint. Total scenarios <=10 (here 6) to bound sub burn.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: permission_choice field + final-output artifact + serve Deny wiring + surface scenario dirs</name>
  <files>voss/eval/suite.py, voss/eval/runner.py, tests/eval/test_task_spec.py, tests/eval/surfaces/01-do-add-function/task.toml, tests/eval/surfaces/01-do-add-function/fixture/calc.py, tests/eval/surfaces/02-chat-explain/task.toml, tests/eval/surfaces/02-chat-explain/fixture/calc.py, tests/eval/surfaces/03-edit-add-method/task.toml, tests/eval/surfaces/03-edit-add-method/fixture/calc.py, tests/eval/surfaces/04-serve-write-file/task.toml, tests/eval/surfaces/04-serve-write-file/fixture/.gitkeep, tests/eval/surfaces/05-serve-permission-allow/task.toml, tests/eval/surfaces/05-serve-permission-allow/fixture/.gitkeep, tests/eval/surfaces/06-serve-permission-deny/task.toml, tests/eval/surfaces/06-serve-permission-deny/fixture/.gitkeep</files>
  <read_first>
    - voss/eval/suite.py (TaskSpec from E3-01 with surface/target_file — add permission_choice the same additive way)
    - voss/eval/runner.py (_drive_task serve branch from E3-03 — currently `await _drive_serve(spec, cwd)` default Allow; thread spec.permission_choice through. run_suite loop lines 390-456 — the `diff = _file_diff(cwd)` → `_run_checks` sequence where the final-output artifact write goes)
    - voss/harness/server/app.py (line 186 — `PermissionGate(mode=mode, auto_yes=False)` hardcoded; auto_approve_edits is a no-op on serve; mode decides gating)
    - tests/eval/golden/03-approved-edit/task.toml (FULL — the scenario shape: prompt/mode/rubric/judge_inputs/auto_approve_edits + [[checks]])
    - tests/eval/golden/03-approved-edit/fixture/ (calc.py, main.py — fixture seed shape)
    - tests/eval/test_task_spec.py (the surface field tests from E3-01 — add a permission_choice test in the same style)
    - .planning/phases/E3-surface-e2e/E3-RESEARCH.md (task.toml examples: cli:do lines 200-215, serve permission lines 678-698; Open Question 1 target_file lines 730-733; Open Question 3 cli:edit scope lines 740-743)
    - .planning/phases/E3-surface-e2e/E3-PATTERNS.md (task.toml section lines 271-312)
  </read_first>
  <action>
    (1) voss/eval/suite.py: add `permission_choice: Literal["a", "A", "d"] = "a"` to TaskSpec after target_file (additive; default Allow; serve-only). Add a unit test test_permission_choice_default_and_deny in tests/eval/test_task_spec.py (default == "a"; model_validate with permission_choice="d" → "d"; invalid value rejected).

    (2) voss/eval/runner.py: in the _drive_task serve branch, change to `await _drive_serve(spec, cwd, permission_choice=spec.permission_choice)`. No JSONL row change (permission_choice is input config, not output) → REQUIRED_FIELDS unchanged.

    (3) voss/eval/runner.py: FINAL-OUTPUT ARTIFACT — in the run_suite loop, AFTER `diff = _file_diff(cwd)` and BEFORE `gate_pass, check_results = _run_checks(spec.checks, cwd)`, add `(cwd / ".voss-eval-final.txt").write_text(final or "")`. Ordering is load-bearing: after diff (so the artifact never appears in the judge's file_diff input), before checks (so file_contains/cmd checks can assert on the model's final output for any surface — this makes gate_pass falsifiable for read-only scenarios like cli:chat). Applies to all suites; golden checks don't reference the file, so golden behavior is unchanged. No row change → REQUIRED_FIELDS unchanged.

    (4) Author 6 scenario dirs under tests/eval/surfaces/ (each = task.toml + fixture/). Keep total <=6 (well under the <=10 cap). Each task.toml MUST have surface, mode, rubric, judge_inputs, and >=1 FALSIFIABLE [[checks]] (a check that can fail if the turn does nothing — no check may pass by fixture construction alone):

      01-do-add-function (surface="cli:do", mode="edit", auto_approve_edits=true): fixture/calc.py seed `def add(a, b):\n    return a + b\n`. prompt = ask to add a `def multiply(a, b)` returning a*b to calc.py. checks: file_contains calc.py "def multiply"; cmd `grep -q "def add" calc.py` (don't clobber existing).

      02-chat-explain (surface="cli:chat", mode="plan"): fixture/calc.py same seed. prompt = "Read calc.py and explain in one sentence what the add() function does. Include the word 'sum' in your answer." (non-interactive single turn). checks: cmd `test -s .voss-eval-final.txt` (the turn produced non-empty final output — falsifiable: fails if the chat turn crashed or emitted nothing); file_contains .voss-eval-final.txt "sum" (the instructed token appears in the captured output). rubric: PASS if the explanation correctly describes addition/sum of two values.

      03-edit-add-method (surface="cli:edit", mode="edit", target_file="calc.py"): fixture/calc.py same seed. prompt = add a `def subtract(a, b)` to calc.py. checks: file_contains calc.py "def subtract".

      04-serve-write-file (surface="serve", mode="auto"): empty fixture (.gitkeep). prompt = write hello.py that prints "Hello, World!". checks: file_exists hello.py; file_contains hello.py "print". Basic serve turn: mode="auto" means the server gate auto-allows (app.py:186 PermissionGate(mode="auto") — no permission.updated event fires; genuinely gate-free). Do NOT set auto_approve_edits — it is a no-op on serve (CreateSessionBody has no auto_approve field) and implying otherwise is misleading.

      05-serve-permission-allow (surface="serve", mode="plan", permission_choice="a"): empty fixture (.gitkeep). prompt = write hello.py that prints "Hello, World!" — mode="plan" gates fs_write, the gate fires, the driver Allows via /permission. checks: file_exists hello.py; file_contains hello.py "print". This is the marquee D-09 proof (gate fires → Allow → file written). Scenarios 05 (Allow) + 06 (Deny) are the SOLE permission-flow pair in the suite.

      06-serve-permission-deny (surface="serve", mode="plan", permission_choice="d"): empty fixture (.gitkeep). prompt = write secret.py. checks: cmd `! test -f secret.py` (Deny means the write does NOT happen) — the turn degrades without hanging; rubric: PASS if the model reports it could not write / was denied. This asserts deny-no-hang at the live level (parser-level was E3-03).

    Use `.gitkeep` (empty file) for serve fixtures that start empty so the dir exists and _prepare_fixture copies it.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_task_spec.py -x -q && .venv/bin/python -c "from voss.eval.suite import load_suite; from pathlib import Path; t=load_suite(Path('tests/eval/surfaces'), suite='surfaces'); print(sorted(i for i,_ in t)); assert len(t)==6; assert {s.surface for _,s in t}=={'cli:do','cli:chat','cli:edit','serve'}"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "permission_choice" voss/eval/suite.py` >= 1; default "a"; the new test_permission_choice_* test passes.
    - `grep -c "permission_choice=spec.permission_choice" voss/eval/runner.py` >= 1 (serve dispatch threads the choice).
    - `grep -c "voss-eval-final" voss/eval/runner.py` >= 1, and in run_suite the write_text occurs AFTER the `_file_diff(cwd)` call and BEFORE the `_run_checks(` call (verify by reading the loop).
    - REQUIRED_FIELDS unchanged (permission_choice + the artifact write add no row fields): `.venv/bin/python -m pytest tests/eval/test_voss_eval_stub.py -q` green. Existing golden stub run unaffected: `.venv/bin/python -m pytest tests/eval -q -m 'not live'` green.
    - 6 scenario dirs exist; `load_suite(Path('tests/eval/surfaces'), suite='surfaces')` returns 6 specs; the surface set == {cli:do, cli:chat, cli:edit, serve} (serve appears 3x).
    - Every scenario task.toml has >=1 [[checks]]: `grep -rl "\[\[checks\]\]" tests/eval/surfaces/*/task.toml | wc -l` == 6. No scenario's check set can pass on the untouched fixture alone (falsifiable: 02 requires non-empty .voss-eval-final.txt + "sum"; 01/03/04/05 require model-written content; 06 requires the denied write to be absent after a turn that attempted it).
    - 02-chat-explain's checks reference `.voss-eval-final.txt` (cmd `test -s` + file_contains "sum"); it has NO file_exists check on pre-seeded fixture files.
    - 04-serve-write-file has surface="serve", mode="auto", and NO auto_approve_edits key (no-op on serve); no permission event is expected for it.
    - 05-serve-permission-allow has surface="serve", mode="plan", permission_choice="a"; 06-serve-permission-deny has mode="plan", permission_choice="d" — the sole permission-flow pair.
    - No new packages installed (`git status` shows no lockfile/deps changes).
  </acceptance_criteria>
  <done>permission_choice additive field + serve Deny wiring + final-output artifact write in place; 6 surface scenarios authored covering every surface with falsifiable checks; scenario 04 is genuinely gate-free via mode="auto"; suite loads and validates offline.</done>
</task>

<task type="auto">
  <name>Task 2: Suite-load + dispatch integration test (offline, no live model)</name>
  <files>tests/eval/test_surface_suite_load.py</files>
  <read_first>
    - tests/eval/test_suite_loads.py (FULL — _write_task helper + load_suite assertion pattern; lines 1-50)
    - voss/eval/suite.py (load_suite signature + the new fields)
    - voss/eval/runner.py (_drive_task dispatch — surface routing; the cli:* and serve branches)
    - .planning/phases/E3-surface-e2e/E3-PATTERNS.md (test_surface_suite_load.py section lines 392-428)
    - .planning/phases/E3-surface-e2e/E3-RESEARCH.md (Validation map EVSRF-09 line 788; Wave 0 gaps lines 795-799)
  </read_first>
  <action>
    Create tests/eval/test_surface_suite_load.py (offline — no creds, no live model):

    - test_surfaces_suite_loads_all: load_suite(Path("tests/eval/surfaces"), suite="surfaces"); assert the 6 expected dir ids are found and sorted; assert each spec.surface is the expected value per dir; assert every spec has >=1 check (spec.checks != []).
    - test_surface_dispatch_routes: assert _drive_task routes each surface to the right driver WITHOUT spawning a real subprocess — monkeypatch _drive_cli_do/_drive_cli_chat/_drive_cli_edit/_drive_serve to record which was called and return a canned (final, None, False); call _drive_task for a TaskSpec of each surface and assert the matching driver was invoked, and that surface="internal" does NOT call any of the four (falls through to the existing path — you may assert by checking none of the four monkeypatched drivers were called for an internal spec, guarding the internal spec so it returns early or using a stub provider).
    - test_serve_deny_scenario_choice: load the 06-serve-permission-deny spec and assert spec.permission_choice == "d" and spec.surface == "serve".
    - test_serve_basic_scenario_auto_mode: load the 04-serve-write-file spec and assert spec.mode == "auto" (the gate-free basic serve turn) and spec.surface == "serve".

    Follow the fictional-API guard: import the real driver symbols and assert they exist before monkeypatching; a NameError must fail the test loudly rather than an xfail masking a renamed driver.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_surface_suite_load.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - test_surfaces_suite_loads_all asserts exactly the 6 dir ids and the correct spec.surface per dir, and spec.checks non-empty for all 6.
    - test_surface_dispatch_routes proves cli:do→_drive_cli_do, cli:chat→_drive_cli_chat, cli:edit→_drive_cli_edit, serve→_drive_serve via monkeypatched drivers (no real subprocess), and internal calls none of them.
    - test_serve_deny_scenario_choice asserts the 06 scenario's permission_choice == "d".
    - test_serve_basic_scenario_auto_mode asserts the 04 scenario's mode == "auto".
    - The test runs offline: `.venv/bin/python -m pytest tests/eval/test_surface_suite_load.py -q` green with no credentials.
    - Full eval suite green: `.venv/bin/python -m pytest tests/eval -q -m 'not live'`.
  </acceptance_criteria>
  <done>The surfaces suite loads and dispatches correctly, proven offline; every surface routes to its driver; the Deny scenario's choice and the basic scenario's auto mode are wired.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 3: Live proof run on codex subscription auth (D-11, EVSRF-06)</name>
  <files>(none — verification-only checkpoint; produces .voss/eval/&lt;timestamp&gt;/ artifacts which are git-ignored, no tracked repo files modified)</files>
  <read_first>
    - .planning/phases/E3-surface-e2e/E3-CONTEXT.md (D-11 proof criteria)
    - .planning/phases/E1-eval-substrate/E1-05-SUMMARY.md (the E1 live-proof checkpoint this mirrors — operator creds, artifact recording)
    - tests/eval/surfaces/ (the 6 scenarios authored in Task 1 — what the live run exercises)
  </read_first>
  <action>Pause for the operator to run the live surfaces suite on codex subscription auth: `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite surfaces --auth codex`. The operator confirms the run header prints "6 tasks · max 15 turns/task" before the first model call, then inspects the printed `.voss/eval/&lt;timestamp&gt;/runs.jsonl` for &gt;=80% gate_pass (&gt;=5/6), 0 capped rows, a surface field on every row, the 05-serve-permission-allow row gate_pass=true (gate fired → Allow → hello.py written), and 06-serve-permission-deny completing in bounded time with no secret.py written; and confirms summary.md renders the gate-pass + judge-rate columns. No tracked repo files are written; artifacts land under git-ignored .voss/. This is the E3 phase ship gate (EVSRF-06, D-11). See &lt;how-to-verify&gt; for the exact steps.</action>
  <verify>Human types "approved" after confirming &gt;=80% gate_pass, 0 capped, the permission-Allow scenario passed, and the permission-Deny scenario finished without a 5-minute hang; artifact path + gate-pass count recorded in the SUMMARY.</verify>
  <done>Documented live run on codex auth meets D-11 (&gt;=80% gate_pass, 0 capped, permission-Allow among passers, Deny no-hang); artifacts recorded in the SUMMARY; explicit operator approval logged.</done>
  <what-built>
    The full surfaces suite (6 scenarios across cli:do, cli:chat, cli:edit, serve-basic, serve-permission-Allow, serve-permission-Deny) driving real `voss` entry points end-to-end, hybrid-scored through the E1 substrate. All driver code is proven offline (CLI stub tests, FAKE_TURN serve test, permission parser tests). This checkpoint runs the suite LIVE on operator codex subscription auth — the one step requiring real credentials, mirroring E1-05.
  </what-built>
  <how-to-verify>
    1. Ensure codex subscription auth is available (the same creds E1-05 used): `voss chat --auth=codex` should authenticate.
    2. Run the live suite (the run header prints "6 tasks · max 15 turns/task" before the first model call — confirm sub-burn exposure):
       `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite surfaces --auth codex`
    3. Inspect the artifacts at the printed `.voss/eval/<timestamp>/` path:
       - `runs.jsonl`: confirm >=80% of rows have gate_pass=true (>=5 of 6), `capped` is false on every row (0 capped), and every row carries a `surface` field.
       - Confirm the `05-serve-permission-allow` row has gate_pass=true (the marquee permission proof — gate fired, Allow sent, hello.py written).
       - Confirm `06-serve-permission-deny` completed (no 5-minute hang; the run finished in bounded time) and its check (no secret.py written) passed.
       - `summary.md`: confirm the gate-pass-rate and judge-rate columns render and the per-surface scenarios appear.
    4. Record the artifact path + the gate-pass count + any failing scenario in the SUMMARY.
  </how-to-verify>
  <resume-signal>Type "approved" if >=80% gate_pass, 0 capped, and the permission-Allow scenario passed; otherwise describe which scenarios failed (and paste the failing rows) so a gap-closure plan can address them.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| task.toml permission_choice → serve driver | operator-authored choice; Literal["a","A","d"] constrains it |
| live codex creds → eval run artifacts | the live run uses real subscription auth; artifacts (runs.jsonl/summary.md) must not embed credentials |
| serve Deny scenario → server gate | Deny must degrade the turn without hanging to the 300s server timeout |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E3-12 | Tampering | invalid permission_choice in task.toml | mitigate | Literal["a","A","d"] rejects unknown values at validation (test_permission_choice_*) |
| T-E3-13 | Information | codex creds leaking into runs.jsonl/summary.md from the live run | mitigate | rows record model/judge_model ids + verdicts only (no auth material); _live_env never serialized; checkpoint step inspects artifacts for cleanliness |
| T-E3-14 | Denial | live serve-Deny scenario hanging the run | mitigate | scenario timeout (180s) < server 300s gate timeout; driver always replies "d"; checkpoint confirms the run finished in bounded time |
| T-E3-15 | Denial | unbounded sub burn on the live run | mitigate | E1 max_turns cap (15) + run header prints "6 tasks · max 15 turns/task" before the first model call; total scenarios bounded to 6 (<=10) |
| T-E3-16 | Tampering | non-falsifiable checks producing false-green gate_pass | mitigate | every scenario's checks require model-produced state (.voss-eval-final.txt content, model-written files, or denied-write absence); no check passes on the untouched fixture alone |
| T-E3-SC | Tampering | npm/pip/cargo installs | accept | zero new packages; no install tasks |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval -q -m 'not live'` → full eval suite green (suite-load + dispatch + all driver tests)
- load_suite(surfaces) finds 6 scenarios covering every surface; each has >=1 falsifiable check
- serve Deny scenario wired with permission_choice="d"; serve basic scenario gate-free via mode="auto"
- run_suite writes .voss-eval-final.txt after diff, before checks (golden behavior unchanged)
- LIVE (human checkpoint): `VOSS_DEV=1 voss eval --suite surfaces --auth codex` → >=80% gate_pass, 0 capped, permission-Allow passing; artifacts recorded in SUMMARY
</verification>

<success_criteria>
- <=6 scenarios under tests/eval/surfaces/ covering cli:do/cli:chat/cli:edit/serve(basic-auto + Allow + Deny); each with rubric + >=1 falsifiable check (EVSRF-05, D-01, D-03, D-11)
- additive permission_choice field; serve Deny driven with "d"; 05/06 the sole permission-flow pair
- final-output artifact makes model output check-addressable for every surface; gate_pass falsifiable everywhere
- suite loads + dispatches offline (proven); no new deps
- documented live proof on codex auth: >=80% gate_pass, 0 capped, permission-Allow scenario passing — human checkpoint, artifacts in SUMMARY (EVSRF-06, D-11)
</success_criteria>

<output>
Create `.planning/phases/E3-surface-e2e/E3-04-SUMMARY.md` when done
</output>
