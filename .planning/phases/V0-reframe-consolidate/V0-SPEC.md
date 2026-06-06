# Phase V0: Reframe & Consolidate — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.151 (gate: ≤ 0.20)
**Requirements:** 5 locked

## Goal

Reframe Voss's canonical identity docs so the lead positioning is "Voss is an **agent engineering organization layer**, with the `.voss` language + harness as its substrate" — promoting `docs/ORCHESTRATION_LAYERS.md` to the canonical PRD, naming the six primitives, mapping every roadmap track to them, and adding a glossary — so a new contributor can trace identity → primitives → phases from one source. Docs-only; no runtime change; the public README/npm brand is untouched.

## Background

The org-layer identity, the six primitives, and the L0–L4 recursion exist **only** in `docs/ORCHESTRATION_LAYERS.md` (the PRD added 2026-06-05). The three other identity docs lead with the older framing:
- `PRD.md` (repo root, 27KB) — "Voss Language — PRD", *"AI-native programming language that compiles to Python."*
- `README.md` — *"A language for confidence-aware, budget-bounded LLM programs"* (npm `@vosslang` brand).
- `.planning/PROJECT.md` — *"AI-native coding harness and programming language."*

No `docs/agent-org-architecture.md` exists; no terminology glossary exists in any identity doc; no phase→primitive map exists. `ORCHESTRATION_LAYERS.md` already carries the six-primitive table (§4.1), the L0–L4 recursion table (§4.2), and a roadmap-status banner, but lacks an explicit glossary and a full per-track phase→primitive map.

**Locked direction (interview):** ORCHESTRATION_LAYERS.md becomes the canonical PRD (old PRD.md archived-as-superseded); the org-layer identity *layers above* the language+harness substrate (brand preserved); ORCHESTRATION_LAYERS.md IS the architecture doc (no new duplicate file); glossary + phase→primitive map both land in it; README/npm stays out of scope.

## Requirements

1. **Canonical PRD promotion**: `docs/ORCHESTRATION_LAYERS.md` is designated the canonical PRD + architecture doc; the old `PRD.md` is archived-as-superseded.
   - Current: `PRD.md` (root) is the de-facto PRD and frames Voss as a language; `ORCHESTRATION_LAYERS.md` is one design doc among several with no canonical status.
   - Target: `ORCHESTRATION_LAYERS.md` header states it is the canonical PRD + architecture doc; `PRD.md` carries a top SUPERSEDED banner linking to it and stating it is retained as the historical language-PRD.
   - Acceptance: `ORCHESTRATION_LAYERS.md` contains a line declaring canonical-PRD status; `PRD.md` first screen contains a "⊘ SUPERSEDED" banner with a relative link to `docs/ORCHESTRATION_LAYERS.md`.

2. **PROJECT.md identity reframe**: the planning entry doc leads with the org-layer identity atop the named substrate.
   - Current: `.planning/PROJECT.md` opens "Voss is an AI-native coding harness and programming language…".
   - Target: the lead paragraph names "agent engineering organization layer" as the primary framing AND explicitly names the `.voss` language + harness as the substrate beneath it (brand not erased).
   - Acceptance: PROJECT.md lead contains the phrase "agent engineering organization" AND retains a reference to both `.voss` language and harness as substrate.

3. **Six primitives defined**: the canonical PRD names and defines all six primitives.
   - Current: `ORCHESTRATION_LAYERS.md §4.1` lists the six primitives in a table (capabilities, principles, orchestration, roles, memory, verification).
   - Target: that section is confirmed/normalized so each of the six has a one-line product meaning AND a named implementation surface.
   - Acceptance: the canonical PRD lists exactly these six — capabilities, principles, orchestration, roles, memory, verification — each with a meaning and an implementation-surface cell.

4. **Phase→primitive map**: every roadmap track maps to at least one primitive, in the canonical PRD.
   - Current: no doc maps M/T/A/O/F/V phases (or tracks) onto the six primitives.
   - Target: a phase→primitive map section in `ORCHESTRATION_LAYERS.md` tagging every roadmap track prefix (M, T, A, O, F, V) to ≥1 of the six primitives.
   - Acceptance: the map covers all six track prefixes (M, T, A, O, F, V); each row references ≥1 of the six primitive names; superseded O-track noted as folded into V.

5. **Terminology glossary**: the canonical PRD defines the org-layer vocabulary.
   - Current: no glossary in any identity doc; terms (EM, card, board, gate, verifier…) used without a single definition source.
   - Target: a glossary section in `ORCHESTRATION_LAYERS.md` defining the core terms.
   - Acceptance: glossary defines at least these 11 terms — capability, role, agent, subagent, EM, card, board, gate, verifier, reviewer, audit.

