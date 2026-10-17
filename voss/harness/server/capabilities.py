"""Protocol support; independent of provider login or model availability."""
from importlib.metadata import version
from typing import Literal

from pydantic import BaseModel


class Capabilities(BaseModel):
    v: Literal[1] = 1
    engine_version: str
    capabilities: list[str]


def report() -> Capabilities:
    return Capabilities(
        engine_version=version("voss"),
        capabilities=["sessions.v1", "tasks.replay.v1", "swarms.v1", "diagnostics.v1"],
    )
