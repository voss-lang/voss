"""Project prompt override loader (V16-04, R5/D-18).

`voss sync` writes editable copies of the reviewer/EM prompts under
`.voss/prompts/<name>.txt`. At load time the project copy wins when present;
otherwise the package template renders byte-identically to today (R5).
Runtime placeholders are filled via plain str.replace — never Jinja at
runtime (D-18), so user edits cannot raise StrictUndefined.
"""
from __future__ import annotations

from pathlib import Path

from voss.harness.cognition import voss_dir
from voss.template_render import render_package_template


def default_runtime_vars(agent: str, root: Path) -> dict[str, str]:
    """The standard ${AGENT}/${PROJECT}/${WORKSPACE} substitution set (D-18)."""
    return {"AGENT": agent, "PROJECT": root.name, "WORKSPACE": str(root)}


def load_prompt(
    name: str,
    *,
    resource: str,
    cwd: Path | None = None,
    runtime_vars: dict[str, str] | None = None,
) -> str:
    """Return the project prompt copy when present, else the package render.

    Project copy: `<cwd>/.voss/prompts/<name>.txt`. Each runtime_vars key K
    replaces the literal `${K}` via str.replace; unknown placeholders pass
    through untouched. Absent/unreadable copy falls back to
    `render_package_template("voss", resource, {})`.
    """
    root = cwd if cwd is not None else Path.cwd()
    project_copy = voss_dir(root) / "prompts" / f"{name}.txt"
    if project_copy.is_file():
        try:
            text = project_copy.read_text()
        except (OSError, UnicodeDecodeError):
            text = None
        if text is not None:
            for key, value in (runtime_vars or {}).items():
                text = text.replace("${" + key + "}", value)
            return text
    return render_package_template("voss", resource, {})


__all__ = ["default_runtime_vars", "load_prompt"]
