"""VXMEM-07 RED test for agent-facing `memory_recall` external hits."""
from __future__ import annotations

import asyncio

from .conftest import write_config_toml


def test_agent_gets_external_hits(indexed_fixture_vault, monkeypatch):
    """VXMEM-07: the agent recall tool fuses external hits with memory hits."""
    write_config_toml(
        indexed_fixture_vault.cwd,
        monkeypatch,
        [indexed_fixture_vault.source],
    )

    from voss.harness.memory_store import Hit
    from voss.harness.recall.external_index import ExternalRecallService
    from voss.harness.tools import attach_memory_tools

    class StubStore:
        def recall(self, query: str, top_k: int = 5, source: str | None = None):
            return [
                Hit(
                    source="memory",
                    locator="notes:local",
                    score=0.9,
                    excerpt=f"memory hit for {query}",
                )
            ]

    external_service = ExternalRecallService(
        indexed_fixture_vault.cwd,
        session_id="test-session",
    )
    external_service.build_all()

    tools = {}
    attach_memory_tools(
        tools,
        store=StubStore(),
        session_id="test-session",
        external_service=external_service,
    )
    output = asyncio.run(
        tools["memory_recall"].invoke(query="installation quickstart setup", top_k=5)
    )

    assert "[memory]" in output
    assert "[docs]" in output
    assert "getting-started.md" in output
