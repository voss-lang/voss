# Phase T5: Shell Ergonomics - Research

**Researched:** 2026-05-16
**Domain:** asyncio subprocess lifecycle, cross-process job inventory, cross-platform signal/memory enforcement
**Confidence:** HIGH (codebase anchors all verified at file:line; cross-platform claims verified against official docs + CPython issues)

## RESEARCH COMPLETE

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 Handle shape:** `shell_run_background` returns `bg-NNN` (monotonic counter, zero-padded 3 digits, resets per session). Raw PID is internal-only on JobRecord `{handle, pid, started_at, cmd, log_path, status, exit_code}`. PID never returned to LLM.
- **D-02 Output buffer:** Merged stdout+stderr → single disk tail file `.voss-cache/jobs/<session_id>/<handle>.log`. No in-memory ring buffer. Reaped on session exit unless `--keep-logs`.
- **D-03 Monitor semantics:** `shell_monitor(handle, since_ms=0)` non-blocking. Envelope `[cursor N][running|exit M]\n<chunk>`. `since_ms` param name preserved but treated internally as opaque byte offset. 30KB chunk cap with `<truncated, N more bytes — re-monitor with cursor M>`.
- **D-04 `voss jobs` CLI:** Aligned human table (`HANDLE PID STATUS RUNTIME CMD`) default; `--json` one JSON record per line. Session-scoped only.
- **D-05 Allowlist parity:** `shell_run_background` reuses `shell_allowed()` verbatim. No second allowlist.
- **D-06 Signal surface:** `shell_signal(handle, signal)` accepts ONLY `"INT"`/`"TERM"`. KILL is internal-only (lifecycle escalation). Unknown → `<denied: unsupported signal>`. `"INT"`→`SIGINT`, `"TERM"`→`SIGTERM` via `proc.send_signal(...)`.
- **D-07 SHELL-01 cap raise:** `shell_run` truncation constant 4096→30720, single-line change at tools.py:156 area. Existing 30s timeout preserved.
- **D-08 Telemetry:** Reuse `tool.call`/`tool.result` for the three new tools. Add ONE new flat-dict event `shell.background.reap`.
- **D-09 Session-id source:** `<session_id>` = existing `SessionRecord.session_id`.

### Claude's Discretion

- Separate `_JOBS` registry in lifecycle.py vs reuse `_SUBPROCESSES` (researcher recommends separate — different reap semantics).
- 100MB RSS / 30s no-output enforcement: psutil polling vs `resource.setrlimit` (researcher recommends psutil; macOS ignores RLIMIT_RSS).
- `voss jobs --json` field naming: JobRecord dict verbatim.
- CMD truncation: ellipsis at `terminal_width - 50`, no wrap.
- `shell_run_background` is_mutating=True (serialized, never in parallel read batch — T2 PAR-02).
- `--keep-logs` flag at `voss chat` entry, defaults false.

### Deferred Ideas (OUT OF SCOPE)

Cross-session `voss jobs` inventory; per-tool `--keep-logs` override; `shell_signal` HUP/USR1/USR2; TUI bottom-pane status strip (M14); in-memory ring buffer mirror; per-binary runtime override; Windows `DETACHED_PROCESS` (researcher verifies whether needed); cmd interpolation/templating; job priority/nice/cpuset.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHELL-01 | `shell_run` output cap 4KB→30KB | One-constant change tools.py:156 (`4096`→`30720`). Pattern already proven: `fs_read_many` uses `30720` at tools.py:68. Slow test `test_real_shell_run_timeout_contract_documented` asserts `timeout=30.0` via source inspection — a sibling source-inspection test should assert the new cap. |
| SHELL-02 | `shell_run_background(cmd) -> handle` | `create_subprocess_exec(*argv, stdout=PIPE, stderr=STDOUT)` + detached pump task + `_JOBS` registry. shell_allowed/split_command reused verbatim (sandbox.py:43,76). Registered as ToolEntry(is_mutating=True) at tools.py:367 area. |
| SHELL-03 | `shell_monitor(handle, since_ms=0) -> chunk` | `open(log).seek(offset).read(30720)` + JobRecord.status read. POSIX concurrent-read-while-writing is safe. Non-blocking, no background poller. |
| SHELL-04 | `shell_signal(handle, signal)` | `proc.send_signal(SIGINT/SIGTERM)`. Windows degradation documented (Q5). |
| SHELL-05 | `voss jobs` CLI | New click command appended to `AGENT_COMMANDS` (cli.py:1989). CRITICAL: must read disk sidecar `<handle>.meta.json` — separate process from the chat session (Q7). |
</phase_requirements>

## Summary

T5 extends three well-established Voss subsystems with **zero architectural novelty** — every pattern it needs already exists in the codebase: `shell_allowed`/`split_command` (sandbox.py), `create_subprocess_exec` + `wait_for` (tools.py shell_run), the SIGTERM-deadline-then-SIGKILL reap loop (lifecycle.py `reap_all`), the `ToolEntry(is_mutating=...)` registry, the flat-dict telemetry `emit()` (telemetry.py), and the click `AGENT_COMMANDS` tuple. The work is mostly **composition + one cross-process design decision**.

The single highest-risk design point is **Q7: `voss jobs` runs in a different OS process than the `voss chat` session that owns the jobs.** In-memory `_JOBS` is invisible to it. This forces a disk sidecar (`<handle>.meta.json`) per job. This is not optional and changes the JobRecord persistence shape — flag for the planner as a Wave-0-shaping decision. The second risk is the **100MB RSS cap**: `resource.setrlimit(RLIMIT_RSS, …)` is a confirmed no-op on macOS/Darwin (kernel ignores it), so the only cross-platform mechanism is **psutil polling** — which requires adding `psutil` as the first new runtime dependency since the harness was built. psutil is a top-100 PyPI package (352M downloads/month, maintained, source repo present) — legitimate, but the dependency addition needs explicit planner acknowledgment.

