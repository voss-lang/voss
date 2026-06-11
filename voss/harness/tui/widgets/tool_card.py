"""ToolCard widget — one in-place mutable card per tool call (spec §3.4, R3).

One widget per call, keyed by `call_id` in TranscriptView. Layout: status
glyph + tool name + arg summary, result metric right-aligned.

    running:   ⠹ fs_edit voss/provider.py                       1.2s
    ok:        ⏺ fs_edit voss/provider.py                     +12 -48
               ⎿ ▸ 1 hunk · ctrl+d full diff
    error:     ⏺ shell_run pytest -x                            exit 1
               ⎿ ▾ FAILED tests/... (auto-expanded, first 10 lines)

States: running (spinner frames at 2 Hz, dim, live elapsed) → settled
(`TOOL_OK` in signal-good / signal-error). Output body is collapsed by
default for ok (expand: click, or `expand()/collapse()/toggle()` for the
R4 ctrl+o global and R6 nav mode); errors auto-expand the first 10 lines.
Edit-class tools render an inline mini-diff (up to 3 hunks, built from the
call args — the harness result string carries only a line-count delta) in
`$good`/`$error` foreground; `ctrl+d`'s full DiffModal stays on the
permissions bridge, untouched.
"""
from __future__ import annotations

import re
import time
from typing import Any

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.widget import Widget

from .. import glyphs


SPINNER_INTERVAL_S = 0.5  # 2 Hz — same cadence as WorkingIndicator
OUTPUT_TAIL_LINES = 20    # ok body: output tail length (spec §3.4)
ERROR_HEAD_LINES = 10     # error body: auto-expanded head length
MAX_DIFF_HUNKS = 3        # inline mini-diff hunk cap (spec §3.4)
HUNK_SIDE_LINES = 4       # per-hunk per-side line cap (full diff = ctrl+d)

# Tool classes for the right-aligned metric (spec §3.4). Derived from the
# registered toolset in voss/harness/tools.py.
_READ_TOOLS = frozenset({"fs_read", "fs_read_many"})
_EDIT_TOOLS = frozenset({"fs_edit", "fs_edit_many", "fs_write"})
_SHELL_TOOLS = frozenset({"shell_run", "shell_run_background"})
_MATCH_TOOLS = frozenset({"fs_grep", "fs_glob", "code_search", "find_references"})

_EXIT_RE = re.compile(r"^\[exit (-?\d+)\]")
_DELTA_RE = re.compile(r"\(([+-]\d+) lines")


def _short(value: Any, limit: int = 40) -> str:
    s = str(value)
    if len(s) > limit:
        return s[: limit - 1] + "…"
    return s


def _fmt_duration(seconds: float) -> str:
    if seconds >= 10:
        return f"{seconds:.0f}s"
    return f"{seconds:.1f}s"


def _metric(
    name: str,
    args: dict,
    summary: str,
    elapsed_s: float,
    output: str | None = None,
) -> str:
    """Right-aligned result metric per tool class; default is duration.

    read → `N lines`, edit/write → `+a -d`, shell → `exit N · 1.2s`,
    grep/glob → `N matches`. Parses what the result text / args carry;
    anything unparseable falls back to duration.
    """
    duration = _fmt_duration(elapsed_s)
    if name in _SHELL_TOOLS:
        # shell_run results start with `[exit N]` (first line == summary).
        m = _EXIT_RE.match(output or summary or "")
        if m:
            return f"exit {m.group(1)} · {duration}"
        return duration
    if name in _READ_TOOLS:
        if output:
            return f"{len(output.splitlines())} lines"
        return duration
    if name in _MATCH_TOOLS:
        if output:
            if output.startswith("<no matches>"):
                return "0 matches"
            n = len(output.splitlines())
            return f"{n} match{'es' if n != 1 else ''}"
        return duration
    if name in _EDIT_TOOLS:
        added, deleted = _edit_counts(name, args)
        if added is not None:
            return f"+{added} -{deleted}"
        # fs_edit result: `edited path (+N lines)` — net delta fallback.
        m = _DELTA_RE.search(summary or "")
        if m:
            return f"{m.group(1)} lines"
        return duration
    return duration


