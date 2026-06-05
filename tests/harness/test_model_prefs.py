"""Tests for model_prefs (recents + favorites JSON store)."""
from __future__ import annotations

import pytest

from voss.harness import model_prefs as mp


@pytest.fixture
def path(tmp_path):
    return tmp_path / "model_prefs.json"


def test_empty_when_absent(path):
    assert mp.recent(path) == []
    assert mp.favorites(path) == []


def test_record_recent_most_recent_first(path):
    mp.record_recent("anthropic", "claude-sonnet-4-5", path=path)
    mp.record_recent("ollama-cloud", "gemma3:27b", path=path)
    assert mp.recent(path) == [("ollama-cloud", "gemma3:27b"),
                               ("anthropic", "claude-sonnet-4-5")]


def test_record_recent_dedups_and_promotes(path):
    mp.record_recent("a", "1", path=path)
    mp.record_recent("b", "2", path=path)
    mp.record_recent("a", "1", path=path)  # re-use -> front, no dup
    assert mp.recent(path) == [("a", "1"), ("b", "2")]


def test_record_recent_caps(path):
    for i in range(12):
        mp.record_recent("p", f"m{i}", path=path)
    rec = mp.recent(path)
    assert len(rec) == mp.RECENT_CAP
    assert rec[0] == ("p", "m11")  # newest


def test_toggle_favorite_roundtrip(path):
    assert mp.is_favorite("opencode", "kimi", path=path) is False
    assert mp.toggle_favorite("opencode", "kimi", path=path) is True
    assert mp.is_favorite("opencode", "kimi", path=path) is True
    assert mp.favorites(path) == [("opencode", "kimi")]
    assert mp.toggle_favorite("opencode", "kimi", path=path) is False
    assert mp.favorites(path) == []


def test_recent_and_favorites_coexist(path):
    mp.record_recent("a", "1", path=path)
    mp.toggle_favorite("b", "2", path=path)
    assert mp.recent(path) == [("a", "1")]
    assert mp.favorites(path) == [("b", "2")]


def test_corrupt_file_is_empty(path):
    path.write_text("{not json")
    assert mp.recent(path) == []
    assert mp.favorites(path) == []
