---
phase: E3-surface-e2e
plan: 03
type: execute
wave: 3
depends_on: [E3-02]
files_modified:
  - voss/eval/runner.py
  - tests/eval/test_surface_drivers.py
autonomous: true
requirements: [EVSRF-03, EVSRF-04]
must_haves:
  truths:
    - "_drive_serve spawns `python -m voss.cli serve`, parses the {v,port,token} stdout handshake (60s), then drives a turn over httpx REST+SSE"
    - "The SSE GET stream is opened BEFORE the POST /message (events emitted in the gap are not lost)"
    - "On permission.updated the driver POSTs /session/:id/permission with {id, choice}; Allow ('a') completes the turn, Deny ('d') degrades without hanging"
    - "session.idle terminates the SSE loop; final event text is captured as the driver's final"
    - "The bearer token is sent as an Authorization header and never written to any artifact or log"
    - "The serve subprocess is always reaped (stdin EOF heartbeat + proc.wait/kill in finally), even on error"
  artifacts:
    - path: "voss/eval/runner.py"
      provides: "_drive_serve + a unit-testable SSE consume/permission-reply helper + wired serve dispatch"
      contains: "_drive_serve"
    - path: "tests/eval/test_surface_drivers.py"
      provides: "FAKE_TURN serve integration test + permission Allow/Deny parser unit tests"
      contains: "VOSS_SERVE_FAKE_TURN"
  key_links:
    - from: "voss/eval/runner.py _drive_serve"
      to: "POST /session, GET /session/:id/events, POST /session/:id/message, POST /session/:id/permission"
      via: "httpx.AsyncClient REST + client.stream SSE aiter_lines"
      pattern: "/session/\\{?sid|/permission|/events|/message"
    - from: "voss/eval/runner.py _drive_task serve branch"
      to: "_drive_serve"
      via: "await _drive_serve(spec, cwd); map (final, crash_reason, capped)"
      pattern: "_drive_serve\\(spec"
---

<objective>
Implement the serve HTTP/SSE driver — the marquee E3 proof — that spawns `voss serve` as a subprocess, consumes the `{v,port,token}` handshake, drives a full turn over raw httpx REST + SSE (D-07, D-08, EVSRF-03), and handles the permission-gate flow (Allow completes the turn; Deny degrades without hanging — D-09, EVSRF-04). Wire it into the `_drive_task` serve branch. Prove the spawn/handshake/SSE/final plumbing with a `VOSS_SERVE_FAKE_TURN=1` integration test, and prove the permission Allow/Deny reply logic with parser-level unit tests (the FAKE_TURN seam does NOT exercise the permission gate — the live permission proof is the D-11 human checkpoint in E3-04).

Purpose: First Python-native SSE client proof of the V15 live plane end-to-end (spawn → handshake → SSE → permission gate → final) with a real model — nothing in the repo does this today.
Output: `_drive_serve` + a unit-testable SSE consume/permission-reply helper, wired serve dispatch, FAKE_TURN integration test, permission Allow/Deny unit tests.

HARD PRECONDITION: E1-03/E1-04 merged; E3-01 (dispatch skeleton) and E3-02 (CLI drivers + _live_env) merged. Wave ordering guarantees this. E3-03 shares voss/eval/runner.py with E3-02 → sequential wave (file-overlap).
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
@.planning/PROTOCOL.md
@.planning/phases/E3-surface-e2e/E3-02-SUMMARY.md

<interfaces>
Wire contract (pinned from source — do NOT invent beyond this):
- Handshake (serve.py:59): stdout line `{"v":1,"port":N,"token":"<url-safe-32-byte>"}`, printed with flush AFTER the socket binds (race-safe). Token field non-empty.
- serve spawn: `python -m voss.cli serve` (serve_cmd takes NO --cwd; cwd flows via session create body). stdin held open = heartbeat; stdin EOF self-terminates the server.
- POST /session  (app.py:288, status 201): body {"cwd": "<fixture>", "auth": "auto"}; header Authorization: Bearer <token>; resp {"v":1,"id":"<sid>","auth":...,"resumed":...}.
- GET /session/{sid}/events (app.py:390, EventSourceResponse): first event `server.connected`; thereafter `event: <type>\ndata: <json>\n\n`; payload also carries a `type` field. ping=15.
- POST /session/{sid}/message (app.py:354, status 202): body {"parts":[{"type":"text","text":"<prompt>"}], "mode":"plan"|"edit"|"auto"}.
- permission.updated event (app.py:128-136): data {"v":1,"type":"permission.updated","id":"<8hex>","tool_name":...,"args":{...},"dimension":"tool"}.
- POST /session/{sid}/permission (app.py:379): body {"id":"<req_id>","choice":"a"|"A"|"d"}; resp {"v":1,"status":"ok"} (or "stale" if the future already resolved). The server gate Future.result(timeout=300) returns "d" on timeout.
- final event: data {"v":1,"type":"final","text":"<answer>",...}. session.idle event terminates the stream.

