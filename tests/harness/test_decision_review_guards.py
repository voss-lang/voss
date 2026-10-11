from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DECISION_REVIEW = ROOT / "voss" / "harness" / "decision_review.py"
REVIEW_SHADOW = ROOT / "voss" / "harness" / "board" / "review_shadow.py"
BOARD = ROOT / "voss" / "harness" / "board"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text())


def _is_review_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "review"


def _targets(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return node.targets
    if isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        return [node.target]
    return []


def verdict_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    bindings = {
        id(node): {t.id for t in node.targets if isinstance(t, ast.Name)}
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and _is_review_call(node.value)
    }
    names = set().union(*bindings.values())
    found = []
    for node in ast.walk(tree):
        for target in _targets(node):
            if isinstance(target, ast.Name) and target.id in names and target.id not in bindings.get(id(node), set()):
                found.append(f"reassigned {target.id}")
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id in names:
                found.append(f"attribute set on {target.value.id}")
        if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in names:
            func = node.func
            if (isinstance(func, ast.Name) and func.id == "replace") or (isinstance(func, ast.Attribute) and func.attr == "replace"):
                found.append(f"replace on {node.args[0].id}")
    return found


@pytest.mark.parametrize("path", [DECISION_REVIEW, REVIEW_SHADOW], ids=["decision_review", "review_shadow"])
def test_no_gates_import_and_no_reviewer_verdict(path):
    tree = _tree(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").endswith("gates")
            assert "gates" not in {a.name for a in node.names}
            assert "ReviewerVerdict" not in {a.name for a in node.names}
        if isinstance(node, ast.Import):
            assert not any(a.name.endswith("gates") for a in node.names)
        assert not (isinstance(node, ast.Name) and node.id == "ReviewerVerdict")
        assert not (isinstance(node, ast.Attribute) and node.attr == "ReviewerVerdict")


def test_review_shadow_never_changes_the_inner_verdict():
    source = REVIEW_SHADOW.read_text()
    tree = ast.parse(source)
    assert any(isinstance(n, ast.Assign) and _is_review_call(n.value) for n in ast.walk(tree))
    assert verdict_violations(source) == []
    assert not any(isinstance(n, ast.Attribute) and n.attr == "conf" for n in ast.walk(tree))


def test_guard_ignores_receipt_replace_in_decision_review():
    source = DECISION_REVIEW.read_text()
    assert "dataclasses.replace(receipt" in source
    assert verdict_violations(source) == []


@pytest.mark.parametrize(
    "bad",
    [
        "v = inner.review(card)\nv = dataclasses.replace(v, conf=1.0)\n",
        "v = inner.review(card)\nw = replace(v, verdict='pass')\n",
        "v = inner.review(card)\nv.conf = 1.0\n",
        "v = inner.review(card)\nv = other\n",
    ],
    ids=["dataclasses_replace", "bare_replace", "attribute_set", "reassigned"],
)
def test_guard_flags_a_changed_verdict(bad):
    assert verdict_violations(bad)


def test_gates_and_verdict_know_nothing_of_review():
    for name in ("gates.py", "verdict.py"):
        text = (BOARD / name).read_text()
        assert "decision_review" not in text
        assert "review_shadow" not in text


def test_machine_references_review_shadow_once():
    assert (BOARD / "machine.py").read_text().count("review_shadow") == 1
