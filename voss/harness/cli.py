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
from dataclasses import asdict
from pathlib import Path

import click

from voss_runtime import EpisodicMemory, configure, get_config
from voss_runtime.providers import LiteLLMProvider
from voss_runtime.providers.base import ModelProvider

from . import auth as auth_mod
from . import cognition as cognition_mod
from . import session as session_store
from .agent import Plan, run_turn
from .permissions import PermissionGate, PermissionStore
from .providers import AnthropicOAuthProvider, OpenAIOAuthProvider
from .render import make_renderer
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


def _handle_login(provider: str | None) -> None:
    """Status + refresh for existing creds; for missing, print upstream commands.

    M1 contract (deliberate narrowing of D-08): we do NOT drive a bespoke
    OAuth flow. D-10 forbids new credential stores, so re-auth must go
    through the upstream CLI (`claude /login`, `codex login`). This function:
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
    mode: str,
    yes_to_all: bool,
    auth_pref: str,
) -> None:
    """Run a one-shot agent task and print the final answer.

    Stdin (when piped) is appended to the task as additional context.
    """
    cwd = Path(cwd_str).resolve()
    _resolve_default_model(model)
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
    do_bundle = cognition_mod.load(cwd)
    gate = PermissionGate(
        mode=mode,  # type: ignore[arg-type]
        store=PermissionStore.load(cwd),
        auto_yes=yes_to_all or json_mode,
        project_policy=do_bundle.permissions if do_bundle.initialized else None,
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
    mode: str,
    auth_pref: str,
) -> None:
    """Interactive agent REPL. Ctrl-D or /exit to quit."""
    cwd = Path(cwd_str).resolve()
    _resolve_default_model(model)
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
    mode: str,
    auth_pref: str,
) -> None:
    """Scoped edit REPL. Writes restricted to <PATH> + sibling test mirror (D-02).

    Out-of-scope writes prompt to expand the scope for this session only.
    Reads stay free under the cwd path jail.
    """
    from .edit_scope import EditScope

    cwd = Path(cwd_str).resolve()
    _resolve_default_model(model)
    res, provider = _resolve_auth_or_die(auth_pref)
    cfg = get_config()

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
) -> None:
    cfg = get_config()
    renderer = make_renderer(json_mode=json_mode)
    tools = make_toolset(cwd)
    total_cost = record.total_cost_usd
    last_plan: Plan | None = None

    def _tok_count(text: str) -> int:
        if _litellm is not None:
            try:
                return int(
                    _litellm.token_counter(model=cfg.default_model, text=text)
                )
            except Exception:  # noqa: BLE001
                pass
        return max(len(text) // 4, 1)

    bundle = cognition_mod.load(cwd, token_count=_tok_count)
    if bundle.load_errors:
        for err in bundle.load_errors:
            click.echo(f"cognition error: {err}", err=True)

    gate = PermissionGate(
        mode=mode,  # type: ignore[arg-type]
        store=PermissionStore.load(cwd),
        edit_scope=edit_scope,
        project_policy=bundle.permissions if bundle.initialized else None,
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
        if line == "/analyze":
            _handle_analyze(
                cwd=cwd,
                provider=provider,
                history=history,
                record=record,
                renderer=renderer,
                tools=tools,
                gate=gate,
            )
            continue
        if line.startswith("/save-plan"):
            _handle_save_plan(
                cwd=cwd, last_plan=last_plan, record=record, line=line
            )
            continue
        if line == "/model" or line.startswith("/model "):
            parts = line.split(maxsplit=1)
            if len(parts) == 1:
                claude = auth_mod.load_anthropic_oauth()
                codex = auth_mod.load_codex()
                click.echo(f"  active: {cfg.default_model}")
                claude_ok = bool(claude and not claude.expired)
                codex_ok = bool(codex and (codex.api_key or codex.has_oauth))
                click.echo(f"  Claude: {'available' if claude_ok else 'unavailable'}")
                click.echo(f"  Codex:  {'available' if codex_ok else 'unavailable'}")
            else:
                from . import config as harness_config

                new_model = parts[1].strip()
                configure(default_model=new_model)
                cfg = get_config()
                harness_config.set_preferred_model(new_model)
                click.echo(f"  model: {cfg.default_model} (persisted)")
            continue
        if line == "/mode" or line.startswith("/mode "):
            mparts = line.split()
            if len(mparts) == 1:
                click.echo(f"  mode: {gate.mode}")
                continue
            new_mode = mparts[1].strip()
            if new_mode not in ("plan", "edit", "auto"):
                click.echo("mode must be plan|edit|auto", err=True)
                continue
            if new_mode == "auto" and "--confirm" not in mparts:
                click.echo(
                    "escalating to auto requires --confirm "
                    "(e.g. /mode auto --confirm)",
                    err=True,
                )
                continue
            gate.mode = new_mode  # type: ignore[assignment]
            click.echo(f"  mode: {new_mode}")
            continue
        if line == "/login" or line.startswith("/login "):
            lparts = line.split(maxsplit=1)
            login_provider = lparts[1].strip() if len(lparts) == 2 else None
            _handle_login(login_provider)
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

        if _classify_intent(line) == "analyze":
            _handle_analyze(
                cwd=cwd,
                provider=provider,
                history=history,
                record=record,
                renderer=renderer,
                tools=tools,
                gate=gate,
            )
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
                    session_id=record.id,
                    cognition=bundle,
                    prior_context=prior_context,
                )
            )
            # prior_context is one-shot: only the first turn rehydrates it.
            prior_context = None
        except Exception as e:  # noqa: BLE001
            click.echo(f"error: {e}", err=True)
            continue
        last_plan = result.plan
        if result.run is not None:
            record.runs.append(asdict(result.run))
        total_cost += result.cost_usd
        renderer.show_final(
            result.final, confidence=result.confidence, cost_usd=result.cost_usd
        )


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
                "/analyze               refresh project cognition (.voss/ + .voss-cache/)",
                "/save-plan [title]     persist the most recent plan to .voss/plans/",
            ]
        )
    )


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


AGENT_COMMANDS = (
    do_cmd,
    chat_cmd,
    edit_cmd,
    doctor_cmd,
    sessions_cmd,
    resume_cmd,
    tools_cmd,
    config_cmd,
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
