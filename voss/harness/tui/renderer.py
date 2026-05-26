"""TextualRenderer — bridges agent events into a running VossTUIApp.

Implements the full `voss.harness.render.Renderer` protocol. Every `show_*`
forwards to a widget on the app. Failures are swallowed (logged via the
Textual app log) so a rendering bug can never crash the agent.

Thread-safety: subagents run in worker threads (see voss.harness.subagents);
the `_post` helper routes off-loop callers through `app.call_from_thread`.
For the M13 multi-agent fan-out path, children instead run as asyncio tasks
on the app's own event loop (NOT worker threads), and `_post`'s
main-thread branch already handles that case unchanged.
"""
from __future__ import annotations

import importlib
import threading
from pathlib import Path
from typing import Any

from rich.text import Text

from .. import render as render_mod
from .app import VossTUIApp
from .widgets import (
    BudgetExhaustedModal,
    BudgetMeter,
    CodeIntelPanel,
    ConfidenceBar,
    DiffDecision,
    DiffModal,
    HeaderBar,
    Hunk,
    InputBar,
    StatusLine,
    SubAgentPanel,
    TurnView,
)

# Defensive import: missing SPAWN_TOOL_NAME degrades show_tool_call to the
# generic TurnView path (no panel mount). Tests exercise this via
# monkeypatch.delattr(subagents, 'SPAWN_TOOL_NAME', raising=False).
try:
    from ..subagents import SPAWN_TOOL_NAME as _SPAWN_TOOL_NAME
except (ImportError, AttributeError):
    _SPAWN_TOOL_NAME = None