def _edit_counts(name: str, args: dict) -> tuple[int | None, int]:
    """Derive `+a -d` line counts from edit-class call args (None = unknown)."""
    if name == "fs_write" and "content" in args:
        return len(str(args["content"]).splitlines() or [""]), 0
    if name == "fs_edit" and args.get("old") is not None and "new" in args:
        return (
            len(str(args["new"]).splitlines() or [""]),
            len(str(args["old"]).splitlines() or [""]),
        )
    if name == "fs_edit_many" and isinstance(args.get("edits"), list):
        added = deleted = 0
        for e in args["edits"]:
            if not isinstance(e, dict):
                return None, 0
            added += len(str(e.get("new", "")).splitlines() or [""])
            deleted += len(str(e.get("old", "")).splitlines() or [""])
        return added, deleted
    return None, 0


def _diff_hunks(name: str, args: dict) -> list[tuple[list[str], list[str]]]:
    """(old_lines, new_lines) hunks for the inline mini-diff, from call args.

    The settled tool result string carries only a line-count delta (the
    DiffModal hunks live inside the tool function and never reach the
    renderer), so the mini-diff is rebuilt from the args the renderer
    already has. Anchor-based fs_edit calls (no `old`) yield no hunks.
    """
    if name == "fs_edit" and args.get("old") is not None and "new" in args:
        return [
            (
                str(args["old"]).splitlines() or [""],
                str(args["new"]).splitlines() or [""],
            )
        ]
    if name == "fs_edit_many" and isinstance(args.get("edits"), list):
        hunks = []
        for e in args["edits"][:MAX_DIFF_HUNKS]:
            if not isinstance(e, dict):
                continue
            hunks.append(
                (
                    str(e.get("old", "")).splitlines() or [""],
                    str(e.get("new", "")).splitlines() or [""],
                )
            )
        return hunks
    return []


