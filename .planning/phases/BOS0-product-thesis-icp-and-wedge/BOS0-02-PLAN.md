---
phase: BOS0-product-thesis-icp-and-wedge
plan: 02
type: execute
wave: 2
depends_on: [BOS0-01]
files_modified:
  - .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-DISCOVERY-SCRIPT.md
autonomous: true
requirements: [BOS-PROD-03]

must_haves:
  truths:
    - "An interviewer can run a design-partner interview that validates problem existence and current decision behavior BEFORE pitching the wedge"
    - "A reader can see that problem-validation questions are ordered before any wedge-pitch / wedge-resonance question (D-07)"
    - "A reader can see the interviewee target is the ICP: EMs/eng-leads of small multi-agent teams, with dev users probed for current delegation behavior (D-08)"
    - "A reader can see willingness-to-pay questions come AFTER problem validation and are non-leading (D-07)"
  artifacts:
    - path: ".planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-DISCOVERY-SCRIPT.md"
      provides: "Mom-Test-style design-partner discovery script with problem-first ordering"
      contains: "## Problem validation"
  key_links:
    - from: "BOS0-DISCOVERY-SCRIPT.md wedge-resonance section"
      to: "BOS0-PRODUCT-BRIEF.md delegation wedge"
      via: "wedge-resonance questions probe the delegation wedge defined in the brief"
      pattern: "delegation"
---

<objective>
Write the design-partner discovery script: the Mom-Test-style interview questions that validate the problem before pitching the wedge. Problem existence and current decision behavior come first; wedge-resonance and willingness-to-pay come after, and must not lead the witness.

Purpose: First design-partner interviews must confirm the delegation/review/validation problem actually hurts and how teams decide today BEFORE Voss pitches its wedge — otherwise the wedge validates nothing.
Output: `.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-DISCOVERY-SCRIPT.md` — completes the BOS-PROD-03 "first design-partner validation questions" requirement.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-CONTEXT.md
@.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md
@.planning/REQUIREMENTS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write the Mom-Test-style design-partner discovery script (problem-first)</name>
  <files>.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-DISCOVERY-SCRIPT.md</files>
  <read_first>
    - .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-CONTEXT.md (locked decisions, especially D-07 problem-first and D-08 interviewee target)
    - .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md (the brief written in Plan 01 — wedge-resonance questions must probe the delegation wedge as the brief defines it; do not introduce a different wedge)
    - .planning/REQUIREMENTS.md (BOS-PROD-03 — "first design-partner validation questions")
  </read_first>
  <action>
    Create BOS0-DISCOVERY-SCRIPT.md as a prose interview script. Exact question wording and ordering are your discretion WITHIN the D-07 problem-first constraint. The script MUST contain these named sections in this order:

    1. An "Interviewee target" section (per D-08): the interviewees are the ICP from D-01/D-03 — EMs / engineering-leads of small multi-agent engineering teams (buyer-side), with dev users probed for current delegation behavior. State who you are trying to talk to and why.

    2. A "## Problem validation" section (use this exact heading) (per D-07, Mom-Test style): questions that establish whether delegation/review/validation decisions actually hurt TODAY and HOW teams make those decisions now — what signals or data they use, who decides, what goes wrong. These must be backward-looking / behavior-based (ask about what they actually did recently), NOT hypothetical ("would you...") and NOT leading toward Voss. Include a clearly larger count of these than wedge-pitch questions — at least 5 distinct problem-validation questions.

    3. A "Current decision behavior" subsection or block within/after problem validation (per D-07): specifically probe how delegation (task -> agent or human) is decided today, and probe dev users for their current delegation behavior (per D-08).

    4. A "Wedge resonance" section that comes AFTER problem validation (per D-07): only here may the script surface the delegation wedge from the brief. Probe whether the delegation recommendation surface resonates, without leading the witness. These questions probe the SAME wedge the brief defines (delegation: task -> agent/human) — do not invent review/validation wedges here (those are later per D-02).

    5. A "Willingness to pay" section LAST (per D-07): probe budget/ownership/buying behavior in a non-leading, behavior-based way. Keep it light — this is not a pricing study (pricing hypotheses are deferred per CONTEXT.md).

    The document must make the problem-first ordering visually obvious: problem-validation questions appear before any wedge-pitch question, and willingness-to-pay appears last.

    Constraints: Prose only, no code, no schema. Do NOT scope a design-partner sourcing plan (where to find teams) — that is deferred per CONTEXT.md. Do NOT build pricing hypotheses. Keep wedge questions narrow to delegation per D-02.
  </action>
  <verify>
    <automated>test -f .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-DISCOVERY-SCRIPT.md && grep -q '## Problem validation' .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-DISCOVERY-SCRIPT.md && awk '/[Pp]roblem validation/{p=NR} /[Ww]edge resonance/{w=NR} END{exit !(p>0 && w>0 && p<w)}' .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-DISCOVERY-SCRIPT.md</automated>
  </verify>
  <acceptance_criteria>
    - BOS0-DISCOVERY-SCRIPT.md exists.
    - The file contains the literal heading `## Problem validation`.
    - The "Problem validation" section appears BEFORE the "Wedge resonance" section in document order (D-07 problem-first).
    - The file has at least 5 distinct problem-validation questions, more than the number of wedge-pitch questions.
    - The file names the interviewee target as EMs/eng-leads of small multi-agent teams (buyer-side) with dev users probed for current delegation behavior (D-08).
    - The Wedge resonance section probes the delegation (task -> agent/human) wedge as defined in BOS0-PRODUCT-BRIEF.md, not a different wedge.
    - A "Willingness to pay" section exists and appears after problem validation (D-07).
    - The file contains NO fenced code blocks and NO data schema.
    - The file does NOT include a design-partner sourcing plan or pricing hypotheses (deferred).
  </acceptance_criteria>
  <done>BOS0-DISCOVERY-SCRIPT.md exists and satisfies every acceptance criterion above; problem-first ordering is structurally enforced and the wedge section aligns with the brief's delegation wedge.</done>
</task>

</tasks>

<verification>
Docs-only phase; final verification is human review of the script against D-07 (problem-first, non-leading) and D-08 (interviewee = ICP buyer-side + dev users) in BOS0-CONTEXT.md. The automated checks confirm the `## Problem validation` heading exists and precedes wedge-resonance, but the human reviewer confirms the questions are genuinely Mom-Test-style (behavior-based, non-leading) and that the wedge-resonance questions match the brief's delegation wedge.
</verification>

<success_criteria>
- BOS-PROD-03 completed: the first design-partner validation questions are documented, problem-first.
- Ordering enforces D-07: problem validation -> wedge resonance -> willingness to pay.
- Interviewee target matches D-08.
- Wedge-resonance questions align with the delegation wedge from Plan 01's brief.
</success_criteria>

<output>
Create `.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-02-SUMMARY.md` when done.
</output>
