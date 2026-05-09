import json
import time
from pathlib import Path

import httpx
import pytest

from voss.harness import auth as A


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Force file-path discovery (skip macOS keychain).
    monkeypatch.setattr(A, "_read_macos_keychain", lambda: None)
    return tmp_path


def _write_claude_creds(home: Path, *, expires_in: int = 3600) -> None:
    blob = {
        "claudeAiOauth": {
            "accessToken": "sk-ant-oat01-AAAA",
            "refreshToken": "sk-ant-ort01-BBBB",
            "expiresAt": int((time.time() + expires_in) * 1000),
            "subscriptionType": "max",
            "scopes": ["user:inference"],
        }
    }
    p = home / ".claude" / ".credentials.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(blob))


def _write_codex_auth(home: Path, *, api_key: str = "sk-test-codex", with_tokens: bool = True) -> None:
    blob: dict = {"auth_mode": "ChatGPT" if with_tokens else "ApiKey", "OPENAI_API_KEY": api_key}
    if with_tokens:
        blob["tokens"] = {
            "id_token": "id",
            "access_token": "access",
            "refresh_token": "refresh",
            "account_id": "acct_123",
        }
    p = home / ".codex" / "auth.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(blob))


class TestLoadAnthropicOauth:
    def test_returns_creds_from_file(self, fake_home: Path) -> None:
        _write_claude_creds(fake_home)
        creds = A.load_anthropic_oauth()
        assert creds is not None
        assert creds.access_token == "sk-ant-oat01-AAAA"
        assert creds.subscription_type == "max"
        assert not creds.expired

    def test_none_when_missing(self, fake_home: Path) -> None:
        assert A.load_anthropic_oauth() is None

    def test_expired_flag(self, fake_home: Path) -> None:
        _write_claude_creds(fake_home, expires_in=-3600)
        creds = A.load_anthropic_oauth()
        assert creds is not None
        assert creds.expired


class TestLoadCodex:
    def test_returns_api_key(self, fake_home: Path) -> None:
        _write_codex_auth(fake_home)
        codex = A.load_codex()
        assert codex is not None
        assert codex.api_key == "sk-test-codex"
        assert codex.access_token == "access"
        assert codex.auth_mode == "ChatGPT"

    def test_none_when_missing(self, fake_home: Path) -> None:
        assert A.load_codex() is None


class TestResolve:
    def test_env_anthropic_wins(self, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
        _write_claude_creds(fake_home)
        _write_codex_auth(fake_home)
        res = A.resolve("auto")
        assert res.source == "env-anthropic"

    def test_falls_back_to_claude_oauth(self, fake_home: Path) -> None:
        _write_claude_creds(fake_home)
        res = A.resolve("auto")
        assert res.source == "claude-oauth"
        assert res.anthropic_oauth is not None

    def test_falls_back_to_codex(self, fake_home: Path) -> None:
        _write_codex_auth(fake_home)
        res = A.resolve("auto")
        assert res.source == "codex"
        assert res.openai_api_key == "sk-test-codex"

    def test_explicit_codex_skips_claude(self, fake_home: Path) -> None:
        _write_claude_creds(fake_home)
        _write_codex_auth(fake_home)
        res = A.resolve("codex")
        assert res.source == "codex"

    def test_explicit_claude_with_no_creds_returns_none(self, fake_home: Path) -> None:
        _write_codex_auth(fake_home)  # only codex
        res = A.resolve("claude")
        assert res.source == "none"

    def test_none_pref_returns_none(self, fake_home: Path) -> None:
        _write_claude_creds(fake_home)
        res = A.resolve("none")
        assert res.source == "none"


class TestRefreshAnthropic:
    def test_refresh_updates_token(self, fake_home: Path) -> None:
        _write_claude_creds(fake_home, expires_in=10)
        creds = A.load_anthropic_oauth()
        assert creds is not None

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.host == "console.anthropic.com"
            body = json.loads(request.content)
            assert body["grant_type"] == "refresh_token"
            assert body["refresh_token"] == "sk-ant-ort01-BBBB"
            assert body["client_id"] == A.CLAUDE_CODE_CLIENT_ID
            return httpx.Response(
                200,
                json={
                    "access_token": "sk-ant-oat01-NEW",
                    "refresh_token": "sk-ant-ort01-NEW",
                    "expires_in": 7200,
                },
            )

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        new = A.refresh_anthropic(creds, client=client)
        assert new.access_token == "sk-ant-oat01-NEW"
        assert new.refresh_token == "sk-ant-ort01-NEW"
        # Persisted to file.
        on_disk = json.loads((fake_home / ".claude" / ".credentials.json").read_text())
        assert on_disk["claudeAiOauth"]["accessToken"] == "sk-ant-oat01-NEW"
