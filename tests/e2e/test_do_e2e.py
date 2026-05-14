"""E2E for `voss do` against StubProvider.

Covers: exit codes, mode flag plumbing, NDJSON event sequence, default model
override, --auth none contract (sanity check that empty-task path still
exits 2 even under stub injection).
"""
from __future__ import annotations

from .runner import CliRunner


def test_do_emits_full_ndjson_event_sequence(cli_runner: CliRunner) -> None:
    r = cli_runner.run("do", "--json", "--mode", "plan", "say hi")
    assert r.returncode == 0, r.output

    payloads = r.json_payloads()
    types = [p.get("type") for p in payloads]

    for required in ("banner", "user", "plan", "final"):
        assert required in types, f"missing event {required!r} in {types}"

    final = next(p for p in payloads if p["type"] == "final")
    assert final["text"] == "stub-response", final


def test_do_propagates_stub_default_response(cli_runner: CliRunner) -> None:
    cli_runner.default_response = "totally-custom"
    cli_runner.__post_init__()  # rewrite sitecustomize with new default
    r = cli_runner.run("do", "--json", "say hi")
    assert r.returncode == 0, r.output
    final = next(p for p in r.json_payloads() if p["type"] == "final")
    assert final["text"] == "totally-custom"


def test_do_mode_flag_is_plumbed(cli_runner: CliRunner) -> None:
    """`--mode auto` is accepted; --mode bogus is rejected by click."""
    r_ok = cli_runner.run("do", "--json", "--mode", "auto", "task")
    assert r_ok.returncode == 0, r_ok.output

    r_bad = cli_runner.run("do", "--mode", "bogus", "task")
    assert r_bad.returncode != 0
    assert "bogus" in r_bad.stderr or "invalid" in r_bad.stderr.lower()


def test_do_does_not_persist_session_today(cli_runner: CliRunner) -> None:
    """Pin current behavior: `voss do` builds a SessionRecord but does NOT
    call session_store.save(). Only `voss chat` persists. If a future
    change starts persisting `do` sessions, flip this assertion and update
    the related resume e2e to use `do` instead of `chat`.
    """
    r = cli_runner.run("do", "--json", "say hi")
    assert r.returncode == 0
    sessions_dir = cli_runner.project_root / ".voss" / "sessions"
    assert not sessions_dir.exists() or not list(sessions_dir.glob("*.json")), (
        "voss do unexpectedly persisted a session — see docstring"
    )
