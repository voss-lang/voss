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
    BudgetArg,
    Call,
    ClassDecl,
    ConfidenceGate,
    CtxBlock,
    DictLit,
    ExprStmt,
    FloatLit,
    FnDecl,
    Identifier,
    IfStmt,
    IncludeStmt,
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
    TryCatch,
    TypeExpr,
    TypeKwarg,
    TypeRef,
    UnaryOp,
    UseStmt,
    WithinFallback,
    YieldStmt,
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


_MEMORY_CLASSES = {
    "episodic": "EpisodicMemory",
    "semantic": "SemanticMemory",
    "working": "WorkingMemory",
}


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
    current_ctx_name: str | None = None

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
            args = [self.emit_arg(a, await_context=False) for a in expr.agent.args]
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
        if (
            isinstance(call.callee, Identifier)
            and call.callee.name == "ask"
            and self.current_ctx_name is not None
        ):
            arg_texts = [self.emit_arg(a, await_context=await_context) for a in call.args]
            return f"await {self.current_ctx_name}.ask({', '.join(arg_texts)})"

        callee_text = self.emit(call.callee, await_context=await_context)
        arg_texts = [self.emit_arg(a, await_context=await_context) for a in call.args]
        text = f"{callee_text}({', '.join(arg_texts)})"
        if (
            await_context
            and isinstance(call.callee, Identifier)
            and call.callee.name in self.generated_fns
        ):
            text = f"await {text}"
        return text

    def emit_arg(self, arg: Arg, *, await_context: bool) -> str:
        value = self.emit(arg.value, await_context=await_context)
        if arg.name is None:
            return value
        return f"{_mangle(arg.name)}={value}"


def _emit_kwarg_value(value: Node) -> str:
    if isinstance(value, BudgetArg):
        return repr(value.value)
    if isinstance(value, IntLit):
        return repr(value.value)
    if isinstance(value, FloatLit):
        return repr(value.value)
    if isinstance(value, StringLit):
        return repr(value.value)
    if isinstance(value, BoolLit):
        return "True" if value.value else "False"
    if isinstance(value, NullLit):
        return "None"
    if isinstance(value, QualName):
        return ".".join(_mangle(part) for part in value.parts)
    raise CodegenError(
        f"unsupported AST node for codegen: {type(value).__name__}"
    )


