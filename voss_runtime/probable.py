from __future__ import annotations
import operator
import warnings
from dataclasses import dataclass, field
from typing import Generic, Literal, Optional, TypeVar
from .exceptions import ConfidenceTooLowError

T = TypeVar("T")

Source = Literal["jev", "self_report", "unknown", "given"]
_SOURCES = ("jev", "self_report", "unknown", "given")
_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}
_UNMEASURED = (
    "confidence gate on an unmeasured value always fails: ask() does not measure "
    "confidence; use judge(...).to_probable() for a measured one"
)


@dataclass(frozen=True)
class ProbableValue(Generic[T]):
    value: T
    confidence: Optional[float]
    source: Source = field(default="given", kw_only=True)

    def __post_init__(self):
        if self.source not in _SOURCES:
            raise ValueError(f"source must be one of {_SOURCES}, got {self.source!r}")
        if (self.confidence is None) != (self.source == "unknown"):
            raise ValueError("confidence is None if and only if source is 'unknown'")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")

    @classmethod
    def from_reply(cls, value: T) -> ProbableValue[T]:
        conf = getattr(value, "confidence", None)
        if isinstance(conf, (int, float)) and not isinstance(conf, bool):
            return cls(value, float(conf), source="self_report")
        return cls(value, None, source="unknown")

    def meets(self, op: str, threshold: float) -> bool:
        if self.confidence is None:
            warnings.warn(_UNMEASURED, RuntimeWarning, stacklevel=2)
            return False
        return _OPS[op](self.confidence, threshold)

    def gate(self, threshold: float) -> Optional[T]:
        if threshold <= 0:
            return self.value
        return self.value if self.meets(">=", threshold) else None

    def unwrap(self, threshold: float = 0.0) -> T:
        if threshold > 0 and (self.confidence is None or self.confidence < threshold):
            shown = "unknown" if self.confidence is None else self.confidence
            raise ConfidenceTooLowError(f"confidence {shown} < {threshold}")
        return self.value

    def __matmul__(self, threshold: float) -> bool:
        return self.meets(">=", threshold)

    def __repr__(self) -> str:
        shown = "unknown" if self.confidence is None else f"{self.confidence:.2f}"
        return f"ProbableValue(value={self.value!r}, confidence={shown})"
