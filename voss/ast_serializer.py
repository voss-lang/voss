from __future__ import annotations
from dataclasses import fields
from typing import Any
from pathlib import Path

from .ast_nodes import Node, Span


def to_dict(node: Any, *, normalize_spans: bool = False) -> Any:
    """Convert a Voss AST node tree to a deterministic JSON-serializable dict.

    When normalize_spans=True:
      - Span.file is replaced with its basename only (path-stable across machines).
      - Span.line_start/col_start/line_end/col_end are zeroed.
      - Span.synthetic flag preserved.
    """
    if isinstance(node, Span):
        if normalize_spans:
            return {
                "file": Path(node.file).name if node.file != "<synthetic>" else node.file,
                "lines": [0, 0],
                "cols": [0, 0],
                "synthetic": node.synthetic,
            }
        return {
            "file": node.file,
            "lines": [node.line_start, node.line_end],
            "cols": [node.col_start, node.col_end],
            "synthetic": node.synthetic,
        }
    if isinstance(node, Node):
        out: dict[str, Any] = {"_node": type(node).__name__}
        for f in fields(node):
            val = getattr(node, f.name)
            out[f.name] = to_dict(val, normalize_spans=normalize_spans)
        return out
    if isinstance(node, (list, tuple)):
        return [to_dict(c, normalize_spans=normalize_spans) for c in node]
    if isinstance(node, dict):
        return {k: to_dict(v, normalize_spans=normalize_spans) for k, v in node.items()}
    # Primitives — int, float, str, bool, None.
    return node
