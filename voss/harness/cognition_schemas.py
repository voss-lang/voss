"""Strict pydantic v2 schemas for .voss/*.yml and .voss/project.json (D-07).

Every model uses `model_config = STRICT` so unknown keys are rejected loud.
This is the "fail at REPL boot, not mid-turn" contract from D-07.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

STRICT = {"extra": "forbid"}
McpScope = Literal["plan", "edit", "auto"]
# V12 dangerous-operation classes (VSAFE-02).
SafetyClass = Literal[
    "irreversible", "deploy", "delete", "migration", "money", "prod"
]


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
    # H5.1: OpenCode-style wildcard rule map. Either a per-tool decision
    # (`"bash": "ask"`) or per-command sub-map (`"bash": {"*": "ask",
    # "git status *": "allow"}`). Values are "allow" | "ask" | "deny".
    # Last-match-wins within a sub-map (put "*" first). Empty by default →
    # existing tool_policy.deny behaviour is unchanged.
    rules: dict[str, Any] = Field(default_factory=dict)


# safety.yml (V12 — VSAFE-02/03/04/06)
# Strict project-local safety policy. Separate from permissions.yml: this file
# routes dangerous/factory-only operations through named runbooks/pipelines or
# scaffolded procedures — it does NOT change allow/ask/deny semantics.
class SafetyRunbook(BaseModel):
    model_config = STRICT
    name: str
    description: str = ""
    steps: list[str] = Field(default_factory=list)


class SafetyPipeline(BaseModel):
    model_config = STRICT
    name: str
    description: str = ""
    steps: list[str] = Field(default_factory=list)


class SafetyPathRule(BaseModel):
    """Factory-only path glob → named runbook (VSAFE-06)."""
    model_config = STRICT
    id: str | None = None
    glob: str
    runbook: str
    classes: list[SafetyClass] = Field(default_factory=list)


class SafetyOperationRule(BaseModel):
    """Factory-only command/operation pattern → named runbook (VSAFE-02)."""
    model_config = STRICT
    id: str | None = None
    tool: str | None = None  # optional tool-name filter (e.g. "shell_run")
    pattern: str  # fnmatch over the command/op text (e.g. "git push *")
    runbook: str
    classes: list[SafetyClass] = Field(default_factory=list)


class SafetyLatencyRule(BaseModel):
    """Latency-critical operation → fixed pipeline (VSAFE-03)."""
    model_config = STRICT
    id: str | None = None
    tool: str | None = None
    pattern: str
    pipeline: str


class SafetyScaffoldRule(BaseModel):
    """Force weak/cheap/fast model roles onto a scaffolded procedure (VSAFE-04)."""
    model_config = STRICT
    id: str | None = None
    roles: list[str] = Field(default_factory=list)
    model_tiers: list[str] = Field(default_factory=list)  # e.g. ["cheap", "fast"]
    pattern: str = "*"
    runbook: str | None = None


class SafetyConfig(BaseModel):
    model_config = STRICT
    runbooks: list[SafetyRunbook] = Field(default_factory=list)
    pipelines: list[SafetyPipeline] = Field(default_factory=list)
    factory_only_paths: list[SafetyPathRule] = Field(default_factory=list)
    factory_only_operations: list[SafetyOperationRule] = Field(default_factory=list)
    latency_pipelines: list[SafetyLatencyRule] = Field(default_factory=list)
    weak_model_scaffolds: list[SafetyScaffoldRule] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_references(self) -> "SafetyConfig":
        """Fail closed (T-V12-01): rules must reference declared runbooks/pipelines."""
        runbooks = {r.name for r in self.runbooks}
        pipelines = {p.name for p in self.pipelines}
        for i, rule in enumerate(self.factory_only_paths):
            if rule.runbook not in runbooks:
                raise ValueError(
                    f"factory_only_paths[{i}] references unknown runbook "
                    f"'{rule.runbook}'"
                )
        for i, rule in enumerate(self.factory_only_operations):
            if rule.runbook not in runbooks:
                raise ValueError(
                    f"factory_only_operations[{i}] references unknown runbook "
                    f"'{rule.runbook}'"
                )
        for i, rule in enumerate(self.latency_pipelines):
            if rule.pipeline not in pipelines:
                raise ValueError(
                    f"latency_pipelines[{i}] references unknown pipeline "
                    f"'{rule.pipeline}'"
                )
        for i, rule in enumerate(self.weak_model_scaffolds):
            if rule.runbook is not None and rule.runbook not in runbooks:
                raise ValueError(
                    f"weak_model_scaffolds[{i}] references unknown runbook "
                    f"'{rule.runbook}'"
                )
        return self


# validation.yml
class ValidationCommand(BaseModel):
    model_config = STRICT
    name: str
    run: str
    on: list[Literal["save", "pre_apply", "post_run"]]


class ValidationConfig(BaseModel):
    model_config = STRICT
    commands: list[ValidationCommand] = Field(default_factory=list)
