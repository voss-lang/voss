---
phase: E4-sdk-proof
plan: 02
type: execute
wave: 2
depends_on: [E4-01, E3-01]
files_modified:
  - voss/eval/suite.py
  - voss/eval/runner.py
  - tests/eval/test_sdk.py
autonomous: true
requirements: [EVSDK-01, EVSDK-02]
must_haves:
  truths:
    - "TaskSpec.surface accepts sdk:python, sdk:ts, sdk:go, sdk:rust and still defaults to internal (existing surfaces + golden tasks unchanged)"
    - "_drive_task dispatches surface=sdk:python to an in-process driver that calls run_turn and returns TurnResult.final"
    - "_drive_task dispatches surface=sdk:ts|sdk:go|sdk:rust to _drive_sdk_client which spawns voss serve, then spawns the matching consumer subprogram, reads the consumer's JSON, and returns the final text"
    - "_drive_sdk_client pre-spawns voss serve (60s handshake) and passes VOSS_BASE_URL/VOSS_TOKEN/VOSS_CWD/VOSS_PYTHON/VOSS_PROMPT/VOSS_MODE to the consumer via env — the consumer never self-launches the server (TS 10s timeout pitfall avoided)"
    - "_drive_sdk_client sets VOSS_PYTHON to the absolute interpreter path for the go consumer (interpreterPath CWD pitfall)"
    - "_drive_sdk_python imports run_turn/PermissionGate from voss.harness public __all__ (PlainRenderer/make_toolset are the documented private exceptions, commented as the M7 SDK gap)"
    - "The serve subprocess is always killed in a finally block (stdin EOF heartbeat then wait, kill on timeout) — no orphaned server"
    - "E4 adds NO new JSONL row fields: REQUIRED_FIELDS sentinel is unchanged (consumer result feeds the existing final/gate_pass paths)"
  artifacts:
    - path: "voss/eval/suite.py"
      provides: "surface Literal extended with sdk:python|sdk:ts|sdk:go|sdk:rust (additive, extra=forbid safe)"
      contains: "sdk:python"
    - path: "voss/eval/runner.py"
      provides: "_drive_sdk_python in-process driver + _drive_sdk_client subprocess driver + sdk:* dispatch branches"
      contains: "_drive_sdk_client"
    - path: "tests/eval/test_sdk.py"
      provides: "surface-accepts-sdk-values test (xfail removed) + sdk:python/ts/go/rust stub driver tests (xfail removed for the ones provable hermetically)"
      contains: "_drive_sdk_python"
  key_links:
    - from: "voss/eval/runner.py _drive_task"
      to: "spec.surface == sdk:python"
      via: "dispatch branch → _drive_sdk_python; returns (record, final, None, False)"
      pattern: "sdk:python"
    - from: "voss/eval/runner.py _drive_task"
      to: "spec.surface in sdk:ts|sdk:go|sdk:rust"
      via: "dispatch branch → _drive_sdk_client(consumer=surface.split(':')[1])"
      pattern: "_drive_sdk_client"
    - from: "voss/eval/runner.py _drive_sdk_client"
      to: "voss serve subprocess + consumer subprocess"
      via: "Popen serve → parse handshake → spawn consumer with VOSS_BASE_URL/VOSS_TOKEN env → read JSON final"
      pattern: "VOSS_BASE_URL"
---

