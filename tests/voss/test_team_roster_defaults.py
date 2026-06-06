"""Default seven-role roster + per-role tier-based defaults (VTEAM-09)."""

from __future__ import annotations

from voss import parse
from voss.ast_nodes import TeamDecl
from voss.harness.team import DEFAULT_ROSTER, compile_team

_SEVEN = ("architect", "backend", "frontend", "tester", "reviewer", "skeptic", "docs")

# Broad ceiling so every default role scope (src/**, tests/**, docs/** subtrees)
# is contained — matches the PRD §"Example Syntax" ceiling.
_EMPTY_ROSTER_SRC = '''team Eng {
  ceiling { budget: 120000 tokens, scope: ["src/**", "tests/**", "docs/**"] }
}
'''


def _only_team(src: str) -> TeamDecl:
    prog = parse(src if src.endswith("\n") else src + "\n", "<test>")
    teams = [d for d in prog.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]


def test_default_roster_is_the_prd_seven() -> None:
    assert DEFAULT_ROSTER == _SEVEN


def test_empty_roster_injects_seven_roles() -> None:
    config, registry = compile_team(_only_team(_EMPTY_ROSTER_SRC))
    assert config.roster_ids == frozenset(_SEVEN)
    assert set(registry.ids()) == set(_SEVEN)


def test_each_default_role_has_full_defaults() -> None:
    _, registry = compile_team(_only_team(_EMPTY_ROSTER_SRC))
    for name in _SEVEN:
        spec = registry.get(name)
        assert spec is not None, name
        assert spec.description.strip(), name
        assert spec.role_prompt.strip(), name
        # model-tier resolved to a concrete (non-tier) id.
        assert spec.model and spec.model not in ("strong", "cheap", "fast"), name
        assert spec.scope is not None and len(spec.scope.globs) >= 1, name
        assert spec.tools is not None and len(spec.tools) >= 1, name


def test_declared_roster_suppresses_injection() -> None:
    src = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster r {
    backend { model: "opus", scope: "src/api/**", tools: ["fs"] }
  }
}
'''
    config, registry = compile_team(_only_team(src))
    assert config.roster_ids == frozenset({"backend"})
    assert registry.get("architect") is None


def test_agents_only_suppresses_injection() -> None:
    src = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  agent em { scope: "all" }
}
'''
    config, _ = compile_team(_only_team(src))
    assert config.roster_ids == frozenset({"em"})


def test_legacy_ui_ai_still_resolve() -> None:
    src = '''team Eng {
  ceiling { budget: 100 tokens, scope: "src/**" }
  roster r {
    ui { scope: "src/ui/**", tools: ["fs"] }
    ai { scope: "src/ai/**", tools: ["fs", "net"] }
  }
}
'''
    _, registry = compile_team(_only_team(src))
    ui = registry.get("ui")
    ai = registry.get("ai")
    assert ui is not None and "ui" in ui.description.lower()
    assert ai is not None and ai.net is True
