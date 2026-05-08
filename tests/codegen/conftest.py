from __future__ import annotations

import ast as _ast

import pytest

from voss.ast_nodes import Program, Span, Stmt


def span(file: str = "example.voss", line: int = 1, col: int = 1) -> Span:
    return Span(file=file, line_start=line, col_start=col, line_end=line, col_end=col)


def program(*body: Stmt, file: str = "example.voss") -> Program:
    return Program(span=span(file=file), body=tuple(body))


def assert_python_parses(source: str) -> None:
    _ast.parse(source)


_FORBIDDEN_IMPORT_FRAGMENTS = ("from voss ", "from voss.", "import voss", "voss.analyzer")


def assert_no_compiler_imports(source: str) -> None:
    for fragment in _FORBIDDEN_IMPORT_FRAGMENTS:
        assert fragment not in source, f"generated source must not contain {fragment!r}"


@pytest.fixture
def make_span():
    return span


@pytest.fixture
def make_program():
    return program


@pytest.fixture
def python_parses():
    return assert_python_parses


@pytest.fixture
def no_compiler_imports():
    return assert_no_compiler_imports
