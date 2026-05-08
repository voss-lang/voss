from __future__ import annotations

from voss.ast_nodes import Program, Span, Stmt


def span(file: str = "example.voss", line: int = 1, col: int = 1) -> Span:
    return Span(
        file=file,
        line_start=line,
        col_start=col,
        line_end=line,
        col_end=col + 1,
    )


def program(*body: Stmt, file: str = "example.voss") -> Program:
    return Program(span=span(file=file), body=tuple(body))
