# Phase V18: Budget-Aware Context Allocator (Token Optimization) — Research

**Researched:** 2026-06-10
**Domain:** Agent loop token packing, prompt cache coherence, savings telemetry
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Loudness:** Surface savings as `context packed: X→Y (−Z%)` in `/cost` AND in the existing F3 budget HUD. Reuse the F3 OSC surface (`recorder.py` `_emit_budget_osc`/`_emit_context_osc`) — do not build a new HUD widget.

**D-02 — Ledger location/granularity:** Session-scoped `.voss/sessions/<id>/token-savings.jsonl`, one record per assembled turn (`{iter, original_tokens_est, packed_tokens_est, method, cache_read_tokens, ...}`). GCs with the session; no unbounded project-root growth.

**D-03 — Framing (honesty):** Per-turn figures labeled as estimates (`~`), reconciled against provider-reported usage when available. No cumulative "hero" number in the default surface. `packed <= original` always.

**D-04 — Dollar figure:** Report tokens AND an estimated `$` saved. Derive `$` from token delta × model price via existing F3 cost map / litellm (`LITELLM_LOCAL_MODEL_COST_MAP=true` already wired). The `$` is also labeled `~estimate`. Prompt-cache billing (cache reads at reduced rate) must be reflected so the `$` is not inflated.

### Claude's Discretion

- **Default posture & config:** Packing ON with a conservative profile; `--no-pack` byte-identical escape hatch. Config shape: prefer a `[context]` block in the existing `~/.config/voss/config.toml` over a new file.
- **Decay aggressiveness (K/M):** Default to large recent-full tier (conservative K) and late digest→fold cutoff (M). Aggressive profiles are opt-in. Exact K/M values are planner/researcher's — informed by the VOPT-07 quality gate.
- **Digest method scope:** Structural/extractive only in V18. No LLM-summarization on any V18 path.

### Deferred Ideas (OUT OF SCOPE)

- Opt-in LLM-summarization profile — future phase, post quality-gate proof.
- Project-root cumulative lifetime savings ledger.
- F4 context-heatmap rendering of packed/evicted files — F4 territory.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VOPT-01 | Pure ContextAllocator packs variable message region under token ceiling at agent.py:708 chokepoint | §Chokepoint Integration, §Architecture Patterns Pattern 1 |
| VOPT-02 | Three-tier iteration-age decay: full / one-line digest / folded summary; structural/extractive; newest always full | §Architecture Patterns Pattern 2, §Code Examples |
| VOPT-03 | Cache-coherent packing: never repack T4 prefix; recompact only on hysteresis threshold crossing | §Cache Coherence, §Architecture Patterns Pattern 3 |
| VOPT-04 | Eviction pointers via M10 code/ API; no new index/embedding | §Eviction Pointer API |
| VOPT-05 | Savings ledger: per-turn JSONL, `/cost` line, F3 OSC; honest estimates; packed<=original always | §Savings Ledger & Surfacing, §D-01..D-04 |
| VOPT-06 | Config surface + `--no-pack` escape hatch; byte-identical when disabled; conservative default | §Config & Escape Hatch |
| VOPT-07 | M5 quality-preservation eval: packing-on vs off; biting gate; success rate gate | §Quality-Preservation Eval |
| VOPT-08 | Coherence guard: no new index/embedding/budget substrate; recorder OSC shape unchanged; T4 prefix bytes unchanged under --no-pack | §Coherence Guard |
</phase_requirements>

---

## Summary

V18 inserts a `ContextAllocator` class at the exact line where `voss do` rebuilds its `messages` list on every iteration (`agent.py:708-716`). Today that loop appends `_serialize_iter_for_replay(prior)` for every prior iteration unconditionally — the only decay is the per-result 400-char string cap at line 454-456. V18 replaces that unconditional full-replay with a budget-aware packer that renders the N most recent iterations full, the next M−N as one-line structural digests, and everything older as a single folded "Earlier work summary" block. It writes a `token-savings.jsonl` ledger alongside the existing session file and appends a savings line to `/cost` and the F3 HUD.

The codebase is well-prepared for this insertion. `_default_token_count` already exists for estimation. `_serialize_iter_for_replay` is the exact rendering function the tier system extends. The T4 `cache_control: ephemeral` prefix is already marked and must not be disturbed. The `IterationRecord.cache_read_input_tokens` field already records per-turn cache hits for coherence proof. The M10 `CodeIntelService` exposes `search()`, `find_definition()`, and `find_references()` for eviction pointer re-fetch references. `litellm.model_cost` indexed by the model string (e.g. `claude-opus-4-8`) provides both `input_cost_per_token` and `cache_read_input_token_cost`, enabling honest dollar netting.

The primary engineering risk is cache coherence: naively rewriting the replay tail on every loop entry defeats the T4 prefix cache. The solution is append-only steady state with hysteresis-threshold-gated recompaction. The second risk is byte-identity under `--no-pack`: the allocator must be on a branch that is never reached when the flag is set, not an allocator that "happens to produce the same output."

**Primary recommendation:** Implement `ContextAllocator` as a new pure module (`voss/harness/context_allocator.py`) that takes `(iter_records, budget_tokens, profile)` and returns a list of `(assistant_msg, user_msg)` pairs. Slot it at `agent.py:713` behind a single `if packing_enabled` branch. Make the disabled path literally the existing four-line loop — this guarantees byte-identity by construction and makes `--no-pack` a code path rather than a "same output" assertion.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Context assembly / packing | Python harness (agent.py loop) | — | All message assembly happens in the single `_run_turn_exec` loop; no cross-tier data |
| Token estimation | Python harness (litellm / fallback) | — | `_default_token_count` already lives here |
| Cache coherence / breakpoints | Python harness (agent.py sys_blocks) | Provider (Anthropic cache API) | Provider implements caching; harness controls which blocks get `cache_control` |
| Savings ledger write | Python harness (post-assembly) | — | Purely local file write to `.voss/sessions/<id>/token-savings.jsonl` |
| Savings display (`/cost`) | Python harness CLI (cli.py `_cost`) | — | Reads ledger from disk |
| Savings display (F3 HUD) | Python harness (recorder.py OSC) | Rust PTY reader | Emits OSC; Rust reader strips and forwards; no Rust code change in V18 |
| Eviction pointer resolution | Python harness (code/service.py) | — | M10 CodeIntelService; V18 calls read-only |
| Quality-preservation eval | Python harness (voss/eval/) | — | M5 golden suite; V18 adds a packing-on/off variant |
| Config persistence | `~/.config/voss/config.toml` `[context]` block | — | Follows existing pattern in harness/config.py |

