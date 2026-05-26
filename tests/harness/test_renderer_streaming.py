"""T1-05 Task 2b: stream_delta + finalize_stream on every Renderer impl.

Renderer Protocol gains two methods; every concrete impl (TtyRenderer,
PlainRenderer, JsonRenderer, TextualRenderer) implements them following
that class's existing output-channel convention.

Also pins telemetry.note_turn(**kwargs) passthrough for the new
iteration_count + exit_reason keys (no telemetry.py source change).
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from rich.console import Console

from voss.harness import telemetry
from voss.harness.render import (
    CompactRenderer,
    JsonRenderer,
    PlainRenderer,
    Renderer,
    TtyRenderer,
    make_renderer,
)


@pytest.fixture(autouse=True)
def _reset_turn():
    telemetry.begin_turn()
    yield
    telemetry.clear_turn()


class TestTtyRenderer:
    def test_banner_is_low_chrome_ignite_header(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("NO_COLOR", raising=False)
        buf = io.StringIO()
        tty = TtyRenderer(
            console=Console(
                file=buf,
                width=80,
                force_terminal=True,
                color_system="truecolor",
            )
        )
        tty.banner(model="model", cwd=Path.cwd(), git_status="clean")
        out = buf.getvalue()
        assert "voss" in out
        assert "model" in out
        assert "voss · agent" not in out
        assert "╭" not in out
        assert "╰" not in out
        assert "38;2;255;91;31" in out

    def test_stream_delta_writes_to_console(self) -> None:
        buf = io.StringIO()
        tty = TtyRenderer(console=Console(file=buf, width=80, force_terminal=False))
        tty.stream_delta("hello ")
        tty.stream_delta("world")
        out = buf.getvalue()
        assert "hello " in out
        assert "world" in out

    def test_finalize_stream_writes_metadata_line(self) -> None:
        buf = io.StringIO()
        tty = TtyRenderer(console=Console(file=buf, width=80, force_terminal=False))
        tty.stream_delta("body")
        tty.finalize_stream(role="assistant", confidence=0.92, cost_usd=0.012)
        out = buf.getvalue()
        assert "assistant" in out
        assert "conf 0.92" in out
        assert "$0.0120" in out

    def test_finalize_stream_safe_without_prior_delta(self) -> None:
        buf = io.StringIO()
        tty = TtyRenderer(console=Console(file=buf, width=80, force_terminal=False))
        # No prior stream_delta — must not raise.
        tty.finalize_stream(role="assistant")
        assert "assistant" in buf.getvalue()


class TestPlainRenderer:
    def test_stream_delta_writes_stdout_no_newline(self, capsys) -> None:
        p = PlainRenderer()
        p.stream_delta("hel")
        p.stream_delta("lo")
        cap = capsys.readouterr()
        assert cap.out == "hello"

    def test_finalize_stream_writes_newline_then_stderr_meta(self, capsys) -> None:
        p = PlainRenderer()
        p.stream_delta("body")
        p.finalize_stream(role="assistant", confidence=0.92, cost_usd=0.012)
        cap = capsys.readouterr()
        # stdout: body + trailing newline only.
        assert cap.out == "body\n"
        # stderr: one-line meta footer.
        assert "assistant" in cap.err
        assert "conf 0.92" in cap.err


class TestJsonRenderer:
    def test_stream_delta_emits_event(self, capsys) -> None:
        j = JsonRenderer()
        j.stream_delta("hello")
        cap = capsys.readouterr()
        line = cap.out.strip().splitlines()[-1]
        ev = json.loads(line)
        assert ev["type"] == "stream.delta"
        assert ev["text"] == "hello"
        assert ev["v"] == 1

    def test_finalize_stream_emits_event(self, capsys) -> None:
        j = JsonRenderer()
        j.finalize_stream(
            role="assistant",
            confidence=0.92,
            cost_usd=0.012,
            timestamp="2026-05-15T12:00:00+00:00",
        )
        cap = capsys.readouterr()
        line = cap.out.strip().splitlines()[-1]
        ev = json.loads(line)
        assert ev["type"] == "stream.finalize"
        assert ev["role"] == "assistant"
        assert ev["confidence"] == pytest.approx(0.92)
        assert ev["cost_usd"] == pytest.approx(0.012)
        assert ev["timestamp"] == "2026-05-15T12:00:00+00:00"


class TestCompactRenderer:
    def test_banner_is_low_chrome_without_panel_border(self) -> None:
        buf = io.StringIO()
        compact = CompactRenderer(
            console=Console(file=buf, width=80, force_terminal=False)
        )
        compact.banner(model="model", cwd=Path.cwd(), git_status="clean")
        out = buf.getvalue()
        assert "voss" in out
        assert "model" in out
        assert "╭" not in out
        assert "╰" not in out

    def test_stream_delta_and_finalize_stream(self) -> None:
        buf = io.StringIO()
        compact = CompactRenderer(
            console=Console(file=buf, width=80, force_terminal=False)
        )
        compact.stream_delta("hello ")
        compact.stream_delta("world")
        compact.finalize_stream(role="assistant", confidence=0.92, cost_usd=0.012)
        out = buf.getvalue()
        assert "hello world" in out
        assert "assistant" in out
        assert "conf 0.92" in out

    def test_make_renderer_compact_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VOSS_RENDERER", "compact")
        renderer = make_renderer(json_mode=False, plain=False, force_tui=False)
        assert isinstance(renderer, CompactRenderer)

    def test_make_renderer_embedded_env_does_not_force_compact(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VOSS_EMBEDDED", "1")
        monkeypatch.setattr("sys.stdout.isatty", lambda: False)
        renderer = make_renderer(json_mode=False, plain=False, force_tui=False)
        assert isinstance(renderer, PlainRenderer)

    def test_make_renderer_plain_wins_over_compact(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VOSS_RENDERER", "compact")
        renderer = make_renderer(json_mode=False, plain=True, force_tui=False)
        assert isinstance(renderer, PlainRenderer)

    def test_force_tui_env_wins_over_compact(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """VOSS_FORCE_TUI=1 overrides VOSS_RENDERER=compact (embedded pane fix)."""
        monkeypatch.setenv("VOSS_RENDERER", "compact")
        monkeypatch.setenv("VOSS_FORCE_TUI", "1")
        from voss.harness.tui.renderer import TextualRenderer

        renderer = make_renderer(json_mode=False, plain=False, force_tui=False)
        assert isinstance(renderer, TextualRenderer)


class TestTextualRendererDelegates:
    def test_stream_delta_forwards_to_turn_view(self, monkeypatch) -> None:
        from voss.harness.tui.renderer import TextualRenderer

        recorded: list[tuple[str, tuple, dict]] = []

        class RecordingRenderer(TextualRenderer):
            def __init__(self) -> None:  # bypass app dependency
                pass

            def _safe(self, widget_fn, attr, *args, **kwargs):
                recorded.append((attr, args, kwargs))

        r = RecordingRenderer()
        r.stream_delta("hello")
        r.finalize_stream(
            role="assistant",
            confidence=0.92,
            cost_usd=0.012,
            timestamp="2026-05-15T00:00:00+00:00",
        )

        assert recorded[0][0] == "stream_delta"
        assert recorded[0][1] == ("hello",)

        assert recorded[1][0] == "finalize_stream"
        assert recorded[1][2] == {
            "role": "assistant",
            "confidence": 0.92,
            "cost_usd": 0.012,
            "timestamp": "2026-05-15T00:00:00+00:00",
            "accumulated_text": None,
        }


class TestProtocolMembership:
    def test_concrete_impls_satisfy_protocol(self) -> None:
        # Renderer is runtime_checkable. All three concrete impls (TextualRenderer
        # tested separately above) must now satisfy isinstance check after the
        # new method addition.
        assert isinstance(TtyRenderer(console=Console(file=io.StringIO())), Renderer)
        assert isinstance(CompactRenderer(console=Console(file=io.StringIO())), Renderer)
        assert isinstance(PlainRenderer(), Renderer)
        assert isinstance(JsonRenderer(), Renderer)


class TestNoteTurnPassthrough:
    def test_note_turn_accepts_iteration_count_and_exit_reason(self) -> None:
        telemetry.note_turn(
            iteration_count=3,
            exit_reason="done",
            cost_usd=0.1,
            outcome="complete",
        )
        meta = telemetry._turn_meta.get() or {}
        assert meta.get("iteration_count") == 3
        assert meta.get("exit_reason") == "done"
        assert meta.get("cost_usd") == pytest.approx(0.1)
        assert meta.get("outcome") == "complete"
