"""
Typed protocols for the Board surface
EMBoardHandle codes against these protocols so it never imports from
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Protocol, runtime_checkable


Column = Literal["Backlog", "Planned", "InProgress", "InReview", "Blocked", "Done"]

TERMINAL_COLUMNS: frozenset[str] = frozenset({"Done", "Blocked"})


@runtime_checkable
class CardProtocol(Protocol):
    node_id: str
    column: str
    risk_tier: str
    retry_count: int
    deadline: float


@runtime_checkable
class BoardProtocol(Protocol):
    def cards(self) -> list: ...
    def move(self, card: object, to: str) -> object: ...
    def _tick_once(self, now: float) -> None: ...
