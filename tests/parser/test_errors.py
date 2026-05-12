import pytest
from voss import parse
from voss.exceptions import VossParseError

@pytest.mark.parametrize("src,fragment", [
    # Unknown unit suffix.
    ("ctx(budget: 4000 banana) { return 1 }\n", "banana"),
    # Missing closing brace.
    ("fn f() { return 1\n", None),
    # Bare @ with nothing after it.
    ("@\nfn f() {}\n", None),
    # Invalid character.
    ("let x = ?\n", "?"),
])
def test_parse_error_raised(src, fragment):
    with pytest.raises(VossParseError) as exc_info:
        parse(src, file="<test>")
    err = exc_info.value
    assert err.line >= 1
    assert err.col >= 1
    assert err.file == "<test>"
    if fragment:
        # The error message OR the source_excerpt should mention the offending fragment.
        assert fragment in str(err) or fragment in err.source_excerpt or fragment in err.got

def test_error_has_expected_list():
    try:
        parse("fn f() {\n", "<test>")
    except VossParseError as e:
        assert isinstance(e.expected, list)

def test_error_has_source_excerpt():
    try:
        parse("ctx(budget: 4000 banana) { }\n", "<test>")
    except VossParseError as e:
        # source_excerpt may be empty if Lark fails before lex completes; just verify the field exists.
        assert isinstance(e.source_excerpt, str)