FAKE_TURN seam (app.py:166-178): VOSS_SERVE_FAKE_TURN=1 makes _run_turn emit a canned turn (show_user → ... → show_final(f"echo: {text}") → session_idle) over the real event/SSE path WITHOUT a provider. IMPORTANT: the FAKE_TURN path returns BEFORE _install_server_permissions — it does NOT emit permission.updated. So FAKE_TURN proves spawn/handshake/SSE/final/idle, but CANNOT prove the permission reply path; test permission at the parser/unit level and prove it live in E3-04.

_drive_task return tuple (from E3-01): (record, final, crash_reason_or_None, capped). _live_env from E3-02.
RESEARCH Pattern 3 (lines 280-460) and PATTERNS runner.py serve section (lines 148-235) carry the full reference body — mirror it.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: _drive_serve (spawn + handshake + SSE-before-POST + permission reply + teardown)</name>
  <files>voss/eval/runner.py</files>
  <read_first>
    - voss/eval/runner.py (FULL — imports lines 1-35 confirm asyncio/json/subprocess/httpx present; add sys/threading/time if missing; _live_env from E3-02; _drive_task serve branch stub from E3-01)
    - voss/harness/server/serve.py (lines 44-60 — handshake emission: secrets.token_urlsafe(32), bind-before-print, json.dumps({"v":1,"port":...,"token":...}), flush=True)
    - voss/harness/server/app.py (lines 288-419 — POST /session, GET /events generator first-event server.connected, POST /message, POST /permission reply_permission; lines 118-152 _install_server_permissions emits permission.updated with 8hex id; lines 160-178 FAKE_TURN seam that SKIPS permissions)
    - .planning/PROTOCOL.md (§2 handshake, §4 SSE, §6 event union, §7 permission, §11 message/idle)
    - .planning/phases/E3-surface-e2e/E3-RESEARCH.md (Pattern 3 lines 280-460 full _drive_serve reference; Pitfall 1 SSE order lines 572-576; Pitfall 4 cold-start handshake timeout lines 590-594; Pitfall 5 deny-no-hang lines 596-600; anti-patterns lines 476-483)
    - .planning/phases/E3-surface-e2e/E3-PATTERNS.md (runner.py serve section lines 148-235 — exact body to mirror)
  </read_first>
  <action>
    In voss/eval/runner.py add `import sys`, `import threading`, `import time` if not already present. Implement two functions so the permission/SSE logic is unit-testable WITHOUT a live server:

    (A) `async def _consume_sse(client, base_url, sid, headers, *, permission_choice) -> str`: given an OPEN AsyncClient, open `client.stream("GET", f"{base_url}/session/{sid}/events", headers={**headers, "Accept":"text/event-stream"})`; INSIDE that `async with`, FIRST POST the message (so the stream is open before message events flow — Pitfall 1), then consume `aiter_lines()`. Parse SSE frames: strip "\r"; blank line resets event_type; ":" lines are pings (skip); "event:" sets event_type; "data:" json-loads the payload; `ev_type = payload.get("type", event_type)`. On `permission.updated`: `await client.post(f"{base_url}/session/{sid}/permission", json={"id": payload["id"], "choice": permission_choice}, headers=headers)` (do NOT block the loop on a separate thread — issue the reply as a normal await inside the async-for; httpx AsyncClient supports concurrent requests on one client). On `final`: capture `payload.get("text","")`. On `session.idle`: break. Return final_text. Take the message-post as a callback/param so the same function is exercised in unit tests with a fake stream. NON-NEGOTIABLE: `_consume_sse` MUST exist as a module-level importable helper named exactly `_consume_sse` — Task 2's unit tests import it unconditionally; inlining this loop into _drive_serve is NOT permitted. (Factoring discretion applies only to WHERE the POST /message happens inside the stream context — the invariants are stream-open-before-message and reply-as-await-inside-loop.)

    (B) `async def _drive_serve(spec, cwd, *, permission_choice="a", timeout=180.0) -> tuple[str, str | None, bool]`:
      - env = _live_env(cwd); ensure env["VOSS_DEV"]="1".
      - proc = subprocess.Popen([sys.executable, "-m", "voss.cli", "serve"], env=env, cwd=str(cwd), stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True, bufsize=1). Drain stderr in a daemon thread into a list so the pipe never fills and blocks the server (Pitfall 4 anti-pattern).
      - Parse handshake: iterate proc.stdout lines, json.loads each, accept the first with a non-empty "token"; 60s deadline (time.monotonic); on timeout proc.kill() and return ("", f"handshake timeout; stderr: {last 10 stderr lines}", False).
      - base_url = f"http://127.0.0.1:{handshake['port']}"; headers = {"Authorization": f"Bearer {handshake['token']}"}.
      - try: async with httpx.AsyncClient(timeout=timeout) as client: POST /session {"cwd": str(cwd), "auth": "auto"} → raise_for_status → sid = r.json()["id"]; final = await _consume_sse(client, base_url, sid, headers, permission_choice=permission_choice, <message body {"parts":[{"type":"text","text":spec.prompt}],"mode":spec.mode}>).
      - except Exception as exc: return ("", f"{type(exc).__name__}: {str(exc)[:300]}", False).
      - finally: if proc.stdin: proc.stdin.close() (EOF heartbeat → server self-terminates); try proc.wait(timeout=10) except TimeoutExpired: proc.kill().
      - return (final, None, False).

    SECURITY: never log or write `handshake["token"]` anywhere except the Authorization header. Do not put the token into the returned final, crash_reason, or any artifact. crash_reason must not echo the bearer header.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.eval.runner import _drive_serve, _consume_sse; import inspect; assert inspect.iscoroutinefunction(_drive_serve); print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "_drive_serve" voss/eval/runner.py` >= 1 and `_drive_serve` is an async function (the import verify prints `ok`).
    - `_consume_sse` is a module-level importable helper: `from voss.eval.runner import _consume_sse` succeeds (the verify command imports it) — NOT inlined into _drive_serve.
    - The SSE stream is opened before the message POST: `grep -n "client.stream" voss/eval/runner.py` appears before the `/message` POST within the serve consume flow (verify by reading the function — stream-context wraps the message post).
    - Handshake parse uses a 60s deadline and rejects lines without a token: `grep -c "token" voss/eval/runner.py` >= 1 and `grep -c "60" voss/eval/runner.py` >= 1 (handshake deadline).
    - Permission reply posts {"id":..., "choice": permission_choice} to /session/.../permission: `grep -c "/permission" voss/eval/runner.py` >= 1 and `grep -c "choice" voss/eval/runner.py` >= 1.
    - Teardown is in a finally with stdin.close() + proc.wait/kill: `grep -c "proc.stdin.close" voss/eval/runner.py` >= 1 and `grep -c "proc.kill" voss/eval/runner.py` >= 1.
    - The token never appears in crash_reason/final/artifacts: no `grep` for the literal token; assert by code review that only `headers` carries it (and the threat test in Task 2 asserts crash_reason on a forced failure contains no "Bearer").
    - `.venv/bin/python -c "import voss.eval.runner"` imports cleanly.
  </acceptance_criteria>
  <done>_drive_serve spawns/handshakes/drives a turn over SSE with stream-before-message ordering, permission reply, and guaranteed teardown; _consume_sse is a module-level importable helper; token confined to the Authorization header.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire serve dispatch + FAKE_TURN integration test + permission Allow/Deny unit tests</name>
  <files>voss/eval/runner.py, tests/eval/test_surface_drivers.py</files>
  <read_first>
    - voss/eval/runner.py (the _drive_task serve branch stub from E3-01 — replace with await _drive_serve; the _consume_sse + _drive_serve from Task 1)
    - voss/harness/server/app.py (FAKE_TURN seam lines 160-178 — what it emits: show_final(f"echo: {text}") then session_idle; it does NOT emit permission.updated)
    - tests/harness/test_server_app.py (lines 1-49 FAKE_TURN/TestClient setup; lines 119-138 test_permission_reply_resolves_future pattern — the permission Future contract)
    - tests/eval/conftest.py (autouse VOSS_DEV=1 inherited)
    - .planning/phases/E3-surface-e2e/E3-PATTERNS.md (test_surface_drivers.py serve section lines 363-388 — FAKE_TURN fixture + serve stub test)
    - .planning/phases/E3-surface-e2e/E3-RESEARCH.md (Validation map EVSRF-05/06/07 lines 784-786; Pitfall 5 deny-no-hang lines 596-600; Pitfall 6 sentinel staleness lines 602-606)
  </read_first>
  <action>
    In voss/eval/runner.py _drive_task: replace the serve not-implemented stub branch (from E3-01) with a real call: `final, crash_reason, capped = await _drive_serve(spec, cwd)` (default Allow; E3-04 adds the permission_choice field to TaskSpec and threads it through). Return `(record, final, crash_reason, capped)`. The Deny path is exercised at the unit level (below) and live via a dedicated scenario in E3-04.

    In tests/eval/test_surface_drivers.py add:

    - test_serve_stub (FAKE_TURN integration): the fixture uses `monkeypatch.setenv("VOSS_SERVE_FAKE_TURN", "1")` — env-only injection; `_live_env`'s `dict(os.environ)` copy picks it up naturally and passes it to the spawned server. Do NOT monkeypatch `_live_env` for the serve tests. Build a tmp fixture cwd. spec = TaskSpec(prompt="hello", mode="plan", rubric="...", surface="serve"). final, crash, capped = asyncio.run(_drive_serve(spec, cwd)). Assert crash is None and "echo: hello" in final (the FAKE_TURN canned final). This proves spawn → handshake → POST /session → SSE-open-before-message → final → session.idle → teardown end-to-end against the real server, no provider, no creds.

    - test_serve_permission_allow_parser AND test_serve_permission_deny_parser (UNIT, parser-level — FAKE_TURN does NOT emit permission.updated, so drive _consume_sse with a FAKE httpx client/stream): construct a fake AsyncClient whose `.stream(...)` yields a synthetic SSE line sequence containing a `permission.updated` frame (with id="abcd1234"), then a `final` frame, then `session.idle`, and whose `.post(...)` records calls. Run `_consume_sse(fake_client, base, sid, headers, permission_choice="a", ...)`; assert the fake client recorded a POST to `/session/<sid>/permission` with json {"id":"abcd1234","choice":"a"}, and the returned final text matches the synthetic final. Repeat with permission_choice="d" asserting choice=="d" AND that the loop still terminates on session.idle (no hang — bounded by the synthetic stream).

    - test_serve_token_not_leaked (THREAT): force _drive_serve to fail after handshake (e.g. monkeypatch httpx.AsyncClient.post to raise) and assert the returned crash_reason contains neither "Bearer" nor the handshake token substring.

    Wave-0 fictional-API guard (MEMORY "GSD scaffold fictional API"): import `_consume_sse` unconditionally — `from voss.eval.runner import _consume_sse` at module top, alongside `_drive_serve`. Task 1's acceptance criteria guarantee `_consume_sse` exists as a module-level importable helper; an ImportError/NameError must fail these tests loudly. Do NOT wrap the import in try/except, do NOT xfail or skip, and do NOT adapt the tests around a missing or renamed helper.

    No JSONL field is added in this plan, so REQUIRED_FIELDS is unchanged — but confirm `surface` is still present from E3-01 (Pitfall 6 — do not let the sentinel drift).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_surface_drivers.py -x -q -k "serve or permission"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "_drive_serve(spec" voss/eval/runner.py` >= 1 (serve dispatch wired; no remaining not-implemented serve stub).
    - test_surface_drivers.py contains `monkeypatch.setenv("VOSS_SERVE_FAKE_TURN", "1")`: `grep -c 'monkeypatch.setenv("VOSS_SERVE_FAKE_TURN"' tests/eval/test_surface_drivers.py` >= 1. The serve/permission tests do NOT monkeypatch `_live_env` (the CLI stub tests from E3-02 in the same file may) — FAKE_TURN reaches the spawned server solely via the os.environ setenv.
    - test_surface_drivers.py imports `_consume_sse` unconditionally at module top: `grep -c "_consume_sse" tests/eval/test_surface_drivers.py` >= 1, with no try/except around the import and no xfail/skip guards on the permission tests.
    - test_serve_stub passes: asyncio.run(_drive_serve(...)) with VOSS_SERVE_FAKE_TURN=1 returns crash None and final containing "echo: hello" — proving spawn/handshake/SSE/final/idle/teardown end-to-end offline.
    - test_serve_permission_allow_parser asserts a POST to /session/<sid>/permission with json {"id":"abcd1234","choice":"a"}.
    - test_serve_permission_deny_parser asserts choice=="d" AND the consume loop terminates on session.idle (the test completes in bounded time — no 300s hang).
    - test_serve_token_not_leaked asserts the crash_reason contains neither "Bearer" nor the token.
    - All serve/permission tests run offline (no creds, no network beyond loopback FAKE_TURN server): `.venv/bin/python -m pytest tests/eval/test_surface_drivers.py -q -k "serve or permission"` green.
    - `surface` still in REQUIRED_FIELDS (no sentinel drift): `grep -c "surface" tests/eval/test_voss_eval_stub.py` >= 1.
    - Full eval suite green: `.venv/bin/python -m pytest tests/eval -q -m 'not live'`.
  </acceptance_criteria>
  <done>serve dispatch wired; FAKE_TURN integration test (env-pinned via monkeypatch.setenv only) proves the full spawn→SSE→final plumbing offline; permission Allow/Deny proven at the parser level against the unconditionally-imported _consume_sse with deny-no-hang; token-leak threat asserted.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| serve subprocess stdout (handshake) → driver | untrusted-shaped JSON line; validate token non-empty before use |
