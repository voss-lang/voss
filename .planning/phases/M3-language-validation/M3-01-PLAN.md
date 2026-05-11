---
phase: M3
plan: 01
type: execute
wave: 0
depends_on: [M1, M2]
files_modified:
  - voss/analyzer.py
  - tests/examples/test_check_speed.py
autonomous: true
requirements:
  - LANG-05
  - LANG-09
tags:
  - analyzer
  - static-check
  - performance

must_haves:
  truths:
    - "voss check never instantiates SemanticMatcher or imports sentence_transformers when analyzer is invoked with emit_indexes=False."
    - "Analyzer._visit_match_stmt still walks scrutinee inference + per-case body (static signature validation) when emit_indexes=False; only the embedding computation (index_builder.build_cases) is skipped."
    - "A _match_entries row is recorded with cases=[] for every match-similar block when emit_indexes=False, preserving static visibility."
    - "tests/examples/test_check_speed.py::test_check_does_not_load_hf_encoder asserts sys.modules has no 'sentence_transformers' entry after an in-process analyze() of samples/support.voss with emit_indexes=False."
  artifacts:
    - path: "voss/analyzer.py"
      provides: "_visit_match_stmt with emit_indexes=False early-return guard (per D-03)"
      contains: "if not self.emit_indexes"
    - path: "tests/examples/test_check_speed.py"
      provides: "Wave-0 sentinel: test_check_does_not_load_hf_encoder"
      contains: "sentence_transformers"
  key_links:
    - from: "voss/analyzer.py::Analyzer._visit_match_stmt"
      to: "self.emit_indexes flag (analyzer.py:204-211, 435)"
      via: "early-return before index_builder allocation"
      pattern: "emit_indexes"
    - from: "tests/examples/test_check_speed.py::test_check_does_not_load_hf_encoder"
      to: "voss.analyze + voss.parse + samples/support.voss"
      via: "in-process analyze with emit_indexes=False then sys.modules introspection"
      pattern: "assert \"sentence_transformers\" not in sys.modules"
---

<objective>
Land the D-03 static-only-check invariant: Analyzer._visit_match_stmt early-returns when emit_indexes=False so the SemanticMatcherIndexBuilder (and therefore the HF sentence_transformers encoder) is never instantiated during `voss check`. Add the Wave-0 sentinel test that proves it. This single fix moves `voss check samples/support.voss` from warm ~8.9s to <1.5s and unblocks every downstream M3 test from the cold-HF-load tax.

Purpose: D-03 is the lynchpin of every M3 success criterion that touches speed. Every downstream wave assumes `voss check` is fast. The sentinel test is the regression gate that catches future code paths re-importing the encoder during check. Covers LANG-05 (match similar preserved as a static-only construct) and LANG-09 (the three samples pass voss check fast enough to be useful after edits, per ROADMAP cross-cutting constraint).

Output:
- `voss/analyzer.py:479-501` — `_visit_match_stmt` gated on `emit_indexes`.
- `tests/examples/test_check_speed.py` — new file with `test_check_does_not_load_hf_encoder` only. The per-sample wall-clock speed gate parametrize (D-13) lands in M3-06; this plan creates the file with just the sentinel so M3-02/03/04 can run their suites without the cold HF tax.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M3-language-validation/M3-CONTEXT.md
@.planning/phases/M3-language-validation/M3-RESEARCH.md
@.planning/phases/M3-language-validation/M3-PATTERNS.md
@voss/analyzer.py
@tests/cli/test_check.py

<interfaces>
From voss/analyzer.py:197-228 (Analyzer.__init__ signature — emit_indexes already a constructor kwarg):

```
class Analyzer:
    def __init__(
        self,
        *,
        source_path: str | None = None,
        emit_indexes: bool = True,
        token_estimator: TokenEstimator | None = None,
        index_builder: IndexBuilder | None = None,
    ) -> None:
        ...
        self.emit_indexes = emit_indexes
        self.index_builder: IndexBuilder | None = index_builder
        self._match_entries: list[dict] = []
```

From voss/analyzer.py:479-501 (current _visit_match_stmt — the D-03 fix site):

