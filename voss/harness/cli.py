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
from dataclasses import asdict, dataclass
from pathlib import Path
from types import SimpleNamespace

import click

from voss_runtime import EpisodicMemory, configure, get_config
from voss_runtime.providers import LiteLLMProvider
from voss_runtime.providers.base import ModelProvider

from . import auth as auth_mod
from . import cognition as cognition_mod
from . import conventions
from . import session as session_store
from . import voss_md
from .memory_cli import memory_group
from .memory_store import MemoryStore
from .agent import Plan
from .permissions import PermissionGate, PermissionStore
from .plugins import load_plugins, set_plugin_enabled
from .providers import AnthropicOAuthProvider, OpenAIOAuthProvider
from .render import make_renderer
from .skill_registry import SkillRegistry, default_skill_registry
from .slash import SlashCommand, SlashRegistry
from .subagents import (
    SubagentRegistry,
    attach_subagent_tool,
    default_subagent_registry,
    run_subagent,
)
from .tools import make_toolset

try:
    import litellm as _litellm  # type: ignore
except Exception:  # noqa: BLE001
    _litellm = None  # type: ignore[assignment]


_INTENT_ALLOWLIST = frozenset(
    {
        "analyze repo",
        "analyze this repo",
        "analyze this project",
        "update project memory",
        "refresh cognition",
        "rebuild cognition",
    }
)


def _classify_intent(line: str) -> str | None:
    """Literal-match natural-language router. No LLM. Returns intent name or None."""
    return "analyze" if line.lower().strip() in _INTENT_ALLOWLIST else None


def _handle_analyze(
    *,
    cwd: Path,
    provider: ModelProvider,
    history: EpisodicMemory,
    record: session_store.SessionRecord,
    renderer,
    tools,
    gate: PermissionGate,
) -> None:
    from .skills.analyze import run as analyze_run

    analyze_run(
        cwd=cwd,
        provider=provider,
        history=history,
        record=record,
        renderer=renderer,
        tools=tools,
        gate=gate,
    )


