from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from click.testing import CliRunner

from tests.harness.review_fakes import choice_body, install_jev
from tests.harness.test_decision_review_packet import _git
from voss.harness import decision_review as dr
from voss.harness import judgments as j
from voss.harness.swarm_store import SwarmStore
from voss_runtime.judgments import JudgmentLedger

ABSTAIN = {"supported": 0.05, "contradicted": 0.05, "insufficient_evidence": 0.9}


@pytest.fixture(autouse=True)
def repo(monkeypatch, tmp_path) -> Path:
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(j.auth, "load_provider_key", lambda env_key: None)
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "edit.py").write_text("value = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    monkeypatch.chdir(root)
    return root


@pytest.fixture()
def jev(monkeypatch):
    return install_jev(monkeypatch, lambda request: httpx.Response(200, json=choice_body(request)))


def _invoke(*args: str):
    return CliRunner().invoke(j.judge_cmd, ["review", *args])


def _state(request) -> dict:
    return json.loads(request.content)["state"]


def _side_commit(repo: Path) -> str:
    _git(repo, "checkout", "-q", "-b", "side")
    (repo / "edit.py").write_text("value = 'foo'\n")
    _git(repo, "commit", "-q", "-am", "foo")
    sha = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-")
    return sha


def _swarm(repo: Path, *, head: str | None, worktree: str = "/nonexistent/worktree") -> tuple[str, str]:
    store = SwarmStore(repo)
    swarm = store.create(goal="g", cwd=str(repo))
    task = store.add_task(swarm.id, goal="edit.py sets value to foo", owned_files=["edit.py"])
    store.mark_assigned(swarm.id, task.id, session_id="s")
    if head is not None:
        store.mark_candidate_ready(swarm.id, task.id, branch="swarm/b", worktree=worktree, head=head)
    return swarm.id, task.id


def test_working_tree_review_prints_assessments_and_writes_nothing(repo, jev):
    (repo / "edit.py").write_text("value = 2\n")
    (repo / "new_mod.py").write_text("bar = 1\n")
    assert not (repo / ".voss" / "config.yml").exists()
    result = _invoke("--criterion", "adds foo", "--criterion", "logs bar")
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == "Requirement assessments (advisory)"
    assert lines[1].startswith("  AC-1  supported  P(supported)=0.90  current")
    assert lines[2].startswith("  AC-2  supported")
    assert lines[3].startswith("packet ") and "model jev-1.13.0" in lines[3]
    assert "adds foo" not in result.output
    assert len(jev) == 1
    assert "+++ b/new_mod.py" in _state(jev[0])["diff"]
    assert list(repo.rglob("judgments.json")) == []


def test_criteria_file_keeps_explicit_ids(repo, jev, tmp_path):
    path = tmp_path / "criteria.txt"
    path.write_text("- AC-7: x\n- y")
    result = _invoke("--criteria-file", str(path))
    assert result.exit_code == 0, result.output
    assert [c["id"] for c in _state(jev[0])["criteria"]] == ["AC-7", "AC-2"]
    assert "  AC-7  supported" in result.output and "  AC-2  supported" in result.output


def test_ref_review_assesses_that_commit(repo, jev):
    sha = _side_commit(repo)
    result = _invoke("--criterion", "adds foo", "--ref", sha, "--json")
    assert result.exit_code == 0, result.output
    detail = json.loads(result.output)["detail"]
    assert detail["candidate"]["kind"] == "commit" and detail["candidate"]["head"] == sha
    assert "+value = 'foo'" in _state(jev[0])["diff"]


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ([{"name": "unit", "status": "passed"}, {"name": "lint", "status": "skipped"}], ["passed", "skipped"]),
        ([{"type": "unit", "pass": True, "detail": "ok"}, {"type": "lint", "pass": False}], ["passed", "failed"]),
    ],
)
def test_checks_file_in_either_shape_reaches_the_request(repo, jev, tmp_path, data, expected):
    path = tmp_path / "checks.json"
    path.write_text(json.dumps(data))
    result = _invoke("--criterion", "adds foo", "--checks", str(path))
    assert result.exit_code == 0, result.output
    assert [c["status"] for c in _state(jev[0])["checks"]] == expected


def test_unknown_check_status_is_refused_before_any_request(repo, jev, tmp_path):
    path = tmp_path / "checks.json"
    path.write_text(json.dumps([{"name": "unit", "status": "green"}]))
    result = _invoke("--criterion", "adds foo", "--checks", str(path))
    assert result.exit_code == 1
    assert "green" in result.stderr
    assert jev == []


def test_swarm_candidate_uses_task_goal_and_candidate_head(repo, jev):
    sha = _side_commit(repo)
    swarm_id, task_id = _swarm(repo, head=sha)
    result = _invoke("--swarm", swarm_id, "--task", task_id, "--json")
    assert result.exit_code == 0, result.output
    assert _state(jev[0])["criteria"] == [{"id": "AC-1", "text": "edit.py sets value to foo"}]
    receipt = json.loads(result.output)
    assert receipt["detail"]["candidate"]["head"] == sha
    assert receipt["mode"] == "explicit"
    assert not (repo / ".voss" / "swarm" / swarm_id / "reviews").exists()
    events = (repo / ".voss" / "swarm" / swarm_id / "events" / "events.jsonl").read_text().splitlines()
    assert [json.loads(e)["type"] for e in events] == ["swarm.create", "swarm.task", "swarm.assign", "swarm.candidate_ready"]


