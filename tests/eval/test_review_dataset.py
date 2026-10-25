from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pytest

from voss.eval.retrieval import PINNED_COMMIT
from voss.eval.review import (
    FREEZE_SEED,
    KINDS,
    RELEASE_BAR,
    DatasetError,
    LockedSplitError,
    load_fixtures,
    main,
    pairs,
)

DATASET = Path(__file__).resolve().parents[2] / "evals" / "review"
SHAPES = {
    "missing_criterion": {"fixtures": 2, "criteria": 2, "supported": 1},
    "contradicted": {"fixtures": 2, "criteria": 2, "supported": 1},
    "failed_check": {"fixtures": 2, "criteria": 2, "supported": 1},
    "skipped_check": {"fixtures": 2, "criteria": 2, "supported": 1},
    "no_checks": {"fixtures": 2, "criteria": 2, "supported": 0},
    "ambiguous": {"fixtures": 2, "criteria": 2, "supported": 0},
    "supported": {"fixtures": 2, "criteria": 2, "supported": 2},
}
DIFF = "--- a/pkg.py\n+++ b/pkg.py\n@@ -1 +1 @@\n-a = 1\n+a = 2\n"
CHECKS = {
    "failed_check": [{"name": "tests", "status": "failed"}],
    "skipped_check": [{"name": "tests", "status": "skipped"}],
    "no_checks": [],
}


def label(gold: str, *, confidence: str = "high", flag: str = "none", note: str = "") -> dict:
    return {"gold": gold, "confidence": confidence, "flag": flag, "note": note}


def fixture(n: int, kind: str) -> dict:
    shape = SHAPES[kind]
    negative = "contradicted" if kind == "contradicted" else "insufficient_evidence"
    golds = ["supported"] * shape["supported"] + [negative] * (shape["criteria"] - shape["supported"])
    return {
        "id": f"rv-{n:03d}",
        "kind": kind,
        "title": f"change {n}",
        "criteria": [f"requirement {n}.{i}" for i in range(1, shape["criteria"] + 1)],
        "diff": DIFF,
        "checks": CHECKS.get(kind, [{"name": "tests", "status": "passed"}]),
        "verification_note": "",
        "labels": {f"AC-{i}": label(gold) for i, gold in enumerate(golds, 1)},
    }


def default_fixtures() -> list[dict]:
    return [fixture(n, kind) for n, kind in enumerate([kind for kind in KINDS for _ in range(2)], 1)]


