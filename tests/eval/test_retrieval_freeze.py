from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.eval.test_retrieval_loader import POOL, label, query, write_dataset
from voss.eval import retrieval
from voss.eval.retrieval import (
    BOOTSTRAP_B,
    BOOTSTRAP_SEED,
    K,
    LABEL_FIELDS,
    NDCG_GAIN_MIN,
    RECALL_DROP_MAX,
    main,
)

CHUNKS = {cid: (cid.split(":")[1], 1, 9, f"text of {cid}\n") for cid in POOL}
QUERY_IDS = [
    "b01-g001-q1", "b01-g001-q2", "b01-g002-q1", "b01-g003-q1", "b01-g004-q1",
    "b02-g001-q1", "b02-g002-q1", "b02-g003-q1", "b02-g004-q1",
]
ADVERSARIAL = {"b02-g001", "b02-g002"}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def unfrozen(root: Path) -> Path:
    queries = [
        query(qid, "", kind="adversarial" if qid.rsplit("-", 1)[0] in ADVERSARIAL else "concept")
        for qid in QUERY_IDS
    ]
    labels = [
        {**label(qid, cid, "necessary" if rank == 0 else "irrelevant"), "text_sha": sha(CHUNKS[cid][3])}
        for qid in QUERY_IDS
        for rank, cid in enumerate(POOL)
    ]
    return write_dataset(root, queries=queries, labels=labels)


def edit_labels(root: Path, batch: str, change) -> None:
    path = root / "labels" / f"batch-{batch}.csv"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    change(rows)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_queries(root: Path) -> list[dict]:
    return [
        json.loads(line)
        for path in sorted((root / "queries").glob("*.jsonl"))
        for line in path.read_text().splitlines()
    ]


def group_splits(root: Path) -> dict[str, str]:
    splits: dict[str, set[str]] = {}
    for row in read_queries(root):
        splits.setdefault(row["group"], set()).add(row["split"])
    assert all(len(values) == 1 for values in splits.values())
    return {group: values.pop() for group, values in splits.items()}


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def run_freeze(root: Path, *extra: str) -> int:
    return main(["freeze", "--root", str(root), "--expect-groups", "8", *extra])


@pytest.fixture(autouse=True)
def pinned(monkeypatch):
    monkeypatch.setattr(retrieval, "_pinned_chunks", lambda: CHUNKS)


def test_freeze_assigns_whole_groups_evenly_within_kind(tmp_path):
    root = unfrozen(tmp_path)
    before = read_queries(root)

    assert run_freeze(root) == 0

    splits = group_splits(root)
    assert Counter(splits.values()) == {"dev": 4, "test": 4}
    assert Counter(splits[group] for group in ADVERSARIAL) == {"dev": 1, "test": 1}
    assert Counter(split for group, split in splits.items() if group not in ADVERSARIAL) == {"dev": 3, "test": 3}
    after = read_queries(root)
    assert [row["id"] for row in after] == [row["id"] for row in before]
    assert [{**row, "split": ""} for row in after] == before


def test_freeze_is_reproducible_for_the_same_seed(tmp_path):
    first, second = unfrozen(tmp_path / "a"), unfrozen(tmp_path / "b")

    assert run_freeze(first) == 0
    assert run_freeze(second) == 0

    assert group_splits(first) == group_splits(second)


def test_freeze_writes_metrics_thresholds_counts_and_hashes(tmp_path, capsys):
    root = unfrozen(tmp_path)

    assert run_freeze(root) == 0

    frozen = json.loads((root / "freeze.json").read_text())
    assert frozen["frozen_at"] == datetime.now(timezone.utc).date().isoformat()
    assert frozen["commit"] == "a" * 40
    assert frozen["seed"] == BOOTSTRAP_SEED
    queries_per_split = Counter(row["split"] for row in read_queries(root))
    assert frozen["splits"] == {
        split: {"groups": 4, "queries": queries_per_split[split], "adversarial_groups": 1, "ambiguous_groups": 0}
        for split in ("dev", "test")
    }
    assert frozen["metrics"]["k"] == K
    assert frozen["metrics"]["ndcg"]["gain"] == "2^g-1"
    assert frozen["metrics"]["ndcg"]["discount"] == "1/log2(rank+1)"
    assert "directly_useful or necessary" in frozen["metrics"]["recall"]
    assert frozen["metrics"]["bootstrap"] == {
        "method": "paired percentile", "b": BOOTSTRAP_B, "seed": BOOTSTRAP_SEED, "unit": "group", "alpha": 0.05,
    }
    assert frozen["thresholds"] == {
        "ndcg_gain_min": NDCG_GAIN_MIN, "ci": "lower bound > 0", "recall_drop_max": RECALL_DROP_MAX,
    }
    expected = {"corpus.json"} | {
        f"{sub}/batch-{batch}.{ext}"
        for sub, ext in (("queries", "jsonl"), ("baseline", "jsonl"), ("labels", "csv"))
        for batch in ("01", "02")
    }
    assert set(frozen["files"]) == expected
    for name, digest in frozen["files"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
    out = capsys.readouterr().out
    assert "dev: 4 groups" in out and "test: 4 groups" in out
    assert "ndcg" not in out.lower()


@pytest.mark.parametrize(
    ("change", "extra"),
    [
        (lambda root: edit_labels(root, "01", lambda rows: rows[0].update(flag="review")), ()),
        (lambda root: edit_labels(root, "02", lambda rows: rows[1].update(grade="")), ()),
        (lambda root: None, ("--expect-groups", "9")),
        (lambda root: (root / "freeze.json").write_text("{}\n"), ()),
    ],
    ids=["flagged-row", "check-fails", "group-count", "already-frozen"],
)
def test_freeze_refuses_without_writing(tmp_path, change, extra):
    root = unfrozen(tmp_path)
    change(root)
    before = snapshot(root)

    assert run_freeze(root, *extra) == 1

    assert snapshot(root) == before
