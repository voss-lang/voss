"""Scope containment / ceiling invariants at compile time (OTEAM-05)."""

from __future__ import annotations

from pathlib import Path

import pytest

from voss import parse
from voss.ast_nodes import TeamDecl
from voss.harness.team import (
    TeamRoleScope,
    VossTeamConfigError,
    compile_team,
)

_EXAMPLES = Path(__file__).resolve().parents[1] / "parser" / "examples"
_STRAWMAN = _EXAMPLES / "team_strawman.voss"


def _prog(src: str, file: str = "<test>"):
    return parse(src if src.endswith("\n") else src + "\n", file)


def _only_team(decls) -> TeamDecl:
    teams = [d for d in decls.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]


def test_role_scope_contained_in_ceiling_compiles() -> None:
    src = """team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { scope: "src/api/**", tools: ["fs"] }
  }
}
"""
    td = _only_team(_prog(src))
    _, registry = compile_team(td)
    bk = registry.get("backend")
    assert bk is not None and bk.scope is not None
    assert bk.scope.globs == ("src/api/**",)


def test_role_scope_outside_ceiling_rejects() -> None:
    src = """team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { scope: "etc/**", tools: ["fs"] }
  }
}
"""
    td = _only_team(_prog(src))
    with pytest.raises(VossTeamConfigError) as ei:
        compile_team(td)
    msg = str(ei.value)
    assert "backend" in msg
    assert "src/**" in msg and "etc/**" in msg


def test_role_without_scope_inherits_ceiling() -> None:
    src = """team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { model: "opus", tools: ["fs"] }
  }
}
"""
    td = _only_team(_prog(src))
    config, registry = compile_team(td)
    assert config.ceiling.scope is not None
    spec = registry.get("backend")
    assert spec is not None and spec.scope is not None
    assert spec.scope.globs == config.ceiling.scope.globs


def test_role_scope_equals_ceiling_compiles() -> None:
    src = """team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { scope: "src/**", tools: ["fs"] }
  }
}
"""
    td = _only_team(_prog(src))
    config, registry = compile_team(td)
    bk = registry.get("backend")
    assert config.ceiling.scope is not None and bk is not None
    assert bk.scope is not None
    assert bk.scope.globs == config.ceiling.scope.globs


def test_glob_containment_heuristic_known_cases() -> None:
    ceil = TeamRoleScope(("src/**",))

    assert TeamRoleScope(("src/api/**",)).is_contained_in(ceil) is True
    assert TeamRoleScope(("src/web/**",)).is_contained_in(ceil) is True
    assert TeamRoleScope(("src/ml/**",)).is_contained_in(ceil) is True

    assert TeamRoleScope(("etc/**",)).is_contained_in(ceil) is False
    web = TeamRoleScope(("src/web/**",))
    assert TeamRoleScope(("src/api/**",)).is_contained_in(web) is False

    # Known limitation under prefix-up-to-wildcard: not semantic path-set inclusion.
    assert TeamRoleScope(("**/test/**",)).is_contained_in(ceil) is False


def test_union_of_role_scopes_subset_of_ceiling() -> None:
    td = _only_team(_prog(_STRAWMAN.read_text(encoding="utf-8"), "team_strawman.voss"))
    config, registry = compile_team(td)
    ceil = config.ceiling.scope
    assert ceil is not None
    for spec in registry.entries():
        if spec.scope is None:
            continue
        for g in spec.scope.globs:
            assert TeamRoleScope((g,)).is_contained_in(ceil) is True


def test_scope_string_form_and_list_form_equivalent() -> None:
    string_team = """team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { scope: "src/api/**", tools: ["fs"] }
  }
}
"""
    list_team = """team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster e {
    backend { scope: ["src/api/**"], tools: ["fs"] }
  }
}
"""
    _, registry_s = compile_team(_only_team(_prog(string_team)))
    _, registry_l = compile_team(_only_team(_prog(list_team)))
    assert registry_s.get("backend") is not None
    assert registry_l.get("backend") is not None
    assert registry_s.get("backend").scope == registry_l.get("backend").scope
    assert registry_s.get("backend").scope == TeamRoleScope(("src/api/**",))
