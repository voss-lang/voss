"""Session-tree substrate: per-node budget envelopes and fan-out allocation.

Nodes persist at <cwd>/.voss/sessions/<root_id>/<node_id>.json (0o600).
Separate from flat SessionRecord snapshots — never merged into session.save().
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from voss_runtime import BudgetScope

__all__ = [
    "BudgetAllocationError",
    "BudgetCapRaiseError",
    "SessionTreeManager",
    "SessionTreeNode",
    "finalize_node",
    "mutate_envelope",
]


class BudgetAllocationError(Exception):
    """Raised when a child allocation would oversell the parent envelope."""


class BudgetCapRaiseError(Exception):
    """Raised when an upward envelope delta (cap raise) is rejected."""

    def __init__(self, node_id: str, attempted_delta: int, reason: str) -> None:
        self.node_id = node_id
        self.attempted_delta = attempted_delta
        self.reason = reason
        super().__init__(
            f"cap raise rejected for node {node_id}: "
            f"delta={attempted_delta} ({reason})"
        )


@dataclass
class SessionTreeNode:
    id: str
    root_id: str
    parent_run_id: Optional[str]
    envelope: dict
    terminal_state: Optional[dict]
    created_at: str
    ended_at: Optional[str]
    rejected_raises: list = field(default_factory=list)
    _budget: Optional[BudgetScope] = field(default=None, init=False, repr=False)
    _finalized: bool = field(default=False, init=False, repr=False)

    @classmethod
    def create_root(cls, *, cwd: Path, limit: int) -> SessionTreeNode:
        node_id = uuid.uuid4().hex[:12]
        node = cls(
            id=node_id,
            root_id=node_id,
            parent_run_id=None,
            envelope={"limit": limit, "spent": 0},
            terminal_state=None,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ended_at=None,
            rejected_raises=[],
        )
        _write_node_file(node, cwd)
        return node

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_budget", None)
        d.pop("_finalized", None)
        return d


_NODE_FIELDS = {f.name for f in dataclasses.fields(SessionTreeNode)}


def _hydrate_node(data: dict) -> SessionTreeNode:
    kept = {k: v for k, v in data.items() if k in _NODE_FIELDS}
    kept.setdefault("rejected_raises", [])
    return SessionTreeNode(**kept)


def _write_node_file(node: SessionTreeNode, cwd: Path) -> Path:
    path = cwd / ".voss" / "sessions" / node.root_id / f"{node.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(node.to_dict(), indent=2))
    path.chmod(0o600)
    return path


def finalize_node(
    node: SessionTreeNode,
    *,
    exit_reason: str,
    final: str = "",
    cwd: Path,
) -> None:
    """STUB (O1-02 Task 1 RED): import hook only; logic added in Task 2."""
    pass


def mutate_envelope(node: SessionTreeNode, delta: int, cwd: Path) -> None:
    """Single guarded mutator for envelope changes (D-04)."""
    if delta > 0:
        node.rejected_raises.append(
            {
                "attempted_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "requested_delta": delta,
                "reason": "cap_raise_rejected",
            }
        )
        _write_node_file(node, cwd)
        raise BudgetCapRaiseError(node.id, delta, "non-extendable cap")
    node.envelope["spent"] += abs(delta)
    _write_node_file(node, cwd)


class SessionTreeManager:
    """Owns one tree's allocation state; one instance per running root."""

    def __init__(
        self, root_node: SessionTreeNode, *, reserve: int, cwd: Path
    ) -> None:
        self._root = root_node
        self._reserve = reserve
        self._cwd = cwd
        self._children: list[SessionTreeNode] = []
        self._lock = asyncio.Lock()

    async def allocate_child(self, limit: int) -> SessionTreeNode:
        async with self._lock:
            allocated = sum(c.envelope["limit"] for c in self._children)
            available = (
                self._root.envelope["limit"] - self._reserve - allocated
            )
            if limit > available:
                raise BudgetAllocationError(
                    f"child limit {limit} exceeds available {available} "
                    f"(reserve={self._reserve})"
                )
            child_id = uuid.uuid4().hex[:12]
            child = SessionTreeNode(
                id=child_id,
                root_id=self._root.id,
                parent_run_id=self._root.id,
                envelope={"limit": limit, "spent": 0},
                terminal_state=None,
                created_at=datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                ended_at=None,
                rejected_raises=[],
            )
            self._children.append(child)
            _write_node_file(child, self._cwd)
            child._budget = BudgetScope(token_limit=limit, name=child.id)
            return child
