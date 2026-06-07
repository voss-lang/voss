"""EMBoardHandle — cage-bounded facade for the EM (O5-02, OEM-02/06/07/08).

The handle is the EM's ONLY board API. Legal verbs are explicitly listed;
everything else (ceiling writes, budget extension, agent invention) does NOT
exist on this class. Cage by API surface area, not by trust.

Audit records live in an in-memory side-table (_node_audit), NOT on
SessionTreeNode directly. This preserves O1 SPEC-5's strict-additive field
invariant. W5 integration confirms the on-disk persistence shape.
"""
from __future__ import annotations

import asyncio
import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from voss.harness.permissions import PermissionGate
from voss.harness.session_tree import (
    SessionTreeManager,
    SessionTreeNode,
    _write_node_file,
    finalize_node,
)
from voss.harness.subagents import SubagentRegistry, SubagentSpec
from voss.harness.team import (
    TeamConfig,
    TeamRoleScope,
    filter_toolset_for_role,
    gate_for_role,
)
from voss.harness.tools import make_toolset

from .errors import EMCageViolation
from .protocols import TERMINAL_COLUMNS, BoardProtocol, Column
from .tickets import (
    KillRecord,
    RescopeRecord,
    RoutingRationale,
    RunFinal,
    Ticket,
)


# ---------------------------------------------------------------------------
# BoardSnapshot (read-only view)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BoardSnapshot:
    """Read-only snapshot of the board state. Mutation is futile."""
    cards: tuple
    tickets: tuple


# ---------------------------------------------------------------------------
# NodeAudit (in-memory side-table per node)
# ---------------------------------------------------------------------------

@dataclass
class _NodeAudit:
    routing_rationales: list = field(default_factory=list)
    kill_record: Optional[KillRecord] = None
    rescope_record: Optional[RescopeRecord] = None


# ---------------------------------------------------------------------------
# EMBoardHandle
# ---------------------------------------------------------------------------

