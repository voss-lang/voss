"""Voss board state machine package (O3).

Public API:
    ReviewerVerdict, Reviewer   — O4 plug-in contract (verdict.py)
    BoardWIPError, BoardGateError, BoardTimeoutError — typed errors (errors.py)
    Board, Card, Column, RiskTier — state machine (machine.py, O3-02)
"""
from .verdict import ReviewerVerdict, Reviewer
from .errors import BoardError, BoardWIPError, BoardGateError, BoardTimeoutError
from .machine import Board, Card, Column, RiskTier

__all__ = [
    "ReviewerVerdict", "Reviewer",
    "BoardError", "BoardWIPError", "BoardGateError", "BoardTimeoutError",
    "Board", "Card", "Column", "RiskTier",
]
