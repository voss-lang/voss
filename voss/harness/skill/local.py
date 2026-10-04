"""Discover SKILL.md folders without copying their contents into Voss."""
from __future__ import annotations

import asyncio
import warnings
from dataclasses import dataclass
from pathlib import Path

import yaml

from .. import local_sources
from ..config import config_path
from ..sandbox import jail_path


@dataclass(frozen=True)
class LocalSkill:
    name: str
    description: str
    path: Path
    manual: bool = False


def discover(cwd: Path) -> dict[str, LocalSkill]:
    home = local_sources.user_home()
    roots = [home / ".claude/skills", local_sources.codex_home() / "skills", home / ".agents/skills"]
    projects = local_sources.project_dirs(cwd)
    for root in projects:
        roots.extend(root / folder / "skills" for folder in (".claude", ".codex", ".agents"))
    roots.append(config_path().parent / "skills")
    roots.extend(root / ".voss/skills" for root in projects)
    disabled: set[Path] = set()
    for path in [local_sources.codex_home() / "config.toml", *[root / ".codex/config.toml" for root in projects]]:
        config = local_sources.read_config(path).get("skills", {})
        for entry in config.get("config", []) if isinstance(config, dict) else []:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                continue
            target = Path(entry["path"]).expanduser()
            target = (target if target.is_absolute() else path.parent / target).resolve()
            if entry.get("enabled") is False:
                disabled.add(target)
            else:
                disabled.discard(target)
    skills: dict[str, LocalSkill] = {}
    for root in roots:
        for path in sorted(root.glob("*/SKILL.md")):
            resolved = path.resolve()
            if resolved in disabled or resolved.parent in disabled:
                continue
            try:
                text = path.read_text(encoding="utf-8")
                lines = text.splitlines()
                metadata = {}
                if lines and lines[0] == "---":
                    end = lines.index("---", 1)
                    metadata = yaml.safe_load("\n".join(lines[1:end])) or {}
                if not isinstance(metadata, dict):
                    raise ValueError("expected frontmatter mapping")
                name = metadata.get("name", path.parent.name)
                description = metadata.get("description", "")
                if not isinstance(name, str) or not isinstance(description, str):
                    raise ValueError("invalid skill metadata")
                skills[name] = LocalSkill(name, description, resolved, bool(metadata.get("disable-model-invocation")))
            except (OSError, ValueError, yaml.YAMLError):
                warnings.warn(f"Could not read local skill: {path}", stacklevel=2)
    return skills


def read_skill(skill: LocalSkill, path: str = "SKILL.md") -> str:
    target = jail_path(skill.path.parent, path)
    return target.read_text(encoding="utf-8")


def prompt(name: str, arguments: list[str]) -> str:
    return f"Use the local skill {name!r}. Read its SKILL.md with skill_read before acting.\nTask: {' '.join(arguments)}"


def make_handler(skill: LocalSkill):
    def handler(ctx, args):
        from voss_runtime import get_config
        from ..agent import run_turn
        from ..cli import _run_turn_with_teardown

        turn = run_turn(
            prompt(skill.name, args), tools=ctx.tools, cwd=ctx.cwd, renderer=ctx.renderer,
            provider=ctx.provider, model=get_config().default_model, history=ctx.history,
            permissions=ctx.gate, session_id=ctx.record.id,
        )
        result = asyncio.run(_run_turn_with_teardown(turn, None, tools=ctx.tools, cwd=ctx.cwd))
        ctx.renderer.show_final(result.final, confidence=result.confidence, cost_usd=result.cost_usd)
    return handler
