---
phase: M7-sdk-polish
plan: 04
type: execute
wave: 4
depends_on: []
files_modified:
  - voss_runtime/_config.py
autonomous: true
requirements:
  - SDK-04
must_haves:
  truths:
    - "`RuntimeConfig.from_toml(path)` reads the `[runtime]` section of the given TOML file and returns a NEW `RuntimeConfig` instance (does NOT mutate the module-level `_config` singleton)."
    - "`RuntimeConfig.from_toml(missing_path)` raises `FileNotFoundError` (loud per M1 D-13 / D-15)."
    - "`RuntimeConfig.default()` resolves dataclass-defaults → `~/.config/voss/config.toml` `[runtime]` overlay → env-var overlay; missing file is silent (D-16)."
    - "Env-var overlay coerces numeric fields via `int()` / `float()` with a clear error pointing at the offending env-var name when the cast fails (D-17)."
    - "Env-vars win over file values when both are present (D-16)."
    - "Unknown keys in the `[runtime]` TOML section emit a stderr warning but do not fail (D-18)."
    - "Existing `configure(**kwargs)`, `get_config()`, `reset_config()` are unchanged."
  artifacts:
    - path: "voss_runtime/_config.py"
      provides: "Two new classmethods on RuntimeConfig: from_toml, default"
      contains: "def from_toml"
    - path: "tests/test_config.py"
      provides: "Coverage for from_toml happy path, missing file, env overlay, unknown keys, bad coercion"
      contains: "def test_from_toml"
  key_links:
    - from: "RuntimeConfig.default"
      to: "~/.config/voss/config.toml"
      via: "Path.home() / '.config' / 'voss' / 'config.toml'"
      pattern: "config\\.toml"
    - from: "RuntimeConfig.default"
      to: "os.environ"
      via: "8 VOSS_* env-var names listed in D-16"
      pattern: "VOSS_"
---

<objective>
Add two classmethods to the existing `RuntimeConfig` dataclass in
`voss_runtime/_config.py`:

- `RuntimeConfig.from_toml(path: str | Path) -> RuntimeConfig` — reads
  the `[runtime]` section of a TOML file via `tomllib` (stdlib, Python
  3.11+) and returns a NEW instance. Raises `FileNotFoundError` on
  missing path (D-15). Warns on unknown keys (D-18). Does NOT touch
  the module-level `_config` singleton.
- `RuntimeConfig.default() -> RuntimeConfig` — resolves dataclass
  defaults → `~/.config/voss/config.toml` `[runtime]` overlay (silent
  if file missing) → env-var overlay. Env wins over file.

Purpose: Embedders currently must construct `RuntimeConfig` field-by-field
or call `configure(**kwargs)`. Closes the "Configuration via TOML" gap
from `docs/sdk.md` "Known gaps (closing in M7)". Closes SDK-04.

Output:
- `voss_runtime/_config.py` — two new classmethods (and necessary
  imports: `tomllib`, `os`, `Path`, `warnings`).
- `tests/test_config.py` — extended with from_toml + default coverage.

This is an additive plan: existing `RuntimeConfig`, `configure`,
`get_config`, `reset_config` are unchanged. No new dependency.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/M7-sdk-polish/M7-CONTEXT.md
@.planning/phases/M7-sdk-polish/M7-RESEARCH.md
@.planning/phases/M7-sdk-polish/M7-PATTERNS.md
@voss_runtime/_config.py

<interfaces>
Existing `RuntimeConfig` at `voss_runtime/_config.py:6-15` (do NOT
modify fields):
```python
@dataclass
class RuntimeConfig:
    default_model: str = "claude-sonnet-4-5"
    default_embedding_model: str = "text-embedding-3-small"
    local_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_retries: int = 1
    match_threshold: float = 0.75
    cache_dir: str = ".voss-cache"
    timeout_seconds: float = 60.0
    max_output_tokens: int = 4096
```

The 8 known field names form the whitelist for both TOML and env-var
overlays. Add new classmethods only — do not change any field types or
defaults.

Env-var mapping (per D-16): `VOSS_<UPPER_SNAKE>` mirrors the dataclass
field name:

| Field | Env-var | Cast |
|---|---|---|
| `default_model` | `VOSS_DEFAULT_MODEL` | `str` |
| `default_embedding_model` | `VOSS_DEFAULT_EMBEDDING_MODEL` | `str` |
| `local_embedding_model` | `VOSS_LOCAL_EMBEDDING_MODEL` | `str` |
| `max_retries` | `VOSS_MAX_RETRIES` | `int` |
| `match_threshold` | `VOSS_MATCH_THRESHOLD` | `float` |
| `cache_dir` | `VOSS_CACHE_DIR` | `str` |
| `timeout_seconds` | `VOSS_TIMEOUT_SECONDS` | `float` |
| `max_output_tokens` | `VOSS_MAX_OUTPUT_TOKENS` | `int` |

TOML shape example:
```toml
[runtime]
default_model = "gpt-4o"
max_retries = 3
match_threshold = 0.8
```

