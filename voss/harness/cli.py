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

from .agent import run_turn
from .permissions import PermissionGate, PermissionStore
from .render import make_renderer
from . import session as session_store
from .tools import make_toolset


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _detect_provider_or_die() -> None:
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        click.echo(
            "no provider key in env. set ANTHROPIC_API_KEY or OPENAI_API_KEY.",
            err=True,
        )
        sys.exit(2)


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
def do_cmd(
    task: tuple[str, ...],
    model: str | None,
    cwd_str: str,
    json_mode: bool,
    mode: str,
    yes_to_all: bool,
) -> None:
    """Run a one-shot agent task and print the final answer.

    Stdin (when piped) is appended to the task as additional context.
    """
    _detect_provider_or_die()
    cwd = Path(cwd_str).resolve()
    if model:
        configure(default_model=model)
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
    renderer.show_user(text)

    result = asyncio.run(
        run_turn(
            text,
            tools=tools,
            cwd=cwd,
            renderer=renderer,
            model=cfg.default_model,
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
def chat_cmd(model: str | None, cwd_str: str, json_mode: bool, mode: str) -> None:
    """Interactive agent REPL. Ctrl-D or /exit to quit."""
    _detect_provider_or_die()
    cwd = Path(cwd_str).resolve()
    if model:
        configure(default_model=model)
    cfg = get_config()

    _run_repl(
        cwd=cwd,
        json_mode=json_mode,
        mode=mode,
        history=EpisodicMemory(capacity=40),
        record=session_store.SessionRecord.new(cwd=cwd, model=cfg.default_model),
    )


def _run_repl(
    *,
    cwd: Path,
    json_mode: bool,
    mode: str,
    history: EpisodicMemory,
    record: session_store.SessionRecord,
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
    """Diagnose env: provider keys, runtime imports."""
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    cfg = get_config()
    click.echo(f"default model      : {cfg.default_model}")
    click.echo(f"ANTHROPIC_API_KEY  : {'set' if has_anthropic else 'unset'}")
    click.echo(f"OPENAI_API_KEY     : {'set' if has_openai else 'unset'}")
    try:
        import voss_runtime  # noqa: F401

        click.echo("voss_runtime       : importable")
    except Exception as e:  # noqa: BLE001
        click.echo(f"voss_runtime       : FAIL {e}")


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


AGENT_COMMANDS = (do_cmd, chat_cmd, doctor_cmd)


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
        ctx.invoke(chat_cmd, model=None, cwd_str=".", json_mode=False, mode="edit")


register(main)


if __name__ == "__main__":
    main()
