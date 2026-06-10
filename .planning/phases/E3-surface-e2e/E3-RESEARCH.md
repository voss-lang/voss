# Phase E3: Surface E2E - Research

**Researched:** 2026-06-10
**Domain:** Live subprocess/HTTP eval drivers for CLI and server surfaces
**Confidence:** HIGH

---

## Summary

E3 adds four per-surface drivers — `cli:do`, `cli:chat`, `cli:edit`, and `serve` — on top of the E1 substrate, all gated behind `VOSS_DEV=1`. The drivers live in `voss/eval/runner.py` and dispatch from `_drive_task` via the new `surface` field on `TaskSpec`. Scenarios go in `tests/eval/surfaces/<NN>-<slug>/task.toml` and run via `voss eval --suite surfaces`.

**Critical execution dependency:** E1-03 through E1-05 have NOT yet been executed (only E1-01 and E1-02 have summaries). E3 cannot be planned until E1 finishes — `run_suite` does not yet accept `max_turns`, `gate_pass`/`capped` are not wired into JSONL rows, and golden checks are not retrofitted. E3 treats the E1-03 plan's pinned interfaces as contracts (they will be live before E3 executes).

**Primary recommendation:** Implement per-surface driver functions in `voss/eval/runner.py` that are pure "invocation adapters" — each produces a `(final: str, file_diff: str)` tuple which feeds directly into the existing hybrid-scoring path. Keep serve scenarios hermetic-testable via `VOSS_SERVE_FAKE_TURN=1`; live scenarios require codex subscription auth and `VOSS_DEV=1`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Live suite covers exactly four surfaces: `cli:do`, `cli:chat` (scripted non-interactive turn), `cli:edit`, and `serve` (session create → live turn → SSE consumption → permission Allow/Deny → final).

**D-02:** Excluded from E3: `voss doctor`/`voss check` (no model involvement), `voss board`/`voss team run` (org-plane, heavy multi-agent sub burn), multiagent chat spawn.

**D-03:** Reuse the E1 substrate, no new runner: scenarios are `task.toml` files in `tests/eval/surfaces/<NN>-<slug>/` invoked via `voss eval --suite surfaces`.

**D-04:** `TaskSpec` gains an optional `surface` field (default `"internal"` = current in-process drive). Values: `internal | cli:do | cli:chat | cli:edit | serve`. The runner dispatches per-surface drivers.

**D-05:** CLI surfaces run as real subprocesses (`python -m voss.cli ...`) with live auth env passed through — reuse `Result`/invocation ergonomics of `tests/e2e/runner.py` WITHOUT its stub `sitecustomize.py` injection.

**D-06:** `cli:chat` is driven non-interactively (piped/scripted single prompt + exit). No PTY.

**D-07:** Server driver = raw Python httpx + SSE inside the eval runner. NOT TS/Go SDKs.

**D-08:** Server scenarios spawn `voss serve` as a subprocess and consume the one-line `{v,port,token}` stdout handshake. One server per scenario, killed on completion.

**D-09:** Permission-gate flow in scope: at least one serve scenario must hit a gated tool call, receive `permission.updated` on SSE, reply Allow via `POST /session/:id/permission`, complete the turn. A Deny variant asserts the turn degrades without hanging.

**D-10:** `tests/e2e/` stays untouched (hermetic regression layer, normal pytest, CI-safe). E3's live suite is a separate artifact. No shared fixtures.

**D-11:** One documented live run on codex subscription auth: every surface ≥1 scenario, overall ≥80% gate_pass, 0 capped rows, serve permission-gate scenario among the passers.

### Claude's Discretion
- Scenario count per surface (1–2 each; keep total sub burn ≤ ~10 scenarios).
- Driver internals (where subprocess/SSE drivers live in `voss/eval/`, naming, timeout plumbing).
- serve readiness/teardown details (handshake parse, port wait, kill semantics).
- Whether `surface` dispatch is a registry dict or match statement.

### Deferred Ideas (OUT OF SCOPE)
- `voss board` / `voss team run` live e2e
- Multiagent chat spawn live scenario
- Stub-layer graduation/dedup with live suite
- TS/Go SDK-driven server scenarios (E4)
- PTY-interactive chat driving (E5)
</user_constraints>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TaskSpec `surface` field + dispatch | eval substrate (runner.py) | suite.py schema | Routing belongs in the runner alongside the existing `_drive_task`; schema owns validation |
| `cli:do` subprocess driver | eval driver (runner.py) | tests/e2e/runner.py (reference, not reused) | Subprocess invocation mirrors e2e runner but without stub injection |
| `cli:chat` non-interactive driver | eval driver (runner.py) | cli.py stdin/input() path | Piped stdin drives the REPL's `input()` loop; driver controls process stdin |
| `cli:edit` subprocess driver | eval driver (runner.py) | cli.py edit_cmd | Requires a concrete file argument; fixture must contain a target file |
| `serve` HTTP/SSE driver | eval driver (runner.py) | server/app.py contract | Driver must own spawn, handshake parse, SSE streaming, permission reply, teardown |
| Permission-gate reply | serve driver (in-runner) | PROTOCOL.md §7 | Driver-side: POST /session/:id/permission; server-side already handles it |
| Auth pass-through (CLI surfaces) | os.environ (inherited) | harness/auth.py | Subprocess inherits caller env; no auth mutation needed |
| Auth for serve surface | serve driver | server/app.py create_session | `auth` field in CreateSessionBody defaults to "auto" — inherits env |
| JSONL row + scoring | E1 substrate (runner.py) | suite.py checks | E3 drivers feed `final` + `file_diff` into existing row-building path |

---

## Standard Stack

### Core (no new dependencies — all already installed)

