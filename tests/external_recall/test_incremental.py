"""VXMEM-03/05 RED tests for derived external recall caches."""
from __future__ import annotations

import json
import shutil

import pytest


@pytest.fixture
def counting_embed(monkeypatch):
    """Embedding function that records every text Chroma asks to embed."""
    try:
        from chromadb.utils import embedding_functions
    except Exception:
        pytest.skip("chromadb DefaultEmbeddingFunction unavailable")

    class CountingEmbed(embedding_functions.EmbeddingFunction):
        def __init__(self) -> None:
            self._inner = embedding_functions.DefaultEmbeddingFunction()
            self.embedded_texts: list[str] = []

        def __call__(self, input):  # noqa: A002 - chroma's parameter name
            self.embedded_texts.extend(str(t) for t in input)
            return self._inner(input)

    fn = CountingEmbed()

    from voss_runtime.memory.semantic import SemanticMemory

    monkeypatch.setattr(SemanticMemory, "_embedding_function", lambda self: fn)
    return fn


def _copy_vault(tmp_path, fixture_vault_path):
    vault = tmp_path / "recall_vault"
    shutil.copytree(fixture_vault_path, vault)
    source = {"name": "docs", "path": str(vault), "glob": "**/*.md"}
    return vault, source


def _build_vault(tmp_path, fixture_vault_path):
    vault, source = _copy_vault(tmp_path, fixture_vault_path)

    from voss.harness.recall.external_index import ExternalSourceIndex

    index = ExternalSourceIndex(tmp_path, source)
    index.build()
    return vault, source, index


def _manifest_path(cwd):
    return cwd / ".voss-cache" / "recall" / "docs" / "semantic-manifest.json"


def test_derived_cache_rm_safe(indexed_fixture_vault):
    """VXMEM-03: `.voss-cache/recall` is derived and rebuildable."""
    shutil.rmtree(indexed_fixture_vault.cwd / ".voss-cache" / "recall")

    try:
        from chromadb.api.client import SharedSystemClient
    except Exception:
        SharedSystemClient = None
    if SharedSystemClient is not None:
        SharedSystemClient.clear_system_cache()

    from voss.harness.recall.external_index import ExternalSourceIndex

    index = ExternalSourceIndex(indexed_fixture_vault.cwd, indexed_fixture_vault.source)
    index.build()
    hits = index.query("installation quickstart setup", top_k=5)

    assert hits, "rebuilt external index must answer fixture-vault queries"
    assert any("getting-started.md" in h.locator for h in hits)


def test_manifest_has_hash_per_file(indexed_fixture_vault):
    """VXMEM-03: manifest records a content hash for every ingested md file."""
    manifest = json.loads(_manifest_path(indexed_fixture_vault.cwd).read_text())
    files = manifest["files"]
    expected = {
        str(path.relative_to(indexed_fixture_vault.path))
        for path in indexed_fixture_vault.path.rglob("*.md")
    }

    assert set(files) == expected
    assert expected, "fixture vault must include markdown files"
    for record in files.values():
        assert record["hash"]
        assert record["chunk_ids"]


def test_touch_one_file_reembeds_only_it(tmp_path, fixture_vault_path, counting_embed):
    """VXMEM-05: touching one source file re-embeds only that file's chunks."""
    vault, _source, index = _build_vault(tmp_path, fixture_vault_path)
    counting_embed.embedded_texts.clear()

    target = vault / "getting-started.md"
    target.write_text(
        target.read_text()
        + "\n## Troubleshooting\n"
        + "Reembedded sentinel quickstart installation phrase.\n"
    )
    index.build()

    assert counting_embed.embedded_texts, "changed file must re-embed"
    assert any("Reembedded sentinel" in t for t in counting_embed.embedded_texts)
    for text in counting_embed.embedded_texts:
        assert "GET /users" not in text, "unchanged api-reference.md must not re-embed"
        assert "# v2.0" not in text, "unchanged changelog.md must not re-embed"


def test_unchanged_zero_embeds(tmp_path, fixture_vault_path, counting_embed):
    """VXMEM-05: rebuilding an unchanged vault performs zero embed calls."""
    _vault, _source, index = _build_vault(tmp_path, fixture_vault_path)
    counting_embed.embedded_texts.clear()

    index.build()

    assert counting_embed.embedded_texts == []


def test_deleted_file_purges_chunks(tmp_path, fixture_vault_path, counting_embed):
    """VXMEM-05: deleted source files are purged from manifest and results."""
    vault, _source, index = _build_vault(tmp_path, fixture_vault_path)
    assert index.query("endpoint authentication rate limit", top_k=5)

    (vault / "api-reference.md").unlink()
    index.build()

    manifest = json.loads(_manifest_path(tmp_path).read_text())
    assert "api-reference.md" not in manifest["files"]
    hits = index.query("endpoint authentication rate limit users", top_k=5)
    assert all("api-reference.md" not in h.locator for h in hits)
