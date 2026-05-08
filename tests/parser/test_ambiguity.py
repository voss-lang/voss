import pytest
from pathlib import Path
from lark import Lark, Tree

GRAMMAR_PATH = Path(__file__).resolve().parents[2] / "voss" / "grammar.lark"
EXAMPLES_DIR = Path(__file__).parent / "examples"

@pytest.fixture(scope="module")
def ambig_parser():
    # Plan body specifies lexer="contextual"; Lark 1.x rejects that with Earley
    # ("Parser 'earley' does not support lexer 'contextual'"). Use "dynamic" to
    # match production parser config in voss/parser.py.
    return Lark(
        GRAMMAR_PATH.read_text(),
        parser="earley",
        lexer="dynamic",
        propagate_positions=True,
        ambiguity="explicit",
    )

def _has_ambig(tree) -> bool:
    if isinstance(tree, Tree):
        if tree.data == "_ambig":
            return True
        return any(_has_ambig(c) for c in tree.children)
    return False

@pytest.mark.parametrize("name", ["classify", "support", "research", "assistant"])
def test_no_ambiguity_in_examples(ambig_parser, name):
    src = (EXAMPLES_DIR / f"{name}.voss").read_text()
    tree = ambig_parser.parse(src)
    assert not _has_ambig(tree), f"Grammar produced ambiguous parses for {name}.voss"
