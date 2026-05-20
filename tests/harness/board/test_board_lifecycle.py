"""O3-04 Task 2: Board.start/stop async lifecycle."""
from __future__ import annotations

import asyncio

import pytest

from voss.harness.board import Board
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.board.machine import _BoardConfig, _DEFAULT_WIP
from voss.harness.board.tick import FakeClock
from voss.harness.session_tree import SessionTreeManager, SessionTreeNode
from voss.harness.team import TeamCeiling


class TestBoardStartStop:
    @pytest.mark.asyncio
    async def test_start_spawns_task_stop_cancels(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub()
        cfg = _BoardConfig(
            wip=dict(_DEFAULT_WIP), p_overrides={}, retry_ceiling=3,
            card_deadline_s=1800.0, tick_interval_s=0.05, gates=(),
        )
        board = Board(
            manager=manager, reviewer=stub, cwd=cwd, cfg=cfg,
            team_ceiling=TeamCeiling(budget_tokens=1_000_000, scope=None, latency_seconds=None),
            root_node_id=manager._root.id, clock=fake_clock,
        )
        board.start()
        assert board._tick_task is not None
        assert not board._tick_task.done()

        await board.stop()
        assert board._tick_task is None

    @pytest.mark.asyncio
    async def test_stop_when_not_started_is_noop(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub()
        cfg = _BoardConfig(
            wip=dict(_DEFAULT_WIP), p_overrides={}, retry_ceiling=3,
            card_deadline_s=1800.0, tick_interval_s=0.05, gates=(),
        )
        board = Board(
            manager=manager, reviewer=stub, cwd=cwd, cfg=cfg,
            team_ceiling=TeamCeiling(budget_tokens=1_000_000, scope=None, latency_seconds=None),
            root_node_id=manager._root.id, clock=fake_clock,
        )
        await board.stop()  # no-op, no error

    @pytest.mark.asyncio
    async def test_start_idempotent(self, tmp_recorder, fake_clock):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub()
        cfg = _BoardConfig(
            wip=dict(_DEFAULT_WIP), p_overrides={}, retry_ceiling=3,
            card_deadline_s=1800.0, tick_interval_s=0.05, gates=(),
        )
        board = Board(
            manager=manager, reviewer=stub, cwd=cwd, cfg=cfg,
            team_ceiling=TeamCeiling(budget_tokens=1_000_000, scope=None, latency_seconds=None),
            root_node_id=manager._root.id, clock=fake_clock,
        )
        board.start()
        task1 = board._tick_task
        board.start()  # idempotent
        assert board._tick_task is task1
        await board.stop()

    @pytest.mark.asyncio
    async def test_tick_loop_forces_timeout_during_real_sleep(self, tmp_path):
        """Integration: start() with real async sleep; card times out."""
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1_000_000)
        manager = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        stub = DeterministicReviewerStub()
        fake = FakeClock(0.0)
        cfg = _BoardConfig(
            wip=dict(_DEFAULT_WIP), p_overrides={}, retry_ceiling=3,
            card_deadline_s=0.0, tick_interval_s=0.02, gates=(),
        )
        board = Board(
            manager=manager, reviewer=stub, cwd=tmp_path, cfg=cfg,
            team_ceiling=TeamCeiling(budget_tokens=1_000_000, scope=None, latency_seconds=None),
            root_node_id=root.id, clock=fake,
        )
        card = await board.spawn_card(deadline_override=fake() + 0.0)
        # Advance clock past deadline before starting the loop.
        fake.advance(1.0)
        board.start()
        await asyncio.sleep(0.1)
        await board.stop()
        assert board.cards()[0].column == "Blocked"
