from pathlib import Path

from lark import Lark

from voss.ast_nodes import BudgetArg, StringLit, TypeRef
from voss.parser import _Transformer

# Build a parser whose start rule is type_expr. Lark 1.x does not support
# lexer="contextual" with parser="earley"; the production parser uses the
# Earley-compatible dynamic lexer, so this helper mirrors that reality.
_GRAMMAR = (Path(__file__).resolve().parents[2] / "voss" / "grammar.lark").read_text()
_TYPE_PARSER = Lark(
    _GRAMMAR,
    parser="earley",
    lexer="dynamic",
    propagate_positions=True,
    start="type_expr",
)


def _parse_type(src: str) -> TypeRef:
    tree = _TYPE_PARSER.parse(src)
    return _Transformer("<test>").transform(tree)


def test_simple_name():
    t = _parse_type("string")
    assert t.name.parts == ("string",)
    assert t.generics == ()
    assert t.kwargs == ()


def test_dotted_name():
    t = _parse_type("memory.episodic")
    assert t.name.parts == ("memory", "episodic")


def test_single_generic():
    t = _parse_type("list<string>")
    assert t.name.parts == ("list",)
    assert len(t.generics) == 1
    assert t.generics[0].name.parts == ("string",)


def test_multi_generic():
    t = _parse_type("dict<string, int>")
    assert len(t.generics) == 2


def test_nested_generic():
    t = _parse_type("dict<string, list<probable<int>>>")
    inner = t.generics[1]
    assert inner.name.parts == ("list",)
    assert inner.generics[0].name.parts == ("probable",)
    assert inner.generics[0].generics[0].name.parts == ("int",)


def test_probable_generic():
    t = _parse_type("probable<string>")
    assert t.name.parts == ("probable",)
    assert t.generics[0].name.parts == ("string",)


def test_memory_kwargs_turns():
    t = _parse_type("memory.episodic(capacity: 20 turns)")
    assert t.name.parts == ("memory", "episodic")
    assert len(t.kwargs) == 1
    kw = t.kwargs[0]
    assert kw.name == "capacity"
    assert isinstance(kw.value, BudgetArg)
    assert kw.value.unit == "turns"
    assert kw.value.value == 20


def test_memory_kwargs_strings():
    t = _parse_type('memory.semantic(source: "./docs/", model: "all-MiniLM-L6-v2")')
    assert t.name.parts == ("memory", "semantic")
    names = [k.name for k in t.kwargs]
    assert names == ["source", "model"]
    assert isinstance(t.kwargs[0].value, StringLit)


def test_trailing_comma_allowed():
    t = _parse_type("dict<string, int,>")
    assert len(t.generics) == 2


def test_kwargs_trailing_comma():
    t = _parse_type("memory.episodic(capacity: 20 turns,)")
    assert len(t.kwargs) == 1


def test_generics_allow_newline_continuation():
    t = _parse_type("dict<\n  string,\n  list<int>,\n>")
    assert len(t.generics) == 2
    assert t.generics[1].name.parts == ("list",)
