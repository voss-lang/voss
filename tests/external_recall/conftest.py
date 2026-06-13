"""Shared fixtures for the V22 external recall RED suite.

Imports of the planned V22 module `voss.harness.recall.external_index` are
deferred into fixture/test bodies so pytest collection succeeds before the
implementation exists. Runtime ImportError/NotImplementedError is the RED
signal for later V22 waves.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

SOURCE_NAME = "docs"


@pytest.fixture
def fake_embed_fn(monkeypatch):
    """Patch SemanticMemory onto Chroma's bundled DefaultEmbeddingFunction.

    ONNX, no network, no MiniLM download. Skips when chromadb is absent
    (the optional `voss[search]` dep) - pattern from tests/memory/test_semantic.py.
    """
    try:
        from chromadb.utils import embedding_functions
    except Exception:
        pytest.skip("chromadb DefaultEmbeddingFunction unavailable")
    fn = embedding_functions.DefaultEmbeddingFunction()

    from voss_runtime.memory.semantic import SemanticMemory

    monkeypatch.setattr(SemanticMemory, "_embedding_function", lambda self: fn)
    return fn


@pytest.fixture
def chroma_disabled_env(monkeypatch):
    """Force the chromadb-absent path for BM25-only degradation tests."""
    import sys

    monkeypatch.setitem(sys.modules, "chromadb", None)

    from voss_runtime.memory import semantic as _semantic

    def _raise(self, *args, **kwargs):
        raise ModuleNotFoundError("No module named 'chromadb'")

    monkeypatch.setattr(_semantic.SemanticMemory, "__init__", _raise)
    return monkeypatch


@pytest.fixture
def fixture_vault_path() -> Path:
    """Return the committed V22 fixture vault path owned by Worker B."""
    return Path(__file__).parent.parent / "fixtures" / "recall_vault"


def _toml_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_config_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sources: list[dict[str, str]] | None = None,
    *,
    body: str | None = None,
) -> Path:
    """Write XDG config.toml with `[[recall.sources]]` entries."""
    config_home = tmp_path / "xdg"
    config_dir = config_home / "voss"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.toml"

    if body is None:
        lines: list[str] = []
        for source in sources or []:
            lines.append("[[recall.sources]]")
            lines.append(f'name = "{_toml_quote(source["name"])}"')
            lines.append(f'path = "{_toml_quote(source["path"])}"')
            if "glob" in source:
                lines.append(f'glob = "{_toml_quote(source["glob"])}"')
            lines.append("")
        body = "\n".join(lines)

    config_path.write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    return config_path


@pytest.fixture
def indexed_fixture_vault(tmp_path, fixture_vault_path, fake_embed_fn):
    """Copy the fixture vault into tmp_path and build one external source.

    VXMEM-03/05/08 tests need a source path, source dict, and built index.
    The ExternalSourceIndex import is intentionally deferred into this fixture.
    """
    vault = tmp_path / "recall_vault"
    shutil.copytree(fixture_vault_path, vault)
    source = {"name": SOURCE_NAME, "path": str(vault), "glob": "**/*.md"}

    from voss.harness.recall.external_index import ExternalSourceIndex

    index = ExternalSourceIndex(tmp_path, source)
    index.build()
    return SimpleNamespace(cwd=tmp_path, path=vault, source=source, index=index)
