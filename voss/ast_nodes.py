from __future__ import annotations
from dataclasses import dataclass, field

# Concrete AST nodes are frozen+slotted; sequence fields use tuples (not lists)
# so nodes remain hashable and safe to share across analyzer/codegen passes.

@dataclass(frozen=True, slots=True)
class Span:
    file: str
    line_start: int
    col_start: int
    line_end: int
    col_end: int
    synthetic: bool = False

    @classmethod
    def synthetic_from(cls, parent: "Span | None") -> "Span":
        if parent is None:
            return cls(file="<synthetic>", line_start=-1, col_start=-1, line_end=-1, col_end=-1, synthetic=True)
        return cls(file=parent.file, line_start=-1, col_start=-1, line_end=-1, col_end=-1, synthetic=True)


# Abstract bases — declared as dataclasses so `span` is inherited cleanly.
@dataclass(frozen=True, slots=True)
class Node:
    span: Span

@dataclass(frozen=True, slots=True)
class Expr(Node): ...

@dataclass(frozen=True, slots=True)
class Stmt(Node): ...

@dataclass(frozen=True, slots=True)
class Decl(Stmt): ...

@dataclass(frozen=True, slots=True)
class TypeExpr(Node): ...

@dataclass(frozen=True, slots=True)
class Pattern(Node): ...


# Literal expressions
@dataclass(frozen=True, slots=True)
class IntLit(Expr):
    value: int

@dataclass(frozen=True, slots=True)
class FloatLit(Expr):
    value: float

@dataclass(frozen=True, slots=True)
class StringLit(Expr):
    value: str
    triple: bool = False

@dataclass(frozen=True, slots=True)
class BoolLit(Expr):
    value: bool

@dataclass(frozen=True, slots=True)
class NullLit(Expr):
    pass

@dataclass(frozen=True, slots=True)
class Identifier(Expr):
    name: str


# Unit-suffix budget literal — used by ctx/within and by type kwargs (D-07, D-09).
# Plan 02-03 will consume this when adding ctx/within statements.
@dataclass(frozen=True, slots=True)
class BudgetArg(Node):
    name: str            # the kwarg name in source ("budget", "latency", "cost", "capacity")
    unit: str            # normalized: "tokens" | "ms" | "s" | "usd" | "turns"
    value: int | float
    raw: str             # original text e.g. "4000 tokens"


# Statement wrappers needed by the literal-only program in this plan.
@dataclass(frozen=True, slots=True)
class ExprStmt(Stmt):
    expr: Expr


# Program — top-level AST root for plan 02-01.
@dataclass(frozen=True, slots=True)
class Program(Node):
    body: tuple[Stmt, ...] = field(default_factory=tuple)
