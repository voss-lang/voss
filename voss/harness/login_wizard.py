"""Interactive login wizard for first-run / `/login` flows.

Wraps upstream credential CLIs (`claude`, `codex`) rather than driving OAuth
directly — see D-10. Surfaces three credential paths:

  1. Claude Code OAuth — spawns `claude` so the user can run `/login` inside
     it, then polls `~/.claude/.credentials.json` (via auth.wait_for_creds).
  2. Codex OAuth — runs `codex login`, then polls `~/.codex/auth.json`.
  3. Paste an API key — sets it in the process env so the current voss
     session resolves immediately. Persistence is added in Phase 3.

Style: minimal, monospace, single accent, no emoji. Matches `render.py`.

All external IO is injectable (`input_fn`, `secret_input_fn`, `detect`,
`spawn`, `waiter`, `console`) so the wizard is unit-testable without touching
real terminals, processes, or the filesystem.
"""
from __future__ import annotations

import getpass
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from voss.harness import auth as auth_mod
from voss.harness.auth import Resolution, UpstreamCli


CLAUDE_INSTALL_HINT = (
    "Install Claude Code: https://docs.anthropic.com/en/docs/claude-code/quickstart"
)
CODEX_INSTALL_HINT = (
    "Install Codex CLI: https://github.com/openai/codex"
)

ANTHROPIC_KEY_PREFIX = "sk-ant-"
OPENAI_KEY_PREFIX = "sk-"

DEFAULT_POLL_TIMEOUT = 180.0


# ---------------------------------------------------------------------------
# Injection types
# ---------------------------------------------------------------------------


InputFn = Callable[[str], str]
SecretInputFn = Callable[[str], str]
DetectFn = Callable[[UpstreamCli], Optional[Path]]
SpawnFn = Callable[[list[str]], int]
WaitFn = Callable[..., Optional[Resolution]]


def _default_spawn(argv: list[str]) -> int:
    """Run an upstream CLI inline so the user can interact with it.

    Returns the subprocess exit code; non-zero is non-fatal — the wizard
    still polls for creds (the user may have logged in despite an odd exit).
    """
    try:
        return subprocess.call(argv)
    except FileNotFoundError:
        return 127


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------


@dataclass
class _Deps:
    console: Console
    input_fn: InputFn
    secret_input_fn: SecretInputFn
    detect: DetectFn
    spawn: SpawnFn
    waiter: WaitFn
    poll_timeout: float


def run_login_wizard(
    *,
    reason: str = "no credentials found",
    console: Optional[Console] = None,
    input_fn: InputFn = input,
    secret_input_fn: SecretInputFn = getpass.getpass,
    detect: DetectFn = auth_mod.detect_upstream_cli,
    spawn: SpawnFn = _default_spawn,
    waiter: WaitFn = auth_mod.wait_for_creds,
    poll_timeout: float = DEFAULT_POLL_TIMEOUT,
) -> Optional[Resolution]:
    """Run the interactive login wizard. Returns a Resolution or None.

    A return of None means the user quit; the caller should fall back to its
    existing no-creds behaviour (print upstream instructions, exit non-zero).
    """
    deps = _Deps(
        console=console or Console(),
        input_fn=input_fn,
        secret_input_fn=secret_input_fn,
        detect=detect,
        spawn=spawn,
        waiter=waiter,
        poll_timeout=poll_timeout,
    )

    while True:
        _render_menu(deps, reason)
        choice = _prompt_menu(deps)
        if choice == "1":
            res = _branch_claude(deps)
        elif choice == "2":
            res = _branch_codex(deps)
        elif choice == "3":
            res = _branch_apikey(deps)
        elif choice in ("q", "Q", ""):
            deps.console.print("[dim]login cancelled[/dim]")
            return None
        else:
            deps.console.print(f"[yellow]unknown choice: {choice!r}[/yellow]")
            continue

        if res is not None:
            deps.console.print(f"[green]✓ signed in via {res.source}[/green] — {res.detail}")
            return res
        # Branch returned None (timeout / install missing / aborted) — loop.


# ---------------------------------------------------------------------------
# Menu rendering
# ---------------------------------------------------------------------------


