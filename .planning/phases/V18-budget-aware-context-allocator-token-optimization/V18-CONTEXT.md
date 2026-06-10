# Phase V18: Budget-Aware Context Allocator (Token Optimization) - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

V18 inserts a **budget-aware context allocator (token packer)** at the harness's single message-assembly chokepoint (`voss/harness/agent.py:708-716`), which today replays every prior iteration in full on every loop entry — unbounded in iteration count. The allocator packs the variable (non-cached) region under a token ceiling: recent iterations full, older as one-line digests, ancient folded into a rolling summary, with re-fetch pointers to existing retrieval. **Reuse-not-rebuild:** consumes M10 code-intel + F2 hybrid search + F3 budget telemetry + T4 caching; adds no index, embeddings, or second budget system. Reduces only **future** turns — already-sent tokens are billed.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked (VOPT-01..08).** See `V18-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V18-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Pure `ContextAllocator` packing the variable message region under a ceiling at the `agent.py:708` chokepoint
- Iteration-age decay (full / digest / folded tiers), structural/extractive by default
- Cache-coherent recompaction (preserve T4 prefix; hysteresis thresholds; optional second breakpoint)
- Eviction pointers that re-fetch through existing M10 `code/` tools (and F2 when present)
- Session-scoped `token-savings.jsonl` ledger + honest `/cost` + F3 savings line
- Config surface + `--no-pack` escape hatch + conservative default profile
- M5 packing-on-vs-off quality-preservation eval with a biting gate
- Coherence guard proving no duplicated index/budget substrate

**Out of scope (from SPEC.md):**
- New code index / embeddings / vector store / search backend — M10/F2 own it
- LLM-based summarization as a *default* path — opt-in profile, later
- New context-pane UI — F4 heatmap renders; V18 emits numbers
- Changing `tools.py` 30KB caps or `HISTORY_WINDOW`
- Provider exact-tokenizer integration — estimates suffice
- Cross-session / cross-agent shared packing
- Retroactive savings — only future turns optimized

</spec_lock>

<decisions>
## Implementation Decisions

### Savings Surfacing (discussed)
- **D-01 — Loudness:** Surface the savings as a `context packed: X→Y (−Z%)` line in `/cost` AND in the existing F3 budget HUD. Reuse the F3 OSC surface (`recorder.py` `_emit_budget_osc`/`_emit_context_osc`) — do not build a new HUD widget.
- **D-02 — Ledger location/granularity:** Session-scoped `.voss/sessions/<id>/token-savings.jsonl`, one record per assembled turn (`{iter, original_tokens_est, packed_tokens_est, method, cache_read_tokens, ...}`). GC's with the session; no unbounded project-root growth. (Project-root cumulative lifetime ledger deferred — see Deferred.)
- **D-03 — Framing (honesty):** Per-turn figures labeled as estimates (`~`), reconciled against provider-reported usage when available. **No cumulative "hero" number** in the default surface — avoids reading as overclaim. Estimates come from `_default_token_count` (`agent.py:73`); `packed ≤ original` always.
- **D-04 — Dollar figure:** Report tokens **and an estimated `$` saved** (user override of the tokens-only recommendation). Derive `$` from the token delta × model price via the existing F3 cost map / litellm (`LITELLM_LOCAL_MODEL_COST_MAP=true` already wired in the live plane). The `$` is **also labeled `~estimate`** and reconciled with real cost when known — honesty framing (D-03) applies to the dollar figure too. Prompt-cache billing (cache reads at reduced rate) must be reflected so the `$` is not inflated.

### Claude's Discretion (defaulted per SPEC — planner may revisit)
User chose to lock only Savings Surfacing; the remaining gray areas default per SPEC:
- **Default posture & config:** Default to **packing ON with a conservative profile** (short runs unchanged; `--no-pack` byte-identical escape hatch). Config shape (a `[context]` block in existing config vs separate `context.yml`) is planner's choice — favor the existing config surface to avoid a new file.
- **Decay aggressiveness (K/M):** Default to a **large recent-full tier** (conservative K) and a late digest→fold cutoff (M) so the default barely changes behavior; aggressive profiles are opt-in. Exact K/M values = planner/researcher (informed by the M5 quality gate, VOPT-07).
- **Digest method scope:** **Structural/extractive only** this phase (no LLM-summarization on any path in V18). An opt-in LLM-summary profile is explicitly deferred (see Deferred).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements
- `.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-SPEC.md` — Locked requirements (VOPT-01..08), boundaries, acceptance criteria. MUST read before planning.

### The chokepoint + token plumbing (modify here)
- `voss/harness/agent.py` §708-716 — message assembly; the full-replay loop the allocator replaces
- `voss/harness/agent.py` §431-458 — `_serialize_iter_for_replay` (per-iteration rendering; tier logic attaches here)
- `voss/harness/agent.py` §363-395 — T4 `cache_control` static prefix (NEVER repacked; breakpoint at :393-394)
- `voss/harness/agent.py` §73 — `_default_token_count` (estimation source for packing + ledger)
- `voss/harness/agent.py` §500, §1008-1009 — `token_budget=60_000` + budget-exhaustion halt (packing budget derives from this)

