---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 05
type: execute
wave: 4
depends_on: [V19-02, V19-04, V19-06]
files_modified:
  - voss/harness/agent.py
  - voss/harness/cli.py
autonomous: true
requirements: [VSEM-06]
must_haves:
  truths:
    - "Top-k task-relevant code chunks are injected as a `## Code Recall` section in system context"
    - "The injected section is <=1000 tokens measured by the V18 token counter"
    - "The section lives inside the V18-packed variable region and is evictable under pressure (no second budget)"
    - "When the index is not ready the section is skipped entirely (no blocking, no placeholder)"
    - "`[code_recall] inject = false` produces zero injection bytes"
  artifacts:
    - path: "voss/harness/agent.py"
      provides: "code_recall_text param threaded through _compose_system_blocks + run_turn"
      contains: "code_recall_text"
    - path: "voss/harness/cli.py"
      provides: "_render_code_recall_text + wiring at do_cmd/chat_cmd"
      contains: "_render_code_recall_text"
  key_links:
    - from: "cli.py do_cmd/chat_cmd"
      to: "agent.run_turn(code_recall_text=...)"
      via: "_render_code_recall_text(cwd, task_text)"
      pattern: "code_recall_text="
    - from: "_compose_system_blocks"
      to: "V18 variable region"
      via: "evictable text block after project_index_text"
      pattern: "code_recall_text"
---

<objective>
Auto-inject top-k task-relevant code chunks into system context as an evictable, <=1000-token `## Code Recall` section living INSIDE the V18 variable region, with a config off-switch (VSEM-06). Thread `code_recall_text` through `_compose_system_blocks` + `run_turn` (agent.py) and render/wire it at `do_cmd`/`chat_cmd` (cli.py), parallel to the existing `project_index_text` flow.

Purpose: Surface concept-relevant code to the agent without a frontier grep loop, under the V18 token economy (no second budget system — the allocator may evict/fold it like any variable-region content).
Output: the `code_recall_text` parameter end-to-end + `_render_code_recall_text`. Sequenced last (Wave 4): depends on V19-02 query, V19-06 `inject` flag, and V19-04 (both edit cli.py — serialized to avoid conflict).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-SPEC.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-CONTEXT.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md

<interfaces>
voss/harness/agent.py:
  _compose_system_blocks(*, voss_md_block, cognition_text, principles_text="",
     project_index_text="", prior_context_text, loop_system) -> list[dict]   # agent.py:372-404
     # the `if text` filter drops empty strings — empty default = backward compatible
  run_turn(... project_index_text: str = "" ...)   # agent.py:502-520 — add code_recall_text param

voss/harness/cli.py:
  _render_project_index_text(cwd, session_id=None) -> str        # cli.py:767 — analog renderer
  do_cmd: project_index_text=_render_project_index_text(cwd)     # cli.py:1751, passed at run_turn ~1807
  chat_cmd: project_index_text=...                               # cli.py:2045-2075
  (other run_turn call sites with project_index_text: ~2207, ~2298, ~3289 — pass code_recall_text where the do/chat task text is available)

voss/harness/code/semantic_index.py (V19-02/03):
  CodeIndexService(cwd) / CodeIndex(cwd).query(query, top_k) -> list[Hit]; is_ready()
voss/harness/config.py (V19-06):
  get_code_recall_config()["inject"] -> bool   # off-switch
V18 token counter — the same counter used to measure project_index_text / variable-region content (reuse it; do not invent a counter)
</interfaces>

