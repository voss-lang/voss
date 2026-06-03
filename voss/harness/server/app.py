"""FastAPI app: the harness REST+SSE server (HYBRID-REFACTOR-PLAN H1.5-H1.14).

Wraps the existing `agent.run_turn` behind the protocol in `.planning/PROTOCOL.md`.
Auth, providers, tools, sessions, and permissions are reused from the harness —
this module only adds transport: routes, an event bus, and a permission bridge.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import uuid
from concurrent.futures import Future
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from sse_starlette import EventSourceResponse, ServerSentEvent
from starlette.responses import JSONResponse

from voss_runtime import EpisodicMemory, get_config  # noqa: F401  (get_config used lazily)

from .. import auth as auth_mod
from .. import session as session_store
from ..agent import run_turn
from ..permissions import PermissionGate, PermissionStore
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


# ---------------------------------------------------------------------------
# auth -> provider (mirrors cli._resolve_auth_or_die, minus TTY wizard/sys.exit)
# ---------------------------------------------------------------------------


def _resolve_provider(preference: str) -> tuple[auth_mod.Resolution, Any]:
    """Resolve credentials to a (Resolution, provider). Never exits the process.

    Server analogue of `cli._resolve_auth_or_die`: same provider-selection
    switch, but a missing credential is a caller error (raised by the route),
    not a login wizard / `sys.exit`.
    """
    # Test seam: a hermetic fake turn needs a session without real creds.
    if os.environ.get("VOSS_SERVE_FAKE_TURN"):
        return _FakeResolution(), object()

    from voss_runtime.providers import LiteLLMProvider

    from ..providers import AnthropicOAuthProvider, OpenAIOAuthProvider

    res = auth_mod.resolve(preference)
    if res.source == "none":
        return res, None
    if res.source == "claude-oauth":
        provider: Any = AnthropicOAuthProvider(res.anthropic_oauth)
    elif res.source == "codex-oauth":
        provider = OpenAIOAuthProvider(res.codex_oauth)
    else:
        # env/voss anthropic|openai|codex all go through LiteLLM (key already
        # injected into os.environ by auth.resolve).
        provider = LiteLLMProvider()
    return res, provider


# ---------------------------------------------------------------------------
# permission bridge (H1.9) — mirrors tui/permissions_bridge over the protocol
# ---------------------------------------------------------------------------


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
        # Scope-expand uses the same channel; map y/n at the client.
        return _ask("scope_expand", {"target": target}, "tool")

    gate.prompt_fn = prompt
    gate.scope_prompt_fn = scope_prompt


# ---------------------------------------------------------------------------
# turn runner
# ---------------------------------------------------------------------------


async def _run_turn(session: ServerSession, text: str, mode: str) -> None:
    """Drive one turn; publish events; persist. Runs as session.task."""
    loop = asyncio.get_running_loop()
    renderer = EventBusRenderer(session.queue, session_id=session.id, loop=loop)

    # Test seam: emit a canned turn over the real event/SSE path (no provider).
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
        )
        _install_server_permissions(gate, session, renderer)

        try:
            from .. import voss_md

            voss_md_text = voss_md.read_and_inject(session.cwd)
        except Exception:
            voss_md_text = None

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
        )
        renderer.show_final(
            result.final, confidence=result.confidence, cost_usd=result.cost_usd
        )
        if result.run is not None:
            session.record.runs.append(asdict(result.run))
    except asyncio.CancelledError:
        raise
    finally:
        try:
            session_store.save(session.record, session.history)
        except Exception:
            pass
        renderer.session_idle()
        session.task = None


# ---------------------------------------------------------------------------
# request models
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# app factory
# ---------------------------------------------------------------------------


def create_app(token: str | None = None) -> FastAPI:
    token = token or secrets.token_urlsafe(32)
    mgr = SessionManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        # shutdown: cancel any in-flight turns
        for s in mgr.list():
            if s.busy and s.task is not None:
                s.task.cancel()

    app = FastAPI(title="voss-harness", version="1", lifespan=lifespan)
    app.state.token = token
    app.state.sessions = mgr

    app.add_middleware(_BearerASGI, token=token)

    def _require(session_id: str) -> ServerSession:
        s = mgr.get(session_id)
        if s is None:
            raise HTTPException(404, "session not found")
        return s

    # -- session CRUD (H1.6) ------------------------------------------------

    @app.post("/session", status_code=201)
    def create_session(body: CreateSessionBody) -> dict:
        cwd = Path(body.cwd or ".").resolve()
        res, provider = _resolve_provider(body.auth)
        if provider is None:
            raise HTTPException(400, f"no usable credentials ({res.detail})")
        if body.resume:
            try:
                record, history = session_store.load(body.resume, cwd)
            except FileNotFoundError:
                raise HTTPException(404, f"no saved session {body.resume!r}")
            except ValueError as exc:  # ambiguous id
                raise HTTPException(409, str(exc))
            # M2: forward ALL prior runs as prior context (consumed on turn 1).
            s = mgr.adopt(
                record=record,
                history=history,
                provider=provider,
                prior_context=record.runs or None,
            )
            return {"v": 1, "id": s.id, "auth": res.source, "resumed": True}
        model = body.model or get_config().default_model
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

    # -- message + abort + permission (H1.7, H1.10, H1.9) -------------------

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

    @app.post("/session/{session_id}/permission")
    def reply_permission(session_id: str, body: PermissionReply) -> dict:
        s = _require(session_id)
        fut = s.pending.get(body.id)
        if fut is not None and not fut.done():
            fut.set_result(body.choice)
            return {"v": 1, "status": "ok"}
        return {"v": 1, "status": "stale"}

    # -- SSE (H1.8) ---------------------------------------------------------

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

    # -- doctor (H1.7 stub; H3.1 expands) -----------------------------------

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
            "checks": [
                {
                    "name": c.name,
                    "status": c.result.name,
                    "detail": c.detail,
                    "fix": c.fix,
                }
                for c in checks
            ],
        }

    # -- OpenAPI: force the event union into components (H1.14) --------------

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