class StatementEmitter:
    __slots__ = (
        "writer",
        "expr",
        "type",
        "imports",
        "current_ctx_name",
        "_ctx_depth",
        "_within_count",
    )

    def __init__(
        self,
        writer: PythonWriter,
        expr_emitter: ExpressionEmitter,
        type_emitter: TypeEmitter,
        imports: ImportCollector,
    ) -> None:
        self.writer = writer
        self.expr = expr_emitter
        self.type = type_emitter
        self.imports = imports
        self.current_ctx_name: str | None = None
        self._ctx_depth = 0
        self._within_count = 0

    def emit(self, stmt: Stmt) -> None:
        if isinstance(stmt, ExprStmt):
            self._emit_expr_stmt(stmt)
            return
        if isinstance(stmt, LetStmt):
            self._emit_let(stmt)
            return
        if isinstance(stmt, ReturnStmt):
            self._emit_return(stmt)
            return
        if isinstance(stmt, YieldStmt):
            self._emit_yield(stmt)
            return
        if isinstance(stmt, IncludeStmt):
            self._emit_include(stmt)
            return
        if isinstance(stmt, IfStmt):
            self._emit_if(stmt)
            return
        if isinstance(stmt, FnDecl):
            self._emit_fn(stmt)
            return
        if isinstance(stmt, CtxBlock):
            self._emit_ctx(stmt)
            return
        if isinstance(stmt, WithinFallback):
            self._emit_within(stmt)
            return
        if isinstance(stmt, TryCatch):
            self._emit_try(stmt)
            return
        raise CodegenError(
            f"unsupported AST node for codegen: {type(stmt).__name__}"
        )

    @staticmethod
    def _is_global_ask(expr: Node) -> bool:
        return (
            isinstance(expr, Call)
            and isinstance(expr.callee, Identifier)
            and expr.callee.name == "ask"
        )

    @staticmethod
    def _is_probable_type(t: TypeExpr | None) -> bool:
        return (
            isinstance(t, TypeRef)
            and len(t.name.parts) == 1
            and t.name.parts[0] == "probable"
        )

    @staticmethod
    def _is_memory_type(t: TypeExpr | None) -> bool:
        return (
            isinstance(t, TypeRef)
            and len(t.name.parts) >= 1
            and t.name.parts[0] == "memory"
        )

    def _allocate_ctx_name(self) -> str:
        self._ctx_depth += 1
        return "ctx" if self._ctx_depth == 1 else f"ctx_{self._ctx_depth}"

    def _release_ctx_name(self) -> None:
        self._ctx_depth -= 1

    def _allocate_within_name(self) -> str:
        self._within_count += 1
        return (
            "_within_primary_"
            if self._within_count == 1
            else f"_within_primary_{self._within_count}"
        )

    def _emit_expr_stmt(self, stmt: ExprStmt) -> None:
        if self._is_global_ask(stmt.expr) and self.current_ctx_name is None:
            self._wrap_implicit_ctx(
                lambda: self._write_implicit_ask_call(stmt.expr, prefix="")
            )
            return
        self.writer.write(self.expr.emit(stmt.expr, await_context=True))

    def _emit_let(self, stmt: LetStmt) -> None:
        if self._is_memory_type(stmt.type_annot) and stmt.value is None:
            self._emit_memory_let(stmt)
            return
        if (
            stmt.value is not None
            and self._is_global_ask(stmt.value)
            and self.current_ctx_name is None
        ):
            self._emit_implicit_ctx_let(stmt)
            return

        text = _mangle(stmt.name)
        if stmt.type_annot is not None:
            text += f": {self.type.emit(stmt.type_annot)}"
        if stmt.value is not None:
            text += f" = {self.expr.emit(stmt.value, await_context=True)}"
        self.writer.write(text)

    def _emit_memory_let(self, stmt: LetStmt) -> None:
        type_ref = stmt.type_annot
        assert isinstance(type_ref, TypeRef)
        parts = type_ref.name.parts
        kind = parts[1] if len(parts) > 1 else "working"
        cls = _MEMORY_CLASSES.get(kind)
        if cls is None:
            raise CodegenError(f"unknown memory kind: {kind}")
        self.imports.add_runtime(cls)
        kwargs = [
            f"{_mangle(kw.name)}={_emit_kwarg_value(kw.value)}"
            for kw in type_ref.kwargs
        ]
        self.writer.write(
            f"{_mangle(stmt.name)} = {cls}({', '.join(kwargs)})"
        )

    def _emit_implicit_ctx_let(self, stmt: LetStmt) -> None:
        is_probable = self._is_probable_type(stmt.type_annot)
        if is_probable:
            self.imports.add_runtime("ProbableValue")

        def write_body() -> None:
            ask_call = stmt.value
            assert isinstance(ask_call, Call)
            arg_texts = [
                self.expr.emit_arg(a, await_context=True) for a in ask_call.args
            ]
            if is_probable:
                arg_texts.append("return_type=ProbableValue")
            annot = ""
            if is_probable:
                annot = ": ProbableValue"
            elif stmt.type_annot is not None:
                annot = f": {self.type.emit(stmt.type_annot)}"
            self.writer.write(
                f"{_mangle(stmt.name)}{annot} = await ctx.ask({', '.join(arg_texts)})"
            )

        self._wrap_implicit_ctx(write_body)

    def _emit_return(self, stmt: ReturnStmt) -> None:
        if (
            stmt.value is not None
            and self._is_global_ask(stmt.value)
            and self.current_ctx_name is None
        ):
            def write_body() -> None:
                arg_texts = [
                    self.expr.emit_arg(a, await_context=True)
                    for a in stmt.value.args  # type: ignore[union-attr]
                ]
                self.writer.write(
                    f"return await ctx.ask({', '.join(arg_texts)})"
                )

            self._wrap_implicit_ctx(write_body)
            return

        if stmt.value is None:
            self.writer.write("return")
        else:
            value = self.expr.emit(stmt.value, await_context=True)
            self.writer.write(f"return {value}")

    def _emit_yield(self, stmt: YieldStmt) -> None:
        if self.current_ctx_name is not None:
            if stmt.value is None:
                self.writer.write("return")
            else:
                value = self.expr.emit(stmt.value, await_context=True)
                self.writer.write(f"return {value}")
            return
        if stmt.value is None:
            self.writer.write("yield")
        else:
            value = self.expr.emit(stmt.value, await_context=True)
            self.writer.write(f"yield {value}")

    def _emit_include(self, stmt: IncludeStmt) -> None:
        if self.current_ctx_name is None:
            raise CodegenError("include statement outside ctx block")
        value = self.expr.emit(stmt.value, await_context=False)
        self.writer.write(f"await {self.current_ctx_name}.add({value})")

    def _emit_if(self, stmt: IfStmt) -> None:
        condition = stmt.condition
        if isinstance(condition, ConfidenceGate):
            target = self.expr.emit(condition.target, await_context=True)
            cond_text = f"{target}.confidence {condition.op} {condition.threshold}"
        else:
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

    def _emit_ctx(self, stmt: CtxBlock) -> None:
        self.imports.add_runtime("ContextScope")
        name = self._allocate_ctx_name()
        budget = stmt.budget.value
        budget_text = repr(int(budget) if isinstance(budget, int) or budget == int(budget) else budget)
        self.writer.write(
            f"async with ContextScope(token_budget={budget_text}) as {name}:"
        )
        prev_ctx = self.current_ctx_name
        prev_expr_ctx = self.expr.current_ctx_name
        self.current_ctx_name = name
        self.expr.current_ctx_name = name
        try:
            with self.writer.indent():
                if stmt.body:
                    for inner in stmt.body:
                        self.emit(inner)
                else:
                    self.writer.write("pass")
        finally:
            self.current_ctx_name = prev_ctx
            self.expr.current_ctx_name = prev_expr_ctx
            self._release_ctx_name()

    def _emit_within(self, stmt: WithinFallback) -> None:
        self.imports.add_runtime("BudgetExceededError")
        self.imports.add_runtime("run_with_budget")
        helper_name = self._allocate_within_name()

        self.writer.write(f"async def {helper_name}():")
        with self.writer.indent():
            if stmt.primary:
                for inner in stmt.primary:
                    self.emit(inner)
            else:
                self.writer.write("pass")

        kwargs = self._normalize_within_kwargs(stmt.budget_args)
        kwargs_text = ", ".join(f"{name}={value}" for name, value in kwargs)
        self.writer.write("try:")
        with self.writer.indent():
            call = f"{helper_name}()"
            args_text = f"{call}, {kwargs_text}" if kwargs_text else call
            self.writer.write(f"return await run_with_budget({args_text})")
        self.writer.write("except BudgetExceededError:")
        with self.writer.indent():
            if stmt.fallback:
                for inner in stmt.fallback:
                    self.emit(inner)
            else:
                self.writer.write("pass")

    def _normalize_within_kwargs(
        self, args: tuple[BudgetArg, ...]
    ) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for arg in args:
            unit = arg.unit
            if unit == "tokens":
                result.append(("token_limit", repr(int(arg.value))))
            elif unit == "ms":
                result.append(("latency_ms", repr(int(arg.value))))
            elif unit == "s":
                result.append(("latency_ms", repr(int(arg.value * 1000))))
            elif unit == "usd":
                result.append(("cost_usd", repr(arg.value)))
            else:
                raise CodegenError(
                    f"unsupported within budget unit: {unit!r}"
                )
        return result

    def _emit_try(self, stmt: TryCatch) -> None:
        self.writer.write("try:")
        with self.writer.indent():
            if stmt.try_body:
                for inner in stmt.try_body:
                    self.emit(inner)
            else:
                self.writer.write("pass")
        clause = (
            "except Exception:"
            if stmt.exc_name is None
            else f"except Exception as {_mangle(stmt.exc_name)}:"
        )
        self.writer.write(clause)
        with self.writer.indent():
            if stmt.catch_body:
                for inner in stmt.catch_body:
                    self.emit(inner)
            else:
                self.writer.write("pass")

    def _wrap_implicit_ctx(self, write_body) -> None:
        self.imports.add_runtime("ContextScope")
        name = self._allocate_ctx_name()
        self.writer.write(
            f"async with ContextScope(token_budget=4000) as {name}:"
        )
        prev_ctx = self.current_ctx_name
        prev_expr_ctx = self.expr.current_ctx_name
        self.current_ctx_name = name
        self.expr.current_ctx_name = name
        try:
            with self.writer.indent():
                write_body()
        finally:
            self.current_ctx_name = prev_ctx
            self.expr.current_ctx_name = prev_expr_ctx
            self._release_ctx_name()

    def _write_implicit_ask_call(self, call: Call, *, prefix: str) -> None:
        arg_texts = [self.expr.emit_arg(a, await_context=True) for a in call.args]
        self.writer.write(
            f"{prefix}await ctx.ask({', '.join(arg_texts)})"
        )


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
        stmt_emitter = StatementEmitter(
            body_writer, expr_emitter, type_emitter, self.imports
        )

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
