---
phase: M3
plan: 04
type: execute
wave: 1
depends_on: [M1, M2, M3-02]
files_modified:
  - samples/classify.voss
  - samples/support.voss
  - samples/research.voss
  - examples/raw_python/support.py
  - examples/raw_python/research.py
autonomous: true
requirements:
  - LANG-01
  - LANG-02
  - LANG-04
  - LANG-06
  - LANG-07
  - LANG-08
tags:
  - samples
  - parity
  - framing

must_haves:
  truths:
    - "samples/classify.voss opens with a header comment line naming the primitives demonstrated (`# classify.voss — probable<T>, confidence gate (@ p >= 0.80), implicit ctx fallback.` or equivalent)."
    - "samples/support.voss opens with a header comment naming primitives AND now declares `let tickets: memory.episodic(capacity: 50 turns)` AND calls `tickets.add(userMessage, role: \"user\")` at the top of handleMessage AND `include tickets.last(6)` inside the `case _` ctx block."
    - "samples/research.voss opens with a header comment naming primitives AND now begins with `use voss_runtime::tools::tool` AND wraps the `webSearch(topic, max_results: 5)` call in `try { ... } catch e { include \"web search unavailable\" }` inside the Researcher agent's ctx block."
    - "voss check samples/{classify,support,research}.voss exits 0 against the extended samples (parser/analyzer/codegen all support the constructs per RESEARCH §Summary; no compiler changes are required in this plan)."
    - "examples/raw_python/support.py imports EpisodicMemory and constructs a module-scope tickets = EpisodicMemory(capacity=50); handle_message calls tickets.add(user_message, role=\"user\") and adds tickets.render() (last 6 turns) to the ContextScope in the fallback branch."
    - "examples/raw_python/research.py wraps the web_search call inside Researcher.run with a try/except Exception that falls back to adding 'web search unavailable' to the context."
    - "voss run samples/classify.voss under VOSS_HERMETIC=1 (depends on M3-02's providers.get hook landed in Wave 0) exits 0 with non-empty stdout — the LANG-10 contract per D-04."
  artifacts:
    - path: "samples/classify.voss"
      provides: "header comment line + unchanged body (LANG-02 demo)"
      contains: "probable"
    - path: "samples/support.voss"
      provides: "header comment + memory.episodic declaration + add/last calls (D-05 + D-14)"
      contains: "memory.episodic"
    - path: "samples/research.voss"
      provides: "header comment + use voss_runtime::tools::tool + try/catch around webSearch (D-06 + D-14)"
      contains: "try"
    - path: "examples/raw_python/support.py"
      provides: "EpisodicMemory parity matching samples/support.voss (D-12)"
      contains: "EpisodicMemory"
    - path: "examples/raw_python/research.py"
      provides: "try/except around web_search matching samples/research.voss (D-12)"
      contains: "except Exception"
  key_links:
    - from: "samples/support.voss::handleMessage"
      to: "memory.episodic(capacity: 50 turns)"
      via: "let tickets declaration + tickets.add + tickets.last(6)"
      pattern: "tickets.add\\|tickets.last"
    - from: "samples/research.voss::Researcher"
      to: "try { webSearch(...) } catch e { ... }"
      via: "try_stmt grammar.lark:133 lowering to codegen.py:1107-1126"
      pattern: "try \\{\\|catch"
    - from: "examples/raw_python/support.py::handle_message"
      to: "tickets.add + tickets.render"
      via: "module-scope EpisodicMemory(capacity=50)"
      pattern: "tickets\\.(add|render|last)"
    - from: "examples/raw_python/research.py::Researcher.run"
      to: "try: web_search(...) except Exception"
      via: "fallback writes 'web search unavailable' to ctx"
      pattern: "except Exception"
---

<objective>
Extend the three canonical samples and their raw-python parity oracles per D-05, D-06, D-14, and bundled D-12 (same-PR sample ↔ raw-parity coupling). After this plan, `voss check samples/{classify,support,research}.voss` continues to exit 0; `voss run samples/classify.voss` works hermetically (because M3-02 landed in Wave 0); the e2e test repoint in M3-05 will validate the extensions end-to-end against the raw_python oracles.

