from __future__ import annotations

import importlib.resources
from collections.abc import Mapping
from typing import Any

from jinja2 import Environment, StrictUndefined


_ENV = Environment(
    autoescape=False,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)


def render_package_template(
    package: str,
    resource: str,
    context: Mapping[str, Any],
) -> str:
    template = importlib.resources.files(package).joinpath(resource)
    return _ENV.from_string(template.read_text()).render(**context)
