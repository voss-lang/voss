"""EMBoardHandle — cage-bounded facade for the EM (O5-02, OEM-02/06/07/08).

The handle is the EM's ONLY board API. Legal verbs are explicitly listed;
everything else (ceiling writes, budget extension, agent invention) does NOT
exist on this class. Cage by API surface area, not by trust.

Audit records live in an in-memory side-table (_node_audit), NOT on
SessionTreeNode directly. This preserves O1 SPEC-5's strict-additive field
invariant. W5 integration confirms the on-disk persistence shape.
"""
from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from voss_runtime import EpisodicMemory

from voss.harness.permissions import PermissionGate
from voss.harness.session_tree import (
    SessionTreeManager,
    finalize_node,
    mutate_envelope,
)
from voss.harness.subagents import (
    MissionBrief,
    ScopeLine,
    SiblingLine,
    SubagentRegistry,
    SubagentSpec,
    agent_task,
)
from voss.harness.team import (
    TeamConfig,
    TeamRoleScope,
    filter_toolset_for_role,
    gate_for_role,
)
from voss.harness.tools import make_toolset

from .errors import EMCageViolation
from .protocols import TERMINAL_COLUMNS, BoardProtocol
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
    dispatched: frozenset = frozenset()


@dataclass(frozen=True, slots=True)
class WorkerArtifact:
    """A worker turn's output, attached to its card for the review gates."""
    artifact_text: str
    file_diff: str
    repo_context: str
    tests_passed: bool


# ---------------------------------------------------------------------------
# NodeAudit (in-memory side-table per node)
# ---------------------------------------------------------------------------