Purpose: D-05 (`memory.episodic` in support) + D-06 (`try/catch` + `use` in research) are the LANG-07 + LANG-08 runnable-sample coverage. D-14 sample headers are the per-sample LANG-01 framing surface. D-12 requires the raw-python files to stay in lockstep with the .voss source, so this plan bundles the matching edits into the same tasks per RESEARCH §Pitfall 7. D-08 (`prompt` + `@tool` coverage) is intentionally a no-op: the existing `prompt SupportAgent { ... }` block in samples/support.voss and the implicit `@tool` surface via `tools: [webSearch]` in samples/research.voss already satisfy LANG-08 for those two constructs; this plan preserves those existing lines unchanged, completing D-08 by non-edit.

Wave note: this plan was promoted from Wave 0 to Wave 1 to honor a soft dependency on M3-02. The Task-2 and Task-3 verify steps invoke `VOSS_HERMETIC=1 python3 examples/raw_python/{support,research}.py`, which depends on M3-02 Task 1's `voss_runtime/providers/__init__.py` env-var short-circuit being committed first. M3-04 cannot run in parallel with M3-02.

Output:
- `samples/classify.voss` — header comment line added; body unchanged.
- `samples/support.voss` — header comment + memory.episodic declaration + `.add` / `.last` calls.
- `samples/research.voss` — header comment + `use voss_runtime::tools::tool` + try/catch around webSearch.
- `examples/raw_python/support.py` — EpisodicMemory parity (matches the .voss source under same StubProvider seed).
- `examples/raw_python/research.py` — try/except parity around web_search.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M3-language-validation/M3-CONTEXT.md
@.planning/phases/M3-language-validation/M3-RESEARCH.md
@.planning/phases/M3-language-validation/M3-PATTERNS.md
@samples/classify.voss
@samples/support.voss
@samples/research.voss
@examples/raw_python/support.py
@examples/raw_python/research.py
@tests/parser/examples/assistant.voss
@voss_runtime/memory/episodic.py
@voss_runtime/__init__.py

<interfaces>
From voss_runtime/memory/episodic.py:11-67 (EpisodicMemory API confirmed):

```
@dataclass
class EpisodicMemory:
    capacity: int = 20
    summary: str = ""
    turns: list[Turn] = field(default_factory=list)
    ...
    def add(self, content: str, *, role: str = "user") -> None: ...
    def last(self, n: int) -> list[dict]: ...   # returns [{"role": ..., "content": ...}, ...]
    def render(self) -> list[dict]: ...
```

From voss_runtime/__init__.py:21,38 — EpisodicMemory is re-exported from the top-level package: `from voss_runtime import EpisodicMemory` works.

From tests/parser/examples/assistant.voss:1-17 — canonical reference for memory.episodic syntax in .voss:
```
let history: memory.episodic(capacity: 20 turns)
fn chat(userMessage: string) -> string {
    history.add(userMessage, role: "user")
    ctx(budget: 4000 tokens) {
        include history.last(6)
        ...
    }
}
```

From voss/grammar.lark — relevant rules:
- Line 133: `try_stmt: "try" block "catch" [NAME] block` (both `try { } catch { }` and `try { } catch e { }` parse)
- Line 174-175: `use_path` uses `::` separator with ≥2 segments; period-separated is NOT accepted (RESEARCH §Pitfall 1)
- Line 215: COMMENT: /\#[^\n]*/ — # comments accepted

From voss/codegen.py contracts (verified via tests/codegen/test_imports.py:71-90):
- `use voss_runtime::tools::tool`  →  `from voss_runtime.tools import tool`
- `use voss_runtime::tools`         →  `from voss_runtime import tools`

From samples/research.voss line 4: `tools: [webSearch]` already references webSearch as a bare name. The `use voss_runtime::tools::tool` import is cosmetic for LANG-08 coverage; it does NOT introduce a name conflict (the agent body uses `webSearch`, not `tool`).

