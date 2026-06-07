"""V10 RED scaffold — gate{} block compile to GateConfig (VLANG-01b).

Targets the planned GateConfig (voss.harness.team) and TeamConfig.gate_configs.
RED expected. No expected-fail/skip masks (gsd-scaffold-fictional-api).
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


_TEAM_WITH_GATE = """team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
  gate done {
    require tests_passed
    require independent_review
    require evidence_refs
  }
}
"""


def test_gate_block_compiles_to_gate_config() -> None:
    from voss.harness.team import GateConfig

    config, _registry = compile_team(_only_team(_prog(_TEAM_WITH_GATE)))
    assert len(config.gate_configs) == 1
    gate = config.gate_configs[0]
    assert isinstance(gate, GateConfig)
    assert gate.name == "done"
    assert gate.requires == frozenset(
        {"tests_passed", "independent_review", "evidence_refs"}
    )
