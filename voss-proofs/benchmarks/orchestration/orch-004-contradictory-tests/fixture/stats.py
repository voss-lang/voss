def mean(xs: list[float]) -> float:
    """Arithmetic mean. Raises ValueError for an empty list."""
    if not xs:
        raise ValueError("mean of empty list")
    return sum(xs) // len(xs)


def median(xs: list[float]) -> float:
    """Middle value; the mean of the two middle values for an even count.
    Raises ValueError for an empty list."""
    if not xs:
        raise ValueError("median of empty list")
    s = sorted(xs)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
