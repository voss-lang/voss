# Daily-Driver Punch List — Gap Analysis Against M5/M6

**Created:** 2026-05-15
**Author:** harness audit (Voss vs. Claude Code / Codex / Pi)
**Status:** Approved 2026-05-15. T-phases landed in `ROADMAP.md`. Versioning split:
- **v0.1.1 patch:** T6 only (PRD §2.4 slash debt — contract bug, not new feature).
- **v0.2.0 minor:** T1, T2, T3, T4, T5, T7, T8 alongside M8/M9/M10.
- **v0.3.0+:** M11–M15 (unfair-advantage features).
- **v1.0.0:** API lock once dogfood signals stable public surface.

## TL;DR

M5 (Eval + Distribution Prep) and M6 (npm Wrapper) are correctly scoped for
their goals — they ship quality measurement and a frictionless install path.
Neither closes the gap that makes Voss feel un-daily-driveable on real coding
work. The gap is **interaction depth**, not packaging.

This punch list proposes **T-prefixed phases** (T = "table stakes for daily
driver") to slot between v0.1 ship and the v0.2 capability work
(M8 / M9 / M10–M15). T-phases differ from M-phases in that they don't add
**new** product surface — they close known competitive gaps against Claude
Code / Codex / Pi on the surface that already exists.

The T-phases below are sequenced by user-visible unlock. T1 alone makes
`voss do` feel like a coding agent instead of a one-shot planner. T1–T4
together close the bulk of the competitive gap. T5–T8 are polish.

---

## What M5 and M6 don't fix

M5 ships golden eval tasks, pass-rate / mean-cost / confidence-correlation
tracking, packaging smoke. M6 ships the npm wrapper and per-platform Python
vendoring.

After both ship, the harness still has these gaps relative to Claude Code,
Codex CLI, and Pi:

| Gap | Severity | M5/M6 closes? |
|---|---|---|
| Single-shot plan loop — no iteration after tool results | P0 | No |
| Sequential tool execution — no parallelism on read-only steps | P0 | No |
| No network surface (WebFetch / WebSearch / MCP) | P0 | No |
| No streaming render — TurnView appends post-hoc | P1 | No |
| `action_interrupt` is a stub | P1 | No |
| No Anthropic prompt caching on stable sys-prompt prefix | P1 | No |
| PRD §2.4 slash debt: `/diff /apply /discard /budget /resume /why` | P1 | No |
| `/cost` flat-total only — no by-model / by-tool breakdown | P2 | No |
| Shell output capped at 4KB; no background mode | P1 | No |
| `fs_edit` single-occurrence only; no batch multi-edit | P2 | No |
| Skills registry ships exactly 1 skill (`analyze`) | P2 | No |
| Input bar single-line; no `!cmd` / `#mem` / multi-line paste | P2 | No |

P0 = user immediately notices, blocks adoption.
P1 = user notices within a session, accumulates friction.
P2 = polish; user adapts but loses leverage.

---

## Proposed T-phases

Each phase below mirrors the M-phase template (Goal / Requirements / Required
commands / Capabilities / Success Criteria / Cross-cutting constraints) so it
slots into ROADMAP.md with no schema change.

### Phase T1 — Iteration Loop + Streaming + Interrupt

**Goal:** Turn the single-shot plan→execute→done flow into a real agent loop
that re-plans on tool results, streams text as it arrives, and cancels
cleanly on user interrupt.

**Requirements (proposed):** ITER-01..06

- ITER-01 `_run_turn_exec` is a while-loop, not a one-shot. Loop exits on
  agent-emitted `done` signal, max-iteration cap, or budget exhaustion.
- ITER-02 Each iteration's tool results feed back into the model context for
  the next planner call.
- ITER-03 Provider call switches from `complete` to `stream`; TurnView renders
  incremental deltas via `RichLog.write`.
- ITER-04 `action_interrupt` (`tui/app.py:79`) cancels the in-flight asyncio
  task and surfaces "interrupted" in the recorder.
- ITER-05 Confidence gate moves from per-turn (single plan) to per-loop-exit
  (final answer). Mid-loop low confidence triggers another plan iteration,
  not a `/clarify`.
- ITER-06 Loop telemetry records iteration count, per-iteration cost, and
  exit reason (done / max-iter / budget / interrupt).

**Required surface:** No new CLI verbs — `voss do` and `voss chat` already
route through `run_turn`. Behavior change only.

**Capabilities:**
- Multi-step coding tasks (run tests → see failure → fix → rerun) work in one
  turn instead of requiring user-driven re-prompts.
- Streaming text appears in TurnView as the model produces it.
- Ctrl-C / `Esc Esc` cancels mid-turn without leaving the recorder dirty.

**Success Criteria (proposed):**
1. The "rename + check + test" path in eval task #2 (M5 golden tasks)
   completes in one `voss do` invocation without user re-prompting.
2. First visible token in TurnView ≤ 500ms after provider acceptance
   (measured against streaming provider).
3. `action_interrupt` cancels an in-flight turn and produces a closed
   recorder entry within 100ms.
4. Max iteration default = 8, configurable via `harness.toml`. Hit-cap path
   produces a structured "halted: max-iter" final, not a crash.

**Cross-cutting constraints:**
- Recorder semantics: each iteration is a sub-record under one Turn, not N
  Turns. Preserves M2 RunRecord schema for `voss resume` compatibility.
- Plan substitution (`_substitute_placeholders`) is removed — prior results
  flow via context, not string templating.
- M9 TUI renderer mounts a "thinking…" placeholder cell that mutates into
  the streaming Final cell when the first token arrives.

---

### Phase T2 — Parallel Tool Calls + Multi-Edit Primitive

**Goal:** Read-only steps execute in parallel; mutations stay serialized.
File edits can batch multiple replacements atomically.

**Requirements (proposed):** PAR-01..04

- PAR-01 `_run_step_loop` partitions steps into read-only batches and
  mutating singletons; read-only batches run via `asyncio.gather`.
- PAR-02 Permission gate enforces "no mutation in parallel batch" at the
  step-classification layer, not the tool layer.
- PAR-03 New tool `fs_edit_many(path, edits=[{old, new}, ...])` applies a
  list of replacements atomically. All-or-nothing: any miss aborts and
  leaves the file untouched.
- PAR-04 New tool `fs_read_many(paths=[...])` returns a single bundled
  response. Avoids N roundtrips when the plan needs context from 5+ files.

**Capabilities:**
- A plan that reads 6 files + greps 2 patterns finishes in one round-trip
  worth of latency instead of 8.
- A rename that touches 12 occurrences in one file commits in one tool call.

**Success Criteria (proposed):**
1. Wall-clock latency of a 6-file plan-step drops by ≥40% vs. serial baseline
   (measured against M5 eval task #5 "summarize-diff" with multiple file
   reads).
2. `fs_edit_many` rejects the entire batch if any `old` doesn't match
   uniquely; recorder logs the offending index.
3. Mutation step interleaved into a read batch forces split-and-wait;
   property test covers ordering.

**Cross-cutting constraints:**
- Diff modal (M9-05) handles the multi-edit case via per-hunk approval
  unchanged — `fs_edit_many` decomposes into N hunks at the modal layer.
- No tool gets parallelism by accident: mutation classification is checked
  at registration (existing `ToolEntry.is_mutating`).

---

### Phase T3 — Network Surface (WebFetch + WebSearch + MCP Client)

**Goal:** Give the agent access to live documentation and external tools
without inventing a new protocol. Gates network at the harness boundary, not
per-call.

**Requirements (proposed):** NET-01..05

- NET-01 New tool `web_fetch(url)` returns text content via `httpx`. Honors
  `tools.allow_net` config flag (HARNESS-PLAN §6 — currently declared,
  unenforced).
- NET-02 New tool `web_search(query)` — pluggable backend (DuckDuckGo HTML
  default, no API key required for v0.1; Brave / Tavily as opt-in).
- NET-03 MCP client over stdio — lift Codex's launcher pattern. Configure
  via `.voss/mcp.yml`. Tools surface in `voss tools` with origin marker.
- NET-04 MCP tool permission scope defaults to `plan` (read-only); mutation
  requires explicit user opt-in per server in `permissions.yml`.
- NET-05 Network tools off by default; `voss --allow-net` or
  `tools.allow_net = true` in config opts in.

**Required commands:**
```
voss mcp list                   # registered MCP servers
voss mcp call <server> <tool>   # debug: invoke an MCP tool directly
```

**Capabilities:**
- Agent can fetch library docs mid-turn (Context7 via MCP, official API
  references via WebFetch).
- Third-party MCP servers (Playwright, GitHub, Linear) callable as tools.
- Audit trail: every network call recorded in `decisions.md`.

**Success Criteria (proposed):**
1. Default install has no network access; opt-in is one line of config.
2. `voss mcp call` works against the Anthropic reference MCP filesystem
   server out of the box.
3. M5 eval suite gains task #6 "fetch + summarize" that requires `web_fetch`.

**Cross-cutting constraints:**
- Path-jail and shell allowlist don't apply to network tools; sandbox is
  per-tool-class.
- MCP server processes reaped on session exit (mirror M10 LSP-server pattern).
- Network telemetry events: `net.request` / `net.response` with redacted
  URLs in `recorder.py`.

---

### Phase T4 — Prompt Caching + Cost Truthfulness

**Goal:** Stop rebuilding the system prompt every turn. Track cost honestly
including cache reads.

**Requirements (proposed):** CACHE-01..04

- CACHE-01 Anthropic provider adds `cache_control: {type: "ephemeral"}` to
  the cognition block and VOSS.md block in system messages.
- CACHE-02 Cost accounting reads `usage.cache_creation_input_tokens` and
  `usage.cache_read_input_tokens` from the response and prices them at
  Anthropic's published rates (10% / 90% discount).
- CACHE-03 `/cost` slash gains `--by-model` and `--by-tool` flags (closes
  PRD §2.4 debt). Output includes a "cache-savings" line.
- CACHE-04 OpenAI provider adopts the equivalent caching path when the model
  reports cache eligibility.

**Capabilities:**
- Multi-turn sessions cost ~10% of the input-token bill on the cached
  prefix.
- `/cost` shows where money actually went.

**Success Criteria (proposed):**
1. Two consecutive turns in the same `voss chat` session with cognition
   loaded show cache_read_input_tokens > 0 on the second turn (recorder
   asserts).
2. `/cost --by-model` matches `sum(per-turn cost_usd by model)` to 4
   decimals.
3. Cost reported by `/cost` includes cache cost (not just non-cached input).

**Cross-cutting constraints:**
- Cache key must be stable across turns — VOSS.md content drift invalidates
  the cache (acceptable).
- Cache TTL is 5 minutes (Anthropic default); document in `harness.toml`.

---

### Phase T5 — Shell Ergonomics (Output Budget + Background + Monitor)

**Goal:** Real builds and test runs survive the shell tool. Long-running
tasks don't block the agent.

**Requirements (proposed):** SHELL-01..05

- SHELL-01 `shell_run` default output cap raised from 4KB → 30KB.
- SHELL-02 New `shell_run_background(cmd) -> handle` returns a job handle;
  process runs detached and is reaped on session exit (mirrors M14 plan but
  ships smaller and earlier — pure shell, no file-watch).
- SHELL-03 New `shell_monitor(handle, since_ms=0) -> chunk` streams output
  incrementally; called by the agent in subsequent turns.
- SHELL-04 New `shell_signal(handle, signal="INT"|"TERM")` for cleanup.
- SHELL-05 `voss jobs` CLI lists running background processes for the
  current session.

**Capabilities:**
- `npm run build` kicked off in turn 1, agent continues, status checked in
  turn 3.
- Test output of 25KB lands intact instead of truncated.

**Success Criteria (proposed):**
1. A 20-second background `sleep && echo done` job is observable via
   `shell_monitor` from a second agent turn.
2. Background jobs orphaned by `voss exit` get SIGTERM within 2s, then
   SIGKILL at 5s.
3. Per-process resource cap: 100MB memory, 30s no-output watchdog (kills the
   job, recorder logs).

**Cross-cutting constraints:**
- Shell allowlist still applies to background commands.
- Background jobs do not inherit the agent's TTY (no terminal-control
  escape hatches).
