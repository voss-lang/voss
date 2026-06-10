---
title: E-track exploration decisions — internal proof suite (e2e + evals)
date: 2026-06-10
context: /gsd-explore session; origin = captured todo 2026-06-10-discuss-e2e-automated-testing-and-evaluations-phase (now completed/folded into E-track)
---

# E-track: Internal Proof Suite — decisions

Purpose: prove the product (model + functionality) actually works end-to-end — not just that unit tests pass. Motivated by false-green history (scaffold tests passing without real behavior, stale sentinels).

## Locked decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Model backend | **Subscription-backed flagship models via existing voss auth** (`--auth=codex` ChatGPT sub, /models routing). Ollama = optional fallback only. | Real models user actually uses, $0 marginal spend, reuses existing auth resolution. Ollama rejected as primary: weak models make failures ambiguous (model vs product). |
| Judging | **Hybrid** — deterministic gates (file exists, tests pass in target repo, diff applies, exit code) for pass/fail; LLM-judge quality scoring on top. | Agentic outcomes fuzzy; deterministic-only misses quality, judge-only untrustworthy. M5's judge_run plan already pointed here. |
| Cadence | **On-demand only, internal-only.** Make target / dev verb. Never shipped, no packaging, no public docs. | Sub rate limits + needs Ben's auth → can't be CI-default or user-facing. |
| Environments axis | **Runtime surfaces** (CLI verbs, server plane, SDK, TUI, voss-app) × **target repo shapes** (Python, Rust, TS). NOT an OS/clean-machine matrix. | What "autonomous testing across environments" meant. |
| Team rollout observability | **Keep local eval artifacts canonical; add LangSmith only as an optional export/trace adapter if Voss rolls out to an engineering team.** | Team usage likely needs shared dashboards, trace comparison, annotation, and evaluator calibration. LangSmith fits that, but must not own pass/fail semantics, deterministic gates, auth, caching, or local reproducibility. |
| M5 fate | **Superseded into E-track** (O→V pattern). EVAL-01..05 absorbed by E1/E2. M5-06 (packaging smoke) already shipped, stays as-is. | M5's golden tasks + `voss eval` CLI + judge are E-track seed material; one home for proof work. |

## Phase sketch (E1–E5)

- **E1: Eval substrate** — suite loader, TaskSpec, runner, JSONL results + summary, hybrid judge, subscription-auth model wiring, per-run budget/turn cap. Absorbs M5-01..04.
- **E2: Golden tasks × repo matrix** — py/rust/ts fixture repos; agent proves cognition + edits per project shape. Absorbs M5-05.
- **E3: Surface e2e** — CLI verbs + server plane driven end-to-end with real model inference.
- **E4: SDK proof** — `voss.harness` / `voss_runtime` public API exercised as a real consumer.
- **E5: TUI + voss-app autonomous driving** — hardest; Tauri WebDriver impossible on macOS (known constraint from A2), needs different approach.

## Team rollout note

If E-track becomes a shared engineering-team workflow, add a **non-canonical LangSmith export path** after E1 is stable:

- Local source of truth stays `.voss/eval/<run>/runs.jsonl` + `summary.md`.
- Export can attach LangSmith trace/run URLs back into local rows.
- Export is opt-in (`--export langsmith` / env), internal-only, and optional dependency-gated.
- LangSmith is for shared observability, trace inspection, dataset/annotation workflows, evaluator calibration, and run comparison — not for deterministic gates or response caching.
- Live E-track runs should continue measuring current model behavior; replay/cassettes stay limited to hermetic tests.

## Caveats accepted

- Sub usage caps: small suite + per-run budget cap; on-demand keeps burn low.
- Only runs on machines with Ben's auth — fine, internal-only.
- Nondeterministic outputs: hybrid judging + success-rate-over-N runs.
- Codex backend-api quirks already handled (no temperature/max_tokens, gpt-5.x only).
- LangSmith/team dashboard support is useful if this becomes multi-user, but it is a later adapter and not required for E1.

## Open questions (for E1 spec/discuss)

- Per-run budget/turn cap defaults so a suite run can't eat weekly sub limits.
- Judge model routing — judge also rides subscription auth? Same model as actor or different?
- How E-track relates to existing `tests/e2e/` (pytest, presumably mocked/stubbed) — keep both layers or graduate some into E-track.
- V18-05's "M5 packing-on-vs-off quality gate" now consumes E1 substrate instead of M5.
