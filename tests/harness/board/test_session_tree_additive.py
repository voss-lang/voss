"""O3-01 Task 1: additive substrate tests for SessionTreeNode + SessionTreeManager."""
from __future__ import annotations

import json

import pytest

from voss.harness.session import EXIT_REASONS, RunRecord
from voss.harness.session_tree import (
    SessionTreeManager,
    SessionTreeNode,
    _hydrate_node,
    _write_node_file,
)


class TestSessionTreeNodeAdditiveFields:
    def test_new_root_has_empty_transitions_and_retry_notes(self, tmp_path):
        node = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        assert node.transitions == []
        assert node.retry_notes == []

    def test_transitions_and_retry_notes_round_trip_through_disk(self, tmp_path):
        node = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        node.transitions.append({"from": "Backlog", "to": "Planned", "ts": "t0"})
        node.retry_notes.append({"round": 1, "notes": "fix the test"})
        _write_node_file(node, tmp_path)

        # Re-read from disk and hydrate.
        path = tmp_path / ".voss" / "sessions" / node.root_id / f"{node.id}.json"
        data = json.loads(path.read_text())
        restored = _hydrate_node(data)

        assert restored.transitions == [{"from": "Backlog", "to": "Planned", "ts": "t0"}]
        assert restored.retry_notes == [{"round": 1, "notes": "fix the test"}]

    def test_hydrate_backwards_compat_with_pre_o3_json(self):
        """Pre-O3 node JSON files lack transitions/retry_notes keys.
        _hydrate_node must default them to [] without raising."""
        pre_o3 = {
            "id": "abc",
            "root_id": "abc",
            "parent_run_id": None,
            "envelope": {"limit": 1000, "spent": 0},
            "terminal_state": None,
            "created_at": "2026-01-01T00:00:00Z",
            "ended_at": None,
            "rejected_raises": [],
        }
        node = _hydrate_node(pre_o3)
        assert node.transitions == []
        assert node.retry_notes == []


class TestSessionTreeManagerGetNode:
    def test_get_node_returns_root(self, tmp_path):
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        assert mgr.get_node(root.id) is root

    def test_get_node_returns_none_for_unknown(self, tmp_path):
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        assert mgr.get_node("does-not-exist") is None

    @pytest.mark.asyncio
    async def test_get_node_returns_child_after_allocate(self, tmp_path):
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(100)
        assert mgr.get_node(child.id) is child


class TestExitReasonsExtension:
    def test_timeout_in_exit_reasons(self):
        assert "timeout" in EXIT_REASONS

    def test_run_record_accepts_timeout_exit_reason(self):
        rec = RunRecord(id="x", started_at="", ended_at="", exit_reason="timeout")
        assert rec.exit_reason == "timeout"

    def test_exit_reasons_is_sorted_superset_of_pre_o3(self):
        pre_o3 = {"done", "max-iter", "budget", "interrupt", "batch-invariant"}
        assert pre_o3.issubset(EXIT_REASONS)
        # "killed" added post-O3 by O5 for the EM kill-flow; "error" added by
        # V4-01 (VTREE-07) for the exception-path subagent finalize. Subset
        # check (not ==) so additive EXIT_REASONS members don't churn this test.
        assert (pre_o3 | {"timeout", "killed", "error"}).issubset(EXIT_REASONS)
