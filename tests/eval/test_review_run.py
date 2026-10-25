from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tests.eval.test_review_dataset import DATASET, DIFF, write_dataset
from tests.harness.review_fakes import SUPPORTED, choice_body, install_jev
from voss.eval import runner
from voss.eval.review import load_fixtures, main, receipt_summary, score
from voss.harness import decision_review as dr
from voss.harness import judgments
from voss.harness.board.reviewer_b import ReviewerB, _ReviewerBOutput
from voss_runtime.providers.base import ProviderResponse

LOCATION = "test-loc"
LOCKED_2 = DATASET.parent / "review-locked-2"
INSUFFICIENT = {"supported": 0.05, "contradicted": 0.05, "insufficient_evidence": 0.9}
LEANING = {"supported": 0.7, "contradicted": 0.2, "insufficient_evidence": 0.1}
ROW_KEYS = {"fixture", "criterion", "kind", "gold", "flag", "label", "probabilities"}
BASELINE_KEYS = {"fixture", "split", "kind", "verdict", "conf", "evidence_refs", "domain_inferred", "error"}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))


@pytest.fixture
def tree(tmp_path) -> Path:
    path = tmp_path / "tree"
    path.mkdir()
    (path / "pkg.py").write_text("a = 1\n")
    return path


@pytest.fixture
def root(tmp_path, tree) -> Path:
    data = write_dataset(tmp_path / "data")
    assert main(["freeze", "--root", str(data), "--tree", str(tree)]) == 0
    return data


