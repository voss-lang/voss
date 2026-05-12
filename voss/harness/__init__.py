"""Voss agent harness — public API surface.

This module re-exports the stable public surface of the Voss harness. Names
listed in ``__all__`` are the **only** harness symbols covered by the
public-API stability contract (see ``docs/sdk.md``).

Anything not in ``__all__`` — including all submodules (``voss.harness.cli``,
``voss.harness.agent``, ``voss.harness.session``, etc.) — is considered
private implementation and may change in any release, including patch
versions, without notice. Pre-1.0 (the current track) reserves the right to
break the public surface in minor releases; patch releases will not break it.

Embed Voss in a Python application::

    from voss.harness import run_turn, Plan, ToolCall, TurnResult

    result: TurnResult = await run_turn(
        task="summarize this repo",
        tools=my_tool_registry,
        cwd=Path.cwd(),
        renderer=my_renderer,
    )

Run the CLI programmatically::

    from voss.harness import main
    main(["do", "summarize this repo"])
"""

from .agent import Plan, RunSemantics, ToolCall, TurnResult, run_turn
from .cli import main
from .permissions import PermissionGate
from .tools import ToolEntry

__all__ = [
    "Plan",
    "PermissionGate",
    "RunSemantics",
    "ToolCall",
    "ToolEntry",
    "TurnResult",
    "main",
    "run_turn",
]
