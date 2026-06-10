# Phase V18: Budget-Aware Context Allocator (Token Optimization) — Specification

**Created:** 2026-06-10
**Ambiguity score:** 0.19 (gate: ≤ 0.20)
**Requirements:** 8 locked (VOPT-01..08)

## Goal

The harness assembles its LLM request by replaying **every** prior iteration in full on **every** loop entry (`voss/harness/agent.py:708-716`), so a long `voss do` run's input grows without bound in iteration count. V18 inserts a **budget-aware context allocator** at that one chokepoint: it packs the variable (non-cached) message region under a token ceiling by rendering recent iterations in full, older ones as one-line digests, and ancient ones as a single folded summary — leaving re-fetch pointers to the **existing** M10 code-intel / F2 search surfaces instead of carrying detail forever. It preserves the T4 cached prefix, recompacts only at hysteresis thresholds (so the prompt cache stays warm), and writes a falsifiable `token-savings.jsonl` ledger gated by an M5 quality-preservation eval. Zero new retrieval substrate: V18 **consumes** M10/F2/F3/T4, it does not rebuild them.

## Background

Voss already owns most of the token-spend substrate; V18 is the one missing layer (the packer), not a re-build:

- **Full-replay assembly (the gap).** Each loop entry rebuilds `messages` as `[cached sys_blocks, rider, user_prompt]` then appends `_serialize_iter_for_replay(prior)` for **all** prior iterations (`voss/harness/agent.py:708-716`). `_serialize_iter_for_replay` (`agent.py:431-458`) renders every iteration identically — plan JSON + per-tool-result lines truncated to 400 chars (`agent.py:454-456`) — regardless of age. The only existing bound is `HISTORY_WINDOW = 30` (`agent.py:213`) on the pre-loop history block (`agent.py:607`), which does not cap the per-iteration replay tail.
- **Budget is tracked, not packed.** `token_budget` defaults to 60_000 (`agent.py:500`); the loop tracks `tokens_used` and **halts** when the budget is spent (`agent.py:1008-1009`) but never trims context to *fit* a ceiling. `_default_token_count(text, model=...)` (`agent.py:73`) already exists for estimation.
- **Caching prefix exists (T4 / CACHE-01, shipped).** The static prefix (voss.md + cognition + principles + project index + prior context + loop system) is marked `cache_control: ephemeral` (`agent.py:363-395`, breakpoint at `agent.py:393-394`). `IterationRecord` records `cache_creation_input_tokens` / `cache_read_input_tokens` (`voss/harness/session.py:115-121`). Naive per-turn rewriting of the tail would defeat any tail caching — packing must be cache-coherent.
- **Retrieval exists (M10, shipped).** `voss/harness/code/` provides the project index + `code_search`/`find_definition`/`find_references` (`service.py`, `index.py`, `context.py`) and the `## Project Index` auto-injection (≤1500 tokens). **F2 Hybrid Semantic Search** (BM25+vector RRF, ready-to-execute) extends this. V18 re-fetches through these; it adds no index.
- **Budget telemetry exists (F3, shipped).** `recorder.py` emits a budget OSC (`_emit_budget_osc`, `recorder.py:98-127`) and a context OSC (`_emit_context_osc`, `recorder.py:130-140`). These **report** tokens used vs limit; neither records *what packing saved* (original vs packed).
- **Tool output caps exist.** `SHELL_OUTPUT_CAP_BYTES = 30720` truncates shell/file reads (`voss/harness/tools.py:22,154-155,308-309`). V18 does not change these.

Origin: competitive teardown of an external Electron+Rust ADE ("Plyrium Forge") whose paywalled `token_savings` feature is a code-RAG index + per-agent token-budget context packer + a `token-savings.jsonl` ledger feeding many small worktree-isolated agents. Voss already has the index (M10/F2), the budgets (F3/agent), and small agents (V4/V8). The **only** missing primitive is the budget-aware packer + its ledger. Hard limit inherited from that analysis: V18 can only reduce **future** turns — tokens already sent are billed and unrecoverable.

## Requirements

1. **VOPT-01 — Context allocator at the assembly chokepoint**: a pure, testable packer builds the variable (non-cached) message region under a token ceiling, replacing the unconditional full replay.
   - Current: `agent.py:708-716` appends every prior iteration's (assistant plan + user tool-results) on every loop; grows unbounded with iteration count; only the per-result 400-char cap applies (`agent.py:454-456`), no whole-region ceiling.
   - Target: a `ContextAllocator` computes `packing_budget = token_budget − reserve(cached_prefix_est + rider + user_prompt + completion_headroom)` and selects/renders replay entries to fit, estimating with `_default_token_count` (`agent.py:73`). It is a pure function of (prior iterations, budget, profile) — no provider call, no I/O — and is unit-tested in isolation. Assembly calls it to produce the post-prefix message list.
   - Acceptance: with 50 synthetic prior iterations the assembled non-cached region is ≤ ceiling; with ≤ the recent-full tier size it is byte-identical to today's output (no-op below threshold); the allocator runs and is asserted with no provider and no filesystem.

