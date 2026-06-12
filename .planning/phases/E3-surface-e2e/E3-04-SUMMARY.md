---
phase: E3-surface-e2e
plan: 04
subsystem: testing
tags: [eval, surfaces, serve, permissions, sse, live-proof, codex]

# Dependency graph
requires:
  - phase: E3-surface-e2e (plans 01-03)
    provides: "surface schema field + all four drivers (_drive_cli_do/chat/edit, _drive_serve + _consume_sse)"
  - phase: E1-eval-substrate
    provides: "run_suite/_run_checks/judge substrate the surfaces suite runs through"
provides:
  - "6-scenario surfaces suite covering cli:do, cli:chat, cli:edit, serve-basic(auto), serve-permission-Allow, serve-permission-Deny"
  - "TaskSpec.permission_choice Literal['a','A','d'] (additive, default Allow) threaded into _drive_serve"
  - "Final-output artifact (.voss-eval-final.txt) written after _file_diff, before _run_checks — model output check-addressable on every surface"
  - "HARNESS FIX: PermissionGate._prompt consults injected prompt_fn without a TTY (server bridge was dead code)"
  - "HARNESS FIX: bridge-gated checks offloaded to asyncio.to_thread (on-loop Future wait deadlocked serve permissions)"
  - "Documented live proof on codex auth: 100% gate_pass (6/6), 0 capped, permission-Allow passing, Deny bounded"
affects: [E-track closeout, serve permission consumers (TUI/ADE attach), VCKP-13b permission proxy]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Interactive permission tier = mode edit (plan mode structurally denies mutating tools pre-prompt); bridge gates (prompt_fn set) must run off the event loop"]

