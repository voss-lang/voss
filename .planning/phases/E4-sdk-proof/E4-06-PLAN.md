---
phase: E4-sdk-proof
plan: 06
type: execute
wave: 4
depends_on: [E4-03, E4-04, E4-05]
files_modified:
  - tests/eval/sdk/01-python-basic/task.toml
  - tests/eval/sdk/01-python-basic/fixture/calc.py
  - tests/eval/sdk/02-ts-permission-allow/task.toml
  - tests/eval/sdk/02-ts-permission-allow/fixture/calc.py
  - tests/eval/sdk/03-go-permission-allow/task.toml
  - tests/eval/sdk/03-go-permission-allow/fixture/calc.py
  - tests/eval/sdk/04-rust-permission-allow/task.toml
  - tests/eval/sdk/04-rust-permission-allow/fixture/calc.py
  - tests/eval/test_sdk.py
autonomous: true
requirements: [EVSDK-03, EVSDK-04, EVSDK-05, EVSDK-06]
must_haves:
  truths:
    - "voss eval --suite sdk loads exactly the four sdk scenarios (one per surface) from tests/eval/sdk/<NN>/ with no double-nesting"
    - "Each scenario task.toml declares its surface (sdk:python|sdk:ts|sdk:go|sdk:rust) and validates against TaskSpec (extra=forbid) with the shared shape-agnostic fixture"
    - "All four scenarios use ONE simple fixture shape (a minimal calc.py repo), NOT the E2 py/rust/ts matrix (D-07 shape-agnostic)"
    - "Each consumer (ts/go/rust), driven end-to-end against a FAKE_TURN serve, emits one valid JSON line with all six keys and decodes the typed event stream (event_types_seen contains session.idle); saw_permission_gate=false under FAKE_TURN"
    - "Consumer output is scored by the single E1 substrate: gate (deterministic checks) + judge on the consumer's final; no per-runtime scoring anywhere"
    - "A stub-mode suite run emits one JSONL row per scenario carrying surface=sdk:* with the existing REQUIRED_FIELDS set (E4 adds no new row keys)"
  artifacts:
    - path: "tests/eval/sdk/01-python-basic/task.toml"
      provides: "sdk:python scenario (in-process, public API audit) with checks + rubric"
      contains: "surface = \"sdk:python\""
    - path: "tests/eval/sdk/02-ts-permission-allow/task.toml"
      provides: "sdk:ts scenario (live permission Allow; hermetic-drains-without-gate in stub)"
      contains: "surface = \"sdk:ts\""
    - path: "tests/eval/sdk/03-go-permission-allow/task.toml"
      provides: "sdk:go scenario"
      contains: "surface = \"sdk:go\""
    - path: "tests/eval/sdk/04-rust-permission-allow/task.toml"
      provides: "sdk:rust scenario"
      contains: "surface = \"sdk:rust\""
    - path: "tests/eval/test_sdk.py"
      provides: "suite-load (xfail removed) + stub-mode suite rows + the three consumer end-to-end schema/decode tests (ts/go/rust)"
      contains: "event_types_seen"
  key_links:
    - from: "voss eval --suite sdk"
      to: "tests/eval/sdk/<NN>/task.toml"
      via: "load_suite(suite_root=tests/eval/sdk, suite='sdk') — suite_root.name=='sdk' so used directly (no double-nest)"
      pattern: "suite.*sdk"
    - from: "runner.py _run_checks + judge_run"
      to: "consumer final + file_diff"
      via: "single E1 scoring substrate scores the consumer result (no per-runtime scoring)"
      pattern: "_run_checks|judge_run"
---

<objective>
Wave 3 (EVSDK-06 + the consumer end-to-end proofs EVSDK-03/04/05): create the four SDK suite scenarios on a single shape-agnostic fixture, wire `voss eval --suite sdk` so the runner loads + hybrid-scores them through the single E1 substrate, and prove each consumer (ts/go/rust) end-to-end against a FAKE_TURN serve (the schema + typed-event-decode assertions are consolidated here because this plan owns `tests/eval/test_sdk.py`, keeping the three W2 consumer plans truly parallel). A stub-mode suite run proves all four surfaces emit one JSONL row each (surface=sdk:*) with the existing REQUIRED_FIELDS set — no new row keys, single scoring substrate.

