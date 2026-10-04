from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from voss.eval.retrieval import DatasetError, LockedSplitError, load_dataset

LABEL_FIELDS = [
    "query_id", "chunk_id", "path", "line_start", "line_end", "text_sha",
    "source", "grade", "confidence", "flag", "note",
]
POOL = [f"code:{name}.py:000" for name in "abcdef"]


def query(qid: str, split: str, kind: str = "concept") -> dict:
    group = qid.rsplit("-", 1)[0]
    return {
        "id": qid, "group": group, "batch": qid[1:3], "text": f"where is {qid}",
        "kind": kind, "synthetic": kind == "adversarial", "seed": False, "split": split, "note": "",
    }


def label(qid: str, chunk: str, grade: str, *, source: str = "pool", flag: str = "none") -> dict:
    return {
        "query_id": qid, "chunk_id": chunk, "path": chunk.split(":")[1], "line_start": 1,
        "line_end": 9, "text_sha": "0" * 12, "source": source, "grade": grade,
        "confidence": "high", "flag": flag, "note": "",
    }


def default_queries() -> list[dict]:
    return [
        query("b01-g001-q1", "dev"),
        query("b01-g001-q2", "dev"),
        query("b01-g002-q1", "test"),
        query("b02-g001-q1", "dev", kind="adversarial"),
        query("b02-g002-q1", "test"),
    ]


def default_labels() -> list[dict]:
    return [
        label("b01-g001-q1", POOL[0], "necessary"),
        label("b01-g001-q1", POOL[1], "irrelevant"),
        label("b01-g001-q2", POOL[0], "directly_useful"),
        label("b01-g001-q2", "code:z.py:000", "necessary", source="gold"),
        label("b01-g002-q1", POOL[0], "necessary"),
        label("b02-g001-q1", POOL[2], "contextual"),
        label("b02-g002-q1", POOL[3], "directly_useful"),
    ]


def write_dataset(root: Path, queries: list[dict] | None = None, labels: list[dict] | None = None) -> Path:
    queries = default_queries() if queries is None else queries
    labels = default_labels() if labels is None else labels
    for sub in ("queries", "baseline", "labels"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    (root / "corpus.json").write_text(json.dumps({"repo": "voss", "commit": "a" * 40, "pool_size": 15}))
    for batch in sorted({row["batch"] for row in queries}):
        rows = [row for row in queries if row["batch"] == batch]
        (root / "queries" / f"batch-{batch}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows)
        )
        pools = [
            {
                "query_id": row["id"],
                "embedding_model": "test",
                "pool": [
                    {"rank": rank, "chunk_id": chunk, "path": chunk.split(":")[1], "line_start": 1,
                     "line_end": 9, "text_sha": "0" * 12, "score": 1.0 / rank}
                    for rank, chunk in enumerate(POOL, start=1)
                ],
                "bm25": POOL,
            }
            for row in rows
        ]
        (root / "baseline" / f"batch-{batch}.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in pools)
        )
        with (root / "labels" / f"batch-{batch}.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=LABEL_FIELDS)
            writer.writeheader()
            writer.writerows(row for row in labels if row["query_id"][1:3] == batch)
    return root


def test_default_load_returns_only_dev_queries(tmp_path: Path) -> None:
    dataset = load_dataset(write_dataset(tmp_path))

    assert dataset.split == "dev"
    assert set(dataset.queries) == {"b01-g001-q1", "b01-g001-q2", "b02-g001-q1"}
    assert set(dataset.labels) == set(dataset.queries)
    assert dataset.labels["b01-g001-q1"] == {POOL[0]: 3, POOL[1]: 0}
    assert dataset.labels["b01-g001-q2"] == {POOL[0]: 2, "code:z.py:000": 3}
    assert dataset.pools["b01-g001-q1"] == POOL
    assert set(dataset.pools) == set(dataset.queries)
    assert dataset.chunk_paths["code:z.py:000"] == "z.py"
    assert dataset.group_of == {
        "b01-g001-q1": "b01-g001", "b01-g001-q2": "b01-g001", "b02-g001-q1": "b02-g001",
    }
    assert dataset.adversarial == ("b02-g001-q1",)
    assert dataset.ambiguous == ()
    assert dataset.scored_queries == ("b01-g001-q1", "b01-g001-q2", "b02-g001-q1")


def test_test_split_requires_locked_final(tmp_path: Path) -> None:
    root = write_dataset(tmp_path)

    with pytest.raises(LockedSplitError):
        load_dataset(root, split="test")

    dataset = load_dataset(root, split="test", locked_final=True)
    assert set(dataset.queries) == {"b01-g002-q1", "b02-g002-q1"}
    assert dataset.labels["b01-g002-q1"] == {POOL[0]: 3}


def test_default_load_never_parses_test_split_labels(tmp_path: Path) -> None:
    labels = default_labels() + [label("b01-g002-q1", POOL[1], "BAD")]
    root = write_dataset(tmp_path, labels=labels)

    dataset = load_dataset(root)
    assert "b01-g002-q1" not in dataset.labels

    with pytest.raises(DatasetError, match="b01-g002-q1"):
        load_dataset(root, split="test", locked_final=True)


def test_ambiguous_queries_are_listed_and_not_scored(tmp_path: Path) -> None:
    labels = default_labels() + [label("b01-g001-q2", POOL[1], "contextual", flag="ambiguous")]
    dataset = load_dataset(write_dataset(tmp_path, labels=labels))

    assert dataset.ambiguous == ("b01-g001-q2",)
    assert dataset.scored_queries == ("b01-g001-q1", "b02-g001-q1")


@pytest.mark.parametrize(
    ("queries", "labels", "match"),
    [
        (None, default_labels() + [label("b01-g001-q1", POOL[2], "great")], r"batch-01\.csv: b01-g001-q1"),
        (default_queries() + [query("b01-g001-q1", "dev")], None, r"batch-01\.jsonl: duplicate query id b01-g001-q1"),
        (default_queries() + [query("b01-g001-q3", "test")], None, r"batch-01\.jsonl: b01-g001-q3: group b01-g001"),
        (None, default_labels() + [label("b02-g001-q1", "code:q.py:000", "necessary")], r"batch-02\.csv: b02-g001-q1"),
    ],
    ids=["unknown-grade", "duplicate-id", "group-spans-splits", "chunk-not-in-pool"],
)
def test_invalid_rows_raise_dataset_error(tmp_path: Path, queries, labels, match: str) -> None:
    root = write_dataset(tmp_path, queries=queries, labels=labels)

    with pytest.raises(DatasetError, match=match):
        load_dataset(root)


def test_unfrozen_split_is_rejected(tmp_path: Path) -> None:
    root = write_dataset(tmp_path, queries=default_queries() + [query("b02-g003-q1", "")])

    with pytest.raises(DatasetError, match="dataset not frozen"):
        load_dataset(root)
