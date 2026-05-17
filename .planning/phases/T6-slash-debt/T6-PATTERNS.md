# Phase T6 — PRD §2.4 Slash Debt — Pattern Map

**Generated:** 2026-05-16 (authored from verified live-code anchors after agent write failed to persist 3×; every line/excerpt below was grepped from the working tree, not inferred).

**Phase posture:** HARDEN + TEST + DISCOVERABILITY. No new files in `voss/`, no new persistence (D-08). 4 edit sites, all with in-repo analogs.

Slash handler contract (all sites): `SlashHandler = Callable[[Any, list[str], str], None]` (`voss/harness/slash.py:8`); handlers are local closures in `_build_slash_registry`, output via `click.echo`, errors via `click.echo(..., err=True)`, never raise to the loop. Registry: `SlashRegistry.register/lookup` (`slash.py:25/30`), `SlashCommand.handler` (`slash.py:15`). Tests dispatch handlers directly: `reg.lookup("/x").handler(fake_ctx, args, line)` then assert on `capsys`.

---

## Edit Site 1 — `/cost --by-tool` even-split derivation (D-01, SLASH-07)

**Target:** `voss/harness/cli.py` `_cost` (def at `cli.py:582`). Replace the stub branch `cli.py:585-591`.

**Exact stub text being DELETED** (`cli.py:585-591`):
```
if "by-tool" in flags:
    click.echo(
        "  /cost --by-tool: per-tool cost tracking lands with T4 "
        "(prompt caching). Recorder doesn't yet attribute provider "
        "cost to individual tool calls."
    )
    return
```
Deleting this also obsoletes the tripwire test `test_cost_by_tool_is_honest_stub` (`tests/harness/test_repl_slash.py:225-231`, asserts `"T4" in out`) — see Edit Site 4. Expected/required per D-01, not a regression.

**Analog to mirror — the sibling `--by-model` branch (`cli.py:592-619`):**
```
if "by-model" in flags:
    by_model: dict[str, float] = {}
    for run in ctx.record.runs:
        m = ctx.record.model or get_config().default_model or "unknown"
        by_model[m] = by_model.get(m, 0.0) + float(run.get("cost_usd", 0.0))
    if not by_model:
        click.echo(f"session cost: ${ctx.total_cost:.4f} (no runs yet)")
        return
    width = max(len(m) for m in by_model)
    click.echo(f"session cost: ${ctx.total_cost:.4f}")
    for m, c in sorted(by_model.items(), key=lambda kv: -kv[1]):
        click.echo(f"  {m:<{width}}  ${c:.4f}")
    return
```
`--by-tool` is structurally a clone of this dict-aggregate-then-width-align-then-sorted-desc shape, with ONE critical difference: `--by-model` reads **run-level** `run.get("cost_usd")`; `--by-tool` must descend into each run's **iterations**.

**Data shape facts (verified):**
- `ctx.record.runs` elements are dict-like (`run.get("cost_usd")`, `run["iterations"]`).
- `RunRecord.iterations: list[IterationRecord]` (`voss/harness/session.py:132`).
- `IterationRecord` (`session.py:97-103`): `tool_results: list[dict]` (default `[]`), `cost_usd: float` (default `0.0`).
- tool_result element shape (`voss/harness/agent.py:341-348`): `tr.get("name","")`, `tr.get("args",{})`, `tr.get("result")`. Aggregate key = `tr["name"]`.

