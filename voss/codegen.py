from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from keyword import iskeyword
from pathlib import Path
from typing import Iterator

from .ast_nodes import Program, UseStmt
from .diagnostics import AnalysisResult


@dataclass(frozen=True, slots=True)
class CodegenResult:
    source: str
    imports: tuple[str, ...]
    requires_async_main: bool
    analysis: AnalysisResult | None = None


class CodegenError(Exception):
    pass


class PythonWriter:
    __slots__ = ("lines", "indent_level")

    def __init__(self) -> None:
        self.lines: list[str] = []
        self.indent_level: int = 0

    def write(self, line: str = "") -> None:
        if line == "":
            self._append_blank()
            return
        self.lines.append("    " * self.indent_level + line)

    def blank(self) -> None:
        self._append_blank()

    def _append_blank(self) -> None:
        if self.lines and self.lines[-1] == "":
            return
        self.lines.append("")

    @contextmanager
    def indent(self) -> Iterator[None]:
        self.indent_level += 1
        try:
            yield
        finally:
            self.indent_level -= 1

    def render(self) -> str:
        lines = list(self.lines)
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines) + "\n"


@dataclass(slots=True)
class ImportCollector:
    stdlib: set[str] = field(default_factory=set)
    runtime: set[str] = field(default_factory=set)
    pydantic_base_model: bool = False
    user_imports: list[tuple[tuple[str, ...], str | None]] = field(default_factory=list)

    def add_stdlib(self, name: str) -> None:
        self.stdlib.add(name)

    def add_runtime(self, name: str) -> None:
        self.runtime.add(name)

    def add_base_model(self) -> None:
        self.pydantic_base_model = True

    def add_use(self, path: tuple[str, ...], alias: str | None = None) -> None:
        if len(path) < 2:
            raise CodegenError(f"use path must have at least two segments, got {path!r}")
        entry = (tuple(path), alias)
        if entry not in self.user_imports:
            self.user_imports.append(entry)

    def render(self) -> tuple[list[str], tuple[str, ...]]:
        groups: list[list[str]] = []

        if self.stdlib:
            groups.append([f"import {name}" for name in sorted(self.stdlib)])

        third_party: list[str] = []
        if self.pydantic_base_model:
            third_party.append("from pydantic import BaseModel")
        for path, alias in self.user_imports:
            module = ".".join(path[:-1])
            name = path[-1]
            line = f"from {module} import {name}"
            if alias is not None:
                line += f" as {alias}"
            third_party.append(line)
        if third_party:
            groups.append(third_party)

        if self.runtime:
            names = ", ".join(sorted(self.runtime))
            groups.append([f"from voss_runtime import {names}"])

        lines: list[str] = []
        for index, group in enumerate(groups):
            if index > 0:
                lines.append("")
            lines.extend(group)

        meta = tuple(line for line in lines if line)
        return lines, meta


class NameMangler:
    __slots__ = ()

    def mangle(self, name: str) -> str:
        if iskeyword(name):
            return name + "_"
        return name


def generate_python(
    program: Program,
    *,
    source_path: str | Path | None = None,
    analysis: AnalysisResult | None = None,
    cache_dir: str | Path = ".voss-cache",
) -> CodegenResult:
    if analysis is None:
        from .analyzer import analyze

        analysis = analyze(program, source_path=source_path, cache_dir=cache_dir)

    if not analysis.ok:
        raise CodegenError("semantic analysis failed; refusing to generate Python")

    imports = ImportCollector()
    writer = PythonWriter()

    for stmt in program.body:
        if isinstance(stmt, UseStmt):
            imports.add_use(stmt.path, alias=stmt.alias)

    import_lines, import_meta = imports.render()
    for line in import_lines:
        writer.write(line)

    if import_lines:
        writer.blank()

    source = writer.render()
    if source.strip() == "":
        source = "\n"

    return CodegenResult(
        source=source,
        imports=import_meta,
        requires_async_main=False,
        analysis=analysis,
    )
