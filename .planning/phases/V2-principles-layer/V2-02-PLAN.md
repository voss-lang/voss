---
phase: V2-principles-layer
plan: 02
type: execute
wave: 2
depends_on: [V2-01]
files_modified:
  - voss/harness/agent.py
  - voss/harness/render.py
  - tests/harness/test_principles_injection.py
autonomous: true
requirements: [VPRIN-04]
must_haves:
  truths:
    - "The system prompt for a `voss do`/`voss chat` turn contains a distinct `## Principles` block"
    - "The principles block is a separate labeled block (not merged into cognition or VOSS.md) inside the cacheable static prefix"
    - "An over-cap principles set truncates and emits a `principles_overflow` renderer event"
    - "With no project file, the injected block carries the six default principles"
  artifacts:
    - path: "voss/harness/agent.py"
      provides: "PRINCIPLES_BUDGET_TOKENS, _compose_principles_block, principles_text param on _compose_system_blocks, wired call site"
      contains: "PRINCIPLES_BUDGET_TOKENS"
    - path: "voss/harness/render.py"
      provides: "show_principles_overflow renderer method on Renderer protocol + all renderer impls"
      contains: "principles_overflow"
    - path: "tests/harness/test_principles_injection.py"
      provides: "block-present, separate-block, overflow-event, defaults-injected tests via stub renderer"
      contains: "principles_overflow"
  key_links:
    - from: "voss/harness/agent.py:_compose_system_blocks"
      to: "principles_text"
      via: "distinct labeled block in the blocks list"
      pattern: "principles_text"
    - from: "voss/harness/agent.py:_compose_principles_block"
      to: "render.show_principles_overflow"
      via: "overflow event on cap exceed"
      pattern: "principles_overflow"
---

<objective>
Inject the resolved principles as a distinct, labeled `## Principles` block into the cacheable static prefix assembled by `_compose_system_blocks`, so `voss do`/`voss chat` (and current subagents) carry the team's principles as opaque text. Mirror cognition's budget pattern at ~1k tokens: truncate on overflow and emit a new `principles_overflow` renderer event.

Purpose: Realize VPRIN-04 — principles reach the live agent context via the existing injection seam, capped and overflow-warned exactly like cognition's 6k pattern.
Output: capped principles block composed and wired into the system prompt; a new renderer overflow event.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V2-principles-layer/V2-SPEC.md
@.planning/phases/V2-principles-layer/V2-CONTEXT.md

<interfaces>
<!-- The injection seam + the cognition cap/overflow pattern to mirror -->
From voss/harness/agent.py:
- `COGNITION_BUDGET_TOKENS = 6000` (L53) — budget constant precedent.
- `_default_token_count(text, *, model) -> int` (L69) — REUSE this exact token-count helper; pass it the same way cognition does.
- `_compose_cognition_prompt(bundle, *, model, token_count_fn, renderer)` (L79) — the cap → measure → on-overflow truncate + `renderer.show_cognition_overflow(...)` → return truncated body pattern to MIRROR at ~1k.
- `_compose_system_blocks(*, voss_md_block, cognition_text, project_index_text="", prior_context_text, loop_system) -> list[dict]` (L318) — the ordered cacheable text-block assembler. Add a `principles_text` param; insert it as its OWN block. The LAST non-empty block gets `cache_control: ephemeral` — principles is static-per-run so it belongs inside this prefix.
- Call site (L571-586): `cognition_text = _compose_cognition_prompt(...)` then `sys_blocks = _compose_system_blocks(voss_md_block=..., cognition_text=..., project_index_text=..., prior_context_text=..., loop_system=...)`. Compose principles_text here (alongside cognition_text) and pass it in.

From voss/harness/render.py:
- `class Renderer(Protocol)` (L28) — add the new event signature here.
- `def show_cognition_overflow(self, *, architecture_tokens: int, budget: int = 6000) -> None` (L55 proto; L263 TtyRenderer impl) — the precedent shape to mirror as `show_principles_overflow`. Renderer impls: TtyRenderer, CompactRenderer, PlainRenderer, JsonRenderer (each needs the method; quiet/no-op acceptable for compact/plain/json per their existing style).

