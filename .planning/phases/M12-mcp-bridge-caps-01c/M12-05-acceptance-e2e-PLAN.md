---
phase: M12-mcp-bridge-caps-01c
plan: 05
type: execute
wave: 4
depends_on: [M12-01, M12-02, M12-03, M12-04]
files_modified:
  - tests/harness/mcp/test_mcp_serve_e2e.py
autonomous: true
requirements: [MCP-01, MCP-02, MCP-03, MCP-04, MCP-05, MCP-06, MCP-07]

must_haves:
  truths:
    - "An e2e test spawns `python3 -m voss.cli mcp serve --mode plan --cwd <tmp>` as a real subprocess, feeds it newline-delimited JSON-RPC, reads its stdout, completes the 2025-11-25 handshake, and exchanges `tools/list` + `tools/call` without the subprocess crashing"
    - "The handshake response carries `protocolVersion == \"2025-11-25\"` and `serverInfo.name` ∈ {\"voss\", <name from .voss/mcp.yml server.name>}"
    - "`tools/list` returns EXACTLY 13 tool descriptors (6 low-level + 7 skills) when `.voss/mcp.yml` is absent (default `*`/`*`)"
    - "In `--mode plan`: calling `analyze` (mutating) returns `CallToolResult` with `isError=True` and content text containing `denied by mode plan`; calling `fs_read` (read-only) returns `isError=False` and reads the seeded file's contents"
    - "Restarting the subprocess with `--mode edit` lets a previously-denied mutating tool/skill proceed at the gate level (it still may error for other reasons, but it MUST NOT be denied by the mode tier)"
    - "Telemetry events `mcp.server.request` and `mcp.server.response` are emitted at least once per `tools/call` (captured via VOSS_TELEMETRY_FILE env-var pointing the recorder at a tmp file)"
  artifacts:
    - path: "tests/harness/mcp/test_mcp_serve_e2e.py"
      provides: "true subprocess roundtrip test of voss mcp serve --mode {plan,edit}; handshake + tools/list count + plan-deny + edit-allow + telemetry-event capture; ALL via real stdio"
      contains: "def test_mcp_serve_plan_mode_denies_mutating_tool"
      min_lines: 140
  key_links:
    - from: "tests/harness/mcp/test_mcp_serve_e2e.py"
      to: "voss/harness/cli.py mcp_serve_cmd"
      via: "subprocess.Popen([sys.executable, '-m', 'voss.cli', 'mcp', 'serve', '--mode', 'plan', '--cwd', str(tmp)], stdin=PIPE, stdout=PIPE, stderr=PIPE)"
      pattern: "voss\\.cli.*mcp.*serve"
    - from: "tests/harness/mcp/test_mcp_serve_e2e.py"
      to: "voss/harness/telemetry.py"
      via: "VOSS_TELEMETRY_FILE env var directs telemetry.emit to a tmp file; test reads that file to assert event names"
      pattern: "VOSS_TELEMETRY_FILE"
---

<objective>
Phase acceptance gate. Build a true subprocess-level end-to-end test that
spawns `voss mcp serve` and exchanges real JSON-RPC over stdio, proving the
M12 contract end-to-end: handshake works, all 13 tools advertised,
plan-mode denies mutating tools cleanly, edit-mode lets them through the
mode tier, telemetry events land.

Satisfies the Nyquist Dim-8 acceptance test for the phase. Closes
MCP-01..07.
</objective>

<context>
@.planning/phases/M12-mcp-bridge-caps-01c/M12-CONTEXT.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-PLAN-OUTLINE.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-01-server-scaffold-PLAN.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-02-tools-advertisement-dispatch-PLAN.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-03-skills-bridge-PLAN.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-04-cli-serve-command-PLAN.md

