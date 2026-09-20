"""
Top-level test fixtures shared across the whole suite.
Test isolation for leaked provider API keys: `voss.harness.auth` injects
"""
from __future__ import annotations

import os

import pytest

_LEAK_PRONE_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")


@pytest.fixture(autouse=True)
def _isolated_env(request, monkeypatch, tmp_path) -> None:
    saved = {k: os.environ.get(k) for k in _LEAK_PRONE_KEYS}
    if request.node.get_closest_marker("live") is None:
        for key in _LEAK_PRONE_KEYS:
            os.environ.pop(key, None)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        monkeypatch.setenv("VOSS_HOME", str(tmp_path / "voss"))
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


_ABORT_PRONE_NATIVE = frozenset({
    "torch", "onnxruntime", "sentence_transformers", "tokenizers",
})
_EXIT_DIAG_NATIVE = _ABORT_PRONE_NATIVE | frozenset({
    "grpc", "chromadb", "hnswlib", "transformers", "posthog",
    "opentelemetry", "watchdog", "textual", "litellm",
})


def _snapshot_sys_modules() -> list[str]:
    import sys

    try:
        return list(sys.modules)
    except RuntimeError:
        return []


def _abort_prone_native_loaded(names: list[str] | None = None) -> bool:
    loaded = set(names if names is not None else _snapshot_sys_modules())
    return bool(loaded & _ABORT_PRONE_NATIVE)


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int):
    snapshot_plugin = None
    original_save_svg_diffs = None
    try:
        import pytest_textual_snapshot as snapshot_mod
    except ImportError:
        snapshot_mod = None
    else:
        snapshot_plugin = snapshot_mod
        original_save_svg_diffs = snapshot_plugin.save_svg_diffs

        def save_svg_diffs_without_environment(diffs, report_session, num_snapshots_passing):
            for diff in diffs:
                diff.environment = {}
            return original_save_svg_diffs(
                diffs, report_session, num_snapshots_passing
            )

        snapshot_plugin.save_svg_diffs = save_svg_diffs_without_environment
    try:
        yield
    finally:
        if snapshot_plugin is not None and original_save_svg_diffs is not None:
            snapshot_plugin.save_svg_diffs = original_save_svg_diffs
        _report_exit_state()
        session.config._voss_exitstatus = exitstatus


def pytest_unconfigure(config: pytest.Config) -> None:
    """Skip C++ teardown when it would abort, without eating the report.

    Torch/onnxruntime abort in Py_Finalize ("terminate called without an active
    exception") once a background index build has loaded them, so the session
    ends with `os._exit` instead. This hook is the right place for it, not
    `pytest_sessionfinish`, in both process roles:

    On the main process, `pytest_unconfigure` runs after every reporter, so the
    failure summary, durations and coverage report have already been written.
    Exiting from `pytest_sessionfinish` truncated all three — a red CI run
    reported a bare exit 1 with the failing test named nowhere.

    On an xdist worker, the session-finish message is how the controller learns
    the worker is done. Exiting before it lands reads as a crashed node and the
    worker is respawned, re-importing torch each time. By `pytest_unconfigure`
    the message has been sent, so the worker may exit the same way — and it
    must, or it aborts in Py_Finalize like any other process here.
    """
    if not (os.environ.get("VOSS_EXIT_DIAG") or _abort_prone_native_loaded()):
        return
    import sys

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(getattr(config, "_voss_exitstatus", 0))


def _report_exit_state() -> None:
    if not os.environ.get("VOSS_EXIT_DIAG"):
        return
    import sys
    import threading

    lines = ["[exit-diag] live threads:"]
    for t in threading.enumerate():
        target = getattr(t, "_target", None)
        where = f"{getattr(target, '__module__', '?')}.{getattr(target, '__qualname__', '?')}" if target else "?"
        lines.append(f"  {t.name} daemon={t.daemon} alive={t.is_alive()} target={where}")
    names = _snapshot_sys_modules()
    native = [
        m for m in sorted(names)
        if m.split(".")[0] in _EXIT_DIAG_NATIVE and "." not in m
    ]
    lines.append(f"[exit-diag] native-ish top-level modules loaded: {native}")
    sys.stderr.write("\n".join(lines) + "\n")
    sys.stderr.flush()
