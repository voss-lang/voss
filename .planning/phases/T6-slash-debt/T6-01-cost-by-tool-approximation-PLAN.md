---
phase: T6-slash-debt
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/cli.py
  - tests/harness/test_repl_slash.py
autonomous: true
requirements: [SLASH-07]
must_haves:
  truths:
    - "Running /cost --by-tool prints a per-tool USD breakdown derived from existing RunRecord iteration data"
    - "Every /cost --by-tool output carries an unmissable ~approx caveat and never mentions T4"
    - "/cost --by-model continues to work unchanged"
    - "/cost --by-tool with no attributable tool-call data prints an informational line, not an error"
    - "There is at least one integration test exercising the /cost --by-tool happy path (ROADMAP T6 SC#1)"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "Real derived --by-tool even-split aggregation replacing the lands-with-T4 stub"
      contains: "by-tool"
    - path: "tests/harness/test_repl_slash.py"
      provides: "Rewritten --by-tool test asserting the approximation (replaces test_cost_by_tool_is_honest_stub)"
      contains: "~approx"
  key_links:
    - from: "voss/harness/cli.py _cost --by-tool branch"
      to: "ctx.record.runs[*]['iterations'][*]['tool_results']"
      via: "even-split cost_usd / len(tool_results) aggregated per tool name"
      pattern: "iterations"
---