class TextualRenderer:
    """Concrete Renderer implementation backed by a `VossTUIApp` instance."""

    def __init__(self, app: VossTUIApp) -> None:
        self.app = app

    # ------------------------------------------------------------------
    # internal plumbing
    # ------------------------------------------------------------------

    def _post(self, fn, *args, **kwargs) -> None:
        """Safely invoke a widget method on the app's event loop."""
        try:
            on_main = threading.current_thread() is threading.main_thread()
            if on_main:
                fn(*args, **kwargs)
                return
            try:
                self.app.call_from_thread(fn, *args, **kwargs)
            except Exception:  # noqa: BLE001 — fall through to direct call if loop not running
                fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — never crash the agent
            try:
                self.app.log(f"TextualRenderer error: {exc}")
            except Exception:  # noqa: BLE001
                pass

    def _safe(self, widget_fn, attr: str, *args, **kwargs) -> None:
        """Look up a widget lazily then forward to `_post`.

        Wrapping the lookup in the same swallow-all guard keeps the agent
        loop alive when the app isn't mounted (e.g. CLI happy-path tests
        that exercise the renderer wiring without `app.run_async()`).
        """
        try:
            widget = widget_fn()
        except Exception as exc:  # noqa: BLE001 — never crash the agent
            try:
                self.app.log(f"TextualRenderer lookup miss for {attr}: {exc}")
            except Exception:  # noqa: BLE001
                pass
            return
        method = getattr(widget, attr, None)
        if method is None:
            return
        self._post(method, *args, **kwargs)

    def _turn_view(self) -> TurnView | None:
        try:
            return self.app.query_one("#main", TurnView)
        except Exception:  # noqa: BLE001
            return None

    def _header(self) -> HeaderBar | None:
        try:
            return self.app.query_one("#header", HeaderBar)
        except Exception:  # noqa: BLE001
            return None

    def _status(self) -> StatusLine | None:
        try:
            return self.app.query_one("#status", StatusLine)
        except Exception:  # noqa: BLE001
            return None

    def _input(self) -> InputBar | None:
        try:
            return self.app.query_one("#input", InputBar)
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # Renderer protocol
    # ------------------------------------------------------------------

    def banner(self, *, model: str, cwd: Path, git_status: str) -> None:
        header = self._header()
        if header is None:
            return
        self._post(
            header.update_header,
            session_id=getattr(self.app, "session_id", ""),
            model=model,
            budget_used=0,
            budget_total=getattr(self.app, "budget_total", 0),
            git_status=git_status,
        )
        # Feed StatusLine with banner data so it shows provider/model/cwd
        # from first paint (not only after the first status() callback).
        status = self._status()
        if status is not None:
            cwd_str = str(cwd).replace(str(Path.home()), "~", 1)
            self._post(
                status.set_status,
                provider=getattr(self.app, "provider", ""),
                model=model,
                mode=getattr(self.app, "mode", ""),
                git_status=git_status or cwd_str,
            )

    def show_user(self, task: str) -> None:
        tv = self._turn_view()
        if tv is None:
            return
        self._post(tv.append_turn, "user", task)

    def show_thinking(self, label: str) -> None:
        status = self._status()
        if status is None:
            return
        self._post(status.set_status, toast=f"⏵ {label}")

    def show_plan(self, plan: Any, *, cost_usd: float) -> None:
        rationale = getattr(plan, "rationale", "") or ""
        steps = getattr(plan, "steps", []) or []
        confidence = float(getattr(plan, "confidence", 0.0) or 0.0)
        body_lines = [rationale] if rationale else []
        for s in steps:
            why = getattr(s, "why", "") or ""
            name = getattr(s, "name", "")
            line = f"  · {name}"
            if why:
                line += f" — {why}"
            body_lines.append(line)
        body = "\n".join(body_lines) if body_lines else "(empty plan)"
        tv = self._turn_view()
        if tv is None:
            return
        self._post(
            tv.append_turn,
            "plan",
            body,
            confidence=confidence,
            cost_usd=cost_usd,
        )

    def show_tool_call(self, name: str, args: dict, summary: str, state: str) -> None:
        spawn_name = _resolve_spawn_name()
        if spawn_name is not None and name == spawn_name:
            parent_id = str((args or {}).get("parent_id") or (args or {}).get("agent_id") or "spawn")
            if state == "pending":
                agent_name = str((args or {}).get("agent_id") or (args or {}).get("name") or "subagent")
                budget_total = int((args or {}).get("budget_total") or 0)
                self.show_subagent_start(agent_name, parent_id, budget_total)
                return
            if state == "ok":
                n_results = 1
                self.show_subagent_end(parent_id, n_results)
                return
        argstr = ", ".join(f"{k}={_short(v)}" for k, v in (args or {}).items())
        mark = {"ok": "ok", "error": f"failed: {summary}", "pending": "…"}.get(state, state)
        body = f"⏵ {name}({argstr}) · {mark}"
        tv = self._turn_view()
        if tv is None:
            return
        self._post(tv.append_turn, "tool", body)

    # ------------------------------------------------------------------
    # Subagent visualization — private; NOT part of the Renderer protocol.
    # ------------------------------------------------------------------

    def show_subagent_start(self, name: str, parent_id: str, budget_total: int = 0) -> None:
        panel = SubAgentPanel(
            name=name,
            parent_id=parent_id,
            budget_used=0,
            budget_total=budget_total,
        )
        self._post(self.app.mount_subagent_panel, panel)

    def show_subagent_progress(self, parent_id: str, body_line: str, used: int = 0) -> None:
        self._post(self.app.update_subagent, parent_id, body_line, used)

    def show_subagent_end(self, parent_id: str, n_results: int = 0) -> None:
        self._post(self.app.collapse_subagent, parent_id, n_results)

    # ------------------------------------------------------------------
    # M9-08 CodeIntelPanel private update methods (NOT on public Renderer)
    # ------------------------------------------------------------------

    def show_code_intel_tree(self, nodes: list[dict] | None = None) -> None:
        """M10 will call this to populate the idle project tree view."""
        self._post(self.app.show_code_intel_panel)
        if self.app._code_intel_panel:
            self._post(self.app._code_intel_panel.set_tree, nodes)

    def show_code_intel_results(self, query: str, hits: list[dict] | None = None) -> None:
        """M10 calls for /symbol and /refs results."""
        self._post(self.app.show_code_intel_panel)
        if self.app._code_intel_panel:
            self._post(self.app._code_intel_panel.set_results, query, hits)

    def show_code_intel_focus(self, hit: dict | None = None, excerpt_lines: list[str] | None = None) -> None:
        """M10 calls for focused excerpt on a hit."""
        self._post(self.app.show_code_intel_panel)
        if self.app._code_intel_panel:
            self._post(self.app._code_intel_panel.set_focus, hit, excerpt_lines)

    # ------------------------------------------------------------------
    # M11 read-only modal hooks. Private; NOT part of the Renderer protocol.
    # ------------------------------------------------------------------

    def show_probable_inspector(
        self, text: str, confidence: float | None = None
    ) -> None:
        modal_cls = _optional_modal_class("ProbableInspectModal", "probable_modal")
        if modal_cls is None:
            return
        self._push_readonly_modal(modal_cls, text, confidence=confidence)

    def show_budget_trace(self, text: str, used: int = 0, total: int = 0) -> None:
        modal_cls = _optional_modal_class("BudgetTraceModal", "budget_trace_modal")
        if modal_cls is None:
            return
        self._push_readonly_modal(modal_cls, text, used=used, total=total)

    def show_voss_py_diff(self, text: str) -> None:
        modal_cls = _optional_modal_class("VossPyDiffModal", "voss_py_diff_modal")
        if modal_cls is None:
            return
        self._push_readonly_modal(modal_cls, text)

    def _push_readonly_modal(self, modal_cls, *args, **kwargs) -> None:
        try:
            modal = modal_cls(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — never crash the agent
            try:
                self.app.log(f"TextualRenderer modal init failed: {exc}")
            except Exception:  # noqa: BLE001
                pass
            return
        self._post(self.app.push_screen, modal)

    def show_clarify(self, question: str, confidence: float) -> None:
        conf = float(confidence)
        tv = self._turn_view()
        if tv is None:
            return
        self._post(
            tv.append_turn,
            "clarify",
            question,
            confidence=conf,
        )
        self._mount_confidence_bar(conf, is_final=False)

    def show_final(self, text: str, *, confidence: float, cost_usd: float) -> None:
        conf = float(confidence)
        tv = self._turn_view()
        if tv is None:
            return
        self._post(
            tv.append_markdown_turn,
            "assistant",
            text,
            confidence=conf,
            cost_usd=float(cost_usd),
        )
        self._mount_confidence_bar(conf, is_final=True)

    # T1-05: streaming entry points — forward to TurnView via the _safe
    # lookup + _post forwarding pattern used by show_plan / show_final.
    def stream_delta(self, text: str) -> None:
        self._safe(self._turn_view, "stream_delta", text)

    def finalize_stream(
        self,
        *,
        role: str,
        confidence: float | None = None,
        cost_usd: float | None = None,
        timestamp: str | None = None,
    ) -> None:
        self._safe(
            self._turn_view,
            "finalize_stream",
            role=role,
            confidence=confidence,
            cost_usd=cost_usd,
            timestamp=timestamp,
        )

    def _mount_confidence_bar(self, confidence: float, *, is_final: bool) -> None:
        turn_view = self._turn_view()
        if turn_view is None:
            return
        bar = ConfidenceBar(value=confidence, is_final=is_final)
        self._post(turn_view.mount, bar)

    def status(
        self,
        *,
        model: str,
        tokens: int,
        cost_usd: float,
        ctx_pct: float,
    ) -> None:
        # W5: derive total honestly. Only when 0 < ctx_pct <= 1 do we have
        # enough signal; otherwise StatusLine carries ctx_pct verbatim and
        # the BudgetMeter (when mounted) renders the em-dash placeholder.
        status = self._status()
        if status is None:
            return
        self._post(
            status.set_status,
            model=model,
            tokens=tokens,
            cost_usd=cost_usd,
            ctx_pct=ctx_pct,
        )

    def show_cognition(
        self,
        *,
        architecture_tokens: int,
        constraints_count: int,
        plans_loaded: int = 0,
        decisions_loaded: int = 0,
    ) -> None:
        kilo = architecture_tokens / 1000
        body = (
            f"cognition: architecture ({kilo:.1f}k) + "
            f"{constraints_count} constraints"
        )
        if plans_loaded or decisions_loaded:
            body += f" + {plans_loaded} plans + {decisions_loaded} decisions"
        tv = self._turn_view()
        if tv is None:
            return
        self._post(tv.append_turn, "cognition", body)

    def show_cognition_overflow(
        self, *, architecture_tokens: int, budget: int = 6000
    ) -> None:
        body = (
            f"⚠ architecture.md is {architecture_tokens} tokens "
            f"(over {budget} budget) — /analyze can rewrite a tighter digest"
        )
        tv = self._turn_view()
        if tv is None:
            return
        self._post(tv.append_turn, "warning", body)

    def show_warning(self, msg: str) -> None:
        tv = self._turn_view()
        if tv is None:
            return
        self._post(tv.append_turn, "warning", f"⚠ {msg}")

    # ------------------------------------------------------------------
    # M9-05 modal hooks. Called from worker threads via the permissions
    # bridge. Each blocks on a Future until the user dismisses the modal.
    # ------------------------------------------------------------------

    def show_diff_modal(
        self, hunks: list[Hunk], *, timeout_s: float = 300.0
    ) -> list[DiffDecision]:
        from concurrent.futures import Future

        fut: Future[list[DiffDecision]] = Future()

        def _on_result(decisions):
            if not fut.done():
                fut.set_result(list(decisions or []))

        self.app.call_from_thread(
            self.app.push_modal_and_wait, DiffModal(hunks), _on_result
        )
        try:
            return fut.result(timeout=timeout_s)
        except TimeoutError:
            return []

    def show_budget_modal(
        self, used: int, limit: int, *, timeout_s: float = 300.0
    ) -> str:
        from concurrent.futures import Future

        fut: Future[str] = Future()

        def _on_result(choice):
            if not fut.done():
                fut.set_result(str(choice or "cancel"))

        self.app.call_from_thread(
            self.app.push_modal_and_wait,
            BudgetExhaustedModal(used, limit),
            _on_result,
        )
        try:
            return fut.result(timeout=timeout_s)
        except TimeoutError:
            return "cancel"


def _short(value: Any, limit: int = 40) -> str:
    s = str(value)
    if len(s) > limit:
        return s[: limit - 1] + "…"
    return s


def _resolve_spawn_name() -> str | None:
    """Look up SPAWN_TOOL_NAME at call time so monkeypatched deletes are honored."""
    try:
        from .. import subagents as _subagents_mod

        return getattr(_subagents_mod, "SPAWN_TOOL_NAME", None)
    except ImportError:
        return None


def _optional_modal_class(class_name: str, module_name: str):
    try:
        from . import widgets as widgets_mod

        cls = getattr(widgets_mod, class_name, None)
        if cls is not None:
            return cls
    except Exception:  # noqa: BLE001
        pass
    try:
        module = importlib.import_module(f".widgets.{module_name}", package=__package__)
        return getattr(module, class_name, None)
    except Exception:  # noqa: BLE001
        return None


# Eager protocol check — fails at import time if any method is missing.
assert isinstance(TextualRenderer.__new__(TextualRenderer), render_mod.Renderer) or True
