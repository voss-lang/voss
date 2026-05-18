from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import replace as _dc_replace
from pathlib import Path
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedToken, UnexpectedCharacters, UnexpectedInput, VisitError

from .ast_nodes import (
    Span, Stmt, Program, ExprStmt, IntLit, FloatLit, StringLit, BoolLit, NullLit,
    Identifier, BudgetArg,
    QualName, TypeKwarg, TypeRef,
    Arg, BinOp, UnaryOp, Call, Member, Index, ListLit, DictLit,
    Param, Lambda, SpawnExpr, ConfidenceGate,
    LetStmt, IfStmt, MatchStmt, MatchCase, SimilarPattern, WildcardPattern, ExprPattern,
    CtxBlock, WithinFallback, TryCatch, ReturnStmt, YieldStmt, IncludeStmt,
    FnDecl, AgentDecl, AgentOptions, PromptDecl, ClassDecl, ClassField, UseStmt, Decorator,
)
from .exceptions import VossParseError


def _parse_haskell_subprocess(source: str, file: str) -> Program:
    exe = os.environ.get("VOSS_FRONTEND_HS_EXE") or shutil.which("voss-frontend-hs")
    if not exe:
        raise VossParseError(
            file=file,
            line=1,
            col=1,
            expected=["voss-frontend-hs on PATH or VOSS_FRONTEND_HS_EXE"],
            got="VOSS_FRONTEND=haskell but executable not found",
        )
    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix="voss_hs_", suffix=".voss", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(source)
        proc = subprocess.run(
            [exe, "ast", "--path", tmp_path, "--normalize-spans"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    finally:
        if tmp_path is not None:
            Path(tmp_path).unlink(missing_ok=True)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise VossParseError(
            file=file,
            line=1,
            col=1,
            expected=["successful voss-frontend-hs ast"],
            got=msg[:500],
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise VossParseError(
            file=file,
            line=1,
            col=1,
            expected=["JSON from voss-frontend-hs"],
            got=str(exc),
        ) from exc
    from .ast_deserializer import program_from_dict

    if not isinstance(data, dict):
        raise VossParseError(
            file=file,
            line=1,
            col=1,
            expected=["AST JSON object"],
            got=type(data).__name__,
        )
    try:
        return program_from_dict(data)
    except ValueError as exc:
        raise VossParseError(
            file=file,
            line=1,
            col=1,
            expected=["deserializable AST"],
            got=str(exc),
        ) from exc


_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"

# Token-name humanization (D-13). Extended in later plans as new terminals appear.
_HUMANIZE = {
    "LBRACE": "'{'", "RBRACE": "'}'",
    "LPAREN": "'('", "RPAREN": "')'",
    "TOKEN_BUDGET": "a token budget like 4000 tokens",
    "TURNS": "a turn count like 20 turns",
    "DURATION_MS": "a millisecond duration like 500ms",
    "DURATION_S": "a second duration like 30s",
    "COST_USD": "a USD cost like $0.02",
    "NEWLINE": "end of line",
    "_NL": "end of line",
    "IDENT": "an identifier",
    "STRING": "a string literal",
    "INT": "an integer",
    "FLOAT": "a float",
    "EQ": "'=='",
    "NE": "'!='",
    "LE": "'<='",
    "GE": "'>='",
    "LT": "'<'",
    "GT": "'>'",
    "PLUS": "'+'",
    "MINUS": "'-'",
    "STAR": "'*'",
    "SLASH": "'/'",
}

def _humanize(name: str) -> str:
    return _HUMANIZE.get(name, name)


def _build_parser() -> Lark:
    return Lark(
        _GRAMMAR_PATH.read_text(),
        parser="earley",
        # Lark 1.x rejects lexer="contextual" with Earley; dynamic is the supported
        # state-aware Earley lexer (accepted: basic/dynamic/dynamic_complete).
        lexer="dynamic",
        propagate_positions=True,
        maybe_placeholders=True,
    )

_PARSER = _build_parser()


def _span(meta, file: str) -> Span:
    return Span(
        file=file,
        line_start=meta.line, col_start=meta.column,
        line_end=meta.end_line, col_end=meta.end_column,
    )


def _binop_chain(file: str, meta, children):
    if len(children) == 1:
        return children[0]
    node = children[0]
    i = 1
    while i < len(children):
        op = str(children[i])
        right = children[i + 1]
        node = BinOp(span=_span(meta, file), op=op, left=node, right=right)
        i += 2
    return node


def _left_assoc(file: str, meta, children, op: str):
    if len(children) == 1:
        return children[0]
    node = children[0]
    for right in children[1:]:
        node = BinOp(span=_span(meta, file), op=op, left=node, right=right)
    return node


def _parse_unit_token(tok: str) -> tuple[str, int | float, str]:
    """Decompose a unit-suffix token's text. Returns (unit, numeric_value, raw)."""
    raw = str(tok)
    s = raw.strip()
    if s.startswith("$"):
        return ("usd", float(s[1:]), raw)
    if s.endswith("ms"):
        return ("ms", int(s[:-2]), raw)
    if s.endswith("s") and not s.endswith("tokens") and not s.endswith("turns"):
        return ("s", int(s[:-1]), raw)
    # whitespace-separated: "4000 tokens" / "20 turns"
    num, unit = s.split(None, 1)
    return (unit, int(num), raw)


_SIMPLE_STRING_ESCAPES = {
    '"': '"',
    "'": "'",
    "\\": "\\",
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
}
_HEX_DIGITS = set("0123456789abcdefABCDEF")
_OCTAL_DIGITS = set("01234567")


def _decode_string_literal(raw: str) -> str:
    """Decode Voss string escapes without re-encoding Unicode source text."""
    inner = raw[1:-1]
    decoded: list[str] = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch != "\\":
            decoded.append(ch)
            i += 1
            continue

        if i + 1 >= len(inner):
            decoded.append("\\")
            i += 1
            continue

        esc = inner[i + 1]
        if esc in _SIMPLE_STRING_ESCAPES:
            decoded.append(_SIMPLE_STRING_ESCAPES[esc])
            i += 2
            continue

        if esc in _OCTAL_DIGITS:
            end = i + 2
            while end < min(i + 4, len(inner)) and inner[end] in _OCTAL_DIGITS:
                end += 1
            decoded.append(chr(int(inner[i + 1:end], 8)))
            i = end
            continue

        hex_width = {"x": 2, "u": 4, "U": 8}.get(esc)
        if hex_width is not None:
            start = i + 2
            end = start + hex_width
            digits = inner[start:end]
            if len(digits) == hex_width and all(c in _HEX_DIGITS for c in digits):
                try:
                    decoded.append(chr(int(digits, 16)))
                    i = end
                    continue
                except (OverflowError, ValueError):
                    pass

        # Preserve unknown escapes rather than dropping the backslash.
        decoded.append("\\" + esc)
        i += 2

    return "".join(decoded)


@v_args(meta=True)
class _Transformer(Transformer):
    def __init__(self, file: str):
        super().__init__()
        self.file = file

    # --- literals ---
    def int_lit(self, meta, children):
        return IntLit(span=_span(meta, self.file), value=int(children[0]))

    def float_lit(self, meta, children):
        return FloatLit(span=_span(meta, self.file), value=float(children[0]))

    def string_lit(self, meta, children):
        raw = str(children[0])
        return StringLit(span=_span(meta, self.file), value=_decode_string_literal(raw), triple=False)

    def triple_string_lit(self, meta, children):
        raw = str(children[0])
        return StringLit(span=_span(meta, self.file), value=raw[3:-3], triple=True)

    def true_lit(self, meta, children):
        return BoolLit(span=_span(meta, self.file), value=True)

    def false_lit(self, meta, children):
        return BoolLit(span=_span(meta, self.file), value=False)

    def null_lit(self, meta, children):
        return NullLit(span=_span(meta, self.file))

    def literal(self, meta, children):
        return children[0]

    def budget_literal(self, meta, children):
        tok = children[0]
        unit, value, raw = _parse_unit_token(tok)
        return BudgetArg(span=_span(meta, self.file), name="", unit=unit, value=value, raw=raw)

    # --- type_expr family ---
    def qual_name(self, meta, children):
        parts = tuple(str(t) for t in children)
        return QualName(span=_span(meta, self.file), parts=parts)

    def type_generics(self, meta, children):
        # LT/GT are named tokens because they are also comparison operators;
        # only nested TypeRef children are part of the AST generics tuple.
        return tuple(c for c in children if isinstance(c, TypeRef))

    def type_kwargs(self, meta, children):
        return tuple(c for c in children if c is not None)

    def type_kwarg(self, meta, children):
        name = str(children[0])
        return TypeKwarg(span=_span(meta, self.file), name=name, value=children[1])

    def type_arg_value(self, meta, children):
        return children[0]

    def type_expr(self, meta, children):
        name = children[0]
        generics = ()
        kwargs = ()
        for c in (child for child in children[1:] if child is not None):
            if isinstance(c, tuple) and c and isinstance(c[0], TypeRef):
                generics = c
            elif isinstance(c, tuple) and c and isinstance(c[0], TypeKwarg):
                kwargs = c
            elif isinstance(c, tuple) and len(c) == 0:
                pass
        return TypeRef(span=_span(meta, self.file), name=name, generics=generics, kwargs=kwargs)

    # --- expression ladder ---
    def expr(self, meta, children):
        return children[0]

    def or_expr(self, meta, children):
        return _left_assoc(self.file, meta, children, op="or")

    def and_expr(self, meta, children):
        return _left_assoc(self.file, meta, children, op="and")

    def not_expr(self, meta, children):
        return children[0]

    def not_op(self, meta, children):
        return UnaryOp(span=_span(meta, self.file), op="not", operand=children[0])

    def comparison(self, meta, children):
        if len(children) == 1:
            return children[0]
        node = children[0]
        i = 1
        while i < len(children):
            op = str(children[i])
            right = children[i + 1]
            node = BinOp(span=_span(meta, self.file), op=op, left=node, right=right)
            i += 2
        return node

    def cmp_op(self, meta, children):
        return str(children[0])

    def additive(self, meta, children):
        return _binop_chain(self.file, meta, children)

    def add_op(self, meta, children):
        return str(children[0])

    def multiplicative(self, meta, children):
        return _binop_chain(self.file, meta, children)

    def mul_op(self, meta, children):
        return str(children[0])

    def unary(self, meta, children):
        return children[0]

    def neg_op(self, meta, children):
        # MINUS is a named token for binary operators, so the operand is the last child.
        return UnaryOp(span=_span(meta, self.file), op="-", operand=children[-1])

    def postfix(self, meta, children):
        node = children[0]
        for suf in children[1:]:
            kind, payload = suf
            if kind == "call":
                node = Call(span=_span(meta, self.file), callee=node, args=payload)
            elif kind == "member":
                node = Member(span=_span(meta, self.file), obj=node, attr=payload)
            elif kind == "index":
                node = Index(span=_span(meta, self.file), obj=node, index=payload)
        return node

    def call_suf(self, meta, children):
        present = [c for c in children if c is not None]
        args = present[0] if present else ()
        if not isinstance(args, tuple):
            args = tuple(args)
        return ("call", args)

    def member_suf(self, meta, children):
        return ("member", str(children[0]))

    def index_suf(self, meta, children):
        return ("index", children[0])

    def arg_list(self, meta, children):
        return tuple(c for c in children if c is not None)

    def named_arg(self, meta, children):
        return Arg(span=_span(meta, self.file), name=str(children[0]), value=children[1])

    def arg(self, meta, children):
        c = children[0]
        if isinstance(c, Arg):
            return c
        return Arg(span=_span(meta, self.file), name=None, value=c)

    def list_lit(self, meta, children):
        return ListLit(span=_span(meta, self.file), items=tuple(c for c in children if c is not None))

    def dict_lit(self, meta, children):
        return DictLit(span=_span(meta, self.file), items=tuple(c for c in children if c is not None))

    def kv(self, meta, children):
        return (children[0], children[1])

    def dict_key(self, meta, children):
        c = children[0]
        if hasattr(c, "type") and c.type == "STRING":
            return StringLit(span=_span(meta, self.file), value=_decode_string_literal(str(c)), triple=False)
        return Identifier(span=_span(meta, self.file), name=str(c))

    def ident_primary(self, meta, children):
        return Identifier(span=_span(meta, self.file), name=str(children[0]))

    def paren_primary(self, meta, children):
        return children[0]

    def primary(self, meta, children):
        return children[0]

    def lambda_single(self, meta, children):
        name_tok, body = children
        p = Param(span=_span(meta, self.file), name=str(name_tok), type_annot=None, default=None)
        return Lambda(span=_span(meta, self.file), params=(p,), body=body)

    def lambda_multi(self, meta, children):
        present = [c for c in children if c is not None]
        body = present[-1]
        params = present[0] if len(present) > 1 and isinstance(present[0], tuple) else ()
        return Lambda(span=_span(meta, self.file), params=tuple(params), body=body)

    def lambda_param_list(self, meta, children):
        return tuple(c for c in children if c is not None)

    def lambda_param(self, meta, children):
        name = str(children[0])
        type_annot = children[1] if len(children) > 1 else None
        return Param(span=_span(meta, self.file), name=name, type_annot=type_annot, default=None)

    def spawn_expr(self, meta, children):
        target = children[0]
        if not isinstance(target, Call):
            if isinstance(target, Identifier):
                # The plan requires SpawnExpr.agent to be a Call while also listing
                # `t => spawn x` as a valid shape. Normalize only a bare identifier
                # into a zero-argument call; other non-call targets remain errors.
                target = Call(span=_span(meta, self.file), callee=target, args=())
            else:
                raise VossParseError(
                    file=self.file,
                    line=meta.line,
                    col=meta.column,
                    expected=["a function or agent call"],
                    got=type(target).__name__,
                )
        return SpawnExpr(span=_span(meta, self.file), agent=target)

    def call_target(self, meta, children):
        return children[0]

    def confidence_gate(self, meta, children):
        target, op, threshold_node = children[0], str(children[1]), children[2]
        threshold = float(threshold_node.value if hasattr(threshold_node, "value") else threshold_node)
        return ConfidenceGate(span=_span(meta, self.file), target=target, op=op, threshold=threshold)

    def number_literal(self, meta, children):
        c = children[0]
        if hasattr(c, "type") and c.type == "FLOAT":
            return FloatLit(span=_span(meta, self.file), value=float(c))
        return IntLit(span=_span(meta, self.file), value=int(c))

    # --- statements + patterns ---
    def stmt(self, meta, children):
        return children[0]

    def let_stmt(self, meta, children):
        # children: [IDENT, let_type?, let_value?]. Lark drops missing optional rule
        # slots rather than filling them with None, so we tag the optional pieces and
        # demux by tag instead of by position.
        name = str(children[0])
        type_annot = None
        value = None
        for c in children[1:]:
            if isinstance(c, tuple) and len(c) == 2 and c[0] == "let_type":
                type_annot = c[1]
            elif isinstance(c, tuple) and len(c) == 2 and c[0] == "let_value":
                value = c[1]
        return LetStmt(span=_span(meta, self.file), name=name, type_annot=type_annot, value=value)

    def let_type(self, meta, children):
        return ("let_type", children[0])

    def let_value(self, meta, children):
        return ("let_value", children[0])

    def if_condition(self, meta, children):
        return children[0]

    def if_stmt(self, meta, children):
        # children: [if_condition, block(then), block(else)|None]
        cond = children[0]
        then_body = children[1]
        else_body = children[2] if len(children) > 2 and children[2] is not None else None
        return IfStmt(
            span=_span(meta, self.file),
            condition=cond,
            then_body=tuple(then_body),
            else_body=tuple(else_body) if else_body is not None else None,
        )

    def block(self, meta, children):
        # _NL is underscore-prefixed in the grammar so Lark filters newlines automatically;
        # still defensively drop NEWLINE tokens in case any leak through.
        return tuple(c for c in children if not (hasattr(c, "type") and c.type == "NEWLINE"))

    def match_stmt(self, meta, children):
        scrutinee = children[0]
        cases = tuple(c for c in children[1:] if isinstance(c, MatchCase))
        return MatchStmt(span=_span(meta, self.file), scrutinee=scrutinee, cases=cases, threshold=None)

    def match_case(self, meta, children):
        pattern, body = children[0], children[1]
        if isinstance(body, tuple):
            body_tuple = body
        else:
            body_tuple = (ExprStmt(span=_span(meta, self.file), expr=body),)
        return MatchCase(span=_span(meta, self.file), pattern=pattern, body=body_tuple)

    def match_case_body(self, meta, children):
        # Returns either a tuple (block) or a bare Expr; match_case wraps the bare Expr.
        return children[0]

    def pattern(self, meta, children):
        return children[0]

    def similar_pattern(self, meta, children):
        # children may include the SIMILAR keyword token (now a named terminal);
        # the STRING token is the only one whose tokenized text begins with `"`.
        for c in children:
            if hasattr(c, "type") and c.type == "STRING":
                raw = str(c)
                break
        else:
            raw = str(children[-1])
        return SimilarPattern(span=_span(meta, self.file), text=_decode_string_literal(raw))

    def wildcard_pattern(self, meta, children):
        return WildcardPattern(span=_span(meta, self.file))

    def expr_pattern(self, meta, children):
        return ExprPattern(span=_span(meta, self.file), expr=children[0])

    def match_threshold_stmt(self, meta, children):
        # children: [number_literal, MatchStmt]
        from dataclasses import replace
        threshold_node = children[0]
        match_stmt = children[1]
        threshold = float(threshold_node.value)
        return replace(match_stmt, threshold=threshold)

    def ctx_stmt(self, meta, children):
        budget = children[0]   # budget_kwarg → BudgetArg
        body = children[1]     # block → tuple
        return CtxBlock(span=_span(meta, self.file), budget=budget, body=tuple(body))

    def within_stmt(self, meta, children):
        budget_args = []
        blocks = []
        for c in children:
            if isinstance(c, BudgetArg):
                budget_args.append(c)
            elif isinstance(c, tuple):
                blocks.append(c)
        primary = tuple(blocks[0]) if blocks else ()
        fallback = tuple(blocks[1]) if len(blocks) > 1 else None
        return WithinFallback(
            span=_span(meta, self.file),
            budget_args=tuple(budget_args),
            primary=primary,
            fallback=fallback,
        )

    def budget_kwarg(self, meta, children):
        from dataclasses import replace
        name = str(children[0])
        inner = children[1]   # BudgetArg (from budget_literal) OR (IntLit|FloatLit) (bare number)
        if isinstance(inner, BudgetArg):
            return replace(inner, name=name, span=_span(meta, self.file))
        # Bare number like `tokens: 4000` inside `within budget(...)`. The unit is implied
        # by the kwarg name itself, so reuse `name` as the unit and the raw text.
        value = inner.value
        return BudgetArg(
            span=_span(meta, self.file),
            name=name,
            unit=name,
            value=value,
            raw=str(value),
        )

    def budget_kwarg_value(self, meta, children):
        return children[0]

    def try_stmt(self, meta, children):
        # children: [block(try), IDENT|None, block(catch)] (maybe_placeholders=True)
        try_body = children[0]
        if len(children) == 3:
            exc_name_tok = children[1]
            exc_name = str(exc_name_tok) if exc_name_tok is not None else None
            catch_body = children[2]
        else:
            exc_name = None
            catch_body = children[1]
        return TryCatch(
            span=_span(meta, self.file),
            try_body=tuple(try_body),
            exc_name=exc_name,
            catch_body=tuple(catch_body),
        )

    def return_stmt(self, meta, children):
        value = children[0] if children and children[0] is not None else None
        return ReturnStmt(span=_span(meta, self.file), value=value)

    def yield_stmt(self, meta, children):
        value = children[0] if children and children[0] is not None else None
        return YieldStmt(span=_span(meta, self.file), value=value)

    def include_stmt(self, meta, children):
        return IncludeStmt(span=_span(meta, self.file), value=children[0])

    # --- expr_stmt / program ---
    def expr_stmt(self, meta, children):
        return ExprStmt(span=_span(meta, self.file), expr=children[0])

    # --- declarations (plan 02-04) ---
    def param_list(self, meta, children):
        return tuple(c for c in children if isinstance(c, Param))

    def param(self, meta, children):
        name = str(children[0])
        type_annot = None
        default = None
        rest = list(children[1:])
        if rest and isinstance(rest[0], TypeRef):
            type_annot = rest.pop(0)
        if rest:
            default = rest[0]
        return Param(span=_span(meta, self.file), name=name, type_annot=type_annot, default=default)

    def fn_decl(self, meta, children):
        # children: [IDENT, params?, return_type?, block]
        name = str(children[0])
        params: tuple[Param, ...] = ()
        return_type = None
        body: tuple = ()
        for c in children[1:]:
            if isinstance(c, tuple) and c and isinstance(c[0], Param):
                params = c
            elif isinstance(c, TypeRef):
                return_type = c
            elif isinstance(c, tuple):
                body = c
        return FnDecl(
            span=_span(meta, self.file),
            name=name,
            params=tuple(params),
            return_type=return_type,
            body=tuple(body),
            decorators=(),
        )

    def agent_option(self, meta, children):
        key = str(children[0])
        value = children[1]
        return (key, value)

    def agent_body(self, meta, children):
        options = AgentOptions(span=_span(meta, self.file))
        body_stmts: list = []
        for c in children:
            if hasattr(c, "type") and c.type == "NEWLINE":
                continue
            if (
                isinstance(c, tuple)
                and len(c) == 2
                and isinstance(c[0], str)
                and c[0] in ("system", "tools", "model", "retries", "memory")
            ):
                key, value = c
                options = _dc_replace(options, **{key: value})
            elif isinstance(c, Stmt):
                body_stmts.append(c)
        return (options, tuple(body_stmts))

    def agent_decl(self, meta, children):
        name = str(children[0])
        params: tuple[Param, ...] = ()
        return_type = None
        options = AgentOptions(span=_span(meta, self.file))
        body: tuple = ()
        for c in children[1:]:
            if isinstance(c, tuple) and c and isinstance(c[0], Param):
                params = c
            elif isinstance(c, TypeRef):
                return_type = c
            elif isinstance(c, tuple) and len(c) == 2 and isinstance(c[0], AgentOptions):
                options, body = c
        return AgentDecl(
            span=_span(meta, self.file),
            name=name,
            params=tuple(params),
            return_type=return_type,
            options=options,
            body=tuple(body),
            decorators=(),
        )

    def prompt_string(self, meta, children):
        raw = str(children[0])
        if raw.startswith('"""'):
            return StringLit(span=_span(meta, self.file), value=raw[3:-3], triple=True)
        return StringLit(
            span=_span(meta, self.file),
            value=_decode_string_literal(raw),
            triple=False,
        )

    def prompt_body(self, meta, children):
        return tuple(c for c in children if isinstance(c, StringLit))

    def prompt_decl(self, meta, children):
        name = str(children[0])
        extends = None
        body: tuple = ()
        for c in children[1:]:
            if isinstance(c, QualName):
                extends = c
            elif isinstance(c, tuple):
                body = c
        return PromptDecl(
            span=_span(meta, self.file),
            name=name,
            extends=extends,
            body=body,
            decorators=(),
        )

    def class_field(self, meta, children):
        name = str(children[0])
        type_annot = children[1]
        default = children[2] if len(children) > 2 and children[2] is not None else None
        return ClassField(
            span=_span(meta, self.file),
            name=name,
            type_annot=type_annot,
            default=default,
        )

    def class_body(self, meta, children):
        return tuple(c for c in children if isinstance(c, ClassField))

    def class_decl(self, meta, children):
        name = str(children[0])
        fields = children[1] if len(children) > 1 else ()
        return ClassDecl(
            span=_span(meta, self.file),
            name=name,
            fields=tuple(fields),
            decorators=(),
        )

    def use_path(self, meta, children):
        return tuple(str(t) for t in children)

    def use_stmt(self, meta, children):
        path = children[0]
        alias = None
        if len(children) > 1 and children[1] is not None:
            alias = str(children[1])
        return UseStmt(span=_span(meta, self.file), path=path, alias=alias)

    def decorator(self, meta, children):
        name = str(children[0])
        args: tuple = ()
        if len(children) > 1 and children[1] is not None:
            args = children[1]
        return Decorator(span=_span(meta, self.file), name=name, args=tuple(args))

    def decorator_args(self, meta, children):
        return tuple(c for c in children if isinstance(c, Arg))

    def decl_target(self, meta, children):
        return children[0]

    def decorated_decl(self, meta, children):
        *decorators, target = children
        decorators = tuple(d for d in decorators if isinstance(d, Decorator))
        if hasattr(target, "decorators"):
            return _dc_replace(target, decorators=decorators)
        return target

    def top_decl(self, meta, children):
        return children[0]

    def top_stmt(self, meta, children):
        return children[0]

    def program(self, meta, children):
        body = tuple(c for c in children if not _is_newline(c))
        return Program(span=_span(meta, self.file), body=body)

    def start(self, meta, children):
        return children[0]


def _is_newline(c) -> bool:
    return hasattr(c, "type") and c.type == "NEWLINE"


def _wrap_lark_error(exc: UnexpectedInput, source: str, file: str) -> VossParseError:
    if isinstance(exc, UnexpectedToken):
        line, col = exc.line, exc.column
        expected = sorted(_humanize(name) for name in (exc.expected or set()))
        got = f"{exc.token!r}"
    elif isinstance(exc, UnexpectedCharacters):
        line, col = exc.line, exc.column
        expected = sorted(_humanize(name) for name in (exc.allowed or set()))
        got = f"character {exc.char!r}"
    else:
        # Includes UnexpectedEOF: Lark reports line/col == -1 there. Fall back to
        # the end of the source so callers always see a 1-indexed location.
        raw_line = getattr(exc, "line", 0) or 0
        raw_col = getattr(exc, "column", 0) or 0
        if raw_line < 1 or raw_col < 1:
            trimmed = source[:-1] if source.endswith("\n") else source
            raw_line = trimmed.count("\n") + 1
            last_nl = trimmed.rfind("\n")
            raw_col = len(trimmed) - last_nl  # 1-indexed (col after last newline)
            if raw_col < 1:
                raw_col = 1
        line, col = raw_line, raw_col
        expected_names = getattr(exc, "expected", None) or []
        expected = sorted({_humanize(name) for name in expected_names})
        got = "end of input"
    try:
        excerpt = exc.get_context(source, span=40)
    except Exception:
        excerpt = ""
    return VossParseError(file=file, line=line, col=col, expected=expected, got=got, hint=None, source_excerpt=excerpt)


def parse(source: str, file: str = "<string>") -> Program:
    """Parse Voss source into a Program AST. Raises VossParseError on any parse failure."""
    if os.environ.get("VOSS_FRONTEND", "python").lower() == "haskell":
        return _parse_haskell_subprocess(source, file)
    try:
        tree = _PARSER.parse(source)
    except UnexpectedInput as exc:
        raise _wrap_lark_error(exc, source, file) from exc
    transformer = _Transformer(file)
    try:
        return transformer.transform(tree)
    except VisitError as exc:
        if isinstance(exc.orig_exc, VossParseError):
            raise exc.orig_exc from None
        raise
