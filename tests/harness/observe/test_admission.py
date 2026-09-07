from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.observe import admission
from voss.harness.observe.admission import (
    Admission,
    admit,
    error_signature,
    fingerprint,
    is_expected_nonzero,
    normalize_argv,
)
from voss.harness.observe.admission import test_runner as find_test_runner
from voss.harness.observe.models import (
    CommandCompletedEvent,
    CommandFailedEvent,
    CommandStartedEvent,
    TestFailedEvent,
)
from voss.harness.observe.store import ObserveStore


def _completed(event_id: str, argv: list[str], exit_code: int = 1) -> CommandCompletedEvent:
    return CommandCompletedEvent(
        event_id=event_id,
        command_id=f"cmd-{event_id}",
        repository_id="repo-1",
        worktree_id="wt-1",
        adapter_id="voss-pty",
        repository_state_id="head:abc:def",
        source_ref={"source": "adapter", "ref": "pane-1"},
        payload={
            "argv": argv,
            "argv_text": " ".join(argv),
            "cwd": "/repo",
            "exit_code": exit_code,
            "duration_ms": 100,
        },
    )


@pytest.fixture
def store(tmp_path: Path):
    store = ObserveStore("repo-1", state_dir=tmp_path)
    yield store
    store.close()


def test_test_runner_vocabulary() -> None:
    for argv in (
        ["pnpm", "test"],
        ["pnpm", "test", "--", "--watch=false"],
        ["npm", "test"],
        ["pytest"],
        ["pytest", "-x", "tests/"],
        ["cargo", "test"],
        ["vitest"],
        ["vitest", "run"],
        ["jest"],
        ["go", "test", "./..."],
        ["/usr/local/bin/pytest", "-q"],
    ):
        assert find_test_runner(list(argv)) is not None, argv
    for argv in (["pnpm", "build"], ["cargo", "build"], ["grep", "x"], []):
        assert find_test_runner(list(argv)) is None, argv


def test_expected_nonzero_vocabulary() -> None:
    assert is_expected_nonzero(["grep", "nothing_here", "file"])
    assert is_expected_nonzero(["test", "-e", "/tmp/x"])
    assert is_expected_nonzero(["diff", "a", "b"])
    assert is_expected_nonzero(["git", "diff", "--exit-code"])
    assert not is_expected_nonzero(["git", "diff"])
    assert not is_expected_nonzero(["pnpm", "test"])
    assert not is_expected_nonzero([])


def test_error_signature_normalizes_digits_and_whitespace() -> None:
    a = error_signature("AssertionError at line 42\n  failed  3 times")
    b = error_signature("AssertionError at line 87\n  failed 9 times")
    assert a == b
    assert error_signature("everything is fine") != error_signature("other output")


def test_fingerprint_inputs() -> None:
    kwargs = {
        "repository_id": "r",
        "worktree_id": "w",
        "argv": ["pnpm", "test"],
        "error_sig": "sig",
        "repository_state_id": "state",
    }
    assert fingerprint(**kwargs) == fingerprint(**kwargs)
    assert fingerprint(**{**kwargs, "repository_state_id": "changed"}) != fingerprint(**kwargs)
    assert normalize_argv(["/usr/bin/pytest", "-q"]) == '["pytest", "-q"]'


def test_failing_test_command_derives_test_failed_and_queues(
    store: ObserveStore,
) -> None:
    result = admit(store, _completed("ev-1", ["pnpm", "test"]), error_text="1 failed")
    assert result.decision == "queue"
    assert result.reason == "queued"
    assert result.policy_version == "observe-admission-v1"
    derived = result.derived_event
    assert isinstance(derived, TestFailedEvent)
    assert derived.caused_by == "ev-1"
    assert derived.payload.runner == "pnpm test"
    assert derived.payload.exit_code == 1
    assert store.has_event("ev-1")
    assert store.has_event(derived.event_id)
    assert store.count_pending("wt-1") == 1
    pending = store.pending_investigations("wt-1")
    assert pending[0]["trigger_event_id"] == derived.event_id
    source_admission = store.admissions(event_id="ev-1")
    assert [(a["decision"], a["reason"]) for a in source_admission] == [
        ("record_only", "derived")
    ]


def test_non_test_failure_derives_command_failed(store: ObserveStore) -> None:
    result = admit(store, _completed("ev-1", ["make", "build"]))
    assert result.decision == "queue"
    assert isinstance(result.derived_event, CommandFailedEvent)
    assert not isinstance(result.derived_event, TestFailedEvent)


