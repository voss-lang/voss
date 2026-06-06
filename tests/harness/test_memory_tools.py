"""Tier 2 #6(a): agent-callable memory tools (memory_recall / memory_remember)
wrapping MemoryStore."""
from __future__ import annotations

import asyncio
from pathlib import Path

from voss.harness.memory_store import MemoryStore
from voss.harness.tools import attach_memory_tools


def _tools(tmp_path: Path) -> dict:
    store = MemoryStore(tmp_path).bind(session_id="sess-1")
    tools: dict = {}
    attach_memory_tools(tools, store=store, session_id="sess-1")
    return tools


def test_remember_then_recall(tmp_path: Path) -> None:
    tools = _tools(tmp_path)
    out = asyncio.run(
        tools["memory_remember"].invoke(text="the auth token expires after one hour")
    )
    assert out.startswith("remembered:")
    hits = asyncio.run(tools["memory_recall"].invoke(query="auth token expiry"))
    assert "auth token" in hits
    assert "[note]" in hits


def test_recall_no_hits(tmp_path: Path) -> None:
    tools = _tools(tmp_path)
    out = asyncio.run(tools["memory_recall"].invoke(query="nothing stored yet"))
    assert out == "(no hits)"


def test_empty_inputs_error(tmp_path: Path) -> None:
    tools = _tools(tmp_path)
    assert "empty query" in asyncio.run(tools["memory_recall"].invoke(query="  "))
    assert "empty note" in asyncio.run(tools["memory_remember"].invoke(text="   "))


def test_mutating_flags(tmp_path: Path) -> None:
    tools = _tools(tmp_path)
    assert tools["memory_recall"].is_mutating is False
    assert tools["memory_remember"].is_mutating is True
