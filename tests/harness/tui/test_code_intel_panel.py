"""M9-08 CodeIntelPanel standalone widget tests.

Uses a minimal pilot host for active-app context (Textual requirement for
child mutations). Widget logic remains standalone with no M10 imports.
"""

from __future__ import annotations

import pytest

from voss.harness.tui.app import VossTUIApp
from voss.harness.tui.widgets.code_intel_panel import CodeIntelPanel


def test_code_intel_panel_imports_cleanly() -> None:
    import ast
    import voss.harness.tui.widgets.code_intel_panel as mod
    with open(mod.__file__) as f:
        src = f.read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "voss.harness.code" in node.module:
            pytest.fail("Forbidden voss.harness.code import")
    assert "CodeIntelService" not in src


@pytest.mark.asyncio
async def test_code_intel_panel_all_modes() -> None:
    app = VossTUIApp()
    async with app.run_test() as pilot:
        p = CodeIntelPanel()
        pilot.app.mount(p)
        await pilot.pause()

        p.set_tree(None)
        await pilot.pause()
        body = p.query_one("#intel-body")
        texts = [str(getattr(w, "render", lambda: "")()) for w in body.children]
        assert any("No project index" in t for t in texts)

        p.set_tree([{"name": "src", "kind": "dir"}])
        await pilot.pause()
        texts = [str(getattr(w, "render", lambda: "")()) for w in body.children]
        assert any("Project tree" in t for t in texts)

        p.set_results("foo", [{"file": "a.py", "line": 42}])
        await pilot.pause()
        texts = [str(getattr(w, "render", lambda: "")()) for w in body.children]
        assert any("Results for: foo" in t for t in texts)

        p.set_focus({"file": "x.py", "line": 10}, ["def x():"])
        await pilot.pause()
        texts = [str(getattr(w, "render", lambda: "")()) for w in body.children]
        assert any("Focus: x.py:10" in t for t in texts)