---

## Standard Stack

V18 introduces **no new external packages.** All dependencies are already installed in the project venv.

### Core (already in venv)

| Library | Version (verified) | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| litellm | 1.84.0 [VERIFIED: pip show] | `token_counter` for estimation; `model_cost` map for $ derivation | Already imported in agent.py:49-52; used by `_default_token_count` |
| Python stdlib (`json`, `pathlib`, `dataclasses`) | 3.13 | JSONL ledger write, path construction, dataclass records | Zero-dep |

### No New Packages Required

The Package Legitimacy Audit is minimal because V18 adds no new dependencies.

---

## Package Legitimacy Audit

> V18 introduces no new external packages. All capabilities come from litellm (already installed) and Python stdlib.

| Package | Registry | Age | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|
| litellm | PyPI | 2+ yrs, 50M+ downloads | [OK] (existing dep) | Approved — already in venv (1.84.0) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
voss do (task)
    │
    ▼
_run_turn_exec() — per-turn outer loop
    │
    ├─ ONCE per turn ─────────────────────────────────────────────────
    │   sys_blocks = _compose_system_blocks(...)    ← IMMUTABLE (T4 cache_control)
    │   [voss_md | cognition | principles | project_index | prior_context | loop_system]
    │   last block gets  cache_control: ephemeral
    │
    ├─ EACH ITERATION (agent.py:687-716) ──────────────────────────
    │   rider = _build_iter_rider(index, tokens_used, prior_iters)   ← per-iter system
    │   messages = [sys_blocks, rider, user_prompt]
    │
    │   if packing_enabled:                  ← V18 insertion point (:713)
    │     replay_pairs = ContextAllocator.pack(
    │                       all_iter_records,
    │                       packing_budget,
    │                       profile)
    │   else:                               ← --no-pack: byte-identical path
    │     replay_pairs = [_serialize_iter_for_replay(p) for p in all_iter_records]
    │
    │   messages += replay_pairs            ← (assistant, user) interleaved
    │
    │   ── provider.stream(messages) ──────────────────────────────
    │         │
    │         ▼
    │    Usage event → cache_read_input_tokens   ← VOPT-03 coherence proof
    │
    │   post-stream:
    │   ─ _append_savings_record(session_id, iter, orig, packed, ...)  ← VOPT-05
    │   ─ _emit_budget_osc(...)                                         ← F3 (unchanged)
    │   ─ _emit_context_osc(...)                                        ← F3 (unchanged)
    │
    ▼
ContextAllocator.pack() internals:
    packing_budget = token_budget − reserve(cached_prefix_est + rider + user_prompt + completion_headroom)
    │
    ├─ Tier 0 (FULL):  last K iters → _serialize_iter_for_replay(iter)  (unchanged rendering)
    ├─ Tier 1 (DIGEST): iters K..M → _render_iter_digest(iter)          (one-line structural)
    └─ Tier 2 (FOLD):   iters >M   → _render_fold_summary(older_iters)  (single block)
                                       + eviction pointers if files referenced
    │
    ▼
    Token estimation via _default_token_count at each tier boundary
    Stop adding tiers when sum > packing_budget
    Hysteresis: recompact ONLY when estimated_usage ≥ HIGH_WATER * packing_budget
              → hold stable until estimated_usage ≤ LOW_WATER * packing_budget
```

### Recommended Project Structure

```
voss/harness/
├── context_allocator.py        # NEW — pure ContextAllocator class
│                               #   pack(), _render_iter_digest(), _render_fold_summary()
│                               #   _build_eviction_pointer(), PackingProfile dataclass
├── agent.py                    # MODIFY — slot allocator at :713, add --no-pack branch
├── cli.py                      # MODIFY — add --no-pack flag to do_cmd; extend _cost()
├── config.py                   # MODIFY — add _parse_context_section() + [context] reader
├── recorder.py                 # MODIFY — add _append_savings_record() helper
└── session.py                  # READ-ONLY — _sessions_dir() already handles pathing

tests/harness/
├── test_context_allocator.py   # NEW — pure unit tests (no provider, no fs)
├── test_agent_packing.py       # NEW — integration tests via FakeStreamingProvider
├── test_savings_ledger.py      # NEW — ledger write/read correctness
└── test_agent_loop.py          # MODIFY — add --no-pack byte-identity assertion
```

---

## Pattern 1: The Assembly Chokepoint (VOPT-01)

**What:** The exact four-line loop at `agent.py:713-716` that V18 replaces with the allocator branch.

**Current code (lines 708-716) [VERIFIED: read source]:**
```python
# agent.py:708-716 — today's full-replay loop
messages: list[dict] = [
    {"role": "system", "content": sys_blocks},  # cached static prefix (CACHE-01)
    {"role": "system", "content": rider},
    {"role": "user", "content": user_prompt},
]
for prior in all_iter_records:                  # UNBOUNDED growth
    a_msg, u_msg = _serialize_iter_for_replay(prior)
    messages.append(a_msg)
    messages.append(u_msg)
```

**V18 insertion [ASSUMED — not yet written]:**
```python
# V18 insertion at agent.py:713
messages: list[dict] = [
    {"role": "system", "content": sys_blocks},
    {"role": "system", "content": rider},
    {"role": "user", "content": user_prompt},
]
if packing_enabled and all_iter_records:
    replay_pairs = _context_allocator.pack(
        all_iter_records, packing_budget, packing_profile
    )
    for a_msg, u_msg in replay_pairs:
        messages.append(a_msg)
        messages.append(u_msg)
else:
    # --no-pack: exact pre-V18 code path — byte-identical
    for prior in all_iter_records:
        a_msg, u_msg = _serialize_iter_for_replay(prior)
        messages.append(a_msg)
        messages.append(u_msg)
