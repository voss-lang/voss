# Orchestration Plan: Caged Autonomous Eng Team (ADE Orchestration)

> **⊘ SUPERSEDED (2026-06-05) by the V-track.** This O1–O6 design is retained as historical/reference. The canonical orchestration track is now **V0–V12** in `ROADMAP.md`, designed in `docs/ORCHESTRATION_LAYERS.md` (a superset that absorbs M13). Mapping: O1→V4, O2→V3, O3→V5, O4→V6, O5→V7, O6→V9. O6's 6 ready plans re-point to V9. The cage invariants, A/B-split rationale, decision log, and residual-risk analysis below remain valid input to the V-phase SPECs.

**Created:** 2026-05-17
**Status:** ⊘ SUPERSEDED by V-track (2026-06-05). Design converged + stress-tested; folded into V0–V12.
**Track:** O-prefixed phases (O1–O6). Multi-agent orchestration layer on the Voss harness.
**Relationship:** Sibling to `HARNESS-PLAN.md` (single-agent harness) and `MCP-PLAN.md`. Builds on M13 (Multi-agent in Chat — exposes raw `spawn`/`gather`). O-phases add the *caged orchestrator* on top: a board-driven autonomous eng team that cannot escape budget/scope/confidence.
**Source:** Conversation 2026-05-17 — full Socratic decision tree + adversarial stress-test, decision log at bottom.

---

## 1. Thesis

Every autonomous agent-team product today is an unbounded blackbox. Voss already ships the primitives nobody else has: per-call budgets, confidence gates, write-scope locks, replayable session audit. The ADE orchestrator is the demonstration vehicle that makes those legible:

> **A fully autonomous AI engineering team that operates inside a *provable* cage — hard budget, global scope ceiling, an independent judge gating every state transition, and a fully replayable run.** Not "trust the swarm." **"Audit the cage."**

This is **not a pivot**. It is the showcase skin on the harness. The single-agent harness must be boring-solid first; the orchestrator fans it out. No second system. The orchestrator + board + rituals are expressed in `.voss`; the harness owns execution.

---

## 2. Roles

| Role | Identity | Authority | Constraints |
|---|---|---|---|
| **Human** | The user | Describes an idea; final sign-off | Sees the audit, not work-in-flight. No in-flight approvals (autonomous to Done). |
| **Engineering Manager (EM)** | LLM, lead | Full lead-engineer: plans tickets/AC/DoD from the idea, runs the board, mutates cards, dispatches specialists | Cannot rewrite `ceiling`/`p`. Cannot invent agents (selects from declared roster). AC/DoD are *worker scaffolding, NOT the audit bar*. |
| **Engineer roster** | Specialists: backend / frontend / ui / ai (extensible) | Carry out a bounded card | Per-role scope + tool/permission profile. EM selects per task; cannot author its own gating tests. |
| **Reviewer-A** | Independent agent | Re-derives the judging bar from the **original human idea**; authors verification (deterministic tests for code domains; eval harness for AI domain via `voss/eval/`) | Sole owner of bar + verification. Does not render verdicts. |
| **Reviewer-B** | Independent agent, tiered (fast intermediate / strong at →Done) | Renders the confidence verdict: AI slop, errors, correctness | Separate session/model, no shared memory with A or EM. Sees `[artifact, acceptance, repo, original_idea]`. **Blind to EM narrative/plan.** Has explicit authority to fail a card whose A-verification diverges from the idea. |

**Why the A/B split:** "reviewer authors tests" concentrates bar + tests + verdict in one component and silently collapses the →Done double gate into one source. Splitting author (A) from judge (B) restores two genuinely independent sources at →Done and un-blinds calibration telemetry.

**Why the audit bar = original idea (not EM's AC):** EM authors AC/DoD (correct product UX — humans only describe an idea). If the reviewer judged against EM's AC, EM grades its own homework. So AC/DoD guide the worker; the *audit bar* is the immutable human idea, independently re-interpreted by Reviewer-A.

---

## 3. Board (the orchestrator state machine)

The Kanban board is **not a UI metaphor — it is the orchestrator's state machine.**

Columns: `Backlog → Planned → InProgress → InReview → Blocked → Done`

- **Per-column WIP** (e.g. `InProgress: 3`, `InReview: 2`). Surfaces bottlenecks, forces finishing over starting, and backpressures reviewer cost for free (cap InReview WIP = cap concurrent reviewer calls).
- **Confidence gate fires only on transitions with an artifact** (`InProgress→InReview`, `→Done`). Transitions with no artifact (`Backlog→Planned`, `Planned→InProgress`) gate on budget+scope only — confidence over nothing is theater.
- **Tiered reviewer cost:** fast model at intermediate gates, strong model at `→Done`. Safe *because* →Done is double-gated.

### Gate predicates

| Transition | Gate |
|---|---|
| `InProgress→InReview` | `conf(ReviewerB.fast) ≥ p ∧ scope.ok ∧ budget.ok` |
| `InReview→Done` (code) | `conf(ReviewerB.strong) ≥ p ∧ tests.pass ∧ scope.clean` |
| `InReview→Done` (AI/ML) | `conf(ReviewerB.strong) ≥ p ∧ eval.score ≥ threshold ∧ scope.clean` |
| `any→Blocked` | budget exhausted ∨ confidence floor missed ∨ scope violation ∨ retry ceiling hit ∨ timeout |

- **`p` = per-card-risk** (scales with scope × budget × core-file-touch). **Human-declared in `.voss`, EM-immutable.** EM controls risk *inputs* (card scope/budget) — mitigated by routing-rationale + kill-lineage audit, not fully closed (residual).
- **→Done is double-gated, two independent sources.** Reviewer-B cannot ship code that fails A-authored objective checks. For AI cards the deterministic test is swapped for an eval harness so the second source survives in the one domain where slop is hardest to eyeball.
- **Critic loop:** Reviewer-B rejects → card back to InProgress, reviewer notes appended to that card's episodic memory (so retries don't repeat). Bounded by **retry ceiling (≈3) AND budget, whichever hits first → Blocked.**