def answer_all(probabilities: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        qids = json.loads(request.content)["questions"]
        return httpx.Response(200, json=choice_body(request, dict.fromkeys(qids, probabilities)))

    return handler


def run(root: Path, tree: Path, *extra: str) -> int:
    return main(["run", "--root", str(root), "--tree", str(tree), "--location", LOCATION, *extra])


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_dev_run_writes_report_rows_receipts_and_markdown(monkeypatch, root, tree):
    seen = install_jev(monkeypatch, answer_all(SUPPORTED))
    dev = load_fixtures(root, split="dev")

    assert run(root, tree) == 0

    assert len(seen) == len(dev) == 7
    for request in seen:
        body = json.loads(request.content)
        assert set(body["questions"]) == {"AC-1", "AC-2"}
        assert body["state"]["code"] == "### pkg.py\na = 2"
    reports = root / "reports"
    report = json.loads((reports / "review-dev.json").read_text())
    rows = read_jsonl(reports / "review-dev" / "rows.jsonl")
    receipts = read_jsonl(reports / "review-dev" / "receipts.jsonl")
    frozen = json.loads((root / "freeze.json").read_text())
    assert report["status"] == "complete" and report["split"] == "dev"
    assert report["threshold"] == dr.THRESHOLD
    assert report["rubric_version"] == dr.RUBRIC_VERSION
    assert report["model"] == "jev-1.13.0" and report["location"] == LOCATION
    assert report["metrics"] == score(rows)
    assert report["receipts"] == receipt_summary(receipts)
    assert report["release_bar"] == frozen["release_bar"]
    assert report["passed"] is None
    assert len(rows) == 14 and all(set(row) == ROW_KEYS for row in rows)
    assert {row["label"] for row in rows} == {"supported"}
    assert "requirement" not in (reports / "review-dev" / "rows.jsonl").read_text()
    assert len(receipts) == 7
    assert {(r["purpose"], r["mode"], r["status"]) for r in receipts} == {(dr.PURPOSE, "explicit", "answered")}
    assert (reports / "review-dev.md").read_text().startswith("# Requirement assessments eval (dev)")


def test_dev_runs_can_repeat(monkeypatch, root, tree):
    seen = install_jev(monkeypatch, answer_all(SUPPORTED))

    assert run(root, tree) == 0
    assert run(root, tree) == 0

    assert len(seen) == 14
    assert json.loads((root / "reports" / "review-dev.json").read_text())["status"] == "complete"


def test_a_failed_fixture_has_no_labels_and_the_run_continues(monkeypatch, root, tree):
    failing = sorted(load_fixtures(root, split="dev"), key=lambda row: row["id"])[0]
    succeed = answer_all(SUPPORTED)

    def handler(request: httpx.Request) -> httpx.Response:
        if json.loads(request.content)["state"]["criteria"][0]["text"] == failing["criteria"][0]:
            return httpx.Response(500)
        return succeed(request)

    seen = install_jev(monkeypatch, handler)

    assert run(root, tree) == 0

    assert len(seen) == 7
    rows = read_jsonl(root / "reports" / "review-dev" / "rows.jsonl")
    failed = [row for row in rows if row["fixture"] == failing["id"]]
    assert len(failed) == 2 and all(row["label"] is None and row["probabilities"] is None for row in failed)
    assert all(row["label"] == "supported" for row in rows if row["fixture"] != failing["id"])
    receipts = read_jsonl(root / "reports" / "review-dev" / "receipts.jsonl")
    assert sorted(r["status"] for r in receipts).count("unavailable") == 1


def test_test_split_without_locked_final_refuses(monkeypatch, root, tree, capsys):
    seen = install_jev(monkeypatch, answer_all(SUPPORTED))

    assert run(root, tree, "--split", "test") == 2

    assert "--locked-final" in capsys.readouterr().err
    assert seen == []
    assert not (root / "reports").exists()


@pytest.mark.parametrize(("probabilities", "passed"), [(INSUFFICIENT, True), (SUPPORTED, False)])
def test_locked_run_marks_started_first_and_runs_once(monkeypatch, root, tree, capsys, probabilities, passed):
    marker = root / "reports" / "review-test.json"
    answer = answer_all(probabilities)

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(marker.read_text())["status"] == "started"
        return answer(request)

    seen = install_jev(monkeypatch, handler)

    assert run(root, tree, "--split", "test", "--locked-final") == 0

    assert len(seen) == 7
    report = json.loads(marker.read_text())
    false_supported = report["metrics"]["false_supported"]
    assert report["status"] == "complete" and report["split"] == "test"
    assert report["threshold"] == dr.THRESHOLD
    assert report["passed"] is passed
    assert report["passed"] == (false_supported["n"] > 0 and false_supported["rate"] <= 0.05)
    assert "release bar" in (root / "reports" / "review-test.md").read_text()
    before = marker.read_bytes()
    capsys.readouterr()

    assert run(root, tree, "--split", "test", "--locked-final") == 2

    assert "scored once" in capsys.readouterr().err
    assert len(seen) == 7
    assert marker.read_bytes() == before


def kill(monkeypatch, root):
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")


def drop_key(monkeypatch, root):
    monkeypatch.setattr(judgments, "resolve_api_key", lambda: None)


def unfreeze(monkeypatch, root):
    (root / "freeze.json").unlink()


def edit_fixture(monkeypatch, root):
    path = root / "fixtures" / "batch-01.jsonl"
    path.write_text(path.read_text().replace('"requirement 1.1"', '"requirement 1.1 edited"'))


@pytest.mark.parametrize("change", [kill, drop_key, unfreeze, edit_fixture])
@pytest.mark.parametrize("split", ["dev", "test"])
def test_refuses_before_any_request(monkeypatch, root, tree, capsys, change, split):
    seen = install_jev(monkeypatch, answer_all(SUPPORTED))
    change(monkeypatch, root)

    assert run(root, tree, "--split", split, "--locked-final") == 2

    assert capsys.readouterr().err.strip()
    assert seen == []
    assert not (root / "reports").exists()


def test_tune_replays_dev_probabilities_without_requests(monkeypatch, root, tree, capsys):
    seen = install_jev(monkeypatch, answer_all(LEANING))
    assert run(root, tree) == 0
    capsys.readouterr()

    assert main(["tune", "--root", str(root)]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert len(seen) == 7
    assert lines[0].split() == ["threshold", "false_supported", "contradicted_recall", "coverage"]
    assert [line.split()[0] for line in lines[1:]] == ["0.55", "0.60", "0.65", "0.70", "0.75", "0.80", "0.85", "0.90", "0.95"]
    assert lines[1].split()[1:3] == ["1.000", "(8/8)"] and lines[1].split()[-1] == "1.000"
    assert lines[5].split()[1:3] == ["0.000", "(0/8)"] and lines[5].split()[-1] == "0.000"


def test_tune_refuses_a_test_report(tmp_path, capsys):
    report = tmp_path / "reports" / "review-test.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({"split": "test", "status": "complete"}))

    assert main(["tune", "--report", str(report)]) == 2

    assert "dev report" in capsys.readouterr().err


def test_locked_corpus_rubric_matches_the_evaluator():
    assert json.loads((LOCKED_2 / "corpus.json").read_text())["rubric_version"] == dr.RUBRIC_VERSION


class FakeProvider:
    def __init__(self, fail_first: bool = False):
        self.models: list[str] = []
        self.fail_first = fail_first

    async def complete(self, **kw):
        self.models.append(kw["model"])
        if self.fail_first and len(self.models) == 1:
            raise RuntimeError("provider down")
        parsed = _ReviewerBOutput(conf=0.7, verdict="pass", notes="ok", evidence_refs=["pkg.py:1"], domain_inferred="code")
        return ProviderResponse(text="{}", model=kw["model"], prompt_tokens=1, completion_tokens=1, cost_usd=0.0, parsed=parsed)

    def count_tokens(self, **kw):
        return 1


@pytest.fixture
def reviewer(monkeypatch):
    state = {"provider": FakeProvider(), "calls": [], "cards": []}
    original = ReviewerB.review

    def provider_for_eval(*, stub, auth_pref):
        state["calls"].append((stub, auth_pref))
        return state["provider"], None

    def spy(self, card, *, tier="fast"):
        state["cards"].append((card, tier))
        return original(self, card, tier=tier)

    monkeypatch.setattr(runner, "_provider_for_eval", provider_for_eval)
    monkeypatch.setattr(ReviewerB, "review", spy)
    return state


def baseline(root: Path, tree: Path, *extra: str) -> int:
    return main(["baseline-b", "--root", str(root), "--tree", str(tree), *extra])


def test_baseline_b_records_the_real_reviewer_per_fixture(root, tree, reviewer):
    dev = {row["id"]: row for row in load_fixtures(root, split="dev")}

    assert baseline(root, tree, "--model", "M", "--auth", "claude") == 0

    out = json.loads((root / "reports" / "reviewer-b-baseline-dev.json").read_text())
    assert out["model"] == "M" and out["auth"] == "claude" and out["split"] == "dev"
    assert [row["fixture"] for row in out["rows"]] == sorted(dev)
    for row in out["rows"]:
        assert set(row) == BASELINE_KEYS
        assert row["split"] == "dev" and row["kind"] == dev[row["fixture"]]["kind"]
        assert (row["verdict"], row["conf"], row["evidence_refs"], row["domain_inferred"], row["error"]) == (
            "pass", 0.7, ["pkg.py:1"], "code", None,
        )
    assert reviewer["calls"] == [(False, "claude")]
    assert reviewer["provider"].models == ["M"] * 7
    assert {tier for _, tier in reviewer["cards"]} == {"strong"}
    for card, _ in reviewer["cards"]:
        fixture = next(row for row in dev.values() if row["title"] == card.original_idea)
        assert card.acceptance_criteria == "\n".join(fixture["criteria"])
        assert card.file_diff == DIFF
        assert card.repo_context == "### pkg.py\na = 2"
        expected = {"failed_check": "tests: failed", "skipped_check": "tests: skipped", "no_checks": dr.NO_CHECKS}
        assert card.artifact_text == expected.get(fixture["kind"], "tests: passed")


def test_baseline_b_records_a_provider_error_and_continues(root, tree, reviewer):
    reviewer["provider"] = FakeProvider(fail_first=True)

    assert baseline(root, tree) == 0

    rows = json.loads((root / "reports" / "reviewer-b-baseline-dev.json").read_text())["rows"]
    assert len(rows) == 7
    assert rows[0]["error"] == "RuntimeError" and rows[0]["verdict"] is None
    assert all(row["error"] is None and row["verdict"] == "pass" for row in rows[1:])


@pytest.mark.parametrize("split", ["test", "all"])
def test_baseline_b_locked_split_needs_locked_final(root, tree, reviewer, split):
    assert baseline(root, tree, "--split", split) == 2

    assert reviewer["calls"] == [] and reviewer["cards"] == []
    assert not (root / "reports").exists()


def test_baseline_b_runs_once_per_split(root, tree, reviewer):
    assert baseline(root, tree, "--split", "test", "--locked-final") == 0
    path = root / "reports" / "reviewer-b-baseline-test.json"
    before = path.read_bytes()

    assert baseline(root, tree, "--split", "test", "--locked-final") == 2

    assert len(reviewer["calls"]) == 1 and len(reviewer["cards"]) == 7
    assert path.read_bytes() == before


def write_compare_inputs(root: Path, baseline_name: str) -> dict:
    reports = root / "reports"
    (reports / "review-test").mkdir(parents=True)
    pair_rate = {"k": 1, "n": 4, "rate": 0.25, "ci": [0.05, 0.7]}
    (reports / "review-test.json").write_text(json.dumps({
        "status": "complete", "split": "test", "threshold": 0.8, "metrics": {"false_supported": pair_rate},
    }))
    rows = [
        ("rv-001", "AC-1", "supported", "none", "supported"),
        ("rv-001", "AC-2", "insufficient_evidence", "none", "supported"),
        ("rv-002", "AC-1", "contradicted", "none", "contradicted"),
        ("rv-003", "AC-1", "insufficient_evidence", "none", "abstained"),
        ("rv-004", "AC-1", "supported", "none", "supported"),
        ("rv-005", "AC-1", "insufficient_evidence", "ambiguous", "supported"),
    ]
    (reports / "review-test" / "rows.jsonl").write_text("".join(
        json.dumps({"fixture": f, "criterion": c, "kind": "k", "gold": g, "flag": fl, "label": lb, "probabilities": None}) + "\n"
        for f, c, g, fl, lb in rows
    ))
    verdicts = [("rv-001", "test", "pass", None), ("rv-002", "test", "fail", None), ("rv-003", "test", None, "TimeoutError"),
                ("rv-004", "test", "pass", None), ("rv-005", "test", "pass", None), ("rv-009", "dev", "pass", None)]
    (reports / baseline_name).write_text(json.dumps({"rows": [
        {"fixture": f, "split": s, "verdict": v, "error": e} for f, s, v, e in verdicts if s == "test" or "all" in baseline_name
    ]}))
    return pair_rate


@pytest.mark.parametrize("name", ["reviewer-b-baseline-test.json", "reviewer-b-baseline-all.json"])
def test_compare_lines_up_reviewer_b_and_jev_on_negative_fixtures(tmp_path, capsys, name):
    pair_rate = write_compare_inputs(tmp_path, name)

    assert main(["compare", "--root", str(tmp_path)]) == 0

    result = json.loads((tmp_path / "reports" / "review-compare.json").read_text())
    assert result["informational"] is True
    assert result["negative_fixtures"] == 3 and result["compared_fixtures"] == 2
    assert result["reviewer_b_errors"] == 1
    assert {k: result["reviewer_b_passes"][k] for k in ("k", "n", "rate")} == {"k": 1, "n": 2, "rate": 0.5}
    assert {k: result["jev_fixture_false_supported"][k] for k in ("k", "n", "rate")} == {"k": 1, "n": 2, "rate": 0.5}
    assert len(result["reviewer_b_passes"]["ci"]) == 2
    assert result["jev_pair_false_supported"] == pair_rate
    assert "informational" in capsys.readouterr().out


@pytest.mark.parametrize("status", [None, "started"])
def test_compare_needs_a_complete_locked_report(tmp_path, capsys, status):
    if status:
        (tmp_path / "reports").mkdir()
        (tmp_path / "reports" / "review-test.json").write_text(json.dumps({"status": status}))

    assert main(["compare", "--root", str(tmp_path)]) == 2

    assert "complete locked run" in capsys.readouterr().err
    assert not (tmp_path / "reports" / "review-compare.json").exists()
