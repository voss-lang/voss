---
phase: T4-prompt-caching-cost-truthfulness
plan: 03
type: execute
wave: 3
depends_on: ["T4-01", "T4-02"]
files_modified:
  - voss/harness/agent.py
  - tests/harness/test_agent_caching.py
  - tests/harness/test_cache_invalidation.py
autonomous: true
requirements: [CACHE-01, CACHE-06]

must_haves:
  truths:
    - "agent.py exposes a module-level `_compose_system_blocks(*, voss_md_block, cognition_text, prior_context_text, loop_system) -> list[dict]`."
    - "Each non-empty input becomes one `{'type': 'text', 'text': ...}` block."
    - "Exactly one block — the LAST static-prefix block — carries `cache_control: {'type': 'ephemeral'}`."
    - "Empty inputs produce an empty block list (no spurious marker)."
    - "The run_turn message list now sends the cached prefix as `messages[0]['content'] = sys_blocks` (list) instead of `sys_prompt` (string). Rider stays as `messages[1]` and remains uncached."
    - "Each of four drift triggers (VOSS.md, cognition, prior_context, max_iterations) produces a byte-different rendered block list via `json.dumps(blocks, sort_keys=True)`."
  artifacts:
    - path: "voss/harness/agent.py"
      provides: "_compose_system_blocks helper + multi-block messages[0] composition."
      contains: "_compose_system_blocks"
    - path: "tests/harness/test_agent_caching.py"
      provides: "CACHE-01 marker shape + position assertions (green)."
    - path: "tests/harness/test_cache_invalidation.py"
      provides: "CACHE-06 four-drift parametrized assertions (green)."
  key_links:
    - from: "voss/harness/agent.py:run_turn"
      to: "_compose_system_blocks"
      via: "function call replacing sys_prompt str join"
      pattern: "_compose_system_blocks\\("
---

<objective>
Restructure the agent.py system-prompt composition from a single joined string into a multi-block list with one trailing `cache_control: ephemeral` marker on the last static-prefix block. Land the four-drift invalidation test suite. Turn the two T4-01 red stubs for CACHE-01 and CACHE-06 green.

Purpose: This is the harness-side core of T4. The block list is the wire format LiteLLM's `translate_system_message` propagates to Anthropic verbatim (RESEARCH.md Pattern 1; verified against litellm 1.74.7 transformation.py:545-596). The byte-diff invalidation tests are the falsifiability anchor proving D-08's four drift triggers actually mutate the rendered prefix.
Output: One new helper in agent.py + replacement of two existing composition sites + two green test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-SPEC.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-CONTEXT.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-RESEARCH.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-PATTERNS.md
@voss/harness/agent.py

<interfaces>
<!-- Existing helper that the new composer consumes verbatim. -->

From voss/harness/agent.py:285-287:
```python
def _compose_loop_system(max_iterations: int) -> str:
    """Fill the PLAN_LOOP_SYSTEM placeholder via str.replace (cache-stable)."""
    return PLAN_LOOP_SYSTEM.replace("{max_iterations}", str(max_iterations))
```

The new helper signature (insert immediately AFTER `_compose_loop_system`):
```python
def _compose_system_blocks(
    *,
    voss_md_block: str,
    cognition_text: str,
    prior_context_text: str,
    loop_system: str,
) -> list[dict]:
    ...
```

Existing call site to REPLACE (voss/harness/agent.py:506-516): builds `sys_prompt = "\n\n".join(...)` from `voss_md_block, cognition_text, prior_context_text, _compose_loop_system(max_iterations)`. The replacement constructs `sys_blocks = _compose_system_blocks(...)` from the same four inputs.

