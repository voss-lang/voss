---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 07
type: execute
wave: 6
depends_on: [V17-03, V17-04, V17-06]
files_modified:
  - docs/agent-coordination.md
  - .planning/phases/V16-managed-docs-prompt-generation/V17-COORDINATION-HANDOFF.md
autonomous: true
requirements: [VBUS-07, VBUS-08]
# Doc covers the bus verbs from the locked SPEC contract; the bus-verb --help assertion fully passes only after V17-06 (V15-gated) ships.

must_haves:
  truths:
    - "docs/agent-coordination.md documents every shipped verb, the 0/1/2/124 exit codes, the env vars, the label vocabulary, and a pre-edit guard example"
    - "every documented command's --help exits 0"
    - "the V16 phase dir contains a handoff note instructing folding a condensed version into the managed AGENTS.md section"
    - "the coherence guard passes at phase end: swarm/ byte-unchanged, no new UI components, sandbox.rs tests pass unmodified, no fs-watcher dep"
  artifacts:
    - path: "docs/agent-coordination.md"
      provides: "Coordination conventions doc for agent consumption"
      contains: "VOSS_AGENT_ID"
    - path: ".planning/phases/V16-managed-docs-prompt-generation/V17-COORDINATION-HANDOFF.md"
      provides: "Handoff note referencing the doc for V16 AGENTS.md folding"
      contains: "agent-coordination.md"
  key_links:
    - from: "docs/agent-coordination.md"
      to: "voss claims / voss bus verbs"
      via: "documented usage + exit codes + pre-edit guard example"
      pattern: "voss claims check"
    - from: ".planning/phases/V16-.../V17-COORDINATION-HANDOFF.md"
      to: "docs/agent-coordination.md"
      via: "explicit reference for the managed AGENTS.md section"
      pattern: "agent-coordination.md"
---

