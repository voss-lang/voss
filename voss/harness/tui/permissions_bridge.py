"""TUI bridge: install modal-driven prompt callables into a PermissionGate.

The bridge does NOT modify `voss.harness.permissions.PermissionGate`. It uses
the existing `prompt_fn` and `scope_prompt_fn` dependency-injection points
(permissions.py lines 113-115) to route prompts through Textual modals while
the gate's `check()` logic stays byte-unchanged.

Threading: agent tools run on worker threads. The Future round-trip uses
`app.call_from_thread` to push the modal on the event loop, then blocks the
worker on `Future.result(timeout=...)` until the user makes a choice or the
inattention timeout (5 minutes default) elapses. Timeout → 'd' / 'n' (deny).
"""
from __future__ import annotations

from concurrent.futures import Future
from typing import Optional

from voss.harness.permissions import PermissionGate

from .widgets import PermissionModal, ScopeExpandModal


# 5-minute hard cap on user inattention. Test override allowed.
DEFAULT_TIMEOUT_S: float = 300.0


def _verb_for(tool_name: str) -> str:
    if tool_name in {"shell_run", "shell_run_background"}:
        return "run"
    if tool_name == "shell_signal":
        return "signal"
    if tool_name in {"fs_write", "fs_edit"}:
        return "modify"
    return "use"


def _short_target(tool_name: str, args: dict, limit: int = 60) -> str:
    if tool_name in {"shell_run", "shell_run_background"}:
        raw = str(args.get("cmd", ""))
    elif tool_name == "shell_signal":
        raw = str(args.get("handle", ""))
    elif tool_name in {"fs_write", "fs_edit"}:
        raw = str(args.get("path", ""))
    else:
        raw = ", ".join(f"{k}={v}" for k, v in (args or {}).items())
    if len(raw) > limit:
        return raw[: limit - 1] + "…"
    return raw


def install_tui_permissions(
    gate: PermissionGate, app, *, timeout_s: Optional[float] = None
) -> None:
    """Swap modal-driven callables into `gate.prompt_fn` and `gate.scope_prompt_fn`.

    After this call the gate's logic is unchanged; it merely consults the TUI
    modals instead of stderr/stdin when it needs a decision.
    """
    deadline = timeout_s if timeout_s is not None else DEFAULT_TIMEOUT_S

    def prompt(tool_name: str, args: dict) -> str:
        fut: Future[str] = Future()

        def _on_result(choice):
            # `dismiss(result)` callback path. `result` may be None if the
            # screen is popped without a value (defensive).
            if choice is None:
                choice = "d"
            if not fut.done():
                fut.set_result(str(choice))

        modal = PermissionModal(
            tool_name=tool_name,
            action_verb=_verb_for(tool_name),
            target=_short_target(tool_name, args),
        )
        app.call_from_thread(app.push_screen, modal, _on_result)
        try:
            return fut.result(timeout=deadline)
        except TimeoutError:
            return "d"

    def scope_prompt(target: str) -> str:
        fut: Future[str] = Future()

        def _on_result(choice):
            if choice is None:
                choice = "n"
            if not fut.done():
                fut.set_result(str(choice))

        modal = ScopeExpandModal(target=target)
        app.call_from_thread(app.push_screen, modal, _on_result)
        try:
            return fut.result(timeout=deadline)
        except TimeoutError:
            return "n"

    gate.prompt_fn = prompt
    gate.scope_prompt_fn = scope_prompt
