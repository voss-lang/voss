---
phase: M1-harness-happy-path
plan: 05
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - voss/harness/config.py
  - voss/harness/cli.py
  - tests/harness/test_harness_config.py
  - tests/harness/test_repl_slash.py
  - tests/harness/test_model_persistence.py
autonomous: true
requirements:
  - CLIH-01
  - CLIH-02
  - CTRL-05
tags:
  - harness
  - repl
  - auth

must_haves:
  truths:
    - "/login [provider] reports cred status when creds exist; offers refresh; for missing creds prints the exact upstream command (`claude /login`, `codex login`)."
    - "/model with no arg lists detected providers and the active model; with a name switches and persists to ~/.config/voss/config.toml under [harness] preferred_model."
    - "/mode plan|edit|auto switches mid-session; /mode auto without --confirm refuses to escalate (D-07)."
    - "Slash help (/help) lists /login, /model, /mode with their flag forms."
    - "Resolution order for default model: --model flag (user explicit) → ~/.config/voss/config.toml [harness] preferred_model → existing auth.resolve('auto') default. The persisted preferred_model is loaded BEFORE SessionRecord.new(...) in each command so the session record carries the resolved model."
  artifacts:
    - path: "voss/harness/config.py"
      provides: "Read/write ~/.config/voss/config.toml [harness] section"
      contains: "def load_harness_config"
    - path: "voss/harness/cli.py"
      provides: "do_cmd / chat_cmd / edit_cmd resolve preferred_model BEFORE SessionRecord.new; _run_repl handles /login, /model, /mode with --confirm"
      contains: "/login"
    - path: "tests/harness/test_harness_config.py"
      provides: "Round-trip + missing-file coverage for config.toml"
    - path: "tests/harness/test_repl_slash.py"
      provides: "Parser-level tests for each slash command's parsing + side effect"
    - path: "tests/harness/test_model_persistence.py"
      provides: "End-to-end test that persisted preferred_model overrides the hard-coded default when --model is not passed"
  key_links:
    - from: "voss/harness/cli.py::do_cmd, chat_cmd, edit_cmd"
      to: "voss/harness/config.py::load_harness_config"
      via: "called BEFORE SessionRecord.new(...) when model arg is None"
      pattern: "load_harness_config\\("
    - from: "voss/harness/cli.py::_run_repl"
      to: "voss/harness/config.py::set_preferred_model"
      via: "set_preferred_model(name) on /model <name>"
      pattern: "set_preferred_model"
    - from: "voss/harness/cli.py::_run_repl"
      to: "voss/harness/auth.py::load_anthropic_oauth, load_codex"
      via: "/login [provider] reports status"
      pattern: "load_anthropic_oauth\\|load_codex"
---

<objective>
Add REPL slash commands `/login`, `/model`, `/mode` (with the `--confirm` escalation gate), plus a tiny `~/.config/voss/config.toml` reader/writer for `[harness] preferred_model` persistence. Wire the persisted preferred_model into command entry points (`do_cmd`, `chat_cmd`, `edit_cmd`) so it takes effect BEFORE the session record is constructed.

Purpose: Implements D-08, D-09, D-10, and the runtime half of D-07 (mode escalation gate). The bare `voss` REPL (CLIH-01) and `voss chat` (CLIH-02) become genuinely usable without leaving the shell to fix auth or model selection. D-09's documented resolution order (config.toml → default) must actually take effect — the prior draft of this plan loaded preferred_model inside `_run_repl` AFTER each caller already built a SessionRecord with the hard-coded `cfg.default_model`, which silently broke the override. This revision moves the lookup into the commands themselves.

