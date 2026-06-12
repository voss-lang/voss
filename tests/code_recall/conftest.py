"""Shared fixtures for the V19 semantic-code-memory suite (tests/code_recall/).

Wave-0 RED scaffold (V19-01). Imports of the planned Wave-1+ module
`voss.harness.code.semantic_index` are deferred into fixture/test bodies so
pytest COLLECTION succeeds before the module exists — the ImportError at
runtime IS the RED signal (never fabricate a fake module API to dodge it).

Planned API these fixtures pin (see V19-01-PLAN.md <interfaces>):
    from voss.harness.code.semantic_index import CodeIndex, CodeIndexService
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Fixture repo: 3 small .py files with known symbol boundaries. alpha/beta
# carry distinct vocab so golden-style queries can discriminate files.
FIXTURE_FILES: dict[str, str] = {
    "alpha.py": (
        '"""Alpha module: retry backoff helpers."""\n'
        "\n"
        "\n"
        "def alpha_retry_backoff(attempt: int) -> float:\n"
        '    """Exponential backoff delay for a retry attempt."""\n'
        "    return min(2.0 ** attempt, 30.0)\n"
        "\n"
        "\n"
        "def alpha_helper() -> str:\n"
        '    """Greeting used by chunk-boundary tests."""\n'
        '    return "alpha"\n'
    ),
    "beta.py": (
        '"""Beta module: json serialization utilities."""\n'
        "\n"
        "\n"
        "def beta_serialize(payload: dict) -> str:\n"
        '    """Serialize a payload dict to a json string."""\n'
        "    import json\n"
        "    return json.dumps(payload, sort_keys=True)\n"
        "\n"
        "\n"
        "class BetaCodec:\n"
        '    """Round-trip codec for beta payloads."""\n'
        "\n"
        "    def decode(self, raw: str) -> dict:\n"
        "        import json\n"
        "        return json.loads(raw)\n"
    ),
    "gamma.py": (
        '"""Gamma module: filesystem cache eviction."""\n'
        "\n"
        "\n"
        "def gamma_evict_cache(root) -> int:\n"
        '    """Evict stale cache entries under root, return count."""\n'
        "    count = 0\n"
        "    for child in root.glob('*.tmp'):\n"
        "        child.unlink()\n"
        "        count += 1\n"
        "    return count\n"
    ),
}


def write_fixture_repo(root: Path) -> Path:
    """Materialize FIXTURE_FILES under root and return root."""
    for name, content in FIXTURE_FILES.items():
        (root / name).write_text(content)
    return root


@pytest.fixture
def fake_embed_fn(monkeypatch):
    """Patch SemanticMemory onto Chroma's bundled DefaultEmbeddingFunction.

    ONNX, no network, no MiniLM download. Skips when chromadb is absent
    (the optional `voss[search]` dep) — pattern from tests/memory/test_semantic.py.
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
def indexed_fixture_repo(tmp_path, fake_embed_fn):
    """Fixture repo with the M10 SQLite index AND the V19 chroma index built.

    Passes a DETERMINISTIC session_id so enrichment-ledger tests can assert
    rows land at the /cost-readable session-scoped path (never
    .voss/sessions/None/).
    """
    write_fixture_repo(tmp_path)

    from voss.harness.code.index import build_index

    build_index(tmp_path)

    # Planned Wave-1 API — RED (ModuleNotFoundError) until V19-02 lands.
    from voss.harness.code.semantic_index import CodeIndex

    CodeIndex(tmp_path).build(session_id="test-session")
    return tmp_path


@pytest.fixture
def chroma_disabled_env(monkeypatch):
    """Force the chromadb-absent path: SemanticMemory construction raises
    ModuleNotFoundError, so CodeIndex._maybe_semantic must degrade to BM25.
    """
    import sys

    monkeypatch.setitem(sys.modules, "chromadb", None)

    from voss_runtime.memory import semantic as _semantic

    def _raise(self, *args, **kwargs):
        raise ModuleNotFoundError("No module named 'chromadb'")

    monkeypatch.setattr(_semantic.SemanticMemory, "__init__", _raise)
    return monkeypatch


class ProviderCallRecorder:
    """Recording stub substituted for the enrichment provider build path."""

    def __init__(self) -> None:
        self.call_count = 0
        self.calls: list[dict] = []
        self.models: list[str] = []


@pytest.fixture
def stub_provider(monkeypatch):
    """Replace voss.harness.model_router.build_provider_for_model with a recorder.

    VSEM-07/08 tests assert call_count semantics: profile-off builds must
    leave call_count at 0; profile-on builds must record only the
    index_enrich role's model. Implementations MUST resolve the builder via
    the model_router module attribute (not a from-import binding) so this
    interception holds.
    """
    from voss.harness import model_router

    rec = ProviderCallRecorder()

    class _NullProvider:
        def __getattr__(self, name):
            def _call(*args, **kwargs):
                return None

            return _call

    def _stub_build(entry, *, api_key=None):
        model_id = getattr(entry, "id", str(entry))
        rec.call_count += 1
        rec.models.append(model_id)
        rec.calls.append({"model": model_id, "api_key": api_key})
        return _NullProvider(), model_id

    monkeypatch.setattr(model_router, "build_provider_for_model", _stub_build)
    return rec