```

**Key invariant:** `all_iter_records` is populated at `agent.py:992`:
```python
all_iter_records.append(rec._iterations[-1])
```
This happens at the END of each iteration, so at the top of iteration N, `all_iter_records` contains iterations 0..N-1. The allocator receives the complete prior-iterations list.

**packing_budget computation [ASSUMED]:**
```python
cached_prefix_est = sum(_default_token_count(b["text"] if isinstance(b["text"], str) else "", model=model)
                        for b in sys_blocks if isinstance(b, dict))
rider_est = _default_token_count(rider, model=model)
user_est = _default_token_count(user_prompt, model=model)
completion_headroom = cfg.max_output_tokens  # e.g. 4096
reserve = cached_prefix_est + rider_est + user_est + completion_headroom
packing_budget = token_budget - reserve
```

---

## Pattern 2: Tiered Decay Rendering (VOPT-02)

**What:** Three rendering tiers over `all_iter_records`. The existing `_serialize_iter_for_replay` function is the "full" tier — no change to its output.

**Current `_serialize_iter_for_replay` (agent.py:431-458) [VERIFIED: read source]:**
```python
def _serialize_iter_for_replay(iter_rec) -> tuple[dict, dict]:
    plan_dict = iter_rec.plan or {}
    assistant_content = json.dumps({
        "rationale": plan_dict.get("rationale", ""),
        "steps": plan_dict.get("steps", []) or [],
        "final_when_done": plan_dict.get("final_when_done", ""),
    })
    assistant_msg = {"role": "assistant", "content": assistant_content}

    lines = [f"Tool results for iteration {iter_rec.index}:"]
    for tr in iter_rec.tool_results or []:
        name = tr.get("name", "")
        args = str(tr.get("args", {}) or {})[:400]    # ← :454-456
        result_str = str(tr.get("result", ""))[:400]  # ← :454-456
        lines.append(f"- {name}({args}) -> {result_str}")
    user_msg = {"role": "user", "content": "\n".join(lines)}
    return assistant_msg, user_msg
```

**Existing rider digest in `_build_iter_rider` (agent.py:416-427) [VERIFIED: read source]:**
```python
# Existing one-line summary used for the RIDER (not the replay tail):
for ir in prior_iters:
    plan = ir.plan or {}
    step_count = len(plan.get("steps", []) or [])
    tool_count = len(ir.tool_results or [])
    snippet_src = plan.get("final_when_done") or plan.get("rationale") or ""
    snippet = snippet_src.replace("\n", " ")[:60]
    lines.append(f"- Iter {ir.index}: {step_count} steps, {tool_count} tools, {snippet}")
```
This pattern is directly reusable as the digest tier for the replay tail.

**Digest tier rendering [ASSUMED]:**
```python
def _render_iter_digest(iter_rec) -> tuple[dict, dict]:
    """One-line structural digest: counts + first/last tool result snippet."""
    plan = iter_rec.plan or {}
    tool_results = iter_rec.tool_results or []
    tools_summary = ", ".join(tr.get("name", "?") for tr in tool_results[:3])
    if len(tool_results) > 3:
        tools_summary += f"… (+{len(tool_results)-3})"
    outcome = plan.get("final_when_done") or plan.get("rationale") or ""
    assistant_msg = {
        "role": "assistant",
        "content": f"[digest] Iter {iter_rec.index}: {len(tool_results)} tools ({tools_summary})"
    }
    user_msg = {
        "role": "user",
        "content": f"Iter {iter_rec.index} summary: {outcome.replace(chr(10),' ')[:120]}"
    }
    return assistant_msg, user_msg
```

**Fold tier rendering [ASSUMED]:**
```python
def _render_fold_summary(iter_recs: list) -> list[tuple[dict, dict]]:
    """Single block summarizing N+ ancient iterations."""
    if not iter_recs:
        return []
    indices = [r.index for r in iter_recs]
    all_tools = set()
    for r in iter_recs:
        all_tools.update(tr.get("name","") for tr in (r.tool_results or []))
    # eviction pointers: files referenced in tool results
    eviction_lines = []
    for r in iter_recs:
        for tr in (r.tool_results or []):
            args = tr.get("args") or {}
            if isinstance(args, dict):
                path = args.get("path") or args.get("file")
                if path:
                    eviction_lines.append(f"↻ re-fetch: code_search(\"{path}\")")
    eviction_block = "\n".join(dict.fromkeys(eviction_lines[:5]))  # dedupe, cap
    summary = (
        f"[Earlier work: iters {min(indices)}–{max(indices)}, "
        f"tools used: {', '.join(sorted(all_tools)[:8])}"
        f"{', ...' if len(all_tools) > 8 else ''}]"
    )
    if eviction_block:
        summary += f"\n{eviction_block}"
    return [
        ({"role": "assistant", "content": summary},
         {"role": "user", "content": f"Older iterations {min(indices)}–{max(indices)} folded."})
    ]
```

**Conservative default profile [ASSUMED]:**
```python
@dataclass
class PackingProfile:
    recent_full_k: int = 8    # last 8 iterations full (conservative)
    digest_cutoff_m: int = 20 # iters 8..20 as digests
    high_water: float = 0.80  # recompact when usage >= 80% of packing_budget
    low_water: float = 0.60   # hold until usage <= 60%
    enabled: bool = True
```
With `recent_full_k=8` and `token_budget=60_000`, a default run that completes in ≤8 iterations produces byte-identical output to pre-V18 — the "conservative default leaves short runs unchanged" requirement is met structurally.

---

## Pattern 3: Cache-Coherent Recompaction (VOPT-03)

**What:** Keep the T4 `cache_control: ephemeral` prefix untouched; only recompact the replay tail when estimated usage crosses the high-water mark.

**T4 prefix assembly (agent.py:363-395) [VERIFIED: read source]:**
```python
def _compose_system_blocks(...) -> list[dict]:
    blocks = [{"type": "text", "text": text} for text in (...) if text]
    if blocks:
        blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}
    return blocks