Existing messages list to MODIFY (voss/harness/agent.py:569-573):
```python
messages: list[dict] = [
    {"role": "system", "content": sys_prompt},
    {"role": "system", "content": rider},
    {"role": "user", "content": user_prompt},
]
```
The first entry's `content` becomes `sys_blocks` (list of dicts). Rider stays a string and remains an uncached messages[1].
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add _compose_system_blocks helper and turn CACHE-01 test green</name>
  <files>voss/harness/agent.py, tests/harness/test_agent_caching.py</files>
  <behavior>
    - `_compose_system_blocks(voss_md_block="A", cognition_text="B", prior_context_text="C", loop_system="D")` returns a list of 4 dicts, each `{"type": "text", "text": ...}`, with the last block carrying `cache_control: {"type": "ephemeral"}`.
    - All-empty inputs return `[]` (no blocks at all → no spurious marker; matches behavior of pre-T4 `"\n\n".join(... if s)` which produces an empty string).
    - Inputs that are empty strings are filtered out (`if text:` guard) — only non-empty slices become blocks.
    - Exactly one block carries `cache_control` regardless of how many non-empty inputs there are.
  </behavior>
  <action>
    Insert `_compose_system_blocks` into `voss/harness/agent.py` immediately AFTER the existing `_compose_loop_system` function (after current line 287). Use the body from T4-PATTERNS.md "Apply to `voss/harness/agent.py`" / RESEARCH.md Pattern 1:

    The helper iterates the four inputs in order, appends `{"type": "text", "text": text}` for each non-empty one, then mutates the final element in-place via `blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}` (preserves immutability of earlier elements). Returns `list[dict]`.

    Docstring cites CACHE-01 + CACHE-06 invalidation behavior (block-level slicing preserves D-08 byte-diff resolution; collapsing to a joined string would collapse the four drift surfaces into one).

    Turn the two T4-01 red stubs in `tests/harness/test_agent_caching.py` GREEN:
    - `test_system_blocks_have_single_marker`: build with four non-empty inputs, assert `isinstance(blocks, list)`, `len(blocks) == 4`, all `b["type"] == "text"`, exactly one block has `cache_control`, the marker is on `blocks[-1]`, and the marker value is `{"type": "ephemeral"}`.
    - `test_empty_inputs_produce_empty_block_list`: build with all-empty strings, assert `blocks == []`.

    Do NOT touch the existing `_compose_loop_system`, `_build_iter_rider`, or any other helper. Do NOT modify the messages-list composition site yet — that lands in Task 2 so the failure surface is bisectable.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_agent_caching.py -x -q</automated>
  </verify>
  <done>Both tests in test_agent_caching.py pass. `_compose_system_blocks` exists and is callable from `voss.harness.agent`.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Replace string composition with block list at the messages-build site</name>
  <files>voss/harness/agent.py</files>
  <behavior>
    - The run_turn function builds `sys_blocks: list[dict]` instead of `sys_prompt: str`.
    - `messages[0]["content"]` is the block list (cached static prefix).
    - `messages[1]["content"]` is the per-iter rider string (uncached) — unchanged.
    - `messages[2]["content"]` is the user prompt — unchanged.
    - The existing prior-iters replay (`for prior in all_iter_records: ...`) is unchanged.
    - All other code paths (cognition.snapshot emit, telemetry events, exit handling) are untouched.
  </behavior>
  <action>
    Two surgical edits in `voss/harness/agent.py`:

    (1) Replace lines 506-516 (current `voss_md_block = ...` + `sys_prompt = "\n\n".join(...)` block) with the new composition per T4-PATTERNS.md "Apply to messages-build site":
    ```
    voss_md_block = f"# VOSS.md\n{voss_md_text}" if voss_md_text else ""
    sys_blocks = _compose_system_blocks(
        voss_md_block=voss_md_block,
        cognition_text=cognition_text,
        prior_context_text=prior_context_text,
        loop_system=_compose_loop_system(max_iterations),
    )
    ```
    Add a one-line comment above `sys_blocks = ...`: `# T4 CACHE-01: cached static prefix as block list; rider (below, per-iter) stays a string and remains uncached.`

    (2) Replace line 570 (`{"role": "system", "content": sys_prompt},`) with `{"role": "system", "content": sys_blocks},  # cached static prefix (CACHE-01)`. Do NOT modify lines 571 or 572 — rider and user prompt unchanged.

    Run the full harness test suite (excluding the still-red T4 tests) to verify no regression. The agent loop's downstream Usage / Plan handling is untouched.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py tests/harness/test_agent_integration.py tests/harness/test_agent_caching.py -x -q</automated>
  </verify>
  <done>
    Existing agent tests still pass. `grep -n 'sys_prompt' voss/harness/agent.py` returns no matches (the variable name is fully replaced). `grep -n 'sys_blocks' voss/harness/agent.py` returns exactly the composition line + the messages-list line. test_agent_caching.py still green.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Turn CACHE-06 four-drift invalidation test green</name>
  <files>tests/harness/test_cache_invalidation.py</files>
  <behavior>
    - Each of four drift triggers (VOSS.md, cognition, prior_context, max_iterations) produces a byte-different rendered block list.
    - Comparison is `json.dumps(blocks, sort_keys=True).encode()` — deterministic, captures any nested `cache_control` movement.
    - Parametrized cases use the IDs from VALIDATION.md: `voss_md`, `cognition`, `prior_ctx`, `max_iters`.
  </behavior>
  <action>
    Convert the T4-01 red `test_drift_changes_rendered_prefix` stub in `tests/harness/test_cache_invalidation.py` to a working parametrized test per RESEARCH.md §"Cache-invalidation test scaffold" and T4-PATTERNS.md.

    Imports: `json`, `pytest`, `from voss.harness.agent import _compose_system_blocks, _compose_loop_system`.

    Helper `_render(*, voss_md, cognition, prior_ctx, max_iters)` calls `_compose_system_blocks(voss_md_block=f"# VOSS.md\n{voss_md}" if voss_md else "", cognition_text=cognition, prior_context_text=prior_ctx, loop_system=_compose_loop_system(max_iters))`.

    Parametrize with the four cases from T4-PATTERNS.md / RESEARCH.md (each case mutates exactly ONE field — voss_md, cognition, prior_ctx, or max_iters — between dict A and dict B; the other three are constant). Each test invocation asserts `json.dumps(_render(**a), sort_keys=True).encode() != json.dumps(_render(**b), sort_keys=True).encode()` with a failure message naming the drift field.

    Add a docstring at module level: `"""CACHE-06: each of the four locked drift triggers (D-08) produces a byte-different rendered prefix, forcing Anthropic's per-block cache miss."""`

    Do NOT test model swap — D-08 documents it as inherent to Anthropic's per-model keying and explicitly NOT a Voss-side test.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_cache_invalidation.py -x -q</automated>
  </verify>
  <done>All four parametrize cases pass. The test enforces that `_compose_system_blocks` preserves block boundaries (collapsing to a single joined string would break the byte-diff resolution for individual drift cases).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| harness→provider | Multi-block content list crosses the agent→provider boundary; LiteLLM's `translate_system_message` propagates `cache_control` verbatim (verified RESEARCH.md §Summary). |