def test_swarm_refusals_make_zero_requests(repo, jev):
    sha = _side_commit(repo)
    swarm_id, task_id = _swarm(repo, head=sha)
    open_swarm, open_task = _swarm(repo, head=None)
    for args in (
        ("--swarm", swarm_id, "--task", "nope"),
        ("--swarm", open_swarm, "--task", open_task),
        ("--swarm", "..", "--task", task_id),
        ("--swarm", swarm_id, "--task", "a..b"),
        ("--swarm", "missing", "--task", task_id),
    ):
        result = _invoke(*args)
        assert result.exit_code == 1, args
        assert "review refused:" in result.stderr
    assert jev == []


def test_run_saves_one_receipt_for_audit(repo, jev):
    (repo / ".voss" / "sessions" / "root_r1").mkdir(parents=True)
    (repo / "edit.py").write_text("value = 2\n")
    result = _invoke("--criterion", "adds foo", "--run", "root_r1")
    assert result.exit_code == 0, result.output
    assert "saved to .voss/sessions/root_r1/judgments.json" in result.output
    data = json.loads((repo / ".voss" / "sessions" / "root_r1" / "judgments.json").read_text())
    assert len(data["receipts"]) == 1
    assert data["receipts"][0]["mode"] == "explicit"
    assert data["receipts"][0]["purpose"] == "review.requirements"


@pytest.mark.parametrize("run_id", ["unknown", "a/b", "..", "a\\b", ""])
def test_unsafe_or_unknown_run_is_refused_before_any_request(repo, jev, run_id):
    (repo / ".voss" / "sessions" / "a").mkdir(parents=True)
    result = _invoke("--criterion", "adds foo", "--run", run_id)
    assert result.exit_code == 1
    assert "review refused:" in result.stderr
    assert jev == []


def test_kill_switch_fails_loudly_with_zero_requests(repo, jev, monkeypatch):
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    result = _invoke("--criterion", "adds foo")
    assert result.exit_code == 1
    assert result.stderr.startswith("judgment disabled: ")
    assert jev == []


def test_missing_key_fails_loudly_with_zero_requests(repo, jev, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY")
    result = _invoke("--criterion", "adds foo")
    assert result.exit_code == 1
    assert result.stderr.startswith("judgment unavailable: ")
    assert jev == []


@pytest.mark.parametrize(
    "args",
    [
        ("--swarm", "s", "--task", "t", "--ref", "HEAD"),
        ("--swarm", "s", "--task", "t", "--criterion", "x"),
        ("--task", "t", "--criterion", "x"),
        ("--swarm", "s", "--criterion", "x"),
        (),
        ("--saved",),
        ("--saved", "--swarm", "s"),
        ("--saved", "--swarm", "s", "--task", "t", "--ref", "HEAD"),
        ("--saved", "--swarm", "s", "--task", "t", "--criterion", "x"),
        ("--saved", "--swarm", "s", "--task", "t", "--run", "r"),
    ],
)
def test_bad_flag_combinations_are_usage_errors(repo, jev, args):
    result = _invoke(*args)
    assert result.exit_code == 2, result.output
    assert jev == []


@pytest.mark.parametrize("flag", ["--criteria-file", "--checks"])
def test_saved_rejects_file_inputs(repo, jev, tmp_path, flag):
    path = tmp_path / "x.txt"
    path.write_text("[]")
    result = _invoke("--saved", "--swarm", "s", "--task", "t", flag, str(path))
    assert result.exit_code == 2
    assert jev == []


async def _saved_review(repo: Path, monkeypatch, swarm_id: str, task_id: str) -> Path:
    install_jev(monkeypatch, lambda request: httpx.Response(200, json=choice_body(request, {"AC-1": ABSTAIN})))
    ledger = JudgmentLedger(4, 0.01)
    (repo / "edit.py").write_text("value = 2\n")
    await dr.assess_candidate(cwd=repo, criteria="adds foo", ledger=ledger, mode="shadow")
    (repo / "edit.py").write_text("value = 1\n")
    return dr.write_candidate_review(dr.candidate_review_path(repo, swarm_id, task_id), ledger)


async def test_saved_prints_the_stored_assessment_with_zero_requests(repo, monkeypatch):
    path = await _saved_review(repo, monkeypatch, "s1", "t1")
    seen = install_jev(monkeypatch, lambda request: pytest.fail("no request expected"))
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    monkeypatch.delenv("TYPESAFE_API_KEY")
    result = _invoke("--saved", "--swarm", "s1", "--task", "t1")
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0] == "Requirement assessments (advisory)"
    assert lines[1] == "  AC-1  unclear (abstained)  P(insufficient_evidence)=0.90  current"
    assert lines[2].startswith("packet ") and "cost $" in lines[2]
    as_json = _invoke("--saved", "--swarm", "s1", "--task", "t1", "--json")
    assert as_json.exit_code == 0
    assert json.loads(as_json.output) == json.loads(path.read_text())
    assert json.loads(as_json.output)["receipts"][0]["mode"] == "shadow"
    assert seen == []


def test_saved_without_a_file_says_so(repo, jev):
    result = _invoke("--saved", "--swarm", "s1", "--task", "t9")
    assert result.exit_code == 1
    assert "no saved assessment for task t9" in result.stderr
    assert jev == []

