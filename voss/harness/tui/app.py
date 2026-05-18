"""VossTUIApp — Textual app shell mounting the locked region grid.

UI-SPEC region grid (1 row header, scrollable main pane + collapsible side
panel, 1 row status, 1+ row input). M9-02 ships the empty shell; later
plans wire palette (M9-03), recorder (M9-04), modals (M9-05), resume
(M9-06).
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal

from voss.harness.session import SessionRecord
from voss.harness.slash import SlashRegistry
from voss_runtime.memory.episodic import EpisodicMemory

from .keymap import KEYMAP
from .widgets import (
    ForkConfirmModal,
    HeaderBar,
    HelpOverlay,
    InputBar,
    LocalBlockNote,
    LocalBlockShell,
    SideRegion,
    StatusLine,
    SubAgentPanel,
    TurnView,
)


class VossTUIApp(App):
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        (b.key, b.action, b.description)
        for b in KEYMAP
        if b.context in ("global", "input", "modal")
    ]

    def __init__(
        self,
        *,
        session_id: str = "",
        model: str = "",
        budget_total: int = 0,
        slash_registry: SlashRegistry | None = None,
        history: EpisodicMemory | None = None,
        **kw,
    ) -> None:
        super().__init__(**kw)
        self.session_id = session_id
        self.model = model
        self.budget_total = budget_total
        self.slash_registry = slash_registry or SlashRegistry()
        self.history = history
        self._turn_dispatch = None
        # M9-06 fork wiring. cli.py (M9-07) sets `record` on the live app.
        # `focused_turn_index` defaults to the most recent turn.
        self.record: SessionRecord | None = None
        self.focused_turn_index: int | None = None
        # T1-06: tracks the in-flight agent turn task so action_interrupt
        # can cancel it. Cleared via add_done_callback when the task ends.
        self.active_turn_task: Optional[asyncio.Task] = None

    def register_turn_task(self, task: asyncio.Task) -> None:
        """Register the active agent-turn task (T1-06).

        cli._run_turn_cancellable calls this once per turn so
        action_interrupt has a handle to cancel. Raises on double-register
        when a prior task is still running.
        """
        if self.active_turn_task is not None and not self.active_turn_task.done():
            raise RuntimeError("active turn task already registered")
        self.active_turn_task = task
        task.add_done_callback(self._clear_turn_task)

    def _clear_turn_task(self, task: asyncio.Task) -> None:
        # done_callback fires whether the task completed naturally or was
        # cancelled — either way the slot is now free for the next turn.
        self.active_turn_task = None

    def action_open_help(self) -> None:
        self.push_screen(HelpOverlay(KEYMAP, self.slash_registry))

    def push_modal_and_wait(self, modal, on_decision_callback) -> None:
        """Push a modal screen and wire its dismiss result to a callback.

        Used by the M9-05 permissions bridge to drive PermissionModal /
        ScopeExpandModal / DiffModal / BudgetExhaustedModal from worker
        threads via `call_from_thread(self.push_modal_and_wait, ...)`.
        """
        self.push_screen(modal, on_decision_callback)

    def action_dismiss_modal(self) -> None:
        try:
            self.pop_screen()
        except Exception:  # noqa: BLE001 — no screen to pop
            pass

    def action_redraw(self) -> None:
        self.refresh()

    def action_interrupt(self) -> None:
        # T1-06: cancel the in-flight turn task. The agent loop's
        # CancelledError handler in _run_turn_exec finalizes the recorder
        # with exit_reason="interrupt".
        task = self.active_turn_task
        if task is not None and not task.done():
            task.cancel()

    # ------------------------------------------------------------------
    # M9-06 fork-from-turn (TUI-08).
    # ------------------------------------------------------------------

    def _resolve_fork_index(self) -> int | None:
        if self.record is None or not self.record.turns:
            return None
        if self.focused_turn_index is not None:
            idx = self.focused_turn_index
        else:
            idx = len(self.record.turns) - 1
        if idx < 0 or idx >= len(self.record.turns):
            return None
        return idx

    def action_fork_turn(self) -> None:
        idx = self._resolve_fork_index()
        if idx is None:
            return

        def _on_confirm(confirmed) -> None:
            if not confirmed:
                return
            # Local import — keeps fork.py UI-free (pure data) and avoids a
            # circular import at module load.
            from .fork import fork_session

            assert self.record is not None  # _resolve_fork_index guards
            new = fork_session(self.record, idx, Path(self.record.cwd))
            try:
                self.query_one("#status", StatusLine).set_status(
                    toast=f"Resumed {new.id} · {len(new.turns)} turns"
                )
            except Exception:  # noqa: BLE001 — status widget may not be mounted in tests
                pass

        self.push_screen(ForkConfirmModal(idx), _on_confirm)

    def action_focus_next(self) -> None:
        super().action_focus_next()

    def action_focus_previous(self) -> None:
        super().action_focus_previous()

    # ------------------------------------------------------------------
    # M9-04 mutators called by TextualRenderer + RecorderBridge.
    # ------------------------------------------------------------------

    def mount_subagent_panel(self, panel: "SubAgentPanel") -> None:
        side = self.query_one("#side")
        side.mount(panel)
        side.display = True
        side.styles.display = "block"

    def update_subagent(self, parent_id: str, body_line: str, used: int = 0) -> None:
        for panel in self.query(SubAgentPanel):
            if getattr(panel, "parent_id", None) == parent_id:
                panel.append_body(body_line)
                if used:
                    panel.update_budget(used)
                return

    def collapse_subagent(self, parent_id: str, n_results: int = 0) -> None:
        for panel in list(self.query(SubAgentPanel)):
            if getattr(panel, "parent_id", None) == parent_id:
                panel.remove()
        # Hide side region when empty.
        side = self.query_one("#side")
        if not list(side.query(SubAgentPanel)):
            side.display = False
            side.styles.display = "none"
        try:
            self.query_one("#main", TurnView).append_turn(
                "gather", f"✓ gathered · {n_results} results"
            )
        except Exception:  # noqa: BLE001
            pass

    def update_inspected(self, paths: list[str]) -> None:
        try:
            tv = self.query_one("#main", TurnView)
        except Exception:  # noqa: BLE001
            return
        for path in paths:
            tv.append_turn("inspect", path)

    def update_changed(self, paths: list[str]) -> None:
        try:
            tv = self.query_one("#main", TurnView)
        except Exception:  # noqa: BLE001
            return
        for path in paths:
            tv.append_turn("change", path)

    def append_tool_line(self, summary: str, *, state: str = "ok") -> None:
        try:
            tv = self.query_one("#main", TurnView)
        except Exception:  # noqa: BLE001
            return
        prefix = "✓" if state == "ok" else "✗"
        tv.append_turn("tool", f"{prefix} {summary}")

    def on_input_bar_submitted(self, event: InputBar.Submitted) -> None:
        if self._turn_dispatch is None:
            return
        result = self._turn_dispatch(event.value)
        if asyncio.iscoroutine(result):
            task = asyncio.create_task(result)
        else:
            async def _done():
                return result

            task = asyncio.create_task(_done())
        self.register_turn_task(task)

    def on_local_event(self, event_name: str, payload: dict) -> None:
        try:
            tv = self.query_one("#main", TurnView)
        except Exception:  # noqa: BLE001
            return
        if getattr(tv, "_turn_count", 0) == 0:
            tv.clear()
        if event_name == "shell.local":
            block = LocalBlockShell(
                str(payload.get("cmd", "")),
                str(payload.get("stdout", "")),
                str(payload.get("stderr", "")),
                int(payload.get("exit_code", 0)),
            )
        elif event_name == "memory.note":
            block = LocalBlockNote()
        elif event_name == "notice":
            try:
                from .widgets import LocalBlockNotice
            except Exception:  # noqa: BLE001
                tv.append_turn("notice", str(payload.get("message", "")))
                return
            block = LocalBlockNotice(str(payload.get("message", "")))
        else:
            return
        tv._turn_count += 1  # noqa: SLF001 - matches TurnView append protocol.
        tv.write(block.render())

    def compose(self) -> ComposeResult:
        yield HeaderBar(id="header")
        with Horizontal():
            yield TurnView(id="main")
            yield SideRegion(id="side")
        yield StatusLine(id="status")
        yield InputBar(id="input")

    def on_mount(self) -> None:
        # Locked default focus = input bar.
        self.query_one("#input", InputBar).focus()
        # Seed header so an unbound app still renders something useful.
        self.query_one("#header", HeaderBar).update_header(
            session_id=self.session_id,
            model=self.model,
            budget_used=0,
            budget_total=self.budget_total,
            git_status="",
        )
