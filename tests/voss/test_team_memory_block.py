"""V10 RED scaffold — memory{} block compile to MemoryConfig (VLANG-01c).

Targets the planned MemoryConfig (voss.harness.team) + TeamConfig.memory, and
the documented defaults. RED expected. No expected-fail/skip masks (gsd-scaffold-fictional-api).
"""
from __future__ import annotations

from voss import parse
from voss.ast_nodes import TeamDecl
from voss.harness.team import compile_team


def _prog(src: str, file: str = "<test>"):
    return parse(src if src.endswith("\n") else src + "\n", file)


def _only_team(decls) -> TeamDecl:
    teams = [d for d in decls.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]


_TEAM_FULL_MEMORY = """team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
  memory {
    decisions: "custom/dec"
    sessions: "custom/sess"
    semantic: "custom/sem"
  }
}
"""

_TEAM_PARTIAL_MEMORY = """team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
  memory {
    decisions: "custom/dec"
  }
}
"""


def test_memory_block_compiles_to_memory_config() -> None:
    from voss.harness.team import MemoryConfig

    config, _registry = compile_team(_only_team(_prog(_TEAM_FULL_MEMORY)))
    assert isinstance(config.memory, MemoryConfig)
    assert config.memory.decisions == "custom/dec"
    assert config.memory.sessions == "custom/sess"
    assert config.memory.semantic == "custom/sem"


def test_memory_block_defaults_when_keys_omitted() -> None:
    config, _registry = compile_team(_only_team(_prog(_TEAM_PARTIAL_MEMORY)))
    assert config.memory.decisions == "custom/dec"
    assert config.memory.sessions == ".voss/sessions"
    assert config.memory.semantic == ".voss-cache/semantic"