```
def _visit_match_stmt(self, match: MatchStmt) -> None:
    self._infer_expr(match.scrutinee)
    similar_pairs: list[tuple[str, str]] = []
    for ordinal, case in enumerate(match.cases):
        if isinstance(case.pattern, SimilarPattern):
            label = f"case_{ordinal}"
            similar_pairs.append((case.pattern.text, label))
        for s in case.body:
            self._visit_stmt(s)
    if not similar_pairs:
        return
    if self.index_builder is None:
        self.index_builder = SemanticMatcherIndexBuilder()
    built = self.index_builder.build_cases(similar_pairs)
    threshold = match.threshold if match.threshold is not None else 0.75
    match_id = f"match_{match.span.line_start}_{match.span.col_start}"
    self._match_entries.append(
        {"match_id": match_id, "threshold": threshold, "cases": built}
    )
```

From voss/analyzer.py:748-768 (module-level `analyze` factory — accepts emit_indexes kwarg, forwards to Analyzer):

```
def analyze(
    program,
    *,
    source_path: str | None = None,
    emit_indexes: bool = True,
    token_estimator: TokenEstimator | None = None,
    index_builder: IndexBuilder | None = None,
) -> AnalyzeResult:
    ...
```

From voss/__init__.py — `analyze` and `parse` are re-exported (verify with `python -c "from voss import analyze, parse; print(analyze, parse)"`).

From tests/cli/test_check.py:70-80 (sentinel-style invariant pattern this test follows):

