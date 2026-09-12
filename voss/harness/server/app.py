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
import uuid
from concurrent.futures import Future
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field, ValidationError
from sse_starlette import EventSourceResponse, ServerSentEvent
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from voss_runtime import EpisodicMemory, get_config  # noqa: F401  (get_config used lazily)

from .. import auth as auth_mod
from .. import session as session_store
from ..agent import run_turn
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
    OwnershipOverlapError,
    Role,
    SwarmStore,
    build_ownership_policy,
)
from ..tools import make_toolset
from . import events as E
from .renderer import EventBusRenderer
from .sessions import ServerSession, SessionManager

PERMISSION_TIMEOUT_S = 300.0


class _FakeResolution:
    """Stand-in Resolution for the VOSS_SERVE_FAKE_TURN test seam."""

    source = "fake"
    detail = "VOSS_SERVE_FAKE_TURN"


class _FakePlan:
    confidence = 0.9
    steps: list = []


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
    """Default model id for codex-oauth sessions (gpt-5.x only).

    The ChatGPT-account Codex backend rejects non-gpt-5.x model ids; the harness
    default (`claude-sonnet-4-5`) 400s there and the turn dies before any output.
    Mirrors `cli._codex_default_model` WITHOUT importing `cli` (whose top-level
    `@click` command registration has heavy import side effects): read Codex CLI's
    own default, else fall back to the first subscription codex model.
    """
    m = auth_mod.load_codex_default_model()
    if m and m.startswith("gpt-5."):
        return m
    from ..subscription_models import SUBSCRIPTION_MODELS

    return SUBSCRIPTION_MODELS["codex"][0].id


def _effective_model(requested: str | None, res: Any) -> str:
    """Resolve a requested model id to a concrete one for a spawned session.

    The swarm roster uses the literal `"default"` sentinel (swarm_store.Role)
    to mean 'no explicit choice' — treat it (and None) as unspecified and fall
    through to the serve-env default then the config default. An explicit,
    non-sentinel model is honored as-is. In all cases the codex-oauth gpt-5.x
    constraint is applied last (mirrors create_session, app.py:556-565), so a
    non-gpt-5.x id never reaches the Codex backend and 400s the turn.
    """
    model = requested if (requested and requested != "default") else None
    model = (
        model
        or os.environ.get("VOSS_SERVE_DEFAULT_MODEL")
        or get_config().default_model
    )
    if res.source == "codex-oauth" and not model.startswith("gpt-5."):
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
    from ..memory_store import MemoryStore
    from ..swarm_store import scoped_recall

    store = MemoryStore(session.cwd)
    hits = scoped_recall(store, text, session.swarm_owned_files)
    if not hits:
        return ""
    lines = ["## Task-scoped recall (your owned files)"]
    for h in hits:
        lines.append(f"- {h.locator}: {h.excerpt}")
    return "\n".join(lines)


# turn runner