**Primary recommendation:** Build a **separate `_JOBS` registry** in lifecycle.py with its own `register_job`/`reap_jobs`/`signal_job`, one **supervisor asyncio task per job** that does *both* the stdout→disk pump *and* the 30s-no-output + 100MB-RSS watchdog (single task, not two), a **per-job `<handle>.meta.json` disk sidecar** updated on every state transition so the out-of-process `voss jobs` CLI can read it, and **`psutil` as a new runtime dependency** for cross-platform RSS polling. Use `start_new_session=True` (POSIX) so the watchdog can `os.killpg` the whole tree; map signals to `TerminateProcess` on Windows with documented graceful-shutdown degradation.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Allowlist gate for bg command | Sandbox (`sandbox.py`) | — | Single source of truth; D-05 reuses `shell_allowed` verbatim |
| Process spawn + detach | Tools (`tools.py`) | Lifecycle | Spawn site mirrors `shell_run`; handle/registry ownership is lifecycle's |
| Job lifetime / reap / watchdog | Lifecycle (`lifecycle.py`) | — | `_JOBS` registry parallels `_SUBPROCESSES`; reap on session exit |
| stdout→disk pump | Lifecycle-owned asyncio task | — | Must survive across agent turns; owned by registry, cancelled on reap |
| Cursor read of log | Tools (`shell_monitor`) | — | Pure file `seek/read`; no process interaction |
| Cross-process inventory | CLI (`cli.py` `voss jobs`) | Disk sidecar | `voss jobs` is a separate process — reads `.meta.json`, never in-memory state |
| Memory/no-output enforcement | Lifecycle-owned watchdog task | psutil | Cross-platform RSS requires polling; setrlimit insufficient on macOS |
| Telemetry | telemetry.emit (existing) | — | `tool.*` free for all tools; `shell.background.reap` from `reap_jobs` |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | py3.11+ | subprocess spawn, pump task, watchdog `wait_for` | Already the harness's subprocess substrate (tools.py, lifecycle.py) `[VERIFIED: codebase]` |
| `signal` (stdlib) | py3.11+ | `SIGINT`/`SIGTERM` constants for `send_signal` | Already used by lifecycle reap `[VERIFIED: codebase]` |
| `psutil` | `>=5.9,<8` | Cross-platform per-process RSS polling for the 100MB cap | Only cross-platform mechanism; `resource.RLIMIT_RSS` is a macOS no-op `[VERIFIED: PyPI 7.2.2; CITED: docs.python.org/3/library/resource.html]` |
| `click` | `>=8.1.0` (existing dep) | `voss jobs` subcommand | Every Voss CLI verb is click; `AGENT_COMMANDS` tuple is the registration point `[VERIFIED: pyproject.toml:18, cli.py:1989]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `resource` (stdlib) | py3.11+ | OPTIONAL Linux-only belt-and-suspenders `RLIMIT_AS`/`RLIMIT_RSS` on the child via `preexec_fn` | Only if planner wants a Linux kernel-enforced backstop in addition to psutil polling. Not required. |
| `shutil.get_terminal_size` (stdlib) | py3.11+ | `voss jobs` CMD column truncation width | D-04 human table; degrade to 80 cols when not a TTY |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psutil polling | `resource.setrlimit(RLIMIT_RSS)` | **REJECTED** — Darwin kernel silently ignores RLIMIT_RSS (confirmed long-standing BSD behavior; CPython issue 78783). Linux-only. |
| psutil polling | `resource.setrlimit(RLIMIT_AS)` (address space) | Linux-enforced but **address space ≠ RSS**: JIT/threads/mmap inflate AS far above RSS → false kills on legit builds (pytest, node). Wrong proxy for "100MB memory". |
| Disk `.meta.json` sidecar | In-memory `_JOBS` only | **IMPOSSIBLE for SHELL-05** — `voss jobs` is a separate process invocation; cannot see the chat session's heap. Sidecar is mandatory. |
| Separate `_JOBS` registry | Reuse `_SUBPROCESSES` | Reuse breaks: jobs need watchdog timers, mid-life explicit signals, and may exceed the 5s reap deadline. Separate registry (D-discretion confirms). |
| Two tasks (pump + watchdog) | One supervisor task | One task is simpler and race-free: the same loop that drains stdout also enforces the 30s-no-output deadline via `wait_for` (Q2). |

**Installation:**

```bash
pip install 'psutil>=5.9,<8'
```

Add to `pyproject.toml` `[project] dependencies` (NOT optional-extras — it is required for SHELL-02 success criterion #3 on all platforms). Note `pyproject.toml` currently has **no `psutil`** in dependencies, optional `search`, or `dev` — this is a genuinely new runtime dep. `[VERIFIED: pyproject.toml:10-44; ModuleNotFoundError confirmed at research time]`

**Version verification:** `psutil` latest is **7.2.2** (verified `pip index versions psutil` at research time). Pin `>=5.9,<8` for a wide compatible band; `memory_info().rss` API is stable since 1.x. `[VERIFIED: PyPI registry]`

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `psutil` | PyPI | ~16 yrs (since 0.1.1) | ~352M/month | github.com/giampaolo/psutil | not run (unavailable) | Approved — but `[ASSUMED]` per provenance rule |

slopcheck was not available at research time. Per the package-legitimacy protocol the dependency is tagged `[ASSUMED]` and the planner SHOULD add a `checkpoint:human-verify` task before the install step. **Mitigating evidence (strong):** psutil is a top-100 PyPI package, 352M downloads/month, 15,000+ dependent packages, single well-known maintainer (Giampaolo Rodola), active source repo, 16-year history, latest 7.2.2. This is among the lowest-risk possible third-party Python deps. No postinstall scripts (pure C-extension build). Planner: a single human-eyeball confirmation of the `pyproject.toml` line is sufficient — no extended investigation warranted.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                          voss chat session (process A)
  ┌──────────────────────────────────────────────────────────────────────┐
  │                                                                        │
  │  agent turn N                                                          │
  │     │ shell_run_background(cmd)                                         │
  │     ▼                                                                   │
  │  shell_allowed(cmd) ──denied──▶ "<denied: …>"                           │
  │     │ ok                                                                │
  │     ▼                                                                   │
  │  create_subprocess_exec(*argv,                                          │
  │      stdout=PIPE, stderr=STDOUT,                                        │
  │      start_new_session=True)          ──spawn──▶  child proc (+ tree)   │
  │     │                                                  │ stdout         │
  │     ▼                                                  ▼                │
  │  register_job(JobRecord)            ┌──────────────────────────────┐    │
  │     │  assigns bg-NNN               │ supervisor task (per job,     │    │
  │     │  writes <handle>.meta.json    │  owned by _JOBS, survives     │    │
  │     ▼                               │  agent turns):                │    │
  │  return "bg-NNN" ──▶ agent turn N+1 │   loop:                       │    │
  │                          │          │     chunk = wait_for(         │    │
  │     ┌────────────────────┘          │        proc.stdout.read(64k), │    │
  │     │ shell_monitor(bg-NNN,         │        timeout=30) ──TO──▶ kill│    │
  │     │   since_ms=cursor)            │     append chunk → .log file   │    │
  │     ▼                               │     poll psutil rss>100MB ▶kill│    │
  │  open(.log).seek(cursor)            │   on EOF: status=exit M       │    │
  │  .read(30720)                       │     update .meta.json         │    │
  │     │                               └──────────────────────────────┘    │
  │     ▼                                          │ writes               │
  │  "[cursor M][running|exit K]\n<chunk>"         ▼                       │
  │                              .voss-cache/jobs/<session_id>/            │
  │                                  bg-NNN.log   bg-NNN.meta.json          │
  │  session exit / atexit                          ▲                       │
  │     │ reap_jobs(): SIGTERM→2s→SIGKILL@5s         │ reads                │
  │     ▼   emit shell.background.reap               │                      │
  └──────────────────────────────────────────────────┼───────────────────┘
                                                      │
              voss jobs (process B — SEPARATE)        │
  ┌───────────────────────────────────────────────────┼──────────────────┐
  │  glob .voss-cache/jobs/<current_session_id>/*.meta.json               │
  │  parse → render HANDLE PID STATUS RUNTIME CMD  (or --json one/line)   │
  └──────────────────────────────────────────────────────────────────────┘
```

