# Phase T6: PRD §2.4 Slash Debt - Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 4 (1 source file with 3 distinct edit sites + 1 test file)
**Analogs found:** 4 / 4 (all in-repo — this is a harden+test phase, every pattern already exists)

> **Phase posture (from T6-CONTEXT D-05/D-08):** HARDEN + TEST + DISCOVERABILITY,
> not greenfield. Every slash already has a working implementation. There is
> **no new file** and **no new persistence**. All four "files" below are
> *edit sites* within two existing files. Every analog is an adjacent function
> in the same file — the planner/executor must *replicate the established
> shape*, not invent.

---

## File Classification

| Modified File / Edit Site | Role | Data Flow | Closest Analog | Match Quality |
|---------------------------|------|-----------|----------------|---------------|
| `voss/harness/cli.py` `_cost` `--by-tool` branch (585-591, replaces stub) | cost-derivation logic (slash handler sub-branch) | transform (read-only aggregation over `record.runs`) | `_cost` `--by-model` branch, same fn, lines 592-610 | exact (sibling branch, same handler) |
| `voss/harness/cli.py` `_print_slash_help` (1587-1589) | help renderer | request-response (read live registry → stdout) | `SlashRegistry.help_lines` `slash.py:45-52` + grouping is net-new | role-match (renderer exists; grouping is the only new logic) |
| `voss/harness/cli.py` `main` group docstring epilog (2197-2201) | config / CLI help text | request-response (static help text) | `chat_cmd` docstring `cli.py:1195` | role-match (one signpost line, no new code) |
| `tests/harness/test_repl_slash.py` per-slash happy-path tests + replace `test_cost_by_tool_is_honest_stub` (225-231) | test | request-response (handler-direct, capsys) | `TestT6Behaviors` class, same file, lines 128-258 | exact (extend the existing T6 test class) |

