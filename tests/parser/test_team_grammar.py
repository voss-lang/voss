"""Acceptance tests for `team { … }` grammar (OTEAM-01, OTEAM-04, OTEAM-08)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from voss.ast_nodes import (
    AgentDecl,
    BoardDecl,
    BoardGate,
    CeilingDecl,
    RitualDecl,
    RosterDecl,
    Span,
    TeamAgentDecl,
    TeamDecl,
)
from voss.parser import VossParseError
from voss.harness.team import TeamCeiling, TeamPolicy, TeamRoleScope

_EXAMPLES = Path(__file__).resolve().parent / "examples"
_STRAWMAN = _EXAMPLES / "team_strawman.voss"


def test_minimal_team_parses(parse_source):
    prog = parse_source(
        """team Eng {
  ceiling { budget: 1000 tokens, scope: \"src/**\" }
}
"""
    )
    teams = [d for d in prog.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    td = teams[0]
    assert td.name == "Eng"
    assert td.ceiling is not None
    assert td.ceiling.budget == 1000
    assert td.ceiling.scope == ("src/**",)


def test_full_strawman_parses(parse_source):
    src = _STRAWMAN.read_text(encoding="utf-8")
    prog = parse_source(src, file="team_strawman.voss")
    teams = [d for d in prog.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    td = teams[0]
    assert td.name == "Engineering"

    agents = [a for a in td.agents if isinstance(a, TeamAgentDecl)]
    assert len(agents) == 1
    assert agents[0].name == "em"

    assert len(td.rosters) == 1
    r0 = td.rosters[0]
    assert isinstance(r0, RosterDecl)
    assert r0.name == "engineers"
    assert tuple(role.name for role in r0.roles) == ("backend", "frontend", "ui", "ai")

    assert td.board is not None
    assert isinstance(td.board, BoardDecl)

    rituals = td.rituals
    assert len(rituals) == 1
    assert isinstance(rituals[0], RitualDecl)
    assert rituals[0].name == "ContextDigest"


def test_unknown_ceiling_key_rejects(parse_source):
    with pytest.raises(VossParseError) as ei:
        parse_source(
            """team Eng {
  ceiling { foo: 1 }
}
"""
        )
    err = ei.value
    assert f"{err.line}:{err.col}" in str(err)


def test_unknown_role_kv_key_rejects(parse_source):
    with pytest.raises(VossParseError) as ei:
        parse_source(
            """team Eng {
  ceiling { budget: 100 tokens }
  roster e {
    backend { foo: 1 }
  }
}
"""
        )
    err = ei.value
    assert f"{err.line}:{err.col}" in str(err)


def test_team_agent_no_paren_collision(parse_source):
    prog_team = parse_source(
        """team E {
  ceiling { budget: 100 tokens }
  agent em { model: \"opus\" }
}
"""
    )
    td = next(d for d in prog_team.body if isinstance(d, TeamDecl))
    assert len(td.agents) == 1
    assert isinstance(td.agents[0], TeamAgentDecl)
    assert td.agents[0].name == "em"

    prog_agent = parse_source("agent em(x) { x }\n", file="agent.voss")
    ad = prog_agent.body[0]
    assert isinstance(ad, AgentDecl)
    assert ad.name == "em"
    assert len(ad.params) == 1


def test_duplicate_ceiling_rejects(parse_source):
    with pytest.raises(VossParseError) as ei:
        parse_source(
            """team Eng {
  ceiling { budget: 100 tokens }
  ceiling { budget: 200 tokens }
}
"""
        )
    msg = str(ei.value)
    assert "duplicate" in msg.lower()
    assert "Eng" in msg


def test_missing_ceiling_rejects(parse_source):
    with pytest.raises(VossParseError) as ei:
        parse_source(
            """team Eng {
  agent em { model: \"opus\" }
}
"""
        )
    msg = str(ei.value)
    assert "missing required block: ceiling" in msg
    assert "Eng" in msg


def test_team_decl_is_frozen():
    span = Span(
        file="<t>",
        line_start=1,
        col_start=1,
        line_end=1,
        col_end=1,
    )
    ceil = CeilingDecl(
        span=span,
        budget=1,
        scope=("x",),
        latency_seconds=None,
    )
    td = TeamDecl(
        span=span,
        name="T",
        ceiling=ceil,
        policy=None,
        agents=(),
        rosters=(),
        board=None,
        rituals=(),
    )
    with pytest.raises(FrozenInstanceError):
        td.name = "nope"  # type: ignore[misc]


def test_team_ceiling_value_object_is_frozen():
    tc = TeamCeiling(
        budget_tokens=1,
        scope=TeamRoleScope(("src/**",)),
        latency_seconds=None,
    )
    with pytest.raises(FrozenInstanceError):
        tc.budget_tokens = 2  # type: ignore[misc]


def test_team_policy_value_object_is_frozen():
    pol = TeamPolicy(p=0.85)
    with pytest.raises(FrozenInstanceError):
        pol.p = None  # type: ignore[misc]


def test_board_block_round_trips_opaquely(parse_source):
    src = _STRAWMAN.read_text(encoding="utf-8")
    prog = parse_source(src, file="team_strawman.voss")
    td = next(d for d in prog.body if isinstance(d, TeamDecl))
    assert td.board is not None
    items = td.board.items
    assert isinstance(items, tuple) and len(items) > 0
    gates = [x for x in items if isinstance(x, BoardGate)]
    assert gates, "expected at least one BoardGate"
    assert any("Done" in repr(g) for g in gates)


def test_ritual_block_round_trips_opaquely(parse_source):
    src = _STRAWMAN.read_text(encoding="utf-8")
    prog = parse_source(src, file="team_strawman.voss")
    td = next(d for d in prog.body if isinstance(d, TeamDecl))
    ritual = td.rituals[0]
    assert ritual.name == "ContextDigest"
    keys = {k for k, _ in ritual.kvs}
    assert "every" in keys


# ---------------------------------------------------------------------------
# V10 Wave-0 RED: principles / gate / memory blocks (VLANG-01a/01b/01c).
# These import planned AST nodes that DO NOT EXIST YET (created in V10-02) —
# the four tests below are expected RED. No xfail masks (gsd-scaffold-fictional-api).
# ---------------------------------------------------------------------------


def test_principles_block_parses(parse_source):
    from voss.ast_nodes import PrinciplesBlockDecl

    prog = parse_source(
        """principles {
  diff: "Make the smallest diff that solves the task."
  evidence: "No factual claim without evidence."
}
"""
    )
    blocks = [d for d in prog.body if isinstance(d, PrinciplesBlockDecl)]
    assert len(blocks) == 1
    assert blocks[0].items == (
        ("diff", "Make the smallest diff that solves the task."),
        ("evidence", "No factual claim without evidence."),
    )


def test_team_with_principles_block(parse_source):
    from voss.ast_nodes import PrinciplesBlockDecl

    prog = parse_source(
        """team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
  principles {
    diff: "Make the smallest diff that solves the task."
  }
}
"""
    )
    td = next(d for d in prog.body if isinstance(d, TeamDecl))
    assert isinstance(td.principles, PrinciplesBlockDecl)


def test_gate_block_parses(parse_source):
    from voss.ast_nodes import GateBlockDecl

    prog = parse_source(
        """gate done {
  require tests_passed
  require independent_review
  require evidence_refs
}
"""
    )
    blocks = [d for d in prog.body if isinstance(d, GateBlockDecl)]
    assert len(blocks) == 1
    assert blocks[0].name == "done"
    assert blocks[0].requires == (
        "tests_passed",
        "independent_review",
        "evidence_refs",
    )


def test_memory_block_parses(parse_source):
    from voss.ast_nodes import MemoryBlockDecl

    prog = parse_source(
        """memory {
  decisions: "d"
  sessions: "s"
}
"""
    )
    blocks = [d for d in prog.body if isinstance(d, MemoryBlockDecl)]
    assert len(blocks) == 1
    assert blocks[0].decisions == "d"
    assert blocks[0].sessions == "s"
    assert blocks[0].semantic is None
