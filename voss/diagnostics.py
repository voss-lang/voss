from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .ast_nodes import Span

DiagnosticSeverity = Literal["warning", "error"]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: DiagnosticSeverity
    code: str
    message: str
    span: Span
    hint: str | None = None

    def __str__(self) -> str:
        base = (
            f"{self.span.file}:{self.span.line_start}:{self.span.col_start}: "
            f"{self.severity} {self.code}: {self.message}"
        )
        if self.hint:
            return f"{base}\n  hint: {self.hint}"
        return base


@dataclass(frozen=True, slots=True)
class EmittedIndex:
    match_id: str
    path: Path
    case_count: int
    threshold: float
    model: str


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    diagnostics: tuple[Diagnostic, ...] = ()
    indexes: tuple[EmittedIndex, ...] = ()

    @property
    def warnings(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.severity == "warning")

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.severity == "error")

    @property
    def ok(self) -> bool:
        return not self.errors
