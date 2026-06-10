# Phase E3: Surface E2E - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning (gated on E1 execution)

<domain>
## Phase Boundary

E3 proves each runtime entry point works end-to-end with **real model inference**: the CLI verbs (`voss do`, `voss chat`, `voss edit`) driven as real subprocesses, and the server plane (`voss serve` → session → SSE event stream → permission gate → final) driven as a real HTTP/SSE client — all scored through the E1 hybrid substrate (deterministic checks + LLM judge, turn caps, JSONL + summary artifacts). Today's `tests/e2e/` covers these surfaces only on StubProvider; nothing proves them live.

**Hard dependency:** E1 must be executed first — E3 consumes `TaskSpec.checks`, `_run_checks`, turn caps, the `VOSS_DEV` gate, and the judge split. Plan E3 only after E1 waves 1–3 are merged.

</domain>

<decisions>
## Implementation Decisions

*(User delegated all four discussed areas to Claude's recommendations — selections below are binding.)*

### Surface inventory (what E3 covers)
- **D-01:** Live suite covers exactly four surfaces: `cli:do`, `cli:chat` (scripted non-interactive turn), `cli:edit`, and `serve` (session create → live turn → SSE consumption → permission Allow/Deny → final).
- **D-02:** Excluded from E3: `voss doctor`/`voss check` (no model involvement — stub layer already proves them), `voss board`/`voss team run` (org-plane, heavy multi-agent sub burn — own phase if needed), multiagent chat spawn (same reason). All captured in deferred.

### Harness shape (how scenarios run)
- **D-03:** Reuse the E1 substrate, no new runner: scenarios are `task.toml` files in a new suite dir `tests/eval/surfaces/<NN>-<slug>/` invoked via `voss eval --suite surfaces` (VOSS_DEV-gated, turn caps, hybrid scoring, JSONL + summary all inherited).
- **D-04:** `TaskSpec` gains an optional `surface` field (default `"internal"` = current in-process drive, preserving E1 golden tasks unchanged). Values: `internal | cli:do | cli:chat | cli:edit | serve`. The runner dispatches per-surface drivers.
- **D-05:** CLI surfaces run as **real subprocesses** (`python -m voss.cli ...` from the fixture cwd) with live auth env passed through — reuse the `Result`/invocation ergonomics of `tests/e2e/runner.py` but WITHOUT its stub `sitecustomize.py` injection. Checks run against the fixture dir + captured stdout/stderr; judge receives final output + file diff as in E1.
- **D-06:** `cli:chat` is driven non-interactively (piped/scripted single prompt + exit) — no PTY puppeteering in E3.

### Server-plane driving
- **D-07:** Server driver = **raw Python httpx + SSE** inside the eval runner — NOT the TS/Go SDKs (separate runtimes; proving SDKs is E4's job). httpx is already a repo dependency.
- **D-08:** Server scenarios spawn `voss serve` as a subprocess and consume the one-line `{v,port,token}` stdout handshake (same contract as V15 sidecar / `crates/voss-sdk` `spawn_with`, 60s cold-start). One server per scenario, killed on completion — no shared server across scenarios.
- **D-09:** The permission-gate flow is in scope: at least one serve scenario must hit a gated tool call, receive `permission.updated` on the SSE stream, reply Allow via the `POST /session/:id/permission` route (exact route per `PROTOCOL.md`), and complete the turn. A Deny variant asserts the turn degrades without hanging.

### Stub-layer relationship
- **D-10:** `tests/e2e/` stays untouched as the hermetic regression layer (runs in normal pytest, CI-safe). E3's live suite is a separate artifact under `tests/eval/surfaces/`. No graduation, no dedup, no shared fixtures in E3.

### Proof criteria (phase closing act, mirrors E1's EVSUB-07)
- **D-11:** One documented live run on codex subscription auth: every surface has ≥1 scenario, overall ≥80% gate_pass, 0 capped rows, serve permission-gate scenario among the passers. Human checkpoint task (operator creds), artifacts recorded in phase SUMMARY.

### Claude's Discretion
- Scenario count per surface (1–2 each; keep total sub burn ≤ ~10 scenarios).
- Driver internals (where subprocess/SSE drivers live in `voss/eval/`, naming, timeout plumbing — reuse E1's check timeout pattern).
- serve readiness/teardown details (handshake parse, port wait, kill semantics).
- Whether `surface` dispatch is a registry dict or match statement.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contracts
- `.planning/phases/E1-eval-substrate/E1-SPEC.md` — E1 locked requirements (substrate E3 consumes: checks, caps, gate, judge split).
- `.planning/phases/E1-eval-substrate/E1-CONTEXT.md` — E1 decisions D-01..D-11 (check shapes, cap semantics, VOSS_DEV, judge pin).
- `.planning/notes/e-track-eval-decisions.md` — E-track decision log (backend, judging, cadence; LangSmith = later adapter only, not E3).

### Substrate + existing layers
- `voss/eval/suite.py`, `voss/eval/runner.py` — post-E1 state is the integration base (TaskSpec.checks, `_run_checks`, max_turns, judge guard).
- `tests/e2e/runner.py` — subprocess CLI invocation ergonomics to mirror (Result dataclass, NDJSON parsing); its stub `sitecustomize.py` mechanism is exactly what E3 drivers must NOT install.
- `.planning/PROTOCOL.md` — wire contract for serve plane (event union §6, permission route, handshake).
- `crates/voss-sdk` `spawn_with` + V15 sidecar (`.planning/ROADMAP.md` Phase V15 section) — proven spawn/handshake pattern (60s cold-start, `LITELLM_LOCAL_MODEL_COST_MAP=true`).

### Live-auth path
- `voss/harness/auth.py` — codex subscription auth; quirks (no temperature/max_tokens, gpt-5.x only) must not regress.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- E1 substrate (post-execution): `TaskSpec` + `checks` union, `_run_checks`, turn caps, `[eval]` config, `VOSS_DEV` gate, JSONL writer, summary columns — E3 adds drivers, not scoring.
- `tests/e2e/runner.py` — `Result` dataclass, `json_payloads()` NDJSON helper, tmp-project-root invocation pattern.
- `httpx` — already used in `voss/eval/runner.py` (stub NetSession) and harness; SSE consumption pattern exists in harness/server code.
- Go SDK `client_test.go` spawn/handshake/no-orphan supervisor — reference behavior for serve lifecycle (not reused directly; Python reimplementation).

### Established Patterns
- Stub-mode hermetic testing: every new driver needs a stub-driveable test path (subprocess driver can target a stubbed CLI via the existing sitecustomize trick IN TESTS ONLY; live path skips it).
- `judge_inputs = ["final", "file_diff"]` — for serve scenarios "final" = final event payload text; for cli surfaces = stdout.
- Additive JSONL: new fields (e.g. `surface`) appended, never reordered; REQUIRED_FIELDS sentinel updated in same plan.

### Integration Points
- `voss/eval/runner.py` dispatch point: where `_drive_task` is called per task — surface field routes to subprocess/serve drivers there.
- `voss eval --suite surfaces` — suite loader already takes `--suite`; new dir under `tests/eval/surfaces/`.
- `tests/eval/conftest.py` (post-E1) — VOSS_DEV autouse extends to new driver tests.

</code_context>

<specifics>
## Specific Ideas

- Serve permission-gate scenario is the marquee proof — it exercises the V15 live plane end-to-end (spawn, handshake, SSE, gate, reply, final) with a real model, which nothing in the repo does today.
- Run header + caps must make total sub-burn visible upfront (suite is bigger than E1's golden 6).

</specifics>

<deferred>
## Deferred Ideas

- `voss board` / `voss team run` live e2e — org-plane surface, heavy multi-agent sub burn; own phase if team-run proof becomes a priority.
- Multiagent chat spawn live scenario — same burn concern; revisit after E3 baseline exists.
- Stub-layer graduation/dedup with live suite — revisit once both layers coexist for a while.
- TS/Go SDK-driven server scenarios — E4 (SDK proof) territory.
- PTY-interactive chat driving — E5 (TUI/voss-app autonomous driving) territory.

</deferred>

---

*Phase: E3-surface-e2e*
*Context gathered: 2026-06-10*