<objective>
Document the coordination vocabulary (VBUS-07) and run the final coherence-guard verification (VBUS-08). Write `docs/agent-coordination.md` covering claims + bus verbs, the exit-code contract, env vars, the label vocabulary, and a pre-edit guard example; drop a handoff note in the V16 phase dir telling V16 to fold a condensed version into its managed AGENTS.md section template (no template edits here — V16's territory). Then verify the coherence guard is green: `apps/voss-app/src/swarm/` byte-unchanged, no new Solid components, `sandbox.rs` tests pass unmodified, no fs-watcher dependency.

Purpose: VBUS-07 conventions + V16 handoff; VBUS-08 coherence verification.
Output: `docs/agent-coordination.md` (new), V16 handoff note (new).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-CONTEXT.md
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-PATTERNS.md
@.planning/seeds/SEED-001-coordination-bus.md

<interfaces>
<!-- Doc conventions + shipped surface to document -->
docs/sdk.md: bare `# Title`, no YAML frontmatter (Voss docs style to mirror)
Shipped verbs: voss claims stake|check|release|extend|list (V17-03); voss bus send|inbox|wait (V17-06, V15-gated)
Exit codes: 0 clear/success · 1 conflict · 2 identity/discovery/usage · 124 wait timeout
Env vars: VOSS_AGENT_ID (always at spawn), VOSS_SERVER_PORT + VOSS_SERVER_TOKEN (bus, V15-gated)
Label vocabulary (SEED-001 / SPEC): coord:blocker, coord:handoff, mission:<id>, review-request
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write docs/agent-coordination.md + V16 handoff note</name>
  <files>docs/agent-coordination.md, .planning/phases/V16-managed-docs-prompt-generation/V17-COORDINATION-HANDOFF.md</files>
  <read_first>
    - docs/sdk.md (bare-heading no-frontmatter doc style)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md (VBUS-07 target: verbs, exit codes, env vars, label vocabulary, pre-edit guard example)
    - .planning/seeds/SEED-001-coordination-bus.md (label vocabulary + reframe context for the doc's framing)
    - voss/harness/claims.py (the actual shipped verb names/flags to document accurately)
  </read_first>
  <action>Create `docs/agent-coordination.md` (bare `# Agent Coordination` heading, no YAML frontmatter, matching docs/sdk.md). Sections: Overview (advisory coordination for external CLI agents, tier-C complement to VCKP-13); Environment Variables (VOSS_AGENT_ID injected into every pane at spawn; VOSS_SERVER_PORT/VOSS_SERVER_TOKEN for bus, V15-gated); Claims Verbs (stake/check/release/extend/list with flags, glob + URI patterns, TTL default 30min, idempotent self-overlap); Bus Verbs (send/inbox/wait with @mentions + labels, document from the locked SPEC contract even pre-V15); Exit Codes (table: 0 clear, 1 conflict, 2 identity/discovery/usage, 124 wait timeout); Label Vocabulary (coord:blocker, coord:handoff, mission:<id>, review-request); Pre-edit Guard Example (`voss claims check <files> || { echo "blocked"; exit 1; }` shell snippet — this is documentation prose, allowed in a .md doc); V16 Handoff (one line pointing to the managed AGENTS.md section). Then create `.planning/phases/V16-managed-docs-prompt-generation/V17-COORDINATION-HANDOFF.md`: a short note instructing V16 to fold a condensed version of docs/agent-coordination.md (verbs + label vocabulary + pre-edit guard one-liner) into the managed AGENTS.md section template, explicitly referencing `docs/agent-coordination.md` as the source of truth and noting V17 does NOT edit AGENTS.md templates directly.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_coordination_doc.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - test_coordination_doc.py passes (doc exists; documented commands --help exit 0; the bus-verb --help portion passes once V17-06 has shipped, else the test's bus section is try/except-guarded per V17-01)
    - `grep -c 'VOSS_AGENT_ID' docs/agent-coordination.md` >= 1 and the doc contains a `voss claims check` pre-edit guard example
    - The doc's exit-code section lists 0, 1, 2, and 124
    - `.planning/phases/V16-managed-docs-prompt-generation/V17-COORDINATION-HANDOFF.md` exists and contains the string `agent-coordination.md`
  </acceptance_criteria>
  <done>Coordination doc covers all shipped verbs + exit codes + env vars + labels + guard example; V16 handoff note references it.</done>
</task>

<task type="auto">
  <name>Task 2: Final coherence-guard verification (VBUS-08)</name>
  <files>.planning/phases/V16-managed-docs-prompt-generation/V17-COORDINATION-HANDOFF.md</files>
  <read_first>
    - tests/harness/test_coherence_guard.py (the guard written in V17-01 — this task RUNS it as the phase-end gate)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md (VBUS-08 acceptance: swarm/ byte-unchanged, no new UI, sandbox.rs tests pass unmodified, no fs-watcher)
    - apps/voss-app/src/swarm/swarmTypes.ts (the file the guard hashes)
  </read_first>
  <action>This is a verification task — no new production code. Run the coherence guard test plus the sandbox.rs cargo tests and confirm VBUS-08 holds after the whole phase landed: `apps/voss-app/src/swarm/` is byte-unchanged (the guard's runtime hash baseline catches any drift), no new Solid component files were added under apps/voss-app/src for V17, `crates/voss-app-core/src/sandbox.rs` is byte-unchanged and its tests pass unmodified, and no fs-watcher / chokidar / watchdog dependency was added to apps/voss-app or the harness. If the guard fails, the offending change must be reverted — V17 must not add parallel substrate or touch frozen adjacent code. Record the green guard result + the `git diff --stat` of swarm/ and sandbox.rs (both empty) in the summary. Append a confirmation line to the V16 handoff note that the coherence guard passed (so the file has a write to anchor this task; keep it a single appended line, do not rewrite the note).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_coherence_guard.py -x -q && cargo test -p voss-app-core 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - test_coherence_guard.py passes (swarm/ file-set + hashes unchanged, no fs-watcher dep, no unexpected new Solid component)
    - `cargo test -p voss-app-core` passes including the existing sandbox.rs tests (unmodified)
    - `git diff --stat apps/voss-app/src/swarm/ crates/voss-app-core/src/sandbox.rs` is empty (zero changes)
    - The V16 handoff note has a single appended line confirming the coherence guard passed
  </acceptance_criteria>
  <done>VBUS-08 verified: zero parallel substrate, swarm/ + sandbox.rs untouched, no fs-watcher dep, no new UI; guard green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| doc author -> repo docs | Documentation only; no executable surface introduced |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V17-18 | Info disclosure | doc leaks secret-handling guidance | mitigate | Doc explicitly states no secrets belong in bus messages (journal is plaintext); guidance per planning security note |
| T-V17-19 | Tampering | scope creep adds parallel substrate | mitigate | Coherence guard (Task 2) is the enforcement gate — any swarm/sandbox/fs-watcher drift fails the phase |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_coordination_doc.py tests/harness/test_coherence_guard.py -x -q` GREEN.
- `cargo test -p voss-app-core` GREEN (sandbox.rs unmodified).
- swarm/ + sandbox.rs diff-empty.
</verification>

<success_criteria>
Coordination conventions documented for agent consumption with a V16 handoff; coherence guard proves V17 added no parallel substrate and touched no frozen adjacent code.
</success_criteria>

<output>
Create `.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-07-SUMMARY.md` when done.
</output>