| driver → server (loopback HTTP) | bearer token in Authorization header; loopback-only, no TLS needed |
| bearer token → artifacts/logs | the token is an ephemeral per-process secret; must never reach JSONL/summary/crash_reason |
| permission gate (server Future) → driver reply | Allow/Deny choice must always be sent so the gate never hangs to its 300s timeout |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E3-07 | Spoofing | handshake token interception | mitigate | server binds 127.0.0.1 only (PROTOCOL §1); driver connects loopback; no token on the wire outside loopback |
| T-E3-08 | Information | bearer token leaking into JSONL/summary/crash_reason/logs | mitigate | token confined to the Authorization header; crash_reason truncates exc text and is asserted free of "Bearer"/token (test_serve_token_not_leaked) |
| T-E3-09 | Denial | permission gate hangs on missing reply | mitigate | driver always issues a reply on permission.updated (Allow or Deny); deny-no-hang asserted; scenario timeout (180s) < server 300s gate timeout |
| T-E3-10 | Denial | runaway/zombie serve subprocess | mitigate | stdin-EOF heartbeat + proc.wait(timeout=10)/proc.kill() in finally; stderr drained in a daemon thread so the pipe never blocks the server |
| T-E3-11 | Tampering | FAKE_TURN seam activating outside tests | mitigate | VOSS_SERVE_FAKE_TURN is read only by the server (app.py:166) and set ONLY via monkeypatch.setenv inside the test fixture; live drivers never set it; live run (E3-04) runs without it |
| T-E3-SC | Tampering | npm/pip/cargo installs | accept | zero new packages (httpx/fastapi/uvicorn/sse-starlette already installed); no install tasks |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/test_surface_drivers.py -q -k "serve or permission"` → serve + permission tests green offline
- FAKE_TURN integration: spawn → handshake → SSE-before-message → final → idle → teardown
- Permission Allow ('a') and Deny ('d') reply asserted at parser level; deny terminates (no hang)
- Token confined to Authorization header; crash_reason free of Bearer/token
- `.venv/bin/python -m pytest tests/eval -q -m 'not live'` → full suite green
</verification>

<success_criteria>
- serve driver spawns server, parses handshake, drives a turn over httpx REST+SSE with stream-before-message ordering (EVSRF-03, D-07, D-08)
- permission.updated → reply; Allow completes, Deny degrades without hanging (EVSRF-04, D-09)
- FAKE_TURN integration test proves the full plumbing offline; permission proven at parser level (live proof = E3-04 checkpoint)
- bearer token never leaks into artifacts; serve subprocess always reaped
</success_criteria>

<output>
Create `.planning/phases/E3-surface-e2e/E3-03-SUMMARY.md` when done
</output>