key-files:
  created:
    - tests/eval/surfaces/ (6 scenario dirs, plans' Task 1)
    - tests/eval/test_surface_suite_load.py
  modified:
    - voss/eval/suite.py
    - voss/eval/runner.py
    - voss/harness/permissions.py
    - voss/harness/agent.py
    - tests/harness/test_permissions_modes.py
    - tests/eval/surfaces/05-serve-permission-allow/task.toml
    - tests/eval/surfaces/06-serve-permission-deny/task.toml

key-decisions:
  - "Scenarios 05/06 switched mode plan→edit: mode_allows (permissions.py:316) structurally denies mutating tools in plan mode BEFORE any prompt — the research pin 'plan mode gates fs_write with a prompt' was wrong against source; edit mode is the interactive tier. 06 had been passing vacuously."
  - "Permission-bridge offload narrowed to gates with prompt_fn set — unconditional to_thread broke the partition-scheduler cancellation test's timing assumptions (4 tool starts within 5 bare yields); plain/auto gates keep the sync path"
  - "Judge on codex auth parked: backend rejects gpt-5.5-mini (model not supported) and non-streaming calls ('Stream must be set to true') — gate_pass is the D-11 criterion; judge fix is follow-up work"

patterns-established:
  - "Live checkpoints validate evidence on disk before recording approval — first 'approved' contradicted artifacts (stale 33% run) and was investigated, not recorded"

requirements-completed: [EVSRF-05, EVSRF-06]

# Metrics
duration: ~75min (incl. two live runs + two harness bug fixes)
completed: 2026-06-12
---

# Phase E3 Plan 04: Surfaces Suite + Live Proof Summary

**Live proof caught and fixed two real harness bugs (dead serve permission bridge + event-loop deadlock); final codex run: 100% gate_pass (6/6), 0 capped, permission-Allow marquee passing, Deny bounded at 29s**

## Performance

- **Duration:** ~75 min across checkpoint investigation, two harness fixes, three live runs
- **Completed:** 2026-06-12 (run timestamp 2026-06-12T000608Z)
- **Tasks:** 3 (Tasks 1-2 pre-executed earlier; Task 3 checkpoint this session)
- **Files modified:** 7 + 6 scenario dirs

## Accomplishments
- 6-scenario surfaces suite proven live end-to-end on codex subscription auth (gpt-5.5)
- The marquee D-09 flow verified at every layer: serve edit-mode turn → `permission.updated` SSE → driver replies Allow via /permission → fs_write executes → hello.py written → clean final + idle
- Two product bugs found by the live run and fixed (below) — exactly the anti-false-green mission

## Live Proof (Task 3 checkpoint — EVSRF-06, D-11)

- **Artifacts:** `.voss/eval/2026-06-12T000608.214625+0000/` (runs.jsonl + summary.md; git-ignored)
- **Header:** `6 tasks · max 15 turns/task · toolchains: py=OK rust=OK ts=OK` printed pre-model
- **Gate pass: 100% (6/6) — exceeds the >=80% bar.** 0 capped. Every row carries `surface`.
- **05-serve-permission-allow: gate_pass=true** (11.4s)
- **06-serve-permission-deny: completed in 29.2s** (no hang), secret.py absent
- Credential scan of runs.jsonl: clean (only the `input_tokens` field name matches token-y patterns)
- Judge verdicts: error on codex auth (backend rejects gpt-5.5-mini and non-streaming judge calls) — does not affect the gate criterion; follow-up noted below
- **Operator approval:** "approved" (initial approval predated valid artifacts — the only run on disk was a stale 33% run; investigated rather than recorded, leading to the bug hunt below; criteria genuinely met on the final run)

## Bugs Found by the Live Proof (both fixed + regression-tested)

**1. Serve permission bridge was dead code (permissions.py)**
`PermissionGate._prompt` denied on non-TTY stdin BEFORE consulting the injected `prompt_fn`. The server bridge installs `prompt_fn` on a headless process → every gated tool returned `<denied: non-interactive denial>`; `permission.updated` never emitted. `_prompt_expand` directly above had the correct guard. Fixed to `if self.prompt_fn is None and not sys.stdin.isatty()`. Existing tests had monkeypatched `isatty→True` around the landmine; new `TestInjectedPromptWithoutTTY` regression class pins the contract.

**2. Bridge gate deadlocked the event loop (agent.py)**
`gate.check` ran synchronously on the loop thread inside `_invoke_step_with_gate`; the bridge prompt blocks on a `concurrent.futures.Future` that only a /permission route on that same loop can resolve → frozen until the 300s permission timeout. Fix: gates with `prompt_fn` set are checked via `asyncio.to_thread`; plain gates (auto_yes / interactive CLI) keep the sync path — an unconditional offload broke `test_cancellation_propagates_to_in_flight_reads` timing assumptions and was narrowed.

**3. Scenario design fix (05/06 mode plan→edit)**
Plan mode hard-denies mutating tools structurally (`mode_allows`) before any prompt — no permission event can ever fire in plan mode. The interactive tier is edit mode. 05 was unpassable as authored; 06 passed vacuously. Both now exercise the real prompt flow.

## Task Commits

1. **Tasks 1+2 (pre-executed):** `207f661` (failing field test), `114faf0` (permission_choice + artifact + scenarios), `d1a55c9` (suite-load/dispatch tests)
2. **Checkpoint fixes:** `d2ee604` (agent.py offload; commit message documents both bugs) + permissions.py/tests/scenario tomls absorbed by the concurrent auto-committer into `2bea26a` (misleading "chromadb" message; content verified)

## Verification
- Harness suite: **2114 passed**, 0 failed (incl. new regression tests; scheduler cancellation test green with narrowed offload)
- Eval offline suite: green (all surface + matrix + golden tests)
- Isolated live debug: permission.updated → Allow → write confirmed before the full rerun

## Issues Encountered
- First operator "approved" had no supporting artifacts (only a stale 2026-06-10 33% run with permission-Allow failing) — surfaced the contradiction, ran fresh, found the bugs above.
- Judge on codex auth structurally broken two ways (unsupported judge model + non-streaming call rejected). Parked: D-11 keys on gate_pass; judge-on-codex needs a streaming-capable judge path or a different judge auth source. Candidate backlog item.

## Next Phase Readiness
- E3 phase ship gate cleared: every runtime entry point (cli:do/chat/edit, serve basic/Allow/Deny) proven live with hybrid scoring
- Serve permission fixes directly unblock TUI/ADE attach permission UX (VCKP-13b) — the bridge now actually works headless

---
*Phase: E3-surface-e2e*
*Completed: 2026-06-12*
