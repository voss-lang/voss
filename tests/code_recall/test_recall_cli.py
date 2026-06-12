"""VSEM-05 RED tests: `voss recall` exits 0 with labeled hits; --json honors
the documented schema and leaks no secrets (threat T-V19-04).

In-process click CliRunner so the fake-embed monkeypatch applies to the
command's own SemanticMemory construction.
"""
from __future__ import annotations

import json

from click.testing import CliRunner

from .conftest import write_fixture_repo

SECRET_VALUE = "AKIAIOSFODNN7EXAMPLEKEY"


def _repo_with_secret(tmp_path):
    write_fixture_repo(tmp_path)
    (tmp_path / "settings.py").write_text(
        '"""Settings module holding service credentials."""\n'
        "\n"
        f'API_KEY = "{SECRET_VALUE}"\n'
        'SERVICE_URL = "https://example.invalid/api"\n'
    )

    from voss.harness.code.index import build_index

    build_index(tmp_path)

    from voss.harness.code.semantic_index import CodeIndex

    CodeIndex(tmp_path).build(session_id="test-session")
    return tmp_path


def test_exit_0_labeled(indexed_fixture_repo):
    """`voss recall <q>` exits 0; every hit labeled [code] or [memory]."""
    from voss.cli import main

    result = CliRunner().invoke(
        main,
        ["recall", "retry backoff delay", "--cwd", str(indexed_fixture_repo)],
    )

    assert result.exit_code == 0, result.output
    labeled = [
        line
        for line in result.output.splitlines()
        if line.startswith("[code]") or line.startswith("[memory]")
    ]
    assert labeled, f"expected [code]/[memory]-labeled hits, got:\n{result.output}"


def test_json_schema(tmp_path, fake_embed_fn):
    """--json output carries the documented schema (source field per hit) and
    contains NO secret/key strings from indexed files (T-V19-04)."""
    repo = _repo_with_secret(tmp_path)

    from voss.cli import main

    result = CliRunner().invoke(
        main,
        ["recall", "api key service credentials", "--json", "--cwd", str(repo)],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    hits = payload["hits"] if isinstance(payload, dict) else payload
    assert isinstance(hits, list)
    assert hits, "query against the secret-bearing fixture must return hits"
    for hit in hits:
        assert hit["source"] in ("code", "memory")
        assert "locator" in hit
        assert "score" in hit

    assert SECRET_VALUE not in result.output, (
        "JSON output must never include secret values from indexed files"
    )
