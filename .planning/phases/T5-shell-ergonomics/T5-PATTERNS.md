# Phase T5: Shell Ergonomics - Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 13 (3 new, 10 modified)
**Analogs found:** 13 / 13 (every T5 file has an in-repo analog — zero architectural novelty, confirmed by RESEARCH §Summary)

This phase is **90% composition of existing tested primitives**. Every pattern is
quotable from an existing file at a cited line. The planner should QUOTE the
excerpts below directly into plan action steps rather than describe them.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/tools.py` (SHELL-01 cap) | tool | transform | `tools.py:156` self / `tools.py:68` fs_read_many 30720 | exact (one constant) |
| `voss/harness/tools.py` (shell_run_background) | tool | streaming / process-spawn | `tools.py:128-158` shell_run | exact (role+spawn) |
| `voss/harness/tools.py` (shell_monitor) | tool | file-I/O (cursor read) | `tools.py:94-104` fs_read / `tools.py:54-70` _read_one_for_bundle | role-match |
| `voss/harness/tools.py` (shell_signal) | tool | request-response | `tools.py:128-140` shell_run gate prologue | role-match |
| `voss/harness/tools.py` (3 ToolEntry regs) | config | — | `tools.py:359-376` registry dict | exact |
| `voss/harness/lifecycle.py` (`_JOBS`, register_job, reap_jobs, signal_job, supervisor task) | service | event-driven / process-lifecycle | `lifecycle.py:24-101` `_SUBPROCESSES`/`reap_all`/`_atexit_hook`/`reset_for_tests` | exact (parallel registry) |
| `voss/harness/lifecycle.py` (JobRecord dataclass) | model | — | `session.py:146-188` SessionRecord (additive dataclass + `_hydrate`) | exact |
| `voss/harness/lifecycle.py` (`.meta.json` atomic sidecar) | utility | file-I/O | `sandbox.py:93-102` write_cache (temp→`.replace()`) | exact |
| `voss/harness/permissions.py` (SHELL set + D-12 edit deny) | middleware | request-response | `permissions.py:46,49-64,154-167` | exact |
| `voss/harness/tui/permissions_bridge.py` (new tool verbs/targets) | middleware | request-response | `permissions_bridge.py:27-44` `_verb_for`/`_short_target` | exact |
| `voss/harness/cli.py` (`voss jobs` cmd + AGENT_COMMANDS) | route | request-response | `cli.py:1592-1611` sessions_cmd + `:1989-2009` AGENT_COMMANDS | exact |
| `voss/harness/cli.py` (`--keep-logs` flag + `.active-session` write/remove) | config | — | `cli.py:1148-1218` chat_cmd options + `:1391-1405` REPL exit hook | role-match |
| `voss/harness/cli.py` (`voss jobs` tolerant sidecar read) | utility | file-I/O | `session.py:213-224` `_scan_dir` (swallow OSError/JSONDecodeError) | exact |
| `voss/harness/recorder.py` | config | — | `recorder.py:22,224-234` VALIDATE_TOOLS / `_parse_exit` | **no-change, cite-as-reason** |
| `voss/harness/telemetry.py` (`shell.background.reap`) | utility | event-driven | `telemetry.py:190-222` emit + `permissions.py:182-193` flat-dict call site | exact |
| `pyproject.toml` (`psutil>=5.9,<8`) | config | — | `pyproject.toml:10-23` `[project] dependencies` | exact |
| `tests/harness/test_t5_shell.py` (NEW) | test | — | `test_shell_timeout.py` (full) + `test_lifecycle.py` (full) | exact |
| `tests/harness/fixtures/emit.py` (NEW) | test fixture | streaming | `test_lifecycle.py:38-44` SIG_IGN `-c` script precedent | role-match |
| `tests/harness/test_shell_timeout.py` (extend) | test | — | `test_shell_timeout.py:116-128` source-inspection guard | exact |
| `tests/harness/test_lifecycle.py` (extend) | test | — | `test_lifecycle.py:14-18,37-58,84-97` autouse reset + SIGKILL bounds | exact |

> **cognition.py:678 — NO CHANGE.** That line is a *bootstrap-turn prompt*
> deny-list ("do not use shell_run"); the bootstrap turn produces exactly one
> `fs_write` and never spawns shell. New T5 tools are unreachable there. CONTEXT
> §Integration listed it speculatively; RESEARCH did not require it. Planner:
> skip cognition.py.

---

## Pattern Assignments

### `voss/harness/tools.py` — SHELL-01 cap raise (tool, transform)

**Analog:** the line itself + the proven sibling at `tools.py:68`.

**Before** (`voss/harness/tools.py:155-158`, inside `shell_run`):
```python
text = out.decode("utf-8", errors="replace")
if len(text) > 4096:
    text = text[:4096] + f"\n<truncated, total {len(out)} bytes>"
return f"[exit {proc.returncode}]\n{text}"
```

**After** — single constant change `4096`→`30720` (×2 on the same line pair),
identical to the already-shipped pattern at `tools.py:68`:
```python
if len(text) > 30720:  # 30KB cap (T5 SHELL-01 / D-07; matches fs_read_many tools.py:68)
    text = text[:30720] + f"\n<truncated, total {len(out)} bytes>"