## Boundaries

**In scope:**
- Designate `docs/ORCHESTRATION_LAYERS.md` as canonical PRD + architecture doc (header line).
- Add to `ORCHESTRATION_LAYERS.md`: a glossary section and a phase→primitive map section; normalize the six-primitives section.
- Reframe `.planning/PROJECT.md` lead to org-layer-atop-substrate.
- Add a SUPERSEDED banner to root `PRD.md` pointing to the canonical PRD.
- A "why this is not a rigid pipeline" framing present in the canonical PRD (the §1 thesis already gestures at this; confirm/strengthen).

**Out of scope:**
- `README.md` and npm `@vosslang` package copy — public rebrand is a separate, higher-stakes decision (deferred).
- Any runtime/code change, CLI surface, or `.voss` grammar — V0 is docs/identity only (grammar work is V10).
- Creating a new `docs/agent-org-architecture.md` — `ORCHESTRATION_LAYERS.md` IS the architecture doc (no duplicate).
- Rewriting M/O/F/A phase *detail* content or requirements — only the cross-track primitive map is added, not phase rewrites.
- Marketing/site copy beyond the planning + PRD docs.

## Constraints

- Docs-only: the phase diff must contain no source-code, CLI, or grammar changes.
- Reuse, don't recreate: the six-primitive and L0–L4 tables already in `ORCHESTRATION_LAYERS.md` are the source — V0 normalizes/links them, it does not author parallel copies elsewhere.
- Single source of truth: glossary + phase→primitive map live in the canonical PRD only; other docs link to it rather than duplicating.
- Brand preservation: the `.voss` language and harness identity must remain present (named as substrate), not deleted, in every reframed doc.

## Acceptance Criteria

- [ ] `docs/ORCHESTRATION_LAYERS.md` declares itself the canonical PRD + architecture doc.
- [ ] Root `PRD.md` carries a "⊘ SUPERSEDED" banner on its first screen linking to `docs/ORCHESTRATION_LAYERS.md`.
- [ ] `.planning/PROJECT.md` lead contains "agent engineering organization" AND still names `.voss` language + harness as substrate.
- [ ] Canonical PRD lists all six primitives (capabilities, principles, orchestration, roles, memory, verification), each with meaning + implementation surface.
- [ ] Canonical PRD contains a phase→primitive map covering every track prefix (M, T, A, O, F, V), each mapped to ≥1 primitive.
- [ ] Canonical PRD contains a glossary defining ≥ the 11 terms: capability, role, agent, subagent, EM, card, board, gate, verifier, reviewer, audit.
- [ ] Canonical PRD contains a "why this is not a rigid pipeline" section/framing.
- [ ] `README.md` and npm package copy are unchanged in the phase diff (scope guard).
- [ ] No non-documentation files appear in the phase diff (scope guard).

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Canonical-PRD promotion + reframe target locked              |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | README/npm + new arch-doc + code explicitly out of scope     |
| Constraint Clarity | 0.75  | 0.65 | ✓      | Docs-only, reuse-not-recreate, brand-preserve, single-source |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | Soft "<15min" replaced with doc-presence checks              |
| **Ambiguity**      | 0.151 | ≤0.20| ✓      |                                                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                        |
|-------|-------------------|--------------------------------------------------|-----------------------------------------------------------------------|
| 1     | Researcher        | Which doc is the canonical PRD (PRD.md vs ORCH)? | Promote `ORCHESTRATION_LAYERS.md`; archive `PRD.md` as superseded      |
| 1     | Researcher        | Org-layer vs the shipped language/harness brand? | Org-layer leads *atop* the language+harness substrate; brand preserved |
| 1     | Researcher        | New arch doc vs existing ORCHESTRATION_LAYERS?    | `ORCHESTRATION_LAYERS.md` IS the architecture doc; no duplicate        |
| 2     | Researcher/Simplifier | Where do glossary (P0-05) + phase map (P0-04) live? | Both into the canonical PRD (single source)                      |
| 2     | Boundary Keeper   | Is public README/npm in scope?                   | Internal docs only; README/npm untouched (deferred)                   |
| 2     | Failure Analyst   | Make "<15min contributor" falsifiable?           | Replace with concrete doc-presence checks                             |

---

*Phase: V0-reframe-consolidate*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V0 — implementation decisions (exact section structure, banner wording, glossary entries)*
