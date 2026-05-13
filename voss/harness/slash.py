from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Any, Callable


SlashHandler = Callable[[Any, list[str], str], None]


@dataclass(frozen=True)
class SlashCommand:
    name: str
    help: str
    handler: SlashHandler
    aliases: tuple[str, ...] = ()
    mutating: bool = False
    hidden: bool = False


class SlashRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}

    def register(self, command: SlashCommand) -> None:
        names = (command.name, *command.aliases)
        for name in names:
            self._commands[name] = command

    def lookup(self, name: str) -> SlashCommand | None:
        return self._commands.get(name)

    def ids(self, *, include_hidden: bool = False) -> list[str]:
        seen: set[str] = set()
        ids: list[str] = []
        for command in self._commands.values():
            if command.name in seen:
                continue
            if command.hidden and not include_hidden:
                continue
            seen.add(command.name)
            ids.append(command.name)
        return sorted(ids)

    def help_lines(self) -> list[str]:
        commands = [
            self._commands[name]
            for name in self.ids()
            if not self._commands[name].hidden
        ]
        width = max((len(c.name) for c in commands), default=0)
        return [f"{c.name:<{width}}  {c.help}" for c in commands]

    def dispatch(self, ctx: Any, line: str) -> bool:
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            raise ValueError(f"invalid slash command: {exc}") from exc
        if not parts or not parts[0].startswith("/"):
            return False
        command = self.lookup(parts[0])
        if command is None:
            return False
        command.handler(ctx, parts[1:], line)
        return True