D-02/D-06 LOCKED forms (verbatim from CONTEXT + RESEARCH disambiguation per Pitfall 1):
- support header: `# support.voss — prompt block, match similar (semantic routing), ctx(budget: N tokens), memory.episodic.`
- research header: `# research.voss — agent, spawn, gather, ctx(budget: N tokens), within/fallback, try/catch, use.`
- classify header: `# classify.voss — probable<T>, confidence gate (@ p >= 0.80), implicit ctx fallback.`
(Exact wording per RESEARCH §Pattern 4 + Code Examples; treat as the canonical strings — the existing `# classify.voss` etc. first lines stay, the header text is the SECOND comment line.)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add header comments to samples/{classify,support,research}.voss (D-14)</name>
  <files>samples/classify.voss, samples/support.voss, samples/research.voss</files>
  <read_first>
    - samples/classify.voss (lines 1-13 — full file; confirm the existing first line is `# classify.voss`)
    - samples/support.voss (lines 1-23 — full file; confirm the existing first line is `# support.voss`)
    - samples/research.voss (lines 1-41 — full file; confirm the existing first line is `# research.voss`)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern 4: Sample header comment (D-14)" — the exact "Demonstrates:" form for classify)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"samples/classify.voss — D-14 only", §"samples/support.voss — D-05 + D-14", §"samples/research.voss — D-06 + D-14")
    - .planning/phases/M3-language-validation/M3-CONTEXT.md (§D-14 — locked decision)
  </read_first>
  <behavior>
    - samples/classify.voss line 1 is unchanged (`# classify.voss`). A new line 2 contains the primitives list. Body (intent, classifyIntent function, result, print) is byte-for-byte unchanged from current.
    - samples/support.voss line 1 is unchanged. A new line 2 contains the primitives list. The remaining lines (prompt block, handleMessage function) are unchanged in this Task; the memory.episodic extension lands in Task 2.
    - samples/research.voss line 1 is unchanged. A new line 2 contains the primitives list. Body unchanged in this Task; the use + try/catch extension lands in Task 3.
    - `voss check samples/classify.voss && voss check samples/support.voss && voss check samples/research.voss` exit 0 after this task.
  </behavior>
  <action>
    1. For samples/classify.voss: insert a new line 2 with text `# classify.voss — probable<T>, confidence gate (@ p >= 0.80), implicit ctx fallback.` (em-dash U+2014). The existing line 1 `# classify.voss` stays. The original line 2 (`fn classifyIntent...`) becomes line 3. Preserve all blank lines and trailing newline.
    2. For samples/support.voss: insert a new line 2 with text `# support.voss — prompt block, match similar (semantic routing), ctx(budget: N tokens), memory.episodic.` (em-dash U+2014).
    3. For samples/research.voss: insert a new line 2 with text `# research.voss — agent, spawn, gather, ctx(budget: N tokens), within/fallback, try/catch, use.` (em-dash U+2014).
    4. Use the em-dash U+2014 in ALL THREE header lines. UTF-8 byte sequence is 0xE2 0x80 0x94. Do NOT use a hyphen-minus, en-dash, or double-hyphen.
    5. After all three edits, run `python3 -m voss.cli check samples/classify.voss`, `... check samples/support.voss`, `... check samples/research.voss` — each must exit 0. The header lines are comments per grammar.lark:215; parser accepts.
    6. Do NOT modify any other line in any sample in this task. Body changes happen in Tasks 2 + 3.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m voss.cli check samples/classify.voss && python3 -m voss.cli check samples/support.voss && python3 -m voss.cli check samples/research.voss && python -c "import re; from pathlib import Path; for f in ('classify','support','research'):
    content = Path(f'samples/{f}.voss').read_text()
    lines = content.splitlines()
    assert lines[0] == f'# {f}.voss', f'line 1 changed in {f}: {lines[0]!r}'
    assert lines[1].startswith(f'# {f}.voss — '), f'header missing in {f}: {lines[1]!r}'
    assert '—' in lines[1], f'em-dash missing in {f}'
