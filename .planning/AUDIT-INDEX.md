# AUDIT-INDEX.md — Voss Planning Corpus Audit

Two-axis classification of every doc and track in the `.planning/` corpus before any archive, move, or delete. Built by phase BOS1 per decisions D-01..D-05. This index is the gate that satisfies PROJECT.md's "no blind deletion" out-of-scope rule.

## Taxonomy

Every entry is classified on two independent axes (D-02). Each data row carries exactly one enum value per axis — both cells non-empty.

- **Axis 1 — Status:** `active` | `historical` | `superseded` | `archive-candidate`
- **Axis 2 — BOS-relationship:** `substrate` | `dependency` | `historical-context` | `out-of-scope`

Supersession pointers mirror existing markers in STATE.md / ROADMAP.md (D-02 specifics). No new supersessions are invented here — "—" where none is recorded.

## Per-file audit

| doc / track | status | BOS-relationship | reason | supersedes / superseded-by |
|---|---|---|---|---|

### Loose root plans

| doc / track | status | BOS-relationship | reason | supersedes / superseded-by |
|---|---|---|---|---|
| ADE-REDESIGN.md | active | dependency | Implementation plan for A12 (voss-app ADE Visual Redesign); A12 still TBD in ROADMAP, left sidebar + warm palette design not yet shipped | — |
| CODEX-OAUTH-PLAN.md | active | dependency | Reverse-engineering plan for ChatGPT-sub Codex OAuth wire format; harness provider auth path still referenced by v1.1 baseline | — |
| Feature Plan.md | active | dependency | Design doc for F-track (F1–F6 v1 substrate features); F2/F4/F5 still ready-to-execute, F3 complete | — |
| HARNESS-PLAN.md | historical | dependency | v0.1 harness plan / M-track design reference; M0–M4 shipped, M6–M8 still ready — harness remains the BOS substrate | — |
| HYBRID-REFACTOR-PLAN.md | active | substrate | Live client/server refactor contract (H0–H7); owns the harness server + SSE plane BOS consumes | supersedes RUST-PORT-PLAN.md |
| MCP-PLAN.md | active | dependency | Explainer for M12 (MCP Bridge — expose harness as MCP server); M12 still TBD in ROADMAP | — |
| OPENCODE-TUI-ADAPTER-CONTRACT.md | archive-candidate | historical-context | OpenCode TUI fork feasibility gate; paused — Textual TUI confirmed intact, fork deemed possibly unnecessary | — |
| ORCHESTRATION-PLAN.md | superseded | historical-context | O1–O6 caged-autonomous-team design; whole O-track ⊘ superseded by V-track (banner in file line 1) | superseded by V-track (docs/ORCHESTRATION_LAYERS.md) |
| PROTOCOL.md | active | substrate | Live harness wire contract (v1, locked for H1–H6); V13.1 contracts derive from it; BOS event export builds on this | — |
| RUST-PORT-PLAN.md | superseded | historical-context | Subprocess-bridge Rust port (R1–R9); replaced by hybrid client/server approach that keeps auth/providers in Python | superseded by HYBRID-REFACTOR-PLAN.md |
| TUI-FIXES-HANDOFF.md | archive-candidate | historical-context | One-shot handoff for Textual TUI slash-palette + perf fixes; targeted fixes, likely applied, no longer a live plan | — |
| VOSS-USERSPACE-OS-HANDOFF.md | archive-candidate | out-of-scope | Exploratory "Voss OS" thread; file self-declares "not a committed roadmap phase, no implementation started" | — |

### seeds/

| doc / track | status | BOS-relationship | reason | supersedes / superseded-by |
|---|---|---|---|---|
| seeds/agent-capability-surface.md | historical | dependency | Seed for M10–M15 capability buildout; M10/M13/M15 shipped, M11/M12/M14 still ready — informed M-track substrate | — |
| seeds/managed-docs-generation.md | historical | dependency | Seed for V16 managed docs/prompt generation; V16 ✅ COMPLETE 2026-06-10, seed consumed | — |
| seeds/project-memory-voss-md.md | active | dependency | Seed for M8 (Project Memory — VOSS.md + cross-session recall); M8 still "Ready to execute" in STATE | — |
| seeds/SEED-001-coordination-bus.md | active | dependency | Planted BOS context — reframed as future external-agent CLI verbs over the existing server/SSE plane; PROJECT.md carry-forward stance keeps it as BOS11 input | — |
| seeds/SEED-002-codebase-rag-tiered-indexing.md | historical | dependency | Seed for codebase RAG + tiered model routing; routed to V19 (✅ COMPLETE) + V21/V22 stretch — V-track substrate | — |
| seeds/tui-shell-textual.md | active | dependency | Seed for M9 (TUI Shell — Textual); M9 still "Ready to execute (7 plans)" in STATE | — |

### notes/

| doc / track | status | BOS-relationship | reason | supersedes / superseded-by |
|---|---|---|---|---|
| notes/daily-driver-punch-list.md | historical | dependency | Source of T-phases (T1–T8 gap-closure); T1–T6/T8 implemented per 2026-06-02 update — harness interaction-depth substrate | — |
| notes/e-track-eval-decisions.md | active | dependency | Locked decisions for E-track (internal proof suite); E3 ✅ complete, E1/E4 in progress, E2/E5 TBD — BOS validation surface | — |
| notes/plan-grid-drag-rearrange.md | active | dependency | Ready-to-implement plan for voss-app pane drag-rearrange (A3 grid substrate); A3 shipped, this feature still pending | — |
| notes/seed-structured-pane-rendering.md | historical | dependency | Seed for V15 structured pane rendering; V15 ✅ COMPLETE — seed consumed, V-track substrate | — |
| notes/voss-agent-unfair-advantage.md | active | historical-context | Strategic thesis framing Voss's language primitives as auditable agent features; informs V-track product identity, not a runtime substrate | — |

