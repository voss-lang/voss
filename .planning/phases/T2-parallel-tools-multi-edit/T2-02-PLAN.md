---
phase: T2-parallel-tools-multi-edit
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/config.py
  - voss_runtime/_config.py
  - voss/harness/cli.py
  - tests/harness/test_agent_config.py
autonomous: true
requirements: [PAR-05]
must_haves:
  truths:
    - "voss_runtime.RuntimeConfig has a max_parallel_reads: int field defaulting to 8"
    - "voss.harness.config.get_max_parallel_reads() reads [agent] max_parallel_reads from the same TOML loader T1-04 introduces, with safe int parsing"
    - "Out-of-range value (n < 1 or n > 32) falls back to default 8 with RuntimeWarning"
    - "Non-int value (e.g. 'foo') falls back to default 8 with RuntimeWarning"
    - "cli.py bootstrap calls configure(max_parallel_reads=get_max_parallel_reads()) once at startup, alongside T1-04's max_iterations bootstrap"
    - "get_config().max_parallel_reads returns the configured value at runtime; the singleton honors the configure() call"
    - "Both [agent] max_iterations (T1) and [agent] max_parallel_reads (T2) parse from the same [agent] block in ~/.config/voss/config.toml"
  artifacts:
    - path: "voss_runtime/_config.py"
      provides: "RuntimeConfig.max_parallel_reads: int = 8 field"
      contains: "max_parallel_reads"
    - path: "voss/harness/config.py"
      provides: "get_max_parallel_reads() loader with range validation + fallback warning"
      contains: "def get_max_parallel_reads"
    - path: "voss/harness/cli.py"
      provides: "Bootstrap configure(...) call extended with max_parallel_reads=get_max_parallel_reads()"
      contains: "max_parallel_reads"
    - path: "tests/harness/test_agent_config.py"
      provides: "5 roundtrip + fallback tests for max_parallel_reads"
      contains: "test_max_parallel_reads"
  key_links:
    - from: "voss/harness/config.py:get_max_parallel_reads"
      to: "voss_runtime._config.RuntimeConfig.max_parallel_reads"
      via: "default sourced from get_config().max_parallel_reads"
      pattern: "get_config\\(\\)\\.max_parallel_reads"
    - from: "voss/harness/cli.py bootstrap"
      to: "voss.harness.config.get_max_parallel_reads"
      via: "configure(max_parallel_reads=get_max_parallel_reads())"
      pattern: "max_parallel_reads=get_max_parallel_reads\\(\\)"
---

<objective>
Land the PAR-05 config knob: `[agent] max_parallel_reads` in
`~/.config/voss/config.toml` parses through the same `[agent]` section loader
T1-04 introduces, with default 8, range 1–32, and graceful fallback-with-
RuntimeWarning on bad values. Wire `RuntimeConfig.max_parallel_reads` as the
singleton field consumed by the scheduler (T2-03 will read
`get_config().max_parallel_reads`). Bootstrap from `cli.py` parallel to
T1-04's `max_iterations` bootstrap.

Purpose: SPEC PAR-05 + CONTEXT.md D-15/D-16 lock this knob's existence,
default, and range. RESEARCH.md A2 confirms `RuntimeConfig` is a `@dataclass`
that accepts new fields via `configure(...)` (matches T1-04 pattern). This
plan is Wave 1 because it has no dependency on T1-04 — both phases co-design
the `[agent]` section, and T2 owns the loader extension per CONTEXT.md D-15
("T2 owns the loader extension"). Wave 1 parallel with T2-01 (zero file overlap).

Output: RuntimeConfig.max_parallel_reads field; get_max_parallel_reads()
loader; cli.py bootstrap wire-in; roundtrip + fallback tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-RESEARCH.md
@.planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-04-PLAN.md
@voss/harness/config.py
@voss_runtime/_config.py
@voss/harness/cli.py
</context>

<interfaces>
Existing config.py shape (`voss/harness/config.py:18-39`):
```
_HARNESS_BLOCK = re.compile(r"^\[harness\][^\[]*", re.MULTILINE)
_KV = re.compile(r'^\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)

def _parse_harness_section(text: str) -> dict[str, str]: ...
def load_harness_config() -> dict[str, str]: ...
```