print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^# classify.voss — " samples/classify.voss` returns 1.
    - `grep -c "^# support.voss — " samples/support.voss` returns 1.
    - `grep -c "^# research.voss — " samples/research.voss` returns 1.
    - `python -c "import sys; sys.exit(0 if all(b'\xe2\x80\x94' in open(f'samples/{n}.voss','rb').read() for n in ('classify','support','research')) else 1)"` exits 0 (em-dash U+2014 confirmed binary-grep across all three).
    - `python3 -m voss.cli check samples/classify.voss` exits 0.
    - `python3 -m voss.cli check samples/support.voss` exits 0.
    - `python3 -m voss.cli check samples/research.voss` exits 0.
    - `grep -c "^# classify.voss$" samples/classify.voss` returns 1 (the original line 1 is preserved).
  </acceptance_criteria>
  <done>Each sample now opens with a primitive-listing header comment; voss check still passes on all three.</done>
</task>

<task type="auto">
  <name>Task 2: Extend samples/support.voss with memory.episodic + matching examples/raw_python/support.py parity (D-05 + D-12)</name>
  <files>samples/support.voss, examples/raw_python/support.py</files>
  <read_first>
    - samples/support.voss (post-Task-1; full file)
    - examples/raw_python/support.py (lines 1-39 — full file; identifies the insertion points for EpisodicMemory and the render call)
    - tests/parser/examples/assistant.voss (lines 1-17 — the canonical memory.episodic + `.add` + `.last` syntax reference)
    - voss_runtime/memory/episodic.py (lines 1-67 — full module: confirm `EpisodicMemory(capacity: int = 20)`, `.add(content, role="user")`, `.last(n)` returns list[dict], `.render()` returns list[dict])
    - voss_runtime/__init__.py (lines 21, 38 — confirms EpisodicMemory is re-exported)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern: extend samples/support.voss with memory.episodic (D-05)" — verbatim target shape)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"samples/support.voss — D-05 + D-14", §"examples/raw_python/support.py — D-12 parity")
  </read_first>
  <behavior>
    - samples/support.voss has a new module-scope declaration `let tickets: memory.episodic(capacity: 50 turns)` placed after the `prompt SupportAgent { ... }` block and before `fn handleMessage`.
    - samples/support.voss handleMessage body begins with `tickets.add(userMessage, role: "user")` (mirroring assistant.voss line 6).
    - samples/support.voss has `include tickets.last(6)` inside the `case _ => { ctx(budget: 3000 tokens) { ... } }` branch, placed before the existing `yield ask(userMessage)`. Mirrors assistant.voss line 11.
    - examples/raw_python/support.py imports `EpisodicMemory` from voss_runtime (added to the existing `from voss_runtime import ContextScope, SemanticMatcher` line, becoming `from voss_runtime import ContextScope, EpisodicMemory, SemanticMatcher`).
    - examples/raw_python/support.py declares `tickets = EpisodicMemory(capacity=50)` at module scope (after the SUPPORT_SYSTEM_PROMPT constant, before the matcher).
    - examples/raw_python/support.py `handle_message` calls `tickets.add(user_message, role="user")` at function entry (first line after the `def`).
    - examples/raw_python/support.py `handle_message` async-with ContextScope branch adds the rendered last-6 turns to the context before calling `ctx.ask`. Concretely: `for turn in tickets.last(6): await ctx.add(f"{turn['role']}: {turn['content']}")` OR `await ctx.add("\n".join(f"{t['role']}: {t['content']}" for t in tickets.last(6)))` — match the shape codegen actually produces for `include history.last(6)` (verify by reading codegen output once after the .voss edit, before finalizing the .py side).
    - `voss check samples/support.voss` exits 0.
    - The .voss source and the raw_python source produce the same observable side effects on `tickets` under identical input sequences (same number of calls to `tickets.add`, same `tickets.last(6)` shape). The stdout-byte parity assertion lives in M3-05's e2e test extension; this task ensures the contract.
  </behavior>
  <action>
    1. Read the current `samples/support.voss` after Task 1 to find exact line offsets for the prompt block and the fn handleMessage signature.
    2. Add the let declaration: between the closing `}` of `prompt SupportAgent { ... }` and the `fn handleMessage(...) -> string {` line, insert a blank line then `let tickets: memory.episodic(capacity: 50 turns)` then another blank line. The mid-file blank lines match assistant.voss styling at lines 1-5.
    3. Inside `fn handleMessage`, add as the first statement (above `match userMessage { ... }`): `tickets.add(userMessage, role: "user")`. Indent 4 spaces. No trailing blank line before `match`.
    4. Inside the `case _ => { ctx(budget: 3000 tokens) { ... } }` branch (currently containing only `yield ask(userMessage)`), insert `include tickets.last(6)` as the first statement inside the `ctx` block, before `yield ask(userMessage)`. Indent 12 spaces (matching the existing yield line indentation; if existing is 16, match exactly).
    5. After saving samples/support.voss, run `python3 -m voss.cli check samples/support.voss`. Must exit 0. If it errors with `memory.episodic`-related diagnostics, the parser/analyzer does not yet support `(capacity: N turns)` argument — re-read voss/grammar.lark and voss/analyzer.py and verify; if support is missing, STOP this task and escalate (RESEARCH §Summary asserts all constructs already parse, so any failure is a discrepancy).
    6. Run `python3 -m voss.cli compile samples/support.voss --cache-dir /tmp/voss-m304-cache 2>&1 | head -30` and inspect the generated Python to confirm the lowering: `EpisodicMemory(capacity=50)`, `tickets.add(userMessage, role="user")`, `tickets.last(6)` (or `.render()` — codegen choice). This guides the raw_python edit shape so they remain byte-parity.
    7. Edit examples/raw_python/support.py:
       a. Change the import line `from voss_runtime import ContextScope, SemanticMatcher` to `from voss_runtime import ContextScope, EpisodicMemory, SemanticMatcher`. Alphabetical order maintained.
       b. After the `SUPPORT_SYSTEM_PROMPT = (...)` block (current lines 6-8), and before the `matcher = SemanticMatcher(...)` block, insert: `tickets = EpisodicMemory(capacity=50)`. One blank line above and below.
       c. In the `async def handle_message(user_message: str) -> str:` function body (current line 28+), add as the very first statement after the def: `tickets.add(user_message, role="user")`.
       d. Inside the `async with ContextScope(token_budget=3000) as ctx:` branch (current lines 33-35), before `await ctx.add(f"system: {SUPPORT_SYSTEM_PROMPT}")` (or before `return await ctx.ask(...)`), add a line that mirrors how codegen renders `include tickets.last(6)`. Use whichever shape matches: typically `for turn in tickets.last(6): await ctx.add(f"{turn['role']}: {turn['content']}")`. If codegen output (Step 6) uses `tickets.render()` instead, mirror that.
    8. Run `VOSS_HERMETIC=1 python3 examples/raw_python/support.py` — must exit 0. The VOSS_HERMETIC short-circuit is provided by M3-02 Task 1 (Wave 0); this plan is in Wave 1 so the hook is guaranteed present.
    9. Do NOT change any other behavior in either file. Do NOT introduce model: annotations to the .voss source (RESEARCH Q-4 forbids — would force CI to pre-register a model name).
    10. Per RESEARCH §Pitfall 7, the .voss + .py edits MUST land in the same task — do not split into separate tasks.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m voss.cli check samples/support.voss && grep -c "memory.episodic" samples/support.voss && grep -c "tickets.add" samples/support.voss && grep -c "tickets.last" samples/support.voss && grep -c "EpisodicMemory" examples/raw_python/support.py && grep -c "tickets.add(user_message" examples/raw_python/support.py && VOSS_HERMETIC=1 python3 examples/raw_python/support.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "let tickets: memory.episodic(capacity: 50 turns)" samples/support.voss` returns 1.
    - `grep -c "tickets.add(userMessage" samples/support.voss` returns 1.
    - `grep -c "tickets.last(6)" samples/support.voss` returns 1.
    - `grep -c "include tickets.last" samples/support.voss` returns 1.
    - `python3 -m voss.cli check samples/support.voss` exits 0.
    - `grep -c "EpisodicMemory" examples/raw_python/support.py` returns at least 2 (import + construction).
    - `grep -c "tickets = EpisodicMemory(capacity=50)" examples/raw_python/support.py` returns 1.
    - `grep -c "tickets.add(user_message" examples/raw_python/support.py` returns 1.
    - `grep -E "tickets\\.(last|render)" examples/raw_python/support.py | wc -l` returns at least 1.
    - `VOSS_HERMETIC=1 python3 examples/raw_python/support.py` exits 0 with non-empty stdout.
    - `python3 -m voss.cli compile samples/support.voss --cache-dir /tmp/voss-m304-cache 2>&1 | grep -E "EpisodicMemory|tickets" | wc -l` returns at least 1 (confirms codegen path includes the new identifiers).
  </acceptance_criteria>
  <done>support.voss + support.py both exercise memory.episodic with matching shapes; voss check passes; raw script runs hermetically.</done>
</task>

<task type="auto">
  <name>Task 3: Extend samples/research.voss with use + try/catch + matching examples/raw_python/research.py parity (D-06 + D-12)</name>
  <files>samples/research.voss, examples/raw_python/research.py</files>
  <read_first>
    - samples/research.voss (post-Task-1; full file)
    - examples/raw_python/research.py (lines 1-65 — full file; identifies the web_search call site inside Researcher.run)
    - voss/grammar.lark (lines 133, 174-175 — try_stmt + use_path; confirm `::` is the only accepted separator and ≥2 segments required)
    - voss/parser.py (lines 542-557 for try_stmt parsing; lines 711-715 for use_stmt — confirms both `try { } catch { }` and `try { } catch e { }` accepted)
    - tests/codegen/test_imports.py (lines 50-105 — confirms `use voss_runtime::tools::tool` lowers to `from voss_runtime.tools import tool` and `tool` is a real exported symbol)
    - voss_runtime/tools.py (lines 54-58 — confirms `tool` symbol is exported and is the decorator)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern: extend samples/research.voss with try/catch + use (D-06)" — verbatim target shape; §"Pitfall 1" — use voss.tools does NOT parse; must be voss_runtime::tools::tool)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"samples/research.voss — D-06 + D-14", §"examples/raw_python/research.py — D-12 parity")
    - .planning/phases/M3-language-validation/M3-CONTEXT.md (§D-06 — locked decision; the literal "use voss.tools" wording is shorthand, resolved by RESEARCH to voss_runtime::tools::tool)
  </read_first>
  <behavior>
    - samples/research.voss line 3 (after Task 1's two header lines) contains `use voss_runtime::tools::tool`. The `::` separator is mandatory (Pitfall 1). The three-segment path exercises the more interesting parser case (RESEARCH Q-1 recommendation).
    - samples/research.voss `agent Researcher` body wraps the `let results = webSearch(topic, max_results: 5)` + `include results` sequence in `try { ... } catch e { include "web search unavailable" }`. The `try` block lives INSIDE the existing `ctx(budget: 2000 tokens) { ... }`; the `try` does NOT wrap the `yield ask(...)` call.
    - The rest of samples/research.voss (Synthesizer, runResearch, within/fallback, print) is unchanged.
    - examples/raw_python/research.py adds a `try: results = web_search(topic, max_results=5); await ctx.add("\n".join(results))` / `except Exception: await ctx.add("web search unavailable")` block inside Researcher.run (current lines 27-30). The existing `try/except BudgetExceededError` at lines 54-60 is untouched.
    - `voss check samples/research.voss` exits 0.
    - `VOSS_HERMETIC=1 python3 examples/raw_python/research.py` exits 0 with non-empty stdout. The VOSS_HERMETIC short-circuit is provided by M3-02 Task 1 (Wave 0); this plan is in Wave 1 so the hook is guaranteed present.
  </behavior>
  <action>
    1. Read samples/research.voss after Task 1 to find current line offsets.
    2. After the two header comment lines (line 1 + line 2 from Task 1), insert: a blank line then `use voss_runtime::tools::tool` then another blank line, BEFORE the `agent Researcher(...)` declaration. The full new top should read:
       Line 1: `# research.voss`
       Line 2: `# research.voss — agent, spawn, gather, ctx(budget: N tokens), within/fallback, try/catch, use.`
       Line 3: blank
       Line 4: `use voss_runtime::tools::tool`
       Line 5: blank
       Line 6: `agent Researcher(topic: string) -> string {`
    3. Inside `agent Researcher`'s existing `ctx(budget: 2000 tokens) { ... }` block, wrap the existing two-line sequence (the `let results = webSearch(topic, max_results: 5)` declaration immediately followed by `include results`) in a `try { ... } catch e { ... }` block. After the edit, the ctx body contains, in order: a `try {` opening brace at the same indent as the original `let results` line; the two original lines re-indented 4 spaces deeper inside the try-block; a `} catch e {` line at the original indent; a single statement `include "web search unavailable"` indented 4 spaces deeper inside the catch-block; a closing `}` at the original indent; then the original `yield ask("Summarize the key findings on: " + topic)` line unchanged at the original indent. Verify indentation matches the existing ctx block by inspecting how `include results` is indented today and using that as the indent baseline for the try and catch opening braces.
    4. Run `python3 -m voss.cli check samples/research.voss`. Must exit 0. If parser errors on `use voss_runtime::tools::tool`, re-read voss/grammar.lark:174-175 — the `::` separator and 3-segment path are documented as supported. If the error is on `try { ... } catch e { ... }`, re-read parser.py:542-557.
    5. Edit examples/raw_python/research.py:
       a. Inside `class Researcher(VossAgent)` method `run` (currently lines 26-30), replace the two-line sequence `results = web_search(topic, max_results=5)` followed by `await ctx.add("\n".join(results))` with a try/except block. After the edit, the async-with body contains, in order: a `try:` line at the existing 8-space indent; the two original statements re-indented to 12 spaces inside the try; an `except Exception:` line at 8 spaces; a single statement `await ctx.add("web search unavailable")` at 12 spaces inside the except; followed by the existing `return await ctx.ask(...)` line unchanged at 8 spaces.
       b. Do NOT touch the existing try/except BudgetExceededError block at lines 54-60. Do NOT add any new imports — `Exception` is a builtin.
    6. Run `VOSS_HERMETIC=1 python3 examples/raw_python/research.py` — must exit 0. The script prints a synthesizer result (or the fallback join, under StubProvider).
    7. Per RESEARCH §Pitfall 7, the .voss + .py edits MUST land in the same task.
    8. Do NOT add model: annotations to the agent. Do NOT touch Synthesizer. Do NOT touch runResearch. Do NOT remove the bare `webSearch` reference inside `tools: [webSearch]` — the `use voss_runtime::tools::tool` import is cosmetic for LANG-08 surface coverage (per RESEARCH §Open Question Q-1).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -m voss.cli check samples/research.voss && grep -c "use voss_runtime::tools::tool" samples/research.voss && grep -c "try {" samples/research.voss && grep -c "catch e {" samples/research.voss && grep -c "web search unavailable" samples/research.voss && grep -c "web search unavailable" examples/raw_python/research.py && grep -c "except Exception" examples/raw_python/research.py && VOSS_HERMETIC=1 python3 examples/raw_python/research.py | head -5</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^use voss_runtime::tools::tool" samples/research.voss` returns 1.
    - `grep -c "try {" samples/research.voss` returns 1 (only the new try block; do not double-count any existing pattern).
    - `grep -c "catch e {" samples/research.voss` returns 1.
    - `grep -c "\"web search unavailable\"" samples/research.voss` returns 1.
    - `python3 -m voss.cli check samples/research.voss` exits 0.
    - `python3 -m voss.cli compile samples/research.voss --cache-dir /tmp/voss-m304-cache 2>&1 | grep -E "try:|except|from voss_runtime.tools import tool" | wc -l` returns at least 2 (try/except lowering + use lowering).
    - `grep -c "except Exception" examples/raw_python/research.py` returns 1 (the new one only — existing block is `except BudgetExceededError`).
    - `grep -c "web search unavailable" examples/raw_python/research.py` returns 1.
    - `grep -c "except BudgetExceededError" examples/raw_python/research.py` returns 1 (existing block preserved).
    - `VOSS_HERMETIC=1 python3 examples/raw_python/research.py` exits 0 with non-empty stdout.
  </acceptance_criteria>
  <done>research.voss + research.py both exercise try/catch and the use construct with matching shapes; voss check passes; raw script runs hermetically.</done>
