from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


SkillHandler = Callable[[Any, list[str]], None]


@dataclass(frozen=True)
class SkillEntry:
    id: str
    description: str
    handler: SkillHandler
    mutating: bool = False


class SkillRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, SkillEntry] = {}

    def register(self, entry: SkillEntry) -> None:
        self._entries[entry.id] = entry

    def get(self, skill_id: str) -> SkillEntry | None:
        return self._entries.get(skill_id)

    def ids(self) -> list[str]:
        return sorted(self._entries)

    def entries(self) -> list[SkillEntry]:
        return [self._entries[k] for k in self.ids()]


def default_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()

    def analyze(ctx: Any, _args: list[str]) -> None:
        from .cli import _handle_analyze

        _handle_analyze(
            cwd=ctx.cwd,
            provider=ctx.provider,
            history=ctx.history,
            record=ctx.record,
            renderer=ctx.renderer,
            tools=ctx.tools,
            gate=ctx.gate,
        )

    registry.register(
        SkillEntry(
            id="analyze",
            description="Refresh project cognition (.voss/ + .voss-cache/).",
            handler=analyze,
            mutating=True,
        )
    )

    def rename_symbol(ctx: Any, args: list[str]) -> None:
        from .skills.rename_symbol import run

        run(
            cwd=ctx.cwd,
            provider=ctx.provider,
            history=ctx.history,
            record=ctx.record,
            renderer=ctx.renderer,
            tools=ctx.tools,
            gate=ctx.gate,
            args=args,
        )

    registry.register(
        SkillEntry(
            id="rename-symbol",
            description="Anchor + scope-aware rename across the repo.",
            handler=rename_symbol,
            mutating=True,
        )
    )

    def voss_lint_as_skill(ctx: Any, args: list[str]) -> None:
        from .skills.voss_lint_as_skill import run

        run(
            cwd=ctx.cwd,
            provider=ctx.provider,
            history=ctx.history,
            record=ctx.record,
            renderer=ctx.renderer,
            tools=ctx.tools,
            gate=ctx.gate,
            args=args,
        )

    registry.register(
        SkillEntry(
            id="voss-lint-as-skill",
            description="Lint .voss sources and emit structured JSON diagnostics.",
            handler=voss_lint_as_skill,
            mutating=False,
        )
    )
    return registry
