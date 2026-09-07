"""Observe enrollment (device settings) and `.voss/observe.yml` repo policy.

Enrollment lives at `<app-state>/observe/enrollment.json` and is
device-controlled. The repository file may only narrow the defaults: smaller
capture/investigation limits, additional exclude paths, a command allowlist.
It can never enable observation or widen a limit.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from voss.harness.observe.store import observe_dir


class RepoEnrollment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    capture: bool = True
    analysis: bool = False
    provider: str | None = None
    disclosure: bool = False
    budget_usd: float | None = None
    paused: bool = False


class EnrollmentFile(BaseModel):
    repositories: dict[str, RepoEnrollment] = Field(default_factory=dict)


def enrollment_path(state_dir: Path | None = None) -> Path:
    return observe_dir(state_dir) / "enrollment.json"


def load_enrollment(state_dir: Path | None = None) -> EnrollmentFile:
    path = enrollment_path(state_dir)
    if not path.exists():
        return EnrollmentFile()
    try:
        return EnrollmentFile.model_validate(json.loads(path.read_text()))
    except (OSError, ValueError) as exc:
        warnings.warn(
            f"could not load observe enrollment from {path}: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return EnrollmentFile()


def save_enrollment(
    enrollment: EnrollmentFile, state_dir: Path | None = None
) -> Path:
    path = enrollment_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(enrollment.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    )
    path.chmod(0o600)
    return path


def get_repo_enrollment(
    repository_id: str, state_dir: Path | None = None
) -> RepoEnrollment | None:
    return load_enrollment(state_dir).repositories.get(repository_id)


def set_repo_enrollment(
    repository_id: str, repo: RepoEnrollment, state_dir: Path | None = None
) -> Path:
    enrollment = load_enrollment(state_dir)
    enrollment.repositories[repository_id] = repo
    return save_enrollment(enrollment, state_dir)


class RepoCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    argv: list[str]
    failure_kind: Literal["command.failed", "test.failed"] = "command.failed"


class CapturePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_output_bytes: int = 262144


class InvestigationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_model_calls: int = 4
    timeout_seconds: int = 90
    max_specialists: int = 1


class RepoPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exclude_paths: list[str] = Field(default_factory=list)
    commands: dict[str, RepoCommand] | None = None
    capture: CapturePolicy = Field(default_factory=CapturePolicy)
    investigation: InvestigationPolicy = Field(default_factory=InvestigationPolicy)


DEFAULT_POLICY = RepoPolicy()

_POLICY_KEYS = {"exclude_paths", "commands", "capture", "investigation"}


@dataclass
class PolicyLoad:
    policy: RepoPolicy
    warnings: list[str] = field(default_factory=list)
    path: Path | None = None


def load_repo_policy(
    repo_root: str | Path, *, defaults: RepoPolicy | None = None
) -> PolicyLoad:
    defaults = defaults or RepoPolicy()
    path = Path(repo_root) / ".voss" / "observe.yml"
    if not path.exists():
        return PolicyLoad(policy=defaults)
    try:
        raw = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        return PolicyLoad(
            policy=defaults, warnings=[f"could not parse {path}: {exc}"], path=path
        )
    if not isinstance(raw, dict):
        return PolicyLoad(
            policy=defaults, warnings=[f"{path}: expected a mapping"], path=path
        )
    if raw.get("version", 1) != 1:
        return PolicyLoad(
            policy=defaults,
            warnings=[f"{path}: unsupported version {raw.get('version')!r}"],
            path=path,
        )

    body = raw.get("observe")
    if not isinstance(body, dict):
        body = {k: v for k, v in raw.items() if k != "version"}

    warns: list[str] = []
    for key in body:
        if key not in _POLICY_KEYS:
            warns.append(f"{path}: unknown key {key!r} ignored")

    exclude_paths = sorted(
        set(defaults.exclude_paths)
        | {str(p) for p in (body.get("exclude_paths") or [])}
    )

    commands = defaults.commands
    raw_commands = body.get("commands")
    if raw_commands is not None:
        if not isinstance(raw_commands, dict):
            warns.append(f"{path}: commands must be a mapping; ignored")
        else:
            parsed: dict[str, RepoCommand] = {}
            for name, spec in raw_commands.items():
                try:
                    parsed[str(name)] = RepoCommand.model_validate(spec)
                except ValueError as exc:
                    warns.append(f"{path}: commands.{name}: {exc}; ignored")
            commands = parsed

    capture = _narrow_capture(body.get("capture"), defaults.capture, path, warns)
    investigation = _narrow_investigation(
        body.get("investigation"), defaults.investigation, path, warns
    )

    return PolicyLoad(
        policy=RepoPolicy(
            exclude_paths=exclude_paths,
            commands=commands,
            capture=capture,
            investigation=investigation,
        ),
        warnings=warns,
        path=path,
    )


def _narrow_int(
    raw: Any, default: int, label: str, path: Path, warns: list[str]
) -> int:
    if raw is None:
        return default
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
    except (TypeError, ValueError):
        warns.append(f"{path}: {label} {raw!r} is not a positive integer; ignored")
        return default
    if value > default:
        warns.append(f"{path}: {label} {value} exceeds default {default}; clamped")
        return default
    return value


def _narrow_capture(
    raw: Any, defaults: CapturePolicy, path: Path, warns: list[str]
) -> CapturePolicy:
    if raw is None:
        return defaults
    if not isinstance(raw, dict):
        warns.append(f"{path}: capture must be a mapping; ignored")
        return defaults
    return CapturePolicy(
        max_output_bytes=_narrow_int(
            raw.get("max_output_bytes"),
            defaults.max_output_bytes,
            "capture.max_output_bytes",
            path,
            warns,
        )
    )


def _narrow_investigation(
    raw: Any, defaults: InvestigationPolicy, path: Path, warns: list[str]
) -> InvestigationPolicy:
    if raw is None:
        return defaults
    if not isinstance(raw, dict):
        warns.append(f"{path}: investigation must be a mapping; ignored")
        return defaults
    return InvestigationPolicy(
        max_model_calls=_narrow_int(
            raw.get("max_model_calls"),
            defaults.max_model_calls,
            "investigation.max_model_calls",
            path,
            warns,
        ),
        timeout_seconds=_narrow_int(
            raw.get("timeout_seconds"),
            defaults.timeout_seconds,
            "investigation.timeout_seconds",
            path,
            warns,
        ),
        max_specialists=_narrow_int(
            raw.get("max_specialists"),
            defaults.max_specialists,
            "investigation.max_specialists",
            path,
            warns,
        ),
    )


__all__ = [
    "DEFAULT_POLICY",
    "CapturePolicy",
    "EnrollmentFile",
    "InvestigationPolicy",
    "PolicyLoad",
    "RepoCommand",
    "RepoEnrollment",
    "RepoPolicy",
    "enrollment_path",
    "get_repo_enrollment",
    "load_enrollment",
    "load_repo_policy",
    "save_enrollment",
    "set_repo_enrollment",
]