The diagram's load-bearing point: **process B never touches in-memory state.** All cross-process truth flows through `<handle>.meta.json`.

### Recommended Project Structure

No new modules. Surgical edits to existing files (matches user CLAUDE.md "surgical changes"):

```
voss/harness/
├── tools.py        # +3 tool descriptors (shell_run_background, shell_monitor,
│                   #  shell_signal) + 3 ToolEntry registrations; SHELL-01 constant
├── lifecycle.py    # +_JOBS registry, JobRecord, register_job, reap_jobs,
│                   #  signal_job, the supervisor task fn; piggyback _atexit_hook
├── cli.py          # +jobs_cmd click command; add to AGENT_COMMANDS;
│                   #  +--keep-logs option on chat_cmd
├── permissions.py  # SHELL set extended; signature() handles new tools
├── tui/permissions_bridge.py  # _verb_for / _short_target handle new tool names
├── recorder.py     # (confirm) VALIDATE_TOOLS — see Q9 recommendation
└── cognition.py    # update line 678 deny-list text (mention new tools)
```

### Pattern 1: Allowlist-then-spawn (reuse verbatim)

**What:** Gate on `shell_allowed()` BEFORE any subprocess work; `split_command()` for argv.
**When to use:** `shell_run_background` opening lines — identical to `shell_run`.
**Example:**

```python
# Source: voss/harness/tools.py:134-140 (shell_run) — mirror exactly
ok, reason = shell_allowed(cmd)
if not ok:
    return f"<denied: {reason}>"
try:
    argv = split_command(cmd)
except SandboxError as e:
    return f"<denied: {e}>"
```

### Pattern 2: Single supervisor task per job (pump + watchdog fused)

**What:** One asyncio task owns the entire job: drains stdout to disk, enforces the 30s-no-output deadline via the same `wait_for`, polls RSS, records exit on EOF.
**When to use:** Spawned by `shell_run_background` after `register_job`; handle stored on JobRecord, cancelled by `reap_jobs`.
**Example:**

```python
# Pattern synthesized from tools.py shell_run wait_for + lifecycle reap shape.
# `[ASSUMED]` shape — planner refines. RSS poll cadence ~1s; pump read 64KB.
async def _supervise(rec: "JobRecord") -> None:
    proc, path = rec.proc, Path(rec.log_path)
    last_rss_poll = 0.0
    with open(path, "ab", buffering=0) as fh:
        while True:
            try:
                chunk = await asyncio.wait_for(
                    proc.stdout.read(65536), timeout=30.0  # no-output watchdog
                )
            except asyncio.TimeoutError:
                _kill_tree(proc); rec.status = "killed"
                _emit_reap(rec, signal="KILL", reason="watchdog_no_output")
                break
            if not chunk:                       # EOF → process finished
                await proc.wait()
                rec.status = "done"; rec.exit_code = proc.returncode
                break
            fh.write(chunk)                     # disk tail (D-02)
            now = time.monotonic()
            if now - last_rss_poll >= 1.0:
                last_rss_poll = now
                if _tree_rss_bytes(rec.pid) > 100 * 1024 * 1024:
                    _kill_tree(proc); rec.status = "killed"
                    _emit_reap(rec, signal="KILL", reason="watchdog_mem")
                    break
    _write_meta(rec)                            # final state → sidecar
```

Key points the planner must preserve:
- `open(path, "ab", buffering=0)` — append, unbuffered, so `shell_monitor` in the same process sees bytes immediately.
- The watchdog and pump are the **same `wait_for`** — Q2 confirms this is cleaner than a separate monotonic-timer task. A TimeoutError on the read *is* the no-output condition.
- `_write_meta(rec)` is also called at every status transition (start, kill, done) so process B's `voss jobs` is current.

### Pattern 3: Cross-process state via disk sidecar

**What:** Every JobRecord state change writes `<handle>.meta.json` atomically (write-temp-then-rename, mirroring `sandbox.write_cache` tools.py-adjacent pattern at sandbox.py:99-101).
**When to use:** On register, on each status transition, on reap. Read by `voss jobs`.
**Example:**

```python
# Atomic write pattern already in codebase: sandbox.py:99-101
tmp = meta_path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(asdict(rec_public)))   # PID-bearing OK on disk; never to LLM
tmp.replace(meta_path)
```

### Anti-Patterns to Avoid

