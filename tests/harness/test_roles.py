"""Model-role config parsing + chain construction."""
from __future__ import annotations

from pathlib import Path

from voss.harness import roles
from voss.harness.model_catalog import ModelEntry, ProviderGroup
from voss_runtime.providers.fallback import FallbackProvider


def _entry(provider_id: str, model_id: str, env_key: str | None = None) -> ModelEntry:
    return ModelEntry(
        id=model_id,
        name=model_id,
        provider_id=provider_id,
        provider_label=provider_id,
        api_base=None,
        env_key=env_key,
        free=False,
        subscription=False,
        context=None,
        tool_call=True,
    )


def _groups() -> list[ProviderGroup]:
    return [
        ProviderGroup(
            id="anthropic",
            label="Anthropic",
            api_base=None,
            env_key="ANTHROPIC_API_KEY",
            models=(
                _entry("anthropic", "claude-opus-4-8", "ANTHROPIC_API_KEY"),
                _entry("anthropic", "claude-haiku-4-5", "ANTHROPIC_API_KEY"),
            ),
        ),
        ProviderGroup(
            id="opencode",
            label="OpenCode Zen",
            api_base="https://zen.example/v1",
            env_key="OPENCODE_API_KEY",
            models=(_entry("opencode", "claude-opus-4-5", "OPENCODE_API_KEY"),),
        ),
    ]


_CONFIG = """
[harness]
preferred_model = "claude-opus-4-8"

[harness.roles.default]
chain = [
  { provider = "anthropic", model = "claude-opus-4-8" },
  { provider = "opencode", model = "claude-opus-4-5" },
]

[harness.roles.smol]
chain = [{ provider = "anthropic", model = "claude-haiku-4-5" }]
"""


def _write(tmp_path: Path) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(_CONFIG)
    return p


class TestLoadRoleChains:
    def test_parses_chains_in_order(self, tmp_path: Path) -> None:
        chains = roles.load_role_chains(_write(tmp_path))
        assert [c.model for c in chains["default"]] == ["claude-opus-4-8", "claude-opus-4-5"]
        assert chains["default"][0].provider == "anthropic"
        assert [c.model for c in chains["smol"]] == ["claude-haiku-4-5"]

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert roles.load_role_chains(tmp_path / "nope.toml") == {}

    def test_malformed_rows_skipped(self, tmp_path: Path) -> None:
        p = tmp_path / "c.toml"
        p.write_text(
            '[harness.roles.default]\nchain = [{ provider = "anthropic" }, '
            '{ provider = "anthropic", model = "claude-opus-4-8" }]\n'
        )
        chains = roles.load_role_chains(p)
        assert [c.model for c in chains["default"]] == ["claude-opus-4-8"]


class TestBuildRoleProvider:
    def test_builds_fallback_from_chain(self, tmp_path: Path) -> None:
        chains = roles.load_role_chains(_write(tmp_path))
        built = roles.build_role_provider(
            "default",
            groups=_groups(),
            chains=chains,
            getter=lambda k: "key-present",
            keyring_get=lambda k: None,
        )
        assert built is not None
        provider, primary = built
        assert isinstance(provider, FallbackProvider)
        assert primary == "claude-opus-4-8"
        assert provider.candidate_models == ["claude-opus-4-8", "claude-opus-4-5"]

    def test_unknown_candidates_skipped(self, tmp_path: Path) -> None:
        chains = {"default": [roles.RoleCandidate("anthropic", "does-not-exist")]}
        built = roles.build_role_provider(
            "default", groups=_groups(), chains=chains, getter=lambda k: "k", keyring_get=lambda k: None
        )
        assert built is None

    def test_absent_role_returns_none(self, tmp_path: Path) -> None:
        built = roles.build_role_provider(
            "plan", groups=_groups(), chains={}, getter=lambda k: "k", keyring_get=lambda k: None
        )
        assert built is None
