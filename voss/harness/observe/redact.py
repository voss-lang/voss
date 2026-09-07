"""Evidence redaction, applied before any evidence row is written.

Reuses the telemetry redaction patterns (`redact_tool_args`, `redact_url`).
Best effort, not proof that arbitrary terminal output is safe.
"""
from __future__ import annotations

import re
from typing import Any

from voss.harness.telemetry import redact_tool_args, redact_url

_SENSITIVE_NAME = re.compile(
    r"[A-Z0-9_]*(PASSWORD|SECRET|TOKEN|API_KEY|APIKEY|AUTHORIZATION|CREDENTIAL|PRIVATE_KEY)[A-Z0-9_]*"
)
_ASSIGNMENT = re.compile(
    r"\b(?P<key>[A-Za-z_][A-Za-z0-9_]*)(?P<sep>\s*[=:]\s*)(?P<quote>[\"']?)(?P<value>[^\s\"']+)(?P=quote)"
)
_URL = re.compile(r"https?://[^\s\"'<>)]+")


def redact_text(text: str) -> str:
    def _sub(match: re.Match[str]) -> str:
        key = match.group("key")
        if _SENSITIVE_NAME.fullmatch(key.upper()):
            return f"{key}{match.group('sep')}<redacted>"
        return match.group(0)

    redacted = _ASSIGNMENT.sub(_sub, text)
    return _URL.sub(lambda m: redact_url(m.group(0)), redacted)


def redact_argv(argv: list[str]) -> list[str]:
    return [redact_text(arg) for arg in argv]


def redact_mapping(args: dict[str, Any]) -> dict[str, Any]:
    return redact_tool_args(args)


__all__ = ["redact_argv", "redact_mapping", "redact_text"]
