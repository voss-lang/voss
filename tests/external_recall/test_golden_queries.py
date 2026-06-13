"""VXMEM-08 deterministic golden-query gate over the V22 fixture vault."""
from __future__ import annotations

import shutil

import pytest

GOLDEN_QUERIES: list[tuple[str, str]] = [
    ("installation quickstart", "getting-started.md"),
    ("setup configuration", "getting-started.md"),
    ("first steps", "getting-started.md"),
    ("endpoint authentication", "api-reference.md"),
    ("users rate limit", "api-reference.md"),
    ("notes endpoint", "api-reference.md"),
    ("chunk boundary heading", "concepts/chunking.md"),
    ("embedding oversize guard", "concepts/chunking.md"),
    ("ATX headings", "concepts/chunking.md"),
    ("2026 breaking change release", "changelog.md"),
]


@pytest.mark.parametrize(
    ("query", "expected_file"),
    [
        pytest.param(query, expected, id=f"VXMEM-08 golden-{idx:02d}")
        for idx, (query, expected) in enumerate(GOLDEN_QUERIES, start=1)
    ],
)
def test_golden_query(indexed_fixture_vault, query, expected_file):
    """VXMEM-08: semantic external recall returns expected fixture file in top 5."""
    hits = indexed_fixture_vault.index.query(query, top_k=5)
    locators = [h.locator for h in hits]

    assert any(expected_file in locator for locator in locators), (
        f"{query!r} expected {expected_file}, got {locators}"
    )


def test_golden_query_bm25(tmp_path, fixture_vault_path, chroma_disabled_env):
    """VXMEM-08: the same deterministic gate works with Chroma disabled."""
    vault = tmp_path / "recall_vault"
    shutil.copytree(fixture_vault_path, vault)
    source = {"name": "docs", "path": str(vault), "glob": "**/*.md"}

    from voss.harness.recall.external_index import ExternalSourceIndex

    index = ExternalSourceIndex(tmp_path, source)
    index.build()

    failures: list[str] = []
    for query, expected_file in GOLDEN_QUERIES:
        hits = index.query(query, top_k=5)
        locators = [h.locator for h in hits]
        if not any(expected_file in locator for locator in locators):
            failures.append(f"{query!r} expected {expected_file}, got {locators}")

    assert not failures, "\n".join(failures)