```

> **Also patch `_shell_capture` at `tools.py:395-396`** — it carries an
> *independent* `4096` literal (`if len(text) > 4096:`). RESEARCH/CONTEXT cite
> only `:156`; this is the second site the planner must not miss. Decision for
> planner: D-07 says "single-line change at tools.py:156 area" — `_shell_capture`
> backs `voss_check`/git tools, **not** `shell_run`. Recommend: raise it too for
> consistency OR scope D-07 to the `shell_run` site only and note `_shell_capture`
> stays 4096 deliberately. Flag explicitly so plan-checker reconciles vs verbatim D-07.

**Envelope is unchanged** — `<truncated, total N bytes>` text preserved (D-07).
**Timeout `wait_for(..., timeout=30.0)` at `:149` is untouched** (D-07).

---

### `voss/harness/tools.py` — `shell_run_background` (tool, streaming / process-spawn)

**Analog:** `voss/harness/tools.py:128-158` `shell_run` — copy the gate prologue
verbatim, then *diverge* at the spawn (no `communicate()`, no `wait_for`).

**Allowlist-then-spawn prologue — COPY VERBATIM** (`tools.py:130-147`):
```python
ok, reason = shell_allowed(cmd)
if not ok:
    return f"<denied: {reason}>"
try:
    argv = split_command(cmd)
except SandboxError as e:
    return f"<denied: {e}>"
try:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,        # merged stdout+stderr — D-02
    )
```

**Divergence (D-01/D-02):** instead of `await asyncio.wait_for(proc.communicate(),
timeout=30.0)` (which is `shell_run`'s line 149), `shell_run_background`:
1. adds `start_new_session=True` to the `create_subprocess_exec` kwargs
   (POSIX tree-kill prerequisite — RESEARCH Pitfall + Anti-Pattern: ONLY safe
   when paired with `os.killpg`; CONTEXT anti-pattern caution is satisfied by
   that pairing, see lifecycle supervisor below);
2. calls `lifecycle.register_job(...)` which mints `bg-NNN`, creates the
   supervisor task, writes the first `.meta.json`;
3. returns the bare slug string `"bg-NNN"` (PID never in the return — D-01).

Imports already present at `tools.py:1-13` (`asyncio`, `subprocess`, `Path`,
`shell_allowed`, `split_command`, `SandboxError`). New need: `from . import
lifecycle` (or call through a passed-in registry — planner decides; recommend
direct `from . import lifecycle` to mirror `permissions.py:180 from . import
telemetry` lazy-import-inside-function precedent).

**String envelope convention** (`shell_run` returns `f"[exit {rc}]\n{text}"` at
`:158`) — `shell_run_background` returns just `"bg-NNN"` (D-01); the
`[cursor N][running|exit M]` envelope belongs to `shell_monitor`.

---

### `voss/harness/tools.py` — `shell_monitor` (tool, file-I/O cursor read)

**Analog:** `voss/harness/tools.py:54-70` `_read_one_for_bundle` — the 30KB-cap +
`<truncated, total N bytes>` shape; and `tools.py:94-104` `fs_read` for the
short-lived `open`/`read` discipline.

**Cap + truncation pattern to mirror** (`tools.py:68-70`):
```python
if len(text) > 30720:  # 30KB cap (T2-CONTEXT.md D-13)
    text = text[:30720] + f"\n<truncated, total {len(text)} bytes>"
return text
```

**T5 adaptation (D-03):** non-blocking; `since_ms` reinterpreted as opaque byte
offset; envelope `[cursor N][running|exit M]\n<chunk>`; truncation suffix
`<truncated, N more bytes — re-monitor with cursor M>` (different wording from
the `fs_read_many` suffix — D-03 locks this exact string). Read discipline
(RESEARCH Pitfall 5 — POSIX+Windows safe):
```python
with open(log_path, "rb") as f:   # read-only, short-lived
    f.seek(offset)
    chunk = f.read(30720)
```
`is_mutating=False` → read-only tool (see registry below). Pure file read, no
process interaction (RESEARCH Architectural Responsibility Map).

---

### `voss/harness/tools.py` — `shell_signal` (tool, request-response)

**Analog:** `shell_run` gate-prologue shape (`tools.py:130-136`) for the
early-return `<denied: ...>` convention.

**Pattern (D-06):** validate `signal ∈ {"INT","TERM"}` → else
`return "<denied: unsupported signal>"` (mirrors `tools.py:136`
`return f"<denied: {reason}>"` early-return idiom). Map
`"INT"→signal.SIGINT`, `"TERM"→signal.SIGTERM`. Resolve JobRecord by handle via
`lifecycle.signal_job(handle, sig)` → `proc.send_signal(sig)` on the
`asyncio.subprocess.Process` held by `_JOBS`. `"KILL"` is NOT accepted
(internal-only, owned by reap — D-06). New import: `import signal`.

---

### `voss/harness/tools.py` — 3 ToolEntry registrations (config)

**Analog:** `voss/harness/tools.py:359-376` registry dict (every existing entry
is a one-liner; web_fetch shows the multi-flag form).

**Insert beside `shell_run`** (`tools.py:367`):
```python
"shell_run": ToolEntry(descriptor=shell_run, is_mutating=True),
```
**Add (RESEARCH §Code Examples / CONTEXT D-discretion, T2 PAR-02):**
```python
"shell_run_background": ToolEntry(descriptor=shell_run_background, is_mutating=True),
"shell_monitor":        ToolEntry(descriptor=shell_monitor, is_mutating=False),  # read-only file read
"shell_signal":         ToolEntry(descriptor=shell_signal, is_mutating=True),
```
`is_mutating=True` ⇒ serialized, never in a parallel read batch (T2 PAR-02 holds
automatically). `shell_monitor` `is_mutating=False` ⇒ allowed in `mode=plan`
(it executes nothing) and MAY join a parallel read batch.

---

### `voss/harness/lifecycle.py` — `_JOBS` registry + reap + supervisor (service, process-lifecycle)

**Analog:** `voss/harness/lifecycle.py:24-101` — the WHOLE file is the template.
Build a **parallel** registry, not a reuse (CONTEXT anti-pattern + RESEARCH
Alternatives: jobs need watchdog timers / mid-life signals / may exceed 5s).

**Module-level registry pattern** (`lifecycle.py:24-27`) — add a sibling:
```python
_SUBPROCESSES: list[asyncio.subprocess.Process] = []
_SESSIONS: list[object] = []
_TERM_DEADLINE_S = 5.0
# T5 add (parallel, NOT a reuse — distinct reap semantics):
# _JOBS: dict[str, JobRecord] = {}
```

**Reap-with-deadline shape — COPY VERBATIM into `reap_jobs`** (`lifecycle.py:42-63`):
```python
try:
    proc.terminate()
