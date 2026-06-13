"""VXMEM-07 RED tests for `voss recall` external-source fan-out."""
from __future__ import annotations

import json

from click.testing import CliRunner

from .conftest import write_config_toml


def test_plain_labeled_hits(indexed_fixture_vault, monkeypatch):
    """VXMEM-07: plain recall output renders external hits as `[<name>]`."""
    write_config_toml(
        indexed_fixture_vault.cwd,
        monkeypatch,
        [indexed_fixture_vault.source],
    )

    from voss.cli import main

    result = CliRunner().invoke(
        main,
        [
            "recall",
            "--cwd",
            str(indexed_fixture_vault.cwd),
            "--refresh",
            "installation",
            "quickstart",
            "setup",
        ],
    )

    assert result.exit_code == 0, result.output
    assert any(line.startswith("[docs]") for line in result.output.splitlines())


def test_json_source_field(indexed_fixture_vault, monkeypatch):
    """VXMEM-07: JSON output preserves the true external source field."""
    write_config_toml(
        indexed_fixture_vault.cwd,
        monkeypatch,
        [indexed_fixture_vault.source],
    )

    from voss.cli import main

    result = CliRunner().invoke(
        main,
        [
            "recall",
            "--cwd",
            str(indexed_fixture_vault.cwd),
            "--json",
            "endpoint",
            "authentication",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    hits = payload["hits"]
    assert hits
    assert any(hit["source"] == "docs" for hit in hits)
    for hit in hits:
        assert "locator" in hit
        assert "score" in hit


def test_degradation_no_chromadb(tmp_path, monkeypatch, fixture_vault_path, chroma_disabled_env):
    """VXMEM-07: Chroma-absent recall exits 0 and uses external BM25 hits."""
    source = {"name": "docs", "path": str(fixture_vault_path), "glob": "**/*.md"}
    write_config_toml(tmp_path, monkeypatch, [source])

    from voss.cli import main

    result = CliRunner().invoke(
        main,
        [
            "recall",
            "--cwd",
            str(tmp_path),
            "--refresh",
            "notes",
            "endpoint",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "[docs]" in result.output
    assert "api-reference.md" in result.output


def test_code_memory_labels_still_resolve():
    """VXMEM-07: schema change keeps code/memory labels and external labels."""
    from voss.harness.cli import _recall_hit_fields
    from voss.harness.memory_store import Hit

    code = Hit(
        source="code",
        locator="code:voss/harness/cli.py:000",
        score=1.0,
        excerpt="def recall_cmd",
        line_start=42,
        line_end=45,
    )
    memory = Hit(source="memory", locator="notes:abc", score=0.8, excerpt="saved note")
    external = Hit(
        source="docs",
        locator="docs:getting-started.md:000",
        score=0.7,
        excerpt="installation quickstart",
        line_start=3,
        line_end=8,
    )

    code_fields = _recall_hit_fields(code)
    memory_fields = _recall_hit_fields(memory)
    external_fields = _recall_hit_fields(external)

    assert code_fields["source"] == "code"
    assert code_fields["path"] == "voss/harness/cli.py"
    assert code_fields["line_start"] == 42
    assert memory_fields["source"] == "memory"
    assert memory_fields["path"] is None
    assert external_fields["source"] == "docs"
    assert external_fields["path"] is None
