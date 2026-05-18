# Phase M11: Voss-aware Tools (CAPS-01b) - Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 20 candidate source/test files
**Analogs found:** 17 / 20

---

## File Classification

| New/Modified File | Role | Closest Analog | Match Quality |
|---|---|---|---|
| `voss/harness/voss_inspect.py` | pure inspector helpers | `voss/harness/session.py`, `voss/harness/recorder.py` | role-match |
| `tests/harness/test_voss_inspect.py` | core unit tests | `tests/harness/test_session_iterations.py` | exact |
| `voss/harness/voss_lint_schema.py` | schema normalizer | `voss/harness/skills/voss_lint_as_skill.py` | role-match |
| `tests/harness/test_voss_lint_schema.py` | schema contract tests | `tests/skills/test_skills_smoke.py` | role-match |
| `voss/harness/voss_diff.py` | `.voss` to Python diff helper | `voss/cli.py` compile path, `voss/codegen.py` | role-match |
| `tests/harness/test_voss_diff.py` | diff tests | `tests/codegen/test_examples.py` | role-match |
| `voss/harness/tools.py` | tool registration | existing `make_toolset()` entries | exact |
| `voss/harness/cli.py` | click commands + slash handlers | existing `/why`, `/cost`, `/diff`, `jobs_cmd` | exact |
| `tests/harness/test_tools.py` | tool classification tests | self | exact |
| `tests/harness/test_repl_slash.py` | slash tests | self | exact |
| `voss/harness/tui/widgets/probable_modal.py` | read-only modal | `budget_modal.py`, `confidence_bar.py` | role-match |
| `voss/harness/tui/widgets/budget_trace_modal.py` | read-only modal | `budget_modal.py`, `budget_meter.py` | role-match |
| `voss/harness/tui/widgets/voss_py_diff_modal.py` | read-only modal | `diff_modal.py` | role-match |
| `voss/harness/tui/widgets/__init__.py` | public widget exports | self | exact |
| `voss/harness/tui/renderer.py` | modal bridge | existing `show_budget_modal()` / `show_diff_modal()` | exact |
| `tests/harness/tui/test_m11_modals.py` | modal tests | `test_budget_modal.py`, `test_textual_renderer_protocol.py` | role-match |
| `tests/harness/test_m11_acceptance.py` | phase acceptance guard | `test_no_new_runtime_hooks.py`, `test_repl_slash.py` | role-match |

---

## Patterns to Copy

### Recorded Session Normalization

`SessionRecord.runs` are dictionaries after JSON hydration. `RunRecord`
instances also exist in live code paths. New helpers must accept both.

Pattern:

```python
def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
```

Use this for decisions, iterations, token fields, and exit reasons.

### Tool Registration

`make_toolset()` returns:

```python
"voss_check": ToolEntry(descriptor=voss_check, is_mutating=False),
```

M11 tools should follow the same shape:

```python
@tool(name="voss_probable_inspect", description="Inspect recorded Voss decision confidence.")
async def voss_probable_inspect(session: str, decision: int | None = None) -> str:
    ...

"voss_probable_inspect": ToolEntry(descriptor=voss_probable_inspect, is_mutating=False),
```

No M11 tool is mutating. The explicit tool count tests must be updated.

### Slash Registration

Existing slash handlers are local functions inside `_build_slash_registry()`,
then added as `SlashCommand(...)` entries. Follow the `/why` and `/diff`
pattern:

```python
def _probable(ctx, args, _line):
    ...

SlashCommand("/probable", "inspect recorded decision confidence", _probable)
```

Do not add `/budget`; it is already the T6 USD budget command. Use `/btrace`.

### Click Commands

Existing standalone command pattern:

```python
@click.command("tools")
@click.option("--cwd", ...)
def tools_cmd(cwd_str: str) -> None:
    ...
```

Add command groups in `voss/harness/cli.py` and register them in
`AGENT_COMMANDS`. Keep top-level `voss run` reserved for the compiler.

Recommended command surface:

- `voss inspect probable <session-id> [--decision N] [--cwd .]`
- `voss inspect budget <session-id> [--cwd .]`
- `voss vdiff <file.voss> [--cwd .]`

### Lint Schema Consumer

Producer file `voss/harness/skills/voss_lint_as_skill.py` is the source of
truth. Consumer module only validates and normalizes:

- top-level `version == 1`
- `findings` is a list
- each finding has exactly `file`, `line`, `col`, `rule`, `severity`, `msg`,
  `hint`

Do not add fields and do not rename fields.

### Voss Diff Pairing

Compile command pattern in `voss/cli.py`:

- `_walk_voss_sources()`
- `_compile_source()`
- `.voss-cache/harness/<stem>.py` for directory compile.
- `harness/cache.py` constants:
  `CACHE_HARNESS_DIR = ".voss-cache/harness"`, `MANIFEST_NAME = "_manifest.json"`.

M11 should create pure helper functions in `voss/harness/voss_diff.py`:

- read source `.voss`
- resolve cached Python side if present
- otherwise parse/analyze/generate Python in memory
- render a bounded two-pane text view

No durable source map file.

### TUI Read-only Modals

`DiffModal` is approval-specific; do not reuse it for read-only Voss/Python
diffs. Copy the modal-shell pattern only:

```python
class SomeModal(ModalScreen):
    BINDINGS = [("escape", "cancel", "Close")]
    def compose(self) -> ComposeResult:
        with Vertical(id="..."):
            yield Static("...", id="...", classes="modal-title")
```

Use existing glyphs only; do not add new glyph constants unless unavoidable.

---

## Anti-patterns

- Adding fields to `RunRecord`, `IterationRecord`, or `SessionRecord`.
- Editing `voss/harness/recorder.py`.
- Editing `voss_runtime/probable.py`, `voss_runtime/budget.py`, or
  `voss_runtime/agent.py`.
- Calling the probable inspector a DAG or graph when it is an ordered
  decision sequence.
- Reusing `/budget` for the tracer.
- Reusing `DiffModal` accept/reject actions for a read-only generated-code
  viewer.

