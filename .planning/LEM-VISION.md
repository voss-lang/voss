# LEM — Large Event Model (Vision)

**Status:** Vision / north-star. NOT a committed near-term phase.
**Created:** 2026-06-18
**Owner stance:** docs-only. No code, no model training implied by this doc.

> A LEM is a foundation model over the **engineering event stream**. The analogy is
> `LLM : text-tokens :: LEM : BOS3-events`. It is the long-horizon payoff of the v0.2
> Behavioral OS Foundation — built only *after* the decision/outcome corpus exists.
> PROJECT.md is explicit that v1 is **not** a foundation model or online RL; this doc
> records where the foundation-model ambition lives so the data contracts stay ready
> for it without pulling the model forward.

---

## 1. What a LEM is

A self-supervised sequence model trained on ordered BOS engineering-event sequences
(a task lineage: `task → session → swarm.assign → file edits → review → CI → deploy →
incident`). Closest real-world analogs — **steal these playbooks, not the LLM-over-prose one:**

- **EHR foundation models** (BEHRT, Med-BERT, Foresight) — transformers over per-patient
  event timelines. A BOS *trace* ≈ a patient timeline.
- **Sequential-recommendation transformers** (SASRec, BERT4Rec, generative recommenders) —
  next-event prediction over user-action sequences.
- **Log/event anomaly transformers** — perplexity-as-anomaly over system event logs.

### Outputs (downstream tasks)
1. **State embedding** — a dense vector for the current engineering state of a
   task / team / repo. Replaces hand-crafted policy features.
2. **Outcome prior** — `P(clean_merge / rework / revert / failed_validation /
   escaped_defect / incident)` + a cycle-time distribution, predicted from decision-time
   state. A learned prior for the BOS5 reward model.
3. **Trajectory generation** — autoregressive next-event sampling → counterfactual
   simulation ("what if we routed to agent B / reduced review depth").
4. **Surprise / anomaly** — high perplexity (low-likelihood event) as a self-supervised
   guardrail signal, complementing BOS5 D-10 tension pairs.

---

## 2. Why BOS specifically needs it

BOS's hard problem is not the UI — it is the **feature representation and reward model**
feeding delegation/review/validation policies. A LEM attacks exactly that surface:

| BOS pain | LEM contribution | Consumer phase |
|---|---|---|
| Policies need features → hand-crafted, brittle | learned state embedding replaces hand features | BOS13, BOS14 |
| Reward model cold-starts with no logged outcomes | LEM outcome head = prior before enough data | BOS5, BOS15 |
| Offline eval can't observe counterfactuals | AR generation simulates un-taken decisions | BOS15 |
| Guardrails are purely rule-based | LEM perplexity = self-supervised anomaly signal | BOS5 D-10, BOS-GOV-04 |

It de-risks BOS13–16. It is the payoff, not the foundation.

---

## 3. The corpus IS the BOS data substrate (key realization)

**The BOS3 / BOS4 / BOS5 contracts already being specced ARE the LEM training corpus.**
Nothing new is needed at the data layer — only three properties must stay honest:

1. **BOS3 D-04 trace/correlation id = the sequence key.** It is literally the "document"
   boundary for a training sequence. Already specced.
2. **BOS3 D-02 bitemporal + as-of = the no-leakage guard during training.** A sequence
   prefix used to predict an outcome contains only events with `event_time ≤ decision_time`;
   outcomes are appended strictly as later tokens and masked for the prediction task. The
   bitemporal model *is* the leakage guard. Already specced.
3. **BOS5 outcomes = appended terminal tokens.** BOS5 D-02 (revisable, append-only) +
   D-09 (multi-horizon, recomputable) means outcome events slot in as later sequence
   tokens and become prediction targets at horizon-h. Already specced — and a perfect fit.

Corollary: we are building the corpus correctly without yet naming the consumer. The job
of *this* doc is to keep it that way, not to build the model.

---

## 4. Design axes (decisions a future LEM SPEC would lock)

| Axis | Options | Current lean + rationale |
|---|---|---|
| **Sequence unit** | per-trace / per-actor / per-repo / per-team | **per-trace atomic** (= BOS3 trace id); actor + repo as context tokens. Per-actor timelines risk individual ranking (PROJECT.md bans) — keep actor signal team-aggregated or privacy-gated (BOS6). |
| **Tokenization** | event-type vocab; continuous-field handling | event_type = vocab token; continuous fields (cycle_time, diff size, file count) = quantized bins **+** time-delta encoding (events are unevenly spaced — Med-BERT / time-aware style). Reuse BOS5's quantization choices so corpus tokens == contract bins. |
| **Training objective** | masked-event (BERT) / autoregressive (GPT) / hybrid | **AR primary** — only AR yields counterfactual simulation, the BOS15 prize. Optional masked head for embeddings. |
| **Outcome head** | single head / multi-task per reward objective | multi-task: one head per BOS5 reward objective (D-07) + cycle-time regressor; horizon-conditioned (D-09). |
| **Special tokens** | — | `[TRACE_START]`, `[DECISION]` (a BOS4 decision point), `[OUTCOME]` (a BOS5 outcome), `[MASK]`. |
| **Scale path** | native transformer now / LLM-bridge / tabular-first | **staged** (§5) — early corpus is thousands of traces, not billions of tokens. |

