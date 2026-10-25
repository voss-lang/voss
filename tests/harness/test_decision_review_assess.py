from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import re

import httpx
import pytest

from tests.harness.review_fakes import SUPPORTED, choice_body, install_jev
from tests.harness.test_decision_review_packet import _git
from voss.harness import decision_review as dr
from voss_runtime.judgments import USD_PER_INPUT_TOKEN, ChoiceResult, JudgmentError, JudgmentLedger

SENTINEL = "SENTINEL-j403"
FOUR = "AC-1: adds foo\nAC-2: adds bar\nAC-3: logs errors\nAC-4: documents it"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))


def _ledger() -> JudgmentLedger:
    return JudgmentLedger(4, 0.01)


def _packet(criteria=FOUR, **overrides) -> dr.EvidencePacket:
    args = {
        "diff": "+++ b/a.py\n+foo\n",
        "code": "### a.py\nfoo",
        "checks": [dr.CheckResult("tests", "passed")],
        "candidate": {"kind": "working_tree", "touched_paths": ["a.py"], "tree_digest": "0" * 16},
    }
    args.update(overrides)
    return dr.build_packet(criteria, **args)


def _answering(overrides=None):
    return lambda request: httpx.Response(200, json=choice_body(request, overrides))


MIXED = {
    "AC-1": {"supported": 0.85, "contradicted": 0.1, "insufficient_evidence": 0.05},
    "AC-2": {"supported": 0.05, "contradicted": 0.9, "insufficient_evidence": 0.05},
    "AC-3": {"supported": 0.05, "contradicted": 0.05, "insufficient_evidence": 0.9},
    "AC-4": {"supported": 0.79, "contradicted": 0.11, "insufficient_evidence": 0.1},
}
BAD_SUM = {"supported": 0.25, "contradicted": 0.25, "insufficient_evidence": 0.0}


@pytest.mark.parametrize("mode", ["shadow", "explicit"])
async def test_labels_follow_probabilities_and_the_threshold(monkeypatch, mode):
    seen = install_jev(monkeypatch, _answering(MIXED))
    packet = _packet()
    ledger = _ledger()
    receipt = await dr.assess(packet, mode=mode, ledger=ledger)
    assert len(seen) == 1
    questions = json.loads(seen[0].content)["questions"]
    assert list(questions) == ["AC-1", "AC-2", "AC-3", "AC-4"]
    assert {q["type"] for q in questions.values()} == {"choice"}
    assert receipt.detail["labels"] == {"AC-1": "supported", "AC-2": "contradicted", "AC-3": "abstained", "AC-4": "abstained"}
    assert list(receipt.answers) == receipt.detail["criterion_ids"] == ["AC-1", "AC-2", "AC-3", "AC-4"]
    assert receipt.purpose == "review.requirements"
    assert receipt.rubric_version == "review.requirements.v2"
    assert receipt.artifact_revision == packet.packet_id == receipt.detail["packet_id"]
    assert receipt.mode == mode
    assert receipt.status == "answered" and receipt.fallback_reason is None
    assert ledger.receipts == [receipt]


def test_label_for_reads_probabilities_only():
    answer = ChoiceResult("supported", {"supported": 0.5, "contradicted": 0.3, "insufficient_evidence": 0.2}, 0.99)
    assert dr.label_for(answer, dr.THRESHOLD) == "abstained"
    assert dr.label_for(ChoiceResult("contradicted", SUPPORTED, 0.1), dr.THRESHOLD) == "supported"
    with pytest.raises(AssertionError):
        dr.label_for(answer, 0.5)


async def test_one_malformed_answer_shows_no_answer_and_keeps_the_rest(monkeypatch):
    install_jev(monkeypatch, _answering({"AC-2": BAD_SUM}))
    receipt = await dr.assess(_packet("AC-1: a\nAC-2: b\nAC-3: c"), mode="shadow", ledger=_ledger())
    assert receipt.status == "answered"
    assert receipt.detail["labels"] == {"AC-1": "supported", "AC-2": "no_answer", "AC-3": "supported"}
    assert list(receipt.answers) == ["AC-1", "AC-3"]