Reading via `tomllib.loads(path.read_text())`. The data structure is a
nested dict — `data.get("runtime", {})` returns the section dict (empty
dict when section is missing — handled without raising per D-14).

Pattern 4 (M7-PATTERNS.md): `dataclasses.replace(defaults, **overrides)`
is the canonical fluent idiom — already used at `_config.py:29` in the
existing `configure`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add RuntimeConfig.from_toml and RuntimeConfig.default classmethods + tests</name>
  <files>voss_runtime/_config.py, tests/test_config.py</files>
  <behavior>
    - `test_from_toml_happy_path`: write to `tmp_path/cfg.toml`:
      `[runtime]\ndefault_model = "gpt-4o"\nmax_retries = 3\nmatch_threshold = 0.8\n`.
      Call `RuntimeConfig.from_toml(tmp_path / "cfg.toml")`. Assert
      `.default_model == "gpt-4o"`, `.max_retries == 3`, `.match_threshold == 0.8`,
      `.timeout_seconds == 60.0` (default preserved for unset field).
    - `test_from_toml_returns_new_instance_not_singleton`: import
      `_config`, capture `before = _config._config`, call
      `RuntimeConfig.from_toml(...)`, assert `_config._config is before`
      (singleton untouched).
    - `test_from_toml_missing_section_returns_defaults`: write
      `tmp_path/cfg.toml` containing only `[harness]\npreferred_model = "x"\n`
      (no `[runtime]` section). Call `from_toml`. Assert returned
      instance equals `RuntimeConfig()` (all defaults).
    - `test_from_toml_missing_file_raises`: call `from_toml(tmp_path / "nope.toml")`,
      assert `FileNotFoundError` raised (D-15).
    - `test_from_toml_unknown_keys_warns_does_not_fail`: write
      `[runtime]\nunknown_key = "x"\ndefault_model = "ok"\n`. Call
      `from_toml`. Assert no exception; assert returned `.default_model == "ok"`;
      assert a warning (captured via `capsys` on stderr or via
      `warnings.catch_warnings`) mentions `unknown_key` (D-18).
    - `test_default_uses_dataclass_defaults_when_no_file_no_env`:
      monkeypatch `Path.home` to return `tmp_path` (so the home
      config.toml doesn't exist). Clear all `VOSS_*` env-vars via
      `monkeypatch.delenv`. Call `RuntimeConfig.default()`. Assert
      returned instance equals `RuntimeConfig()`.
    - `test_default_overlay_order_file_then_env`: under monkeypatched
      home, write `~/.config/voss/config.toml`
      (`tmp_path/.config/voss/config.toml`) with
      `[runtime]\ndefault_model = "from-file"\nmax_retries = 5\n`.
      Set `VOSS_MAX_RETRIES=9`. Call `default()`. Assert
      `.default_model == "from-file"` (from file, no env override) AND
      `.max_retries == 9` (env wins over file per D-16).
    - `test_default_env_coercion_int`: set `VOSS_MAX_OUTPUT_TOKENS="2048"`,
      assert `default().max_output_tokens == 2048` (int cast applied).
    - `test_default_env_coercion_float`: set `VOSS_TIMEOUT_SECONDS="30.5"`,
      assert `default().timeout_seconds == 30.5`.
    - `test_default_env_coercion_bad_value_raises`: set
      `VOSS_MAX_RETRIES="not_an_int"`. Call `default()`. Assert
      `ValueError` raised, and the error message contains
      `"VOSS_MAX_RETRIES"` (D-17 "clear error pointing at the offending
      env-var name").
    - `test_default_missing_file_is_silent`: under monkeypatched home
      with NO config.toml, NO `VOSS_*` env-vars, call `default()`.
      Assert no warning, no exception, returns defaults.
  </behavior>
  <action>
    Per D-14, D-15, D-16, D-17, D-18, R-05 (env coercion R-05 within
    research §Q5).

    Add to top of `voss_runtime/_config.py`:
    ```python
    import os
    import tomllib
    import warnings
    from pathlib import Path
    from dataclasses import dataclass, field, replace
    from threading import Lock
    ```
    (The file already has `os`, `replace`, `Lock`, `dataclass`, `field`
    — only add `tomllib`, `warnings`, `Path`. Preserve existing imports.)

    Define a module-level constant for the env-var mapping (or inline
    in the classmethod — Claude's discretion). Recommend a frozen tuple
    of `(field_name, env_var_name, cast)` triples for clarity:

    ```python
    _ENV_OVERLAY: tuple[tuple[str, str, type], ...] = (
        ("default_model", "VOSS_DEFAULT_MODEL", str),
        ("default_embedding_model", "VOSS_DEFAULT_EMBEDDING_MODEL", str),
        ("local_embedding_model", "VOSS_LOCAL_EMBEDDING_MODEL", str),
        ("max_retries", "VOSS_MAX_RETRIES", int),
        ("match_threshold", "VOSS_MATCH_THRESHOLD", float),
        ("cache_dir", "VOSS_CACHE_DIR", str),
        ("timeout_seconds", "VOSS_TIMEOUT_SECONDS", float),
        ("max_output_tokens", "VOSS_MAX_OUTPUT_TOKENS", int),
    )
    ```
    Keep `_ENV_OVERLAY` private (underscore prefix per cross-cutting
    constraint 3 — no new private surface introduced as a side effect).

    Implement as classmethods on `RuntimeConfig`:

    `from_toml(cls, path)`:
    1. `p = Path(path)`. If `not p.exists()`: raise `FileNotFoundError(f"runtime config not found: {p}")`.
    2. `data = tomllib.loads(p.read_text())`.
    3. `section = data.get("runtime", {})`. If not a dict, raise
       `ValueError(f"[runtime] section in {p} must be a table")`.
    4. Compute the set of known field names from
       `{f.name for f in dataclasses.fields(cls)}`. For each key in
       `section` not in that set, emit
       `warnings.warn(f"unknown key in [runtime] section of {p}: {key}")`
       (stderr via standard warnings module — pytest's `recwarn`
       fixture catches these).
    5. Build `kwargs = {k: v for k, v in section.items() if k in known}`.
    6. Return `replace(cls(), **kwargs)`.

    `default(cls)`:
    1. `base = cls()` (dataclass defaults).
    2. File overlay: `home_cfg = Path.home() / ".config" / "voss" / "config.toml"`.
       If `home_cfg.exists()`: load via `cls.from_toml(home_cfg)` and
       use that as the new base. (Reuses the unknown-key warning path.)
       If file missing: silent, keep `base` (D-16).
    3. Env overlay: for each `(field_name, env_var, cast)` in
       `_ENV_OVERLAY`, if `env_var in os.environ`: try `value = cast(os.environ[env_var])`,
       catching `ValueError` and re-raising with a friendlier message:
       `raise ValueError(f"{env_var}={os.environ[env_var]!r} is not a valid {cast.__name__}") from None`
       (per D-17 + R-05). Collect into an `env_kwargs` dict.
    4. Return `replace(base, **env_kwargs)` (env wins over file).

    Decorate both methods with `@classmethod`. Add concise docstrings
    pointing at the env-var table and the resolution order.

    Extend `tests/test_config.py` with the 11 behavior bullets above.
    Use `monkeypatch` (pytest builtin) for `os.environ` and
    `pathlib.Path.home` manipulation. Use `tmp_path` for the TOML file
    fixtures. Use `pytest.warns(UserWarning)` for the unknown-keys
    warning assertion. For the singleton non-mutation test, import
    `voss_runtime._config as cfg_mod` and inspect `cfg_mod._config`
    identity before/after.
  </action>
  <verify>
    <automated>pytest tests/test_config.py -x -q</automated>
  </verify>
  <done>
    `tests/test_config.py` passes all 11 new tests plus all existing
    tests in that file. `RuntimeConfig.from_toml` raises on missing
    file. `RuntimeConfig.default` is silent on missing home config.
    Env-var coercion errors name the offending variable. The module
    `_config` singleton is never mutated by either classmethod.
  </done>
</task>

</tasks>

<verification>
- `pytest tests/test_config.py -x` passes.
- `python -c "from voss_runtime import RuntimeConfig; print(RuntimeConfig.default().default_model)"` prints the default model name (no exception, no warnings on stderr in a clean env).
- `VOSS_MAX_RETRIES=oops python -c "from voss_runtime import RuntimeConfig; RuntimeConfig.default()"` exits with `ValueError` mentioning `VOSS_MAX_RETRIES`.
- Manual grep: `grep -E "^    (from_toml|default)" voss_runtime/_config.py | grep -c "classmethod\|def" >= 2` (presence check).
- Manual grep: `grep -c "^import tomllib" voss_runtime/_config.py` returns `1`.
- No changes to `_config = RuntimeConfig()` / `_lock = Lock()` module-level state.
- No changes to `configure`, `get_config`, `reset_config`.
</verification>

<success_criteria>
- `RuntimeConfig.from_toml(path)` reads `[runtime]` section via `tomllib`, raises `FileNotFoundError` on missing path, warns on unknown keys, never mutates the singleton.
- `RuntimeConfig.default()` resolves defaults → home TOML (silent if missing) → env overlay, with env winning over file.
- Env-var coercion raises a friendly `ValueError` naming the offending env-var.
- 8 env-vars supported, one per dataclass field, matching `VOSS_<UPPER_SNAKE>` naming.
- No changes to `RuntimeConfig` fields or to `configure` / `get_config` / `reset_config`.
- `voss_runtime/__init__.py` already exports `RuntimeConfig` — no `__all__` change needed in this plan (the classmethod additions are reachable through the existing export).
- No changes to `tests/packaging/test_public_api.py` (Wave 6 / M7-06).
- No changes to `docs/sdk.md` (Wave 6 / M7-06).
</success_criteria>

<output>
After completion, create `.planning/phases/M7-sdk-polish/M7-04-SUMMARY.md`
documenting the env-var mapping table, the resolution order
(defaults → file → env), and the 11 test cases.
</output>