except ProcessLookupError:
    continue
except Exception as exc:
    sys.stderr.write(f"lifecycle.reap_all: terminate failed: {exc!r}\n")
    continue
try:
    await asyncio.wait_for(proc.wait(), timeout=_TERM_DEADLINE_S)
except asyncio.TimeoutError:
    try:
        proc.kill()
    except ProcessLookupError:
        pass
    ...
    await proc.wait()
```
Reap timing (RESEARCH Open Q2, recommend pinned): SIGTERM at t≈0
("within 2s" trivially satisfied), `wait_for(timeout=5.0)`, SIGKILL at t=5s —
reuses the existing `_TERM_DEADLINE_S = 5.0` constant unchanged. POSIX tree-kill:
escalate via `os.killpg(os.getpgid(proc.pid), sig)` (not bare `proc.kill()`)
because `start_new_session=True` put the job in its own group — kills
grandchildren too (RESEARCH Anti-Pattern resolution).

**atexit piggyback** (`lifecycle.py:80-101`) — extend `_atexit_hook`'s guard and
the `reap_all()` body to also drain `_JOBS`; do NOT register a second atexit
hook (CONTEXT Reusable Assets: "T5 piggybacks — no new atexit hook"). Current
guard:
```python
def _atexit_hook() -> None:
    if not _SUBPROCESSES and not _SESSIONS:   # extend: `and not _JOBS`
        return
```

**`reset_for_tests` extension — MANDATORY** (`lifecycle.py:75-77`, RESEARCH
Wave-0 gap):
```python
def reset_for_tests() -> None:
    _SUBPROCESSES.clear()
    _SESSIONS.clear()
    # T5: _JOBS.clear()  (also cancel any live supervisor tasks)
```

**Supervisor task (pump + 30s-no-output watchdog + 100MB RSS poll, ONE task):**
NET-NEW shape, no exact analog. Synthesized from `shell_run`'s
`asyncio.wait_for(..., timeout=30.0)` (`tools.py:149`) + `reap_all`'s kill ladder.
RESEARCH §Pattern 2 gives the `[ASSUMED]` skeleton — quote it verbatim into the
plan. Key invariants the planner MUST preserve (RESEARCH Pitfalls 2/6):
- `open(path, "ab", buffering=0)` — unbuffered append so same-process
  `shell_monitor` sees bytes immediately.
- Pump and watchdog are the *same* `wait_for` — a `TimeoutError` on
  `proc.stdout.read(65536)` IS the no-output condition (one task, race-free).
- Store the `asyncio.Task` handle ON the JobRecord inside `_JOBS` (strong ref —
  otherwise GC'd: "Task was destroyed but it is pending"). Same ownership
  discipline `_SUBPROCESSES` uses for `proc` handles.
- RSS poll: `psutil.Process(pid).children(recursive=True)` tree-sum vs
  100*1024*1024, ~1s tick (D-10).

**`shell.background.reap` emitted from reap path** — see telemetry section.

---

### `voss/harness/lifecycle.py` — JobRecord (model)

**Analog:** `voss/harness/session.py:146-188` `SessionRecord` — `@dataclass`,
`classmethod new()` factory, `_SESSION_FIELDS`/`_hydrate` tolerant rehydration.

**Pattern to mirror** (`session.py:146-188`):
```python
@dataclass
class SessionRecord:
    id: str
    name: str
    ...
    @classmethod
    def new(cls, *, cwd: Path, model: str, name: str = "") -> "SessionRecord":
        sid = uuid.uuid4().hex[:12]
        ...

_SESSION_FIELDS = {f.name for f in dataclasses.fields(SessionRecord)}

def _hydrate(data: dict) -> SessionRecord:
    kept = {k: v for k, v in data.items() if k in _SESSION_FIELDS}
    ...
    return SessionRecord(**kept)