- Foundation for M14 (file-watch) without committing M14's scope.

---

### Phase T6 — PRD §2.4 Slash Debt

**Goal:** Ship the slash commands the PRD promised and the user expects.
Most are 20-line wrappers around existing data.

**Requirements (proposed):** SLASH-01..07

- SLASH-01 `/diff` — show pending unapplied edits (DiffModal already exists
  in M9-05; needs a slash entry point outside the auto-trigger path).
- SLASH-02 `/apply` — apply pending edits (currently auto via permission
  gate; needs explicit user-initiated path for `plan` mode).
- SLASH-03 `/discard` — drop pending edits.
- SLASH-04 `/budget <usd>` — raise/lower remaining session budget at runtime.
- SLASH-05 `/resume <id|name>` — load a prior session into the live REPL
  without restarting.
- SLASH-06 `/why` — render the last plan's `rationale` + `ProbableValue`
  confidence breakdown (PRD's "killer feature").
- SLASH-07 `/cost --by-model` / `--by-tool` (overlaps T4 CACHE-03 — ship
  whichever lands first, no rework).

**Capabilities:**
- Daily REPL ergonomics match the PRD §2.4 contract.

**Success Criteria (proposed):**
1. Each slash listed in PRD §2.4 is registered in `_build_slash_registry`
   and has at least one integration test exercising the happy path.
2. `/why` shows confidence + rationale from the most recent `Plan` without
   a provider call.
3. `voss --help` lists all v0.1 slashes; help discoverability matches Codex.

**Cross-cutting constraints:**
- No new persistence — slashes operate on the live `ReplContext`.
- M9 SlashPalette autocomplete includes all seven (M9-03 already reserves
  slot names).

---

### Phase T7 — Skills Bootstrap

**Goal:** Ship 5–10 ready-to-use skills so the registry isn't just a hook.

**Requirements (proposed):** SKL-01..06

- SKL-01 `rename-symbol` — anchor + scope-aware rename across the repo
  (eval task #2's reference workflow, packaged).
- SKL-02 `add-test` — locate a public function, generate a unit test, plant
  a failing assertion (eval task #3).
- SKL-03 `summarize-diff` — pipe `git diff` → PR description (eval task #5).
- SKL-04 `port-py-to-voss` — Python → `.voss` translation for the
  classify/support/research sample shapes.
- SKL-05 `audit-cognition` — re-run `analyze` against drift, propose a
  one-paragraph update to `architecture.md`.
- SKL-06 `voss-lint-as-skill` — wraps `voss check` with structured
  diagnostic output (foundation for M11).

**Capabilities:**
- `voss skills` lists 6+ ready entries on a fresh install.
- Each ships with an eval fixture in M5's golden-task suite.

**Success Criteria (proposed):**
1. Every skill is invokable via `/skill <id>` and runs to completion on a
   reference repo without permission escalation.
2. Skills pair 1:1 with M5 eval tasks where applicable.

**Cross-cutting constraints:**
- Skills are Voss-authored (`.voss` files) where the language can express
  them; otherwise Python with a `.voss` lint pass demonstrating skill
  composability.
- M15 (marketplace) is unblocked but not required.

---

### Phase T8 — Input Bar Ergonomics

**Goal:** The input bar stops being the slowest part of the loop.

**Requirements (proposed):** INPUT-01..05

- INPUT-01 Multi-line input via `Shift-Enter`; `Enter` submits.
- INPUT-02 `!<cmd>` prefix runs an allowlisted shell command without
  spawning a turn (matches Claude Code's `!` mode).
- INPUT-03 `#<text>` prefix appends a memory note to `VOSS.md` without
  spawning a turn (matches Claude Code's `#` mode).
- INPUT-04 `Ctrl-R` reverse-search through episodic history.
- INPUT-05 Paste-image detection — if clipboard has an image and the model
  supports it, attach as a vision input.

**Capabilities:**
- Composing a multi-paragraph task or pasting a stack trace doesn't fight
  the input bar.
- Quick memory updates and one-off shell commands stay in-session.

**Success Criteria (proposed):**
1. All five INPUT-0X behaviors covered by Textual snapshot tests.
2. `!` and `#` shortcuts emit recorder events (`shell.local` / `memory.note`)
   and bypass `run_turn`.

**Cross-cutting constraints:**
- M9 keymap (`tui/keymap.py`) is the source of truth; this phase only adds
  bindings, doesn't rewrite the table.

---

## Sequencing rationale

| Order | Phase | Unlock |
|---|---|---|
| 1 | T1 — Iteration loop + streaming + interrupt | Biggest single user-visible jump. Voss stops being a one-shot. |
| 2 | T4 — Prompt caching + cost truthfulness | Cheap to ship after T1; multi-turn cost drops ~10×. |
| 3 | T2 — Parallel tools + multi-edit | Compounds T1 — iterations get faster. |
| 4 | T3 — Network surface | Greenfield coding work needs docs; MCP unlocks ecosystem. |
| 5 | T6 — Slash debt | Trivial in LOC, high in user trust. |
| 6 | T5 — Shell ergonomics | Real builds/tests stop being painful. |
| 7 | T7 — Skills bootstrap | Compounds with M5 eval tasks. |
| 8 | T8 — Input ergonomics | Polish; lands when M9 keymap is stable. |

### Relationship to existing M-phases

- **T1–T2 must land before M5 eval is meaningful.** Single-shot loop caps
  pass rate on multi-step golden tasks. Re-run M5 baseline after T1–T2.
- **T3 (MCP) makes M12 mostly a server-mode milestone.** Client side ships
  here; M12 becomes "expose harness as MCP server" — a tighter scope.
- **T4 (caching) compounds with M8 (Project Memory).** VOSS.md becomes a
  cache-anchor; M8's hit-rate eval gains a cost-savings signal for free.
- **T5 (background shell) is the headless half of M14.** Ship without
  file-watch; M14 layers `watchdog` on top.
- **T6 (slash debt) closes M1's PRD-conformance gap.** Should arguably be a
  bug fix to M1 rather than a new phase; treat as M1.1 if preferred.
- **T7 (skills) feeds directly into M5 (eval) and M15 (marketplace).**

### Relationship to v0.1 ship lock

M0 declared v0.1 = 64 requirements across M0–M7. T-phases add 42 new
requirements (locked in ROADMAP coverage table).

**Decision (2026-05-15):** Hybrid split.

- **v0.1.1 patch:** T6 only. PRD §2.4 promised those slashes in v0.1;
  shipping them is closing a contract bug, not adding a feature.
- **v0.2.0 minor:** T1, T2, T3, T4, T5, T7, T8 alongside M8/M9/M10.
  Daily-driver table stakes complete.
- **v0.3.0+:** M11–M15. Unfair-advantage features (Voss-aware tools,
  MCP server, multi-agent in chat, watch, marketplace).
- **v1.0.0:** API lock once dogfood signals stable public surface.

Rationale: T1 rewrites `_run_turn_exec` into a while-loop and shifts the
confidence gate semantics — a 0.1.1 patch can't carry that change without
breaking SDK embedders. Pre-1.0 minor bumps may break per `docs/sdk.md`
§Versioning, so v0.2.0 is the right slot. 1.0 stays reserved for the post-
M15 surface freeze.

---

## What's intentionally NOT in this list

- **Multi-machine agents** — Out of scope per HARNESS-PLAN §12.
- **Telemetry / cloud sync** — Out of scope per M5 constraints.
- **Web UI / IDE integrations** — Out of scope per HARNESS-PLAN §12.
- **Tree-sitter for `ast.search`** — Deferred per HARNESS-PLAN §10.
- **Windows support beyond npm wrapper** — Deferred per M6.
- **Renaming `voss do` / `voss chat`** — Surface lock per M0.

---

## Open questions for owner

1. ~~v0.1 ship lock — promote any T-phases into v0.1, or ship as v0.2?~~
   **Resolved 2026-05-15:** T6 → v0.1.1 patch; T1–T5 + T7–T8 → v0.2.
2. ~~T6 (slash debt) — bug-fix patch to M1, or standalone phase?~~
   **Resolved 2026-05-15:** Standalone T6 phase, shipped as v0.1.1 patch.
3. ~~T3 (network) — DuckDuckGo HTML for `web_search`?~~
   **Resolved 2026-05-15:** Rejected. Ship `web_search` with no built-in
   backend; opt-in Brave / Tavily via API key.
4. T5 (background shell) — does the harness commit to `voss jobs` as a
   top-level CLI verb, or does that belong only inside the REPL? *(Still
   open — defaulting to top-level per SHELL-05 unless SPEC pushes back.)*
5. T1 (iteration loop) — right max-iteration default? Claude Code has no
   hard cap; Codex caps at 25. Proposed 8 is conservative. *(Still open —
   final number locked in T1 SPEC.)*