def write_rows(root: Path, rows: list[dict]) -> None:
    (root / "fixtures").mkdir(parents=True, exist_ok=True)
    half = len(rows) // 2
    for batch, chunk in (("01", rows[:half]), ("02", rows[half:])):
        (root / "fixtures" / f"batch-{batch}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in chunk))


def write_dataset(root: Path, rows: list[dict] | None = None, **corpus_overrides) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    corpus = {
        "repo": "voss", "commit": PINNED_COMMIT, "rubric_version": "review.requirements.v1",
        "kinds": SHAPES, "expected_pairs": 28, "min_locked_negatives": 8, **corpus_overrides,
    }
    (root / "corpus.json").write_text(json.dumps(corpus, indent=2) + "\n")
    write_rows(root, default_fixtures() if rows is None else rows)
    return root


def read_rows(root: Path) -> list[dict]:
    return [
        json.loads(line)
        for path in sorted((root / "fixtures").glob("*.jsonl"))
        for line in path.read_text().splitlines()
    ]


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def tree(tmp_path) -> Path:
    path = tmp_path / "tree"
    path.mkdir()
    (path / "pkg.py").write_text("a = 1\n")
    return path


def run(command: str, root: Path, tree: Path, *extra: str) -> int:
    return main([command, "--root", str(root), "--tree", str(tree), *extra])


def frozen_dataset(tmp_path: Path, tree: Path) -> Path:
    root = write_dataset(tmp_path / "data")
    assert run("freeze", root, tree) == 0
    return root


def test_locked_split_needs_locked_final(tmp_path, tree):
    root = frozen_dataset(tmp_path, tree)

    with pytest.raises(LockedSplitError):
        load_fixtures(root, split="test")

    rows = load_fixtures(root, split="test", locked_final=True)
    assert rows and {row["split"] for row in rows} == {"test"}


def test_dev_split_returns_only_dev_fixtures(tmp_path, tree):
    root = frozen_dataset(tmp_path, tree)

    rows = load_fixtures(root, split="dev")

    assert len(rows) == 7
    assert {row["split"] for row in rows} == {"dev"}


def test_unfrozen_dataset_cannot_be_loaded(tmp_path):
    root = write_dataset(tmp_path / "data")

    with pytest.raises(DatasetError, match="not frozen"):
        load_fixtures(root, split="dev")
    with pytest.raises(DatasetError, match="not frozen"):
        load_fixtures(root, split="test", locked_final=True)


def test_check_accepts_valid_fixtures(tmp_path, tree, capsys):
    root = write_dataset(tmp_path / "data")

    assert run("check", root, tree) == 0

    assert "14 fixtures ok" in capsys.readouterr().out


def test_check_limits_to_one_batch(tmp_path, tree, capsys):
    root = write_dataset(tmp_path / "data")

    assert run("check", root, tree, "--batch", "02") == 0

    assert "7 fixtures ok" in capsys.readouterr().out


def mutate(index: int, change):
    def apply(rows: list[dict]) -> None:
        change(rows[index])
    return apply


def add_criterion(row: dict) -> None:
    row["criteria"].append("one more requirement")
    row["labels"]["AC-3"] = label("insufficient_evidence")


CASES = [
    ("duplicate-id", lambda rows: rows[1].update(id=rows[0]["id"]), "rv-001: duplicate id"),
    ("bad-id", mutate(0, lambda row: row.update(id="rv-1")), "'rv-1': bad id"),
    ("unknown-kind", mutate(0, lambda row: row.update(kind="flaky")), "unknown kind 'flaky'"),
    ("label-keys", mutate(0, lambda row: row["labels"].update({"AC-9": row["labels"].pop("AC-2")})), "label keys"),
    ("criteria-count", mutate(2, add_criterion), "contradicted needs 2 criteria, has 3"),
    ("supported-count", mutate(0, lambda row: row["labels"]["AC-2"].update(gold="supported")), "missing_criterion needs 1 supported gold labels, has 2"),
    ("bad-gold", mutate(0, lambda row: row["labels"]["AC-1"].update(gold="maybe")), "AC-1: bad gold 'maybe'"),
    ("bad-confidence", mutate(0, lambda row: row["labels"]["AC-1"].update(confidence="medium")), "AC-1: bad confidence 'medium'"),
    ("bad-flag", mutate(0, lambda row: row["labels"]["AC-1"].update(flag="unsure")), "AC-1: bad flag 'unsure'"),
    ("low-unflagged", mutate(0, lambda row: row["labels"]["AC-1"].update(confidence="low")), "AC-1: low confidence must be flagged"),
    ("bad-checks", mutate(0, lambda row: row.update(checks=[{"name": "tests"}])), "bad checks"),
    ("failed-without-failed", mutate(4, lambda row: row.update(checks=[{"name": "tests", "status": "passed"}])), "failed_check needs a failed check"),
    ("skipped-without-skipped", mutate(6, lambda row: row.update(checks=[])), "skipped_check needs a skipped check"),
    ("no-checks-with-check", mutate(8, lambda row: row.update(checks=[{"type": "tests", "pass": True}])), "no_checks must record no checks"),
    ("other-with-failed", mutate(12, lambda row: row.update(checks=[{"name": "tests", "status": "failed"}])), "supported must not have a failed or skipped check"),
    ("other-with-skipped", mutate(0, lambda row: row.update(checks=[{"name": "lint", "status": "skipped"}])), "missing_criterion must not have a failed or skipped check"),
    ("diff-not-applying", mutate(0, lambda row: row.update(diff=DIFF.replace("-a = 1", "-a = 7"))), "diff does not apply"),
    ("empty-diff", mutate(0, lambda row: row.update(diff="")), "diff does not apply"),
]


@pytest.mark.parametrize(("change", "expected"), [case[1:] for case in CASES], ids=[case[0] for case in CASES])
def test_check_reports_each_problem(tmp_path, tree, capsys, change, expected):
    rows = default_fixtures()
    change(rows)
    root = write_dataset(tmp_path / "data", rows)

    assert run("check", root, tree) == 1

    out = capsys.readouterr().out
    assert expected in out
    assert "fixtures ok" not in out


def test_review_lists_only_flagged_pairs(tmp_path, capsys):
    rows = default_fixtures()
    rows[0]["labels"]["AC-2"] = label("insufficient_evidence", confidence="low", flag="review", note="maybe covered by tests")
    rows[3]["labels"]["AC-1"] = label("supported", confidence="low", flag="review", note="partial")
    rows[5]["labels"]["AC-2"] = label("insufficient_evidence", flag="reviewed")
    rows[7]["labels"]["AC-2"] = label("insufficient_evidence", flag="ambiguous")
    root = write_dataset(tmp_path / "data", rows)

    assert main(["review", "--root", str(root)]) == 0

    assert "2 pairs need review" in capsys.readouterr().out
    text = (root / "REVIEW.md").read_text()
    assert "## rv-001 AC-2" in text and "> requirement 1.2" in text
    assert "`insufficient_evidence`" in text and "maybe covered by tests" in text
    assert "## rv-004 AC-1" in text and "> requirement 4.1" in text and "partial" in text
    assert text.count("## ") == 2


def test_review_with_nothing_flagged(tmp_path, capsys):
    root = write_dataset(tmp_path / "data")

    assert main(["review", "--root", str(root)]) == 0

    assert "0 pairs need review" in capsys.readouterr().out
    assert "No pairs need review." in (root / "REVIEW.md").read_text()


def test_freeze_splits_whole_fixtures_evenly_within_kind(tmp_path, tree):
    root = write_dataset(tmp_path / "data")
    before = read_rows(root)

    assert run("freeze", root, tree) == 0

    after = read_rows(root)
    assert [{key: value for key, value in row.items() if key != "split"} for row in after] == before
    assert Counter(row["split"] for row in after) == {"dev": 7, "test": 7}
    for kind in KINDS:
        assert Counter(row["split"] for row in after if row["kind"] == kind) == {"dev": 1, "test": 1}
    split_pairs = Counter(row["split"] for row in after for _ in row["labels"])
    assert split_pairs == {"dev": 14, "test": 14}


def test_freeze_is_deterministic_for_a_seed(tmp_path, tree):
    first = write_dataset(tmp_path / "a")
    second = write_dataset(tmp_path / "b")

    assert run("freeze", first, tree) == 0
    assert run("freeze", second, tree) == 0

    assert read_rows(first) == read_rows(second)


def test_freeze_writes_rules_counts_and_hashes(tmp_path, tree, capsys):
    root = write_dataset(tmp_path / "data")

    assert run("freeze", root, tree) == 0

    frozen = json.loads((root / "freeze.json").read_text())
    assert frozen["frozen_at"] == datetime.now(timezone.utc).date().isoformat()
    assert frozen["commit"] == PINNED_COMMIT
    assert frozen["rubric_version"] == "review.requirements.v1"
    assert frozen["seed"] == FREEZE_SEED
    for split in ("dev", "test"):
        counts = frozen["splits"][split]
        assert counts["fixtures"] == 7 and counts["pairs"] == 14
        assert counts["negatives"] == 8 and counts["ambiguous"] == 0
        assert counts["gold"] == {"contradicted": 1, "insufficient_evidence": 7, "supported": 6}
    assert set(frozen["metrics"]) == {
        "false_supported", "contradicted_recall", "abstention_rate", "coverage", "ambiguity", "brier", "latency", "cost",
    }
    assert frozen["threshold_policy"]["start"] == 0.80
    assert "dev" in frozen["threshold_policy"]["tuning"]
    assert frozen["release_bar"] == {
        "false_supported_max": RELEASE_BAR,
        "basis": "point estimate on the locked split",
        "interval": "Wilson 95%, reported, not gating",
    }
    assert set(frozen["files"]) == {"corpus.json", "fixtures/batch-01.jsonl", "fixtures/batch-02.jsonl"}
    for name, digest in frozen["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
    out = capsys.readouterr().out
    assert "dev: 7 fixtures, 14 pairs, 8 negatives" in out
    assert "test: 7 fixtures, 14 pairs, 8 negatives" in out


def test_locked_only_corpus_freezes_every_fixture_into_test(tmp_path, tree):
    root = write_dataset(tmp_path / "data", locked_only=True)

    assert run("freeze", root, tree) == 0

    assert {row["split"] for row in read_rows(root)} == {"test"}
    frozen = json.loads((root / "freeze.json").read_text())
    assert frozen["splits"]["dev"]["fixtures"] == 0
    assert frozen["splits"]["test"]["fixtures"] == 14
    assert frozen["split_algorithm"] == "every fixture is test"


def test_ambiguous_pairs_do_not_count_as_locked_negatives(tmp_path, tree):
    rows = default_fixtures()
    for row in rows:
        if row["kind"] == "no_checks":
            row["labels"]["AC-1"]["flag"] = "ambiguous"
    root = write_dataset(tmp_path / "data", rows, min_locked_negatives=7)

    assert run("freeze", root, tree) == 0

    frozen = json.loads((root / "freeze.json").read_text())
    assert frozen["splits"]["test"]["negatives"] == 7
    assert frozen["splits"]["test"]["ambiguous"] == 1


def odd_kind(root: Path) -> None:
    shapes = {**SHAPES, "missing_criterion": {**SHAPES["missing_criterion"], "fixtures": 3}}
    write_dataset(root, default_fixtures() + [fixture(15, "missing_criterion")], kinds=shapes)


REFUSALS = [
    ("already-frozen", lambda root: (root / "freeze.json").write_text("{}\n")),
    ("flagged-pair", lambda root: write_dataset(root, flagged_rows())),
    ("check-fails", lambda root: write_dataset(root, [{**default_fixtures()[0], "diff": ""}, *default_fixtures()[1:]])),
    ("kind-count", lambda root: write_dataset(root, kinds={**SHAPES, "supported": {**SHAPES["supported"], "fixtures": 4}})),
    ("unequal-pairs", odd_kind),
    ("few-locked-negatives", lambda root: write_dataset(root, min_locked_negatives=9)),
]


def flagged_rows() -> list[dict]:
    rows = default_fixtures()
    rows[0]["labels"]["AC-2"] = label("insufficient_evidence", confidence="low", flag="review")
    return rows


@pytest.mark.parametrize("change", [case[1] for case in REFUSALS], ids=[case[0] for case in REFUSALS])
def test_freeze_refuses_without_changing_fixtures(tmp_path, tree, change):
    root = write_dataset(tmp_path / "data")
    change(root)
    before = snapshot(root)

    assert run("freeze", root, tree) == 1

    assert snapshot(root) == before


def test_pairs_flattens_every_criterion():
    rows = default_fixtures()[:2]

    assert pairs(rows) == [
        {"fixture": "rv-001", "kind": "missing_criterion", "criterion": "AC-1", "gold": "supported", "flag": "none"},
        {"fixture": "rv-001", "kind": "missing_criterion", "criterion": "AC-2", "gold": "insufficient_evidence", "flag": "none"},
        {"fixture": "rv-002", "kind": "missing_criterion", "criterion": "AC-1", "gold": "supported", "flag": "none"},
        {"fixture": "rv-002", "kind": "missing_criterion", "criterion": "AC-2", "gold": "insufficient_evidence", "flag": "none"},
    ]


def test_corpus_fixes_the_100_pair_shape():
    corpus = json.loads((DATASET / "corpus.json").read_text())
    kinds = corpus["kinds"]

    assert corpus["commit"] == PINNED_COMMIT
    assert corpus["rubric_version"] == "review.requirements.v1"
    assert set(kinds) == set(KINDS)
    assert all(shape["fixtures"] % 2 == 0 for shape in kinds.values())
    assert sum(shape["fixtures"] * shape["criteria"] for shape in kinds.values()) == corpus["expected_pairs"] == 100
    locked_negatives = sum(shape["fixtures"] // 2 * (shape["criteria"] - shape["supported"]) for shape in kinds.values())
    assert locked_negatives == 33 >= corpus["min_locked_negatives"] == 30


@pytest.mark.skipif(not (DATASET / "freeze.json").exists(), reason="review dataset not frozen yet")
def test_frozen_review_files_match_their_sha256():
    files = json.loads((DATASET / "freeze.json").read_text())["files"]
    listed = {"corpus.json"} | {f"fixtures/{path.name}" for path in (DATASET / "fixtures").glob("*.jsonl")}

    assert set(files) == listed
    changed = [name for name, digest in files.items() if hashlib.sha256((DATASET / name).read_bytes()).hexdigest() != digest]
    assert not changed, f"frozen files changed: {changed}"
