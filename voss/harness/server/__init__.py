"""Voss harness REST+SSE server (HYBRID-REFACTOR-PLAN H1).

Hosts the existing agent loop (`voss.harness.agent.run_turn`) behind an
HTTP+SSE contract (`.planning/PROTOCOL.md`) so a thin client can drive it.
The agent loop, providers, tools, sessions, permissions, and auth are NOT
reimplemented here — the server is an `EventBusRenderer` (satisfying the
existing `render.Renderer` protocol) publishing events onto an async queue
drained by an SSE endpoint.

Private implementation surface. Nothing here is part of the public SDK.
"""

from . import events
from .renderer import EventBusRenderer

__all__ = ["EventBusRenderer", "events"]
