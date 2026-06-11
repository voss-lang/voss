"""VossTUIApp — Textual app shell mounting the locked region grid.

UI-SPEC region grid (1 row header, scrollable main pane + collapsible side
panel, 1 row status, 1+ row input). M9-02 ships the empty shell; later
plans wire palette (M9-03), recorder (M9-04), modals (M9-05), resume
(M9-06).
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from voss.harness.session import SessionRecord
from voss.harness.slash import SlashRegistry
from voss_runtime.memory.episodic import EpisodicMemory

from .keymap import KEYMAP

# Fenced code block: ```lang\n ...body... ```  (lang optional). DOTALL so a
# block can span lines; non-greedy so adjacent blocks don't merge.
_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def extract_last_code_block(text: str) -> str | None:
    """Return the body of the LAST fenced code block in `text`, or None.

    Pure helper so the copy-code action can be unit-tested without an App.
    """
    if not text:
        return None
    blocks = _FENCE_RE.findall(text)
    if not blocks:
        return None
    return blocks[-1].rstrip("\n")
from .widgets import (
    CodeIntelPanel,
    ForkConfirmModal,
    HelpOverlay,
    InputBar,
    LocalBlockNote,
    LocalBlockShell,
    SideRegion,
    StatusLine,
    Toast,
    ToolCard,
    TranscriptView,
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
        self.cwd: Path | None = None
        self.git_status: str = ""
        self.provider: str = ""
        self.mode: str = ""
        self.total_cost: float = 0.0
        self._turn_dispatch = None
        # M9-06 fork wiring. cli.py (M9-07) sets `record` on the live app.
        # `focused_turn_index` defaults to the most recent turn.
        self.record: SessionRecord | None = None
        self.focused_turn_index: int | None = None
        # R4 (spec §7.2): app-scoped expand/collapse-all state (D-09 quiet-
        # by-default). action_toggle_detail (ctrl+o) applies it uniformly to
        # every mounted ToolCard / AgentTreeCard; cards mounted while
        # expanded-mode is on mount expanded.
        self._detail_expanded: bool = False
        # T1-06: tracks the in-flight agent turn task so action_interrupt
        # can cancel it. Cleared via add_done_callback when the task ends.
        self.active_turn_task: Optional[asyncio.Task] = None
        # R6 (spec §7.3): inputs submitted while a turn runs queue here and
        # dispatch FIFO from _clear_turn_task. ctrl+c clears the queue
        # before it interrupts.
        self._queued_inputs: list[str] = []
        # R4 (spec §5.6): CodeIntelPanel is #side's only occupant.
        self._code_intel_panel: CodeIntelPanel | None = None
        # Last assistant response text, captured by TextualRenderer so
        # action_copy_code (ctrl+y) can yank its last fenced code block.
        self._last_response_text: str = ""

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
        # cancelled — either way the slot is now free for the next turn and
        # the working indicator comes down (R2 spec §3.6: removed on
        # finalize AND on interrupt — this single point covers both).
        self.active_turn_task = None
        try:
            self.query_one("#main", TranscriptView).hide_working()
        except Exception:  # noqa: BLE001 — transcript absent in tests
            pass
        # R6 (spec §7.3): turn finalize is the authoritative dispatch point
        # for queued inputs — FIFO, one at a time (the next queued message
        # dispatches when THIS dispatch's own done-callback fires). The
        # interrupt path never reaches here with a queue: action_interrupt
        # clears it before cancelling.
        if self._queued_inputs:
            next_value = self._queued_inputs.pop(0)
            self._refresh_queue_chips()
            try:
                self._dispatch_input(next_value)
            except Exception:  # noqa: BLE001 — loop tearing down
                pass

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

    def _toast(self, message: str) -> None:
        # R5 (spec §5.3): toasts render in the overlay Toast widget, not the
        # status line, so session metadata never jumps.
        try:
            self.query_one("#toast", Toast).show_toast(message)
        except Exception:  # noqa: BLE001 — toast widget absent in tests
            pass

    def note_response_text(self, text: str) -> None:
        """Record the latest assistant response for the copy-code action."""
        if text:
            self._last_response_text = text

    def action_copy_code(self) -> None:
        """Yank the last fenced code block (or the whole last response) to the
        system clipboard. Ported from OpenCode's copy ergonomics — RichLog has
        no native selection at this Textual version, so we copy structurally."""
        text = self._last_response_text or ""
        block = extract_last_code_block(text)
        payload = block if block is not None else text.strip()
        if not payload:
            self._toast("nothing to copy yet")
            return
        try:
            self.copy_to_clipboard(payload)
        except Exception:  # noqa: BLE001 — clipboard may be unavailable (no OSC52)
            self._toast("copy failed")
            return
        self._toast("copied code block" if block is not None else "copied response")

    def action_interrupt(self) -> None:
        # Ctrl+C behavior: if a turn is running, cancel it. If idle, exit app.
        task = self.active_turn_task
        if task is not None and not task.done():
            # R2 spec §3.3: the streamed block keeps its content and the
            # footer reads `· interrupted`. Mark BEFORE cancelling so the
            # agent's CancelledError finalize_stream consumes the flag.
            try:
                self.query_one("#main", TranscriptView).mark_interrupted()
            except Exception:  # noqa: BLE001 — transcript absent in tests
                pass
            task.cancel()
            return
        # No active turn — exit the Textual app (returns to normal terminal).
        self.exit()

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

    # ------------------------------------------------------------------
    # R4 global expand/collapse-all (spec §7.2, generalizes the M13-04
    # sub-agent detail reveal — same ctrl+o key, superset behavior).
    # Bound via keymap.py's "main" tier; D-09 quiet-by-default preserved.
    # ------------------------------------------------------------------

    def action_toggle_detail(self) -> None:
        # One app-scoped toggle applied uniformly to every mounted ToolCard
        # (AgentTreeCard included — it subclasses ToolCard) so cards mounted
        # while expanded-mode is on stay consistent with the global state
        # (TranscriptView checks `_detail_expanded` at mount).
        self._detail_expanded = not self._detail_expanded
        for card in self.query(ToolCard):
            if self._detail_expanded:
                card.expand()
            else:
                card.collapse()

    def action_focus_next(self) -> None:
        super().action_focus_next()

    def action_focus_previous(self) -> None:
        super().action_focus_previous()

    # ------------------------------------------------------------------
    # R4 (spec §5.6): #side has exactly one occupant — CodeIntelPanel.
    # The M9-08 region-share/pin state machine is deleted; show/hide only.
    # ------------------------------------------------------------------

    def show_code_intel_panel(self) -> None:
        """Show the CodeIntelPanel (the side region's only occupant)."""
        side = self.query_one("#side")
        if self._code_intel_panel:
            if self._code_intel_panel not in list(side.children):
                side.mount(self._code_intel_panel)
            self._code_intel_panel.display = True
            side.display = True
            side.styles.display = "block"

    def hide_code_intel_panel(self) -> None:
        """Hide the side region (back to the focused composer layout)."""
        side = self.query_one("#side")
        side.display = False
        side.styles.display = "none"

    def update_inspected(self, paths: list[str]) -> None:
        try:
            tv = self.query_one("#main", TranscriptView)
        except Exception:  # noqa: BLE001
            return
        for path in paths:
            tv.append_turn("inspect", path)

    def update_changed(self, paths: list[str]) -> None:
        try:
            tv = self.query_one("#main", TranscriptView)
        except Exception:  # noqa: BLE001
            return
        for path in paths:
            tv.append_turn("change", path)

    def append_tool_line(self, summary: str, *, state: str = "ok") -> None:
        try:
            tv = self.query_one("#main", TranscriptView)
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
        # R2 spec §3.6: indicator appears on dispatch (≤ 100 ms). Removal is
        # the task done_callback in _clear_turn_task.
        try:
            self.query_one("#main", TranscriptView).show_working()
        except Exception:  # noqa: BLE001 — transcript absent in tests
            pass

    def on_mention_palette_mention_submitted(self, event) -> None:
        """Insert the selected file path into the input, replacing the @token."""
        path = getattr(event, "value", "")
        if not path:
            return
        try:
            self.query_one("#input", InputBar).insert_mention(path)
        except Exception:  # noqa: BLE001 — input absent in tests
            pass

    def on_slash_palette_palette_submitted(self, event) -> None:
        """Route slash palette selection through the normal dispatch path."""
        cmd_name = getattr(event, "value", "")
        if not cmd_name:
            return
        # Re-post as an InputBar.Submitted so _turn_dispatch handles it.
        # cmd_name may already carry a leading "/" (registry ids do) — normalize
        # so we never produce "//agent".
        self.on_input_bar_submitted(InputBar.Submitted("/" + cmd_name.lstrip("/")))

    def on_local_event(self, event_name: str, payload: dict) -> None:
        try:
            tv = self.query_one("#main", TranscriptView)
        except Exception:  # noqa: BLE001
            return
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
        tv.add_local_block(block)

    def compose(self) -> ComposeResult:
        # R5 (spec §5.1): HeaderBar deleted — budget lives in the StatusLine
        # right zone; session id surfaces via the launch toast (and the R6
        # HomeScreen data rows).
        with Horizontal():
            yield TranscriptView(id="main")
            yield SideRegion(id="side")
        yield StatusLine(id="status")
        yield InputBar(id="input")
        yield Toast(id="toast")

    def on_mount(self) -> None:
        # Locked default focus = input bar.
        self.query_one("#input", InputBar).focus()
        # M9-08: keep CodeIntelPanel ready, but start in the focused composer
        # layout. Sub-agent/code-intel activity can reveal the side region.
        self._code_intel_panel = CodeIntelPanel()
        side = self.query_one("#side")
        side.mount(self._code_intel_panel)
        side.display = False
        side.styles.display = "none"
        cwd_text = ""
        if self.cwd is not None:
            try:
                cwd_text = str(self.cwd).replace(str(Path.home()), "~", 1)
            except Exception:  # noqa: BLE001
                cwd_text = str(self.cwd)
        self.query_one("#status", StatusLine).set_status(
            provider=self.provider,
            model=self.model,
            mode=self.mode,
            git_status=self.git_status or cwd_text,
            tokens=0,
            cost_usd=self.total_cost,
            ctx_pct=0.0,
            budget_total=self.budget_total,
        )
        # R5 (spec §5.5): mode-aware input border (plan/restricted → $warn).
        self.query_one("#input", InputBar).set_mode(self.mode)
        # R5 (spec §5.1): session id is no longer in chrome — surface it once
        # on launch via the toast overlay (HomeScreen data rows land in R6).
        if self.session_id:
            self._toast(f"session {self.session_id[:8]}")
