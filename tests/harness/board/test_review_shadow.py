from __future__ import annotations

import asyncio
import dataclasses
import json
import time
from types import SimpleNamespace

import httpx
import pytest

from tests.harness.board.test_reviewer_integration import _FakeProviderForB
from tests.harness.review_fakes import choice_body, install_jev
from voss.harness import judgments
from voss.harness.board import Board, BoardGateError
from voss.harness.board.machine import write_human_approval
from voss.harness.board.review_shadow import ShadowReviewer
from voss.harness.board.reviewer_b import ReviewerB
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.board.verdict import ReviewerVerdict
from voss.harness.session_tree import SessionTreeManager, SessionTreeNode

from .conftest import build_test_team

CRITERIA = "AC-1: adds foo\nAC-2: logs bar"
DIFF = "+++ b/src/a.py\n+foo\n"
REPO_CONTEXT = "### src/a.py\nfoo"
CONFIDENT = {"supported": 0.99, "contradicted": 0.005, "insufficient_evidence": 0.005}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(judgments.auth, "load_provider_key", lambda env_key: None)


def _enable(root, text="judgments:\n  enabled: true\n  review: shadow\n"):
    path = root / ".voss" / "config.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _answering(overrides=None):
    return lambda request: httpx.Response(200, json=choice_body(request, overrides))


def _recorder(root):
    root.mkdir(parents=True, exist_ok=True)
    node = SessionTreeNode.create_root(cwd=root, limit=1_000_000)
    return SessionTreeManager(node, reserve=0, cwd=root)


def _stub_b(verdict="pass"):
    return DeterministicReviewerStub(conf=0.99, verdict=verdict, source="B", tier="strong")


def _board(manager, cwd, reviewer_b=None):
    stub_a = DeterministicReviewerStub(conf=0.99, verdict="pass", source="A", tier="fast")
    return Board.from_team_config(
        build_test_team(), recorder=manager,
        reviewer_a=stub_a, reviewer_b=reviewer_b or _stub_b(), cwd=cwd,
    )


def _artifact(**overrides):
    fields = {"tests_passed": True, "scope_violations": (), "file_diff": DIFF, "repo_context": REPO_CONTEXT}
    fields.update(overrides)
    return SimpleNamespace(**fields)


async def _to_inreview(board, *, criteria=CRITERIA, artifact=None, risk_tier="low"):
    card = await board.spawn_card(risk_tier=risk_tier)
    card = board.move(card, to="Planned")
    card = board.move(card, to="InProgress")
    card = dataclasses.replace(card, acceptance_criteria=criteria, artifact=artifact or _artifact())
    board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
    return board.move(card, to="InReview")


def _sidecar(manager, cwd):
    return cwd / ".voss" / "sessions" / manager._root.id / "judgments.json"


def _receipts(manager, cwd):
    return json.loads(_sidecar(manager, cwd).read_text())


class _Fixed:
    def __init__(self):
        self.verdict = ReviewerVerdict(conf=0.5, source="B", tier="strong", verdict="fail", notes="", evidence_refs=())
        self.calls = []

    def review(self, card, **kwargs):
        self.calls.append(kwargs)
        return self.verdict


class _Raising:
    def review(self, card, **kwargs):
        raise RuntimeError("inner failed")


class _Untiered:
    def __init__(self):
        self.verdict = _Fixed().verdict

    def review(self, card):
        return self.verdict


def _card():
    return SimpleNamespace(acceptance_criteria=CRITERIA, artifact=_artifact())


async def test_review_off_keeps_the_injected_stub(tmp_recorder):
    manager, cwd = tmp_recorder
    stub = _stub_b()
    board = _board(manager, cwd, stub)
    assert board._reviewer_b is stub


async def test_shadow_wraps_only_reviewer_b(monkeypatch, tmp_recorder):
    manager, cwd = tmp_recorder
    _enable(cwd)
    install_jev(monkeypatch, _answering())
    stub = _stub_b()
    board = _board(manager, cwd, stub)
    assert isinstance(board._reviewer_b, ShadowReviewer)
    assert board._reviewer_b._inner is stub
    assert board._reviewer is stub
    assert isinstance(board._reviewer_a, DeterministicReviewerStub) and board._reviewer_a.source == "A"


async def test_strong_review_returns_the_inner_verdict_object(monkeypatch, tmp_recorder):
    manager, cwd = tmp_recorder
    _enable(cwd)
    seen = install_jev(monkeypatch, _answering())
    inner = _Fixed()
    wrapper = ShadowReviewer(inner, cwd=cwd, manager=manager)
    assert wrapper.review(_card(), tier="strong") is inner.verdict
    assert inner.calls == [{"tier": "strong"}]
    assert len(seen) == 1


