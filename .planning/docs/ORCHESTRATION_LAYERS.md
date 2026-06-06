# Voss PRD: Agent Engineering Organization Layer

> **Roadmap status (2026-06-05):** This PRD is the design source for the **V-track (V0–V12)** in `ROADMAP.md`. Its phases P0–P12 map 1:1 to V0–V12. The V-track **supersedes the O-track** (V3↔O2, V4↔O1, V5↔O3, V6↔O4, V7↔O5, V9↔O6) and **absorbs M13** into V8. Roadmap requirement IDs are namespaced `V*` (e.g. `CAP-*`→`VCAP-*`, `MAG-*`→`VMAG-*`, `LANG-*`→`VLANG-*`, `ADE-*`→`VADE-*`) to avoid collisions with M3/M13/A12; the un-prefixed IDs below remain canonical for design, and each `V{n}-SPEC.md` maps PRD-ID → roadmap-ID. Build keystone: **V4 (P4) session tree + budget fan-out**, budget enforced pre-emptively.

## 1. Product Thesis

Voss should become an orchestration layer for AI coding agents that models software work like a high-performing engineering organization, not a rigid automation pipeline.

The product should provide agents with:

* A clean toolbelt
* Project-local memory
* Declarative team roles
* Explicit engineering principles
* Bounded scope and budget
* Independent review
* Continuous verification
* Replayable audit history

The key product promise:

> Voss lets AI agents work like an engineering team while keeping every action scoped, budgeted, reviewed, and replayable.

## 2. Current Repo Assessment

### 2.1 What Already Exists

Voss already has the foundation for this direction:

| Layer             | Existing Scaffold                                                                         |
| ----------------- | ----------------------------------------------------------------------------------------- |
| Runtime           | `voss_runtime` with confidence, context, budget, semantic matching, memory, agents, tools |
| Harness           | `voss/harness` with CLI, permissions, sessions, recorder, tools, sandbox, cognition       |
| Subagents         | `SubagentSpec`, `SubagentRegistry`, `run_subagent`, default roles                         |
| Team config       | `.voss team{}` parser/compile direction, `TeamConfig`, per-role scope/budget/tools        |
| Multi-agent UX    | M13 planned around live subagent panels, fan-out, steering, gather                        |
| Orchestration     | O1-O6 planned around session tree, board, reviewers, EM loop, audit                       |
| Code intelligence | M10 planned around LSP, ast-grep, project index, code search                              |
| Desktop ADE       | Tauri app with panes, layout, session persistence, command palette, status bar, themes    |

### 2.2 What Is Still Fragmented

The repo has many strong components, but they are distributed across phases:

* Runtime agent primitives exist separately from harness subagent orchestration.
* `.voss team{}` exists as a config direction but is not yet the default execution path.
* Multi-agent chat exists as a phase but is not yet unified with the O-track session-tree cage.
* Reviewer-A/B and EM loops are specified but need to become a coherent product flow.
* The desktop ADE has panes and visual surfaces, but the audit/review product is not yet the center of the experience.
* Engineering principles are implied in prompts and docs, but not yet first-class config.

## 3. Product Goals

### 3.1 Primary Goal

Build Voss into a controlled AI engineering organization runtime.

A user should be able to say:

```text
Implement OAuth login with tests and docs.
```

And Voss should:

1. Convert the idea into scoped work cards.
2. Assign work to declared roles.
3. Partition budget and permissions.
4. Execute work in parallel where safe.
5. Run verification continuously.
6. Route work through independent reviewers.
7. Block unsafe or unverified completion.
8. Produce a replayable audit trail.
9. Ask for human sign-off only at meaningful decision points.

### 3.2 Non-Goals

Voss should not become:

* A generic chatbot wrapper
* A pure workflow DSL
* A “swarm” demo with weak audit
* A replacement for all programming languages
* A fully autonomous deploy/delete/money executor without human confirmation
* A distributed multi-machine agent system in the near term

## 4. Core Product Model

### 4.1 Six Product Primitives

