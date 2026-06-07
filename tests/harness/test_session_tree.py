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
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from voss.harness import subagents as subagents_mod
from voss.harness.cli import session_group
from voss.harness.session import EXIT_REASONS, RunRecord, SessionRecord
from voss.harness.session_tree import (
    BudgetAllocationError,
    BudgetCapRaiseError,
    SessionTreeManager,
    SessionTreeNode,
    SessionTreeNotFoundError,
    _hydrate_node,
    export_tree,
    finalize_node,
    mutate_envelope,
)
from voss.harness.subagents import (
    SubagentRegistry,
    SubagentSpec,
    run_subagent,
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
        # O3 OBRD-01: per-card transition + retry history (additive).
        "transitions",
        "retry_notes",
        # V4 VTREE-08: nullable scope/role spawn metadata (additive).
        "scope",
        "role",
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


class TestSchemaExtension:
    def test_default_scope_role_null(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        assert root.scope is None
        assert root.role is None

    async def test_scope_role_spawn(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        child = await mgr.allocate_child(100, scope="review", role="worker")
        assert child.scope == "review"
        assert child.role == "worker"
        on_disk = json.loads(_node_path(tmp_path, root.id, child.id).read_text())
        assert on_disk["scope"] == "review"
        assert on_disk["role"] == "worker"

    async def test_spawn_without_scope_role_null(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        child = await mgr.allocate_child(100)
        assert child.scope is None
        assert child.role is None
        on_disk = json.loads(_node_path(tmp_path, root.id, child.id).read_text())
        assert on_disk["scope"] is None
        assert on_disk["role"] is None

    def test_pre_v4_file_hydrates_null(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        data = root.to_dict()
        data.pop("scope", None)
        data.pop("role", None)
        node = _hydrate_node(data)
        assert node.scope is None
        assert node.role is None


# ---------------------------------------------------------------------------
# V4-02: pre-emptive spend guard + spend wiring + all-reason finalize boundary.
# ---------------------------------------------------------------------------


def _registry() -> SubagentRegistry:
    reg = SubagentRegistry()
    reg.register(
        SubagentSpec(id="worker", description="bounded task", role_prompt="do it")
    )
    return reg


def _turn_result(*, final: str, prompt_tokens: int, completion_tokens: int, exit_reason):
    """A minimal TurnResult stand-in with a RunRecord-like `.run`."""
    run = SimpleNamespace(
        iteration_total_prompt_tokens=prompt_tokens,
        iteration_total_completion_tokens=completion_tokens,
        exit_reason=exit_reason,
    )
    return SimpleNamespace(final=final, run=run)


async def _run(node, tmp_path: Path) -> str:
    return await run_subagent(
        agent_id="worker",
        task="t",
        registry=_registry(),
        cwd=tmp_path,
        renderer=None,
        provider=object(),
        model="m",
        gate=object(),
        node=node,
    )


class TestSpendGuard:
    async def test_guard_blocks_when_envelope_exhausted(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=100)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(100)
        mutate_envelope(child, delta=-100, cwd=tmp_path)
        assert child.envelope["spent"] >= child.envelope["limit"]

        with patch.object(subagents_mod, "run_turn", new=AsyncMock()) as mock_turn:
            out = await _run(child, tmp_path)

        mock_turn.assert_not_called()
        assert out == "<halted: budget — envelope exhausted>"
        assert child._finalized is True
        assert child.terminal_state is not None
        assert child.terminal_state["exit_reason"] == "budget"

    async def test_spent_updated_after_call(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(1000)
        assert child.envelope["spent"] == 0

        result = _turn_result(
            final="ok", prompt_tokens=30, completion_tokens=20, exit_reason=None
        )
        with patch.object(
            subagents_mod, "run_turn", new=AsyncMock(return_value=result)
        ):
            out = await _run(child, tmp_path)

        assert out == "ok"
        assert child.envelope["spent"] == 50
        assert child.terminal_state["exit_reason"] == "done"
        on_disk = json.loads(_node_path(tmp_path, root.id, child.id).read_text())
        assert on_disk["envelope"]["spent"] == 50

    async def test_no_run_record_no_spend_update(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(1000)

        result = SimpleNamespace(final="done", run=None)
        with patch.object(
            subagents_mod, "run_turn", new=AsyncMock(return_value=result)
        ):
            out = await _run(child, tmp_path)

        assert out == "done"
        assert child.envelope["spent"] == 0
        assert child.terminal_state["exit_reason"] == "done"

    async def test_soft_exit_budget_finalizes_budget(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(1000)

        result = _turn_result(
            final="hit cap", prompt_tokens=10, completion_tokens=5, exit_reason="budget"
        )
        with patch.object(
            subagents_mod, "run_turn", new=AsyncMock(return_value=result)
        ):
            out = await _run(child, tmp_path)

        assert out == "hit cap"
        assert child.envelope["spent"] == 15
        assert child.terminal_state["exit_reason"] == "budget"


class TestAllReasonsFinalize:
    @pytest.mark.parametrize("reason", sorted(EXIT_REASONS))
    def test_finalize_accepts_every_exit_reason(
        self, tmp_path: Path, reason: str
    ) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=100)
        finalize_node(root, exit_reason=reason, final="", cwd=tmp_path)
        assert root._finalized is True
        assert root.terminal_state is not None
        assert root.terminal_state["exit_reason"] == reason
        assert root.ended_at is not None

    async def test_timeout_path(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(1000)

        with patch.object(
            subagents_mod,
            "run_turn",
            new=AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            with pytest.raises(asyncio.TimeoutError):
                await _run(child, tmp_path)

        assert child._finalized is True
        assert child.terminal_state["exit_reason"] == "timeout"
        assert child.ended_at is not None

    async def test_error_path(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(1000)

        with patch.object(
            subagents_mod,
            "run_turn",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            with pytest.raises(RuntimeError):
                await _run(child, tmp_path)

        assert child._finalized is True
        assert child.terminal_state["exit_reason"] == "error"
        assert "boom" in child.terminal_state["final"]
        assert child.ended_at is not None

    async def test_budget_exception_path(self, tmp_path: Path) -> None:
        from voss_runtime.exceptions import BudgetExceededError

        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(1000)

        with patch.object(
            subagents_mod,
            "run_turn",
            new=AsyncMock(
                side_effect=BudgetExceededError(
                    reason="cap", limit=1000, observed=1001
                )
            ),
        ):
            out = await _run(child, tmp_path)

        assert out == "<halted: budget>"
        assert child._finalized is True
        assert child.terminal_state["exit_reason"] == "budget"

    async def test_no_double_finalize_first_reason_wins(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=0, cwd=tmp_path)
        child = await mgr.allocate_child(1000)

        # Error branch finalizes with "error"; the finally net must NOT overwrite.
        with patch.object(
            subagents_mod,
            "run_turn",
            new=AsyncMock(side_effect=ValueError("nope")),
        ):
            with pytest.raises(ValueError):
                await _run(child, tmp_path)

        assert child.terminal_state["exit_reason"] == "error"
        assert child.terminal_state["final"] == "<error: nope>"


# ---------------------------------------------------------------------------
# V4-03: consolidated export (VTREE-10) + voss session tree CLI (VTREE-09).
# ---------------------------------------------------------------------------


class TestExport:
    async def test_export_round_trips(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        n = 3
        children = [
            await mgr.allocate_child(100, scope="review", role="worker")
            for _ in range(n)
        ]

        tree = export_tree(root.id, tmp_path)
        assert tree["root_id"] == root.id
        assert len(tree["nodes"]) == n + 1

        by_id = {node["id"]: node for node in tree["nodes"]}
        assert root.id in by_id
        assert {c.id for c in children} <= set(by_id)

        # Parent linkage + scope/role present; round-trip via _hydrate_node.
        for child in children:
            data = by_id[child.id]
            assert data["parent_run_id"] == root.id
            assert data["scope"] == "review"
            assert data["role"] == "worker"
            rehydrated = _hydrate_node(data)
            assert rehydrated.id == child.id
            assert rehydrated.envelope == child.envelope
            assert rehydrated.scope == "review"
            assert rehydrated.role == "worker"

        root_data = by_id[root.id]
        assert root_data["parent_run_id"] is None

    async def test_reconstructs_from_disk_alone(self, tmp_path: Path) -> None:
        # VTREE-03: N children → N node files; tree rebuilds from export only.
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        n = 4
        children = [await mgr.allocate_child(100) for _ in range(n)]

        tree_dir = _sessions_tree_dir(tmp_path, root.id)
        assert len(list(tree_dir.glob("*.json"))) == n + 1

        tree = export_tree(root.id, tmp_path)
        rebuilt = {
            node["id"]: _hydrate_node(node) for node in tree["nodes"]
        }
        assert set(rebuilt) == {root.id} | {c.id for c in children}
        for child in children:
            assert rebuilt[child.id].parent_run_id == root.id

    def test_open_node_exports_null_terminal_state(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=500)
        tree = export_tree(root.id, tmp_path)
        assert tree["nodes"][0]["terminal_state"] is None

    def test_export_unknown_root_raises(self, tmp_path: Path) -> None:
        with pytest.raises(SessionTreeNotFoundError):
            export_tree("deadbeefcafe", tmp_path)

    def test_export_empty_dir_raises(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / ".voss" / "sessions" / "emptyroot01"
        empty_dir.mkdir(parents=True)
        with pytest.raises(SessionTreeNotFoundError):
            export_tree("emptyroot01", tmp_path)


class TestCLI:
    async def test_known_root_exit_zero(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        child = await mgr.allocate_child(100, scope="review", role="worker")

        result = CliRunner().invoke(
            session_group, ["tree", root.id, "--cwd", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert root.id in result.output
        assert child.id in result.output

    def test_unknown_root_exit_nonzero(self, tmp_path: Path) -> None:
        result = CliRunner().invoke(
            session_group, ["tree", "deadbeefcafe", "--cwd", str(tmp_path)]
        )
        assert result.exit_code != 0
        assert result.output.strip() != ""

    async def test_json_mode_parses(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        await mgr.allocate_child(100)

        result = CliRunner().invoke(
            session_group, ["tree", root.id, "--cwd", str(tmp_path), "--json"]
        )
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "nodes" in payload
        assert payload["root_id"] == root.id
        assert len(payload["nodes"]) == 2
