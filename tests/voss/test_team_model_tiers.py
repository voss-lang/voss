"""Tier->model resolution for the team compiler (VTEAM-08).

Single home for tier behavior: the config-backed tier table (Task 1) and the
`_parse_model_value` closed-set resolution + raw passthrough + diagnostics
(Task 3). Team-level cases stay RED until Task 3 lands.
"""

from __future__ import annotations

import pytest

from voss import parse
from voss.ast_nodes import TeamDecl
from voss.harness import config as harness_config
from voss.harness.config import get_model_tiers
from voss.harness.team import VossTeamConfigError, compile_team


@pytest.fixture()
def xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


def _write_config(body: str) -> None:
    p = harness_config.config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def _only_team(src: str) -> TeamDecl:
    prog = parse(src if src.endswith("\n") else src + "\n", "<test>")
    teams = [d for d in prog.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]


def _compile_role(model_value: str):
    src = f'''team Eng {{
  ceiling {{ budget: 100 tokens, scope: "src/**" }}
  roster e {{
    backend {{ model: "{model_value}", scope: "src/api/**", tools: ["fs"] }}
  }}
}}
'''
    _, registry = compile_team(_only_team(src))
    return registry.get("backend")


# --- Task 1: config-backed tier table -------------------------------------


def test_builtin_tiers_present(xdg) -> None:
    tiers = get_model_tiers()
    assert set(tiers.keys()) == {"strong", "cheap", "fast"}
    for tier, mid in tiers.items():
        assert isinstance(mid, str) and mid.strip(), tier


def test_model_tiers_override(xdg) -> None:
    _write_config(
        "[model_tiers]\n"
        'strong = "custom-strong-model"\n'
    )
    tiers = get_model_tiers()
    assert tiers["strong"] == "custom-strong-model"
    # Untouched tiers keep built-in defaults (shallow merge).
    assert tiers["cheap"] and tiers["fast"]


# --- Task 3: tier resolution in _parse_model_value ------------------------


def test_tier_strong_resolves_to_concrete_id(xdg) -> None:
    spec = _compile_role("strong")
    assert spec is not None
    assert spec.model == get_model_tiers()["strong"]


def test_tier_cheap_and_fast_resolve(xdg) -> None:
    assert _compile_role("cheap").model == get_model_tiers()["cheap"]
    assert _compile_role("fast").model == get_model_tiers()["fast"]


def test_raw_model_string_passes_through(xdg) -> None:
    # Offline: no catalog call, raw id preserved.
    spec = _compile_role("opus")
    assert spec is not None and spec.model == "opus"


def test_typo_tier_treated_as_raw_id(xdg) -> None:
    # "strog" is not in the closed tier set -> raw passthrough (locked semantics).
    spec = _compile_role("strog")
    assert spec is not None and spec.model == "strog"


def test_misconfigured_tier_raises_naming_tier(xdg) -> None:
    _write_config(
        "[model_tiers]\n"
        'strong = ""\n'
    )
    with pytest.raises(VossTeamConfigError) as ei:
        _compile_role("strong")
    assert "strong" in str(ei.value)