```
**T5 JobRecord schema (D-01/D-11 — sidecar IS the JobRecord serialized):**
`{handle, pid, started_at, cmd, log_path, status, exit_code, runtime_ms}`.
Mirror the `_FIELDS`/`_hydrate` tolerant-load idiom for `voss jobs` to parse
forward/backward-compatibly. `pid` lives on the dataclass + on disk
(humans/`voss jobs` need it) but is NEVER in a tool-return string (D-01).

---

### `voss/harness/lifecycle.py` — `.meta.json` atomic sidecar write (utility, file-I/O)

**Analog:** `voss/harness/sandbox.py:93-102` `write_cache` — the exact crash-safe
temp-then-rename idiom RESEARCH §Pattern 3 / §Don't-Hand-Roll mandate.

**COPY VERBATIM** (`sandbox.py:99-101`):
```python
tmp = target.with_suffix(target.suffix + ".tmp")
tmp.write_text(text)
tmp.replace(target)
```
Call on EVERY state transition (register / each status change / reap) so the
out-of-process `voss jobs` always reads a complete JSON (RESEARCH Pitfall 1/5:
partial JSON crashes `voss jobs`). `write_cache` also shows the
`.voss-cache` jailing convention: `jail_path(project_root, ".voss-cache")` →
`mkdir(parents=True, exist_ok=True)`. T5 path:
`.voss-cache/jobs/<session_id>/<handle>.meta.json` (+ `.log`).

---

### `voss/harness/permissions.py` — SHELL set + D-12 edit-mode deny (middleware)

**Analog + exact edit site:** `voss/harness/permissions.py:46,49-64,154-167`.

**Before** (`permissions.py:46`):
```python
SHELL = {"shell_run"}
```
**After (CONTEXT D-12 / RESEARCH Security V4):**
```python
SHELL = {"shell_run", "shell_run_background", "shell_monitor", "shell_signal"}
```

**Before** (`permissions.py:60-63`, the edit-mode literal-name deny):
```python
if mode == "edit":
    if tool_name == "shell_run":
        return False, "denied by mode edit"
    return True, "ok"
```
**After (D-12 — close the is_mutating=True slip-through; recommend the
generalized form from RESEARCH Security threat table):**
```python
if mode == "edit":
    if tool_name in {"shell_run", "shell_run_background", "shell_signal"}:
        return False, "denied by mode edit"
    return True, "ok"          # shell_monitor stays allowed: executes nothing (D-12)
```
> `mode_allows` does NOT receive `is_mutating` filtered by SHELL membership today
> — it's a literal-name check. Generalizing to `is_mutating and tool_name in
> SHELL` (RESEARCH suggested alt) would ALSO deny `shell_monitor`? No —
> `shell_monitor` is `is_mutating=False`, so `is_mutating and ...` keeps it
> allowed. Either form works; the explicit set is more legible. Planner picks
> one — flag for plan-checker as the D-12 security-correctness decision.

**`needs_prompt` already covers new tools** (`permissions.py:154-162`): edit-mode
branch is `tool_name in WRITE or tool_name in SHELL` — extending the `SHELL` set
above auto-enrolls the new tools into the prompt path. No change needed at :162.

**`signature` may want a bg-aware case** (`permissions.py:164-167`): currently
special-cases `shell_run` (`f"shell_run:{first_arg}"`). Planner decides if
`shell_run_background` deserves the same per-binary always-allow granularity
(recommend: yes, mirror the `shell_run` branch keyed on `cmd`'s first token;
`shell_signal`/`shell_monitor` fall through to bare tool-name signature).

---

### `voss/harness/tui/permissions_bridge.py` — new-tool verbs/targets (middleware)

**Analog:** `voss/harness/tui/permissions_bridge.py:27-44` `_verb_for` /
`_short_target` — pure name→display maps; the bridge logic stays byte-unchanged.

**Before** (`permissions_bridge.py:27-32`):
```python
def _verb_for(tool_name: str) -> str:
    if tool_name == "shell_run":
        return "run"
    if tool_name in {"fs_write", "fs_edit"}:
        return "modify"
    return "use"
```
**After (additive — keep the existing `shell_run`):**
```python
def _verb_for(tool_name: str) -> str:
    if tool_name in {"shell_run", "shell_run_background"}:
        return "run"
    if tool_name == "shell_signal":
        return "signal"
    if tool_name in {"fs_write", "fs_edit"}:
        return "modify"
    return "use"   # shell_monitor → "use" (and it won't prompt anyway, read-only)
```
**`_short_target`** (`permissions_bridge.py:35-44`): add
`shell_run_background` to the `cmd`-extracting branch (line 36
`raw = str(args.get("cmd", ""))`), and `shell_signal` to a `handle`-extracting
branch. `shell_monitor` falls through to the generic kwargs join (it never
prompts — read-only — so cosmetic only).

---

### `voss/harness/cli.py` — `voss jobs` command + AGENT_COMMANDS (route)

**Analog:** `voss/harness/cli.py:1592-1611` `sessions_cmd` (the closest
session-scoped list+render verb) and the RESEARCH-cited `doctor_cmd:1517-1540`
(aligned-column rendering). Registration tuple at `cli.py:1989-2009`.

**Command-shape pattern** (`cli.py:1592-1611` sessions_cmd):
```python
@click.command("sessions")
@click.option("--all", "--global", "include_legacy", is_flag=True, help="...")
def sessions_cmd(include_legacy: bool) -> None:
    """List saved agent sessions ..."""
    cwd = Path.cwd()
    records = session_store.list_sessions(cwd=cwd, include_legacy=include_legacy)
    if not records:
        click.echo("(no sessions)")
        return
    for r in records:
        click.echo(f"  {r.id[:8]}  {r.updated_at}  {r.model:<28}  {r.first_task()}")
