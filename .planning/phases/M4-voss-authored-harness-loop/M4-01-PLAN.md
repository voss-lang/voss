---
phase: M4
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - voss/grammar.lark
  - voss/parser.py
  - voss/codegen.py
  - tests/parser/test_use_alias.py
  - tests/codegen/test_await_use_import.py
autonomous: true
requirements:
  - DOG-04
tags:
  - compiler
  - grammar
  - codegen
  - wave-0

must_haves:
  truths:
    - "Source `use foo::bar as baz` parses and produces UseStmt(path=('foo','bar'), alias='baz')."
    - "Source `use foo::bar` (no alias) still parses and produces UseStmt(path=('foo','bar'), alias=None)."
    - "Inside an async fn body, a call to a `use`-imported bare-identifier callee is emitted with `await` prefix in generated Python."
    - "Aliased member-call (`h.run_turn(...)`) auto-await is explicitly NOT in scope; only bare-Identifier callees whose name is in `use_imported_names` get the `await` prefix."
    - "Existing `tests/codegen/test_imports.py::test_use_stmt_alias_is_preserved_when_ast_provides_alias` continues to pass."
  artifacts:
    - path: "voss/grammar.lark"
      provides: "use_stmt grammar rule with optional ('as' IDENT) clause"
      contains: 'use_stmt: "use" use_path ("as" IDENT)?'
    - path: "voss/parser.py"
      provides: "use_stmt transformer that propagates alias child when present"
      contains: "alias = str(children[1])"
    - path: "voss/codegen.py"
      provides: "ExpressionEmitter.use_imported_names frozenset + extended auto-await condition"
      contains: "use_imported_names"
    - path: "tests/parser/test_use_alias.py"
      provides: "Wave-0 parser sentinel: alias roundtrip + regression guard for absent alias"
      contains: "use foo::bar as baz"
    - path: "tests/codegen/test_await_use_import.py"
      provides: "Wave-0 codegen sentinel: `use`-imported callee auto-awaited in async fn body"
      contains: "await bar()"
  key_links:
    - from: "voss/grammar.lark:174 (use_stmt rule)"
      to: "voss/parser.py:714-715 (use_stmt transformer)"
      via: "lark adds second child (Token IDENT) when `as <ident>` is present"
      pattern: '"as" IDENT'
    - from: "voss/parser.py:714-715"
      to: "voss/ast.UseStmt(alias=...)"
      via: "transformer reads children[1] when len(children) > 1"
      pattern: "len(children) > 1"
    - from: "voss/codegen.py:441-446 (_emit_call await condition)"
      to: "ExpressionEmitter.use_imported_names"
      via: "frozenset populated from Program.body UseStmts in ProgramEmitter.emit"
      pattern: "use_imported_names"
---

<objective>
Land the compiler-gap sub-plan required by every downstream M4 wave. Two narrow extensions to the existing compiler stack:

1. **Grammar + parser:** `use_path ("as" IDENT)?` clause threaded through `use_stmt` transformer into the existing `UseStmt.alias` field (codegen already supports it per `tests/codegen/test_imports.py:56-60`).
2. **Codegen:** Extend the existing `generated_fns` auto-await condition in `voss/codegen.py:441-446` to ALSO cover bare-Identifier callees whose name is imported via `use`. This is the prereq for executor.voss (Wave 2) to call back into async Python helpers like `_run_step_loop` without returning unawaited coroutines (Pitfall 2).

Purpose: Wave 0 MUST land before any `.voss` file in `voss/harness/agent/` is authored. Pitfall 2 (M4-RESEARCH §"Common Pitfalls") is the loud failure mode: without 1b, `voss compile voss/harness/agent/executor.voss` succeeds, but at runtime tool dispatch returns `<coroutine object>` strings instead of tool results. Covers D-02 (thin .voss seam — `.voss` calls Python via `use`) and unblocks D-04 (executor.voss can call `_run_step_loop` and have it awaited).