### Reuse surfaces (consume read-only — do NOT rebuild)
- `voss/harness/code/` (`service.py`, `index.py`, `context.py`) — M10 code-intel for eviction re-fetch pointers (VOPT-04)
- `voss/harness/recorder.py` §98-140 — F3 budget/context OSC; the savings line plugs in here (D-01)
- `voss/harness/session.py` §115-121 — `IterationRecord` cache-token fields (`cache_creation_input_tokens`/`cache_read_input_tokens`) for cache-coherence proof (VOPT-03)
- F2 Hybrid Semantic Search (BM25+vector RRF, ready-to-execute) — optional richer re-fetch when present

### Out-of-scope boundaries (do NOT change)
- `voss/harness/tools.py` §22, §308-309 — `SHELL_OUTPUT_CAP_BYTES=30720` tool caps (unchanged)
- `voss/harness/agent.py` §213 — `HISTORY_WINDOW=30` (unchanged)

### Prior-phase anchors (shipped/planned context)
- T4 Prompt Caching (CACHE-01..04) — caching prefix discipline
- M10 Codebase Intelligence (CODE-01..07) — project index + `code_search`/`find_definition`/`find_references`
- F3 Budget & Token Visualization (shipped) — OSC budget pipeline / HUD
- M5 Eval (golden tasks; `voss eval`) — host for the VOPT-07 quality gate

*No external ADRs/specs — origin is the conversational competitive teardown of "Plyrium Forge" (Electron+Rust ADE token-saver: code-RAG index + per-agent budget packer + `token-savings.jsonl` ledger feeding worktree-isolated agents).*

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_serialize_iter_for_replay` (`agent.py:431`) — the per-iteration renderer the tiered decay extends (full vs digest vs fold).
- `_default_token_count` (`agent.py:73`) — token estimation for both the packing budget and the ledger; no new tokenizer dep.
- T4 cache prefix machinery (`agent.py:363-395`) — already marks the static prefix cacheable; allocator treats it as immutable and may add a second breakpoint on the stabilized replay prefix.
- F3 OSC emitters (`recorder.py:98-140`) — savings line (D-01) reuses this surface instead of a new HUD.
- M10 `code/service.py` retrieval — eviction pointers resolve through it (D-04 re-fetch), no extra context stored.
- litellm cost map (`LITELLM_LOCAL_MODEL_COST_MAP=true`) — supplies the per-token price for the estimated-$ figure (D-04).

### Established Patterns
- **Append-only + cache breakpoint:** steady-state turns should extend the replay tail append-only so the prompt cache stays warm; recompaction is threshold-gated (hysteresis), not per-turn. Naive per-turn rewriting defeats T4 — this is the load-bearing constraint.
- **Budget halts, doesn't pack (today):** `token_budget` only stops the loop at the cap; V18 adds the missing "pack to fit" behavior under the same budget.
- **Estimates, not exact counts:** harness already runs on `_default_token_count` estimates; ledger + savings inherit that, labeled `~` and reconciled with provider usage when present.

### Integration Points
- `agent.py:708` message assembly — allocator slots in before/at the replay-append loop; `--no-pack` path must be byte-identical to today.
- `recorder.py` budget OSC — savings line emission (D-01).
- `/cost` command — prints the `context packed: X→Y (−Z%) ~$…` line from the per-session ledger (D-01/D-03/D-04).
- `.voss/sessions/<id>/` — ledger storage alongside existing session records (D-02).

</code_context>

<specifics>
## Specific Ideas

- Savings line wording: `context packed: X→Y (−Z%)`, with an estimated `~$` suffix derived from the token delta; all figures labeled estimates.
- The dollar figure must net out prompt-cache savings (cache reads bill at reduced rate) so it isn't inflated — reconcile with litellm/provider cost.
- Default profile should feel like "nothing changed" on short runs; the savings only become visible on long, log-heavy `voss do` sessions (the actual win case).

</specifics>

<deferred>
## Deferred Ideas

- **Opt-in LLM-summarization profile** — richer digests via a cheap model call, instead of structural/extractive. Out of V18 (spends tokens to save tokens; needs its own cost/quality justification). Candidate future phase once structural packing is proven by the VOPT-07 eval.
- **Project-root cumulative lifetime ledger** — a Plyrium-style `.voss/token-savings.jsonl` rollup across all runs for a lifetime "−X%" headline. Chose per-session now (D-02); a rolled-up root summary can layer on later with rotation.
- **F4 context-heatmap rendering of packed/evicted files** — V18 emits the numbers; the visual pane is F4's territory.

None of the above are scope creep into V18 — they are explicitly downstream.

</deferred>

---

*Phase: V18-Budget-Aware Context Allocator (Token Optimization)*
*Context gathered: 2026-06-10*