async def _run_turn(session: ServerSession, text: str, mode: str) -> None:
    """Drive one turn; publish events; persist. Runs as session.task."""
    loop = asyncio.get_running_loop()
    renderer = EventBusRenderer(session.queue, session_id=session.id, loop=loop)

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
            renderer.show_thinking("planning 1/1")
            renderer.show_plan(_FakePlan(), cost_usd=0.0)
            renderer.stream_delta("hello ")
            renderer.stream_delta("from fake turn")
            renderer.finalize_stream(role="assistant", confidence=0.9, cost_usd=0.0)
            renderer.show_final(f"echo: {text}", confidence=0.9, cost_usd=0.0)
        finally:
            renderer.session_idle()
            session.task = None
        return

    try:
        renderer.show_user(text)
        tools = make_toolset(session.cwd, renderer=renderer)
        gate = PermissionGate(
            mode=mode,  # type: ignore[arg-type]
            store=PermissionStore.load(session.cwd),
            auto_yes=False,
            # VSWARM-05: a swarm builder's ownership-deny policy rides the
            # deny-wins project_policy layer. None for non-swarm sessions →
            # byte-identical to pre- behaviour
            project_policy=session.swarm_policy,
        )
        _install_server_permissions(gate, session, renderer)

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
            from ..cli import _render_project_index_text, _render_code_recall_text

            project_index_text = _render_project_index_text(
                session.cwd, session_id=session.id
            )
            # VSWARM-07: a swarm builder gets recall filtered to its ownedFiles
            # non-swarm sessions keep the unscoped code-recall path unchanged
            if session.swarm_owned_files:
                code_recall_text = _swarm_recall_text(session, text)
            else:
                code_recall_text = _render_code_recall_text(
                    session.cwd, text, session_id=session.id
                )
        except Exception:
            project_index_text = ""
            code_recall_text = ""

        result = await run_turn(
            text,
            tools=tools,
            cwd=session.cwd,
            renderer=renderer,
            model=session.model,
            provider=session.provider,
            permissions=gate,
            history=session.history,
            session_id=session.id,
            voss_md_text=voss_md_text,
            prior_context=session.prior_context,
        )
        # Consume resume context once: deep history now flows via session.history
        session.prior_context = None
        renderer.show_final(
            result.final, confidence=result.confidence, cost_usd=result.cost_usd
        )
        if result.run is not None:
            session.record.runs.append(asdict(result.run))
    except asyncio.CancelledError:
        raise
    except Exception as e:  # noqa: BLE001 — surface, don't vanish into a bare idle
        # A provider/backend failure (e.g. a codex 4xx from run_turn ->
        # provider.stream) would otherwise propagate past this finally as an
        # un-awaited task exception, leaving the user a bare session.idle with
        # no signal. Surface it visibly on the transcript BEFORE the finally
        # idles mirrors agent.py's interrupt/batch-invariant error paths
        renderer.stream_delta(f"\n[error: {e}]\n")
        renderer.finalize_stream(role="system", confidence=None, cost_usd=None)
    finally:
        try:
            session_store.save(session.record, session.history)
        except Exception:
            pass
        renderer.session_idle()
        session.task = None


# request models


class CreateSessionBody(BaseModel):
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


class PermissionReply(BaseModel):
    id: str
    choice: str  # a | A | d  (or y | n for scope)


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