Output:
- `voss/grammar.lark:174-175` — `use_stmt` rule extended with `("as" IDENT)?`.
- `voss/parser.py:714-715` — `use_stmt` transformer propagates alias.
- `voss/codegen.py:~349, ~441-446, ~1196-1197` — `use_imported_names` field on ExpressionEmitter, extended await condition, populated from Program.body in ProgramEmitter.emit.
- `tests/parser/test_use_alias.py` — alias-roundtrip + no-alias regression tests.
- `tests/codegen/test_await_use_import.py` — `await bar()` substring assertion for a `use foo::bar` + `fn caller(){ bar() }` source.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M4-voss-authored-harness-loop/M4-CONTEXT.md
@.planning/phases/M4-voss-authored-harness-loop/M4-RESEARCH.md
@.planning/phases/M4-voss-authored-harness-loop/M4-PATTERNS.md
@.planning/phases/M4-voss-authored-harness-loop/M4-VALIDATION.md
@voss/grammar.lark
@voss/parser.py
@voss/codegen.py
@voss/ast.py
@tests/codegen/test_imports.py

<interfaces>
<!-- Key contracts the executor will touch. Extracted from current tree at commit 99d292e. -->

From voss/ast.py (UseStmt already supports alias — only the parser link is broken):
- `UseStmt(span, path: tuple[str, ...], alias: str | None)` — dataclass field already present.

From voss/grammar.lark (line 174-175, current shape):
```
use_stmt: "use" use_path
use_path: IDENT ("::" IDENT)*
```

From voss/parser.py (line 711-715, current shape):
```python
def use_path(self, meta, children):
    return tuple(str(t) for t in children)

def use_stmt(self, meta, children):
    return UseStmt(span=_span(meta, self.file), path=children[0], alias=None)
```

From voss/codegen.py (line 441-446, current await condition):
```python
if (
    await_context
    and isinstance(call.callee, Identifier)
    and call.callee.name in self.generated_fns
):
    text = f"await {text}"
```

From voss/codegen.py (line 349-ish, ExpressionEmitter dataclass — field placement):
```python
@dataclass
class ExpressionEmitter:
    imports: ImportCollector
    ...
    generated_fns: frozenset[str] = field(default_factory=frozenset)
```

From voss/codegen.py (~line 1175-1200, ProgramEmitter.emit — where ExpressionEmitter is constructed and Program.body UseStmts are walked):
- `ImportCollector.add_use(path, alias=None)` already exists at codegen.py:126-131.
- `from voss.ast import UseStmt` already imported.

