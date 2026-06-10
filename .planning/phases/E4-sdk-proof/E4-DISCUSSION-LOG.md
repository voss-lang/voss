# Phase E4: SDK Proof - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** E4-sdk-proof
**Areas discussed:** SDK surface inventory, Scenario depth, Driving mechanics, Repo-shape interaction (all 4 — user delegated)

---

## Disambiguation

User invoked `/gsd-discuss-phase 4`. Bare "4" was ambiguous — the SDK mis-resolved it to a dead legacy `.planning/phases/04-codegen/` dir (`roadmap.get-phase 4` → found:false). Presented the real candidates (A4/V4/E4/F4); **user chose E4 — SDK Proof.**

## Gray-area selection

No E4-SPEC existed; `spec_loaded=false` (decisions seed EVSDK-*). Four gray areas presented (mirroring the E3 surface-proof structure). **User response: "apply your recommendations for all questions and create context.md"** — full delegation.

| Area | Options offered | Decision applied |
|------|-----------------|------------------|
| SDK surface inventory | python-only · +which clients (TS/Go/Rust) | **Python + TS + Go** (Rust deferred — not in `sdk/`; C doc-only out) |
| Scenario depth | smoke · representative workflow | **representative** (spawn→stream→permission Allow/Deny→final→read session/audit) |
| Driving mechanics | spawn SDK-consumer subprograms scored by Python runner · extend each SDK's own suite | **spawn minimal committed consumers** (E1 stays single scoring substrate) |
| Repo-shape interaction | shape-agnostic once · across py/rust/ts fixtures | **shape-agnostic** (SDK contract identical per shape; E2 owns shape axis) |

---

## Rationale anchors

- E3-CONTEXT is the direct analog; E3 explicitly deferred SDK-driven scenarios to E4 (E3 drove serve via raw httpx). E4 reuses E1 substrate + extends E3's `surface` dispatch.
- Python+TS+Go are the confirmed-shipped surfaces (`docs/sdk.md` M7 API + `sdk/typescript` V13.1 + `sdk/go` V13.3); Rust client not present in `sdk/` → deferred.
- Single scoring substrate (E-track ethos): consumer subprograms produce output; E1 gate+judge+JSONL score it — never scatter scoring across runtimes.
- Permission-gate round-trip through the actual SDK client = the marquee proof (nothing proves it today; V13.x tests are drift/type + stub-server only).
- Shape-agnostic = avoid 3× sub-burn for zero new SDK-contract signal.

## Deferred Ideas

- Rust client (V13.2) scenario (until confirmed shipped) · C ABI (doc-only) · SDK×repo-shape cross-product · org-plane SDK scenarios · LangSmith trace export.