```
def test_check_does_not_emit_indexes_or_cache_files():
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        path = _write("clean.voss", _CLEAN_SOURCE)
        result = runner.invoke(main, ["check", "--cache-dir", ".voss-cache", str(path)])
        assert result.exit_code == 0, result.output
        fs_path = Path(fs)
        assert not (fs_path / ".voss-cache").exists()
        assert not list(fs_path.glob("**/*.idx"))
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Gate _visit_match_stmt on emit_indexes flag (D-03 static-only check)</name>
  <files>voss/analyzer.py</files>
  <read_first>
    - voss/analyzer.py (lines 166-228: _default_local_model + SemanticMatcherIndexBuilder + Analyzer.__init__ + emit_indexes flag wiring)
    - voss/analyzer.py (lines 435-501: _emit_program_index manifest emission gate + the _visit_match_stmt fix site)
    - voss/analyzer.py (lines 641-719: _emit_program_index — confirm emit_indexes is the ONLY gate that drives manifest writes; the fix must mirror that gating)
    - voss_runtime/semantic.py (lines 1-94: confirm SemanticMatcher.__init__ at 24-43 + _ensure_encoder at 45-50 is where HF loads; the fix avoids triggering this code path)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern 2: Static-only check (D-03)" — verbatim adaptation source; §"Pitfall 2" — sentinel rationale; §"Pitfall 6" — confirms importing voss_runtime.semantic does NOT load the model, only SemanticMatcher() construction does)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"voss/analyzer.py (modify _visit_match_stmt) — D-03 static-only check" — exact adaptation notes)
    - .planning/phases/M3-language-validation/M3-CONTEXT.md (§D-03 — locked decision text)
  </read_first>
  <behavior>
    - Calling `analyze(program, emit_indexes=False)` on a program containing `match similar(...)` cases populates `result.match_entries` with one row per match block; each row has `match_id`, `threshold`, and `cases == []`.
    - Calling `analyze(program, emit_indexes=False)` does NOT instantiate `SemanticMatcherIndexBuilder` (existing behavior at line 642 is also gated; this task adds the second gate at line 490).
    - Calling `analyze(program, emit_indexes=False)` does NOT import `sentence_transformers` (verified by the M3-01 Task 2 sentinel; the analyzer.py change is what makes that assertion green).
    - Calling `analyze(program, emit_indexes=True)` (the existing voss compile / voss run path) is BYTE-FOR-BYTE unchanged: same _match_entries shape with real `cases` from `build_cases`. Existing analyzer tests stay green.
    - Scrutinee inference (`self._infer_expr(match.scrutinee)`) and per-case body walk (`self._visit_stmt(s)`) still run for both branches — static signature validation is preserved per D-03.
  </behavior>
  <action>
    1. In voss/analyzer.py inside `_visit_match_stmt` (currently at lines 479-501), after the existing loop that builds `similar_pairs` and walks `case.body` (lines 480-487) but BEFORE the `if not similar_pairs: return` short-circuit, insert the D-03 guard. Order: scrutinee inference (existing line 480) → per-case loop (existing 481-487) → empty short-circuit (existing 488-489) → NEW emit_indexes guard → existing builder allocation + build_cases (490-492) → existing _match_entries.append (494-498).
    2. The new emit_indexes guard checks `if not self.emit_indexes:`. When true: compute `match_id = f"match_{match.span.line_start}_{match.span.col_start}"` and `threshold = match.threshold if match.threshold is not None else 0.75` (mirror the same expressions already used at lines 494-497). Append `{"match_id": match_id, "threshold": threshold, "cases": []}` to `self._match_entries`. Then `return`.
    3. Do NOT modify `_emit_program_index` (analyzer.py:641-719) — its gate at line 435 (`if self.emit_indexes and self._match_entries`) already prevents manifest writes when emit_indexes is False. The fix is solely in `_visit_match_stmt`.
    4. Do NOT modify `SemanticMatcherIndexBuilder` (analyzer.py:172-184). Do NOT modify the module-level `analyze` factory (analyzer.py:748+) — its signature and forwarding stays untouched.
    5. Do NOT change `_default_local_model` (analyzer.py:166-169). The import `from voss_runtime.semantic import DEFAULT_LOCAL_MODEL` is cheap and does not load the encoder (verified per Pitfall 6).
    6. Add a one-line inline comment above the new guard: `# D-03: static-only check — skip embedding build, keep static signature validation.`
    7. Run `pytest tests/analyzer/ -q` immediately after the edit to confirm no analyzer-test regression. If `tests/analyzer/test_examples.py` previously passed with emit_indexes=False (it does, per current behavior because tests/analyzer/test_examples.py uses FakeIndexBuilder which makes the eager path harmless), it must still pass. If `tests/analyzer/test_examples.py` previously passed with emit_indexes=True somewhere, that test is unchanged by this patch.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/analyzer/ -q && python -c "from voss import parse, analyze; from pathlib import Path; src = Path('samples/support.voss').read_text(); p = parse(src, file='samples/support.voss'); r = analyze(p, source_path='samples/support.voss', emit_indexes=False); assert r.ok, r.diagnostics; assert len(r.match_entries) >= 1; assert all(e['cases'] == [] for e in r.match_entries), r.match_entries; import sys; assert 'sentence_transformers' not in sys.modules, sorted(k for k in sys.modules if 'transform' in k.lower())"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "if not self.emit_indexes" voss/analyzer.py` returns at least 1 (the new guard).
    - `grep -n "D-03" voss/analyzer.py` returns at least 1 line (the inline comment marker).
    - `pytest tests/analyzer/ -q` exits 0 with no new failures vs. baseline.
    - `time python3 -m voss.cli check samples/support.voss` warm wall-clock < 2s (was ~8.9s). Run the command twice; take the second time.
    - `python -c "from voss import parse, analyze; from pathlib import Path; p = parse(Path('samples/support.voss').read_text(), file='samples/support.voss'); r = analyze(p, source_path='samples/support.voss', emit_indexes=False); assert r.ok and len(r.match_entries) >= 1 and all(e['cases'] == [] for e in r.match_entries)"` exits 0.
    - `python -c "from voss import parse, analyze; from pathlib import Path; p = parse(Path('samples/support.voss').read_text(), file='samples/support.voss'); analyze(p, source_path='samples/support.voss', emit_indexes=False); import sys; assert 'sentence_transformers' not in sys.modules"` exits 0.
    - `python -c "from voss import parse, analyze; from pathlib import Path; p = parse(Path('samples/support.voss').read_text(), file='samples/support.voss'); r = analyze(p, source_path='samples/support.voss', emit_indexes=True); assert r.ok and len(r.match_entries) >= 1 and any(e['cases'] for e in r.match_entries)"` exits 0 (the live path still computes real cases — note: this exits 0 only when HF model is locally cached; if it errors due to download, that is acceptable and demonstrates D-03's value).
  </acceptance_criteria>
  <done>Analyzer respects emit_indexes for the embedding-computation path; static signature validation preserved; existing analyzer tests pass; warm `voss check samples/support.voss` is under 2s.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create tests/examples/test_check_speed.py with the D-03 HF-encoder sentinel</name>
  <files>tests/examples/test_check_speed.py</files>
  <read_first>
    - tests/cli/test_check.py (lines 1-97 — CliRunner invariant pattern; reuse the assertion shape from test_check_does_not_emit_indexes_or_cache_files at 70-80)
    - tests/examples/helpers.py (lines 1-69 — confirm run_voss helper exists; this task does NOT call it yet, the per-sample speed gate in M3-06 uses it)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern: tests/examples/test_check_speed.py (D-13, NEW)" — verbatim adaptation source for `test_check_does_not_load_hf_encoder`; only this single test in this plan, NOT the parametrized wall-clock gate)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/examples/test_check_speed.py (NEW) — D-03 sentinel + D-13 wall-clock" — adaptation notes; only the sentinel portion in this plan)
    - voss/__init__.py — confirm `parse` and `analyze` are exported; if not, import from `voss.parser` and `voss.analyzer` instead
    - samples/support.voss (lines 1-23 — confirms a match-similar block exists so the sentinel exercises the D-03 path)
  </read_first>
  <behavior>
    - test_check_does_not_load_hf_encoder: in-process. Reads samples/support.voss, calls parse(src), calls analyze(program, source_path=..., emit_indexes=False). Asserts result.ok is True. Asserts `"sentence_transformers" not in sys.modules`. Asserts no key in sys.modules contains the substring "sentence_transformers" (case-sensitive). On failure prints the offending module names.
    - Test MUST run in the same Python process; pytest's collection itself MUST NOT import sentence_transformers (so the test does not run after some other test in the same session has already imported it — solution: name it `test_check_does_not_load_hf_encoder` and rely on pytest's default file-alphabetical ordering placing this file near the top; additionally, the test imports voss/voss_runtime fresh).
    - File contains ONLY this single test plus a module docstring and the `CHECK_CEILING_SECONDS = 2.0` constant (constant is placed here in preparation for M3-06 even though no test references it in M3-01).
  </behavior>
  <action>
    1. Create tests/examples/test_check_speed.py. Top-level docstring: `"""D-03 + D-13 check-time invariants. Sentinel here; per-sample wall-clock gate lands in M3-06."""`.
    2. Imports: `from __future__ import annotations`, `from pathlib import Path`, `import sys`.
    3. Constant: `CHECK_CEILING_SECONDS = 2.0` (used by M3-06; defined here for shared visibility).
    4. Helper constant: `REPO_ROOT = Path(__file__).resolve().parents[2]` mirroring tests/examples/helpers.py:22.
    5. Define `test_check_does_not_load_hf_encoder()` with no fixtures. Body:
       - `from voss import parse, analyze` (fall back to `from voss.parser import parse; from voss.analyzer import analyze` if the top-level re-export is absent; verify by reading voss/__init__.py during the read_first pass).
       - `src = (REPO_ROOT / "samples" / "support.voss").read_text()`.
       - `program = parse(src, file="samples/support.voss")`.
       - `result = analyze(program, source_path="samples/support.voss", emit_indexes=False)`.
       - `assert result.ok, [d.message for d in result.diagnostics]`.
       - `offenders = sorted(k for k in sys.modules if "sentence_transformers" in k)` — case-sensitive substring match.
       - `assert offenders == [], f"D-03 violated: encoder modules loaded: {offenders}"`.
    6. Do NOT add the parametrized wall-clock gate (`test_check_speed_under_ceiling`) in this plan. M3-06 extends this file.
    7. Do NOT add `pytest` import unless the test uses it; this test does not need it.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/examples/test_check_speed.py::test_check_does_not_load_hf_encoder -v</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/examples/test_check_speed.py` exits 0.
    - `grep -c "test_check_does_not_load_hf_encoder" tests/examples/test_check_speed.py` returns at least 1.
    - `grep -c "sentence_transformers" tests/examples/test_check_speed.py` returns at least 2 (substring check + assertion message).
    - `grep -c "CHECK_CEILING_SECONDS = 2.0" tests/examples/test_check_speed.py` returns 1 (carry-forward constant for M3-06).
    - `grep -c "test_check_speed_under_ceiling" tests/examples/test_check_speed.py` returns 0 (parametrized gate is M3-06's responsibility).
    - `pytest tests/examples/test_check_speed.py::test_check_does_not_load_hf_encoder -v` reports 1 passed.
    - When invoked in isolation (`pytest tests/examples/test_check_speed.py -v -p no:cacheprovider`), the test still passes — confirms it doesn't depend on prior-test side effects.
  </acceptance_criteria>
  <done>Sentinel test exists; passes; M3-06 has a file to extend; future code paths re-importing sentence_transformers during check will fail this test.</done>
</task>

</tasks>

<verification>
- `pytest tests/analyzer/ tests/examples/test_check_speed.py::test_check_does_not_load_hf_encoder -q` exits 0.
- `time python3 -m voss.cli check samples/support.voss` reports warm wall-clock under 2s.
- `pytest tests/cli/test_check.py -q` exits 0 (existing CLI check tests stay green — they were a regression risk because they share the analyzer with the new code path).
- `pytest tests/codegen/ -q` exits 0 (codegen path uses emit_indexes=True and is unchanged; this is a smoke check that the compile/run path is intact).
</verification>

<success_criteria>
- D-03 invariant: voss check never instantiates SemanticMatcher / never imports sentence_transformers.
- LANG-05 covered: match similar(...) still validates statically — scrutinee inference + case-body walk run for every emit_indexes value.
- LANG-09 unblocked: `voss check samples/support.voss` is fast enough for the M3-06 speed gate to land cleanly.
- No regression to compile/run path (`emit_indexes=True` behavior unchanged).
- Wave-0 sentinel file (tests/examples/test_check_speed.py) exists for M3-06 to extend.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| analyzer → embedding builder | A `match similar(...)` source span crosses from static AST into a code path that previously eagerly loaded a HF model. After D-03 the boundary closes at check time. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M3-01 | Denial of Service | Analyzer._visit_match_stmt eagerly loads HF sentence_transformers during `voss check` → ~13s cold load + network if HF cache missing | mitigate | Gate `build_cases` on `self.emit_indexes`; record `cases=[]` row so static visibility preserved. |
| T-M3-02 | Tampering | A future contributor re-introduces an eager encoder load via a different code path (e.g. a transitive `from voss_runtime.semantic import SemanticMatcher` at module scope) | mitigate | Sentinel test `test_check_does_not_load_hf_encoder` asserts `sentence_transformers` absent from `sys.modules` after in-process analyze — catches regressions in any code path. |
| T-M3-03 | Information Disclosure | An eager HF model load at check time could in principle make outbound HTTP calls to huggingface.co (Hub download) on CI runners with no cache | mitigate | Same fix as T-M3-01; net effect: zero network calls at check time. |
| T-M3-04 | Repudiation | Static check silently drops cases analysis, so a malformed `match similar(...)` syntax escapes detection | accept | Scrutinee inference + per-case body walk still run for emit_indexes=False (the D-03 guard is placed AFTER those steps). Diagnostics for malformed match cases continue to surface. No silent degradation. |
</threat_model>

<output>
After completion, create `.planning/phases/M3-language-validation/M3-01-SUMMARY.md` documenting: (1) the exact line range of the analyzer.py change, (2) the new sentinel test signature and assertion shape, (3) measured before/after `voss check` warm wall-clock for samples/support.voss, (4) confirmation that emit_indexes=True path is unchanged (point to `analyze` smoke run in verify), (5) the M3-06 hand-off: which file gets the parametrized wall-clock gate, which constant is already in place.
</output>