- **Reusing `_SUBPROCESSES` for jobs** — different reap timing, watchdog timers, mid-life signals. Use a separate `_JOBS` dict keyed by handle. (CONTEXT anti-patterns; confirmed.)
- **Two tasks for pump and watchdog** — race-prone and harder to cancel atomically. One supervisor task. (Q2.)
- **In-memory-only job state** — breaks SHELL-05 entirely (separate process). (Q7.)
- **`resource.setrlimit(RLIMIT_RSS)` as the memory cap** — no-op on macOS. (Q1.)
- **`start_new_session=True` without a tree-kill** — CONTEXT warns about this; the resolution is: DO use `start_new_session=True` AND `os.killpg` the group so grandchildren die too. The CONTEXT caution ("do NOT add without verifying signal propagation") is satisfied by pairing it with `killpg` (Q5).
- **Wall-clock `since_ms`** — rejected; opaque byte offset only (D-03).
- **Returning PID to the LLM** — PID is internal JobRecord field; only `bg-NNN` crosses the tool boundary (D-01). Sidecar JSON on disk MAY carry PID (humans/`voss jobs` need it).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-platform per-process RSS | `/proc` parsing + `ps` shelling + Windows WMI | `psutil.Process(pid).memory_info().rss` | psutil picks the fastest accurate path per OS (Win32 API / /proc / Mach); hand-rolled `/proc` breaks on macOS/Windows |
| Child-tree memory sum | manual pid walking | `proc.children(recursive=True)` + sum rss | psutil already exposes recursive descendants |
| SIGTERM-then-SIGKILL deadline | new timer logic | copy `lifecycle.reap_all` loop shape (`terminate` → `wait_for(timeout)` → `kill` → `wait`) | Proven, tested (test_lifecycle.py asserts 4.5–6.5s SIGKILL fallback) |
| Allowlist parsing | new validator | `shell_allowed()` + `split_command()` verbatim | D-05; single source of truth |
| Atomic sidecar write | naive `write_text` | temp-write-then-`replace` (sandbox.py:99-101) | crash-safe; partial JSON breaks `voss jobs` |
| CLI subcommand wiring | argparse | click command + append to `AGENT_COMMANDS` | every Voss verb is click; argparse would be foreign |

**Key insight:** T5 is 90% composition of existing, tested Voss primitives. The only genuinely new external capability is cross-platform RSS measurement, and that is exactly what psutil exists for. Any hand-rolled memory probe will be wrong on at least one of the three target OSes.

## Runtime State Inventory

> T5 is additive (new tools + new registry), not a rename/refactor. This section is included because T5 introduces **new on-disk runtime state** that downstream phases (M14) and crash-recovery must account for.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | NEW: `.voss-cache/jobs/<session_id>/<handle>.log` and `<handle>.meta.json` per background job. Not in git (`.voss-cache` is in `_VENDORED` ignore set, cognition.py:443). | New code path; reaped on session exit unless `--keep-logs`. M14 will consume `.meta.json` shape — keep it stable. |
| Live service config | None — T5 spawns ephemeral subprocesses, registers no external services. | None — verified: no daemon/service registration in scope. |
| OS-registered state | None — no Task Scheduler / launchd / systemd / pm2. Background jobs are child processes of the chat session, reaped via atexit. | None. |
| Secrets/env vars | None new. Child inherits chat-process env (same as `shell_run` today). No new secret keys. | None. |
| Build artifacts | NEW runtime dep `psutil` (C extension) — `pip install` rebuilds; no stale-artifact risk since it is a fresh dep. | Planner: add to `pyproject.toml`; `pip install -e .[dev]` re-resolves. |

**Canonical recovery question:** *After a chat session crashes (no clean atexit), what's left?* → Orphaned child processes (their parent died; on POSIX they reparent to init and keep running until they exit naturally — the `start_new_session` group is no longer signalled) **plus** stale `.log`/`.meta.json` with `status:"running"` that no process will ever update. M14 (or a future cleanup) may want a "stale job" sweep; **out of T5 scope** but the planner should note `.meta.json` `status` can be permanently stale after a crash — `voss jobs` should show last-known status, not claim liveness it can't verify. Recommend `voss jobs` cross-check `psutil.pid_exists(pid)` when rendering (cheap, makes the table honest).

## Common Pitfalls

### Pitfall 1: `voss jobs` cannot see in-memory `_JOBS` (CRITICAL — shapes Wave 0)
**What goes wrong:** Implementer puts JobRecords only in `lifecycle._JOBS`; `voss jobs` returns empty because it is a *different OS process* (`voss jobs` is a fresh click invocation, not the running `voss chat`).
**Why it happens:** `_JOBS` lives in the chat process's heap. `voss jobs` `import`s the module fresh — empty dict.
**How to avoid:** Mandatory `<handle>.meta.json` sidecar, written on every state transition. `voss jobs` globs `.voss-cache/jobs/<session_id>/*.meta.json`. **The session_id discovery problem:** `voss jobs` must know *which* session is current. The chat session's `SessionRecord.id` is minted at `chat_cmd` (cli.py:1215) and not exported to a well-known location. **Planner decision required:** either (a) `voss chat` writes the active session id to a stable path (e.g. `.voss-cache/jobs/.active-session`) on start and clears on exit, and `voss jobs` reads it; or (b) `voss jobs` lists *all* `.voss-cache/jobs/*/` dirs and the newest-mtime dir is "current". Recommend (a) — explicit, race-free, and the CONTEXT defers cross-session inventory so single-active-session is the contract.
**Warning signs:** `voss jobs` empty during an active job; tests pass only because they call the in-process registry directly.