```
**Aligned-column / `--json` ergonomics** — RESEARCH §Code-Example skeleton
(D-04). Human table columns `HANDLE PID STATUS RUNTIME CMD`; column-width via
`shutil.get_terminal_size` (degrade to 80 when not a TTY), CMD ellipsis at
`terminal_width - 50`. `--json`: one JSON record per line, JobRecord dict
verbatim. `doctor_cmd:1537-1540` shows the `max(len(...))`+`f"{x:<{w}}"`
alignment idiom to copy. RESEARCH §Runtime-State recommends a
`psutil.pid_exists(pid)` cross-check so the table doesn't claim false liveness
after a crash (optional polish, A6).

**Registration** (`cli.py:1989-2009`) — append `jobs_cmd,` to the
`AGENT_COMMANDS` tuple:
```python
AGENT_COMMANDS = (
    do_cmd, chat_cmd, edit_cmd, login_cmd, logout_cmd, doctor_cmd,
    sessions_cmd, resume_cmd, tools_cmd, ...
    # T5: jobs_cmd,
)
```
`register(group)` at `:2012-2015` iterates the tuple — no other wiring.

---

### `voss/harness/cli.py` — `voss jobs` tolerant sidecar read (utility, file-I/O)

**Analog:** `voss/harness/session.py:213-224` `_scan_dir` — the exact
glob-dir + swallow-`(OSError, json.JSONDecodeError)`-continue idiom for reading
a directory of JSON the writer may be mid-rename on (RESEARCH Pitfall 5).

**COPY THE TOLERANCE SHAPE** (`session.py:217-223`):
```python
for p in dir_path.glob("*.json"):
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        continue
    ...