**Derivation spec (D-01, even-split, zero new persistence):**
- For each iteration with `cost_usd > 0` AND non-empty `tool_results`: per-call share = `cost_usd / len(tool_results)`; add that share to `by_tool[tr["name"]]` for each `tr` in `tool_results`.
- Skip iterations with `cost_usd == 0` or empty `tool_results` (Claude's-Discretion: skip — a turn with no tool calls contributes nothing).
- Output: one-time loud legend line `~approx (turn cost ÷ N tool calls)` (header once + clean rows; Claude's-Discretion preference), then width-aligned `{name:<width}  ${c:.4f}` rows sorted desc, mirroring `--by-model`.
- Reuse the `--by-model` empty-guard / total-line idiom.

**D-06 note (carry on this plan, no T4 file edited):** T6 ships before T4 and OWNS both `/cost --by-model` (already coded) and `/cost --by-tool` (this derivation). `T4-CONTEXT.md` D-09's placeholder-edit is dead-on-arrival; whoever executes T4 later must NOT re-stub `--by-tool`. T6 edits zero T4 files.

---

## Edit Site 2 — grouped `_print_slash_help` (D-04, SC#3, SLASH-01..07)

**Target:** `voss/harness/cli.py` `_print_slash_help` (def `cli.py:1587`, called at `cli.py:576`). Replace the flat listing with a grouped renderer.

**Registry source of truth:** the one-line `help` strings already exist per command in `_build_slash_registry` (e.g. the `/cost` help string `"session cost so far ([--by-model | --by-tool])"` at `cli.py:907`). D-04 = grouping only; do NOT rewrite descriptions.

**Spec:**
- Named buckets, finalized against the LIVE registry contents: **Editing** (`/diff` `/apply` `/discard`), **Session** (`/resume` `/budget` `/cost` `/clear`), **Insight** (`/why` `/tools` `/analyze`), **Control** (`/help` `/exit` `/mode`).
- **Long-tail `Other` bucket rule (mandatory):** any registered slash not in a named bucket falls into an `Other` group so NO registered command is ever dropped. Iterate `registry` ids; assert every id appears exactly once across all buckets.
- Preserve the existing width-align style (`f"  {name:<{width}}  {desc}"` idiom — same as the `--by-model` aligner) and the existing one-line `help` strings verbatim.

**Test constraint:** extend `TestSlashHelp` (`tests/harness/test_repl_slash.py:81`) — add a grouped-help assertion (group headers present; every `_build_slash_registry()` id rendered exactly once) WITHOUT weakening its existing token assertions.

---

## Edit Site 3 — dual-`main` `/help` signpost (D-04 widened, operator-approved W3)

**Two targets (operator chose BOTH entries, 2026-05-16):**
1. **Production** `voss/cli.py` `main` group docstring — `def main` at `voss/cli.py:149`, docstring `voss/cli.py:150-156` (`"""voss — compiler and agent. ... """`). This is `voss = "voss.cli:main"` (pyproject console script) — what pip/npm `voss --help` users actually see.
2. **Standalone** `voss/harness/cli.py` `main` group docstring — `@click.group(...)` at `cli.py:2192`, `def main` at `cli.py:2197`, preceded by the comment `# standalone entry: \`python -m voss.harness ...\`` at `cli.py:2188`. This is the line D-04 literally cited.

**Spec:** add the SAME single signpost sentence to BOTH docstrings (e.g. `Interactive commands: run \`voss chat\`, then /help`). NO `epilog=` kwarg on either group; NO slash-list duplication in either CLI (single canonical list stays in in-REPL `/help`, Edit Site 2). Acceptance asserts each of `python -m voss.cli --help` and `python -m voss.harness --help` shows exactly one `/help` signpost line and no second slash list. Record the operator-approved D-04 scope-widening verbatim in `T6-02-SUMMARY.md`.

---

## Edit Site 4 — test fixture extension + obsoleted-test rewrite + per-slash coverage (SC#1/SC#2, D-02/D-03/D-07)

**Target:** `tests/harness/test_repl_slash.py` ONLY. No production file touched (`git status --porcelain voss/` must stay empty for T6-03).

**Existing harness to reuse (do not replace):**
- `fake_ctx` fixture (`test_repl_slash.py:134`, in `class TestT6Behaviors:` at `:128`).
- Direct-dispatch pattern: `reg = _build_slash_registry(...)`; `reg.lookup("/x").handler(fake_ctx, args, line)`; assert `capsys`.
- Module-level parity test `test_t6_prd_slash_commands_registered` (`:118`) — extend its asserted tuple to include `/cost`.
- `TestSlashHelp` (`:81`), `TestT6Behaviors` (`:128`) house new cases.

**Edit Site 4a — obsoleted-test rewrite (T6-01 Task 2):** rewrite `test_cost_by_tool_is_honest_stub` (`:225-231`) — delete the `assert "T4" in out` tripwire, instead extend `fake_ctx`'s `record.runs` with an `iterations` key (each iteration `{cost_usd: float, tool_results: [{"name": ...}, ...]}`) and assert: tool names present, `~approx` legend present, `"T4" not in out`. Keep the existing `test_cost_by_model` (`:220`, `$0.0200` style) green — fixture extension must be ADDITIVE.

**Edit Site 4b — per-slash happy-path coverage (T6-03):**
- `/diff` (SLASH-01): subprocess monkeypatch OR `tmp_path` git repo; assert git-tree diff output (D-02, no code change).
- `/discard` (SLASH-03): already covered by existing tests (`:237`, `:247`) — D-02 git-tree, test-only, confirm in roll-up, no new code.
- `/resume` (SLASH-05, D-03): monkeypatch `voss.harness.cli.session_store.load`. Resolution order is FIXED at `voss/harness/session.py:222` (`_scan_dir`): `data.get("id","").startswith(target) or data.get("name") == target` — a single OR predicate, NO id-first/name-second ordering (also at `session.py:305,316`). Tests assert BOTH arms (id-prefix, exact-name) + cross-cwd warning (warn + stay in current cwd) WITHOUT changing that predicate.
- `/why` (SLASH-06, SC#2, D-07): audit-only. `_why` at `cli.py:655` reads `ctx.last_plan` only, renders `confidence:.2f` + rationale, NO provider call. **D-07 RESOLVED:** PRD Ticket 7 (`.vscode/voss_v_0_1_scope_lock.md:1213-1221`) is satisfied by the existing single `confidence:.2f` float; `ProbableValue` (PRD `:712`) is a runtime-layer type, NOT a `/why` output-format mandate → **NO `/why` code delta**, test + documented rationale only.
- Roll-up: confirm every SLASH-01..07 has ≥1 happy-path test; full-file + `tests/harness/` pytest green gate (exit-code-preserving, no `| tail`).

---

## Wave / serialization rationale

All three plans edit `voss/harness/cli.py` and/or `tests/harness/test_repl_slash.py` (overlapping `files_modified`). T6-02 also adds `voss/cli.py` (W3). File-ownership rule forces strict serialization: **W1 (T6-01) → W2 (T6-02) → W3 (T6-03)**. Each plan ~15-25% context. T6-01 doubles as the test-scaffold-first step (rewrites the `--by-tool` tripwire alongside its code change).