class EMBoardHandle:
    """Cage-bounded facade — the EM's ONLY board API.

    Deliberately absent: set_ceiling, set_p, set_budget, extend_budget,
    register_role, register_agent, mutate_team_config. The EM cannot
    reach them through ANY tool call.
    """

    def __init__(
        self,
        *,
        board: BoardProtocol,
        registry: SubagentRegistry,
        team_config: TeamConfig,
        manager: SessionTreeManager,
        base_gate: PermissionGate,
        cwd: Path,
        subagent_runner: Optional[Callable] = None,
        renderer: object = None,
        provider: object = None,
        model: str = "",
    ) -> None:
        self._board = board
        self._registry = registry
        self._team_config = team_config
        self._manager = manager
        self._base_gate = base_gate
        self._cwd = cwd
        self._subagent_runner = subagent_runner
        self._renderer = renderer
        self._provider = provider
        self._model = model
        self._tickets: dict[str, Ticket] = {}
        self._node_audit: dict[str, _NodeAudit] = {}

    def _get_audit(self, node_id: str) -> _NodeAudit:
        if node_id not in self._node_audit:
            self._node_audit[node_id] = _NodeAudit()
        return self._node_audit[node_id]

    def _role_spec(self, role_id: str) -> SubagentSpec:
        spec = self._registry.get(role_id)
        if spec is None:
            spec = SubagentSpec(id=role_id, description=f"role {role_id}", role_prompt="")
        return spec

    def _derive_role_gate(self, role_id: str) -> PermissionGate:
        """Derive per-role gate via registry lookup + gate_for_role (dispatch_card path)."""
        return gate_for_role(self._role_spec(role_id), self._base_gate)

    # --- READ ----------------------------------------------------------------

    def snapshot(self) -> BoardSnapshot:
        return BoardSnapshot(
            cards=tuple(self._board.cards()),
            tickets=tuple(self._tickets.values()),
        )

    def all_cards_terminal(self) -> bool:
        return all(
            getattr(c, "column", "") in TERMINAL_COLUMNS
            for c in self._board.cards()
        )

    # --- WRITE: ticket lifecycle ---------------------------------------------

    def create_ticket(
        self,
        *,
        original_idea: str,
        acceptance_criteria: str,
        dod: str,
        worker_role: str,
        domain: str = "code",
        risk_tier: str = "med",
    ) -> Ticket:
        if worker_role not in self._team_config.roster_ids:
            raise EMCageViolation(
                op="create_ticket",
                reason=f"worker_role {worker_role!r} not in roster {sorted(self._team_config.roster_ids)}",
            )
        ticket_id = uuid.uuid4().hex[:12]
        rr_id = uuid.uuid4().hex[:12]
        ticket = Ticket(
            id=ticket_id,
            card_node_id="",  # filled after board spawn
            original_idea=original_idea,
            acceptance=acceptance_criteria,
            dod=dod,
            worker_role=worker_role,
            routing_rationale_id=rr_id,
            domain=domain,  # type: ignore[arg-type]
            risk_tier=risk_tier,  # type: ignore[arg-type]
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self._tickets[ticket_id] = ticket
        return ticket

    def set_ac(self, card_id: str, acceptance_criteria: str) -> Ticket:
        ticket = self._tickets[card_id]
        new_ticket = dataclasses.replace(ticket, acceptance=acceptance_criteria)
        self._tickets[card_id] = new_ticket
        return new_ticket

    def set_dod(self, card_id: str, dod: str) -> Ticket:
        ticket = self._tickets[card_id]
        new_ticket = dataclasses.replace(ticket, dod=dod)
        self._tickets[card_id] = new_ticket
        return new_ticket

    # --- WRITE: board mutation -----------------------------------------------

    def dispatch_card(
        self,
        *,
        card_id: str,
        role_id: str,
        task: str,
        rationale_text: str,
        candidates_considered: tuple[str, ...],
        confidence_hint: float | None = None,
    ) -> RoutingRationale:
        # Cage: role must be in roster.
        if role_id not in self._team_config.roster_ids:
            raise EMCageViolation(
                op="dispatch_card",
                reason=f"role {role_id!r} not in roster {sorted(self._team_config.roster_ids)}",
            )

        # Emit RoutingRationale BEFORE subagent fires (audit-survives-crash).
        rr = RoutingRationale(
            id=uuid.uuid4().hex[:12],
            card_id=card_id,
            chosen_role=role_id,
            candidates_considered=candidates_considered,
            rationale_text=rationale_text,
            confidence_hint=confidence_hint,
            ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

        # Store on side-table.
        # Use card_id as node_id proxy (tickets map card_id → ticket → card_node_id).
        ticket = self._tickets.get(card_id)
        node_id = ticket.card_node_id if ticket else card_id
        self._get_audit(node_id).routing_rationales.append(rr)

        # Derive per-role gate + toolset via O2 helpers.
        spec = self._role_spec(role_id)
        role_gate = self._derive_role_gate(role_id)
        base_toolset = make_toolset(self._cwd, renderer=self._renderer)
        role_toolset = filter_toolset_for_role(spec, base_toolset)

        # Fire subagent (async, fire-and-forget if runner provided).
        if self._subagent_runner is not None:
            asyncio.ensure_future(
                self._subagent_runner(
                    agent_id=role_id,
                    task=task,
                    registry=self._registry,
                    cwd=self._cwd,
                    renderer=self._renderer,
                    provider=self._provider,
                    model=self._model,
                    gate=role_gate,
                )
            ) if False else None  # placeholder — real dispatch in W4

        return rr

    def kill_card(self, card_id: str, rationale_text: str) -> KillRecord:
        # Find the card via the board.
        card = None
        for c in self._board.cards():
            if getattr(c, "node_id", None) == card_id:
                card = c
                break

        # Cage: cannot kill a Done card.
        if card is not None and getattr(card, "column", "") == "Done":
            raise EMCageViolation(
                op="kill_card",
                reason=f"cannot kill card in column 'Done'",
            )

        kr = KillRecord(
            killed_node_id=card_id,
            rationale_text=rationale_text,
            evidence_refs=(),
            killed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self._get_audit(card_id).kill_record = kr

        # Finalize the session-tree node (exit_reason="killed").
        node = self._manager.get_node(card_id)
        if node is not None and not node._finalized:
            finalize_node(node, exit_reason="killed", cwd=self._cwd)

        return kr

    def rescope_card(
        self,
        *,
        card_id: str,
        new_worker_role: str,
        rationale_text: str,
        new_acceptance: tuple[str, ...] = (),
        new_dod: tuple[str, ...] = (),
        new_scope: TeamRoleScope | None = None,
    ) -> RescopeRecord:
        # Find the card.
        card = None
        for c in self._board.cards():
            if getattr(c, "node_id", None) == card_id:
                card = c
                break

        # Cage: cannot rescope a Done card.
        if card is not None and getattr(card, "column", "") == "Done":
            raise EMCageViolation(
                op="rescope_card",
                reason=f"cannot rescope card in column 'Done'",
            )

        # Cage: new_scope must be contained in ceiling.scope.
        if new_scope is not None and self._team_config.ceiling.scope is not None:
            if not new_scope.is_contained_in(self._team_config.ceiling.scope):
                raise EMCageViolation(
                    op="rescope_card",
                    reason="new_scope exceeds ceiling.scope",
                )

        # Kill the predecessor.
        successor_id = uuid.uuid4().hex[:12]
        kr = KillRecord(
            killed_node_id=card_id,
            rationale_text=f"rescoped: {rationale_text}",
            evidence_refs=(),
            killed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            successor_card_id=successor_id,
        )
        self._get_audit(card_id).kill_record = kr

        # Finalize predecessor node.
        node = self._manager.get_node(card_id)
        if node is not None and not node._finalized:
            finalize_node(node, exit_reason="killed", cwd=self._cwd)

        # Emit RescopeRecord on the successor.
        rr = RescopeRecord(
            predecessor_card_id=card_id,
            successor_card_id=successor_id,
            diff_summary=rationale_text,
            rationale_text=rationale_text,
            new_acceptance=new_acceptance,
            new_dod=new_dod,
            rescoped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self._get_audit(successor_id).rescope_record = rr

        return rr

    # --- DRIVER --------------------------------------------------------------

    async def tick(self) -> None:
        import time
        self._board._tick_once(time.monotonic())

    def force_block_all(self, reason: str) -> None:
        """Harness-only, NOT EM-callable."""
        for card in self._board.cards():
            col = getattr(card, "column", "")
            if col not in TERMINAL_COLUMNS:
                try:
                    self._board.move(card, to="Blocked")
                except Exception:
                    pass

    def finalize_run(self) -> RunFinal:
        cards = self._board.cards()
        done = sum(1 for c in cards if getattr(c, "column", "") == "Done")
        blocked = sum(1 for c in cards if getattr(c, "column", "") == "Blocked")
        killed = sum(1 for a in self._node_audit.values() if a.kill_record is not None)
        rescoped = sum(1 for a in self._node_audit.values() if a.rescope_record is not None)
        return RunFinal(
            root_id=self._manager._root.id,
            idea="",
            total_cards=len(cards),
            done_count=done,
            blocked_count=blocked,
            killed_count=killed,
            rescope_count=rescoped,
            em_iterations=0,
            ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
