from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from voss.eval import retrieval
from voss.eval.retrieval import EXCLUDED_PATHS, POOL_SIZE, DatasetError, build_pools, chunk_map, main
from voss.harness.code.semantic_index import CodeIndex

CHUNKS = {
    "code:a.py:000": ("a.py", 1, 2, "def alpha():\n    return 1\n"),
    "code:a.py:001": ("a.py", 3, 4, "def beta():\n    return 2\n"),
    "code:b.py:000": ("b.py", 1, 12, "".join(f"line {n} {'x' * 120}\n\n" for n in range(1, 13))),
    "code:c.py:000": ("c.py", 1, 2, "def gamma():\n    return 3\n"),
    "code:d.py:000": ("d.py", 1, 2, "def delta():\n    return 4\n"),
}
POOL_IDS = ["code:a.py:000", "code:b.py:000", "code:c.py:000"]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def write_corpus(root: Path) -> Path:
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "alpha.py").write_text(
        "import os\n\n\ndef merge_rankings(a, b):\n    return a + b\n\n\nclass Fusion:\n    pass\n"
    )
    (root / "pkg" / "beta.py").write_text("def tokenize_text(text):\n    return text.split()\n")
    golden = root / EXCLUDED_PATHS[0]
    golden.parent.mkdir(parents=True)
    golden.write_text('QUERIES = ["merge rankings fusion tokenize text"]\n')
    return root


def fake_pools(corpus_dir, queries, *, require_vector=True):
    return [
        {
            "query_id": query["id"],
            "embedding_model": "test",
            "pool": [
                {"rank": rank, **retrieval._entry(cid, CHUNKS[cid]), "score": 1.0 / rank}
                for rank, cid in enumerate(POOL_IDS, start=1)
            ],
            "bm25": POOL_IDS,
        }
        for query in queries
    ]


