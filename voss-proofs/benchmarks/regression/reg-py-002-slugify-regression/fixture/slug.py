import re


def slugify(text: str) -> str:
    """Lowercase ASCII words joined by hyphens."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]", "-", text)
    return text.strip("-")
