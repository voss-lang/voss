"""O3-01 Task 2: AST import-set proof for verdict.py (O4 plug-in safety).

This is the load-bearing OBRD-07 acceptance test. If this test breaks,
O4's Reviewer A/B impls will have circular-import problems.
"""
from __future__ import annotations

import ast
from pathlib import Path


def test_verdict_imports_only_stdlib():
    """verdict.py must import ONLY from {typing, dataclasses, __future__}."""
    source = Path("voss/harness/board/verdict.py").read_text()
    tree = ast.parse(source)

    found_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                found_modules.add(node.module)
            # level > 0 means relative import — that would be a harness dep.
            if node.level and node.level > 0:
                found_modules.add(f"<relative level={node.level}>")

    allowed = {"typing", "dataclasses", "__future__"}
    extra = found_modules - allowed
    assert extra == set(), (
        f"verdict.py imports non-allowed modules: {extra}. "
        f"Only {allowed} are permitted (O3-SPEC L124)."
    )