| user→harness (VOSS.md) | VOSS.md is a user-authored project file feeding the cached prefix. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T4-03-01 | Tampering | _compose_system_blocks input | mitigate | `cache_control` marker placed by Voss-controlled composer, never by user content. The marker dict is constructed inline (`{"type": "ephemeral"}`) — no way for caller-supplied strings to inject a structural change. |
| T-T4-03-02 | Tampering | VOSS.md drift | mitigate | CACHE-06 invalidation tests assert prefix mutation invalidates cache, preventing cross-version cache poisoning (RESEARCH.md §Security Domain). |
| T-T4-03-03 | Information Disclosure | block list content | accept | System prompt content (VOSS.md, cognition, prior_context, loop system) is part of the Voss harness contract today; no new disclosure surface. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py -x -q` exits 0.
- `python3 -m pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py tests/harness/test_agent_integration.py -x -q` still green (no regression in existing agent tests despite the messages[0] shape change).
- `grep -n 'sys_prompt' voss/harness/agent.py | grep -v '^#'` returns zero matches.
- `grep -nE '_compose_system_blocks\b' voss/harness/agent.py` returns: one definition + one call site.
- `python3 -c "from voss.harness.agent import _compose_system_blocks; b=_compose_system_blocks(voss_md_block='A', cognition_text='B', prior_context_text='C', loop_system='D'); assert len(b)==4 and b[-1]['cache_control']=={'type':'ephemeral'}"` exits 0.
</verification>

<success_criteria>
- `_compose_system_blocks` exists, is callable, and returns a list of typed text blocks with exactly one trailing `cache_control: ephemeral` marker.
- `voss/harness/agent.py` sends `messages[0]["content"]` as a block list (not a joined string).
- Rider stays a separate uncached `messages[1]` system message — D-01 contract preserved.
- CACHE-01 marker-shape stub and CACHE-06 four-drift stub are GREEN.
- No existing harness test regresses (the messages[0] shape change is invisible to stub providers and to tests that don't introspect the wire format).
- No OAuth-provider path modified (Pitfall 3 deferral honored — caching scoped to LiteLLM path).
</success_criteria>

<output>
Create `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-03-SUMMARY.md` when done. Note explicitly that OAuth-provider cache marker preservation is OUT OF T4 scope per RESEARCH.md Pitfall 3 and is a v0.2 follow-up (`AnthropicOAuthProvider._payload` reconstructs `[{"type":"text","text":chunk}]` and silently drops markers from list-typed content).
</output>
