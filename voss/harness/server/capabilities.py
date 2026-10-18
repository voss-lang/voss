"""Protocol support; independent of provider login or model availability."""
from importlib.metadata import version
from typing import Literal

from pydantic import BaseModel


class Capabilities(BaseModel):
    v: Literal[1] = 1
    engine_version: str
    capabilities: list[str]


def report(*, oauth_only: bool = False) -> Capabilities:
    return Capabilities(
        engine_version=version("voss"),
        capabilities=["sessions.v1", "tasks.replay.v1", "tasks.graph.v1", "tasks.review.v1", "swarms.v1", "diagnostics.v1", "harness.availability.v1"] + (["harness.oauth-only.v1", "plans.preview.v1"] if oauth_only else []),
    )
