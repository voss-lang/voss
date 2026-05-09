"""Terminal renderer for the harness.

Goal: minimal, monospace, single accent. Glyphs: `▌ ❯ ⏵ ⚠`. No emoji.
TTY mode = rich Live updates. Non-TTY = plain text on stdout, traces on stderr.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


# ---------------------------------------------------------------------------
# Public protocol
# ---------------------------------------------------------------------------


class Renderer(Protocol):
    def banner(self, *, model: str, cwd: Path, git_status: str) -> None: ...
    def show_user(self, task: str) -> None: ...
    def show_thinking(self, label: str) -> None: ...
    def show_plan(self, plan: Any, *, cost_usd: float) -> None: ...
    def show_tool_call(self, name: str, args: dict, summary: str, state: str) -> None: ...
    def show_clarify(self, question: str, confidence: float) -> None: ...
    def show_final(self, text: str, *, confidence: float, cost_usd: float) -> None: ...
    def status(self, *, model: str, tokens: int, cost_usd: float, ctx_pct: float) -> None: ...


def make_renderer(*, json_mode: bool) -> Renderer:
    if json_mode or not sys.stdout.isatty():
        return JsonRenderer() if json_mode else PlainRenderer()
    return TtyRenderer()


# ---------------------------------------------------------------------------
# TTY (rich)
# ---------------------------------------------------------------------------


GLYPH_TOOL = "⏵"
GLYPH_WARN = "⚠"
GLYPH_PROMPT = "▌"


@dataclass
class TtyRenderer:
    console: Console = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.console is None:
            self.console = Console(highlight=False)

    def banner(self, *, model: str, cwd: Path, git_status: str) -> None:
        cwd_str = str(cwd).replace(str(Path.home()), "~", 1)
        body = Text()
        body.append("voss · agent\n", style="bold")
        body.append(f"{model} · {cwd_str} · {git_status}\n", style="dim")
        body.append("\nType a task, or /help.", style="dim")
        self.console.print(Panel(body, border_style="dim", padding=(1, 2)))

    def show_user(self, task: str) -> None:
        self.console.print(f"\n[bold]{GLYPH_PROMPT}[/bold] {task}\n")

    def show_thinking(self, label: str) -> None:
        self.console.print(f"[dim]  … {label}[/dim]")

    def show_plan(self, plan: Any, *, cost_usd: float) -> None:
        rationale = getattr(plan, "rationale", "")
        steps = getattr(plan, "steps", [])
        confidence = getattr(plan, "confidence", 0.0)
        self.console.print()
        self.console.print(f"  [bold]Plan[/bold] [dim](confidence {confidence:.2f})[/dim]")
        if rationale:
            self.console.print(f"  [dim]{rationale}[/dim]")
        for s in steps:
            why = f" — {s.why}" if s.why else ""
            self.console.print(f"  [dim]•[/dim] {s.name}{why}")
        self.console.print()

    def show_tool_call(self, name: str, args: dict, summary: str, state: str) -> None:
        glyph_color = {"ok": "green", "error": "red", "pending": "yellow"}.get(state, "dim")
        mark = {"ok": "✓", "error": "✗", "pending": "…"}[state]
        argstr = ", ".join(f"{k}={_short(v)}" for k, v in args.items())
        head = f"  [dim]{GLYPH_TOOL}[/dim] {name}([dim]{argstr}[/dim])"
        tail = f"[{glyph_color}]{mark}[/{glyph_color}] [dim]{summary}[/dim]"
        self.console.print(f"{head}  {tail}")

    def show_clarify(self, question: str, confidence: float) -> None:
        self.console.print(
            f"\n  [yellow]{GLYPH_WARN}[/yellow] confidence {confidence:.2f} — clarifying:"
        )
        self.console.print(f"  {question}\n")

    def show_final(self, text: str, *, confidence: float, cost_usd: float) -> None:
        self.console.print()
        self.console.print(text)
        self.console.print(
            f"\n  [dim]confidence {confidence:.2f} · ${cost_usd:.4f}[/dim]"
        )

    def status(self, *, model: str, tokens: int, cost_usd: float, ctx_pct: float) -> None:
        line = f"─ {model} · {tokens:,} tok · ${cost_usd:.3f} · ctx {ctx_pct:.0%} "
        line += "─" * max(0, self.console.width - len(line))
        self.console.print(f"[dim]{line}[/dim]")


def _short(v: Any, limit: int = 40) -> str:
    s = str(v)
    if len(s) > limit:
        return s[: limit - 1] + "…"
    return s


# ---------------------------------------------------------------------------
# Plain (non-TTY pipe target)
# ---------------------------------------------------------------------------


class PlainRenderer:
    def banner(self, *, model: str, cwd: Path, git_status: str) -> None:
        pass

    def show_user(self, task: str) -> None:
        print(f"> {task}", file=sys.stderr)

    def show_thinking(self, label: str) -> None:
        print(f"... {label}", file=sys.stderr)

    def show_plan(self, plan: Any, *, cost_usd: float) -> None:
        steps = getattr(plan, "steps", [])
        conf = getattr(plan, "confidence", 0.0)
        print(f"plan: {len(steps)} steps, conf={conf:.2f}", file=sys.stderr)

    def show_tool_call(self, name: str, args: dict, summary: str, state: str) -> None:
        print(f"[{state}] {name}({args}) -> {summary}", file=sys.stderr)

    def show_clarify(self, question: str, confidence: float) -> None:
        print(question)

    def show_final(self, text: str, *, confidence: float, cost_usd: float) -> None:
        print(text)

    def status(self, *, model: str, tokens: int, cost_usd: float, ctx_pct: float) -> None:
        pass


# ---------------------------------------------------------------------------
# JSON (NDJSON, one event per line on stdout)
# ---------------------------------------------------------------------------


class JsonRenderer:
    V = 1

    def _emit(self, **kw: Any) -> None:
        kw.setdefault("v", self.V)
        sys.stdout.write(json.dumps(kw, default=str) + "\n")
        sys.stdout.flush()

    def banner(self, *, model: str, cwd: Path, git_status: str) -> None:
        self._emit(type="banner", model=model, cwd=str(cwd), git=git_status)

    def show_user(self, task: str) -> None:
        self._emit(type="user", task=task)

    def show_thinking(self, label: str) -> None:
        self._emit(type="thinking", label=label)

    def show_plan(self, plan: Any, *, cost_usd: float) -> None:
        self._emit(
            type="plan",
            confidence=getattr(plan, "confidence", 0.0),
            steps=[{"name": s.name, "args": s.args} for s in getattr(plan, "steps", [])],
            cost_usd=cost_usd,
        )

    def show_tool_call(self, name: str, args: dict, summary: str, state: str) -> None:
        self._emit(type="tool", name=name, args=args, summary=summary, state=state)

    def show_clarify(self, question: str, confidence: float) -> None:
        self._emit(type="clarify", question=question, confidence=confidence)

    def show_final(self, text: str, *, confidence: float, cost_usd: float) -> None:
        self._emit(type="final", text=text, confidence=confidence, cost_usd=cost_usd)

    def status(self, *, model: str, tokens: int, cost_usd: float, ctx_pct: float) -> None:
        self._emit(type="status", model=model, tokens=tokens, cost_usd=cost_usd, ctx_pct=ctx_pct)
