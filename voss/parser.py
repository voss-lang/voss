from __future__ import annotations
from pathlib import Path
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedToken, UnexpectedCharacters, UnexpectedInput

from .ast_nodes import (
    Span, Program, ExprStmt, IntLit, FloatLit, StringLit, BoolLit, NullLit,
    Identifier, BudgetArg,
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
    "IDENT": "an identifier",
    "STRING": "a string literal",
    "INT": "an integer",
    "FLOAT": "a float",
}

def _humanize(name: str) -> str:
    return _HUMANIZE.get(name, name)


def _build_parser() -> Lark:
    return Lark(
        _GRAMMAR_PATH.read_text(),
        parser="earley",
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
        return StringLit(span=_span(meta, self.file), value=bytes(raw[1:-1], "utf-8").decode("unicode_escape"), triple=False)

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

    # --- expr / expr_stmt / program ---
    def expr(self, meta, children):
        c = children[0]
        # An IDENT token (not a literal subtree) becomes Identifier.
        if hasattr(c, "type") and c.type == "IDENT":
            return Identifier(span=_span(meta, self.file), name=str(c))
        return c

    def budget_literal(self, meta, children):
        tok = children[0]
        unit, value, raw = _parse_unit_token(tok)
        return BudgetArg(span=_span(meta, self.file), name="", unit=unit, value=value, raw=raw)

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
    return transformer.transform(tree)
