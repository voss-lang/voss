"""T1-06 Task 1: VossTUIApp.active_turn_task + register/clear + action_interrupt."""
from __future__ import annotations

import asyncio

import pytest

from voss.harness.tui.app import VossTUIApp


class TestRegisterAndClear:
    def test_active_turn_task_defaults_none(self) -> None:
        app = VossTUIApp()
        assert app.active_turn_task is None

    @pytest.mark.asyncio
    async def test_register_then_complete_clears_via_callback(self) -> None:
        app = VossTUIApp()

        async def _stub() -> str:
            return "done"

        task = asyncio.create_task(_stub())
        app.register_turn_task(task)
        assert app.active_turn_task is task
        result = await task
        assert result == "done"
        # done_callback runs before await returns? Give the loop a tick.
        await asyncio.sleep(0)
        assert app.active_turn_task is None

    @pytest.mark.asyncio
    async def test_double_register_raises(self) -> None:
        app = VossTUIApp()

        async def _hang() -> None:
            await asyncio.sleep(60)

        task = asyncio.create_task(_hang())
        try:
            app.register_turn_task(task)
            with pytest.raises(RuntimeError) as exc:
                app.register_turn_task(asyncio.create_task(_hang()))
            assert "already registered" in str(exc.value)
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task


class TestActionInterrupt:
    def test_no_op_when_no_task_registered(self) -> None:
        app = VossTUIApp()
        # Must not raise.
        app.action_interrupt()
        assert app.active_turn_task is None

    @pytest.mark.asyncio
    async def test_cancels_running_task(self) -> None:
        app = VossTUIApp()

        async def _hang() -> None:
            await asyncio.sleep(60)

        task = asyncio.create_task(_hang())
        app.register_turn_task(task)

        app.action_interrupt()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_no_op_on_already_done_task(self) -> None:
        app = VossTUIApp()

        async def _quick() -> str:
            return "ok"

        task = asyncio.create_task(_quick())
        app.register_turn_task(task)
        await task
        await asyncio.sleep(0)  # let done_callback run
        # active_turn_task is now None — interrupt is a no-op.
        app.action_interrupt()
        assert task.done()
        assert not task.cancelled()


class TestPriorTaskCanBeReplaced:
    @pytest.mark.asyncio
    async def test_register_after_prior_task_done(self) -> None:
        app = VossTUIApp()

        async def _q() -> int:
            return 1

        t1 = asyncio.create_task(_q())
        app.register_turn_task(t1)
        await t1
        await asyncio.sleep(0)

        async def _q2() -> int:
            return 2

        t2 = asyncio.create_task(_q2())
        # Should NOT raise — t1 is done.
        app.register_turn_task(t2)
        assert app.active_turn_task is t2
        await t2
        await asyncio.sleep(0)
        assert app.active_turn_task is None
