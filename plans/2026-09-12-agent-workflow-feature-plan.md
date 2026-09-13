# Voss features for daily agentic coding

Research date: 2026-09-12. Status: proposal, not an approved replacement for the roadmap.

Updated after inspecting the separate active `Voss-ADE` repository. The initial pass covered only Voss's archived desktop. Read [the ADE integration findings](2026-09-12-ade-harness-integration-findings.md) before selecting implementation work: reliable task/event contracts and client/server context parity now precede the feature sequence below.

Build toward this experience: **Voss knows what I am trying to finish, gives each agent the context it needs, and shows me what actually works.**

Scope: Voss features for a personal coding workflow. Priorities below are hypotheses based on repository evidence and the workflow rules supplied in this conversation; they are not measured productivity findings. Start with one agent. Delegation remains explicitly enabled, and the current Astra/medium policy remains authoritative.

## What already exists

“Implemented” below means source exists and was inspected. It does not mean every provider, UI, or end-to-end path was exercised. Paths are relative to the repository root.

| Capability | Existing implementation and evidence | Product implication |
|---|---|---|
| Agent execution | `voss/harness/agent.py` implements iterative tool execution, context assembly, budget handling, and prior-run context. | Improve the existing harness instead of inventing another agent loop. |
| Instructions | `voss/harness/instructions.py` bundles AGENTS.md/CLAUDE.md with scope, hashes, budgets, and truncation metadata. Global instruction reading defaults off in this module. | A visible explanation of which rules apply can build on existing metadata. |
| Session continuity | `voss/harness/session.py` persists sessions and run records, including goals, assumptions, decisions, changed files, validation, failures, and follow-ups. `agent.py` renders prior-run context. | “Continue my task” should extend these records, not create a separate conversation database. |
| Context compression | `voss/harness/context_allocator.py` keeps recent iterations, digests older ones, and folds earlier work into a compact summary with re-fetch pointers. `agent.py` calls the allocator. | Token management already exists. Improve preservation of task meaning and decisions. |
| Project memory | `voss/harness/memory_store.py` stores turns, ledgers, decisions, conventions, and notes. Retrieval combines keyword search and optional semantic search; keyword fallback exists. | No need to build generic memory storage or vector search from scratch. |
| Memory controls | `voss/harness/memory_cli.py` exposes promotion, forgetting, pinning, inspection, and reindexing. Store supports retrieval telemetry and optional recency/frequency ranking, disabled by default. | Focus on correctness, relevance, and visibility before more ranking machinery. |
| Learning conventions | `voss/harness/conventions.py` extracts candidates with supporting evidence and offers selection on clean exit. | “Remember this correction” is an extension of an existing feature. |
| Code context | `voss/harness/cli.py` has code-recall injection and pinned-memory injection. `voss/harness/code/` supplies code-context machinery. | Build a coherent task briefing over these inputs. |
| Nested agents | `voss/harness/multiagent.py` supplies spawn/steer/status/gather; `session_tree.py` persists agent ancestry and budget envelopes. | Agent trees, delegation, steering, and child budgets are already foundations. |
| Swarm tasks | `voss/harness/swarm_store.py` stores tasks, owned files, dependencies, assignment, and candidate identity in an event-backed store. | Extend task state instead of adding another task manager. |
| Scoped work | Native ownership policies are built in `swarm_store.py` and attached in `server/app.py`. Swarm recall filters results to owned-file paths. | Preserve write boundaries while improving access to relevant supporting information. |
| External workers | `swarm_agents.py`, `swarm_runtime.py`, and `swarm_worktree.py` implement CLI launch, isolated checkouts, ownership reconciliation, and preserved candidates. `/swarm/{swarm_id}/run` invokes the runtime. | This is existing code, not a proposed new multi-provider engine. Real CLI compatibility still needs validation. |
| Coordination | `docs/agent-coordination.md` and `voss/harness/claims.py` describe/implement advisory file claims; server plane supplies messaging and swarm events. | Reuse existing coordination. Advisory claims are not an enforced sandbox. |
| Review and outcomes | `voss/harness/board/machine.py` contains review gates and approval persistence. `bos_events.py`, `bos_ledger.py`, and `bos_decisions.py` provide event/decision records; permissions and swarm runtime emit decisions. | A completion receipt and workflow feedback can reuse existing records. A complete learning product was not established by this audit. |
| Desktop surface | This repository's older desktop lives in `archive/voss-ade/`. A separate active `Voss-ADE` repo implements a Rust/Tauri canvas with terminals, hooks, messaging, workspaces, and a partial optional harness bridge. | Use the active ADE as the client. Its PLAN.md Sprints 11–15 define the task, review, and context/memory surfaces these harness improvements should serve. |

## Concrete gaps found in the inspected paths

