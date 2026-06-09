"""
Project Index context renderer (M10-05 Task 1).

Produces a bounded `## Project Index` markdown section with no raw snippets.
"""

from __future__ import annotations

from typing import Any

from voss.template_render import render_package_template

from .models import IndexSummary


def render_project_index_section(
    summary: IndexSummary | None,
    *,
    max_tokens: int = 1500,
    token_count_fn: Any = None,  # optional for future
) -> str:
    """
    Render the `## Project Index` section.

    - Counts by language
    - Top modules by symbol count
    - Entry points (if any)
    - Never includes raw file content
    - Adds (truncated) marker if we would exceed budget (simple length heuristic for now)
    """
    if summary is None or summary.file_count == 0:
        return ""

    languages = ""
    if summary.languages:
        languages = ", ".join(
            f"{lang} ({cnt})"
            for lang, cnt in sorted(summary.languages.items(), key=lambda x: -x[1])
        )
    top_modules = [
        {"path": module, "count": count} for module, count in summary.top_modules[:10]
    ]
    entry_points = ", ".join(f"`{entry}`" for entry in summary.entry_points[:5])

    body = render_package_template(
        "voss",
        "templates/code/project_index.md.jinja",
        {
            "languages": languages,
            "top_modules": top_modules,
            "entry_points": entry_points,
            "file_count": summary.file_count,
            "symbol_count": summary.symbol_count,
        },
    ).removesuffix("\n")

    # Simple truncation guard (real token count would be better, but this satisfies the plan for v0.2)
    if len(body) > max_tokens * 3.5:  # rough chars-to-tokens
        body = body[: int(max_tokens * 3.5)] + "\n\n(truncated)"

    return body
