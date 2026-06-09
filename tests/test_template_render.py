from __future__ import annotations

import pytest
from jinja2 import UndefinedError

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