From tests/codegen/test_imports.py:56-60 (existing alias-preservation test — must continue to pass):
- Hand-builds `UseStmt(path=("foo","bar"), alias="baz")` directly into AST, runs codegen, asserts `from foo import bar as baz` appears. Wave 0 parser change does NOT touch this — it adds the missing source-level path.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Grammar + parser — `use ... as alias`</name>
  <files>voss/grammar.lark, voss/parser.py, tests/parser/test_use_alias.py</files>
  <read_first>
    - voss/grammar.lark:174-175 (current use_stmt + use_path rules; see also try_stmt:133 for the `[NAME]` optional-token idiom — analogous shape for the new `("as" IDENT)?` clause)
    - voss/parser.py:711-715 (current use_path + use_stmt transformer methods)
    - voss/ast.py — locate `UseStmt` dataclass; confirm `alias: str | None = None` field is already declared
    - tests/codegen/test_imports.py:56-60 (existing alias-preservation test — Wave 0 must not break it)
    - tests/parser/conftest.py + tests/parser/test_use_decorators.py (test style: plain `def`, `from voss.parser import parse`, `program.body[0]` indexing)
    - M4-RESEARCH.md §"Pattern 1a" (lines ~250-280) + §"Code Examples" (lines ~860-895)
    - M4-PATTERNS.md §"voss/grammar.lark (line 174-175) — Wave 0 Pattern 1a" and §"voss/parser.py:714-715 — Wave 0 Pattern 1a"
  </read_first>
  <behavior>
    - Test `test_use_with_alias_parses`: source `"use foo::bar as baz\n"` → `program.body[0]` is `UseStmt` with `path == ("foo", "bar")` and `alias == "baz"`.
    - Test `test_use_without_alias_still_works`: source `"use foo::bar\n"` → `program.body[0]` is `UseStmt` with `alias is None` (regression guard).
    - Test `test_use_with_alias_single_segment_path`: source `"use foo as bar\n"` → `path == ("foo",)`, `alias == "bar"` (covers single-IDENT use_path with alias).
    - Existing `tests/codegen/test_imports.py::test_use_stmt_alias_is_preserved_when_ast_provides_alias` continues to pass (regression guard).
    - Existing `tests/parser/test_use_decorators.py` continues to pass (no-alias cases must not regress).
  </behavior>
  <action>
    Edit `voss/grammar.lark` line 174: change `use_stmt: "use" use_path` to `use_stmt: "use" use_path ("as" IDENT)?`. Leave `use_path` line 175 unchanged. The `"as"` literal becomes an anonymous terminal lark auto-creates; no new terminal declaration in the lines 177-219 terminals block.

    Edit `voss/parser.py` lines 714-715 `use_stmt` method: replace the single-line `return UseStmt(..., alias=None)` with logic that reads `children[1]` when `len(children) > 1`. Exact target body (no fenced code in action — for prose: assign `path = children[0]`; assign `alias = None` initially; if `len(children) > 1 and children[1] is not None` then assign `alias = str(children[1])`; return `UseStmt(span=_span(meta, self.file), path=path, alias=alias)`). No new imports.

    Create `tests/parser/test_use_alias.py` (NEW file). Import `parse` from `voss.parser` and `UseStmt` from `voss.ast`. Define three plain `def` tests per the behavior section above. Use the same source-text-and-assert style as `tests/parser/test_use_decorators.py`. No `pytest-asyncio`; no fixtures beyond what tests/parser/conftest.py provides.

    Decision references: D-02 (thin .voss imports Python symbols via `use`); Pattern 1a (M4-RESEARCH §Pattern 1).
  </action>
  <verify>
    <automated>pytest tests/parser/test_use_alias.py tests/codegen/test_imports.py tests/parser/test_use_decorators.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/parser/test_use_alias.py -q` exits 0 with 3 passed.
    - `pytest tests/codegen/test_imports.py -q` exits 0 (regression — alias-preservation test must still pass).
    - `pytest tests/parser/test_use_decorators.py -q` exits 0 (regression — pre-existing use tests still pass).
    - `grep -n '("as" IDENT)?' voss/grammar.lark` returns line 174 (or whichever line use_stmt ends up on).
    - `grep -n 'alias = str(children\[1\])' voss/parser.py` returns one match in the use_stmt method.
  </acceptance_criteria>
  <done>Grammar accepts `use foo::bar as baz`; parser propagates alias into UseStmt; existing codegen alias-preservation test continues to pass; tests/parser/test_use_alias.py has 3 passing tests.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Codegen — auto-await for `use`-imported callees</name>
  <files>voss/codegen.py, tests/codegen/test_await_use_import.py</files>
  <read_first>
    - voss/codegen.py:126-148 (ImportCollector.add_use + render — already supports aliasing in emitted `from X import Y as Z` lines)
    - voss/codegen.py:~349 (ExpressionEmitter dataclass — where the existing `generated_fns: frozenset[str] = field(default_factory=frozenset)` field lives)
    - voss/codegen.py:417-447 (_emit_call — the await condition at lines 441-446 is the target)
    - voss/codegen.py:1173-1250 (ProgramEmitter.emit — where ExpressionEmitter is instantiated and Program.body is walked for UseStmts; codegen.py:1196-1197 is the documented insertion point)
    - voss/codegen.py:798-811 (_emit_fn — confirms `async def` is the emitted shape for FnDecl, so the await context is naturally async)
    - voss/codegen.py:1192 (`requires_async_main = bool(execs)` — confirms programs with only `use` + `fn` decls compile to a module with no `async def main()` wrapper)
    - voss/ast.py (UseStmt — `path: tuple[str, ...]`, `alias: str | None`; the bound name is `stmt.alias or stmt.path[-1]`)
    - tests/codegen/test_imports.py:1-105 (existing codegen-test style: parse → analyze → generate_python → assert substring on `result.source`)
    - M4-RESEARCH.md §"Pattern 1b" (lines ~282-310) + §"Code Examples" (lines ~899-947)
    - M4-PATTERNS.md §"voss/codegen.py:441-446 — Wave 0 Pattern 1b (auto-await for `use`-imported callees)"
    - M4-RESEARCH.md §"Pitfall 2" (lines ~775-790) — defines the failure mode this task prevents
  </read_first>
  <behavior>
    - Test `test_use_imported_name_is_awaited_in_async_context`: source `"use foo::bar\nfn caller() { bar() }\n"` → generated Python contains the substring `"await bar()"`.
    - Test `test_use_imported_alias_is_awaited`: source `"use foo::bar as baz\nfn caller() { baz() }\n"` → generated Python contains `"await baz()"` (auto-await fires on the bound name, which is the alias).
    - Test `test_use_imported_member_call_not_awaited`: source `"use voss::harness as h\nfn caller() { h.run_turn() }\n"` → generated Python does NOT contain `"await h.run_turn()"` (D-recommendation: aliased member-call auto-await deferred from M4; only bare Identifier callees are auto-awaited).
    - Test `test_local_fn_still_awaited`: regression — `fn other(){ } fn caller(){ other() }` → `"await other()"` in output (existing generated_fns behavior preserved).
    - Existing codegen tests in `tests/codegen/` continue to pass.
  </behavior>
  <action>
    Edit `voss/codegen.py` ExpressionEmitter dataclass (~line 349). Add a new field directly after the existing `generated_fns: frozenset[str] = field(default_factory=frozenset)` line: `use_imported_names: frozenset[str] = field(default_factory=frozenset)` (same default-factory shape).

    Edit `voss/codegen.py` `_emit_call` await condition at lines 441-446. Extend the boolean expression so that the `text = f"await {text}"` line fires when `await_context` is true AND `isinstance(call.callee, Identifier)` AND `(call.callee.name in self.generated_fns OR call.callee.name in self.use_imported_names)`. Keep the existing two conditions intact; ONLY widen the third clause via an OR. Do NOT extend to Member callees; do NOT auto-await non-async-context calls.

    Edit `voss/codegen.py` `ProgramEmitter.emit` (~line 1196-1197) at the construction site of `ExpressionEmitter`. Build the `use_imported_names` frozenset by walking `self.program.body` (or the local variable that holds Program.body in that scope; read the file to find the exact identifier) and collecting `stmt.alias or stmt.path[-1]` for every `stmt` where `isinstance(stmt, UseStmt)`. Pass the frozenset as the new keyword argument `use_imported_names=...` when constructing `ExpressionEmitter(...)`. `UseStmt` is already imported in codegen.py — verify before adding.

    Create `tests/codegen/test_await_use_import.py` (NEW file). Use the source-text-and-assert pattern from `tests/codegen/test_imports.py`: import `parse` from `voss.parser`, `analyze` from `voss.analyzer`, `generate_python` from `voss.codegen`. Call analyze with `emit_indexes=False` (M3 D-03 carry-forward — Pitfall 7). Define the four tests per the behavior section. Assert on substring presence/absence in `result.source`.

    Decision references: D-02 (thin .voss imports Python via `use`); D-04 (executor.voss calls Python `_run_step_loop` and `tool.invoke_dict` — both async); Pattern 1b (M4-RESEARCH §Pattern 1); Pitfall 2 mitigation.

    Per A1 (M4-RESEARCH §Assumptions Log): the codegen extension is ~5-10 LOC of diff. If the ExpressionEmitter constructor turns out to require positional args at the call site, pass `use_imported_names` as the next positional after `generated_fns`. Read the file to confirm the constructor call shape before editing.
  </action>
  <verify>
    <automated>pytest tests/codegen/test_await_use_import.py tests/codegen/test_imports.py tests/codegen/ -q</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/codegen/test_await_use_import.py -q` exits 0 with 4 passed.
    - `pytest tests/codegen/ -q` exits 0 (no regressions in existing codegen tests).
    - `grep -n 'use_imported_names' voss/codegen.py` returns at least 3 matches (field declaration, await condition, ProgramEmitter construction site).
    - `grep -n 'use_imported_names' tests/codegen/test_await_use_import.py` — at minimum the substring `await bar()` and `await baz()` appear as test assertions; the test file does NOT need to reference the field name.
    - Confirm bare-Member auto-await is NOT introduced: `grep -n 'isinstance(call.callee, Member)' voss/codegen.py` returns no NEW matches added by this task in the `_emit_call` await block (existing Member-related code is fine; only the await condition at 441-446 changed).
  </acceptance_criteria>
  <done>Codegen auto-awaits bare-Identifier calls to `use`-imported names in async contexts. Member callees and synchronous contexts are unchanged. tests/codegen/test_await_use_import.py has 4 passing tests; full tests/codegen/ suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Source `.voss` text → compiler | M4 grammar extension widens the parser's accepted surface by 1 token (`as`). All input is repo-controlled `.voss` files; no external untrusted input. |