### Pitfall 2: asyncio pipe backpressure stalls a noisy job
**What goes wrong:** A job emitting faster than the pump drains fills the asyncio StreamReader buffer (default limit 64KB). If the pump isn't actively reading (e.g. blocked on slow disk), the OS pipe buffer fills and the child *blocks on write* — job appears hung.
**Why it happens:** `create_subprocess_exec(..., stdout=PIPE)` uses a `StreamReader` with a default `limit` of 64KB; the transport pauses reading from the pipe when the buffer is full.
**How to avoid:** The single supervisor task must `await proc.stdout.read(65536)` in a tight loop with no other awaits between reads (disk append is fast and synchronous). Read 64KB chunks (matches the buffer limit). Do NOT do per-line `readline()` on high-volume build output. Do NOT block the supervisor on anything other than the read and the cheap RSS poll. This is inherently self-correcting *as long as the task is scheduled*, which it is (it's a real `_JOBS`-owned task, not orphaned).
**Warning signs:** A `npm run build`-class job stalls at a fixed byte count; killing it shows it was blocked in `write()`.

### Pitfall 3: macOS RLIMIT_RSS silently does nothing
**What goes wrong:** Implementer sets `resource.setrlimit(RLIMIT_RSS, (100MB, 100MB))` via `preexec_fn`; works on Linux CI, ships, and on the developer's Mac a 4GB job is never killed.
**Why it happens:** The Darwin/BSD kernel does not enforce RLIMIT_RSS — `setrlimit` succeeds but the limit is ignored. Long-standing platform behavior (see CPython issue 78783, BSD man pages). `RLIMIT_AS` *is* enforced on macOS but address space ≠ RSS (JIT/threads inflate it → false kills).
**How to avoid:** psutil polling is the *only* mechanism that enforces a real RSS cap on macOS. setrlimit may be added as a Linux-only redundant backstop but must not be the primary control.
**Warning signs:** Memory-cap tests green on Linux CI, the watchdog never fires on a Mac.

### Pitfall 4: Windows signal semantics degrade silently
**What goes wrong:** `shell_signal(bg-001, "INT")` is documented to the agent as "interrupt for graceful shutdown"; on Windows it terminates abruptly with no cleanup.
**Why it happens:** On Windows, asyncio `terminate()`/`send_signal(SIGTERM)` calls `TerminateProcess()` (hard kill, no cleanup). `SIGINT`→graceful only works if the child was created with `CREATE_NEW_PROCESS_GROUP` AND the signal sent is `CTRL_C_EVENT` — and even then it hits the *whole group* including the Voss process if not isolated.
**How to avoid:** Document the degradation in the `shell_signal` tool description and in CONTEXT-traceable research: *"Windows: both INT and TERM map to TerminateProcess; graceful-shutdown semantics (signal handlers, cleanup) are not guaranteed on Windows."* This is a documentation deliverable, not a code fix — matching the CONTEXT deferred item. POSIX gets true SIGINT/SIGTERM.
**Warning signs:** Windows users report build artifacts not cleaned up after `shell_signal`.

### Pitfall 5: reading the log while the pump appends — Windows share mode
**What goes wrong:** `shell_monitor` `open()`s the `.log` while the pump has it open for append. POSIX: fine (independent file descriptors, concurrent read+append is well-defined). Windows: depends on share mode — Python's default `open()` on Windows uses a share mode that *does* allow concurrent read, but a `.tmp`→`replace` on the *meta* file can raise `PermissionError` if the reader holds the target open.
**Why it happens:** Windows file locking is mandatory-ish; `os.replace` over an open target can fail with `PermissionError`.
**How to avoid:** For the `.log`: open read-only, short-lived (`with open(...,'rb') as f: f.seek(n); data=f.read(30720)`), close immediately — POSIX-and-Windows safe. For the `.meta.json`: `voss jobs` reads it with a short-lived open + tolerate `JSONDecodeError`/`PermissionError` by retrying once (matches existing tolerant pattern in session.py `_scan_dir` which swallows `OSError`/`JSONDecodeError`).
**Warning signs:** Intermittent `voss jobs` crash on Windows under an actively-updating job.

### Pitfall 6: orphaned pump task leaks across turns or dies too early
**What goes wrong:** The pump task is created with `asyncio.create_task` inside the tool call; if its reference is not held by `_JOBS`, the event loop may GC it ("Task was destroyed but it is pending"), silently stopping output capture after the tool returns.
**Why it happens:** asyncio only weakly tracks tasks; an un-referenced task can be garbage-collected.
**How to avoid:** Store the `asyncio.Task` handle on the JobRecord inside `_JOBS` (strong ref). `reap_jobs` cancels it explicitly. This is the same ownership discipline `_SUBPROCESSES` uses for proc handles.
**Warning signs:** `shell_monitor` shows output then it stops growing while the process is demonstrably still running.

## Code Examples

### Reap-with-deadline (copy the shape, retune timing per Q6)

```python
# Source: voss/harness/lifecycle.py:38-63 reap_all — proven, test-covered.
# T5 reap_jobs reuses this shape with T5 timing (see Q6 for exact semantics).
try:
    proc.terminate()                                  # SIGTERM (POSIX) / TerminateProcess (Win)
except ProcessLookupError:
    continue
try:
    await asyncio.wait_for(proc.wait(), timeout=DEADLINE)
except asyncio.TimeoutError:
    proc.kill()                                       # SIGKILL
    await proc.wait()
```

### Tool registration (mirror existing entries)

```python
# Source: voss/harness/tools.py:367 — add three sibling entries
"shell_run_background": ToolEntry(descriptor=shell_run_background, is_mutating=True),
"shell_monitor":        ToolEntry(descriptor=shell_monitor, is_mutating=False),  # read-only
"shell_signal":         ToolEntry(descriptor=shell_signal, is_mutating=True),
```
Note: `shell_monitor` is **read-only** (`is_mutating=False`) — it only reads a file. This means in `mode=plan` it is allowed (READ tier) and in T2 parallel batches it MAY be batched with other reads. `shell_run_background`/`shell_signal` are `is_mutating=True` → serialized, never in a parallel read batch (T2 PAR-02 holds automatically — confirms CONTEXT discretion).

### click subcommand (mirror doctor_cmd / sessions_cmd)

```python
# Source: voss/harness/cli.py:1517 doctor_cmd shape + :1989 AGENT_COMMANDS
@click.command("jobs")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")
def jobs_cmd(cwd_str: str, json_mode: bool) -> None:
    """List background jobs for the current session."""
    ...   # glob .voss-cache/jobs/<active_session>/*.meta.json
# then add `jobs_cmd,` to the AGENT_COMMANDS tuple (cli.py:1989)
```

### Telemetry reap event (D-08, flat dict per T4 precedent)

```python
# Source: telemetry.emit signature telemetry.py:190; flat-dict convention
# matches existing emit sites (e.g. permission.result permissions.py:183).
telemetry.emit(
    "shell.background.reap",
    "info",
    data={
        "handle": rec.handle, "pid": rec.pid, "signal": sig,
        "exit_code": rec.exit_code, "runtime_ms": runtime_ms,
        "reason": reason,  # session_exit|watchdog_no_output|watchdog_mem|explicit_signal
    },
)
```
`tool.call`/`tool.result` fire automatically for the three new tools — verified at agent.py:1041-1079: the emit uses `step.name` generically with no allowlist, so any registered tool gets both events for free. D-08's "no new start/exit event" is satisfied.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `resource.setrlimit(RLIMIT_RSS)` for memory caps | psutil polling (cross-platform) | Long-standing — Darwin never enforced RLIMIT_RSS | Must use psutil for any Mac-correct RSS cap |
| Hand-rolled `/proc`/`ps` memory reads | `psutil.Process().memory_info().rss` | psutil 1.x+ (mature ~16 yrs) | One API, three OSes |
| Blocking subprocess + thread | asyncio subprocess + single supervisor task | Already the Voss baseline (tools.py, lifecycle.py) | No new concurrency model |

**Deprecated/outdated:** Nothing T5 touches is deprecated. `asyncio.subprocess`, `psutil.memory_info`, `proc.send_signal` are all current and stable on py3.11+ (target is `requires-python = ">=3.11"`, pyproject.toml:9).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8 + pytest-asyncio 0.23 (`asyncio_mode = "auto"`) `[VERIFIED: pyproject.toml:38-39,66]` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/harness/test_t5_shell.py -x -q` |
| Full suite command | `pytest -q` (testpaths = `tests`, `--strict-markers`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHELL-01 | shell_run cap is 30720 | unit (source-inspection, mirrors existing test_shell_timeout.py:117) | `pytest tests/harness/test_shell_timeout.py -k cap -q` | ❌ Wave 0 (add `assert "30720" in src` sibling to the `timeout=30.0` assertion) |
| SHELL-01 | output >30KB truncates with `<truncated, total N bytes>` | unit | `pytest tests/harness/test_t5_shell.py::test_shell_run_30kb_truncation -q` | ❌ Wave 0 |
| SHELL-02 | bg job spawns, returns `bg-001`, PID not in result string | unit (fake fast command) | `pytest tests/harness/test_t5_shell.py::test_background_returns_handle -q` | ❌ Wave 0 |
| SHELL-02 | handle counter monotonic + zero-padded per session | unit | `...::test_handle_counter -q` | ❌ Wave 0 |
| SHELL-03 | monitor returns `[cursor N][running]\n<chunk>`; cursor round-trips; `[exit M]` after EOF | integration (deterministic emitter command) | `...::test_monitor_cursor_progression -q` | ❌ Wave 0 |
| SHELL-03 | success-criterion #1: 20s job observable from a second turn | integration (use a *short* deterministic emitter, NOT a real 20s sleep) | `...::test_monitor_across_turns -q` | ❌ Wave 0 |
| SHELL-04 | INT/TERM accepted; KILL/unknown → `<denied: unsupported signal>` | unit | `...::test_signal_surface -q` | ❌ Wave 0 |
| SHELL-04 | SIGTERM actually delivered (POSIX): job exits | integration (POSIX-only `@pytest.mark.skipif`) | `...::test_signal_terminates -q` | ❌ Wave 0 |
| SHELL-05 | `voss jobs` reads sidecar from a *separate* invocation; renders table + `--json` | integration (CliRunner; pre-seed `.meta.json` on disk, no live job) | `...::test_voss_jobs_reads_sidecar -q` | ❌ Wave 0 |
| SC #2 | reap: SIGTERM then SIGKILL escalation timing | integration (SIG_IGN child, monotonic assertion like test_lifecycle.py:56) | `...::test_reap_jobs_escalation -q` | ❌ Wave 0 |
| SC #3 | 30s-no-output watchdog kills + emits `shell.background.reap reason=watchdog_no_output` | integration (inject a **small test deadline**, not 30s) | `...::test_no_output_watchdog -q` | ❌ Wave 0 |
| SC #3 | 100MB RSS watchdog kills + emits `reason=watchdog_mem` | integration (monkeypatch the `_tree_rss_bytes` probe to return >100MB; do NOT actually allocate) | `...::test_rss_watchdog -q` | ❌ Wave 0 |

**Deterministic test primitives (critical — subprocess+asyncio+cross-turn is the hard part):**
- Existing precedent: `test_lifecycle.py` uses `shutil.which("sleep")`/`python3 -c`, asserts elapsed bounds; `test_shell_timeout.py` uses `sys.executable -c "import time; time.sleep(5)"` with a **short injected timeout (0.2–0.3s)**, never the real 30s. T5 tests MUST follow this: inject small deadlines, not production constants.
- Deterministic emitter for monitor/pump tests: `python3 -c "import sys,time; [(_ for _ in ()).throw if 0 else (sys.stdout.write(f'{i}\n'), sys.stdout.flush(), time.sleep(0.05)) for i in range(N)]"` — bounded, fast, line-counted. Simpler: a tiny `tests/harness/fixtures/emit.py` helper script printing N lines with small sleeps.
- Watchdog timing: parametrize/inject `no_output_deadline_s` (default 30.0) so tests pass 0.3. Mirrors how `test_shell_timeout.py:25` shims a 0.3s timeout.
- RSS watchdog: monkeypatch the RSS-probe function to return a synthetic >100MB value — never allocate real memory in a unit test (slow, flaky, OOM-risk).
- Reap escalation: SIG_IGN-SIGTERM child (test_lifecycle.py:38-44 pattern) + `time.monotonic()` bounds.
- `voss jobs` cross-process realism: do NOT spawn a real session. Pre-write `.voss-cache/jobs/<sid>/bg-001.meta.json` to a `tmp_path`, point the active-session pointer at it, run `click.testing.CliRunner().invoke(jobs_cmd, [...])`. This is the honest test of the cross-process contract without process orchestration.
- `lifecycle.reset_for_tests()` (lifecycle.py:75) must be extended to also clear `_JOBS` (autouse fixture pattern, test_lifecycle.py:14).

### Sampling Rate

- **Per task commit:** `pytest tests/harness/test_t5_shell.py tests/harness/test_lifecycle.py -x -q`
- **Per wave merge:** `pytest -q -m "not live"`
- **Phase gate:** Full suite green (`pytest -q`) before `/gsd:verify-work`. Coverage gate `fail_under = 90` on `voss_runtime` — note T5 code lives in `voss.harness` (not `voss_runtime`), so `[tool.coverage.run] source = ["voss_runtime"]` does NOT cover harness; coverage gate is not affected by T5, but tests should still cover the new harness code by behavior.

### Wave 0 Gaps

- [ ] `tests/harness/test_t5_shell.py` — covers SHELL-01..05 + SC #1/#3 (does not exist)
- [ ] `tests/harness/fixtures/emit.py` (or inline `-c` snippet) — deterministic bounded line emitter for pump/monitor tests
- [ ] Extend `lifecycle.reset_for_tests()` to clear `_JOBS` (otherwise cross-test job leakage)
- [ ] Extend `tests/harness/test_shell_timeout.py` source-inspection test (or new sibling) to assert the `30720` constant — mirrors the existing `timeout=30.0` guard at :128 so SHELL-01 can't silently regress
- [ ] Reap-escalation timing test using the SIG_IGN pattern from `test_lifecycle.py`
- [ ] Framework install: `psutil` must be added to deps before `test_rss_watchdog` can `import psutil` (even though the probe is monkeypatched, the production module imports it). Add `psutil` to `[project] dependencies` in Wave 0.

## Security Domain

`security_enforcement` is not set in `.planning/config.json` (absent = enabled). T5 surface is local subprocess execution — the relevant controls:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface (local CLI) |
| V3 Session Management | no | Session = local SessionRecord, no network session |
| V4 Access Control | yes | `PermissionGate` mode-tier + `is_mutating` (existing); new tools join SHELL group / WRITE-equivalent gating. `shell_signal`/`shell_run_background` prompt in `edit` mode like `shell_run` (permissions.py:61 explicitly denies `shell_run` in edit mode — planner must decide if the new mutating shell tools get the same explicit denial; recommend: extend the `mode_allows` edit-mode check to the new tool names for parity, else they slip through edit mode). |
| V5 Input Validation | yes | `shell_allowed()` (deny tokens + metachar reject + binary allowlist, sandbox.py:43) reused verbatim — D-05. `shell_signal` validates signal ∈ {INT,TERM} (D-06). |
| V6 Cryptography | no | No crypto in scope |

### Known Threat Patterns for {local subprocess execution}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Command injection via metachars in `cmd` | Tampering/EoP | `shell_allowed` rejects `;|&&` etc.; `create_subprocess_exec` (no `/bin/sh`) — already enforced, reused |
| Runaway/forkbomb background process | DoS | 30s-no-output + 100MB-RSS watchdog; reap on session exit; `start_new_session`+`killpg` kills the whole tree (no orphan grandchildren) |
| Orphan after crash keeps consuming resources | DoS | Documented limitation (Runtime State Inventory) — POSIX reparents to init; `voss jobs` should `pid_exists`-check to not falsely claim liveness |
| PID leak to the model enabling targeted signals | Info disclosure | D-01: PID never crosses the tool boundary; only `bg-NNN`. Sidecar JSON (disk, human-facing) MAY carry PID. |
| `shell_signal` privilege via mode bypass | EoP | **ACTION for planner:** permissions.py:61 hard-denies `shell_run` in `edit` mode by literal name. `shell_run_background`/`shell_signal` are NOT covered by that literal check → they would be *allowed* in edit mode while `shell_run` is denied. Inconsistent. Recommend extending the `mode == "edit"` branch in `mode_allows` (permissions.py:60-63) to deny the new mutating shell tools too, OR generalize to `is_mutating and tool in SHELL`. Flag as a security-correctness decision. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | psutil `>=5.9,<8` band is compatible with the project's py3.11+ and the `memory_info().rss` API; psutil legitimate (slopcheck unavailable) | Standard Stack / Audit | Low — psutil rss API stable since 1.x; 352M downloads/mo. Planner adds a human-verify checkpoint per protocol. |
| A2 | The supervisor-task code shape (Pattern 2) is the right factoring | Architecture Patterns | Medium — alternative is pump+watchdog split (rejected for race reasons); if asyncio scheduling surprises arise the planner may revisit. Shape is `[ASSUMED]`, not verified by a running prototype. |
| A3 | `start_new_session=True` + `os.killpg` is correct for tree-kill on POSIX and does not break signal delivery to the Voss process itself | Pitfalls / Security | Medium — well-documented pattern but CONTEXT explicitly cautions about `start_new_session`. Resolution: it's safe *only* when paired with group-kill; planner must test orphan-grandchild reaping (SC #2). |
| A4 | Active-session discovery for `voss jobs` via a `.voss-cache/jobs/.active-session` pointer file written by `chat_cmd` | Pitfall 1 | Medium — this is a *new* small contract not in CONTEXT (CONTEXT only locks the dir layout). Planner/discuss may prefer "newest dir mtime". Pin before Wave 0. |
| A5 | macOS does not enforce RLIMIT_RSS (so psutil is mandatory) | Pitfalls / Stack | Low — long-standing BSD/Darwin platform behavior, corroborated by CPython issue 78783 and the platform-dependent caveat in docs.python.org/3/library/resource.html. Treated as established fact, not session-verified on a Mac. |
| A6 | `voss jobs` should `psutil.pid_exists()`-check to avoid claiming false liveness | Runtime State Inventory | Low — a robustness recommendation, not a locked requirement; planner may treat as optional polish. |

## Open Questions

1. **Active-session discovery mechanism for `voss jobs` (A4)**
   - What we know: CONTEXT locks the dir layout `.voss-cache/jobs/<session_id>/` and that `voss jobs` is session-scoped; `SessionRecord.id` minted at cli.py:1215.
   - What's unclear: how the *separate* `voss jobs` process learns the current session_id. Not specified in CONTEXT.
   - Recommendation: `chat_cmd` writes `.voss-cache/jobs/.active-session` (the session_id) on REPL start, removes on clean exit; `voss jobs` reads it, falls back to newest-mtime dir if absent. Surface to discuss-phase if a richer multi-session story is wanted (CONTEXT defers cross-session, so single-active is acceptable).

2. **Exact reap timing — reconcile SC #2 with existing 5s deadline (Q6)**
   - What we know: ROADMAP SC #2 verbatim: *"Orphaned background jobs get SIGTERM within 2s, SIGKILL at 5s on session exit."* Existing `reap_all` uses a single 5s SIGTERM→SIGKILL deadline (lifecycle.py:27, test asserts 4.5–6.5s).
   - Interpretation (recommend, pin in plan): on session exit, `reap_jobs` sends **SIGTERM immediately (t≈0, "within 2s" trivially satisfied)**, waits up to **5s** for clean exit, sends **SIGKILL at t=5s**. The "within 2s" clause is a *latency ceiling on issuing SIGTERM*, not a SIGTERM→SIGKILL gap; SIGKILL deadline is 5s (matches existing pattern, lets the new `_TERM_DEADLINE_S`-style constant be 5.0). This is the least-surprising reading and reuses the proven reap shape.
   - Risk if mis-pinned: an over-aggressive 2s SIGKILL would kill legitimate jobs mid-graceful-shutdown. Recommend the conservative reading above; flag for plan-checker to verify against the verbatim ROADMAP line.

3. **`recorder.VALIDATE_TOOLS` membership (Q9)**
   - What we know: `VALIDATE_TOOLS = {"shell_run", "voss_check"}` (recorder.py:22) drives validation-record capture via `_parse_exit` of the `[exit N]` prefix. The new tools' envelopes are `[cursor N][running|exit M]` (D-03) — *not* `[exit N]`, so `_parse_exit` returns 0 (recorder.py:226 requires literal `"[exit "` prefix).
   - Recommendation: **Do NOT add the new tools to VALIDATE_TOOLS.** Their envelope shape is incompatible with `_parse_exit`, and background jobs are not "validation runs" in the recorder's sense (build/test *foreground* runs are). The `shell.background.reap` telemetry event + the disk log are the forensic trail (D-08 rationale). This matches CONTEXT D-08 ("no new event for start/normal-exit; tool.result carries it"). Minimal-additive per T1/T2 precedent → **no RunRecord/IterationRecord/SessionRecord change needed** (answers Q9: disk log + reap event is sufficient; SPEC has no resumability requirement for background jobs and handles explicitly do NOT survive session restart per D-01).

4. **Windows detach correctness (CONTEXT deferred item)**
   - What we know: `asyncio.create_subprocess_exec` on Windows uses `TerminateProcess` for terminate/kill; `CREATE_NEW_PROCESS_GROUP` needed only for CTRL_C_EVENT graceful semantics.
   - Recommendation: T5's reap is `terminate()`→`kill()` which both map to `TerminateProcess` on Windows — *correct for reaping* (the job dies). No `DETACHED_PROCESS` flag needed for the reap contract. Graceful `shell_signal("INT")` is the only Windows degradation, and that is a documented limitation (Pitfall 4), not a code requirement. POSIX gets `start_new_session=True` for tree-kill; Windows skips it (no `os.killpg`; rely on `TerminateProcess` of the job pid — orphan grandchildren on Windows are a documented residual, acceptable for v0.2 and consistent with the CONTEXT deferral).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python3` (asyncio subprocess) | SHELL-02..04 | ✓ | py3.11+ (pyproject requires-python) | none needed |
| `psutil` | SC #3 (100MB RSS cap) | ✗ (not installed, not a dep) | — (PyPI latest 7.2.2) | NO viable cross-platform fallback. `resource.setrlimit` is Linux-only. **Must be added as a runtime dep** — this is the one blocking dependency. |
| `pytest`/`pytest-asyncio` | all tests | ✓ | 8.x / 0.23 (dev extra) | none needed |
| POSIX `sleep`/`signal` | reap + signal integration tests | ✓ (macOS/Linux) | — | tests `@pytest.mark.skipif` on Windows for POSIX-only signal assertions (test_lifecycle.py precedent) |

**Missing dependencies with no fallback:**
- `psutil` — blocking for SC #3 cross-platform. Planner MUST add `psutil>=5.9,<8` to `pyproject.toml [project] dependencies` in Wave 0 (with the human-verify checkpoint from the legitimacy audit). Without it the 100MB cap is unenforceable on macOS.

**Missing dependencies with fallback:** none.

## Sources

### Primary (HIGH confidence)
- Codebase anchors, all read at file:line this session: `voss/harness/tools.py` (ToolEntry :19-51, shell_run :128-158, fs_read_many 30720 cap :68, registry :360-375), `voss/harness/lifecycle.py` (full — reap_all :38-72, _atexit_hook :80-101, reset_for_tests :75), `voss/harness/sandbox.py` (shell_allowed :43, split_command :76, write_cache atomic :93-102), `voss/harness/permissions.py` (SHELL :46, mode_allows edit-deny shell_run :60-64, signature :164-167, telemetry emit :180-194), `voss/harness/tui/permissions_bridge.py` (:27-44), `voss/harness/session.py` (SessionRecord.id :148-172, tolerant _scan_dir :213-224, additive-dataclass doctrine :30-40), `voss/harness/telemetry.py` (emit :190-222, flat-dict convention), `voss/harness/agent.py` (tool.call/tool.result generic emit :1041-1079), `voss/harness/recorder.py` (VALIDATE_TOOLS :22, _parse_exit :224-234), `voss/harness/cli.py` (chat_cmd :1148-1218, doctor_cmd :1517, AGENT_COMMANDS :1989, register :2012), `voss/cli.py` (main group :143, register hook :370-373), `pyproject.toml` (deps :10-44, pytest cfg :65-74), `tests/harness/test_lifecycle.py`, `tests/harness/test_shell_timeout.py` (deterministic-test precedents), `.planning/ROADMAP.md` T5 :909-937 + M14 :593-616, `.planning/config.json` (nyquist_validation:true).
- [Python `resource` docs](https://docs.python.org/3/library/resource.html) — RLIMIT_RSS/RLIMIT_AS platform-dependent caveat.
- [Python asyncio-subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) — Windows terminate→TerminateProcess; CREATE_NEW_PROCESS_GROUP for CTRL_C_EVENT.

### Secondary (MEDIUM confidence)
- [psutil documentation](https://psutil.readthedocs.io/) — `memory_info().rss` portable on all platforms; `children(recursive=True)`.
- [CPython issue 78783 — resource.setrlimit strange behaviour under macOS](https://github.com/python/cpython/issues/78783) — corroborates Darwin RLIMIT enforcement quirks.
- [psutil · PyPI](https://pypi.org/project/psutil/) / [pypistats psutil](https://pypistats.org/packages/psutil) — 352M downloads/month, maintained by Giampaolo Rodola, latest 7.2.2 (legitimacy evidence).

### Tertiary (LOW confidence)
- General asyncio pipe-backpressure behavior (64KB StreamReader default `limit`) — widely documented community knowledge, consistent with stdlib design; treat the exact buffer constant as `[ASSUMED]` and read 64KB chunks to stay safe regardless.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — psutil necessity proven (macOS RLIMIT_RSS no-op corroborated by docs + CPython issue); all reused libs already in codebase.
- Architecture: HIGH for what reuses existing patterns (allowlist, reap, registry, telemetry, CLI); MEDIUM for the supervisor-task factoring (A2) and active-session pointer (A4) which are new and `[ASSUMED]`.
- Pitfalls: HIGH — every pitfall is anchored to a verified codebase fact or an official-docs platform behavior.
- Cross-process `voss jobs` (the headline risk): HIGH that the problem is real (separate process, empty heap — verified by how click commands are invoked); MEDIUM on the recommended pointer-file solution (a new contract for the planner/discuss to ratify).

**Research date:** 2026-05-16
**Valid until:** 2026-06-15 (stable domain — stdlib + a 16-year-old dep; 30-day window)