| Primitive     | Product Meaning            | Implementation Surface                              |
| ------------- | -------------------------- | --------------------------------------------------- |
| Capabilities  | Agent toolbelt             | `voss/harness/tools.py`, M10-M15 capabilities       |
| Principles    | Engineering culture        | New `.voss/principles.yml` or `principles {}` block |
| Orchestration | Delegation and integration | O5 Engineering Manager loop                         |
| Roles         | Specialist lenses          | `.voss team{}` and `SubagentSpec`                   |
| Memory        | Institutional knowledge    | `.voss/`, `.voss-cache/`, cognition, recorder       |
| Verification  | Review loop                | O3 board gates, O4 reviewers, evals, tests          |

### 4.2 Recursive Architecture

Voss should support the same control model at multiple levels:

| Level | Meaning           | Voss Object                               |
| ----- | ----------------- | ----------------------------------------- |
| L0    | Tools             | Capability registry                       |
| L1    | Single agent      | Harness `run_turn`                        |
| L2    | Team              | `.voss team{}` plus subagents             |
| L3    | Organization      | EM loop plus board plus reviewers         |
| L4    | Meta-organization | Review panels, calibration, audit product |

## 5. Required User Experience

### 5.1 CLI Experience

Core commands:

```bash
voss do "implement feature X"
voss chat
voss team check
voss team run "goal"
voss board
voss audit <run_id>
voss sessions
voss resume <session_id>
voss verify <run_id>
```

### 5.2 ADE Experience

The desktop ADE should center around:

* Goal input
* Board state
* Agent roster
* Subagent panels
* Budget meter
* Diff viewer
* Verification status
* Reviewer verdicts
* Session tree replay
* Final audit report

### 5.3 Human Control Model

Human control should focus on high-leverage moments:

* Approve broad goal
* Approve team/role config
* Approve risky permissions
* Approve irreversible operations
* Review final audit
* Sign off on merge-ready result

The user should not be forced to manually approve every low-risk read/search/test step.

## 6. Phased Roadmap

## Phase 0: Reframe And Consolidate

### Objective

Align the repo around the new identity:

> Voss is an agent engineering organization layer, with `.voss` as its declarative control language.

### Requirements

| ID    | Requirement                                                                                                             |
| ----- | ----------------------------------------------------------------------------------------------------------------------- |
| P0-01 | Update `PRD.md` to lead with “agent engineering organization,” not “Python fork.”                                       |
| P0-02 | Add a new architecture doc: `docs/agent-org-architecture.md`.                                                           |
| P0-03 | Define six primitives: capabilities, principles, orchestration, roles, memory, verification.                            |
| P0-04 | Mark existing M/O/F/A phases as belonging to these primitives.                                                          |
| P0-05 | Add a repo-wide terminology table: capability, role, agent, subagent, EM, card, board, gate, verifier, reviewer, audit. |

### Acceptance Criteria

* New contributor can understand the system in under 15 minutes.
* Docs explain why Voss is not just a pipeline runner.
* Roadmap references primitives consistently.

## Phase 1: Capability Surface Hardening

### Objective

Make the agent toolbelt clean, composable, typed, permissioned, and auditable.

### Existing Assets

* `voss/harness/tools.py`
* `voss/harness/permissions.py`
* `voss/harness/sandbox.py`
* `voss/harness/code/`
* M10 code intelligence
* M11 Voss-aware tools
* M12 MCP bridge
* M14 file watch
* M15 skills marketplace

### Requirements

| ID     | Requirement                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| CAP-01 | Define a normalized `Capability` schema for all tools.                                                                                           |
| CAP-02 | Every capability must declare name, description, input schema, output schema, mutability, network usage, scope requirements, and audit behavior. |
| CAP-03 | Capabilities must be order-agnostic unless explicitly marked as stateful.                                                                        |
| CAP-04 | Add `voss capabilities list`.                                                                                                                    |
| CAP-05 | Add `voss capabilities inspect <name>`.                                                                                                          |
| CAP-06 | Add capability groups: `fs`, `git`, `test`, `shell`, `net`, `code`, `memory`, `review`, `mcp`.                                                   |
| CAP-07 | Unify MCP tools into the same capability registry.                                                                                               |
| CAP-08 | Capability invocation must emit recorder events.                                                                                                 |
| CAP-09 | Mutating capabilities must require permission gate approval unless in approved role/mode.                                                        |
| CAP-10 | Capabilities must be testable with stub inputs and deterministic output fixtures.                                                                |

