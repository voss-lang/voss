import pytest
from voss.ast_nodes import IntLit, FloatLit, StringLit, BoolLit, NullLit, Identifier, ExprStmt

@pytest.mark.parametrize("src,cls,attr,expected", [
    ("0", IntLit, "value", 0),
    ("42", IntLit, "value", 42),
    ("3.14", FloatLit, "value", 3.14),
    ('"hello"', StringLit, "value", "hello"),
    ('"with \\"quote\\""', StringLit, "value", 'with "quote"'),
    ("true", BoolLit, "value", True),
    ("false", BoolLit, "value", False),
])
def test_literal_parses(parse_source, src, cls, attr, expected):
    program = parse_source(src)
    stmt = program.body[0]
    assert isinstance(stmt, ExprStmt)
    assert isinstance(stmt.expr, cls)
    assert getattr(stmt.expr, attr) == expected

def test_null_literal(parse_source):
    program = parse_source("null")
    assert isinstance(program.body[0].expr, NullLit)

def test_triple_string(parse_source):
    program = parse_source('"""multi\nline"""')
    s = program.body[0].expr
    assert isinstance(s, StringLit)
    assert s.triple is True
    assert "multi" in s.value and "line" in s.value

def test_identifier(parse_source):
    program = parse_source("my_var")
    assert isinstance(program.body[0].expr, Identifier)
    assert program.body[0].expr.name == "my_var"

def test_span_populated(parse_source):
    program = parse_source("42")
    span = program.body[0].expr.span
    assert span.line_start == 1
    assert span.col_start == 1
    assert span.file == "<test>"