---

## 5. Honest staging (do not skip steps)

```
v0   heuristic features              BOS13/14    now — no learning at all
v1   tabular/GBM outcome model       BOS15/16    on frozen feature snapshot (BOS4 D-03)
v1.5 LLM-bridge outcome predictor    BOS16       serialize event seq → text → fine-tune/
                                                 in-context an existing LLM (borrow priors
                                                 while corpus is small)
v2   small native event transformer  LEM phase   first real LEM — fits small data
v3   scaled LEM + counterfactual sim LEM phase   once corpus threshold is hit
```

Gate every step on PROJECT.md Safety: no LEM-derived signal raises autonomy / cuts review /
skips validation without BOS15 offline eval + guardrail clearance.

---

## 6. Roadmap placement

LEM is **not** a near phase. Two cheap moves keep the substrate ready (both wired now):

- **BOS3 — LEM-tokenizability note (added to BOS3-CONTEXT deferred).** The event schema must
  be tokenizable: every continuous field has a quantization story, and the trace/correlation
  id is a clean, complete sequence key. Mostly already true (D-02/D-04); made export-explicit.
- **BOS16 — sequence-export contract (note added to ROADMAP, to fold in when BOS16 is
  specced under BOS-RL-01).** Broaden "the lab consumes exported event/decision/outcome data"
  to define a **point-in-time sequence export**: per-trace, as-of-correct, outcomes appended
  as terminal tokens. One export, two consumers — the contextual bandit (BOS16/BOS-RL-02) AND
  the LEM.
- **Deferred dedicated phase** — a future **BOS19+ "Large Event Model"** phase, opened only
  when corpus size justifies it (mirrors "bandits/RL only after enough logged decisions").

---

## 7. LEM-specific landmines

- **Goodhart on the LEM** — if a policy optimizes LEM-*predicted* reward, the LEM becomes a
  gameable proxy. BOS5 D-10 tension-pair guardrails must apply to predicted reward, not only
  observed.
- **Distribution shift** — policies change behavior → corpus drifts → LEM goes stale.
  Re-export + offline-eval before any redeploy (no online learning — Safety constraint).
- **Counterfactual extrapolation** — the AR simulator predicts into action space never
  observed (the un-taken delegation). Must emit confidence and lean on BOS15 holdouts/shadow,
  never trusted blind.
- **Actor surveillance** — actor-timeline modeling risks individual ranking (PROJECT.md bans).
  Keep embeddings team-level or privacy-gate per BOS6.
- **Sparse corpus early** — external events (CI/deploy/incident) are unintegrated until BOS12,
  so the first LEM trains mostly on harness/swarm/task events. Scope that honestly.
- **Small-data overfit** — start tabular (v1), graduate to a transformer (v2) only when corpus
  size supports it; the LLM-bridge (v1.5) covers the gap.

---

## 8. Canonical references

- `.planning/PROJECT.md` — Learning direction ("v1 is not a foundation model or online RL");
  Constraints §Data (point-in-time, no leakage), §Safety (no autonomy increase without offline
  eval + guardrails), §Trust (team-level, no individual ranking).
- `.planning/phases/BOS3-engineering-event-schema/BOS3-CONTEXT.md` — D-02 (bitemporal/as-of =
  leakage guard), D-04 (trace id = sequence key). See its Deferred §LEM-readiness note.
- `.planning/phases/BOS4-decision-ledger-schema/BOS4-CONTEXT.md` — D-03 (frozen feature
  snapshot = the v1 tabular feature row), D-04 (outcomes joined after-the-fact).
- `.planning/phases/BOS5-outcome-labels-and-reward-model/BOS5-CONTEXT.md` — D-02/D-09
  (revisable, multi-horizon outcomes = appended targets), D-07 (multi-objective reward =
  multi-task heads), D-10 (tension pairs apply to predicted reward too).
- `.planning/ROADMAP.md` — BOS-prefixed phases §"LEM (Large Event Model) readiness";
  BOS15 (offline eval), BOS16 (RL lab boundary, BOS-RL-01..03).
- `.planning/REQUIREMENTS.md` — BOS-RL-01 (lab consumes exported event/decision/outcome data —
  the export this doc extends), BOS-RL-02 (counterfactual eval + guardrail gates), BOS-RL-03
  (online learning is future, gated).

---

*This is a vision doc. It locks no requirements and authorizes no model work. It exists so the
BOS data contracts stay LEM-ready and the foundation-model ambition has a documented home.*