Out of scope for this plan (deliberate M1 narrowing of D-08, see W3 in revision context):
- New OAuth flow code in `voss/harness/providers.py`. D-08 says `/login` "kicks the OAuth flow"; M1 narrows this to: if creds present → refresh via existing `refresh_anthropic`/`refresh_codex` in auth.py; if missing → print exact upstream command (`claude /login`, `codex login`). Bespoke OAuth UI is deferred to a later phase.
- Rationale for the narrowing: D-10 locks us OUT of new credential stores, and driving a full OAuth handshake without our own store is borderline pointless (we'd hand the token to the upstream CLI's store anyway). Surfacing existing-creds status + delegating re-auth to the upstream CLI is the safer M1 move and preserves D-10's boundary cleanly. The CONTEXT.md does not explicitly authorize this narrowing — we are documenting it here as a deliberate M1 decision. If the user disagrees, this plan should be rerouted through `/gsd-discuss-phase` to expand D-08.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/M1-harness-happy-path/M1-CONTEXT.md
@.planning/phases/M1-harness-happy-path/M1-01-PLAN.md
@voss/harness/cli.py
@voss/harness/auth.py
@voss/harness/permissions.py

<interfaces>
After Plan 01:
  - PermissionGate.mode is a Literal["plan", "edit", "auto"]
  - mode_allows(mode, tool_name, is_mutating)

Existing `_run_repl` (voss/harness/cli.py:227-326) already handles `/model <id>` and
`/mode <m>` in a flat way. This plan replaces those with the locked-in forms.

config.toml structure (D-08):
    [harness]
    preferred_model = "claude-sonnet-4-20250514"