| Library | Version (installed) | Purpose | Why Standard |
|---------|---------------------|---------|--------------|
| `httpx` | 0.28.1 | HTTP client for serve driver (REST + SSE) | Already in repo via litellm/anthropic; `async with client.stream()` + `aiter_lines()` available |
| `subprocess` (stdlib) | 3.13 | CLI subprocess driver | Already used by `tests/e2e/runner.py`; no new dep |
| `asyncio` (stdlib) | 3.13 | serve driver async loop | Already used by eval runner |
| `sse-starlette` | ≥3.4 | Server-side SSE (no new client dep needed) | Existing server dep; client-side uses raw httpx |

[VERIFIED: installed, confirmed via `.venv/bin/python -c "import httpx; print(httpx.__version__)"` → `0.28.1`]
[VERIFIED: fastapi, uvicorn already installed in `.venv`]

**No new packages to install.** E3 is a pure code addition that wires existing dependencies.

---

## Package Legitimacy Audit

E3 introduces **zero new external packages**. All required libraries (httpx, subprocess, asyncio, fastapi, uvicorn, sse-starlette) are already present in the project's `.venv`. The Package Legitimacy Gate is not applicable.

**Packages removed due to slopcheck:** none
**Packages flagged as suspicious:** none

---

## Architecture Patterns

### System Architecture Diagram

```
voss eval --suite surfaces
     │
     ▼
run_suite() ──── load_suite("surfaces") ──► tests/eval/surfaces/**/*.toml
     │                                       (surface field: cli:do | cli:chat | cli:edit | serve)
     │
     ├── for each task:
     │     │
     │     ▼
     │   _drive_task(task_id, spec, ..., surface=spec.surface)
     │     │
     │     ├─ surface == "internal" ──► existing run_turn() in-process [unchanged]
     │     │
     │     ├─ surface == "cli:do"   ──► _drive_cli_do(spec, cwd, env)
     │     │                               subprocess: python -m voss.cli do "<prompt>" --plain
     │     │                               returns (stdout-as-final, "")
     │     │
     │     ├─ surface == "cli:chat" ──► _drive_cli_chat(spec, cwd, env)
     │     │                               subprocess: python -m voss.cli chat --plain
     │     │                               stdin = "<prompt>\n" → input() → EOFError → exit
     │     │                               returns (stdout-as-final, "")
     │     │
     │     ├─ surface == "cli:edit" ──► _drive_cli_edit(spec, cwd, env, target_file)
     │     │                               subprocess: python -m voss.cli edit <target_file> --plain
     │     │                               stdin = "<prompt>\n" → REPL → EOFError → exit
     │     │                               returns (stdout-as-final, git diff)
     │     │
     │     └─ surface == "serve"    ──► _drive_serve(spec, cwd, env)
     │                                     spawn: python -m voss.cli serve
     │                                     read stdout handshake: {"v":1,"port":N,"token":"..."}
     │                                     POST /session  → session_id
     │                                     GET /session/:id/events (SSE open)
     │                                     POST /session/:id/message {parts, mode}
     │                                     stream events until session.idle:
     │                                       permission.updated → POST /session/:id/permission
     │                                       final → capture text
     │                                       session.idle → done
     │                                     kill server subprocess
     │                                     returns (final.text, git diff from fixture cwd)
     │
     ▼
   _run_checks(spec.checks, cwd)   ──► gate_pass, check_results  [E1-01 executor]
     │
     ▼
   judge_run(...)                  ──► verdict  [E1 judge; skipped if capped]
     │
     ▼
   _append_row(runs_path, row)     ──► .voss/eval/<ts>/runs.jsonl
     │                                 (additive: surface field appended)
     ▼
   write_summary(...)              ──► .voss/eval/<ts>/summary.md
```

### Recommended Project Structure

```
voss/eval/
├── suite.py          # +surface field on TaskSpec (E3 change)
├── runner.py         # +surface dispatch + 4 driver functions (E3 change)
├── judge.py          # unchanged
└── summary.py        # unchanged (surface field in JSONL is additive)

tests/eval/
└── surfaces/         # new suite directory (E3 creates)
    ├── 01-do-simple/
    │   ├── task.toml       # surface = "cli:do"
    │   └── fixture/        # seed project dir (git init in _prepare_fixture)
    ├── 02-chat-turn/
    │   ├── task.toml       # surface = "cli:chat"
    │   └── fixture/
    ├── 03-edit-file/
    │   ├── task.toml       # surface = "cli:edit", target_file = "..."
    │   └── fixture/
    ├── 04-serve-basic/
    │   ├── task.toml       # surface = "serve"
    │   └── fixture/
    └── 05-serve-permission/
        ├── task.toml       # surface = "serve", triggers fs_write permission gate
        └── fixture/

tests/eval/
└── test_surface_drivers.py   # stub-mode driver unit tests (VOSS_SERVE_FAKE_TURN)
```

### Pattern 1: surface Field on TaskSpec (Additive Schema Extension)

