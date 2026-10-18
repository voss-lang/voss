"""FastAPI app: harness REST+SSE server wrapping agent.run_turn."""
from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import sqlite3
import shlex
import os
import secrets
import subprocess
import uuid
from concurrent.futures import Future
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field, ValidationError
from sse_starlette import EventSourceResponse, ServerSentEvent
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response

from voss_runtime import EpisodicMemory, get_config  # noqa: F401  (get_config used lazily)

from .. import ambient
from .. import auth as auth_mod
from .. import cognition as cognition_mod
from .. import config as harness_config
from .. import session as session_store
from ..agent import Plan, run_turn
from ..observe import admission as observe_admission
from ..observe import bos_drain, repository as observe_repository
from ..bos_ledger import BosEventLedger
from ..observe.enrollment import (
    RepoEnrollment,
    get_repo_enrollment,
    load_enrollment,
    load_repo_policy,
    set_repo_enrollment,
)
from ..observe.models import ObserveEventAdapter
from ..observe.redact import redact_argv, redact_text
from ..observe.store import ObserveStore, db_path, observe_dir
from ..permissions import PermissionGate, PermissionStore
from ..swarm_agents import is_native
from ..swarm_store import (
    OPEN, DONE, CANDIDATE_READY,
    OwnershipOverlapError,
    Role,
    SwarmStore,
    build_ownership_policy,
)
from ..tools import attach_memory_tools, attach_mcp_tools, make_toolset
from ..memory_gateway import open_memory_store
from ..memory_store import MemoryStore
from . import commands
from . import capabilities
from . import preview
from . import task_graph
from .. import oauth
from . import events as E
from . import models as model_selection
from .diffs import DiffReply, DiffReviewRenderer
from .task_journal import TaskSnapshot, TaskEvent, CommandAck
from .renderer import EventBusRenderer
from .sessions import ServerSession, SessionManager

PERMISSION_TIMEOUT_S = 300.0


class _FakeResolution:
    """Stand-in Resolution for the VOSS_SERVE_FAKE_TURN test seam."""

    source = "fake"
    detail = "VOSS_SERVE_FAKE_TURN"


class _BearerASGI:
    """Raw ASGI bearer-auth middleware.

    Implemented at the ASGI layer (not BaseHTTPMiddleware) because
    BaseHTTPMiddleware buffers response bodies, which breaks SSE streaming.
    Rejects unauthenticated requests before they reach any route.
    """

    def __init__(self, app, token: str) -> None:
        self._app = app
        self._token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode("latin-1")
        ok = auth.startswith("Bearer ") and secrets.compare_digest(
            auth[7:], self._token
        )
        if not ok:
            resp = JSONResponse({"v": 1, "detail": "unauthorized"}, status_code=401)
            await resp(scope, receive, send)
            return
        await self._app(scope, receive, send)


# auth -> provider (mirrors cli._resolve_auth_or_die, minus TTY wizard/sys.exit)


def _resolve_provider(preference: str) -> tuple[auth_mod.Resolution, Any]:
    """Resolve credentials to a (Resolution, provider). Never exits the process.

    Server analogue of `cli._resolve_auth_or_die`: same provider-selection
    switch, but a missing credential is a caller error (raised by the route),
    not a login wizard / `sys.exit`.
    """
    # Test seam: a hermetic fake turn needs a session without real creds
    if os.environ.get("VOSS_SERVE_FAKE_TURN"):
        return _FakeResolution(), object()

    from voss_runtime.providers import LiteLLMProvider

    from ..claude_agent_provider import ClaudeAgentProvider
    from ..providers import OpenAIOAuthProvider

    # Same persisted-default rule as cli._resolve_auth_or_die: `[harness] auth`
    # applies when nothing more specific was asked for.
    if preference == "auto":
        saved = harness_config.load_harness_config().get("auth")
        if saved in ("claude", "codex", "api", "none"):
            preference = saved

    res = auth_mod.resolve(preference)
    if res.source == "none":
        return res, None
    if res.source == "claude-agent":
        provider: Any = ClaudeAgentProvider(cli_path=res.cli_path)
    elif res.source == "codex-oauth":
        provider = OpenAIOAuthProvider(res.codex_oauth)
    else:
        # env/voss anthropic|openai|codex all go through LiteLLM (key already
        # injected into os.environ by auth.resolve)
        provider = LiteLLMProvider()
    return res, provider


def _codex_session_model() -> str:
    """Default model id for codex-oauth sessions.

    The ChatGPT-account Codex backend rejects ids it does not serve; the harness
    default (`claude-sonnet-4-5`) 400s there and the turn dies before any output.
    Mirrors `cli._codex_default_model` WITHOUT importing `cli` (whose top-level
    `@click` command registration has heavy import side effects): read Codex CLI's
    own default, else fall back to the first subscription codex model.
    """
    m = auth_mod.load_codex_default_model()
    if auth_mod.is_codex_backend_model(m):
        return m  # type: ignore[return-value]
    from ..subscription_models import SUBSCRIPTION_MODELS

    return SUBSCRIPTION_MODELS["codex"][0].id


def _effective_model(requested: str | None, res: Any) -> str:
    """Resolve a requested model id to a concrete one for a spawned session.

    The swarm roster uses the literal `"default"` sentinel (swarm_store.Role)
    to mean 'no explicit choice' — treat it (and None) as unspecified and fall
    through to the serve-env default then the config default. An explicit,
    non-sentinel model is honored as-is. In all cases the codex-oauth backend
    constraint is applied last (mirrors create_session, app.py:556-565), so an
    id that backend does not serve never reaches it and 400s the turn.
    """
    model = requested if (requested and requested != "default") else None
    model = (
        model
        or os.environ.get("VOSS_SERVE_DEFAULT_MODEL")
        or get_config().default_model
    )
    if res.source == "codex-oauth" and not auth_mod.is_codex_backend_model(model):
        model = _codex_session_model()
    return model


# permission bridge mirrors tui/permissions_bridge over the protocol


def _install_server_permissions(
    gate: PermissionGate, session: ServerSession, renderer: EventBusRenderer
) -> None:
    """Route gate prompts through `permission.updated` events + /permission replies.

    `prompt_fn`/`scope_prompt_fn` run on harness worker threads; they emit an
    event (thread-safe via the renderer's loop hop) and block on a
    `concurrent.futures.Future` that the /permission route resolves.
    """

    def _ask(tool_name: str, args: dict, dimension: str) -> str:
        req_id = uuid.uuid4().hex[:8]
        fut: Future[str] = Future()
        session.pending[req_id] = fut
        renderer.emit(
            E.PermissionUpdated(
                id=req_id, tool_name=tool_name, args=args, dimension=dimension
            )
        )
        try:
            return fut.result(timeout=PERMISSION_TIMEOUT_S)
        except TimeoutError:
            return "d"
        finally:
            session.pending.pop(req_id, None)
            if session.journal:
                session.journal.resolve(session.id, req_id)

    def prompt(tool_name: str, args: dict) -> str:
        return _ask(tool_name, args, "tool")

    def scope_prompt(target: str) -> str:
        # Scope-expand uses the same channel; map y/n at the client
        return _ask("scope_expand", {"target": target}, "tool")

    gate.prompt_fn = prompt
    gate.scope_prompt_fn = scope_prompt


# swarm ownership escalation + scoped recall ( VSWARM-05/07/10)

# fs_edit_many is NOT in permissions.WRITE but the ownership policy keys it, so
# escalate on it too
_SWARM_WRITE_TOOLS = {"fs_write", "fs_edit", "fs_edit_many"}


def _apply_swarm_escalation(
    gate: PermissionGate, session: ServerSession, renderer: EventBusRenderer
) -> None:
    """Wrap `gate.check` so an ownership denial on a WRITE tool escalates to the
    operator instead of silently failing (VSWARM-10). The deny itself already
    fired at the project_policy deny-wins layer (permissions.py:288-295) which
    runs before mode/auto_yes — auto_yes cannot bypass it. On denial we emit
    `swarm.needs_operator` (+ a paired PermissionUpdated carrying the request id
    so the EXISTING /session/{id}/permission Future bridge answers it) and block
    on that Future. An approve overrides to allow + records a decision; anything
    else keeps the deny + records it."""
    orig_check = gate.check

    def _checked(tool_name, args, *, is_mutating=False, is_network=False):
        allowed, why = orig_check(
            tool_name, args, is_mutating=is_mutating, is_network=is_network
        )
        if allowed or tool_name not in _SWARM_WRITE_TOOLS:
            return allowed, why
        # Ownership denial → escalate through the existing permission bridge
        path = str(args.get("path", ""))
        req_id = uuid.uuid4().hex[:8]
        fut: Future[str] = Future()
        session.pending[req_id] = fut
        renderer.emit(
            E.SwarmNeedsOperator(
                swarm_id=session.swarm_id or "",
                task_id=session.swarm_task_id or "",
                session_id=session.id,
                tool_name=tool_name,
                path=path,
            )
        )
        # Paired event on the existing permission channel carries the id so a
        # client answers via POST /session/{id}/permission (reuse, not new wire)
        renderer.emit(
            E.PermissionUpdated(
                id=req_id, tool_name=tool_name, args=dict(args), dimension="tool"
            )
        )
        try:
            answer = fut.result(timeout=PERMISSION_TIMEOUT_S)
        except TimeoutError:
            answer = "d"
        finally:
            session.pending.pop(req_id, None)
            if session.journal:
                session.journal.resolve(session.id, req_id)
        approved = answer in ("a", "A", "y")
        if session.swarm_id:
            # Decision audit is cwd-scoped (.voss/decisions); a fresh store
            # writes the file without needing the in-memory swarm state
            SwarmStore(session.cwd).record_gate_decision(
                session.swarm_id,
                session.swarm_task_id or "",
                session.id,
                gate_type="ownership_override" if approved else "ownership_denied",
                confidence=1.0 if approved else 0.0,
                detail=f"{tool_name} {path}: operator {'approved' if approved else 'denied'}",
            )
        if approved:
            return True, "operator approved"
        return False, why

    gate.check = _checked  # type: ignore[method-assign]


