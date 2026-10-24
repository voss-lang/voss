"""T1-06 Task 2: _run_turn_cancellable cli helper.

Wraps an agent-turn coroutine with cancel-on-Ctrl-C semantics: installs a
SIGINT handler and re-raises any CancelledError as click.Abort.
"""
from __future__ import annotations

import asyncio

import click
import pytest

from voss.harness.cli import _run_turn_cancellable
from voss.harness.render import PlainRenderer


def test_happy_path_returns_result() -> None:
    async def _coro() -> str:
        return "sentinel"

    out = _run_turn_cancellable(_coro(), renderer=PlainRenderer())
    assert out == "sentinel"


def test_cancelled_coroutine_raises_click_abort() -> None:
    async def _hang() -> None:
        loop = asyncio.get_event_loop()
        loop.call_later(0.01, asyncio.current_task().cancel)
        await asyncio.sleep(10)

    with pytest.raises(click.Abort):
        _run_turn_cancellable(_hang(), renderer=PlainRenderer())


def test_signal_handler_unsupported_does_not_raise(monkeypatch) -> None:
    """On platforms where add_signal_handler raises NotImplementedError
    (Windows), the helper falls back gracefully."""

    def boom(*a, **kw):
        raise NotImplementedError("simulated Windows")

    monkeypatch.setattr(
        asyncio.SelectorEventLoop, "add_signal_handler", boom, raising=False
    )

    async def _coro() -> str:
        return "ok"

    out = _run_turn_cancellable(_coro(), renderer=PlainRenderer())
    assert out == "ok"
