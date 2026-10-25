def clamp(value: float, low: float, high: float) -> float:
    """Limit `value` to the inclusive range [low, high]."""
    return max(low, min(value, high))
