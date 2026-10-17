"""Benchmark, config and run-record contracts (task.v1, config.v1, run.v1)."""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CmdCheck(_Strict):
    type: Literal["cmd"]
    run: str
    timeout: int = 60


class FileExistsCheck(_Strict):
    type: Literal["file_exists"]
    path: str


class FileContainsCheck(_Strict):
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

Category = Literal[
    "decision", "swarm", "orchestration", "code", "review",
    "memory", "safety", "runtime", "e2e",
]


class Meta(_Strict):
    id: str | None = None
    version: int = 1
    category: Category = "code"
    dataset: Literal["regression", "dev", "locked"] = "regression"
    synthetic: bool
    origin: str
    language: str | None = None


class Acceptance(_Strict):
    criteria: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)


class Budget(_Strict):
    max_turns: int | None = None
    token_budget: int | None = None
    wall_s: float = 600.0


class BenchmarkSpec(_Strict):
    """Superset of `voss.eval.suite.TaskSpec`: a plain voss task.toml validates unchanged."""

    prompt: str
    mode: Literal["plan", "edit", "auto"]
    rubric: str
    judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
    provider: str | None = None
    model: str | None = None
    auto_approve_edits: bool = False
    tools: list[str] = Field(default_factory=list)
    checks: list[AnyCheck] = Field(default_factory=list)
    surface: Literal[
        "internal", "cli:do", "cli:chat", "cli:edit", "serve",
        "sdk:python", "sdk:ts", "sdk:go", "sdk:rust",
    ] = "internal"
    target_file: str | None = None
    permission_choice: Literal["a", "A", "d"] = "a"
    corpus: Literal["pinned"] | None = None
    recall: Literal["off", "shadow", "active"] | None = None

    meta: Meta | None = None
    acceptance: Acceptance = Field(default_factory=Acceptance)
    hidden_checks: list[AnyCheck] = Field(default_factory=list)
    budget: Budget = Field(default_factory=Budget)
    requires: list[str] = Field(default_factory=list)


class Config(_Strict):
    name: str
    adapter: Literal["oracle", "null", "voss-serve"]
    description: str = ""
    live: bool = False
    mode: Literal["plan", "edit", "auto"] | None = None
    auth: str = "auto"
    model: str | None = None
    permission_choice: Literal["a", "A", "d"] | None = None
    voss_bin: str = "voss"
    env: dict[str, str] = Field(default_factory=dict)


BUILTIN_CONFIGS = {
    "oracle": Config(name="oracle", adapter="oracle", description="applies reference.patch"),
    "null": Config(name="null", adapter="null", description="changes nothing"),
}


class CheckResult(_Strict):
    name: str
    kind: Literal["visible", "hidden", "scope"]
    passed: bool
    detail: str = ""
    log: str | None = None


class Usage(_Strict):
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    cost_source: str | None = None


class ConfigRef(_Strict):
    name: str
    adapter: str
    sha256: str


class VossInfo(_Strict):
    version: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class Judge(_Strict):
    verdict: str
    confidence: float | None = None
    model: str | None = None


class RunRecord(_Strict):
    schema_version: Literal["run.v1"] = "run.v1"
    experiment_id: str
    run_id: str
    scenario_id: str
    scenario_version: int = 1
    scenario_sha256: str | None = None
    dataset: str | None = None
    category: str | None = None
    synthetic: bool | None = None
    config: ConfigRef
    voss: VossInfo | None = None
    model: str | None = None
    provider: str | None = None
    live: bool = False
    seed: int = 0
    run_idx: int = 0
    started_at: str
    duration_s: float | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    checks: list[CheckResult] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    exit_reason: str | None = None
    errors: list[str] = Field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None
    claimed_complete: bool | None = None
    verified: bool | None = None
    judge: Judge | None = None
    evaluator_version: str


def load_spec(task_dir: Path) -> BenchmarkSpec:
    return BenchmarkSpec.model_validate(tomllib.loads((task_dir / "task.toml").read_text()))


def scenario_id(task_dir: Path, spec: BenchmarkSpec) -> str:
    return (spec.meta.id if spec.meta and spec.meta.id else None) or task_dir.name


def load_bench(bench: Path) -> list[tuple[Path, BenchmarkSpec]]:
    return [
        (d, load_spec(d))
        for d in sorted(bench.resolve().iterdir())
        if d.is_dir() and (d / "task.toml").exists()
    ]


def load_config(name_or_path: str, configs_dir: Path) -> Config:
    if name_or_path in BUILTIN_CONFIGS:
        return BUILTIN_CONFIGS[name_or_path]
    path = Path(name_or_path)
    if not path.suffix:
        path = configs_dir / f"{name_or_path}.toml"
    return Config.model_validate(tomllib.loads(path.read_text()))


SCHEMAS = {"task.v1": BenchmarkSpec, "config.v1": Config, "run.v1": RunRecord}
