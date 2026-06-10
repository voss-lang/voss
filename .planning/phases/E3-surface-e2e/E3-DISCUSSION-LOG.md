# Phase E3: Surface E2E - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** E3-surface-e2e
**Areas discussed:** Surface inventory, Harness shape, Server-plane driving, Stub-layer relationship

**Mode note:** AskUserQuestion menus returned empty twice; areas presented as plain-text list. User replied "apply all of your recommendations and create CONTEXT.md" — all four areas resolved with Claude's recommended options, delegated explicitly.

---

## Surface inventory

| Option | Description | Selected |
|--------|-------------|----------|
| Core four: do / chat / edit / serve(+SSE+permission) | Model-involving surfaces only | ✓ (recommended, auto-applied) |
| Include board/team run + multiagent | Org-plane coverage, heavy sub burn | deferred |
| Include doctor/check | No model involvement — stub layer suffices | excluded |

---

## Harness shape

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse E1 substrate + `surface` field + per-surface drivers, `voss eval --suite surfaces` | One scoring/caps/artifact system | ✓ (recommended, auto-applied) |
| Separate live-marked pytest layer | Second result format, no caps/judge reuse | |
| New standalone runner | Rebuild against reuse-not-rebuild principle | |

---

## Server-plane driving

| Option | Description | Selected |
|--------|-------------|----------|
| Raw Python httpx + SSE, spawn serve subprocess + handshake | Same runtime, httpx already a dep; SDKs are E4's proof | ✓ (recommended, auto-applied) |
| V13.1 TS client | Cross-runtime harness complexity | |
| Go SDK | Same | |

Permission-gate Allow/Deny flow: in scope (Allow completes turn; Deny degrades without hang).

---

## Stub-layer relationship

| Option | Description | Selected |
|--------|-------------|----------|
| Keep tests/e2e/ untouched as hermetic regression layer; E3 separate | Two layers, distinct jobs | ✓ (recommended, auto-applied) |
| Graduate/share scenarios | Coupling, premature | |

---

## Claude's Discretion

- Scenario counts per surface (≤ ~10 total)
- Driver module placement/naming, timeout plumbing
- Serve readiness/teardown details
- Surface dispatch mechanism

## Deferred Ideas

- board/team-run live e2e (own phase)
- Multiagent spawn live scenario
- Stub↔live graduation/dedup
- SDK-driven server scenarios → E4
- PTY-interactive chat → E5