<objective>
Wave 1 keystone (EVSDK-01, EVSDK-02): extend the E3-01-owned `surface` Literal with the four `sdk:*` values and wire two new drivers into `_drive_task` — `_drive_sdk_python` (in-process, public-API-only) and `_drive_sdk_client` (spawns `voss serve` + the W0 consumer subprogram, reads the consumer's structured JSON, returns the final text). This is the single plan that touches `suite.py` and `runner.py`; the W2 consumer plans only touch their own consumer dirs.

E3-03 (the `serve` driver) is NOT executed on this checkout, so there is no `_drive_serve` to reuse — this plan writes its own serve-spawn lifecycle inside `_drive_sdk_client` from the PATTERNS Pattern 3 / E3-RESEARCH serve-spawn pattern (Popen `python -m voss.cli serve` with stdin=PIPE heartbeat, 60s handshake parse of `{v,port,token}`, drain-stderr thread, kill-in-finally). The serve `serve` surface branch (line 359-366) stays exactly as E3-03 left it — DO NOT implement or alter it; that is E3-03's territory.

DEPENDENCY (Option a — satisfied): `depends_on: [E4-01, E3-01]`. E3-01 already shipped the `surface` Literal at `suite.py:55` and owns it; E4 extends it additively. E4-01 shipped the three consumer subprograms `_drive_sdk_client` spawns. No `suite.py:55` literal conflict — E3-01 is the sole owner of the literal's existence; E4 appends values.

Purpose: One additive Literal extension + two drivers; internal/cli:*/serve/golden behavior unchanged.
Output: extended surface Literal, `_drive_sdk_python`, `_drive_sdk_client`, sdk:* dispatch, hermetic driver tests.
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
<!-- suite.py:55 TODAY (E3-01, executed) — extra="forbid"; extend the Literal in place: -->
surface: Literal["internal", "cli:do", "cli:chat", "cli:edit", "serve"] = "internal"
target_file: str | None = None
<!-- E4 extends to: Literal["internal","cli:do","cli:chat","cli:edit","serve","sdk:python","sdk:ts","sdk:go","sdk:rust"] -->

<!-- runner.py _drive_task TODAY (lines 335-394, executed E3-01/E3-02) — sequential `if spec.surface == ...` returns,
     then the `if task_id.startswith("05-")` resume branch, then the internal run_turn else. Add sdk:* branches
     BEFORE the `if task_id.startswith("05-")` fallthrough (after the `if spec.surface == "serve":` block): -->
async def _drive_task(task_id, spec, *, cwd, provider, model, stub=False, max_turns=15)
    -> tuple[SessionRecord, str, str | None, bool]:   # (record, final, crash_reason_or_None, capped)

<!-- _drive_resume is the model for the in-process renderer/toolset call shape (runner.py lines 276-332):
     run_turn(spec.prompt, tools=make_toolset(cwd, net=...), cwd=cwd, renderer=PlainRenderer(),
              model=model, provider=provider, history=EpisodicMemory(capacity=40), permissions=permissions) -->

<!-- _live_env helper (runner.py:200-208, executed E3-02) — reuse its env-base for the serve + consumer spawn:
     dict(os.environ) + LITELLM_LOCAL_MODEL_COST_MAP=true + VOSS_DEV=1 + offline guards -->

<!-- run_suite row dict (runner.py ~562) already appends "surface": spec.surface (E3-01). E4 adds NO new row keys.
     REQUIRED_FIELDS sentinel (test_voss_eval_stub.py:11-35) already contains "surface" — leave it unchanged. -->

<!-- Imports present at runner.py top: asyncio, json, os, subprocess, sys, time; run_turn, PlainRenderer,
     make_toolset, PermissionGate, SessionRecord; EpisodicMemory, configure, get_config. Add `threading` if absent. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend surface Literal + _drive_sdk_python in-process driver</name>
  <files>voss/eval/suite.py, voss/eval/runner.py, tests/eval/test_sdk.py</files>
  <behavior>
    - TaskSpec(prompt="x", mode="plan", rubric="r", surface="sdk:python").surface == "sdk:python"; same for sdk:ts/sdk:go/sdk:rust
    - TaskSpec(... surface="internal") still defaults/validates; golden tasks (no surface key) still load 6
    - TaskSpec.model_validate({... surface:"sdk:bogus"}) raises pydantic.ValidationError
    - _drive_sdk_python(spec, cwd=..., provider=StubProvider, model=None) returns a non-empty final string for a stub turn (proves run_turn drives via public symbols)
  </behavior>
  <read_first>
    - voss/eval/suite.py (FULL — 72 lines; surface field line 55, target_file line 56, ConfigDict extra="forbid" line 44, Literal import)
    - voss/eval/runner.py (lines 276-332 `_drive_resume` — the in-process run_turn call shape to mirror; lines 1-40 imports; lines 200-208 `_live_env`)
    - voss/harness/__init__.py (the `__all__` list — confirm run_turn/PermissionGate/TurnResult are public; PlainRenderer/make_toolset are NOT in __all__ → documented private exception)
    - docs/sdk.md (the public Python surface symbols an external embedder uses — the audit target; the NullRenderer/PlainRenderer "Known gaps" note)
    - .planning/phases/E4-sdk-proof/E4-PATTERNS.md (Pattern 2 `_drive_sdk_python` lines 97-130; Pitfall 6 private-symbols guard)
    - .planning/phases/E4-sdk-proof/E4-RESEARCH.md (sdk:python public API map lines 100-122; Pitfall 6 lines 388-392)
    - tests/eval/test_surface_drivers.py (the stub-mode driver-test pattern: construct TaskSpec, asyncio.run(_drive_*), assert tuple)
  </read_first>
  <action>
    (1) In voss/eval/suite.py extend the existing `surface` Literal (line 55) IN PLACE to add the four values:
        surface: Literal["internal", "cli:do", "cli:chat", "cli:edit", "serve", "sdk:python", "sdk:ts", "sdk:go", "sdk:rust"] = "internal"
        Touch nothing else (target_file, ConfigDict, load_task, load_suite unchanged). extra="forbid" is satisfied — surface is an existing declared field gaining Literal members.

    (2) In voss/eval/runner.py add `_drive_sdk_python` near `_drive_resume`. It mirrors the in-process run_turn call but imports ONLY from the public surface, with the two documented private exceptions commented:
        - `from voss.harness import run_turn, PermissionGate` (public __all__)
        - `from voss.harness.render import PlainRenderer  # private — documented M7 SDK gap (docs/sdk.md "Known gaps — NullRenderer")`
        - `from voss.harness.tools import make_toolset  # private — runner-internal; acceptable (same path as _drive_task)`
        - `from voss_runtime import EpisodicMemory, configure, get_config` (public)
        Signature: `async def _drive_sdk_python(spec, *, cwd, provider, model, max_turns=15) -> str`. Body: snapshot get_config(), configure(max_iterations=max_turns), build `PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)`, `result = await run_turn(spec.prompt, tools=make_toolset(cwd), cwd=cwd, renderer=PlainRenderer(), model=model, provider=provider, history=EpisodicMemory(capacity=40), permissions=permissions)`, restore config in finally, `return result.final`. Add a module-level comment block above it: "sdk:python proves the docs/sdk.md public embedder surface (D-04). It is in-process like `internal` but restricts itself to voss.harness/voss_runtime public __all__ symbols; PlainRenderer + make_toolset are the documented M7 private gap."

    (3) In tests/eval/test_sdk.py: REMOVE the xfail from `test_surface_accepts_sdk_python_ts_go_rust` and make it a real test asserting all four sdk:* values validate + a sdk:bogus raises ValidationError + golden still loads 6. REMOVE the xfail from `test_drive_sdk_python_stub` and make it real: build a tmp fixture dir, construct a StubProvider via `voss_runtime.providers.StubProvider`, `final = asyncio.run(_drive_sdk_python(spec, cwd=tmp, provider=stub, model=None))`, assert `final` is a non-empty str. (Mirror the `test_cli_*_stub` shape in test_surface_drivers.py.)
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_sdk.py::test_surface_accepts_sdk_python_ts_go_rust tests/eval/test_sdk.py::test_drive_sdk_python_stub tests/eval/test_task_spec.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "sdk:python" voss/eval/suite.py` >= 1 and the Literal contains all four sdk:* values: `.venv/bin/python -c "from voss.eval.suite import TaskSpec; [TaskSpec(prompt='x',mode='plan',rubric='r',surface=s) for s in ('sdk:python','sdk:ts','sdk:go','sdk:rust')]; print('ok')"` prints ok.
    - `.venv/bin/python -c "from voss.eval.suite import TaskSpec; TaskSpec.model_validate({'prompt':'x','mode':'plan','rubric':'r','surface':'sdk:bogus'})" 2>&1 | grep -c ValidationError` >= 1.
    - Golden tasks still load 6: `.venv/bin/python -c "from voss.eval.suite import load_suite; from pathlib import Path; print(len(load_suite(Path('tests/eval/golden'), suite='golden')))"` prints 6.
    - `_drive_sdk_python` imports only public + the two commented private exceptions: `grep -n "from voss.harness" voss/eval/runner.py` shows no NEW import of voss.harness.session / voss.harness.providers inside the sdk:python driver (only render+tools as commented exceptions).
    - `grep -c "make_toolset\|PlainRenderer" voss/eval/runner.py` >= 1 with adjacent `# private` comment lines: `grep -c "private" voss/eval/runner.py` >= 2.
    - test_drive_sdk_python_stub passes returning a non-empty final; `import voss.eval.runner` clean.
  </acceptance_criteria>
  <done>surface Literal carries the four sdk:* values additively; _drive_sdk_python drives run_turn via the public embedder surface (private renderer/toolset commented as M7 gap); golden/internal unchanged; hermetic sdk:python test green.</done>
</task>

<task type="auto">
  <name>Task 2: _drive_sdk_client serve+consumer driver + sdk:* dispatch</name>
  <files>voss/eval/runner.py, tests/eval/test_sdk.py</files>
  <read_first>
    - voss/eval/runner.py (lines 335-394 `_drive_task` — the sequential `if spec.surface == ...` chain + the `if spec.surface == "serve":` not-implemented block at 359-366 that must stay untouched; lines 200-208 `_live_env`; imports lines 1-40 — confirm subprocess/sys/time present, add threading if absent)
    - .planning/phases/E4-sdk-proof/E4-PATTERNS.md (Pattern 1 `_drive_sdk_client` lines 132-219 — the full serve-spawn + consumer-spawn lifecycle to copy; Shared "Serve spawn/handshake" lines 616-632; "VOSS_PYTHON env" lines 649-657)
    - .planning/phases/E3-surface-e2e/E3-RESEARCH.md (serve driver mechanics: handshake parse, stdin heartbeat, kill pattern — the source pattern PATTERNS Pattern 1 mirrors)
    - tests/eval/sdk/consumers/ts/consumer.js + go/main.go + crates/voss-sdk/examples/sdk_proof_consumer.rs (the W0 consumers this driver spawns — confirm the run commands: `node consumer.js`, `go run .` from the go dir, `cargo run --example sdk_proof_consumer`)
    - voss/harness/server/app.py (lines 166-178 FAKE_TURN — for the hermetic test path the driver spawns serve with VOSS_SERVE_FAKE_TURN=1)
    - tests/eval/test_surface_drivers.py (driver-test pattern for the hermetic stub tests)
  </read_first>
  <action>
    Add `_drive_sdk_client(spec, *, cwd, consumer, timeout=180.0) -> str` to voss/eval/runner.py, copying PATTERNS Pattern 1 (lines 132-219). Steps:
      1. Build the serve env from `_live_env(cwd)` (auth inherited, LITELLM_LOCAL_MODEL_COST_MAP, VOSS_DEV). Popen `[sys.executable, "-m", "voss.cli", "serve"]` with cwd=cwd, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True, bufsize=1.
      2. Start a daemon thread that drains proc_server.stderr (prevents pipe-buffer block).
      3. Read stdout lines with a 60s monotonic deadline; parse each as JSON; the first dict with a "token" key is the handshake. On deadline, kill + raise TimeoutError. base_url = f"http://127.0.0.1:{handshake['port']}", token = handshake["token"].
      4. Build consumer_env = serve env + VOSS_BASE_URL, VOSS_TOKEN, VOSS_CWD=str(cwd), VOSS_PYTHON=str(Path(sys.executable).resolve()) (Go interpreterPath fix — Pitfall 2), VOSS_PROMPT=spec.prompt, VOSS_MODE=spec.mode.
      5. Select cmd + run-cwd by consumer:
         - "ts": cmd=["node", "tests/eval/sdk/consumers/ts/consumer.js"], run-cwd=None
         - "go": cmd=["go", "run", "."], run-cwd="tests/eval/sdk/consumers/go" (go.mod resolution needs cwd=consumer dir)
         - "rust": cmd=["cargo","run","--manifest-path","crates/voss-sdk/Cargo.toml","--example","sdk_proof_consumer","--quiet"], run-cwd=None
      6. subprocess.run(cmd, env=consumer_env, capture_output=True, text=True, timeout=timeout, check=False, cwd=run-cwd). Parse the LAST stdout line as JSON; return consumer_result.get("final",""). On (TimeoutExpired, JSONDecodeError, IndexError) return "".
      7. finally: close proc_server.stdin (EOF heartbeat → server self-terminates), proc_server.wait(timeout=10), proc_server.kill() on TimeoutExpired. NEVER leave an orphaned server.

    Wire dispatch in _drive_task: AFTER the existing `if spec.surface == "serve":` block (line 366) and BEFORE `if task_id.startswith("05-")`, add:
      `if spec.surface == "sdk:python":` → `final = await _drive_sdk_python(spec, cwd=cwd, provider=provider, model=model, max_turns=max_turns); return record, final, None, False`
      `if spec.surface in ("sdk:ts", "sdk:go", "sdk:rust"):` → `final = await _drive_sdk_client(spec, cwd=cwd, consumer=spec.surface.split(":")[1]); return record, final, None, False`
    Leave the serve branch, the resume branch, and the internal else COMPLETELY unchanged. Add `import threading` at the top if not already present.

    In tests/eval/test_sdk.py: convert `test_drive_sdk_client_ts_stub`, `test_drive_sdk_client_go_stub`, `test_drive_sdk_client_rust_stub` from xfail to real HERMETIC tests. Each: skipif the toolchain (node/go/cargo) is absent; monkeypatch.setenv("VOSS_SERVE_FAKE_TURN","1") so the spawned serve emits the canned `echo: <prompt>` final with NO permission gate; build a tmp fixture cwd with one file; `final = asyncio.run(_drive_sdk_client(spec, cwd=tmp, consumer="ts"))` (resp. go/rust); assert `final` contains "echo" (the FAKE_TURN final text) OR is a non-empty str. Add a comment in each: "hermetic: FAKE_TURN emits no permission.updated; saw_permission_gate will be false — that is correct for stub mode (RESEARCH Pitfall 3)." Mark these `@pytest.mark.slow` if the marker exists (they spawn a real server + build/run a consumer).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_sdk.py -q -k "drive_sdk_client and ts" 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "_drive_sdk_client" voss/eval/runner.py` >= 2 (definition + dispatch call).
    - `grep -c "VOSS_BASE_URL" voss/eval/runner.py` >= 1 and `grep -c "VOSS_PYTHON" voss/eval/runner.py` >= 1 (env passed to consumer; Go interpreterPath fix).
    - The serve branch is untouched: `grep -c "surface 'serve' driver not implemented (E3-03)" voss/eval/runner.py` >= 1 (E3-03 territory preserved).
    - Dispatch routes sdk:* before the resume branch: `grep -n "sdk:python\|sdk:ts\|task_id.startswith" voss/eval/runner.py` shows the sdk:* branches appear before `task_id.startswith("05-")`.
    - serve is always killed: `grep -c "stdin.close\|proc_server.kill\|\.wait(timeout=" voss/eval/runner.py` >= 1 inside a finally (no orphan).
    - `import voss.eval.runner` clean (no NameError); the hermetic ts driver test passes: `.venv/bin/python -m pytest tests/eval/test_sdk.py -k "drive_sdk_client and ts" -q` reports 0 failed (skipped acceptable if node absent — but node IS present per RESEARCH).
    - REQUIRED_FIELDS unchanged (E4 adds no new row keys): `git diff --stat tests/eval/test_voss_eval_stub.py` shows no change to REQUIRED_FIELDS (the sentinel already has surface from E3-01).
    - `.venv/bin/python -m pytest tests/eval -q -m 'not live' -k "not builds and not resolves and not drive_sdk_client" 2>&1 | tail -3` shows no NEW regression in the internal/golden/cli paths (pre-existing E2 matrix RED failures excepted).
  </acceptance_criteria>
  <done>_drive_sdk_client spawns serve (60s handshake, kill-in-finally) + the W0 consumer, reads its JSON, returns final; sdk:python/ts/go/rust dispatch wired; serve branch untouched; hermetic driver tests green; no new JSONL fields.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| task.toml surface value → TaskSpec validation | sdk:* are operator input; extra="forbid" + Literal constrain the value space |
| Python runner → voss serve subprocess | loopback (127.0.0.1) + bearer token from the handshake; the runner owns the token + lifecycle |
| Python runner → consumer subprocess | consumer receives token via env (not CLI arg); consumer is committed in-repo |
| consumer stdout → runner JSON parse | untrusted last-line; parsed with json.loads under try/except → "" on failure |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E4-04 | Tampering | invalid sdk:* surface in task.toml | mitigate | Literal[...sdk:python,sdk:ts,sdk:go,sdk:rust] rejects unknown values (test asserts sdk:bogus → ValidationError) |
| T-E4-05 | Information Disclosure | VOSS_TOKEN passed to consumer env | mitigate | Token is ephemeral per-scenario, loopback-only server, env visible to same user only (not a CLI arg, not logged) |
| T-E4-06 | Denial | runaway serve/consumer subprocess | mitigate | consumer subprocess.run(timeout=180); serve killed in finally (stdin EOF → wait(10) → kill); no orphan |
| T-E4-07 | Tampering | malicious/garbage consumer stdout last line | mitigate | json.loads(stdout.strip().splitlines()[-1]) under try/except (JSONDecodeError/IndexError → "" → row records a clean FAIL, no crash) |
| T-E4-08 | Spoofing | consumer connecting to a non-loopback server | accept | base_url is hardcoded http://127.0.0.1:{port} from the runner-owned handshake; consumer cannot redirect it |
| T-E4-SC | Tampering | npm/pip/cargo installs | accept | E4 introduces zero new packages (RESEARCH Package Legitimacy Audit: not applicable); no install task in this plan |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/test_sdk.py tests/eval/test_task_spec.py -q` → sdk:* surfaces validate; _drive_sdk_python + hermetic _drive_sdk_client(ts) green
- surface Literal extended additively; golden loads 6; internal/cli:*/serve branches byte-unchanged
- _drive_sdk_client owns serve lifecycle (60s handshake, kill-in-finally), passes VOSS_BASE_URL/VOSS_TOKEN/VOSS_PYTHON to the consumer
- E4 adds no new JSONL row keys; REQUIRED_FIELDS sentinel unchanged
- `.venv/bin/python -m pytest tests/eval -q -m 'not live'` → no new regression (pre-existing E2 matrix RED excepted)
</verification>

<success_criteria>
- EVSDK-01: surface dispatch — Literal accepts sdk:python|ts|go|rust; runner routes to _drive_sdk_python / _drive_sdk_client
- EVSDK-02: sdk:python in-process driver calls run_turn via the public embedder surface; returns TurnResult.final
- serve lifecycle owned by the runner (TS 10s timeout pitfall avoided; Go interpreterPath fixed via VOSS_PYTHON)
- internal/cli:*/serve/golden paths unchanged; no new JSONL fields
</success_criteria>

<output>
Create `.planning/phases/E4-sdk-proof/E4-02-SUMMARY.md` when done
</output>