def _swarm_recall_text(session: ServerSession, text: str) -> str:
    """Task-scoped recall for a swarm builder: recall filtered to ownedFiles
    (VSWARM-07). Returns "" when there are no owned files or no scoped hits."""
    if not session.swarm_owned_files:
        return ""
    from ..swarm_store import scoped_recall

    store = session.memory_store or open_memory_store(session.cwd)
    hits = scoped_recall(store, text, session.swarm_owned_files)
    if not isinstance(store, MemoryStore):
        retained = [
            hit for hit in store.recall(text)
            if hit.source in {"notes", "conventions", "decisions"}
        ]
        hits = MemoryStore._rrf_merge([hits, retained], top_k=5)
    if not hits:
        return ""
    lines = [
        "## Task-scoped recall (owned files and project memory)"
        if not isinstance(store, MemoryStore)
        else "## Task-scoped recall (your owned files)"
    ]
    for h in hits:
        lines.append(f"- {h.locator}: {h.excerpt}")
    return "\n".join(lines)


# turn runner


async def _run_ambient_turn(
    session: ServerSession, text: str, mode: str, route: str, renderer: EventBusRenderer,
) -> None:
    status = ambient.status_answer(
        provider=model_selection.provider_label(session.provider, session.auth),
        model=session.model, mode=mode,
    )
    if route == "local":
        session.history.add(text, role="user")
        session.history.add(status, role="assistant")
        renderer.show_final(status, confidence=1.0, cost_usd=0.0)
        return
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    response = await ambient.complete(
        text, provider=session.provider, model=session.model, cwd=session.cwd,
        history=session.history, status=status, prior_context=session.prior_context,
    )
    session.record.runs.append(asdict(session_store.RunRecord(
        id=uuid.uuid4().hex[:12], started_at=started,
        ended_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        goal=text, cost_usd=response.cost_usd, exit_reason="done",
        iteration_total_prompt_tokens=response.prompt_tokens,
        iteration_total_completion_tokens=response.completion_tokens,
    )))
    renderer.status(
        model=session.model, tokens=response.total_tokens,
        cost_usd=response.cost_usd, ctx_pct=0.0,
    )
    renderer.show_final(response.text, confidence=1.0, cost_usd=response.cost_usd)


async def _run_turn(session: ServerSession, text: str, mode: str) -> None:
    """Drive one turn; publish events; persist. Runs as session.task."""
    loop = asyncio.get_running_loop()
    renderer = (
        DiffReviewRenderer(session, loop=loop) if session.review_diffs else
        EventBusRenderer(session.queue, session_id=session.id, loop=loop, model=session.model)
    )

    # VSWARM-04 spawn-gate: a builder session created before its assignment
    # holds a set (unsignaled) gate_event and runs ZERO turns until the
    # coordinator's swarm.assign sets it. await directly in the coroutine
    # (NOT asyncio.to_thread Pitfall) so it suspends, yields the
    # loop, and integrates with cancellation. Ungated sessions (gate_event is
    # None) skip this entirely byte-identical to pre- behaviour
    if session.gate_event is not None:
        await session.gate_event.wait()

    # Test seam: emit a canned turn over the real event/SSE path (no provider)
    if os.environ.get("VOSS_SERVE_FAKE_TURN"):
        try:
            renderer.show_user(text)
            renderer.set_phase("run")
            renderer.show_thinking("planning 1/1")
            plan = Plan(rationale="fake turn", confidence=0.9)
            renderer.show_plan(plan, cost_usd=0.0)
            renderer.stream_delta("hello ")
            renderer.stream_delta("from fake turn")
            renderer.finalize_stream(role="assistant", confidence=0.9, cost_usd=0.0)
            session.last_plan = plan
            renderer.show_final(f"echo: {text}", confidence=0.9, cost_usd=0.0)
            session.turn_outcome = "done"
        finally:
            renderer.set_phase("ambient")
            renderer.session_idle()
            if session.execution_plan is None:
                session.task = None
        return

    mcp_client = None
    try:
        renderer.show_user(text)
        route = "voss_run" if session.execution_plan or session.swarm_id or session.gate_event is not None else ambient.route(text)
        renderer.set_phase("run" if route == "voss_run" else "ambient")
        if route != "voss_run":
            await _run_ambient_turn(session, text, mode, route, renderer)
            session.turn_outcome = "done"
            return
        tools = make_toolset(session.cwd, renderer=renderer, background_indexing=session.execution_plan is None)
        memory_kwargs = {}
        if session.execution_plan is not None:
            tools = {name: tool for name, tool in tools.items() if name in preview.TOOLS}
        else:
            mcp_client = await attach_mcp_tools(tools, session.cwd)
            if session.memory_store is None:
                session.memory_store = open_memory_store(session.cwd)
            if not isinstance(session.memory_store, MemoryStore):
                attach_memory_tools(tools, store=session.memory_store, session_id=session.id)
                memory_kwargs["pinned_memory_text"] = await asyncio.to_thread(
                    session.memory_store.render_pinned_memory_text, model=session.model
                )
        bundle = cognition_mod.load(session.cwd)
        for err in bundle.load_errors:
            renderer.show_warning(f"cognition error: {err}")
        gate = PermissionGate(
            mode=mode,  # type: ignore[arg-type]
            store=PermissionStore.load(session.cwd),
            auto_yes=False,
            # VSWARM-05: a swarm builder's ownership-deny policy takes the
            # project_policy slot in place of .voss/permissions.yml.
            project_policy=(
                session.swarm_policy
                if session.swarm_policy is not None
                else bundle.permissions if bundle.initialized else None
            ),
            safety_policy=bundle.safety if bundle.initialized else None,
            # No protocol channel for a typed confirmation, and stdin is the
            # heartbeat, so irreversible actions are denied.
            safety_confirm_fn=lambda req: "",
        )
        _install_server_permissions(gate, session, renderer)
        if session.swarm_policy is not None:
            _apply_swarm_escalation(gate, session, renderer)
        if session.execution_plan is not None:
            preview.install_scope(gate, session)

        try:
            from .. import voss_md

            voss_md_text = voss_md.read_and_inject(session.cwd)
        except Exception:
            voss_md_text = None

        # Seed the turn with the project index + task-relevant code recall
        # so the agent has a map of the repo instead of blind-globbing to
        # discover it. Mirrors the CLI's `voss do` injection path; both renders
        # are additive and self-guard (return "" on any failure / not-ready /
        # inject-off), so a turn never breaks because injection is unavailable
        try:
            from ..cli import _render_project_index_text, _scoped_turn

            project_index_text = "" if session.execution_plan is not None else _render_project_index_text(
                session.cwd, session_id=session.id
            )
            # VSWARM-07: a swarm builder gets recall filtered to its ownedFiles
            # non-swarm sessions keep the unscoped code-recall path unchanged
            if session.swarm_owned_files:
                code_recall_text = await asyncio.to_thread(_swarm_recall_text, session, text)
            else:
                code_recall_text = ""
        except Exception:
            project_index_text = ""
            code_recall_text = ""

        def make_turn(recall: dict):
            return run_turn(
                text,
                tools=tools,
                cwd=session.cwd,
                renderer=renderer,
                model=session.model,
                provider=session.provider,
                permissions=gate,
                history=session.history,
                session_id=session.id,
                cognition=bundle,
                voss_md_text=voss_md_text,
                project_index_text=project_index_text,
                code_recall_text=recall.get("code_recall_text", ""),
                prior_context=session.prior_context,
                **memory_kwargs,
            )

        if session.execution_plan is not None:
            result = await make_turn({})
        elif session.swarm_owned_files:
            result = await make_turn({"code_recall_text": code_recall_text})
        else:
            result = await _scoped_turn(session.cwd, text, session.id, run_turn, make_turn)
        # Consume resume context once: deep history now flows via session.history
        session.prior_context = None
        session.last_plan = result.plan
        session.turn_outcome = result.run.exit_reason if result.run is not None else "unknown"
        renderer.show_final(
            result.final, confidence=result.confidence, cost_usd=result.cost_usd
        )
        if result.run is not None:
            session.record.runs.append(asdict(result.run))
    except asyncio.CancelledError:
        raise
    except auth_mod.OAuthRequired:
        session.turn_outcome = "authentication_required"
    except Exception as e:  # noqa: BLE001 — surface, don't vanish into a bare idle
        # A provider/backend failure (e.g. a codex 4xx from run_turn ->
        # provider.stream) would otherwise propagate past this finally as an
        # un-awaited task exception, leaving the user a bare session.idle with
        # no signal. Surface it visibly on the transcript BEFORE the finally
        # idles mirrors agent.py's interrupt/batch-invariant error paths
        session.turn_outcome = "error"
        renderer.stream_delta(f"\n[error: {e}]\n")
        renderer.finalize_stream(role="system", confidence=None, cost_usd=None)
    finally:
        if mcp_client is not None:
            await mcp_client.aclose()
        try:
            session.record.total_cost_usd = sum(
                float(r.get("cost_usd", 0.0) or 0.0) for r in session.record.runs
            )
            session_store.save(session.record, session.history)
        except Exception:
            pass
        renderer.set_phase("ambient")
        renderer.session_idle()
        if session.execution_plan is None:
            session.task = None


def _await_authentication(session: ServerSession, availability: oauth.Availability):
    session.journal.update(session.id, phase="waiting", outcome="authentication_required",
                           pending_actions=[{"kind": "authentication", **availability.model_dump()}])


