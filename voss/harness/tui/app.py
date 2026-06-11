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
from textual.containers import Horizontal, Vertical

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
    HeaderBar,
    HelpOverlay,
    InputBar,
    LocalBlockNote,
    LocalBlockShell,
    SideRegion,
    StatusLine,
    SubAgentPanel,
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
        # M13-04: app-scoped sub-agent step-detail visibility (D-09 quiet-by-
        # default). Applied uniformly across every mounted SubAgentPanel body
        # by action_toggle_subagent_detail (one toggle, not per-panel state).
        self._subagent_detail_visible: bool = False
        # T1-06: tracks the in-flight agent turn task so action_interrupt
        # can cancel it. Cleared via add_done_callback when the task ends.
        self.active_turn_task: Optional[asyncio.Task] = None
        # M9-08 CodeIntelPanel region-share state machine (default code_intel;
        # SubAgentPanel wins on active spawn unless pinned).
        self._side_owner: str = "code_intel"
        self._side_pinned: bool = False
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

    def _toast(self, message: str) -> None:
        try:
            self.query_one("#status", StatusLine).set_status(toast=message)
        except Exception:  # noqa: BLE001 — status widget absent in tests
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
    # M13-04 quiet-by-default sub-agent step-detail reveal (D-09 / MAG-02).
    # Bound to ctrl+o (keymap.py "main" tier). Mirrors action_fork_turn's
    # placement: a "main"-context action handler living on VossTUIApp.
    # ------------------------------------------------------------------

    def action_toggle_subagent_detail(self) -> None:
        # One app-scoped toggle applied uniformly to every mounted panel so
        # panels mounted-while-revealed stay consistent with the global state.
        self._subagent_detail_visible = not self._subagent_detail_visible
        target = "block" if self._subagent_detail_visible else "none"
        for panel in self.query(SubAgentPanel):
            try:
                body = panel.query_one(
                    f"#panel-body-{panel.parent_id}", Vertical
                )
                body.styles.display = target
            except Exception:  # noqa: BLE001 — panel mid-mount may lack body
                pass

    def action_focus_next(self) -> None:
        super().action_focus_next()

    def action_focus_previous(self) -> None:
        super().action_focus_previous()

    # ------------------------------------------------------------------
    # M9-04 mutators called by TextualRenderer + RecorderBridge.
    # ------------------------------------------------------------------

    def mount_subagent_panel(self, panel: "SubAgentPanel") -> None:
        self.show_subagent_panel()  # M9-08 ownership (respects pin)
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
        # M9-08: if not pinned to sub_agent, restore CodeIntelPanel on final gather.
        side = self.query_one("#side")
        if not list(side.query(SubAgentPanel)):
            if not self._side_pinned or self._side_owner == "code_intel":
                self._side_owner = "code_intel"
                if self._code_intel_panel:
                    # Re-mount if it was removed during spawn
                    if self._code_intel_panel not in list(side.children):
                        side.mount(self._code_intel_panel)
                    side.display = True
                    side.styles.display = "block"
            else:
                side.display = False
                side.styles.display = "none"
        try:
            self.query_one("#main", TranscriptView).append_turn(
                "gather", f"✓ gathered · {n_results} results"
            )
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # M9-08 CodeIntelPanel region-share + pin API (CODE-07 contract)
    # ------------------------------------------------------------------

    def show_code_intel_panel(self) -> None:
        """Show / restore the CodeIntelPanel (default side occupant)."""
        self._side_owner = "code_intel"
        side = self.query_one("#side")
        if self._code_intel_panel:
            if self._code_intel_panel not in list(side.children):
                side.mount(self._code_intel_panel)
            side.display = True
            side.styles.display = "block"

    def show_subagent_panel(self) -> None:
        """Switch side region to SubAgentPanel (called on spawn when not pinned)."""
        if self._side_pinned and self._side_owner == "code_intel":
            return  # pinned to code intel, ignore auto switch
        self._side_owner = "sub_agent"
        # hide code intel while sub is active (unless pinned the other way)
        if self._code_intel_panel and not self._side_pinned:
            try:
                self._code_intel_panel.display = False
            except Exception:
                pass

    def pin_side_panel(self, owner: str) -> None:
        """Pin the side region to 'code_intel' or 'sub_agent' (suspends auto-switch)."""
        if owner in ("code_intel", "sub_agent"):
            self._side_pinned = True
            self._side_owner = owner
            if owner == "code_intel":
                self.show_code_intel_panel()
            else:
                self.show_subagent_panel()

    def unpin_side_panel(self) -> None:
        """Release the pin; auto-switching resumes on next spawn/gather."""
        self._side_pinned = False
        # restore sensible default
        if not list(self.query(SubAgentPanel)):
            self.show_code_intel_panel()

    def restore_code_intel_panel(self) -> None:
        """Explicit restore used by gather paths and pin release."""
        self._side_owner = "code_intel"
        self._side_pinned = False
        self.show_code_intel_panel()

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
        yield HeaderBar(id="header")
        with Horizontal():
            yield TranscriptView(id="main")
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
        )
