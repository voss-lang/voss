"""Frozen value objects for the team / organizational cage (O2).

Implements the structural shell for OTEAM-04 (immutable cage metadata) and
OTEAM-08 (opaque board/ritual carriers). Compilation from `*Decl` AST nodes
into these types is **O2-02** — this module only holds constructors and
immutability guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass

from voss.ast_nodes import Span


class VossTeamConfigError(Exception):
    """Raised when team configuration is invalid or inconsistent (compile phase)."""

    def __init__(
        self,
        message: str,
        *,
        role_span: Span | None = None,
        ceiling_span: Span | None = None,
    ) -> None:
        super().__init__(message)
        self.role_span = role_span
        self.ceiling_span = ceiling_span


@dataclass(frozen=True, slots=True)
class TeamRoleScope:
    globs: tuple[str, ...]

    def is_contained_in(self, other: TeamRoleScope | None) -> bool:
        if other is None:
            return True
        raise NotImplementedError("scope containment implemented in O2-02")


@dataclass(frozen=True, slots=True)
class TeamCeiling:
    budget_tokens: int | None
    scope: TeamRoleScope | None
    latency_seconds: int | None


@dataclass(frozen=True, slots=True)
class TeamPolicy:
    p: object | None


@dataclass(frozen=True, slots=True)
class BoardSpec:
    raw_items: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class RitualSpec:
    name: str
    raw_kvs: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class TeamConfig:
    name: str
    ceiling: TeamCeiling
    policy: TeamPolicy
    em_agent_id: str | None
    roster_ids: frozenset[str]
    board: BoardSpec | None
    rituals: tuple[RitualSpec, ...]