async def test_wholly_invalid_response_shadow_records_why(monkeypatch):
    install_jev(monkeypatch, _answering({f"AC-{i}": BAD_SUM for i in range(1, 5)}))
    receipt = await dr.assess(_packet(), mode="shadow", ledger=_ledger())
    assert receipt.status == "invalid_response"
    assert receipt.fallback_reason == "invalid_response"
    assert receipt.detail["labels"] == {}
    assert receipt.answers == {}


async def test_wholly_invalid_response_explicit_raises_after_recording(monkeypatch):
    install_jev(monkeypatch, _answering({f"AC-{i}": {"type": "choice"} for i in range(1, 5)}))
    ledger = _ledger()
    with pytest.raises(JudgmentError) as err:
        await dr.assess(_packet(), mode="explicit", ledger=ledger)
    assert err.value.outcome == "invalid_response"
    [receipt] = ledger.receipts
    assert receipt.status == "invalid_response" and receipt.mode == "explicit"
    assert receipt.detail["labels"] == {}


@pytest.mark.parametrize(
    ("setup", "reason", "status", "outcome"),
    [
        ("killed", "disabled", "disabled", "disabled"),
        ("no_key", "no_key", "unavailable", "unavailable"),
        ("oversize", "oversize", "unavailable", "budget_exhausted"),
    ],
)
@pytest.mark.parametrize("mode", ["shadow", "explicit"])
async def test_pre_request_fallbacks_make_zero_requests(monkeypatch, setup, reason, status, outcome, mode):
    seen = install_jev(monkeypatch, _answering())
    packet = _packet()
    if setup == "killed":
        monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    elif setup == "no_key":
        monkeypatch.delenv("TYPESAFE_API_KEY")
    else:
        packet = _packet(["requirement " + "z" * 30000])
    ledger = _ledger()
    if mode == "explicit":
        with pytest.raises(JudgmentError) as err:
            await dr.assess(packet, mode=mode, ledger=ledger)
        assert err.value.outcome == outcome
        [receipt] = ledger.receipts
    else:
        receipt = await dr.assess(packet, mode=mode, ledger=ledger)
        assert ledger.receipts == [receipt]
    assert seen == []
    assert (receipt.fallback_reason, receipt.status, receipt.mode) == (reason, status, mode)
    assert receipt.attempts == 0 and receipt.answers == {}
    assert receipt.artifact_revision == packet.packet_id
    assert receipt.detail["labels"] == {}


async def test_no_criteria_makes_zero_requests(monkeypatch):
    seen = install_jev(monkeypatch, _answering())
    packet = _packet([])
    receipt = await dr.assess(packet, mode="shadow", ledger=_ledger())
    assert receipt.fallback_reason == "no_criteria"
    ledger = _ledger()
    with pytest.raises(ValueError):
        await dr.assess(packet, mode="explicit", ledger=ledger)
    assert ledger.receipts[0].fallback_reason == "no_criteria"
    assert seen == []


async def test_shadow_timeout_is_recorded_without_raising(monkeypatch):
    async def slow(request):
        await asyncio.sleep(2)
        return httpx.Response(200, json=choice_body(request))

    install_jev(monkeypatch, slow, timeout_ms=50)
    receipt = await dr.assess(_packet(), mode="shadow", ledger=_ledger())
    assert receipt.fallback_reason == "timeout"
    assert receipt.status == "unavailable"
    assert receipt.detail["labels"] == {}


async def test_detail_is_content_free(monkeypatch):
    install_jev(monkeypatch, _answering())
    checks = [dr.CheckResult(f"{SENTINEL}-{s}", s) for s in dr.CHECK_STATUSES] + [dr.CheckResult("unit", "passed")]
    packet = _packet(
        f"AC-1: {SENTINEL} adds foo\nAC-2: adds bar",
        diff=f"+++ b/a.py\n+{SENTINEL}\n",
        code=f"### a.py\n{SENTINEL}",
        checks=checks,
        verification_note=SENTINEL,
    )
    receipt = await dr.assess(packet, mode="shadow", ledger=_ledger())
    assert set(receipt.detail) == {"packet_id", "criterion_ids", "labels", "threshold", "trimmed", "request_bytes", "candidate", "checks"}
    assert receipt.detail["checks"] == {"passed": 2, "failed": 1, "skipped": 1, "not_run": 1, "stale": 1}
    assert receipt.detail["threshold"] == 0.80
    assert receipt.detail["trimmed"] == {"code": False, "diff": False}
    assert receipt.detail["request_bytes"] > 0
    assert receipt.detail["candidate"] == packet.candidate
    assert SENTINEL not in json.dumps(asdict(receipt))


