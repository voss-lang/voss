---
phase: T3-network-surface
plan: 09
type: execute
wave: 5
depends_on: [T3-05, T3-07, T3-08]
files_modified:
  - .github/workflows/mcp-integration.yml
  - tests/eval/golden/06-fetch-summarize/task.toml
  - tests/eval/golden/06-fetch-summarize/expected.md
  - voss/harness/eval.py
  - tests/harness/test_eval_task_6_stub.py
autonomous: false
requirements: [NET-01, NET-03]
must_haves:
  truths:
    - ".github/workflows/mcp-integration.yml runs a CI job that: (1) checks out the repo, (2) installs Node.js via actions/setup-node, (3) installs Python deps via pip install -e .[dev], (4) runs `voss mcp call filesystem <read-tool-name> --arg path=./README.md` against the pinned @modelcontextprotocol/server-filesystem@<pinned> server, (5) asserts the output contains the literal substring 'voss' (from the README.md content)"
    - "The CI job pins the @modelcontextprotocol/server-filesystem npm version explicitly (no @latest) and pins the read-tool name to the value resolved by Task 1 checkpoint (recorded in T3-09 post-checkpoint task note). The CI workflow may be templated but cannot be merged to main until both pins are populated."
    - "tests/eval/golden/06-fetch-summarize/ exists with task.toml requiring web_fetch + expected.md describing the success criteria"
    - "voss/harness/eval.py loads task 06 alongside the existing 5 golden tasks; --stub mode uses httpx.MockTransport to satisfy the web_fetch call hermetically"
    - "tests/harness/test_eval_task_6_stub.py runs voss eval --stub and asserts task 06 completes (PASS or FAIL is acceptable in CI — the test asserts the run COMPLETED without runtime error, mirroring M5 existing pattern)"
  artifacts:
    - path: ".github/workflows/mcp-integration.yml"
      provides: "GitHub Actions job 'mcp-integration' running voss mcp call against pinned reference filesystem server"
      contains: "actions/setup-node"
    - path: "tests/eval/golden/06-fetch-summarize/task.toml"
      provides: "Task definition: a goal that requires the agent to call web_fetch and produce a summary"
      contains: "web_fetch"
    - path: "tests/eval/golden/06-fetch-summarize/expected.md"
      provides: "Human-readable expected-outcome description for the task (LLM-judge rubric input per M5 pattern)"
      contains: "fetch"
    - path: "voss/harness/eval.py"
      provides: "Task 06 loaded by glob; --stub MockTransport injection for web_fetch URL"
      contains: "06-fetch-summarize"
    - path: "tests/harness/test_eval_task_6_stub.py"
      provides: "Pytest that invokes voss eval --stub for task 06 and asserts completion"
      contains: "test_task_6_stub_runs"
  key_links:
    - from: ".github/workflows/mcp-integration.yml"
      to: "@modelcontextprotocol/server-filesystem@<pinned-version>"
      via: "npx -y @modelcontextprotocol/server-filesystem@<pinned-version> in mcp.yml fixture; pinned exact-version not @latest"
      pattern: "@modelcontextprotocol/server-filesystem@"
    - from: "voss/harness/eval.py:task 06 loader"
      to: "tests/eval/golden/06-fetch-summarize/task.toml"
      via: "task glob discovers the directory; task.toml.tools = ['web_fetch']"
      pattern: "06-fetch-summarize"
---

<objective>
Validate the entire T3 stack end-to-end via two CI surfaces:
1. **MCP integration job:** `.github/workflows/mcp-integration.yml` exercises `voss mcp call filesystem <read-tool> path=./README.md` against the pinned real npm reference server `@modelcontextprotocol/server-filesystem`. This is the load-bearing proof that NET-03 acceptance (d) holds against a non-mocked server.
2. **M5 eval task #6:** "fetch + summarize" — a golden task that requires `web_fetch` to succeed. Adds the sixth task to the existing M5 eval suite (tasks 01-05 already exist). `voss eval --stub` runs hermetically via httpx.MockTransport.

This plan is the final wave and the END of T3 — once green, all 13 SPEC acceptance criteria are satisfied.

Purpose: Two SPEC acceptance bullets fall to this plan:
- "CI job `mcp-integration` runs `voss mcp call filesystem read_file path=./README.md` against the pinned `@modelcontextprotocol/server-filesystem` via `npx -y` and asserts the README content appears in output"
- "M5 eval suite gains task #6 with a `task.toml` requiring `web_fetch` to succeed; `voss eval --stub` covers it via `httpx` stub transport"

