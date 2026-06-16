"""Regression tests for codex-oauth model snapping + provider-error visibility.

FIX-1 target: ``voss/harness/server/app.py`` (this test imports it; it does not
modify it). Two defects, both surfaced by the swarm diagnosis:

1. **Model snap.** When auth resolves to ``codex-oauth`` the ChatGPT Codex
   backend only accepts ``gpt-5.x`` model ids. ``create_session`` currently sets
   the session model to ``body.model or VOSS_SERVE_DEFAULT_MODEL or
   get_config().default_model`` (``claude-sonnet-4-5``) without snapping it to a
   codex model, so the first ``provider.stream`` 400s. The CLI already does this
   snap (``cli.py:686-687``); the server must reach parity.

2. **Silent swallow.** ``_run_turn`` catches only ``asyncio.CancelledError``; a
   provider ``RuntimeError`` is orphaned on the asyncio task and the only event
   the client sees is ``session.idle`` (a bare empty turn). The turn must instead
   surface a visible event.

Empirical proof of the underlying bug (DIAG-B, server stderr captured in
``/tmp/voss_repro/s1_plan_default_serve.log``)::

    Task exception was never retrieved
    RuntimeError: OpenAI OAuth stream failed [400]: b'{"detail":"The
    \\'claude-sonnet-4-5\\' model is not supported when using Codex with a
    ChatGPT account."}'

These tests are RED on current code and GREEN after FIX-1. The guard tests
(valid gpt-5 kept; non-codex auth untouched) are GREEN both before and after and
exist so the fix cannot over-snap.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from voss.harness import auth as auth_mod
from voss.harness.server import app as appmod

TOKEN = "test-token-codex-snap"


class _Res:
    """Minimal ``auth.Resolution`` stand-in (the route reads only .source)."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.detail = f"fake {source}"


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Hermetic codex default — independent of any local ~/.codex/config.toml, so
    # the snap resolves deterministically to a gpt-5.x id in CI without creds.
    monkeypatch.setattr(
        auth_mod, "load_codex_default_model", lambda path=None: "gpt-5.5"
    )
    monkeypatch.setattr(appmod.session_store, "save", lambda record, history: None)
    monkeypatch.delenv("VOSS_SERVE_DEFAULT_MODEL", raising=False)
    app = appmod.create_app(TOKEN)
    c = TestClient(app)
    c._cwd = str(tmp_path)  # type: ignore[attr-defined]
    return c


def _use_provider(monkeypatch, source: str = "codex-oauth") -> None:
    """Force `_resolve_provider` to a given auth source + a stub provider."""
    monkeypatch.setattr(
        appmod, "_resolve_provider", lambda pref: (_Res(source), object())
    )


def _create(client, **body) -> str:
    body.setdefault("cwd", client._cwd)
    r = client.post("/session", json=body, headers=_auth())
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _model_of(client, sid: str) -> str:
    return client.get(f"/session/{sid}", headers=_auth()).json()["model"]


# --- (1) model snapping -----------------------------------------------------


def test_codex_oauth_snaps_explicit_non_gpt5_model(client, monkeypatch):
    """codex-oauth + an explicit claude model -> snapped to gpt-5.x.

    RED today: the session keeps ``claude-sonnet-4-5`` and the codex backend 400s.
    """
    _use_provider(monkeypatch)
    sid = _create(client, model="claude-sonnet-4-5")
    model = _model_of(client, sid)
    assert model.startswith("gpt-5."), (
        f"codex-oauth session kept non-codex model {model!r}; the ChatGPT Codex "
        "backend 400s on it (DIAG-B serve.log)"
    )


def test_codex_oauth_snaps_default_model(client, monkeypatch):
    """codex-oauth + no body.model -> the (non-gpt5) config default is snapped."""
    _use_provider(monkeypatch)
    sid = _create(client)  # body.model omitted -> get_config().default_model
    model = _model_of(client, sid)
    assert model.startswith("gpt-5."), (
        f"codex-oauth default-model session kept {model!r}; expected a gpt-5.x snap"
    )


def test_codex_oauth_keeps_valid_gpt5_model(client, monkeypatch):
    """Guard: an already-valid gpt-5.x model is left intact (no double-snap)."""
    _use_provider(monkeypatch)
    sid = _create(client, model="gpt-5.4")
    assert _model_of(client, sid) == "gpt-5.4"


