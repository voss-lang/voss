# Phase T5: Shell Ergonomics — Discussion Log

**Date:** 2026-05-16
**Mode:** discuss (default)
**Human reference only — NOT consumed by downstream agents.**

---

## Areas Selected

User multi-selected all 4 presented gray areas: Handle shape, Output buffer model, Monitor semantics, voss jobs + allowlist parity.

---

## Area 1 — Handle shape

**Question:** Background job handle shape — returned by shell_run_background, consumed by shell_monitor/signal?

**Options presented:**
1. Slug `bg-NNN` (Recommended) — session-scoped monotonic counter, PID hidden
2. UUID-4 string — globally unique but verbose
3. Raw PID as string — collision risk + OS leak

**Selected:** Slug `bg-NNN`

**→ D-01.** Session-scoped monotonic counter, zero-padded 3 digits, resets per session. PID internal-only on JobRecord.

---

## Area 2 — Output buffer model

**Question:** Where does background-job stdout/stderr live during the job's life?

**Options presented:**
1. Disk tail file only (Recommended) — `.voss-cache/jobs/<session_id>/<handle>.log`
2. In-memory ring buffer only — cheap reads, lost on crash
3. Both — memory ring + disk tail — 2x code

**Selected:** Disk tail file only

**→ D-02.** Merged stdout+stderr, partitioned by session_id, reaped on session exit unless `--keep-logs`. Byte cursor for monitor.

---

## Area 3 — Monitor semantics

**Question:** shell_monitor semantics — blocking model + cursor interpretation?

**Options presented:**
1. Non-blocking, opaque cursor (Recommended) — since_ms reinterpreted as byte offset, no timestamp map
2. Short-poll with deadline_ms — blocks up to deadline
3. True wall-clock since_ms — sidecar `.idx` map, per-flush IO

**Selected:** Non-blocking, opaque cursor

**→ D-03.** `[cursor N][running|exit M]\n<chunk>` envelope. `since_ms` param name preserved per ROADMAP but treated as byte offset. Iteration loop polls between turns. 30KB chunk cap.

---

## Area 4 — voss jobs output + allowlist parity

**Question A:** `voss jobs` CLI output format?

**Options presented:** Human table default + `--json` (Recommended) / Human only / JSON only

**Selected:** Human table default, `--json` flag

**→ D-04.** Aligned table (HANDLE PID STATUS RUNTIME CMD) default; `--json` one record per line; session-scoped.

**Question B:** Allowlist parity for shell_run_background?

**Options presented:** Same allowlist (Recommended) / Stricter subset / Same + per-binary timeout override

**Selected:** Same allowlist as shell_run

**→ D-05.** Reuse `shell_allowed()` verbatim. Background risk bounded by lifecycle reap + 100MB/30s watchdog, not allowlist narrowing.

---

## Derived Decisions (not directly asked)

- **D-06** Signal surface — INT/TERM only per locked ROADMAP; KILL internal-only (lifecycle escalation).
- **D-07** SHELL-01 cap raise — single constant 4096→30720 at tools.py:156 area.
- **D-08** Telemetry — reuse `tool.call`/`tool.result`; one NEW flat event `shell.background.reap`.
- **D-09** session_id source — existing `SessionRecord.session_id` UUID4.

---

## Deferred / Scope-Redirected

Captured in CONTEXT.md `<deferred>`: cross-session inventory, per-tool keep-logs, extra signals, TUI status strip (M14), memory ring mirror, per-binary timeout override, Windows DETACHED_PROCESS verification, cmd templating, job priority/nice.

No scope creep raised by user during discussion.

---

## Claude's Discretion Items

Recorded in CONTEXT.md `<decisions>` § Claude's Discretion: separate `_JOBS` lifecycle registry, psutil-polling vs setrlimit (researcher), JSON field naming, CMD truncation, is_mutating=True classification, `--keep-logs` flag location.
