"""Agent commands for the unified `voss` CLI.

Defines `do_cmd`, `chat_cmd`, `doctor_cmd` as standalone click Commands.
- `voss.cli` imports them and adds them to the compiler's `main` group.
- `python -m voss.harness` builds a small standalone group for testing.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import SimpleNamespace

import click
import psutil

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
from .sandbox import SandboxError, jail_path
from .multiagent import attach_multiagent_tools
from .skill_registry import SkillRegistry, default_skill_registry
from .slash import SlashCommand, SlashRegistry
from .subagents import (
    SubagentRegistry,
    attach_subagent_tool,
    default_subagent_registry,
    run_subagent,
)
from .tools import attach_memory_tools, make_toolset
from .voss_inspect import (
    load_run,
    render_budget_timeline,
    render_decision_sequence,
)

try:
    import litellm as _litellm  # type: ignore
except Exception:  # noqa: BLE001
    _litellm = None  # type: ignore[assignment]


def _bootstrap_runtime_config() -> None:
    """Wire on-disk [agent] config into the RuntimeConfig singleton.

    Runs once at module import. Pulls max_iterations (T1-04) and
    max_parallel_reads (T2-02 / PAR-05) from ~/.config/voss/config.toml
    and pushes them into the runtime via a single configure() call.
    Out-of-range / malformed values fall back to the dataclass defaults
    with a RuntimeWarning (see voss.harness.config getters).
    """
    from .config import get_allow_net, get_max_iterations, get_max_parallel_reads

    configure(
        max_iterations=get_max_iterations(),
        max_parallel_reads=get_max_parallel_reads(),
        allow_net=get_allow_net(),
    )


_NET_SESSION: "NetSession | None" = None


def _get_net_session() -> "NetSession":
    """Lazily construct the process-wide NetSession.

    Lazy so test-import never allocates an httpx client and the boot
    configure() stays construct-free (matches T1-04/T2-02 pattern).
    NetSession.__init__ registers itself with lifecycle for reap.
    """
    global _NET_SESSION
    if _NET_SESSION is None:
        from .config import get_net_rate_limits
        from .net import NetSession

        _NET_SESSION = NetSession(rate_overrides=get_net_rate_limits())
    return _NET_SESSION


_bootstrap_runtime_config()


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
    # T6 / SLASH-04 — session-scoped USD ceiling. None = unbounded.
    budget_usd: float | None = None
    project_index_text: str = ""
    # Git-backed undo/redo (OpenCode-leverage port): each /undo snapshots the
    # agent's content for the reverted files so /redo can restore them.
    redo_stack: list = field(default_factory=list)


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


def _apply_role_chain(provider, role: str, *, user_explicit: str | None = None):
    """Wrap the live provider in `role`'s fallback chain when one is configured
    (`[harness.roles.<role>]`). 429/quota on the primary then cascades to the
    next candidate within a turn. Returns the (possibly wrapped) provider and
    points `default_model` at the chain's primary. `--model` (user_explicit)
    wins and skips the override. Never raises — a missing chain or offline
    catalog leaves the provider untouched.
    """
    if user_explicit:
        return provider
    from . import roles

    try:
        built = roles.build_role_provider(role)
    except Exception:  # noqa: BLE001 — boot must never crash on catalog issues
        built = None
    if built is None:
        return provider
    new_provider, primary = built
    configure(default_model=primary)
    return new_provider


def _apply_boot_model(provider, *, user_explicit: str | None):
    """Honor a persisted catalog-routed selection (/models) + default role chain.

    When `[harness] preferred_provider` is set and the model resolves in the
    cached catalog, rebuild the live provider for it and configure the routed
    model string (e.g. ``openai/gemma3:27b``). Then, if a `[harness.roles.default]`
    chain is configured, wrap the result in its fallback cascade. `--model` wins
    and skips both overrides. Never raises — an offline/missing catalog leaves
    the auth-resolved provider in place.
    """
    if user_explicit:
        return provider
    from . import model_router

    try:
        routed = model_router.boot_routed_provider()
    except Exception:  # noqa: BLE001 — boot must never crash on catalog issues
        routed = None
    if routed is not None:
        new_provider, model_string = routed
        configure(default_model=model_string)
        provider = new_provider
    return _apply_role_chain(provider, "default")


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


def _run_turn_cancellable(coro, *, renderer):
    """Run an agent-turn coroutine with cancel-on-Ctrl-C semantics (T1-06).

    Replaces `asyncio.run(coro)` everywhere. Steps:
      1. Create a new event loop and a Task wrapping the coro.
      2. If `renderer.app` exists (TextualRenderer only — see
         voss/harness/tui/renderer.py:47), register the Task on that app so
         VossTUIApp.action_interrupt can cancel it.
      3. Install a SIGINT handler so Ctrl-C in the headless path also
         cancels the Task. On platforms where add_signal_handler raises
         NotImplementedError (Windows) or RuntimeError (non-main thread),
         fall back without raising.
      4. Run the loop until the Task completes.
      5. Return the result. Re-raise CancelledError as click.Abort so the
         CLI exits with a non-zero status on user-initiated cancel.
    """
    import signal as _signal

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    task = loop.create_task(coro)

    app = getattr(renderer, "app", None)
    if app is not None and hasattr(app, "register_turn_task"):
        app.register_turn_task(task)

    handler_installed = False
    try:
        try:
            loop.add_signal_handler(_signal.SIGINT, task.cancel)
            handler_installed = True
        except (NotImplementedError, RuntimeError):
            # Windows / non-main-thread fallback; KeyboardInterrupt still
            # reaches the loop via the default handler.
            pass
        try:
            return loop.run_until_complete(task)
        except asyncio.CancelledError:
            raise click.Abort()
    finally:
        if handler_installed:
            try:
                loop.remove_signal_handler(_signal.SIGINT)
            except Exception:  # noqa: BLE001
                pass
        loop.close()
        asyncio.set_event_loop(None)


async def _run_turn_with_teardown(turn_coro, teardown):
    """Await one chat-turn coroutine, then ALWAYS run the M13 orphan-teardown.

    M13-06 / T-M13-02: child sub-agents are detached `asyncio.create_task`
    coroutines on the SAME event loop that runs the parent turn. The plain
    path's `_run_turn_cancellable` closes that loop after the turn, so the
    defensive `_teardown_orphans` (cancel + release + collapse un-gathered
    children) MUST run on this loop, in this coroutine's `finally`, before the
    loop is torn down — otherwise an un-gathered or cancelled turn would leak
    orphan child tasks/panels into the next turn. The teardown is itself
    idempotent (a clean turn that called `subagent_gather` leaves nothing to
    do), so running it unconditionally per turn is safe.
    """
    try:
        return await turn_coro
    finally:
        if teardown is not None:
            try:
                await teardown()
            except Exception:  # noqa: BLE001 — teardown must never mask the turn
                pass


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
    # Honor a persisted default (`[harness] auth`) when the caller didn't force
    # a specific source. Lets `voss chat` always use e.g. codex even when
    # OPENAI_API_KEY is exported in the shell. Explicit --auth=<x> still wins.
    if preference == "auto":
        from . import config as _hc

        saved = _hc.load_harness_config().get("auth")
        if saved in AUTH_CHOICES and saved != "auto":
            preference = saved

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
        click.echo(
            "  [deprecated: claude-oauth (Claude subscription) is no longer "
            "supported. Anthropic prohibits subscription OAuth tokens in "
            "third-party tools (Consumer ToS) and blocks them server-side since "
            "2026-01-09, so calls will likely fail. Use --auth=api with "
            "ANTHROPIC_API_KEY, or --auth=codex for a ChatGPT subscription.]",
            err=True,
        )
        provider: ModelProvider = AnthropicOAuthProvider(res.anthropic_oauth)  # type: ignore[arg-type]
    elif res.source == "codex-oauth":
        click.echo(
            "  [codex-oauth: using your ChatGPT subscription via "
            "chatgpt.com/backend-api/codex (unofficial endpoint; $0 per-token "
            "but ToS-gray and may change without notice).]",
            err=True,
        )
        provider = OpenAIOAuthProvider(res.codex_oauth)  # type: ignore[arg-type]
        cfg = get_config()
        # The ChatGPT-account Codex backend only accepts gpt-5.x model ids
        # (gpt-5/gpt-5-codex/gpt-4o are rejected). Snap any non-codex default
        # to the current best, gpt-5.5; leave an explicit gpt-5.x choice alone.
        if not cfg.default_model.startswith("gpt-5."):
            configure(default_model="gpt-5.5")
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


def _render_probable_inspect(
    cwd: Path, session_id_or_name: str, decision_index: int | None
) -> str:
    run = load_run(cwd, session_id_or_name)
    return render_decision_sequence(run, decision_index=decision_index)


def _render_budget_inspect(cwd: Path, session_id_or_name: str) -> str:
    run = load_run(cwd, session_id_or_name)
    return render_budget_timeline(run)


def _render_voss_py_diff(cwd: Path, source: str) -> str:
    source = source.strip()
    if not source:
        raise ValueError("missing source: expected .voss file")
    try:
        path = jail_path(cwd, source)
    except SandboxError as exc:
        raise ValueError(f"path outside cwd: {source}") from exc
    if not path.exists():
        raise FileNotFoundError(f"not found: {source}")
    if path.is_dir():
        raise ValueError(f"expected .voss file, got directory: {source}")
    if path.suffix != ".voss":
        raise ValueError(f"expected .voss source file, got {source}")
    try:
        from .voss_diff import render_voss_py_diff
    except ModuleNotFoundError as exc:
        if exc.name == "voss.harness.voss_diff":
            raise ValueError("voss diff core unavailable") from exc
        raise
    try:
        return render_voss_py_diff(path, cwd=cwd)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(str(exc)) from exc


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


def _run_async_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: list[object] = []
    error: list[BaseException] = []

    def _runner() -> None:
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:  # noqa: BLE001
            error.append(exc)

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return result[0] if result else None


def _get_code_service(cwd: Path, session_id: str | None = None):
    from voss.harness.code.service import CodeIntelService

    return CodeIntelService.for_cwd(cwd, session_id=session_id)


def _looks_like_project_root(cwd: Path) -> bool:
    try:
        if cwd.resolve() == Path.home().resolve():
            return False
    except OSError:
        pass
    markers = (
        ".git",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "deno.json",
        "pnpm-workspace.yaml",
    )
    return any((cwd / marker).exists() for marker in markers)


def _render_project_index_text(cwd: Path, session_id: str | None = None) -> str:
    if not _looks_like_project_root(cwd):
        return ""
    try:
        from voss.harness.code.context import render_project_index_section

        svc = _get_code_service(cwd, session_id=session_id)
        return render_project_index_section(svc.get_project_index_summary()) or ""
    except Exception:
        return ""


def _show_code_intel_results(ctx: ReplContext, query: str, items: list[dict]) -> None:
    renderer = getattr(ctx, "renderer", None)
    show = getattr(renderer, "show_code_intel_results", None)
    if callable(show):
        try:
            show(query, items)
        except Exception:
            pass


def _symbol(ctx: ReplContext, args: list[str], _line: str) -> None:
    if not args or args[0] in ("--help", "-h"):
        click.echo("usage: /symbol <name>   (M10 code intelligence — index)")
        return
    symbol = args[0]
    svc = _get_code_service(ctx.cwd, session_id=ctx.record.id)
    res = svc.find_symbols(symbol, max_results=10)
    items = res.get("items", [])
    if not items:
        click.echo(f"no symbols found for {symbol}")
        _show_code_intel_results(ctx, f"/symbol {symbol}", [])
        return
    for item in items:
        click.echo(
            f"{item['name']} {item['file']}:{item['line']} "
            f"[{item.get('language', 'unknown')} {item.get('source', 'index')}]"
        )
    _show_code_intel_results(ctx, f"/symbol {symbol}", items)


def _refs(ctx: ReplContext, args: list[str], _line: str) -> None:
    if not args or args[0] in ("--help", "-h"):
        click.echo("usage: /refs <symbol>   (M10 code intelligence — index + LSP)")
        return
    symbol = args[0]
    svc = _get_code_service(ctx.cwd, session_id=ctx.record.id)
    res = _run_async_sync(svc.find_references(symbol, max_results=10))
    items = res.get("items", []) if isinstance(res, dict) else []
    if not items:
        click.echo(f"no references found for {symbol}")
        _show_code_intel_results(ctx, f"/refs {symbol}", [])
        return
    for item in items:
        click.echo(
            f"{item['file']}:{item['line']} "
            f"[{item.get('language', 'unknown')} {item.get('source', 'regex')}] "
            f"{item.get('context', '')}"
        )
    _show_code_intel_results(ctx, f"/refs {symbol}", items)


def _refresh(ctx: ReplContext, args: list[str], _line: str) -> None:
    if args and args[0] in ("--help", "-h"):
        click.echo("usage: /refresh   rebuild code index under .voss-cache/code/")
        return
    svc = _get_code_service(ctx.cwd, session_id=ctx.record.id)
    res = _run_async_sync(svc.code_refresh())
    if isinstance(res, dict) and res.get("result") == "ok":
        ctx.project_index_text = _render_project_index_text(ctx.cwd, session_id=ctx.record.id)
        summary = svc.get_project_index_summary()
        if summary is not None:
            click.echo(
                f"refreshed code index: {summary.file_count} files, "
                f"{summary.symbol_count} symbols"
            )
        else:
            click.echo("refreshed code index")
        renderer = getattr(ctx, "renderer", None)
        show = getattr(renderer, "show_code_intel_tree", None)
        if callable(show) and summary is not None:
            try:
                show([
                    {"label": path, "count": count}
                    for path, count in summary.top_modules
                ])
            except Exception:
                pass
        return
    click.echo(f"refresh failed: {res}", err=True)


def _build_slash_registry() -> SlashRegistry:
    registry = SlashRegistry()

    def _exit(ctx: ReplContext, _args: list[str], _line: str) -> None:
        ctx.should_exit = True

    def _help(ctx: ReplContext, _args: list[str], _line: str) -> None:
        _print_slash_help(ctx.slash_registry)

    def _clear(ctx: ReplContext, _args: list[str], _line: str) -> None:
        ctx.history = EpisodicMemory(capacity=40)
        click.echo("episodic memory cleared.")

    def _cost(ctx: ReplContext, args: list[str], _line: str) -> None:
        # T6 / SLASH-07: support --by-model and --by-tool flags.
        flags = {a.lstrip("-") for a in args}
        if "by-tool" in flags:
            click.echo(
                "  /cost --by-tool: per-tool cost tracking lands with T6 SLASH-07. "
                "Recorder doesn't yet attribute provider cost to individual tool calls."
            )
            return
        if "by-model" in flags:
            # SessionRecord pins one model per session today. Group by
            # record.model from each run; falls back to "unknown".
            by_model: dict[str, float] = {}
            for run in ctx.record.runs:
                m = (
                    ctx.record.model
                    or get_config().default_model
                    or "unknown"
                )
                by_model[m] = by_model.get(m, 0.0) + float(run.get("cost_usd", 0.0))
            if not by_model:
                click.echo(f"session cost: ${ctx.total_cost:.4f} (no runs yet)")
                return
            width = max(len(m) for m in by_model)
            click.echo(f"session cost: ${ctx.total_cost:.4f}")
            for m, c in sorted(by_model.items(), key=lambda kv: -kv[1]):
                click.echo(f"  {m:<{width}}  ${c:.4f}")
            return
        # Default: flat total (existing behavior).
        budget = ctx.budget_usd
        if budget is not None:
            pct = (ctx.total_cost / budget * 100.0) if budget > 0 else 0.0
            click.echo(
                f"session cost: ${ctx.total_cost:.4f} / ${budget:.2f} "
                f"({pct:.1f}%)"
            )
        else:
            click.echo(f"session cost: ${ctx.total_cost:.4f}")

    def _budget(ctx: ReplContext, args: list[str], _line: str) -> None:
        # T6 / SLASH-04. No args → show current. One arg → set USD ceiling.
        if not args:
            if ctx.budget_usd is None:
                click.echo("  budget: unbounded")
            else:
                click.echo(
                    f"  budget: ${ctx.budget_usd:.2f} "
                    f"(used ${ctx.total_cost:.4f})"
                )
            return
        try:
            new_budget = float(args[0].lstrip("$"))
        except ValueError:
            click.echo("usage: /budget <usd>  (e.g. /budget 5.00)", err=True)
            return
        if new_budget < 0:
            click.echo("budget must be non-negative", err=True)
            return
        ctx.budget_usd = new_budget
        if new_budget == 0:
            click.echo("  budget: cleared (unbounded)")
            ctx.budget_usd = None
            return
        warn = (
            "  ⚠ already over budget"
            if ctx.total_cost > new_budget
            else ""
        )
        click.echo(
            f"  budget: ${new_budget:.2f} (used ${ctx.total_cost:.4f}){warn}"
        )

    def _probable(ctx: ReplContext, args: list[str], _line: str) -> None:
        raw_args = list(args)
        args, decision_raw = _pop_flag_value(raw_args, "--decision")
        if "--decision" in raw_args and decision_raw is None:
            click.echo(
                "usage: /probable <session-id-or-name> [--decision N]",
                err=True,
            )
            return
        if len(args) > 1:
            click.echo(
                "usage: /probable <session-id-or-name> [--decision N]",
                err=True,
            )
            return
        try:
            decision_index = (
                int(decision_raw) if decision_raw is not None else None
            )
        except ValueError:
            click.echo("--decision must be an integer", err=True)
            return
        target = args[0] if args else ctx.record.id
        try:
            text = _render_probable_inspect(ctx.cwd, target, decision_index)
        except (FileNotFoundError, ValueError, IndexError) as exc:
            click.echo(f"/probable failed: {exc}", err=True)
            return
        show = getattr(getattr(ctx, "renderer", None), "show_probable_inspector", None)
        if callable(show):
            show(text)
        else:
            click.echo(text)

    def _btrace(ctx: ReplContext, args: list[str], _line: str) -> None:
        if len(args) > 1:
            click.echo("usage: /btrace <session-id-or-name>", err=True)
            return
        target = args[0] if args else ctx.record.id
        try:
            text = _render_budget_inspect(ctx.cwd, target)
        except (FileNotFoundError, ValueError, IndexError) as exc:
            click.echo(f"/btrace failed: {exc}", err=True)
            return
        show = getattr(getattr(ctx, "renderer", None), "show_budget_trace", None)
        if callable(show):
            show(text)
        else:
            click.echo(text)

    def _vdiff(ctx: ReplContext, args: list[str], _line: str) -> None:
        if len(args) != 1:
            click.echo("usage: /vdiff <file.voss>", err=True)
            return
        try:
            text = _render_voss_py_diff(ctx.cwd, args[0])
        except (FileNotFoundError, ValueError) as exc:
            click.echo(f"/vdiff failed: {exc}", err=True)
            return
        show = getattr(getattr(ctx, "renderer", None), "show_voss_py_diff", None)
        if callable(show):
            show(text)
        else:
            click.echo(text)

    def _why(ctx: ReplContext, _args: list[str], _line: str) -> None:
        # T6 / SLASH-06. Render last plan's rationale + per-step why +
        # confidence. No provider call — reads ctx.last_plan only.
        plan = ctx.last_plan
        if plan is None:
            click.echo("no plan yet — run a turn first", err=True)
            return
        click.echo(f"  rationale: {plan.rationale}")
        click.echo(f"  confidence: {plan.confidence:.2f}")
        if plan.steps:
            click.echo("  steps:")
            for i, step in enumerate(plan.steps, 1):
                why = (step.why or "").strip()
                tag = f" — {why}" if why else ""
                click.echo(f"    {i}. {step.name}{tag}")
        if plan.open_question:
            click.echo(f"  open question: {plan.open_question}")
        if plan.final_when_done:
            click.echo(f"  final-when-done: {plan.final_when_done}")

    def _diff(ctx: ReplContext, args: list[str], _line: str) -> None:
        # T6 / SLASH-01. v0.1 applies edits immediately (no queued-diff
        # store yet — that lands with T1 iteration loop). Surface honest
        # diff against the working tree via `git diff`.
        cmd = ["git", "diff"]
        if args and args[0] in ("--staged", "--cached"):
            cmd.append("--cached")
            args = args[1:]
        cmd.extend(args)  # optional path filter
        try:
            out = subprocess.run(
                cmd,
                cwd=str(ctx.cwd),
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            click.echo(f"/diff failed: {exc}", err=True)
            return
        if out.returncode != 0 and out.stderr:
            click.echo(out.stderr.rstrip(), err=True)
            return
        body = out.stdout.rstrip()
        if not body:
            click.echo("  (no changes)")
            return
        click.echo(body)

    def _apply(_ctx: ReplContext, _args: list[str], _line: str) -> None:
        # T6 / SLASH-02. Honest stub: v0.1 has no pending-edit queue. Edits
        # commit immediately under PermissionGate. Real queued-apply lands
        # with T1 iteration loop (per ROADMAP). Surface this rather than
        # silently no-op.
        click.echo(
            "  /apply: v0.1 applies edits immediately under PermissionGate. "
            "Pending-edit queue + per-hunk approval lands with T1 + M9-05. "
            "Use /mode plan to dry-run, then /mode edit to commit."
        )

    def _discard(ctx: ReplContext, args: list[str], _line: str) -> None:
        # T6 / SLASH-03. v0.1 has no pending-edit queue; the meaningful
        # action is reverting files the agent changed in the most recent
        # run. Requires --confirm flag; lists files otherwise.
        if not ctx.record.runs:
            click.echo("  no runs yet — nothing to discard.")
            return
        last_run = ctx.record.runs[-1]
        changed = list(last_run.get("changed") or [])
        if not changed:
            click.echo("  last run changed no files — nothing to discard.")
            return
        if "--confirm" not in args:
            click.echo(
                "  /discard would `git checkout --` against the last run's "
                "changed files:"
            )
            for path in changed:
                click.echo(f"    {path}")
            click.echo("  re-run with --confirm to revert.")
            return
        try:
            out = subprocess.run(
                ["git", "checkout", "--", *changed],
                cwd=str(ctx.cwd),
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            click.echo(f"/discard failed: {exc}", err=True)
            return
        if out.returncode != 0:
            click.echo(
                (out.stderr or "git checkout failed").rstrip(), err=True
            )
            return
        click.echo(f"  reverted {len(changed)} file(s) via git checkout.")

    def _undo(ctx: ReplContext, _args: list[str], _line: str) -> None:
        # OpenCode-leverage port of /undo (ctrl+x u): git-backed revert of the
        # last run's file changes, but reversible — snapshot the agent's content
        # first so /redo can put it back. Unlike /discard, no --confirm (it's
        # undoable) and it records a redo entry.
        if not ctx.record.runs:
            click.echo("  no runs yet — nothing to undo.")
            return
        changed = list(ctx.record.runs[-1].get("changed") or [])
        if not changed:
            click.echo("  last run changed no files — nothing to undo.")
            return
        snapshot: dict[str, bytes | None] = {}
        for rel in changed:
            p = ctx.cwd / rel
            try:
                snapshot[rel] = p.read_bytes() if p.exists() else None
            except OSError:
                snapshot[rel] = None
        reverted: list[str] = []
        failed: list[str] = []
        for rel in changed:
            try:
                out = subprocess.run(
                    ["git", "checkout", "--", rel],
                    cwd=str(ctx.cwd),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                click.echo(f"/undo failed: {exc}", err=True)
                return
            (reverted if out.returncode == 0 else failed).append(rel)
        if reverted:
            ctx.redo_stack.append(
                {"reverted": reverted, "snapshot": snapshot}
            )
            click.echo(
                f"  undid {len(reverted)} file change(s) via git. /redo to restore."
            )
        if failed:
            click.echo(
                "  could not revert (untracked or not in git): "
                + ", ".join(failed),
                err=True,
            )

    def _redo(ctx: ReplContext, _args: list[str], _line: str) -> None:
        # Restore the agent's content captured by the most recent /undo.
        if not ctx.redo_stack:
            click.echo("  nothing to redo.")
            return
        entry = ctx.redo_stack.pop()
        snapshot = entry.get("snapshot", {})
        restored = 0
        for rel in entry.get("reverted", []):
            content = snapshot.get(rel)
            p = ctx.cwd / rel
            try:
                if content is None:
                    if p.exists():
                        p.unlink()
                else:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(content)
                restored += 1
            except OSError as exc:
                click.echo(f"  /redo: could not restore {rel}: {exc}", err=True)
        click.echo(f"  redid {restored} file change(s).")

    def _resume(ctx: ReplContext, args: list[str], _line: str) -> None:
        # T6 / SLASH-05. Live REPL resume: swap history + record without
        # restarting the process. Gate/cognition/tools stay bound to the
        # live cwd — cross-cwd resume still requires `voss resume <id>`.
        if not args:
            click.echo("usage: /resume <session-id-or-name>", err=True)
            return
        target = args[0]
        try:
            new_record, new_history = session_store.load(target, cwd=ctx.cwd)
        except (FileNotFoundError, ValueError) as exc:
            click.echo(f"/resume failed: {exc}", err=True)
            return
        if Path(new_record.cwd).resolve() != ctx.cwd.resolve():
            click.echo(
                f"  warning: session cwd is {new_record.cwd}; staying in "
                f"{ctx.cwd}. Cross-cwd resume requires `voss resume`.",
                err=True,
            )
        ctx.record = new_record
        ctx.history = new_history
        ctx.total_cost = new_record.total_cost_usd
        ctx.last_plan = None
        ctx.prior_context = new_record.runs[-1] if new_record.runs else None
        click.echo(
            f"  resumed: {new_record.name} "
            f"({len(new_record.turns)} turns, "
            f"${new_record.total_cost_usd:.4f})"
        )

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

    def _models(ctx: ReplContext, args: list[str], _line: str) -> None:
        """Catalog-driven model picker (models.dev). CLI: list/filter/select by
        name; the TUI gets the searchable modal in P4."""
        from . import config as harness_config
        from . import model_catalog, model_router

        try:
            groups = model_catalog.load_catalog()
        except Exception as exc:  # noqa: BLE001
            click.echo(f"  models catalog unavailable: {exc}", err=True)
            return
        connected = model_router.connected_providers(groups)
        current = get_config().default_model

        def _apply(entry) -> None:
            provider, model_str, key_present = model_router.prepare_model(entry)
            if not key_present:
                click.echo(
                    f"  {entry.provider_label} needs an API key ({entry.env_key}). "
                    f"Set the env var or connect via the picker (ctrl+a, P5).",
                    err=True,
                )
                return
            configure(default_model=model_str)
            harness_config.set_preferred_routed(entry.id, entry.provider_id)
            from . import model_prefs

            model_prefs.record_recent(entry.provider_id, entry.id)
            ctx.provider = provider
            click.echo(f"  model: {entry.name} · {entry.provider_label} (persisted)")

        def _print(entries) -> None:
            last = None
            for m in entries:
                if m.provider_id != last:
                    mark = "" if connected.get(m.provider_id) else "  (needs key)"
                    click.echo(f"\n  {m.provider_label}{mark}")
                    last = m.provider_id
                tag = " · Free" if m.free else ""
                here = "  ←" if (m.id == current or f"openai/{m.id}" == current) else ""
                click.echo(f"    {m.id}{tag}{here}")

        # Bare `/models` in the TUI opens the searchable modal picker, with
        # Favorites + Recent sections pinned on top (models.dev catalog below).
        app = getattr(getattr(ctx, "renderer", None), "app", None)
        if not args and app is not None and app.__class__.__name__ == "VossTUIApp":
            from . import model_prefs
            from .model_catalog import ProviderGroup
            from .tui.widgets.model_picker_modal import ModelPickerModal

            def _resolve(pairs):
                out = []
                for pid, mid in pairs:
                    e = model_router.find_entry(groups, pid, mid)
                    if e is not None:
                        out.append(e)
                return out

            synth, syn_ids, conn2 = [], set(), dict(connected)
            fav = _resolve(model_prefs.favorites())
            if fav:
                synth.append(ProviderGroup("favorites", "Favorites", None, None, tuple(fav)))
                syn_ids.add("favorites")
                conn2["favorites"] = True
            rec = _resolve(model_prefs.recent())
            if rec:
                synth.append(ProviderGroup("recent", "Recent", None, None, tuple(rec)))
                syn_ids.add("recent")
                conn2["recent"] = True

            def _on_pick(entry) -> None:
                if entry is not None:
                    _apply(entry)

            app.push_screen(
                ModelPickerModal(
                    synth + groups, conn2, current, synthetic_ids=frozenset(syn_ids)
                ),
                _on_pick,
            )
            return

        # `/models set <id> [provider]` — non-interactive, works in CLI + TUI.
        if args and args[0] == "set":
            if len(args) < 2:
                click.echo("  usage: /models set <model-id> [provider-id]", err=True)
                return
            model_id = args[1]
            provider_id = args[2] if len(args) > 2 else None
            hits = model_router.find_by_id(groups, model_id, provider_id=provider_id)
            if not hits:
                click.echo(f"  no model '{model_id}'", err=True)
            elif len(hits) > 1:
                click.echo(
                    f"  '{model_id}' exists in {len(hits)} providers; add one of: "
                    + ", ".join(h.provider_id for h in hits),
                    err=True,
                )
            else:
                _apply(hits[0])
            return

        query = " ".join(args).strip()
        if query:
            matches = model_router.match_models(groups, query)
            if len(matches) == 1:
                _apply(matches[0])
            elif not matches:
                click.echo(f"  no models match '{query}'", err=True)
            else:
                click.echo(f"  {len(matches)} match '{query}':")
                _print(matches)
                click.echo("\n  refine, or `/models set <id> [provider]`")
            return

        # No args: full grouped list + hint.
        _print(model_router.flatten(groups))
        click.echo(
            f"\n  active: {current}\n"
            "  select: /models <query>  or  /models set <id> [provider]"
        )

    def _auth(ctx: ReplContext, args: list[str], _line: str) -> None:
        """Show or persist the default credential source (`[harness] auth`).

        Takes effect on the next launch. `/auth codex` -> plain `voss chat`
        uses the ChatGPT subscription even if OPENAI_API_KEY is exported.
        """
        from . import config as harness_config

        if not args:
            saved = harness_config.load_harness_config().get("auth") or "auto"
            click.echo(f"  default auth: {saved}")
            click.echo(f"  choices: {', '.join(AUTH_CHOICES)}")
            return
        pref = args[0].strip().lower()
        if pref not in AUTH_CHOICES:
            click.echo(f"  invalid: {pref}. choices: {', '.join(AUTH_CHOICES)}", err=True)
            return
        harness_config.set_preferred_auth(pref)
        click.echo(f"  default auth: {pref} (persisted — applies next launch)")

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
        SlashCommand(
            "/cost",
            "session cost so far ([--by-model | --by-tool])",
            _cost,
        ),
        SlashCommand(
            "/budget",
            "show or set session USD ceiling: /budget [<usd>]",
            _budget,
        ),
        SlashCommand(
            "/probable",
            "inspect recorded decisions: /probable [session] [--decision N]",
            _probable,
        ),
        SlashCommand(
            "/btrace",
            "inspect recorded budget timeline: /btrace [session]",
            _btrace,
        ),
        SlashCommand(
            "/vdiff",
            "show source vs generated Python: /vdiff <file.voss>",
            _vdiff,
        ),
        SlashCommand(
            "/why",
            "explain the last plan (rationale, confidence, step why)",
            _why,
        ),
        SlashCommand(
            "/diff",
            "show working-tree diff: /diff [--staged] [<path>]",
            _diff,
        ),
        SlashCommand(
            "/apply",
            "no-op stub — edits commit immediately in v0.1 (T1 will queue)",
            _apply,
        ),
        SlashCommand(
            "/discard",
            "revert last run's changed files via `git checkout` (--confirm)",
            _discard,
            mutating=True,
        ),
        SlashCommand(
            "/undo",
            "git-backed revert of the last run's file changes (reversible via /redo)",
            _undo,
            mutating=True,
        ),
        SlashCommand(
            "/redo",
            "restore the file changes undone by the most recent /undo",
            _redo,
            mutating=True,
        ),
        SlashCommand(
            "/resume",
            "live-resume a saved session by id/name (same cwd only)",
            _resume,
            mutating=True,
        ),
        SlashCommand("/tools", "list registered tools", _tools),
        SlashCommand("/login", "launch sign-in wizard (or `/login status` for cred status)", _login),
        SlashCommand("/model", "list providers or switch (persists to config.toml)", _model),
        SlashCommand("/models", "pick a model from the models.dev catalog (Zen, Ollama Cloud, …)", _models),
        SlashCommand("/auth", "show/set default credential source (auto|claude|codex|api|none)", _auth),
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
        # M10-04 code intelligence slash surface
        SlashCommand("/symbol", "find symbols matching <name> (uses index + LSP)", _symbol),
        SlashCommand("/refs", "find references to <symbol>", _refs),
        SlashCommand("/refresh", "rebuild code index (and optionally refresh cognition)", _refresh, mutating=False),
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


def _repl_prompt() -> str:
    glyph = ">" if os.environ.get("VOSS_NO_UNICODE") == "1" else "❯"
    if os.environ.get("NO_COLOR") == "1" or not sys.stdout.isatty():
        return f"{glyph} "
    return f"\x1b[1;38;2;255;91;31m{glyph}\x1b[0m "


def _provider_label(auth_detail: str) -> str:
    lower = auth_detail.lower()
    if "openai" in lower or "codex" in lower:
        return "OpenAI"
    if "anthropic" in lower or "claude" in lower:
        return "Anthropic"
    return ""


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
    "--allow-net/--no-allow-net",
    "allow_net",
    default=None,
    help=(
        "Enable (--allow-net) or disable (--no-allow-net) network tools "
        "(web_fetch, web_search, MCP) for this session. When neither is "
        "passed, falls back to [tools] allow_net in config.toml. NOTE: "
        "SPEC NET-05d criterion `--allow-net=false` is satisfied via the "
        "click-idiomatic `--no-allow-net` form (click flag pairs do not "
        "accept `--flag=value` syntax)."
    ),
)
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
    allow_net: bool | None,
    auth_pref: str,
) -> None:
    """Run a one-shot agent task and print the final answer.

    Stdin (when piped) is appended to the task as additional context.
    """
    cwd = Path(cwd_str).resolve()
    _apply_no_unicode_env(no_unicode)
    _resolve_default_model(model)
    if allow_net is True:
        configure(allow_net=True)
    elif allow_net is False:
        configure(allow_net=False)
    # else allow_net is None: TOML setting applied at bootstrap wins
    res, provider = _resolve_auth_or_die(auth_pref)
    provider = _apply_boot_model(provider, user_explicit=model)
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
    # T5: deliberate _nosession — do_record is defined later; one-shot voss do
    # bg jobs are reaped at process exit, with no voss jobs contract.
    tools = make_toolset(cwd, renderer=renderer, net=_get_net_session())
    voss_md.ensure_migrated(cwd)
    do_bundle = cognition_mod.load(cwd)
    voss_md_text = voss_md.read_and_inject(cwd)
    project_index_text = _render_project_index_text(cwd)
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
    attach_memory_tools(tools, store=do_memory_store, session_id=do_record.id)

    renderer.banner(model=cfg.default_model, cwd=cwd, git_status=_git_status(cwd))
    click.echo(f"  [auth: {res.source} — {res.detail}]")
    renderer.show_user(text)

    run_turn = _resolve_run_turn(cwd)
    result = _run_turn_cancellable(
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
            project_index_text=project_index_text,
        ),
        renderer=renderer,
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
    "--allow-net/--no-allow-net",
    "allow_net",
    default=None,
    help=(
        "Enable (--allow-net) or disable (--no-allow-net) network tools "
        "(web_fetch, web_search, MCP) for this session. When neither is "
        "passed, falls back to [tools] allow_net in config.toml. NOTE: "
        "SPEC NET-05d criterion `--allow-net=false` is satisfied via the "
        "click-idiomatic `--no-allow-net` form (click flag pairs do not "
        "accept `--flag=value` syntax)."
    ),
)
@click.option(
    "--auth",
    "auth_pref",
    type=click.Choice(AUTH_CHOICES),
    default="auto",
    help="Credential source.",
)
@click.option(
    "--keep-logs",
    "keep_logs",
    is_flag=True,
    default=False,
    help="Keep background-job logs/sidecars on session exit (default: reap them).",
)
def chat_cmd(
    model: str | None,
    cwd_str: str,
    json_mode: bool,
    plain: bool,
    no_unicode: bool,
    mode: str,
    allow_net: bool | None,
    auth_pref: str,
    keep_logs: bool,
) -> None:
    """Interactive agent REPL. Ctrl-D or /exit to quit."""
    cwd = Path(cwd_str).resolve()
    _apply_no_unicode_env(no_unicode)
    _resolve_default_model(model)
    if allow_net is True:
        configure(allow_net=True)
    elif allow_net is False:
        configure(allow_net=False)
    # else allow_net is None: TOML setting applied at bootstrap wins
    res, provider = _resolve_auth_or_die(auth_pref)
    provider = _apply_boot_model(provider, user_explicit=model)
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
        keep_logs=keep_logs,
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
    provider = _apply_boot_model(provider, user_explicit=model)
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
    keep_logs: bool = False,
) -> None:
    cfg = get_config()
    renderer = make_renderer(json_mode=json_mode, plain=plain)
    from .tui.renderer import TextualRenderer

    tools = make_toolset(
        cwd,
        renderer=renderer,
        net=_get_net_session(),
        session_id=record.id,
    )
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
    project_index_text = (
        "" if isinstance(renderer, TextualRenderer)
        else _render_project_index_text(cwd, session_id=record.id)
    )

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
        project_index_text=project_index_text,
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
    attach_memory_tools(tools, store=ctx.memory_store, session_id=record.id)
    # M13-06: additively attach the non-blocking multi-agent fan-out toolset
    # (subagent_spawn/steer/status/gather) alongside the unchanged serial
    # subagent_run tool (D-02 back-compat). attach_multiagent_tools returns the
    # defensive _teardown_orphans awaitable (M13-03) — captured here and run in
    # a finally on the per-turn run_turn await below so an un-gathered or
    # cancelled chat turn cannot leak orphan child tasks/panels (T-M13-02).
    _multiagent_teardown = attach_multiagent_tools(
        tools,
        registry=subagent_registry,
        cwd=cwd,
        renderer=renderer,
        provider=provider,
        model=lambda: get_config().default_model,
        gate=gate,
        cognition=bundle,
    )

    jobs_root = jail_path(cwd, ".voss-cache") / "jobs"
    active_session = jobs_root / ".active-session"
    try:
        jobs_root.mkdir(parents=True, exist_ok=True)
        active_session.write_text(record.id)
    except OSError as exc:
        click.echo(f"active session marker skipped: {exc}", err=True)

    git_status = _git_status(cwd)
    renderer.banner(model=cfg.default_model, cwd=cwd, git_status=git_status)

    if auth_detail and not isinstance(renderer, TextualRenderer):
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

    try:
        if isinstance(renderer, TextualRenderer):
            renderer.app.history = ctx.history
            renderer.app.cwd = cwd
            renderer.app.record = record
            renderer.app.slash_registry = slash_registry
            renderer.app.model = cfg.default_model
            renderer.app.git_status = git_status
            renderer.app.provider = _provider_label(auth_detail)
            renderer.app.mode = mode
            renderer.app.total_cost = ctx.total_cost

            async def _dispatch_tui_turn(line: str):
                if line.startswith("/"):
                    import io
                    old_stdout, old_stderr = sys.stdout, sys.stderr
                    cap_out, cap_err = io.StringIO(), io.StringIO()
                    handled = False
                    try:
                        sys.stdout, sys.stderr = cap_out, cap_err
                        handled = slash_registry.dispatch(ctx, line)
                    except ValueError as exc:
                        renderer.show_warning(str(exc))
                        return None
                    finally:
                        sys.stdout, sys.stderr = old_stdout, old_stderr
                    out = cap_out.getvalue().rstrip()
                    err = cap_err.getvalue().rstrip()
                    if out:
                        try:
                            tv = renderer.app.query_one("#main")
                            renderer._post(tv.append_turn, "system", out)
                        except Exception:  # noqa: BLE001
                            pass
                    if err:
                        renderer.show_warning(err)
                    if handled:
                        if ctx.should_exit:
                            renderer.app.exit()
                        return None
                    renderer.show_warning(f"unknown command: {line}. /help for list.")
                    return None
                renderer.show_user(line)
                try:
                    if not ctx.project_index_text:
                        ctx.project_index_text = _render_project_index_text(
                            cwd, session_id=record.id
                        )
                    run_turn = _resolve_run_turn(cwd)
                    result = await _run_turn_with_teardown(
                        run_turn(
                            line,
                            tools=tools,
                            cwd=cwd,
                            renderer=renderer,
                            model=get_config().default_model,
                            history=ctx.history,
                            permissions=gate,
                            provider=ctx.provider,
                            session_id=record.id,
                            cognition=bundle,
                            prior_context=ctx.prior_context,
                            voss_md_text=ctx.voss_md_text,
                            project_index_text=ctx.project_index_text,
                        ),
                        _multiagent_teardown,
                    )
                    ctx.prior_context = None
                except Exception as e:  # noqa: BLE001
                    renderer.show_warning(f"error: {e}")
                    return None
                ctx.last_plan = result.plan
                if result.run is not None:
                    record.runs.append(asdict(result.run))
                ctx.total_cost += result.cost_usd
                renderer.show_final(
                    result.final,
                    confidence=result.confidence,
                    cost_usd=result.cost_usd,
                )
                return result

            renderer.app._turn_dispatch = _dispatch_tui_turn
            asyncio.run(renderer.app.run_async())
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

        while True:
            try:
                line = input(_repl_prompt())
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
                result = _run_turn_cancellable(
                    _run_turn_with_teardown(
                        run_turn(
                            line,
                            tools=tools,
                            cwd=cwd,
                            renderer=renderer,
                            model=get_config().default_model,
                            history=ctx.history,
                            permissions=gate,
                            provider=ctx.provider,
                            session_id=record.id,
                            cognition=bundle,
                            prior_context=ctx.prior_context,
                            voss_md_text=ctx.voss_md_text,
                            project_index_text=ctx.project_index_text,
                        ),
                        _multiagent_teardown,
                    ),
                    renderer=renderer,
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
    finally:
        try:
            from . import lifecycle

            try:
                asyncio.run(lifecycle.reap_jobs())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(lifecycle.reap_jobs())
                finally:
                    loop.close()
            if not keep_logs:
                shutil.rmtree(jobs_root / record.id, ignore_errors=True)
            active_session.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            click.echo(f"job reap skipped: {exc}", err=True)


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

    # M15-06: surface gate-only confinement when third-party skills installed
    third_party = [p for p in load_plugins(cwd) if p.skill_id and p.voss_entry]
    if third_party:
        ids = ", ".join(p.skill_id for p in third_party)
        click.echo(f"  {'third-party skills':<20}: {len(third_party)} ({ids})")
        click.echo(f"  {'skill confinement':<20}: gate-level only (OS-level sandbox deferred)")
    else:
        click.echo(f"  {'third-party skills':<20}: 0")

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
    """Render slash help grouped by semantic category (D-04 / SC#3).

    Named groups are rendered first in fixed order; any registered non-hidden
    slash not assigned to a named group falls under a final "Other" bucket so
    nothing is ever silently dropped. Per-group width alignment mirrors the
    style in SlashRegistry.help_lines (slash.py:45-52).
    """
    registry = registry or _build_slash_registry()

    # Explicit buckets finalized against live _build_slash_registry() contents.
    # Order of groups and members within groups is semantic (not alpha).
    named_groups: list[tuple[str, list[str]]] = [
        ("Editing", ["/diff", "/apply", "/discard"]),
        ("Session", ["/resume", "/budget", "/cost", "/clear", "/save-session"]),
        ("Insight", ["/why", "/probable", "/btrace", "/vdiff", "/tools", "/analyze"]),
        ("Control", ["/help", "/exit", "/mode", "/model"]),
    ]

    placed: set[str] = set()
    for header, names in named_groups:
        members: list[SlashCommand] = []
        for name in names:
            cmd = registry.lookup(name)
            if cmd and not cmd.hidden:
                members.append(cmd)
                placed.add(name)
        if not members:
            continue
        click.echo(header)
        width = max(len(c.name) for c in members)
        for c in members:
            click.echo(f"  {c.name:<{width}}  {c.help}")
        click.echo()

    # Long-tail Other bucket (D-05 / M9-03 parity): everything not yet placed.
    other_members: list[SlashCommand] = []
    for name in registry.ids(include_hidden=False):
        if name not in placed:
            cmd = registry.lookup(name)
            if cmd and not cmd.hidden:
                other_members.append(cmd)
    if other_members:
        click.echo("Other")
        width = max(len(c.name) for c in other_members)
        for c in other_members:
            click.echo(f"  {c.name:<{width}}  {c.help}")


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


_JOB_META_FIELDS = (
    "handle",
    "pid",
    "started_at",
    "cmd",
    "log_path",
    "status",
    "exit_code",
    "runtime_ms",
)


def _read_job_meta(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except PermissionError:
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not all(k in data for k in _JOB_META_FIELDS):
        return None
    return {k: data[k] for k in _JOB_META_FIELDS}


def _newest_jobs_dir(cache: Path) -> Path | None:
    newest: tuple[float, Path] | None = None
    try:
        entries = list(cache.iterdir())
    except OSError:
        return None
    for path in entries:
        try:
            if not path.is_dir():
                continue
            if not _has_job_sidecars(path):
                continue
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if newest is None or mtime > newest[0]:
            newest = (mtime, path)
    return newest[1] if newest is not None else None


def _has_job_sidecars(path: Path) -> bool:
    try:
        return any(path.glob("*.meta.json"))
    except OSError:
        return False


def _active_jobs_session(cache: Path) -> Path | None:
    active = cache / ".active-session"
    try:
        sid = active.read_text().strip()
    except OSError:
        sid = ""
    if sid:
        try:
            session_dir = jail_path(cache, sid)
        except Exception:  # noqa: BLE001
            session_dir = None
        if session_dir is not None and session_dir.is_dir() and _has_job_sidecars(session_dir):
            return session_dir

    return _newest_jobs_dir(cache)


def _runtime_label(runtime_ms: object) -> str:
    try:
        ms = max(0, int(runtime_ms))
    except (TypeError, ValueError):
        ms = 0
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _display_status(rec: dict) -> str:
    status = str(rec.get("status", ""))
    if status != "running":
        return status
    try:
        live = psutil.pid_exists(int(rec["pid"]))
    except (TypeError, ValueError, psutil.Error):
        live = False
    return "running" if live else "stale"


@click.command("jobs")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")
def jobs_cmd(cwd_str: str, json_mode: bool) -> None:
    """List background jobs for the current session."""
    cwd = Path(cwd_str).resolve()
    cache = jail_path(cwd, ".voss-cache") / "jobs"
    session_dir = _active_jobs_session(cache)
    if session_dir is None:
        click.echo("(no background jobs)")
        return

    records: list[dict] = []
    try:
        meta_paths = sorted(session_dir.glob("*.meta.json"))
    except OSError:
        meta_paths = []
    for path in meta_paths:
        rec = _read_job_meta(path)
        if rec is not None:
            records.append(rec)

    if not records:
        click.echo("(no background jobs)")
        return

    if json_mode:
        for rec in records:
            rendered = dict(rec)
            rendered["status"] = _display_status(rec)
            click.echo(json.dumps(rendered))
        return

    rows = [
        (
            str(rec["handle"]),
            str(rec["pid"]),
            _display_status(rec),
            _runtime_label(rec["runtime_ms"]),
            str(rec["cmd"]),
        )
        for rec in records
    ]
    headers = ("HANDLE", "PID", "STATUS", "RUNTIME", "CMD")
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows))
        for i in range(len(headers) - 1)
    ]
    click.echo(
        f"{headers[0]:<{widths[0]}}  {headers[1]:<{widths[1]}}  "
        f"{headers[2]:<{widths[2]}}  {headers[3]:<{widths[3]}}  {headers[4]}"
    )
    terminal_cols = shutil.get_terminal_size((80, 24)).columns
    max_cmd = max(10, terminal_cols - sum(widths) - 10)
    for handle, pid, status, runtime, cmd in rows:
        if len(cmd) > max_cmd:
            cmd = cmd[: max_cmd - 1] + "…"
        click.echo(
            f"{handle:<{widths[0]}}  {pid:<{widths[1]}}  "
            f"{status:<{widths[2]}}  {runtime:<{widths[3]}}  {cmd}"
        )


async def _run_watch_loop(
    *,
    command: str,
    argv: list[str],
    cwd: Path,
    globs: list[str],
    debounce_ms: int,
    session_id: str,
    max_reruns: int,
    idle_timeout_s: float | None,
) -> None:
    """Watch loop: spawn the command, re-spawn it on debounced file change.

    Stops after `max_reruns` re-runs (0 = unbounded), after `idle_timeout_s`
    with no events (None = never), or on cancel/Ctrl-C. Always reaps the
    watcher and child job on exit. Kept free of test-environment sniffing so
    the same path runs in tests and production; tests bound it via the args.
    """
    import re
    import signal as signal_mod

    from . import lifecycle

    watch_handle = await lifecycle.register_watcher(
        globs, cwd, session_id=session_id, debounce_ms=debounce_ms
    )
    click.echo(watch_handle)

    job_handle = await lifecycle.register_job(
        cmd=command, argv=argv, cwd=cwd, session_id=session_id
    )

    rec = lifecycle._find_watcher(watch_handle, session_id=session_id)
    if rec is None:
        await lifecycle.reap_watchers()
        await lifecycle.reap_jobs()
        return

    cursor = 0
    reruns = 0
    last_activity = time.monotonic()
    try:
        while True:
            await asyncio.sleep(0.05)
            events_str = lifecycle._read_log_cursor(
                Path(rec.log_path), cursor, status=rec.status
            )
            match = re.match(r"\[cursor (\d+)\]", events_str)
            if match:
                new_cursor = int(match.group(1))
                if new_cursor > cursor:
                    cursor = new_cursor
                    last_activity = time.monotonic()
                    lifecycle.signal_job(
                        job_handle, signal_mod.SIGTERM, session_id=session_id
                    )
                    job_handle = await lifecycle.register_job(
                        cmd=command, argv=argv, cwd=cwd, session_id=session_id
                    )
                    reruns += 1
                    if max_reruns > 0 and reruns >= max_reruns:
                        break
            if (
                idle_timeout_s is not None
                and (time.monotonic() - last_activity) > idle_timeout_s
            ):
                break
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await lifecycle.reap_watchers()
        await lifecycle.reap_jobs()


@click.command("watch")
@click.argument("command")
@click.option("--glob", "globs", multiple=True, default=("**/*",))
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--daemon", "daemon_mode", is_flag=True)
@click.option("--debounce-ms", default=200, type=int)
@click.option("--_is-worker", "is_worker", is_flag=True)
@click.option("--_max-reruns", "max_reruns", default=0, type=int, hidden=True)
@click.option(
    "--_idle-timeout-ms", "idle_timeout_ms", default=0, type=int, hidden=True
)
def watch_cmd(
    command: str,
    globs: tuple[str, ...],
    cwd_str: str,
    daemon_mode: bool,
    debounce_ms: int,
    is_worker: bool,
    max_reruns: int,
    idle_timeout_ms: int,
) -> None:
    """Watch files and run a command on change."""
    cwd = Path(cwd_str).resolve()

    from .sandbox import shell_allowed, split_command, SandboxError

    ok, reason = shell_allowed(command)

    if not ok:
        click.echo(f"<denied: {reason}>")
        sys.exit(1)

    try:
        argv = split_command(command)
    except SandboxError as e:
        click.echo(f"<denied: {e}>")
        sys.exit(1)

    import shutil
    if argv and argv[0] in ("python", "python3") and not shutil.which(argv[0]):
        argv[0] = sys.executable

    if daemon_mode and not is_worker:
        from .watch.daemon import spawn_detached_worker

        try:
            watch_idx = sys.argv.index("watch")
            original_args = sys.argv[watch_idx + 1:]
        except ValueError:
            original_args = []
        pid = spawn_detached_worker(original_args)
        time.sleep(0.2)
        try:
            os.kill(pid, 0)
        except OSError:
            click.echo(f"<error: daemon worker {pid} exited immediately>")
            sys.exit(1)
        click.echo(f"watch (daemonized PID: {pid})")
        return

    session_id = "_nosession"
    idle_timeout_s = (idle_timeout_ms / 1000) if idle_timeout_ms > 0 else None

    asyncio.run(
        _run_watch_loop(
            command=command,
            argv=argv,
            cwd=cwd,
            globs=list(globs),
            debounce_ms=debounce_ms,
            session_id=session_id,
            max_reruns=max_reruns,
            idle_timeout_s=idle_timeout_s,
        )
    )


@click.group("inspect")
def inspect_group() -> None:
    """Inspect persisted run records."""


@inspect_group.command("probable")
@click.argument("session_id_or_name")
@click.option("--decision", "decision_index", type=int, default=None)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def inspect_probable_cmd(
    session_id_or_name: str, decision_index: int | None, cwd_str: str
) -> None:
    """Show recorded probable decision sequence."""
    try:
        text = _render_probable_inspect(
            Path(cwd_str).resolve(), session_id_or_name, decision_index
        )
    except (FileNotFoundError, ValueError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(text)


@inspect_group.command("budget")
@click.argument("session_id_or_name")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def inspect_budget_cmd(session_id_or_name: str, cwd_str: str) -> None:
    """Show recorded budget timeline."""
    try:
        text = _render_budget_inspect(Path(cwd_str).resolve(), session_id_or_name)
    except (FileNotFoundError, ValueError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(text)


@click.command("vdiff")
@click.argument("source", metavar="FILE.voss")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def vdiff_cmd(source: str, cwd_str: str) -> None:
    """Show source vs generated Python for a .voss file."""
    try:
        text = _render_voss_py_diff(Path(cwd_str).resolve(), source)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(text)


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
    # T5: no session_id — tools_cmd never invokes tools (deliberate _nosession).
    tools = make_toolset(cwd)
    name_w = max(len(n) for n in tools)
    click.echo(f"  {'name':<{name_w}}  {'mutating':<8}  description")
    click.echo(f"  {'-' * name_w}  {'-' * 8}  {'-' * 40}")
    for name in sorted(tools):
        entry = tools[name]
        mut = "yes" if entry.is_mutating else "no"
        desc = entry.description
        if len(desc) > 60:
            desc = desc[:59] + "…"
        click.echo(f"  {name:<{name_w}}  {mut:<8}  {desc}")


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
    renderer = renderer or make_renderer(json_mode=False)
    # T5: deliberate _nosession — not a live session loop.
    tools = make_toolset(cwd, renderer=renderer, net=_get_net_session())
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
        project_index_text=_render_project_index_text(cwd),
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
    attach_memory_tools(
        tools,
        store=MemoryStore(cwd).bind(session_id=ctx.record.id),
        session_id=ctx.record.id,
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


@skill_group.command("add")
@click.argument("source")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--allow-tofu", is_flag=True, default=False, help="TOFU-pin unknown keys on first install")
def skill_add_cmd(source: str, cwd_str: str, allow_tofu: bool) -> None:
    """Install a skill bundle from a local path, git URL, or GitHub shorthand."""
    from .skill.install import SkillTrustError, install_bundle

    cwd = Path(cwd_str).resolve()
    try:
        skill_id = install_bundle(source, cwd=cwd, allow_tofu=allow_tofu)
        click.echo(f"skill installed: {skill_id}")
    except SkillTrustError as e:
        click.echo(f"error: {e}", err=True)
        raise click.exceptions.Exit(code=1) from None


@skill_group.command("list")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def skill_list_cmd(cwd_str: str) -> None:
    """List installed third-party skills."""
    cwd = Path(cwd_str).resolve()
    plugins = load_plugins(cwd)
    found = False
    for p in plugins:
        if p.skill_id and p.voss_entry:
            found = True
            status = "enabled" if p.enabled else "disabled"
            click.echo(f"  {p.skill_id:<24} {status:<10} tools={p.scope_tools} fs={p.scope_fs} net={p.scope_net}")
    if found:
        click.echo("")
        click.echo("  note: scope enforcement applies to harness tool calls only (OS-level sandbox deferred)")
    else:
        click.echo("  (no third-party skills installed)")


@skill_group.command("remove")
@click.argument("skill_id")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def skill_remove_cmd(skill_id: str, cwd_str: str) -> None:
    """Remove an installed skill."""
    from .skill.install import remove_bundle

    cwd = Path(cwd_str).resolve()
    remove_bundle(skill_id, cwd=cwd)
    click.echo(f"skill removed: {skill_id}")


@skill_group.command("update")
@click.argument("skill_id")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def skill_update_cmd(skill_id: str, cwd_str: str) -> None:
    """Re-fetch and re-verify an installed skill (prior version intact on failure)."""
    from .skill.install import SkillTrustError, update_bundle

    cwd = Path(cwd_str).resolve()
    try:
        update_bundle(skill_id, cwd=cwd)
        click.echo(f"skill updated: {skill_id}")
    except SkillTrustError as e:
        click.echo(f"error: {e} (prior version intact)", err=True)
        raise click.exceptions.Exit(code=1) from None


@skill_group.command("trust")
@click.argument("pub_key_b64")
@click.option("--identity", required=True, help="Author identity (e.g. email)")
def skill_trust_cmd(pub_key_b64: str, identity: str) -> None:
    """Trust a signing key by pinning it to an identity."""
    from .trust import key_fingerprint, pin_key

    fp = key_fingerprint(pub_key_b64)
    click.echo(f"key fingerprint: {fp}")
    click.confirm(f"Trust key for identity '{identity}'?", abort=True)
    pin_key(identity, pub_key_b64)
    click.echo(f"key pinned for {identity}")


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


def _parse_arg_kvs(args_kvs: tuple[str, ...]) -> dict[str, object]:
    """Parse repeatable --arg key=value pairs for direct MCP calls."""
    import json as json_lib

    args_dict: dict[str, object] = {}
    for kv in args_kvs:
        if "=" not in kv:
            raise click.ClickException(
                f"invalid --arg {kv!r}: expected key=value"
            )
        key, raw_val = kv.split("=", 1)
        try:
            args_dict[key] = json_lib.loads(raw_val)
        except (json_lib.JSONDecodeError, ValueError):
            args_dict[key] = raw_val
    return args_dict


@click.group("mcp")
def mcp_group() -> None:
    """Inspect and debug MCP server connections."""


@mcp_group.command("list")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--json", "json_mode", is_flag=True, help="Emit machine-readable JSON.")
def mcp_list_cmd(cwd_str: str, json_mode: bool) -> None:
    """List configured MCP servers and their advertised tools."""
    import json as json_lib

    from voss.harness.mcp import McpClient, McpConfigError, load_mcp_config

    cwd = Path(cwd_str).resolve()
    try:
        config = load_mcp_config(cwd)
    except McpConfigError as e:
        click.echo(f"<error: mcp config: {e}>", err=True)
        raise click.exceptions.Exit(1) from e

    if config is None or not config.servers:
        if json_mode:
            click.echo(json_lib.dumps({"servers": []}))
        else:
            click.echo("<no MCP servers configured>")
        return

    client = McpClient(config)
    client.set_cwd(cwd)

    async def _populate() -> None:
        try:
            for name in config.servers:
                try:
                    await client.ensure_launched(name)
                except Exception as ex:  # noqa: BLE001
                    click.echo(f"<warning: {name} launch failed: {ex}>", err=True)
        finally:
            await client.aclose()

    asyncio.run(_populate())
    servers_payload = []
    for name, server in config.servers.items():
        tools = client._tools_cache.get(name, [])
        servers_payload.append(
            {
                "name": name,
                "command": server.command + server.args,
                "tools": [tool["name"] for tool in tools],
            }
        )

    if json_mode:
        click.echo(json_lib.dumps({"servers": servers_payload}, indent=2))
    else:
        for server_payload in servers_payload:
            click.echo(f"{server_payload['name']}:")
            click.echo(f"  command: {' '.join(server_payload['command'])}")
            tools = server_payload["tools"]
            click.echo(
                f"  tools: {', '.join(tools) if tools else '<none discovered>'}"
            )
            click.echo("")


@mcp_group.command("call")
@click.argument("server")
@click.argument("tool_name")
@click.option(
    "--arg",
    "args_kvs",
    multiple=True,
    help=(
        "key=value argument (repeatable). Values parsed as JSON when JSON-shaped; "
        "raw string fallback."
    ),
)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def mcp_call_cmd(
    server: str,
    tool_name: str,
    args_kvs: tuple[str, ...],
    cwd_str: str,
) -> None:
    """Call an MCP tool directly. Bypasses PermissionGate (developer tool)."""
    from voss.harness.mcp import McpClient, McpConfigError, load_mcp_config

    cwd = Path(cwd_str).resolve()
    try:
        config = load_mcp_config(cwd)
    except McpConfigError as e:
        click.echo(f"<error: mcp config: {e}>", err=True)
        raise click.exceptions.Exit(1) from e

    if config is None or server not in config.servers:
        click.echo(f"<error: unknown server: {server!r}>", err=True)
        raise click.exceptions.Exit(1)

    try:
        args_dict = _parse_arg_kvs(args_kvs)
    except click.ClickException as e:
        click.echo(f"<error: {e.message}>", err=True)
        raise click.exceptions.Exit(1) from e

    client = McpClient(config)
    client.set_cwd(cwd)

    async def _invoke() -> dict[str, object]:
        try:
            return await client.call_tool(server, tool_name, args_dict)
        except Exception as ex:  # noqa: BLE001
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"<error: mcp transport: {ex}>",
                    }
                ],
                "__transport_error": True,
            }
        finally:
            await client.aclose()

    result = asyncio.run(_invoke())
    if result.get("__transport_error"):
        content = result["content"]
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                click.echo(first.get("text", ""), err=True)
        raise click.exceptions.Exit(1)

    transport_error = False
    content = result.get("content", [])
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = str(item.get("text", ""))
                if text.startswith("<error: mcp transport:"):
                    transport_error = True
                click.echo(text)

    if result.get("isError"):
        if transport_error:
            raise click.exceptions.Exit(1)
        raise click.exceptions.Exit(2)


class _NullRenderer:
    """Renderer that emits nothing.

    The MCP server's stdout is the JSON-RPC wire; PlainRenderer writes
    show_final/stream_delta/finalize_stream to stdout and would corrupt the
    frame stream (Threat T-M12-04-02). Any renderer method a skill calls is a
    no-op here.
    """

    def __getattr__(self, _name: str):
        return lambda *a, **k: None


@mcp_group.command("serve")
@click.option(
    "--mode",
    type=click.Choice(["plan", "edit", "auto"], case_sensitive=False),
    required=True,
    help=(
        "Permission mode for incoming MCP calls. REQUIRED — no default. "
        "plan denies all mutating tools; edit allows fs writes but denies "
        "shell; auto allows everything."
    ),
)
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root the server operates against. Default: current dir.",
)
def mcp_serve_cmd(mode: str, cwd_str: str) -> None:
    """Run the Voss MCP server over stdio.

    Skills executed by this server use the SERVER's configured LLM provider
    for cost. The calling MCP host does NOT see the LLM cost.
    """
    import types

    from voss.harness.mcp.config import (
        McpConfigError,
        McpServerExposureConfig,
        load_mcp_config,
    )
    from voss.harness.mcp.server import McpServer
    from voss.harness.mcp.server_skills import make_skill_dispatch
    from voss.harness.mcp.server_tools import (
        build_tool_descriptors,
        build_tool_dispatch,
    )
    from voss.harness.permissions import PermissionGate
    from voss.harness.skill_registry import default_skill_registry
    from voss.harness.tools import make_toolset

    cwd = Path(cwd_str).resolve()
    try:
        cfg = load_mcp_config(cwd)
    except McpConfigError as e:
        click.echo(f"<error: mcp config: {e}>", err=True)
        raise click.exceptions.Exit(1) from e
    server_cfg = cfg.server if cfg is not None else None
    if server_cfg is None:
        server_cfg = McpServerExposureConfig()

    tools = make_toolset(cwd)
    reg = default_skill_registry()
    try:
        descriptors = build_tool_descriptors(tools, reg, server_cfg)
    except McpConfigError as e:
        click.echo(f"<error: mcp config: {e}>", err=True)
        raise click.exceptions.Exit(1) from e

    gate = PermissionGate(mode=mode, auto_yes=True)
    record = types.SimpleNamespace(model="mcp-server", id="mcp-serve")
    renderer = _NullRenderer()  # JSON-RPC stdout purity (T-M12-04-02)
    skill_dispatch = make_skill_dispatch(
        cwd=cwd,
        provider=None,
        history=None,
        record=record,
        renderer=renderer,
        tools=tools,
        gate=gate,
        skill_registry=reg,
    )
    dispatch = build_tool_dispatch(tools, reg, skill_dispatch, gate)
    server_name = server_cfg.name or "voss"
    server = McpServer(
        name=server_name, tool_descriptors=descriptors, dispatch=dispatch
    )

    async def _run() -> None:
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader(loop=loop)
        protocol = asyncio.StreamReaderProtocol(reader, loop=loop)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin.buffer)
        transport, w_proto = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout.buffer
        )
        writer = asyncio.StreamWriter(transport, w_proto, None, loop)
        await server.serve_stdio(reader, writer)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        raise click.exceptions.Exit(0)


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


@click.command("consensus")
@click.option("--staged", "input_mode", flag_value="staged", default=True, help="Critique staged changes (default).")
@click.option("--diff", "ref", default=None, metavar="REF", help="Critique diff against REF.")
@click.option("--stdin", "input_mode", flag_value="stdin", help="Read diff from stdin.")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Working directory.")
@click.option("--auth", "auth_pref", type=click.Choice(AUTH_CHOICES), default="auto", help="Credential source.")
@click.option("--model", default=None, help="Model override.")
def consensus_cmd(input_mode: str, ref: str | None, cwd_str: str, auth_pref: str, model: str | None) -> None:
    """Critique a diff against .voss/constraints.yml rules."""
    from voss.harness.consensus import capture_diff, format_violations, load_constraints, run_critique

    cwd = Path(cwd_str).resolve()
    _resolve_default_model(model)

    constraints = load_constraints(cwd)
    if constraints is None:
        sys.exit(0)

    mode = "ref" if ref else input_mode
    try:
        diff_text = capture_diff(mode, cwd, ref=ref)
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(2)

    if not diff_text:
        click.echo("\u2713 No changes to critique.")
        sys.exit(0)

    res, provider = _resolve_auth_or_die(auth_pref)
    provider = _apply_boot_model(provider, user_explicit=model)
    # commit-time critique runs the `commit` role chain when configured,
    # overriding the default-role provider; --model still wins.
    provider = _apply_role_chain(provider, "commit", user_explicit=model)
    cfg = get_config()
    result = asyncio.run(run_critique(provider, cfg.default_model, constraints, diff_text))

    if result is None:
        click.echo("warning: LLM request failed — commit proceeds (fail-open).", err=True)
        sys.exit(0)

    text, has_violations = format_violations(result)
    click.echo(text)
    if has_violations and constraints.mode == "block":
        sys.exit(1)
    sys.exit(0)


HOOK_SHIM = "#!/bin/sh\n# Installed by: voss hooks install\nexec voss consensus --staged\n"
HOOK_MARKER = "Installed by: voss hooks install"


@click.group("hooks")
def hooks_group() -> None:
    """Manage git pre-commit hook for voss consensus."""


@hooks_group.command("install")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Working directory.")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing hook.")
def hooks_install_cmd(cwd_str: str, force: bool) -> None:
    """Install a pre-commit hook that runs voss consensus."""
    cwd = Path(cwd_str).resolve()
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=5,
    )
    if out.returncode != 0:
        click.echo("Error: not a git repository.", err=True)
        sys.exit(2)
    git_root = Path(out.stdout.strip())
    hook_path = git_root / ".git" / "hooks" / "pre-commit"
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    if hook_path.exists() and not force:
        click.echo("Error: .git/hooks/pre-commit already exists. Use --force to overwrite.", err=True)
        sys.exit(1)
    hook_path.write_text(HOOK_SHIM)
    hook_path.chmod(0o755)
    click.echo(f"Installed pre-commit hook at {hook_path}")


@hooks_group.command("uninstall")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Working directory.")
def hooks_uninstall_cmd(cwd_str: str) -> None:
    """Remove a voss-installed pre-commit hook."""
    cwd = Path(cwd_str).resolve()
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=5,
    )
    if out.returncode != 0:
        click.echo("Error: not a git repository.", err=True)
        sys.exit(2)
    git_root = Path(out.stdout.strip())
    hook_path = git_root / ".git" / "hooks" / "pre-commit"
    if not hook_path.exists():
        click.echo("No pre-commit hook found.")
        sys.exit(0)
    content = hook_path.read_text(encoding="utf-8")
    if HOOK_MARKER not in content:
        click.echo("Error: .git/hooks/pre-commit was not installed by voss. Remove manually.", err=True)
        sys.exit(1)
    hook_path.unlink()
    click.echo("Removed pre-commit hook.")


@click.command("serve")
@click.option("--host", default="127.0.0.1", help="Bind host (loopback only).")
@click.option("--port", default=0, type=int, help="Bind port; 0 = ephemeral.")
@click.option("--token", default=None, help="Bearer token; auto-generated if omitted.")
def serve_cmd(host: str, port: int, token: str | None) -> None:
    """Run the REST+SSE harness server for thin clients (voss-tui).

    Prints a one-line `{port, token}` handshake to stdout, then serves until
    the parent process exits. Requires the `server` extra (`pip install
    voss[server]`).
    """
    try:
        from .server.serve import run_server
    except ImportError as exc:  # pragma: no cover - missing optional dep
        raise click.ClickException(
            "the server extra is not installed — run: pip install 'voss[server]'"
        ) from exc
    run_server(host=host, port=port, token=token)


AGENT_COMMANDS = (
    do_cmd,
    serve_cmd,
    chat_cmd,
    edit_cmd,
    login_cmd,
    logout_cmd,
    doctor_cmd,
    sessions_cmd,
    jobs_cmd,
    watch_cmd,
    inspect_group,
    vdiff_cmd,
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
    mcp_group,
    logs_group,
    eval_cmd,
    consensus_cmd,
    hooks_group,
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
    Interactive commands: run `voss chat`, then /help
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
