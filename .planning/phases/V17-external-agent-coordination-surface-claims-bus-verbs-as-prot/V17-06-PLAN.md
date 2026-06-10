---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 06
type: execute
wave: 5
depends_on: [V17-05]
blocked_on: V15
files_modified:
  - voss/harness/bus_client.py
  - voss/harness/cli.py
autonomous: true
requirements: [VBUS-04, VBUS-06]

must_haves:
  truths:
    - "voss bus send|inbox|wait exist as click subcommands and register into the main CLI"
    - "bus verbs discover the server via VOSS_SERVER_PORT/VOSS_SERVER_TOKEN; absent/unreachable -> exit 2 with actionable stderr"
    - "bus wait --mention <me> --timeout <s> blocks on the SSE stream until a match; timeout -> exit 124"
    - "bus inbox returns unread messages once, then none on a repeat call (cursor advanced)"
    - "bus verbs --json output includes an advice array"
  artifacts:
    - path: "voss/harness/bus_client.py"
      provides: "bus_group click group: send/inbox/wait REST+SSE clients + advice"
      contains: "bus_group"
  key_links:
    - from: "voss/harness/cli.py AGENT_COMMANDS"
      to: "voss.harness.bus_client.bus_group"
      via: "import + tuple membership"
      pattern: "bus_group"
    - from: "bus wait"
      to: "GET /bus/events SSE"
      via: "bearer HTTP stream consumer filtered by mention/label"
      pattern: "/bus/events"
---

<objective>
**V15-GATED — execute only after V15 ships the server (and after V17-05 server endpoints exist).** Client half of the bus: `voss bus send|inbox|wait` as thin REST/SSE clients of the V17-05 endpoints, discovering the server via `VOSS_SERVER_PORT`/`VOSS_SERVER_TOKEN` (exit 2 when absent/unreachable), with the exit-code contract (timeout -> exit 124) and `advice` arrays in `--json` (VBUS-06). Register `bus_group` into the main CLI.

Purpose: VBUS-04 client verbs + VBUS-06 advice on bus verbs.
Output: new `voss/harness/bus_client.py`, registered in `voss/harness/cli.py`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-PATTERNS.md

<interfaces>
<!-- Server endpoints from V17-05 this client targets -->
POST /bus/send  body {body, mentions[], labels[], sender} -> {"v":1,"id": ulid}
GET  /bus/inbox?agent=<id>  -> {"v":1,"messages":[{id,sender,body,mentions,labels,ts}, ...]}
GET  /bus/events  (SSE)     -> ServerSentEvent(event="bus.message", data=<BusMessage json>)
Auth: Authorization: Bearer <VOSS_SERVER_TOKEN>; host loopback :<VOSS_SERVER_PORT>

