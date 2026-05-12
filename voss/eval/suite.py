"""Task suite loader + TaskSpec schema (M5 D-05, D-07)."""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
