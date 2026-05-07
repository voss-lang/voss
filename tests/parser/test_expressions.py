from pathlib import Path

from lark import Lark

from voss.ast_nodes import (
    BinOp,
    BudgetArg,
    Call,
    ConfidenceGate,
    DictLit,
    Identifier,
    Index,
    IntLit,
    ListLit,
    Member,
    UnaryOp,
)
from voss.parser import _Transformer


_GRAMMAR = (Path(__file__).resolve().parents[2] / "voss" / "grammar.lark").read_text()
_CONFIDENCE_PARSER = Lark(
    _GRAMMAR,
    parser="earley",
    lexer="dynamic",
    propagate_positions=True,
    start="confidence_gate",
)


def _parse_confidence_gate(src: str) -> ConfidenceGate:
    tree = _CONFIDENCE_PARSER.parse(src)
    return _Transformer("<test>").transform(tree)


def test_arithmetic_precedence(parse_source):
    p = parse_source("1 + 2 * 3")
    e = p.body[0].expr
    assert isinstance(e, BinOp) and e.op == "+"
    assert isinstance(e.right, BinOp) and e.right.op == "*"


def test_comparison(parse_source):
    p = parse_source("a < b")
    e = p.body[0].expr
    assert isinstance(e, BinOp) and e.op == "<"


def test_logical(parse_source):
    p = parse_source("a and b or c")
    e = p.body[0].expr
    assert isinstance(e, BinOp) and e.op == "or"
    assert isinstance(e.left, BinOp) and e.left.op == "and"


def test_full_expression_precedence(parse_source):
    p = parse_source("a + b * c == d - e and not f or g(x).y[0]")
    e = p.body[0].expr
    assert isinstance(e, BinOp) and e.op == "or"

    left = e.left
    assert isinstance(left, BinOp) and left.op == "and"
    assert isinstance(left.right, UnaryOp) and left.right.op == "not"

    comparison = left.left
    assert isinstance(comparison, BinOp) and comparison.op == "=="
    assert isinstance(comparison.left, BinOp) and comparison.left.op == "+"
    assert isinstance(comparison.left.right, BinOp) and comparison.left.right.op == "*"
    assert isinstance(comparison.right, BinOp) and comparison.right.op == "-"

    right = e.right
    assert isinstance(right, Index)
    assert isinstance(right.obj, Member) and right.obj.attr == "y"
    assert isinstance(right.obj.obj, Call)


def test_not(parse_source):
    p = parse_source("not x")
    e = p.body[0].expr
    assert isinstance(e, UnaryOp) and e.op == "not"


def test_confidence_gate_start_rule():
    gate = _parse_confidence_gate("result @ p >= 0.75")
    assert isinstance(gate, ConfidenceGate)
    assert isinstance(gate.target, Identifier)
    assert gate.target.name == "result"
    assert gate.op == ">="
    assert gate.threshold == 0.75


def test_unary_minus(parse_source):
    p = parse_source("-5")
    e = p.body[0].expr
    assert isinstance(e, UnaryOp) and e.op == "-"
    assert isinstance(e.operand, IntLit)


def test_call_no_args(parse_source):
    p = parse_source("foo()")
    e = p.body[0].expr
    assert isinstance(e, Call) and e.args == ()


def test_call_positional_and_named(parse_source):
    p = parse_source("gather(handles, timeout: 30s)")
    e = p.body[0].expr
    assert isinstance(e, Call)
    assert e.callee.name == "gather"
    assert e.args[0].name is None
    assert e.args[1].name == "timeout"
    assert isinstance(e.args[1].value, BudgetArg)
    assert e.args[1].value.unit == "s"


def test_member_chain(parse_source):
    p = parse_source("a.b.c")
    e = p.body[0].expr
    assert isinstance(e, Member) and e.attr == "c"
    assert isinstance(e.obj, Member) and e.obj.attr == "b"


def test_index(parse_source):
    p = parse_source("xs[0]")
    e = p.body[0].expr
    assert isinstance(e, Index)


def test_chained_call_member_index(parse_source):
    p = parse_source("a.b(1)[2]")
    e = p.body[0].expr
    assert isinstance(e, Index)
    assert isinstance(e.obj, Call)
    assert isinstance(e.obj.callee, Member)


def test_list_lit(parse_source):
    p = parse_source("[1, 2, 3,]")
    e = p.body[0].expr
    assert isinstance(e, ListLit)
    assert len(e.items) == 3


def test_dict_lit(parse_source):
    p = parse_source('{"k": 1, name: 2}')
    e = p.body[0].expr
    assert isinstance(e, DictLit)
    assert len(e.items) == 2


def test_paren_grouping(parse_source):
    p = parse_source("(1 + 2) * 3")
    e = p.body[0].expr
    assert isinstance(e, BinOp) and e.op == "*"
    assert isinstance(e.left, BinOp) and e.left.op == "+"


def test_continuation_inside_parens(parse_source):
    p = parse_source("foo(\n  1,\n  2,\n)")
    e = p.body[0].expr
    assert isinstance(e, Call) and len(e.args) == 2


def test_continuation_inside_list_brackets(parse_source):
    p = parse_source("[\n  1,\n  2,\n]")
    e = p.body[0].expr
    assert isinstance(e, ListLit) and len(e.items) == 2


def test_continuation_inside_dict_braces(parse_source):
    p = parse_source("{\n  name: 1,\n  other: 2,\n}")
    e = p.body[0].expr
    assert isinstance(e, DictLit) and len(e.items) == 2
