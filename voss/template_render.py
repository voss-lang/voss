from __future__ import annotations

from functools import lru_cache
from collections.abc import Mapping
from typing import Any

from jinja2 import Environment, PackageLoader, StrictUndefined


@lru_cache(maxsize=None)
def _environment(package: str) -> Environment:
    return Environment(
        autoescape=False,
        keep_trailing_newline=True,
        loader=PackageLoader(package, ""),
        lstrip_blocks=True,
        trim_blocks=True,
        undefined=StrictUndefined,
    )


def render_package_template(
    package: str,
    resource: str,
    context: Mapping[str, Any],
) -> str:
    template = _environment(package).get_template(resource)
    return template.render(**context)
