"""Lock the SessionRecord redaction guarantee (D-17).

If a future change adds a SessionRecord field that holds provider creds or
adds a serialization path that bypasses the dataclass, these tests fail.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from voss_runtime import EpisodicMemory

from voss.harness import session as session_store


@pytest.fixture
def state_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return tmp_path / "state" / "voss" / "sessions"


class TestSchemaAllowlist:
    def test_saved_json_has_exactly_schema_keys(self, state_dir, tmp_path):
        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        history.add("hello", role="user")
        path = session_store.save(record, history)
        data = json.loads(path.read_text())
        expected = {
            "id", "name", "cwd", "model", "started_at", "updated_at",
            "total_cost_usd", "turns",
        }
        assert set(data.keys()) == expected

    def test_no_credentials_keys_at_top_level(self, state_dir, tmp_path):
        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        path = session_store.save(record, history)
        text = path.read_text()
        forbidden_top_level_keys = (
            '"access_token"', '"refresh_token"', '"api_key"',
            '"Authorization"', '"anthropic-beta"', '"oauth_token"',
            '"credentials"', '"provider"', '"headers"',
        )
        for key in forbidden_top_level_keys:
            assert key not in text, f"forbidden key present: {key}"

    def test_secret_patterns_absent_from_clean_session(self, state_dir, tmp_path):
        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        history.add("summarize this repo", role="user")
        history.add("the repo is a Python harness.", role="assistant")
        path = session_store.save(record, history)
        text = path.read_text()
        # Creds-shaped patterns the harness itself would never put in a
        # transcript. Their presence means the schema allowlist broke.
        secret_patterns = (
            "sk-ant-", "sk-proj-", "Bearer ",
            "oauth_token", "access_token", "Authorization",
        )
        for pat in secret_patterns:
            assert pat not in text, f"secret pattern leaked: {pat!r}"


class TestUserPromptsArePassthrough:
    """User prompt content is intentionally not redacted — the user typed it."""

    def test_user_prompt_with_secret_shape_is_preserved(self, state_dir, tmp_path):
        record = session_store.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4")
        history = EpisodicMemory(capacity=10)
        history.add("debug this: my key was sk-test-DEADBEEF", role="user")
        path = session_store.save(record, history)
        text = path.read_text()
        assert "sk-test-DEADBEEF" in text  # user typed it; we preserve it


class TestDocstringFreezesGuarantee:
    def test_module_docstring_mentions_redaction_guarantee(self):
        assert session_store.__doc__ is not None
        assert "Redaction guarantee" in session_store.__doc__
