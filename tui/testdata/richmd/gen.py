"""Regenerate the Rich reference renders: .venv/bin/python gen.py

Each NAME.md is rendered by rich.markdown.Markdown (code_theme="monokai"),
the renderer the Textual TUI uses, into NAME_WIDTH.txt as plain text with
trailing spaces removed.
"""
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

here = Path(__file__).parent
for md in sorted(here.glob("*.md")):
    for width in (40, 74):
        console = Console(width=width, color_system=None, record=True, file=open("/dev/null", "w"))
        console.print(Markdown(md.read_text(), code_theme="monokai"))
        lines = [line.rstrip() for line in console.export_text().split("\n")]
        while lines and lines[-1] == "":
            lines.pop()
        (here / f"{md.stem}_{width}.txt").write_text("\n".join(lines) + "\n")
