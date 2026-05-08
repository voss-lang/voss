from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from keyword import iskeyword
from pathlib import Path
from typing import Iterator

from .ast_nodes import (
    AgentDecl,
    Arg,
    BinOp,
    BoolLit,
    Call,
    ClassDecl,
    DictLit,
    ExprStmt,
    FloatLit,
    FnDecl,
    Identifier,
    IfStmt,
    Index,
    IntLit,
    Lambda,
    LetStmt,
    ListLit,
    Member,
    NullLit,
    Node,
    Param,
    Program,
    PromptDecl,
    QualName,
    ReturnStmt,
    SpawnExpr,
    Stmt,
    StringLit,
    TypeExpr,
    TypeRef,
    UnaryOp,
    UseStmt,
)
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


_MANGLER = NameMangler()


def _mangle(name: str) -> str:
    return _MANGLER.mangle(name)


class TypeEmitter:
    __slots__ = ("imports",)

    _PRIMITIVES = {
        "string": "str",
        "int": "int",
        "float": "float",
        "bool": "bool",
    }

    def __init__(self, imports: ImportCollector) -> None:
        self.imports = imports

    def emit(self, type_expr: TypeExpr) -> str:
        if not isinstance(type_expr, TypeRef):
            raise CodegenError(
                f"unsupported AST node for codegen: {type(type_expr).__name__}"
            )
        parts = type_expr.name.parts
        last = parts[-1]
        if len(parts) == 1:
            if last in self._PRIMITIVES:
                return self._PRIMITIVES[last]
            if last == "list" and type_expr.generics:
                inner = self.emit(type_expr.generics[0])
                return f"list[{inner}]"
            if last == "dict" and len(type_expr.generics) == 2:
                k = self.emit(type_expr.generics[0])
                v = self.emit(type_expr.generics[1])
                return f"dict[{k}, {v}]"
            if last == "probable":
                self.imports.add_runtime("ProbableValue")
                return "ProbableValue"
        return ".".join(_mangle(part) for part in parts)


@dataclass(slots=True)
class ExpressionEmitter:
    generated_fns: frozenset[str] = field(default_factory=frozenset)

    def emit(self, expr: Node, *, await_context: bool = False) -> str:
        if isinstance(expr, IntLit):
            return repr(expr.value)
        if isinstance(expr, FloatLit):
            return repr(expr.value)
        if isinstance(expr, StringLit):
            return repr(expr.value)
        if isinstance(expr, BoolLit):
            return "True" if expr.value else "False"
        if isinstance(expr, NullLit):
            return "None"
        if isinstance(expr, Identifier):
            return _mangle(expr.name)
        if isinstance(expr, BinOp):
            left = self._emit_operand(expr.left, await_context)
            right = self._emit_operand(expr.right, await_context)
            return f"{left} {expr.op} {right}"
        if isinstance(expr, UnaryOp):
            operand = self._emit_operand(expr.operand, await_context)
            sep = " " if expr.op.isalpha() else ""
            return f"{expr.op}{sep}{operand}"
        if isinstance(expr, Call):
            return self._emit_call(expr, await_context=await_context)
        if isinstance(expr, Member):
            obj = self.emit(expr.obj, await_context=await_context)
            return f"{obj}.{expr.attr}"
        if isinstance(expr, Index):
            obj = self.emit(expr.obj, await_context=await_context)
            idx = self.emit(expr.index, await_context=await_context)
            return f"{obj}[{idx}]"
        if isinstance(expr, ListLit):
            items = [
                self.emit(item, await_context=await_context) for item in expr.items
            ]
            return f"[{', '.join(items)}]"
        if isinstance(expr, DictLit):
            pairs = [
                f"{self.emit(k, await_context=await_context)}: "
                f"{self.emit(v, await_context=await_context)}"
                for k, v in expr.items
            ]
            return f"{{{', '.join(pairs)}}}"
        if isinstance(expr, Lambda):
            params = ", ".join(_mangle(p.name) for p in expr.params)
            body = self.emit(expr.body, await_context=False)
            if params:
                return f"lambda {params}: {body}"
            return f"lambda: {body}"
        if isinstance(expr, SpawnExpr):
            agent_name = self.emit(expr.agent.callee, await_context=False)
            args = [self._emit_arg(a, await_context=False) for a in expr.agent.args]
            return f"{agent_name}().spawn({', '.join(args)})"
        raise CodegenError(
            f"unsupported AST node for codegen: {type(expr).__name__}"
        )

    def _emit_operand(self, expr: Node, await_context: bool) -> str:
        text = self.emit(expr, await_context=await_context)
        if isinstance(expr, (BinOp, UnaryOp)):
            return f"({text})"
        return text

    def _emit_call(self, call: Call, *, await_context: bool) -> str:
        callee_text = self.emit(call.callee, await_context=await_context)
        arg_texts = [self._emit_arg(a, await_context=await_context) for a in call.args]
        text = f"{callee_text}({', '.join(arg_texts)})"
        if (
            await_context
            and isinstance(call.callee, Identifier)
            and call.callee.name in self.generated_fns
        ):
            text = f"await {text}"
        return text

    def _emit_arg(self, arg: Arg, *, await_context: bool) -> str:
        value = self.emit(arg.value, await_context=await_context)
        if arg.name is None:
            return value
        return f"{_mangle(arg.name)}={value}"