<!-- CLI analog (PATTERNS.md) -->
voss/harness/cli.py: agent_group click group shape (lines ~3400-3402); env-discovery exit-2 (lines ~1693-1697); jobs_cmd --json (lines ~2882-2886); AGENT_COMMANDS (line ~4484)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: bus_client.py — send/inbox/wait verbs + discovery + advice</name>
  <files>voss/harness/bus_client.py</files>
  <behavior>
    - bus send "@A done" --label task-done -> POST /bus/send, exit 0
    - bus inbox (VOSS_AGENT_ID=A) after two sends -> returns both; repeat call -> returns none (cursor advanced)
    - bus wait --mention A --timeout 60 -> blocks on SSE, unblocks within 2s of a matching send, prints message, exit 0
    - bus wait with no matching message -> exit 124 at timeout
    - any verb with VOSS_SERVER_PORT/TOKEN unset -> exit 2, stderr explains discovery
    - --json output includes an "advice" array (e.g. wait timeout -> advise `voss bus inbox`)
  </behavior>
  <read_first>
    - voss/harness/cli.py (lines ~3400-3441 agent_group; ~1693-1697 env-discovery exit-2; ~2882-2886 jobs_cmd --json with advice)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-CONTEXT.md (D-08 flat stream via @mentions+labels; D-07/VBUS-06 advice composition)
    - voss/harness/server/bus.py (the V17-05 endpoints + BusMessage shape this client consumes)
    - tests/harness/bus/test_bus_wait.py + test_bus_inbox.py (tests this client must satisfy alongside the server)
  </read_first>
  <action>Create `voss/harness/bus_client.py` with `@click.group("bus")` (`bus_group`) and subcommands send/inbox/wait, each with `--json "json_mode"`. A `_resolve_server()` helper reads `VOSS_SERVER_PORT` + `VOSS_SERVER_TOKEN`; if either absent, `click.echo("VOSS_SERVER_PORT/VOSS_SERVER_TOKEN not set. Run inside a voss-managed pane or start voss serve.", err=True); sys.exit(2)`. Use stdlib `http.client`/`urllib` (or the existing harness HTTP helper if one is conventional — check cli.py) for the loopback bearer requests; on connection refused, exit 2 with an actionable message. send: POST /bus/send with body/mentions(parsed from @-tokens)/labels(--label, multiple); identity = VOSS_AGENT_ID for `sender`; exit 0 on 2xx. inbox: GET /bus/inbox?agent=<VOSS_AGENT_ID>; print messages (or one JSON record/line under --json) with an `advice` array; cursor advance is server-side (V17-05). wait: open the /bus/events SSE stream with bearer auth, filter incoming bus.message events by `--mention <id>` and/or `--label <l>`, print the first match and exit 0; enforce `--timeout <s>` (default reasonable) -> on expiry exit 124 (RESEARCH Pattern 9); --json timeout output includes advice like `["voss bus inbox"]`. All verbs honor the 0/2/124 exit contract. No new heavyweight deps (stdlib HTTP/SSE parsing acceptable).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/bus/test_bus_wait.py tests/harness/bus/test_bus_inbox.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - bus wait/inbox tests pass end-to-end against the V17-05 server (XPASS)
    - `grep -v '^#' voss/harness/bus_client.py | grep -c 'sys.exit(2)'` >= 1 and `grep -c 'sys.exit(124)' voss/harness/bus_client.py` >= 1
    - `grep -c 'advice' voss/harness/bus_client.py` >= 1
    - `CliRunner().invoke(bus_group, ["--help"]).exit_code == 0` (asserted in test or summary)
    - no new package added to pyproject.toml dependencies (VBUS-08)
  </acceptance_criteria>
  <done>send/inbox/wait work as REST/SSE clients with discovery exit-2, timeout exit-124, and advice arrays.</done>
</task>

<task type="auto">
  <name>Task 2: Register bus_group in the main CLI</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py (lines ~4484-4525 AGENT_COMMANDS + register())
    - voss/harness/bus_client.py (bus_group to import)
  </read_first>
  <action>Import `bus_group` from `voss.harness.bus_client` in the cli.py import block (match existing style), and add `bus_group` to the `AGENT_COMMANDS` tuple alongside `claims_group` (added in V17-03). Do not modify `register()`. Do not touch board/jobs paths. Confirm `voss bus --help` resolves.</action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness import cli; assert any(getattr(c, 'name', None) == 'bus' for c in cli.AGENT_COMMANDS), 'bus_group not registered'; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - the one-liner prints OK (bus_group in AGENT_COMMANDS)
    - `grep -c 'bus_group' voss/harness/cli.py` >= 2 (import + tuple entry)
    - `git diff voss/harness/cli.py` shows only import + tuple additions
  </acceptance_criteria>
  <done>bus group reachable from the main CLI; no collateral edits.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| shell env -> bus client | VOSS_SERVER_PORT/TOKEN + VOSS_AGENT_ID are env-supplied; message args attacker-controllable |
| bus client -> loopback server | bearer-authed HTTP/SSE to localhost |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V17-15 | Spoofing | sender field set by client | accept | Advisory identity (SEED-001); sender = VOSS_AGENT_ID, spoofable, accepted |
| T-V17-16 | Info disclosure | token in env / process args | mitigate | Token read from env only, sent in Authorization header (not argv); no secrets logged |
| T-V17-17 | DoS | wait holds an SSE connection indefinitely | mitigate | --timeout bounds the wait; exit 124 on expiry closes the stream |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/bus/ -x -q` GREEN end-to-end (client + server).
- bus_group registered; no new deps; board/jobs diff-clean.
</verification>

<success_criteria>
Bus client verbs front the server plane with discovery (exit 2), deterministic wait (exit 124 timeout), cursor-correct inbox, and advice arrays — completing VBUS-04 and VBUS-06's bus surface.
</success_criteria>

<output>
Create `.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-06-SUMMARY.md` when done.
</output>
