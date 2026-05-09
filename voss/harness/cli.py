"""Agent commands for the unified `voss` CLI.

Defines `do_cmd`, `chat_cmd`, `doctor_cmd` as standalone click Commands.
- `voss.cli` imports them and adds them to the compiler's `main` group.
- `python -m voss.harness` builds a small standalone group for testing.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import click

from voss_runtime import EpisodicMemory, configure, get_config
from voss_runtime.providers import LiteLLMProvider
from voss_runtime.providers.base import ModelProvider

from . import auth as auth_mod
from . import session as session_store
from .agent import run_turn
from .permissions import PermissionGate, PermissionStore
from .providers import AnthropicOAuthProvider, OpenAIOAuthProvider
from .render import make_renderer
from .tools import make_toolset


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


AUTH_CHOICES = ("auto", "claude", "codex", "api", "none")


def _resolve_auth_or_die(preference: str) -> tuple[auth_mod.Resolution, ModelProvider]:
    """Pick an auth path, build a provider for it, or exit 2."""
    res = auth_mod.resolve(preference)
    if res.source == "none":
        click.echo(
            f"no usable credentials ({res.detail}). try one of:\n"
            "  • export ANTHROPIC_API_KEY=... (or OPENAI_API_KEY)\n"
            "  • run `claude login` (Claude Code, macOS Keychain)\n"
            "  • run `codex login` (~/.codex/auth.json)\n"
            "  • voss --auth=<auto|claude|codex|api>",
            err=True,
        )
        sys.exit(2)

    if res.source == "claude-oauth":
        provider: ModelProvider = AnthropicOAuthProvider(res.anthropic_oauth)  # type: ignore[arg-type]
    elif res.source == "codex-oauth":
        click.echo(
            "  [warning: codex-oauth (ChatGPT subscription) is experimental — "
            "chatgpt.com/backend-api/codex requires Codex-specific request shape "
            "the harness doesn't fully match yet. Use --auth=api with "
            "OPENAI_API_KEY for reliable OpenAI access.]",
            err=True,
        )
        provider = OpenAIOAuthProvider(res.codex_oauth)  # type: ignore[arg-type]
        cfg = get_config()
        if cfg.default_model.startswith("claude") or cfg.default_model == "gpt-5":
            configure(default_model="gpt-5-codex")
    elif res.source == "env-anthropic":
        provider = LiteLLMProvider()
    elif res.source in ("env-openai", "codex"):
        if res.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", res.openai_api_key)
        cfg = get_config()
        if cfg.default_model.startswith("claude"):
            configure(default_model="gpt-4o")
        provider = LiteLLMProvider()
    else:
        provider = LiteLLMProvider()
    return res, provider


def _git_status(cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "not a git repo"
    if out.returncode != 0:
        return "not a git repo"
    lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
    if not lines:
        return "clean"
    plus = sum(1 for ln in lines if ln.startswith(("A", "?")))
    minus = sum(1 for ln in lines if ln.startswith("D"))
    mod = sum(1 for ln in lines if ln.startswith(" M") or ln.startswith("M"))
    return f"+{plus} ~{mod} -{minus}"


# ---------------------------------------------------------------------------
# do — one-shot
# ---------------------------------------------------------------------------


@click.command("do")
@click.argument("task", nargs=-1, required=False)
@click.option("--model", default=None, help="Override default model.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--json", "json_mode", is_flag=True, help="Emit NDJSON events on stdout.")
@click.option(
    "--mode",
    type=click.Choice(["plan", "edit", "auto"]),
    default="edit",
    help="Permission tier.",
)
@click.option("--yes", "yes_to_all", is_flag=True, help="Skip permission prompts.")
@click.option(
    "--auth",
    "auth_pref",
    type=click.Choice(AUTH_CHOICES),
    default="auto",
    help="Credential source.",
)
def do_cmd(
    task: tuple[str, ...],
    model: str | None,
    cwd_str: str,
    json_mode: bool,
    mode: str,
    yes_to_all: bool,
    auth_pref: str,
) -> None:
    """Run a one-shot agent task and print the final answer.

    Stdin (when piped) is appended to the task as additional context.
    """
    cwd = Path(cwd_str).resolve()
    if model:
        configure(default_model=model)
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()

    parts = list(task)
    if not sys.stdin.isatty():
        parts.append("\n--- piped stdin ---\n")
        parts.append(sys.stdin.read())
    text = " ".join(parts).strip()
    if not text:
        click.echo("no task. usage: voss do \"<task>\"", err=True)
        sys.exit(2)

    renderer = make_renderer(json_mode=json_mode)
    tools = make_toolset(cwd)
    gate = PermissionGate(
        mode=mode,  # type: ignore[arg-type]
        store=PermissionStore.load(cwd),
        auto_yes=yes_to_all or json_mode,
    )

    renderer.banner(model=cfg.default_model, cwd=cwd, git_status=_git_status(cwd))
    click.echo(f"  [auth: {res.source} — {res.detail}]")
    renderer.show_user(text)

    result = asyncio.run(
        run_turn(
            text,
            tools=tools,
            cwd=cwd,
            renderer=renderer,
            model=cfg.default_model,
            provider=provider,
            permissions=gate,
        )
    )
    renderer.show_final(result.final, confidence=result.confidence, cost_usd=result.cost_usd)


# ---------------------------------------------------------------------------
# chat — REPL
# ---------------------------------------------------------------------------


@click.command("chat")
@click.option("--model", default=None, help="Override default model.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--json", "json_mode", is_flag=True, help="Emit NDJSON events on stdout.")
@click.option(
    "--mode",
    type=click.Choice(["plan", "edit", "auto"]),
    default="edit",
    help="Permission tier.",
)
@click.option(
    "--auth",
    "auth_pref",
    type=click.Choice(AUTH_CHOICES),
    default="auto",
    help="Credential source.",
)
def chat_cmd(
    model: str | None,
    cwd_str: str,
    json_mode: bool,
    mode: str,
    auth_pref: str,
) -> None:
    """Interactive agent REPL. Ctrl-D or /exit to quit."""
    cwd = Path(cwd_str).resolve()
    if model:
        configure(default_model=model)
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()

    _run_repl(
        cwd=cwd,
        json_mode=json_mode,
        mode=mode,
        history=EpisodicMemory(capacity=40),
        record=session_store.SessionRecord.new(cwd=cwd, model=cfg.default_model),
        provider=provider,
        auth_detail=f"{res.source} — {res.detail}",
    )


def _run_repl(
    *,
    cwd: Path,
    json_mode: bool,
    mode: str,
    history: EpisodicMemory,
    record: session_store.SessionRecord,
    provider: ModelProvider,
    auth_detail: str = "",
) -> None:
    cfg = get_config()
    renderer = make_renderer(json_mode=json_mode)
    tools = make_toolset(cwd)
    gate = PermissionGate(
        mode=mode,  # type: ignore[arg-type]
        store=PermissionStore.load(cwd),
    )
    total_cost = record.total_cost_usd
    renderer.banner(model=cfg.default_model, cwd=cwd, git_status=_git_status(cwd))
    if auth_detail:
        click.echo(f"  [auth: {auth_detail}]")
    if record.turns:
        click.echo(f"resumed: {record.name} ({len(record.turns)} prior turns)")

    while True:
        try:
            line = input("▌ ")
        except (EOFError, KeyboardInterrupt):
            click.echo()
            return
        line = line.strip()
        if not line:
            continue

        # Slash commands.
        if line in ("/exit", "/quit"):
            return
        if line == "/help":
            _print_slash_help()
            continue
        if line == "/clear":
            history = EpisodicMemory(capacity=40)
            click.echo("episodic memory cleared.")
            continue
        if line == "/cost":
            click.echo(f"session cost: ${total_cost:.4f}")
            continue
        if line == "/tools":
            for name, td in tools.items():
                click.echo(f"  {name} — {td.description}")
            continue
        if line.startswith("/model "):
            new_model = line.split(" ", 1)[1].strip()
            configure(default_model=new_model)
            cfg = get_config()
            click.echo(f"model: {cfg.default_model}")
            continue
        if line.startswith("/mode "):
            new_mode = line.split(" ", 1)[1].strip()
            if new_mode not in ("plan", "edit", "auto"):
                click.echo("mode must be plan|edit|auto", err=True)
                continue
            gate.mode = new_mode  # type: ignore[assignment]
            click.echo(f"mode: {new_mode}")
            continue
        if line.startswith("/save"):
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip():
                record.name = parts[1].strip()
            record.total_cost_usd = total_cost
            record.model = cfg.default_model
            path = session_store.save(record, history)
            click.echo(f"saved: {path}")
            continue
        if line.startswith("/"):
            click.echo(f"unknown command: {line}. /help for list.", err=True)
            continue

        renderer.show_user(line)
        try:
            result = asyncio.run(
                run_turn(
                    line,
                    tools=tools,
                    cwd=cwd,
                    renderer=renderer,
                    model=cfg.default_model,
                    history=history,
                    permissions=gate,
                    provider=provider,
                )
            )
        except Exception as e:  # noqa: BLE001
            click.echo(f"error: {e}", err=True)
            continue
        total_cost += result.cost_usd
        renderer.show_final(
            result.final, confidence=result.confidence, cost_usd=result.cost_usd
        )


# ---------------------------------------------------------------------------
# doctor — diagnostics
# ---------------------------------------------------------------------------


@click.command("doctor")
def doctor_cmd() -> None:
    """Diagnose env: credentials, runtime imports, picked auth path."""
    cfg = get_config()
    click.echo(f"default model       : {cfg.default_model}")
    click.echo(f"ANTHROPIC_API_KEY   : {'set' if os.environ.get('ANTHROPIC_API_KEY') else 'unset'}")
    click.echo(f"OPENAI_API_KEY      : {'set' if os.environ.get('OPENAI_API_KEY') else 'unset'}")

    claude = auth_mod.load_anthropic_oauth()
    if claude:
        click.echo(
            f"Claude Code OAuth   : found ({claude.subscription_type}, "
            f"expires in {claude.expires_in_seconds}s)"
        )
    else:
        click.echo("Claude Code OAuth   : not found")

    codex = auth_mod.load_codex()
    if codex:
        bits = []
        if codex.api_key:
            bits.append("OPENAI_API_KEY")
        if codex.access_token:
            bits.append("OAuth tokens")
        click.echo(f"Codex creds         : found ({codex.auth_mode}; {', '.join(bits) or 'empty'})")
    else:
        click.echo("Codex creds         : not found")

    res = auth_mod.resolve("auto")
    click.echo(f"--auth=auto picks   : {res.source} — {res.detail}")

    try:
        import voss_runtime  # noqa: F401

        click.echo("voss_runtime        : importable")
    except Exception as e:  # noqa: BLE001
        click.echo(f"voss_runtime        : FAIL {e}")


def _print_slash_help() -> None:
    click.echo(
        "\n".join(
            [
                "/help          show this list",
                "/exit /quit    leave the REPL (also Ctrl-D)",
                "/clear         drop episodic memory",
                "/cost          session cost so far",
                "/tools         list registered tools",
                "/model <id>    switch model",
                "/mode <m>      plan | edit | auto",
                "/save [name]   persist session snapshot",
            ]
        )
    )


@click.command("sessions")
def sessions_cmd() -> None:
    """List saved agent sessions."""
    records = session_store.list_sessions()
    if not records:
        click.echo("(no sessions)")
        return
    for r in records:
        click.echo(
            f"  {r.id[:8]}  {r.updated_at}  {r.model:<28}  {r.first_task()}"
        )


@click.command("resume")
@click.argument("session_id_or_name")
@click.option(
    "--mode",
    type=click.Choice(["plan", "edit", "auto"]),
    default="edit",
    help="Permission tier.",
)
@click.option("--json", "json_mode", is_flag=True, help="Emit NDJSON events on stdout.")
@click.option(
    "--auth",
    "auth_pref",
    type=click.Choice(AUTH_CHOICES),
    default="auto",
    help="Credential source.",
)
def resume_cmd(
    session_id_or_name: str,
    mode: str,
    json_mode: bool,
    auth_pref: str,
) -> None:
    """Resume a saved session by id-prefix or name."""
    try:
        record, history = session_store.load(session_id_or_name)
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"resume failed: {e}", err=True)
        sys.exit(1)
    cwd = Path(record.cwd)
    if record.model:
        configure(default_model=record.model)
    res, provider = _resolve_auth_or_die(auth_pref)
    _run_repl(
        cwd=cwd,
        json_mode=json_mode,
        mode=mode,
        history=history,
        record=record,
        provider=provider,
        auth_detail=f"{res.source} — {res.detail}",
    )


AGENT_COMMANDS = (do_cmd, chat_cmd, doctor_cmd, sessions_cmd, resume_cmd)


def register(group: click.Group) -> None:
    """Attach all agent commands to a click Group."""
    for cmd in AGENT_COMMANDS:
        group.add_command(cmd)


# ---------------------------------------------------------------------------
# standalone entry: `python -m voss.harness ...`
# ---------------------------------------------------------------------------


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.pass_context
def main(ctx: click.Context) -> None:
    """voss · agent (standalone harness invocation).

    Usually invoked as `voss do` / `voss chat`. Bare invocation drops into chat.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(
            chat_cmd,
            model=None,
            cwd_str=".",
            json_mode=False,
            mode="edit",
            auth_pref="auto",
        )


register(main)


if __name__ == "__main__":
    main()