Read first:
- `voss/harness/telemetry.py` (look for `VOSS_TELEMETRY_FILE` env var or
  equivalent file-sink option; if absent, the telemetry-assertion portion of
  the test uses an in-process monkeypatch via importing `telemetry` in the
  PARENT process won't see subprocess events — see Notes below).
- `voss/harness/mcp/client.py` for the JSON-RPC wire-format conventions.
- The handshake sequence: `initialize` → server replies → `notifications/
  initialized` → `tools/list` → server replies → `tools/call` → server replies.

NOTES on telemetry capture across processes:
The server runs in a subprocess; the parent test process can capture
server-side telemetry events only if telemetry can be sinked to a FILE the
child writes and the parent reads. If `VOSS_TELEMETRY_FILE` (or a similar
env-driven file sink) exists in `voss/harness/telemetry.py`, use it. If NOT,
the test asserts the request/response shape via the JSON-RPC RESPONSE only
(content-text + isError) and notes that telemetry-event capture across
processes is deferred to a future plan. This is acceptable: the wire-level
deny envelope is the primary acceptance signal; telemetry is corroborative.
Read `voss/harness/telemetry.py` and pick the capture method that exists; if
neither exists, drop the telemetry assertion and document it as a deviation.
</context>

<threat_model>
| ID | Threat | Mitigation |
|---|---|---|
| T-M12-05-01 | Subprocess hang causes the test to wait forever | Every subprocess interaction uses a per-call `timeout=` (5s default, 10s for the slowest `tools/call` if a skill is hit). After all assertions, send EOF via `proc.stdin.close()` and `proc.wait(timeout=5)`; on timeout, `proc.kill()`. |
| T-M12-05-02 | Test depends on the host's existing global `.voss/mcp.yml` and leaks state | All subprocesses are spawned with `cwd=<tmp_path>` and `env=<minimal env with HOME=tmp>` (or at minimum no inherited `XDG_CONFIG_HOME` pointing at the dev's real ~/.config). The autouse `isolated_state` style isn't available across processes — set `XDG_STATE_HOME` + `XDG_CONFIG_HOME` explicitly. |
| T-M12-05-03 | Telemetry events from prior tests pollute the assertion | Telemetry capture (when used) writes to a fresh per-test tmp file via `VOSS_TELEMETRY_FILE` env var or equivalent. |
| T-M12-05-04 | `serve_stdio` writes ANY non-JSON-RPC bytes to stdout (e.g. an accidental `print` from a renderer) and breaks the test's line-by-line read | The test parses every stdout line with `json.loads`; the first failing parse fails loudly with the bad line in the error. M12-04's renderer-purity constraint is what prevents this in production; the test validates it. |
| T-M12-05-05 | Spawned subprocess errors with a Python ImportError (e.g. the editable install isn't on path) and the test confuses "import error" with "JSON-RPC error" | Spawn with `cwd=tmp` but **explicitly** preserve the parent's `PYTHONPATH` (and prepend the repo root) so the subprocess can import `voss.*`. Assert subprocess `returncode == 0` at the end (or treat non-zero as a structured test failure with the captured `stderr` text). |

Out-of-scope: load testing, concurrent client testing, HTTP transport,
daemon-mode tests, MCP host integration tests (running the real Claude
Desktop subprocess pair — deferred).
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add `tests/harness/mcp/test_mcp_serve_e2e.py` with subprocess roundtrip helpers + 3 e2e tests</name>
  <read_first>
    voss/harness/cli.py (M12-04 — confirm `voss mcp serve` entry point)
    voss/harness/mcp/server.py (M12-01 — confirm handshake response shape)
    voss/harness/mcp/server_tools.py (M12-02 — confirm 13-tool advertisement)
    voss/harness/telemetry.py (full file — check for VOSS_TELEMETRY_FILE or equivalent file-sink hook)
    tests/harness/mcp/test_mcp_serve_cli.py (M12-04 sibling — style reference)
  </read_first>
  <action>
    Create `tests/harness/mcp/test_mcp_serve_e2e.py`.

    Module-level helper functions (sync — subprocess interaction is line-based):

    ```python
    import json, os, sys, subprocess, time, tempfile
    from pathlib import Path

    REPO_ROOT = Path(__file__).resolve().parents[3]  # adjust to match repo layout

    def _spawn_server(tmp: Path, *, mode: str, env_extra: dict | None = None) -> subprocess.Popen:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{REPO_ROOT}{os.pathsep}{env.get('PYTHONPATH','')}"
        env["XDG_STATE_HOME"] = str(tmp / "state")
        env["XDG_CONFIG_HOME"] = str(tmp / "config")
        if env_extra:
            env.update(env_extra)
        proc = subprocess.Popen(
            [sys.executable, "-m", "voss.cli", "mcp", "serve",
             "--mode", mode, "--cwd", str(tmp)],
            cwd=str(tmp),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env,
        )
        return proc

    def _send_request(proc: subprocess.Popen, payload: dict) -> dict:
        line = (json.dumps(payload) + "\n").encode("utf-8")
        proc.stdin.write(line)
        proc.stdin.flush()
        # Read one JSON-RPC response line. Handle notifications (no id) by
        # skipping if the response carries no matching id.
        deadline = time.monotonic() + 5.0
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError(f"no response within 5s for {payload}")
            raw = proc.stdout.readline()
            if not raw:
                stderr = proc.stderr.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"server EOF; stderr: {stderr}")
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError as e:
                raise AssertionError(
                    f"non-JSON line on stdout (renderer leak?): {raw!r}"
                ) from e
            if msg.get("id") == payload.get("id"):
                return msg

    def _close(proc: subprocess.Popen) -> None:
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    ```

    Tests:

    1. `def test_handshake_lists_thirteen_tools(tmp_path)`:
       - `proc = _spawn_server(tmp_path, mode="plan")`
       - Send `{"jsonrpc":"2.0","id":1,"method":"initialize","params":
         {"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":
         {"name":"t","version":"0"}}}`.
       - Assert `resp["result"]["protocolVersion"] == "2025-11-25"`.
       - Assert `resp["result"]["serverInfo"]["name"] in ("voss",)`.
       - Send `notifications/initialized` (no id, no expected response —
         just write and continue).
       - Send `{"id":2,"method":"tools/list",...}`.
       - Assert `len(resp["result"]["tools"]) == 13`.
       - Cross-check tool names contain all of
         `{"fs_read","fs_glob","fs_grep","voss_check","git_status","git_diff","analyze","rename-symbol","voss-lint-as-skill","summarize-diff","audit-cognition","add-test","port-py-to-voss"}`.
       - Assert each descriptor has `annotations.destructiveHint` as a bool.
       - `_close(proc)`.

    2. `def test_plan_mode_denies_mutating_tool(tmp_path)`:
       - `proc = _spawn_server(tmp_path, mode="plan")`
       - Complete handshake (initialize + notifications/initialized).
       - Send `{"id":3,"method":"tools/call","params":{"name":"analyze",
         "arguments":{"args":[]}}}`.
       - Assert `resp["result"]["isError"] is True`.
       - Assert `"denied by mode plan"` in `resp["result"]["content"][0]
         ["text"]`.
       - `_close(proc)`.

    3. `def test_plan_mode_allows_read_only_tool(tmp_path)`:
       - Seed `tmp_path / "hello.txt"` with `"hi mcp"`.
       - `proc = _spawn_server(tmp_path, mode="plan")`
       - Complete handshake.
       - Send `{"id":4,"method":"tools/call","params":{"name":"fs_read",
         "arguments":{"path":"hello.txt"}}}`.
       - Assert `resp["result"]["isError"] is False`.
       - Assert `"hi mcp"` in `resp["result"]["content"][0]["text"]`.
       - `_close(proc)`.

    4. `def test_edit_mode_passes_mutating_tool_through_gate(tmp_path)`:
       - `proc = _spawn_server(tmp_path, mode="edit")`
       - Complete handshake.
       - Send `tools/call` for `voss-lint-as-skill` with `args=["."]` (a
         read-only skill; verifies the skill bridge wire-up under a non-plan
         mode). Assert `isError is False` and the response content text is
         parseable JSON with `version == 1`.
       - **Do NOT** call an actual mutating skill (`analyze`/`rename-symbol`/
         `add-test`/`port-py-to-voss`) here — those have side effects
         (subprocess writes, run_turn LLM calls) that this test cannot afford.
         The plan-mode-denies test (case 2) is the structural proof; case 4
         only proves edit mode does not auto-deny by mode tier.
       - `_close(proc)`.

    5. `def test_unknown_tool_returns_iserror_envelope(tmp_path)`:
       - `proc = _spawn_server(tmp_path, mode="plan")`
       - Complete handshake.
       - Send `tools/call` for `name="nope"`, `arguments={}`.
       - Assert `resp["result"]["isError"] is True` and `"unknown tool: nope"`
         in `content[0]["text"]`.
       - `_close(proc)`.

    6. `def test_eof_exits_subprocess_cleanly(tmp_path)`:
       - `proc = _spawn_server(tmp_path, mode="plan")`
       - Close stdin without sending anything.
       - `proc.wait(timeout=5)`; assert `proc.returncode == 0`.

    7. **Telemetry-event capture** (conditional on file-sink availability):
       - Inspect `voss/harness/telemetry.py` for an env-var-driven file sink.
         If something like `VOSS_TELEMETRY_FILE` or equivalent exists:
         - `tel_file = tmp_path / "tel.ndjson"`
         - `proc = _spawn_server(tmp_path, mode="plan",
           env_extra={"VOSS_TELEMETRY_FILE": str(tel_file)})`
         - Complete handshake + one `tools/call` for `fs_read`.
         - `_close(proc)`; read `tel_file`.
         - Assert at least one event with name `mcp.server.request` and one
           with `mcp.server.response`.
         - If telemetry.py uses a DIFFERENT env var or method, adapt to
           that. If telemetry.py has NO file-sink option:
           - Mark the test with `pytest.mark.skip(reason="telemetry file
             sink not implemented; covered by M12-01 in-process tests")` and
             document this as a deviation in the SUMMARY.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/mcp/test_mcp_serve_e2e.py</automated>
    <automated>python3 -m pytest -q tests/harness/mcp/</automated>
    <automated>python3 -m pytest -q tests/harness/ -k "mcp" </automated>
  </verify>
  <acceptance_criteria>
    - All 6 non-conditional tests pass under `python3 -m pytest -q tests/harness/mcp/test_mcp_serve_e2e.py`
    - The handshake-13 test asserts EXACTLY 13 advertised tools and cross-checks all 13 names
    - The plan-mode-deny test asserts `denied by mode plan` in the response content for the `analyze` skill
    - The plan-mode-allow test asserts `fs_read` succeeds in plan mode (read-only invariant)
    - The unknown-tool test asserts `unknown tool: nope` envelope
    - The EOF test asserts subprocess returncode 0 after stdin close
    - Telemetry test passes OR is explicitly skipped with a documented reason — never a silent pass
    - Full pre-existing `tests/harness/mcp/` suite still passes
  </acceptance_criteria>
  <done>True subprocess e2e test proves: handshake, 13-tool advertisement, plan-mode mutating deny, plan-mode read-only allow, edit-mode read-only skill round-trip, unknown-tool envelope, clean EOF exit. MCP-01..07 all exercised.</done>
</task>

</tasks>

<verification>
```bash
cd /Users/benjaminmarks/Projects/Voss

# 1. e2e test green
python3 -m pytest -q tests/harness/mcp/test_mcp_serve_e2e.py

# 2. Full mcp suite green (regression guard)
python3 -m pytest -q tests/harness/mcp/

# 3. Whole skill + harness regression
python3 -m pytest -q tests/harness/ -k "mcp"

# 4. Whitespace
git diff --check
```
</verification>

<success_criteria>
- `tests/harness/mcp/test_mcp_serve_e2e.py` spawns `voss mcp serve` as a real subprocess and completes the JSON-RPC handshake over stdio.
- The 13-tool advertisement is exercised end-to-end.
- Plan-mode denies a mutating skill (`analyze`) at the mode tier with the exact `denied by mode plan` reason text on the wire.
- Plan-mode allows `fs_read` to succeed in read-only mode.
- Edit-mode does NOT auto-deny a read-only skill (`voss-lint-as-skill`) by mode tier.
- Unknown tool name returns an `isError=True` envelope on the wire.
- Subprocess exits cleanly on stdin EOF.
- Telemetry event capture is either asserted or explicitly skipped with a documented reason.
- All 6 non-conditional e2e tests pass; full mcp suite passes; `git diff --check` clean.
- This plan satisfies the Nyquist Dim-8 acceptance gate for M12: every requirement (MCP-01..07) has at least one wire-level assertion.
</success_criteria>

<output>
Create `.planning/phases/M12-mcp-bridge-caps-01c/M12-05-SUMMARY.md` when done.
</output>
