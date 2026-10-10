from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from voss.eval.retrieval import (
    NDCG_GAIN_MIN,
    PINNED_COMMIT,
    RECALL_DROP_MAX,
    LockedSplitError,
    load_dataset,
)

DATASET = Path(__file__).resolve().parents[2] / "evals" / "retrieval"


def frozen() -> dict:
    return json.loads((DATASET / "freeze.json").read_text())


def query_rows() -> list[dict]:
    return [
        json.loads(line)
        for path in sorted((DATASET / "queries").glob("*.jsonl"))
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def test_every_frozen_file_matches_its_sha256():
    files = frozen()["files"]
    listed = {"corpus.json"} | {
        path.relative_to(DATASET).as_posix()
        for sub in ("queries", "baseline", "labels")
        for path in (DATASET / sub).rglob("*")
        if path.is_file()
    }

    assert set(files) == listed
    changed = [name for name, digest in files.items() if hashlib.sha256((DATASET / name).read_bytes()).hexdigest() != digest]
    assert not changed, f"frozen files changed: {changed}"


def test_corpus_commit_is_pinned_and_frozen():
    corpus = json.loads((DATASET / "corpus.json").read_text())

    assert corpus["commit"] == PINNED_COMMIT == frozen()["commit"]


def test_split_metadata_is_100_groups_each_and_constant_within_groups():
    splits: dict[str, set[str]] = {}
    for row in query_rows():
        splits.setdefault(row["group"], set()).add(row["split"])

    assert len(splits) == 200
    assert all(len(values) == 1 for values in splits.values())
    assert Counter(next(iter(values)) for values in splits.values()) == {"dev": 100, "test": 100}
    assert {split: counts["groups"] for split, counts in frozen()["splits"].items()} == {"dev": 100, "test": 100}


def test_default_load_is_dev_only_and_scores_exclude_ambiguous():
    dev_ids = {row["id"] for row in query_rows() if row["split"] == "dev"}
    dataset = load_dataset(DATASET)

    assert dataset.split == "dev"
    assert set(dataset.queries) == dev_ids
    assert set(dataset.scored_queries) == dev_ids - set(dataset.ambiguous)
    assert not set(dataset.scored_queries) & set(dataset.ambiguous)


def test_test_split_stays_locked():
    with pytest.raises(LockedSplitError):
        load_dataset(DATASET, split="test")


def test_frozen_thresholds_match_module_constants():
    thresholds = frozen()["thresholds"]

    assert thresholds["ndcg_gain_min"] == NDCG_GAIN_MIN
    assert thresholds["recall_drop_max"] == RECALL_DROP_MAX
    assert thresholds["ci"] == "lower bound > 0"