async def _drive_turn(session: ServerSession, text: str, mode: str):
    session.turn_outcome = None
    try:
        await _run_turn(session, text, mode)
        if isinstance(session.provider, oauth.BoundProvider) and session.provider.blocked is not None:
            _await_authentication(session, session.provider.blocked)
            return
        snapshot = session.journal.snapshot(session.id)
        questions = [action for action in snapshot.pending_actions if action.get("kind") == "clarify"]
        phase = "completed" if session.turn_outcome == "done" else "failed"
        if questions and session.turn_outcome != "error":
            phase = "waiting"
        session.journal.update(session.id, phase=phase, outcome=session.turn_outcome or "unknown",
                               pending_actions=questions if phase == "waiting" else [])
    except asyncio.CancelledError:
        session.journal.update(session.id, phase="cancelled", outcome="cancelled", pending_actions=[])
        raise
    except auth_mod.OAuthRequired:
        _await_authentication(session, session.provider.blocked)
    except Exception:
        session.journal.update(session.id, phase="failed", outcome="error", pending_actions=[])
    finally:
        for future in list(session.pending.values()):
            if not future.done():
                future.set_result("d")
        for pending in list(session.pending_diffs.values()):
            if not pending.future.done():
                pending.future.set_result([])
        session.pending.clear()
        session.pending_diffs.clear()
        session.task = None


# request models


class CreateSessionBody(BaseModel):
    review_diffs: bool = False
    parentID: str | None = None
    title: str | None = None
    cwd: str | None = None
    model: str | None = None
    auth: str = "auto"
    resume: str | None = None  # id/name of a saved session to resume (H4.1)


class MessagePart(BaseModel):
    type: str = "text"
    text: str = ""


class MessageBody(BaseModel):
    parts: list[MessagePart] = []
    mode: str = "plan"
    command_id: str | None = None


class PermissionReply(BaseModel):
    id: str
    choice: str  # a | A | d  (or y | n for scope)


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class SessionHistory(BaseModel):
    v: int = 1
    turns: list[HistoryTurn]


# swarm


class RoleSpec(BaseModel):
    name: str
    # R3 agent axis mirrors swarm_store.Role (see SWARM-RECONCILIATION)
    agent: str = "voss"
    command: str = ""
    args: list[str] = []
    model: str = "default"
    auth_pref: str = "auto"


class CreateSwarmBody(BaseModel):
    goal: str
    cwd: str | None = None
    builders: int = 2
    # Optional explicit roster; when omitted the SwarmStore default_roster
    # (coordinator + N builders + reviewer) is spawned (VSWARM-08)
    roster: list[RoleSpec] | None = None


class CreateTaskBody(BaseModel):
    goal: str
    owned_files: list[str] = []
    depends_on: list[str] = []


class SwarmMessageBody(BaseModel):
    # Inter-agent / operator message. `kind` selects the lifecycle event the
    # route emits over the swarm SSE plane (assign also unblocks a builder's
    # spawn-gate). gate/needs_operator are scriptable here; their automatic
    # emit points are wired in
    from_session: str | None = None
    text: str = ""
    kind: str = "message"  # message|assign|worker_done|gate|needs_operator|complete
    task_id: str | None = None
    session_id: str | None = None  # target builder (assign) / subject session
    gate_type: str = ""
    detail: str = ""
    tool_name: str = ""
    path: str | None = None
    summary: str | None = None
    task_count: int = 0
    confidence: float = 0.0


# observe


class ObserveEvidenceItem(BaseModel):
    kind: str = "command_output"
    content: str = ""
    truncated: bool = False


class ObserveEventBody(BaseModel):
    event: dict[str, Any]
    evidence: list[ObserveEvidenceItem] = []


class ObserveEnrollmentPatch(BaseModel):
    enabled: bool | None = None
    capture: bool | None = None
    analysis: bool | None = None
    provider: str | None = None
    disclosure: bool | None = None
    budget_usd: float | None = None
    paused: bool | None = None


class ObserveSettingsBody(BaseModel):
    repository_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    enrollment: ObserveEnrollmentPatch


# app factory


