import json
import pytest
from pathlib import Path
from voss import parse, to_dict

EXAMPLES_DIR = Path(__file__).parent / "examples"
GOLDEN_DIR = Path(__file__).parent / "golden"
NAMES = ("classify", "support", "research", "assistant")

@pytest.mark.parametrize("name", NAMES)
def test_example_parses(name):
    src = (EXAMPLES_DIR / f"{name}.voss").read_text()
    program = parse(src, file=f"{name}.voss")
    assert program is not None

@pytest.mark.parametrize("name", NAMES)
def test_example_matches_golden(name):
    src = (EXAMPLES_DIR / f"{name}.voss").read_text()
    program = parse(src, file=f"{name}.voss")
    actual = to_dict(program, normalize_spans=True)
    expected = json.loads((GOLDEN_DIR / f"{name}.ast.json").read_text())
    assert actual == expected, f"AST diverged from golden for {name}.voss"