| AST → generated Python text | Codegen emits `from X import Y as Z` (existing) and `await Y(...)` (new condition). Generated text is later read by `voss.harness.cli` via `importlib.util.spec_from_file_location` — Python's normal import machinery handles trust. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M4-W0-grammar-inj | Tampering | `voss/grammar.lark` use_stmt rule | mitigate | `("as" IDENT)?` only accepts an IDENT (which the lark IDENT terminal already validates as `/[a-zA-Z_][a-zA-Z0-9_]*/`); no string-content injection possible. Codegen emits `from path import name as alias` where `alias` is the validated IDENT — no template injection. |
| T-M4-W0-await-skip | Tampering | `voss/codegen.py:_emit_call` | mitigate | Auto-await widened only for bare-Identifier callees whose name appears in the closed set `use_imported_names`. Member calls are unchanged. Worst case if the codegen patch is incorrect: a downstream `.voss` returns an unawaited coroutine — caught by Wave 3 parity test (Pitfall 2 sentinel). |
| T-M4-W0-test-bypass | Tampering | `tests/parser/test_use_alias.py`, `tests/codegen/test_await_use_import.py` | accept | Tests are in-repo and read-only on the parser/codegen they exercise. No external input. |
</threat_model>

<verification>
After both tasks land:
1. `pytest tests/parser/test_use_alias.py tests/codegen/test_await_use_import.py tests/codegen/test_imports.py tests/parser/test_use_decorators.py -q` exits 0.
2. `pytest tests/parser/ tests/codegen/ -q` exits 0 (no regressions in either suite).
3. The compiled output for a Wave 2 fixture `use voss::harness::agent::_run_step_loop` + `fn foo(){ _run_step_loop([],{},None,None) }` contains `await _run_step_loop(...)` — this is the executor.voss prereq, verified indirectly by `test_use_imported_name_is_awaited_in_async_context`.
4. M4-VALIDATION rows `grammar-use-alias` and `codegen-await-use` flip from ❌ to ✓.
</verification>

<success_criteria>
- Source `use foo::bar as baz` parses and produces `UseStmt(path=("foo","bar"), alias="baz")`.
- Existing AST-direct alias codegen test (`tests/codegen/test_imports.py:56-60`) continues to pass.
- Codegen emits `await NAME(...)` for bare-Identifier calls to `use`-imported NAMEs in async fn bodies.
- Codegen does NOT emit `await` for Member-callees against aliased module imports (M4 defers aliased member auto-await).
- All tests in `tests/parser/` and `tests/codegen/` pass.
- Total compiler diff stays under ~50 LOC (A1 assumption budget).
</success_criteria>

<output>
After completion, create `.planning/phases/M4-voss-authored-harness-loop/M4-01-SUMMARY.md` documenting:
- Exact lines edited (grammar.lark, parser.py, codegen.py with line numbers as they end up after edits).
- The `use_imported_names` frozenset construction site in ProgramEmitter.emit.
- Any deviation from Pattern 1a/1b (if the ExpressionEmitter constructor required positional args, document the call-site shape).
- Total LOC of compiler diff.
- All 7 new tests passing; full tests/parser + tests/codegen suites green.
</output>
