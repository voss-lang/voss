from __future__ import annotations

import pytest
from jinja2 import UndefinedError

from voss.harness.agent import _compose_prior_context_block
from voss.harness.cognition import bootstrap_prompt
from voss.template_render import render_package_template


def test_render_package_template_uses_strict_undefined() -> None:
    with pytest.raises(UndefinedError, match="project_name"):
        render_package_template("voss", "templates/init/README.md.jinja", {})


def test_render_package_template_preserves_trailing_newline() -> None:
    rendered = render_package_template(
        "voss",
        "templates/init/pyproject.toml.jinja",
        {"project_name": "demo"},
    )

    assert rendered == (
        "[project]\n"
        'name = "demo"\n'
        'version = "0.1.0"\n'
        'description = "A Voss project."\n'
        'requires-python = ">=3.11"\n'
        "dependencies = [\n"
        '    "voss",\n'
        "]\n"
    )


def test_bootstrap_prompt_renders_inventory_sections() -> None:
    rendered = bootstrap_prompt(
        {
            "name": "demo",
            "git_head": "abc123",
            "analyzed_at": "2026-01-01T00:00:00Z",
            "file_count": 3,
            "primary_language": "python",
            "dir_tree": [],
            "manifest_path": "",
            "manifest_head": "",
            "readme_head": "",
        }
    )

    assert "project `demo`" in rendered
    assert "### Top-level directory tree" in rendered
    assert "  (none)" in rendered
    assert "### Manifest: (none detected)" in rendered
    assert "### README.md: (missing)" in rendered
    assert "git_head: abc123" in rendered


def test_prior_context_block_renders_single_run() -> None:
    rendered = _compose_prior_context_block(
        {
            "goal": "fix bug",
            "plan": {"rationale": "inspect first"},
            "decisions": [{"title": "use grep"}],
            "follow_ups": [],
            "risks": ["flaky test"],
        }
    )

    assert rendered.startswith("Prior context (most-recent turn):\n")
    assert "- goal: fix bug" in rendered
    assert "  - use grep" in rendered
    assert "- follow_ups:\n(none)" in rendered
    assert "  - flaky test" in rendered
