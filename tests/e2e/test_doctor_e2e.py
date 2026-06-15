"""E2E for `voss doctor`.

The subprocess inherits the sandboxed XDG_STATE_HOME + HOME + CONFIG, so
diagnostic checks run against a clean state. Without valid creds, the
auth check is allowed to WARN (we don't assert exit 0); we only assert
that the command runs to completion and emits the expected rows.
"""
from __future__ import annotations

from .runner import CliRunner


REQUIRED_ROWS = (
    "python",
    "voss import",
    "git",
    "cwd writable",
    "config dirs",
    "project dirs",
)


def test_doctor_emits_all_expected_rows(cli_runner: CliRunner) -> None:
    r = cli_runner.run("doctor")
    # Exit code may be 0 or non-zero depending on whether the sandboxed
    # environment trips a FAIL row; assert we ran the command, not the verdict.
    assert r.returncode in (0, 1), r.output
    for row in REQUIRED_ROWS:
        assert row in r.stdout, f"doctor missing row {row!r}\nstdout:\n{r.stdout}"


def test_doctor_reports_cognition_state(cli_runner: CliRunner) -> None:
    r = cli_runner.run("doctor")
    # The old ad-hoc ".voss/ initialized" row was folded into the registry's
    # "cognition" check (diagnostics.check_cognition). Fixture project has
    # VOSS.md → cognition.initialized = True → detail reports "initialized".
    # Match the row by its label + detail together — a bare "cognition"
    # substring also appears in the sandbox tmp path (cwd writable row).
    line = next(
        (
            ln
            for ln in r.stdout.splitlines()
            if "cognition" in ln and "initialized" in ln.lower()
        ),
        "",
    )
    assert line, f"no cognition row reporting initialized state\n{r.stdout}"


def test_doctor_reports_legacy_session_count(cli_runner: CliRunner) -> None:
    r = cli_runner.run("doctor")
    assert "legacy sessions" in r.stdout, r.stdout
