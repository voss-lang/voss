"""Phase 3 tests: keyring-backed credential persistence + resolve precedence.

`keyring` exposes a `set_keyring()` hook that lets us install an in-memory
backend for tests — no Keychain access, no Secret Service required.
"""
from __future__ import annotations

from typing import Optional

import pytest

from voss.harness import auth as A


# ---------------------------------------------------------------------------
# In-memory keyring backend
# ---------------------------------------------------------------------------


class InMemoryKeyring:
    """Minimal `keyring.backend.KeyringBackend` shim. Stores values in a dict."""

    priority = 1  # required attr; any positive value avoids the "fail" backend.

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> Optional[str]:
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self._store.pop((service, username), None)


@pytest.fixture
def keyring_mem(monkeypatch: pytest.MonkeyPatch) -> InMemoryKeyring:
    """Install an in-memory keyring backend for the duration of the test."""
    import keyring

    backend = InMemoryKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    monkeypatch.setattr(keyring, "get_password", backend.get_password)
    monkeypatch.setattr(keyring, "set_password", backend.set_password)
    monkeypatch.setattr(keyring, "delete_password", backend.delete_password)
    return backend


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Sandbox HOME so real ~/.claude / ~/.codex creds on the dev machine
    # do not bleed into precedence tests.
    monkeypatch.setenv("HOME", str(tmp_path))
    # Force file-path discovery (skip macOS keychain for OAuth-token lookups).
    monkeypatch.setattr(A, "_read_macos_keychain", lambda: None)


# ---------------------------------------------------------------------------
# Roundtrip + delete
# ---------------------------------------------------------------------------


def test_save_then_load_roundtrip(keyring_mem: InMemoryKeyring):
    assert A.save_voss_creds("anthropic", "sk-ant-roundtrip") is True
    assert A.load_voss_creds("anthropic") == "sk-ant-roundtrip"


def test_load_returns_none_when_absent(keyring_mem: InMemoryKeyring):
    assert A.load_voss_creds("openai") is None


def test_delete_removes_credential(keyring_mem: InMemoryKeyring):
    A.save_voss_creds("openai", "sk-test")
    assert A.delete_voss_creds("openai") is True
    assert A.load_voss_creds("openai") is None


def test_load_strips_whitespace(keyring_mem: InMemoryKeyring):
    keyring_mem.set_password(A.KEYRING_SERVICE, "anthropic", "  sk-ant-x  \n")
    assert A.load_voss_creds("anthropic") == "sk-ant-x"


def test_load_treats_empty_as_absent(keyring_mem: InMemoryKeyring):
    keyring_mem.set_password(A.KEYRING_SERVICE, "anthropic", "")
    assert A.load_voss_creds("anthropic") is None


# ---------------------------------------------------------------------------
# Graceful fallback when keyring unusable
# ---------------------------------------------------------------------------


def test_load_handles_missing_keyring(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(A, "_keyring_module", lambda: None)
    assert A.load_voss_creds("anthropic") is None


def test_save_returns_false_when_no_backend(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(A, "_keyring_module", lambda: None)
    assert A.save_voss_creds("anthropic", "sk-ant-x") is False


def test_save_returns_false_when_backend_raises(
    monkeypatch: pytest.MonkeyPatch, keyring_mem: InMemoryKeyring
):
    import keyring

    def boom(*_args, **_kwargs):
        raise RuntimeError("backend down")

    monkeypatch.setattr(keyring, "set_password", boom)
    assert A.save_voss_creds("anthropic", "sk-ant-x") is False


# ---------------------------------------------------------------------------
# resolve() precedence
# ---------------------------------------------------------------------------


def test_voss_anthropic_outranks_env(
    keyring_mem: InMemoryKeyring, monkeypatch: pytest.MonkeyPatch
):
    """Wizard-set keyring creds win over stale shell env exports."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stale-env")
    A.save_voss_creds("anthropic", "sk-ant-fresh")

    res = A.resolve("auto")
    assert res.source == "voss-anthropic"
    # And the env is overwritten so downstream LiteLLM picks up the right key.
    import os

    assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-fresh"


def test_voss_openai_outranks_env(
    keyring_mem: InMemoryKeyring, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-stale")
    A.save_voss_creds("openai", "sk-fresh")

    res = A.resolve("auto")
    assert res.source == "voss-openai"
    assert res.openai_api_key == "sk-fresh"
    import os

    assert os.environ["OPENAI_API_KEY"] == "sk-fresh"


def test_env_used_when_no_voss_creds(
    keyring_mem: InMemoryKeyring, monkeypatch: pytest.MonkeyPatch
):
    """With no keyring creds, env vars still resolve (CI / Docker path)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-env-only")
    res = A.resolve("auto")
    assert res.source == "env-anthropic"


def test_resolve_with_no_creds_at_all(keyring_mem: InMemoryKeyring):
    res = A.resolve("auto")
    assert res.source == "none"
