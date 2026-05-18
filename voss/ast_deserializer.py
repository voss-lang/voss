"""Reconstruct `ast_nodes` trees from `ast_serializer.to_dict` JSON."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from . import ast_nodes as A

U = TypeVar("U")


def _opt(conv: Callable[[Any], U], x: Any) -> U | None:
    if x is None:
        return None
    return conv(x)


def _span(d: dict[str, Any]) -> A.Span:
    lines = d["lines"]
    cols = d["cols"]
    return A.Span(
        file=d["file"],
        line_start=int(lines[0]),
        col_start=int(cols[0]),
        line_end=int(lines[1]),
        col_end=int(cols[1]),
        synthetic=bool(d.get("synthetic", False)),
    )


def _node(d: Any) -> A.Node:
    if not isinstance(d, dict):
        raise ValueError(f"expected AST object dict, got {type(d).__name__}")
    if "lines" in d and "cols" in d and "file" in d and "_node" not in d:
        raise ValueError("Span not valid as Node; use _span only inside node payloads")
    tag = d.get("_node")
    if not tag or not isinstance(tag, str):
        raise ValueError(f"missing or invalid _node in {d!r}")
    builder = _BUILDERS.get(tag)
    if builder is None:
        raise ValueError(f"unknown AST node type: {tag!r}")
    return builder(d)


def _expr(d: Any) -> A.Expr:
    n = _node(d)
    if not isinstance(n, A.Expr):
        raise ValueError(f"expected Expr, got {type(n).__name__}")
    return n


def _stmt(d: Any) -> A.Stmt:
    n = _node(d)
    if not isinstance(n, A.Stmt):
        raise ValueError(f"expected Stmt, got {type(n).__name__}")
    return n


def _decl(d: Any) -> A.Decl:
    n = _node(d)
    if not isinstance(n, A.Decl):
        raise ValueError(f"expected Decl, got {type(n).__name__}")
    return n


def _type_expr(d: Any) -> A.TypeExpr:
    n = _node(d)
    if not isinstance(n, A.TypeExpr):
        raise ValueError(f"expected TypeExpr, got {type(n).__name__}")
    return n


def _pattern(d: Any) -> A.Pattern:
    n = _node(d)
    if not isinstance(n, A.Pattern):
        raise ValueError(f"expected Pattern, got {type(n).__name__}")
    return n


def _gate_or_expr(d: Any) -> A.Expr | A.ConfidenceGate:
    n = _node(d)
    if isinstance(n, (A.Expr, A.ConfidenceGate)):
        return n
    raise ValueError(f"expected Expr or ConfidenceGate, got {type(n).__name__}")


def _type_kwarg_value(d: Any) -> A.Node:
    n = _node(d)
    if not isinstance(n, (A.Expr, A.BudgetArg, A.QualName, A.TypeExpr)):
        # literals and BudgetArg/QualName are Node subclasses
        pass
    if isinstance(
        n,
        (
            A.IntLit,
            A.FloatLit,
            A.StringLit,
            A.BoolLit,
            A.NullLit,
            A.BudgetArg,
            A.QualName,
        ),
    ):
        return n
    raise ValueError(f"invalid type kwarg value node: {type(n).__name__}")


def _stmts(arr: Any) -> tuple[A.Stmt, ...]:
    if not isinstance(arr, list):
        raise ValueError(f"expected stmt list, got {type(arr).__name__}")
    return tuple(_stmt(x) for x in arr)


def _exprs(arr: Any) -> tuple[A.Expr, ...]:
    if not isinstance(arr, list):
        raise ValueError(f"expected expr list, got {type(arr).__name__}")
    return tuple(_expr(x) for x in arr)


def _params(arr: Any) -> tuple[A.Param, ...]:
    if not isinstance(arr, list):
        raise ValueError(f"expected param list, got {type(arr).__name__}")
    return tuple(_node(x) for x in arr)  # type: ignore[return-value]


def _args(arr: Any) -> tuple[A.Arg, ...]:
    if not isinstance(arr, list):
        raise ValueError(f"expected arg list, got {type(arr).__name__}")
    return tuple(_node(x) for x in arr)  # type: ignore[return-value]


def _decorators(arr: Any) -> tuple[A.Decorator, ...]:
    if not isinstance(arr, list):
        raise ValueError(f"expected decorators list, got {type(arr).__name__}")
    return tuple(_node(x) for x in arr)  # type: ignore[return-value]


def _match_cases(arr: Any) -> tuple[A.MatchCase, ...]:
    if not isinstance(arr, list):
        raise ValueError(f"expected match cases list, got {type(arr).__name__}")
    return tuple(_node(x) for x in arr)  # type: ignore[return-value]


def _type_exprs(arr: Any) -> tuple[A.TypeExpr, ...]:
    if not isinstance(arr, list):
        return ()
    return tuple(_type_expr(x) for x in arr)


def _type_kwargs(arr: Any) -> tuple[A.TypeKwarg, ...]:
    if not isinstance(arr, list):
        return ()
    return tuple(_node(x) for x in arr)  # type: ignore[return-value]


def _dict_items(arr: Any) -> tuple[tuple[A.Expr, A.Expr], ...]:
    if not isinstance(arr, list):
        raise ValueError(f"expected dict items list, got {type(arr).__name__}")
    out: list[tuple[A.Expr, A.Expr]] = []
    for pair in arr:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f"dict item must be [k,v], got {pair!r}")
        out.append((_expr(pair[0]), _expr(pair[1])))
    return tuple(out)


def _build_program(d: dict[str, Any]) -> A.Program:
    return A.Program(span=_span(d["span"]), body=_stmts(d["body"]))


def _build_int_lit(d: dict[str, Any]) -> A.IntLit:
    return A.IntLit(span=_span(d["span"]), value=int(d["value"]))


def _build_float_lit(d: dict[str, Any]) -> A.FloatLit:
    return A.FloatLit(span=_span(d["span"]), value=float(d["value"]))


def _build_string_lit(d: dict[str, Any]) -> A.StringLit:
    return A.StringLit(
        span=_span(d["span"]),
        value=str(d["value"]),
        triple=bool(d.get("triple", False)),
    )


def _build_bool_lit(d: dict[str, Any]) -> A.BoolLit:
    return A.BoolLit(span=_span(d["span"]), value=bool(d["value"]))


def _build_null_lit(d: dict[str, Any]) -> A.NullLit:
    return A.NullLit(span=_span(d["span"]))


def _build_identifier(d: dict[str, Any]) -> A.Identifier:
    return A.Identifier(span=_span(d["span"]), name=str(d["name"]))


def _build_budget_arg(d: dict[str, Any]) -> A.BudgetArg:
    return A.BudgetArg(
        span=_span(d["span"]),
        name=str(d["name"]),
        unit=str(d["unit"]),
        value=d["value"],
        raw=str(d["raw"]),
    )


def _build_expr_stmt(d: dict[str, Any]) -> A.ExprStmt:
    return A.ExprStmt(span=_span(d["span"]), expr=_expr(d["expr"]))


def _qual_name_node(d: Any) -> A.QualName:
    n = _node(d)
    if not isinstance(n, A.QualName):
        raise ValueError(f"expected QualName, got {type(n).__name__}")
    return n


def _build_qual_name(d: dict[str, Any]) -> A.QualName:
    return A.QualName(
        span=_span(d["span"]),
        parts=tuple(str(x) for x in d["parts"]),
    )


def _build_type_kwarg(d: dict[str, Any]) -> A.TypeKwarg:
    return A.TypeKwarg(
        span=_span(d["span"]),
        name=str(d["name"]),
        value=_type_kwarg_value(d["value"]),
    )


def _build_type_ref(d: dict[str, Any]) -> A.TypeRef:
    return A.TypeRef(
        span=_span(d["span"]),
        name=_qual_name_node(d["name"]),
        generics=_type_exprs(d.get("generics", ())),
        kwargs=_type_kwargs(d.get("kwargs", ())),
    )


def _build_arg(d: dict[str, Any]) -> A.Arg:
    return A.Arg(
        span=_span(d["span"]),
        name=d["name"] if d.get("name") is not None else None,
        value=_expr(d["value"]),
    )


def _build_bin_op(d: dict[str, Any]) -> A.BinOp:
    return A.BinOp(
        span=_span(d["span"]),
        op=str(d["op"]),
        left=_expr(d["left"]),
        right=_expr(d["right"]),
    )


def _build_unary_op(d: dict[str, Any]) -> A.UnaryOp:
    return A.UnaryOp(
        span=_span(d["span"]),
        op=str(d["op"]),
        operand=_expr(d["operand"]),
    )


def _build_call(d: dict[str, Any]) -> A.Call:
    return A.Call(
        span=_span(d["span"]),
        callee=_expr(d["callee"]),
        args=_args(d.get("args", ())),
    )


def _build_member(d: dict[str, Any]) -> A.Member:
    return A.Member(
        span=_span(d["span"]),
        obj=_expr(d["obj"]),
        attr=str(d["attr"]),
    )


def _build_index(d: dict[str, Any]) -> A.Index:
    return A.Index(
        span=_span(d["span"]),
        obj=_expr(d["obj"]),
        index=_expr(d["index"]),
    )


def _build_list_lit(d: dict[str, Any]) -> A.ListLit:
    return A.ListLit(span=_span(d["span"]), items=_exprs(d.get("items", ())))


def _build_dict_lit(d: dict[str, Any]) -> A.DictLit:
    return A.DictLit(span=_span(d["span"]), items=_dict_items(d.get("items", ())))


def _build_param(d: dict[str, Any]) -> A.Param:
    return A.Param(
        span=_span(d["span"]),
        name=str(d["name"]),
        type_annot=_opt(_type_expr, d.get("type_annot")),
        default=_opt(_expr, d.get("default")),
    )


def _build_lambda(d: dict[str, Any]) -> A.Lambda:
    return A.Lambda(
        span=_span(d["span"]),
        params=_params(d["params"]),
        body=_expr(d["body"]),
    )


def _build_spawn_expr(d: dict[str, Any]) -> A.SpawnExpr:
    agent = _node(d["agent"])
    if not isinstance(agent, A.Call):
        raise ValueError("SpawnExpr.agent must be Call")
    return A.SpawnExpr(span=_span(d["span"]), agent=agent)


def _build_confidence_gate(d: dict[str, Any]) -> A.ConfidenceGate:
    return A.ConfidenceGate(
        span=_span(d["span"]),
        target=_expr(d["target"]),
        op=str(d["op"]),
        threshold=float(d["threshold"]),
    )


def _build_similar_pattern(d: dict[str, Any]) -> A.SimilarPattern:
    return A.SimilarPattern(span=_span(d["span"]), text=str(d["text"]))


def _build_wildcard_pattern(d: dict[str, Any]) -> A.WildcardPattern:
    return A.WildcardPattern(span=_span(d["span"]))


def _build_expr_pattern(d: dict[str, Any]) -> A.ExprPattern:
    return A.ExprPattern(span=_span(d["span"]), expr=_expr(d["expr"]))


def _build_let_stmt(d: dict[str, Any]) -> A.LetStmt:
    return A.LetStmt(
        span=_span(d["span"]),
        name=str(d["name"]),
        type_annot=_opt(_type_expr, d.get("type_annot")),
        value=_opt(_expr, d.get("value")),
    )


def _build_if_stmt(d: dict[str, Any]) -> A.IfStmt:
    eb = d.get("else_body")
    return A.IfStmt(
        span=_span(d["span"]),
        condition=_gate_or_expr(d["condition"]),
        then_body=_stmts(d["then_body"]),
        else_body=_stmts(eb) if isinstance(eb, list) else None,
    )


def _build_match_case(d: dict[str, Any]) -> A.MatchCase:
    return A.MatchCase(
        span=_span(d["span"]),
        pattern=_pattern(d["pattern"]),
        body=_stmts(d["body"]),
    )


def _build_match_stmt(d: dict[str, Any]) -> A.MatchStmt:
    thr = d.get("threshold")
    return A.MatchStmt(
        span=_span(d["span"]),
        scrutinee=_expr(d["scrutinee"]),
        cases=_match_cases(d["cases"]),
        threshold=float(thr) if thr is not None else None,
    )


def _build_ctx_block(d: dict[str, Any]) -> A.CtxBlock:
    return A.CtxBlock(
        span=_span(d["span"]),
        budget=_node(d["budget"]),  # type: ignore[arg-type]
        body=_stmts(d["body"]),
    )


def _build_within_fallback(d: dict[str, Any]) -> A.WithinFallback:
    fb = d.get("fallback")
    return A.WithinFallback(
        span=_span(d["span"]),
        budget_args=tuple(_node(x) for x in d["budget_args"]),  # type: ignore[arg-type]
        primary=_stmts(d["primary"]),
        fallback=_stmts(fb) if isinstance(fb, list) else None,
    )


def _build_try_catch(d: dict[str, Any]) -> A.TryCatch:
    en = d.get("exc_name")
    return A.TryCatch(
        span=_span(d["span"]),
        try_body=_stmts(d["try_body"]),
        exc_name=str(en) if en is not None else None,
        catch_body=_stmts(d["catch_body"]),
    )


def _build_return_stmt(d: dict[str, Any]) -> A.ReturnStmt:
    v = d.get("value")
    return A.ReturnStmt(
        span=_span(d["span"]),
        value=_expr(v) if v is not None else None,
    )


def _build_yield_stmt(d: dict[str, Any]) -> A.YieldStmt:
    v = d.get("value")
    return A.YieldStmt(
        span=_span(d["span"]),
        value=_expr(v) if v is not None else None,
    )


def _build_include_stmt(d: dict[str, Any]) -> A.IncludeStmt:
    return A.IncludeStmt(span=_span(d["span"]), value=_expr(d["value"]))


def _build_decorator(d: dict[str, Any]) -> A.Decorator:
    return A.Decorator(
        span=_span(d["span"]),
        name=str(d["name"]),
        args=_args(d.get("args", ())),
    )


def _build_fn_decl(d: dict[str, Any]) -> A.FnDecl:
    return A.FnDecl(
        span=_span(d["span"]),
        name=str(d["name"]),
        params=_params(d["params"]),
        return_type=_opt(_type_expr, d.get("return_type")),
        body=_stmts(d["body"]),
        decorators=_decorators(d.get("decorators", ())),
    )


def _list_lit_node(d: Any) -> A.ListLit:
    n = _node(d)
    if not isinstance(n, A.ListLit):
        raise ValueError(f"AgentOptions.tools must be ListLit, got {type(n).__name__}")
    return n


def _build_agent_options(d: dict[str, Any]) -> A.AgentOptions:
    return A.AgentOptions(
        span=_span(d["span"]),
        system=_opt(_expr, d.get("system")),
        tools=_opt(_list_lit_node, d.get("tools")),
        model=_opt(_expr, d.get("model")),
        retries=_opt(_expr, d.get("retries")),
        memory=_opt(_expr, d.get("memory")),
    )


def _build_agent_decl(d: dict[str, Any]) -> A.AgentDecl:
    opts = d["options"]
    return A.AgentDecl(
        span=_span(d["span"]),
        name=str(d["name"]),
        params=_params(d["params"]),
        return_type=_opt(_type_expr, d.get("return_type")),
        options=_node(opts),  # type: ignore[arg-type]
        body=_stmts(d["body"]),
        decorators=_decorators(d.get("decorators", ())),
    )


def _prompt_body_string(d: Any) -> A.StringLit:
    n = _node(d)
    if not isinstance(n, A.StringLit):
        raise ValueError(f"prompt body expects StringLit, got {type(n).__name__}")
    return n


def _build_prompt_decl(d: dict[str, Any]) -> A.PromptDecl:
    body_raw = d["body"]
    body: tuple[A.StringLit, ...] = tuple(_prompt_body_string(x) for x in body_raw)
    return A.PromptDecl(
        span=_span(d["span"]),
        name=str(d["name"]),
        extends=_opt(_qual_name_node, d.get("extends")),
        body=body,
        decorators=_decorators(d.get("decorators", ())),
    )


def _build_class_field(d: dict[str, Any]) -> A.ClassField:
    df = d.get("default")
    return A.ClassField(
        span=_span(d["span"]),
        name=str(d["name"]),
        type_annot=_type_expr(d["type_annot"]),
        default=_expr(df) if df is not None else None,
    )


def _build_class_decl(d: dict[str, Any]) -> A.ClassDecl:
    return A.ClassDecl(
        span=_span(d["span"]),
        name=str(d["name"]),
        fields=tuple(_node(x) for x in d["fields"]),  # type: ignore[arg-type]
        decorators=_decorators(d.get("decorators", ())),
    )


def _build_use_stmt(d: dict[str, Any]) -> A.UseStmt:
    al = d.get("alias")
    return A.UseStmt(
        span=_span(d["span"]),
        path=tuple(str(x) for x in d["path"]),
        alias=str(al) if al is not None else None,
    )


_BUILDERS: dict[str, Callable[[dict[str, Any]], A.Node]] = {
    "Program": _build_program,
    "IntLit": _build_int_lit,
    "FloatLit": _build_float_lit,
    "StringLit": _build_string_lit,
    "BoolLit": _build_bool_lit,
    "NullLit": _build_null_lit,
    "Identifier": _build_identifier,
    "BudgetArg": _build_budget_arg,
    "ExprStmt": _build_expr_stmt,
    "QualName": _build_qual_name,
    "TypeKwarg": _build_type_kwarg,
    "TypeRef": _build_type_ref,
    "Arg": _build_arg,
    "BinOp": _build_bin_op,
    "UnaryOp": _build_unary_op,
    "Call": _build_call,
    "Member": _build_member,
    "Index": _build_index,
    "ListLit": _build_list_lit,
    "DictLit": _build_dict_lit,
    "Param": _build_param,
    "Lambda": _build_lambda,
    "SpawnExpr": _build_spawn_expr,
    "ConfidenceGate": _build_confidence_gate,
    "SimilarPattern": _build_similar_pattern,
    "WildcardPattern": _build_wildcard_pattern,
    "ExprPattern": _build_expr_pattern,
    "LetStmt": _build_let_stmt,
    "IfStmt": _build_if_stmt,
    "MatchCase": _build_match_case,
    "MatchStmt": _build_match_stmt,
    "CtxBlock": _build_ctx_block,
    "WithinFallback": _build_within_fallback,
    "TryCatch": _build_try_catch,
    "ReturnStmt": _build_return_stmt,
    "YieldStmt": _build_yield_stmt,
    "IncludeStmt": _build_include_stmt,
    "Decorator": _build_decorator,
    "FnDecl": _build_fn_decl,
    "AgentOptions": _build_agent_options,
    "AgentDecl": _build_agent_decl,
    "PromptDecl": _build_prompt_decl,
    "ClassField": _build_class_field,
    "ClassDecl": _build_class_decl,
    "UseStmt": _build_use_stmt,
}


def program_from_dict(data: dict[str, Any]) -> A.Program:
    """Deserialize the root `Program` object from `to_dict(program)` JSON."""
    n = _node(data)
    if not isinstance(n, A.Program):
        raise ValueError(f"root must be Program, got {type(n).__name__}")
    return n
