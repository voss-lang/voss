"""S3.5: /observe routes — ingest with admission, cursor pagination, settings,
SSE stream with seq cursor, bearer auth.

Covers AC-S3-3 (duplicate POST → one row, record_only:duplicate), AC-S3-8
(unenrolled → 403, nothing stored), and AC-S3-10 (SSE seq order; reconnect
with last seq → no gaps/dupes over 1,000 events). The store and enrollment
run for real against the isolated XDG_STATE_HOME sandbox.
"""

from __future__ import annotations

import asyncio
import json
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from voss.harness.server import app as appmod
from voss.harness.observe.enrollment import RepoEnrollment, set_repo_enrollment
from voss.harness.observe.models import ObserveEventAdapter
from voss.harness.observe.store import ObserveStore, db_path

TOKEN = "observe-routes-test-token"
REPO = "repo-1"


def _auth() -> dict:
    return {"Authorization": f"Bearer {TOKEN}"}


def _client() -> TestClient:
    return TestClient(appmod.create_app(TOKEN))


def _enroll(**overrides) -> None:
    set_repo_enrollment(REPO, RepoEnrollment(enabled=True, **overrides))


def _event(event_id: str, event_type: str, payload: dict) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "command_id": f"cmd-{event_id}",
        "repository_id": REPO,
        "worktree_id": "wt-1",
        "adapter_id": "voss-pty",
        "repository_state_id": "head:abc:def",
        "source_ref": {"source": "adapter", "ref": "pane-1"},
        "payload": payload,
    }


def _started(event_id: str) -> dict:
    return _event(
        event_id,
        "command.started",
        {"argv": ["ls"], "argv_text": "ls", "cwd": "/repo"},
    )


def _completed(event_id: str, argv: list[str] | None = None, exit_code: int = 0) -> dict:
    argv = argv or ["make", "build"]
    return _event(
        event_id,
        "command.completed",
        {
            "argv": argv,
            "argv_text": " ".join(argv),
            "cwd": "/repo",
            "exit_code": exit_code,
            "duration_ms": 42,
        },
    )


def test_auth_required_on_all_observe_routes() -> None:
    c = _client()
    assert c.post("/observe/events", json={"event": _started("ev-a")}).status_code == 401
    assert c.get("/observe/events", params={"repository_id": REPO}).status_code == 401
    assert c.get("/observe/settings").status_code == 401
    assert (
        c.patch(
            "/observe/settings",
            json={"repository_id": REPO, "enrollment": {"enabled": True}},
        ).status_code
        == 401
    )
    assert c.get("/observe/stream", params={"repository_id": REPO}).status_code == 401


def test_ac_s3_8_unenrolled_repository_rejected_and_nothing_stored() -> None:
    c = _client()
    r = c.post("/observe/events", json={"event": _started("ev-1")}, headers=_auth())
    assert r.status_code == 403
    body = r.json()
    assert body["decision"] == "reject"
    assert body["reason"] == "not_enrolled"
    assert not db_path(REPO).exists()


def test_paused_enrollment_rejects_without_storing() -> None:
    _enroll(paused=True)
    c = _client()
    r = c.post("/observe/events", json={"event": _started("ev-1")}, headers=_auth())
    assert r.status_code == 403
    assert r.json()["reason"] == "paused"
    assert not db_path(REPO).exists()


def test_capture_disabled_rejects_without_storing() -> None:
    _enroll(capture=False)
    c = _client()
    r = c.post("/observe/events", json={"event": _started("ev-1")}, headers=_auth())
    assert r.status_code == 403
    assert r.json()["reason"] == "capture_disabled"
    assert not db_path(REPO).exists()


def test_invalid_event_is_422() -> None:
    _enroll()
    c = _client()
    r = c.post(
        "/observe/events",
        json={"event": {"event_type": "command.started"}},
        headers=_auth(),
    )
    assert r.status_code == 422
    assert not db_path(REPO).exists()


def test_ac_s3_3_duplicate_post_stores_one_row_and_reports_duplicate() -> None:
    _enroll()
    c = _client()
    event = _completed("ev-dup")
    r1 = c.post("/observe/events", json={"event": event}, headers=_auth())
    assert r1.status_code == 200
    assert r1.json()["decision"] == "record_only"
    assert r1.json()["reason"] == "observed"
    r2 = c.post("/observe/events", json={"event": event}, headers=_auth())
    assert r2.status_code == 200
    assert r2.json()["decision"] == "record_only"
    assert r2.json()["reason"] == "duplicate"
    with ObserveStore(REPO) as store:
        assert len(store.list_events(limit=100)) == 1
        decisions = [a["reason"] for a in store.admissions()]
    assert decisions == ["observed", "duplicate"]


