# Phase E4: SDK Proof - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning (consumes E1 substrate [shipped] + extends E3's `surface` dispatch; no SPEC — decisions seed EVSDK-*)

<domain>
## Phase Boundary

E4 proves the public **SDK surfaces** work as real external consumers driving **live** model runs — not just type-checked or drift-gated. Surfaces: the Python embedder API (`voss.harness` / `voss_runtime`, the M7 public surface, in-process) and the shipped client SDKs (TypeScript `sdk/typescript` V13.1, Go `sdk/go` V13.3) consuming the `voss serve` REST/SSE plane. All scored through the E1 hybrid substrate (deterministic checks + LLM judge, turn caps, `VOSS_DEV` gate, JSONL + summary). This is E3's surface-proof pattern applied to the SDK surface — E3 explicitly drove serve via raw httpx and **deferred SDK-driven scenarios to E4**.

**Dependencies:** Consumes E1 substrate (`TaskSpec.checks`, `_run_checks`, caps, judge split — research-verified SHIPPED in E1-01/02/03). Extends E3's `surface`-field driver dispatch (E3 planned, not yet executed) — sequence E4 after E3, OR E4 defines its own `sdk:*` surfaces if E3 hasn't merged. Reuses the `voss serve` spawn/`{v,port,token}` handshake (V15 / `crates/voss-sdk` `spawn_with`, 60s cold-start).

</domain>

<decisions>
## Implementation Decisions