def _handle_save_plan(
    *,
    cwd: Path,
    last_plan: "Plan | None",
    record: session_store.SessionRecord,
    line: str,
) -> None:
    if last_plan is None:
        click.echo("no plan to save yet — run a turn first", err=True)
        return
    remainder = line[len("/save-plan") :].strip()
    title = remainder or None
    try:
        path = cognition_mod.write_plan_md(
            cwd,
            last_plan,
            session_id=record.id,
            model=record.model,
            title=title,
        )
        try:
            shown = path.relative_to(cwd)
        except ValueError:
            shown = path
        click.echo(f"plan saved: {shown}")
    except OSError as exc:
        click.echo(f"warning: failed to save plan: {exc}", err=True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


AUTH_CHOICES = ("auto", "claude", "codex", "api", "none")


@dataclass
class ReplContext:
    cwd: Path
    renderer: object
    tools: dict
    gate: PermissionGate
    history: EpisodicMemory
    record: session_store.SessionRecord
    provider: ModelProvider
    skill_registry: SkillRegistry
    subagent_registry: SubagentRegistry
    slash_registry: SlashRegistry
    cognition: object | None = None
    prior_context: dict | None = None
    last_plan: Plan | None = None
    total_cost: float = 0.0
    should_exit: bool = False
    voss_md_text: str | None = None
    memory_store: object | None = None
    model: str | None = None
    persist_conventions_selection: str | None = None


def _resolve_default_model(user_explicit: str | None) -> None:
    """Resolve the global default model per D-09.

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


def _resolve_run_turn(cwd: Path | None = None):
    from . import config as harness_config

    backend = os.environ.get("VOSS_HARNESS")
    if backend is None:
        backend = harness_config.load_harness_config().get("backend")
    backend = backend or "python"

    if backend not in ("python", "compiled"):
        raise click.ClickException(
            f"invalid VOSS_HARNESS={backend!r}: expected 'python' or 'compiled'"
        )

    if backend == "python":
        from .agent import run_turn

        return run_turn

    from . import cache as harness_cache

    project_root = (cwd or Path.cwd()).resolve()
    harness_cache.assert_fresh(project_root)

    import importlib.util

    loop_py = project_root / harness_cache.CACHE_HARNESS_DIR / "loop.py"
    spec = importlib.util.spec_from_file_location(
        "voss_compiled_harness_loop",
        loop_py,
    )
    if spec is None or spec.loader is None:
        raise click.ClickException(f"failed to load compiled harness: {loop_py}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_turn


def _emit_harness_boot_telemetry(cwd: Path, model: str | None) -> None:
    """Emit session lifecycle when agent commands start (only if VOSS_LOG is enabled)."""
    from . import config as harness_config
    from . import telemetry as tel_mod

    if not tel_mod.enabled():
        return
    backend = os.environ.get("VOSS_HARNESS")
    if backend is None:
        backend = harness_config.load_harness_config().get("backend")
    backend_str = str(backend or "python").strip()
    tel_mod.ensure_trace_id()
    tel_mod.emit_harness_start(backend=backend_str, cwd=str(cwd.resolve()), model=model)


def _handle_login_status(provider: str | None) -> None:
    """Status + refresh for existing creds; for missing, print upstream commands.

    M1 contract: re-auth flows go through the upstream CLI (`claude /login`,
    `codex login`); this function only refreshes EXISTING tokens and prints
    upstream commands for MISSING tokens. The interactive `voss login`
    wizard (Phase 4) is the user-facing entry point for first-run setup.
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
                click.echo(
                    f"  Claude: refresh failed ({e}). Run: claude /login",
                    err=True,
                )
        else:
            click.echo(
                f"  Claude: OK (expires in {claude.expires_in_seconds}s, "
                f"{claude.subscription_type})"
            )
    if provider in (None, "openai", "codex"):
        codex = auth_mod.load_codex()
        if codex is None:
            click.echo("  Codex:  no creds found. Run: codex login")
        else:
            bits: list[str] = []
            if codex.api_key:
                bits.append("OPENAI_API_KEY")
            if codex.has_oauth:
                bits.append("OAuth tokens")
            click.echo(
                f"  Codex:  OK ({codex.auth_mode}; {', '.join(bits) or 'empty'})"
            )
    if provider is not None and provider not in ("anthropic", "openai", "codex"):
        click.echo(
            f"unknown provider: {provider}. use anthropic | openai",
            err=True,
        )


_handle_login = _handle_login_status  # backward-compat alias for older callers


def _resolve_auth_or_die(preference: str) -> tuple[auth_mod.Resolution, ModelProvider]:
    """Pick an auth path, build a provider for it, or exit 2.

    First-run UX: on a TTY with no creds, launch the interactive login wizard
    instead of failing out. Non-TTY callers (CI, pipes, `voss do < script`)
    still get the original exit-2 error so scripted invocations stay
    deterministic.
    """
    res = auth_mod.resolve(preference)
    if res.source == "none":
        from . import login_wizard

        if login_wizard.stdin_is_interactive():
            new_res = login_wizard.run_login_wizard(
                reason=f"no credentials found ({res.detail})"
            )
            if new_res is not None:
                res = new_res
        if res.source == "none":
            click.echo(
                f"no usable credentials ({res.detail}). try one of:\n"
                "  • run `voss login` to launch the interactive setup wizard\n"
                "  • export ANTHROPIC_API_KEY=... (or OPENAI_API_KEY)\n"
                "  • run `claude /login` (Claude Code, macOS Keychain)\n"
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
    elif res.source in ("env-anthropic", "voss-anthropic"):
        # `resolve()` already injected ANTHROPIC_API_KEY into env for the
        # voss-anthropic case, so LiteLLM picks it up the same as env-anthropic.
        provider = LiteLLMProvider()
    elif res.source in ("env-openai", "voss-openai", "codex"):
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


def _print_plugins(ctx: ReplContext) -> None:
    plugins = load_plugins(
        ctx.cwd,
        command_ids=ctx.slash_registry.ids(),
        skill_ids=ctx.skill_registry.ids(),
        agent_ids=ctx.subagent_registry.ids(),
    )
    if not plugins:
        click.echo("(no plugins)")
        return
    for plugin in plugins:
        status = "enabled" if plugin.enabled else "disabled"
        click.echo(f"  {plugin.id:<20} {status:<8} {plugin.name}")
        for warning in plugin.warnings:
            click.echo(f"    warning: {warning}", err=True)


def _print_skills(ctx: ReplContext) -> None:
    for entry in ctx.skill_registry.entries():
        mut = "mut" if entry.mutating else "read"
        click.echo(f"  {entry.id:<16} {mut:<4} {entry.description}")


def _print_agents(ctx: ReplContext) -> None:
    for spec in ctx.subagent_registry.entries():
        click.echo(f"  {spec.id:<16} {spec.description}")


_RECALL_USAGE = "usage: /recall <query> [--top N] [--source turn|decision|convention|ledger|note]"


def _pop_flag_value(args: list[str], flag: str) -> tuple[list[str], str | None]:
    """Return (args_without_flag, flag_value or None)."""
    if flag not in args:
        return args, None
    idx = args.index(flag)
    if idx + 1 >= len(args):
        return args[:idx], None
    value = args[idx + 1]
    return args[:idx] + args[idx + 2 :], value


def _recall(ctx, args: list[str], _line: str) -> None:
    if not args:
        click.echo(_RECALL_USAGE, err=True)
        return
    args, top_raw = _pop_flag_value(list(args), "--top")
    args, source = _pop_flag_value(args, "--source")
    try:
        top_k = int(top_raw) if top_raw is not None else 5
    except ValueError:
        click.echo(_RECALL_USAGE, err=True)
        return
    query = " ".join(args).strip()
    if not query:
        click.echo(_RECALL_USAGE, err=True)
        return
    store = getattr(ctx, "memory_store", None)
    if store is None:
        click.echo("/recall unavailable: memory store not bound", err=True)
        return
    hits = store.recall(query, top_k=top_k, source=source)
    if not hits:
        click.echo("(no hits)")
        return
    for h in hits:
        click.echo(f"[{h.source}] {h.locator}  (score {h.score:.2f})")
        excerpt = (h.excerpt or "").replace("\n", " ")[:160]
        if excerpt:
            click.echo(f"  {excerpt}")


def _forget(ctx, args: list[str], _line: str) -> None:
    if not args:
        click.echo("usage: /forget <pattern> [--yes]", err=True)
        return
    pattern = args[0]
    confirm = "--yes" in args[1:]
    non_interactive = not sys.stdin.isatty()
    if non_interactive and not confirm:
        click.echo("/forget requires --yes in non-interactive mode", err=True)
        return
    store = getattr(ctx, "memory_store", None)
    if store is None:
        click.echo("/forget unavailable: memory store not bound", err=True)
        return
    n = store.forget(pattern, confirm=confirm)
    click.echo(f"tombstoned: {n} entries")


def _memory(ctx, args: list[str], _line: str) -> None:
    args, source = _pop_flag_value(list(args), "--source")
    store = getattr(ctx, "memory_store", None)
    if store is None:
        click.echo("/memory unavailable: memory store not bound", err=True)
        return
    click.echo(store.summary(source=source))


def _save_note(ctx, args: list[str], _line: str) -> None:
    # Pitfall 1 invariant: do NOT mutate ctx.record.name — that is /save-session's job.
    text = " ".join(args).strip()
    if not text:
        click.echo("usage: /save <note text>", err=True)
        return
    store = getattr(ctx, "memory_store", None)
    if store is None:
        click.echo("/save unavailable: memory store not bound", err=True)
        return
    try:
        path = store.write_note(text, session_id=ctx.record.id)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"failed: {exc}", err=True)
        return
    cwd = getattr(ctx, "cwd", None)
    try:
        display = path.relative_to(cwd) if cwd else path
    except ValueError:
        display = path
    click.echo(f"note saved: {display}")


def _build_slash_registry() -> SlashRegistry:
    registry = SlashRegistry()

    def _exit(ctx: ReplContext, _args: list[str], _line: str) -> None:
        ctx.should_exit = True

    def _help(ctx: ReplContext, _args: list[str], _line: str) -> None:
        _print_slash_help(ctx.slash_registry)

    def _clear(ctx: ReplContext, _args: list[str], _line: str) -> None:
        ctx.history = EpisodicMemory(capacity=40)
        click.echo("episodic memory cleared.")

    def _cost(ctx: ReplContext, _args: list[str], _line: str) -> None:
        click.echo(f"session cost: ${ctx.total_cost:.4f}")

    def _tools(ctx: ReplContext, _args: list[str], _line: str) -> None:
        for name, td in ctx.tools.items():
            click.echo(f"  {name} — {td.description}")

    def _analyze(ctx: ReplContext, _args: list[str], _line: str) -> None:
        skill = ctx.skill_registry.get("analyze")
        if skill is not None:
            skill.handler(ctx, [])

    def _save_plan(ctx: ReplContext, _args: list[str], line: str) -> None:
        _handle_save_plan(
            cwd=ctx.cwd, last_plan=ctx.last_plan, record=ctx.record, line=line
        )

    def _model(ctx: ReplContext, args: list[str], _line: str) -> None:
        cfg = get_config()
        if not args:
            claude = auth_mod.load_anthropic_oauth()
            codex = auth_mod.load_codex()
            click.echo(f"  active: {cfg.default_model}")
            claude_ok = bool(claude and not claude.expired)
            codex_ok = bool(codex and (codex.api_key or codex.has_oauth))
            click.echo(f"  Claude: {'available' if claude_ok else 'unavailable'}")
            click.echo(f"  Codex:  {'available' if codex_ok else 'unavailable'}")
            return
        from . import config as harness_config

        new_model = " ".join(args).strip()
        configure(default_model=new_model)
        harness_config.set_preferred_model(new_model)
        click.echo(f"  model: {get_config().default_model} (persisted)")

    def _mode(ctx: ReplContext, args: list[str], _line: str) -> None:
        if not args:
            click.echo(f"  mode: {ctx.gate.mode}")
            return
        new_mode = args[0].strip()
        if new_mode not in ("plan", "edit", "auto"):
            click.echo("mode must be plan|edit|auto", err=True)
            return
        if new_mode == "auto" and "--confirm" not in args:
            click.echo(
                "escalating to auto requires --confirm "
                "(e.g. /mode auto --confirm)",
                err=True,
            )
            return
        ctx.gate.mode = new_mode  # type: ignore[assignment]
        click.echo(f"  mode: {new_mode}")

    def _login(_ctx: ReplContext, args: list[str], _line: str) -> None:
        # /login              → interactive wizard (first-run setup)
        # /login status [p]   → status + refresh for existing creds (legacy)
        # /login anthropic|openai|codex → status for a single provider
        if not args:
            from . import login_wizard

            login_wizard.run_login_wizard(reason="re-auth from REPL")
            return
        if args[0] == "status":
            _handle_login_status(args[1] if len(args) > 1 else None)
            return
        _handle_login_status(args[0])

    def _save_session(ctx: ReplContext, args: list[str], _line: str) -> None:
        if args:
            ctx.record.name = " ".join(args).strip()
        ctx.record.total_cost_usd = ctx.total_cost
        ctx.record.model = get_config().default_model
        path = session_store.save(ctx.record, ctx.history)
        click.echo(f"saved: {path}")

    def _plugins(ctx: ReplContext, _args: list[str], _line: str) -> None:
        _print_plugins(ctx)

    def _plugin(ctx: ReplContext, args: list[str], _line: str) -> None:
        if len(args) != 2 or args[0] not in ("enable", "disable"):
            click.echo("usage: /plugin enable|disable <id>", err=True)
            return
        path = set_plugin_enabled(args[1], args[0] == "enable")
        click.echo(f"plugin {args[1]} {'enabled' if args[0] == 'enable' else 'disabled'}: {path}")

    def _skills(ctx: ReplContext, _args: list[str], _line: str) -> None:
        _print_skills(ctx)

    def _skill(ctx: ReplContext, args: list[str], _line: str) -> None:
        if not args:
            click.echo("usage: /skill <id> [args...]", err=True)
            return
        entry = ctx.skill_registry.get(args[0])
        if entry is None:
            click.echo(f"unknown skill: {args[0]}", err=True)
            return
        entry.handler(ctx, args[1:])

    def _agents(ctx: ReplContext, _args: list[str], _line: str) -> None:
        _print_agents(ctx)

    def _agent(ctx: ReplContext, args: list[str], _line: str) -> None:
        if len(args) < 3 or args[0] != "spawn":
            click.echo("usage: /agent spawn <id> <task>", err=True)
            return
        result = asyncio.run(
            run_subagent(
                agent_id=args[1],
                task=" ".join(args[2:]),
                registry=ctx.subagent_registry,
                cwd=ctx.cwd,
                renderer=ctx.renderer,
                provider=ctx.provider,
                model=get_config().default_model,
                gate=ctx.gate,
                cognition=ctx.cognition,
            )
        )
        click.echo(result)

    for command in (
        SlashCommand("/help", "show this list", _help),
        SlashCommand("/exit", "leave the REPL (also Ctrl-D)", _exit, aliases=("/quit",)),
        SlashCommand("/clear", "drop episodic memory", _clear),
        SlashCommand("/cost", "session cost so far", _cost),
        SlashCommand("/tools", "list registered tools", _tools),
        SlashCommand("/login", "launch sign-in wizard (or `/login status` for cred status)", _login),
        SlashCommand("/model", "list providers or switch (persists to config.toml)", _model),
        SlashCommand("/mode", "plan | edit | auto; auto requires --confirm", _mode),
        SlashCommand("/save-session", "persist session snapshot", _save_session, mutating=True),
        SlashCommand("/recall", "search memory (top-N hits across sources)", _recall),
        SlashCommand("/forget", "delete memory entries matching <pattern>", _forget, mutating=True),
        SlashCommand("/memory", "summarize current memory store", _memory),
        SlashCommand("/save", "append a manual note to memory", _save_note, mutating=True),
        SlashCommand("/analyze", "refresh project cognition (.voss/ + .voss-cache/)", _analyze, mutating=True),
        SlashCommand("/save-plan", "persist the most recent plan to .voss/plans/", _save_plan, mutating=True),
        SlashCommand("/plugins", "list plugin manifests", _plugins),
        SlashCommand("/plugin", "enable|disable a plugin manifest", _plugin, mutating=True),
        SlashCommand("/skills", "list registered skills", _skills),
        SlashCommand("/skill", "run a registered skill", _skill, mutating=True),
        SlashCommand("/agents", "list registered subagents", _agents),
        SlashCommand("/agent", "spawn a registered subagent", _agent, mutating=True),
    ):
        registry.register(command)
    return registry


# ---------------------------------------------------------------------------
# do — one-shot
# ---------------------------------------------------------------------------


def _apply_no_unicode_env(no_unicode: bool) -> None:
    """Set VOSS_NO_UNICODE=1 BEFORE make_renderer/glyphs import.

    The glyphs module reads the env var at import time and rewires its
    module-level constants to ASCII fallbacks. Tests can also drive the
    same code path by setting `VOSS_NO_UNICODE=1` directly.
    """
    if no_unicode:
        os.environ["VOSS_NO_UNICODE"] = "1"


def _wire_tui_permissions_if_textual(gate: PermissionGate, renderer) -> None:
    """If `renderer` is a TextualRenderer, install modal-driven permission prompts.

    Deferred imports keep cli.py decoupled from the Textual import graph on
    the plain / non-TTY paths.
    """
    from .tui.permissions_bridge import install_tui_permissions
    from .tui.renderer import TextualRenderer

    if isinstance(renderer, TextualRenderer):
        install_tui_permissions(gate, renderer.app)


@click.command("do")
@click.argument("task", nargs=-1, required=False)
@click.option("--model", default=None, help="Override default model.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--json", "json_mode", is_flag=True, help="Emit NDJSON events on stdout.")
@click.option("--plain", "plain", is_flag=True, help="Use line-streamed renderer; bypass TUI.")
@click.option(
    "--no-unicode",
    "no_unicode",
    is_flag=True,
    help="Use ASCII fallback for TUI glyphs (sets VOSS_NO_UNICODE=1).",
)
@click.option(
    "--mode",
    type=click.Choice(["plan", "edit", "auto"]),
    default="plan",  # D-07: do defaults to plan
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
    plain: bool,
    no_unicode: bool,
    mode: str,
    yes_to_all: bool,
    auth_pref: str,
) -> None:
    """Run a one-shot agent task and print the final answer.

    Stdin (when piped) is appended to the task as additional context.
    """
    cwd = Path(cwd_str).resolve()
    _apply_no_unicode_env(no_unicode)
    _resolve_default_model(model)
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()

    _emit_harness_boot_telemetry(cwd, cfg.default_model)

    parts = list(task)
    if not sys.stdin.isatty():
        parts.append("\n--- piped stdin ---\n")
        parts.append(sys.stdin.read())
    text = " ".join(parts).strip()
    if not text:
        click.echo("no task. usage: voss do \"<task>\"", err=True)
        sys.exit(2)

    renderer = make_renderer(json_mode=json_mode, plain=plain)
    tools = make_toolset(cwd)
    voss_md.ensure_migrated(cwd)
    do_bundle = cognition_mod.load(cwd)
    voss_md_text = voss_md.read_and_inject(cwd)
    gate = PermissionGate(
        mode=mode,  # type: ignore[arg-type]
        store=PermissionStore.load(cwd),
        auto_yes=yes_to_all or json_mode,
        project_policy=do_bundle.permissions if do_bundle.initialized else None,
    )
    _wire_tui_permissions_if_textual(gate, renderer)
    attach_subagent_tool(
        tools,
        registry=default_subagent_registry(),
        cwd=cwd,
        renderer=renderer,
        provider=provider,
        model=lambda: get_config().default_model,
        gate=gate,
        cognition=do_bundle,
    )

    # Conventions hook locals: do_record/do_history/do_memory_store — pinned by M8-04 plan.
    do_cwd = cwd
    do_provider = provider
    do_model = cfg.default_model
    do_record = session_store.SessionRecord.new(cwd=cwd, model=do_model)
    do_history = EpisodicMemory(capacity=40)
    do_memory_store = MemoryStore(cwd).bind(session_id=do_record.id)

    renderer.banner(model=cfg.default_model, cwd=cwd, git_status=_git_status(cwd))
    click.echo(f"  [auth: {res.source} — {res.detail}]")
    renderer.show_user(text)

    run_turn = _resolve_run_turn(cwd)
    result = asyncio.run(
        run_turn(
            text,
            tools=tools,
            cwd=cwd,
            renderer=renderer,
            model=do_model,
            provider=do_provider,
            permissions=gate,
            history=do_history,
            session_id=do_record.id,
            voss_md_text=voss_md_text,
        )
    )
    renderer.show_final(result.final, confidence=result.confidence, cost_usd=result.cost_usd)

    if result.run is not None:
        do_record.runs.append(asdict(result.run))

    do_ctx = SimpleNamespace(
        provider=do_provider,
        model=do_model,
        cwd=do_cwd,
        persist_conventions_selection=None,
    )
    try:
        conventions.run_on_clean_exit(
            do_ctx,
            history=do_history,
            record=do_record,
            memory_store=do_memory_store,
        )
    except Exception as exc:  # noqa: BLE001
        click.echo(f"conventions extraction skipped: {exc}", err=True)


# ---------------------------------------------------------------------------
# chat — REPL
# ---------------------------------------------------------------------------


@click.command("chat")
@click.option("--model", default=None, help="Override default model.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--json", "json_mode", is_flag=True, help="Emit NDJSON events on stdout.")
@click.option("--plain", "plain", is_flag=True, help="Use line-streamed renderer; bypass TUI.")
@click.option(
    "--no-unicode",
    "no_unicode",
    is_flag=True,
    help="Use ASCII fallback for TUI glyphs (sets VOSS_NO_UNICODE=1).",
)
@click.option(
    "--mode",
    type=click.Choice(["plan", "edit", "auto"]),
    default="plan",  # D-07: chat defaults to plan
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
    plain: bool,
    no_unicode: bool,
    mode: str,
    auth_pref: str,
) -> None:
    """Interactive agent REPL. Ctrl-D or /exit to quit."""
    cwd = Path(cwd_str).resolve()
    _apply_no_unicode_env(no_unicode)
    _resolve_default_model(model)
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()

    _emit_harness_boot_telemetry(cwd, cfg.default_model)

    _run_repl(
        cwd=cwd,
        json_mode=json_mode,
        plain=plain,
        mode=mode,
        history=EpisodicMemory(capacity=40),
        record=session_store.SessionRecord.new(cwd=cwd, model=cfg.default_model),
        provider=provider,
        auth_detail=f"{res.source} — {res.detail}",
    )


@click.command("edit")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
@click.option("--model", default=None, help="Override default model.")
@click.option("--json", "json_mode", is_flag=True, help="Emit NDJSON events on stdout.")
@click.option("--plain", "plain", is_flag=True, help="Use line-streamed renderer; bypass TUI.")
@click.option(
    "--no-unicode",
    "no_unicode",
    is_flag=True,
    help="Use ASCII fallback for TUI glyphs (sets VOSS_NO_UNICODE=1).",
)
@click.option(
    "--mode",
    type=click.Choice(["plan", "edit", "auto"]),
    default="edit",
    help="Permission tier (default edit per D-07).",
)
@click.option(
    "--auth",
    "auth_pref",
    type=click.Choice(AUTH_CHOICES),
    default="auto",
    help="Credential source.",
)
def edit_cmd(
    path: str,
    cwd_str: str,
    model: str | None,
    json_mode: bool,
    plain: bool,
    no_unicode: bool,
    mode: str,
    auth_pref: str,
) -> None:
    """Scoped edit REPL. Writes restricted to <PATH> + sibling test mirror (D-02).

    Out-of-scope writes prompt to expand the scope for this session only.
    Reads stay free under the cwd path jail.
    """
    from .edit_scope import EditScope

    cwd = Path(cwd_str).resolve()
    _apply_no_unicode_env(no_unicode)
    _resolve_default_model(model)
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()

    _emit_harness_boot_telemetry(cwd, cfg.default_model)

    scope = EditScope.resolve(cwd, path)
    record = session_store.SessionRecord.new(
        cwd=cwd,
        model=cfg.default_model,
        name=f"edit-{Path(path).name}",
    )

    click.echo(f"  edit scope: {', '.join(scope.summary()) or path}")

    _run_repl(
        cwd=cwd,
        json_mode=json_mode,
        plain=plain,
        mode=mode,
        history=EpisodicMemory(capacity=40),
        record=record,
        provider=provider,
        auth_detail=f"{res.source} — {res.detail}",
        edit_scope=scope,
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
    edit_scope=None,
    prior_context: dict | None = None,
    plain: bool = False,
) -> None:
    cfg = get_config()
    renderer = make_renderer(json_mode=json_mode, plain=plain)
    tools = make_toolset(cwd)
    skill_registry = default_skill_registry()
    subagent_registry = default_subagent_registry()
    slash_registry = _build_slash_registry()

    def _tok_count(text: str) -> int:
        if _litellm is not None:
            try:
                return int(
                    _litellm.token_counter(model=cfg.default_model, text=text)
                )
            except Exception:  # noqa: BLE001
                pass
        return max(len(text) // 4, 1)

    voss_md.ensure_migrated(cwd)
    bundle = cognition_mod.load(cwd, token_count=_tok_count)
    if bundle.load_errors:
        for err in bundle.load_errors:
            click.echo(f"cognition error: {err}", err=True)
    voss_md_text = voss_md.read_and_inject(cwd)

    gate = PermissionGate(
        mode=mode,  # type: ignore[arg-type]
        store=PermissionStore.load(cwd),
        edit_scope=edit_scope,
        project_policy=bundle.permissions if bundle.initialized else None,
    )
    _wire_tui_permissions_if_textual(gate, renderer)
    ctx = ReplContext(
        cwd=cwd,
        renderer=renderer,
        tools=tools,
        gate=gate,
        history=history,
        record=record,
        provider=provider,
        skill_registry=skill_registry,
        subagent_registry=subagent_registry,
        slash_registry=slash_registry,
        cognition=bundle,
        prior_context=prior_context,
        total_cost=record.total_cost_usd,
        voss_md_text=voss_md_text,
        memory_store=MemoryStore(cwd).bind(session_id=record.id),
        model=cfg.default_model,
    )
    attach_subagent_tool(
        tools,
        registry=subagent_registry,
        cwd=cwd,
        renderer=renderer,
        provider=provider,
        model=lambda: get_config().default_model,
        gate=gate,
        cognition=bundle,
    )

    renderer.banner(model=cfg.default_model, cwd=cwd, git_status=_git_status(cwd))
    if auth_detail:
        click.echo(f"  [auth: {auth_detail}]")
    if record.turns:
        click.echo(f"resumed: {record.name} ({len(record.turns)} prior turns)")

    # D-04: non-blocking drift hint. T-M2-22: wrap in try/except so a
    # malformed frontmatter can never crash REPL boot.
    if bundle.initialized and bundle.architecture_frontmatter:
        try:
            drift = cognition_mod.drift_check(cwd, bundle.architecture_frontmatter)
        except (OSError, ValueError) as exc:
            click.echo(f"drift check failed: {exc}", err=True)
        else:
            if drift.is_stale:
                click.echo(
                    f"  cognition stale ({drift.reason}) — /analyze to refresh"
                )

    while True:
        try:
            line = input("▌ ")
        except (EOFError, KeyboardInterrupt):
            click.echo()
            try:
                conventions.run_on_clean_exit(
                    ctx,
                    history=ctx.history,
                    record=record,
                    memory_store=ctx.memory_store,
                )
            except Exception as exc:  # noqa: BLE001
                click.echo(f"conventions extraction skipped: {exc}", err=True)
            return
        line = line.strip()
        if not line:
            continue

        # Slash commands.
        if line.startswith("/"):
            try:
                handled = slash_registry.dispatch(ctx, line)
            except ValueError as exc:
                click.echo(str(exc), err=True)
                continue
            if ctx.should_exit:
                return
            if handled:
                cfg = get_config()
                continue
        if line.startswith("/"):
            click.echo(f"unknown command: {line}. /help for list.", err=True)
            continue

        if _classify_intent(line) == "analyze":
            skill = skill_registry.get("analyze")
            if skill is not None:
                skill.handler(ctx, [])
            continue

        renderer.show_user(line)
        try:
            run_turn = _resolve_run_turn(cwd)
            result = asyncio.run(
                run_turn(
                    line,
                    tools=tools,
                    cwd=cwd,
                    renderer=renderer,
                    model=cfg.default_model,
                    history=ctx.history,
                    permissions=gate,
                    provider=provider,
                    session_id=record.id,
                    cognition=bundle,
                    prior_context=ctx.prior_context,
                    voss_md_text=ctx.voss_md_text,
                )
            )
            # prior_context is one-shot: only the first turn rehydrates it.
            ctx.prior_context = None
        except Exception as e:  # noqa: BLE001
            click.echo(f"error: {e}", err=True)
            continue
        ctx.last_plan = result.plan
        if result.run is not None:
            record.runs.append(asdict(result.run))
        ctx.total_cost += result.cost_usd
        renderer.show_final(
            result.final, confidence=result.confidence, cost_usd=result.cost_usd
        )


# ---------------------------------------------------------------------------
# login / logout — credential setup
# ---------------------------------------------------------------------------


@click.command("login")
def login_cmd() -> None:
    """Launch the interactive sign-in wizard.

    Walks through Claude Code OAuth, Codex OAuth, or pasting an API key
    (persisted to the OS keychain via `keyring`). Idempotent — running it
    again over an existing credential just lets the user switch paths.
    """
    from . import login_wizard

    if not login_wizard.stdin_is_interactive():
        click.echo(
            "voss login requires an interactive terminal. Set ANTHROPIC_API_KEY "
            "or OPENAI_API_KEY for non-interactive use.",
            err=True,
        )
        sys.exit(2)
    res = login_wizard.run_login_wizard(reason="voss login")
    if res is None:
        sys.exit(2)


@click.command("logout")
@click.argument("provider", type=click.Choice(["anthropic", "openai"]))
def logout_cmd(provider: str) -> None:
    """Remove a voss-stored API key from the OS keychain.

    Does NOT touch Claude Code (~/.claude/.credentials.json) or Codex
    (~/.codex/auth.json) — manage those via their own CLIs.
    """
    removed = auth_mod.delete_voss_creds(provider)  # type: ignore[arg-type]
    if removed:
        click.echo(f"voss logout: cleared keyring entry for `{provider}`")
    else:
        click.echo(
            f"voss logout: no `{provider}` entry in keyring (or backend unavailable)",
            err=True,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# doctor — diagnostics
# ---------------------------------------------------------------------------


@click.command("doctor")
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root to check.",
)
def doctor_cmd(cwd_str: str) -> None:
    """Diagnose harness setup. Diagnose-only; never executes fixes (D-13)."""
    from . import diagnostics as diag

    cwd = Path(cwd_str).resolve()
    results = diag.run_all_checks(cwd)

    glyph = {
        diag.CheckResult.OK: ("✓", "green"),
        diag.CheckResult.WARN: ("⚠", "yellow"),
        diag.CheckResult.FAIL: ("✗", "red"),
    }
    name_width = max(len(c.name) for c in results) + 2
    for c in results:
        g, color = glyph[c.result]
        click.echo(f"  {click.style(g, fg=color)}  {c.name:<{name_width}} {c.detail}")
        if c.fix and c.result is not diag.CheckResult.OK:
            click.echo(f"     → {c.fix}")

    # M2-06: appended cognition rows (D-11 #8/#9, D-12).
    bundle = cognition_mod.load(cwd)
    click.echo(f"  {'.voss/ initialized':<20}: {'yes' if bundle.initialized else 'no'}")
    if bundle.initialized and bundle.architecture_frontmatter:
        try:
            drift = cognition_mod.drift_check(cwd, bundle.architecture_frontmatter)
        except (OSError, ValueError) as exc:
            click.echo(f"  {'cognition staleness':<20}: error ({exc})")
        else:
            if drift.is_stale:
                click.echo(
                    f"  {'cognition staleness':<20}: stale ({drift.reason})"
                )
            else:
                click.echo(f"  {'cognition staleness':<20}: fresh")
    else:
        click.echo(f"  {'cognition staleness':<20}: n/a")
    legacy_dir = session_store.legacy_state_dir()
    legacy_count = (
        len(list(legacy_dir.glob("*.json"))) if legacy_dir.exists() else 0
    )
    if legacy_count:
        click.echo(
            f"  {'legacy sessions':<20}: {legacy_count} (read-only via voss sessions --all)"
        )
    else:
        click.echo(f"  {'legacy sessions':<20}: 0")

    code = diag.aggregate_exit_code(results)

    warns = [c for c in results if c.result is diag.CheckResult.WARN]
    fails = [c for c in results if c.result is diag.CheckResult.FAIL]
    if code != 0:
        click.echo("\nfailed checks. fix above and re-run.", err=True)
    elif warns and not fails:
        # D-14: WARN-only runs exit 0 but surface a one-line stderr summary
        # so CI / shell prompts can notice informational misses.
        names = ", ".join(c.name for c in warns)
        plural = "warning" if len(warns) == 1 else "warnings"
        click.echo(f"doctor: {len(warns)} {plural} ({names})", err=True)
    sys.exit(code)


def _print_slash_help(registry: SlashRegistry | None = None) -> None:
    registry = registry or _build_slash_registry()
    click.echo("\n".join(registry.help_lines()))


@click.command("sessions")
@click.option(
    "--all",
    "--global",
    "include_legacy",
    is_flag=True,
    help="Include legacy sessions from ~/.local/state/voss/sessions/.",
)
def sessions_cmd(include_legacy: bool) -> None:
    """List saved agent sessions (cwd-scoped; --all merges legacy XDG dir)."""
    cwd = Path.cwd()
    records = session_store.list_sessions(cwd=cwd, include_legacy=include_legacy)
    if not records:
        click.echo("(no sessions)")
        return
    for r in records:
        tag = "[legacy] " if getattr(r, "_legacy", False) else ""
        click.echo(
            f"  {tag}{r.id[:8]}  {r.updated_at}  {r.model:<28}  {r.first_task()}"
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
@click.option("--plain", "plain", is_flag=True, help="Use line-streamed renderer; bypass TUI.")
@click.option(
    "--no-unicode",
    "no_unicode",
    is_flag=True,
    help="Use ASCII fallback for TUI glyphs (sets VOSS_NO_UNICODE=1).",
)
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
    plain: bool,
    no_unicode: bool,
    auth_pref: str,
) -> None:
    """Resume a saved session by id-prefix or name."""
    _apply_no_unicode_env(no_unicode)
    try:
        record, history = session_store.load(session_id_or_name, cwd=Path.cwd())
    except (FileNotFoundError, ValueError) as e:
        click.echo(f"resume failed: {e}", err=True)
        sys.exit(1)
    cwd = Path(record.cwd)
    if record.model:
        configure(default_model=record.model)
    res, provider = _resolve_auth_or_die(auth_pref)
    prior = record.runs[-1] if record.runs else None
    _run_repl(
        cwd=cwd,
        json_mode=json_mode,
        plain=plain,
        mode=mode,
        history=history,
        record=record,
        provider=provider,
        auth_detail=f"{res.source} — {res.detail}",
        prior_context=prior,
    )


# ---------------------------------------------------------------------------
# tools — registry table
# ---------------------------------------------------------------------------


@click.command("tools")
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
def tools_cmd(cwd_str: str) -> None:
    """List registered harness tools."""
    cwd = Path(cwd_str).resolve()
    tools = make_toolset(cwd)
    name_w = max(len(n) for n in tools)
    click.echo(f"  {'name':<{name_w}}  {'mut':<5}  description")
    click.echo(f"  {'-' * name_w}  {'-' * 5}  {'-' * 40}")
    for name in sorted(tools):
        entry = tools[name]
        mut = "yes" if entry.is_mutating else "no"
        desc = entry.description
        if len(desc) > 60:
            desc = desc[:59] + "…"
        click.echo(f"  {name:<{name_w}}  {mut:<5}  {desc}")


def _extension_context(
    *,
    cwd: Path,
    provider: ModelProvider | None = None,
    renderer=None,
    gate: PermissionGate | None = None,
) -> SimpleNamespace:
    skill_registry = default_skill_registry()
    subagent_registry = default_subagent_registry()
    slash_registry = _build_slash_registry()
    tools = make_toolset(cwd)
    renderer = renderer or make_renderer(json_mode=False)
    gate = gate or PermissionGate(mode="edit", store=PermissionStore.load(cwd))
    ctx = SimpleNamespace(
        cwd=cwd,
        renderer=renderer,
        tools=tools,
        gate=gate,
        history=EpisodicMemory(capacity=40),
        record=session_store.SessionRecord.new(cwd=cwd, model=get_config().default_model),
        provider=provider,
        skill_registry=skill_registry,
        subagent_registry=subagent_registry,
        slash_registry=slash_registry,
        cognition=cognition_mod.load(cwd),
        prior_context=None,
        last_plan=None,
        total_cost=0.0,
    )
    if provider is not None:
        attach_subagent_tool(
            tools,
            registry=subagent_registry,
            cwd=cwd,
            renderer=renderer,
            provider=provider,
            model=lambda: get_config().default_model,
            gate=gate,
            cognition=ctx.cognition,
        )
    return ctx


@click.command("plugins")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def plugins_cmd(cwd_str: str) -> None:
    """List plugin manifests."""
    ctx = _extension_context(cwd=Path(cwd_str).resolve())
    _print_plugins(ctx)  # type: ignore[arg-type]


@click.group("plugin")
def plugin_group() -> None:
    """Manage plugin manifest enablement."""


@plugin_group.command("enable")
@click.argument("plugin_id")
def plugin_enable_cmd(plugin_id: str) -> None:
    path = set_plugin_enabled(plugin_id, True)
    click.echo(f"plugin {plugin_id} enabled: {path}")


@plugin_group.command("disable")
@click.argument("plugin_id")
def plugin_disable_cmd(plugin_id: str) -> None:
    path = set_plugin_enabled(plugin_id, False)
    click.echo(f"plugin {plugin_id} disabled: {path}")


@click.command("skills")
def skills_cmd() -> None:
    """List registered skills."""
    ctx = _extension_context(cwd=Path.cwd())
    _print_skills(ctx)  # type: ignore[arg-type]


@click.group("skill")
def skill_group() -> None:
    """Run registered skills."""


@skill_group.command("run")
@click.argument("skill_id")
@click.argument("args", nargs=-1)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--model", default=None)
@click.option("--auth", "auth_pref", type=click.Choice(AUTH_CHOICES), default="auto")
def skill_run_cmd(
    skill_id: str,
    args: tuple[str, ...],
    cwd_str: str,
    model: str | None,
    auth_pref: str,
) -> None:
    """Run a registered skill."""
    cwd = Path(cwd_str).resolve()
    _resolve_default_model(model)
    _res, provider = _resolve_auth_or_die(auth_pref)
    ctx = _extension_context(cwd=cwd, provider=provider)
    entry = ctx.skill_registry.get(skill_id)
    if entry is None:
        raise click.ClickException(f"unknown skill: {skill_id}")
    entry.handler(ctx, list(args))


@click.command("agents")
def agents_cmd() -> None:
    """List registered subagents."""
    ctx = _extension_context(cwd=Path.cwd())
    _print_agents(ctx)  # type: ignore[arg-type]


@click.group("agent")
def agent_group() -> None:
    """Run registered subagents."""


@agent_group.command("spawn")
@click.argument("agent_id")
@click.argument("task", nargs=-1, required=True)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--model", default=None)
@click.option("--auth", "auth_pref", type=click.Choice(AUTH_CHOICES), default="auto")
@click.option("--mode", type=click.Choice(["plan", "edit", "auto"]), default="edit")
def agent_spawn_cmd(
    agent_id: str,
    task: tuple[str, ...],
    cwd_str: str,
    model: str | None,
    auth_pref: str,
    mode: str,
) -> None:
    """Spawn a registered subagent for one task."""
    cwd = Path(cwd_str).resolve()
    _resolve_default_model(model)
    _res, provider = _resolve_auth_or_die(auth_pref)
    _emit_harness_boot_telemetry(cwd, get_config().default_model)
    renderer = make_renderer(json_mode=False)
    gate = PermissionGate(mode=mode, store=PermissionStore.load(cwd), auto_yes=True)  # type: ignore[arg-type]
    registry = default_subagent_registry()
    result = asyncio.run(
        run_subagent(
            agent_id=agent_id,
            task=" ".join(task),
            registry=registry,
            cwd=cwd,
            renderer=renderer,
            provider=provider,
            model=get_config().default_model,
            gate=gate,
            cognition=cognition_mod.load(cwd),
        )
    )
    click.echo(result)


# ---------------------------------------------------------------------------
# config — open/show ~/.config/voss/config.toml
# ---------------------------------------------------------------------------


def _config_toml_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "voss" / "config.toml"


@click.command("config")
@click.option(
    "--show",
    is_flag=True,
    help="Print config to stdout instead of opening editor.",
)
@click.option(
    "--config-path",
    "config_path_override",
    default=None,
    type=click.Path(path_type=Path),
    help="Override config.toml location (testing).",
)
def config_cmd(show: bool, config_path_override: Path | None) -> None:
    """Open or show ~/.config/voss/config.toml."""
    path = config_path_override if config_path_override else _config_toml_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[harness]\n")
        path.chmod(0o600)

    if show:
        text = path.read_text()
        if text.strip():
            click.echo(text, nl=False)
        else:
            click.echo("(empty)")
        return

    editor = os.environ.get("EDITOR", "vi")
    try:
        subprocess.run([editor, str(path)], check=False)
    except OSError as e:
        click.echo(f"failed to launch editor {editor!r}: {e}", err=True)
        sys.exit(1)


@click.command("eval")
@click.option("--suite", default="golden", show_default=True, help="Evaluation suite name.")
@click.option("--stub", is_flag=True, help="Use deterministic stub provider.")
@click.option("--live", is_flag=True, help="Mark run as live provider evaluation.")
@click.option("-k", "k", default=1, show_default=True, type=int, help="Runs per task.")
@click.option(
    "--out",
    "out_path",
    default=None,
    type=click.Path(path_type=Path, file_okay=False),
    help="Output directory.",
)
@click.option("--judge-model", default=None, help="Override judge model.")
@click.option("--task", default=None, help="Run a single task id.")
@click.option(
    "--auth",
    "auth_pref",
    type=click.Choice(AUTH_CHOICES),
    default="auto",
    show_default=True,
    help="Credential source.",
)
def eval_cmd(
    suite: str,
    stub: bool,
    live: bool,
    k: int,
    out_path: Path,
    judge_model: str | None,
    task: str | None,
    auth_pref: str,
) -> None:
    """Run the golden evaluation suite."""
    from voss.eval.runner import run_suite

    run_suite(
        suite=suite,
        stub=stub,
        live=live,
        k=k,
        out=out_path,
        judge_model=judge_model,
        task=task,
        auth_pref=auth_pref,
    )


@click.group("logs")
def logs_group() -> None:
    """Tail NDJSON harness telemetry (written when VOSS_LOG=1 and VOSS_LOG_PATH is set)."""


@logs_group.command("watch")
@click.argument(
    "path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
)
@click.option(
    "--poll-interval",
    default=0.15,
    type=float,
    show_default=True,
    help="Sleep interval when no new lines are available.",
)
def logs_watch_cmd(path: Path, poll_interval: float) -> None:
    """Follow a log file while another process appends JSON lines (Ctrl-C to stop).

    Example — terminal A: VOSS_LOG=1 VOSS_LOG_PATH=.voss-cache/harness.ndjson voss chat

    Terminal B: voss logs watch .voss-cache/harness.ndjson
    """
    import time

    with path.open(encoding="utf-8") as fh:
        fh.seek(0, os.SEEK_END)
        try:
            while True:
                line = fh.readline()
                if line:
                    click.echo(line.rstrip("\n"))
                else:
                    time.sleep(max(poll_interval, 0.05))
        except KeyboardInterrupt:
            click.echo("", err=True)


AGENT_COMMANDS = (
    do_cmd,
    chat_cmd,
    edit_cmd,
    login_cmd,
    logout_cmd,
    doctor_cmd,
    sessions_cmd,
    resume_cmd,
    tools_cmd,
    plugins_cmd,
    plugin_group,
    skills_cmd,
    skill_group,
    agents_cmd,
    agent_group,
    memory_group,
    config_cmd,
    logs_group,
    eval_cmd,
)


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
            mode="plan",  # D-07: bare voss defaults to plan
            auth_pref="auto",
        )


register(main)


if __name__ == "__main__":
    main()