```
T5: glob `.voss-cache/jobs/<active_session>/*.meta.json`, same swallow. On
Windows add a single retry on `PermissionError` (RESEARCH Pitfall 5) — extend
the except tuple to `(OSError, json.JSONDecodeError)` (PermissionError ⊂ OSError,
so it's already swallowed; retry-once is the only addition).

---

### `voss/harness/cli.py` — `--keep-logs` flag + `.active-session` write/remove (config)

**Analog (flag):** `voss/harness/cli.py:1148-1218` `chat_cmd` — the option-stack
+ `_run_repl(...)` hand-off. Add `@click.option("--keep-logs", is_flag=True,
default=False, ...)` alongside the existing options at `:1148-1184`; thread it
through `chat_cmd(...)` params and into `_run_repl`.

**Analog (`.active-session` lifecycle hook):** `cli.py:1391-1405` — the REPL
loop's clean-exit branch. RESEARCH Pitfall 1 / Open-Q1 recommendation (A4):
`chat_cmd`/`_run_repl` writes `.voss-cache/jobs/.active-session` (containing
`record.id`) on REPL start, removes on clean exit; `voss jobs` reads it.

- **Write site:** `_run_repl` body, after `record` is bound — earliest is
  alongside `ctx = ReplContext(... record=record ...)` at `cli.py:1343-1360`
  (where `record.id` is already used: `MemoryStore(cwd).bind(session_id=record.id)`
  at :1358 is the proof `record.id` is the session-id source — confirms D-09).
- **Remove site:** the `except (EOFError, KeyboardInterrupt):` clean-exit block
  at `cli.py:1394-1405`, beside the existing `conventions.run_on_clean_exit`
  call. Wrap in try/except (best-effort, must not crash exit — same discipline
  as the `conventions extraction skipped` guard at :1403-1404).

**Reap-on-exit honoring `--keep-logs`:** the same clean-exit block (:1394-1405)
is where `lifecycle.reap_jobs()` should run (the existing `reap_all` is only
ever fired by the `_atexit_hook` at `lifecycle.py:101`; REPL has no explicit
reap call — confirmed: grep found no `reap_all` caller outside lifecycle.py).
`--keep-logs=False` ⇒ `rm -rf .voss-cache/jobs/<session_id>/` after reap;
`True` ⇒ skip the rm. Planner: decide whether reap_jobs fires here explicitly
OR rides the atexit piggyback — recommend explicit call here so the session-id
dir cleanup is deterministic and ordered before process exit.

> `record.id` (`session.py:163` `uuid.uuid4().hex[:12]`) IS the `<session_id>`
> path component (D-09) — confirmed by its existing use at `cli.py:1358` and
> `cli.py:1445` (`session_id=record.id` passed to `run_turn`).

---

### `voss/harness/recorder.py` — NO CHANGE (config, cite-as-reason)

**Analog / reason source:** `voss/harness/recorder.py:22,224-234`.

`VALIDATE_TOOLS = {"shell_run", "voss_check"}` (`:22`) drives validation-record
capture via `_parse_exit` (`:224-234`):
```python
def _parse_exit(result: str) -> int:
    if not result.startswith("[exit "):   # ← literal prefix required
        return 0
```
The new tools' envelopes are `bg-NNN` (shell_run_background) and
`[cursor N][running|exit M]` (shell_monitor) — **neither starts with
`"[exit "`**, so `_parse_exit` returns 0. **Do NOT add the new tools to
`VALIDATE_TOOLS`** (RESEARCH Open-Q3 / CONTEXT D-08): envelope-incompatible,
and background jobs are not "validation runs". Forensic trail is the disk
`.log` + the `shell.background.reap` event (D-08). No RunRecord /
IterationRecord / SessionRecord change (T1/T2 minimal-additive precedent;
handles explicitly do NOT survive session restart per D-01).

---

### `voss/harness/telemetry.py` — `shell.background.reap` event (utility, event-driven)

**Analog:** `voss/harness/telemetry.py:190-222` `emit()` signature +
`voss/harness/permissions.py:182-193` as the canonical flat-`data`-dict call
site (T4 D-05 precedent).

**`emit` is generic** (`telemetry.py:190-196`) — no allowlist, any `kind`/`data`:
```python
def emit(kind: str, level: str, msg: str | None = None, *,
         data: dict[str, Any] | None = None) -> None:
```
**Flat-dict call-site pattern to mirror** (`permissions.py:183-193`):
```python
telemetry.emit(
    "permission.result", "info",
    data={"tool": tool_name, "allowed": allowed, "why": why,
          "mode": self.mode, "args": telemetry.redact_tool_args(dict(args))},
)
```
**T5 emit (D-08), call site = `lifecycle.reap_jobs` / supervisor kill path:**
```python
from . import telemetry   # lazy import inside fn, mirrors permissions.py:180
telemetry.emit(
    "shell.background.reap", "info",
    data={"handle": rec.handle, "pid": rec.pid, "signal": sig,
          "exit_code": rec.exit_code, "runtime_ms": runtime_ms,
          "reason": reason},   # session_exit|watchdog_no_output|watchdog_mem|explicit_signal
)
```
`tool.call`/`tool.result` fire automatically for the 3 new tools (RESEARCH:
agent.py:1041-1079 emits generically off `step.name`, no allowlist) — D-08's
"no new start/exit event" is satisfied for free. NO change to telemetry.py
source — only a new call site in lifecycle.py.

---

### `pyproject.toml` — `psutil>=5.9,<8` (config)

**Analog:** `pyproject.toml:10-23` `[project] dependencies` list.

**Before** (`pyproject.toml:10-23`):
```toml
dependencies = [
    "lark>=1.1.9",
    ...
    "keyring>=24.0",
]
```
**After (CONTEXT D-10 / RESEARCH Standard-Stack — first new runtime dep since
the harness was built):** append one line:
```toml
    "psutil>=5.9,<8",
```
Add to `[project] dependencies` (NOT `optional-dependencies.search` / `dev` —
required for SC #3 on all platforms; RESEARCH §Installation). **Planner MUST
add a `checkpoint:human-verify` task before the install step** (RESEARCH
§Package-Legitimacy-Audit: slopcheck unavailable → `[ASSUMED]`; single
eyeball of this one line suffices, no extended investigation — psutil is
top-100 PyPI, 352M dl/mo, 16-yr history, no postinstall scripts).

---

## Shared Patterns

### Allowlist-then-act (gate before any side effect)
**Source:** `voss/harness/tools.py:130-140` (`shell_run`) +
`voss/harness/sandbox.py:43-90` (`shell_allowed`/`split_command`).
**Apply to:** `shell_run_background` (reuse `shell_allowed` VERBATIM — D-05, no
second allowlist). `shell_signal` reuses only the early-return `<denied: …>`
idiom for its `signal ∈ {INT,TERM}` check. **Do not touch `sandbox.py`** (D-05
— cite it as analog, zero edits).

### String tool envelopes (prefix-bracket convention)
**Source:** `voss/harness/tools.py:158` (`f"[exit {rc}]\n{text}"`),
`tools.py:68-70` (`<truncated, total N bytes>`), `tools.py:136`
(`<denied: …>`).
**Apply to:** all 3 new tools. `shell_run_background`→`"bg-NNN"`;
`shell_monitor`→`[cursor N][running|exit M]\n<chunk>` +
`<truncated, N more bytes — re-monitor with cursor M>`;
`shell_signal`→`<denied: unsupported signal>` / an ack string.

### Crash-safe disk write (temp → `.replace()`)
**Source:** `voss/harness/sandbox.py:99-101` (`write_cache`).
**Apply to:** every `.meta.json` sidecar transition write in lifecycle.py.
Mirror also the `.voss-cache` jailing (`sandbox.py:95-98` mkdir-parents idiom).

### Tolerant directory-of-JSON read (swallow OSError/JSONDecodeError)
**Source:** `voss/harness/session.py:213-224` (`_scan_dir`); same idiom repeats
at `session.py:275,285,303,314`.
**Apply to:** `voss jobs` reading `*.meta.json`; the `.active-session` pointer
read (treat missing/garbage as "no active session").

### Additive dataclass + tolerant `_hydrate`
**Source:** `voss/harness/session.py:146-188` (`SessionRecord`/`_SESSION_FIELDS`/
`_hydrate`).
**Apply to:** `JobRecord` (so the on-disk sidecar schema can evolve for M14
without breaking older `voss jobs`).

### Registry-owned async lifetime + atexit piggyback
**Source:** `voss/harness/lifecycle.py:24-101` (whole file);
`voss/harness/net.py:49` (`register_session` self-registration precedent).
**Apply to:** `_JOBS` dict holding both `proc` AND the supervisor `asyncio.Task`
(strong ref — RESEARCH Pitfall 6); extend `_atexit_hook`, `reap_all`,
`reset_for_tests` rather than adding parallel hooks.

### Generic flat-dict telemetry emit
**Source:** `voss/harness/telemetry.py:190-222` + call-site
`voss/harness/permissions.py:182-193` (T4 D-05 flat-data convention).
**Apply to:** `shell.background.reap` only (D-08). No telemetry.py source edit.

### Deterministic subprocess test (short injected deadline, never prod constant)
**Source:** `tests/harness/test_shell_timeout.py:25,54-77` (0.2–0.3s injected
timeout shim); `tests/harness/test_lifecycle.py:21-58` (`shutil.which`,
`python3 -c` script, `time.monotonic()` elapsed-bounds, SIG_IGN-SIGTERM child).
**Apply to:** ALL `test_t5_shell.py` integration tests — inject small
`no_output_deadline_s` (e.g. 0.3), monkeypatch the RSS probe to a synthetic
>100MB (never allocate), use the SIG_IGN child + monotonic bounds for reap
escalation. RESEARCH §Validation makes these MANDATORY.

### Source-inspection regression guard
**Source:** `tests/harness/test_shell_timeout.py:116-128`
(`assert "timeout=30.0" in inspect.getsource(tools_mod.make_toolset)`).
**Apply to:** a sibling assertion `assert "30720" in src` so SHELL-01's cap
cannot silently regress (RESEARCH Wave-0 gap; mirror at :128).

### Autouse registry-reset fixture
**Source:** `tests/harness/test_lifecycle.py:14-18`.
**Apply to:** `test_t5_shell.py` — autouse fixture calling the extended
`lifecycle.reset_for_tests()` (now clearing `_JOBS`) before/after each test to
prevent cross-test job leakage (RESEARCH Wave-0 gap).

---

## New Files — Analog / Pattern Pointers

### `tests/harness/test_t5_shell.py` (NEW — test)
**Analog:** `tests/harness/test_shell_timeout.py` (full) +
`tests/harness/test_lifecycle.py` (full). Copy: the `_short_timeout_shell_run`
shim style (`test_shell_timeout.py:25-44`); `make_toolset(tmp_path)["tool"]
.descriptor` + `asyncio.run(shell.invoke(...))` invocation
(`test_shell_timeout.py:103-113`); SIG_IGN child + monotonic bounds
(`test_lifecycle.py:37-58`); autouse reset fixture (`test_lifecycle.py:14-18`);
`@pytest.mark.skipif(_PYTHON_BIN is None ...)` / `shutil.which`
(`test_lifecycle.py:21-25`). `voss jobs` cross-process test:
`click.testing.CliRunner().invoke(jobs_cmd, [...])` against a pre-seeded
`tmp_path/.voss-cache/jobs/<sid>/bg-001.meta.json` + `.active-session` pointer
(RESEARCH §Validation — do NOT spawn a real session). Markers available:
`pyproject.toml:67-71` (`slow`, `live`, `acceptance`; no `t5` marker — use
`slow` for the source-inspection guard like `test_shell_timeout.py:116`).

### `tests/harness/fixtures/emit.py` (NEW — test fixture)
**Analog:** the inline `python3 -c` script precedent at
`tests/harness/test_lifecycle.py:38-44` (a multi-line `-c` string with
`sys.stdout.write` + `flush` + `time.sleep`). `tests/harness/fixtures/` exists
(holds only `.sse` capture files today — no `.py` precedent; this is the first
fixture *script*). Pattern pointer (RESEARCH §Validation deterministic-emitter):
a tiny module printing N lines with small `time.sleep(0.05)` + `sys.stdout
.flush()`, bounded and line-counted, invoked via
`sys.executable, str(fixtures_dir/"emit.py"), "<N>"`. Keep it allowlist-clean if
ever routed through `shell_allowed` (`python3` is in
`sandbox.py:9` `DEFAULT_SHELL_ALLOWLIST`; but tests typically bypass the gate
like `test_shell_timeout.py:61-74`).

### `voss/harness/lifecycle.py` supervisor task (NEW shape inside existing file)
**No exact analog — synthesized.** Pointer: RESEARCH §Pattern 2 (`_supervise`
`[ASSUMED]` skeleton — quote verbatim) fusing `tools.py:149`
`asyncio.wait_for(..., timeout=30.0)` (the no-output watchdog mechanism) with
`lifecycle.py:42-63` kill ladder. `start_new_session=True` + `os.killpg`
tree-kill: **net-new to the codebase** (grep confirms no existing `killpg` /
`start_new_session` usage). RESEARCH Anti-Pattern resolves the CONTEXT caution:
the flag is safe ONLY paired with group-kill; SC #2 must test orphan-grandchild
reaping (RESEARCH Assumption A3, MEDIUM risk — flag for plan-checker).

---

## No Analog Found

| File / Capability | Role | Data Flow | Reason |
|-------------------|------|-----------|--------|
| `lifecycle.py` supervisor task (pump+watchdog fused) | service | streaming | Net-new factoring; closest is the `wait_for` timeout idiom (`tools.py:149`) + reap ladder (`lifecycle.py:42-63`) — composed, not copied. RESEARCH §Pattern 2 is the `[ASSUMED]` template. |
| `start_new_session=True` + `os.killpg` tree-kill | service | process-lifecycle | Zero existing process-group usage in repo (grep-confirmed). Net-new; RESEARCH Pitfall/Anti-Pattern is the only guidance. SC #2 must validate. |
| cross-platform RSS probe (`psutil.Process(pid).children(recursive=True)` sum) | utility | — | No existing memory-probe anywhere; `psutil` is a brand-new dep. RESEARCH §Don't-Hand-Roll mandates psutil — do not hand-roll `/proc`/`ps`. |

All three "no analog" items are NET-NEW capability the planner builds from the
RESEARCH skeletons, NOT from a copyable file. Everything else in T5 has an exact
or role-match in-repo analog cited above.

---

## Metadata

**Analog search scope:** `voss/harness/{tools,lifecycle,sandbox,permissions,
session,telemetry,recorder,cli,cognition}.py`, `voss/harness/tui/
permissions_bridge.py`, `voss/harness/net.py`, `pyproject.toml`,
`tests/harness/{test_lifecycle,test_shell_timeout}.py`,
`tests/harness/fixtures/`.
**Files scanned:** 14 source files + 2 test files + pyproject + fixtures dir.
**Pattern extraction date:** 2026-05-16

---

## PATTERN MAPPING COMPLETE

**Phase:** T5 - Shell Ergonomics
**Files classified:** 13 (3 new, 10 modified)
**Analogs found:** 13 / 13 (every file has an exact or role-match in-repo analog;
3 net-new *capabilities* inside otherwise-analogged files reference RESEARCH
skeletons)

### Coverage
- Files with exact analog: 9 (SHELL-01 cap, registry, `_JOBS`/reap, JobRecord,
  sidecar write, permissions, permissions_bridge, `voss jobs`+AGENT_COMMANDS,
  tolerant read, telemetry call-site, pyproject, both test extensions)
- Files with role-match analog: 4 (shell_monitor, shell_signal, `--keep-logs`/
  `.active-session`, fixtures/emit.py)
- Files with no analog: 0 (3 net-new *capabilities* — supervisor task,
  killpg tree-kill, psutil RSS — flagged with RESEARCH pointers, not files)

### Key Patterns Identified
- **Reap/registry is a verbatim parallel of `lifecycle.py`** — `_JOBS` mirrors
  `_SUBPROCESSES`; `reap_jobs` copies the `terminate → wait_for(5.0) → kill`
  ladder; `_atexit_hook`/`reap_all`/`reset_for_tests` are EXTENDED, not
  duplicated (no second atexit hook).
- **All cross-process truth flows through the `sandbox.py:99-101` atomic
  temp→`.replace()` sidecar** — `voss jobs` (separate OS process) reads
  `*.meta.json` with the `session.py:213-224` swallow-OSError/JSONDecodeError
  idiom; in-memory `_JOBS` is invisible to it (the headline Wave-0 constraint).
- **Allowlist + envelope conventions are reused verbatim** — `shell_allowed`
  unchanged (D-05, sandbox.py NOT edited), `<denied: …>`/`[exit N]`/
  `<truncated, total N bytes>` prefix-bracket strings extended for the new tools.
- **Tests inject short deadlines, never production constants** — every T5
  integration test follows `test_shell_timeout.py` (0.3s shim) /
  `test_lifecycle.py` (SIG_IGN + monotonic bounds); a source-inspection
  `assert "30720" in src` guards SHELL-01 like the existing `timeout=30.0` guard.

### Planner Flags (decisions to surface to plan-checker)
1. **Second 4096 literal at `tools.py:395-396` (`_shell_capture`)** — CONTEXT/
   RESEARCH cite only `:156`. Decide: raise both or scope D-07 to `shell_run`.
2. **D-12 deny form** — explicit name-set vs `is_mutating and tool in SHELL`
   (both correct; `shell_monitor` stays allowed either way since
   `is_mutating=False`). Security-correctness decision.
3. **`.active-session` pointer (A4)** — a NEW small contract not in CONTEXT
   (CONTEXT only locks the dir layout). RESEARCH recommends pointer-file over
   newest-mtime; pin in Wave 0.
4. **Reap timing (Open-Q2)** — pin "SIGTERM at t≈0, SIGKILL at t=5s reusing
   `_TERM_DEADLINE_S=5.0`"; verify against verbatim ROADMAP SC #2 line.
5. **`psutil` add** — `checkpoint:human-verify` task before install (legitimacy
   audit `[ASSUMED]`, slopcheck unavailable).
6. **cognition.py:678 — NO CHANGE** (bootstrap-prompt deny-list, unreachable by
   T5 tools). Drop from the modify list despite CONTEXT §Integration listing it.

### File Created
`/Users/benjaminmarks/Projects/Voss/.planning/phases/T5-shell-ergonomics/T5-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Every modify site has a before/after-quotable excerpt
with file:line; every new file/capability points at an exact analog or a named
RESEARCH skeleton. Planner can quote these directly into PLAN.md action steps.