### Implementation Notes

* Extend `ToolEntry` rather than replacing it.
* Preserve current call sites.
* Add metadata fields incrementally.
* Treat MCP as just another capability provider.
* Keep capability output JSON-first.

### Acceptance Criteria

* Agent can list and inspect available capabilities.
* Role tool filters can operate on capability groups.
* Network tools are default-deny unless role allows `net`.
* Every capability invocation appears in audit output.

## Phase 2: Principles Layer

### Objective

Make engineering principles first-class and inject them into every agent context without hardcoding workflow steps.

### Requirements

| ID      | Requirement                                                                            |
| ------- | -------------------------------------------------------------------------------------- |
| PRIN-01 | Add `.voss/principles.yml` support.                                                    |
| PRIN-02 | Add optional `.voss` syntax: `principles { ... }`.                                     |
| PRIN-03 | Principles must compile into immutable `PrinciplesConfig`.                             |
| PRIN-04 | Principles must be injected into EM, worker, reviewer, and tester contexts.            |
| PRIN-05 | Default principles must ship with Voss.                                                |
| PRIN-06 | Project-local principles override defaults only additively unless explicitly disabled. |
| PRIN-07 | `voss principles show` displays active principles.                                     |
| PRIN-08 | Audit report records which principles were active during a run.                        |

### Default Principles

```yaml
diff: "Make the smallest diff that solves the task."
evidence: "No factual claim without evidence."
tests: "Tests prove behavior, not coverage theater."
scope: "Do not edit outside assigned scope."
review: "Review intent and correctness before style."
reversibility: "Prefer reversible changes unless the user approves risk."
```

### Acceptance Criteria

* Every agent prompt includes the active principles.
* Principles are visible in audit.
* Changing principles changes subsequent runs but not historical audits.
* No control flow depends on individual principle strings.

## Phase 3: Team Specification And Role Cage

### Objective

Make `.voss team{}` the declarative source of truth for role roster, budget, scope, tools, and model tiering.

### Existing Assets

* `TeamDecl`
* `TeamConfig`
* `compile_team`
* enriched `SubagentSpec`
* `gate_for_role`
* `filter_toolset_for_role`
* scope containment tests

### Requirements

| ID      | Requirement                                                                                                  |
| ------- | ------------------------------------------------------------------------------------------------------------ |
| TEAM-01 | Finalize `.voss team{}` grammar and AST shape.                                                               |
| TEAM-02 | `team{}` must compile to frozen `TeamConfig` plus `SubagentRegistry`.                                        |
| TEAM-03 | `SubagentSpec` must carry role id, prompt, model, mode, scope, budget, tools, and network allowance.         |
| TEAM-04 | EM cannot invent agents outside declared registry.                                                           |
| TEAM-05 | Role scope must be compile-time contained in global ceiling.                                                 |
| TEAM-06 | Role budget must be compile-time contained in global ceiling.                                                |
| TEAM-07 | Role tools must be filtered through capability registry.                                                     |
| TEAM-08 | Model tiering must be explicit per role.                                                                     |
| TEAM-09 | Default roster must include `architect`, `backend`, `frontend`, `tester`, `reviewer`, `skeptic`, and `docs`. |
| TEAM-10 | `voss team check` validates syntax, scope, tools, model availability, and budget.                            |

### Example Syntax

```voss
team "default" {
  ceiling {
    budget: 120000 tokens
    scope: ["src/**", "tests/**", "docs/**"]
    latency: 30m
  }

  principles {
    diff: "Smallest diff that solves it"
    evidence: "No claim without evidence"
  }

  role architect {
    model: "strong"
    mode: "plan"
    scope: ["src/**", "docs/**"]
    tools: ["fs", "code", "git"]
    budget: 12000 tokens
  }

  role backend {
    model: "cheap"
    mode: "edit"
    scope: ["src/server/**", "tests/server/**"]
    tools: ["fs", "code", "test", "git"]
    budget: 24000 tokens
  }

  role reviewer {
    model: "strong"
    mode: "plan"
    scope: ["src/**", "tests/**"]
    tools: ["fs", "code", "test", "git"]
    budget: 16000 tokens
  }
}
```

