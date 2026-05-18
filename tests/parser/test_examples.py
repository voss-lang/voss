import json
from pathlib import Path

import pytest
from voss import parse, to_dict

EXAMPLES_DIR = Path(__file__).parent / "examples"
GOLDEN_DIR = Path(__file__).parent / "golden"
NAMES = ("classify", "support", "research", "assistant", "grammar_surface")
COVERAGE_NAMES = ("coverage/memory_semantic", "coverage/memory_working")
GOLDEN_MATCH_NAMES = NAMES + COVERAGE_NAMES

@pytest.mark.parametrize("name", NAMES)
def test_example_parses(name):
    src = (EXAMPLES_DIR / f"{name}.voss").read_text()
    program = parse(src, file=f"{name}.voss")
    assert program is not None


@pytest.mark.parametrize("name", COVERAGE_NAMES)
def test_coverage_example_parses(name):
    src = (EXAMPLES_DIR / f"{name}.voss").read_text()
    program = parse(src, file=f"{name}.voss")
    assert program.body

@pytest.mark.parametrize("name", GOLDEN_MATCH_NAMES)
def test_example_matches_golden(name):
    src = (EXAMPLES_DIR / f"{name}.voss").read_text()
    program = parse(src, file=f"{Path(name).name}.voss")
    actual = to_dict(program, normalize_spans=True)
    expected = json.loads((GOLDEN_DIR / f"{name}.ast.json").read_text())
    assert actual == expected, f"AST diverged from golden for {name}.voss"
