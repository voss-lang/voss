import json
import stat
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

    def test_falls_back_to_claude_agent(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_claude_creds(fake_home)
        monkeypatch.setattr(
            A, "detect_upstream_cli", lambda name: Path("/opt/bin/claude")
        )
        res = A.resolve("auto")
        assert res.source == "claude-agent"
        assert res.anthropic_oauth is not None
        assert res.cli_path == Path("/opt/bin/claude")

    def test_claude_creds_without_cli_fall_through_under_auto(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_claude_creds(fake_home)
        monkeypatch.setattr(A, "detect_upstream_cli", lambda name: None)
        res = A.resolve("auto")
        assert res.source == "none"

    def test_explicit_claude_creds_without_cli_hints_install(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_claude_creds(fake_home)
        monkeypatch.setattr(A, "detect_upstream_cli", lambda name: None)
        res = A.resolve("claude")
        assert res.source == "none"
        assert "not on PATH" in res.detail

    def test_explicit_claude_cli_without_creds_hints_login(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            A, "detect_upstream_cli", lambda name: Path("/opt/bin/claude")
        )
        res = A.resolve("claude")
        assert res.source == "none"
        assert "claude /login" in res.detail

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

    def test_explicit_claude_with_no_creds_returns_none(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_codex_auth(fake_home)  # only codex
        monkeypatch.setattr(A, "detect_upstream_cli", lambda name: None)
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
        mode = stat.S_IMODE((fake_home / ".claude" / ".credentials.json").stat().st_mode)
        assert mode == 0o600


class TestRefreshCodex:
    def test_refresh_updates_file_permissions(self, fake_home: Path) -> None:
        _write_codex_auth(fake_home)
        creds = A.load_codex()
        assert creds is not None

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.host == "auth.openai.com"
            assert "grant_type=refresh_token" in request.content.decode()
            return httpx.Response(
                200,
                json={
                    "access_token": "access-new",
                    "refresh_token": "refresh-new",
                },
            )

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        A.refresh_codex(creds, client=client)
        path = fake_home / ".codex" / "auth.json"
        on_disk = json.loads(path.read_text())
        assert on_disk["tokens"]["access_token"] == "access-new"
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_resolve_accepts_role_kwarg(monkeypatch):
    """M5 D-10: role kwarg accepted, ignored in v0.1."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from voss.harness.auth import resolve

    r_default = resolve()
    r_judge = resolve(role="judge")
    assert r_default.source == r_judge.source
    assert r_default.detail == r_judge.detail


def test_resolve_role_with_none_preference():
    """role is ignored when preference='none'."""
    from voss.harness.auth import resolve

    r = resolve(preference="none", role="judge")
    assert r.source == "none"


# ---------------------------------------------------------------------------
# Phase 1: detect_upstream_cli + wait_for_creds
# ---------------------------------------------------------------------------


def test_detect_upstream_cli_present(tmp_path, monkeypatch):
    """When the binary is on PATH, returns an absolute Path."""
    fake_bin = tmp_path / "claude"
    fake_bin.write_text("#!/bin/sh\nexit 0\n")
    fake_bin.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))

    found = A.detect_upstream_cli("claude")
    assert found is not None
    assert found == fake_bin


def test_detect_upstream_cli_absent(tmp_path, monkeypatch):
    """When PATH has no `codex` binary, returns None."""
    monkeypatch.setenv("PATH", str(tmp_path))  # empty dir
    assert A.detect_upstream_cli("codex") is None


def test_wait_for_creds_claude_appears(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
):
    """File written mid-poll resolves before timeout."""
    monkeypatch.setattr(A, "detect_upstream_cli", lambda name: Path("/opt/bin/claude"))
    calls = {"sleep": 0}

    def fake_sleep(_: float) -> None:
        # On the second sleep, materialize the creds file.
        calls["sleep"] += 1
        if calls["sleep"] == 2:
            _write_claude_creds(fake_home)

    # Monotonic clock that never crosses the deadline so the loop relies on
    # the cred file appearing, not the timeout.
    t = {"now": 0.0}

    def fake_now() -> float:
        t["now"] += 0.1
        return t["now"]

    res = A.wait_for_creds(
        "claude",
        timeout=60.0,
        poll=0.01,
        now=fake_now,
        sleep=fake_sleep,
    )
    assert res is not None
    assert res.source == "claude-agent"
    assert res.anthropic_oauth is not None
    assert res.cli_path == Path("/opt/bin/claude")


def test_wait_for_creds_codex_appears(fake_home: Path):
    """Codex auth.json appearing mid-poll yields a codex resolution."""
    calls = {"sleep": 0}

    def fake_sleep(_: float) -> None:
        calls["sleep"] += 1
        if calls["sleep"] == 1:
            _write_codex_auth(fake_home, with_tokens=False)

    t = {"now": 0.0}

    def fake_now() -> float:
        t["now"] += 0.1
        return t["now"]

    res = A.wait_for_creds(
        "codex",
        timeout=60.0,
        poll=0.01,
        now=fake_now,
        sleep=fake_sleep,
    )
    assert res is not None
    assert res.source == "codex"
    assert res.openai_api_key == "sk-test-codex"


def test_wait_for_creds_timeout(fake_home: Path):
    """Returns None once the deadline passes without creds materializing."""
    sleeps = {"n": 0}

    def fake_sleep(_: float) -> None:
        sleeps["n"] += 1

    # Three calls to `now`: initial deadline calc, two loop checks. The second
    # loop check trips the timeout.
    sequence = iter([0.0, 0.5, 200.0])

    def fake_now() -> float:
        return next(sequence)

    res = A.wait_for_creds(
        "claude",
        timeout=120.0,
        poll=0.01,
        now=fake_now,
        sleep=fake_sleep,
    )
    assert res is None
    # Slept at least once before noticing timeout.
    assert sleeps["n"] >= 1