def test_non_codex_auth_keeps_model(client, monkeypatch):
    """Guard: non-codex auth must NOT be snapped (don't break Anthropic/etc.)."""
    _use_provider(monkeypatch, source="claude-agent")
    sid = _create(client, model="claude-sonnet-4-5")
    assert _model_of(client, sid) == "claude-sonnet-4-5"


# --- (2) resume path --------------------------------------------------------


def test_codex_oauth_resume_snaps_runtime_model_without_mutating_disk(
    monkeypatch, tmp_path
):
    """RESUME: a saved codex session with a non-gpt5 model must RUN on gpt-5.x,
    while the persisted record.model stays unchanged (non-destructive).

    The snap in FIX-1 lives in the non-resume branch only; the resume branch
    calls ``mgr.adopt(model=record.model)`` and returns before it. This test
    drives whether the snap also covers the resume/adopt path. (Uses a real
    on-disk save under tmp_path — hermetic; the resume create() reads but never
    writes the record.)
    """
    from voss_runtime import EpisodicMemory

    from voss.harness import session as sstore

    monkeypatch.setattr(
        auth_mod, "load_codex_default_model", lambda path=None: "gpt-5.5"
    )
    _use_provider(monkeypatch)  # codex-oauth

    rec = sstore.SessionRecord.new(
        cwd=tmp_path, model="claude-sonnet-4-5", name="resume-me"
    )
    sstore.save(rec, EpisodicMemory())

    app = appmod.create_app(TOKEN)
    c = TestClient(app)
    r = c.post(
        "/session",
        json={"cwd": str(tmp_path), "resume": "resume-me"},
        headers=_auth(),
    )
    assert r.status_code == 201, r.text
    assert r.json()["resumed"] is True
    sid = r.json()["id"]

    runtime_model = c.get(f"/session/{sid}", headers=_auth()).json()["model"]
    assert runtime_model.startswith("gpt-5."), (
        f"resumed codex-oauth session runs non-codex model {runtime_model!r}; "
        "the snap must also cover the resume/adopt path"
    )

    # Non-destructive: the persisted record keeps its original model.
    rec2, _ = sstore.load("resume-me", tmp_path)
    assert rec2.model == "claude-sonnet-4-5", (
        f"resume mutated the on-disk record.model to {rec2.model!r}"
    )


# --- (3) provider-error visibility ------------------------------------------


async def test_run_turn_surfaces_provider_error(monkeypatch, tmp_path):
    """A provider failure must surface a VISIBLE event, not a bare session.idle.

    Mirrors the real codex 400: ``provider.stream`` raises -> ``run_turn`` raises
    -> ``app._run_turn`` is the swallow site (it catches only CancelledError, and
    ``_run_turn_exec`` likewise does not catch generic exceptions). We drive
    ``_run_turn`` directly (the established pattern in
    ``tests/harness/test_server_app.py``) and inject the failure at ``run_turn``,
    which is equivalent to ``provider.stream`` raising for this swallow path.

    RED today: only ``user`` + ``session.idle`` reach the queue.
    """
    monkeypatch.setattr(appmod.session_store, "save", lambda record, history: None)

    async def _boom(text, *, renderer, **kw):
        renderer.show_thinking("planning 1/8")
        raise RuntimeError("OpenAI OAuth stream failed [400]: model not supported")

    monkeypatch.setattr(appmod, "run_turn", _boom)

    app = appmod.create_app(TOKEN)
    mgr = app.state.sessions
    s = mgr.create(cwd=tmp_path, model="gpt-5.5", provider=object())

    # Pre-fix `_run_turn` re-raises (only CancelledError is caught); post-fix it
    # catches, emits a visible event, and returns. Tolerate both so the real
    # assertion is the queue contents below.
    try:
        await appmod._run_turn(s, "hi", "plan")
    except RuntimeError:
        pass

    seen: list[str] = []
    while not s.queue.empty():
        seen.append(s.queue.get_nowait().type)

    assert "user" in seen
    assert seen[-1] == "session.idle"
    visible_error = [
        t for t in seen if t in ("error", "warning", "final", "stream.delta")
    ]
    assert visible_error, (
        f"provider failure produced no visible event (queue was {seen}); the user "
        "sees a bare idle with no indication of the error"
    )
    assert s.task is None