**No new slash handlers.** SLASH-01..06 already register and pass their existing
`TestT6Behaviors` tests (test_repl_slash.py:171-257). T6's only *logic* change is
the `--by-tool` branch (D-01) and `/help` grouping (D-04). Everything else is
audit + add ≥1 happy-path test (SC#1).

---

## Pattern Assignments

### Edit Site 1 — `_cost` `--by-tool` branch (cost-derivation logic, transform)

**Analog:** the `--by-model` branch in the *same function* (`voss/harness/cli.py:592-610`).
Copy its structure exactly: flag check → iterate `ctx.record.runs` → build a
`dict[str, float]` → empty guard → width-aligned sorted echo. The ONLY
differences are (a) descend into per-iteration data for `tool_results`, and
(b) the loud `~approx` legend (D-01).

**Slash-handler signature + flag-parse pattern to keep** (cli.py:582-585):
```python
def _cost(ctx: ReplContext, args: list[str], _line: str) -> None:
    # T6 / SLASH-07: support --by-model and --by-tool flags.
    flags = {a.lstrip("-") for a in args}
    if "by-tool" in flags:
        ...  # <-- D-01 REPLACES the 585-591 stub body here
```

**Current stub body being DELETED** (cli.py:585-591 — this exact text is what
`test_cost_by_tool_is_honest_stub` asserts on, see Edit Site 4):
```python
    if "by-tool" in flags:
        click.echo(
            "  /cost --by-tool: per-tool cost tracking lands with T4 "
            "(prompt caching). Recorder doesn't yet attribute provider "
            "cost to individual tool calls."
        )
        return
```

**Aggregation pattern to COPY (the `--by-model` analog, cli.py:592-610):**
```python
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

**Underlying data shape `--by-tool` derives from (zero new persistence, D-08).**
`ctx.record.runs` is `list[dict]` (serialized `RunRecord`, `session.py:113-136`).
The `--by-model` analog uses **run-level** `run["cost_usd"]`. The D-01 even-split
must descend one level into **per-iteration** records, where `tool_results` lives:

- `RunRecord.iterations: list[IterationRecord]` → serialized as `run["iterations"]` (list[dict]).
- `IterationRecord` (`session.py:96-109`): `cost_usd: float`, `tool_results: list[dict]`.
- `tool_results` dict element shape (built at `agent.py:748-755`):
  ```python
  {"name": s.name, "args": {...redacted...}, "result": "..."}
  ```
  → the tool name key is `tr["name"]`.

**D-01 even-split logic the executor must write** (new — no exact analog, but
mirror the `--by-model` skeleton above; this is the derivation spec):
- For each `run` in `ctx.record.runs`, for each `it` in `run.get("iterations", [])`:
  - `cost = float(it.get("cost_usd", 0.0))`; `trs = it.get("tool_results") or []`
  - If `cost <= 0` or `not trs`: **skip** (Claude's-Discretion recommendation in
    CONTEXT line 64 — a turn with no tool calls contributes nothing).
  - `share = cost / len(trs)`; for each `tr` in `trs`:
    `by_tool[tr.get("name", "?")] += share`
- Empty guard + width-aligned sorted echo: copy the `--by-model` tail verbatim.
- **Loud caveat (D-01, mandatory):** emit a one-time header/legend line tagged
  `~approx (turn cost ÷ N tool calls)` (CONTEXT line 65 recommends header-once +
  clean rows, not per-row suffix). The phrase must make the approximation
  unmissable; it must NOT mention "T4" (that string is the obsoleted tripwire).

**Error-handling convention (keep):** `_cost` never raises; empty/no-data path
prints an informational line and `return`s (same as `--by-model`'s
`"(no runs yet)"`). No `err=True` needed — `--by-tool` with no data is not an
error, it's "nothing attributable yet".

---

### Edit Site 2 — `_print_slash_help` grouped output (help renderer, request-response)

**Analog:** `_print_slash_help` (`voss/harness/cli.py:1587-1589`) + the registry
it reads (`SlashRegistry.help_lines`, `slash.py:45-52`).

**Current renderer (flat, alphabetical) — the thing D-04 replaces:**
```python
def _print_slash_help(registry: SlashRegistry | None = None) -> None:
    registry = registry or _build_slash_registry()
    click.echo("\n".join(registry.help_lines()))
```

**`help_lines()` width-alignment pattern to preserve** (`slash.py:45-52`) — the
grouped renderer must keep this `name` left-pad style per group:
```python
def help_lines(self) -> list[str]:
    commands = [
        self._commands[name]
        for name in self.ids()
        if not self._commands[name].hidden
    ]
    width = max((len(c.name) for c in commands), default=0)
    return [f"{c.name:<{width}}  {c.help}" for c in commands]
```

**Registry read API available to the new grouped renderer:**
- `registry.ids(include_hidden=False) -> list[str]` (sorted names, dedup'd, `slash.py:33-43`).
- `registry.lookup(name) -> SlashCommand | None` (`slash.py:30-31`).
- `SlashCommand` fields (`slash.py:11-18`): `.name`, `.help`, `.aliases`,
  `.mutating`, `.hidden`. Each registered command already carries its one-line
  `help` string (see the `SlashCommand("/why", "explain the last plan ...", _why)`
  registrations at cli.py:901-959) — **D-04's one-line description per slash
  already exists**; the only new work is *grouping*, not authoring descriptions.

**Grouping spec (D-04, CONTEXT lines 50-52)** — define group→slash-name buckets,
then for each group echo a header + the `help_lines`-style aligned rows for that
group's members, then any ungrouped registered slashes under a fallback bucket so
nothing silently disappears (M9-03 SlashPalette parity, D-05). Suggested groups
(planner finalizes against the live registry at cli.py:901-959):
- **Editing:** `/diff` `/apply` `/discard`
- **Session:** `/resume` `/budget` `/cost` `/clear` `/save-session`
- **Insight:** `/why` `/tools` `/analyze`
- **Control:** `/help` `/exit` `/mode` `/model`

**Existing test that constrains this change** (`TestSlashHelp`,
test_repl_slash.py:81-86) — the grouped output MUST still contain every token
this asserts (`/login`, `/model`, `/mode`, `--confirm`). Don't drop slashes when
grouping; bucket the long tail rather than omit.

---

### Edit Site 3 — `voss --help` epilog signpost (CLI help text, request-response)

**Analog:** the `chat_cmd` docstring (`voss/harness/cli.py:1195`):
```python
    """Interactive agent REPL. Ctrl-D or /exit to quit."""
```

**Target to edit — the `main` group docstring** (`cli.py:2196-2201`); this is
the text Click renders for `voss --help`:
```python
@click.pass_context
def main(ctx: click.Context) -> None:
    """voss · agent (standalone harness invocation).

    Usually invoked as `voss do` / `voss chat`. Bare invocation drops into chat.
    """
```

**Pattern:** add exactly ONE signpost line to this docstring (D-04 — single
canonical `/help`, CLI epilog points to it, no slash list duplicated). e.g. a
trailing line like `Interactive commands: run \`voss chat\`, then /help`.
No new code, no `epilog=` kwarg needed — the docstring *is* the help body.
(Click's `context_settings` here is `help_option_names`, cli.py:2192-2195; do
not add an `epilog=` arg — extend the docstring to match the existing style.)

---

### Edit Site 4 — `tests/harness/test_repl_slash.py` (test, request-response)

**Analog:** the entire `TestT6Behaviors` class in the *same file*
(test_repl_slash.py:128-258). Every new per-slash happy-path test (SC#1) must
copy this exact shape: build registry → `lookup(name).handler(fake_ctx, args, line)`
→ assert on `capsys.readouterr()`.

**`fake_ctx` fixture to REUSE/EXTEND** (test_repl_slash.py:133-169) — already
provides a `SimpleNamespace` ctx with `record.runs` as `list[dict]`. For the new
`--by-tool` test, the existing `runs` entries (lines 156-159) have only
`cost_usd` + `changed` — extend ONE run dict with an `iterations` key matching
the real shape so the even-split has data:
```python
runs=[
    {"cost_usd": 0.008, "changed": []},
    {
        "cost_usd": 0.012,
        "changed": ["voss/harness/cli.py"],
        "iterations": [
            {
                "cost_usd": 0.012,
                "tool_results": [
                    {"name": "fs_read", "args": {}, "result": "..."},
                    {"name": "fs_grep", "args": {}, "result": "..."},
                ],
            }
        ],
    },
],
```
(0.012 ÷ 2 tools → fs_read 0.006, fs_grep 0.006 — assert both names + a `~approx`
marker appear; assert `"T4"` does NOT.)

**Canonical test pattern to copy** (test_repl_slash.py:216-223, the `--by-model`
test — closest analog for the new `--by-tool` test):
```python
def test_cost_by_model_groups_by_session_model(self, fake_ctx, capsys):
    from voss.harness.cli import _build_slash_registry

    reg = _build_slash_registry()
    reg.lookup("/cost").handler(fake_ctx, ["--by-model"], "/cost --by-model")
    out = capsys.readouterr().out
    assert "claude-sonnet-4-7" in out
    assert "$0.0200" in out  # 0.012 + 0.008
```

**Test that MUST be REPLACED, not added to** (test_repl_slash.py:225-231) — D-01
deliberately obsoletes this; the `"T4" in out` assertion is the tripwire CONTEXT
line 154 calls out. Rewrite it to assert the approximation output instead:
```python
def test_cost_by_tool_is_honest_stub(self, fake_ctx, capsys):   # <- rename + rewrite
    from voss.harness.cli import _build_slash_registry

    reg = _build_slash_registry()
    reg.lookup("/cost").handler(fake_ctx, ["--by-tool"], "/cost --by-tool")
    out = capsys.readouterr().out
    assert "T4" in out  # references the phase that closes this gap  <- DELETE this assertion
```
Replace with: assert tool names appear, assert the `~approx` legend appears,
assert `"T4" not in out`.

**Registration-parity test to extend** (test_repl_slash.py:118-125) — already
asserts `/diff /apply /discard /budget /resume /why` register. Add `/cost`
`--by-model`/`--by-tool` coverage and any missing SLASH-01..07 happy-path
exercises here or as new `TestT6Behaviors` methods (SC#1: ≥1 integration test
per slash).

**Per-slash happy-path coverage gaps (SC#1) — what to add, mirroring existing
methods in the same class:**
- `/diff` and `/discard --confirm` (live git) — CONTEXT line 130-131 says heavier
  integrations are "covered by Plan 07 e2e"; for T6, the dry-run path
  (`test_discard_dry_run_lists_files`, line 233) is the existing analog; add a
  `/diff` happy-path test using `tmp_path` as a git repo or a `subprocess.run`
  monkeypatch following the same capsys shape.
- `/resume` — assert `session_store.load` resolution: `session.py:227-261`
  `load()` already resolves id-prefix OR exact name (`_scan_dir`,
  session.py:213-224: `data["id"].startswith(...) or data["name"] == ...`).
  D-03 only needs a test confirming `/resume <name>` and `/resume <id>` both
  resolve and that cross-cwd prints the warning (cli.py:767-772) — NO code
  change to resolution order.
- `/why`, `/budget`, `/apply`, `/cost --by-model`, `/discard` dry-run — already
  covered (test_repl_slash.py:171-257). Audit-only per D-05.

---

## Shared Patterns

### Slash handler signature & I/O convention
**Source:** `voss/harness/slash.py:8` + every handler in `_build_slash_registry`
(cli.py:572-899).
**Apply to:** the `--by-tool` branch (no signature change — it's a sub-branch of
existing `_cost`).
```python
SlashHandler = Callable[[Any, list[str], str], None]   # (ctx, args, line) -> None
# stdout via click.echo(...); errors via click.echo(..., err=True)
# handlers never raise to the REPL loop; they print + return
```
The `--by-tool` "no attributable data" path is informational → plain
`click.echo` + `return` (mirror `--by-model`'s `"(no runs yet)"`), NOT `err=True`.

### Read-only aggregation over `ctx.record.runs`
**Source:** `_cost` `--by-model` (cli.py:592-610).
**Apply to:** `--by-tool` (D-01). Pattern = build a `dict[str, float]`, empty
guard returns an info line, `width = max(len(k) for k in d)`, then
`for k, v in sorted(d.items(), key=lambda kv: -kv[1]): click.echo(f"  {k:<{width}}  ${v:.4f}")`.
Zero new persistence (D-08): only *reads* the already-serialized
`RunRecord`/`IterationRecord` dicts.

### Test-by-handler-direct-dispatch (no full REPL loop)
**Source:** module docstring test_repl_slash.py:1-5 + `TestT6Behaviors`
(test_repl_slash.py:128-258).
**Apply to:** every new SC#1 test. Build `_build_slash_registry()`, call
`reg.lookup("/x").handler(fake_ctx, args, line)`, assert on
`capsys.readouterr()`. Reuse the `fake_ctx` `SimpleNamespace` fixture; extend
its `runs` dicts rather than introducing a real `SessionRecord`.

### Subprocess-with-timeout (only if a /diff e2e test shells out)
**Source:** `_diff` (cli.py:684-702) / `_discard` (cli.py:736-752).
**Apply to:** any new git-touching test setup — `subprocess.run(..., cwd=str(ctx.cwd),
capture_output=True, text=True, timeout=15)`, stderr surfaced via
`click.echo(..., err=True)`. Pattern reused, not extended (D-08).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | None. This is a harden+test phase; every required pattern (handler shape, run aggregation, registry render, handler-direct test) already exists in-repo. The only net-new *logic* is (a) the `--by-tool` even-split arithmetic — no exact analog but structurally a clone of `--by-model`, and (b) `/help` grouping — a thin wrapper over the existing `help_lines()` aligner. Neither warrants RESEARCH.md fallback. |

---

## Cross-Phase Reconciliation Note (D-06 — for the planner, not a code change)

T6 OWNS `/cost --by-tool` and ships before T4. T4-CONTEXT D-09's placeholder
edit (changing the stub message to say "T6") becomes a **no-op/obsolete** the
moment T6 lands the real approximation. **T6 must NOT edit any T4 file.** The
planner should add a one-line note in the T6 plan flagging that whoever later
executes T4 must NOT re-introduce a `--by-tool` stub (the T6 approximation is
the final behavior).

---

## Metadata

**Analog search scope:** `voss/harness/cli.py`, `voss/harness/slash.py`,
`voss/harness/session.py`, `voss/harness/recorder.py`, `voss/harness/agent.py`,
`tests/harness/test_repl_slash.py`.
**Files scanned:** 6.
**Key data-shape facts confirmed:** `ctx.record.runs` is `list[dict]`
(serialized `RunRecord`, session.py:113); per-iteration cost+tools live at
`run["iterations"][*]` → `IterationRecord` (session.py:96-109) with
`cost_usd: float` + `tool_results: list[dict]`; each `tool_results` element is
`{"name", "args", "result"}` (agent.py:748-755). The `--by-model` analog uses
*run-level* `cost_usd`; `--by-tool` must descend one level into `iterations`.
**Pattern extraction date:** 2026-05-16.