D-07 (shape-agnostic): all four scenarios reuse ONE minimal fixture shape — a flat `calc.py` repo (NOT the E2 py/rust/ts matrix). The SDK contract (REST/SSE/typed events/permission/readers) is identical regardless of the target repo; the repo-shape axis is owned by E2. Crossing SDK x shapes = pure subscription burn for zero new SDK-contract signal.

Pitfall 7 (suite double-nesting): scenarios live at `tests/eval/sdk/<NN>-<slug>/task.toml` directly. `run_suite` computes `suite_root = project_root / tests/eval / sdk` then `load_suite(suite_root, suite="sdk")`; because `suite_root.name == "sdk"`, `load_suite` uses it directly (no `sdk/sdk/` nesting).

Permission gate (D-03): the ts/go/rust scenarios are the permission-Allow marquee path. In STUB mode (FAKE_TURN) they drain to idle with `saw_permission_gate=false` — the deterministic checks for the stub path assert only SSE plumbing + the consumer's JSON emission, NOT the gate. The live Allow/Deny round-trip is plan 07 (EVSDK-07, operator checkpoint). Scenario task.tomls MUST NOT encode a stub-mode assertion that the gate fired.

Purpose: Make the four surfaces a single runnable, hybrid-scored suite on one shape-agnostic fixture + prove each consumer end-to-end hermetically; single E1 substrate; no new JSONL fields.
Output: four task.tomls + shared fixture + suite-load/stub-row tests + three consumer schema/decode tests.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E4-sdk-proof/E4-CONTEXT.md
@.planning/phases/E4-sdk-proof/E4-RESEARCH.md
@.planning/phases/E4-sdk-proof/E4-PATTERNS.md
@.planning/phases/E4-sdk-proof/E4-VALIDATION.md

<interfaces>
<!-- TaskSpec fields a task.toml may set (suite.py, extra="forbid"): -->
//   prompt(str, required), mode("plan"|"edit"|"auto", required), rubric(str, required),
//   judge_inputs(list of "final"|"file_diff"), provider, model, auto_approve_edits(bool),
//   tools(list), checks(list of AnyCheck), surface(...sdk:python|sdk:ts|sdk:go|sdk:rust), target_file(str|None)
// Every key in task.toml MUST be a declared field (extra=forbid). (permission_choice is added by plan 07.)

<!-- AnyCheck types (tests/eval/golden/03-approved-edit/task.toml is the reference): -->
//   [[checks]] type="file_contains" path="calc.py" text="sum_two"
//   [[checks]] type="cmd" run="! grep -q 'def add(' calc.py"

<!-- load_suite (suite.py:63-70): suite_dir = suite_root if suite_root.name==suite or suite=="" else suite_root/suite -->
<!-- run_suite (runner.py ~570): suite_root = project_root / SUITE_ROOT / suite; SUITE_ROOT = Path("tests/eval") -->
<!-- so `--suite sdk` -> suite_root = tests/eval/sdk, suite_root.name=="sdk" -> used directly (Pitfall 7 avoided) -->

<!-- _drive_sdk_client (plan 02) spawns serve + the consumer. For the consumer schema tests, factor a test-local _spawn_fake_serve(cwd) helper (Popen voss serve with VOSS_SERVE_FAKE_TURN, parse {port,token}, kill); do NOT add it to runner.py. -->

