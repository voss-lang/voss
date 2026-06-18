---
phase: BOS0-product-thesis-icp-and-wedge
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md
autonomous: true
requirements: [BOS-PROD-01, BOS-PROD-02, BOS-PROD-03]

must_haves:
  truths:
    - "A reader can state the Behavioral OS product boundary: a team control plane over AI-assisted engineering work, NOT a generic PM clone"
    - "A reader can name the ICP: small multi-agent engineering teams (3-15 devs) already running multiple coding agents"
    - "A reader can name the economic buyer (EM/eng-lead) and the daily users (devs), and how the two are reconciled"
    - "A reader can name the first wedge (delegation: task -> agent/human) and why it is observable today via the V25 swarm assignment flow"
    - "A reader can state the external category ('control plane for AI engineering teams') and the internal north-star term ('Behavioral OS')"
    - "A reader can list what BOS is explicitly NOT (Jira/Linear/Atlassian clone; individual surveillance/ranking/leaderboards)"
    - "A reader can state the core tension (top-down EM buyer vs dev-generated data substrate) and its resolution (devs already on the Voss ADE; no new dev behavior required)"
  artifacts:
    - path: ".planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md"
      provides: "Product boundary, ICP, buyer/user split, wedge, positioning, anti-positioning, and the tension+resolution"
      contains: "## Anti-positioning"
  key_links:
    - from: "BOS0-PRODUCT-BRIEF.md wedge section"
      to: "V25 server-native swarm assignment flow (swarm.assign)"
      via: "wedge claim grounded in an existing observable event source"
      pattern: "swarm|assign|delegation"
---

<objective>
Write the Behavioral OS product brief: the single document that anchors WHO the product is for and WHAT the first wedge is. It locks the product boundary, ICP, buyer/user split, primary wedge, external/internal positioning, anti-positioning, and the core buyer-vs-substrate tension with its resolution.

