"""S3.7 — `voss observe enable|disable|pause|resume|status|events|reconcile`."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness.cli import AGENT_COMMANDS, observe_group
from voss.harness.bos_ledger import BosEventLedger
from voss.harness.observe.models import CommandCompletedEvent, CommandStartedEvent
from voss.harness.observe.repository import repository_id
from voss.harness.observe.store import ObserveStore


def _run(args: list[str]):
    return CliRunner().invoke(observe_group, args)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return root


def _event(repo_root: Path, event_id: str, **overrides) -> CommandStartedEvent:
    fields = {
        "event_id": event_id,
        "command_id": f"cmd-{event_id}",
        "repository_id": repository_id(repo_root),
        "worktree_id": "wt-1",
        "adapter_id": "voss-pty",
        "repository_state_id": "head:abc:def",
        "source_ref": {"source": "adapter", "ref": "pane-1"},
        "payload": {"argv": ["ls"], "argv_text": "ls", "cwd": str(repo_root)},
    }
    fields.update(overrides)
    return CommandStartedEvent(**fields)


def _completed(repo_root: Path, event_id: str, **payload_overrides) -> CommandCompletedEvent:
    base = _event(repo_root, event_id).model_dump()
    base.pop("event_type")
    base["payload"] = {
        "argv": ["pnpm", "test"],
        "argv_text": "pnpm test",
        "cwd": str(repo_root),
        "exit_code": 1,
        "duration_ms": 1234,
    }
    base["payload"].update(payload_overrides)
    return CommandCompletedEvent(**base)


def test_registered() -> None:
    assert observe_group in AGENT_COMMANDS


def test_status_not_enrolled(repo: Path) -> None:
    res = _run(["status", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "not enrolled" in res.output


def test_status_not_a_repo(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    res = _run(["status", "--repo", str(tmp_path)])
    assert res.exit_code == 1
    assert "!" in res.output


def test_enable_status_disable_roundtrip(repo: Path) -> None:
    res = _run(["enable", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "enabled=yes" in res.output
    assert "capture=on" in res.output

    res = _run(["status", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "enabled=yes" in res.output
    assert "outbox: 0 pending, 0 delivered" in res.output

    res = _run(["disable", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "enabled=no" in res.output

    res = _run(["status", "--repo", str(repo)])
    assert "enabled=no" in res.output
    assert "not enrolled" not in res.output


def test_pause_resume(repo: Path) -> None:
    assert _run(["enable", "--repo", str(repo)]).exit_code == 0
    res = _run(["pause", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "paused=yes" in res.output
    res = _run(["resume", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "paused=no" in res.output


def test_enrollment_persists(repo: Path) -> None:
    assert _run(["enable", "--repo", str(repo)]).exit_code == 0
    from voss.harness.observe.enrollment import enrollment_path

    data = json.loads(enrollment_path().read_text())
    rid = repository_id(repo)
    assert data["repositories"][rid]["enabled"] is True


def test_events_empty(repo: Path) -> None:
    res = _run(["events", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "(no events)" in res.output


def test_events_lists_recent_with_tail(repo: Path) -> None:
    rid = repository_id(repo)
    with ObserveStore(rid) as store:
        for i in range(5):
            store.insert_event(_event(repo, f"ev-{i}"))

    res = _run(["events", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert res.output.count("[command.started]") == 5

    res = _run(["events", "--repo", str(repo), "--tail", "2"])
    assert res.exit_code == 0, res.output
    lines = [l for l in res.output.splitlines() if "[command.started]" in l]
    assert len(lines) == 2


def test_events_since_relative(repo: Path) -> None:
    rid = repository_id(repo)
    old = _event(repo, "ev-old").model_dump(mode="json")
    old["event_time"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(
        timespec="seconds"
    )
    with ObserveStore(rid) as store:
        store.insert_event(CommandStartedEvent(**old))
        store.insert_event(_event(repo, "ev-new"))

    res = _run(["events", "--repo", str(repo), "--since", "30m"])
    assert res.exit_code == 0, res.output
    assert res.output.count("[command.started]") == 1


def test_events_since_iso(repo: Path) -> None:
    rid = repository_id(repo)
    with ObserveStore(rid) as store:
        store.insert_event(_event(repo, "ev-1"))
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    res = _run(["events", "--repo", str(repo), "--since", future])
    assert res.exit_code == 0, res.output
    assert "(no events)" in res.output


def test_events_bad_since(repo: Path) -> None:
    res = _run(["events", "--repo", str(repo), "--since", "bogus"])
    assert res.exit_code != 0


def test_events_completed_shows_exit(repo: Path) -> None:
    rid = repository_id(repo)
    with ObserveStore(rid) as store:
        store.insert_event(_completed(repo, "ev-fail"))
    res = _run(["events", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "[command.completed]" in res.output
    assert "pnpm test" in res.output
    assert "exit=1" in res.output


def test_reconcile_replays_and_repeats_clean(repo: Path) -> None:
    rid = repository_id(repo)
    with ObserveStore(rid) as store:
        store.insert_event(_event(repo, "ev-a"))
        store.insert_event(_event(repo, "ev-b"))

    res = _run(["reconcile", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "replayed=2" in res.output
    assert "pending=0" in res.output
    assert "delivered=2" in res.output

    ledger_events = BosEventLedger(repo).read_events()
    assert [e["event_id"] for e in ledger_events] == ["ev-a", "ev-b"]

    res = _run(["reconcile", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "replayed=0" in res.output


def test_reconcile_without_store(repo: Path) -> None:
    res = _run(["reconcile", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "replayed=0" in res.output


def test_status_shows_backlog(repo: Path) -> None:
    assert _run(["enable", "--repo", str(repo)]).exit_code == 0
    rid = repository_id(repo)
    with ObserveStore(rid) as store:
        store.insert_event(_event(repo, "ev-a"))
        store.record_outbox_failure("ev-a", "boom")
    res = _run(["status", "--repo", str(repo)])
    assert res.exit_code == 0, res.output
    assert "1 pending, 0 delivered" in res.output
    assert "oldest=ev-a" in res.output
    assert "last_error=boom" in res.output