async def test_ledger_cost_is_settled_once_from_usage(monkeypatch):
    install_jev(monkeypatch, _answering())
    ledger = _ledger()
    await dr.assess(_packet(), mode="explicit", ledger=ledger)
    assert len(ledger.receipts) == 1
    assert ledger.observed_usd == pytest.approx(100 * USD_PER_INPUT_TOKEN)
    assert ledger.receipts[0].cost_usd == pytest.approx(100 * USD_PER_INPUT_TOKEN)
    assert ledger.held_usd == 0


async def _value(x):
    return x


def test_run_sync_without_a_running_loop():
    assert dr.run_sync(_value(7)) == 7


async def test_run_sync_inside_a_running_loop():
    assert dr.run_sync(_value(8)) == 8


@pytest.mark.parametrize("in_loop", [False, True])
async def test_run_sync_propagates_coroutine_errors_and_runs_once(in_loop):
    runs = []

    async def boom():
        runs.append(1)
        raise RuntimeError("boom")

    def call():
        with pytest.raises(RuntimeError, match="boom"):
            dr.run_sync(boom())

    if in_loop:
        call()
    else:
        await asyncio.to_thread(call)
    assert runs == [1]


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "edit.py").write_text("value = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


async def test_assess_candidate_working_tree(monkeypatch, repo):
    seen = install_jev(monkeypatch, _answering())
    (repo / "edit.py").write_text("value = 2\n")
    (repo / "new_mod.py").write_text("bar = 1\n")
    ledger = _ledger()
    receipt = await dr.assess_candidate(cwd=repo, criteria="AC-1: adds foo\nAC-2: adds bar", ledger=ledger)
    assert len(seen) == 1
    state = json.loads(seen[0].content)["state"]
    assert "+++ b/new_mod.py" in state["diff"]
    candidate = receipt.detail["candidate"]
    assert candidate["kind"] == "working_tree"
    assert candidate["touched_paths"] == ["edit.py", "new_mod.py"]
    assert re.fullmatch(r"[0-9a-f]{16}", candidate["tree_digest"])
    assert receipt.mode == "explicit" and ledger.receipts == [receipt]


@pytest.mark.parametrize("worktree", ["repo", "missing"])
async def test_assess_candidate_commit(monkeypatch, repo, tmp_path, worktree):
    install_jev(monkeypatch, _answering())
    (repo / "edit.py").write_text("value = 'foo'\n")
    _git(repo, "commit", "-q", "-am", "foo")
    sha = _git(repo, "rev-parse", "HEAD")
    path = repo if worktree == "repo" else tmp_path / "gone"
    receipt = await dr.assess_candidate(cwd=repo, criteria="adds foo", head=sha, worktree=path, ledger=_ledger())
    assert receipt.detail["candidate"] == {"kind": "commit", "head": sha, "touched_paths": ["edit.py"]}


async def test_assess_candidate_shadow_records_failure_and_explicit_raises(monkeypatch, repo):
    install_jev(monkeypatch, lambda request: httpx.Response(500))
    (repo / "edit.py").write_text("value = 2\n")
    receipt = await dr.assess_candidate(cwd=repo, criteria="adds foo", ledger=_ledger(), mode="shadow")
    assert (receipt.status, receipt.fallback_reason, receipt.mode) == ("unavailable", "unavailable", "shadow")
    ledger = _ledger()
    with pytest.raises(JudgmentError):
        await dr.assess_candidate(cwd=repo, criteria="adds foo", ledger=ledger)
    assert ledger.receipts[0].mode == "explicit"


def test_candidate_review_path(tmp_path):
    assert dr.candidate_review_path(tmp_path, "s1", "t1") == tmp_path / ".voss" / "swarm" / "s1" / "reviews" / "t1.json"
    for bad in ("../x", "a/b", "", "a..b"):
        with pytest.raises(ValueError):
            dr.candidate_review_path(tmp_path, bad, "t1")
        with pytest.raises(ValueError):
            dr.candidate_review_path(tmp_path, "s1", bad)


async def test_write_candidate_review_writes_one_fresh_ledger(monkeypatch, tmp_path):
    install_jev(monkeypatch, _answering())
    path = dr.candidate_review_path(tmp_path, "s1", "t1")
    assert dr.write_candidate_review(path, _ledger()) is None
    assert not path.exists()
    first = _ledger()
    await dr.assess(_packet(), mode="shadow", ledger=first)
    assert dr.write_candidate_review(path, first) == path
    data = json.loads(path.read_text())
    assert data["schema_version"] == 1
    assert data["judgments_cost_usd"] == first.observed_usd
    assert data["held_usd"] == first.held_usd
    assert data["receipts"] == [asdict(first.receipts[0])]
    assert path.stat().st_mode & 0o777 == 0o600
    second = _ledger()
    await dr.assess(_packet("AC-1: other"), mode="shadow", ledger=second)
    dr.write_candidate_review(path, second)
    data = json.loads(path.read_text())
    assert [r["call_id"] for r in data["receipts"]] == [second.receipts[0].call_id]
    assert data["judgments_cost_usd"] == second.observed_usd


def _forbidden(lines):
    return [line for line in lines if re.search(r"score|correctness|confidence", line, re.IGNORECASE)]


async def test_assessment_lines_render_labels(monkeypatch):
    overrides = {
        "AC-1": SUPPORTED,
        "AC-2": {"supported": 0.05, "contradicted": 0.9, "insufficient_evidence": 0.05},
        "AC-3": {"supported": 0.2, "contradicted": 0.1, "insufficient_evidence": 0.7},
        "AC-4": BAD_SUM,
    }
    install_jev(monkeypatch, _answering(overrides))
    receipt = asdict(await dr.assess(_packet(), mode="shadow", ledger=_ledger()))
    lines = dr.assessment_lines(receipt, stale=False)
    assert lines == [
        "Requirement assessments (advisory)",
        "  AC-1  supported  P(supported)=0.90  current",
        "  AC-2  contradicted  P(contradicted)=0.90  current",
        "  AC-3  unclear (abstained)  P(insufficient_evidence)=0.70  current",
        "  AC-4  no answer  current",
    ]
    stale = dr.assessment_lines(receipt, stale=True)
    assert stale[0] == dr.HEADING
    assert all(line.endswith(dr.STALE_TEXT) for line in stale[1:])
    assert _forbidden(lines + stale) == []


async def test_assessment_lines_show_the_reason_never_a_number(monkeypatch):
    install_jev(monkeypatch, _answering())
    receipt = asdict(await dr.assess(_packet(["z" * 30000]), mode="shadow", ledger=_ledger()))
    lines = dr.assessment_lines(receipt, stale=False)
    assert lines == [dr.HEADING, "  not available: oversize"]
    assert not re.search(r"\d", "".join(lines))


@pytest.mark.parametrize(
    "receipt",
    [
        {"status": "answered", "detail": None},
        {"status": "answered", "detail": "x"},
        {"status": "answered"},
        None,
        [],
        {"status": "answered", "answers": {}, "detail": {"criterion_ids": 3, "labels": {}}},
        {"status": "answered", "answers": [], "detail": {"criterion_ids": ["AC-1"], "labels": {"AC-1": "supported"}}},
        {"status": "answered", "answers": {"AC-1": {"probabilities": {"supported": "x"}}}, "detail": {"criterion_ids": ["AC-1"], "labels": {"AC-1": "supported"}}},
        {"status": "answered", "answers": {}, "detail": {"criterion_ids": ["AC-1"], "labels": {"AC-1": "abstained"}}},
    ],
)
def test_assessment_lines_tolerate_malformed_receipts(receipt):
    lines = dr.assessment_lines(receipt, stale=False)
    assert lines == [dr.HEADING, "  not available: malformed receipt"]
    assert _forbidden(lines) == []