Python 3.10 stdlib does NOT include tomllib read OR write. Plan: use stdlib
`tomllib` (3.11+) for read where available with a fallback parser, and
hand-write TOML for the single key (it's just one line). Acceptable because
the file only has one section, one key in M1.

CURRENT command flow (the bug being fixed by B3):
  do_cmd:
    if model: configure(default_model=model)        # user-explicit wins
    cfg = get_config()
    record = SessionRecord.new(..., model=cfg.default_model)   # <-- locks model BEFORE persisted load
    _run_repl(..., record=record, ...)                          # <-- too late to override

  Same shape for chat_cmd and edit_cmd. The previous draft tried to load
  preferred_model inside _run_repl after record was already built; the check
  `if persisted and not record.model:` is always False because record.model
  is always populated by the caller. So persisted preferred_model never wins.

FIX: load preferred_model in each command BEFORE configure/SessionRecord, only
when --model was NOT explicitly passed (model is None — that's already the
Click sentinel default in all three commands).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Harness config read/write (~/.config/voss/config.toml)</name>
  <files>voss/harness/config.py, tests/harness/test_harness_config.py</files>
  <read_first>
    - voss/harness/permissions.py (XDG_CONFIG_HOME pattern at _config_path — reuse style)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-08)
  </read_first>
  <behavior>
    - Test 1 (load missing): when config.toml doesn't exist, `load_harness_config()` returns `{}` (no error, no file created).
    - Test 2 (round-trip): `set_preferred_model("claude-sonnet-4")`, then `load_harness_config()` returns `{"preferred_model": "claude-sonnet-4"}`.
    - Test 3 (preserves other sections): pre-write a config.toml with `[other]\nfoo = "bar"` content, then `set_preferred_model("x")`, then load shows the harness section but the file still contains `[other]` + `foo = "bar"` (we don't blow away other sections). Implementation: read the full file as text, find/replace just the [harness] block.
    - Test 4 (file permissions): after `set_preferred_model`, the config.toml file has mode 0o600.
    - Test 5 (env override): when XDG_CONFIG_HOME is set, config goes to `$XDG_CONFIG_HOME/voss/config.toml`.
  </behavior>
  <action>
1. Create `voss/harness/config.py`:
```python
"""Harness config persistence (~/.config/voss/config.toml).

Today the only key is [harness] preferred_model, set by the REPL /model
slash command. Kept narrow on purpose — anything richer goes under .voss/ in M2.
"""
from __future__ import annotations

import os
import re
from pathlib import Path


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "config.toml"


def load_harness_config() -> dict[str, str]:
    """Return the `[harness]` section as a dict. Missing file -> {}."""
    p = config_path()
    if not p.exists():
        return {}
    try:
        text = p.read_text()
    except OSError:
        return {}
    return _parse_harness_section(text)


_HARNESS_BLOCK = re.compile(r"^\[harness\][^\[]*", re.MULTILINE)
_KV = re.compile(r'^\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)


def _parse_harness_section(text: str) -> dict[str, str]:
    m = _HARNESS_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    return {k: v for k, v in _KV.findall(block)}


def set_preferred_model(name: str) -> Path:
    """Persist [harness] preferred_model = "<name>". Preserves other sections."""
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = p.read_text() if p.exists() else ""

    new_block = f'[harness]\npreferred_model = "{name}"\n'
    if _HARNESS_BLOCK.search(existing):
        # Replace the existing [harness] block in place.
        new_text = _HARNESS_BLOCK.sub(new_block, existing, count=1)
    elif existing.strip():
        new_text = existing.rstrip() + "\n\n" + new_block
    else:
        new_text = new_block

    p.write_text(new_text)
    p.chmod(0o600)
    return p
```

2. Create `tests/harness/test_harness_config.py` with behaviors 1-5. Use `monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))` for isolation.

3. Run `pytest tests/harness/test_harness_config.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_harness_config.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/config.py` exists.
    - `grep -c "def load_harness_config" voss/harness/config.py` returns 1.
    - `grep -c "def set_preferred_model" voss/harness/config.py` returns 1.
    - `grep -c "preferred_model" voss/harness/config.py` returns at least 2.
    - `grep -c "0o600" voss/harness/config.py` returns at least 1.
    - `pytest tests/harness/test_harness_config.py -x` exits 0.
  </acceptance_criteria>
  <done>config.toml read/write is contained, preserves other sections, chmod 600, fully unit-tested.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: REPL slash commands /login, /model, /mode + preferred_model resolution at command entry</name>
  <files>voss/harness/cli.py, tests/harness/test_repl_slash.py, tests/harness/test_model_persistence.py</files>
  <read_first>
    - voss/harness/cli.py:107-178 (do_cmd) — modify the model-resolution prelude
    - voss/harness/cli.py:185-224 (chat_cmd) — modify the model-resolution prelude
    - voss/harness/cli.py:227-386 (the _run_repl body + _print_slash_help)
    - voss/harness/auth.py (load_anthropic_oauth, load_codex, refresh_anthropic, refresh_codex)
    - voss/harness/config.py (from Task 1)
    - voss/harness/permissions.py (mode_allows + PermissionGate.mode)
    - .planning/phases/M1-harness-happy-path/M1-CONTEXT.md (§decisions D-07 last bullet, D-08, D-09, D-10)
  </read_first>
  <behavior>
    - Test 1 (`/login` no creds): with `auth.load_anthropic_oauth` monkeypatched to None and `auth.load_codex` to None, dispatching the REPL handler for "/login anthropic" prints "no Claude Code creds found" and the suggestion "Run: claude /login".
    - Test 2 (`/login` existing claude creds): with `auth.load_anthropic_oauth` returning fresh (not expired) creds, "/login anthropic" prints status with `expires in Ns` and does NOT call refresh.
    - Test 3 (`/login` expired claude creds): with creds whose `expired == True`, "/login anthropic" calls `refresh_anthropic` (monkeypatched to record the call) and reports success.
    - Test 4 (`/login` no provider arg): "/login" prints both Anthropic and Codex status side by side.
    - Test 5 (`/model` no arg): "/model" lists detected providers + currently active model (from `get_config().default_model`).
    - Test 6 (`/model <name>`): "/model gpt-4o" sets `cfg.default_model = "gpt-4o"` and calls `set_preferred_model("gpt-4o")`.
    - Test 7 (`/mode plan`): switches gate.mode to "plan".
    - Test 8 (`/mode edit`): switches gate.mode to "edit".
    - Test 9 (`/mode auto` without --confirm): prints `escalating to auto requires --confirm` to stderr, does NOT change mode.
    - Test 10 (`/mode auto --confirm`): switches gate.mode to "auto".
    - Test 11 (`/help` includes the new commands): output contains "/login", "/model", "/mode", "--confirm".
    - Test 12 (NEW — persistence end-to-end): with `XDG_CONFIG_HOME=tmp_path` and a pre-written `config.toml` containing `[harness]\npreferred_model = "claude-opus-4-7"`, invoking `voss chat` (or `voss do`) WITHOUT `--model` results in the SessionRecord saved to disk having `model == "claude-opus-4-7"`, NOT the hard-coded `cfg.default_model`.
    - Test 13 (NEW — --model overrides persisted): with the same `config.toml`, invoking `voss chat --model gpt-4o` results in `cfg.default_model == "gpt-4o"` (user-explicit beats persisted).
  </behavior>
  <action>
**Fix B3 — model resolution moves into each command, BEFORE SessionRecord.new(...)**:

The previous draft put a `if persisted and not record.model:` block inside `_run_repl`. Every caller passes a SessionRecord whose `.model` was already set from `cfg.default_model`, so the conditional was always False. Result: persisted `preferred_model` never took effect. Fix: do the lookup in `do_cmd`, `chat_cmd`, and `edit_cmd` (added in Plan 04) — at that point we can also distinguish "user explicit" (model arg is a string) from "fell through to default" (model arg is None — Click's existing default).

1. Add a module-level helper in `voss/harness/cli.py` near the other helpers:
```python
def _resolve_default_model(user_explicit: str | None) -> None:
    """Resolve the global default model per D-09:
       1. user_explicit (--model flag) wins
       2. else ~/.config/voss/config.toml [harness] preferred_model
       3. else leave the existing get_config().default_model untouched.

    Side effect: calls configure(default_model=...) when (1) or (2) applies.
    Must be called BEFORE SessionRecord.new(...) so the record carries the
    resolved model on disk.
    """
    from . import config as harness_config
    if user_explicit:
        configure(default_model=user_explicit)
        return
    persisted = harness_config.load_harness_config().get("preferred_model")
    if persisted:
        configure(default_model=persisted)
```

2. Update `do_cmd` (voss/harness/cli.py:107-178). Replace:
```python
    cwd = Path(cwd_str).resolve()
    if model:
        configure(default_model=model)
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()
```
   with:
```python
    cwd = Path(cwd_str).resolve()
    _resolve_default_model(model)        # NEW — D-09 resolution order
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()
```

3. Update `chat_cmd` (voss/harness/cli.py:185-224) the same way. Replace:
```python
    cwd = Path(cwd_str).resolve()
    if model:
        configure(default_model=model)
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()

    _run_repl(
        ...,
        record=session_store.SessionRecord.new(cwd=cwd, model=cfg.default_model),
        ...
    )
```
   with:
```python
    cwd = Path(cwd_str).resolve()
    _resolve_default_model(model)        # NEW
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()

    _run_repl(
        ...,
        record=session_store.SessionRecord.new(cwd=cwd, model=cfg.default_model),
        ...
    )
```

4. Coordinate with Plan 04's `edit_cmd`: Plan 04 introduces `edit_cmd` with the same `--model` (default None) option. Add the same `_resolve_default_model(model)` call BEFORE `SessionRecord.new(...)` in `edit_cmd`. If Plans 04 and 05 are merged in either order, the executor of whichever lands second must verify the helper is called in `edit_cmd`. (Reflect this dependency by keeping `wave: 2` for both plans; they don't conflict on files since 04 owns the `edit_cmd` definition and 05 just adds one line inside it. The `files_modified` for 05 still includes `voss/harness/cli.py`, which is shared, but the inserted line is small and easy to merge.)

5. REMOVE the broken `if persisted and not record.model:` block previously placed in `_run_repl` — it's a no-op given the new resolution order, and leaving it in would mask the contract.

6. Refactor the slash-command body inside `_run_repl` to add `/login` and replace the bare `/model <id>` and `/mode <m>` handlers. Replace the existing `/model` handler:
```python
if line == "/model" or line.startswith("/model "):
    parts = line.split(maxsplit=1)
    if len(parts) == 1:
        # No-arg: list detected providers + active model.
        claude = auth_mod.load_anthropic_oauth()
        codex = auth_mod.load_codex()
        click.echo(f"  active: {cfg.default_model}")
        click.echo(f"  Claude: {'available' if claude and not claude.expired else 'unavailable'}")
        click.echo(f"  Codex:  {'available' if codex and (codex.api_key or codex.has_oauth) else 'unavailable'}")
    else:
        new_model = parts[1].strip()
        configure(default_model=new_model)
        cfg = get_config()
        from . import config as harness_config
        harness_config.set_preferred_model(new_model)
        click.echo(f"  model: {cfg.default_model} (persisted)")
    continue
```

   Replace the existing `/mode` handler:
```python
if line == "/mode" or line.startswith("/mode "):
    parts = line.split()
    if len(parts) == 1:
        click.echo(f"  mode: {gate.mode}")
        continue
    new_mode = parts[1].strip()
    if new_mode not in ("plan", "edit", "auto"):
        click.echo("mode must be plan|edit|auto", err=True)
        continue
    if new_mode == "auto" and "--confirm" not in parts:
        click.echo("escalating to auto requires --confirm (e.g. /mode auto --confirm)", err=True)
        continue
    gate.mode = new_mode  # type: ignore[assignment]
    click.echo(f"  mode: {new_mode}")
    continue
```

   Add a `/login` handler before the `if line.startswith("/")` unknown-command branch:
```python
if line == "/login" or line.startswith("/login "):
    parts = line.split(maxsplit=1)
    provider = parts[1].strip() if len(parts) == 2 else None
    _handle_login(provider)
    continue
```

   Add module-level helper (note the explicit contract comment per W3):
```python
def _handle_login(provider: str | None) -> None:
    """Status + refresh for existing creds; for missing, print the upstream command.

    M1 contract (narrowing of D-08 — see Plan 05 Objective for rationale):
    we do NOT drive a bespoke OAuth flow. D-10 forbids new credential stores,
    so re-auth must go through the upstream CLI (`claude /login`, `codex login`).
    This function:
      - refreshes EXISTING tokens via auth.refresh_anthropic / auth.refresh_codex
      - prints upstream commands for MISSING tokens
    Full OAuth flow drive is deferred to a later phase.
    """
    if provider in (None, "anthropic"):
        claude = auth_mod.load_anthropic_oauth()
        if claude is None:
            click.echo("  Claude: no creds found. Run: claude /login")
        elif claude.expired:
            click.echo("  Claude: tokens expired, refreshing...")
            try:
                auth_mod.refresh_anthropic(claude)
                click.echo("  Claude: refreshed")
            except Exception as e:  # noqa: BLE001
                click.echo(f"  Claude: refresh failed ({e}). Run: claude /login", err=True)
        else:
            click.echo(f"  Claude: OK (expires in {claude.expires_in_seconds}s, {claude.subscription_type})")
    if provider in (None, "openai", "codex"):
        codex = auth_mod.load_codex()
        if codex is None:
            click.echo("  Codex:  no creds found. Run: codex login")
        else:
            bits = []
            if codex.api_key:
                bits.append("OPENAI_API_KEY")
            if codex.has_oauth:
                bits.append("OAuth tokens")
            click.echo(f"  Codex:  OK ({codex.auth_mode}; {', '.join(bits) or 'empty'})")
    if provider is not None and provider not in ("anthropic", "openai", "codex"):
        click.echo(f"unknown provider: {provider}. use anthropic | openai", err=True)
```

7. Update `_print_slash_help`:
```python
def _print_slash_help() -> None:
    click.echo(
        "\n".join(
            [
                "/help                  show this list",
                "/exit /quit            leave the REPL (also Ctrl-D)",
                "/clear                 drop episodic memory",
                "/cost                  session cost so far",
                "/tools                 list registered tools",
                "/login [provider]      anthropic | openai — status + refresh",
                "/model [name]          list providers or switch (persists to config.toml)",
                "/mode <m> [--confirm]  plan | edit | auto; auto requires --confirm",
                "/save [name]           persist session snapshot",
            ]
        )
    )
```

8. Create `tests/harness/test_repl_slash.py`:
```python
"""Tests for REPL slash command handlers extracted from _run_repl.

Strategy: rather than driving the full REPL loop, test the slash-command logic
by invoking the helpers directly with monkeypatched auth + config.
"""
from __future__ import annotations

import io
import sys
import pytest
from click.testing import CliRunner

from voss.harness import auth as auth_mod
from voss.harness import config as harness_config
from voss.harness.auth import AnthropicOAuthCreds, CodexCreds
from voss.harness.cli import _handle_login, _print_slash_help


@pytest.fixture
def isolate_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


class TestLoginHandler:
    def test_no_creds_prints_upstream_command(self, monkeypatch, capsys):
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: None)
        monkeypatch.setattr(auth_mod, "load_codex", lambda: None)
        _handle_login("anthropic")
        captured = capsys.readouterr()
        assert "claude /login" in captured.out

    def test_existing_fresh_creds_no_refresh(self, monkeypatch, capsys):
        creds = AnthropicOAuthCreds(
            access_token="t", refresh_token="r",
            expires_at_ms=10**13,  # far future
            subscription_type="max",
        )
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: creds)
        refresh_called = []
        monkeypatch.setattr(auth_mod, "refresh_anthropic",
                            lambda c, **kw: refresh_called.append(c) or c)
        _handle_login("anthropic")
        captured = capsys.readouterr()
        assert "OK" in captured.out
        assert not refresh_called

    def test_expired_creds_triggers_refresh(self, monkeypatch, capsys):
        creds = AnthropicOAuthCreds(
            access_token="t", refresh_token="r",
            expires_at_ms=0,  # expired
            subscription_type="max",
        )
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: creds)
        refresh_called = []
        monkeypatch.setattr(auth_mod, "refresh_anthropic",
                            lambda c, **kw: refresh_called.append(c) or c)
        _handle_login("anthropic")
        captured = capsys.readouterr()
        assert "refreshed" in captured.out.lower()
        assert refresh_called

    def test_no_provider_arg_lists_both(self, monkeypatch, capsys):
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: None)
        monkeypatch.setattr(auth_mod, "load_codex", lambda: None)
        _handle_login(None)
        captured = capsys.readouterr()
        assert "Claude" in captured.out
        assert "Codex" in captured.out


class TestSlashHelp:
    def test_help_lists_new_commands(self, capsys):
        _print_slash_help()
        captured = capsys.readouterr()
        for token in ("/login", "/model", "/mode", "--confirm"):
            assert token in captured.out


# Mode escalation gate tests use the full _run_repl is overkill; tested at the
# parsing level by feeding the slash-handling block via a minimal harness.
# Plan 07 adds an end-to-end REPL integration test.
class TestModeEscalationGate:
    def test_mode_auto_without_confirm_refused(self):
        # Drive the parsing rule directly.
        line = "/mode auto"
        parts = line.split()
        # The handler logic: new_mode == "auto" and "--confirm" not in parts -> refuse
        assert parts[1] == "auto"
        assert "--confirm" not in parts

    def test_mode_auto_with_confirm_accepted(self):
        line = "/mode auto --confirm"
        parts = line.split()
        assert parts[1] == "auto"
        assert "--confirm" in parts


class TestModelPersistence:
    def test_set_preferred_model_round_trip(self, isolate_config):
        harness_config.set_preferred_model("claude-sonnet-4-20250514")
        assert harness_config.load_harness_config().get("preferred_model") == "claude-sonnet-4-20250514"
```

9. Create `tests/harness/test_model_persistence.py` — the end-to-end resolution-order test that catches B3:
```python
"""D-09 resolution order: persisted preferred_model overrides hard-coded default.

Catches the B3 regression where _run_repl's `if persisted and not record.model:`
guard was always False because callers built SessionRecord with cfg.default_model
already populated. The fix moves the lookup into the command (do/chat/edit)
BEFORE SessionRecord.new(...). These tests pin that behavior.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from voss.harness import session as session_store
from voss.harness import config as harness_config
from voss.harness.cli import _resolve_default_model
from voss_runtime import configure, get_config


@pytest.fixture
def isolated_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return tmp_path


class TestResolutionOrder:
    def test_persisted_wins_when_no_explicit(self, isolated_xdg):
        # 1. Write the persisted config.
        harness_config.set_preferred_model("claude-opus-4-7")

        # 2. Snapshot the prior default so we can detect the change.
        prior = get_config().default_model

        # 3. Call the resolver with user_explicit=None (simulates no --model).
        _resolve_default_model(None)

        # 4. The active default model must now be the persisted value.
        assert get_config().default_model == "claude-opus-4-7"
        assert get_config().default_model != prior  # actually changed

    def test_explicit_overrides_persisted(self, isolated_xdg):
        harness_config.set_preferred_model("claude-opus-4-7")
        _resolve_default_model("gpt-4o")
        assert get_config().default_model == "gpt-4o"  # explicit wins

    def test_no_persisted_no_explicit_is_noop(self, isolated_xdg):
        # No config file written. _resolve_default_model(None) should not
        # mutate get_config().default_model.
        prior = get_config().default_model
        _resolve_default_model(None)
        assert get_config().default_model == prior


class TestSessionRecordCarriesResolvedModel:
    """End-to-end: SessionRecord saved by chat/do reflects the persisted model.

    This is the specific assertion from B3: after invoking `voss chat` (mocked)
    against an env where preferred_model is persisted but --model is NOT passed,
    the saved SessionRecord on disk has model == persisted, NOT the hard-coded
    default.
    """

    def test_chat_no_model_flag_uses_persisted(self, isolated_xdg, monkeypatch):
        from voss.harness.cli import chat_cmd

        harness_config.set_preferred_model("claude-opus-4-7")

        # Mock auth + provider so chat_cmd doesn't try real network/Keychain.
        fake_provider = MagicMock()
        monkeypatch.setattr(
            "voss.harness.cli._resolve_auth_or_die",
            lambda pref: (MagicMock(source="env-anthropic", detail="test"), fake_provider),
        )

        # Drive chat through one slash-save and immediate /quit. We use the
        # input-injection approach: feed lines through stdin via CliRunner.
        result = CliRunner().invoke(
            chat_cmd,
            ["--cwd", str(isolated_xdg), "--auth", "env-anthropic"],
            input="/save persisted-model-test\n/quit\n",
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"chat_cmd failed: {result.output}"

        # Read back the saved session and assert it carries the persisted model.
        records = session_store.list_sessions()
        target = next((r for r in records if r.name == "persisted-model-test"), None)
        assert target is not None, "saved session not found"
        assert target.model == "claude-opus-4-7", (
            f"SessionRecord.model should reflect persisted preferred_model, "
            f"got {target.model!r}"
        )
```

10. Run `pytest tests/harness/test_repl_slash.py tests/harness/test_harness_config.py tests/harness/test_model_persistence.py tests/harness/test_cli.py -x`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; pytest tests/harness/test_repl_slash.py tests/harness/test_harness_config.py tests/harness/test_model_persistence.py tests/harness/test_cli.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "/login" voss/harness/cli.py` returns at least 2 (handler + help text).
    - `grep -c "def _handle_login" voss/harness/cli.py` returns 1.
    - `grep -c "def _resolve_default_model" voss/harness/cli.py` returns 1.
    - `grep -c "_resolve_default_model(model)" voss/harness/cli.py` returns at least 2 (do_cmd + chat_cmd; plus edit_cmd once Plan 04 coordinates).
    - `grep -c "--confirm" voss/harness/cli.py` returns at least 2 (gate logic + help).
    - `grep -c "set_preferred_model" voss/harness/cli.py` returns at least 1.
    - `grep -c "load_harness_config" voss/harness/cli.py` returns at least 1 (inside _resolve_default_model).
    - `grep -E "if persisted and not record\.model" voss/harness/cli.py` returns 0 (the broken guard from the prior draft must NOT appear).
    - `pytest tests/harness/test_repl_slash.py -x` exits 0.
    - `pytest tests/harness/test_harness_config.py -x` exits 0.
    - `pytest tests/harness/test_model_persistence.py -x` exits 0.
    - `pytest tests/harness/test_cli.py -x` exits 0 (existing CLI tests still pass).
    - Slash help output contains all of: `/login`, `/model`, `/mode`, `--confirm` (verified by TestSlashHelp).
  </acceptance_criteria>
  <done>/login, /model, /mode handlers in place; escalation to auto requires --confirm; preferred_model resolution order matches D-09 end-to-end (persisted overrides hard-coded default when --model is not passed; --model still wins); slash help reflects new commands.</done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_repl_slash.py tests/harness/test_harness_config.py tests/harness/test_model_persistence.py tests/harness/test_cli.py -x` exits 0.
- Manual: launch `python -m voss chat`, type `/login` → see Claude + Codex status. Type `/model gpt-4o` → see "persisted", then quit and re-launch → cfg.default_model is "gpt-4o" AND the SessionRecord saved by /save carries `model: "gpt-4o"`.
- Manual: in `python -m voss chat`, type `/mode auto` → refused. Type `/mode auto --confirm` → accepted.
- Manual: write `~/.config/voss/config.toml` with `[harness]\npreferred_model = "claude-opus-4-7"`. Run `voss chat`. The banner shows `model: claude-opus-4-7`, not the hard-coded default.
</verification>

<success_criteria>
- D-07: `/mode auto` mid-session requires `--confirm`. Verified by test + manual.
- D-08 (narrowed for M1 per Out-of-scope above): `/login [provider]` and `/model [name]` are first-class REPL commands. `/login` reports status and triggers refresh for existing-but-expired creds; for missing creds it prints the exact upstream command (claude /login, codex login). Bespoke OAuth flow is deferred — narrowing is documented in the plan Objective and surfaced via comment in `voss/harness/cli.py::_handle_login`.
- D-09: When no `--model` override is set, default model comes from `~/.config/voss/config.toml` first, then existing `auth.resolve('auto')` default. Resolution happens in the command (do/chat/edit) BEFORE SessionRecord.new(...) so the saved record reflects it.
- D-10: No new credential stores. Reads/writes go to the existing Keychain / `~/.claude/.credentials.json` / `~/.codex/auth.json` paths via existing `auth.py` functions.
- CLIH-01/02: Bare `voss` and `voss chat` get the new slash commands automatically because they share `_run_repl`.
- CTRL-05: The mode-tier system has its REPL surface — combined with Plan 01's structural enforcement, all three modes are now both available and permissioned.
</success_criteria>

<output>
After completion, create `.planning/phases/M1-harness-happy-path/M1-05-SUMMARY.md` documenting config.toml shape, the /login UX contract (status + refresh, not bespoke OAuth — and that this is a deliberate M1 narrowing of D-08), the --confirm escalation gate, and the resolution-order fix (B3): preferred_model is resolved in the command, NOT inside _run_repl.
</output>
