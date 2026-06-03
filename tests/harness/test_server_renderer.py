"""H1.2 + H1.3 verification.

- EventBusRenderer satisfies the render.Renderer protocol.
- Each of the 13 Renderer methods enqueues the matching protocol event.
- finalize_stream drops accumulated_text (JsonRenderer parity).
- Full bounded queue drops the oldest event (lossy-latest).
- The AgentEvent discriminated union round-trips every member by `type`.
- EventEnvelope exposes the union to OpenAPI codegen.
"""

from __future__ import annotations

import asyncio

from voss.harness.agent import Plan, ToolCall
from voss.harness.render import Renderer
from voss.harness.server import events as E
from voss.harness.server.renderer import EventBusRenderer


def test_satisfies_renderer_protocol() -> None:
    r = EventBusRenderer(asyncio.Queue(), session_id="s1")
    assert isinstance(r, Renderer)


def test_each_method_enqueues_expected_event() -> None:
    q: asyncio.Queue = asyncio.Queue()
    r = EventBusRenderer(q, session_id="s1")

    r.banner(model="m", cwd="/tmp", git_status="clean")
    r.show_user("hi")
    r.show_thinking("planning 1/8")
    r.show_plan(
        Plan(
            rationale="x",
            steps=[ToolCall(name="fs_read", args={"path": "a"})],
            confidence=0.9,
        ),
        cost_usd=0.01,
    )
    r.show_tool_call("fs_read", {"path": "a"}, "read a", "ok")
    r.show_clarify("which?", 0.4)
    r.show_final("done", confidence=0.9, cost_usd=0.02)
    r.stream_delta("tok")
    r.finalize_stream(
        role="assistant",
        confidence=0.9,
        cost_usd=0.02,
        timestamp="t",
        accumulated_text="ignored",
    )
    r.status(model="m", tokens=10, cost_usd=0.02, ctx_pct=0.1)
    r.show_cognition(architecture_tokens=100, constraints_count=2)
    r.show_cognition_overflow(architecture_tokens=7000)
    r.show_warning("careful")

    got = []
    while not q.empty():
        got.append(q.get_nowait())

    # H5.2: show_clarify emits BOTH clarify and a gate.updated event.
    assert [e.type for e in got] == [
        "banner",
        "user",
        "thinking",
        "plan",
        "tool",
        "clarify",
        "gate.updated",
        "final",
        "stream.delta",
        "stream.finalize",
        "status",
        "cognition_loaded",
        "cognition_overflow",
        "warning",
    ]

    by_type = {e.type: e for e in got}
    assert by_type["plan"].confidence == 0.9
    assert by_type["plan"].steps[0].name == "fs_read"
    assert by_type["plan"].steps[0].args == {"path": "a"}
    assert by_type["tool"].state == "ok"
    assert by_type["stream.delta"].text == "tok"
    # accumulated_text intentionally dropped on the wire
    assert not hasattr(by_type["stream.finalize"], "accumulated_text")
    assert by_type["stream.finalize"].role == "assistant"
    assert by_type["gate.updated"].gate == "confidence"


def test_drop_oldest_on_full_queue() -> None:
    q: asyncio.Queue = asyncio.Queue(maxsize=2)
    r = EventBusRenderer(q)
    r.stream_delta("a")
    r.stream_delta("b")
    r.stream_delta("c")  # forces drop of oldest ("a")
    assert q.qsize() == 2
    assert q.get_nowait().text == "b"
    assert q.get_nowait().text == "c"


def test_server_only_helpers() -> None:
    q: asyncio.Queue = asyncio.Queue()
    r = EventBusRenderer(q, session_id="sid42")
    r.server_connected()
    r.session_idle()
    r.emit(E.PermissionUpdated(id="p1", tool_name="fs_write", args={"path": "x"}))
    types = [q.get_nowait().type for _ in range(3)]
    assert types == ["server.connected", "session.idle", "permission.updated"]


def test_discriminated_union_roundtrip() -> None:
    samples: list[E._Base] = [
        E.ServerConnected(),
        E.StreamDelta(text="x"),
        E.SessionIdle(session_id="s"),
        E.ToolEvent(name="fs_read", args={}, summary="", state="pending"),
        E.ProbableEvent(
            text="maybe",
            probability=0.7,
            alternatives=[E.Alternative(text="no", probability=0.3)],
        ),
        E.BudgetUpdated(session_id="s", spent=1.0, limit=10.0, remaining=9.0),
        E.ConfidenceUpdated(session_id="s", score=0.8),
        E.GateUpdated(session_id="s", gate="budget", decision="ask"),
    ]
    for ev in samples:
        wire = ev.model_dump_json()
        back = E.AgentEventAdapter.validate_json(wire)
        assert back.type == ev.type
        assert back == ev


def test_envelope_schema_emits() -> None:
    schema = E.EventEnvelope.model_json_schema()
    assert "event" in schema["properties"]
    # discriminated union surfaces a discriminator mapping for codegen
    assert "$defs" in schema
