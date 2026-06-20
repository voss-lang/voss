# Phase BOS1: Planning Audit and Archive Map - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

BOS1 inventories the accumulated Voss planning corpus and produces a single
**audit index** that classifies each doc/track before any archive, supersession,
or deletion. Planning-hygiene phases may touch files: after the
index exists and per-item approval is given, BOS1 archives and deletes
archive-candidate docs.

Covers BOS-PLAN-01..04:
- 01: BOS phase prefixes introduced (already done in ROADMAP — verify/record).
- 02: stale docs audited + indexed before any archive/delete/supersede.
- 03: roadmap split into enough phases (verify BOS1-BOS18 split is recorded, not re-split).
- 04: existing Voss tracks mapped into BOS as substrate / dependency / historical / out-of-scope.

This phase does NOT: design data schemas (BOS3-5), governance (BOS6), or any
runtime/code. It is a planning-hygiene + track-mapping phase over `.planning/`.
</domain>

<decisions>
## Implementation Decisions

### Audit Scope / Inventory Net
- **D-01:** Audit net =
  - **Per-file**: every loose `.md` plan at `.planning/` root (ADE-REDESIGN, CODEX-OAUTH-PLAN, Feature Plan, HARNESS-PLAN, HYBRID-REFACTOR-PLAN, MCP-PLAN, OPENCODE-TUI-ADAPTER-CONTRACT, ORCHESTRATION-PLAN, PROTOCOL, RUST-PORT-PLAN, TUI-FIXES-HANDOFF, VOSS-USERSPACE-OS-HANDOFF), plus `.planning/seeds/*`, `.planning/notes/*`, `.planning/docs/*`.
  - **Track-level (not per-file)**: the 91 dirs under `.planning/phases/` are rolled up by track (numbered 01-07, M, A, V, O, F, E, T, BOS, 999.x) — each track gets one row, not each phase file. Phases are already indexed in ROADMAP.md/STATE.md, so per-file re-audit is redundant.
  - **Appendix**: stray planning docs OUTSIDE `.planning/` (e.g. `.vscode/voss_v_0_1_scope_lock.md`, repo-root design docs) flagged in an appendix section — noted, not first-class index rows.
- Rejected: loose-root-only (too narrow — misses track mapping for BOS-PLAN-04); exhaustive per-file over all 91 dirs (heavy, redundant with ROADMAP/STATE).

### Classification Taxonomy
- **D-02:** **Two independent axes**, every indexed entry gets both:
  - **Axis 1 — Status** (covers BOS-PLAN-02): `active` | `historical` | `superseded` | `archive-candidate`.
  - **Axis 2 — BOS-relationship** (covers BOS-PLAN-04): `substrate` | `dependency` | `historical-context` | `out-of-scope`.
- Rationale: PLAN-02 (lifecycle status) and PLAN-04 (how a track relates to BOS) are orthogonal questions — a track can be `superseded` in status yet `historical-context` for BOS. Keeping them separate prevents a lossy merged enum.
- Rejected: single 4-label status with PLAN-04 as a free-text note; one merged enum.

### Index Format + Location
- **D-03:** Single human-readable **`AUDIT-INDEX.md` at `.planning/` root**.
  Markdown table, columns: `doc / track` | `status` (axis 1) | `BOS-relationship` (axis 2) | `reason` | `supersedes / superseded-by` pointer.
- JSON sidecar **deferred** — add only if later tooling needs it (noted in Deferred).
- Rejected: JSON-now sidecar; placing index inside `.planning/archive/`.

### Archive Action Boundary
- **D-04:** BOS1 goes **all the way to cleanup**: classify → move → delete, BUT:
  - **Index-first**: no move/delete until `AUDIT-INDEX.md` exists and is reviewed. This is exactly what makes it *not* "blind deletion" (PROJECT.md out-of-scope bars deletion *without* an audit index — the index satisfies that gate).
  - **Per-item human approval**: every move and especially every delete is approved individually by Ben before execution. No batch auto-delete. Honors global git-safety rule (no git write actions without explicit confirmation).
  - **Archive destination**: `archive-candidate` docs that are kept-but-archived move to `.planning/archive/` (already exists, empty). Move preferred over delete; delete reserved for clearly-dead docs with explicit per-item sign-off.
