"""O1 session-tree substrate; no provider, no git.

Tests cover tree persistence, budget fan-out invariant, cap-raise guard,
concurrency no-oversell, and schema isolation (redaction invariant).
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import stat
from pathlib import Path

import pytest

from voss.harness.session import EXIT_REASONS, RunRecord, SessionRecord
from voss.harness.session_tree import (
    BudgetAllocationError,
    BudgetCapRaiseError,
    SessionTreeManager,
    SessionTreeNode,
    finalize_node,
    mutate_envelope,
)

_NODE_JSON_KEYS = frozenset(
    {
        "id",
        "root_id",
        "parent_run_id",
        "envelope",
        "terminal_state",
        "created_at",
        "ended_at",
        "rejected_raises",
    }
)


def _sessions_tree_dir(cwd: Path, root_id: str) -> Path:
    return cwd / ".voss" / "sessions" / root_id


def _node_path(cwd: Path, root_id: str, node_id: str) -> Path:
    return _sessions_tree_dir(cwd, root_id) / f"{node_id}.json"


def _load_nodes_from_disk(cwd: Path, root_id: str) -> dict[str, dict]:
    tree_dir = _sessions_tree_dir(cwd, root_id)
    nodes: dict[str, dict] = {}
    for path in tree_dir.glob("*.json"):
        data = json.loads(path.read_text())
        nodes[data["id"]] = data
    return nodes


class TestTreePersistence:
    async def test_root_and_children_persist_and_reconstruct(
        self, tmp_path: Path
    ) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        n = 3
        children = [await mgr.allocate_child(100) for _ in range(n)]

        tree_dir = _sessions_tree_dir(tmp_path, root.id)
        child_files = [
            p
            for p in tree_dir.glob("*.json")
            if json.loads(p.read_text())["parent_run_id"] == root.id
        ]
        assert len(child_files) == n

        for child in children:
            path = _node_path(tmp_path, root.id, child.id)
            assert path.exists()
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            data = json.loads(path.read_text())
            assert data["parent_run_id"] == root.id
            assert data["root_id"] == root.id

        by_id = _load_nodes_from_disk(tmp_path, root.id)
        child_on_disk = {
            nid: data
            for nid, data in by_id.items()
            if data.get("parent_run_id") == root.id
        }
        assert len(child_on_disk) == n
        for child in children:
            assert child.id in by_id
            assert by_id[child.id]["parent_run_id"] == root.id

        assert {c.id for c in children} == set(child_on_disk)


class TestBudgetFanOut:
    async def test_valid_allocation(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        a = await mgr.allocate_child(300)
        b = await mgr.allocate_child(300)
        c = await mgr.allocate_child(300)
        assert isinstance(a, SessionTreeNode)
        assert isinstance(b, SessionTreeNode)
        assert isinstance(c, SessionTreeNode)
        assert len(mgr._children) == 3

    async def test_oversell_raises(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        await mgr.allocate_child(900)
        tree_dir = _sessions_tree_dir(tmp_path, root.id)
        files_before = set(tree_dir.glob("*.json"))
        with pytest.raises(BudgetAllocationError):
            await mgr.allocate_child(100)
        assert len(mgr._children) == 1
        assert set(tree_dir.glob("*.json")) == files_before


class TestCapRaiseGuard:
    def test_raise_errors(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=500)
        with pytest.raises(BudgetCapRaiseError):
            mutate_envelope(root, delta=50, cwd=tmp_path)

    def test_raise_recorded(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=500)
        with pytest.raises(BudgetCapRaiseError):
            mutate_envelope(root, delta=25, cwd=tmp_path)
        assert len(root.rejected_raises) == 1
        entry = root.rejected_raises[0]
        assert entry["requested_delta"] == 25
        assert "attempted_at" in entry
        path = _node_path(tmp_path, root.id, root.id)
        on_disk = json.loads(path.read_text())
        assert len(on_disk["rejected_raises"]) == 1
        assert on_disk["rejected_raises"][0]["requested_delta"] == 25

    def test_spend_unaffected(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=500)
        mutate_envelope(root, delta=-30, cwd=tmp_path)
        assert root.envelope["spent"] == 30
        path = _node_path(tmp_path, root.id, root.id)
        on_disk = json.loads(path.read_text())
        assert on_disk["envelope"]["spent"] == 30


class TestConcurrency:
    async def test_concurrent_no_oversell(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=900)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        tasks = [mgr.allocate_child(100) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = [r for r in results if isinstance(r, SessionTreeNode)]
        errors = [r for r in results if isinstance(r, BudgetAllocationError)]
        assert len(successes) == 8
        assert len(errors) == 2


class TestSchemaIsolation:
    def test_budget_not_serialized(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=100)
        d = root.to_dict()
        assert "_budget" not in d
        path = _node_path(tmp_path, root.id, root.id)
        on_disk = json.loads(path.read_text())
        assert "_budget" not in on_disk

    def test_node_keys_exact(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=100)
        assert set(root.to_dict().keys()) == _NODE_JSON_KEYS
        path = _node_path(tmp_path, root.id, root.id)
        on_disk = json.loads(path.read_text())
        assert set(on_disk.keys()) == _NODE_JSON_KEYS

    def test_no_schema_merge(self) -> None:
        # Tree-only persisted fields must not collide with Session/Run schemas
        # (id/ended_at/created_at are shared vocabulary, not a merge risk).
        tree_only = _NODE_JSON_KEYS - {"id", "created_at", "ended_at"}
        session_names = {f.name for f in dataclasses.fields(SessionRecord)}
        run_names = {f.name for f in dataclasses.fields(RunRecord)}
        assert tree_only.isdisjoint(session_names)
        assert tree_only.isdisjoint(run_names)


class TestDrainFinalize:
    def test_finalize_sets_terminal_and_ended(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=500)
        finalize_node(
            root,
            exit_reason="budget",
            final="halted: budget",
            cwd=tmp_path,
        )
        assert root.terminal_state is not None
        assert root.terminal_state["exit_reason"] == "budget"
        assert root.terminal_state["final"] == "halted: budget"
        assert root.ended_at is not None
        disk = json.loads(_node_path(tmp_path, root.id, root.id).read_text())
        assert disk["terminal_state"] == root.terminal_state
        assert disk["ended_at"] == root.ended_at

    def test_finalize_is_idempotent(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=400)
        finalize_node(root, exit_reason="done", final="finished", cwd=tmp_path)
        assert root.ended_at is not None
        assert root._finalized is True
        ended_after_first = root.ended_at
        ts_after_first = dict(root.terminal_state) if root.terminal_state else {}
        finalize_node(
            root,
            exit_reason="done",
            final="different",
            cwd=tmp_path,
        )
        assert root.ended_at == ended_after_first
        assert root.terminal_state == ts_after_first

    def test_exit_reason_must_be_valid(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=100)
        assert "quit" not in EXIT_REASONS
        with pytest.raises(ValueError):
            finalize_node(
                root, exit_reason="quit", final="", cwd=tmp_path
            )


class TestNoOpenNodes:
    async def test_no_open_node_after_finalize(
        self, tmp_path: Path
    ) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=900)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        children = [await mgr.allocate_child(100) for _ in range(3)]
        tree_dir = _sessions_tree_dir(tmp_path, root.id)
        json_paths = sorted(tree_dir.glob("*.json"))
        assert len(json_paths) == 4  # root + 3 children
        for node in (root, *children):
            finalize_node(
                node, exit_reason="done", final="closed", cwd=tmp_path
            )
        assert tree_dir.exists()
        for path in tree_dir.glob("*.json"):
            blob = json.loads(path.read_text())
            assert blob.get("terminal_state") is not None
