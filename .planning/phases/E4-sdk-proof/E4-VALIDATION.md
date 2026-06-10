---
phase: E4
slug: sdk-proof
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase E4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Generated from `E4-RESEARCH.md` §Validation Architecture. Per-task map filled by the planner.
> Requirements CONTEXT-decision-driven (D-01..D-08) — minted EVSDK-* (no SPEC).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python runner) + per-SDK consumer subprograms |
| **Interpreter** | `.venv/bin/python` (bare `python3` lacks deps — REQUIRED) |
| **Quick run command** | `.venv/bin/python -m pytest tests/eval/ -k sdk -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/eval/ -q` |
| **SDK stub run** | `VOSS_DEV=1 ... eval --suite sdk --stub` (hermetic: SSE plumbing + typed-event decode; NO permission gate) |
| **SDK live run** | `VOSS_DEV=1 ... eval --suite sdk --auth codex` (subscription; full turn + permission Allow/Deny; skipped without creds) |
| **Toolchains** | node v22.22.3 · go 1.26.2 · cargo 1.95-nightly (all verified present); TS `dist` pre-built, no installs |
| **Estimated runtime** | quick <15s · live bounded by turn caps |

---

## Sampling Rate

- **After every task commit:** quick command (sdk-scoped).
- **After every plan wave:** full `tests/eval/` suite (must not regress E1/E2/E3).
- **Before `/gsd-verify-work`:** SDK stub run green for all four consumer subprograms (build + SSE plumbing + typed decode).
- **Live proof run:** manual, subscription-gated, turn-capped — NOT in automated sampling.

---

## Per-Surface Verification Map

*Filled by the planner. Each surface (sdk:python/ts/go/rust) gets a hermetic stub scenario + a live scenario. Seed rows:*

| Surface | Decision | Hermetic (stub) assertion | Live-only assertion |
|---------|----------|---------------------------|---------------------|
| sdk:python | D-01/D-03/D-04 | in-process public API constructs; SessionView introspect on stubbed turn | live turn + readable session/audit |
| sdk:ts | D-01/D-03/D-06 | `node` consumer builds; connects pre-spawned serve (env, NOT VossLauncher); decodes typed SSE union | live turn + permission Allow/Deny round-trip |
| sdk:go | D-01/D-03/D-06 | `go run` consumer builds; AttachClient to pre-spawned serve; decodes events | live turn + permission round-trip |
| sdk:rust | D-01/D-03/D-06 | `cargo run` consumer builds; `VOSS_SERVE_FAKE_TURN` SSE plumbing | live turn + permission round-trip |
| dispatch | D-05 | `surface` field accepts `sdk:python|ts|go|rust`; runner routes to consumer driver | — |
| proof run | D-08 | — | ≥1 scenario/surface, ≥80% gate_pass, 0 capped, permission scenario passes; human checkpoint |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/eval/test_sdk.py` — RED stubs: surface-field-accepts-sdk-values, each consumer subprogram builds (`go build`/`cargo build`/`node` import resolves), stub-mode SSE-plumbing per surface
- [ ] Verify consumer build paths up front (RESEARCH open Qs: go.mod `replace` directive; TS `file:` vs dist import) before writing consumer logic
- [ ] Reuse existing eval conftest (`VOSS_DEV=1`, stub provider, serve spawn from E3 pattern)

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Live permission round-trip via each SDK client | D-03/D-08 | `VOSS_SERVE_FAKE_TURN` emits no `permission.updated`; needs real model | `VOSS_DEV=1 ... --suite sdk --auth codex`; confirm each client hits gate, replies Allow, reaches final; Deny degrades without hang |
| SDK suite proof run | D-08 | subscription creds | ≥80% gate_pass, 0 capped, all four surfaces ≥1 scenario; record artifacts in SUMMARY |

---

## Validation Sign-Off

- [ ] Every surface has a hermetic stub scenario + a live scenario
- [ ] Consumer subprograms build with zero new package installs
- [ ] No watch-mode flags; live run gated/skipped without creds
- [ ] Feedback latency < 15s (quick)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