From voss/harness/principles.py (V2-01 output):
- `resolve_principles(cwd) -> PrinciplesConfig` (or `merge_principles(...)`) and `resolve_with_sources(cwd)` — the active merged set + provenance. Use `resolve_principles` for injection (text only).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add show_principles_overflow renderer event</name>
  <files>voss/harness/render.py, tests/harness/test_principles_injection.py</files>
  <read_first>
    - voss/harness/render.py (L28-58 Renderer protocol; L263-273 TtyRenderer.show_cognition_overflow + show_warning; L277, L404, L485 the Compact/Plain/Json renderer classes)
    - .planning/phases/V2-principles-layer/V2-CONTEXT.md (D-05 — overflow event named like `principles_overflow`)
  </read_first>
  <behavior>
    - Test: a stub/real renderer exposes `show_principles_overflow(*, principles_tokens, budget=...)`; calling it does not raise.
    - Test: the message/event surfaces the word `principles` and the over-budget token count (assert on captured output or a stub recorder), mirroring `show_cognition_overflow`.
  </behavior>
  <action>
    In `voss/harness/render.py` add `show_principles_overflow(self, *, principles_tokens: int, budget: int = 1000) -> None` to the `Renderer` Protocol (next to `show_cognition_overflow`) and implement it on every renderer impl class — `TtyRenderer` (a yellow warning mirroring `show_cognition_overflow`: e.g. "principles block is {principles_tokens} tokens (over {budget} budget) — truncated"), `CompactRenderer`, `PlainRenderer`, `JsonRenderer` (match each class's existing overflow/warning style; quiet-respecting no-op where the class already no-ops). The event NAME/identifier the harness uses MUST be `principles_overflow` (method name `show_principles_overflow`; any telemetry/event string uses `principles_overflow`). Create `tests/harness/test_principles_injection.py` with a small stub renderer recording overflow calls, covering the <behavior> bullets (the injection tests in Task 2 reuse this stub).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_principles_injection.py -x -q -k overflow_event_shape 2>&1 | tail -5; .venv/bin/python -c "from voss.harness.render import TtyRenderer, CompactRenderer, PlainRenderer, JsonRenderer; [getattr(c, 'show_principles_overflow') for c in (TtyRenderer, CompactRenderer, PlainRenderer, JsonRenderer)]; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `show_principles_overflow` exists on the Renderer protocol and on all four renderer impl classes (the `python -c` import-and-getattr probe prints OK).
    - The event identifier is `principles_overflow` (method `show_principles_overflow`), mirroring `show_cognition_overflow`.
    - The stub-renderer overflow-shape test passes.
  </acceptance_criteria>
  <done>A `principles_overflow` renderer event exists across all renderer impls, mirroring cognition's overflow event; stub recorder + shape test green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Compose + inject the capped ## Principles block</name>
  <files>voss/harness/agent.py, tests/harness/test_principles_injection.py</files>
  <read_first>
    - voss/harness/agent.py (L53 COGNITION_BUDGET_TOKENS; L69 _default_token_count; L79-132 _compose_cognition_prompt cap pattern; L318-346 _compose_system_blocks; L571-586 the call site)
    - voss/harness/principles.py (V2-01: resolve_principles / resolve_with_sources)
    - voss/harness/render.py (Task 1: show_principles_overflow)
    - .planning/phases/V2-principles-layer/V2-SPEC.md (Requirement 3, Acceptance Criteria 4 & 5)
    - .planning/phases/V2-principles-layer/V2-CONTEXT.md (D-03 distinct block in static prefix; D-05 ~1k cap + overflow + reuse token helper)
  </read_first>
  <behavior>
    - Test: `_compose_principles_block` for the default set returns a string beginning with a `## Principles` heading and containing each default principle's text; with no project file the six defaults appear.
    - Test: an over-cap principles set (force a tiny `PRINCIPLES_BUDGET_TOKENS` or feed many long principles) returns a truncated body AND calls `renderer.show_principles_overflow(...)` exactly (assert via the Task 1 stub).
    - Test: `_compose_system_blocks(..., principles_text="## Principles\n...")` returns a blocks list where the principles text is its OWN distinct block (a list entry whose text starts with `## Principles`), separate from `cognition_text` and `voss_md_block` (assert no merge — count blocks / find the principles entry).
    - Test: when `principles_text` is empty, no principles block appears (existing block behavior preserved — falsy blocks filtered).
  </behavior>
  <action>
    In `voss/harness/agent.py`: define `PRINCIPLES_BUDGET_TOKENS = 1000` near `COGNITION_BUDGET_TOKENS`. Add `_compose_principles_block(config, *, model, token_count_fn=None, renderer=None) -> str` mirroring `_compose_cognition_prompt`'s shape: render a distinct `## Principles` heading followed by the active principles (one bullet per principle, opaque text only — iterate the config's ordered `principles` tuple, never branch on a key); if `token_count_fn` is None return the full body; else measure with the SAME `_default_token_count` helper cognition uses; if `measured <= PRINCIPLES_BUDGET_TOKENS` return full body; on overflow emit `renderer.show_principles_overflow(principles_tokens=measured, budget=PRINCIPLES_BUDGET_TOKENS)` (guarded try/except like cognition) and return a truncated body — lock the truncation priority rule here (Claude's discretion): drop whole principles from the END of the ordered list until under budget, appending a "(principles truncated due to budget)" marker, so earlier/default principles survive deterministically. Add a `principles_text: str = ""` parameter to `_compose_system_blocks` and insert it as its OWN entry in the `(voss_md_block, cognition_text, principles_text, project_index_text, prior_context_text, loop_system)` tuple — place it AS A SEPARATE BLOCK adjacent to cognition (lock ordinal: immediately after `cognition_text`), inside the existing falsy-filter + trailing `cache_control: ephemeral` logic (do NOT merge it into cognition_text or voss_md_block). At the call site (~L571-586) compose `principles_text = _compose_principles_block(resolve_principles(cwd), model=model, token_count_fn=_default_token_count, renderer=renderer)` and pass `principles_text=principles_text` into `_compose_system_blocks`. Import `resolve_principles` from `voss.harness.principles`. Role-specific EM/reviewer/tester contexts are NOT wired here (SPEC out-of-scope). Extend `tests/harness/test_principles_injection.py` with the <behavior> bullets (use the Task 1 stub renderer; for the block-separation test call `_compose_system_blocks` directly with a known `principles_text`).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_principles_injection.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `_compose_principles_block` emits a `## Principles` heading + each active principle's opaque text; defaults present when no project file.
    - `_compose_system_blocks` returns the principles text as a DISTINCT block (test asserts a standalone list entry starting with `## Principles`, not merged into cognition/VOSS.md).
    - An over-cap set truncates AND calls `show_principles_overflow` (asserted via stub); `PRINCIPLES_BUDGET_TOKENS = 1000` defined.
    - `.venv/bin/python -m pytest tests/harness/test_principles_injection.py -x -q` exits 0; full agent suite unbroken (`.venv/bin/python -m pytest tests/harness/test_agent_caching.py -q` green — block-list/cache invariant intact).
  </acceptance_criteria>
  <done>Principles inject as a distinct, capped `## Principles` block in the static prefix via `_compose_system_blocks`; ~1k cap truncates + emits `principles_overflow`; call site wired through `resolve_principles`; tests green and no agent-caching regression.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| principles config → system prompt | Resolved principle text crosses into the LLM system prompt as opaque injected text. |
| principles block → token budget | Untrusted-size principle text crosses the ~1k-token cap boundary. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V2-04 | Denial of Service | oversized principles block | mitigate | `PRINCIPLES_BUDGET_TOKENS=1000` hard cap; deterministic end-of-list truncation; `principles_overflow` event emitted. |
| T-V2-05 | Elevation of Privilege | principle text as instructions | accept | Principles are opaque culture text injected as a labeled block; no tool/permission grant derives from them (guard test in V2-03 enforces no control-flow coupling). |
| T-V2-06 | Tampering | cache-prefix block-list shape | mitigate | New block respects the existing falsy-filter + trailing `cache_control: ephemeral` invariant; run `test_agent_caching.py` to confirm cache prefix unbroken. |
| T-V2-SC | Tampering | npm/pip installs | mitigate | No package installs in this plan; legitimacy gate N/A. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_principles_injection.py -q` passes.
- `.venv/bin/python -m pytest tests/harness/test_agent_caching.py -q` passes (block-list / cache prefix invariant intact).
- `grep -n "PRINCIPLES_BUDGET_TOKENS" voss/harness/agent.py` returns the `= 1000` definition.
- `grep -n "principles_overflow" voss/harness/render.py voss/harness/agent.py` confirms the overflow event is wired.
</verification>

<success_criteria>
- Active principles inject as a distinct `## Principles` block into the `voss do`/`voss chat` system prompt via `_compose_system_blocks`.
- ~1k-token cap truncates deterministically and emits `principles_overflow`.
- VPRIN-04 complete; no agent-caching/cache-prefix regression.
</success_criteria>

<output>
Create `.planning/phases/V2-principles-layer/V2-02-SUMMARY.md` when done.
</output>