class ToolCard(Widget):
    """In-place mutable tool-call card (spec §3.4) — running → ok/error.

    Subclasses Widget (not Static): Static's `expand`/`shrink` constructor
    attributes would shadow the spec'd `expand()` method, and Widget's
    `name` kwarg already forces `_tool_name` for the tool name.
    """

    DEFAULT_CLASSES = ""
    DEFAULT_CSS = """
    ToolCard {
        height: auto;
    }
    """

    def __init__(self, call_id: str, name: str, args: dict, **kw) -> None:
        self.call_id = call_id
        self._tool_name = name
        self._args = dict(args or {})
        self._state = "running"
        self._summary = ""
        self._output: str = ""
        self._started = time.monotonic()
        self._elapsed: float = 0.0
        self._expanded = False
        self._frame = 0
        self._spin_timer = None
        super().__init__(**kw)

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        if self._state != "running":
            return
        try:
            self._spin_timer = self.set_interval(
                SPINNER_INTERVAL_S, self._advance_frame
            )
        except Exception:  # noqa: BLE001 — set_interval needs a running app loop
            self._spin_timer = None

    def _advance_frame(self) -> None:
        self._frame += 1
        self.refresh()

    def _stop_spinner(self) -> None:
        if self._spin_timer is not None:
            try:
                self._spin_timer.stop()
            except Exception:  # noqa: BLE001
                pass
            self._spin_timer = None

    def settle(
        self,
        state: str,
        summary: str,
        *,
        output: str | None = None,
        elapsed_s: float | None = None,
    ) -> None:
        """Mutate the card in place to its settled state (ok / error).

        Any non-"ok" state renders as error (denied / unknown-tool settled
        calls arrive as "error"). Errors auto-expand the output body.
        """
        self._stop_spinner()
        self._state = "ok" if state == "ok" else "error"
        self._summary = summary or ""
        self._output = output if output is not None else (summary or "")
        self._elapsed = (
            elapsed_s if elapsed_s is not None else time.monotonic() - self._started
        )
        if self._state == "error":
            self._expanded = True
        self.refresh(layout=True)

    @property
    def state(self) -> str:
        return self._state

    @property
    def expanded(self) -> bool:
        return self._expanded

    # ------------------------------------------------------------------
    # expansion API (click now; R4 global ctrl+o + R6 nav mode reuse this)
    # ------------------------------------------------------------------

    def expand(self) -> None:
        if self._has_body():
            self._expanded = True
            self.refresh(layout=True)

    def collapse(self) -> None:
        self._expanded = False
        self.refresh(layout=True)

    def toggle(self) -> None:
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def on_click(self) -> None:
        self.toggle()

    # ------------------------------------------------------------------
    # rendering
    # ------------------------------------------------------------------

    def _has_body(self) -> bool:
        if self._state == "running":
            return False
        return bool(self._output.strip()) or bool(_diff_hunks(self._tool_name, self._args))

    def _arg_summary(self) -> str:
        return ", ".join(f"{k}={_short(v)}" for k, v in self._args.items())

    def _head(self) -> Table:
        grid = Table.grid(padding=(0, 1, 0, 0), expand=True)
        grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
        grid.add_column(justify="right", no_wrap=True)
        left = Text()
        if self._state == "running":
            frames = glyphs.SPINNER_FRAMES
            left.append(frames[self._frame % len(frames)], style="dim")
            left.append(f" {self._tool_name}", style="dim")
            right = Text(
                _fmt_duration(time.monotonic() - self._started), style="dim"
            )
        else:
            klass = "signal-good" if self._state == "ok" else "signal-error"
            left.append(glyphs.TOOL_OK, style=klass)
            left.append(f" {self._tool_name}")
            right = Text(
                _metric(
                    self._tool_name,
                    self._args,
                    self._summary,
                    self._elapsed,
                    self._output or None,
                ),
                style="dim",
            )
        argstr = self._arg_summary()
        if argstr:
            left.append(f" {argstr}", style="dim")
        grid.add_row(left, right)
        return grid

    def _body_lines(self) -> list[Text]:
        """Expanded body: full args, then mini-diff (edit) or output excerpt."""
        lines: list[Text] = []
        if self._args:
            full = ", ".join(f"{k}={_short(v, 120)}" for k, v in self._args.items())
            lines.append(Text(f"   {full}", style="dim"))
        hunks = _diff_hunks(self._tool_name, self._args)
        if hunks:
            for old_lines, new_lines in hunks:
                for ln in old_lines[:HUNK_SIDE_LINES]:
                    lines.append(Text(f"   - {ln}", style="signal-error"))
                if len(old_lines) > HUNK_SIDE_LINES:
                    lines.append(Text("   - …", style="signal-error"))
                for ln in new_lines[:HUNK_SIDE_LINES]:
                    lines.append(Text(f"   + {ln}", style="signal-good"))
                if len(new_lines) > HUNK_SIDE_LINES:
                    lines.append(Text("   + …", style="signal-good"))
            return lines
        out_lines = self._output.splitlines()
        if self._state == "error":
            excerpt = out_lines[:ERROR_HEAD_LINES]
            truncated = len(out_lines) > ERROR_HEAD_LINES
        else:
            excerpt = out_lines[-OUTPUT_TAIL_LINES:]
            truncated = len(out_lines) > OUTPUT_TAIL_LINES
        if truncated:
            lines.append(Text("   …", style="dim"))
        for ln in excerpt:
            lines.append(Text(f"   {ln}", style="dim"))
        return lines

    def _expander(self) -> Text:
        chevron = glyphs.CHEVRON_OPEN if self._expanded else glyphs.CHEVRON_CLOSED
        line = Text(style="dim")
        line.append(f"{glyphs.OUTPUT_ELBOW} {chevron}")
        if not self._expanded:
            hunks = _diff_hunks(self._tool_name, self._args)
            if hunks:
                n = len(hunks)
                line.append(
                    f" {n} hunk{'s' if n != 1 else ''} · ctrl+d full diff"
                )
            else:
                line.append(" …")
        return line

    def render(self):
        if self._state == "running" or not self._has_body():
            return self._head()
        parts: list[Any] = [self._head(), self._expander()]
        if self._expanded:
            parts.extend(self._body_lines())
        return Group(*parts)

    def plain_text(self) -> str:
        """Flatten the card to plain text (TranscriptView.plain_text + tests)."""
        if self._state == "running":
            frames = glyphs.SPINNER_FRAMES
            glyph = frames[self._frame % len(frames)]
            parts = [f"{glyph} {self._tool_name} {self._arg_summary()}".rstrip()]
        else:
            metric = _metric(
                self._tool_name, self._args, self._summary, self._elapsed,
                self._output or None,
            )
            head_line = f"{glyphs.TOOL_OK} {self._tool_name}"
            argstr = self._arg_summary()
            if argstr:
                head_line += f" {argstr}"
            parts = [f"{head_line}  {metric}"]
        if self._state != "running" and self._has_body():
            parts.append(self._expander().plain)
            if self._expanded:
                parts.extend(t.plain for t in self._body_lines())
        return "\n".join(parts)