def test_repeat_within_cooldown_suppressed(store: ObserveStore) -> None:
    first = admit(store, _completed("ev-1", ["pytest"]), error_text="boom", now=1000.0)
    assert first.decision == "queue"
    second = admit(store, _completed("ev-2", ["pytest"]), error_text="boom", now=1030.0)
    assert second.decision == "suppress"
    assert second.reason == "cooldown"
    decisions = {(a["decision"], a["reason"]) for a in store.admissions()}
    assert ("queue", "queued") in decisions
    assert ("suppress", "cooldown") in decisions
    assert store.count_pending("wt-1") == 1


def test_same_event_posted_twice_is_duplicate(store: ObserveStore) -> None:
    event = _completed("ev-1", ["pytest"])
    first = admit(store, event)
    assert first.decision == "queue"
    second = admit(store, event)
    assert second.decision == "record_only"
    assert second.reason == "duplicate"
    assert len(store.list_events()) == 2  # the completed event + the derived failure


def test_expected_nonzero_recorded_only(store: ObserveStore) -> None:
    result = admit(store, _completed("ev-1", ["grep", "nothing_here", "."]))
    assert result.decision == "record_only"
    assert result.reason == "expected_nonzero"
    assert result.derived_event is None
    assert store.count_pending("wt-1") == 0
    assert store.has_event("ev-1")


def test_coalesce_after_cooldown_while_pending(store: ObserveStore) -> None:
    first = admit(store, _completed("ev-1", ["pytest"]), now=1000.0)
    assert first.decision == "queue"
    later = admit(store, _completed("ev-2", ["pytest"]), now=1000.0 + 61.0)
    assert later.decision == "suppress"
    assert later.reason == "coalesced"
    assert later.investigation_id == first.investigation_id
    assert store.count_pending("wt-1") == 1


def test_queue_full_suppresses(store: ObserveStore) -> None:
    for i in range(admission.MAX_PENDING_PER_WORKTREE):
        result = admit(store, _completed(f"ev-{i}", ["pytest", f"test_{i}.py"]))
        assert result.decision == "queue"
    overflow = admit(store, _completed("ev-overflow", ["pytest", "test_overflow.py"]))
    assert overflow.decision == "suppress"
    assert overflow.reason == "queue_full"
    assert store.count_pending("wt-1") == admission.MAX_PENDING_PER_WORKTREE


def test_queue_is_per_worktree(store: ObserveStore) -> None:
    for i in range(admission.MAX_PENDING_PER_WORKTREE):
        admit(store, _completed(f"ev-{i}", ["pytest", f"test_{i}.py"]))
    other = _completed("ev-other", ["pytest", "test_other.py"])
    other = other.model_copy(update={"worktree_id": "wt-2"})
    result = admit(store, other)
    assert result.decision == "queue"


def test_zero_exit_completed_is_observed(store: ObserveStore) -> None:
    result = admit(store, _completed("ev-1", ["pnpm", "test"], exit_code=0))
    assert result.decision == "record_only"
    assert result.reason == "observed"
    assert store.count_pending("wt-1") == 0


def test_started_event_is_observed(store: ObserveStore) -> None:
    started = CommandStartedEvent(
        event_id="ev-0",
        command_id="cmd-0",
        repository_id="repo-1",
        worktree_id="wt-1",
        adapter_id="voss-pty",
        repository_state_id="head:abc:def",
        source_ref={"source": "adapter", "ref": "pane-1"},
        payload={"argv": ["ls"], "argv_text": "ls", "cwd": "/repo"},
    )
    result = admit(store, started)
    assert (result.decision, result.reason) == ("record_only", "observed")


def test_direct_failure_post_admits(store: ObserveStore) -> None:
    failure = CommandFailedEvent(
        event_id="ev-f",
        command_id="cmd-f",
        repository_id="repo-1",
        worktree_id="wt-1",
        adapter_id="voss-pty",
        repository_state_id="head:abc:def",
        source_ref={"source": "adapter", "ref": "pane-1"},
        caused_by="ev-1",
        payload={
            "argv": ["make", "build"],
            "argv_text": "make build",
            "cwd": "/repo",
            "exit_code": 2,
        },
    )
    result = admit(store, failure)
    assert result.decision == "queue"
    assert result.event_id == "ev-f"


def test_admission_result_shape(store: ObserveStore) -> None:
    result = admit(store, _completed("ev-1", ["pytest"]))
    assert isinstance(result, Admission)
    assert result.investigation_id
    assert len(result.fingerprint) == 64