1. **Compression preserves activity better than meaning.** `_render_fold_summary` retains iteration counts, tool names, and up to five pointers. It does not itself preserve rejected approaches, unresolved blockers, or decision rationale. Other context blocks may retain some information, so this is a loss risk, not proof that all decisions vanish.
2. **Reading context is coupled to writing scope.** `scoped_recall` keeps hits whose locator resolves to an owned file. Useful interfaces, tests, conventions, and decisions may be outside that set. Relevant reading and permitted editing need separate definitions.
3. **Dependency data does not establish dependency scheduling.** `run_cli_swarm` zips roles with tasks and launches the pairs through concurrent gather. This path does not check `depends_on` readiness before launching. Fix this path before advertising reliable dependent parallel work.
4. **Decomposition is not proven to be connected end to end.** `swarm_coordinator.py` implements structured goal decomposition. Search of active Python code found its definition but no production invocation. Treat natural-language goal → decomposition → approved execution as an integration gap until demonstrated.
5. **External agent launch needs a compatibility audit.** The catalog applies common model/cwd flags across several CLIs. Source presence does not establish that every installed CLI accepts those flags or has equivalent enforcement.
6. **Git behavior needs to match the user's policy.** The external-worker path creates worktrees, reconciles out-of-scope edits, and commits candidates. Those are meaningful actions under the supplied Git rules. The launch experience must make the exact actions reviewable and obtain required authorization before invoking that path. No swarm was launched in this research.

## Research findings that affect the plan

Separate an agent's working context from the durable record of a task. Anthropic recommends small, relevant context, just-in-time retrieval, compaction, and structured notes for long work. **Inference for Voss:** protect the current objective and decisions separately from compressible tool logs. [Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

