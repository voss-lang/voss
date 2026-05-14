"""VossTUIApp — Textual app shell mounting the locked region grid.

UI-SPEC region grid (1 row header, scrollable main pane + collapsible side
panel, 1 row status, 1+ row input). M9-02 ships the empty shell; later
plans wire palette (M9-03), recorder (M9-04), modals (M9-05), resume
(M9-06).
"""
from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal

from voss.harness.session import SessionRecord
from voss.harness.slash import SlashRegistry

from .keymap import KEYMAP
from .widgets import (
    ForkConfirmModal,
    HeaderBar,
    HelpOverlay,
    InputBar,
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
        **kw,
    ) -> None:
        super().__init__(**kw)
        self.session_id = session_id
        self.model = model
        self.budget_total = budget_total
        self.slash_registry = slash_registry or SlashRegistry()
        # M9-06 fork wiring. cli.py (M9-07) sets `record` on the live app.
        # `focused_turn_index` defaults to the most recent turn.
        self.record: SessionRecord | None = None
        self.focused_turn_index: int | None = None

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
        # M9-04 wires interrupt to the running turn; M9-03 stub is a no-op.
        pass

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