async def test_fast_and_untiered_reviews_make_no_requests(monkeypatch, tmp_recorder):
    manager, cwd = tmp_recorder
    _enable(cwd)
    seen = install_jev(monkeypatch, _answering())
    inner = _Fixed()
    wrapper = ShadowReviewer(inner, cwd=cwd, manager=manager)
    assert wrapper.review(_card()) is inner.verdict
    assert wrapper.review(_card(), tier="fast") is inner.verdict
    untiered = _Untiered()
    assert ShadowReviewer(untiered, cwd=cwd, manager=manager).review(_card()) is untiered.verdict
    assert inner.calls == [{}, {"tier": "fast"}]
    assert seen == []
    assert not _sidecar(manager, cwd).exists()


async def test_inner_failure_propagates_without_requests(monkeypatch, tmp_recorder):
    manager, cwd = tmp_recorder
    _enable(cwd)
    seen = install_jev(monkeypatch, _answering())
    wrapper = ShadowReviewer(_Raising(), cwd=cwd, manager=manager)
    with pytest.raises(RuntimeError, match="inner failed"):
        wrapper.review(_card(), tier="strong")
    assert seen == []


async def test_done_review_writes_one_receipt(monkeypatch, tmp_recorder):
    manager, cwd = tmp_recorder
    _enable(cwd)
    seen = install_jev(monkeypatch, _answering())
    board = _board(manager, cwd)
    card = await _to_inreview(board)
    assert seen == []
    assert board.move(card, to="Done").column == "Done"
    assert len(seen) == 1
    data = _receipts(manager, cwd)
    [receipt] = data["receipts"]
    assert receipt["purpose"] == "review.requirements"
    assert receipt["mode"] == "shadow" and receipt["status"] == "answered"
    assert set(receipt["detail"]["labels"]) == {"AC-1", "AC-2"}
    assert receipt["cost_usd"] > 0
    assert data["judgments_cost_usd"] == receipt["cost_usd"]


async def test_second_done_adds_a_receipt_without_double_counting(monkeypatch, tmp_recorder):
    manager, cwd = tmp_recorder
    _enable(cwd)
    install_jev(monkeypatch, _answering())
    board = _board(manager, cwd)
    board.move(await _to_inreview(board), to="Done")
    board.move(await _to_inreview(board), to="Done")
    data = _receipts(manager, cwd)
    assert len(data["receipts"]) == 2
    assert data["judgments_cost_usd"] == pytest.approx(sum(r["cost_usd"] for r in data["receipts"]))


@pytest.mark.parametrize(
    ("response", "reason"),
    [(httpx.Response(500), "unavailable"), (httpx.Response(200, json={"answers": {}}), "invalid_response")],
    ids=["http_500", "invalid_body"],
)
async def test_jev_failure_leaves_the_done_move_unchanged(monkeypatch, tmp_recorder, response, reason):
    manager, cwd = tmp_recorder
    _enable(cwd)
    seen = install_jev(monkeypatch, lambda request: response)
    board = _board(manager, cwd)
    assert board.move(await _to_inreview(board), to="Done").column == "Done"
    assert len(seen) == 1
    [receipt] = _receipts(manager, cwd)["receipts"]
    assert receipt["fallback_reason"] == reason
    assert receipt["detail"]["labels"] == {}


async def test_slow_jev_is_bounded_by_the_client_deadline(monkeypatch, tmp_recorder):
    async def slow(request):
        await asyncio.sleep(2)
        return httpx.Response(200, json=choice_body(request))

    manager, cwd = tmp_recorder
    _enable(cwd)
    install_jev(monkeypatch, slow, timeout_ms=50)
    board = _board(manager, cwd)
    card = await _to_inreview(board)
    start = time.monotonic()
    assert board.move(card, to="Done").column == "Done"
    assert time.monotonic() - start < 1.5
    [receipt] = _receipts(manager, cwd)["receipts"]
    assert receipt["fallback_reason"] == "timeout"


async def test_empty_criteria_records_no_criteria_without_requests(monkeypatch, tmp_recorder):
    manager, cwd = tmp_recorder
    _enable(cwd)
    seen = install_jev(monkeypatch, _answering())
    board = _board(manager, cwd)
    assert board.move(await _to_inreview(board, criteria=""), to="Done").column == "Done"
    assert seen == []
    [receipt] = _receipts(manager, cwd)["receipts"]
    assert receipt["fallback_reason"] == "no_criteria"


@pytest.mark.parametrize("repo_context", [REPO_CONTEXT, None], ids=["artifact_context", "no_context"])
async def test_packet_code_comes_from_the_artifact_only(monkeypatch, tmp_recorder, repo_context):
    manager, cwd = tmp_recorder
    (cwd / "src").mkdir()
    (cwd / "src" / "a.py").write_text("ON DISK ONLY\n")
    _enable(cwd)
    seen = install_jev(monkeypatch, _answering())
    board = _board(manager, cwd)
    artifact = _artifact() if repo_context else SimpleNamespace(tests_passed=True, scope_violations=(), file_diff=DIFF)
    board.move(await _to_inreview(board, artifact=artifact), to="Done")
    state = json.loads(seen[0].content)["state"]
    assert state["code"] == (repo_context or "")
    assert state["diff"] == DIFF
    assert "ON DISK ONLY" not in seen[0].content.decode()