**What:** Add `surface: Literal["internal","cli:do","cli:chat","cli:edit","serve"] = "internal"` to `TaskSpec` (extra="forbid" safe because it's an explicit field, not a key violation).

**When to use:** Every surface scenario's `task.toml` sets `surface = "cli:do"` etc. Golden tasks have no `surface` key → default `"internal"` → unchanged behavior (back-compat guaranteed).

```toml
# Source: E3-CONTEXT.md D-04; mirrors existing suite.py field pattern
surface = "cli:do"
prompt = "Add a function that returns the sum of two integers."
mode = "edit"
auto_approve_edits = true
rubric = """
PASS if the function exists in the source file.
"""
judge_inputs = ["final", "file_diff"]

[[checks]]
type = "file_contains"
path = "calc.py"
text = "def add"
```

### Pattern 2: CLI Subprocess Driver (cli:do, cli:chat, cli:edit)

**What:** Invoke `python -m voss.cli <verb> ...` as a subprocess with live auth env, piped stdin, captured stdout/stderr.

**Key insight from `do_cmd` source:**
- `do_cmd` reads piped stdin and appends it to the task. When stdin is piped and NOT a TTY (`sys.stdin.isatty() == False`), it reads `sys.stdin.read()` and appends `"\n--- piped stdin ---\n" + content` to the prompt parts. For the `cli:do` driver, pass the prompt as a CLI argument AND set `stdin=""` to avoid the piped-stdin path adding empty noise — or rely on the argument-only path if piped stdin is clean.
- Actually: `not sys.stdin.isatty()` is True when stdin is piped — even empty stdin appends the separator line. Use `stdin=None` (no piping; let subprocess inherit) to keep TTY detection clean, OR pass the full prompt only as the CLI argument and accept the trailing separator.

**Recommendation:** For `cli:do`, pass the full prompt as the CLI positional argument. Use `stdin=subprocess.DEVNULL` (avoids the piped-stdin branch entirely). The `--plain` flag forces PlainRenderer output (no TUI, clean stdout).

**Key insight from `chat_cmd` / `_run_repl` source:**
- `chat_cmd` enters `_run_repl()` which calls `input(_repl_prompt())` in a loop. When stdin is piped, `input()` reads the first line, processes it as a turn, then on the next call raises `EOFError`. The `except (EOFError, KeyboardInterrupt)` handler runs conventions extraction then returns cleanly. A single piped prompt line drives exactly one turn then exits.
- Use `stdin="single prompt\n"` piped as bytes. Output via `--plain` flag.

**Key insight from `edit_cmd` source:**
- `edit_cmd` requires a positional `path` argument (`click.Path(exists=True)`). The path must exist in the fixture dir at subprocess call time. It then calls `_run_repl()` — same EOFError exit-on-stdin-EOF behavior as chat.
- The `surface` task.toml needs a companion `target_file` field (Claude's discretion) OR the driver derives the target file from the fixture structure. **Recommendation:** add an optional `target_file: str | None = None` field to `TaskSpec` for `cli:edit` scenarios. The driver calls `python -m voss.cli edit <fixture_cwd/target_file> --cwd <fixture_cwd> --plain` with stdin=prompt.

**Auth pass-through:** Subprocess env = `dict(os.environ)` with `LITELLM_LOCAL_MODEL_COST_MAP=true` added (prevents litellm cold-start network fetch that can add 12s). Do NOT strip auth keys — live auth is the entire point of E3 drivers. Do NOT inject `sitecustomize.py` (D-05).

```python
# Source: analysis of voss/harness/cli.py do_cmd, chat_cmd, edit_cmd + tests/e2e/runner.py

import subprocess, sys, os
from pathlib import Path

def _live_env(cwd: Path) -> dict:
    """Build env for live CLI subprocess: inherit caller env, add litellm guard."""
    env = dict(os.environ)
    env["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"
    env["VOSS_DEV"] = "1"
    env["PYDANTIC_DISABLE_PLUGINS"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    return env

def _drive_cli_do(prompt: str, cwd: Path, *, timeout: float = 120.0) -> tuple[str, str]:
    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "do", prompt, "--plain"],
        cwd=str(cwd),
        env=_live_env(cwd),
        stdin=subprocess.DEVNULL,  # no piped stdin; avoids appending the separator
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout, result.returncode  # caller uses stdout as "final"

def _drive_cli_chat(prompt: str, cwd: Path, *, timeout: float = 120.0) -> tuple[str, str]:
    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "chat", "--plain"],
        cwd=str(cwd),
        env=_live_env(cwd),
        input=prompt + "\n",   # single line → input() reads it → EOFError → clean exit
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout, result.returncode
```

[VERIFIED: cli.py source lines 1690-1692 for do_cmd stdin handling; lines 2182-2196 for chat REPL EOF exit; lines 1865-1941 for edit_cmd path argument]

### Pattern 3: Serve Driver (HTTP + SSE)

**What:** Python async function that spawns `voss serve`, reads handshake, drives a full turn via httpx REST + SSE streaming, then kills the server.

**Spawn command (from Rust SDK `supervisor.rs` as reference):**
```
python -m voss.cli serve
```
With env: `LITELLM_LOCAL_MODEL_COST_MAP=true`, `PYDANTIC_DISABLE_PLUGINS=1`, stdin piped (held open as heartbeat — server self-terminates on stdin EOF).

**Handshake (from `serve.py:59`, `PROTOCOL.md §2`):**
```json
{"v":1,"port":54123,"token":"<url-safe-32-byte>"}
```
Server binds BEFORE printing this line (race-safe). Read stdout line-by-line; parse JSON; validate `"token"` field non-empty. Timeout: 60s (litellm cold import can take ~45s on first run; warm ~15s).

**Session creation (`app.py:288-311`):**
```
POST /session
Authorization: Bearer <token>
Content-Type: application/json
{"v":1,"cwd":"<fixture_cwd_str>","auth":"auto"}
→ 201 {"v":1,"id":"<session_id>","auth":"codex-oauth","resumed":false}
```

**SSE open + message (`app.py:390-419`, `PROTOCOL.md §4,§11`):**
```
GET /session/:id/events
Authorization: Bearer <token>
Accept: text/event-stream
→ 200 text/event-stream
  First event: "event: server.connected\ndata: {"v":1,"type":"server.connected"}\n\n"

POST /session/:id/message
Authorization: Bearer <token>
Content-Type: application/json
{"parts":[{"type":"text","text":"<prompt>"}],"mode":"plan"}
→ 202 {"v":1,"status":"accepted"}
```

**SSE event wire format (from `app.py:406-412`, `sse_starlette`):**
```
event: <type>
data: {"v":1,...payload...}
id: <seq>
\n
```
Parse with httpx `aiter_lines()` — detect `event:` prefix, then `data:` prefix; emit on blank line. The `type` discriminator field is also in the `data` JSON payload (redundant with the SSE `event:` field; use JSON `type` for routing since the `AgentEventAdapter` uses it).

**Permission gate flow (from `app.py:379-386`, `PROTOCOL.md §7`):**
```
SSE event: permission.updated
data: {"v":1,"type":"permission.updated","id":"req_id","tool_name":"fs_write","args":{...},"dimension":"tool"}

→ reply:
POST /session/:id/permission
{"id":"req_id","choice":"a"}    # "a"=allow once, "A"=allow always, "d"=deny
→ 200 {"v":1,"status":"ok"}    # or "stale" if timeout
```

**Turn completion (from `PROTOCOL.md §6,§11`):**
```
event: final
data: {"v":1,"type":"final","text":"<agent final answer>","confidence":0.9,"cost_usd":0.01}

event: session.idle
data: {"v":1,"type":"session.idle","session_id":"<id>"}
```
`session.idle` is the terminator — stop reading the SSE stream after this event.

**Teardown:** Kill the serve subprocess (send SIGTERM or `proc.kill()`). Server has stdin-EOF heartbeat so closing the stdin pipe also terminates it. Use `proc.communicate()` with timeout to reap.

```python
# Source: PROTOCOL.md §2, §4, §7, §11; serve.py:59; app.py:288-419; supervisor.rs reference

import asyncio, json, subprocess, sys, os, threading
from pathlib import Path
import httpx

async def _drive_serve(
    prompt: str,
    cwd: Path,
    *,
    mode: str = "plan",
    permission_choice: str = "a",  # "a" = allow, "d" = deny
    timeout: float = 180.0,
) -> tuple[str, str]:
    """Spawn voss serve, drive a full turn, return (final_text, git_diff)."""
    env = _live_env(cwd)
    env["VOSS_DEV"] = "1"

    proc = subprocess.Popen(
        [sys.executable, "-m", "voss.cli", "serve"],
        env=env,
        cwd=str(cwd),
        stdin=subprocess.PIPE,   # held open = heartbeat; closing EOF-terminates server
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    # drain stderr in background so pipe never fills and blocks the server
    stderr_lines = []
    def _drain_stderr():
        for line in proc.stderr:
            stderr_lines.append(line)
    threading.Thread(target=_drain_stderr, daemon=True).start()

    # Parse handshake: {"v":1,"port":N,"token":"..."}
    handshake = None
    import time; deadline = time.monotonic() + 60.0
    for line in proc.stdout:
        try:
            h = json.loads(line.strip())
            if h.get("token"):
                handshake = h
                break
        except json.JSONDecodeError:
            pass
        if time.monotonic() > deadline:
            proc.kill()
            raise TimeoutError(f"handshake timeout; stderr: {''.join(stderr_lines[-10:])}")

    base_url = f"http://127.0.0.1:{handshake['port']}"
    token = handshake["token"]
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1. Create session
            r = await client.post(f"{base_url}/session",
                json={"cwd": str(cwd), "auth": "auto"}, headers=headers)
            r.raise_for_status()
            sid = r.json()["id"]

            # 2. Open SSE stream
            final_text = ""
            async with client.stream("GET", f"{base_url}/session/{sid}/events",
                                     headers={**headers, "Accept": "text/event-stream"}) as sse:
                # 3. Post message
                await client.post(f"{base_url}/session/{sid}/message",
                    json={"parts": [{"type":"text","text":prompt}], "mode": mode},
                    headers=headers)

                # 4. Consume events
                event_type = ""
                async for line in sse.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        try:
                            payload = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        ev_type = payload.get("type", event_type)

                        if ev_type == "permission.updated":
                            req_id = payload["id"]
                            await client.post(
                                f"{base_url}/session/{sid}/permission",
                                json={"id": req_id, "choice": permission_choice},
                                headers=headers)

                        elif ev_type == "final":
                            final_text = payload.get("text", "")

                        elif ev_type == "session.idle":
                            break
    finally:
        if proc.stdin:
            proc.stdin.close()  # EOF heartbeat → server self-terminates
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    return final_text, ""  # file_diff computed by caller from _file_diff(cwd)
```

[VERIFIED: serve.py:59 for handshake shape; app.py:288-419 for all routes; PROTOCOL.md §2,§4,§7,§11 for wire format; supervisor.rs:65 for `LITELLM_LOCAL_MODEL_COST_MAP`; providers.py:369 for `aiter_lines()` SSE consumption pattern]

### Pattern 4: JSONL Row Extension (Additive)

The `surface` field must be appended to the JSONL row in `run_suite`. Following M5 D-04 (additive only):

```python
# In run_suite row dict — append after existing fields
row = {
    ...,  # all existing E1-03 fields
    "surface": spec.surface,  # new additive field
}
```

Also update `REQUIRED_FIELDS` in `test_voss_eval_stub.py` in the same plan that adds the field.

### Anti-Patterns to Avoid

- **Injecting `sitecustomize.py` into CLI driver env:** D-05 explicitly forbids this. The stub injection is for hermetic e2e tests only — E3 drivers run live.
- **Sharing a server across scenarios:** D-08 requires one server per scenario. A shared server would carry cross-scenario session state and make failures non-isolatable.
- **Reading SSE events from a second `httpx.AsyncClient` call:** The SSE connection must be opened BEFORE posting the message (otherwise events emitted between POST and stream-open are lost). The pattern above opens the stream first, then posts inside the same async context.
- **Blocking the SSE iteration on permission reply:** The permission reply must be issued as a concurrent `await client.post(...)` from inside the SSE loop — NOT from a separate thread. Use `async with client.stream(...)` and issue the reply as a standard `await` inside the `async for` body. This works because httpx `AsyncClient` supports concurrent requests.
- **Using `subprocess.PIPE` for stdout AND reading it in a busy loop:** Pipe buffer can fill and block the server. Always drain stderr in a background thread (see pattern above).
- **Checking `sys.stdin.isatty()` behavior for `cli:do`:** When `stdin=subprocess.DEVNULL`, `sys.stdin.isatty()` is `False` AND `sys.stdin.read()` returns `""`. The code at cli.py:1690 appends `"\n--- piped stdin ---\n" + ""` (the empty string). This adds noise to the prompt. Use `stdin=subprocess.PIPE, input=""` NOT `DEVNULL` to avoid, or just pass the full prompt as the CLI argument without expecting any stdin content. **Recommended:** use `stdin=subprocess.PIPE` with `input=""` to explicitly pass empty stdin, matching the behavior of the existing e2e `CliRunner.run()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE frame parsing | Custom state machine | `httpx.Response.aiter_lines()` | Already handles chunked transfer encoding, ping lines (`:` prefix), partial frames across chunks |
| Server process supervision | Custom process pool | One `subprocess.Popen` per scenario + stdin EOF heartbeat | Mirrors proven Rust SDK pattern; server self-terminates on parent death via `getppid()` poll |
| Auth credential resolution | Custom credential reader | Pass `ANTHROPIC_API_KEY` / codex auth via inherited `os.environ` | `_resolve_provider("auto")` in the server and `_resolve_auth_or_die("auto")` in the CLI already do the right thing |
| Scenario isolation | Custom tmpfs or Docker | `_prepare_fixture()` from E1 runner | Git-init temp dir is already the proven pattern; serve driver just passes `cwd` to the server |
| Permission gate simulation | Custom PermissionGate mock | Real `POST /session/:id/permission {"id":..., "choice":"a"}` | The gate is the thing being tested; a mock would not exercise the actual asyncio.Future bridge |

**Key insight:** E3 drivers are thin wrappers around existing infrastructure. The `cli:do/chat/edit` drivers are 10-20 lines each. The `serve` driver is ~60 lines. No new abstractions needed.

---

## E1 Integration Points (Locked Interfaces)

These interfaces are pinned from E1 plans. E1-03/04/05 are not yet executed; treat these as contracts that will be live before E3 executes.

### From E1-01 (EXECUTED — live in runner.py):
```python
# voss/eval/runner.py
def _run_checks(checks: list, cwd: Path) -> tuple[bool, list[dict]]:
    """Run all checks; return (gate_pass, results_list). Never short-circuits."""
    ...

# voss/eval/suite.py
class TaskSpec(BaseModel):
    ...
    checks: list[AnyCheck] = Field(default_factory=list)
```
[VERIFIED: E1-01-SUMMARY.md; runner.py:83-112]

### From E1-02 (EXECUTED — live in config.py and cli.py):
```python
# voss/harness/config.py
DEFAULT_MAX_TURNS = 15
DEFAULT_JUDGE_MODEL = "gpt-5.5-mini"

def get_eval_max_turns() -> int: ...
def get_eval_judge_model() -> str: ...
```
[VERIFIED: E1-02-SUMMARY.md; config.py:249-274]

### From E1-03 (PLAN only — NOT YET EXECUTED):
When E1-03 executes, `run_suite` will gain these additions (E3 plan must reference them as contracts):

```python
def run_suite(
    *,
    suite: str = "golden",
    stub: bool = False,
    max_turns: int | None = None,   # NEW: E1-03 adds this
    ...
) -> Path: ...

# JSONL row will gain these additive fields after E1-03:
row = {
    ...,
    "gate_pass": gate_pass,   # bool
    "capped": capped,          # bool
    "checks": check_results,   # list[dict]
}

# Judge guard becomes:
if crash_reason is None and not capped and judge_provider is not None:
    ...
```

**E3 adds `surface` as a further additive field to the row.**

[CITED: E1-03-PLAN.md task 1 interfaces section]

### From E1-04 (PLAN only — NOT YET EXECUTED):
E1-04 retrofits `[[checks]]` onto golden tasks. E3 surface scenarios must ALSO carry `[[checks]]` that are meaningful for live runs (file_exists, file_contains, cmd). The serve permission-gate scenario in particular should include a `file_contains` or `cmd` check that verifies the file was written (not just that the model said it was written).

---

## Runtime State Inventory

Not applicable — E3 is a greenfield addition (new test suite and drivers). No rename/refactor/migration.

---

## Common Pitfalls

### Pitfall 1: SSE Event Loss from Wrong Connection Order
**What goes wrong:** If the SSE GET is opened AFTER the POST /message, events emitted during the window between POST and stream-open are dropped. The final event may never arrive.
**Why it happens:** sse-starlette buffers events in `s.queue` (asyncio.Queue); events emitted before the SSE consumer connects are dropped because the queue is not a persistent log.
**How to avoid:** Open the SSE stream (`GET /session/:id/events`) BEFORE posting the message. The `server.connected` event is the reliable "ready" signal. The pattern in the sequence above (stream first, message second) is correct.
**Warning signs:** SSE consumer hangs waiting for `session.idle` that never arrives; no `final` event received.

### Pitfall 2: Chat REPL Launches TUI Instead of Plain REPL
**What goes wrong:** `voss chat` without `--plain` attempts to launch the Textual TUI. In a subprocess without a TTY, the TUI may hang or crash.
**Why it happens:** `_run_repl()` checks `isinstance(renderer, TextualRenderer)` which requires the renderer to be the textual renderer. The `--plain` flag forces `PlainRenderer`.
**How to avoid:** Always pass `--plain` to `cli:chat` and `cli:edit` drivers. Also pass `--json` as an alternative if plain output is insufficiently structured.
**Warning signs:** Subprocess hangs or exits with a non-zero code immediately; no stdout captured.

### Pitfall 3: `voss do` Appends Piped-Stdin Separator
**What goes wrong:** `do_cmd` at line 1690 appends `"\n--- piped stdin ---\n" + content` when `not sys.stdin.isatty()`. With `stdin=subprocess.PIPE` and `input=""`, the prompt becomes `"<the prompt>\n--- piped stdin ---\n"`. This is harmless noise in most cases but could confuse the model.
**Why it happens:** The do_cmd explicitly reads stdin when piped. With `subprocess.DEVNULL`, `sys.stdin.isatty()` is still `False` on some platforms, so it attempts to read from `/dev/null` and appends an empty string (plus the separator header).
**How to avoid:** Pass the full prompt as the CLI positional argument ONLY. Use `stdin=subprocess.PIPE, input=""`. The separator is appended as noise but the prompt content is correct.
**Warning signs:** Model receives extra context about "piped stdin"; consider using `--plain` which still works.

### Pitfall 4: Server Handshake Timeout on Cold litellm Import
**What goes wrong:** `voss serve` takes 15–45s to print the handshake line on a cold start (litellm imports its model-cost map). The driver times out before the server is ready.
**Why it happens:** litellm's import tree is large; `.pyc` compilation on first run adds additional delay. Without `LITELLM_LOCAL_MODEL_COST_MAP=true`, litellm may also fetch the cost map from the network (~12s additional).
**How to avoid:** (1) Always set `LITELLM_LOCAL_MODEL_COST_MAP=true` in the spawn env. (2) Use a 60-second handshake timeout (matching the Rust SDK). (3) Drain stderr in a background thread so a full stderr pipe doesn't block the server.
**Warning signs:** Driver times out at exactly 60s; stderr shows "ImportError" or litellm network fetch logs.

### Pitfall 5: Permission Gate Hangs on Deny Without Timeout
**What goes wrong:** A Deny scenario (permission reply `"d"`) leaves the gate returning `"d"` to the server, which processes it. But if the reply is never sent (e.g., a bug in the driver), the server's `Future.result(timeout=PERMISSION_TIMEOUT_S)` default is 300s — the scenario would hang for 5 minutes.
**Why it happens:** The server gate times out at 300s (app.py:36, PERMISSION_TIMEOUT_S = 300.0) and then auto-denies, but the scenario timeout would fire first.
**How to avoid:** Always issue a permission reply in the `permission.updated` event handler, even for Deny scenarios. Set a scenario-level timeout (e.g., 120s) that is shorter than PERMISSION_TIMEOUT_S. The scenario should receive a `final` event with `halted: max-iter` or similar after a deny.
**Warning signs:** Scenario hangs for 120+ seconds; `session.idle` never arrives.

### Pitfall 6: E1-03 Sentinel Tests Go Stale
**What goes wrong:** E3 adds `surface` to the JSONL row, making `REQUIRED_FIELDS` in `test_voss_eval_stub.py` stale. The sentinel test passes (wrong fields) because the set equality check sees extra fields.
**Why it happens:** Known project hazard (MEMORY.md "voss stale sentinel tests").
**How to avoid:** Update `REQUIRED_FIELDS` in the SAME plan that adds the `surface` field to the row. This is the established E1 pattern (E1-03 task 3 updates REQUIRED_FIELDS in the same plan).
**Warning signs:** `test_voss_eval_stub.py` REQUIRED_FIELDS set does not contain `"surface"`; row contains `"surface"` but test still passes (set superset doesn't fail `==` check).

---

## Code Examples

### SSE Consumption with httpx (raw lines, no external SSE library)

```python
# Source: analysis of providers.py:369 (aiter_lines pattern) + PROTOCOL.md §6 SSE wire format

async with client.stream("GET", events_url, headers=headers) as resp:
    event_type = ""
    async for line in resp.aiter_lines():
        line = line.rstrip("\r")
        if not line:
            event_type = ""  # reset on blank line (frame boundary)
            continue
        if line.startswith(":"):
            continue  # ping / comment
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            try:
                payload = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            # type is redundant in both event: and payload["type"] — use payload
            ev_type = payload.get("type", event_type)
            if ev_type == "session.idle":
                break
            yield ev_type, payload
```

### Permission Gate Reply

```python
# Source: PROTOCOL.md §7; app.py:379-386

# During SSE consumption, when ev_type == "permission.updated":
req_id = payload["id"]
# choice: "a" = allow once, "A" = allow always, "d" = deny
reply = await client.post(
    f"{base_url}/session/{session_id}/permission",
    json={"id": req_id, "choice": "a"},
    headers=headers,
)
# {"v":1,"status":"ok"}  — or "stale" if future already resolved
```

### Subprocess Invocation for cli:do

```python
# Source: tests/e2e/runner.py CliRunner.run() + voss/harness/cli.py do_cmd
import subprocess, sys, os

result = subprocess.run(
    [sys.executable, "-m", "voss.cli", "do", prompt, "--plain"],
    cwd=str(fixture_cwd),
    env={**os.environ, "LITELLM_LOCAL_MODEL_COST_MAP": "true",
         "VOSS_DEV": "1", "PYDANTIC_DISABLE_PLUGINS": "1",
         "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
    stdin=subprocess.PIPE,
    input="",          # empty stdin → isatty()=False → appends "" (harmless noise)
    capture_output=True,
    text=True,
    timeout=120.0,
)
# stdout = rendered plain output; result.returncode should be 0
```

### task.toml for serve permission-gate scenario

```toml
# Source: D-09 (locked) + pattern from tests/eval/golden/03-approved-edit/task.toml
surface = "serve"
prompt = "Write a Python file named hello.py that prints 'Hello, World!' to stdout."
mode = "plan"  # forces permission gate on fs_write
auto_approve_edits = false  # driver handles permission via /permission endpoint
rubric = """
PASS if hello.py exists in the project directory and contains a print statement.
"""
judge_inputs = ["final", "file_diff"]

[[checks]]
type = "file_exists"
path = "hello.py"

[[checks]]
type = "file_contains"
path = "hello.py"
text = "print"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No live CLI surface tests | E3 real subprocess drivers | E3 (new) | First proof that `voss do/chat/edit/serve` work end-to-end with real models |
| M5 golden tasks — rubric-only | Hybrid checks + judge (E1) | E1-03 (pending) | Deterministic gates prevent false-green from judge hallucinations |
| SSE tested only via Rust/Go SDK | Python httpx raw SSE driver | E3 (new) | First Python-native SSE client proof |
| `tests/e2e/` stub-only coverage | E3 live surfaces layer | E3 (new) | Two complementary layers: hermetic + live |

**Deprecated/outdated in this domain:**
- `sitecustomize.py` stub injection: correct for `tests/e2e/` hermetic tests; explicitly NOT to be used in E3 live drivers (D-05).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `voss do --plain` produces clean stdout with the final answer; no TUI artifacts | CLI Subprocess Driver pattern | If `--plain` still outputs TUI-style ANSI codes, `final` text is polluted; mitigation: also test `--json` flag |
| A2 | `cli:edit` fixture must contain a file for the `path` argument; planner must add a `target_file` field to TaskSpec OR derive it from fixture structure | Pattern 2 / TaskSpec extension | If edit_cmd can't find the path argument, it exits with click error immediately |
| A3 | The serve driver `asyncio.run()` can drive both the SSE stream and the concurrent permission reply within a single `async with client.stream()` block (httpx supports concurrent requests on a single AsyncClient) | Pattern 3 code | If httpx disallows concurrent requests inside a stream context, permission reply must be issued from a separate task — structural change to driver |
| A4 | E1-03/04/05 will be executed before E3 planning locks into implementation | E1 Integration Points section | If E1 waves 1-3 aren't merged, E3 is blocked at execution time |
| A5 | Cold serve startup with `LITELLM_LOCAL_MODEL_COST_MAP=true` completes in under 60s on this machine | Pitfall 4 | If slower, increase handshake timeout to 90s |

---

## Open Questions

1. **`cli:edit` target file convention**
   - What we know: `edit_cmd` requires `path` (a file that must exist at subprocess call time); the fixture dir provides the cwd context.
   - What's unclear: Should `target_file` be a new TaskSpec field, or should E3 adopt a convention of always placing a `target.py` (or similar) in `cli:edit` fixture dirs?
   - Recommendation: Add `target_file: str | None = None` to TaskSpec as an optional field (consistent with `surface`). The `cli:edit` driver raises a clear error if `target_file` is None for that surface.

2. **serve driver async vs sync integration in run_suite**
   - What we know: `run_suite` uses `asyncio.run(...)` per task. `_drive_task` is an async function.
   - What's unclear: The serve driver is inherently async (httpx AsyncClient). It can run inside `_drive_task`'s existing `asyncio.run()` context.
   - Recommendation: Implement `_drive_serve` as a coroutine (`async def`) called with `await` inside `_drive_task`. The subprocess Popen is synchronous; stdout readline can be done synchronously before entering the async section.

3. **Scenario for `cli:edit` — does it produce useful file diffs?**
   - What we know: `edit_cmd` calls `_run_repl()` which runs real turns with real model writes; git diff is run by the caller from the fixture cwd.
   - What's unclear: Since `edit_cmd` restricts writes to the edit scope, a simple "add a function to this file" prompt should work. But the scope restriction might block writes to other files.
   - Recommendation: Keep the `cli:edit` scenario simple — a fixture with one Python file, prompt asking to add a function to that specific file, mode="edit".

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `.venv/bin/python` | All subprocess drivers | ✓ | 3.13.12 | Use `sys.executable` |
| `httpx` | serve driver | ✓ | 0.28.1 | — |
| `fastapi` + `uvicorn` | `voss serve` (server extra) | ✓ | installed | — |
| `sse-starlette` | `voss serve` SSE emitter | ✓ | ≥3.4 | — |
| Codex subscription auth | D-11 live run | Operator-supplied | — | Cannot run live proof without it |
| `VOSS_DEV=1` | `voss eval` gate | Set by autouse conftest for tests | — | Gate blocks CLI if not set |

**Missing dependencies with no fallback:**
- Codex subscription auth (operator credential, not an installable package) — required for D-11 proof run only; all driver code can be tested with `VOSS_SERVE_FAKE_TURN=1` stub path.

**Missing dependencies with fallback:**
- None for the test/driver implementation itself.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥8.0 with pytest-asyncio (asyncio_mode="auto") |
| Config file | `pyproject.toml` (asyncio_mode = "auto" at line 103) |
| Quick run command | `VOSS_DEV=1 .venv/bin/python -m pytest tests/eval/test_surface_drivers.py -x -q` |
| Full suite command | `VOSS_DEV=1 .venv/bin/python -m pytest tests/eval/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVSRF-01 (D-04) | `TaskSpec.surface` field validates and defaults to "internal"; golden tasks unaffected | unit | `pytest tests/eval/test_task_spec.py -x -q` | ❌ Wave 0: add surface assertions to existing file |
| EVSRF-02 (D-05) | `cli:do` driver spawns subprocess with live env; stdout captured as final | unit stub | `pytest tests/eval/test_surface_drivers.py::test_cli_do_stub -x -q` | ❌ Wave 0 |
| EVSRF-03 (D-06) | `cli:chat` driver drives single turn via piped stdin; EOFError exits cleanly | unit stub | `pytest tests/eval/test_surface_drivers.py::test_cli_chat_stub -x -q` | ❌ Wave 0 |
| EVSRF-04 (D-04 edit) | `cli:edit` driver spawns with target_file arg; REPL exits on EOF | unit stub | `pytest tests/eval/test_surface_drivers.py::test_cli_edit_stub -x -q` | ❌ Wave 0 |
| EVSRF-05 (D-07,D-08) | serve driver spawns server, reads handshake, creates session, drives turn via SSE | integration stub | `pytest tests/eval/test_surface_drivers.py::test_serve_stub -x -q` | ❌ Wave 0 (uses `VOSS_SERVE_FAKE_TURN=1`) |
| EVSRF-06 (D-09) | serve driver handles `permission.updated`, replies Allow, turn completes | integration stub | `pytest tests/eval/test_surface_drivers.py::test_serve_permission_allow_stub -x -q` | ❌ Wave 0 |
| EVSRF-07 (D-09) | Deny variant: driver replies "d"; turn completes (degraded) without hanging | integration stub | `pytest tests/eval/test_surface_drivers.py::test_serve_permission_deny_stub -x -q` | ❌ Wave 0 |
| EVSRF-08 (D-11) | Live full-suite run: ≥80% gate_pass, 0 capped, all surfaces present | manual/live | `VOSS_DEV=1 .venv/bin/python -m voss.cli eval --suite surfaces --auth codex` | ❌ (human checkpoint) |
| EVSRF-09 (D-03) | `voss eval --suite surfaces` loads and runs 4+ surface scenarios | integration stub | `pytest tests/eval/test_surface_suite_load.py -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `VOSS_DEV=1 .venv/bin/python -m pytest tests/eval/test_surface_drivers.py -x -q`
- **Per wave merge:** `VOSS_DEV=1 .venv/bin/python -m pytest tests/eval/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work` + D-11 live run operator checkpoint

### Wave 0 Gaps
- [ ] `tests/eval/test_surface_drivers.py` — covers EVSRF-02..07 using `VOSS_SERVE_FAKE_TURN=1` and `StubProvider` via env
- [ ] `tests/eval/test_surface_suite_load.py` — covers EVSRF-09 (load_suite finds surfaces dir)
- [ ] `tests/eval/surfaces/` directory with 4-5 task.toml + fixture dirs — required for suite load test

---

## Security Domain

> `security_enforcement` not explicitly false in config — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (serve driver auth) | Bearer token from server handshake; constant-time compare in `_BearerASGI` |
| V3 Session Management | yes (serve driver) | Session ids are UUIDs; tokens are per-process ephemeral secrets |
| V4 Access Control | no (internal tool, single-operator) | VOSS_DEV=1 friction gate, not a security boundary |
| V5 Input Validation | yes (permission reply) | choice field validated against expected values in gate; "stale" response for unknown ids |
| V6 Cryptography | minimal | Token generated with `secrets.token_urlsafe(32)` (cryptographically random, 32 bytes); constant-time compare |

### Known Threat Patterns for E3 Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Handshake token interception | Spoofing | Loopback-only (`127.0.0.1`) server binding per PROTOCOL.md §1; no TLS needed on loopback |
| Permission reply race (stale choice) | Tampering | `Future.result(timeout=300)` server-side; "stale" response if future already resolved; test this path |
| Runaway serve subprocess | Denial | 60s handshake timeout + scenario timeout (120s recommended) + stdin-EOF heartbeat; `proc.kill()` in finally |
| Sub credit burn from unbounded turn loops | Denial | E1's `max_turns` cap (default 15) blocks runaway turns; serve driver does not set `max_turns` at the HTTP level but the server respects it if configured |

---

## Sources

### Primary (HIGH confidence)
- `voss/harness/server/app.py` — route implementations, `_BearerASGI`, `_install_server_permissions`, `_run_turn`, `create_app`, `PermissionReply` model
- `voss/harness/server/serve.py` — `run_server()`, handshake emission at line 59
- `voss/harness/server/events.py` — `AgentEvent` discriminated union, all event payload models
- `.planning/PROTOCOL.md` — wire contract (endpoints, event union, permission protocol, handshake)
- `voss/harness/cli.py` — `do_cmd`, `chat_cmd`, `edit_cmd`, `_run_repl`, `serve_cmd` implementations
- `voss/eval/suite.py` — `TaskSpec`, `AnyCheck` (post-E1-01)
- `voss/eval/runner.py` — `_run_checks`, `run_suite`, `_drive_task` (post-E1-01, pre-E1-03)
- `tests/e2e/runner.py` — `CliRunner`, `Result`, subprocess invocation pattern
- `crates/voss-sdk/src/supervisor.rs` — Rust reference for spawn + handshake (60s timeout, env vars)
- `sdk/go/sse.go`, `sdk/go/handshake.go` — Go reference for SSE parsing, handshake format
- `.planning/phases/E1-eval-substrate/E1-02-SUMMARY.md` — `get_eval_max_turns`, `get_eval_judge_model` confirmed live
- `.planning/phases/E1-eval-substrate/E1-03-PLAN.md` — pinned interfaces for E1-03 (not yet executed)

### Secondary (MEDIUM confidence)
- `voss/harness/providers.py:369` — `aiter_lines()` pattern for SSE consumption (confirmed works for Anthropic SSE; E3 applies same pattern to voss SSE stream)

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all deps confirmed installed
- Wire contract: HIGH — read directly from serve.py, app.py, events.py, PROTOCOL.md
- CLI surface behavior: HIGH — read from cli.py do_cmd/chat_cmd/edit_cmd source
- E1 integration interfaces: HIGH for E1-01/02 (executed), MEDIUM for E1-03/04/05 (plan-pinned, not yet run)
- Pitfalls: MEDIUM — derived from code analysis; some from training knowledge of httpx/subprocess patterns

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (30 days — stable codebase; invalidated if E1-03/04/05 deviate from their plans)
