"""P2 tests: env-var-keyed keyring storage + provider connectivity."""
from __future__ import annotations

from typing import Optional

import pytest

from voss.harness import auth as A
from voss.harness import model_router as mr
from voss.harness.model_catalog import ProviderGroup


# In-memory keyring backend (mirrors test_auth_persistence pattern).
class InMemoryKeyring:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> Optional[str]:
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.store.pop((service, username), None)


@pytest.fixture
def keyring_mem(monkeypatch: pytest.MonkeyPatch) -> InMemoryKeyring:
    import keyring

    backend = InMemoryKeyring()
    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)
    monkeypatch.setattr(keyring, "get_password", backend.get_password)
    monkeypatch.setattr(keyring, "set_password", backend.set_password)
    monkeypatch.setattr(keyring, "delete_password", backend.delete_password)
    return backend


def test_provider_key_roundtrip(keyring_mem: InMemoryKeyring) -> None:
    assert A.load_provider_key("OLLAMA_API_KEY") is None
    assert A.save_provider_key("OLLAMA_API_KEY", "tok-123") is True
    assert A.load_provider_key("OLLAMA_API_KEY") == "tok-123"
    assert A.delete_provider_key("OLLAMA_API_KEY") is True
    assert A.load_provider_key("OLLAMA_API_KEY") is None


def test_provider_key_strips_and_empty_is_none(keyring_mem: InMemoryKeyring) -> None:
    keyring_mem.set_password(A.KEYRING_SERVICE, "OPENCODE_API_KEY", "  zk  \n")
    assert A.load_provider_key("OPENCODE_API_KEY") == "zk"
    keyring_mem.set_password(A.KEYRING_SERVICE, "OPENCODE_API_KEY", "")
    assert A.load_provider_key("OPENCODE_API_KEY") is None


def test_provider_key_blank_envkey_is_noop(keyring_mem: InMemoryKeyring) -> None:
    assert A.load_provider_key("") is None
    assert A.save_provider_key("", "x") is False


# --- connectivity ---


def _group(pid: str, env_key: str | None) -> ProviderGroup:
    return ProviderGroup(id=pid, label=pid, api_base=None, env_key=env_key, models=())


def test_connected_via_env() -> None:
    assert mr.provider_connected(
        "ollama-cloud", "OLLAMA_API_KEY",
        getter={"OLLAMA_API_KEY": "x"}.get, keyring_get={}.get, oauth_check=lambda _p: False,
    ) is True


def test_connected_via_keyring() -> None:
    assert mr.provider_connected(
        "opencode", "OPENCODE_API_KEY",
        getter={}.get, keyring_get={"OPENCODE_API_KEY": "k"}.get, oauth_check=lambda _p: False,
    ) is True


def test_keyless_provider_always_connected() -> None:
    assert mr.provider_connected(
        "ollama-local", None, getter={}.get, keyring_get={}.get, oauth_check=lambda _p: False,
    ) is True


def test_disconnected_when_no_key_no_oauth() -> None:
    assert mr.provider_connected(
        "opencode", "OPENCODE_API_KEY",
        getter={}.get, keyring_get={}.get, oauth_check=lambda _p: False,
    ) is False


def test_native_connected_via_oauth_fallback() -> None:
    # anthropic has no env/keyring key but OAuth is present -> connected.
    assert mr.provider_connected(
        "anthropic", "ANTHROPIC_API_KEY",
        getter={}.get, keyring_get={}.get, oauth_check=lambda p: p == "anthropic",
    ) is True


def test_connected_providers_map() -> None:
    groups = [
        _group("anthropic", "ANTHROPIC_API_KEY"),
        _group("ollama-cloud", "OLLAMA_API_KEY"),
        _group("ollama-local", None),
    ]
    out = mr.connected_providers(
        groups,
        getter={"OLLAMA_API_KEY": "x"}.get,
        keyring_get={}.get,
        oauth_check=lambda p: p == "anthropic",
    )
    assert out == {"anthropic": True, "ollama-cloud": True, "ollama-local": True}