Subagents can keep noisy exploration out of the main conversation and return concise results. **Inference for Voss:** an explicitly requested investigator or reviewer may be useful even when parallel code editing would not be. [OpenAI subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Claude's team guidance identifies coordination/token overhead and recommends independent work with clear file ownership. **Inference for Voss:** the scheduler must be able to recommend one agent and sequential work, with parallelism reserved for separable tasks. [Claude Code agent teams](https://code.claude.com/docs/en/agent-teams)

Claude distinguishes instruction files from accumulated memory and uses a bounded memory index with topic files. **Inference for Voss:** distinguish mandatory rules, task state, and retrieved advice visibly; retrieving an old note should not turn it into a new instruction. [Claude Code memory](https://code.claude.com/docs/en/memory)

Anthropic's long-running harness experiments found value in progress artifacts, incremental work, and explicit feature verification across sessions. **Inference for Voss:** completion should refer to observable behavior and evidence; a worker finishing is not sufficient. Its Git practices are not adopted automatically here. [Long-running agent harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

These sources support design patterns. They do not establish measured improvements for Voss or this user's workflow.

## Feature plan in plain English

### 1. “Continue exactly where I left off” — first

**Experience:** Reopen a task and see the goal, latest agreed scope, completed work, failed attempts, current blocker, last verified state, and next useful action. Continue without reconstructing the conversation.

**Reuse:** Sessions, run records, prior-context rendering, context allocator.

**Add:** A compact current-task summary updated at meaningful milestones. Preserve user corrections and decisions during compression. On resume, compare relevant file state against recorded evidence; show what changed since the last check. Store proposed next actions separately from authorization.

**Smallest delivery:** One task, one agent, existing CLI/session surface. No dashboard required.

**Acceptance:** After interruption and forced context compression, a fresh session identifies the correct next action, preserves explicit constraints, and does not repeat a recorded failed attempt without a reason. Exercise stale-file and changed-requirement cases.

### 2. “Give this agent the right briefing” — first

**Experience:** Starting a task produces a short briefing: relevant rules, nearest code examples, related interfaces/tests, previous decisions, and permitted edit scope. “Why did you include this?” shows the source and relevance.

**Reuse:** Instruction bundles, code recall, project memory, pins, scoped recall.

**Add:** Separate edit ownership from read relevance. Include approved project conventions and dependencies even when the worker cannot edit their files. Show omitted/truncated inputs. Keep retrieval task-specific and bounded.

**Acceptance:** A worker editing an implementation receives its relevant interface and test pattern outside its edit scope, while remaining unable to write there through the managed path. An unrelated task does not inherit the same briefing wholesale.

### 3. “Remember the correction, retire the old advice” — next

**Experience:** Say “this is the convention now.” Voss presents a short, editable entry with source, scope, and what it replaces. Later sessions retrieve the current rule, with old advice visibly superseded.

**Reuse:** Convention extraction/review, memory provenance, pins, promotion, forgetting, reindexing.

**Add:** Explicit supersession and freshness for decisions and conventions. Distinguish a one-task exception from a durable rule. Suggest updates at the moment of correction instead of relying only on clean exit. Do not promote project knowledge across projects automatically.

**Acceptance:** A corrected convention wins over an older conflicting note; a task-specific exception remains local to that task; changed code triggers revalidation instead of confident reuse of stale advice.

### 4. “Split this work only when it helps” — after continuity

**Experience:** Voss proposes a concrete work split and explains which parts can run together, which must wait, and why one agent may be sufficient. You enable delegation explicitly. Progress shows actual owners and blockers.

**Reuse:** Swarm tasks, coordinator, ownership, session budgets, events, and existing worker isolation.

**Add:** Connect decomposition to execution; implement dependency readiness in the external-worker path; validate worker/task assignment; apply approved model and permission policy before launch. Give every worker the briefing from feature 2 and a result contract: findings, changed files, evidence, unresolved issues.

**Acceptance:** Dependent tasks wait; overlapping edits are ordered or rejected; a failed prerequisite blocks dependents; unauthorized Git operations never launch. Compare independent research/review and independent edits against a single-agent baseline.

### 5. “Show me what works and what needs me” — alongside orchestration

**Experience:** A task finishes with a compact receipt: requested behavior, change summary, checks actually run, observed results, unverified behavior, and any decision requiring you. Candidate-ready, checked, and integrated are distinct states.

**Reuse:** Run validation/failures, board review gates, candidate identity, server events, decision ledger.

**Add:** Bind evidence to the file state it checked; invalidate affected evidence after subsequent edits. Surface blockers as concrete decisions with a recommended next action. Keep ordinary tool activity out of the attention queue.

**Acceptance:** Editing a checked file makes relevant evidence stale. A failed/skipped check cannot appear as passed. An external worker exit cannot imply its candidate is integrated. Require user-visible behavior checks where appropriate, not arbitrary extra tests for every edit.

### 6. “Tell me which workflow actually helped” — later

**Experience:** Voss can say which kinds of tasks benefited from a reviewer or parallel investigation, based on completed local work. Recommendations remain suggestions.

**Reuse:** BOS events and decision ledger, run usage, review outcomes.

**Add:** Small outcome labels tied to decisions: accepted, reworked, reopened, and time spent resolving problems. Compare similar task categories and disclose small samples. Do not train policies or change models/autonomy automatically.

**Acceptance:** Every recommendation links to supporting observations, separates estimates from measurements, and can abstain when evidence is insufficient.

## Delivery sequence and value checks

| Slice | Deliverable | Verify before moving on |
|---|---|---|
| 0: ADE integration contract | Durable task state/events, explicit execution controls, SDK coverage, server context parity | Reconnection cannot cancel work accidentally; replay and current state agree; ADE can inspect the actual briefing and supported actions. See the ADE findings for milestones. |
| A: continuity | Features 1–2 through one existing entry point | Interrupted work resumes correctly; briefing contains needed context without excessive unrelated material. |
| B: trustworthy memory | Feature 3 plus basic completion receipt from 5 | Corrections survive; stale advice and stale validation are visible. |
| C: deliberate orchestration | Feature 4 plus attention queue from 5 | Dependency order, ownership, candidate states, CLI compatibility, and explicit permissions work end to end. |
| D: feedback | Feature 6 | Enough comparable outcomes exist to support a useful recommendation. |

Before implementation, reconcile these slices with existing V18/V19/V21/V23/V25 and BOS plans. Update or extend those contracts where applicable; do not create a parallel roadmap for already-owned behavior.

Use a small repeated set of representative, non-sensitive tasks: interrupted bug fix, changed requirement after compression, implementation following an existing pattern, conflicting old convention, dependent work split, and final review after another edit. Measure re-explanation prompts, repeated exploration, missed constraints, rework, wall time to a verified result, and token usage where observable. Run comparable tasks under the current workflow first. Targets should follow that baseline; no percentage improvement is claimed here.

Defer a new memory engine, an always-on swarm, a large agent-persona catalog, a new coordination bus, team analytics, and learned routing. Use the active ADE's existing surfaces. The first useful product increment is a reconnectable task with reliable continuity and inspectable context.

## Validation performed for this research

- Inspected active source, runtime callers, relevant tests, README, planning documents, and archived desktop placement. Did not inspect personal session contents or credentials.
- Ran `.venv/bin/python -m pytest -q tests/harness/test_agent_packing.py tests/harness/test_swarm_store.py -m 'not live'`: 13 tests passed, exit code 0. Covers packing integration and swarm store behavior; does not prove semantic preservation or full worker execution.
- No live provider runs, external CLI launches, desktop verification, Git writes, or implementation changes. Broader memory/provider behavior is source-inspected, not certified by this test run.
