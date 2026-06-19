# Phase BOS7: Web Control Plane Boundary - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

BOS7 produces the **web-vs-desktop responsibility map** (BOS-PROD-04): a docs-first
contract defining what belongs in each of four surfaces — **desktop ADE**, **web
control plane**, **backend services**, and **local harness runtime**.

This phase decides WHERE capabilities live (the partition), not HOW any surface is
built. It does NOT: build a web app (web is "future, if built"); design the
recommendation UI itself (BOS9 — BOS7 only places it); define governance/privacy
policy detail (BOS6 — BOS7 places the privacy boundary, BOS6 sets the rules);
specify the event schema (BOS3) or decision ledger (BOS4); define accounts/auth/
multi-tenancy (out-of-scope this milestone). No code.
</domain>

<decisions>
## Implementation Decisions

### Carried Forward (already locked — not re-decided here)
- High-level split (PROJECT.md + BOS0 D-04): **desktop = local execution/ADE node; web = shared team state + dataset/recommendation review.**
- BOS2 architecture: monorepo `apps/web` + `services/*` in one tree; **SQLite (local) → Postgres (shared) one-directional sync**; DuckDB for analytics; V13.1 contracts as drift-gated source of truth.
- V24 already shipped the **desktop** portal (PortalShell: Overview/Runs/Agents/Swarm Map/Review/Context/Memory/Settings).

### 4-Way Surface Partition
- **D-01:** **Thin desktop, backend owns projection.**
  - **Local harness runtime** = execution + raw event emission (the SOURCE; the daemon/loopback server). Job ends at emitting events + serving local clients.
  - **Desktop ADE** = local-first UI, inspect/review of the user's OWN runs, and acts as a worker node for shared BOS state (per BOS10). Does NOT run team projection/analytics.
  - **Backend services** = ingestion/projection (BOS3 event projection, BOS12 integration ingestion), the event ledger (Postgres), decision-ledger store (BOS4), and policy serving (BOS13+).
  - **Web control plane** = shared team read/manage surface over the backend (no business logic of its own beyond presentation/workflow).
  - Flow: **source (harness) → backend (projection/store) → web (team surface)**; desktop reads its own slice locally.
  - Rejected: fat-desktop (duplicates backend projection logic, hard team aggregation); fat-web/terminal-only-desktop (loses local-first review + worker-node value).

### Data / Sync + Privacy Boundary
- **D-02:** **Metadata/decisions sync up; content stays local.**
  - Local-only by default. Only **structured event metadata + decision records + outcome labels** sync up to shared Postgres.
  - **Raw code, prompts, and file contents NEVER leave the desktop.** Only structured/derived signals cross the desktop→server boundary.
  - This crossing IS the privacy boundary; it implements the no-surveillance / trust stance and feeds BOS6 governance rules (BOS7 places the boundary, BOS6 sets the policy).
  - Rejected: full-sync-filter-at-web (weak privacy guarantee); manual-export-only (breaks the live team-control-plane value).

### Review-Surface Placement
- **D-03:** **Review on BOTH desktop and web, scoped differently, one contract.**
  - **Desktop Review tab (V24)** = the user's OWN runs / individual local review.
  - **Web Review** = TEAM-level queue of shared recommendations.
  - A **single BOS9 output contract** renders to both targets (desktop = my-scope, web = team-scope). No logic duplication.
  - Rejected: web-only (no offline/local recommendation review); desktop-only (contradicts PROJECT "web = recommendation review surface").