<!-- run_suite row already includes "surface": spec.surface (E3-01). REQUIRED_FIELDS (test_voss_eval_stub.py) already has "surface". E4 adds NO new row keys. -->
<!-- FAKE_TURN final = "echo: <prompt>"; emits server.connected -> final -> session.idle, NO permission.updated. -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Four sdk task.tomls + one shape-agnostic fixture</name>
  <files>tests/eval/sdk/01-python-basic/task.toml, tests/eval/sdk/01-python-basic/fixture/calc.py, tests/eval/sdk/02-ts-permission-allow/task.toml, tests/eval/sdk/02-ts-permission-allow/fixture/calc.py, tests/eval/sdk/03-go-permission-allow/task.toml, tests/eval/sdk/03-go-permission-allow/fixture/calc.py, tests/eval/sdk/04-rust-permission-allow/task.toml, tests/eval/sdk/04-rust-permission-allow/fixture/calc.py</files>
  <read_first>
    - tests/eval/golden/03-approved-edit/task.toml (the full task.toml field set with [[checks]] — the analog; rubric + judge_inputs + auto_approve_edits + checks)
    - tests/eval/golden/02-plan-only/task.toml (a plan-mode scenario shape — for the python read-only/plan scenario)
    - voss/eval/suite.py (TaskSpec fields + extra="forbid" — confirm every task.toml key is a declared field; the surface Literal now includes sdk:*)
    - tests/eval/matrix/py-01-analyze/fixture/ (the E2 minimal calc fixture shape — a flat calc.py repo; the SDK fixture is ONE such shape, NOT the full matrix)
    - .planning/phases/E4-sdk-proof/E4-PATTERNS.md (task.toml section lines 247-309 — the sdk scenario task.toml pattern incl. the surface field + the stub-placeholder check note; Pitfall 7 suite-dir placement)
    - .planning/phases/E4-sdk-proof/E4-RESEARCH.md (Recommended Project Structure lines 489-518 — the tests/eval/sdk/ layout; D-07 shape-agnostic lines 38-39)
  </read_first>
  <action>
    Create the four scenario dirs under tests/eval/sdk/, each with a task.toml + a fixture/ holding ONE shared minimal shape (a flat calc.py repo — copy the same fixture/calc.py into all four; a single typed function, e.g. `def add(a, b): return a + b`, no src/, no pip install — mirror the E2 py-01 minimal flat shape). Keep each fixture <= a couple files (D-01 minimalism).

    01-python-basic/task.toml: surface = "sdk:python"; mode = "edit"; auto_approve_edits = true; prompt asks to add a function `sum_two(a, b)` returning a + b to calc.py; rubric PASS if calc.py defines sum_two returning a+b; judge_inputs = ["final", "file_diff"]; [[checks]] file_contains path="calc.py" text="sum_two". (In-process public-API audit; no serve.)

    02-ts-permission-allow/task.toml: surface = "sdk:ts"; mode = "plan"; prompt asks the agent to use a shell command to print the working directory (a gated tool call in live mode); rubric PASS if the final reports the working directory path AND (live) the permission gate was exercised; judge_inputs = ["final"]. For the STUB path the deterministic check must assert only the consumer plumbing, NOT the gate. Add a task.toml comment: "Permission gate is exercised LIVE (plan 07). In stub/FAKE_TURN the consumer drains to idle with saw_permission_gate=false; checks here must not assert the gate fired."

    03-go-permission-allow/task.toml: identical to 02 but surface = "sdk:go".
    04-rust-permission-allow/task.toml: identical to 02 but surface = "sdk:rust".

    Every task.toml key MUST be a declared TaskSpec field (extra=forbid). Do NOT add a stub-only check that asserts saw_permission_gate is true (that is live-only). Keep the four scenarios = exactly the four surfaces (plan 07 adds the live Deny variant on top, total 5, within the <= ~8 sub-burn budget).
  </action>
  <verify>
    <automated>.venv/bin/python -c "import sys; from pathlib import Path; from voss.eval.suite import load_suite; t=load_suite(Path('tests/eval/sdk'), suite='sdk'); print(sorted(i for i,_ in t)); sys.exit(0 if len(t)==4 and all(s.surface.startswith('sdk:') for _,s in t) else 1)"</automated>
  </verify>
  <acceptance_criteria>
    - `load_suite(Path('tests/eval/sdk'), suite='sdk')` returns exactly 4 (task_id, spec) pairs, each with `spec.surface` in {sdk:python, sdk:ts, sdk:go, sdk:rust}.
    - No double-nesting: `ls tests/eval/sdk/*/task.toml | wc -l` == 4 (not tests/eval/sdk/sdk/...).
    - Each task.toml validates (extra=forbid): the load_suite call above does not raise.
    - The four fixtures share one shape: each of the four scenario dirs has a fixture/calc.py; the matrix py/rust/ts cross-product is NOT used (no rust/ts fixture dirs under tests/eval/sdk/).
    - No stub-only gate assertion: `grep -rc "saw_permission_gate.*true\|saw_permission_gate = true" tests/eval/sdk/*/task.toml` == 0.
    - Surfaces present once each: `grep -rl "surface = \"sdk:python\"\|surface = \"sdk:ts\"\|surface = \"sdk:go\"\|surface = \"sdk:rust\"" tests/eval/sdk/*/task.toml | wc -l` == 4.
  </acceptance_criteria>
  <done>Four sdk scenarios (one per surface) load via --suite sdk with no double-nesting on a single shape-agnostic calc.py fixture; extra=forbid satisfied; no stub-only gate assertion.</done>