This plan is `autonomous: false` because it contains a **blocking-human checkpoint** for the npm pin choice and tool-name discovery (RESEARCH Pitfall 4 + Open Question 2) — the planner cannot verify the exact tool name without invoking the live npm package, and CI integration that hard-codes a name that doesn't exist breaks everything downstream.

Output: 1 CI workflow file; 2 eval fixture files; eval.py extension; 1 pytest test. A blocking human-verify gate confirms the pinned npm version + tool name before CI executes for real.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T3-network-surface/T3-SPEC.md
@.planning/phases/T3-network-surface/T3-CONTEXT.md
@.planning/phases/T3-network-surface/T3-RESEARCH.md
@.planning/phases/T3-network-surface/T3-PATTERNS.md
@.planning/phases/T3-network-surface/T3-05-PLAN.md
@.planning/phases/T3-network-surface/T3-07-PLAN.md
@.planning/phases/T3-network-surface/T3-08-PLAN.md
@.github/workflows/ci.yml
@voss/harness/eval.py
</context>

<interfaces>
CI workflow template (T3-PATTERNS section "CI Workflow Job Pattern" + .github/workflows/ci.yml):
```yaml
name: mcp-integration

on:
  push:
    branches: [dev, master]
  pull_request:
    branches: [dev, master]

jobs:
  mcp-integration:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: pip install -e ".[dev]"
      - name: Write .voss/mcp.yml fixture
        run: |
          mkdir -p .voss
          cat > .voss/mcp.yml <<'YML'
          servers:
            filesystem:
              command:
                - npx
                - -y
                - '@modelcontextprotocol/server-filesystem@<PINNED_VERSION>'
                - '{cwd}'
              timeout_s: 60.0
          YML
      - name: Smoke voss mcp list
        run: voss mcp list --cwd .
      - name: Smoke voss mcp call read_text_file
        run: |
          set -e
          output=$(voss mcp call filesystem <TOOL_NAME> --arg "path=./README.md")
          echo "----- output -----"
          echo "$output"
          echo "----- end output -----"
          echo "$output" | grep -i "voss" > /dev/null  # README mentions "voss" — assert non-empty content
```

`<PINNED_VERSION>` and `<TOOL_NAME>` are CHECKPOINT POINTS — must be resolved by a blocking human-verify task before the CI workflow is committed for real.

Eval task 06 (tests/eval/golden/06-fetch-summarize/task.toml):
```toml
# Phase T3 / NET-01 — Task 06: web_fetch + summarize
id = "06-fetch-summarize"
goal = "Fetch https://example.com/ and write a one-line summary of the title and main heading."
tools = ["web_fetch", "fs_write"]
expected_summary_keywords = ["example", "domain"]  # rubric input for LLM-as-judge
max_iterations = 4
```

expected.md (rubric input for LLM-as-judge per M5 pattern):
```markdown
# Task 06: Fetch + Summarize

## Success Criteria
- Agent called web_fetch with a valid URL argument
- Agent extracted at least one piece of information from the response (title, heading, or content paragraph)
- Agent wrote a summary file or returned the summary in its final response

## Notes
- Hermetic --stub mode injects a canned httpx MockTransport response with: title "Example Domain", H1 "Example Domain"
- LLM-judge rubric: 1.0 if summary mentions both "example" and "domain"; 0.5 if only one; 0.0 if neither
```

voss/harness/eval.py extension: read the file first (`grep -n "def load_tasks\|task_glob\|golden" voss/harness/eval.py`) to find the existing M5 task-loader. The 5 existing tasks are at tests/eval/golden/01-* through 05-*. Task 06 is loaded by the same glob; no code change needed if the loader uses a wildcard pattern. But --stub injection IS new:

```
# In eval.py, near where the agent is constructed for --stub mode:
if stub_mode:
    # T3-09: inject httpx MockTransport for web_fetch so task 06 (and any future net-using task) is hermetic
    from voss.harness.net import NetSession
    import httpx
    def _stub_handler(request):
        url = str(request.url)
        if "example.com" in url:
            return httpx.Response(200, text=textwrap.dedent("""
                <html><head><title>Example Domain</title></head>
                <body><h1>Example Domain</h1><p>This domain is for illustration.</p></body>
                </html>
            """).strip())
        return httpx.Response(404, text="not found")
    stub_transport = httpx.MockTransport(_stub_handler)
    stub_client = httpx.AsyncClient(transport=stub_transport, follow_redirects=True, max_redirects=5)
    net_session = NetSession(client=stub_client)
    # Pass net_session through to the agent's toolset construction
```

