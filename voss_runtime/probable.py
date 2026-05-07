from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar
from .exceptions import ConfidenceTooLowError

T = TypeVar("T")


@dataclass(frozen=True)
class ProbableValue(Generic[T]):
    value: T
    confidence: float       # 0.0 - 1.0

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")

    def gate(self, threshold: float) -> Optional[T]:
        return self.value if self.confidence >= threshold else None

    def unwrap(self, threshold: float = 0.0) -> T:
        if self.confidence < threshold:
            raise ConfidenceTooLowError(f"confidence {self.confidence} < {threshold}")
        return self.value

    def __matmul__(self, threshold: float) -> bool:
        # Supports `value @ 0.85` syntax — returns True if confidence >= threshold
        return self.confidence >= threshold

    def __repr__(self) -> str:
        return f"ProbableValue(value={self.value!r}, confidence={self.confidence:.2f})"
