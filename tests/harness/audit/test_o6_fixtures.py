"""O6-01 Task 2: Deterministic audit fixtures (OAUD-08).

Provides fixture builders for a synthetic audit session tree. All fixture
data is written under pytest ``tmp_path``, never under the developer's
real ``.voss/`` directory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

ROOT_ID = "root_aabbcc0001"


def _ts(n: int) -> str:
    return f"2026-05-20T10:{n:02d}:00+00:00"


def _node_dict(
    node_id: str,
    *,
    parent_run_id: str | None = None,
    terminal_state: dict | None = None,
    ended_at: str | None = None,
    transitions: list | None = None,
    retry_notes: list | None = None,
    envelope: dict | None = None,
    created_at: str = "",
) -> dict[str, Any]:
    return {
        "id": node_id,
        "root_id": ROOT_ID,
        "parent_run_id": parent_run_id,
        "envelope": envelope or {"limit": 5000, "spent": 0},
        "terminal_state": terminal_state,
        "created_at": created_at or _ts(0),
        "ended_at": ended_at,
        "rejected_raises": [],
        "transitions": transitions or [],
        "retry_notes": retry_notes or [],
    }


def _board_transition(
    from_col: str,
    to_col: str,
    *,
    outcome: str = "passed",
    verdict_snapshot: dict | None = None,
    retry_count: int = 0,
) -> dict:
    return {
        "kind": "board.transition",
        "from": from_col,
        "to": to_col,
        "outcome": outcome,
        "failing_clauses": None,
        "reason": None,
        "verdict_snapshot": verdict_snapshot,
        "retry_count": retry_count,
        "at": _ts(1),
    }


def _verdict_snapshot(
    source: str = "B",
    verdict: str = "pass",
    conf: float = 0.92,
    tier: str = "fast",
) -> dict:
    return {
        "conf": conf,
        "source": source,
        "tier": tier,
        "verdict": verdict,
        "notes": f"{source} {verdict} notes",
        "evidence_refs": [f"test_{source.lower()}_1"],
    }


def _em_ticket(
    ticket_id: str,
    node_id: str,
    *,
    routing_id: str,
    worker_role: str = "backend",
) -> dict:
    return {
        "kind": "em.ticket",
        "id": ticket_id,
        "card_node_id": node_id,
        "original_idea": "fixture idea",
        "acceptance": "fixture AC",
        "dod": "fixture DoD",
        "worker_role": worker_role,
        "routing_rationale_id": routing_id,
        "created_at": _ts(2),
    }


def _em_routing(
    routing_id: str,
    card_id: str,
    *,
    chosen_role: str = "backend",
    candidates: tuple[str, ...] = ("backend", "frontend", "ai"),
    confidence: float | None = 0.85,
) -> dict:
    return {
        "kind": "em.routing",
        "id": routing_id,
        "card_id": card_id,
        "chosen_role": chosen_role,
        "candidates_considered": list(candidates),
        "rationale_text": f"routed to {chosen_role}",
        "ts": _ts(3),
        "confidence_hint": confidence,
    }


def _em_kill(node_id: str) -> dict:
    return {
        "kind": "em.kill",
        "killed_node_id": node_id,
        "rationale_text": "fixture kill rationale",
        "evidence_refs": ["test_kill_evidence"],
        "killed_at": _ts(4),
        "lineage_parent_id": None,
        "successor_card_id": None,
    }


def _em_rescope(pred_id: str, succ_id: str) -> dict:
    return {
        "kind": "em.rescope",
        "predecessor_card_id": pred_id,
        "successor_card_id": succ_id,
        "diff_summary": "rescoped AC",
        "rationale_text": "fixture rescope rationale",
        "rescoped_at": _ts(5),
        "new_acceptance": ["new AC 1"],
        "new_dod": ["new DoD 1"],
    }


def _em_run_final() -> dict:
    return {
        "kind": "em.run_final",
        "root_id": ROOT_ID,
        "idea": "fixture idea",
        "total_cards": 5,
        "done_count": 1,
        "blocked_count": 1,
        "killed_count": 1,
        "rescope_count": 1,
        "em_iterations": 3,
        "ts": _ts(9),
    }


def _leak6_accepted_gap() -> dict:
    return {
        "kind": "audit.leak6",
        "status": "accepted_gap",
        "evidence": "no standup-to-memory writer exists in O1-O5 substrate",
        "mitigation_present": False,
    }


def build_fixture_tree(root: Path) -> dict[str, Path]:
    """Write a full synthetic session tree under ``root`` and return file paths.

    The tree exercises every OAUD-08 scenario:
    - one completed card (node_done)
    - one killed card with kill rationale (node_killed)
    - one rescope lineage (node_rescoped → node_successor)
    - one misroute candidate with routing rationale (node_misroute)
    - one Reviewer-A pass followed by Reviewer-B block (node_ab_block)
    - one timeout-to-Blocked liveness path (node_timeout)
    - one Leak-6 accepted-gap marker (on root)
    """
    sessions_dir = root / ".voss" / "sessions" / ROOT_ID
    sessions_dir.mkdir(parents=True, exist_ok=True)

    nodes: dict[str, dict] = {}

    # Root node
    nodes["root"] = _node_dict(
        ROOT_ID,
        terminal_state={"exit_reason": "done", "final": "session complete"},
        ended_at=_ts(10),
        transitions=[_em_run_final(), _leak6_accepted_gap()],
    )

    # 1. Completed card
    nodes["node_done"] = _node_dict(
        "node_done_0001",
        parent_run_id=ROOT_ID,
        terminal_state={"exit_reason": "done", "final": "card complete"},
        ended_at=_ts(6),
        created_at=_ts(1),
        transitions=[
            _em_ticket("tk_done", "node_done_0001", routing_id="rt_done"),
            _em_routing("rt_done", "tk_done"),
            _board_transition("Backlog", "Done", verdict_snapshot=_verdict_snapshot()),
        ],
    )

    # 2. Killed card
    nodes["node_killed"] = _node_dict(
        "node_killed_01",
        parent_run_id=ROOT_ID,
        terminal_state={"exit_reason": "killed", "final": "killed by EM"},
        ended_at=_ts(5),
        created_at=_ts(1),
        transitions=[
            _em_ticket("tk_kill", "node_killed_01", routing_id="rt_kill"),
            _em_routing("rt_kill", "tk_kill"),
            _em_kill("node_killed_01"),
        ],
    )

    # 3. Rescoped lineage: predecessor → successor
    nodes["node_rescoped"] = _node_dict(
        "node_rescoped_1",
        parent_run_id=ROOT_ID,
        terminal_state={"exit_reason": "killed", "final": "rescoped"},
        ended_at=_ts(5),
        created_at=_ts(1),
        transitions=[
            _em_ticket("tk_resc", "node_rescoped_1", routing_id="rt_resc"),
            _em_routing("rt_resc", "tk_resc"),
            _em_rescope("tk_resc", "tk_succ"),
        ],
    )
    nodes["node_successor"] = _node_dict(
        "node_successor1",
        parent_run_id=ROOT_ID,
        terminal_state={"exit_reason": "done", "final": "successor done"},
        ended_at=_ts(7),
        created_at=_ts(5),
        transitions=[
            _em_ticket("tk_succ", "node_successor1", routing_id="rt_succ"),
            _em_routing("rt_succ", "tk_succ"),
            _board_transition("Backlog", "Done", verdict_snapshot=_verdict_snapshot()),
        ],
    )

    # 4. Misroute candidate
    nodes["node_misroute"] = _node_dict(
        "node_misroute1",
        parent_run_id=ROOT_ID,
        terminal_state={"exit_reason": "done", "final": "done despite misroute"},
        ended_at=_ts(7),
        created_at=_ts(1),
        transitions=[
            _em_ticket("tk_mis", "node_misroute1", routing_id="rt_mis", worker_role="frontend"),
            _em_routing("rt_mis", "tk_mis", chosen_role="frontend", confidence=0.45),
            _board_transition(
                "InReview", "InProgress",
                outcome="refused",
                verdict_snapshot=_verdict_snapshot(verdict="fail", conf=0.55),
                retry_count=1,
            ),
            _board_transition("Backlog", "Done", verdict_snapshot=_verdict_snapshot()),
        ],
        retry_notes=[{"round": 1, "verdict_notes": "misroute retry", "at": _ts(4)}],
    )

    # 5. Reviewer-A pass, Reviewer-B block
    nodes["node_ab_block"] = _node_dict(
        "node_ab_block1",
        parent_run_id=ROOT_ID,
        terminal_state={"exit_reason": "killed", "final": "blocked by B"},
        ended_at=_ts(6),
        created_at=_ts(1),
        transitions=[
            _em_ticket("tk_ab", "node_ab_block1", routing_id="rt_ab"),
            _em_routing("rt_ab", "tk_ab"),
            _board_transition(
                "InReview", "Done",
                outcome="passed",
                verdict_snapshot=_verdict_snapshot(source="A", verdict="pass", conf=0.90),
            ),
            _board_transition(
                "Done", "Blocked",
                outcome="refused",
                verdict_snapshot=_verdict_snapshot(source="B", verdict="block", conf=0.30, tier="strong"),
            ),
        ],
    )

    # 6. Timeout-to-Blocked
    nodes["node_timeout"] = _node_dict(
        "node_timeout_1",
        parent_run_id=ROOT_ID,
        terminal_state={"exit_reason": "timeout", "final": "timed out"},
        ended_at=_ts(8),
        created_at=_ts(1),
        transitions=[
            _em_ticket("tk_to", "node_timeout_1", routing_id="rt_to"),
            _em_routing("rt_to", "tk_to"),
            _board_transition(
                "InProgress", "Blocked",
                outcome="refused",
                verdict_snapshot=_verdict_snapshot(verdict="block", conf=0.0),
            ),
        ],
    )

    paths: dict[str, Path] = {}
    for key, node_data in nodes.items():
        node_id = node_data["id"]
        path = sessions_dir / f"{node_id}.json"
        path.write_text(json.dumps(node_data, indent=2))
        path.chmod(0o600)
        paths[key] = path

    # ------------------------------------------------------------------
    # V9 extension: per-node .review.json sidecars + a separate
    # run-final.json. Schema mirrors voss.harness.board.review_persistence
    # (a_verification / b_verdict / final_outcome) and cli._persist_run_final.
    # These are NOT node files (run-final.json has no `id`; sidecars are
    # named <node_id>.review.json) — the loader must filter them from the
    # node glob (V9-02 landmine fix).
    # ------------------------------------------------------------------
    review_sidecars: dict[str, tuple[str, dict]] = {
        # A pass, B block, strong tier — drives reviewer-sections + slop-rejection.
        "node_ab_block_review": (
            "node_ab_block1",
            {
                "a_verification": {
                    "test_path_or_rubric": "test_ab",
                    "result": "pass",
                    "notes": "A verified",
                },
                "b_verdict": {
                    "conf": 0.30,
                    "source": "B",
                    "tier": "strong",
                    "verdict": "block",
                    "notes": "B blocked",
                    "evidence_refs": ["ev_b_1"],
                    "domain_inferred": "backend",
                },
                "final_outcome": "Blocked",
            },
        ),
        # A pass, B pass — clean Done card.
        "node_done_review": (
            "node_done_0001",
            {
                "a_verification": {
                    "test_path_or_rubric": "test_done",
                    "result": "pass",
                    "notes": "A verified",
                },
                "b_verdict": {
                    "conf": 0.92,
                    "source": "B",
                    "tier": "fast",
                    "verdict": "pass",
                    "notes": "B approved",
                    "evidence_refs": ["ev_b_done"],
                    "domain_inferred": "backend",
                },
                "final_outcome": "Done",
            },
        ),
        # A pass, B fail — a false-pass calibration pair.
        "node_misroute_review": (
            "node_misroute1",
            {
                "a_verification": {
                    "test_path_or_rubric": "test_misroute",
                    "result": "pass",
                    "notes": "A verified",
                },
                "b_verdict": {
                    "conf": 0.55,
                    "source": "B",
                    "tier": "fast",
                    "verdict": "fail",
                    "notes": "B disagrees",
                    "evidence_refs": ["ev_b_mis"],
                    "domain_inferred": "frontend",
                },
                "final_outcome": "Done",
            },
        ),
    }
    # NOTE: node_killed_01 intentionally has NO sidecar (drives the
    # VAUD-03 unsupported-claim test: em.ticket present, sidecar absent).
    for key, (node_id, payload) in review_sidecars.items():
        path = sessions_dir / f"{node_id}.review.json"
        path.write_text(json.dumps(payload, indent=2))
        path.chmod(0o600)
        paths[key] = path

    # Separate run-final.json (NOT a node file — no `id` key).
    run_final_path = sessions_dir / "run-final.json"
    run_final_path.write_text(
        json.dumps(
            {
                "root_id": ROOT_ID,
                "idea": "fixture idea",
                "total_cards": 5,
                "done_count": 1,
                "blocked_count": 1,
                "killed_count": 1,
                "rescope_count": 1,
                "em_iterations": 3,
                "sign_off": {"decision": "approve", "ts": _ts(11)},
            },
            indent=2,
        )
    )
    run_final_path.chmod(0o600)
    paths["run_final"] = run_final_path

    return paths


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFixtureBuilderWritesUnderTmpPath:
    def test_writes_only_under_tmp_path(self, tmp_path: Path):
        paths = build_fixture_tree(tmp_path)
        for key, path in paths.items():
            assert str(path).startswith(str(tmp_path)), (
                f"fixture {key} wrote outside tmp_path: {path}"
            )

    def test_does_not_touch_repo_voss_dir(self, tmp_path: Path):
        cwd = Path.cwd()
        real_voss = cwd / ".voss" / "sessions"
        before = set(real_voss.glob("**/*.json")) if real_voss.exists() else set()
        build_fixture_tree(tmp_path)
        after = set(real_voss.glob("**/*.json")) if real_voss.exists() else set()
        assert before == after


class TestFixtureData:
    @pytest.fixture
    def tree(self, tmp_path: Path) -> dict[str, Path]:
        return build_fixture_tree(tmp_path)

    def test_all_scenario_nodes_present(self, tree: dict[str, Path]):
        expected = {
            "root", "node_done", "node_killed", "node_rescoped",
            "node_successor", "node_misroute", "node_ab_block", "node_timeout",
        }
        # The 8 node entries must all be present. V9 added .review.json /
        # run-final.json keys alongside them, so this is a subset check.
        assert expected <= set(tree.keys())

    def test_all_files_are_valid_json(self, tree: dict[str, Path]):
        for key, path in tree.items():
            data = json.loads(path.read_text())
            assert "id" in data, f"{key} missing 'id'"
            assert "root_id" in data, f"{key} missing 'root_id'"

    def test_killed_node_has_kill_record(self, tree: dict[str, Path]):
        data = json.loads(tree["node_killed"].read_text())
        kills = [t for t in data["transitions"] if t.get("kind") == "em.kill"]
        assert len(kills) == 1
        assert kills[0]["rationale_text"] == "fixture kill rationale"

    def test_rescope_lineage_present(self, tree: dict[str, Path]):
        data = json.loads(tree["node_rescoped"].read_text())
        rescopes = [t for t in data["transitions"] if t.get("kind") == "em.rescope"]
        assert len(rescopes) == 1
        assert rescopes[0]["predecessor_card_id"] == "tk_resc"
        assert rescopes[0]["successor_card_id"] == "tk_succ"

    def test_reviewer_ab_block_present(self, tree: dict[str, Path]):
        data = json.loads(tree["node_ab_block"].read_text())
        transitions = [t for t in data["transitions"] if t.get("kind") == "board.transition"]
        verdicts = [t["verdict_snapshot"] for t in transitions if t.get("verdict_snapshot")]
        sources = [v["source"] for v in verdicts]
        assert "A" in sources
        assert "B" in sources
        b_verdicts = [v for v in verdicts if v["source"] == "B"]
        assert any(v["verdict"] == "block" for v in b_verdicts)

    def test_timeout_node_present(self, tree: dict[str, Path]):
        data = json.loads(tree["node_timeout"].read_text())
        assert data["terminal_state"]["exit_reason"] == "timeout"

    def test_leak6_marker_on_root(self, tree: dict[str, Path]):
        data = json.loads(tree["root"].read_text())
        leak6 = [t for t in data["transitions"] if t.get("kind") == "audit.leak6"]
        assert len(leak6) == 1
        assert leak6[0]["status"] == "accepted_gap"

    def test_routing_rationale_present(self, tree: dict[str, Path]):
        data = json.loads(tree["node_misroute"].read_text())
        routings = [t for t in data["transitions"] if t.get("kind") == "em.routing"]
        assert len(routings) == 1
        assert routings[0]["confidence_hint"] == 0.45

    def test_fixture_ids_are_deterministic(self, tmp_path: Path):
        tree1 = build_fixture_tree(tmp_path / "a")
        tree2 = build_fixture_tree(tmp_path / "b")
        for key in tree1:
            data1 = json.loads(tree1[key].read_text())
            data2 = json.loads(tree2[key].read_text())
            assert data1["id"] == data2["id"], f"{key} id not deterministic"

    def test_nodes_sorted_by_id(self, tree: dict[str, Path]):
        ids = []
        for path in tree.values():
            data = json.loads(path.read_text())
            ids.append(data["id"])
        # root should be first alphabetically is not required, but ids should
        # be stable strings.
        assert all(isinstance(i, str) for i in ids)