def _render_menu(deps: _Deps, reason: str) -> None:
    have_claude = deps.detect("claude") is not None
    have_codex = deps.detect("codex") is not None

    lines: list[str] = []
    lines.append(f"reason: {reason}")
    lines.append("")
    lines.append(f"  1  Claude Code OAuth      {'[ready]' if have_claude else '[needs `claude` CLI]'}")
    lines.append(f"  2  Codex / ChatGPT OAuth  {'[ready]' if have_codex else '[needs `codex` CLI]'}")
    lines.append("  3  Paste an API key       [Anthropic or OpenAI]")
    lines.append("  q  Quit")

    panel = Panel(
        Text("\n".join(lines), style=""),
        title="voss · sign in",
        title_align="left",
        border_style="cyan",
    )
    deps.console.print(panel)


def _prompt_menu(deps: _Deps) -> str:
    try:
        return deps.input_fn("choice [1/2/3/q]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return "q"


# ---------------------------------------------------------------------------
# Branch: Claude Code OAuth
# ---------------------------------------------------------------------------


def _branch_claude(deps: _Deps) -> Optional[Resolution]:
    cli = deps.detect("claude")
    if cli is None:
        deps.console.print(f"[yellow]`claude` CLI not found on PATH.[/yellow]")
        deps.console.print(CLAUDE_INSTALL_HINT)
        return None

    deps.console.print(
        "[dim]launching `claude` — type `/login` inside, finish the browser flow,"
        " then `/exit` back to voss[/dim]"
    )
    deps.spawn([str(cli)])
    deps.console.print("[dim]checking for new Anthropic credentials…[/dim]")
    return deps.waiter("claude", timeout=deps.poll_timeout)


# ---------------------------------------------------------------------------
# Branch: Codex OAuth
# ---------------------------------------------------------------------------


def _branch_codex(deps: _Deps) -> Optional[Resolution]:
    cli = deps.detect("codex")
    if cli is None:
        deps.console.print(f"[yellow]`codex` CLI not found on PATH.[/yellow]")
        deps.console.print(CODEX_INSTALL_HINT)
        return None

    deps.console.print("[dim]running `codex login`…[/dim]")
    deps.spawn([str(cli), "login"])
    deps.console.print("[dim]checking for new OpenAI credentials…[/dim]")
    return deps.waiter("codex", timeout=deps.poll_timeout)


# ---------------------------------------------------------------------------
# Branch: paste API key
# ---------------------------------------------------------------------------


def _branch_apikey(deps: _Deps) -> Optional[Resolution]:
    provider = _prompt_apikey_provider(deps)
    if provider is None:
        return None

    env_var = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    expected_prefix = ANTHROPIC_KEY_PREFIX if provider == "anthropic" else OPENAI_KEY_PREFIX

    try:
        key = deps.secret_input_fn(f"paste {env_var} (input hidden): ").strip()
    except (EOFError, KeyboardInterrupt):
        deps.console.print("[dim]api-key entry cancelled[/dim]")
        return None

    if not key:
        deps.console.print("[yellow]empty key — try again[/yellow]")
        return None
    if not key.startswith(expected_prefix):
        deps.console.print(
            f"[yellow]warning: key does not start with `{expected_prefix}` — "
            f"continuing anyway[/yellow]"
        )

    # Phase 2: transient only — set in process env so this session resolves.
    # Phase 3 will add durable persistence (keyring / ~/.voss/credentials.toml).
    os.environ[env_var] = key
    res = auth_mod.resolve("api")
    if res.source == "none":
        deps.console.print("[red]api resolver still returns 'none' — investigate[/red]")
        return None
    deps.console.print(
        "[dim]key set for this session only — persistence ships in the next phase[/dim]"
    )
    return res


def _prompt_apikey_provider(deps: _Deps) -> Optional[str]:
    deps.console.print("provider:  1 Anthropic   2 OpenAI   (any other key cancels)")
    try:
        raw = deps.input_fn("provider [1/2]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if raw == "1":
        return "anthropic"
    if raw == "2":
        return "openai"
    return None


# ---------------------------------------------------------------------------
# Module-level entry helpers
# ---------------------------------------------------------------------------


def stdin_is_interactive() -> bool:
    """Wrapper so callers can skip the wizard in non-TTY contexts (CI, pipes)."""
    return sys.stdin.isatty() and sys.stdout.isatty()