```
`sys_blocks` is computed ONCE before the iteration while-loop and passed in as `{"role": "system", "content": sys_blocks}`. It is NEVER modified inside the loop. The allocator receives `all_iter_records` (the variable region) and must never touch `sys_blocks`.

**`IterationRecord` cache token fields (session.py:110-111) [VERIFIED: read source]:**
```python
cache_creation_input_tokens: int = 0   # tokens written to cache this turn
cache_read_input_tokens: int = 0       # tokens read from cache this turn
```
These are populated at `agent.py:785-793` from `this_iter_usage`:
```python
iter_cache_read = getattr(this_iter_usage, "cache_read_input_tokens", 0) ...
```
Steady-state cache-warm turns will show `cache_read_input_tokens` dominating (VOPT-03 acceptance). Under `--no-pack` the prefix and its cache breakpoint are byte-identical, so the T4 cache behavior is unchanged.

**Hysteresis implementation [ASSUMED]:**
The allocator carries per-turn stable-region state. On each call:
1. Estimate total token cost of the current packed replay.
2. If `estimated_tokens < packing_budget * HIGH_WATER`: extend append-only (do not recompact, keep previously stable region boundaries).
3. If `estimated_tokens >= packing_budget * HIGH_WATER`: trigger full recompaction (recompute tier boundaries from scratch).
4. The `stable_region_hash` is the SHA-256 of the serialized replay pairs that would NOT be recompacted — verified unchanged across iterations in the acceptance test.

**Optional second `cache_control` breakpoint:** The SPEC allows placing a second breakpoint at the stable replay prefix. The pattern is identical to `_compose_system_blocks`: add `cache_control: {"type": "ephemeral"}` to the last message in the stable region. Only the last block in a message list can carry this. Implementation detail: since `messages[0]` is already `sys_blocks` with `cache_control`, a second breakpoint at the end of the stable replay requires a content list structure or a separate system block — this is a planner decision (SPEC marks it optional for V18).

---

## Eviction Pointer API (VOPT-04)

**M10 `CodeIntelService` signatures [VERIFIED: read source]:**
```python
# voss/harness/code/service.py

class CodeIntelService:
    async def search(self, pattern: str, path: str = ".", max_results: int = 50) -> dict
    # returns: {"result": "ok", "source": "ast-grep"|"regex", "hits": [...]}
    # hit: {"file": str, "line": int, "text": str, "language": str, "source": str}

    async def find_definition(self, symbol: str, path: str | None = None) -> dict
    # returns: {"result": "ok"|"not_found", "symbol": str, "source": "lsp"|"index", "items": [...]}

    async def find_references(self, symbol: str, path: str | None = None, max_results: int = 50) -> dict
```

**Eviction pointer format [ASSUMED]:**
When a folded iteration had tool results that referenced files/symbols, emit:
```
↻ re-fetch via code_search("path/to/file.py") or find_definition("MyClass")
```
The allocator extracts file paths from `tr["args"]["path"]` and symbol names from `tr["args"]["pattern"]` or `tr["args"]["symbol"]` in the tool result args. These are structural — no async call needed at pack time; the hint text is enough for the model to re-invoke the tool.

**F2 status [VERIFIED: STATE.md + phase directory]:** F2 Hybrid Semantic Search has "Plans ready to execute" — it is NOT yet shipped. V18 must treat F2 as optional: eviction pointers reference M10's `code_search`/`find_definition` by default; mention `hybrid_search` only if F2 is available (`voss/harness/code/service.py` can be checked at runtime for the F2 method). The SPEC says "M10/F2 — and F2 when present" — conditional availability is the correct posture.

---

## Savings Ledger and Surfacing (VOPT-05, D-01..D-04)

**Session path convention [VERIFIED: session.py:57-58]:**
```python
def _sessions_dir(cwd: Path) -> Path:
    return (cwd / ".voss" / "sessions").resolve()
```
Session JSON files live at `.voss/sessions/<id>.json`. The token-savings ledger lives alongside at `.voss/sessions/<id>/token-savings.jsonl`.

**JSONL record schema [ASSUMED]:**
```python
{
    "iter": int,                    # iteration index (0-based)
    "original_tokens_est": int,     # _default_token_count of full-replay messages
    "packed_tokens_est": int,       # _default_token_count of packed messages (always <= original)
    "method": str,                  # "full"|"tiered-K8-M20"|"no-pack"
    "cache_read_tokens": int,       # from IterationRecord.cache_read_input_tokens
    "saved_tokens_est": int,        # original - packed (always >= 0)
    "saved_usd_est": float | None,  # token_delta * input_cost_per_token - cache_savings, labeled ~ 
    "model": str,                   # model string for cost lookup
    "ts": str,                      # ISO timestamp
}
```

**Dollar netting formula [VERIFIED: litellm.model_cost map inspection]:**
```python
# litellm.model_cost["claude-opus-4-8"] structure:
# {
#   "input_cost_per_token": 5e-06,
#   "cache_read_input_token_cost": 5e-07,  # reads bill at ~10% of input rate
#   "cache_creation_input_token_cost": 6.25e-06,
#   ...
# }

def estimate_savings_usd(
    saved_tokens: int,
    cache_read_tokens: int,
    model: str,
) -> float | None:
    """Estimate $ saved, netting cache read billing to avoid inflation."""
    cost_entry = litellm.model_cost.get(model)
    if not cost_entry:
        return None
    input_rate = cost_entry.get("input_cost_per_token", 0)
    cache_read_rate = cost_entry.get("cache_read_input_token_cost", 0)
    # Gross savings: token_delta * full input rate
    gross = saved_tokens * input_rate
    # But cache reads already bill at the reduced rate, so net:
    # If the packed tokens would be cache hits, they bill at cache_read_rate not input_rate.
    # Simplified: if cache_read_tokens > 0, those were billed at cache_read_rate already,
    # so the actual $ saved on the delta is the difference.
    cache_reduction = cache_read_tokens * (input_rate - cache_read_rate)
    return max(gross - cache_reduction, 0.0)
