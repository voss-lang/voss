"""Review sidecar persistence (VREV-09).

Writes a per-card ``<node_id>.review.json`` next to the session-tree node file,
mirroring ``session_tree._write_node_file`` (0o600, JSON). Captures Reviewer-A's
verification, Reviewer-B's full verdict, and the final card outcome so a run's
review is durable and re-readable by ``voss review`` (V6-04).

Stdlib-only imports — type hints are strings to avoid a board import cycle.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .gates import GateContext
    from .machine import Card
    from voss.harness.session_tree import SessionTreeManager


def _write_review_sidecar(
    card: "Card",
    ctx: "GateContext",
    *,
    outcome: str,  # "Done" | "Blocked"
    cwd: Path,
    manager: "SessionTreeManager",
) -> Optional[Path]:
    """Write ``<node_id>.review.json`` (0o600) under the card's session root.

    Payload keys: ``a_verification`` (A's authored check, or None), ``b_verdict``
    (B's full verdict dict, or None), ``final_outcome`` (the terminal column).
    Returns the written path, or None if the node is missing (defensive).
    """
    node = manager.get_node(card.node_id)
    if node is None:
        return None

    verdict_a = ctx.verdict_a
    verdict_b = ctx.verdict_b

    a_payload = None
    if verdict_a is not None:
        a_payload = {
            "test_path_or_rubric": (
                verdict_a.evidence_refs[0] if verdict_a.evidence_refs else None
            ),
            "result": verdict_a.verdict,
            "notes": verdict_a.notes,
        }

    payload = {
        "a_verification": a_payload,
        "b_verdict": dataclasses.asdict(verdict_b) if verdict_b is not None else None,
        "final_outcome": outcome,
    }

    path = cwd / ".voss" / "sessions" / node.root_id / f"{card.node_id}.review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    path.chmod(0o600)
    return path