def _strip(transitions):
    return [{k: v for k, v in t.items() if k != "at"} for t in transitions]


async def _scenario(root, reviewer_b):
    manager = _recorder(root)
    board = _board(manager, root, reviewer_b)
    done = await _to_inreview(board)
    board.move(done, to="Done")
    refused = await _to_inreview(board, artifact=_artifact(tests_passed=False))
    with pytest.raises(BoardGateError):
        board.move(refused, to="Done")
    session = root / ".voss" / "sessions" / manager._root.id
    ids = [c.node_id for c in board.cards()]
    transitions = [_strip(manager.get_node(i).transitions) for i in ids]
    reviews = [
        json.loads((session / f"{i}.review.json").read_text()) if (session / f"{i}.review.json").exists() else None
        for i in ids
    ]
    return transitions, reviews, [c.column for c in board.cards()]


def _real_b(root):
    return ReviewerB(provider=_FakeProviderForB(conf=0.99, verdict="pass"), fast_model="test-model", strong_model="test-model", cwd=root)


@pytest.mark.parametrize("make_b", [lambda root: _stub_b(), _real_b], ids=["stub", "real_b"])
async def test_identical_transitions(monkeypatch, tmp_path, make_b):
    seen = install_jev(monkeypatch, _answering())
    off_root, shadow_root = tmp_path / "off", tmp_path / "shadow"
    off = await _scenario(off_root, make_b(off_root))
    assert seen == []
    _enable(shadow_root)
    shadow = await _scenario(shadow_root, make_b(shadow_root))
    assert len(seen) == 2
    assert off == shadow
    assert off[2] == ["Done", "InReview"]
    assert off[1][0]["final_outcome"] == "Done"


CASES = {
    "tests_failed": {"artifact": {"tests_passed": False}},
    "scope_violation": {"artifact": {"scope_violations": ("leak",)}},
    "human_missing": {"risk_tier": "critical"},
    "b_fail": {"verdict": "fail"},
    "b_block": {"verdict": "block"},
}


async def _attempt_done(root, case):
    manager = _recorder(root)
    board = _board(manager, root, _stub_b(case.get("verdict", "pass")))
    card = await _to_inreview(board, artifact=_artifact(**case.get("artifact", {})), risk_tier=case.get("risk_tier", "low"))
    try:
        outcome = ("moved", board.move(card, to="Done").column)
    except BoardGateError as err:
        outcome = ("refused", err.failing_clauses)
    final = next(c for c in board.cards() if c.node_id == card.node_id).column
    return outcome, final, _strip(manager.get_node(card.node_id).transitions)


@pytest.mark.parametrize("name", list(CASES))
async def test_no_path_to_approval(monkeypatch, tmp_path, name):
    seen = install_jev(monkeypatch, _answering({"AC-1": CONFIDENT, "AC-2": CONFIDENT}))
    off = await _attempt_done(tmp_path / "off", CASES[name])
    _enable(tmp_path / "shadow")
    shadow = await _attempt_done(tmp_path / "shadow", CASES[name])
    assert shadow == off
    assert shadow[1] != "Done"
    assert len(seen) == (0 if name == "human_missing" else 1)


async def test_human_approval_still_gates_a_supported_card(monkeypatch, tmp_recorder):
    manager, cwd = tmp_recorder
    _enable(cwd)
    install_jev(monkeypatch, _answering({"AC-1": CONFIDENT, "AC-2": CONFIDENT}))
    board = _board(manager, cwd)
    card = await _to_inreview(board, risk_tier="critical")
    write_human_approval(cwd, manager._root.id, card.node_id, decision="approved", note="ok")
    assert board.move(card, to="Done").column == "Done"


ZERO_CASES = ["review_off", "not_enabled", "no_key", "killed_before_build", "killed_after_build"]


@pytest.mark.parametrize("case", ZERO_CASES)
async def test_zero_calls(monkeypatch, tmp_recorder, case):
    manager, cwd = tmp_recorder
    seen = install_jev(monkeypatch, _answering())
    if case == "review_off":
        _enable(cwd, "judgments:\n  enabled: true\n  review: off\n")
    elif case == "not_enabled":
        _enable(cwd, "judgments:\n  enabled: false\n  review: shadow\n")
    else:
        _enable(cwd)
    if case == "no_key":
        monkeypatch.delenv("TYPESAFE_API_KEY")
    if case == "killed_before_build":
        monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    board = _board(manager, cwd)
    assert isinstance(board._reviewer_b, ShadowReviewer) == (case == "killed_after_build")
    card = await _to_inreview(board)
    if case == "killed_after_build":
        monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    assert board.move(card, to="Done").column == "Done"
    assert seen == []
    assert not _sidecar(manager, cwd).exists()
