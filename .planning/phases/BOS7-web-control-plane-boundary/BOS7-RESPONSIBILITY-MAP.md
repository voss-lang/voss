# BOS7: Web-vs-Desktop Responsibility Map

This is the BOS-PROD-04 placement contract for what belongs in the local harness runtime, desktop ADE, backend services, and web control plane.

How to read this: every capability has exactly one owner surface. `reads` means the surface consumes that capability or its output but does not own the logic. `none` means the surface does not own or consume it. This map places capabilities; it does not design any surface.

## Capability x Surface Matrix

| Capability | local harness | desktop ADE | backend services | web control plane |
|---|---|---|---|---|
| execute agent run | owns | reads | none | none |
| emit raw events | owns | reads | reads | none |
| serve local clients (loopback) | owns | reads | none | none |
| project/ingest events | none | none | owns | reads |
| store event ledger (Postgres) | none | reads | owns | reads |
| store decision ledger (BOS4) | none | reads | owns | reads |
| serve policy (BOS13+) | reads | reads | owns | reads |
| inspect/review own runs | reads | owns | reads | none |
| review team queue | none | none | reads | owns |
| manage team/work model | none | none | reads | owns |
| sync data up (metadata/decisions) | reads | reads | owns | reads |
| hold identity/token | owns | reads | none | none |
| act as desktop worker node | none | owns | reads | reads |
| read shared worker assignments | none | reads | owns | reads |

Identity/token note: the local harness owns the ephemeral loopback bearer token today. Shared web/backend identity does not have an owner in this milestone; the seam is reserved in `PROTOCOL.md` and in the offline/identity section below.

### Matrix rationale

D-01 partitions the system into four surfaces. The local harness is the execution source: it runs agents, emits raw events, and serves loopback clients. The desktop ADE is a local-first UI and worker node: it inspects and reviews the user's own runs, reads local and shared slices, and remains useful without a backend. Backend services own projection, ingestion, Postgres ledgers, and policy serving. The web control plane owns shared team management and team-scope review surfaces over backend state, with no separate business-logic copy.

Rejected alternatives: **fat-desktop** would duplicate backend projection and analytics logic inside the local ADE, making team aggregation hard and privacy boundaries blurry. **fat-web / terminal-only-desktop** would reduce the desktop to a terminal shell, losing local-first review and worker-node value.

## Surface Owner Notes

### Local Harness

- Owns the execution loop.
- Owns local tool and provider invocation.
- Owns raw event emission as the source signal.
- Owns the loopback server contract for local clients.
- Owns the ephemeral loopback bearer token.
- Reads policy when a later phase serves policy from backend services.
- Reads sync state only as needed to produce allowed metadata and decisions.
- Does not own Postgres projection.
- Does not own team analytics.
- Does not own the web team queue.
- Does not own shared accounts.

### Desktop ADE

- Owns the local-first user interface for active work.
- Owns inspection and review of the user's own runs.
- Owns the desktop worker-node surface for future shared BOS state.
- Reads the local harness loopback server.
- Reads local event and session state for my-scope review.
- Reads shared assignment or policy state only as a worker node.
- Does not own team projection logic.
- Does not own shared event or decision ledgers.
- Does not own team-wide management workflows.
- Does not require web or backend availability to keep local work running.

### Backend Services

- Own projection and ingestion.
- Own the shared event ledger in Postgres.
- Own the shared decision-ledger store.
- Own policy serving for BOS13 and later policy phases.
- Own ingestion from future external integrations.
- Read raw or derived event signals only through the structured sync boundary.
- Read desktop worker-node state as structured metadata.
- Do not own local execution.
- Do not own desktop rendering.
- Do not own the web presentation layer.

### Web Control Plane

- Owns shared team read/manage workflows.
- Owns the team-scope recommendation review queue.
- Reads backend ledgers and policy-serving outputs.
- Reads structured metadata, decisions, and outcome labels.
- Does not own local execution.
- Does not own raw event emission.
- Does not own backend projection logic.
- Does not receive raw code, prompts, or file content.
- Does not define accounts or multi-tenancy in this milestone.
- Does not replace the desktop ADE.

## Boundary Rules

