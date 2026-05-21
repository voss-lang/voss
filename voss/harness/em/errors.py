"""Typed exceptions for the EM cage (O5).

EMCageViolation is raised when the EM attempts an operation the cage
forbids: ceiling/p rewrite, non-roster dispatch, budget extension.
Structured `.op` and `.reason` attrs for O6 audit surface.
"""
from __future__ import annotations


class EMCageViolation(Exception):
    """Raised when the EM attempts a cage-forbidden operation.

    Attrs:
        op:     the verb that was refused (e.g. "dispatch", "set_ceiling")
        reason: human-readable refusal reason
    """
    def __init__(self, op: str, reason: str) -> None:
        self.op = op
        self.reason = reason
        super().__init__(f"cage violation [{op}]: {reason}")
