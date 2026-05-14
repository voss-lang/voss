"""RecorderBridge — pure read-only consumer of RunRecorder.

Translates new delta entries on each `flush()` into widget mutator calls on
the bound app. Does NOT mutate RunRecorder or add new emit points anywhere.
M9-04 contract: zero changes to voss/harness/recorder.py or voss_runtime/*.
"""
from __future__ import annotations

from typing import Any

from voss.harness.recorder import RunRecorder


class RecorderBridge:
    """Bind a RunRecorder + a VossTUIApp and surface incremental updates."""

    def __init__(self, recorder: RunRecorder, app: Any) -> None:
        self.recorder = recorder
        self.app = app
        self._seen: dict[str, int] = {
            "inspected": 0,
            "changed": 0,
            "validation": 0,
            "failures": 0,
        }

    def flush(self) -> None:
        """Emit widget calls for entries observed since the previous flush."""
        inspected = list(self.recorder.inspected)
        if len(inspected) > self._seen["inspected"]:
            new_paths = inspected[self._seen["inspected"]:]
            self._call("update_inspected", new_paths)
            self._seen["inspected"] = len(inspected)

        changed = list(self.recorder.changed)
        if len(changed) > self._seen["changed"]:
            new_paths = changed[self._seen["changed"]:]
            self._call("update_changed", new_paths)
            self._seen["changed"] = len(changed)

        validation = list(self.recorder.validation)
        if len(validation) > self._seen["validation"]:
            for entry in validation[self._seen["validation"]:]:
                cmd = str(entry.get("cmd", ""))
                summary = str(entry.get("summary", ""))
                state = "ok" if int(entry.get("exit", 0)) == 0 else "error"
                self._call("append_tool_line", f"{cmd} · {summary}", state=state)
            self._seen["validation"] = len(validation)

        failures = list(self.recorder.failures)
        if len(failures) > self._seen["failures"]:
            for entry in failures[self._seen["failures"]:]:
                tool = str(entry.get("tool", ""))
                err = str(entry.get("error", ""))
                self._call("append_tool_line", f"{tool} · {err}", state="error")
            self._seen["failures"] = len(failures)

    def _call(self, method_name: str, *args, **kwargs) -> None:
        fn = getattr(self.app, method_name, None)
        if fn is None:
            return
        try:
            fn(*args, **kwargs)
        except Exception:  # noqa: BLE001 — bridge must never crash the agent
            pass
