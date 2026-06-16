"""VADE2-11: GET /memory read-only route on the loopback server.

Covers the summary (no query), recall (with query → hits), and bearer-auth
enforcement. MemoryStore runs for real against a tmp cwd.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from voss.harness.server import app as appmod
from voss.harness.memory_store import MemoryStore

TOKEN = "memory-route-test-token"


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def _client() -> TestClient:
    return TestClient(appmod.create_app(TOKEN))


def test_memory_summary_without_query(tmp_path) -> None:
    c = _client()
    r = c.get("/memory", params={"cwd": str(tmp_path)}, headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["v"] == 1
    assert isinstance(body["summary"], str)
    assert body["query"] is None
    assert body["hits"] == []


def test_memory_recall_returns_hits(tmp_path) -> None:
    store = MemoryStore(tmp_path)
    store.write_note(
        "The deployment pipeline uses a blue-green rollout strategy.",
        session_id="sess-1",
    )

    c = _client()
    r = c.get(
        "/memory",
        params={"cwd": str(tmp_path), "q": "deployment rollout strategy", "top_k": 5},
        headers=_auth(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "deployment rollout strategy"
    assert len(body["hits"]) >= 1
    hit = body["hits"][0]
    for key in ("source", "locator", "score", "excerpt"):
        assert key in hit


def test_memory_requires_bearer_auth(tmp_path) -> None:
    c = _client()
    r = c.get("/memory", params={"cwd": str(tmp_path)})
    assert r.status_code == 401