T1-04 has already introduced (or will introduce before T2-02 executes):
- `_AGENT_BLOCK = re.compile(r"^\[agent\][^\[]*", re.MULTILINE)` (or
  equivalent — exact name is T1-04's call)
- `load_agent_config() -> dict[str, str]` parallel to `load_harness_config`
- `get_max_iterations() -> int` consuming `cfg.get("max_iterations")` from
  load_agent_config, with int parse + fallback to default
- A field `max_iterations: int = 8` on `voss_runtime._config.RuntimeConfig`
- `cli.py` bootstrap: `configure(max_iterations=get_max_iterations())` at
  startup

T2-02 piggybacks one more key:
- Add `max_parallel_reads: int = 8` to RuntimeConfig (mirror max_iterations)
- Add `get_max_parallel_reads() -> int` to config.py (mirror get_max_iterations)
- Extend cli.py bootstrap: `configure(max_iterations=..., max_parallel_reads=get_max_parallel_reads())`

ON-DISK FORMAT CONVENTION (per RESEARCH.md "T1-04 establishes the [agent]
section parser"): values are quoted in the TOML file (e.g. `max_parallel_reads
= "8"`) and the loader casts to int at read time. Match T1-04's convention
exactly — do NOT introduce an `_KV_INT` parallel regex unless T1-04 already
did so.

Fallback semantics (locked by SPEC PAR-05 + Constraint 6):
- Out-of-range (n < 1 or n > 32): fall back to default 8, emit
  `warnings.warn(..., RuntimeWarning)` with the offending value
- Non-int (raw fails `int(raw)`): same fallback + warning
- Missing key: return default silently (no warning — missing is normal)

Test convention (from `tests/harness/test_harness_config.py:11-14` — the
`xdg` fixture pattern):
```
@pytest.fixture
def xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path
```
Writing `tmp_path / "voss" / "config.toml"` with an `[agent]` block is the
canonical test setup.

WHY THIS PLAN IS WAVE 1 (no dependency on T1-04 even though T1-04 lays the
[agent] loader): T1-04 is required by EXECUTION but its on-disk file changes
(_AGENT_BLOCK regex + load_agent_config) are already in flight per the
phase context. The planner can choose to either (a) treat T1-04 as a
prerequisite (Wave 0) or (b) defensively duplicate the [agent] parser if
T1-04's symbols are missing. THIS PLAN ASSUMES T1-04 SHIPS THE [agent]
LOADER. If executor reads voss/harness/config.py and does NOT find
`load_agent_config` / `_AGENT_BLOCK`, the executor adds them as part of
this task (Task 1 already covers the loader function — extend to include
the regex if absent).
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: RuntimeConfig.max_parallel_reads field + get_max_parallel_reads loader</name>
  <files>voss_runtime/_config.py, voss/harness/config.py, tests/harness/test_agent_config.py</files>
  <read_first>
    - .planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md (PAR-05 + acceptance criteria 3-4 "max_parallel_reads = 2 caps peak"; "default is 8"; "out-of-range falls back with warning")
    - .planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md (D-15, D-16)
    - .planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md (section "voss/harness/config.py — load_agent_config / get_max_parallel_reads")
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-04-PLAN.md (find the get_max_iterations function and [agent] loader patterns to copy)
    - voss/harness/config.py (entire file; locate any T1-04 additions — `grep -n "agent\|max_iterations" voss/harness/config.py`)
    - voss_runtime/_config.py (entire file; locate RuntimeConfig dataclass + the T1-04 max_iterations field)
    - tests/harness/test_harness_config.py (xdg fixture pattern at lines 11-14)
    - tests/harness/test_agent_config.py if it exists (T1-04 file); otherwise this plan creates it
  </read_first>
  <behavior>
    - get_max_parallel_reads() returns 8 when no config.toml file exists (default)
    - get_max_parallel_reads() returns 8 when config.toml exists but [agent] block lacks max_parallel_reads key
    - get_max_parallel_reads() returns 16 when [agent] max_parallel_reads = "16" is set
    - get_max_parallel_reads() returns 1 when [agent] max_parallel_reads = "1" is set (min boundary)
    - get_max_parallel_reads() returns 32 when [agent] max_parallel_reads = "32" is set (max boundary)
    - get_max_parallel_reads() returns 8 + RuntimeWarning when [agent] max_parallel_reads = "0" is set (below range)
    - get_max_parallel_reads() returns 8 + RuntimeWarning when [agent] max_parallel_reads = "33" is set (above range)
    - get_max_parallel_reads() returns 8 + RuntimeWarning when [agent] max_parallel_reads = "100" is set
    - get_max_parallel_reads() returns 8 + RuntimeWarning when [agent] max_parallel_reads = "foo" is set (non-int)
    - get_max_parallel_reads() returns 8 + RuntimeWarning when [agent] max_parallel_reads = "" is set (empty string)
    - Both max_iterations AND max_parallel_reads round-trip from the same [agent] block in one config.toml
    - configure(max_parallel_reads=12) sets get_config().max_parallel_reads to 12 (RuntimeConfig field round-trip)
    - reset_config() restores get_config().max_parallel_reads to 8 (default)
  </behavior>
  <action>
    Edit `voss_runtime/_config.py`:

    Find the `RuntimeConfig` dataclass. If T1-04 added `max_iterations: int = 8`,
    add `max_parallel_reads: int = 8` immediately AFTER it. If T1-04 has
    NOT yet shipped, add BOTH fields (this plan covers max_parallel_reads;
    add max_iterations only if it's missing AND a comment note "added
    here in T2-02 in case T1-04 lands later; both fields target the
    same [agent] section in config.toml").

    The exact addition (assuming T1-04 already added max_iterations):
    ```
    @dataclass
    class RuntimeConfig:
        # ... existing fields ...
        max_iterations: int = 8        # T1-04
        max_parallel_reads: int = 8    # T2-02 (PAR-05) — per CONTEXT.md D-15
    ```

    Edit `voss/harness/config.py`:

    Locate the T1-04 `load_agent_config` function and `get_max_iterations`
    function. If `load_agent_config` exists, simply add `get_max_parallel_reads`
    as a sibling function. If `load_agent_config` does NOT exist (T1-04 not
    shipped yet), add BOTH `_AGENT_BLOCK` regex + `load_agent_config` +
    `get_max_iterations` + `get_max_parallel_reads`. The pattern is in
    T2-PATTERNS.md section "voss/harness/config.py" and in T1-04-PLAN.md.

    Add `get_max_parallel_reads` body (or extend if the function already
    started):
    ```
    def get_max_parallel_reads() -> int:
        """Resolve [agent] max_parallel_reads with safe fallback + range validation.

        Range 1-32 (inclusive). Out-of-range or non-int values fall back to
        the RuntimeConfig default (8) with a RuntimeWarning. Missing key
        returns the default silently.
        """
        from voss_runtime import get_config
        default = get_config().max_parallel_reads
        cfg = load_agent_config()
        raw = cfg.get("max_parallel_reads")
        if raw is None:
            return default
        try:
            n = int(raw)
        except (TypeError, ValueError):
            import warnings
            warnings.warn(
                f"[agent] max_parallel_reads = {raw!r} is not an integer; "
                f"falling back to default {default}",
                RuntimeWarning,
                stacklevel=2,
            )
            return default
        if not (1 <= n <= 32):
            import warnings
            warnings.warn(
                f"[agent] max_parallel_reads = {n} out of range 1-32; "
                f"falling back to default {default}",
                RuntimeWarning,
                stacklevel=2,
            )
            return default
        return n
    ```

    Write tests in `tests/harness/test_agent_config.py` (extend the T1-04
    file). 13 tests matching the 13 behavior bullets above. Use the
    `xdg` fixture pattern from `tests/harness/test_harness_config.py:11-14`.
    Write config.toml content via `(tmp_path / "voss" / "config.toml").write_text(...)`.

    For RuntimeWarning tests, use `pytest.warns(RuntimeWarning, match="max_parallel_reads")`.

    For the "both keys round-trip" test, write a config.toml with:
    ```
    [agent]
    max_iterations = "12"
    max_parallel_reads = "16"
    ```
    and assert both getters return their respective values.

    Use a `@pytest.fixture(autouse=True)` that calls `reset_config()` at
    setup and teardown to prevent test-order contamination of the
    RuntimeConfig singleton.

    Do NOT modify load_harness_config. Do NOT touch the [harness] regex.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_agent_config.py -x -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "max_parallel_reads" voss_runtime/_config.py` returns 1 match (the field declaration)
    - source assertion: `grep -n "def get_max_parallel_reads" voss/harness/config.py` returns 1 match
    - default assertion: `python -c "from voss_runtime import get_config, reset_config; reset_config(); print(get_config().max_parallel_reads)"` prints `8`
    - range-fallback assertion: pytest test_max_parallel_reads_zero_warns + test_max_parallel_reads_33_warns + test_max_parallel_reads_100_warns all PASS (RuntimeWarning emitted, return value 8)
    - non-int-fallback assertion: pytest test_max_parallel_reads_string_warns + test_max_parallel_reads_empty_warns PASS
    - both-keys-roundtrip assertion: pytest test_both_agent_keys_roundtrip PASS
    - behavior assertion: all 13 pytest behaviors pass
    - regression assertion: `uv run pytest tests/harness/test_harness_config.py tests/harness/test_agent_config.py -x -q` passes (no T1/M1 harness-config regression)
    - test command: `uv run pytest tests/harness/test_agent_config.py -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>RuntimeConfig.max_parallel_reads field present; get_max_parallel_reads loader has 3 paths (missing→default silent, valid int→pass, out-of-range/non-int→default + RuntimeWarning); both max_iterations and max_parallel_reads round-trip from one [agent] block; 13 tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: cli.py bootstrap wires configure(max_parallel_reads=...) at startup</name>
  <files>voss/harness/cli.py, tests/harness/test_cli_bootstrap.py</files>
  <read_first>
    - .planning/phases/T2-parallel-tools-multi-edit/T2-SPEC.md (acceptance criterion 4 "default is 8 and is honored at runtime")
    - .planning/phases/T2-parallel-tools-multi-edit/T2-PATTERNS.md (section "Bootstrapping at cli.py boot")
    - voss/harness/cli.py (entire file; locate the existing configure() call added by T1-04 — `grep -n "configure(\|max_iterations" voss/harness/cli.py`)
    - voss/harness/config.py (just-written get_max_parallel_reads)
    - tests/harness/test_cli_bootstrap.py if it exists; otherwise create
  </read_first>
  <behavior>
    - After importing voss.harness.cli (which triggers the bootstrap), get_config().max_parallel_reads equals what get_max_parallel_reads() resolves to
    - When XDG_CONFIG_HOME points at a tmp_path with [agent] max_parallel_reads = "16", get_config().max_parallel_reads is 16 after cli import (in a subprocess to avoid singleton contamination)
    - When XDG_CONFIG_HOME points at a tmp_path with no config.toml, get_config().max_parallel_reads is 8 (default)
    - cli.py's bootstrap configure() call passes BOTH max_iterations and max_parallel_reads in a single configure() invocation (single source of truth for the singleton)
  </behavior>
  <action>
    Edit `voss/harness/cli.py`:

    Locate the T1-04 bootstrap line. It should look like:
    ```
    from voss_runtime import configure
    from voss.harness.config import get_max_iterations
    configure(max_iterations=get_max_iterations())
    ```

    Extend in place to:
    ```
    from voss_runtime import configure
    from voss.harness.config import get_max_iterations, get_max_parallel_reads
    configure(
        max_iterations=get_max_iterations(),
        max_parallel_reads=get_max_parallel_reads(),
    )
    ```

    If T1-04 has NOT yet shipped (no configure() call exists in cli.py),
    add the full block at the bootstrap location T1-04 was meant to use
    (typically near the top of cli.py after imports). Document in the
    SUMMARY that this plan absorbed the T1-04 bootstrap addition.

    Write `tests/harness/test_cli_bootstrap.py`. Use subprocess.run with a
    fresh Python interpreter to avoid RuntimeConfig singleton contamination
    across tests. Each subprocess:
    1. Sets XDG_CONFIG_HOME to a tmp_path
    2. Optionally writes config.toml with an [agent] section
    3. Imports voss.harness.cli to trigger bootstrap
    4. Prints `get_config().max_parallel_reads`
    5. Test asserts the printed value matches expectation

    Use `sys.executable` for the subprocess invocation and pass env via
    the env= kwarg. Example skeleton:
    ```
    import subprocess
    import sys

    def test_bootstrap_reads_config(tmp_path):
        cfg_dir = tmp_path / "voss"
        cfg_dir.mkdir()
        (cfg_dir / "config.toml").write_text('[agent]\nmax_parallel_reads = "16"\n')
        result = subprocess.run(
            [sys.executable, "-c",
             "import voss.harness.cli; from voss_runtime import get_config; print(get_config().max_parallel_reads)"],
            env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path)},
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "16"
    ```

    Note: if importing voss.harness.cli triggers click side effects that
    interfere with subprocess, switch the import target to whatever
    module/function actually runs the configure() call (likely a
    `_bootstrap_runtime_config()` helper or top-level statement). Read
    cli.py to find the exact bootstrap site.

    Do NOT modify any click command bodies or runtime behavior beyond
    the single configure() call extension.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_cli_bootstrap.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "configure\(.*max_parallel_reads" voss/harness/cli.py` returns >= 1 match
    - source assertion: `grep -n "get_max_parallel_reads" voss/harness/cli.py` returns >= 1 match (imported + called)
    - source assertion: cli.py has exactly one configure() call wiring both keys (avoid double-bootstrap) — `grep -cF "configure(" voss/harness/cli.py` <= existing-count + 0 (extend in place, don't add a second call)
    - subprocess assertion: pytest test_bootstrap_reads_config with [agent] max_parallel_reads = "16" prints "16"
    - default assertion: pytest test_bootstrap_default_no_config prints "8"
    - behavior assertion: all pytest tests pass
    - regression assertion: `uv run pytest tests/harness/ -k "cli or bootstrap or agent_config" -x -q` passes
    - test command: `uv run pytest tests/harness/test_cli_bootstrap.py -x -q`
    - CLI output: exit code 0
  </acceptance_criteria>
  <done>cli.py bootstrap extends configure() to include max_parallel_reads=get_max_parallel_reads() alongside max_iterations; subprocess tests confirm the singleton round-trips from on-disk config.toml; no double-configure regressions.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| on-disk config.toml → in-process RuntimeConfig singleton | User-editable TOML file at `~/.config/voss/config.toml` flows through regex parser into the singleton; malformed/out-of-range values must fall back safely rather than crash the agent |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T2-02-01 | Denial of Service | malformed [agent] max_parallel_reads value (huge int, negative, non-numeric) | mitigate | Range validation 1-32 inclusive + safe int parse; out-of-range and parse-failures fall back to default 8 with RuntimeWarning (no exception propagates to bootstrap; cli.py continues to start) |
| T-T2-02-02 | Tampering | config.toml editing race with bootstrap | accept | Config is read once at cli.py startup; mid-run edits do not affect the running session (existing M1 invariant; no new exposure) |
| T-T2-02-03 | Information Disclosure | RuntimeWarning content includes the offending value | accept | The warning includes `{raw!r}` for diagnosis; values here are integers, not secrets — no PII or credential leakage; mirrors T1-04 max_iterations warning shape |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_agent_config.py tests/harness/test_cli_bootstrap.py -x -q` passes
- `grep -n "max_parallel_reads" voss_runtime/_config.py` returns 1 match (field on RuntimeConfig)
- `grep -n "def get_max_parallel_reads" voss/harness/config.py` returns 1 match
- `grep -nE "configure\(.*max_parallel_reads" voss/harness/cli.py` returns >= 1 match
- Default behavior: no config.toml → `get_config().max_parallel_reads == 8`
- Override behavior: `[agent] max_parallel_reads = "16"` → `get_config().max_parallel_reads == 16`
- Out-of-range "0", "33", "100" → fall back to 8 with RuntimeWarning
- Non-int "foo", "" → fall back to 8 with RuntimeWarning
</verification>

<success_criteria>
- RuntimeConfig.max_parallel_reads field exists with default 8
- get_max_parallel_reads() loader validates range 1-32 + emits RuntimeWarning on fallback
- cli.py bootstrap wires both max_iterations and max_parallel_reads in a single configure() call
- 13 unit tests cover all valid/invalid value paths
- 2 subprocess tests prove the bootstrap actually configures the singleton end-to-end
</success_criteria>

<output>
Create `.planning/phases/T2-parallel-tools-multi-edit/T2-02-SUMMARY.md` when done with: exact line numbers of the new field + loader + bootstrap extension; pytest output showing all tests passing; subprocess-test output proving bootstrap roundtrip works.
</output>
