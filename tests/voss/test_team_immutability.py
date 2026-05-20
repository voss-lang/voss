"""Immutability of compiled TeamConfig / registry specs (OTEAM-04 at compile boundary)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

from voss import parse
from voss.ast_nodes import TeamDecl

from voss.harness.team import TeamRoleScope, compile_team

_EXAMPLES = Path(__file__).resolve().parents[1] / "parser" / "examples"
_STRAWMAN = _EXAMPLES / "team_strawman.voss"


def _prog(src: str, file: str = "<test>"):
    return parse(src if src.endswith("\n") else src + "\n", file)


def _only_team(decls) -> TeamDecl:
    teams = [d for d in decls.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]


def _strawman_config_and_registry():
    td = _only_team(_prog(_STRAWMAN.read_text(encoding="utf-8"), "team_strawman.voss"))
    return compile_team(td)


def test_compiled_team_config_is_frozen() -> None:
    config, _ = _strawman_config_and_registry()

    assignments = (
        ("name", "X"),
        ("ceiling", config.ceiling),
        ("policy", config.policy),
        ("em_agent_id", "x"),
        ("roster_ids", frozenset()),
        ("board", None),
        ("rituals", ()),
    )
    for attr, val in assignments:
        try:
            setattr(config, attr, val)
        except FrozenInstanceError:
            continue
        raise AssertionError(f"expected FrozenInstanceError for config.{attr}")


def test_compiled_team_ceiling_is_frozen() -> None:
    config, _ = _strawman_config_and_registry()
    c = config.ceiling

    for attr, val in (
        ("budget_tokens", 999),
        ("scope", None),
        ("latency_seconds", 1),
    ):
        try:
            setattr(c, attr, val)
        except FrozenInstanceError:
            continue
        raise AssertionError(f"expected FrozenInstanceError for ceiling.{attr}")


def test_compiled_team_policy_is_frozen() -> None:
    config, _ = _strawman_config_and_registry()

    try:
        config.policy.p = 0.1  # type: ignore[attr-defined]
    except FrozenInstanceError:
        return
    raise AssertionError("expected FrozenInstanceError for TeamPolicy")


def test_compiled_registry_specs_are_frozen() -> None:
    _, registry = _strawman_config_and_registry()
    ceiling_scope = TeamRoleScope(("src/**",))

    for spec in registry.entries():
        for attr, val in (
            ("model", "edited"),
            ("mode", "plan"),
            ("scope", ceiling_scope),
            ("budget", 1),
            ("tools", frozenset({"fs"})),
            ("net", True),
        ):
            try:
                setattr(spec, attr, val)
            except FrozenInstanceError:
                continue
            raise AssertionError(
                f"expected FrozenInstanceError for SubagentSpec.{attr} ({spec.id!r})"
            )


def test_no_em_api_to_widen_ceiling() -> None:
    """No ergonomic widen/mutate helpers on compiled ceiling artifacts (OTEAM-04)."""

    config, _ = _strawman_config_and_registry()
    ceiling = config.ceiling
    for name in (
        "with_budget",
        "set_budget",
        "with_scope",
        "set_scope",
        "with_latency",
        "set_latency",
    ):
        assert not hasattr(ceiling, name)

    scope_obj = ceiling.scope
    assert scope_obj is not None
    assert not hasattr(scope_obj, "with_globs") and not hasattr(scope_obj, "set_globs")


def test_roster_ids_is_frozenset() -> None:
    config, _ = _strawman_config_and_registry()
    assert isinstance(config.roster_ids, frozenset)
    try:
        config.roster_ids.add("ghost")  # type: ignore[attr-defined]
    except AttributeError:
        return
    raise AssertionError("expected AttributeError calling frozenset.add")


def test_board_spec_raw_items_is_tuple() -> None:
    config, _ = _strawman_config_and_registry()
    assert config.board is not None
    assert isinstance(config.board.raw_items, tuple)


def test_rituals_is_tuple() -> None:
    config, _ = _strawman_config_and_registry()
    assert isinstance(config.rituals, tuple)
