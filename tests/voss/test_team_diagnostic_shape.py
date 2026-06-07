"""V10 RED scaffold — VossTeamConfigError diagnostic shape (VLANG-02).

Asserts the planned diagnostic surface that V10-04 retrofits: every config error
carries a non-empty `construct`, a non-empty `fix_hint`, and a
`format_diagnostic()` rendering a `file:line` substring. Those attributes do not
exist yet — RED expected. No expected-fail/skip masks (gsd-scaffold-fictional-api).
"""
from __future__ import annotations

import re

import pytest

from voss import parse
from voss.ast_nodes import Span, TeamDecl
from voss.harness.team import VossTeamConfigError, compile_team


def _only_team(src: str) -> TeamDecl:
    prog = parse(src if src.endswith("\n") else src + "\n", "<test>")
    teams = [d for d in prog.body if isinstance(d, TeamDecl)]
    assert len(teams) == 1
    return teams[0]


# Sources that raise VossTeamConfigError TODAY (verified), one per construct.
_BUDGET_SRC = """team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
  roster e {
    backend { budget: 5000 tokens }
  }
}
"""

_SCOPE_SRC = """team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
  roster e {
    backend { scope: "other/**" }
  }
}
"""

_MODEL_SRC = """team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
  roster e {
    backend { model: ["x"] }
  }
}
"""


def _assert_diagnostic_shape(err: VossTeamConfigError, expected_construct: str) -> None:
    assert err.construct == expected_construct
    assert err.fix_hint != ""
    diag = err.format_diagnostic()
    assert re.search(r":\d+", diag), f"expected file:line in {diag!r}"


def test_budget_overflow_diagnostic() -> None:
    with pytest.raises(VossTeamConfigError) as ei:
        compile_team(_only_team(_BUDGET_SRC))
    _assert_diagnostic_shape(ei.value, "budget")


def test_scope_overflow_diagnostic() -> None:
    with pytest.raises(VossTeamConfigError) as ei:
        compile_team(_only_team(_SCOPE_SRC))
    _assert_diagnostic_shape(ei.value, "scope")


def test_model_type_diagnostic() -> None:
    with pytest.raises(VossTeamConfigError) as ei:
        compile_team(_only_team(_MODEL_SRC))
    _assert_diagnostic_shape(ei.value, "model")


def test_missing_ceiling_diagnostic() -> None:
    # The parser requires a ceiling, so the compile-time missing-ceiling raise
    # (construct=="ceiling") is reached by constructing a TeamDecl directly.
    span = Span(file="<test>", line_start=1, col_start=1, line_end=1, col_end=1)
    td = TeamDecl(
        span=span,
        name="Eng",
        ceiling=None,
        policy=None,
        agents=(),
        rosters=(),
        board=None,
        rituals=(),
    )
    with pytest.raises(VossTeamConfigError) as ei:
        compile_team(td)
    _assert_diagnostic_shape(ei.value, "ceiling")