```
The `saved_usd_est` must be labeled `~estimate` in all display surfaces.

**`/cost` extension (cli.py:881-918) [VERIFIED: read source]:**
Current `_cost()` reads `ctx.total_cost` (session-level float) and `ctx.record.runs`. The savings line reads the ledger file and sums/averages for the session. Example output:
```
session cost: $0.1234
context packed: ~14,200→~6,800 tokens (−52%)  ~$0.0038 saved
```
The ledger path must be computable from `ctx.record.id` and `ctx.record.cwd`.

**F3 OSC emitters (recorder.py:98-140) [VERIFIED: read source]:**
- `_emit_budget_osc` signature: `(tokens_used, token_limit, cost_usd, iteration, model)` — shape is unchanged by V18.
- `_emit_context_osc(payload: dict)` — payload is free-form JSON. A savings field can be added to the context OSC payload without breaking the OSC shape contract. Shape-unchanged means: `_emit_budget_osc` is byte-identical; `_emit_context_osc` gains optional fields (additive, non-breaking).

---

## Config and Escape Hatch (VOPT-06)

**Existing config infrastructure [VERIFIED: harness/config.py]:**
```python
# config.py pattern: regex-based TOML section parser
_HARNESS_BLOCK  = re.compile(r"^\[harness\][^\[]*", re.MULTILINE)
_AGENT_BLOCK    = re.compile(r"^\[agent\][^\[]*", re.MULTILINE)
_TOOLS_BLOCK    = re.compile(r"^\[tools\][^\[]*", re.MULTILINE)
# V18 adds:
_CONTEXT_BLOCK  = re.compile(r"^\[context\][^\[]*", re.MULTILINE)
```
Config file lives at `~/.config/voss/config.toml` (or `$XDG_CONFIG_HOME/voss/config.toml`). The `[context]` block follows the exact same pattern as `[agent]`.

**Example `[context]` block [ASSUMED]:**
```toml
[context]
enabled = true          # or false to disable packing project-wide
recent_full_k = 8       # last K iterations full (conservative default)
digest_cutoff_m = 20    # K..M as digests; >M folded
high_water = 0.80       # recompact threshold (fraction of packing_budget)
low_water = 0.60        # hold threshold
```

**`--no-pack` flag wiring [ASSUMED]:**
```python
# cli.py do_cmd:
@click.option("--no-pack", is_flag=True, envvar="VOSS_NO_PACK",
              help="Disable context packing; messages byte-identical to pre-V18.")
```
The flag passes through to `run_turn()` → `_run_turn_exec()` as `packing_enabled: bool = True`. When `False`, the existing `for prior in all_iter_records` loop runs unchanged.

**`ctx(budget:)` interaction [VERIFIED: agent.py:516]:**
The `ContextScope(token_budget=token_budget, ...)` wraps the iteration loop. `packing_budget` is derived from `token_budget` at each iteration head (deducting the stable-region estimate). The `ctx.token_budget` halt at `agent.py:1008-1009` is unchanged — packing reduces how fast tokens are spent but the halt condition is the same.

---

## Quality-Preservation Eval (VOPT-07)

**M5 eval infrastructure [VERIFIED: voss/eval/runner.py, suite.py]:**
```python
# voss/eval/runner.py
SUITE_ROOT = Path("tests/eval")

def run_suite(
    *,
    suite: str = "golden",   # "golden" = 6 tasks (01..06)
    stub: bool = False,       # hermetic smoke using StubProvider
    model: str | None = None,
    ...
) -> Path: ...
```
The eval tasks at `tests/eval/golden/` are: `01-analyze`, `02-plan-only`, `03-approved-edit`, `04-validation`, `05-resume`, `06-fetch-summarize`. Each has `task.toml` with `prompt`, `mode`, `rubric`, `judge_inputs`.

**How to run a packing-on-vs-off comparison [ASSUMED]:**
The cleanest approach is to add a `packing` parameter to `run_suite()` or (simpler, no API change) to use an env-var `VOSS_NO_PACK=1` to flip the escape hatch, run the suite twice, and compare. The eval gate script reads two output JSONL files and asserts:
1. `success_rate(packing_on) >= success_rate(packing_off) - TOLERANCE` (e.g. 0.05 = 5%)
2. `mean_input_tokens(packing_on) < mean_input_tokens(packing_off)` (measurable reduction)

**Biting gate requirement:** A deliberately over-aggressive profile (`recent_full_k=1`, `digest_cutoff_m=2`) should drop at least one golden task — prove the gate catches it. This is a specific test case, not just a pass/fail label.

**Success metric in existing records [VERIFIED: runner.py:83-97]:**
```python
def _extract_signals(record: SessionRecord) -> tuple[float | None, float | None]:
    # Returns (total_cost_usd, confidence)
    # judge_run() returns "pass"/"fail" — that's the success signal
