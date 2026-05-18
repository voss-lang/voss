"""
Project Index context renderer (M10-05 Task 1).

Produces a bounded `## Project Index` markdown section with no raw snippets.
"""

from __future__ import annotations

from typing import Any

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

    lines: list[str] = ["## Project Index", ""]

    # Language counts
    if summary.languages:
        lang_line = ", ".join(f"{lang} ({cnt})" for lang, cnt in sorted(summary.languages.items(), key=lambda x: -x[1]))
        lines.append(f"**Files by language:** {lang_line}")
        lines.append("")

    # Top modules
    if summary.top_modules:
        lines.append("**Top modules by symbol count:**")
        for mod, cnt in summary.top_modules[:10]:
            lines.append(f"- `{mod}` — {cnt} symbols")
        lines.append("")

    # Entry points
    if summary.entry_points:
        eps = ", ".join(f"`{e}`" for e in summary.entry_points[:5])
        lines.append(f"**Entry points:** {eps}")
        lines.append("")

    lines.append(f"_Total: {summary.file_count} files, {summary.symbol_count} symbols_")

    body = "\n".join(lines)

    # Simple truncation guard (real token count would be better, but this satisfies the plan for v0.2)
    if len(body) > max_tokens * 3.5:  # rough chars-to-tokens
        body = body[: int(max_tokens * 3.5)] + "\n\n(truncated)"

    return body
