# Phase V13: External Developer SDK Surfaces (foundation) — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.148 (gate: ≤ 0.20)
**Requirements:** 7 locked

## Goal

Lock the external-developer SDK strategy (surface matrix, five stability tiers, language priority, non-goals), reconcile `docs/sdk.md` with `.planning/PROTOCOL.md`, and build the **language-agnostic codegen substrate** every per-language client (sub-phases V13.1–V13.4) generates from: a statically-exported, committed contract snapshot (`openapi.json` + SSE event-union schema) protected by a CI drift gate. V13 ships **no client code** — only the strategy docs + the contract substrate.

## Background

Grounded in the current repo (scouted 2026-06-06):

- **Server is real and runnable.** `voss serve` CLI exists (`voss/harness/cli.py:3722`); `voss/harness/server/serve.py:run_server` binds an ephemeral loopback port, prints the `{v,port,token}` handshake, and supervises lifecycle. `create_app(token)` (`server/app.py:262`) builds the FastAPI app.
- **OpenAPI is dumpable statically.** `app.py:_force_event_schema` overrides `app.openapi` to force the `EventEnvelope` discriminated union into OpenAPI components (the comment: "so codegen emits a tagged Rust enum"). `create_app(token).openapi()` returns the full schema dict with no live server.
- **The event union is locked.** `voss/harness/server/events.py` defines the 21-member `AgentEvent` discriminated union + `EventEnvelope` + `PROTOCOL_VERSION = 1`. `EventEnvelope.model_json_schema()` yields the SSE contract.
- **Wire contract is LOCKED.** `.planning/PROTOCOL.md` v1 is marked "Contract LOCKED for H1–H6"; consumers explicitly named are "future web/VSCode/SDK clients."
- **The doc contradiction exists.** `docs/sdk.md:240` says "HTTP/remote SDK. Voss is local-first by design. No service, no client." — stale, written before the H-track shipped the server. It does not reference `PROTOCOL.md` at all.
- **Codegen tooling is greenfield.** No `openapi-typescript` / `oapi-codegen` / `progenitor` references anywhere in the repo.
- **Python SDK gaps are owned by M7.** `REQUIREMENTS.md` SDK-01..05 (Renderer/NullRenderer, `tool_entry_from_callable`, `SessionView`, `RuntimeConfig.from_toml`, provider `register`) are "plans ready" but NOT shipped.
- **Reuse points for later sub-phases:** `crates/voss-tui` / `voss-auth` / `voss-bridge` / `voss-render` (V13.2 Rust); `npm/` M6 wrapper tree (V13.1 TS home).

What does NOT exist yet: the SDK Surface Matrix, the stability-tier taxonomy, the reconciled `sdk.md`, a committed contract snapshot (`openapi.json` + event schema), and a CI drift gate. Those are this phase's deliverables.

## Requirements

1. **SDK Surface Matrix**: A language × surface × tier matrix is the single source of truth for which SDK serves which integration style.
   - Current: No matrix exists; SDK strategy is scattered across `docs/sdk.md` (Python-only) and `ORCHESTRATION_LAYERS.md` (implied surfaces).
   - Target: A "SDK Surface Matrix" section added to `docs/ORCHESTRATION_LAYERS.md` mapping each language (Python, TypeScript, Rust, Go, C) against its surfaces (in-process runtime, REST client, SSE event client, server launcher/supervisor, permission helpers, session/audit readers, ABI/schema doc) and assigning each cell a stability tier or "—" / "deferred".
   - Acceptance: `docs/ORCHESTRATION_LAYERS.md` contains a "SDK Surface Matrix" heading with a table whose rows cover all five languages and whose cells reference the five tier names from VSDK-02.

2. **Stability tiers**: Five named tiers exist and every public SDK surface is assigned exactly one.
   - Current: No tier taxonomy; `docs/sdk.md` has only a pre-1.0 semver carve-out, not surface tiers.
   - Target: Five tiers defined — `stable-now`, `experimental`, `generated-from-protocol`, `private-internal`, `deferred` — each with a one-line definition; every surface in the matrix (VSDK-01) carries one.
   - Acceptance: The five tier names appear with definitions in `docs/ORCHESTRATION_LAYERS.md`; no matrix cell is left untiered (every non-"—" cell names one of the five).

