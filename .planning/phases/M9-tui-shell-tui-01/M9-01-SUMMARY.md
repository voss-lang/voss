---
phase: M9
plan: 01
status: complete
date: 2026-05-14
---

# M9-01 Summary — Foundation: Library Choice + Headless Fallback + Baseline Parity

Wave-1 foundation. Textual locked as the M9 TUI library; capability module
shipped; `--plain` flag plumbed through all four interactive entry points;
80×24 minimum-size guard locked; pre-M9 stdout baseline captured and
defended by an automated parity test. Every subsequent M9 plan must keep
`test_plain_parity.py` green.

## Library Decision (TUI-01)

**Textual** confirmed via decision gate. UI-SPEC default per region grid +
modal overlays + scrollable panes + 256/truecolor + asyncio-native. ~5MB
pure-Python install; MIT licensed. Windows-console edge cases have
pre-locked fallback copy in UI-SPEC if they surface in later waves.

## Files Touched

| Path | Status |
|------|--------|
| `pyproject.toml` | `textual>=0.58,<1.0` added to `[project] dependencies` (NOT optional — TUI is the default product surface). |
| `voss/harness/tui/__init__.py` | New subpackage stub (docstring only). |
| `voss/harness/tui/capability.py` | New. `TUIDecision` dataclass + `tui_available()` + `tui_should_activate()` + `min_size_guard()`. |
| `voss/harness/render.py` | `make_renderer(*, json_mode, plain=False, force_tui=False)` — `--plain`/`VOSS_PLAIN` short-circuit to PlainRenderer; `force_tui` + size<80×24 → stderr+exit(2). |
| `voss/harness/cli.py` | `--plain` flag added to `do_cmd`, `chat_cmd`, `edit_cmd`, `resume_cmd`. `_run_repl` gains `plain: bool = False` kwarg. Threading verified by grep. |
| `tests/harness/tui/__init__.py` | Empty. |
| `tests/harness/tui/test_capability_and_plain_fallback.py` | New. 11 tests covering tui_available, all 5 decision-order branches, min_size_guard string, no-eager-import static check. |
| `tests/harness/tui/test_plain_parity.py` | New. 5 tests: baseline parity, auto-fallback parity, --json regression, small-terminal w/o force_tui, force_tui+small=exit(2). |
| `tests/harness/tui/baseline/plain_baseline.txt` | New. Locked stdout-only baseline from FakeProvider canned plan. |

## Capability Module Contract

```python
@dataclass(frozen=True)
class TUIDecision:
    activate: bool
    reason: str

def tui_available() -> bool: ...
def tui_should_activate(*, argv, env, stdout_isatty, json_mode, size) -> TUIDecision: ...
def min_size_guard(size: tuple[int, int]) -> str: ...
```

Decision order (first match wins):

1. `--plain` in argv → `(False, "--plain flag")`
2. `VOSS_PLAIN=1` in env → `(False, "VOSS_PLAIN env")`
3. `json_mode=True` → `(False, "--json mode")`
4. stdout not a TTY → `(False, "non-TTY stdout")`
5. size < 80×24 → `(False, "terminal below 80x24")`
6. `textual` import unavailable → `(False, "textual not installed")`
7. all checks pass → `(True, "ok")`

`tui_available()` uses a deferred `import textual` inside the function body
+ module-level cache. The capability module pays zero Textual import cost
at module-load time (locked by a static source-grep test).

`min_size_guard((cols, rows))` returns the EXACT UI-SPEC line 198 string:
`voss: terminal must be at least 80×24 (current: {cols}×{rows}). Resize or use --plain.`

The `×` glyph (U+00D7) is intentional — UI-SPEC locked.

## `--plain` Plumbing

Each of `do_cmd`, `chat_cmd`, `edit_cmd`, `resume_cmd` gains:

```python
@click.option("--plain", "plain", is_flag=True, help="Use line-streamed renderer; bypass TUI.")
```

`plain` threads through to `make_renderer(json_mode=..., plain=plain)` and
into `_run_repl(plain=..., ...)`. JsonRenderer still short-circuits on
`--json`. `VOSS_PLAIN=1` is honored at the capability layer.

`VOSS_FORCE_TUI=1` is the developer escape hatch used by acceptance tests
that need to assert the size guard fires.

## Baseline Parity