### Acceptance Criteria

* Invalid scope widening fails at compile time.
* Unknown capability fails at compile time.
* Unknown model emits actionable diagnostic.
* EM dispatch to undeclared role fails.
* Legacy `explorer`, `worker`, `reviewer` path remains backward-compatible.

## Phase 4: Session Tree And Budget Fan-Out

### Objective

Make every agent and subagent a first-class recorded node with its own budget, scope, status, artifacts, and audit trail.

### Existing Assets

* O1 plans
* `SessionRecord`
* `RunRecorder`
* `BudgetScope`
* `run_subagent`
* M13 allocator pattern

### Requirements

| ID      | Requirement                                                                         |
| ------- | ----------------------------------------------------------------------------------- |
| TREE-01 | Implement `SessionTreeNode` schema.                                                 |
| TREE-02 | Implement `SessionTreeManager`.                                                     |
| TREE-03 | Persist each node to `.voss/sessions/<root_id>/<node_id>.json`.                     |
| TREE-04 | Enforce `sum(child budgets) + reserve <= parent budget`.                            |
| TREE-05 | Prevent upward budget mutation after allocation.                                    |
| TREE-06 | Record rejected budget raise attempts.                                              |
| TREE-07 | Always finalize child nodes, including error, timeout, budget, killed, and blocked. |
| TREE-08 | Attach scope and role metadata to each node.                                        |
| TREE-09 | Add `voss session tree <root_id>`.                                                  |
| TREE-10 | Add machine-readable tree export for ADE.                                           |

### Acceptance Criteria

* No child can overspend parent allocation.
* No orphan child sessions.
* Every spawned agent has a durable node.
* Failed/killed/timed-out children still reach terminal state.
* Session tree can reconstruct a full run without reading chat transcript.

## Phase 5: Board State Machine

### Objective

Represent orchestration as a board, not an invisible prompt loop.

### Requirements

| ID       | Requirement                                                                                                                            |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| BOARD-01 | Implement board columns: `Backlog`, `Planned`, `InProgress`, `InReview`, `Blocked`, `Done`.                                            |
| BOARD-02 | Define `Card` as work item backed by session-tree node.                                                                                |
| BOARD-03 | Cards must carry original idea, role, scope, risk, artifact target, acceptance criteria, verification requirement, budget, and status. |
| BOARD-04 | Implement WIP limits per column.                                                                                                       |
| BOARD-05 | Implement transition gates.                                                                                                            |
| BOARD-06 | `InProgress -> InReview` requires artifact.                                                                                            |
| BOARD-07 | `InReview -> Done` requires Reviewer-A verification and Reviewer-B verdict.                                                            |
| BOARD-08 | Timeout or critic-loop exhaustion moves card to `Blocked`.                                                                             |
| BOARD-09 | Board transitions must persist to session tree.                                                                                        |
| BOARD-10 | Add `voss board` CLI view.                                                                                                             |

### Transition Gates

| Transition            | Gate                                                                |
| --------------------- | ------------------------------------------------------------------- |
| Backlog → Planned     | EM creates acceptance criteria and role assignment                  |
| Planned → InProgress  | Scope and budget allocated                                          |
| InProgress → InReview | Artifact exists                                                     |
| InReview → Done       | Tests/evals pass and independent review passes                      |
| Any → Blocked         | Timeout, budget, scope error, reviewer block, human decision needed |
| Blocked → Planned     | EM rescope or human approval                                        |

### Acceptance Criteria

* Board state is deterministic and replayable.
* Agents cannot mark their own work Done.
* Done requires independent review.
* Every blocked card has a reason.
* Board can be rendered in CLI and ADE.

## Phase 6: Reviewer A/B Split

### Objective

Make verification independent, cheap, and continuous.

### Requirements