3. **Language priority**: The build order across languages is locked and justified.
   - Current: ROADMAP sub-phase ordering (V13.1 TS → .2 Rust → .3 Go → .4 C) exists but the rationale isn't captured in the SDK strategy doc.
   - Target: Priority documented as Python in-process → TypeScript local client → Rust local/native → Go local/headless → C ABI/schema-only, each with a one-line "why this rank" tied to consumer demand.
   - Acceptance: `docs/ORCHESTRATION_LAYERS.md` states the five-language ordered priority with a rationale line per language; order matches ROADMAP V13.1–.4.

4. **Non-goals**: What V13 (and the SDK track) explicitly will not do is an explicit list.
   - Current: Non-goals are implied in the ROADMAP row but not in the SDK strategy doc.
   - Target: Documented non-goals: no hosted/cloud SDK; no Rust/Go reimplementation of EM/board/runtime semantics; no formal marketplace/plugin sandbox unless separately scoped; no broad language SDKs (Kotlin/Swift/C#/Java/Ruby/PHP) without real consumer demand.
   - Acceptance: `docs/ORCHESTRATION_LAYERS.md` contains a "Non-goals" list for the SDK track with all four items above.

5. **Reconcile sdk.md ↔ PROTOCOL.md**: The stale "no service, no client" claim is removed and the local-client story is correct.
   - Current: `docs/sdk.md:240` asserts "HTTP/remote SDK. Voss is local-first by design. No service, no client. Deferred." with no reference to `PROTOCOL.md` or `voss serve`.
   - Target: `docs/sdk.md` is rewritten to draw the distinction "local loopback client (REST/SSE on `127.0.0.1`, ephemeral token) ≠ hosted/remote SDK" — local client SDK is in-scope (points to PROTOCOL.md + the V13.x sub-phases); only hosted/cloud is a non-goal. `sdk.md` and `PROTOCOL.md` cross-link.
   - Acceptance: `docs/sdk.md` no longer contains the string "No service, no client"; it references `.planning/PROTOCOL.md` and the V13.x local client SDKs; a verifier reading both docs finds no contradiction on whether a local client SDK is in-scope.

6. **Python SDK / M7 linkage**: The Python in-process SDK surface is documented as M7-owned, with org-layer read-views enumerated and gated, without V13 depending on M7 shipping.
   - Current: `docs/sdk.md` "Known gaps (closing in M7)" lists the holes; `REQUIREMENTS.md` SDK-01..05 are unshipped; no enumeration of org-layer read views (capabilities/team/session-tree/audit) to promote.
   - Target: The matrix's Python row cites M7 `SDK-01..05` as the first-class in-process surface, and a "deferred read-views" list enumerates org-layer surfaces (capability list/inspect, team-compile helpers, session-tree readers, audit readers) each tagged with its gating phase (V1 / V3 / V4 / V9).
   - Acceptance: `docs/ORCHESTRATION_LAYERS.md` Python entry references SDK-01..05 and lists ≥4 deferred read-views each annotated with a gating V-phase; V13 introduces no code change to `voss.harness` / `voss_runtime` public surface (M7's job).

7. **Codegen substrate + CI drift gate**: A statically-exported, committed contract snapshot exists and CI fails on any drift.
   - Current: No committed `openapi.json` or event-union schema; no drift gate. The schema lives only in live code (`create_app().openapi()`, `EventEnvelope.model_json_schema()`).
   - Target: A repo-committed contract snapshot — `openapi.json` (from `create_app(<fixed-token>).openapi()`) and an SSE event-union schema (from `EventEnvelope.model_json_schema()`) — plus an exporter script that regenerates them deterministically, plus a CI test that re-exports and compares against the committed snapshot, failing on ANY diff (REST schema OR event union), mirroring the existing H3.3 parity-test pattern. No live server is booted for export. No per-language client code is generated in V13.
   - Acceptance: Committed `openapi.json` + event-union schema files exist; the exporter is re-runnable and deterministic (re-export with no code change produces byte-identical files); the drift-gate test passes on the committed snapshot AND fails when a synthetic field is added to any event model or route without re-snapshotting.

## Boundaries

**In scope:**
- SDK Surface Matrix (language × surface × tier) in `docs/ORCHESTRATION_LAYERS.md`
- Five-tier stability taxonomy with every surface assigned
- Language priority + rationale
- SDK-track non-goals list
- `docs/sdk.md` rewrite reconciling it with `PROTOCOL.md` (kill "no service, no client", cross-link)
- Python/M7 linkage documentation + enumerated deferred read-views with gating phases
- Static contract export (`openapi.json` + event-union schema) committed to the repo
- Deterministic exporter script
- CI drift gate (REST + SSE union, any-diff-fails)

**Out of scope:**
- Any per-language client code (TS/Rust/Go/C) — that is sub-phases V13.1–V13.4
- Codegen *tool* selection (openapi-typescript / oapi-codegen / progenitor / etc.) — each V13.x picks its own off this substrate
- Implementing M7 SDK-01..05 — owned by M7; V13 only documents the linkage
- Deep reader SDKs (full audit/replay, team-compile helpers, capability introspection beyond protocol-exposed data) — gated on V1/V3/V4/V9 freezing, land inside the relevant V13.x when its upstream is ready
- Any change to `PROTOCOL.md` v1 wire contract — it is LOCKED; V13 consumes it, never edits it
- Hosted/cloud/remote SDK — permanent non-goal
- New REST/SSE endpoints or event types — V13 snapshots the existing surface, does not extend it

## Constraints

- **Schema capture is static** — export from the app object (`create_app(<fixed-token>).openapi()`) and `EventEnvelope.model_json_schema()`; no live `voss serve` process in the export or the CI gate (hermetic, deterministic).
- **A fixed token must be used for export** so `openapi.json` is byte-stable across runs (the live server uses a random token; the exporter must pin one).
- **Drift gate covers BOTH** the REST OpenAPI schema and the SSE `EventEnvelope` union; ANY diff vs the committed snapshot fails CI (no additive-only allowance), forcing a deliberate snapshot bump — mirrors the H3.3 parity-test convention.
- **No dependency on M7** — V13 must complete and pass CI whether or not M7 has shipped.
- **`PROTOCOL.md` v1 is immutable in this phase** — a schema change that would alter the snapshot requires a PROTOCOL `v` bump + migration note, out of V13 scope.
- Exact committed path for the snapshot artifacts (e.g. `contracts/openapi.json`, `contracts/events.schema.json`) and CI-wiring details are HOW — finalized in discuss-phase.

## Acceptance Criteria

- [ ] `docs/ORCHESTRATION_LAYERS.md` contains a "SDK Surface Matrix" table covering Python, TypeScript, Rust, Go, C
- [ ] Five tiers (`stable-now`, `experimental`, `generated-from-protocol`, `private-internal`, `deferred`) are defined and every non-"—" matrix cell carries one
- [ ] Language priority (Python → TS → Rust → Go → C) is documented with a per-language rationale, matching ROADMAP V13.1–.4 order
- [ ] SDK-track non-goals list present with all four locked items
- [ ] `docs/sdk.md` no longer contains "No service, no client"; it cross-links `PROTOCOL.md` and the V13.x local client SDKs; no in-scope contradiction remains between the two docs
- [ ] Python matrix entry cites M7 `SDK-01..05` and lists ≥4 deferred read-views each tagged with a gating V-phase (V1/V3/V4/V9)
- [ ] V13 changes zero lines of `voss.harness` / `voss_runtime` public `__all__`
- [ ] Committed `openapi.json` + event-union schema files exist in the repo
- [ ] Re-running the exporter with no code change produces byte-identical snapshot files (deterministic)
- [ ] CI drift-gate test passes against the committed snapshot
- [ ] CI drift-gate test FAILS when a synthetic field is added to any event model or route and the snapshot is not regenerated

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Foundation-only; client code explicitly excluded             |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | V13-vs-V13.x split + deep-reader gating explicit             |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Static export, both schemas, any-diff-fails, no M7 dep       |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 11 pass/fail checks incl. negative drift-gate test           |
| **Ambiguity**      | 0.148 | ≤0.20| ✓      |                                                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective        | Question summary                          | Decision locked                                                        |
|-------|--------------------|-------------------------------------------|------------------------------------------------------------------------|
| 0     | Researcher (scout) | What exists for SDK/server today?         | `voss serve` + OpenAPI + locked EventEnvelope exist; codegen greenfield; M7 unshipped |
| 1     | Boundary Keeper    | What does the V13 pipeline produce?       | Schema + drift gate only (language-agnostic); NO client code in V13    |
| 1     | Researcher         | How is the schema captured?               | Static export from app object (`create_app().openapi()`); no live server |
| 1     | Failure Analyst    | What does the drift gate cover + fail on? | REST OpenAPI + SSE EventEnvelope union; ANY diff fails CI (H3.3 pattern) |

---

*Phase: V13-external-developer-sdk-surfaces-foundation*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V13 — implementation decisions (codegen substrate layout, contract-artifact path, exporter + CI wiring)*
