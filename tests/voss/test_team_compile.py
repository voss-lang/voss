"""Compile-step acceptance for team declarations (OTEAM-02, OTEAM-03, OTEAM-06)."""

from __future__ import annotations

from pathlib import Path

import pytest

from voss import parse
from voss.ast_nodes import Identifier, TeamDecl

from voss.harness.team import VossTeamConfigError, compile_team

_EXAMPLES = Path(__file__).resolve().parents[1] / "parser" / "examples"
_STRAWMAN = _EXAMPLES / "team_strawman.voss"


def _prog(src: str, file: str = "<test>"):
    return parse(src if src.endswith("\n") else src + "\n", file)


def _only_team(decls) -> TeamDecl:
    teams = [d for d in decls.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]


def test_strawman_compiles_to_expected_registry() -> None:
    td = _only_team(_prog(_STRAWMAN.read_text(encoding="utf-8"), "team_strawman.voss"))
    config, registry = compile_team(td)

    assert config.name == "Engineering"
    assert config.ceiling.budget_tokens == 200_000
    assert config.ceiling.scope is not None
    assert config.ceiling.scope.globs == ("src/**",)
    assert config.ceiling.latency_seconds == 1800
    policy_p = config.policy.p
    assert isinstance(policy_p, Identifier)
    assert policy_p.name == "risk_tiered"
    assert config.em_agent_id == "em"
    assert config.roster_ids == frozenset({"em", "backend", "frontend", "ui", "ai"})
    assert config.board is not None and len(config.board.raw_items) > 0
    assert len(config.rituals) == 1 and config.rituals[0].name == "ContextDigest"
    assert registry.ids() == ["ai", "backend", "em", "frontend", "ui"]


def test_ai_role_gets_net() -> None:
    td = _only_team(_prog(_STRAWMAN.read_text(encoding="utf-8"), "team_strawman.voss"))
    _, registry = compile_team(td)
    ai_spec = registry.get("ai")
    assert ai_spec is not None
    assert ai_spec.net is True
    assert ai_spec.tools is not None and "net" in ai_spec.tools


def test_engineer_roles_do_not_get_net() -> None:
    td = _only_team(_prog(_STRAWMAN.read_text(encoding="utf-8"), "team_strawman.voss"))
    _, registry = compile_team(td)
    for role in ("backend", "frontend", "ui"):
        s = registry.get(role)
        assert s is not None
        assert s.net is False
        assert "net" not in (s.tools or frozenset())


def test_compiled_registry_refuses_unknown_id() -> None:
    td = _only_team(_prog(_STRAWMAN.read_text(encoding="utf-8"), "team_strawman.voss"))
    _, registry = compile_team(td)
    ghost = registry.get("freelancer")
    assert ghost is None
    envelope = "<error: unknown subagent {!r}>".format("freelancer")
    expected = '<error: unknown subagent \'freelancer\'>'
    assert envelope == expected


def test_em_scope_equals_ceiling_scope() -> None:
    td = _only_team(_prog(_STRAWMAN.read_text(encoding="utf-8"), "team_strawman.voss"))
    config, registry = compile_team(td)
    em = registry.get("em")
    assert em is not None and config.ceiling.scope is not None
    assert em.scope is not None
    assert em.scope.globs == config.ceiling.scope.globs


def test_backend_scope_is_strict_subset_of_ceiling() -> None:
    td = _only_team(_prog(_STRAWMAN.read_text(encoding="utf-8"), "team_strawman.voss"))
    config, registry = compile_team(td)
    bk = registry.get("backend")
    assert bk is not None and bk.scope is not None and config.ceiling.scope is not None
    assert bk.scope.globs == ("src/api/**",)
    assert bk.scope.is_contained_in(config.ceiling.scope)


def test_role_with_no_scope_inherits_ceiling() -> None:
    src = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster r {
    backend { model: "opus" }
  }
}
'''
    td = _only_team(_prog(src))
    config, registry = compile_team(td)
    assert config.ceiling.scope is not None
    spec = registry.get("backend")
    assert spec is not None and spec.scope is not None
    assert spec.scope.globs == config.ceiling.scope.globs


def test_role_budget_cap_validates_against_ceiling() -> None:
    ok = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { budget: 50 tokens, scope: "src/api/**", tools: ["fs"] }
  }
}
'''
    td_ok = _only_team(_prog(ok))
    cfg_ok, reg_ok = compile_team(td_ok)
    assert cfg_ok.ceiling.budget_tokens == 100
    bk = reg_ok.get("backend")
    assert bk is not None and bk.budget == 50

    bad = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { budget: 200 tokens, scope: "src/api/**", tools: ["fs"] }
  }
}
'''
    td_bad = _only_team(_prog(bad))
    try:
        compile_team(td_bad)
    except VossTeamConfigError as exc:
        assert "200" in str(exc) and "100" in str(exc)
    else:
        raise AssertionError("expected VossTeamConfigError")


def test_open_roster_accepts_custom_role_name() -> None:
    src = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    devops { model: "opus", scope: "src/infra/**", tools: ["fs"] }
  }
}
'''
    td = _only_team(_prog(src))
    _, registry = compile_team(td)
    d = registry.get("devops")
    assert d is not None
    assert "devops" in d.description.lower() or "`devops`" in d.description


def test_unknown_mode_rejects() -> None:
    src = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { mode: "yolo", scope: "src/**", tools: ["fs"] }
  }
}
'''
    td = _only_team(_prog(src))
    with pytest.raises(VossTeamConfigError) as ei:
        compile_team(td)
    msg = str(ei.value)
    assert "yolo" in msg
    assert "plan" in msg and "edit" in msg and "auto" in msg
