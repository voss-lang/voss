from __future__ import annotations

from voss.ast_nodes import (
    AgentDecl,
    AgentOptions,
    Arg,
    BudgetArg,
    Call,
    ClassDecl,
    ClassField,
    Decorator,
    FnDecl,
    Identifier,
    LetStmt,
    ListLit,
    Param,
    PromptDecl,
    QualName,
    ReturnStmt,
    StringLit,
    TypeRef,
)
from voss.codegen import generate_python

from tests.codegen.conftest import (
    assert_no_compiler_imports,
    assert_python_parses,
    program,
    span,
)


def _ident(name: str) -> Identifier:
    return Identifier(span=span(), name=name)


def _qual(*parts: str) -> QualName:
    return QualName(span=span(), parts=parts)


def _type(*parts: str, generics: tuple[TypeRef, ...] = ()) -> TypeRef:
    return TypeRef(span=span(), name=_qual(*parts), generics=generics)


def _duration(value: int | float, unit: str, raw: str) -> BudgetArg:
    return BudgetArg(span=span(), name="timeout", unit=unit, value=value, raw=raw)


def test_agent_decl_lowers_to_voss_agent_subclass():
    agent = AgentDecl(
        span=span(),
        name="Researcher",
        params=(Param(span=span(), name="topic", type_annot=_type("string")),),
        return_type=_type("string"),
        options=AgentOptions(
            span=span(),
            system=StringLit(span=span(), value="You are a research analyst."),
            tools=ListLit(span=span(), items=(_ident("webSearch"),)),
            model=None,
            retries=None,
            memory=None,
        ),
        body=(ReturnStmt(span=span(), value=StringLit(span=span(), value="ok")),),
    )

    result = generate_python(program(agent))
    source = result.source

    assert "from voss_runtime import VossAgent" in source
    assert "class Researcher(VossAgent):" in source
    assert 'system_prompt = "You are a research analyst."' in source
    assert "tools = (webSearch,)" in source
    assert "async def run(self, topic: str) -> str:" in source
    assert_python_parses(source)
    assert_no_compiler_imports(source)


def test_tool_decorator_emits_runtime_tool_above_async_function():
    fn = FnDecl(
        span=span(),
        name="searchWeb",
        params=(Param(span=span(), name="query", type_annot=_type("string")),),
        return_type=_type("string"),
        body=(ReturnStmt(span=span(), value=StringLit(span=span(), value="result")),),
        decorators=(Decorator(span=span(), name="tool"),),
    )

    result = generate_python(program(fn))
    source = result.source
    lines = source.splitlines()

    assert "from voss_runtime import tool" in source
    tool_line = lines.index("@tool")
    assert lines[tool_line + 1].startswith("async def searchWeb(")
    assert_python_parses(source)
    assert_no_compiler_imports(source)


def test_prompt_declaration_and_inheritance_emit_constants():
    base = PromptDecl(
        span=span(),
        name="BaseAssistant",
        extends=None,
        body=(StringLit(span=span(), value="You are a helpful assistant."),),
    )
    child = PromptDecl(
        span=span(),
        name="SupportAgent",
        extends=_qual("BaseAssistant"),
        body=(StringLit(span=span(), value="Answer with support context."),),
    )

    result = generate_python(program(base, child))
    source = result.source

    assert 'BASE_ASSISTANT_PROMPT = "You are a helpful assistant."' in source
    assert (
        'SUPPORT_AGENT_PROMPT = BASE_ASSISTANT_PROMPT + "\\n" + '
        '"Answer with support context."'
    ) in source
    assert_python_parses(source)
    assert_no_compiler_imports(source)


def test_class_decl_lowers_to_pydantic_base_model():
    model = ClassDecl(
        span=span(),
        name="Report",
        fields=(
            ClassField(span=span(), name="content", type_annot=_type("string")),
            ClassField(span=span(), name="score", type_annot=_type("float")),
        ),
    )

    result = generate_python(program(model))
    source = result.source

    assert "from pydantic import BaseModel" in source
    assert "class Report(BaseModel):" in source
    assert "content: str" in source
    assert "score: float" in source
    assert_python_parses(source)
    assert_no_compiler_imports(source)


def test_gather_call_is_awaited_with_timeout_seconds():
    reports = LetStmt(
        span=span(),
        name="reports",
        type_annot=_type("list", generics=(_type("string"),)),
        value=Call(
            span=span(),
            callee=_ident("gather"),
            args=(
                Arg(span=span(), name=None, value=_ident("researchers")),
                Arg(span=span(), name="timeout", value=_duration(60, "s", "60s")),
            ),
        ),
    )
    fn = FnDecl(
        span=span(),
        name="runResearch",
        params=(Param(span=span(), name="researchers"),),
        return_type=_type("list", generics=(_type("string"),)),
        body=(reports, ReturnStmt(span=span(), value=_ident("reports"))),
    )

    result = generate_python(program(fn))
    source = result.source

    assert "from voss_runtime import gather" in source
    assert "reports: list[str] = await gather(researchers, timeout=60)" in source
    assert_python_parses(source)
    assert_no_compiler_imports(source)


def test_duration_ms_timeout_converts_to_seconds_for_gather():
    reports = LetStmt(
        span=span(),
        name="reports",
        type_annot=_type("list", generics=(_type("string"),)),
        value=Call(
            span=span(),
            callee=_ident("gather"),
            args=(
                Arg(span=span(), name=None, value=_ident("researchers")),
                Arg(span=span(), name="timeout", value=_duration(500, "ms", "500ms")),
            ),
        ),
    )
    fn = FnDecl(
        span=span(),
        name="runResearch",
        params=(Param(span=span(), name="researchers"),),
        return_type=_type("list", generics=(_type("string"),)),
        body=(reports, ReturnStmt(span=span(), value=_ident("reports"))),
    )

    result = generate_python(program(fn))
    source = result.source

    assert "reports: list[str] = await gather(researchers, timeout=0.5)" in source
    assert_python_parses(source)
    assert_no_compiler_imports(source)
