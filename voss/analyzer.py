from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Protocol, Sequence

from .ast_nodes import Expr, Node, Program, Stmt
from .diagnostics import AnalysisResult, Diagnostic, EmittedIndex


class TokenEstimator(Protocol):
    def estimate_expr(self, expr: Expr, scope: "Scope") -> int | None: ...
    def estimate_stmt(self, stmt: Stmt, scope: "Scope") -> int | None: ...


class IndexBuilder(Protocol):
    model: str

    def build_cases(
        self, cases: Sequence[tuple[str, str]]
    ) -> list[dict[str, object]]: ...


@dataclass
class Scope:
    symbols: dict[str, object] = field(default_factory=dict)
    estimates: dict[str, int] = field(default_factory=dict)
    gated: set[str] = field(default_factory=set)


class Analyzer:
    def __init__(
        self,
        *,
        source_path: str | Path | None = None,
        cache_dir: str | Path = ".voss-cache",
        emit_indexes: bool = True,
        token_estimator: TokenEstimator | None = None,
        index_builder: IndexBuilder | None = None,
    ) -> None:
        self.source_path = Path(source_path) if source_path is not None else None
        self.cache_dir = Path(cache_dir)
        self.emit_indexes = emit_indexes
        self.token_estimator = token_estimator
        self.index_builder = index_builder
        self.diagnostics: list[Diagnostic] = []
        self.indexes: list[EmittedIndex] = []
        self.scope_stack: list[Scope] = [Scope()]

    def analyze_program(self, program: Program) -> AnalysisResult:
        for stmt in program.body:
            self._visit_stmt(stmt)
        return AnalysisResult(
            diagnostics=tuple(self.diagnostics),
            indexes=tuple(self.indexes),
        )

    def _visit_stmt(self, stmt: Stmt) -> None:
        self._walk(stmt)

    def _visit_expr(self, expr: Expr) -> None:
        self._walk(expr)

    def _walk(self, node: Node) -> None:
        if not is_dataclass(node):
            return
        for f in fields(node):
            if f.name == "span":
                continue
            value = getattr(node, f.name)
            self._walk_value(value)

    def _walk_value(self, value: object) -> None:
        if isinstance(value, Node):
            self._walk(value)
            return
        if isinstance(value, (tuple, list)):
            for item in value:
                self._walk_value(item)
            return
        if isinstance(value, dict):
            for k, v in value.items():
                self._walk_value(k)
                self._walk_value(v)


def analyze(
    program: Program,
    *,
    source_path: str | Path | None = None,
    cache_dir: str | Path = ".voss-cache",
    emit_indexes: bool = True,
    token_estimator: TokenEstimator | None = None,
    index_builder: IndexBuilder | None = None,
) -> AnalysisResult:
    analyzer = Analyzer(
        source_path=source_path,
        cache_dir=cache_dir,
        emit_indexes=emit_indexes,
        token_estimator=token_estimator,
        index_builder=index_builder,
    )
    return analyzer.analyze_program(program)
