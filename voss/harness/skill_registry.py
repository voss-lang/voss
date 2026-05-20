from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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

    def summarize_diff(ctx: Any, _args: list[str]) -> None:
        from .skills.summarize_diff import run

        run(
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
            id="summarize-diff",
            description="Summarize the working-tree git diff as a structured PR description.",
            handler=summarize_diff,
            mutating=False,
        )
    )

    def audit_cognition(ctx: Any, _args: list[str]) -> None:
        from .skills.audit_cognition import run

        run(
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
            id="audit-cognition",
            description="Audit project cognition for drift and propose an architecture update (never writes).",
            handler=audit_cognition,
            mutating=False,
        )
    )

    def add_test(ctx: Any, _args: list[str]) -> None:
        from .skills.add_test import run

        run(
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
            id="add-test",
            description="Locate a public function and generate a failing pytest test.",
            handler=add_test,
            mutating=True,
        )
    )

    def port_py_to_voss(ctx: Any, args: list[str]) -> None:
        from .skills.port_py_to_voss import run

        run(
            cwd=ctx.cwd,
            provider=ctx.provider,
            history=ctx.history,
            record=ctx.record,
            renderer=ctx.renderer,
            tools=ctx.tools,
            gate=ctx.gate,
            source=args[0] if args else None,
        )

    registry.register(
        SkillEntry(
            id="port-py-to-voss",
            description="Translate a Python source file to .voss.",
            handler=port_py_to_voss,
            mutating=True,
        )
    )
    # Load third-party .voss skills AFTER built-ins (built-in ids win on collision)
    load_voss_skills(Path.cwd(), registry)
    return registry


def load_voss_skills(cwd: Path, registry: SkillRegistry) -> None:
    """Discover installed .voss bundles and register them as SkillEntry handlers.

    Runs AFTER built-ins are registered so built-in ids are never shadowed.
    """
    from .plugins import load_plugins
    from .skill.adapter import make_voss_skill_handler
    from .skill.scope import scope_spec_from_manifest

    plugins = load_plugins(cwd)
    for plugin in plugins:
        if not plugin.voss_entry or not plugin.skill_id:
            continue
        if not plugin.enabled:
            continue
        # Skip if built-in id already registered (no shadowing)
        if registry.get(plugin.skill_id) is not None:
            continue
        bundle_dir = plugin.bundle_dir
        if bundle_dir is None:
            continue
        voss_path = bundle_dir / plugin.voss_entry
        if not voss_path.exists():
            continue
        spec = scope_spec_from_manifest({
            "scopes": {
                "tools": plugin.scope_tools,
                "fs": plugin.scope_fs,
                "net": plugin.scope_net,
            }
        })
        registry.register(
            SkillEntry(
                id=plugin.skill_id,
                description=plugin.description,
                handler=make_voss_skill_handler(
                    voss_path, spec, skill_id=plugin.skill_id
                ),
                mutating=plugin.skill_mutating,
            )
        )