def create_app(token: str | None = None) -> FastAPI:
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
        # shutdown: cancel any in-flight turns
        for s in mgr.list():
            if s.busy and s.task is not None:
                s.task.cancel()

    app = FastAPI(title="voss-harness", version="1", lifespan=lifespan)
    app.state.token = token
    app.state.sessions = mgr
    # App-scoped SwarmStore (NOT a module global module globals leak across
    # TestClient instances; Anti-Pattern). Event-log cwd defaults to
    # the serve cwd; tests override app.state.swarm_store to point at a tmp dir
    app.state.swarm_store = SwarmStore(cwd=Path(".").resolve())

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

    # session CRUD

    @app.post("/session", status_code=201)
    def create_session(body: CreateSessionBody) -> dict:
        cwd = Path(body.cwd or ".").resolve()
        # Serve-owner session defaults (E4): SDK clients post only {cwd} the
        # public createSession surfaces carry no auth/model. The process that
        # spawns `voss serve` may pin defaults via env; an explicit body value
        # always wins
        auth_pref = body.auth
        if auth_pref == "auto":
            auth_pref = os.environ.get("VOSS_SERVE_DEFAULT_AUTH", "auto")
        res, provider = _resolve_provider(auth_pref)
        if provider is None:
            raise HTTPException(400, f"no usable credentials ({res.detail})")
        if body.resume:
            try:
                record, history = session_store.load(body.resume, cwd)
            except FileNotFoundError:
                raise HTTPException(404, f"no saved session {body.resume!r}")
            except ValueError as exc:  # ambiguous id
                raise HTTPException(409, str(exc))
            # forward ALL prior runs as prior context (consumed on turn 1)
            s = mgr.adopt(
                record=record,
                history=history,
                provider=provider,
                prior_context=record.runs or None,
            )
            # Twin of the create snap: a saved record may carry a non-gpt-5.x
            # model (e.g. the old default) that the Codex backend 400s on. Snap
            # the EFFECTIVE session model only `record.model` stays intact so
            # the turn-end save (app.py: session_store.save) never corrupts the
            # user's saved model
            if res.source == "codex-oauth" and not s.model.startswith("gpt-5."):
                s.model = _codex_session_model()
            return {"v": 1, "id": s.id, "auth": res.source, "resumed": True}
        model = (
            body.model
            or os.environ.get("VOSS_SERVE_DEFAULT_MODEL")
            or get_config().default_model
        )
        # codex-oauth: snap a non-gpt-5.x model to Codex's default so the
        # backend doesn't 400 the turn into a bare idle (session-scoped; mirrors
        # cli.py:686-687 without the global configure mutation)
        if res.source == "codex-oauth" and not model.startswith("gpt-5."):
            model = _codex_session_model()
        s = mgr.create(cwd=cwd, model=model, provider=provider, title=body.title or "")
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
                }
                for r in records
            ],
        }

    @app.get("/session/{session_id}")
    def get_session(session_id: str) -> dict:
        s = _require(session_id)
        return {"v": 1, "id": s.id, "cwd": str(s.cwd), "model": s.model, "title": s.title, "busy": s.busy}

    @app.delete("/session/{session_id}", status_code=204)
    def delete_session(session_id: str) -> None:
        if not mgr.delete(session_id):
            raise HTTPException(404, "session not found")

    @app.post("/session/{session_id}/message", status_code=202)
    async def post_message(session_id: str, body: MessageBody) -> dict:
        s = _require(session_id)
        if s.busy:
            raise HTTPException(409, "a turn is already running")
        text = " ".join(p.text for p in body.parts if p.type == "text").strip()
        if not text:
            raise HTTPException(422, "empty message")
        s.task = asyncio.create_task(_run_turn(s, text, body.mode))
        return {"v": 1, "status": "accepted"}

    @app.post("/session/{session_id}/abort", status_code=202)
    async def abort(session_id: str) -> dict:
        s = _require(session_id)
        if s.busy and s.task is not None:
            s.task.cancel()
        return {"v": 1, "status": "aborting"}

    @app.get("/session/{session_id}/cost")
    def cost(session_id: str) -> dict:
        s = _require(session_id)
        runs = s.record.runs
        total = sum(float(r.get("cost_usd", 0.0) or 0.0) for r in runs)
        return {"v": 1, "total_usd": total, "turns": len(runs)}

    @app.post("/session/{session_id}/permission")
    def reply_permission(session_id: str, body: PermissionReply) -> dict:
        s = _require(session_id)
        fut = s.pending.get(body.id)
        if fut is not None and not fut.done():
            fut.set_result(body.choice)
            return {"v": 1, "status": "ok"}
        return {"v": 1, "status": "stale"}


    @app.get(
        "/session/{session_id}/events",
        responses={
            200: {
                "content": {
                    "text/event-stream": {
                        "schema": {"$ref": "#/components/schemas/EventEnvelope"}
                    }
                }
            }
        },
    )
    async def events(session_id: str, request: Request) -> EventSourceResponse:
        s = _require(session_id)

        async def gen():
            yield ServerSentEvent(
                event="server.connected", data=E.ServerConnected().model_dump_json()
            )
            try:
                while True:
                    ev = await s.queue.get()
                    yield ServerSentEvent(event=ev.type, data=ev.model_dump_json())
            except asyncio.CancelledError:
                # client disconnected -> abort the in-flight turn
                if s.busy and s.task is not None:
                    s.task.cancel()
                raise

        return EventSourceResponse(gen(), ping=15, send_timeout=30)

    # doctor (; expanded full registry via diagnostics.to_dict
    # read-only by design: repairs are CLI-local `voss doctor --fix` only)

    @app.get("/doctor")
    def doctor(auth: str = "auto", cwd: str = ".") -> dict:
        from .. import diagnostics as diag

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
        from ..memory_store import MemoryStore

        store = MemoryStore(Path(cwd).resolve())
        out: dict = {"v": 1, "summary": store.summary(), "query": q, "hits": []}
        if q:
            hits = store.recall(q, top_k=max(1, min(top_k, 50)))
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

    def _emit_swarm_event(swarm_id: str, ev: E._Base) -> None:
        """Fan a swarm event out to EVERY registered session's queue (Pitfall
        3 — not just the coordinator). Validates the swarm exists first so a
        forged swarm_id cannot inject into unrelated queues (T-V25-04-04)."""
        store = app.state.swarm_store
        if store.get(swarm_id) is None:
            return
        for rec in store.list_agents_by_swarm(swarm_id):
            sess = mgr.get(rec["session_id"])
            if sess is not None:
                EventBusRenderer(sess.queue, session_id=sess.id).emit(ev)

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
        swarm = store.create(
            goal=body.goal, cwd=str(cwd), builders=body.builders, roster=explicit
        )
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
            store.mark_assigned(swarm_id, body.task_id, session_id=body.session_id)
            builder = mgr.get(body.session_id)
            if builder is not None:
                builder.swarm_task_id = body.task_id
                builder.swarm_owned_files = task.owned_files
                # VSWARM-05: attach the per-task ownership-deny policy now that
                # owned_files are known. _run_turn injects it into the gate
                builder.swarm_policy = build_ownership_policy(task.owned_files)
                # In-process unblock ( independent of queue state)
                if builder.gate_event is not None:
                    builder.gate_event.set()
            _emit_swarm_event(
                swarm_id,
                E.SwarmAssign(
                    swarm_id=swarm_id,
                    task_id=body.task_id,
                    session_id=body.session_id,
                    owned_files=task.owned_files,
                    role=(builder.swarm_role if builder else None) or "builder",
                ),
            )
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
            if etype == "swarm.needs_operator":
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
                )
            elif etype == "swarm.candidates_ready":
                _emit_swarm_event(
                    swarm_id,
                    E.SwarmCandidatesReady(
                        swarm_id=swarm_id,
                        candidate_count=ev.get("candidate_count", 0),
                    ),
                )
            elif etype == "swarm.complete":
                _emit_swarm_event(
                    swarm_id,
                    E.SwarmComplete(
                        swarm_id=swarm_id,
                        task_count=ev.get("task_count", 0),
                        summary=ev.get("summary"),
                    ),
                )

        return emit

    @app.post("/swarm/{swarm_id}/run", status_code=202)
    async def run_swarm(swarm_id: str) -> dict:
        """Drive the R3 CLI members of a swarm (worktree spawn + ownership +
        candidate preservation) headlessly. Native roles are untouched — they run via the
        in-process turn path. Fire-and-forget: the orchestrator streams progress
        over the swarm SSE plane; the route returns immediately."""
        store = app.state.swarm_store
        swarm = store.get(swarm_id)
        if swarm is None:
            raise HTTPException(404, "swarm not found")

        from ..swarm_runtime import run_cli_swarm, subprocess_spawn

        repo_root = Path(swarm.cwd)
        on_event = _r3_event_adapter(swarm_id)

        async def _drive() -> None:
            try:
                await run_cli_swarm(
                    store,
                    repo_root,
                    swarm_id,
                    spawn_fn=subprocess_spawn,
                    on_event=on_event,
                )
            except Exception:  # noqa: BLE001 — background driver must not crash the loop
                pass

        asyncio.create_task(_drive())
        return {"v": 1, "status": "running"}

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
        app.openapi_schema = schema
        return schema

    app.openapi = openapi  # type: ignore[assignment]
