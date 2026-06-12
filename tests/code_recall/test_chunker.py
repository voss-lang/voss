"""VSEM-01 RED tests: symbol-boundary chunking + derived-cache rebuild.

Wave-0 scaffold (V19-01). Imports of voss.harness.code.semantic_index live
inside test bodies: ModuleNotFoundError IS the RED signal until V19-02 lands.
"""
from __future__ import annotations

import shutil

from .conftest import write_fixture_repo


def _db_path(root):
    return root / ".voss-cache" / "code" / "index.db"


def test_chunks_split_on_symbol_boundaries(tmp_path):
    """Multi-symbol file yields one chunk per [symbol_start, next_start) region."""
    src = tmp_path / "foo.py"
    src.write_text("def alpha():\n    pass\n\ndef beta():\n    pass\n")

    from voss.harness.code.index import build_index

    build_index(tmp_path)

    from voss.harness.code.semantic_index import extract_chunks

    chunks = extract_chunks(_db_path(tmp_path), "foo.py", src.read_text())
    assert len(chunks) == 2
    line_start_0, line_end_0, text_0 = chunks[0]
    line_start_1, line_end_1, text_1 = chunks[1]
    assert line_start_0 == 1
    assert "alpha" in text_0
    assert line_start_1 == 4
    assert "beta" in text_1
    assert line_end_0 < line_start_1


def test_zero_symbol_file_single_chunk(tmp_path):
    """Pitfall 6: file with no symbols yields exactly one whole-file chunk."""
    src = tmp_path / "data.py"
    content = "# constants only\nX = 1\nY = 2\nZ = 3\n"
    src.write_text(content)

    from voss.harness.code.index import build_index

    build_index(tmp_path)

    from voss.harness.code.semantic_index import extract_chunks

    chunks = extract_chunks(_db_path(tmp_path), "data.py", content)
    assert len(chunks) == 1
    line_start, line_end, text = chunks[0]
    assert line_start == 1
    assert line_end >= 4
    assert "X = 1" in text


def test_oversize_chunk_split(tmp_path):
    """Pitfall 5: >800-char symbol region splits into sub-chunks with
    distinct code:<path>:<seq> ids."""
    body = "\n".join(f"    value_{i} = 'padding padding padding'" for i in range(60))
    content = f"def big():\n{body}\n"
    assert len(content) > 800
    src = tmp_path / "big.py"
    src.write_text(content)

    from voss.harness.code.index import build_index

    build_index(tmp_path)

    from voss.harness.code.semantic_index import _chunk_id, extract_chunks

    chunks = extract_chunks(_db_path(tmp_path), "big.py", content)
    assert len(chunks) >= 2, "oversize region must split into sub-chunks"

    ids = [_chunk_id("big.py", seq) for seq in range(len(chunks))]
    assert ids[0] == "code:big.py:000"
    assert len(set(ids)) == len(ids), "sub-chunk ids must be distinct"


def test_derived_cache(tmp_path, fake_embed_fn):
    """VSEM-01 acceptance: rm .voss-cache + rebuild reproduces a working
    index from the repo alone (the index is a derived cache, never source)."""
    write_fixture_repo(tmp_path)

    from voss.harness.code.index import build_index
    from voss.harness.code.semantic_index import CodeIndex

    build_index(tmp_path)
    CodeIndex(tmp_path).build(session_id="test-session")

    shutil.rmtree(tmp_path / ".voss-cache")

    # Same-process artifact only: chroma caches its System per persist path,
    # so the deleted dir's sqlite handle dangles. A real `rm -rf` + fresh
    # process never needs this.
    from chromadb.api.client import SharedSystemClient

    SharedSystemClient.clear_system_cache()

    build_index(tmp_path)
    index = CodeIndex(tmp_path)
    index.build(session_id="test-session")
    hits = index.query("retry backoff delay", top_k=5)
    assert hits, "rebuilt index must answer queries"
    assert any("alpha" in h.locator for h in hits)