| ID     | Requirement                                                                                         |
| ------ | --------------------------------------------------------------------------------------------------- |
| REV-01 | Reviewer-A derives verification bar from original human idea, not EM-authored acceptance criteria.  |
| REV-02 | Reviewer-A authors tests, evals, or manual verification checklist.                                  |
| REV-03 | Worker agents cannot author their own final gate.                                                   |
| REV-04 | Reviewer-B independently judges artifact, diff, tests, and idea alignment.                          |
| REV-05 | Reviewer-B must be EM-narrative-blind.                                                              |
| REV-06 | Reviewer-B verdict includes confidence, pass/fail/block, evidence refs, notes, and inferred domain. |
| REV-07 | Reviewer-B may fail if Reviewer-A verification diverges from original idea.                         |
| REV-08 | Reviewers operate within budget and scope constraints.                                              |
| REV-09 | Review artifacts are persisted.                                                                     |
| REV-10 | Add `voss review <run_id>` command.                                                                 |

### Reviewer-B Verdict Shape

```python
@dataclass(frozen=True)
class ReviewerVerdict:
    verdict: Literal["pass", "fail", "block"]
    confidence: float
    tier: Literal["fast", "strong"]
    notes: str
    evidence_refs: tuple[str, ...]
    domain_inferred: Literal["code", "ai", "docs", "unknown"] | None
```

### Acceptance Criteria

* Reviewer-A and Reviewer-B see different context packets.
* Reviewer-B does not depend on EM summary.
* Failed verification blocks Done.
* Review evidence is linked to files, tests, diffs, or eval output.
* Audit report can explain why something passed.

## Phase 7: Engineering Manager Loop

### Objective

Implement the autonomous orchestrator as a constrained tech lead.

### Existing Assets

* O5 Engineering Manager plans
* EM stub tests
* Ticket concept
* Board and reviewer dependency chain

### Requirements

| ID    | Requirement                                                      |
| ----- | ---------------------------------------------------------------- |
| EM-01 | Convert human idea into tickets/cards.                           |
| EM-02 | Assign role from declared roster only.                           |
| EM-03 | Produce routing rationale for every assignment.                  |
| EM-04 | Split work to maximize parallelism within budget and WIP limits. |
| EM-05 | Integrate completed artifacts.                                   |
| EM-06 | Kill or rescope cards when blocked.                              |
| EM-07 | Persist kill/rescope lineage.                                    |
| EM-08 | Never mutate ceiling, confidence threshold, or role registry.    |
| EM-09 | Never construct new permission gates outside team config.        |
| EM-10 | Produce final run summary with evidence and residual risk.       |

### EM Loop

```text
Human idea
→ derive cards
→ assign roles
→ allocate budget/scope
→ dispatch workers
→ monitor board
→ route blockers
→ request review
→ integrate results
→ produce audit
→ ask human sign-off
```

### Acceptance Criteria

* EM cannot invent roles.
* EM cannot increase budget.
* EM cannot widen scope.
* EM decisions are logged.
* Misroutes are auditable.
* Killed cards remain inspectable.
* Human can review final rationale.

## Phase 8: Multi-Agent Chat And Live Steering

### Objective

Expose team-style delegation inside `voss chat` and the ADE.

### Existing Assets

* M13 scope
* `SubAgentPanel`
* `run_turn`
* `run_subagent`
* `multiagent.py`
* TUI renderer hooks

### Requirements

| ID     | Requirement                                                          |
| ------ | -------------------------------------------------------------------- |
| MAG-01 | Parent chat agent can spawn child agents non-blockingly.             |
| MAG-02 | Child handles return immediately.                                    |
| MAG-03 | Parent can check child status.                                       |
| MAG-04 | Parent can gather child outputs.                                     |
| MAG-05 | Parent can steer child between iterations.                           |
| MAG-06 | Child budget is allocated from parent budget.                        |
| MAG-07 | Recursive child spawning preserves budget invariant.                 |
| MAG-08 | TUI/ADE displays live child state quietly by default.                |
| MAG-09 | User can reveal child details.                                       |
| MAG-10 | All child events persist into recorder/session tree once O1 is live. |

### Acceptance Criteria

* Multi-agent chat works with stub provider.
* Parent can continue after spawning children.
* Child oversell is impossible.
* Child panels show status, budget, latest tool call, and exit state.
* Ctrl+C remains interrupt.
* Reveal action is explicit.

## Phase 9: Audit Product

### Objective

Make the audit trail the primary trust product.

### Requirements