### Offline / Connectivity + Identity
- **D-04:** **Desktop standalone; web additive; identity seam reserved.**
  - Desktop works **fully offline / standalone** (today's reality preserved). Web + backend are **ADDITIVE** — when absent, desktop runs; the only loss is team sync.
  - **Identity:** local harness keeps its **ephemeral loopback bearer token** (PROTOCOL.md). Shared web identity / accounts are a **SEPARATE future layer** (accounts/auth/multi-tenant are out-of-scope this milestone) — BOS7 only **reserves the boundary seam** where that layer will attach.
  - Rejected: backend-required-for-full-function (breaks local-first/offline); define-accounts-now (violates milestone out-of-scope).

### Claude's Discretion
- The exact format of the responsibility map (recommend: a capability × surface matrix + a flow diagram + prose rationale).
- Capability enumeration granularity (which specific capabilities get rows).
- Where to draw secondary lines that don't change the four decisions above.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition & requirements
- `.planning/ROADMAP.md` BOS phase table (~line 22) + "BOS-prefixed phases" §(~113-149) — BOS7 goal, deliverable ("Web-vs-desktop responsibility map"), build order (BOS7-12 = surfaces/integrations).
- `.planning/REQUIREMENTS.md` line 14 (BOS-PROD-04) + line 248 (coverage). Note line 41 (monorepo stack evolution) is BOS2's, not BOS7's.

### Locked upstream context (carry-forward — DO read, do not contradict)
- `.planning/PROJECT.md` — "Desktop/Web split" constraint (line 68), "Web is the shared control plane" Key Decision (line 78), Out-of-Scope (no accounts/multi-tenant/billing).
- `.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-CONTEXT.md` — D-03/D-04 (EM buyer, devs already on ADE; web buys the control plane on top).
- `.planning/phases/BOS2-monorepo-and-stack-architecture/BOS2-ARCHITECTURE.md` (if present from BOS2 plan) — apps/web + services/* tree, SQLite→Postgres one-directional sync, DuckDB. The data-tier mechanics D-02 sits on top of.
- `.planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md` — derived analytics schema; projection placement (D-01 puts projection in backend services). PROTOCOL.md = harness wire contract (ephemeral loopback token referenced by D-04).
- `.planning/PROTOCOL.md` — local harness auth (ephemeral loopback bearer token); the identity seam D-04 reserves.

### Forward dependencies BOS7 constrains (place, don't design)
- BOS6 governance (privacy/trust) — D-02 boundary feeds it.
- BOS9 recommendation review surface — D-03 placement + single-contract constraint feeds it.
- BOS10 desktop worker-node contract — D-01 "desktop as worker node" feeds it.
- BOS12 external integration ingestion — D-01 puts ingestion in backend services.

### Existing desktop surface (reality to preserve)
- `apps/voss-app` PortalShell (V24) — the existing desktop portal + Review tab; D-03 scopes its review to "my runs."
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `apps/voss-app` PortalShell (V24) — existing desktop control surface; D-03 builds on its Review tab.
- `voss/harness/server/` (loopback daemon + SSE + ephemeral token, PROTOCOL.md) — the "local harness runtime" surface in D-01; D-04 preserves its standalone offline mode + token.
- V25 server-native swarm runtime + BOS10 desktop worker-node direction — supports "desktop as worker node" (D-01).

### Established Patterns
- Docs-first BOS track: contract before code. BOS7 artifact = responsibility map (matrix + flow + rationale).
- Local-first + additive-server (PROJECT) — D-04 codifies it as a boundary rule.
- Privacy-by-placement: structured-signal-only crossing (D-02) rather than policy bolted on later.

### Integration Points
- BOS7 is a placement contract: it constrains BOS6 (privacy rules), BOS9 (review UI), BOS10 (worker node), BOS12 (ingestion), and the future `apps/web` build. It introduces no runtime itself.
</code_context>

<specifics>
## Specific Ideas

- The four-surface map should be a single capability × surface matrix so downstream phases can look up "where does X live" unambiguously.
- "Content never leaves the desktop" (D-02) is the load-bearing privacy claim — it must be stated as an invariant, not a default.
- BOS7 reserves an identity seam but does NOT design accounts — keep the out-of-scope line explicit so a future web-auth phase has a clean attach point.
</specifics>

<deferred>
## Deferred Ideas

- Accounts / auth / shared identity / multi-tenancy — future web-auth phase (out-of-scope this milestone; D-04 only reserves the seam).
- Actually building `apps/web` — future implementation phase; BOS7 is the boundary spec only.
- Recommendation review UI design — BOS9.
- Governance/privacy policy detail (who-sees-what rules) — BOS6.
- Desktop worker-node protocol mechanics — BOS10.
- External integration ingestion mechanics — BOS12.
- Sync conflict/merge semantics beyond "one-directional SQLite→Postgres" — BOS2 owns the mechanism; revisit if bidirectional ever needed.

### Reviewed Todos (not folded)
None — no todo cross-reference matches surfaced for this phase.

</deferred>

---

*Phase: BOS7-web-control-plane-boundary*
*Context gathered: 2026-06-18*
