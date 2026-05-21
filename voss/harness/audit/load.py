"""Read-only audit snapshot loader (O6-02, OAUD-02).

Reads fixture-compatible session-tree JSON, sorts nodes/cards
deterministically, normalizes missing optional O3-O5 payloads to empty
tuples, and never writes to disk.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import (
    AuditCard,
    AuditNode,
    AuditSnapshot,
    KillRecord,
    Leak6Assessment,
    LivenessEvent,
    RescopeRecord,
    ReviewerAssessment,
    RoutingRationale,
)


class AuditLoadError(Exception):
    """Raised when a node file cannot be loaded."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"audit load error at {path}: {reason}")


def _read_node_file(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text()
    except OSError as exc:
        raise AuditLoadError(path, f"cannot read: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuditLoadError(path, f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AuditLoadError(path, "expected a JSON object")
    if "id" not in data:
        raise AuditLoadError(path, "missing required 'id' field")
    return data


def _extract_verdicts(transitions: list[dict]) -> tuple[ReviewerAssessment, ...]:
    out: list[ReviewerAssessment] = []
    for t in transitions:
        if t.get("kind") != "board.transition":
            continue
        vs = t.get("verdict_snapshot")
        if not isinstance(vs, dict):
            continue
        out.append(
            ReviewerAssessment(
                conf=float(vs.get("conf", 0.0)),
                source=str(vs.get("source", "")),
                tier=str(vs.get("tier", "")),
                verdict=str(vs.get("verdict", "")),
                notes=str(vs.get("notes", "")),
                evidence_refs=tuple(vs.get("evidence_refs", ())),
            )
        )
    return tuple(out)


def _extract_routing(transitions: list[dict]) -> RoutingRationale | None:
    for t in transitions:
        if t.get("kind") == "em.routing":
            return RoutingRationale(
                id=str(t.get("id", "")),
                card_id=str(t.get("card_id", "")),
                chosen_role=str(t.get("chosen_role", "")),
                candidates_considered=tuple(t.get("candidates_considered", ())),
                rationale_text=str(t.get("rationale_text", "")),
                ts=str(t.get("ts", "")),
                confidence_hint=t.get("confidence_hint"),
            )
    return None


def _extract_kill(transitions: list[dict]) -> KillRecord | None:
    for t in transitions:
        if t.get("kind") == "em.kill":
            return KillRecord(
                killed_node_id=str(t.get("killed_node_id", "")),
                rationale_text=str(t.get("rationale_text", "")),
                evidence_refs=tuple(t.get("evidence_refs", ())),
                killed_at=str(t.get("killed_at", "")),
                lineage_parent_id=t.get("lineage_parent_id"),
                successor_card_id=t.get("successor_card_id"),
            )
    return None


def _extract_rescope(transitions: list[dict]) -> RescopeRecord | None:
    for t in transitions:
        if t.get("kind") == "em.rescope":
            return RescopeRecord(
                predecessor_card_id=str(t.get("predecessor_card_id", "")),
                successor_card_id=str(t.get("successor_card_id", "")),
                diff_summary=str(t.get("diff_summary", "")),
                rationale_text=str(t.get("rationale_text", "")),
                rescoped_at=str(t.get("rescoped_at", "")),
                new_acceptance=tuple(t.get("new_acceptance", ())),
                new_dod=tuple(t.get("new_dod", ())),
            )
    return None


def _extract_run_final(transitions: list[dict]) -> dict | None:
    for t in transitions:
        if t.get("kind") == "em.run_final":
            return dict(t)
    return None


def _extract_leak6(transitions: list[dict]) -> Leak6Assessment:
    for t in transitions:
        if t.get("kind") == "audit.leak6":
            return Leak6Assessment(
                status=t.get("status", "accepted_gap"),
                evidence=str(t.get("evidence", "")),
                mitigation_present=bool(t.get("mitigation_present", False)),
            )
    return Leak6Assessment(
        status="warning",
        evidence="no Leak-6 assessment found in session tree",
        mitigation_present=False,
    )


def _classify_liveness(data: dict) -> tuple[LivenessEvent, ...]:
    events: list[LivenessEvent] = []
    node_id = data.get("id", "")
    terminal = data.get("terminal_state")
    ended = data.get("ended_at")

    if terminal is not None:
        exit_reason = terminal.get("exit_reason", "")
        if exit_reason == "timeout":
            events.append(
                LivenessEvent(
                    node_id=node_id,
                    event_type="timeout",
                    severity="blocked",
                    detail=f"node {node_id} timed out",
                )
            )
        else:
            events.append(
                LivenessEvent(
                    node_id=node_id,
                    event_type="terminal",
                    severity="ok",
                    detail=f"node {node_id} terminal: {exit_reason}",
                )
            )
    elif ended is None:
        events.append(
            LivenessEvent(
                node_id=node_id,
                event_type="open_node",
                severity="warning",
                detail=f"node {node_id} has no terminal state and no ended_at",
            )
        )

    envelope = data.get("envelope", {})
    limit = envelope.get("limit", 0)
    spent = envelope.get("spent", 0)
    if limit > 0 and spent >= limit:
        events.append(
            LivenessEvent(
                node_id=node_id,
                event_type="reserve_exhausted",
                severity="warning",
                detail=f"node {node_id} spent {spent}/{limit}",
            )
        )

    return tuple(events)


def _build_card(data: dict, *, is_root: bool) -> AuditCard | None:
    """Build an AuditCard from a node dict. Root nodes are not cards."""
    if is_root:
        return None
    transitions = data.get("transitions", [])
    ticket = None
    for t in transitions:
        if t.get("kind") == "em.ticket":
            ticket = t
            break

    kill = _extract_kill(transitions)
    rescope = _extract_rescope(transitions)
    routing = _extract_routing(transitions)
    verdicts = _extract_verdicts(transitions)

    # Determine column from last board transition.
    column = "Backlog"
    for t in transitions:
        if t.get("kind") == "board.transition":
            column = t.get("to", column)

    terminal = data.get("terminal_state")
    if terminal is not None:
        exit_reason = terminal.get("exit_reason", "")
        if exit_reason == "timeout":
            column = "Blocked"
        elif exit_reason == "killed":
            column = "Blocked"
        elif exit_reason == "done":
            column = "Done"

    risk_tier = "med"
    if ticket:
        risk_tier = ticket.get("risk_tier", "med")

    retry_notes_raw = data.get("retry_notes", [])

    return AuditCard(
        node_id=data["id"],
        column=column,
        risk_tier=risk_tier,
        retry_count=len(retry_notes_raw),
        is_killed=kill is not None,
        kill_record=kill,
        is_rescoped=rescope is not None,
        rescope_record=rescope,
        routing=routing,
        verdicts=verdicts,
        retry_notes=tuple(retry_notes_raw),
    )


def load_audit_snapshot(root: Path) -> AuditSnapshot:
    """Load an audit snapshot from a session-tree directory.

    ``root`` should be the project root (parent of ``.voss/``).
    Reads all node JSON files under ``.voss/sessions/<root_id>/``.
    Never writes to disk.
    """
    sessions_dir = root / ".voss" / "sessions"
    if not sessions_dir.exists():
        raise AuditLoadError(sessions_dir, "sessions directory does not exist")

    # Find root directories (each is a session tree).
    root_dirs = sorted(
        d for d in sessions_dir.iterdir() if d.is_dir()
    )
    if not root_dirs:
        raise AuditLoadError(sessions_dir, "no session tree directories found")

    # Load the first (or only) tree root.
    tree_dir = root_dirs[0]
    node_files = sorted(tree_dir.glob("*.json"))
    if not node_files:
        raise AuditLoadError(tree_dir, "no node files found")

    raw_nodes: list[dict] = []
    for nf in node_files:
        raw_nodes.append(_read_node_file(nf))

    # Sort deterministically by id.
    raw_nodes.sort(key=lambda d: d["id"])

    root_id = raw_nodes[0].get("root_id", raw_nodes[0]["id"])

    all_cards: list[AuditCard] = []
    all_kills: list[KillRecord] = []
    all_rescopes: list[RescopeRecord] = []
    all_routings: list[RoutingRationale] = []
    all_verdicts: list[ReviewerAssessment] = []
    all_liveness: list[LivenessEvent] = []
    run_final: dict | None = None
    leak6: Leak6Assessment | None = None

    audit_nodes: list[AuditNode] = []

    for data in raw_nodes:
        is_root = data["id"] == root_id
        transitions = data.get("transitions", [])

        card = _build_card(data, is_root=is_root)
        liveness_events = _classify_liveness(data)

        if card is not None:
            all_cards.append(card)
            if card.kill_record:
                all_kills.append(card.kill_record)
            if card.rescope_record:
                all_rescopes.append(card.rescope_record)
            if card.routing:
                all_routings.append(card.routing)
            all_verdicts.extend(card.verdicts)

        all_liveness.extend(liveness_events)

        if is_root:
            run_final = _extract_run_final(transitions)
            leak6 = _extract_leak6(transitions)

        audit_nodes.append(
            AuditNode(
                id=data["id"],
                root_id=data.get("root_id", root_id),
                parent_run_id=data.get("parent_run_id"),
                envelope=data.get("envelope", {}),
                terminal_state=data.get("terminal_state"),
                created_at=data.get("created_at", ""),
                ended_at=data.get("ended_at"),
                transitions=tuple(transitions),
                cards=(card,) if card is not None else (),
                liveness_events=liveness_events,
            )
        )

    if leak6 is None:
        leak6 = Leak6Assessment(
            status="warning",
            evidence="no Leak-6 assessment found",
            mitigation_present=False,
        )

    return AuditSnapshot(
        root_id=root_id,
        nodes=tuple(audit_nodes),
        cards=tuple(all_cards),
        kills=tuple(all_kills),
        rescopes=tuple(all_rescopes),
        routings=tuple(all_routings),
        verdicts=tuple(all_verdicts),
        liveness=tuple(all_liveness),
        leak6=leak6,
        run_final=run_final,
    )