*(User delegated all four areas to Claude's recommendations — selections below are binding, mirroring the E3 surface-proof structure.)*

### SDK surface inventory (what E4 covers) — D-01/D-02
- **D-01:** E4 proves four SDK surfaces: `sdk:python` (in-process embedder via `voss.harness`/`voss_runtime` public API — M7 surface in `docs/sdk.md`), `sdk:ts` (`sdk/typescript` V13.1 client against live `voss serve`), `sdk:go` (`sdk/go` V13.3 client against live `voss serve`), `sdk:rust` (`crates/voss-sdk` V13.2 client — `VossClient` / `event_stream` / permission-reply, a `cargo run` consumer against live serve). **Research-confirmed (user-approved):** `crates/voss-sdk` is the FULL V13.2 client (not just the `spawn_with` helper) and has a `VOSS_SERVE_FAKE_TURN` hermetic path.
- **D-02 (excluded surfaces):** C ABI (V13.4) is doc-only (no SDK to exercise) — out. (Rust was briefly deferred on a wrong "not in `sdk/`" assumption; research found it at `crates/voss-sdk` and confirmed it full — now in scope per D-01.)

### Scenario depth (what each consumer exercises) — D-03/D-04
- **D-03:** Representative workflow, not smoke. The client SDKs (`sdk:ts`, `sdk:go`) each run the marquee path against a live server: construct client → spawn/attach `voss serve` → create session + one live model turn → consume the typed SSE event union (events decode to the SDK's typed model) → hit a gated tool call → reply **Allow** via the permission route → reach final → read the session/audit back via the SDK's reader. A **Deny** variant asserts the turn degrades without hanging.
- **D-04:** `sdk:python` drives in-process via the public API (construct harness, run a live turn, introspect via the public `SessionView`/session readers) — no serve subprocess required for the in-process path. Checks assert the typed result + readable session; judge scores the agent output.

### Driving mechanics (how scenarios run) — D-05/D-06
- **D-05:** Reuse the E1 substrate + extend E3's per-surface driver dispatch — NO new runner, NO scoring outside E1. Scenarios are `task.toml` files in a new suite dir `tests/eval/sdk/<NN>-<slug>/` invoked via `voss eval --suite sdk` (VOSS_DEV-gated, caps, hybrid scoring, JSONL + summary inherited). New `surface` values: `sdk:python | sdk:ts | sdk:go`.
- **D-06:** For `sdk:ts`/`sdk:go`, the driver spawns a **minimal committed consumer subprogram** (`tests/eval/sdk/consumers/{ts,go}/`) that uses ONLY the real SDK's public client API against the live server and emits a structured JSON result to stdout; the Python runner scores that result + the server-side session/audit artifacts. This keeps E1 the single scoring substrate (E3 driver pattern) rather than scattering gate/judge/JSONL across three runtimes. The consumer programs are tiny + auditable + prove the external-consumer contract (public API only).

### Repo-shape interaction — D-07
- **D-07:** Shape-AGNOSTIC — prove the SDK surface ONCE on a single simple fixture (reuse one E2 Python fixture or a minimal one). The SDK contract (REST/SSE/typed events/permission/readers) is identical regardless of the target repo the agent operates on; the repo-shape axis is already owned by E2. Crossing SDK × py/rust/ts = 3× subscription burn for zero new SDK-contract signal.

### Proof criteria (phase closing act, mirrors E1 EVSUB-07 / E3 D-11) — D-08
- **D-08:** One documented live run on codex subscription auth: every surface (`sdk:python`/`sdk:ts`/`sdk:go`) has ≥1 scenario, overall ≥80% `gate_pass`, 0 capped rows, the permission-gate scenario among the passers. Human checkpoint task (operator creds), artifacts recorded in phase SUMMARY.

### Claude's Discretion
- Scenario count per surface (1–2 each; keep total sub burn ≤ ~8 scenarios).
- Consumer-subprogram internals (build/run command, structured-result schema, timeout plumbing — reuse E1's check-timeout pattern; TS via `node --experimental-strip-types`/`tsx` no-install per E2; Go via `go run`).
- Whether `surface` dispatch extends E3's registry/match or adds parallel `sdk:*` entries (depends on E3 merge order).
- serve readiness/teardown for the client scenarios (reuse E3's serve driver lifecycle).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contracts (read first)
- `.planning/phases/E1-eval-substrate/E1-SPEC.md` — substrate E4 consumes (checks, caps, gate, judge split). Research-verified SHIPPED.
- `.planning/phases/E3-surface-e2e/E3-CONTEXT.md` — the direct analog (surface-proof pattern, `surface` field, serve spawn/handshake driver, proof criteria D-11). E4 mirrors this structure for the SDK surface.
- `.planning/phases/E3-surface-e2e/E3-RESEARCH.md` — serve driver mechanics (handshake parse, SSE consumption, permission route) E4's client scenarios reuse.
- `.planning/notes/e-track-eval-decisions.md` — E-track posture (surfaces × shapes axis; SDK is a runtime surface; internal-only; LangSmith later-only).

### SDK surfaces under test
- `docs/sdk.md` — the Python public API (M7): `from voss_runtime import (...)`, `from voss.harness import (...)`, `SessionView`, `NullRenderer`, `main`. This is `sdk:python`.
- `sdk/typescript/` — V13.1 TS client (serve launcher, REST, SSE typed-event client, permission-reply helpers, typed event union). This is `sdk:ts`.
- `sdk/go/` — V13.3 Go client (attach/serve, session CRUD, stream events, approve/deny gates, export audit/session; `client_test.go` real-server TestMain is the reference). This is `sdk:go`.
- `crates/voss-sdk/` — V13.2 Rust client (`VossClient`, `event_stream`, `spawn_with`, `Supervisor`, typed event union, permission reply; `VOSS_SERVE_FAKE_TURN` hermetic path; integration tests are the reference). This is `sdk:rust`.
- `.planning/ROADMAP.md` §V13.1/V13.3 — the SDK surface matrix + stability tiers; §V15 + `crates/voss-sdk` `spawn_with` — proven serve spawn/handshake (60s cold-start, `LITELLM_LOCAL_MODEL_COST_MAP=true`).
- `.planning/PROTOCOL.md` — wire contract (event union §6, permission route, handshake) the clients consume.

### Substrate + live-auth
- `voss/eval/suite.py`, `voss/eval/runner.py` — post-E1 integration base + (post-E3) `surface` dispatch point.
- `voss/harness/auth.py` — codex subscription auth; quirks (no temperature/max_tokens, gpt-5.x only) must not regress.

*EVSDK-* requirements TBD — no SPEC/REQUIREMENTS entries; this CONTEXT is the seed.*

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- E1 substrate (shipped): `TaskSpec`+`checks`, `_run_checks`, caps, `[eval]` config, `VOSS_DEV` gate, JSONL writer, summary columns — E4 adds drivers + consumer subprograms, not scoring.
- E3's `surface` field + per-surface driver dispatch (planned) — E4 extends with `sdk:python|ts|go`.
- E3's serve driver (spawn `voss serve`, parse `{v,port,token}`, consume SSE, permission route) — E4's `sdk:ts`/`sdk:go` scenarios target the same live server via the SDK clients instead of httpx.
- `sdk/go/client_test.go` — real-server spawn/handshake/no-orphan supervisor; reference for the Go consumer subprogram.
- `sdk/typescript` serve launcher + typed SSE client — basis for the TS consumer subprogram.
- `docs/sdk.md` public Python surface — `sdk:python` in-process driver uses exactly these symbols.

### Established Patterns
- Single scoring substrate: drivers/consumers produce output; E1 gate+judge+JSONL score it. Do NOT add per-runtime scoring.
- Additive JSONL: new `surface` values + any consumer-result fields appended, never reordered; REQUIRED_FIELDS sentinel updated same plan.
- Stub-driveable test path per driver (hermetic CI) + live path (subscription, skipped without creds) — mirror E3.
- Consumer subprograms use the SDK's PUBLIC client API only — proving the external-consumer contract, not internals.

### Integration Points
- `voss/eval/runner.py` `surface` dispatch — add `sdk:*` driver routes.
- `tests/eval/sdk/` new suite dir + `tests/eval/sdk/consumers/{ts,go}/` consumer programs.
- `voss eval --suite sdk` — existing `--suite` loader.
- `tests/eval/conftest.py` VOSS_DEV autouse extends to the new driver tests.

</code_context>

<specifics>
## Specific Ideas

- The permission-gate round-trip THROUGH the actual SDK client (not httpx) is E4's marquee proof — it proves an external developer can drive the full live plane (spawn → session → SSE typed events → gate → Allow/Deny → final → read audit) via the published client, which nothing proves today (V13.x tests are drift/type + stub-server only).
- Keep consumer subprograms minimal + committed so a human can audit exactly what API the "external consumer" touches.
- Run header must surface total sub-burn upfront (SDK suite + live turns).

### Research pitfalls (planner MUST encode)
- **TS handshake timeout:** `VossLauncher.start()` has a hardcoded `HANDSHAKE_TIMEOUT_MS = 10_000` (source + built `dist/node.js`) but cold litellm start is 15-45s. The TS consumer MUST NOT self-launch via `VossLauncher`; the Python runner pre-spawns `voss serve` and passes `VOSS_BASE_URL`/`VOSS_TOKEN` via env to all client consumers.
- **Permission gate is live-only:** `VOSS_SERVE_FAKE_TURN` does NOT emit `permission.updated` (`app.py:166-178`). Hermetic/stub scenarios verify SSE plumbing + typed-event decode only; the Allow/Deny gate round-trip is a **live-only** scenario (subscription, skipped without creds).
- **E3 surface-dispatch dependency:** `suite.py`/`runner.py` have NO `surface` field today (E3 unexecuted). E4 must either gate W1 on E3-01 merging OR absorb E3-01's `surface`-field schema addition (idempotent) — planner decides; flag the chosen path in plan frontmatter.
- **Go `interpreterPath` CWD-relative:** `sdk/go/spawn.go` resolves `.venv/bin/python` relative to CWD; runner sets `VOSS_PYTHON=<abs>` for completeness (moot when consumers use `AttachClient` not `Spawn`).
- **Toolchains present:** node v22.22.3, go 1.26.2, cargo 1.95-nightly; TS `dist` pre-built (`eventsource-parser`/`openapi-fetch` installed). No new package installs.

</specifics>

<deferred>
## Deferred Ideas

- **C ABI (V13.4)** — doc-only, no SDK to exercise; out of E-track surface proofs.
- **SDK × repo-shape cross-product** — proving each SDK across py/rust/ts target repos; only if a shape-specific SDK behavior emerges (E2 owns the shape axis).
- **Org-plane SDK scenarios** (board/team-run via SDK) — heavy multi-agent burn; own phase if needed (mirrors E3 deferral).
- **LangSmith trace export of SDK runs** — E-track later-adapter only, never a dependency.

None is scope creep into E4 — all are explicitly downstream.

</deferred>

---

*Phase: E4-sdk-proof*
*Context gathered: 2026-06-10*
