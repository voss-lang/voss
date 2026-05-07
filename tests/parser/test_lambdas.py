import pytest

from voss import VossParseError
from voss.ast_nodes import BinOp, Call, Lambda, SpawnExpr


def test_single_arg_lambda(parse_source):
    p = parse_source("foo(t => t + 1)")
    arg = p.body[0].expr.args[0].value
    assert isinstance(arg, Lambda)
    assert len(arg.params) == 1
    assert arg.params[0].name == "t"
    assert isinstance(arg.body, BinOp)


def test_multi_arg_lambda(parse_source):
    p = parse_source("foo((x, y) => x + y)")
    arg = p.body[0].expr.args[0].value
    assert isinstance(arg, Lambda)
    assert [p.name for p in arg.params] == ["x", "y"]


def test_zero_arg_lambda(parse_source):
    p = parse_source("foo(() => 1)")
    arg = p.body[0].expr.args[0].value
    assert isinstance(arg, Lambda)
    assert arg.params == ()


def test_spawn_wraps_call(parse_source):
    p = parse_source("spawn Researcher(t)")
    e = p.body[0].expr
    assert isinstance(e, SpawnExpr)
    assert isinstance(e.agent, Call)
    assert e.agent.callee.name == "Researcher"


def test_spawn_rejects_non_call_target_as_parse_error(parse_source):
    with pytest.raises(VossParseError) as exc_info:
        parse_source("spawn foo.bar", file="spawn.voss")

    err = exc_info.value
    assert err.file == "spawn.voss"
    assert err.line == 1
    assert err.col == 1
    assert err.expected == ["a function or agent call"]
    assert err.got == "Member"
    assert "Error trying to process rule" not in str(err)


def test_lambda_with_spawn_body(parse_source):
    p = parse_source("topics.map(t => spawn Researcher(t))")
    lam = p.body[0].expr.args[0].value
    assert isinstance(lam, Lambda)
    assert isinstance(lam.body, SpawnExpr)


def test_lambda_with_bare_spawn_body(parse_source):
    p = parse_source("t => spawn x")
    lam = p.body[0].expr
    assert isinstance(lam, Lambda)
    assert isinstance(lam.body, SpawnExpr)
    assert isinstance(lam.body.agent, Call)
    assert lam.body.agent.callee.name == "x"
