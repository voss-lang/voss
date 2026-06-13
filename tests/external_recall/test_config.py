"""VXMEM-01/02 RED tests for `[[recall.sources]]` config parsing."""
from __future__ import annotations

import pytest

from .conftest import write_config_toml


def test_parse_two_sources(tmp_path, monkeypatch):
    """VXMEM-01: two ordered sources parse, with `glob` defaulting to md."""
    write_config_toml(
        tmp_path,
        monkeypatch,
        [
            {"name": "docs", "path": "docs"},
            {"name": "guides", "path": "guides", "glob": "**/*.markdown"},
        ],
    )

    from voss.harness.config import get_recall_sources

    assert get_recall_sources() == [
        {"name": "docs", "path": "docs", "glob": "**/*.md"},
        {"name": "guides", "path": "guides", "glob": "**/*.markdown"},
    ]


def test_no_section_zero_sources(tmp_path, monkeypatch):
    """VXMEM-01: missing `[recall]` config returns an empty source list."""
    write_config_toml(
        tmp_path,
        monkeypatch,
        body='[harness]\npreferred_model = "claude-sonnet-4-6"\n',
    )

    from voss.harness.config import get_recall_sources

    assert get_recall_sources() == []


def test_reserved_name_rejected(tmp_path, monkeypatch):
    """VXMEM-02: reserved labels stay available for built-in corpora."""
    write_config_toml(
        tmp_path,
        monkeypatch,
        [{"name": "code", "path": "docs"}],
    )

    from voss.harness.config import get_recall_sources

    with pytest.raises(ValueError, match="code"):
        get_recall_sources()


def test_duplicate_name_rejected(tmp_path, monkeypatch):
    """VXMEM-02: duplicate external source names are rejected loudly."""
    write_config_toml(
        tmp_path,
        monkeypatch,
        [
            {"name": "docs", "path": "docs"},
            {"name": "docs", "path": "more-docs"},
        ],
    )

    from voss.harness.config import get_recall_sources

    with pytest.raises(ValueError, match="docs"):
        get_recall_sources()