Read eval.py first — the existing --stub flag may already inject a stub provider; just add the httpx side. If eval.py does not yet have a --stub-friendly extension point for NetSession, the stub handler must be added at the call site where make_toolset(cwd, net=...) is invoked from the eval runner.

Pytest test (tests/harness/test_eval_task_6_stub.py): subprocess-invoke `voss eval --stub --task 06-fetch-summarize` (or whatever the M5 CLI shape is — `grep -n "@click.command\(.eval.\)" voss/harness/cli.py` to find the flags). Capture stdout/stderr. Assert exit code 0; assert the task ran (presence of "06-fetch-summarize" in output) — do NOT assert PASS or FAIL of the agent's actual work (the LLM judge in M5 is non-deterministic; assert COMPLETION only).
</interfaces>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Human checkpoint — pin @modelcontextprotocol/server-filesystem version + verify the actual read-tool name</name>
  <what-built>None yet. This blocking checkpoint resolves two open questions before any code lands:

1. RESEARCH Pitfall 4 + Open Question 2: the server-filesystem npm package 2026.1.14 may use `read_text_file` instead of the `read_file` placeholder name in SPEC. We need to verify against the actual dist.

2. The exact PINNED_VERSION for CI reproducibility (currently 2026.1.14 per RESEARCH but may have moved).</what-built>
  <how-to-verify>
    Run these commands locally (executor on the developer's machine):

    1. Check the current latest version:
       ```
       npm view @modelcontextprotocol/server-filesystem version
       ```
       Record the version. SUGGEST pinning to this exact version (e.g. `2026.1.14` or whatever returns).

    2. Discover the actual read tool name by launching the server and calling tools/list:
       ```
       # Quick discovery script
       mkdir -p /tmp/voss-mcp-probe
       cat > /tmp/voss-mcp-probe/probe.py <<'PY'
       import asyncio, json, subprocess
       async def main():
           proc = await asyncio.create_subprocess_exec(
               "npx", "-y", "@modelcontextprotocol/server-filesystem@<VERSION>", "/tmp/voss-mcp-probe",
               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
           )
           # initialize
           proc.stdin.write((json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}})+"\n").encode())
           await proc.stdin.drain()
           init_resp = await asyncio.wait_for(proc.stdout.readline(), timeout=30)
           print("INIT:", init_resp.decode())
           # initialized
           proc.stdin.write((json.dumps({"jsonrpc":"2.0","method":"notifications/initialized"})+"\n").encode())
           await proc.stdin.drain()
           # tools/list
           proc.stdin.write((json.dumps({"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})+"\n").encode())
           await proc.stdin.drain()
           tools_resp = await asyncio.wait_for(proc.stdout.readline(), timeout=30)
           tools = json.loads(tools_resp)["result"]["tools"]
           for t in tools:
               print("TOOL:", t["name"])
           proc.terminate()
           await proc.wait()
       asyncio.run(main())
       PY
       python3 /tmp/voss-mcp-probe/probe.py 2>&1 | tee /tmp/voss-mcp-probe-output.txt
       ```

       Substitute `<VERSION>` with the version from step 1.

    3. Read the output. Identify:
       - The tool name that reads file contents. Candidates: `read_file`, `read_text_file`. Pick the one that appears in TOOL: lines.
       - Verify the tool accepts `path` argument (look at its inputSchema in tools/list response).

    Resume-signal: provide BOTH values back to the executor as `PINNED_VERSION=...` and `READ_TOOL_NAME=...`. The executor substitutes them in the CI workflow + pytest test.
  </how-to-verify>
  <resume-signal>Type both values on resume: `PINNED_VERSION=X.Y.Z READ_TOOL_NAME=read_text_file` (or whichever variant). Optionally, paste the full tools/list output for traceability.</resume-signal>
</task>

<task type="auto">
  <name>Task 2: Create .github/workflows/mcp-integration.yml + tests/eval/golden/06-fetch-summarize/* + voss/harness/eval.py stub injection + pytest</name>
  <files>.github/workflows/mcp-integration.yml, tests/eval/golden/06-fetch-summarize/task.toml, tests/eval/golden/06-fetch-summarize/expected.md, voss/harness/eval.py, tests/harness/test_eval_task_6_stub.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (Acceptance Criteria — "CI job mcp-integration"; M5 eval task #6)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Environment Availability — Node.js / npx in CI; Open Question 2 — tool name)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (CI Workflow Job Pattern section)
    - .github/workflows/ci.yml (analog — Python setup pattern to mirror)
    - voss/harness/eval.py (entire file — find task-loader glob + --stub flag handling + agent construction)
    - tests/eval/golden/01-*/task.toml (analog — task.toml schema to follow)
    - tests/eval/golden/05-*/task.toml if exists (latest analog)
    - voss/harness/cli.py (locate eval_cmd at line 1774 from earlier grep — read full command body to understand --stub flag plumbing)
    - PINNED_VERSION + READ_TOOL_NAME from Task 1 resume-signal
  </read_first>
  <action>
    Create .github/workflows/mcp-integration.yml per the interfaces template above. Substitute `<PINNED_VERSION>` with the value from Task 1 and `<TOOL_NAME>` with READ_TOOL_NAME. The README grep step asserts non-empty content via `grep -i "voss"` — the project README contains the project name, so this is a robust assertion that doesn't pin to a specific line.

    Create tests/eval/golden/06-fetch-summarize/task.toml. First look at an existing task.toml shape: `cat tests/eval/golden/01-*/task.toml` (or whichever exists — `ls tests/eval/golden/`). Match the field set exactly — id, goal, tools (list), max_iterations, possibly model/temperature/judge_rubric — preserving M5 conventions. The new task's distinctive content:
    - id: "06-fetch-summarize"
    - goal: "Fetch https://example.com/ via web_fetch and write a one-sentence summary that includes both the page title and the main heading. Save the summary to /tmp/voss-eval-06-summary.txt via fs_write."
    - tools: ["web_fetch", "fs_write"]
    - any judge rubric pointer

    Create tests/eval/golden/06-fetch-summarize/expected.md per the interfaces template.

    Edit voss/harness/eval.py:
    - Read it first; locate the --stub flag handling. M5 set up `--stub` as the hermetic mode using a stub provider. T3-09 extends to inject an httpx MockTransport-backed NetSession when the agent calls web_fetch.
    - Locate the make_toolset call inside eval.py. If absent, the agent construction is in another file; trace the import chain (`grep -rn "make_toolset" voss/harness/`). The CLI eval_cmd (cli.py line 1774) is the entry point.
    - Add the stub handler per the interfaces section. When stub_mode is active AND task.tools contains "web_fetch", construct a NetSession with `httpx.MockTransport(_stub_handler)` as the client and pass through to make_toolset(cwd, net=stub_net_session).
    - The stub handler responds to `example.com` (and any other URLs the task might fetch) with canned HTML; unknown URLs return 404.

    Create tests/harness/test_eval_task_6_stub.py:
    ```
    import subprocess, sys, os
    from pathlib import Path

    def test_task_6_stub_runs(tmp_path):
        # Invoke `voss eval --stub --task 06-fetch-summarize` (exact flag names: read cli.py first to confirm)
        # If --task flag doesn't exist, run full eval and grep for 06 in output.
        repo_root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, "-m", "voss", "eval", "--stub"],  # adjust if voss is the entry point not -m voss
            cwd=str(repo_root),
            env={**os.environ, "VOSS_EVAL_FILTER": "06-fetch-summarize"},  # if the CLI supports a filter env; else run full and grep
            capture_output=True, text=True, timeout=300,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # The task completed if its id appears in stdout (regardless of LLM-judge PASS/FAIL)
        assert "06-fetch-summarize" in (result.stdout + result.stderr)
    ```

    If the test_eval_task_6_stub.py subprocess invocation is fragile (test timeouts in CI), an in-process variant is acceptable: import eval.py's run function directly with the stub flag set. The test asserts that the task is discoverable and the eval runner attempts to execute it.

    Final CI workflow check: after Task 1 resume, the workflow file with the resolved version + tool name is committed. The actual CI run is gated by a push/PR to dev or master. The local test of the workflow file is a syntactic check:
    ```
    python -c "import yaml; yaml.safe_load(open('.github/workflows/mcp-integration.yml').read()); print('OK')"
    ```
    plus a check that the templated tokens are gone:
    ```
    grep -c "<PINNED_VERSION>\|<TOOL_NAME>" .github/workflows/mcp-integration.yml
    ```
    must return 0.
  </action>
  <verify>
    <automated>python -c "import yaml; yaml.safe_load(open('.github/workflows/mcp-integration.yml').read()); print('YAML OK')" 2>&amp;1 | tail -3 &amp;&amp; uv run pytest tests/harness/test_eval_task_6_stub.py -x -q 2>&amp;1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - file exists: `test -f .github/workflows/mcp-integration.yml`
    - YAML valid: `python -c "import yaml; yaml.safe_load(open('.github/workflows/mcp-integration.yml').read())"` exits 0
    - templates resolved: `grep -cE "<PINNED_VERSION>|<TOOL_NAME>" .github/workflows/mcp-integration.yml` returns 0
    - pinned version present: `grep -cE "@modelcontextprotocol/server-filesystem@[0-9]" .github/workflows/mcp-integration.yml` returns >= 1 (exact version pin, not @latest)
    - tool name present: `grep -cE "voss mcp call filesystem" .github/workflows/mcp-integration.yml` returns 1 match
    - eval fixtures: `test -f tests/eval/golden/06-fetch-summarize/task.toml && test -f tests/eval/golden/06-fetch-summarize/expected.md`
    - task.toml shape: `grep -cE "id\s*=\s*.06-fetch-summarize." tests/eval/golden/06-fetch-summarize/task.toml` returns 1
    - tools list includes web_fetch: `grep -cE "web_fetch" tests/eval/golden/06-fetch-summarize/task.toml` returns 1
    - eval.py stub: `grep -nE "MockTransport|example\.com" voss/harness/eval.py | wc -l` >= 1
    - pytest passes: test_task_6_stub_runs exits 0 (NOTE: may be skipped if voss CLI module path is unsupported in CI sandbox; in that case test asserts SkipTest reason)
  </acceptance_criteria>
  <done>CI workflow file committed with pinned npm version + verified tool name; task 06 fixture exists with task.toml + expected.md; eval.py injects httpx MockTransport in stub mode for web_fetch URLs; pytest test_task_6_stub_runs proves task 06 is discoverable and runnable via --stub. The CI workflow ACTUAL EXECUTION happens on the next push to dev/master and is verified by reviewing the GitHub Actions run.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CI runner → npm registry → @modelcontextprotocol/server-filesystem | Trust chain: GitHub Actions runner trusts the npm registry; the package is pinned to an exact version to prevent supply-chain drift. |
| CI runner → README.md grep assertion | The README is repo-content; tampering would require commit access. Low risk. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T3-09-01 | Tampering | npm dependency drift breaks CI silently | mitigate | exact version pin in mcp.yml (no @latest); manual bump policy. Pin choice documented in this plan's SUMMARY. |
| T-T3-09-02 | DoS | CI integration job hangs on subprocess timeout | mitigate | workflow timeout-minutes: 10; per-server timeout_s: 60 in mcp.yml |
| T-T3-05 (reaffirm) | DoS | filesystem MCP subprocess leaks on CI runner | accept | CI ephemeral; runner is destroyed after job; production reap via lifecycle.atexit covers local invocations |
</threat_model>

<verification>
- `.github/workflows/mcp-integration.yml` parses as valid YAML
- No `<PINNED_VERSION>` / `<TOOL_NAME>` placeholders remain in the workflow
- `tests/eval/golden/06-fetch-summarize/` exists with task.toml + expected.md
- `voss/harness/eval.py` has the MockTransport stub injection for web_fetch URLs
- test_task_6_stub_runs exits 0 (or skips with a clear reason)
- On the next GitHub Actions run for this branch, the mcp-integration job completes successfully
</verification>

<success_criteria>
- CI workflow pins exact npm version (no @latest)
- The CI smoke step runs `voss mcp call filesystem <verified-tool-name> --arg path=./README.md` and the README content (containing "voss") appears in output
- Eval task 06 is discoverable by voss eval --stub and runs without runtime error
- Stub MockTransport handler returns canned content for example.com
- All 13 SPEC acceptance bullets are now satisfied (Wave 0 scaffolding + all NET-XX feature waves + this final integration plan)
</success_criteria>

<output>
Create `.planning/phases/T3-network-surface/T3-09-SUMMARY.md` when done: record PINNED_VERSION and READ_TOOL_NAME values discovered in Task 1; paste the actual tools/list output from the probe script for posterity (closes RESEARCH Open Question 2); link to the first successful GitHub Actions run of mcp-integration; show pytest output for test_task_6_stub_runs; reaffirm all 13 SPEC acceptance criteria checkboxes can be marked complete.
</output>
