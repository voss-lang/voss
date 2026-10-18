def parse_int(text: str) -> int:
    """Parse a base-10 integer written by a person."""
    digits = "".join(ch for ch in text if ch.isdigit() or ch == "-")
    return int(digits or 0)
