from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    timeout: float = 5.0


def load(raw: dict) -> Settings:
    timeout = raw.get("timeout", 5.0)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout must be a positive number")
    return Settings(timeout=float(timeout))