</task>

<task type="auto">
  <name>Task 2: Three consumer end-to-end schema/decode tests (FAKE_TURN)</name>
  <files>tests/eval/test_sdk.py</files>
  <read_first>
    - tests/eval/test_sdk.py (the W0/W1 scaffold + the plan-02 `test_drive_sdk_client_{ts,go,rust}_stub` tests — extend with full-schema assertions; the build tests confirm the consumers compile)
    - voss/eval/runner.py (`_drive_sdk_client` from plan 02 — the serve-spawn + per-consumer run command + cwd; the tests assert the consumer's FULL JSON, so they spawn a FAKE_TURN serve via a test-local helper and run each consumer directly capturing its stdout)
    - tests/eval/test_surface_drivers.py (the stub-mode driver-test + tmp_path fixtures)
    - voss/harness/server/app.py (lines 166-178 — FAKE_TURN canned final "echo: <prompt>" + no permission.updated)
    - .planning/phases/E4-sdk-proof/E4-VALIDATION.md (EVSDK-03/04/05 rows: each consumer emits valid JSON with final/saw_permission_gate/event_types_seen; stub asserts NO permission gate)
    - crates/voss-sdk/tests/integration.rs (line 224 the FAKE_TURN-no-permission comment — saw_permission_gate=false is correct in stub)
  </read_first>
  <action>
    Add a test-local helper `_spawn_fake_serve(cwd)` to tests/eval/test_sdk.py (mirrors the runner's serve-spawn: Popen `[sys.executable,"-m","voss.cli","serve"]` with VOSS_SERVE_FAKE_TURN=1 + LITELLM_LOCAL_MODEL_COST_MAP + VOSS_DEV in env, stdin=PIPE, parse the {port,token} handshake with a 60s deadline, return (proc, base_url, token); a `_kill_serve(proc)` that closes stdin, waits, kills). Keep it test-local; do NOT add to runner.py.

    Add three end-to-end schema/decode tests, each skipif the toolchain (node/go/cargo) is absent and marked `@pytest.mark.slow` if the marker exists:
      test_ts_consumer_output_schema (skipif node absent): _spawn_fake_serve, build consumer_env (VOSS_BASE_URL/VOSS_TOKEN/VOSS_CWD/VOSS_PROMPT/VOSS_MODE), subprocess.run(["node","tests/eval/sdk/consumers/ts/consumer.js"], env, timeout=120), parse the LAST stdout JSON line. Assert: key set == {"surface","session_id","final","saw_permission_gate","cost_usd","event_types_seen"}; surface=="sdk:ts"; final is a str containing "echo"; saw_permission_gate is False; event_types_seen is a list containing "session.idle". finally _kill_serve.
      test_go_consumer_output_schema (skipif go absent): same, but subprocess.run(["go","run","."], cwd="tests/eval/sdk/consumers/go", timeout=180); surface=="sdk:go".
      test_rust_consumer_output_schema (skipif cargo absent): same, but subprocess.run(["cargo","run","--manifest-path","crates/voss-sdk/Cargo.toml","--example","sdk_proof_consumer","--quiet"], timeout=300); surface=="sdk:rust"; parse the LAST json-decodable stdout line (tolerate cargo build chatter).

    Each test comment: "Hermetic: FAKE_TURN -> server.connected/final/session.idle, NO permission.updated. saw_permission_gate=false is correct (RESEARCH Pitfall 3). The live Allow/Deny round-trip is EVSDK-07 (operator checkpoint, plan 07)." If plan 02 left `test_drive_sdk_client_*_stub` tests asserting only the returned `final`, keep them; these three are the COMPLEMENT asserting the full six-key schema + typed-event decode.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_sdk.py::test_ts_consumer_output_schema tests/eval/test_sdk.py::test_go_consumer_output_schema -q 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - The three schema tests exist by name: `grep -E "def test_ts_consumer_output_schema|def test_go_consumer_output_schema|def test_rust_consumer_output_schema" tests/eval/test_sdk.py` returns 3 lines.
    - ts + go schema tests pass (skipped only if the toolchain is absent — node/go ARE present): `.venv/bin/python -m pytest tests/eval/test_sdk.py -k "consumer_output_schema and not rust" -q` reports 0 failed.
    - The rust schema test passes or is skipped only if cargo absent (cargo IS present): `.venv/bin/python -m pytest tests/eval/test_sdk.py::test_rust_consumer_output_schema -q` reports 0 failed.
    - Each test asserts the exact six-key set + the correct surface + saw_permission_gate False under FAKE_TURN: `grep -c "saw_permission_gate" tests/eval/test_sdk.py` >= 3 and `grep -c "event_types_seen" tests/eval/test_sdk.py` >= 3.
    - The rust test tolerates cargo build chatter (parses the last JSON-decodable line, not blindly splitlines()[-1]).
    - No serve orphan: `_spawn_fake_serve`/`_kill_serve` are used and the serve subprocess is killed in a finally in each test.
  </acceptance_criteria>
  <done>Each consumer (ts/go/rust) is proven end-to-end against a FAKE_TURN serve: emits the six-key JSON schema, decodes the typed event stream (event_types_seen contains session.idle), and reports saw_permission_gate=false (live gate deferred to plan 07).</done>
</task>

<task type="auto">
  <name>Task 3: Suite-load + stub-mode suite rows (single scoring substrate)</name>
  <files>tests/eval/test_sdk.py</files>
  <read_first>
    - tests/eval/test_sdk.py (the W0 `test_sdk_suite_loads` xfail stub — remove the xfail now that the scenarios exist; reuse the `_run_eval` helper)
    - tests/eval/test_voss_eval_stub.py (lines 42-100 — the `_run_eval` subprocess helper + the `set(row) == REQUIRED_FIELDS` row assertion + `_read_rows`; the stub-mode suite-run pattern)
    - voss/eval/runner.py (lines ~560-600 run_suite — the row dict already carries "surface"; --suite/--stub/--task/-k/--out flags; the suite_root computation)
    - voss/harness/server/app.py (lines 166-178 — FAKE_TURN for the ts stub row)
    - .planning/phases/E4-sdk-proof/E4-VALIDATION.md (EVSDK-10 row: voss eval --suite sdk loads N scenarios; the stub-run sampling)
  </read_first>
  <action>
    In tests/eval/test_sdk.py:
      - Remove the xfail from `test_sdk_suite_loads` and make it real: assert `load_suite(Path('tests/eval/sdk'), suite='sdk')` returns 4 scenarios with the four sdk:* surfaces.
      - Add `test_sdk_python_stub_row`: run the runner in STUB mode for the sdk:python scenario only (in-process; no serve) via the `_run_eval` helper with `["--suite","sdk","--stub","--auth","none","--task","01-python-basic","-k","1","--out", out]`; read runs.jsonl; assert exactly 1 row; `set(row) == REQUIRED_FIELDS` (no new keys — single scoring substrate, E4 added none); `row["surface"] == "sdk:python"`.
      - Add `test_sdk_client_stub_row` (skipif node absent, mark slow): run the runner in STUB mode for the sdk:ts scenario with VOSS_SERVE_FAKE_TURN=1 in the env passed to `_run_eval` (so the runner-spawned serve uses the fake turn); assert 1 row, `set(row) == REQUIRED_FIELDS`, `row["surface"] == "sdk:ts"`. (This proves the full --suite -> _drive_sdk_client -> consumer -> E1 scoring path emits a clean additive row through the single substrate.)
      - Add a comment: "E4 adds NO new JSONL row keys; the consumer result feeds the existing final/gate_pass/judge path (single E1 substrate). REQUIRED_FIELDS unchanged from E3-01."
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_sdk.py::test_sdk_suite_loads tests/eval/test_sdk.py::test_sdk_python_stub_row -x -q 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - `test_sdk_suite_loads` passes (xfail removed): `.venv/bin/python -m pytest tests/eval/test_sdk.py::test_sdk_suite_loads -q` reports 0 failed.
    - `test_sdk_python_stub_row` passes: one JSONL row, `set(row) == REQUIRED_FIELDS`, `row["surface"] == "sdk:python"`.
    - `test_sdk_client_stub_row` passes or is skipped only if node absent (node IS present): one row with `row["surface"] == "sdk:ts"` and the exact REQUIRED_FIELDS set.
    - The no-new-JSONL-fields invariant is asserted: `grep -c "REQUIRED_FIELDS" tests/eval/test_sdk.py` >= 1.
    - `git diff tests/eval/test_voss_eval_stub.py` shows REQUIRED_FIELDS unchanged (E4 added no JSONL fields).
    - Full eval suite has no new regression: `.venv/bin/python -m pytest tests/eval -q -m 'not live' 2>&1 | tail -3` (pre-existing E2 matrix RED excepted; the sdk tests green, EVSDK-07 still live-only-skip).
  </acceptance_criteria>
  <done>--suite sdk loads the four scenarios; stub-mode rows for sdk:python and sdk:ts carry surface=sdk:* with the exact REQUIRED_FIELDS set; single E1 scoring substrate confirmed; no new JSONL fields.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| task.toml (operator-authored) -> TaskSpec validation | surface + checks are operator input; extra=forbid + Literal + AnyCheck constrain the value space |
| suite loader path -> filesystem | load_suite reads tests/eval/sdk/<NN>/task.toml; the suite-root name check prevents double-nesting traversal |
| consumer result -> E1 gate/judge | the single E1 substrate scores the consumer's final + file_diff; no per-runtime scoring branch |
| test-local _spawn_fake_serve -> loopback serve | the schema tests spawn a FAKE_TURN serve on 127.0.0.1 and kill it in finally; no orphan, no provider call |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E4-18 | Tampering | unknown key / surface in a task.toml | mitigate | extra=forbid rejects unknown keys; surface Literal rejects non-sdk values; load_suite raises on invalid (test asserts 4 valid loads) |
| T-E4-19 | Tampering | stub-mode scenario asserting the gate fired (false signal) | mitigate | task.tomls carry no saw_permission_gate=true stub check (grep-gated); the gate is live-only (plan 07) |
| T-E4-20 | Denial | suite double-nesting loading zero/duplicate scenarios | mitigate | scenarios placed at tests/eval/sdk/<NN>/ directly; load_suite uses suite_root when name=="sdk" (Pitfall 7); test asserts exactly 4 |
| T-E4-26 | Denial | test-local fake serve orphaned after a schema test | mitigate | _kill_serve closes stdin -> wait -> kill in a finally in every schema test; subprocess timeouts bound the consumer |
| T-E4-SC | Tampering | npm/pip/cargo installs | accept | E4 introduces zero new packages; scenarios are toml + a calc.py fixture; the consumers were built in W0/W2; no install task |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/test_sdk.py -q` -> suite-load + stub-row + three consumer schema tests green (EVSDK-07 still live-only-skip)
- `voss eval --suite sdk` loads exactly 4 scenarios (one per surface) with no double-nesting
- each consumer (ts/go/rust) proven end-to-end against FAKE_TURN: six-key JSON + typed-event decode + saw_permission_gate=false
- stub-mode rows for sdk:python + sdk:ts carry surface=sdk:* with the exact REQUIRED_FIELDS set (no new JSONL fields)
- single E1 scoring substrate (gate + judge on consumer final); no per-runtime scoring
- `.venv/bin/python -m pytest tests/eval -q -m 'not live'` -> no new regression (pre-existing E2 matrix RED excepted)
</verification>

<success_criteria>
- EVSDK-06: sdk task.tomls (one per surface) + suite wiring; voss eval --suite sdk loads + hybrid-scores them via the single E1 substrate on one shape-agnostic fixture (D-07)
- EVSDK-03/04/05: each consumer proven end-to-end against FAKE_TURN (six-key schema + typed-event decode), consolidated here (owns test_sdk.py) to keep the W2 consumer plans parallel
- no new JSONL row keys (REQUIRED_FIELDS unchanged); suite double-nesting avoided (Pitfall 7); no stub-only gate assertion (gate is live-only)
</success_criteria>

<output>
Create `.planning/phases/E4-sdk-proof/E4-06-SUMMARY.md` when done
</output>
