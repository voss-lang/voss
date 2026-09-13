---
phase: V24-ade-product-revamp-swarm-observability
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - apps/voss-app/PRODUCT.md
autonomous: true
requirements: [VADE2-01]
must_haves:
  truths:
    - "A committed product/design contract exists for apps/voss-app"
    - "The contract enumerates the IA model (8 left-portal items), success criteria, and the locked copy vocabulary"
    - "Downstream surfaces (W1-W5) can cite the vocabulary and IA from this contract without re-deriving them"
  artifacts:
    - path: "apps/voss-app/PRODUCT.md"
      provides: "Product register, primary user, IA model, success criteria, locked vocabulary; references V24-UI-SPEC.md as the visual/interaction contract"
      contains: "Swarm Map"
      min_lines: 60
  key_links:
    - from: "apps/voss-app/PRODUCT.md"
      to: ".planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md"
      via: "explicit reference"
      pattern: "V24-UI-SPEC"
---

<objective>
Write the missing product/design contract for `apps/voss-app` and lock the
copy vocabulary before any UI churn (VADE2-01). The contract names the product
register (primary user Ben, future audience developer teams), the information
architecture (the 8 left-portal items), the success criteria for the revamp,
and the exact user-facing vocabulary that every downstream surface must use.

Purpose: Without a locked vocabulary, W1-W5 surfaces would each invent their own
labels and re-expose internal terms. This plan is the single source of truth for
copy and IA that V24-02..08 cite.

Output: `apps/voss-app/PRODUCT.md` (committed), referencing the already-approved
`V24-UI-SPEC.md` as the visual/interaction contract.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-SPEC.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-CONTEXT.md
@.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md
@apps/voss-app/CONCEPT.md
@apps/voss-app/FEATURES.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write apps/voss-app/PRODUCT.md product + design contract</name>
  <files>apps/voss-app/PRODUCT.md</files>
  <read_first>
    - apps/voss-app/CONCEPT.md (existing product concept — register/tone source)
    - apps/voss-app/FEATURES.md (existing feature inventory — what already ships)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-SPEC.md (VADE2-01 acceptance, goal, boundaries)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-CONTEXT.md (D-08..D-11 vocabulary decisions)
    - .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md (§Copywriting Contract — the canonical vocabulary table to mirror)
  </read_first>
  <action>
    Create `apps/voss-app/PRODUCT.md` as the V24 product/design contract. It MUST contain
    these labeled sections:
    1. "Product Register" — default register = product; primary user = Ben; future audience =
       developer teams licensing controlled agent work. Product thesis (from ROADMAP §V24):
       "Terminals are where work runs. Voss is where agent work becomes scoped, observable,
       reviewable, and trustworthy."
    2. "Information Architecture" — the left-portal navigation model with all 8 items in order:
       Overview, Tasks, Agents, Swarm Map, Review, Context, Memory, Settings. State which 4 are
       NEW product surfaces (Overview/Tasks/Agents/Swarm Map) and which 4 wire to existing
       V14/panels as-is (Review/Context/Memory/Settings). State the spatial model: left portal is
       navigation; the terminal grid is the persistent canvas via canvas-swap (cite D-01).
    3. "Success Criteria" — copy the falsifiable bars from V24-SPEC §Acceptance Criteria, plus
       the two hard-fails from the SPEC Interview Log: raw internal labels in default chrome =
       failure; presets-as-navigation = failure.
    4. "Locked Vocabulary" — a table mirroring V24-UI-SPEC §Copywriting Contract for the
       load-bearing terms ONLY: top-level unit = "Task" (portal item "Tasks", NOT "Runs", per D-08);
       observability surface = "Swarm Map" (D-10); safety modes = "Read only" / "Can edit" /
       "Autopilot" (retire Plan/Edit/Auto, per D-11); board work-items inside a Task = "steps"/"cards",
       never "tasks" (D-09); composer CTA = "Create Task"; internal code identifiers `runId`/`RunData`/
       `currentRunId` are retained in code only and NEVER shown (D-09). Cite each decision ID inline.
    5. "Visual & Interaction Contract" — a one-line pointer stating the authoritative visual/interaction
       spec is `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md` (do NOT
       duplicate token tables; reference it). The string "V24-UI-SPEC" MUST appear.
    Use prose + tables only — this is a documentation artifact, no code. Keep it product-coherent and
    citable; downstream plans reference it by section name.
  </action>
  <verify>
    <automated>cd apps/voss-app && test -f PRODUCT.md && grep -q "Swarm Map" PRODUCT.md && grep -q "Read only" PRODUCT.md && grep -q "Can edit" PRODUCT.md && grep -q "Autopilot" PRODUCT.md && grep -q "Create Task" PRODUCT.md && grep -q "V24-UI-SPEC" PRODUCT.md && grep -qi "steps" PRODUCT.md && echo CONTRACT_OK</automated>
  </verify>
  <acceptance_criteria>
    - `apps/voss-app/PRODUCT.md` exists and is at least 60 lines.
    - File contains all five labeled sections: Product Register, Information Architecture,
      Success Criteria, Locked Vocabulary, Visual & Interaction Contract.
    - The Locked Vocabulary section names: Task, Tasks (not Runs), Swarm Map, Read only, Can edit,
      Autopilot, steps/cards, Create Task — and states `runId`/`RunData` are internal-only.
    - Each vocabulary entry cites its decision ID (D-08..D-11) or VADE2-01.
    - The IA section lists all 8 portal items in order and marks the 4 new vs 4 reused surfaces.
    - The contract references `V24-UI-SPEC` as the visual/interaction source of truth.
    - The grep gate command above prints `CONTRACT_OK`.
  </acceptance_criteria>
  <done>PRODUCT.md committed with IA, success criteria, and locked vocabulary; downstream plans can cite it.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| n/a (documentation-only plan) | This plan creates a Markdown contract. No untrusted input, no code, no runtime surface. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V24-01-I | Information Disclosure | PRODUCT.md content | accept | Contract documents product vocabulary only; contains no secrets, tokens, or PII. Author MUST NOT paste credentials or run data into the doc. |
| T-V24-01-T | Tampering | npm/pip/cargo installs | mitigate | No package installs in this plan. RESEARCH §Package Legitimacy Audit confirms zero new deps for V24-01. N/A by construction. |

No HIGH-severity threats. Documentation-only plan; threat surface is effectively nil.
</threat_model>

<verification>
- `apps/voss-app/PRODUCT.md` exists, committed, and passes the grep gate.
- Vocabulary in PRODUCT.md is byte-consistent with V24-UI-SPEC §Copywriting Contract for the load-bearing terms.
</verification>

<success_criteria>
The product/design contract is committed, enumerates the IA + success criteria + locked vocabulary,
and is citable by V24-02..08 (VADE2-01 acceptance met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-01-SUMMARY.md` when done.
</output>