```
The judge verdict (`pass`/`fail`) is in the runs JSONL. Mean input tokens can be read from `run.get("iterations", [])` → `sum(iter["prompt_tokens"])`.

---

## Common Pitfalls

### Pitfall 1: Per-Turn Rewriting Defeats the T4 Cache
**What goes wrong:** If the allocator produces different tier-boundary decisions on every iteration (e.g. re-sorting or re-summarizing on every call), the packed replay tail bytes change each turn and the T4 cache breakpoint cannot be reused.
**Why it happens:** Treating the allocator as stateless — compute fresh from scratch every call.
**How to avoid:** The allocator must carry a `_stable_region` cache across calls within the same run. The stable region is only invalidated when `high_water` is crossed. Steady-state turns extend the stable region by appending new full iterations — no recompaction.
**Warning signs:** `cache_read_input_tokens` stays 0 or near 0 across iterations despite identical sys_blocks.

### Pitfall 2: `--no-pack` Via "Same Output" Rather Than "Same Code Path"
**What goes wrong:** Implementing `--no-pack` as `if not packing_enabled: return self.pack_full_replay()` where `pack_full_replay()` re-implements the loop — any future deviation breaks byte-identity.
**Why it happens:** Temptation to make the allocator handle both paths.
**How to avoid:** The `--no-pack` branch literally IS the original four-line loop (`for prior in all_iter_records: _serialize_iter_for_replay(prior)`). The allocator never touches this code path.

### Pitfall 3: Double-Counting Savings
**What goes wrong:** `saved_usd_est` is inflated because cache reads bill at ~10% of input rate, but the ledger treats the packed delta as if all tokens were billed at the full input rate.
**Why it happens:** Ignoring `cache_read_input_token_cost` in the cost model.
**How to avoid:** Net out cache savings: `gross_saved = delta * input_rate; cache_reduction = cache_read_tokens * (input_rate - cache_read_rate); net_saved = max(gross_saved - cache_reduction, 0)`.

### Pitfall 4: `packed > original` on Degenerate Inputs
**What goes wrong:** Folded summary + eviction pointers are longer than the raw replay for very short histories.
**Why it happens:** The fold block has fixed overhead (the "Earlier work" header + eviction pointer lines).
**How to avoid:** Always check `len(packed_messages) <= len(original_messages)` and `packed_tokens <= original_tokens` before writing to the ledger. If packed >= original, emit the full replay instead and record `method="full"` with `saved_tokens=0`.

### Pitfall 5: Estimate Drift From Actual Token Count
**What goes wrong:** `_default_token_count` (4-chars/token fallback) underestimates or overestimates by 20-30% for JSON-heavy content (plan JSON has many short tokens).
**Why it happens:** The 4-chars/token heuristic is designed for prose, not structured JSON.
**How to avoid:** The ledger records these as `~estimates` (D-03). The reconciliation path reads `iter_rec.prompt_tokens` (provider-reported) after the stream and appends a `provider_prompt_tokens` field to the ledger row. No action needed beyond honest labeling and reconciliation.

### Pitfall 6: `litellm.model_cost` Key Mismatch
**What goes wrong:** The model string from `get_config().default_model` (e.g. `"claude-opus-4-8"`) may not match the exact key in `litellm.model_cost`.
**Why it happens:** litellm uses both bare keys (e.g. `"claude-opus-4-8"`) and prefixed keys (e.g. `"anthropic.claude-opus-4-8"`).
**How to avoid [VERIFIED: litellm.model_cost inspection]:** Direct key `"claude-opus-4-8"` IS present in `litellm.model_cost` with `LITELLM_LOCAL_MODEL_COST_MAP=true`. Fallback pattern: `cost_entry = litellm.model_cost.get(model) or litellm.model_cost.get(f"anthropic.{model}")`. If neither found, return `None` (ledger records `saved_usd_est: null`, no crash).

### Pitfall 7: Config Block Name Collision
**What goes wrong:** `[context]` TOML section conflicts with future or existing TOML usage.
**Why it happens:** The `config.py` regex patterns are section-name literal matches.
**How to avoid:** The existing `_HARNESS_BLOCK`, `_AGENT_BLOCK`, `_TOOLS_BLOCK`, and `_NET_RATE_BLOCK` patterns confirm no `[context]` block exists today. The `[context.packing]` nesting syntax is also safe but adds complexity. `[context]` alone is correct.

### Pitfall 8: Savings Ledger Path in eval/ Temp Dirs
**What goes wrong:** During M5 eval runs, `cwd` is a temp directory; `session_path(id, cwd=cwd)` resolves to the temp dir, which is deleted after the test.
**Why it happens:** The eval runner uses `tempfile.TemporaryDirectory()` and calls `run_turn` with a temp `cwd`.
**How to avoid:** The ledger must be read/written using the same session-path convention as the session JSON (`.voss/sessions/<id>/token-savings.jsonl` under the temp cwd). In the VOPT-07 eval the ledger is readable during the run; after the temp dir is cleaned, the eval only needs the summary output already written to `out_dir/runs.jsonl`. No special handling needed — the ledger naturally lives and dies with the temp fixture.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token estimation | Custom tokenizer | `_default_token_count(text, model=model)` (agent.py:73) | Already exists; litellm + 4-char fallback; no new dep |
| Model cost lookup | Manual price table | `litellm.model_cost[model]` with `LITELLM_LOCAL_MODEL_COST_MAP=true` | Already wired in sidecar; `cache_read_input_token_cost` key present |
| Cache token tracking | Custom cache monitor | `IterationRecord.cache_read_input_tokens` (session.py:111) | Already populated from provider Usage events |
| File path extraction | Custom tool-result parser | `tr["args"]["path"]` or `tr["args"]["file"]` from existing tool_results dicts | Tool results already carry structured args |
| TOML config parsing | New config library | Extend `config.py` with `_CONTEXT_BLOCK` regex (same pattern as `_AGENT_BLOCK`) | Existing zero-dep regex pattern; no tomllib needed for writing |
| Eval success/fail | Custom judge | `judge_run()` in `voss/eval/judge.py` | M5 judge already returns pass/fail per task |

---

## Code Examples

### Existing `_default_token_count` (source of truth for estimation)
```python
# agent.py:73-80 [VERIFIED: read source]
def _default_token_count(text: str, *, model: str) -> int:
    if _litellm is not None:
        try:
            return int(_litellm.token_counter(model=model, text=text))
        except Exception:
            pass
    return max(len(text) // 4, 1)
```

### `IterationRecord` cache fields
```python
# session.py:109-111 [VERIFIED: read source]
cache_creation_input_tokens: int = 0
cache_read_input_tokens: int = 0
```

### `_emit_context_osc` signature (F3 OSC, additive-safe)
```python
# recorder.py:130-140 [VERIFIED: read source]
def _emit_context_osc(payload: dict) -> None:
    if not sys.stdout.isatty():
        return
    json_str = json.dumps(payload, separators=(",", ":"))
    sys.stdout.write(f"\x1b]1337;voss-context={json_str}\x07")
    sys.stdout.flush()
```

### FakeStreamingProvider pattern (existing test double for agent loop tests)
```python
# tests/harness/test_agent_loop.py:76-114 [VERIFIED: read source]
@dataclass
class FakeStreamingProvider:
    scripts: list[list[ProviderStreamEvent]]
    _stream_index: int = 0
    
    def stream(self, **kwargs):
        script = self.scripts[self._stream_index]
        self._stream_index += 1
        async def _gen():
            for ev in script:
                yield ev
        return _gen()
```

### litellm model_cost lookup (cache-rate netting)
```python
# [VERIFIED: litellm.model_cost inspection with LITELLM_LOCAL_MODEL_COST_MAP=true]
import litellm
entry = litellm.model_cost.get("claude-opus-4-8")
# entry = {
#   "input_cost_per_token": 5e-06,
#   "cache_read_input_token_cost": 5e-07,
#   "cache_creation_input_token_cost": 6.25e-06,
#   ...
# }
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Unbounded full replay | Budget-aware tiered decay (V18) | Input token growth bounded by ceiling not iteration count |
| Token tracking only (budget halts) | Token packing (budget packs to fit) | Long runs stay responsive instead of halting |
| `packed > original` possible from fold overhead | Pre-pack check + fallback to `method="full"` | Ledger invariant `packed <= original` maintained always |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | V18 `ContextAllocator` is a new `voss/harness/context_allocator.py` module | Standard Stack, Architecture | Wrong module location; planner adjusts path |
| A2 | `packing_budget = token_budget - reserve(cached_prefix + rider + user_prompt + max_output_tokens)` formula | Pattern 1 | Reserve underestimates → packed messages still overflow; adjust formula |
| A3 | Default `PackingProfile(recent_full_k=8, digest_cutoff_m=20)` leaves ≤8-iteration runs byte-identical | Pattern 2 | Miscalibrated K/M; planner validates via VOPT-02 acceptance test |
| A4 | `--no-pack` wired as `envvar="VOSS_NO_PACK"` on `do_cmd` and eval's `VOSS_NO_PACK=1` override | Config & Escape Hatch | Different env var name; trivially corrected |
| A5 | High-water 0.80 / low-water 0.60 as recompaction thresholds | Pattern 3 | Too aggressive / too conservative; calibrated by planner via VOPT-03 test |
| A6 | Eviction pointer format: `↻ re-fetch via code_search("path") or find_definition("symbol")` | Eviction Pointer API | Model may not recognize the hint format; planner adjusts text |
| A7 | Savings ledger lives at `.voss/sessions/<id>/token-savings.jsonl` (subdirectory of session dir) | Savings Ledger | `_sessions_dir` returns the parent `.voss/sessions/`; full path is `_sessions_dir(cwd) / id / "token-savings.jsonl"`, NOT `_sessions_dir(cwd) / f"{id}.json"` (session JSON path is flat) |
| A8 | `_emit_context_osc` can carry savings fields without breaking Rust reader | Savings Ledger (F3 OSC) | If Rust reader validates exact field set, additive fields break it; must verify reader.rs extract_voss_osc |
| A9 | VOPT-07 "biting gate" achieved by running `recent_full_k=1, digest_cutoff_m=2` as the over-aggressive profile | Quality-Preservation Eval | Profile may not be aggressive enough to fail a golden task; may need even smaller K |

---

## Open Questions

1. **Second `cache_control` breakpoint for the stable replay prefix**
   - What we know: The SPEC marks this as optional for V18 ("MAY place a second `cache_control` breakpoint at the stabilized replay prefix")
   - What's unclear: Whether the Anthropic provider supports multiple `cache_control` breakpoints in one request; the exact message structure required
   - Recommendation: Defer to a `[context] second_breakpoint = false` default; implement as opt-in behind a config flag in V18; do not block V18 on this

2. **Rust reader (`reader.rs extract_voss_osc`) tolerance for new `_emit_context_osc` fields**
   - What we know: `_emit_budget_osc` shape is frozen (VOPT-08); `_emit_context_osc` is free-form `dict`
   - What's unclear: Whether the Rust reader does strict field validation on the context OSC or treats it as pass-through JSON
   - Recommendation: Read `crates/voss-tui/src/reader.rs` (or equivalent) before implementing F3 savings line; if strict validation found, add the savings field without changing existing fields

3. **F2 availability detection at runtime**
   - What we know: F2 is "plans ready to execute" — not shipped; eviction pointers should use M10 `code_search` by default
   - What's unclear: Whether to add a runtime check for F2 availability or simply hard-wire M10 for V18
   - Recommendation: Hard-wire M10 for V18; add a comment `# F2: if HybridSearchService available, prefer it` without implementing the conditional — V18 is "reuse M10, consume F2 when present" but F2 is not yet present

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 venv | All Python code | ✓ | 3.13 | — |
| litellm (in .venv) | token_counter, model_cost | ✓ | 1.84.0 | 4-char/token fallback already in `_default_token_count` |
| pytest + pytest-asyncio | Test suite | ✓ | (in .venv) | — |
| `.venv/bin/python` | Test runner | ✓ | 3.13 | bare python3 lacks deps (known project rule) |
| M10 CodeIntelService | Eviction pointers | ✓ | shipped | No eviction pointers (graceful degradation) |
| F2 HybridSearch | Optional richer pointers | ✗ | not shipped | Fall back to M10 code_search |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/harness/test_context_allocator.py tests/harness/test_savings_ledger.py -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VOPT-01 | 50 synthetic prior iters → assembled region ≤ ceiling; ≤K iters → byte-identical to pre-V18 | unit | `.venv/bin/python -m pytest tests/harness/test_context_allocator.py::test_pack_50_iters_under_ceiling tests/harness/test_context_allocator.py::test_below_threshold_byte_identical -x` | ❌ Wave 0 |
| VOPT-01 | Allocator runs with no provider and no filesystem | unit | `.venv/bin/python -m pytest tests/harness/test_context_allocator.py::test_allocator_pure -x` | ❌ Wave 0 |
| VOPT-02 | 20-iteration golden render shows full/digest/folded at configured boundaries; newest always full | unit | `.venv/bin/python -m pytest tests/harness/test_context_allocator.py::test_tier_boundaries_golden_render -x` | ❌ Wave 0 |
| VOPT-02 | Total tokens strictly ≤ full replay for any input | unit | `.venv/bin/python -m pytest tests/harness/test_context_allocator.py::test_packed_tokens_never_exceed_full -x` | ❌ Wave 0 |
| VOPT-03 | Stable-region hash unchanged across turns below high-water mark | unit | `.venv/bin/python -m pytest tests/harness/test_context_allocator.py::test_stable_region_append_only -x` | ❌ Wave 0 |
| VOPT-03 | Recompaction fires only on high-water crossing | unit | `.venv/bin/python -m pytest tests/harness/test_context_allocator.py::test_recompaction_on_high_water -x` | ❌ Wave 0 |
| VOPT-03 | Steady-state turns show cache_read_input_tokens dominating | integration | `.venv/bin/python -m pytest tests/harness/test_agent_packing.py::test_cache_coherence_steady_state -x` | ❌ Wave 0 |
| VOPT-04 | Folded iter with file references emits actionable re-fetch pointer | unit | `.venv/bin/python -m pytest tests/harness/test_context_allocator.py::test_eviction_pointer_emitted -x` | ❌ Wave 0 |
| VOPT-04 | V18 diff adds no index/embedding/vector code | coherence | `grep -rn "chromadb\|faiss\|annoy\|embedding" voss/harness/context_allocator.py voss/harness/agent.py` (should return empty) | manual |
| VOPT-05 | Multi-iter run writes ledger with packed <= original always | integration | `.venv/bin/python -m pytest tests/harness/test_savings_ledger.py::test_ledger_packed_le_original -x` | ❌ Wave 0 |
| VOPT-05 | --no-pack run records original == packed | integration | `.venv/bin/python -m pytest tests/harness/test_savings_ledger.py::test_no_pack_zero_savings -x` | ❌ Wave 0 |
| VOPT-05 | /cost prints savings line | integration | `.venv/bin/python -m pytest tests/harness/test_savings_ledger.py::test_cost_slash_prints_savings_line -x` | ❌ Wave 0 |
| VOPT-06 | --no-pack yields byte-identical messages to locked pre-V18 golden | acceptance | `.venv/bin/python -m pytest tests/harness/test_agent_packing.py::test_no_pack_byte_identical -x` | ❌ Wave 0 |
| VOPT-06 | Cached prefix bytes unchanged when packing toggled | acceptance | `.venv/bin/python -m pytest tests/harness/test_agent_packing.py::test_cached_prefix_unchanged -x` | ❌ Wave 0 |
| VOPT-07 | packing-on success >= packing-off success − tolerance; mean input tokens lower | eval (live/stub) | `.venv/bin/python -m pytest tests/harness/test_packing_eval_gate.py::test_quality_preservation_gate` | ❌ Wave 0 |
| VOPT-07 | Over-aggressive profile fails gate | eval | `.venv/bin/python -m pytest tests/harness/test_packing_eval_gate.py::test_aggressive_profile_fails_gate` | ❌ Wave 0 |
| VOPT-08 | Full harness suite green (no regressions) | regression | `.venv/bin/python -m pytest tests/ -q` | ✅ existing |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/harness/test_context_allocator.py -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/harness/ -q --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/test_context_allocator.py` — pure unit tests for ContextAllocator (VOPT-01/02/03/04)
- [ ] `tests/harness/test_savings_ledger.py` — ledger write/read + `/cost` assertions (VOPT-05)
- [ ] `tests/harness/test_agent_packing.py` — integration tests via FakeStreamingProvider (VOPT-03/06)
- [ ] `tests/harness/test_packing_eval_gate.py` — M5 eval wrapper + biting gate (VOPT-07)

---

## Security Domain

> ASVS enforcement enabled (absent = enabled from config.json).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (no auth surface added) |
| V3 Session Management | no | — (session IDs are pre-existing UUIDs) |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `packed_tokens_est <= original_tokens_est` invariant enforced before ledger write; ledger path uses `_sessions_dir(cwd)` (traversal-safe, follows existing pattern) |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `session_id` in ledger path | Tampering | Use `_sessions_dir(cwd) / sanitized_id / "token-savings.jsonl"` — same traversal-safe pattern as existing session.py |
| Phantom savings (`packed > original`) in ledger | Tampering/spoofing | Hard invariant check before write; clamp to 0 |
| Inflated $ figure (ignoring cache read discount) | Information disclosure | Net out `cache_read_input_token_cost` in estimate formula |
| Model string injection into `litellm.model_cost` lookup | Tampering | Use `dict.get()` with None fallback — no exec, no format string |

---

## Sources

### Primary (HIGH confidence)
- `voss/harness/agent.py` (read lines 1-1015) — chokepoint lines 708-716 confirmed; `_serialize_iter_for_replay` confirmed at 431-458; T4 prefix at 363-395; `_default_token_count` at 73-80; `token_budget=60_000` at 500; halt at 1008-1009; `all_iter_records` population at 992; `_build_iter_rider` existing digest pattern at 416-427
- `voss/harness/session.py` (read lines 55-130) — `_sessions_dir` at 57-58; `IterationRecord.cache_read_input_tokens` at 110-111
- `voss/harness/recorder.py` (read lines 90-155, 345-404) — `_emit_budget_osc` at 98-127 (shape); `_emit_context_osc` at 130-140; `end_iteration` at 363-401
- `voss/harness/code/service.py` (read lines 1-180) — `CodeIntelService.search`, `find_definition`, `find_references` signatures confirmed
- `voss/harness/config.py` (read full) — `[agent]` block parser pattern for `[context]` block design; existing sections confirmed
- `voss/harness/cli.py` (grep+read lines 881-918) — `_cost()` implementation; session context; `eval_cmd` signature; `--stub` flag pattern
- `voss/eval/runner.py` (read lines 1-330) — `run_suite()` signature; `SUITE_ROOT`; task drive pattern
- `voss/eval/suite.py` (full) — `TaskSpec`, `load_suite`, task directory structure
- `.planning/STATE.md` — F2 status confirmed: "Plans ready to execute" (not shipped)
- `litellm.model_cost` (runtime inspection with `LITELLM_LOCAL_MODEL_COST_MAP=true`) — `claude-opus-4-8` key exists; `input_cost_per_token: 5e-6`; `cache_read_input_token_cost: 5e-7`
- `litellm.token_counter("claude-sonnet-4-6", "Hello world")` returns `4` — confirmed working in venv

### Secondary (MEDIUM confidence)
- `tests/harness/test_agent_loop.py` (read) — `FakeStreamingProvider` test double pattern; `RecordingRenderer` pattern; existing passing test infrastructure
- `tests/harness/test_voss_loop_parity.py` (read) — `FakeProvider` + byte-identity test pattern
- `voss/harness/tools.py:22,308-309` (read) — `SHELL_OUTPUT_CAP_BYTES=30720` confirmed unchanged scope

---

## Metadata

**Confidence breakdown:**
- Chokepoint & integration seams: HIGH — source read directly; line numbers confirmed
- Cache coherence mechanics: HIGH — T4 prefix code confirmed; `IterationRecord` fields confirmed
- Tiered decay patterns: HIGH (existing rider digest pattern) / MEDIUM (allocator output format assumed)
- Savings ledger & litellm cost map: HIGH — runtime inspection confirmed key names and cache rate fields
- Eval integration: HIGH — `run_suite()` signature confirmed; golden tasks listed
- Default profile K/M values: ASSUMED — informed estimates; calibrated by VOPT-07 quality gate

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (stable codebase; litellm model_cost prices may shift, but `LITELLM_LOCAL_MODEL_COST_MAP=true` makes them reproducible)
