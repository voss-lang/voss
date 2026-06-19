# Phase BOS7: Web Control Plane Boundary - Discussion Log

> **Audit trail only.** Decisions captured in CONTEXT.md — this log preserves alternatives considered.

**Date:** 2026-06-18
**Phase:** BOS7-web-control-plane-boundary
**Areas discussed:** 4-way surface partition, Data/sync + privacy boundary, Review-surface placement, Offline/connectivity + identity

---

## 4-Way Surface Partition

| Option | Description | Selected |
|--------|-------------|----------|
| Thin desktop, backend owns projection | harness=source; desktop=local UI+worker; backend=projection/ledger/policy; web=shared surface | ✓ |
| Fat desktop, thin web mirror | desktop runs projection/analytics locally | |
| Fat web/backend, terminal-only desktop | web+backend own logic, desktop pure terminal | |

**User's choice:** Thin desktop, backend owns projection (Recommended).
**Notes:** Clean source→backend→web flow; desktop stays local-first + worker node.

---

## Data / Sync + Privacy Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Metadata/decisions sync, content stays local | only structured metadata+decisions+outcomes sync; raw code/prompts/files never leave desktop | ✓ |
| Full sync, filter at web | sync full events incl content, filter web-side | |
| Manual export only | no live sync | |

**User's choice:** Metadata/decisions sync, content stays local (Recommended).
**Notes:** Content-never-leaves-desktop is the load-bearing privacy invariant; feeds BOS6.

---

## Review-Surface Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Both, scoped differently — one contract | desktop=my runs, web=team queue, single BOS9 contract → two targets | ✓ |
| Web-only | BOS recommendations review only on web | |
| Desktop-only for now | web review deferred | |

**User's choice:** Both, scoped differently — one contract (Recommended).
**Notes:** No logic duplication; shapes BOS9 contract.

---

## Offline / Connectivity + Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Desktop standalone; web additive; identity seam reserved | desktop offline-capable; web additive; loopback token kept; accounts = future seam | ✓ |
| Backend required for full function | desktop degrades heavily offline | |
| Define accounts/auth now | specify shared identity in BOS7 | |

**User's choice:** Desktop standalone; web additive; identity seam reserved (Recommended).
**Notes:** Preserves local-first; accounts stay out-of-scope, only seam reserved.

---

## Claude's Discretion

- Responsibility-map format (recommend capability × surface matrix + flow diagram + rationale).
- Capability enumeration granularity.
- Secondary boundary lines not changing the 4 decisions.

## Deferred Ideas

- Accounts/auth/shared identity/multi-tenancy → future web-auth phase.
- Building apps/web → future implementation phase.
- Recommendation review UI → BOS9.
- Governance/privacy policy detail → BOS6.
- Desktop worker-node mechanics → BOS10.
- External ingestion mechanics → BOS12.
- Sync conflict/merge beyond one-directional → BOS2.