| ID     | Requirement                                                                                                                                                    |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AUD-01 | Add `voss audit <run_id>`.                                                                                                                                     |
| AUD-02 | Audit shows original idea, active principles, team config, budget, scope, board, cards, agent actions, diffs, tests, reviews, blocked items, and final status. |
| AUD-03 | Audit must distinguish EM claims from verified evidence.                                                                                                       |
| AUD-04 | Audit must show budget allocation and consumption per node.                                                                                                    |
| AUD-05 | Audit must show scope violations and denied attempts.                                                                                                          |
| AUD-06 | Audit must show Reviewer-A and Reviewer-B outputs separately.                                                                                                  |
| AUD-07 | Audit must show killed/rescoped lineage.                                                                                                                       |
| AUD-08 | Audit must export Markdown and JSON.                                                                                                                           |
| AUD-09 | ADE must render audit as a navigable session tree.                                                                                                             |
| AUD-10 | Audit must include “residual risk” section.                                                                                                                    |

### Audit Sections

```text
1. Goal
2. Active Team
3. Principles
4. Scope and Budget
5. Board Timeline
6. Work Cards
7. Agent Actions
8. Diff Summary
9. Tests and Evals
10. Reviewer-A Verification
11. Reviewer-B Verdict
12. Blocked/Killed/Rescoped Items
13. Evidence References
14. Residual Risks
15. Final Human Decision
```

### Acceptance Criteria

* User can understand what happened without reading raw logs.
* Audit can be used for PR review.
* Audit can detect unsupported claims.
* Audit is deterministic from persisted run data.

## Phase 10: Voss Language As Coordination Spec

### Objective

Make `.voss` the durable control language for agent engineering work.

### Requirements

| ID      | Requirement                                                                                  |
| ------- | -------------------------------------------------------------------------------------------- |
| LANG-01 | Stabilize grammar for `principles`, `team`, `role`, `gate`, `board`, `review`, and `memory`. |
| LANG-02 | Add compiler diagnostics for scope, budget, tools, and role errors.                          |
| LANG-03 | Add `voss ast` for inspection.                                                               |
| LANG-04 | Add `voss check` for static validation.                                                      |
| LANG-05 | Add `voss compile` to runtime config objects.                                                |
| LANG-06 | Add `voss run <file.voss>` for declared workflows.                                           |
| LANG-07 | Keep raw Python runtime examples as canonical parity tests.                                  |
| LANG-08 | Add examples for team orchestration, reviewer split, and audit gates.                        |

### Proposed New Constructs

```voss
principles { ... }

team "name" { ... }

gate done {
  require tests_passed
  require independent_review
  require evidence_refs
}

memory {
  decisions: ".voss/decisions"
  sessions: ".voss/sessions"
  semantic: ".voss-cache/semantic"
}
```

### Acceptance Criteria

* `.voss` config can fully declare a team run.
* Static errors are clear enough for non-CS users.
* Runtime behavior matches compiled config.
* Language examples are shorter and clearer than equivalent Python.

## Phase 11: ADE Integration

### Objective

Turn the desktop app into a visual Agentic Development Environment.

### Existing Assets

* Tauri shell
* PTY panes
* Grid engine
* Layout presets
* Project open
* Session persistence
* Command palette
* Themes
* Status bar
* Agent sidebar
* Context panel
* SubAgentPanel
* CodeIntelPanel

### Requirements

| ID     | Requirement                                   |
| ------ | --------------------------------------------- |
| ADE-01 | Add team roster panel.                        |
| ADE-02 | Add board panel.                              |
| ADE-03 | Add session tree panel.                       |
| ADE-04 | Add audit panel.                              |
| ADE-05 | Add reviewer verdict panel.                   |
| ADE-06 | Add budget visualization per root/card/agent. |
| ADE-07 | Add scope visualization per role/card.        |
| ADE-08 | Add diff and verification drilldown.          |
| ADE-09 | Add blocked-card human decision flow.         |
| ADE-10 | Add run replay mode.                          |

### Acceptance Criteria

* User can watch multiple agents work without reading terminal spam.
* User can inspect why a card is blocked.
* User can compare reviewer outputs.
* User can replay a run.
* User can sign off from audit view.

## Phase 12: Safety And Factory Fallbacks

### Objective

Keep strict procedural rails only where autonomy is unsafe or inefficient.