Purpose: Every later BOS spec (BOS1-BOS18) inherits this framing. Getting the boundary and wedge wrong here propagates through the whole milestone.
Output: `.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md` — a prose document covering BOS-PROD-01, BOS-PROD-02, BOS-PROD-03.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-CONTEXT.md
@.planning/REQUIREMENTS.md
@.planning/seeds/SEED-001-coordination-bus.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write the product brief (boundary, ICP, buyer/user, wedge, positioning, anti-positioning, tension+resolution)</name>
  <files>.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md</files>
  <read_first>
    - .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-CONTEXT.md (the authoritative locked decisions D-01..D-08)
    - .planning/PROJECT.md (product boundary, governance non-negotiables, Out-of-Scope list)
    - .planning/REQUIREMENTS.md (the "Product Boundary" section: BOS-PROD-01..03)
    - .planning/ROADMAP.md (the "BOS-prefixed phases: Behavioral OS Foundation" section ~lines 113-143, plus the BOS0 row ~line 15)
    - .planning/seeds/SEED-001-coordination-bus.md (reframe: server-backed external-agent CLI verbs, NOT a parallel bus)
  </read_first>
  <action>
    Create BOS0-PRODUCT-BRIEF.md as a prose document. Document structure/headings are your discretion, but the brief MUST contain the following named sections and the exact locked-decision claims (cite the D-XX id inline where noted):

    1. A "Product boundary" section (per BOS-PROD-01): state that the Behavioral OS is a TEAM CONTROL PLANE over AI-assisted engineering work, explicitly NOT a generic project management clone. Frame it as the team-level layer that sits above the existing Voss ADE/harness/server/swarm substrate and turns that activity into a shared decision/outcome system — it does not replace the runtime, it observes and labels it.

    2. An "ICP / first beachhead" section (per BOS-PROD-03, D-01): ICP = small multi-agent engineering teams of 3-15 devs already running multiple coding agents (Claude Code / Codex / Voss). State why they qualify: they feel real coordination pain AND already generate the ADE/swarm events BOS needs to observe. Note the rejected alternatives and why (per D-01): solo power-user (weak pull for a team control plane), devex/platform team at scale-up (long cycle, weaker wedge observability).

    3. A "Buyer / user split" section (per BOS-PROD-03, D-03): EM / engineering-lead is the ECONOMIC BUYER; devs are the DAILY USERS.

    4. A "Wedge" section (per BOS-PROD-02, D-02): the first recommendation surface = DELEGATION (task -> agent/human). State why it is the chosen entry point: it is already modeled in the V25 server-native swarm assignment flow (swarm.assign / task ownership), making it the most directly observable decision today. State that review-depth and validation-depth are LATER wedges (review-depth needs review-outcome data; validation-depth depends on CI/validation ingestion at BOS12) — do NOT scope them into BOS0.

    5. A "Positioning" section (per D-05): external category used with design partners = "control plane for AI engineering teams"; internal / north-star term = "Behavioral OS" (internal only).

    6. An "## Anti-positioning" section (use this exact heading) (per BOS-PROD-01, D-06): state what BOS is NOT — NOT a Jira/Linear/Atlassian PM clone; NOT individual-developer surveillance, ranking, or productivity leaderboards. Tie the surveillance prohibition to PROJECT.md's trust model / Out-of-Scope list.

    7. A "Core tension and resolution" section (per D-04): explicitly state the tension — a TOP-DOWN EM buyer paired with a DEV-GENERATED data substrate. Then state the resolution: the team is ALREADY on the Voss ADE/swarm for agent work (existing product); the EM buys BOS as the team-level control plane over data the devs ALREADY generate; NO NEW DEV BEHAVIOR is required for the wedge to work.

    Constraints: This is prose, not code — no schema, no implementation, no data contracts (those are BOS3+). Respect the CONTEXT.md deferred list: do NOT add a competitive-analysis section as a deliverable, pricing/willingness-to-pay hypotheses, design-partner sourcing, wedge success metrics, or the web-vs-desktop responsibility map (that is BOS-PROD-04 / BOS7). A light competitive mention is allowed only if it sharpens the boundary, but it is not a required section. Ground the wedge claim in the V25 swarm substrate — do not invent a new event source.
  </action>
  <verify>
    <automated>test -f .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md && grep -q '## Anti-positioning' .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md && grep -Eqi 'control plane for AI engineering teams' .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md</automated>
  </verify>
  <acceptance_criteria>
    - BOS0-PRODUCT-BRIEF.md exists.
    - The file contains the literal heading `## Anti-positioning`.
    - The file contains the phrase "control plane for AI engineering teams" (external category, D-05).
    - The file contains the phrase "Behavioral OS" identified as the internal / north-star term (D-05).
    - The file states the ICP as small multi-agent engineering teams of "3-15" devs (D-01).
    - The file names delegation (task -> agent/human) as the first wedge AND references the V25 swarm assignment flow as why it is observable today (BOS-PROD-02, D-02).
    - The file names the EM / engineering-lead as economic buyer and devs as daily users (D-03).
    - The file states the boundary as a team control plane that is NOT a project management clone (BOS-PROD-01).
    - The Anti-positioning section names both: NOT Jira/Linear/Atlassian clone, AND NOT individual surveillance/ranking/leaderboards (D-06).
    - The file explicitly states the top-down-buyer vs dev-generated-substrate tension AND its resolution (devs already on the Voss ADE; no new dev behavior required) (D-04).
    - The file contains NO fenced code blocks, NO data schema, and NO web-vs-desktop responsibility map.
  </acceptance_criteria>
  <done>BOS0-PRODUCT-BRIEF.md exists and satisfies every acceptance criterion above; all seven required sections present with their locked-decision claims and D-XX citations.</done>
</task>

</tasks>

<verification>
This is a docs-only phase; final verification is human review of the brief against the locked decisions (D-01..D-08) in BOS0-CONTEXT.md. The automated greps above confirm structural/content presence but do not judge prose quality. The human reviewer confirms the boundary, ICP, buyer/user, wedge, positioning, anti-positioning, and tension+resolution are all stated correctly per the locked decisions.
</verification>

<success_criteria>
- BOS-PROD-01 covered: boundary stated as team control plane, not PM clone (with anti-positioning).
- BOS-PROD-02 covered: delegation wedge defined and grounded in the V25 swarm observable substrate.
- BOS-PROD-03 covered (brief portion): ICP and buyer/user split documented. (Discovery questions are Plan 02.)
- Core tension (D-04) stated and resolved.
- All seven required sections present.
</success_criteria>

<output>
Create `.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-01-SUMMARY.md` when done.
</output>