2. **VOPT-02 — Iteration-age decay (tiered replay rendering)**: recent iterations render in full, older as one-line digests, ancient folded into one rolling summary.
   - Current: `_serialize_iter_for_replay` (`agent.py:431`) renders every iteration identically regardless of age; the existing `_summarize_prior_iters`-style digest (`agent.py:~420-428`) is used only for the rider, not the replay tail.
   - Target: three tiers — last **K** iterations full (current rendering); iterations K..M → one-line digest (`Iter i: <n> tools, <outcome/snippet>`); older than **M** → folded into a single "Earlier work summary" block. Tier boundaries are profile-driven (VOPT-06). The most recent iteration is always full. Digesting is **structural/extractive** (counts, names, first/last lines) — no LLM summarization call by default (that would spend tokens to save tokens; see Constraints).
   - Acceptance: a golden render test over a 20-iteration history shows full/digest/folded regions at the configured boundaries; total estimated tokens are strictly ≤ full replay and decrease as history grows; the newest iteration is rendered in full in every case.

3. **VOPT-03 — Cache-coherent packing (preserve the T4 breakpoint; recompact on hysteresis)**: packing never rewrites the cached static prefix and recompacts tier boundaries only at thresholds, so the cache stays warm.
   - Current: T4 marks the static prefix `cache_control: ephemeral` (`agent.py:363-395`); the replay tail is uncached and rebuilt every loop. Per-turn rewriting would invalidate tail caching.
   - Target: the allocator (a) treats `sys_blocks` (`agent.py:709`) as immutable — never repacks the cached prefix; (b) packs only the variable region; (c) holds a stable packing across turns and **recompacts tier boundaries only when estimated usage crosses a high-water mark** (e.g. ≥ 80% of `packing_budget`), then holds until a low-water mark — so steady-state turns extend the replay tail append-only rather than rewriting it; (d) MAY place a second `cache_control` breakpoint at the stabilized replay prefix.
   - Acceptance: across a 10-iteration run that stays under the high-water mark, the packed replay prefix is append-only (the stable region's hash is unchanged turn-over-turn); a recompaction event fires only on the high-water crossing; steady-state turns show `cache_read_input_tokens` dominating in `IterationRecord` (`session.py:115-121`).

4. **VOPT-04 — Eviction pointers via existing retrieval (reuse, don't rebuild)**: when detail is dropped, leave a machine-actionable re-fetch pointer to M10/F2 — V18 stores no extra context and adds no index.
   - Current: dropped/truncated tool output is simply lost (`tools.py` 30KB cap appends `<truncated…>`; replay 400-char cap discards the remainder).
   - Target: when the allocator digests or folds an iteration whose tool results referenced files/symbols, it records a compact pointer (path + symbol or line span) and renders a one-line hint (e.g. `↻ re-fetch via code_search("…") / find_definition(…)`) so the model recovers detail on demand through `voss/harness/code/service.py` (or F2 hybrid search). V18 adds **no** new index, embedding store, vector backend, or persistence schema.
   - Acceptance: a folded iteration that read `foo.py:10-40` yields a pointer the agent can act on in a follow-up step; coherence inspection confirms the V18 diff introduces no index/embedding/search-backend code and imports `voss/harness/code/` read-only.

5. **VOPT-05 — Savings ledger (falsifiable measurement)**: per-turn original-vs-packed token estimates are persisted and surfaced honestly.
   - Current: F3 emits a budget OSC (used vs limit, `recorder.py:98-127`); nothing records original-vs-packed, so any "saved N%" claim is unverifiable.
   - Target: each assembled turn appends one JSONL record to a session-scoped `token-savings.jsonl` under `.voss/`: `{iter, original_tokens_est, packed_tokens_est, method, cache_read_tokens}`. `/cost` and the F3 budget surface gain one honest line — `context packed: X→Y (−Z%)` — sourced from the ledger. Numbers are explicitly labeled estimates (from `_default_token_count`), reconciled against provider-reported usage when available, and `packed ≤ original` always (no phantom savings).
   - Acceptance: a multi-iteration run writes a ledger with plausible monotone entries; `/cost` prints the savings line; with packing disabled the ledger records `original == packed` (zero reported savings); no record ever reports `packed > original` or savings exceeding `original_tokens_est`.

6. **VOPT-06 — Config, escape hatch, hermetic default**: packing is configurable, force-disable-able, and deterministic for eval; default is conservative and opt-in-safe.
   - Current: `ctx(budget:)` exists (`agent.py:516`); no packing configuration.
   - Target: a `.voss/` config surface (e.g. a `[context]` block / `context.yml`) controls enable, tier sizes (K/M), and high/low-water thresholds; a `--no-pack` CLI flag + env override force-disable packing for hermetic M5 eval and as an escape hatch. The **default profile is conservative** (large recent-full tier, high thresholds) so short runs are unchanged and the behavior change is opt-in-safe. When disabled, assembled `messages` are byte-identical to the pre-V18 path.
   - Acceptance: `--no-pack` yields byte-identical `messages` to the locked pre-V18 FakeProvider golden; enabling via config alters only the variable region (cached prefix bytes unchanged); the default profile leaves runs at or below the recent-full tier size unchanged.

7. **VOPT-07 — Quality-preservation eval (the honest savings number)**: prove packing cuts tokens without regressing task success.
   - Current: M5 eval (golden tasks; success rate + mean cost; `voss eval`) exists but does not exercise packing.
   - Target: an M5 eval variant runs the golden suite packing-on vs packing-off; the gate is **success rate not regressed beyond a locked tolerance** while mean input tokens drop measurably. The savings % is an eval **output**, not a marketing figure. A deliberately over-aggressive profile that regresses success must be caught by the gate (the gate must bite).
   - Acceptance: the eval report shows packing-on success ≥ packing-off success − tolerance, with mean input-token reduction recorded; a too-aggressive profile that drops a golden task fails the gate, demonstrating it is enforced rather than decorative.

8. **VOPT-08 — Coherence guard**: V18 adds no retrieval/index/budget substrate and keeps the core loop working every wave.
   - Current: M10 code intel (shipped), F2 hybrid search (ready), F3 budget viz (shipped), T4 caching (shipped) already exist.
   - Target: the V18 diff contains no new search index, embedding store, or vector backend (consumes M10/F2); no second budget/cost system (extends F3 + the existing `agent.py` counters); no change to the T4 cached-prefix bytes when packing is disabled; no frozen-schema drift and `crates/` untouched; `voss do` and `voss chat` pass on every wave (PRD §9 top risk).
   - Acceptance: diff inspection — no new index/embedding/vector dependency; `recorder.py` budget-OSC shape unchanged; the cached-prefix golden is byte-identical under `--no-pack`; the full harness suite is green at each wave boundary.

## Boundaries

**In scope:**
- A pure `ContextAllocator` packing the variable message region under a ceiling at the `agent.py:708` chokepoint
- Iteration-age decay (full / digest / folded tiers) for the replay tail, structural/extractive by default
- Cache-coherent recompaction (preserve T4 prefix; hysteresis thresholds; optional second breakpoint)
- Eviction pointers that re-fetch through existing M10 `code/` tools (and F2 when present)
- Session-scoped `token-savings.jsonl` ledger + an honest `/cost` + F3 savings line
- Config surface + `--no-pack` escape hatch + conservative default profile
- An M5 packing-on-vs-off quality-preservation eval with a biting gate
- A coherence guard proving no duplicated index/budget substrate

**Out of scope:**
- Any new code index, embeddings, vector store, or search backend — M10 owns the index, F2 owns hybrid search (V18 consumes them)
- LLM-based summarization of context as a *default* — spending model calls to compress can defeat the savings; an optional `summarize` profile may be specced later, not required here
- New context-pane UI — F4 Visual Context Heatmap owns in-context/compressed-file rendering; V18 emits the numbers, F3/F4 render them
- Changing tool-output caps (`tools.py` 30KB) or `HISTORY_WINDOW`
- Provider exact-tokenizer integration — estimates via `_default_token_count` are sufficient; reconcile against reported usage when present
- Cross-session / cross-agent shared context packing — single run's assembly only
- Retroactive savings — only future turns are affected; already-sent tokens are billed (set expectation, do not claim otherwise)

## Constraints

- **Cache discipline:** the T4 `cache_control` static prefix (`agent.py:363-395`) is never repacked; packing applies only to the variable region; recompaction is threshold-gated (hysteresis), not per-turn, so the prompt cache stays warm. Caching beats pruning unless pruning is large or done at stable boundaries — V18 honors this.
- **Cheap by default:** digesting/folding is structural/extractive (counts, names, head/tail) — **no LLM summarization call on the default path**.
- **Opt-in-safe:** the default profile leaves short runs unchanged; `--no-pack` produces byte-identical `messages` to the pre-V18 baseline (locked FakeProvider golden).
- **Reuse, don't rebuild:** re-fetch goes through `voss/harness/code/` (M10) / F2; no new index, embedding, vector, or persistence substrate; no new heavyweight dependency.
- **Honest numbers:** savings are labeled estimates from `_default_token_count`, reconciled with provider usage when available; `packed ≤ original` always; the ledger never reports phantom savings.
- **Falsifiability gate:** no savings profile ships without passing the VOPT-07 quality eval; a profile that regresses a golden task is rejected.
- **No frozen-schema drift; `crates/` untouched; `voss do`/`voss chat` working every wave** (PRD §9 top risk).

## Acceptance Criteria

- [ ] `ContextAllocator` packs 50 synthetic iterations to ≤ ceiling; ≤ recent-full-tier input is byte-identical to pre-V18; allocator tested pure (no provider, no fs)
- [ ] 20-iteration golden render shows full/digest/folded tiers at configured boundaries; newest iteration always full; total tokens strictly ≤ full replay
- [ ] Under the high-water mark the packed replay prefix is append-only (stable-region hash unchanged turn-over-turn); recompaction fires only on the high-water crossing
- [ ] Steady-state turns show `cache_read_input_tokens` dominating in `IterationRecord`
- [ ] A folded iteration emits an actionable re-fetch pointer resolvable via `code_search`/`find_definition`; V18 diff adds no index/embedding/vector code
- [ ] A run writes session-scoped `token-savings.jsonl` with `packed ≤ original`; `/cost` prints `context packed: X→Y (−Z%)`; `--no-pack` run records `original == packed`
- [ ] `--no-pack` yields byte-identical `messages` to the locked pre-V18 golden; cached-prefix bytes unchanged when packing toggled
- [ ] M5 packing-on vs off: success rate ≥ off − tolerance with mean input-token reduction recorded; an over-aggressive profile fails the gate (gate bites)
- [ ] Coherence: no new index/embedding/vector dep; `recorder.py` budget-OSC shape unchanged; full harness suite green; `crates/` + frozen schemas untouched

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                 |
|--------------------|-------|------|--------|----------------------------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Single chokepoint (`agent.py:708`); reuse-not-rebuild pre-decided     |
| Boundary Clarity   | 0.86  | 0.70 | ✓      | M10/F2/F3/F4/T4 perimeter explicit; no-new-substrate locked           |
| Constraint Clarity | 0.78  | 0.65 | ✓      | Cache discipline, cheap-default, falsifiability locked                |
| Acceptance Criteria| 0.71  | 0.70 | ✓      | 9 pass/fail criteria; tier values + thresholds defer to discuss       |
| **Ambiguity**      | 0.19  | ≤0.20| ✓      | Open knobs: K/M tier sizes, water marks, ledger path, config shape    |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Authored Decisions (pre-discuss)

Derived from the Plyrium Forge teardown + the prior token-optimization analysis, not yet an interview. Discuss-phase locks the open knobs.

| Source                | Decision locked                                                                                   |
|-----------------------|---------------------------------------------------------------------------------------------------|
| Teardown (reuse)      | V18 consumes M10/F2 retrieval + F3 budget + T4 caching; adds **no** index/embedding/budget substrate |
| Analysis (caching)    | Cache-coherent: never repack the T4 prefix; recompact on hysteresis, not per-turn                  |
| Analysis (cost)       | Structural/extractive digesting by default; LLM-summarization is opt-in, not required              |
| Analysis (honesty)    | `token-savings.jsonl` ledger + `packed ≤ original` + M5 quality gate make savings falsifiable      |
| Simplicity / surgical | One chokepoint (`agent.py:708`); `--no-pack` byte-identical; conservative default profile           |
| Hard limit            | Only future turns optimized; already-sent tokens unrecoverable — set expectation, never overclaim   |

## Open knobs for discuss-phase

- Recent-full tier size **K** and digest-cutoff **M** (defaults + per-profile)
- High/low-water marks for recompaction hysteresis
- Ledger location (per-session vs project-root) + retention
- Config shape (`context.yml` vs a `[context]` block in existing config) + `ctx(budget:)` interaction
- Whether to place the optional second `cache_control` breakpoint in V18 or defer
- Exact `/cost` + F3 savings-line wording

---

*Phase: V18-budget-aware-context-allocator-token-optimization*
*Spec created: 2026-06-10*
*Next step: /gsd-discuss-phase V18 — lock K/M tier sizes, water marks, ledger path, config shape, second-breakpoint decision*