---

## 4. Cage invariants (the product is these or it is theater)

1. **Budget is a security boundary, not a cost knob.** Parent envelope fans out parent→card. Hard, pre-committed, **non-extendable by the EM**. No "ask for more tokens" path.
2. **Scope has a global ceiling.** Per-card `edit_scope` + a project ceiling; the *union* of all card scopes cannot exceed it. Stops the EM widening blast radius one card at a time.
3. **Confidence is independent.** Self-reported confidence = theater. The number comes from Reviewer-B, never the EM/engineer. The *threshold* `p` is human-set and EM-immutable.
4. **The audit bar is the original idea, not EM-authored AC.**
5. **Engineers cannot author the verification that gates them.** Reviewer-A owns tests/eval.
6. **Liveness is guaranteed.** A reserved, non-spendable drain budget ensures every in-flight card can always reach a verdict (Done or Blocked) even when the main budget is exhausted; column/card timeouts force `→Blocked` to break WIP deadlock.
7. **The session-tree recorder is the human review product**, not telemetry. Human at sign-off reviews a fait accompli — the audit surface IS the UX.

---

## 5. `.voss` team spec (strawman)

The orchestrator is expressed in `.voss`; the harness executes it. `ceiling` and `p` are declared *above* the EM and it cannot rewrite them — the cage is syntax.

```
team Eng {
  ceiling { budget: 200k tokens, scope: src/**, latency: 30m }

  agent em { model: opus, authority: lead, mode: plan }   // Engineering Manager

  roster engineers {                                       // EM dispatches from this
    backend  { model: sonnet, scope: src/api/**,       tools: [fs,test] }
    frontend { model: sonnet, scope: src/web/**,       tools: [fs,test] }
    ui       { model: sonnet, scope: src/components/**, tools: [fs,test] }
    ai       { model: opus,   scope: src/ai/**,        tools: [fs,test,net] }
  }

  agent reviewer_a { derives: bar + verification from original_idea }   // tests | eval; not the judge
  agent reviewer_b { model: opus, judge: true, tiered: true,
                     checks: [slop, errors, correctness],
                     sees: [artifact, acceptance, repo, original_idea] } // EM-narrative-blind

  board {
    columns: [Backlog, Planned, InProgress, InReview, Blocked, Done]
    wip:   { InProgress: 3, InReview: 2 }
    p:     risk_tiered                       // human-declared, EM-immutable
    retry: { ceiling: 3, then: Blocked }     // budget cap also applies
    liveness: { reserve: 10k tokens, card_timeout: 10m }

    gate InProgress->InReview { conf(reviewer_b.fast)   >= p, scope.ok, budget.ok }
    gate InReview->Done(code) { conf(reviewer_b.strong) >= p, tests.pass, scope.clean }
    gate InReview->Done(ai)   { conf(reviewer_b.strong) >= p, eval.score >= t, scope.clean }
  }

  ritual standup { every: 1h, gather(reviewer_b over board) -> semantic.memory }
}
```

Compiles to: enriched `SubagentRegistry` (per-role model/mode/scope/budget/tools) + a board state machine driven by the harness.

---

## 6. Build reality

**"~80% reuse" is false — do not plan against it.** Genuine reuse: `voss/harness/subagents.py` (SubagentSpec/Registry/run_subagent — but no budget/scope/recorder plumbing today), `voss/eval/judge.py` (`Verdict`/`judge_run` + `auth role="judge"` — an *offline* eval judge, repurposed as an *online* gate is a new contract), `voss/harness/edit_scope.py`, `voss_runtime` `spawn`/`gather`/`AgentHandle`.

**Real build surface:**
- Session-tree + budget fan-out in `recorder.py`/`session.py` (the keystone gap)
- `.voss team{}` parser → enriched registry + specialist roster
- Board state machine + per-column WIP + gated transitions
- Reviewer A/B wiring (independent sessions, tiered B, A authors tests-or-eval)
- EM lead-authority loop + specialist dispatch + routing rationale + kill/re-scope lineage
- Per-AI-card eval-harness binding
- Audit/review product + calibration telemetry + reserve/timeout liveness