class StatementEmitter:
    __slots__ = ("writer", "expr", "type")

    def __init__(
        self,
        writer: PythonWriter,
        expr_emitter: ExpressionEmitter,
        type_emitter: TypeEmitter,
    ) -> None:
        self.writer = writer
        self.expr = expr_emitter
        self.type = type_emitter

    def emit(self, stmt: Stmt) -> None:
        if isinstance(stmt, ExprStmt):
            self.writer.write(self.expr.emit(stmt.expr, await_context=True))
            return
        if isinstance(stmt, LetStmt):
            self._emit_let(stmt)
            return
        if isinstance(stmt, ReturnStmt):
            self._emit_return(stmt)
            return
        if isinstance(stmt, IfStmt):
            self._emit_if(stmt)
            return
        if isinstance(stmt, FnDecl):
            self._emit_fn(stmt)
            return
        raise CodegenError(
            f"unsupported AST node for codegen: {type(stmt).__name__}"
        )

    def _emit_let(self, stmt: LetStmt) -> None:
        text = _mangle(stmt.name)
        if stmt.type_annot is not None:
            text += f": {self.type.emit(stmt.type_annot)}"
        if stmt.value is not None:
            text += f" = {self.expr.emit(stmt.value, await_context=True)}"
        self.writer.write(text)

    def _emit_return(self, stmt: ReturnStmt) -> None:
        if stmt.value is None:
            self.writer.write("return")
            return
        value = self.expr.emit(stmt.value, await_context=True)
        self.writer.write(f"return {value}")

    def _emit_if(self, stmt: IfStmt) -> None:
        condition = stmt.condition
        if not isinstance(condition, (Identifier, BinOp, UnaryOp, Call, Member, Index, BoolLit)):
            raise CodegenError(
                f"unsupported AST node for codegen: {type(condition).__name__}"
            )
        cond_text = self.expr.emit(condition, await_context=True)
        self.writer.write(f"if {cond_text}:")
        with self.writer.indent():
            if stmt.then_body:
                for inner in stmt.then_body:
                    self.emit(inner)
            else:
                self.writer.write("pass")
        if stmt.else_body is not None:
            self.writer.write("else:")
            with self.writer.indent():
                if stmt.else_body:
                    for inner in stmt.else_body:
                        self.emit(inner)
                else:
                    self.writer.write("pass")

    def _emit_fn(self, fn: FnDecl) -> None:
        params = [self._emit_param(p) for p in fn.params]
        sig = f"async def {_mangle(fn.name)}({', '.join(params)})"
        if fn.return_type is not None:
            sig += f" -> {self.type.emit(fn.return_type)}"
        sig += ":"
        self.writer.write(sig)
        with self.writer.indent():
            if fn.body:
                for inner in fn.body:
                    self.emit(inner)
            else:
                self.writer.write("pass")

    def _emit_param(self, param: Param) -> str:
        text = _mangle(param.name)
        if param.type_annot is not None:
            text += f": {self.type.emit(param.type_annot)}"
        if param.default is not None:
            text += f" = {self.expr.emit(param.default, await_context=False)}"
        return text


_DECL_TYPES = (FnDecl, AgentDecl, PromptDecl, ClassDecl)


class ProgramEmitter:
    __slots__ = ("program", "imports")

    def __init__(self, program: Program) -> None:
        self.program = program
        self.imports = ImportCollector()

    def emit(self) -> CodegenResult:
        for stmt in self.program.body:
            if isinstance(stmt, UseStmt):
                self.imports.add_use(stmt.path, alias=stmt.alias)

        fn_names = frozenset(
            stmt.name for stmt in self.program.body if isinstance(stmt, FnDecl)
        )

        decls: list[Stmt] = []
        execs: list[Stmt] = []
        for stmt in self.program.body:
            if isinstance(stmt, UseStmt):
                continue
            if isinstance(stmt, _DECL_TYPES):
                decls.append(stmt)
            else:
                execs.append(stmt)

        requires_async_main = bool(execs)
        if requires_async_main:
            self.imports.add_stdlib("asyncio")

        type_emitter = TypeEmitter(self.imports)
        expr_emitter = ExpressionEmitter(generated_fns=fn_names)
        body_writer = PythonWriter()
        stmt_emitter = StatementEmitter(body_writer, expr_emitter, type_emitter)

        for index, decl in enumerate(decls):
            if index > 0:
                body_writer.blank()
            stmt_emitter.emit(decl)

        if requires_async_main:
            if decls:
                body_writer.blank()
            body_writer.write("async def main():")
            with body_writer.indent():
                if execs:
                    for stmt in execs:
                        stmt_emitter.emit(stmt)
                else:
                    body_writer.write("pass")
            body_writer.blank()
            body_writer.write('if __name__ == "__main__":')
            with body_writer.indent():
                body_writer.write("asyncio.run(main())")

        import_lines, import_meta = self.imports.render()

        final = PythonWriter()
        for line in import_lines:
            final.write(line)
        if import_lines and body_writer.lines:
            final.blank()
        final.lines.extend(body_writer.lines)

        source = final.render()
        if source.strip() == "":
            source = "\n"

        return CodegenResult(
            source=source,
            imports=import_meta,
            requires_async_main=requires_async_main,
        )


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

    emitter = ProgramEmitter(program)
    result = emitter.emit()
    return CodegenResult(
        source=result.source,
        imports=result.imports,
        requires_async_main=result.requires_async_main,
        analysis=analysis,
    )
