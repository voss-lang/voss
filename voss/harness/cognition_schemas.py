"""Strict pydantic v2 schemas for .voss/*.yml and .voss/project.json (D-07).

Every model uses `model_config = STRICT` so unknown keys are rejected loud.
This is the "fail at REPL boot, not mid-turn" contract from D-07.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

STRICT = {"extra": "forbid"}
McpScope = Literal["plan", "edit", "auto"]


# project.json
class ProjectMeta(BaseModel):
    model_config = STRICT
    name: str
    type: str = "library"
    primary_language: str
    entry_points: list[str] = Field(default_factory=list)


# constraints.yml
class ConstraintRule(BaseModel):
    model_config = STRICT
    forbid: list[str] | None = None
    require_tests_for: list[str] | None = None
    max_file_size_lines: int | None = Field(default=None, gt=0)
    custom: str | None = None


class ConstraintsConfig(BaseModel):
    model_config = STRICT
    rules: list[ConstraintRule] = Field(default_factory=list)


# permissions.yml
class ToolPolicy(BaseModel):
    model_config = STRICT
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)


class PathScope(BaseModel):
    model_config = STRICT
    glob: str
    modes: list[Literal["plan", "edit", "auto"]]


class PermissionsConfig(BaseModel):
    model_config = STRICT
    tool_policy: ToolPolicy = Field(default_factory=ToolPolicy)
    path_scopes: list[PathScope] = Field(default_factory=list)
    mcp: dict[str, McpScope] = Field(default_factory=dict)


# validation.yml
class ValidationCommand(BaseModel):
    model_config = STRICT
    name: str
    run: str
    on: list[Literal["save", "pre_apply", "post_run"]]


class ValidationConfig(BaseModel):
    model_config = STRICT
    commands: list[ValidationCommand] = Field(default_factory=list)