- A capability has exactly one owner.
- A reader can consume a capability without owning the logic.
- Local harness is the source of execution truth.
- Backend services are the source of shared projection truth.
- Web is the shared team surface over backend state.
- Desktop is the local ADE and worker node, not a backend-in-miniature.
- Raw content stays local.
- Shared state is structured and derived.
- Web/backend absence must not block local desktop work.
- Accounts and shared identity are reserved as a seam, not designed here.
- BOS7 places capabilities; later phases design their surfaces.
- If a future phase needs to move ownership, it must explicitly revise this placement contract.

## Data Flow

```text
source(local harness) -> backend services(projection/store) -> web control plane(team surface)
```

The local harness emits raw events and remains the source of execution truth. Backend services ingest and project structured events, decisions, and outcome labels into shared ledgers. The web control plane reads the backend projection as the shared team surface. The desktop ADE reads its own slice locally and can act as a worker node over shared state, but it does not own team projection or analytics.

## Privacy Boundary (Invariant)

Invariant: raw code, prompts, and file content never leave the desktop.

Only structured event metadata, decision records, and outcome labels cross the desktop -> server boundary. That crossing is the BOS7 privacy boundary: BOS7 places where data may cross, and BOS6 sets the privacy, trust, reporting, and governance rules that apply to the crossing.

The invariant is placement-level, not a default that can be quietly overridden by a later surface. If a future feature needs raw code, prompts, or file content in shared state, it is outside this BOS7 contract until a later governance phase explicitly changes the boundary.

Rejected alternatives: **full-sync-filter-at-web** is rejected because it would send sensitive content first and rely on downstream filtering later. **manual-export-only** is rejected because it would protect content but break the live team-control-plane value of shared decisions and outcomes.

## Review Placement

Review lives on both desktop and web, scoped differently:

- Desktop ADE owns review of the user's own runs: the local, my-scope review path that can exist in the V24 Review tab and future desktop review surfaces.
- Web control plane owns the team-level recommendation queue: the shared, team-scope review surface over backend state.

Both targets render from a single BOS9 output contract. Desktop and web may present different scopes and layouts, but there is no logic duplication and no separate recommendation contract. BOS7 places review; BOS9 designs the recommendation review UI and output contract.

## Offline + Identity Seam

Desktop works fully standalone and offline. Web and backend are additive: if they are absent or unreachable, local desktop execution still runs, local inspection/review still works, and only team sync is lost.

The local harness keeps the ephemeral loopback bearer token defined by `PROTOCOL.md`: `voss serve` prints a per-process token in its JSON handshake, every REST/SSE request carries `Authorization: Bearer <token>`, and the token is never persisted. BOS7 preserves that local seam.

Shared web identity, accounts, authentication, billing, and multi-tenancy are out of scope for this milestone. BOS7 only reserves the boundary seam where a future web-auth layer can attach; it does not define accounts or shared identity.

## This Constrains

| Downstream consumer | What BOS7 hands it |
|---|---|
| BOS6 | Consumes the D-02 privacy boundary placement: raw code, prompts, and file content stay local; only structured metadata, decisions, and outcome labels cross. BOS6 sets the policy and reporting rules. |
| BOS9 | Consumes the D-03 review placement: one BOS9 output contract renders to desktop my-scope review and web team-scope review with no duplicated logic. BOS9 designs the UI. |
| BOS10 | Consumes the D-01 desktop-as-worker-node placement: desktop ADE owns local worker-node behavior while backend services own shared state projection and assignment serving. BOS10 designs the worker-node contract. |
| BOS12 | Consumes the D-01 backend-ingestion placement: external integration ingestion belongs in backend services, not the desktop ADE or local harness runtime. BOS12 designs ingestion mechanics and identity resolution. |
| future apps/web | Consumes the whole web control plane column: shared team read/manage surface, team recommendation queue, and backend-backed state presentation. The future app builds within that scope. |

BOS7 places these responsibilities. The named downstream phases design their own contracts and implementation details.

## Requirement Coverage

This document satisfies BOS-PROD-04: Voss defines what belongs in desktop ADE, web control plane, backend services, and local harness runtime.