<!-- VSEM-06: <=1000 tokens by the V18 counter; lives in the V18 variable region (evictable); inject=false => zero bytes. -->
<!-- D-07: query = current task goal text (do prompt / first user message); skip entirely when index not ready (no placeholder). -->
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Thread code_recall_text through _compose_system_blocks + run_turn</name>
  <read_first>
    - tests/code_recall/test_injection.py (RED tests: test_token_cap, test_evictable, test_off_switch)
    - voss/harness/agent.py (lines 372-404 _compose_system_blocks; 502-520 run_turn signature + where project_index_text is threaded ~377/518)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md (agent.py section — exact surgical change)
  </read_first>
  <files>voss/harness/agent.py</files>
  <action>Surgical change to `_compose_system_blocks` (agent.py:372-404): add a keyword param `code_recall_text: str = ""` and insert `code_recall_text` into the text tuple immediately AFTER `project_index_text` so it joins the same `if text` filter that drops empty strings (empty default = fully backward compatible with all 3 existing call sites). Update `run_turn` (agent.py:502-520) signature to accept `code_recall_text: str = ""` parallel to `project_index_text: str = ""`, and pass it into the `_compose_system_blocks(...)` call inside run_turn. Because the block is appended to the existing variable-region content (the same tuple project_index_text lives in), it inherits V18 packing/eviction — add NO new budget path, NO separate injection slot, NO second token counter.</action>
  <verify>
    <automated>.venv/bin/python -c "import inspect; from voss.harness.agent import _compose_system_blocks, run_turn; print('code_recall_text' in inspect.signature(_compose_system_blocks).parameters, 'code_recall_text' in inspect.signature(run_turn).parameters)"; .venv/bin/python -m pytest tests/code_recall/test_injection.py::test_evictable tests/code_recall/test_injection.py::test_off_switch -x -q 2>&1 | tail -12</automated>
  </verify>
  <acceptance_criteria>
    - `code_recall_text` is a parameter of BOTH `_compose_system_blocks` and `run_turn` (signature assertion above prints `True True`)
    - `test_injection.py::test_evictable` passes: the V18 allocator can evict the `## Code Recall` block (it is in the variable-region tuple, not a fixed block)
    - empty `code_recall_text` produces zero blocks (filtered by `if text`) — existing agent tests unaffected: `.venv/bin/python -m pytest tests/harness/test_agent_packing.py -q` green
    - no new budget/counter introduced — source review confirms code_recall_text rides the existing variable-region tuple
  </acceptance_criteria>
  <done>code_recall_text threaded through _compose_system_blocks + run_turn as an evictable variable-region block; evict/off RED tests green; existing packing tests unaffected.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: _render_code_recall_text + wire at do_cmd/chat_cmd with <=1000-token cap and off-switch</name>
  <read_first>
    - tests/code_recall/test_injection.py (RED tests: test_token_cap, test_off_switch)
    - voss/harness/cli.py (lines 767-... _render_project_index_text analog; 1751 + 1807 do_cmd flow; 2045-2075 chat_cmd; 2207/2298/3289 other run_turn sites)
    - voss/harness/config.py (get_code_recall_config — inject flag from V19-06)
    - voss/harness/code/semantic_index.py (CodeIndexService.query/is_ready)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md (cli.py injection-wiring section)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-CONTEXT.md (D-07)
  </read_first>
  <files>voss/harness/cli.py</files>
  <action>Add `_render_code_recall_text(cwd, task_text, session_id=None) -> str` to `cli.py`, parallel to `_render_project_index_text`. Body: (1) read `get_code_recall_config()`; if `not cfg["inject"]` return `""` immediately (off-switch → zero bytes, VSEM-06). (2) Obtain the CodeIndexService for cwd; if `not service.is_ready()` return `""` (skip entirely when index not ready — no blocking, no placeholder, D-07). (3) Query `service.query(task_text, top_k=...)` where `task_text` is the current `voss do` prompt / first user message (D-07). (4) Format a `## Code Recall` section: a short header + one `path:line` + excerpt block per hit. (5) Enforce the <=1000-token cap using the SAME V18 token counter that measures project_index_text — append hit blocks until adding the next would exceed 1000 tokens, then stop (hard cap, VSEM-06). Return the section string (or "" if no hits). Wire it: at `do_cmd` (cli.py:1751) add `code_recall_text = _render_code_recall_text(cwd, text)` near the `project_index_text` line and pass `code_recall_text=code_recall_text` into the `run_turn(...)` call (~1807). Apply the same wiring at `chat_cmd` (2045-2075) and at the other run_turn call sites (2207, 2298, 3289) where the task/user-message text is in scope — pass the rendered text, or `""` where no task text is available. Do not block the turn on the index; render returns "" fast when not ready.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/test_injection.py -x -q 2>&1 | tail -15; .venv/bin/python -c "from voss.harness.cli import _render_code_recall_text; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `test_injection.py::test_token_cap` passes: the rendered `## Code Recall` section is <=1000 tokens by the V18 counter
    - `test_injection.py::test_off_switch` passes: `inject=false` → `_render_code_recall_text` returns `""` (zero injection bytes)
    - when `service.is_ready()` is False, `_render_code_recall_text` returns `""` without querying/blocking (source review — D-07)
    - the <=1000 cap uses the SAME V18 token counter as project_index_text (source review — no second counter)
    - `do_cmd` and `chat_cmd` pass `code_recall_text=` into `run_turn` (`grep -n "code_recall_text=" voss/harness/cli.py` shows the call sites)
    - coherence: `.venv/bin/python -m pytest tests/harness/ -q -k "cli or packing"` green (wiring non-breaking)
  </acceptance_criteria>
  <done>_render_code_recall_text caps at <=1000 V18 tokens, honors the inject off-switch, skips when not ready, and is wired into do_cmd/chat_cmd + other run_turn sites; injection RED tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| code chunk hits → system context | repo source injected into the model's system prompt |
| task text → code index query | the user's task prompt drives chunk selection |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V19-05-01 | Denial of Service | unbounded injected context | mitigate | Hard <=1000-token cap by the V18 counter; section lives in the evictable V18 variable region (no second budget) — VSEM-06 |
| T-V19-05-02 | Tampering | injected chunk text | mitigate | Injected chunks are raw repo source rendered as a text block in system context, never executed; agent already has read scope to these files (ASVS V5) |
| T-V19-05-03 | Denial of Service | injection blocking the turn before index ready | mitigate | `_render_code_recall_text` returns "" immediately when `not is_ready()` — no blocking, no placeholder (D-07, VSEM-03 coherence) |
| T-V19-05-04 | Information Disclosure | off-switch bypass | mitigate | `inject=false` short-circuits before any query/render → zero injection bytes (off-switch test) |
| T-V19-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: zero new deps) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/code_recall/test_injection.py tests/harness/test_agent_packing.py -q` — green
- Coherence guard: `voss do` / `voss chat` start and run a turn end-to-end with injection wired (existing harness regression suite green)
</verification>

<success_criteria>
- code_recall_text threaded end-to-end; `## Code Recall` section <=1000 V18 tokens, evictable
- inject=false → zero bytes; not-ready → skipped (no block)
- wired at do_cmd/chat_cmd + remaining run_turn sites
</success_criteria>

<output>
Create `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-05-SUMMARY.md` when done
</output>
