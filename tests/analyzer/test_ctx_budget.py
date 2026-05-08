from __future__ import annotations

from voss import analyze
from voss.ast_nodes import (
    Arg,
    BudgetArg,
    Call,
    CtxBlock,
    Identifier,
    IncludeStmt,
    LetStmt,
    StringLit,
    YieldStmt,
)

from tests.analyzer.conftest import program, span


def positional(value) -> Arg:
    return Arg(span=span(), name=None, value=value)


def ask_call(prompt: str, line: int = 1) -> Call:
    return Call(
        span=span(line=line),
        callee=Identifier(span=span(line=line), name="ask"),
        args=(positional(StringLit(span=span(line=line), value=prompt)),),
    )


def token_budget(value: int, line: int = 1) -> BudgetArg:
    return BudgetArg(
        span=span(line=line),
        name="budget",
        unit="tokens",
        value=value,
        raw=f"{value} tokens",
    )


def test_ctx_literal_prompt_over_budget_warns():
    long_prompt = "this prompt is definitely longer than two tokens"
    ctx = CtxBlock(
        span=span(line=5, col=1),
        budget=token_budget(2, line=5),
        body=(YieldStmt(span=span(line=6), value=ask_call(long_prompt, line=6)),),
    )
    result = analyze(program(ctx), emit_indexes=False)
    warns = [d for d in result.diagnostics if d.code == "ANLY002"]
    assert len(warns) == 1
    msg = warns[0].message
    assert "ctx block static token estimate" in msg
    assert "exceeds declared budget 2" in msg
    assert warns[0].span.line_start == ctx.span.line_start


def test_ctx_literal_prompt_under_budget_is_clean():
    ctx = CtxBlock(
        span=span(line=5),
        budget=token_budget(100, line=5),
        body=(YieldStmt(span=span(line=6), value=ask_call("short", line=6)),),
    )
    result = analyze(program(ctx), emit_indexes=False)
    assert [d for d in result.diagnostics if d.code == "ANLY002"] == []


def test_include_known_string_binding_contributes_to_estimate():
    long_text = "x" * 200  # ~50 tokens by len//4
    let_stmt = LetStmt(
        span=span(line=1),
        name="context",
        type_annot=None,
        value=StringLit(span=span(line=1), value=long_text),
    )
    ctx = CtxBlock(
        span=span(line=2),
        budget=token_budget(5, line=2),
        body=(IncludeStmt(span=span(line=3), value=Identifier(span=span(line=3), name="context")),),
    )
    result = analyze(program(let_stmt, ctx), emit_indexes=False)
    warns = [d for d in result.diagnostics if d.code == "ANLY002"]
    assert len(warns) == 1
    assert "exceeds declared budget 5" in warns[0].message


def test_unknown_call_result_does_not_warn():
    let_stmt = LetStmt(
        span=span(line=1),
        name="context",
        type_annot=None,
        value=Call(
            span=span(line=1),
            callee=Identifier(span=span(line=1), name="loadDynamic"),
            args=(),
        ),
    )
    ctx = CtxBlock(
        span=span(line=2),
        budget=token_budget(1, line=2),
        body=(IncludeStmt(span=span(line=3), value=Identifier(span=span(line=3), name="context")),),
    )
    result = analyze(program(let_stmt, ctx), emit_indexes=False)
    assert [d for d in result.diagnostics if d.code == "ANLY002"] == []


def test_non_token_ctx_budget_is_ignored():
    long_prompt = "this prompt is definitely longer than two tokens"
    latency_budget = BudgetArg(
        span=span(line=5),
        name="latency",
        unit="ms",
        value=500,
        raw="500ms",
    )
    ctx = CtxBlock(
        span=span(line=5),
        budget=latency_budget,
        body=(YieldStmt(span=span(line=6), value=ask_call(long_prompt, line=6)),),
    )
    result = analyze(program(ctx), emit_indexes=False)
    assert [d for d in result.diagnostics if d.code == "ANLY002"] == []
