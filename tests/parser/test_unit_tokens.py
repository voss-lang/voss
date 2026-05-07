import pytest
from voss.ast_nodes import BudgetArg

@pytest.mark.parametrize("src,unit,value", [
    ("4000 tokens", "tokens", 4000),
    ("20 turns", "turns", 20),
    ("500ms", "ms", 500),
    ("30s", "s", 30),
    ("$0.02", "usd", 0.02),
    ("$5", "usd", 5.0),
])
def test_unit_token_parses(parse_source, src, unit, value):
    program = parse_source(src)
    expr = program.body[0].expr
    assert isinstance(expr, BudgetArg)
    assert expr.unit == unit
    assert expr.value == value
    assert expr.raw.strip() == src

def test_unknown_unit_is_parse_error(parse_source):
    from voss import VossParseError
    with pytest.raises(VossParseError) as exc_info:
        parse_source("4000 banana", file="budget.voss")

    err = exc_info.value
    assert err.file == "budget.voss"
    assert err.line == 1
    assert err.col == 6
    assert isinstance(err.expected, list)
    assert "end of line" in err.expected
    assert isinstance(err.got, str)
    assert "b" in err.got
    assert isinstance(err.source_excerpt, str)
    assert "4000 banana" in err.source_excerpt
    assert "^" in err.source_excerpt
