from __future__ import annotations

import inspect
import types
import typing
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

_PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _type_to_schema(t: Any) -> dict[str, Any]:
    origin = typing.get_origin(t)
    args = typing.get_args(t)

    if t in _PY_TO_JSON:
        return {"type": _PY_TO_JSON[t]}
    if origin in (list, typing.List):
        inner = args[0] if args else str
        return {"type": "array", "items": _type_to_schema(inner)}
    if origin in (dict, typing.Dict):
        return {"type": "object"}
    if inspect.isclass(t) and issubclass(t, BaseModel):
        return t.model_json_schema()
    if origin in (typing.Union, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            schema = _type_to_schema(non_none[0])
            schema["nullable"] = True
            return schema
    return {"type": "string"}


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., Any]

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def invoke(self, **kwargs: Any) -> Any:
        return self.func(**kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


def tool(
    func: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
):
    """Decorate a function as a model-callable tool with generated JSON schema."""

    def wrap(f: Callable[..., Any]) -> ToolDescriptor:
        sig = inspect.signature(f)
        hints = typing.get_type_hints(f)
        doc = (f.__doc__ or "").strip()
        first_line = doc.splitlines()[0] if doc else ""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for pname, param in sig.parameters.items():
            ann = hints.get(pname, str)
            schema = _type_to_schema(ann)
            if param.default is inspect._empty:
                required.append(pname)
            else:
                schema["default"] = param.default
            properties[pname] = schema

        params_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }
        return ToolDescriptor(
            name=name or f.__name__,
            description=description or first_line or f.__name__,
            parameters=params_schema,
            func=f,
        )

    return wrap(func) if func is not None else wrap