def test_failing_test_command_queues_one_investigation() -> None:
    _enroll()
    c = _client()
    r = c.post(
        "/observe/events",
        json={
            "event": _completed("ev-fail", argv=["pytest"], exit_code=1),
            "evidence": [
                {"kind": "command_output", "content": "FAILED tests/test_x.py"}
            ],
        },
        headers=_auth(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "queue"
    assert body["investigation_id"]
    assert body["derived_event_id"]
    with ObserveStore(REPO) as store:
        events = store.list_events(limit=100)
        assert [e["event"]["event_type"] for e in events] == [
            "command.completed",
            "test.failed",
        ]
        derived = events[1]["event"]
        assert derived["event_id"] == body["derived_event_id"]
        assert derived["caused_by"] == "ev-fail"
        assert derived["payload"]["runner"] == "pytest"


def test_repeat_failure_within_cooldown_is_suppressed() -> None:
    _enroll()
    c = _client()
    evidence = [{"kind": "command_output", "content": "FAILED tests/test_x.py"}]
    r1 = c.post(
        "/observe/events",
        json={"event": _completed("ev-f1", argv=["pytest"], exit_code=1), "evidence": evidence},
        headers=_auth(),
    )
    assert r1.json()["decision"] == "queue"
    r2 = c.post(
        "/observe/events",
        json={"event": _completed("ev-f2", argv=["pytest"], exit_code=1), "evidence": evidence},
        headers=_auth(),
    )
    assert r2.json()["decision"] == "suppress"
    assert r2.json()["reason"] == "cooldown"


def test_evidence_redacted_before_write_and_linked() -> None:
    _enroll()
    c = _client()
    r = c.post(
        "/observe/events",
        json={
            "event": _completed("ev-redact"),
            "evidence": [
                {
                    "kind": "command_output",
                    "content": "boom AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE detected",
                }
            ],
        },
        headers=_auth(),
    )
    assert r.status_code == 200
    with ObserveStore(REPO) as store:
        ev = store.get_evidence("ev-redact-ev0")
        assert ev is not None
        assert b"AKIAIOSFODNN7EXAMPLE" not in ev["content"]
        assert b"AWS_SECRET_ACCESS_KEY=<redacted>" in ev["content"]
        stored = store.get_event("ev-redact")
        assert stored["event"]["evidence_refs"] == ["ev-redact-ev0"]


def test_events_cursor_pagination() -> None:
    _enroll()
    c = _client()
    for i in range(1, 8):
        r = c.post(
            "/observe/events", json={"event": _started(f"ev-{i}")}, headers=_auth()
        )
        assert r.status_code == 200

    page1 = c.get(
        "/observe/events",
        params={"repository_id": REPO, "limit": 3},
        headers=_auth(),
    ).json()
    assert [e["seq"] for e in page1["events"]] == [1, 2, 3]
    assert page1["next_cursor"] == 3

    page2 = c.get(
        "/observe/events",
        params={"repository_id": REPO, "cursor": page1["next_cursor"], "limit": 3},
        headers=_auth(),
    ).json()
    assert [e["seq"] for e in page2["events"]] == [4, 5, 6]

    page3 = c.get(
        "/observe/events",
        params={"repository_id": REPO, "cursor": page2["next_cursor"], "limit": 3},
        headers=_auth(),
    ).json()
    assert [e["seq"] for e in page3["events"]] == [7]
    assert page3["next_cursor"] == 7

    page4 = c.get(
        "/observe/events",
        params={"repository_id": REPO, "cursor": page3["next_cursor"], "limit": 3},
        headers=_auth(),
    ).json()
    assert page4["events"] == []
    assert page4["next_cursor"] == 7


def test_events_for_unknown_repository_is_empty_without_creating_db() -> None:
    c = _client()
    r = c.get("/observe/events", params={"repository_id": "nope"}, headers=_auth())
    assert r.status_code == 200
    assert r.json() == {"v": 1, "events": [], "next_cursor": 0}
    assert not db_path("nope").exists()


def test_settings_get_and_patch_round_trip() -> None:
    c = _client()
    r = c.get("/observe/settings", headers=_auth())
    assert r.status_code == 200
    assert r.json()["repositories"] == {}

    r = c.patch(
        "/observe/settings",
        json={"repository_id": REPO, "enrollment": {"enabled": True, "analysis": True}},
        headers=_auth(),
    )
    assert r.status_code == 200
    assert r.json()["enrollment"]["enabled"] is True
    assert r.json()["enrollment"]["capture"] is True

    r = c.patch(
        "/observe/settings",
        json={"repository_id": REPO, "enrollment": {"paused": True}},
        headers=_auth(),
    )
    assert r.json()["enrollment"]["paused"] is True
    assert r.json()["enrollment"]["enabled"] is True

    r = c.get("/observe/settings", headers=_auth())
    repo = r.json()["repositories"][REPO]
    assert repo["enabled"] is True
    assert repo["analysis"] is True
    assert repo["paused"] is True


def test_stream_rejects_unenrolled_repository() -> None:
    c = _client()
    r = c.get("/observe/stream", params={"repository_id": REPO}, headers=_auth())
    assert r.status_code == 403
    assert r.json()["reason"] == "not_enrolled"


# TestClient cannot stream sse_starlette responses in this environment (it
# blocks before response headers even on a minimal app), so the stream tests
# drive the ASGI app directly — full middleware stack, real SSE bytes.


async def _stream_body(
    app, params: dict, count: int, extra_headers: list | None = None
) -> tuple[int, bytes]:
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/observe/stream",
        "raw_path": b"/observe/stream",
        "query_string": urlencode(params).encode(),
        "headers": [
            (b"authorization", f"Bearer {TOKEN}".encode()),
            *(extra_headers or []),
        ],
        "client": ("test", 50000),
        "server": ("test", 80),
        "root_path": "",
    }
    messages: list[dict] = []

    async def receive() -> dict:
        await asyncio.sleep(3600)
        return {"type": "http.request"}

    async def send(message: dict) -> None:
        messages.append(message)

    def _body() -> bytes:
        return b"".join(
            m.get("body", b"") for m in messages if m["type"] == "http.response.body"
        )

    task = asyncio.create_task(app(scope, receive, send))
    try:
        deadline = time.monotonic() + 15
        while not task.done() and time.monotonic() < deadline:
            if _body().count(b"event: observe.event") >= count:
                break
            await asyncio.sleep(0.01)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    status = next(
        m["status"] for m in messages if m["type"] == "http.response.start"
    )
    return status, _body()


def _sse_seqs(body: bytes) -> list[int]:
    seqs: list[int] = []
    for block in body.replace(b"\r\n", b"\n").split(b"\n\n"):
        event_type = ""
        data = None
        for line in block.split(b"\n"):
            if line.startswith(b"event:"):
                event_type = line.split(b":", 1)[1].strip().decode()
            elif line.startswith(b"data:"):
                data = line.split(b":", 1)[1].strip()
        if event_type == "observe.event" and data is not None:
            seqs.append(json.loads(data)["seq"])
    return seqs


async def test_ac_s3_10_stream_seq_order_and_reconnect_without_gaps_or_dupes() -> None:
    _enroll()
    with ObserveStore(REPO) as store:
        for i in range(1, 1001):
            store.insert_event(ObserveEventAdapter.validate_python(_started(f"ev-{i}")))

    app = appmod.create_app(TOKEN)
    status, body = await _stream_body(app, {"repository_id": REPO}, 600)
    assert status == 200
    assert body.startswith(b"event: server.connected")
    first = _sse_seqs(body)[:600]
    assert first == list(range(1, 601))

    status, body = await _stream_body(
        app, {"repository_id": REPO, "cursor": first[-1]}, 400
    )
    assert status == 200
    second = _sse_seqs(body)
    assert second == list(range(601, 1001))
    assert first + second == list(range(1, 1001))


async def test_stream_honors_last_event_id_header() -> None:
    _enroll()
    with ObserveStore(REPO) as store:
        for i in range(1, 11):
            store.insert_event(ObserveEventAdapter.validate_python(_started(f"ev-{i}")))

    app = appmod.create_app(TOKEN)
    status, body = await _stream_body(
        app, {"repository_id": REPO}, 3, extra_headers=[(b"last-event-id", b"7")]
    )
    assert status == 200
    assert _sse_seqs(body) == [8, 9, 10]
