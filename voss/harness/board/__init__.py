"""Voss board state machine package (O3).

Public API:
    ReviewerVerdict, Reviewer   — O4 plug-in contract (verdict.py)
    BoardWIPError, BoardGateError, BoardTimeoutError — typed errors (errors.py)

Symbols added in subsequent O3 waves (NOT exported here yet):
    Board, Card, Column         — O3-02 machine.py
"""
from .verdict import ReviewerVerdict, Reviewer
from .errors import BoardError, BoardWIPError, BoardGateError, BoardTimeoutError

__all__ = [
    "ReviewerVerdict", "Reviewer",
    "BoardError", "BoardWIPError", "BoardGateError", "BoardTimeoutError",
]
