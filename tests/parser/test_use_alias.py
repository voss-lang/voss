from voss.ast_nodes import UseStmt
from voss.parser import parse


def test_use_with_alias_parses():
    program = parse("use foo::bar as baz\n", file="<test>")
    use = program.body[0]
    assert isinstance(use, UseStmt)
    assert use.path == ("foo", "bar")
    assert use.alias == "baz"


def test_use_without_alias_still_works():
    program = parse("use foo::bar\n", file="<test>")
    use = program.body[0]
    assert isinstance(use, UseStmt)
    assert use.path == ("foo", "bar")
    assert use.alias is None


def test_use_with_alias_single_segment_path():
    program = parse("use foo as bar\n", file="<test>")
    use = program.body[0]
    assert isinstance(use, UseStmt)
    assert use.path == ("foo",)
    assert use.alias == "bar"