### Requirements

| ID      | Requirement                                                              |
| ------- | ------------------------------------------------------------------------ |
| SAFE-01 | Irreversible actions require explicit confirmation.                      |
| SAFE-02 | Deploy/delete/migration/money/prod operations use fixed runbooks.        |
| SAFE-03 | Latency-critical operations can opt into fixed pipelines.                |
| SAFE-04 | Weak model roles can use scaffolded procedures.                          |
| SAFE-05 | Every factory fallback must be marked as such in audit.                  |
| SAFE-06 | User can configure “factory-only” for certain directories or operations. |
| SAFE-07 | Human confirmation must include risk summary and exact command/action.   |

### Acceptance Criteria

* Dangerous actions cannot be executed by autonomous EM alone.
* Factory fallback does not contaminate normal autonomous path.
* Audit clearly shows when strict runbook mode was used.

## 7. Recommended Build Order

### Near-Term Priority

1. Update product docs around “agent engineering organization.”
2. Finish capability schema hardening.
3. Stabilize `.voss team{}`.
4. Implement session-tree budget fan-out.
5. Implement board state machine.
6. Implement Reviewer-A/B.
7. Implement EM loop.
8. Build audit report.
9. Integrate with ADE.

### Why This Order

The session tree must come before the board because the board needs durable nodes.

The team config must come before EM because EM must dispatch only from a declared roster.

The board must come before reviewers because reviewers need card state and artifacts.

Reviewers must come before Done because Done requires independent verification.

Audit should come after the loop exists, but before polishing UX, because audit is the trust layer.

## 8. Success Metrics

### Developer Value Metrics

| Metric                           | Target                            |
| -------------------------------- | --------------------------------- |
| First useful repo task completed | Under 10 minutes                  |
| User can inspect what changed    | 100 percent of runs               |
| User can resume interrupted work | 100 percent of persisted sessions |
| User can identify blocked reason | 100 percent of blocked cards      |
| Unsupported final claims         | Near zero in audited runs         |
| Agent scope violations           | Zero allowed writes outside scope |
| Budget oversell                  | Zero                              |

### Product Quality Metrics

| Metric                     | Target                                 |
| -------------------------- | -------------------------------------- |
| Stub-mode test suite       | Green every PR                         |
| Live smoke tests           | Nightly                                |
| Session replay determinism | 95 percent plus                        |
| Review false-pass rate     | Measured and decreasing                |
| Human sign-off burden      | Fewer but higher-quality interruptions |

## 9. Biggest Risks

| Risk                                      | Mitigation                                                         |
| ----------------------------------------- | ------------------------------------------------------------------ |
| Too much architecture before usable value | Keep `voss do` and `voss chat` vertical slices working every phase |
| Multi-agent becomes theater               | Make audit and verification non-optional                           |
| `.voss` language becomes too broad        | Focus language on coordination, not general programming            |
| Reviewer-A misreads original idea         | Let Reviewer-B fail idea-divergent verification                    |
| EM over-trusted                           | Make ceiling, threshold, roster, and permissions immutable         |
| UI becomes noisy                          | Quiet-by-default panels, reveal on demand                          |
| Budget system is leaky                    | Treat budget as security boundary, not telemetry                   |

## 10. Product Positioning

### Short

Voss is the operating layer for AI engineering teams.

### Developer-Facing

Voss turns AI coding agents into a bounded, inspectable engineering team with roles, memory, tools, budget, scope, review, and audit.

### Differentiator

Most AI coding tools optimize for one agent writing code faster.

Voss optimizes for verified parallel engineering: multiple agents, declared roles, independent review, hard budgets, scoped tools, and replayable audit.

## 11. MVP Definition

The MVP of this philosophy is not full autonomy.

The MVP is:

```text
One human idea
→ one declared team
→ multiple scoped cards
→ budgeted subagents
→ independent review
→ final audit
```

Minimum demo flow:

```bash
voss team check
voss team run "Add password reset flow with tests"
voss board
voss audit latest
```

MVP must prove:

* EM cannot invent roles.
* Workers cannot leave scope.
* Budget cannot be oversold.
* Review is independent.
* Done requires evidence.
* User can understand the run from audit.
