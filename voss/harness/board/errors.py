"""Typed exceptions for the board state machine (O3).

`BoardError` is the base; the three subclasses each carry a structured
attribute the audit surface (O6) reads.
"""
from __future__ import annotations


class BoardError(Exception):
    """Base for all board-state-machine errors."""


class BoardWIPError(BoardError):
    """Raised when a transition would exceed a destination column's WIP cap.

    Attrs:
        column: the destination column whose cap was exceeded
        cap:    the cap value
    """
    def __init__(self, column: str, cap: int) -> None:
        self.column = column
        self.cap = cap
        super().__init__(f"WIP cap exceeded for column {column!r}: cap={cap}")


class BoardGateError(BoardError):
    """Raised when a transition is refused by a gate predicate or by an unknown column name.

    Attrs:
        reason:          short human-readable refusal reason
        failing_clauses: list of predicate `.name` strings that returned False
    """
    def __init__(self, reason: str, failing_clauses: list[str] | None = None) -> None:
        self.reason = reason
        self.failing_clauses = list(failing_clauses) if failing_clauses else []
        super().__init__(reason)


class BoardTimeoutError(BoardError):
    """Raised when a card is forced terminal by deadline / budget / retry-ceiling.

    Attrs:
        reason: one of {"timeout", "budget", "retry_ceiling"}
    """
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"forced terminal: {reason}")
