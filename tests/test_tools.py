from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from voss_runtime import ToolDescriptor, tool


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


def test_primitive_args_docstring_and_openai_schema_format():
    @tool
    def search(query: str, max_results: int = 5) -> list[str]:
        """Search the web.

        Extra details are ignored for the tool description.
        """
        return [query] * max_results

    assert isinstance(search, ToolDescriptor)
    schema = search.schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "search"
    assert schema["function"]["description"] == "Search the web."
    params = schema["function"]["parameters"]
    assert params["type"] == "object"
    assert params["required"] == ["query"]
    assert params["properties"]["query"] == {"type": "string"}
    assert params["properties"]["max_results"] == {"type": "integer", "default": 5}


def test_decorated_tool_remains_callable_and_invoke_calls_function():
    @tool(name="add_numbers", description="Add two values")
    def add(a: int, b: int = 1) -> int:
        return a + b

    assert add(2, 3) == 5
    assert add.invoke(a=4, b=5) == 9
    assert add.name == "add_numbers"
    assert add.description == "Add two values"


def test_optional_parameter_is_nullable_and_defaulted():
    @tool
    def maybe_scale(value: Optional[int] = None) -> int:
        """Scale an optional integer."""
        return 0 if value is None else value * 2

    params = maybe_scale.schema()["function"]["parameters"]
    assert params["required"] == []
    assert params["properties"]["value"] == {
        "type": "integer",
        "nullable": True,
        "default": None,
    }


def test_pydantic_basemodel_argument_uses_model_json_schema():
    @tool
    def search(request: SearchRequest) -> str:
        """Run a structured search."""
        return request.query

    request_schema = search.parameters["properties"]["request"]
    assert request_schema["type"] == "object"
    assert request_schema["title"] == "SearchRequest"
    assert request_schema["properties"]["query"]["type"] == "string"
    assert request_schema["properties"]["max_results"]["default"] == 5


def test_list_and_dict_types_generate_json_schema():
    @tool
    def summarize(items: list[str], metadata: dict[str, str]) -> str:
        """Summarize a list."""
        return ",".join(items)

    props = summarize.parameters["properties"]
    assert props["items"] == {"type": "array", "items": {"type": "string"}}
    assert props["metadata"] == {"type": "object"}