</task>

</tasks>

<verification>
- `python3 -m voss.cli check samples/classify.voss && python3 -m voss.cli check samples/support.voss && python3 -m voss.cli check samples/research.voss` exits 0.
- `VOSS_HERMETIC=1 python3 examples/raw_python/classify.py && VOSS_HERMETIC=1 python3 examples/raw_python/support.py && VOSS_HERMETIC=1 python3 examples/raw_python/research.py` each exit 0 with non-empty stdout (classify is unchanged in this plan; the run is a smoke check). VOSS_HERMETIC short-circuit is provided by M3-02 (Wave 0 dependency).
- `pytest tests/integration/test_support_example.py tests/integration/test_research_example.py -q` exits 0 (existing integration tests targeting the raw_python files — they will catch regressions in the .py side).
- `python -c "from voss_runtime import EpisodicMemory; t = EpisodicMemory(capacity=50); t.add('x', role='user'); t.add('y', role='assistant'); assert t.last(6) == [{'role':'user','content':'x'}, {'role':'assistant','content':'y'}]"` exits 0.
</verification>

<success_criteria>
- LANG-07 runnable coverage: memory.episodic exercised by samples/support.voss + examples/raw_python/support.py.
- LANG-08 runnable coverage: try/catch + use exercised by samples/research.voss + examples/raw_python/research.py.
- LANG-01 framing surface (D-14): all three samples open with primitive-listing comments.
- D-12 same-PR parity invariant: every .voss edit lands with its raw_python edit in the same task.
- voss check passes on all three samples; raw scripts run hermetically.
- No model: annotations introduced — auto-stub fallback continues to work without per-sample pre-registration (RESEARCH Q-4).
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| sample .voss → user-facing demo | A bug in samples shows up as a broken first impression for any developer trying voss for the first time. |
| .voss source ↔ raw_python parity | Drift between the two surfaces silently breaks the LANG-03 readability claim + the D-12 parity oracle in e2e tests. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M3-13 | Tampering | samples/research.voss uses `use voss.tools` (CONTEXT shorthand) which does not parse → voss check fails on first try | mitigate | This plan canonicalizes the form as `use voss_runtime::tools::tool` per RESEARCH §Pitfall 1; acceptance criteria greps the exact substring. |
| T-M3-14 | Tampering | .voss source extended but raw_python parity file is not updated → e2e parity assertion (M3-05) breaks silently | mitigate | RESEARCH §Pitfall 7 / D-12: every sample-extension task in this plan bundles the matching examples/raw_python/*.py edit. Acceptance criteria for Tasks 2 + 3 both check the .voss and .py greps in the same task. |
| T-M3-15 | Spoofing | A sample includes `model: "real-cred-only-model"` and the auto-stub fallback (M3-02) breaks because the named model is not registered | mitigate | RESEARCH §Q-4 + this plan's action steps explicitly forbid adding model: annotations to any sample. |
| T-M3-16 | Tampering | An em-dash in the header gets silently replaced by hyphen-minus by an editor → grep tests fail | mitigate | All three header acceptance criteria use binary-grep for `\xe2\x80\x94` (U+2014). |
| T-M3-17 | Repudiation | The `use voss_runtime::tools::tool` import is cosmetic and unused → linters strip it | accept | The import lands in the .voss source which is not subject to Python linters; codegen emits it because LANG-08 requires the surface coverage. Acceptance criterion documents the unused-import status. |
</threat_model>

<output>
After completion, create `.planning/phases/M3-language-validation/M3-04-SUMMARY.md` documenting: (1) before/after line counts for each of the 5 modified files, (2) the exact header text used for each sample (with em-dash byte sequence confirmation), (3) the codegen output snippet showing EpisodicMemory(capacity=50) and the try/except lowering, (4) confirmation that voss check + raw_python scripts both exit 0, (5) the hand-off to M3-05: the e2e tests now need to be repointed to samples/ (helpers.py PARSER_EXAMPLES → SAMPLES_DIR) and extended to assert raw-parity against the updated raw_python files, (6) confirmation that no integration test under tests/integration/ regressed.
</output>
</output>
