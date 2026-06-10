"""Task suite loader + TaskSpec schema (M5 D-05, D-07)."""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag


class CmdCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["cmd"]
    run: str
    timeout: int = 60


class FileExistsCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["file_exists"]
    path: str


class FileContainsCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["file_contains"]
    path: str
    text: str


AnyCheck = Annotated[
    Union[
        Annotated[CmdCheck, Tag("cmd")],
        Annotated[FileExistsCheck, Tag("file_exists")],
        Annotated[FileContainsCheck, Tag("file_contains")],
    ],
    Discriminator("type"),
]


class TaskSpec(BaseModel):
    """Validated `task.toml` row. Mirrors M1 D-07 mode tiers + D-08 rubric shape."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(description="Prompt passed to `voss do`.")
    mode: Literal["plan", "edit", "auto"]
    rubric: str = Field(description="Plain-text PASS/FAIL criteria (D-08).")
    judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
    provider: str | None = None
    model: str | None = None
    auto_approve_edits: bool = False
    tools: list[str] = Field(default_factory=list)
    checks: list[AnyCheck] = Field(default_factory=list)
    surface: Literal["internal", "cli:do", "cli:chat", "cli:edit", "serve"] = "internal"
    target_file: str | None = None  # required by cli:edit driver; None for all other surfaces
    permission_choice: Literal["a", "A", "d"] = "a"  # serve-only; default Allow; "d" = Deny


def load_task(task_dir: Path) -> TaskSpec:
    data = tomllib.loads((task_dir / "task.toml").read_text())
    return TaskSpec.model_validate(data)


def load_suite(suite_root: Path, suite: str = "golden") -> list[tuple[str, TaskSpec]]:
    """Return [(task_id, spec), ...] sorted by task_id. task_id = directory basename."""
    suite_dir = suite_root if suite_root.name == suite or suite == "" else suite_root / suite
    tasks: list[tuple[str, TaskSpec]] = []
    for task_dir in sorted(suite_dir.iterdir()):
        if not task_dir.is_dir() or not (task_dir / "task.toml").exists():
            continue
        tasks.append((task_dir.name, load_task(task_dir)))
    return tasks