- **D-05:** Execution ordering inside the phase: (1) build full index, (2) Ben reviews/approves classifications, (3) execute approved moves to `.planning/archive/`, (4) execute approved deletes. Steps 3-4 are gated git/file writes.

### Claude's Discretion
- Exact `AUDIT-INDEX.md` table column ordering and any grouping/section headers.
- How tracks are grouped/labeled in the rollup (by prefix is the obvious cut).
- Wording of `reason` cells and supersession-pointer notation.
- Appendix structure for external stray docs.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition & requirements
- `.planning/ROADMAP.md` §"BOS-prefixed phases: Behavioral OS Implementation Track" + BOS phase table — phase goals, deliverables, and build order.
- `.planning/REQUIREMENTS.md` lines 18-21 (BOS-PLAN-01..04) + line 242 (coverage row) — the four requirements this phase closes.
- `.planning/PROJECT.md` — Out-of-Scope bullet "Deleting old planning docs without an audit/archive index" (the constraint D-04 satisfies) + carry-forward stance on historical V/M/A/F/E-track context.

### Prior phase context
- `.planning/phases/BOS1-planning-audit-and-archive-map/BOS1-PRODUCT-CONTEXT.md` — product framing tracks are mapped against in axis 2.

### Audit target corpus (the thing being inventoried)
- `.planning/STATE.md` — authoritative per-phase status table + recent activity; primary source for track rollup status (axis 1). NOTE: large file (~317 lines / 77k tokens) — read the Phase Status table and headers, don't load whole.
- `.planning/` root loose plans (12 files, see D-01) — per-file audit subjects.
- `.planning/seeds/`, `.planning/notes/`, `.planning/docs/` — per-file audit subjects.
- `.planning/phases/` (91 dirs) — track-level rollup subjects.
- `.planning/archive/` — destination for archive-candidate moves (currently empty).
- External appendix: `.vscode/voss_v_0_1_scope_lock.md` and any repo-root design docs.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None (docs/planning-hygiene phase, no source code touched).
- ROADMAP.md and STATE.md already encode per-phase status + supersession chains (O1-O6→V-track, M13→V8, M5→E-track, O-track→V-track) — reuse these as the status source rather than re-deriving.

### Established Patterns
- Docs-first BOS track: each BOS phase emits a contract/artifact before code. BOS1's artifact is `AUDIT-INDEX.md`.
- Supersession is already recorded inline in STATE.md phase rows (⊘ SUPERSEDED / ABSORBED markers) — index should mirror, not invent, these pointers.

### Integration Points
- Output `AUDIT-INDEX.md` becomes the gate that later phases (and any cleanup) reference before archiving/deleting. Feeds nothing at runtime — pure planning artifact.
</code_context>

<specifics>
## Specific Ideas

- "No blind deletion" is satisfied structurally by D-04's index-first + per-item-approval gate, not by avoiding deletion entirely.
- Status axis should lean on STATE.md's existing supersession markers verbatim where they exist.
- Track rollup keys = phase prefixes already used in ROADMAP.md ("Granularity" line): numbered 01-07, M, A, V, O, F, E, T, BOS, 999.x.
</specifics>

<deferred>
## Deferred Ideas

- Machine-readable `AUDIT-INDEX.json` sidecar — only if future tooling/automation needs it (D-03).
- Actually re-splitting the roadmap (BOS-PLAN-03) — BOS1-BOS18 split exists in ROADMAP.md; BOS1 only *verifies/records* the split is adequate, does not re-architect phases.
- Cleaning up source-code dead files / non-planning artifacts — out of scope; this audit is the `.planning/` corpus only.
- Deleting historical V/M/A/F/E-track CONTEXT/SUMMARY artifacts inside phase dirs — track-level rollup classifies the track, but per-file phase-dir pruning is not in BOS1's net (D-01).

### Reviewed Todos (not folded)
None — no todo cross-reference matches surfaced for this phase.

</deferred>

---

*Phase: BOS1-planning-audit-and-archive-map*
*Context gathered: 2026-06-18*
