from __future__ import annotations
from pathlib import Path
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedToken, UnexpectedCharacters, UnexpectedInput, VisitError

from .ast_nodes import (
    Span, Program, ExprStmt, IntLit, FloatLit, StringLit, BoolLit, NullLit,
    Identifier, BudgetArg,
    QualName, TypeKwarg, TypeRef,
    Arg, BinOp, UnaryOp, Call, Member, Index, ListLit, DictLit,
    Param, Lambda, SpawnExpr, ConfidenceGate,
    LetStmt, IfStmt, MatchStmt, MatchCase, SimilarPattern, WildcardPattern, ExprPattern,
    CtxBlock, WithinFallback, TryCatch, ReturnStmt, YieldStmt, IncludeStmt,
)
from .exceptions import VossParseError

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
        # children: [IDENT, let_type|None, let_value|None] with maybe_placeholders=True.
        # let_type and let_value are wrapper rules so optional slots stay positionally
        # distinct (without them, `let x = 42` collapses to [IDENT, expr] and the value
        # masquerades as a type annotation).
        name = str(children[0])
        type_annot = children[1] if len(children) > 1 and children[1] is not None else None
        value = children[2] if len(children) > 2 and children[2] is not None else None
        return LetStmt(span=_span(meta, self.file), name=name, type_annot=type_annot, value=value)

    def let_type(self, meta, children):
        return children[0]

    def let_value(self, meta, children):
        return children[0]

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
        raw = str(children[0])
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
        inner = children[1]   # BudgetArg from budget_literal — name is ""
        return replace(inner, name=name, span=_span(meta, self.file))

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
        line = getattr(exc, "line", 0) or 0
        col = getattr(exc, "column", 0) or 0
        expected = []
        got = "<unknown>"
    try:
        excerpt = exc.get_context(source, span=40)
    except Exception:
        excerpt = ""
    return VossParseError(file=file, line=line, col=col, expected=expected, got=got, hint=None, source_excerpt=excerpt)


def parse(source: str, file: str = "<string>") -> Program:
    """Parse Voss source into a Program AST. Raises VossParseError on any parse failure."""
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