@dataclass
class _NodeAudit:
    routing_rationales: list = field(default_factory=list)
    kill_record: Optional[KillRecord] = None
    rescope_record: Optional[RescopeRecord] = None
    # V20 VRES-03: full worker prompt assembled at dispatch (additive).
    dispatched_prompt: Optional[str] = None


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
        run_turn_fn: Optional[Callable] = None,
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
        self._run_turn_fn = run_turn_fn
        self._renderer = renderer
        self._provider = provider
        self._model = model
        self._tickets: dict[str, Ticket] = {}
        self._node_audit: dict[str, _NodeAudit] = {}
        self._dispatched: dict[str, tuple[str, str]] = {}

    def _get_audit(self, node_id: str) -> _NodeAudit:
        if node_id not in self._node_audit:
            self._node_audit[node_id] = _NodeAudit()
        return self._node_audit[node_id]

    def _resolve_card_id(self, card_id: str) -> str:
        """EM-facing ids are ticket ids; map to the board card node id."""
        ticket = self._tickets.get(card_id)
        return ticket.card_node_id if ticket and ticket.card_node_id else card_id

    def _find_card(self, node_id: str):
        for c in self._board.cards():
            if getattr(c, "node_id", None) == node_id:
                return c
        return None

    def _block(self, card) -> None:
        if card is not None and getattr(card, "column", "") not in TERMINAL_COLUMNS:
            self._board.move(card, to="Blocked")

    def _role_spec(self, role_id: str) -> SubagentSpec:
        spec = self._registry.get(role_id)
        if spec is None:
            spec = SubagentSpec(id=role_id, description=f"role {role_id}", role_prompt="")
        return spec

    def _derive_role_gate(self, role_id: str) -> PermissionGate:
        """Derive the worker gate via registry lookup + gate_for_role.

        A role without its own scope is confined to the team ceiling scope.
        """
        spec = self._role_spec(role_id)
        if spec.scope is None:
            spec = dataclasses.replace(spec, scope=self._team_config.ceiling.scope)
        return gate_for_role(spec, self._base_gate, cwd=self._cwd)

    def _read_claimed_scopes(self) -> tuple[ScopeLine, ...]:
        """Active claims grouped by agent (VRES-03). Best-effort read-only:
        DB missing/locked/corrupt → empty scopes, never blocks dispatch."""
        import json

        from voss.harness import claims as claims_mod

        try:
            if not claims_mod._get_db_path(self._cwd).exists():
                return ()  # no DB — do not create one on a read path
            conn = claims_mod.open_claims_db(self._cwd)
            try:
                rows = claims_mod.active_claims(conn)
            finally:
                conn.close()
        except Exception:
            return ()
        by_agent: dict[str, set[str]] = {}
        for row in rows:
            try:
                patterns = json.loads(row[2])
            except (ValueError, TypeError):
                continue
            if isinstance(patterns, list):
                by_agent.setdefault(str(row[1]), set()).update(str(p) for p in patterns)
        return tuple(
            ScopeLine(owner_agent=agent, patterns=tuple(sorted(pats)))
            for agent, pats in sorted(by_agent.items())
        )

    def _build_mission_brief(self, *, card_id: str) -> MissionBrief:
        """Assemble dispatch-time context from sources that already exist:
        the ticket table (outcome, siblings) + the claims DB (scopes)."""
        ticket = self._tickets.get(card_id)
        outcome = ""
        if ticket is not None:
            outcome = ticket.original_idea
            if ticket.acceptance and len(ticket.acceptance) <= 120:
                outcome = f"{outcome} (accept: {ticket.acceptance})"

        columns = {
            getattr(c, "node_id", ""): getattr(c, "column", "")
            for c in self._board.cards()
        }
        siblings: list[SiblingLine] = []
        for tid, t in self._tickets.items():
            if tid == card_id:
                continue
            # A ticket with no card yet counts as in-flight (pending dispatch).
            column = columns.get(t.card_node_id, "") if t.card_node_id else ""
            if column in TERMINAL_COLUMNS:
                continue
            siblings.append(
                SiblingLine(role_id=t.worker_role, task_summary=t.original_idea[:120])
            )

        return MissionBrief(
            outcome=outcome,
            siblings=tuple(siblings),
            claimed_scopes=self._read_claimed_scopes(),
        )

    # --- READ ----------------------------------------------------------------

    def snapshot(self) -> BoardSnapshot:
        return BoardSnapshot(
            cards=tuple(self._board.cards()),
            tickets=tuple(self._tickets.values()),
            dispatched=frozenset(self._dispatched),
        )

    def all_cards_terminal(self) -> bool:
        cards = self._board.cards()
        return bool(cards) and all(
            getattr(c, "column", "") in TERMINAL_COLUMNS for c in cards
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
        node_id = self._resolve_card_id(card_id)
        self._get_audit(node_id).routing_rationales.append(rr)

        spec = self._role_spec(role_id)

        # V20 VRES-03: mission brief — outcome, sibling roster, claimed
        # scopes — so the worker is not dispatched blind. Assembled prompt
        # recorded on the audit side-table (additive).
        brief = self._build_mission_brief(card_id=card_id)
        self._get_audit(node_id).dispatched_prompt = agent_task(spec, task, brief=brief)

        self._dispatched[card_id] = (role_id, task)
        return rr

    def kill_card(self, card_id: str, rationale_text: str) -> KillRecord:
        card_id = self._resolve_card_id(card_id)
        card = self._find_card(card_id)

        # Cage: cannot kill a Done card.
        if card is not None and getattr(card, "column", "") == "Done":
            raise EMCageViolation(
                op="kill_card",
                reason="cannot kill card in column 'Done'",
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
        self._block(card)

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
        predecessor_ticket = self._tickets.get(card_id)
        card_id = self._resolve_card_id(card_id)
        card = self._find_card(card_id)

        # Cage: cannot rescope a Done card.
        if card is not None and getattr(card, "column", "") == "Done":
            raise EMCageViolation(
                op="rescope_card",
                reason="cannot rescope card in column 'Done'",
            )

        # Cage: new_scope must be contained in ceiling.scope.
        if new_scope is not None and self._team_config.ceiling.scope is not None:
            if not new_scope.is_contained_in(self._team_config.ceiling.scope):
                raise EMCageViolation(
                    op="rescope_card",
                    reason="new_scope exceeds ceiling.scope",
                )

        # Created first so an out-of-roster role is refused before the kill.
        successor_id = uuid.uuid4().hex[:12]
        if predecessor_ticket is not None:
            successor = self.create_ticket(
                original_idea=predecessor_ticket.original_idea,
                acceptance_criteria="\n".join(new_acceptance) or predecessor_ticket.acceptance,
                dod=", ".join(new_dod) or predecessor_ticket.dod,
                worker_role=new_worker_role,
                domain=predecessor_ticket.domain,
                risk_tier=predecessor_ticket.risk_tier,
            )
            successor_id = successor.id
            self._tickets[successor_id] = dataclasses.replace(
                successor, lineage_parent_id=predecessor_ticket.id,
            )

        # Kill the predecessor.
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
        self._block(card)

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
        if self._run_turn_fn is not None:
            await self._advance()

    async def _advance(self) -> None:
        """Spawn cards for new tickets, then step every dispatched card.

        ponytail: cards run one at a time in the shared cwd; parallel
        workers need per-card worktrees (see swarm_worktree).
        """
        for ticket_id, ticket in list(self._tickets.items()):
            if not ticket.card_node_id:
                card = await self._board.spawn_card(
                    risk_tier=ticket.risk_tier,
                    idea=ticket.original_idea,
                    role=ticket.worker_role,
                    acceptance_criteria=ticket.acceptance,
                    domain=ticket.domain,
                )
                ticket = dataclasses.replace(ticket, card_node_id=card.node_id)
                self._tickets[ticket_id] = ticket
            if ticket_id not in self._dispatched:
                continue
            card = self._find_card(ticket.card_node_id)
            if card is not None and card.column not in TERMINAL_COLUMNS:
                await self._step(ticket_id, card)

    async def _step(self, ticket_id: str, card) -> None:
        """Move one card as far as its gates allow this tick."""
        from voss.harness.board.errors import BoardGateError, BoardWIPError

        try:
            if card.column == "Backlog":
                card = self._board.move(card, to="Planned")
            if card.column == "Planned":
                card = self._board.move(card, to="InProgress")
        except BoardWIPError:
            return
        except BoardGateError:
            self._block(card)
            return

        try:
            if card.column == "InProgress":
                card = await self._run_worker(ticket_id, card)
                card = self._board.move(card, to="InReview")
            if card.column == "InReview":
                self._board.move(card, to="Done")
        except BoardWIPError:
            return
        except BoardGateError as exc:
            node = self._manager.get_node(card.node_id)
            last = node.transitions[-1] if node is not None and node.transitions else {}
            snap = last.get("verdict_snapshot") or {}
            notes = f"gate refused: {', '.join(exc.failing_clauses or [])}"
            if snap.get("notes"):
                notes = f"{notes}\n{snap['notes']}"
            self._retry(card, notes)
        except Exception as exc:  # noqa: BLE001 — a reviewer call failed; retry the card
            self._retry(card, f"review failed: {exc}")

    def _retry(self, card, notes: str) -> None:
        from voss.harness.board.verdict import ReviewerVerdict

        self._board.critic_step(card, ReviewerVerdict(
            conf=0.0, source="B", tier="strong", verdict="fail",
            notes=notes[:2000], evidence_refs=(),
        ))

    async def _run_worker(self, ticket_id: str, card):
        """Run the dispatched role's turn and attach its output to the card."""
        from voss.harness.board.reviewer_a import _extract_exit_code
        from voss.harness.board.reviewer_b import build_repo_context
        from voss.harness.decision_review import collect_working_tree

        role_id, task = self._dispatched[ticket_id]
        node = self._manager.get_node(card.node_id)
        if node is not None and node.retry_notes:
            task = f"{task}\n\nYour previous attempt was rejected:\n{node.retry_notes[-1]['notes']}"
        spec = self._role_spec(role_id)
        tools = filter_toolset_for_role(spec, make_toolset(self._cwd, renderer=self._renderer))
        brief = self._build_mission_brief(card_id=ticket_id)
        try:
            result = await self._run_turn_fn(
                agent_task(spec, task, brief=brief),
                tools=tools,
                cwd=self._cwd,
                renderer=self._renderer,
                model=self._model,
                provider=self._provider,
                history=EpisodicMemory(capacity=20),
                permissions=self._derive_role_gate(role_id),
                token_budget=node.envelope["limit"] - node.envelope["spent"] if node else 60_000,
            )
            final, tool_results = result.final, result.tool_results
            if node is not None and result.run is not None:
                used = (result.run.iteration_total_prompt_tokens or 0) + (
                    result.run.iteration_total_completion_tokens or 0
                )
                if used > 0:
                    mutate_envelope(node, delta=-used, cwd=self._cwd)
        except Exception as exc:  # noqa: BLE001 — a crashed worker is a failed attempt
            final, tool_results = f"<error: worker failed: {exc}>", []

        try:
            diff, _ = collect_working_tree(self._cwd)
        except ValueError:
            diff = ""
        exit_code, _ = _extract_exit_code(tool_results)
        return self._board.attach_artifact(card, WorkerArtifact(
            artifact_text=final,
            file_diff=diff,
            repo_context=build_repo_context(self._cwd, diff) if diff else "",
            tests_passed=exit_code == 0,
        ))

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