### docs/

| doc / track | status | BOS-relationship | reason | supersedes / superseded-by |
|---|---|---|---|---|
| docs/AST-JSON-CONTRACT.md | historical | historical-context | JSON contract for the compiler AST serializer; numbered 01–07 compiler core shipped — language-layer reference, not BOS substrate | — |
| docs/ORCHESTRATION_LAYERS.md | active | dependency | Canonical PRD + architecture doc for the V-track (V0–V12); V-track is the active agent-org runtime BOS consumes as event source | supersedes ORCHESTRATION-PLAN.md |

## Track rollup (.planning/phases/)

One row per phase-track prefix (91 phase dirs rolled up to 10 tracks). Status sourced from STATE.md phase rows; BOS-relationship sourced from ROADMAP + PROJECT carry-forward stance.

| doc / track | status | BOS-relationship | reason | supersedes / superseded-by |
|---|---|---|---|---|
| 01-07 (numbered compiler track) | historical | historical-context | Shipped language core: runtime library, parser/grammar, semantic analysis, codegen, CLI packaging, examples, rust-port — BOS sits above, not on the compiler | — |
| M | active | dependency | Harness track (M0–M15); M0–M4/M15 shipped, M6–M8/M11/M12/M14 still ready — harness is the BOS substrate; M13 absorbed, M5 eval scope superseded | M13 → V8 (absorbed); M5 → E1/E2 |
| A | active | substrate | voss-app desktop ADE track (A1–A13); A1–A3 complete, A4/A9/A10 ready, A6–A8/A12 TBD — desktop is the local ADE/execution node BOS10 defines | A13-02..06 → V25 (A13-01 file schema retained as audit layer) |
| V | active | substrate | Agent Engineering Organization Layer (V0–V25); V5/V7/V8/V10/V11/V13.3/V13.4/V14 ✅ complete, V2/V12/V15/V19/V22/V23 planned/ready — org runtime BOS consumes as event source | absorbs O1-O6 (O1→V4, O2→V3, O3→V5, O4→V6, O5→V7, O6→V9); M13 → V8 |
| O | superseded | historical-context | Caged Autonomous Eng Team (O1–O6); whole track ⊘ superseded by V-track — retained as historical design reference | O1→V4, O2→V3, O3→V5, O4→V6, O5→V7, O6→V9 (superseded by V-track) |
| F | active | dependency | v1 Layer 2 substrate features (F1–F6); F3 complete, F1/F2/F4/F5 ready — ADE/harness substrate features BOS depends on | — |
| E | active | dependency | Internal Proof Suite (E1–E5); E3 ✅ complete, E1 planned, E4 in progress, E2/E5 TBD — on-demand e2e/eval proving the product, BOS validation surface | absorbs M5 eval scope (E1/E2) |
| T | historical | historical-context | Gap-closure track (T1–T8); T1–T6/T8 implemented/complete, T7 TBD — daily-driver table stakes, mostly landed | — |
| BOS | active | substrate | Behavioral OS Foundation (BOS0–BOS18); BOS0 ✅ complete, BOS1 in progress — the active milestone this audit serves | — |
| 999.x | archive-candidate | out-of-scope | Deferred voss-app spike phases (999.1 agents-launcher, 999.2 pane-resize-keybind); not committed, parked — outside the active milestone | — |

## Appendix: stray planning docs outside .planning/

These are NOT first-class index rows — appendix-only, noted per D-01. Status + relationship annotated for awareness; no archive action is implied.

- `.vscode/voss_v_0_1_scope_lock.md` — historical, dependency. v0.1 scope-lock source of truth (M0 source per ROADMAP §M0). Retained as the v0.1 reference; M0 shipped.
- `PRD.md` (repo root) — historical, historical-context. Original language PRD for `.voss`; file self-declares ⊘ SUPERSEDED, points to `.planning/docs/ORCHESTRATION_LAYERS.md` as canonical.
- `README.md` (repo root) — active, historical-context. Project readme / install path; not a planning doc, included only because the repo-root scan surfaced it. Not subject to archive action.
- `SECURITY_AUDIT_REPORT.md` (repo root) — historical, historical-context. Snitch quick-scan report (2026-06-17); one-off audit artifact, not a planning doc.

## Requirement verification

- **BOS-PLAN-01** — VERIFIED. `BOS` phase prefixes already exist in ROADMAP.md: the BOS0 and BOS1 rows appear in the phase table (lines 15–16), and the dedicated `## BOS-prefixed phases: Behavioral OS Foundation` section (lines 113–171) defines BOS0–BOS18 with deliverables. No re-introduction needed — recorded as done.
- **BOS-PLAN-03** — VERIFIED-adequate. The BOS0–BOS18 split is recorded in ROADMAP.md as an 18-row BOS table (lines 151–171, "BOS phase | Deliverable | Notes") plus per-phase rows in the phase-order table (lines 15–33). The split separates product thesis, stack architecture, data modeling (BOS3–BOS5), governance (BOS6), surfaces/integrations (BOS7–BOS12), policy/eval/RL (BOS13–BOS16), behavioral guardrails (BOS17), and PM-suite expansion (BOS18) into distinct phases. Adequate — no re-split performed.