def write_queries(root: Path, ids: list[str]) -> None:
    (root / "queries").mkdir(parents=True, exist_ok=True)
    rows = [
        {"id": qid, "group": qid.rsplit("-", 1)[0], "batch": "01", "text": f"where is {qid}",
         "kind": "concept", "synthetic": False, "seed": False, "split": "", "note": ""}
        for qid in ids
    ]
    (root / "queries" / "batch-01.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))


def read_labels(root: Path) -> list[dict]:
    with (root / "labels" / "batch-01.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_labels(root: Path, rows: list[dict]) -> None:
    with (root / "labels" / "batch-01.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=retrieval.LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): p.read_text() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def pinned(monkeypatch, tmp_path):
    monkeypatch.setattr(retrieval, "materialize", lambda commit=retrieval.PINNED_COMMIT: tmp_path / "corpus")
    monkeypatch.setattr(retrieval, "chunk_map", lambda corpus_dir: CHUNKS)
    monkeypatch.setattr(retrieval, "build_pools", fake_pools)


@pytest.fixture
def root(pinned, tmp_path):
    root = tmp_path / "dataset"
    write_queries(root, ["b01-g001-q1", "b01-g002-q1"])
    assert main(["baseline", "--root", str(root), "--batch", "01"]) == 0
    return root


def test_chunk_map_keys_chunks_by_id_with_location_and_text(tmp_path):
    corpus = write_corpus(tmp_path / "corpus")
    chunks = chunk_map(corpus)
    alpha = {cid: chunk for cid, chunk in chunks.items() if chunk[0] == "pkg/alpha.py"}
    assert list(alpha) == [f"code:pkg/alpha.py:{seq:03d}" for seq in range(len(alpha))]
    assert len(alpha) >= 2
    path, start, end, text = alpha["code:pkg/alpha.py:001"]
    assert (path, start) == ("pkg/alpha.py", 4)
    assert end >= start
    assert text.startswith("def merge_rankings")
    assert any(chunk[0] == "pkg/beta.py" for chunk in chunks.values())


def test_build_pools_bm25_only_excludes_golden_file_and_hashes_text(monkeypatch, tmp_path):
    corpus = write_corpus(tmp_path / "corpus")
    monkeypatch.setattr(CodeIndex, "_maybe_semantic", lambda self: None)
    queries = [{"id": "q1", "text": "merge rankings fusion"}, {"id": "q2", "text": "tokenize text"}]
    rows = build_pools(corpus, queries, require_vector=False)
    chunks = chunk_map(corpus)
    assert [row["query_id"] for row in rows] == ["q1", "q2"]
    for row in rows:
        assert 0 < len(row["pool"]) <= POOL_SIZE
        assert [entry["rank"] for entry in row["pool"]] == list(range(1, len(row["pool"]) + 1))
        for entry in row["pool"]:
            path, start, end, text = chunks[entry["chunk_id"]]
            assert (entry["path"], entry["line_start"], entry["line_end"]) == (path, start, end)
            assert entry["text_sha"] == sha(text)
            assert isinstance(entry["score"], float)
            assert entry["path"] not in EXCLUDED_PATHS
        assert row["bm25"]
        assert all(chunks[cid][0] not in EXCLUDED_PATHS for cid in row["bm25"])
    assert rows[0]["pool"][0]["path"] == "pkg/alpha.py"


def test_build_pools_refuses_without_vector_backend(monkeypatch, tmp_path):
    corpus = write_corpus(tmp_path / "corpus")
    monkeypatch.setattr(CodeIndex, "_maybe_semantic", lambda self: None)
    with pytest.raises(DatasetError, match="vector backend unavailable"):
        build_pools(corpus, [{"id": "q1", "text": "merge"}], require_vector=True)


def test_baseline_writes_pools_and_pool_label_rows(root):
    stored = [json.loads(line) for line in (root / "baseline" / "batch-01.jsonl").read_text().splitlines()]
    assert [row["query_id"] for row in stored] == ["b01-g001-q1", "b01-g002-q1"]
    labels = read_labels(root)
    assert [(row["query_id"], row["chunk_id"]) for row in labels] == [
        (qid, cid) for qid in ("b01-g001-q1", "b01-g002-q1") for cid in POOL_IDS
    ]
    assert {(row["source"], row["grade"], row["flag"]) for row in labels} == {("pool", "", "none")}
    assert labels[0]["text_sha"] == sha(CHUNKS[POOL_IDS[0]][3])


def test_baseline_refuses_rerun_without_force(root):
    before = snapshot(root)
    assert main(["baseline", "--root", str(root), "--batch", "01"]) == 2
    assert snapshot(root) == before


def test_baseline_force_keeps_existing_rows_and_appends_new_query(root):
    labels = read_labels(root)
    labels[0].update(grade="necessary", confidence="high", note="kept")
    write_labels(root, labels)
    write_queries(root, ["b01-g001-q1", "b01-g002-q1", "b01-g003-q1"])
    assert main(["baseline", "--root", str(root), "--batch", "01", "--force"]) == 0
    after = read_labels(root)
    assert after[: len(labels)] == labels
    assert [(row["query_id"], row["chunk_id"]) for row in after[len(labels):]] == [
        ("b01-g003-q1", cid) for cid in POOL_IDS
    ]


def test_pool_prints_compact_blocks(root, capsys):
    assert main(["grade", "--root", str(root), "--batch", "01", "--query", "b01-g001-q1", "--grades", "3 0 1"]) == 0
    capsys.readouterr()
    assert main(["pool", "--root", str(root), "--batch", "01", "--query", "b01-g001-q1"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "where is b01-g001-q1"
    assert "1. code:a.py:000 a.py:1-2 [necessary]" in lines
    assert "2. code:b.py:000 b.py:1-12 [irrelevant]" in lines
    block = lines[lines.index("2. code:b.py:000 b.py:1-12 [irrelevant]") + 1:lines.index("3. code:c.py:000 c.py:1-2 [contextual]")]
    assert len(block) == 8
    assert all(len(line.strip()) <= 100 for line in block)


def test_pool_shows_dash_for_ungraded(root, capsys):
    assert main(["pool", "--root", str(root), "--batch", "01", "--query", "b01-g001-q1"]) == 0
    assert "1. code:a.py:000 a.py:1-2 [-]" in capsys.readouterr().out


def test_pool_full_and_path(root, capsys):
    assert main(["pool", "--root", str(root), "--full", "code:b.py:000"]) == 0
    assert capsys.readouterr().out.rstrip("\n") == CHUNKS["code:b.py:000"][3].rstrip("\n")
    assert main(["pool", "--root", str(root), "--path", "a.py"]) == 0
    assert capsys.readouterr().out.splitlines() == ["code:a.py:000 1-2", "code:a.py:001 3-4"]
    assert main(["pool", "--root", str(root), "--full", "code:zzz.py:000"]) == 2


def test_grade_sets_rank_order_grades_and_review_flags(root):
    assert main(["grade", "--root", str(root), "--batch", "01", "--query", "b01-g001-q1", "--grades", "3 2? 0"]) == 0
    rows = {row["chunk_id"]: row for row in read_labels(root) if row["query_id"] == "b01-g001-q1"}
    assert [(rows[cid]["grade"], rows[cid]["confidence"], rows[cid]["flag"]) for cid in POOL_IDS] == [
        ("necessary", "high", "none"),
        ("directly_useful", "low", "review"),
        ("irrelevant", "high", "none"),
    ]
    assert all(row["grade"] == "" for row in read_labels(root) if row["query_id"] == "b01-g002-q1")


@pytest.mark.parametrize("grades", ["3 2", "3 2 0 1", "3 4 0", "3 x 0", "3 ? 0"])
def test_grade_rejects_bad_tokens_without_changes(root, grades):
    before = snapshot(root)
    assert main(["grade", "--root", str(root), "--batch", "01", "--query", "b01-g001-q1", "--grades", grades]) == 2
    assert snapshot(root) == before


def test_grade_extra_adds_gold_row_from_pinned_chunks(root):
    args = ["grade", "--root", str(root), "--batch", "01", "--query", "b01-g001-q1", "--extra", "code:d.py:000=3"]
    assert main(args) == 0
    assert main(args) == 0
    gold = [row for row in read_labels(root) if row["source"] == "gold"]
    assert len(gold) == 1
    assert gold[0] == {
        "query_id": "b01-g001-q1", "chunk_id": "code:d.py:000", "path": "d.py", "line_start": "1",
        "line_end": "2", "text_sha": sha(CHUNKS["code:d.py:000"][3]), "source": "gold",
        "grade": "necessary", "confidence": "high", "flag": "none", "note": "",
    }


def test_grade_extra_rejects_unknown_chunk(root):
    before = snapshot(root)
    assert main([
        "grade", "--root", str(root), "--batch", "01", "--query", "b01-g001-q1",
        "--grades", "3 0 0", "--extra", "code:nope.py:000=3",
    ]) == 2
    assert snapshot(root) == before


def test_grade_ambiguous_flags_every_query_row(root):
    assert main(["grade", "--root", str(root), "--batch", "01", "--query", "b01-g002-q1", "--ambiguous"]) == 0
    flags = {(row["query_id"], row["flag"]) for row in read_labels(root)}
    assert flags == {("b01-g001-q1", "none"), ("b01-g002-q1", "ambiguous")}


def test_review_lists_only_flagged_rows_with_counts(root):
    main(["grade", "--root", str(root), "--batch", "01", "--query", "b01-g001-q1", "--grades", "3 1? 0"])
    main(["grade", "--root", str(root), "--batch", "01", "--query", "b01-g002-q1", "--ambiguous"])
    assert main(["review", "--root", str(root)]) == 0
    text = (root / "REVIEW.md").read_text()
    assert "| 01 | 6 | 3 | 1 | 1 |" in text
    assert "## b01-g001-q1" in text
    assert "> where is b01-g001-q1" in text
    assert "`code:b.py:000` b.py:1-12; proposed `contextual`; edit `labels/batch-01.csv`" in text
    assert "line 8 " in text and "line 9 " not in text
    assert "code:a.py:000" not in text
    assert "b01-g002-q1" not in text


def test_review_without_flags_says_so(root):
    assert main(["review", "--root", str(root)]) == 0
    assert "No rows need review" in (root / "REVIEW.md").read_text()


def test_check_passes_on_complete_batch(root):
    for qid in ("b01-g001-q1", "b01-g002-q1"):
        main(["grade", "--root", str(root), "--batch", "01", "--query", qid, "--grades", "3 0 1"])
    assert main(["check", "--root", str(root), "--batch", "01"]) == 0


def test_check_lists_every_problem(root, capsys):
    main(["grade", "--root", str(root), "--batch", "01", "--query", "b01-g001-q1", "--grades", "3 0 1"])
    rows = read_labels(root)
    rows[0]["text_sha"] = "f" * 12
    rows[1]["flag"] = "maybe"
    rows = [row for row in rows if (row["query_id"], row["chunk_id"]) != ("b01-g002-q1", "code:c.py:000")]
    write_labels(root, rows)
    capsys.readouterr()
    assert main(["check", "--root", str(root), "--batch", "01"]) == 1
    out = capsys.readouterr().out
    assert "b01-g001-q1/code:a.py:000: text_sha mismatch" in out
    assert "b01-g001-q1/code:b.py:000: bad flag 'maybe'" in out
    assert "b01-g002-q1/code:a.py:000: ungraded" in out
    assert "b01-g002-q1/code:c.py:000: pool chunk has no label row" in out