`tests/harness/tui/baseline/plain_baseline.txt` is the locked stdout-only
byte stream of `voss do --plain "echo plan-baseline"` against the
FakeProvider canned plan (locked in `tests/harness/test_voss_loop_parity.py`).

Idempotent capture:
- If the baseline file is missing AND `VOSS_CAPTURE_BASELINE=1` is set, the
  test writes the baseline and `pytest.skip`s.
- If the baseline file exists, `VOSS_CAPTURE_BASELINE` is IGNORED — bytes
  are always compared. No silent overwrite path.

Click 8.3 dropped the `mix_stderr=False` kwarg and now separates stdout
from stderr by default; the parity test compares `result.stdout`
explicitly so test outcome does not depend on stdout/stderr interleaving.

## Acceptance Gate Status

| Gate | Result |
|------|--------|
| `python -c "import textual"` | passes (0.89.1 installed) |
| `python -c "from voss.harness.tui.capability import tui_available, tui_should_activate, min_size_guard, TUIDecision"` | passes |
| `grep -v '^#' voss/harness/tui/capability.py | grep -c "^import textual"` | 0 (deferred inside `tui_available`) |
| `grep -c "textual>=0.58" pyproject.toml` | 1 |
| `grep -c 'is_flag=True, help="Use line-streamed renderer' voss/harness/cli.py` | 4 (do/chat/edit/resume) |
| `grep -c "plain: bool = False" voss/harness/cli.py` | 1 (`_run_repl` signature) |
| `wc -c tests/harness/tui/baseline/plain_baseline.txt` | 71 bytes (non-empty) |
| `grep -c "from tests.harness.test_voss_loop_parity import FakeProvider" tests/harness/tui/test_plain_parity.py` | 1 |
| `grep -c "VOSS_CAPTURE_BASELINE" tests/harness/tui/test_plain_parity.py` | 2 (idempotent capture logic) |
| `grep -c "class TextualRenderer" voss/harness/render.py` | 0 (M9-02 lands the real one) |
| `pytest tests/harness/tui/ -q` | 16 passed |
| Full harness suite (excl. pre-existing diagnostics failures) | 311 passed, 2 skipped |

## Threat Model Outcomes

| Threat | Status |
|--------|--------|
| T-M9-01-05 baseline silent overwrite | mitigated — VOSS_CAPTURE_BASELINE only writes when file is absent. |
| T-M9-01-02 size-guard exit loop | mitigated — single `sys.exit(2)` path; no retry. |
| T-M9-01-03 baseline leaks user paths | mitigated — FakeProvider canned plan, tmp_path cwd, monkeypatched `_resolve_auth_or_die` returns synthetic `Resolution(source="fake", detail="fake")`. Baseline content: 3 lines, no PII. |

## Deviations from Plan

1. **`test_capability_import_does_not_eager_import_textual` reworked as a static source-grep** instead of `sys.modules` mutation. The original sys.modules approach leaked module bindings across tests (subsequent tests saw a re-imported `voss.harness.tui.capability` instance, breaking monkeypatch routing). Static grep over the file source achieves the same invariant without runtime mutation.

2. **`CliRunner(mix_stderr=False)` dropped** — Click 8.2+ removed the kwarg. Click 8.3 separates stdout and stderr by default. Tests use `result.stdout` and `result.stderr` directly.

3. **`size` parameter in `tui_should_activate` uses live `shutil.get_terminal_size` fallback** when None passed. Default fallback `(80, 24)` is "safe" — the guard never trips on a tty whose size cannot be queried.

4. **`_install_fake_provider` test helper also monkeypatches `_git_status`** to return `"no git"` so the baseline does not embed shell-out output that varies by working directory. The PlainRenderer doesn't currently emit git_status, but pinning it removes any future drift risk if PlainRenderer.banner changes.

5. **Baseline captured stdout-only via `result.stdout`** instead of `result.output` (mixed). UI-SPEC's Headless contract specifies "Stdout byte-identical when `--plain` is set OR when stdout is non-TTY"; comparing the stderr stream as well would conflate user-facing stdout bytes with trace output that PlainRenderer routes to stderr by design.

No other deviations.

## Phase Handoff

- M9-02 builds the Textual app skeleton; this plan's `tui_should_activate` returns the `activate=True` signal it consumes.
- M9-02+ MUST keep `tests/harness/tui/test_plain_parity.py` green or update the baseline via the locked capture path.
- `VOSS_FORCE_TUI=1` is the M9-02 acceptance hook for terminal-too-small tests.