<objective>
Replace the `/cost --by-tool` honest-stub branch (cli.py:585-591, "per-tool cost
tracking lands with T4") with a real, explicitly-labeled derived approximation
that even-splits each iteration's `cost_usd` across that iteration's
`tool_results` and aggregates per tool name (D-01). Closes SLASH-07's
`--by-tool` half. Rewrite the now-obsolete `test_cost_by_tool_is_honest_stub`
test (D-01 deliberately changes its asserted behavior — this is a required,
expected change, NOT a regression).

Purpose: PRD §2.4 promised `/cost --by-tool`; the current stub is a documented
v0.1 contract bug. The provider bills per-LLM-turn, not per-tool-call
(`RunRecorder.cost_usd` is per-iteration), so true per-tool cost does not exist
and cannot without a fabricated model. T6 ships the honest even-split floor with
a loud `~approx` caveat and ZERO new persistence (D-08).
Output: Modified `_cost` `--by-tool` branch in cli.py; rewritten test in
test_repl_slash.py.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/T6-slash-debt/T6-CONTEXT.md
@.planning/phases/T6-slash-debt/T6-PATTERNS.md

<!-- ENV NOTE (W4): All verify/acceptance commands assume the project venv is
     active (execute-plan activates it); otherwise prefix `.venv/bin/`. -->

<interfaces>
<!-- Data shapes the executor needs. Extracted from codebase. No exploration required. -->

Slash handler signature (voss/harness/slash.py:8):
SlashHandler = Callable[[Any, list[str], str], None]   # (ctx, args, line) -> None
# stdout via click.echo(...); errors via click.echo(..., err=True); handlers never raise.

The --by-model analog to clone, _cost in voss/harness/cli.py:592-610:
  flags = {a.lstrip("-") for a in args}; if "by-model" in flags:
  build dict[str, float] over ctx.record.runs (run-level run["cost_usd"])
  → empty guard returns `f"session cost: ${ctx.total_cost:.4f} (no runs yet)"`
  → width = max(len(m) for m in by_model)
  → click.echo(f"session cost: ${ctx.total_cost:.4f}")
  → sorted-by-value-desc: click.echo(f"  {m:<{width}}  ${c:.4f}")
  → return

The stub being DELETED, voss/harness/cli.py:585-591:
  if "by-tool" in flags:
      click.echo("  /cost --by-tool: per-tool cost tracking lands with T4 ...")
      return

Per-iteration data --by-tool must descend into (zero new persistence, D-08):
  ctx.record.runs is list[dict] (serialized RunRecord, session.py:113).
  RunRecord.iterations (recorder.py / session.py:113-129) serializes as
    run["iterations"] (list[dict]).
  IterationRecord (session.py:97-103): cost_usd: float, tool_results: list[dict].
  tool_results element shape (agent.py:748-755): {"name": ..., "args": {...}, "result": "..."}
  → tool name key is tr.get("name", "?").

Test fixture to extend, tests/harness/test_repl_slash.py:133-169:
  fake_ctx is a SimpleNamespace; fake_ctx.record.runs is list[dict] with only
  cost_usd + changed today (lines 156-159):
    runs=[{"cost_usd": 0.008, "changed": []},
          {"cost_usd": 0.012, "changed": ["voss/harness/cli.py"]}]
  The existing --by-model test asserts "$0.0200" (0.012 + 0.008) — fixture
  changes must stay ADDITIVE so that assertion stays green.

Obsoleted test, tests/harness/test_repl_slash.py:225-231:
  def test_cost_by_tool_is_honest_stub(self, fake_ctx, capsys):
      ... reg.lookup("/cost").handler(fake_ctx, ["--by-tool"], "/cost --by-tool")
      out = capsys.readouterr().out
      assert "T4" in out   # <-- the tripwire D-01 deliberately deletes
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Replace the --by-tool stub with the D-01 even-split derived approximation</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py:582-620 (the `_cost` handler — flag-parse + the `--by-tool` stub at 585-591 being deleted + the `--by-model` analog at 592-610 to clone)
    - T6-PATTERNS.md "Edit Site 1" (the derivation spec + the exact stub text being deleted + the `--by-model` skeleton to mirror + the IterationRecord shape facts)
    - voss/harness/recorder.py:28-35,116-146,191-215 (`RunRecorder`, per-iteration `cost_usd`, the `tool_results` list — the EXISTING data D-01 derives from; confirm the serialized `run["iterations"][*]` shape)
    - voss/harness/slash.py:8 (handler signature + I/O convention — never raise, click.echo, no err=True for the no-data path)
  </read_first>
  <behavior>
    - Given an iteration with cost_usd=0.012 and two tool_results (names fs_read, fs_grep), each tool is attributed 0.006 (even split: cost_usd / len(tool_results)).
    - Given an iteration with cost_usd<=0 OR empty/missing tool_results, that iteration contributes nothing (skipped per CONTEXT line 64).
    - Given no attributable data anywhere, an informational line is printed (mirroring --by-model's "(no runs yet)") and the handler returns — NOT err=True, NOT a raise.
    - Output contains a one-time legend line with the substring "~approx (turn cost ÷ N tool calls)".
    - Output never contains the substring "T4".
    - The same tool name across multiple iterations accumulates (aggregate per tool name).
    - /cost --by-model and the default /cost path are unchanged.
  </behavior>
  <action>
    In `_cost` (voss/harness/cli.py), delete the `if "by-tool" in flags:` stub
    body at lines 585-591 (the "per-tool cost tracking lands with T4 (prompt
    caching)" message). Replace it with a derived even-split aggregation that
    mirrors the `--by-model` skeleton structure (build a `dict[str, float]`,
    empty guard, `width = max(...)`, sorted-by-value-desc width-aligned
    `click.echo`). Derivation per D-01: for each `run` in `ctx.record.runs`, for
    each `it` in `run.get("iterations", [])`, compute
    `cost = float(it.get("cost_usd", 0.0))` and `trs = it.get("tool_results") or []`;
    if `cost <= 0` or `not trs`, skip that iteration; otherwise
    `share = cost / len(trs)` and for each `tr` in `trs` add `share` to
    `by_tool[tr.get("name", "?")]`. Empty/no-data path: print an informational
    line (e.g. `no per-tool cost attributable yet`) and `return` — NOT
    `err=True` (the no-data path is informational, mirroring `--by-model`'s
    "(no runs yet)"). Emit the loud caveat as a ONE-TIME header/legend line
    before the rows, containing the exact phrase fragment
    `~approx (turn cost ÷ N tool calls)` (CONTEXT line 65: header-once + clean
    rows, NOT a per-row suffix). The output must NOT contain the substring `T4`
    (that string is the obsoleted tripwire). No fenced code in this action —
    replicate the `--by-model` analog's shape. Closes SLASH-07 `--by-tool`. Zero
    new persistence (D-08) — read-only over already-serialized
    RunRecord/IterationRecord dicts; do not add a field, schema, or store.

    D-06 RECONCILIATION NOTE (no code, no file edit — record in SUMMARY): T6 owns
    BOTH `/cost --by-model` and `/cost --by-tool`. T4-CONTEXT D-09's placeholder
    edit (changing the stub message to reference "T6") is now obsolete/no-op
    because T6 ships the real approximation as the FINAL behavior. Whoever later
    executes T4 MUST NOT re-introduce a `--by-tool` stub. Do NOT edit any T4 file
    from this plan.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "import ast; ast.parse(open('voss/harness/cli.py').read())" && ! grep -q "lands with T4" voss/harness/cli.py && grep -q "~approx (turn cost" voss/harness/cli.py</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "import ast; ast.parse(open('voss/harness/cli.py').read())"` exits 0 (file parses).
    - `grep -n "lands with T4" voss/harness/cli.py` returns NO match (the stub message is gone — the obsoleted `--by-tool` stub line no longer references "T4").
    - `grep -n "by-tool" voss/harness/cli.py` shows the `--by-tool` branch still present (the flag is still handled, not removed).
    - `grep -n "~approx (turn cost" voss/harness/cli.py` shows the loud one-time caveat phrase exists in the `--by-tool` branch.
    - `grep -n "iterations" voss/harness/cli.py` shows the `--by-tool` branch descends into per-iteration data (proves it does not reuse run-level `cost_usd` like `--by-model`).
    - `grep -nE "len\(.*tool_results.*\)|len\(trs\)" voss/harness/cli.py` shows the even-split denominator is the tool-call count (`cost_usd / len(tool_results)`), not byte/token weighting.
    - No T4 file is modified: `git status --porcelain | grep -E "phases/T4-|T4-" && exit 1 || true`.
  </acceptance_criteria>
  <done>The `--by-tool` stub branch is replaced by the derived even-split aggregation with a one-time `~approx (turn cost ÷ N tool calls)` legend; no "T4" string remains in the branch; cli.py parses; `--by-model` + default path untouched; no T4 file touched.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite test_cost_by_tool_is_honest_stub to assert the real approximation (D-01 tripwire — expected, required change)</name>
  <files>tests/harness/test_repl_slash.py</files>
  <read_first>
    - tests/harness/test_repl_slash.py:128-258 (the entire `TestT6Behaviors` class — the `fake_ctx` fixture at 133-169, the `--by-model` test at 216-223 as the closest analog, and the stub test at 225-231 being rewritten)
    - T6-PATTERNS.md "Edit Site 4" (the exact extended `runs` fixture shape with an `iterations` key + the rewrite spec: assert tool names + `~approx` + `"T4" not in out`)
  </read_first>
  <behavior>
    - The `fake_ctx.record.runs` second entry gains an `iterations` list with one iteration: cost_usd 0.012, tool_results [{"name":"fs_read",...},{"name":"fs_grep",...}].
    - Dispatching /cost --by-tool prints both tool names (fs_read, fs_grep).
    - Output contains the `~approx` legend substring.
    - Output does NOT contain "T4".
    - The existing test_cost_by_model_groups_by_session_model still passes (fixture extension is additive — its "$0.0200" assertion stays green).
  </behavior>
  <action>
    This task EXPLICITLY REPLACES the obsoleted `test_cost_by_tool_is_honest_stub`
    (tests/harness/test_repl_slash.py:225-231). D-01 deliberately changes
    `--by-tool` from a stub to a real approximation, so deleting that test's
    `assert "T4" in out` tripwire is an EXPECTED, REQUIRED part of T6 — flag it
    as such in the SUMMARY, NOT as a regression. In the `fake_ctx` fixture,
    extend `record.runs` (lines 156-159): KEEP the existing two run dicts and
    their `cost_usd`/`changed` keys (so `test_cost_by_model_groups_by_session_model`'s
    `$0.0200` assertion stays green — the change must be ADDITIVE), and add an
    `iterations` key to the SECOND run dict containing one iteration dict with
    `cost_usd: 0.012` and a `tool_results` list of two dicts named `fs_read` and
    `fs_grep` (each with `args` and `result` keys to match the real
    agent.py:748-755 shape). Rewrite the method currently named
    `test_cost_by_tool_is_honest_stub`: keep the dispatch shape
    (`reg.lookup("/cost").handler(fake_ctx, ["--by-tool"], "/cost --by-tool")`,
    `out = capsys.readouterr().out`), DELETE the `assert "T4" in out` assertion,
    and replace with assertions that both tool names appear in `out`, that the
    `~approx` legend substring appears in `out`, and that `"T4" not in out`.
    Rename the method to reflect the new behavior (e.g.
    `test_cost_by_tool_derived_approximation`). This is the SLASH-07 SC#1
    integration test for the `--by-tool` happy path. No fenced code in this
    action — copy the `--by-model` test's structure from the same class.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_repl_slash.py -q --tb=short; echo "exit:$?"</automated>
  </verify>
  <acceptance_criteria>
    - `python -m pytest tests/harness/test_repl_slash.py -q` exits 0.
    - `grep -n 'assert "T4" in out' tests/harness/test_repl_slash.py` returns NO match (the obsoleted tripwire assertion is deleted — expected, required).
    - `grep -n "test_cost_by_tool_is_honest_stub" tests/harness/test_repl_slash.py` returns NO match (method renamed).
    - `grep -n "~approx" tests/harness/test_repl_slash.py` shows the new test asserts the legend substring.
    - `grep -nE "fs_read|fs_grep" tests/harness/test_repl_slash.py` shows the new test asserts both tool names appear.
    - `python -m pytest tests/harness/test_repl_slash.py -q -k "by_model"` exits 0 (the additive fixture change did not break the unchanged --by-model test).
  </acceptance_criteria>
  <done>The obsoleted `test_cost_by_tool_is_honest_stub` is renamed and rewritten to assert the approximation output (both tool names + `~approx` + no "T4"); the full test_repl_slash.py suite passes including the unchanged --by-model test; the tripwire deletion is documented as expected in the SUMMARY.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| REPL user → `/cost` handler | User-typed `--by-tool` flag; no further untrusted input crosses into this branch (flag is set-membership tested, not interpolated) |
| Serialized session data → `_cost` aggregation | `ctx.record.runs` dicts are read-only; no eval, no shell, no subprocess, no file write, no network |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T6-01 | Tampering | `--by-tool` aggregation over `run["iterations"]` | accept | Read-only `dict.get` traversal with `float()` coercion + default `0.0`; malformed/missing keys degrade to the empty-data info line and `return`, never raise. Local REPL, no network, ZERO new persistence written (D-08). No ASVS L1 control applies — no trust boundary is crossed with untrusted serialized input beyond the user's own session record. |
| T-T6-02 | Information Disclosure | `~approx` cost figures | accept | Figures are derived from data already in the user's own session record; no new data surfaced, no secret exposure (session payloads already exclude keys per CTRL-09). The loud one-time `~approx (turn cost ÷ N tool calls)` legend prevents the user mis-trusting the precision (truthfulness control). |
| T-T6-SC | Tampering | npm/pip/cargo installs | mitigate | No package installs in this plan (harden+test, zero new deps per D-08). N/A — no slopcheck checkpoint required; no `[ASSUMED]`/`[SUS]` packages introduced. |

No `high`-severity threat. ASVS L1: no input-validation, auth, or injection sink is added — `/cost --by-tool` is a pure read-only aggregation over the in-process `ReplContext`.
</threat_model>

<verification>
- `python -m pytest tests/harness/test_repl_slash.py -q` exits 0.
- `grep -n "lands with T4" voss/harness/cli.py` returns NO match.
- `grep -n "~approx (turn cost" voss/harness/cli.py` returns a match in the `--by-tool` branch.
- `grep -n 'assert "T4" in out' tests/harness/test_repl_slash.py` returns NO match.
- No file under `.planning/phases/T4-*` and no T4-owned source file is modified by this plan.
</verification>

<success_criteria>
- SLASH-07 `--by-tool` ships a derived even-split approximation (`cost_usd / len(tool_results)`, per-tool aggregation, zero-cost/empty-tool iterations skipped) with a loud one-time `~approx (turn cost ÷ N tool calls)` legend and zero new persistence.
- The `--by-tool` SC#1 integration test passes and asserts the approximation (not the stub); the obsoleted tripwire is deleted as an expected, required change.
- D-06 reconciliation note recorded in the SUMMARY; no T4 file edited.
</success_criteria>

<output>
Create `.planning/phases/T6-slash-debt/T6-01-SUMMARY.md` when done. The SUMMARY
MUST include: (1) the D-06 reconciliation note verbatim (T6 owns `--by-tool`;
T4's D-09 placeholder edit is obsolete; future T4 executor must NOT re-stub
`--by-tool`); (2) an explicit note that deleting `test_cost_by_tool_is_honest_stub`'s
`assert "T4" in out` was an EXPECTED, REQUIRED change per D-01, not a regression.
</output>