def create_app(token: str | None = None, *, oauth_only: bool = False) -> FastAPI:
    token = token or secrets.token_urlsafe(32)
    mgr = SessionManager()

    def drain_observe(repository_id: str | None = None) -> None:
        paths = [db_path(repository_id)] if repository_id else observe_dir().glob("*.sqlite")
        for path in paths:
            try:
                with ObserveStore(path.stem) as store:
                    events = store.list_events(limit=1)
                    if events and store.outbox_rows(undelivered_only=True):
                        cwd = events[0]["event"]["payload"]["cwd"]
                        if observe_repository.repository_id(cwd) == path.stem:
                            bos_drain.recover_outbox(
                                store, BosEventLedger(observe_repository.ledger_root(cwd))
                            )
            except (OSError, ValueError, sqlite3.Error):
                logging.getLogger(__name__).warning("Observe outbox recovery unavailable for %s", path.stem)

    async def retry_observe() -> None:
        while True:
            await asyncio.sleep(30)
            await asyncio.to_thread(drain_observe)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await asyncio.to_thread(drain_observe)
        retry = asyncio.create_task(retry_observe())
        try:
            yield
        finally:
            retry.cancel()
            try:
                await retry
            except asyncio.CancelledError:
                pass
            active = [(s.id, s.task) for s in mgr.list() if s.task is not None and not s.task.done()]
            drivers = list(app.state.swarm_runs.values()) + [task for sid, task in active
                      if mgr.get(sid).swarm_id not in app.state.swarm_runs]
            for driver in drivers:
                driver.cancel()
            await asyncio.gather(*drivers, return_exceptions=True)
            for sid, _ in active:
                mgr.journal.update(sid, phase="interrupted", outcome="engine_stopped", pending_actions=[])
            mgr.journal.close()
    app = FastAPI(title="voss-harness", version="1", lifespan=lifespan)
    app.state.token = token
    app.state.sessions = mgr
    app.state.oauth_only = oauth_only
    app.state.oauth_bindings = {}
    app.state.previews = {}
    # App-scoped SwarmStore (NOT a module global module globals leak across
    # TestClient instances; Anti-Pattern). Event-log cwd defaults to
    # the serve cwd; tests override app.state.swarm_store to point at a tmp dir
    app.state.swarm_store = SwarmStore(cwd=Path(".").resolve())
    # swarm id -> the task driving its /run. Holds a strong reference: the
    # loop only keeps a weak one, and a driver that awaits long members would
    # otherwise be collected mid-run.
    app.state.swarm_runs = {}

    app.add_middleware(_BearerASGI, token=token)

    # CORS: the voss-app webview document (dev `http://localhost:5173`, prod
    # `tauri://localhost`) fetches this loopback server cross-origin and sends
    # `Authorization: Bearer …`, which makes every call a CORS request with an
    # OPTIONS preflight. Added AFTER _BearerASGI so it is the OUTERMOST
    # middleware: Starlette's CORSMiddleware answers the (unauthenticated)
    # preflight directly, before bearer auth would 401 it. Auth itself is still
    # enforced on the real request. Loopback-bound + token-gated, so the origin
    # set is restricted to localhost / 127.0.0.1 / [::1] (any port) and the
    # Tauri custom-protocol origins; credentials are off (token rides the
    # Authorization header, not cookies)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"^(https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?"
            r"|tauri://localhost|https?://tauri\.localhost)$"
        ),
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    def _require(session_id: str) -> ServerSession:
        s = mgr.get(session_id)
        if s is None:
            raise HTTPException(404, "session not found")
        return s

    @app.get("/capabilities", response_model=capabilities.Capabilities)
    def get_capabilities():
        return capabilities.report(oauth_only=oauth_only)

    @app.get("/harnesses", response_model=oauth.Catalog)
    def harnesses():
        return oauth.catalog()

    @app.post("/harness/preflight", response_model=oauth.Availability)
    def harness_preflight(body: oauth.PreflightBody):
        return oauth.preflight(body)

    def unavailable_response(availability):
        return JSONResponse({"v": 1, "status": "unavailable", "availability": availability.model_dump()})

    def selected_harness(requested):
        if requested != "auto":
            return requested
        return os.environ.get("VOSS_SERVE_DEFAULT_AUTH") or harness_config.load_harness_config().get("auth", "auto")

    @app.post("/plans/preview", response_model=preview.Result)
    async def prepare_plan(body: preview.Briefing):
        if not oauth_only:
            return preview.Result(status="unsupported", message="Connect an OAuth-only engine to preview execution.")
        result = await preview.prepare(body)
        if result.preview is not None:
            if len(app.state.previews) >= 100:
                app.state.previews.pop(next(iter(app.state.previews)))
            app.state.previews[result.preview.id] = result.preview
        return result

    @app.get("/plans/{plan_id}", response_model=preview.Result)
    async def get_plan(plan_id: str):
        accepted = mgr.journal.plan_result(plan_id)
        if accepted is not None:
            return preview.Result.model_validate(accepted)
        plan = app.state.previews.get(plan_id)
        return preview.Result(status="prepared", preview=plan) if plan else preview.Result(status="stale", message="Preview again.")

    @app.post("/plans/{plan_id}/start", response_model=preview.Result)
    async def start_plan(plan_id: str, body: preview.Start):
        if not oauth_only:
            return preview.Result(status="unsupported", message="Connect an OAuth-only engine to start this preview.")
        body.briefing = preview.normalized(body.briefing)
        payload = body.model_dump()
        try:
            previous = mgr.journal.accepted_plan(plan_id, payload)
        except ValueError as exc:
            return preview.Result(status="stale", message=str(exc))
        if previous is not None:
            return preview.Result.model_validate(previous)
        plan = app.state.previews.get(plan_id)
        if plan is None:
            return preview.Result(status="stale", message="This preview is no longer available. Preview again.")
        if body.revision != plan.revision or preview.digest(body.briefing.model_dump()) != plan.input_revision:
            return preview.Result(status="stale", message="The briefing changed. Preview again before starting.")
        try:
            unchanged = preview.repository(plan.briefing.cwd) == (plan.base_revision, plan.workspace_revision)
        except (ValueError, OSError, subprocess.TimeoutExpired):
            unchanged = False
        if not unchanged:
            return preview.Result(status="stale", message="The repository changed. Preview again before starting.")
        availability, provider = oauth.prepare(oauth.PreflightBody(harness=plan.briefing.harness, model=plan.briefing.model))
        if provider is None:
            return preview.Result(status="unavailable", availability=availability)
        s = mgr.create(cwd=Path(plan.briefing.cwd), model=availability.model, provider=provider, title=plan.briefing.source.text.splitlines()[0][:60])
        s.auth = "claude-agent" if availability.harness == "claude" else "codex-oauth"
        s.record.model_auth = availability.harness
        s.execution_plan = plan.model_dump()
        mgr.journal.begin(s.id, f"plan:{plan.id}", payload, execution_plan=s.execution_plan)
        s.task = asyncio.create_task(preview.drive(s, plan, _run_turn))
        return preview.Result.model_validate(mgr.journal.accepted_plan(plan_id, payload))

    # session CRUD

    @app.post("/session", status_code=201)
    def create_session(body: CreateSessionBody) -> dict:
        cwd = Path(body.cwd or ".").resolve()
        if oauth_only:
            availability, provider = oauth.prepare(oauth.PreflightBody(harness=selected_harness(body.auth), model=body.model or ""))
            if body.resume:
                availability = oauth.unavailable(availability, "resume_unavailable", "Read the saved task state; restarting a saved conversation is unavailable here.")
                provider = None
            if provider is None:
                return unavailable_response(availability)
            s = mgr.create(cwd=cwd, model=availability.model, provider=provider, title=body.title or "")
            s.auth = "claude-agent" if availability.harness == "claude" else "codex-oauth"
            s.record.model_auth = availability.harness
            s.review_diffs = body.review_diffs
            return {"v": 1, "status": "created", "id": s.id, "auth": s.auth, "resumed": False}
        # Serve-owner session defaults (E4): SDK clients post only {cwd} the
        # public createSession surfaces carry no auth/model. The process that
        # spawns `voss serve` may pin defaults via env; an explicit body value
        # always wins
        auth_pref = body.auth
        if auth_pref == "auto":
            auth_pref = os.environ.get("VOSS_SERVE_DEFAULT_AUTH", "auto")
        saved = {} if os.environ.get("VOSS_SERVE_FAKE_TURN") else harness_config.load_harness_config()
        record = None
        if body.resume:
            try:
                record, history = session_store.load(body.resume, cwd)
            except FileNotFoundError:
                raise HTTPException(404, f"no saved session {body.resume!r}")
            except ValueError as exc:
                raise HTTPException(409, str(exc))
            if record.model_auth:
                saved = {
                    "preferred_model": record.model, "auth": record.model_auth,
                    "preferred_provider": record.model_provider,
                }
        restore_selection = (
            auth_pref == "auto" and not body.model and (not record or record.model_auth)
            and not os.environ.get("VOSS_SERVE_DEFAULT_MODEL")
            and saved.get("auth") in ("claude", "codex", "api")
            and saved.get("preferred_model")
        )
        selected = None
        try:
            if restore_selection:
                selected = model_selection.restore(
                    saved["preferred_model"], saved["auth"], saved.get("preferred_provider"),
                )
                res = auth_mod.Resolution(source=selected.source, detail="saved selection")
                provider = selected.provider
            else:
                res, provider = _resolve_provider(auth_pref)
        except Exception:
            raise HTTPException(400, "Could not initialize the selected provider. Check your local login or use --auth.") from None
        if provider is None:
            raise HTTPException(400, f"no usable credentials ({res.detail})")
        if record:
            # forward ALL prior runs as prior context (consumed on turn 1)
            s = mgr.adopt(
                record=record,
                history=history,
                provider=provider,
                prior_context=record.runs or None,
            )
            if selected:
                s.model = selected.model
            # Twin of the create snap: a saved record may carry a model (e.g.
            # the old default) that the Codex backend 400s on. Snap the
            # EFFECTIVE session model only `record.model` stays intact so
            # the turn-end save (app.py: session_store.save) never corrupts the
            # user's saved model
            if res.source == "codex-oauth" and not auth_mod.is_codex_backend_model(
                s.model
            ):
                s.model = _codex_session_model()
            if res.source == "claude-agent" and not s.model.startswith("claude-"):
                s.model = model_selection.SUBSCRIPTION_MODELS["claude"][0].id
            s.auth = res.source
            s.review_diffs = body.review_diffs
            return {"v": 1, "id": s.id, "auth": res.source, "resumed": True}
        model = (
            (selected.model if selected else body.model)
            or os.environ.get("VOSS_SERVE_DEFAULT_MODEL")
            or saved.get("preferred_model")
            or get_config().default_model
        )
        # codex-oauth: snap a model the backend does not serve to Codex's own
        # default so it doesn't 400 the turn into a bare idle (session-scoped;
        # mirrors cli.py:686-687 without the global configure mutation)
        if res.source == "codex-oauth" and not auth_mod.is_codex_backend_model(model):
            model = _codex_session_model()
        if res.source == "claude-agent" and not model.startswith("claude-"):
            model = model_selection.SUBSCRIPTION_MODELS["claude"][0].id
        s = mgr.create(cwd=cwd, model=model, provider=provider, title=body.title or "")
        s.auth = res.source
        s.review_diffs = body.review_diffs
        if selected:
            s.record.model_auth = selected.choice.auth
            s.record.model_provider = selected.choice.provider if selected.choice.auth == "api" else None
        return {"v": 1, "id": s.id, "auth": res.source, "resumed": False}

    @app.get("/session")
    def list_sessions() -> dict:
        return {
            "v": 1,
            "sessions": [
                {"id": s.id, "cwd": str(s.cwd), "model": s.model, "title": s.title, "busy": s.busy}
                for s in mgr.list()
            ],
        }

    @app.get("/sessions/saved")
    def list_saved_sessions(cwd: str = ".") -> dict:
        records = session_store.list_sessions(Path(cwd).resolve())
        return {
            "v": 1,
            "sessions": [
                {
                    "id": r.id,
                    "name": r.name,
                    "cwd": r.cwd,
                    "model": r.model,
                    "updated_at": r.updated_at,
                    "total_cost_usd": r.total_cost_usd,
                    "turns": len(r.turns),
                    "first_task": r.first_task(),
                }
                for r in records
            ],
        }

    @app.get("/session/{session_id}")
    def get_session(session_id: str) -> dict:
        s = _require(session_id)
        return {
            "v": 1, "id": s.id, "cwd": str(s.cwd), "model": s.model,
            "title": s.title, "busy": s.busy, "auth": s.auth,
            "provider": model_selection.provider_label(s.provider, s.auth),
        }

    @app.get("/session/{session_id}/history", response_model=SessionHistory)
    async def session_history(session_id: str) -> SessionHistory:
        s = _require(session_id)
        return SessionHistory(turns=[
            HistoryTurn(role=t.role, content=t.content)
            for t in s.history.turns if t.role in ("user", "assistant", "system")
        ])

    @app.post("/session/{session_id}/clear", status_code=204, response_class=Response)
    async def clear_history(session_id: str) -> Response:
        s = _require(session_id)
        if s.busy:
            raise HTTPException(409, "a turn or model switch is already running")
        s.history = EpisodicMemory(capacity=40)
        s.prior_context = None
        return Response(status_code=204)

    @app.get("/commands", response_model=commands.CommandCatalog)
    def list_commands() -> commands.CommandCatalog:
        return commands.CommandCatalog(commands=list(commands.COMMANDS))

    @app.post("/session/{session_id}/command", response_model=commands.CommandResult)
    async def execute_command(session_id: str, body: commands.CommandRequest) -> commands.CommandResult:
        s = _require(session_id)
        mutating = body.name in {"/save-session", "/save", "/forget"} or (body.name == "/budget" and bool(body.args))
        if mutating and s.busy:
            raise HTTPException(409, "a turn, command, or model switch is already running")
        if mutating:
            s.commanding = True
        try:
            return await commands.execute(s, body)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        finally:
            if mutating:
                s.commanding = False

    @app.get("/models", response_model=model_selection.ModelCatalog)
    def list_models():
        if oauth_only:
            availability = {row.harness: row for row in oauth.catalog().harnesses}
            choices = model_selection.subscription_choices()
            for choice in choices:
                choice.connected = availability[choice.auth].available
            return model_selection.ModelCatalog(models=choices, warning="Local OAuth metadata only; remote access is checked on dispatch.")
        return model_selection.catalog()

    @app.post("/session/{session_id}/model")
    async def select_model(session_id: str, body: model_selection.ModelSelectionBody) -> dict:
        s = _require(session_id)
        if s.busy:
            raise HTTPException(409, "a turn or model switch is already running")
        if not body.model.strip() and not body.auth:
            raise HTTPException(422, "model or auth is required")
        if oauth_only:
            current = s.provider.availability.harness
            availability, provider = oauth.prepare(oauth.PreflightBody(harness=body.auth or current, model=body.model))
            if s.swarm_id or s.execution_plan:
                availability = oauth.unavailable(availability, "selection_unavailable", "Create a new task preview or swarm to change its harness or model.")
                provider = None
            if body.provider:
                availability = oauth.unavailable(availability, "unsupported_harness", "API provider selection is unavailable for managed tasks.")
                provider = None
            if provider is None:
                return unavailable_response(availability)
            s.switching = True
            try:
                await s.provider.aclose()
            finally:
                s.switching = False
            s.provider, s.model = provider, availability.model
            s.auth = "claude-agent" if availability.harness == "claude" else "codex-oauth"
            s.record.model, s.record.model_auth = s.model, availability.harness
            return get_session(session_id)
        s.switching = True
        try:
            selected = await asyncio.to_thread(model_selection.prepare, body, s.model)
            if mgr.get(session_id) is not s:
                raise HTTPException(409, "session changed during model selection")
            choice = selected.choice
            harness_config.set_preferred_selection(
                choice.id, choice.auth, choice.provider if choice.auth == "api" else None,
            )
            s.provider, s.model, s.auth = selected.provider, selected.model, selected.source
            s.record.model = selected.model
            s.record.model_auth = choice.auth
            s.record.model_provider = choice.provider if choice.auth == "api" else None
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        except OSError:
            raise HTTPException(500, "Could not save the model selection. Selection unchanged.") from None
        finally:
            s.switching = False
        return get_session(session_id)

    @app.delete("/session/{session_id}", status_code=204, response_class=Response)
    def delete_session(session_id: str) -> Response:
        if not mgr.delete(session_id):
            raise HTTPException(404, "session not found")
        return Response(status_code=204)

    @app.post("/session/{session_id}/message", status_code=202, response_model=CommandAck)
    async def post_message(session_id: str, body: MessageBody) -> CommandAck:
        key = body.command_id or uuid.uuid4().hex
        payload = body.model_dump(exclude={"command_id"})
        try:
            previous = mgr.journal.receipt(session_id, key, payload)
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        if previous:
            return previous
        s = _require(session_id)
        if s.busy:
            raise HTTPException(409, "a turn is already running")
        swarm_driver = app.state.swarm_runs.get(s.swarm_id)
        if oauth_only and swarm_driver is not None and not swarm_driver.done():
            raise HTTPException(409, "the swarm is already running")
        text = " ".join(p.text for p in body.parts if p.type == "text").strip()
        if not text:
            raise HTTPException(422, "empty message")
        if s.execution_plan is not None:
            return CommandAck(status="preview_required")
        if oauth_only:
            availability, provider = oauth.prepare(oauth.PreflightBody(harness=s.provider.availability.harness, model=s.model))
            if provider is None:
                _await_authentication(s, availability)
                return CommandAck(status="unavailable", availability=availability)
            s.switching = True
            try:
                await s.provider.aclose()
            finally:
                s.switching = False
            s.provider = provider
            if s.swarm_id:
                app.state.oauth_bindings[s.swarm_id][s.swarm_role] = provider
        ack = mgr.journal.begin(s.id, key, payload)
        s.task = asyncio.create_task(_drive_turn(s, text, body.mode))
        return ack

    @app.post("/session/{session_id}/abort", status_code=202, response_model=CommandAck)
    async def abort(session_id: str) -> CommandAck:
        snapshot = mgr.journal.snapshot(session_id)
        if snapshot is None:
            raise HTTPException(404, "task not found")
        s = mgr.get(session_id)
        driver = app.state.swarm_runs.get(snapshot.swarm_id) if snapshot.swarm_id else (s.task if s else None)
        if driver is None or driver.done():
            return CommandAck(status="not_running", run_id=snapshot.run_id, attempt_id=snapshot.attempt_id)
        driver.cancel()
        try:
            await driver
        except asyncio.CancelledError:
            pass
        mgr.journal.update(session_id, phase="cancelled", outcome="cancelled", pending_actions=[])
        return CommandAck(status="cancelled", run_id=snapshot.run_id, attempt_id=snapshot.attempt_id)

    @app.get("/session/{session_id}/cost")
    def cost(session_id: str) -> dict:
        s = _require(session_id)
        runs = s.record.runs
        chat = sum(float(r.get("cost_usd", 0.0) or 0.0) for r in runs)
        judgments = sum(float(r.get("judgments_cost_usd", 0.0) or 0.0) for r in runs)
        return {"v": 1, "total_usd": chat + judgments, "judgments_usd": judgments,
                "turns": len(runs), "budget_usd": s.budget_usd}

    @app.post("/session/{session_id}/permission")
    def reply_permission(session_id: str, body: PermissionReply) -> dict:
        s = mgr.get(session_id)
        if s is None and mgr.journal.snapshot(session_id) is not None:
            return {"v": 1, "status": "stale"}
        s = _require(session_id)
        fut = s.pending.get(body.id)
        if fut is not None and not fut.done():
            fut.set_result(body.choice)
            return {"v": 1, "status": "ok"}
        return {"v": 1, "status": "stale"}

    @app.post("/session/{session_id}/diff")
    async def reply_diff(session_id: str, body: DiffReply) -> dict:
        s = mgr.get(session_id)
        if s is None and mgr.journal.snapshot(session_id) is not None:
            return {"v": 1, "status": "stale"}
        s = _require(session_id)
        pending = s.pending_diffs.get(body.id)
        if pending is None or pending.future.done():
            return {"v": 1, "status": "stale"}
        if body.decisions and len(body.decisions) != pending.count:
            raise HTTPException(422, "Supply one decision per hunk, or an empty list to cancel.")
        pending.future.set_result(body.decisions)
        return {"v": 1, "status": "ok"}


    @app.get("/session/{session_id}/task", response_model=TaskSnapshot)
    def task_snapshot(session_id: str) -> TaskSnapshot:
        snapshot = mgr.journal.snapshot(session_id)
        if snapshot is None:
            raise HTTPException(404, "task not found")
        return snapshot

    @app.get("/session/{session_id}/graph-output", response_model=task_graph.Output)
    def graph_output(session_id: str, node_id: str, attempt_id: str, after: int = 0):
        snapshot = task_snapshot(session_id)
        node = next((node for node in snapshot.graph.nodes if node.id == node_id), None) if snapshot.graph else None
        attempt = next((item for item in node.attempts if item.id == attempt_id), None) if node else None
        if attempt is None or attempt.session_id is None or attempt.output_after is None:
            return task_graph.Output(status="unavailable", message="No journal output is linked to this worker attempt.")
        worker = mgr.journal.snapshot(attempt.session_id)
        if worker is None:
            return task_graph.Output(status="unavailable", message="The worker journal is unavailable.")
        end = attempt.output_through if attempt.output_through is not None else worker.watermark
        if attempt.output_through is None and snapshot.phase in {"cancelled", "interrupted", "failed"}:
            return task_graph.Output(status="unavailable", message="The interrupted attempt has no recorded output boundary.")
        cursor = max(after, attempt.output_after)
        batch = [item for item in mgr.journal.replay(attempt.session_id, cursor, 200) if item.cursor <= end]
        if cursor < end and (not batch or [item.cursor for item in batch] != list(range(cursor + 1, cursor + 1 + len(batch)))):
            return task_graph.Output(status="unavailable", message="The recorded output range is incomplete.", next_cursor=cursor)
        next_cursor = batch[-1].cursor if batch else cursor
        return task_graph.Output(status="available", events=[{"cursor": item.cursor, "event": item.event} for item in batch],
                                 next_cursor=next_cursor, has_more=bool(batch) and next_cursor < end)

    async def replay_events(session_id: str, after: int, *, envelopes: bool):
        cursor = after
        while True:
            batch = mgr.journal.replay(session_id, cursor)
            for entry in batch:
                cursor = entry.cursor
                if envelopes:
                    yield ServerSentEvent(id=str(cursor), event="task.event", data=entry.model_dump_json())
                elif entry.event["type"] != "task.state":
                    yield ServerSentEvent(id=str(cursor), event=entry.event["type"], data=json.dumps(entry.event))
            if not batch:
                await asyncio.sleep(0.05)

    @app.get("/session/{session_id}/task-events", responses={200: {"content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/TaskEvent"}}}}})
    async def task_events(session_id: str, after: int = 0) -> EventSourceResponse:
        snapshot = task_snapshot(session_id)
        if after < 0 or after > snapshot.watermark:
            raise HTTPException(409, "cursor outside journal; fetch snapshot and replay from zero")
        return EventSourceResponse(replay_events(session_id, after, envelopes=True), ping=15, send_timeout=30)

    @app.get("/session/{session_id}/events", responses={200: {"content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/EventEnvelope"}}}}})
    async def events(session_id: str, request: Request) -> EventSourceResponse:
        task_snapshot(session_id)
        try:
            after = int(request.headers.get("Last-Event-ID", "0"))
        except ValueError:
            raise HTTPException(422, "invalid Last-Event-ID")
        async def gen():
            yield ServerSentEvent(event="server.connected", data=E.ServerConnected().model_dump_json())
            async for event in replay_events(session_id, after, envelopes=False):
                yield event
        return EventSourceResponse(gen(), ping=15, send_timeout=30)

    # doctor (; expanded full registry via diagnostics.to_dict
    # read-only by design: repairs are CLI-local `voss doctor --fix` only)

    @app.get("/doctor")
    def doctor(auth: str = "auto", cwd: str = ".") -> dict:
        from .. import diagnostics as diag

        if oauth_only:
            availability = oauth.preflight(oauth.PreflightBody(harness=selected_harness(auth)))
            return {"v": 1, "auth_source": availability.harness, "auth_detail": availability.message,
                    "has_provider": availability.available, "default_model": availability.model,
                    "exit_code": 0 if availability.available else 1,
                    "checks": [{"name": "Local OAuth", "status": "ok" if availability.available else "unavailable",
                                "detail": availability.message, "fix": availability.login_command or "Select a supported harness"}]}
        res, provider = _resolve_provider(auth)
        checks = diag.run_all_checks(Path(cwd).resolve())
        return {
            "v": 1,
            "auth_source": res.source,
            "auth_detail": res.detail,
            "has_provider": provider is not None,
            "default_model": get_config().default_model,
            "exit_code": diag.aggregate_exit_code(checks),
            "checks": [diag.to_dict(c) for c in checks],
        }

    # memory (read-only)

    @app.get("/memory")
    def get_memory(cwd: str = ".", q: str | None = None, top_k: int = 5) -> dict:
        # Read-only view of the harness memory store for the workspace. summary
        # is a cheap fs walk (handles missing dirs); recall runs only when a
        # query is given (it lazily builds the semantic index). VADE2-11
        try:
            store = open_memory_store(Path(cwd).resolve())
            summary = store.summary()
            hits = store.recall(q, top_k=max(1, min(top_k, 50))) if q else []
        except (ValueError, OSError, RuntimeError) as exc:
            raise HTTPException(503, "Memory backend unavailable") from exc
        out: dict = {"v": 1, "summary": summary, "query": q, "hits": []}
        if q:
            out["hits"] = [
                {
                    "source": h.source,
                    "locator": h.locator,
                    "score": h.score,
                    "excerpt": h.excerpt,
                    "session_id": h.session_id,
                    "ts": h.ts,
                    "line_start": h.line_start,
                    "line_end": h.line_end,
                }
                for h in hits
            ]
        return out

    # observe

    def _observe_reject(reason: str) -> JSONResponse:
        return JSONResponse(
            {"v": 1, "decision": "reject", "reason": reason}, status_code=403
        )

    @app.get("/observe/context")
    def observe_context(cwd: str) -> dict[str, str]:
        try:
            return observe_repository.context(cwd)
        except (OSError, ValueError):
            raise HTTPException(422, "not a repository")

    @app.post("/observe/events")
    def post_observe_event(body: ObserveEventBody, background_tasks: BackgroundTasks):
        try:
            event = ObserveEventAdapter.validate_python(body.event)
        except ValidationError as exc:
            raise HTTPException(422, f"invalid observe event: {exc}")
        enrollment = get_repo_enrollment(event.repository_id)
        if enrollment is None or not enrollment.enabled:
            return _observe_reject("not_enrolled")
        if enrollment.paused:
            return _observe_reject("paused")
        if not enrollment.capture:
            return _observe_reject("capture_disabled")
        try:
            ctx = observe_repository.context(event.payload.cwd)
            root = observe_repository.canonical_worktree_root(event.payload.cwd)
        except (OSError, ValueError):
            return _observe_reject("repository_unavailable")
        if ctx != {"repositoryId": event.repository_id, "worktreeId": event.worktree_id}:
            return _observe_reject("scope_mismatch")
        loaded = load_repo_policy(root)
        if loaded.warnings:
            return _observe_reject("invalid_policy")
        policy = loaded.policy
        try:
            event.payload.argv = shlex.split(event.payload.argv_text)
        except ValueError:
            return _observe_reject("invalid_command")
        paths = [Path(event.payload.cwd), *(Path(event.payload.cwd) / arg for arg in event.payload.argv)]
        for path in paths:
            resolved = path.resolve()
            if resolved.is_relative_to(root):
                rel = resolved.relative_to(root).as_posix()
                if any(
                    fnmatch.fnmatchcase(rel, pattern) or
                    fnmatch.fnmatchcase(rel + "/", pattern) or
                    any(fnmatch.fnmatchcase(parent.as_posix() + "/", pattern) for parent in Path(rel).parents)
                    for pattern in policy.exclude_paths
                ):
                    return _observe_reject("excluded_path")
        if policy.commands is not None and not any(
            event.payload.argv[:len(command.argv)] == command.argv
            for command in policy.commands.values()
        ):
            return _observe_reject("command_not_allowed")
        event.repository_state_id = observe_repository.repository_state_id(root)
        event.payload.argv = redact_argv(event.payload.argv)
        event.payload.argv_text = redact_text(event.payload.argv_text)
        store = ObserveStore(event.repository_id)
        try:
            with store.transaction():
                result = persist_observe(store, event, body, policy.capture.max_output_bytes)
        finally:
            store.close()
        background_tasks.add_task(drain_observe, event.repository_id)
        return {
            "v": 1,
            "decision": result.decision,
            "reason": result.reason,
            "policy_version": result.policy_version,
            "event_id": result.event_id,
            "fingerprint": result.fingerprint,
            "investigation_id": result.investigation_id,
            "derived_event_id": result.derived_event.event_id if result.derived_event else None,
        }

    def persist_observe(store, event, body, output_limit):
        if store.has_event(event.event_id):
            return observe_admission.admit(store, event)
        redacted = []
        remaining = output_limit
        for item in body.evidence:
            content = redact_text(item.content).encode("utf-8")
            if len(content) > remaining:
                head = remaining * 3 // 4
                tail = remaining - head
                content = content[:head] + (content[-tail:] if tail else b"")
                item.truncated = True
                if hasattr(event.payload, "truncated"):
                    event.payload.truncated = True
            remaining -= len(content)
            redacted.append(content)
        evidence_ids: list[str] = []
        for index, (item, content) in enumerate(zip(body.evidence, redacted)):
            # Evidence ids derive from event_id so a duplicate POST is an
            # INSERT OR IGNORE no-op instead of a second evidence row
            evidence_id = f"{event.event_id}-ev{index}"
            store.put_evidence(
                evidence_id,
                event.event_id,
                item.kind,
                content,
                truncated=item.truncated,
            )
            evidence_ids.append(evidence_id)
        if evidence_ids:
            event.evidence_refs = [*event.evidence_refs, *evidence_ids]
        error_text = "\n".join(
            content.decode("utf-8", errors="replace")
            for item, content in zip(body.evidence, redacted)
            if item.kind == "command_output"
        )
        return observe_admission.admit(store, event, error_text=error_text)

    @app.get("/observe/events")
    def list_observe_events(
        repository_id: str = Query(pattern=r"^[A-Za-z0-9_-]{1,128}$"), cursor: int = 0, limit: int = 100
    ) -> dict:
        limit = max(1, min(limit, 1000))
        if not db_path(repository_id).exists():
            return {"v": 1, "events": [], "next_cursor": cursor}
        store = ObserveStore(repository_id)
        try:
            events = store.list_events(after_seq=cursor, limit=limit)
        finally:
            store.close()
        return {
            "v": 1,
            "events": events,
            "next_cursor": events[-1]["seq"] if events else cursor,
        }

    @app.get("/observe/settings")
    def get_observe_settings() -> dict:
        enrollment = load_enrollment()
        return {
            "v": 1,
            "repositories": {
                rid: repo.model_dump(mode="json")
                for rid, repo in enrollment.repositories.items()
            },
        }

    @app.patch("/observe/settings")
    def patch_observe_settings(body: ObserveSettingsBody) -> dict:
        current = get_repo_enrollment(body.repository_id) or RepoEnrollment()
        try:
            updated = RepoEnrollment.model_validate({
                **current.model_dump(), **body.enrollment.model_dump(exclude_unset=True)
            })
        except ValidationError:
            raise HTTPException(422, "invalid enrollment settings")
        set_repo_enrollment(body.repository_id, updated)
        return {
            "v": 1,
            "repository_id": body.repository_id,
            "enrollment": updated.model_dump(mode="json"),
        }

    @app.get("/observe/stream")
    async def observe_stream(
        request: Request, repository_id: str, cursor: int | None = None
    ):
        enrollment = get_repo_enrollment(repository_id)
        if enrollment is None or not enrollment.enabled:
            return _observe_reject("not_enrolled")
        if cursor is None:
            last_id = request.headers.get("last-event-id", "")
            cursor = int(last_id) if last_id.isdigit() else 0

        async def gen():
            store = ObserveStore(repository_id)
            try:
                yield ServerSentEvent(
                    event="server.connected", data=E.ServerConnected().model_dump_json()
                )
                after = cursor
                while True:
                    batch = store.list_events(after_seq=after, limit=500)
                    for item in batch:
                        after = item["seq"]
                        yield ServerSentEvent(
                            event="observe.event",
                            id=str(item["seq"]),
                            data=json.dumps(item, sort_keys=True),
                        )
                    if not batch:
                        await asyncio.sleep(0.25)
            finally:
                store.close()

        return EventSourceResponse(gen(), ping=15, send_timeout=30)

    # swarm ( VSWARM-02/03/04/06/08)

    def _publish_swarm_graph(swarm_id: str, event: dict | None = None):
        store = app.state.swarm_store
        swarm = store.get(swarm_id)
        agents = store.list_agents_by_swarm(swarm_id)
        coordinator = next((rec for rec in agents if rec["role"] == "coordinator"), None)
        if swarm is None or coordinator is None:
            return
        owner = mgr.journal.snapshot(coordinator["session_id"])
        graph = task_graph.swarm_state(swarm, owner.graph, owner, event)
        for rec in agents:
            if mgr.get(rec["session_id"]) is not None:
                mgr.journal.update(rec["session_id"], graph=graph.model_dump())

    def _emit_swarm_event(swarm_id: str, ev: E._Base, graph_event: dict | None = None) -> None:
        """Fan a swarm event out to EVERY registered session's queue (Pitfall
        3 — not just the coordinator). Validates the swarm exists first so a
        forged swarm_id cannot inject into unrelated queues (T-V25-04-04)."""
        store = app.state.swarm_store
        if store.get(swarm_id) is None:
            return
        _publish_swarm_graph(swarm_id, graph_event or ev.model_dump())
        for rec in store.list_agents_by_swarm(swarm_id):
            sess = mgr.get(rec["session_id"])
            if sess is not None:
                EventBusRenderer(sess.queue, session_id=sess.id).emit(ev)

    def _assign_to_session(swarm_id: str, task: Any, session_id: str, output_after: int | None = None) -> None:
        """Hand a task to a harness session: mark it, unblock it, announce it.

        Shared by the coordinator's assign message and the native half of
        `/swarm/{id}/run` so both produce the same store state and the same
        `swarm.assign`.
        """
        store = app.state.swarm_store
        store.mark_assigned(swarm_id, task.id, session_id=session_id)
        builder = mgr.get(session_id)
        if builder is not None:
            builder.swarm_task_id = task.id
            builder.swarm_owned_files = task.owned_files
            # VSWARM-05: attach the per-task ownership-deny policy now that
            # owned_files are known. _run_turn injects it into the gate
            builder.swarm_policy = build_ownership_policy(task.owned_files)
            # In-process unblock ( independent of queue state)
            if builder.gate_event is not None:
                builder.gate_event.set()
        event = E.SwarmAssign(
                swarm_id=swarm_id,
                task_id=task.id,
                session_id=session_id,
                owned_files=task.owned_files,
                role=(builder.swarm_role if builder else None) or "builder",
            )
        snapshot = mgr.journal.snapshot(session_id) if builder else None
        metadata = {**event.model_dump(), "attempt_id": snapshot.attempt_id if output_after is not None else event.eid,
                    "model": builder.model if builder else None, "harness": getattr(getattr(builder, "provider", None), "availability", None),
                    "output_after": output_after, "launched": output_after is not None}
        availability = metadata["harness"]
        metadata["harness"] = availability.harness if availability else None
        metadata["provider"] = availability.provider if availability else None
        if builder:
            metadata.update(task_graph.location(builder.cwd))
        _emit_swarm_event(swarm_id, event, metadata)

    @app.post("/swarm", status_code=201)
    async def create_swarm(body: CreateSwarmBody) -> dict:
        store = app.state.swarm_store
        cwd = Path(body.cwd or ".").resolve()
        # Persist the explicit roster (R3 per-role agent axis) so the stored /
        # replayed swarm matches what is spawned; swarm.roster is then the single
        # source the spawn loop iterates
        explicit = (
            [Role(**r.model_dump()) for r in body.roster] if body.roster else None
        )
        bindings = {}
        if oauth_only:
            from ..swarm_store import default_roster
            explicit = explicit or default_roster(body.builders)
            for role in explicit:
                harness = selected_harness(role.auth_pref) if is_native(role) else role.agent
                availability, provider = oauth.prepare(oauth.PreflightBody(harness=harness, model="" if role.model == "default" else role.model))
                if role.command or role.args:
                    availability = oauth.unavailable(availability, "custom_launcher_unavailable", "Custom commands and extra launch arguments are unavailable for OAuth-only tasks.")
                    provider = None
                if provider is not None and not is_native(role):
                    try:
                        oauth.check_cli(provider)
                    except auth_mod.OAuthRequired:
                        availability, provider = provider.blocked, None
                if provider is None:
                    return unavailable_response(availability)
                role.auth_pref, role.model = harness, availability.model
                bindings[role.name] = provider
        swarm = store.create(
            goal=body.goal, cwd=str(cwd), builders=body.builders, roster=explicit
        )
        if oauth_only:
            app.state.oauth_bindings[swarm.id] = bindings
        # Per-role spawn: native (agent="voss") roles run the in-process run_turn
        # loop ( behavior). R3 CLI roles (agent!="voss") are spawned in their
        # own git worktree by the host that integration lands in a later wave
        # here they are recorded as pending so the axis is visible end-to-end
        # Builders are spawn-gated (asyncio.Event created HERE async handler)
        spawned: list[dict] = []
        for role in swarm.roster:
            if not is_native(role):
                spawned.append(
                    {
                        "role": role.name,
                        "agent": role.agent,
                        "model": role.model,
                        "pending": True,
                    }
                )
                continue
            if oauth_only:
                provider = bindings[role.name]
                model = provider.availability.model
            else:
                res, provider = _resolve_provider(role.auth_pref)
                if provider is None:
                    raise HTTPException(400, f"no usable credentials ({res.detail})")
                model = _effective_model(role.model, res)
            sess = mgr.create(cwd=cwd, model=model, provider=provider, title=role.name)
            sess.swarm_id = swarm.id
            sess.swarm_role = role.name
            if role.name.startswith("builder"):
                sess.gate_event = asyncio.Event()
            store.register_agent(swarm.id, sess.id, role.name, [])
            spawned.append(
                {
                    "session_id": sess.id,
                    "role": role.name,
                    "model": sess.model,
                    "agent": role.agent,
                }
            )
        return {"v": 1, "id": swarm.id, "sessions": spawned}

    @app.get("/swarm/{swarm_id}")
    def get_swarm(swarm_id: str) -> dict:
        swarm = app.state.swarm_store.get(swarm_id)
        if swarm is None:
            raise HTTPException(404, "swarm not found")
        return {"v": 1, "swarm": swarm.model_dump()}

    @app.post("/swarm/{swarm_id}/task", status_code=201)
    def create_swarm_task(swarm_id: str, body: CreateTaskBody) -> dict:
        store = app.state.swarm_store
        if store.get(swarm_id) is None:
            raise HTTPException(404, "swarm not found")
        try:
            # add_task runs validate_no_overlap; overlap → 4xx (VSWARM-06)
            task = store.add_task(
                swarm_id, body.goal, body.owned_files, body.depends_on
            )
        except OwnershipOverlapError as exc:
            raise HTTPException(409, str(exc))
        _publish_swarm_graph(swarm_id)
        return {"v": 1, "task": task.model_dump()}

    @app.post("/swarm/{swarm_id}/message", status_code=202)
    async def swarm_message(swarm_id: str, body: SwarmMessageBody) -> dict:
        store = app.state.swarm_store
        swarm = store.get(swarm_id)
        if swarm is None:
            raise HTTPException(404, "swarm not found")

        if body.kind == "assign":
            if not body.task_id or not body.session_id:
                raise HTTPException(422, "assign requires task_id and session_id")
            task = swarm.task(body.task_id)
            if task is None:
                raise HTTPException(404, "task not found")
            _assign_to_session(swarm_id, task, body.session_id)
        elif body.kind == "worker_done":
            if body.task_id:
                store.mark_done(swarm_id, body.task_id, summary=body.summary)
            _emit_swarm_event(
                swarm_id,
                E.SwarmWorkerDone(
                    swarm_id=swarm_id,
                    task_id=body.task_id or "",
                    session_id=body.session_id or "",
                    summary=body.summary,
                ),
            )
        elif body.kind == "gate":
            # A reviewer reject (or any gate) records a decision audit (VSWARM-10)
            if "reject" in body.gate_type:
                store.record_gate_decision(
                    swarm_id,
                    body.task_id or "",
                    body.session_id or "",
                    gate_type=body.gate_type,
                    confidence=body.confidence,
                    detail=body.detail,
                )
            _emit_swarm_event(
                swarm_id,
                E.SwarmGate(
                    swarm_id=swarm_id,
                    task_id=body.task_id or "",
                    gate_type=body.gate_type,
                    detail=body.detail,
                ),
            )
        elif body.kind == "needs_operator":
            _emit_swarm_event(
                swarm_id,
                E.SwarmNeedsOperator(
                    swarm_id=swarm_id,
                    task_id=body.task_id or "",
                    session_id=body.session_id or "",
                    tool_name=body.tool_name,
                    path=body.path,
                ),
            )
        elif body.kind == "complete":
            _emit_swarm_event(
                swarm_id,
                E.SwarmComplete(
                    swarm_id=swarm_id,
                    task_count=body.task_count or len(swarm.tasks),
                    summary=body.summary,
                ),
            )
        return {"v": 1, "status": "accepted"}

    def _r3_event_adapter(swarm_id: str):
        """Map the orchestrator's plain-dict events onto typed SSE events.

        `swarm_runtime` stays transport-free (emits dicts); this closure is the
        seam that turns them into `E.Swarm*` models fanned out via
        `_emit_swarm_event` (R3 execution-plane → SSE)."""

        def emit(ev: dict) -> None:
            etype = ev.get("type")
            if etype == "swarm.assign":
                # CLI members are subprocesses, not harness sessions, so
                # `role` + `task_id` are the member identity here.
                _emit_swarm_event(
                    swarm_id,
                    E.SwarmAssign(
                        swarm_id=swarm_id,
                        task_id=ev.get("task_id", ""),
                        session_id="",
                        owned_files=ev.get("owned_files") or [],
                        role=ev.get("role", ""),
                    ),
                    graph_event=ev,
                )
            elif etype == "swarm.worker_done":
                _emit_swarm_event(
                    swarm_id,
                    E.SwarmWorkerDone(
                        swarm_id=swarm_id,
                        task_id=ev.get("task_id", ""),
                        session_id="",
                        summary=ev.get("summary"),
                    ),
                    graph_event=ev,
                )
            elif etype == "swarm.gate":
                _emit_swarm_event(
                    swarm_id,
                    E.SwarmGate(
                        swarm_id=swarm_id,
                        task_id=ev.get("task_id", ""),
                        gate_type=ev.get("gate_type", ""),
                        detail=ev.get("detail", ""),
                    ),
                    graph_event=ev,
                )
            elif etype == "swarm.needs_operator":
                paths = ev.get("paths") or []
                _emit_swarm_event(
                    swarm_id,
                    E.SwarmNeedsOperator(
                        swarm_id=swarm_id,
                        task_id=ev.get("task_id", ""),
                        session_id=ev.get("session_id", ""),
                        tool_name=ev.get("tool_name", "fs_write"),
                        path=", ".join(paths) if paths else ev.get("path"),
                    ),
                    graph_event=ev,
                )
            elif etype == "swarm.candidate_ready":
                _emit_swarm_event(
                    swarm_id,
                    E.SwarmCandidateReady(
                        swarm_id=swarm_id,
                        task_id=ev.get("task_id", ""),
                        role=ev.get("role", ""),
                        branch=ev.get("branch", ""),
                        worktree=ev.get("worktree", ""),
                        head=ev.get("head", ""),
                        summary=ev.get("summary"),
                    ),
                    graph_event=ev,
                )
            elif etype == "swarm.candidates_ready":
                _emit_swarm_event(
                    swarm_id,
                    E.SwarmCandidatesReady(
                        swarm_id=swarm_id,
                        candidate_count=ev.get("candidate_count", 0),
                    ),
                    graph_event=ev,
                )
            elif etype == "swarm.complete":
                _emit_swarm_event(
                    swarm_id,
                    E.SwarmComplete(
                        swarm_id=swarm_id,
                        task_count=ev.get("task_count", 0),
                        summary=ev.get("summary"),
                    ),
                    graph_event=ev,
                )

        return emit

    @app.post("/swarm/{swarm_id}/run", status_code=202)
    async def run_swarm(swarm_id: str) -> dict:
        """Drive a swarm's members headlessly. Fire-and-forget: the orchestrator
        streams progress over the swarm SSE plane; the route returns immediately.

        Both member kinds run. CLI roles go through `run_cli_swarm` (worktree
        spawn, ownership reconciliation, candidate preservation); native builder
        sessions run one turn each on the in-process path. The default roster is
        all native, so without that second half `/run` on a default swarm did
        nothing at all.

        A swarm with no tasks is seeded here first: one coordinator LLM call
        decomposes the goal into one task per runnable member. A client that
        seeded its own tasks keeps them — this only fills an empty plan.

        One run per swarm at a time, and a member whose session is mid-turn is
        left alone, so a second call cannot start a second turn in a session."""
        store = app.state.swarm_store
        swarm = store.get(swarm_id)
        if swarm is None:
            raise HTTPException(404, "swarm not found")

        from ..swarm_coordinator import SeedError, seed_tasks
        from ..swarm_runtime import run_cli_swarm, subprocess_spawn

        repo_root = Path(swarm.cwd)
        on_event = _r3_event_adapter(swarm_id)
        coordinators = [mgr.get(rec["session_id"]) for rec in store.list_agents_by_swarm(swarm_id)
                        if rec.get("role") == "coordinator"]
        coordinator = next((session for session in coordinators if session is not None), None)
        if coordinator is None:
            raise HTTPException(409, "swarm has no native coordinator task")
        previous = mgr.journal.receipt(coordinator.id, "swarm.run", {"swarm_id": swarm_id})
        if previous:
            return previous.model_dump()
        if coordinator.busy:
            raise HTTPException(409, "coordinator is busy")
        bindings = app.state.oauth_bindings.get(swarm_id, {})
        if oauth_only:
            refreshed = {}
            for role in swarm.roster:
                availability, provider = oauth.prepare(oauth.PreflightBody(harness=role.auth_pref, model=role.model))
                if provider is not None and not is_native(role):
                    try:
                        oauth.check_cli(provider)
                    except auth_mod.OAuthRequired:
                        availability, provider = provider.blocked, None
                if provider is None:
                    _await_authentication(coordinator, availability)
                    return unavailable_response(availability)
                refreshed[role.name] = provider
            bindings.update(refreshed)
            for rec in store.list_agents_by_swarm(swarm_id):
                session = mgr.get(rec["session_id"])
                if session is not None:
                    session.provider = bindings[session.swarm_role]
        cli_roles = [role for role in swarm.roster if not is_native(role)]
        # Native builders are sessions, not subprocesses, so they are found
        # through the agents the create route registered, not the roster.
        native_builders = [
            rec["session_id"]
            for rec in store.list_agents_by_swarm(swarm_id)
            if str(rec.get("role", "")).startswith("builder")
        ]
        members = len(cli_roles) + len(native_builders)

        async def _seed() -> bool:
            """Fill an empty plan. False means the run must not proceed."""
            if swarm.tasks or not members:
                return True
            coord = next(
                (r for r in swarm.roster if r.name == "coordinator"), swarm.roster[0]
            )
            try:
                if oauth_only:
                    provider, model = coordinator.provider, coordinator.model
                else:
                    res, provider = _resolve_provider(coord.auth_pref)
                    if provider is None:
                        raise SeedError(f"no usable credentials ({res.detail})")
                    model = _effective_model(coord.model, res)
                await seed_tasks(
                    store,
                    swarm_id,
                    provider=provider,
                    # _effective_model, not the config default: on a
                    # codex-oauth host that default is an Anthropic id.
                    model=model,
                    cwd=str(repo_root),
                    slots=members,
                )
            except Exception as exc:  # noqa: BLE001 — surfaced, never silent
                on_event(
                    {
                        "type": "swarm.gate",
                        "swarm_id": swarm_id,
                        "task_id": "",
                        "gate_type": "decompose_failed",
                        "detail": str(exc),
                    }
                )
                return False
            return True

        async def _run_native_builder(session_id: str, task: Any) -> None:
            """One native builder: assign, run its turn, report it done."""
            sess = mgr.get(session_id)
            if sess is None or sess.busy:
                raise RuntimeError("native builder is unavailable or busy")
            before = mgr.journal.snapshot(sess.id).watermark
            mgr.journal.begin(sess.id, f"swarm:{task.id}", {"goal": task.goal}, swarm_id=swarm_id, swarm_task_id=task.id)
            _assign_to_session(swarm_id, task, session_id, before)
            sess.task = asyncio.create_task(_drive_turn(sess, task.goal, "auto"))
            try:
                await sess.task
            finally:
                snapshot = mgr.journal.snapshot(sess.id)
                _publish_swarm_graph(swarm_id, {"type": "swarm.worker_done", "task_id": task.id,
                    "attempt_id": snapshot.attempt_id, "output_through": snapshot.watermark,
                    "state": snapshot.phase if snapshot.phase != "active" else "cancelled", "detail": snapshot.outcome})
            if mgr.journal.snapshot(sess.id).phase != "completed":
                raise RuntimeError("native builder did not complete")
            store.mark_done(swarm_id, task.id, summary=None)
            event = E.SwarmWorkerDone(
                swarm_id=swarm_id, task_id=task.id, session_id=session_id, summary=None,
            )
            snapshot = mgr.journal.snapshot(sess.id)
            _emit_swarm_event(swarm_id, event, {**event.model_dump(), "attempt_id": snapshot.attempt_id, "output_through": snapshot.watermark})

        def _gate(gate_type: str, detail: str, task_id: str = "") -> None:
            on_event(
                {
                    "type": "swarm.gate",
                    "swarm_id": swarm_id,
                    "task_id": task_id,
                    "gate_type": gate_type,
                    "detail": detail,
                }
            )

        def _member_event(ev: dict, held: dict) -> None:
            """Pass member events through, holding the run's terminal event.

            `run_cli_swarm` ends with `swarm.candidates_ready` or
            `swarm.complete`, which fires when the CLI half finishes — at once,
            and with a count of zero, when there is no CLI half. The run emits
            one of its own once both halves are done.
            """
            kind = ev.get("type")
            if kind == "swarm.candidates_ready":
                held["candidates"] += int(ev.get("candidate_count") or 0)
                return
            if kind == "swarm.complete":
                return
            on_event(ev)

        async def _drive() -> None:
            try:
                if not await _seed():
                    blocked = next((p.blocked for p in bindings.values() if p.blocked is not None), None)
                    if blocked is not None:
                        _await_authentication(coordinator, blocked)
                    else:
                        mgr.journal.update(coordinator.id, phase="failed", outcome="decompose_failed")
                    return
                # `run_cli_swarm` zips CLI roles against the plan in order, so
                # the native builders take the tail and the two halves never
                # contend. Open tasks only: a re-run must not redo finished work.
                native_tasks = [
                    task
                    for task in store.get(swarm_id).tasks[len(cli_roles) :]
                    if task.state == OPEN
                ]
                _publish_swarm_graph(swarm_id)
                held = {"candidates": 0}
                results = await asyncio.gather(
                    run_cli_swarm(
                        store,
                        repo_root,
                        swarm_id,
                        spawn_fn=(lambda argv, cwd: oauth.spawn_cli(bindings[cwd.name], argv, cwd)) if oauth_only else subprocess_spawn,
                        preflight_fn=(lambda role: oauth.check_cli(bindings[role.name])) if oauth_only else None,
                        on_event=lambda ev: _member_event(ev, held),
                    ),
                    *(
                        _run_native_builder(sid, task)
                        for sid, task in zip(native_builders, native_tasks)
                    ),
                    return_exceptions=True,
                )
                if isinstance(results[0], BaseException):
                    # run_cli_swarm isolates its members, so this is the run
                    # itself failing, not one member.
                    _gate("run_failed", f"CLI members: {results[0]}")
                cli_ran = results[0] if isinstance(results[0], list) else []
                failed = [r for r in cli_ran if r.error]
                if isinstance(results[0], BaseException):
                    failed.append(results[0])
                for task, outcome in zip(native_tasks, results[1:]):
                    if isinstance(outcome, BaseException):
                        _gate("member_failed", f"native builder: {outcome}", task.id)
                        failed.append(outcome)
                if not cli_ran and not native_tasks and not failed:
                    mgr.journal.update(coordinator.id, phase="waiting", outcome="no_runnable_members")
                    # Nothing was driven: a re-run of a finished plan, or a
                    # swarm with no members. Silence beats a terminal event for
                    # a run that never happened.
                    return
                blocked = next((p.blocked for p in bindings.values() if p.blocked is not None), None)
                if blocked is not None:
                    _await_authentication(coordinator, blocked)
                elif failed:
                    # Not `complete`: a client would read the run as finished.
                    # Each failure already has its own member_failed gate.
                    total = len(cli_ran) + len(native_tasks)
                    _gate("run_incomplete", f"{len(failed)} of {total} members failed")
                    mgr.journal.update(coordinator.id, phase="failed", outcome="run_incomplete")
                elif any(task.state not in (DONE, CANDIDATE_READY) for task in store.get(swarm_id).tasks):
                    mgr.journal.update(coordinator.id, phase="waiting", outcome="unfinished_tasks")
                elif held["candidates"]:
                    mgr.journal.update(coordinator.id, phase="candidate_ready", outcome="candidates_ready")
                    on_event(
                        {
                            "type": "swarm.candidates_ready",
                            "swarm_id": swarm_id,
                            "candidate_count": held["candidates"],
                        }
                    )
                else:
                    mgr.journal.update(coordinator.id, phase="completed", outcome="done")
                    on_event(
                        {
                            "type": "swarm.complete",
                            "swarm_id": swarm_id,
                            "task_count": len(cli_ran) + len(native_tasks),
                        }
                    )
            except asyncio.CancelledError:
                mgr.journal.update(coordinator.id, phase="cancelled", outcome="cancelled", pending_actions=[])
                raise
            except Exception as exc:  # noqa: BLE001 — must not crash the loop, must not go quiet
                _gate("run_failed", str(exc))
                mgr.journal.update(coordinator.id, phase="failed", outcome="run_failed")
            finally:
                coordinator.task = None

        if swarm_id in app.state.swarm_runs:
            return {"v": 1, "status": "already running"}
        ack = mgr.journal.begin(coordinator.id, "swarm.run", {"swarm_id": swarm_id}, swarm_id=swarm_id)
        driver = asyncio.create_task(_drive())
        coordinator.task = driver
        app.state.swarm_runs[swarm_id] = driver
        driver.add_done_callback(lambda _t: app.state.swarm_runs.pop(swarm_id, None))
        return ack.model_dump()

    # OpenAPI: force the event union into components

    _force_event_schema(app)
    return app


def _force_event_schema(app: FastAPI) -> None:
    """Ensure EventEnvelope (the AgentEvent union) lands in OpenAPI components."""
    base = app.openapi

    def openapi():
        schema = base()
        comps = schema.setdefault("components", {}).setdefault("schemas", {})
        env = E.EventEnvelope.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        for name, defn in env.pop("$defs", {}).items():
            comps.setdefault(name, defn)
        comps["EventEnvelope"] = env
        task_event = TaskEvent.model_json_schema(ref_template="#/components/schemas/{model}")
        comps.update(task_event.pop("$defs", {}))
        comps["TaskEvent"] = task_event
        app.openapi_schema = schema
        return schema

    app.openapi = openapi  # type: ignore[assignment]