Substantial multi-phase (O1–O6), not wiring.

---

## 7. Residual risks (named, none fatal, not all closed)

1. **Standup → `semantic.memory` poisoning (Leak 6) — UNADDRESSED.** `gather→memory` has no expiry/correction path; one biased digest compounds. Deliberate open gap, flagged not solved. → O6 scope candidate.
2. **Reviewer-A misread propagates.** A authors bar AND verification from a single reading of the idea. Mitigant is an **invariant that must be written into the spec**: Reviewer-B sees the raw idea and has explicit authority to fail a card whose A-verification diverges from it. If not enforced, A's misread propagates silently.
3. **Human sign-off is overloaded — biggest systemic risk.** Three choices route risk to one human moment: final correctness + misroute detection (routing rationale only caught here) + killed-card review. Degrades to "human reads a lot at the end or the cage is decorative." Mitigation candidate (design-add, not decided): forcing function — mandatory diff of killed cards + misroutes surfaced *before* the approve action is available.
4. **Misroute not caught in-flight.** EM emits `routing_rationale` per card, surfaced first-class in audit, but a misrouted card runs and burns budget before sign-off catches it. Accepted (cheap/late).
5. **LLM-judging-LLM slop detection is itself slop-prone.** Calibration telemetry must cover slop-rejection rate, not just pass/fail. Monitoring requirement, not a structural fix.

---

## 8. Decision log (2026-05-17)

| # | Question | Decision |
|---|---|---|
| 1 | Orchestrator brain | Lives in harness, leverages `.voss` to express the team |
| 2 | Orchestrator archetype | LLM planner agent (EM), full lead authority |
| 3 | Planner board authority | Full lead-engineer (create/kill/re-scope/reassign) |
| 4 | Transition gates | Confidence + budget + scope on every (artifact) transition |
| 5 | Human placement | Final sign-off only (autonomous to Done) |
| 6 | Confidence source | Independent reviewer agent (`judge.py` surface) |
| 7 | Reviewer input | Artifact + acceptance + repo + **original task spec**; EM-narrative-blind |
| 8 | →Done gate | Reviewer + deterministic (tests/scope), reviewer can't override |
| 9 | Reviewer cost | Tiered reviewer model (fast intermediate, strong at →Done) |
| 10 | Critic-loop bound | Retry ceiling (≈3) AND budget, first hit → Blocked |
| 11 | Threshold `p` | Per-card-risk, human-declared, EM-immutable |
| 12 | WIP model | Per-column WIP |
| 13 | Leak 1 (rubric capture) | EM authors tickets/AC/DoD; **audit bar = original idea, Reviewer-A re-derives** |
| 14 | Test owner | Reviewer-A authors verification; engineer cannot modify it |
| 15 | Reviewer concentration | **Split A (bar+verification author) vs. B (independent judge)** |
| 16 | Leak 2 (calibration) | Calibration telemetry + sampled human spot-audit |
| 17 | Leak 3 (planner avoidance) | Killed/re-scoped cards = first-class audit surface |
| 18 | Leaks 4/5 (liveness) | Reserved drain budget + timeout→Blocked escape |
| 19 | Role metaphor | Planner = Engineering Manager; worker = specialist Engineer roster |
| 20 | Misroute | EM declares routing rationale, audited (first-class surface) |
| 21 | AI-card →Done hole | Domain-specific eval gate (Reviewer-A eval harness, reuse `voss/eval/`) |

---

## 9. Phase decomposition → O1–O6

| Phase | Name | Delivers | Depends |
|---|---|---|---|
| **O1** | Session-Tree Substrate + Budget Fan-out | Parent→child session tree in `recorder.py`/`session.py`; per-card budget envelope; reserved non-spendable drain budget; hard non-extendable caps | — (keystone) |
| **O2** | `.voss team{}` Spec + Specialist Roster | `team{}` parser → enriched `SubagentSpec` (model/mode/scope/budget/tools); EM-immutable `ceiling`/`p`; backend/frontend/ui/ai roster | O1 |
| **O3** | Board State Machine + Gated Transitions | Columns, per-column WIP, gate predicates, artifact-only confidence gating, →Done double gate, critic-loop ceiling+budget, timeout→Blocked liveness | O1, O2 |
| **O4** | Reviewer A/B Split | Reviewer-A (idea→bar + tests/eval, `voss/eval/` reuse); Reviewer-B (independent tiered judge, slop/errors/correctness, idea-divergence authority) | O2, O3 |
| **O5** | Engineering Manager Loop | EM full-authority autonomous loop; idea→tickets/AC/DoD; specialist dispatch + routing rationale; kill/re-scope lineage; cage-bounded board mutation | O1–O4 |
| **O6** | Audit Product + Calibration + Liveness Hardening | Session-tree review surface; killed-card + routing-rationale first-class; calibration telemetry + slop-rejection spot-audit; reserve/timeout wiring; sign-off forcing function; Leak-6 mitigation candidate | O5 |
