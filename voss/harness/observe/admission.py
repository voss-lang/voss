"""Deterministic admission for observe events (OBS-04).

Outcome is `record_only | suppress | queue | reject` with a reason code and
policy version. A `command.completed` with a nonzero exit derives exactly one
failure event — `test.failed` when argv matches a known test runner, else
`command.failed` — linked via `caused_by`; only the derived event is ever
queued for investigation.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import PurePath

from voss.harness.observe.models import (
    CommandCompletedEvent,
    CommandFailedEvent,
    CommandFailedPayload,
    ObserveEvent,
    TestFailedEvent,
    TestFailedPayload,
)
from voss.harness.observe.store import ObserveStore

POLICY_VERSION = "observe-admission-v1"
COOLDOWN_SECONDS = 60.0
MAX_PENDING_PER_WORKTREE = 10

RECORD_ONLY = "record_only"
SUPPRESS = "suppress"
QUEUE = "queue"
REJECT = "reject"

_TEST_RUNNER_BASENAMES = frozenset({"pytest", "vitest", "jest"})
_TEST_RUNNER_SUBCOMMANDS = frozenset({"pnpm", "npm", "yarn", "cargo", "go"})

_ERROR_LINE = re.compile(r"error|fail|assert|exception|traceback|panic", re.IGNORECASE)
_DIGITS = re.compile(r"\d+")
_WHITESPACE = re.compile(r"\s+")


@dataclass
class Admission:
    decision: str
    reason: str
    policy_version: str
    event_id: str
    fingerprint: str
    derived_event: CommandFailedEvent | TestFailedEvent | None = None
    investigation_id: str | None = None


def _basename(arg0: str) -> str:
    return PurePath(arg0).name


def is_expected_nonzero(argv: list[str]) -> bool:
    if not argv:
        return False
    base = _basename(argv[0])
    if base in ("grep", "diff", "test"):
        return True
    return base == "git" and list(argv[1:3]) == ["diff", "--exit-code"]


def test_runner(argv: list[str]) -> str | None:
    if not argv:
        return None
    base = _basename(argv[0])
    if base in _TEST_RUNNER_BASENAMES:
        return base
    if base in _TEST_RUNNER_SUBCOMMANDS and len(argv) > 1 and argv[1] == "test":
        return f"{base} test"
    return None


def normalize_argv(argv: list[str]) -> str:
    if not argv:
        return ""
    return json.dumps([_basename(argv[0]), *argv[1:]])


def error_signature(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    picked = [line for line in lines if _ERROR_LINE.search(line)] or lines[-5:]
    normalized = _WHITESPACE.sub(" ", _DIGITS.sub("N", "\n".join(picked).lower()))[:500]
    return hashlib.sha256(normalized.encode()).hexdigest()


def fingerprint(
    *,
    repository_id: str,
    worktree_id: str,
    argv: list[str],
    error_sig: str,
    repository_state_id: str,
) -> str:
    h = hashlib.sha256()
    for part in (
        repository_id,
        worktree_id,
        normalize_argv(argv),
        error_sig,
        repository_state_id,
    ):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def derive_failure(
    event: CommandCompletedEvent, *, error_text: str = ""
) -> CommandFailedEvent | TestFailedEvent:
    shared = {
        "trace_id": event.trace_id,
        "parent_event_id": event.event_id,
        "caused_by": event.event_id,
        "actor": event.actor,
        "source_ref": event.source_ref,
        "repository_id": event.repository_id,
        "worktree_id": event.worktree_id,
        "adapter_id": event.adapter_id,
        "command_id": event.command_id,
        "repository_state_id": event.repository_state_id,
        "evidence_refs": list(event.evidence_refs),
    }
    payload = {
        **event.payload.model_dump(),
        "error_signature": error_signature(error_text),
    }
    runner = test_runner(event.payload.argv)
    if runner is not None:
        return TestFailedEvent(
            **shared, payload=TestFailedPayload(**payload, runner=runner)
        )
    return CommandFailedEvent(**shared, payload=CommandFailedPayload(**payload))


def admit(
    store: ObserveStore,
    event: ObserveEvent,
    *,
    error_text: str = "",
    now: float | None = None,
) -> Admission:
    now = time.time() if now is None else now
    fp = fingerprint(
        repository_id=event.repository_id,
        worktree_id=event.worktree_id,
        argv=event.payload.argv,
        error_sig=error_signature(error_text),
        repository_state_id=event.repository_state_id,
    )

    if store.has_event(event.event_id):
        return _record(store, event.event_id, fp, RECORD_ONLY, "duplicate", now)

    if isinstance(event, CommandCompletedEvent) and event.payload.exit_code != 0:
        if is_expected_nonzero(event.payload.argv):
            store.insert_event(event, fingerprint=fp)
            return _record(
                store, event.event_id, fp, RECORD_ONLY, "expected_nonzero", now
            )
        derived = derive_failure(event, error_text=error_text)
        store.insert_event(event, fingerprint=fp)
        _record(store, event.event_id, fp, RECORD_ONLY, "derived", now)
        store.insert_event(derived, fingerprint=fp)
        return _admit_failure(store, derived, fp, now, derived_event=derived)

    if isinstance(event, (CommandFailedEvent, TestFailedEvent)):
        if is_expected_nonzero(event.payload.argv):
            store.insert_event(event, fingerprint=fp)
            return _record(
                store, event.event_id, fp, RECORD_ONLY, "expected_nonzero", now
            )
        store.insert_event(event, fingerprint=fp)
        return _admit_failure(store, event, fp, now)

    store.insert_event(event, fingerprint=fp)
    return _record(store, event.event_id, fp, RECORD_ONLY, "observed", now)


def _admit_failure(
    store: ObserveStore,
    event: CommandFailedEvent | TestFailedEvent,
    fp: str,
    now: float,
    *,
    derived_event: CommandFailedEvent | TestFailedEvent | None = None,
) -> Admission:
    last_queued = store.latest_admission(fp, decisions=(QUEUE,))
    if (
        last_queued is not None
        and now - float(last_queued["decided_at"]) < COOLDOWN_SECONDS
    ):
        return _record(
            store, event.event_id, fp, SUPPRESS, "cooldown", now,
            derived_event=derived_event,
        )
    pending = store.pending_by_fingerprint(event.worktree_id, fp)
    if pending is not None:
        return _record(
            store, event.event_id, fp, SUPPRESS, "coalesced", now,
            derived_event=derived_event,
            investigation_id=pending["investigation_id"],
        )
    if store.count_pending(event.worktree_id) >= MAX_PENDING_PER_WORKTREE:
        return _record(
            store, event.event_id, fp, SUPPRESS, "queue_full", now,
            derived_event=derived_event,
        )
    investigation_id = uuid.uuid4().hex[:12]
    store.enqueue_investigation(
        investigation_id=investigation_id,
        worktree_id=event.worktree_id,
        trigger_event_id=event.event_id,
        fingerprint=fp,
    )
    return _record(
        store, event.event_id, fp, QUEUE, "queued", now,
        derived_event=derived_event,
        investigation_id=investigation_id,
    )


def _record(
    store: ObserveStore,
    event_id: str,
    fp: str,
    decision: str,
    reason: str,
    now: float,
    *,
    derived_event: CommandFailedEvent | TestFailedEvent | None = None,
    investigation_id: str | None = None,
) -> Admission:
    store.record_admission(
        event_id=event_id,
        fingerprint=fp,
        decision=decision,
        reason=reason,
        policy_version=POLICY_VERSION,
        decided_at=now,
    )
    return Admission(
        decision=decision,
        reason=reason,
        policy_version=POLICY_VERSION,
        event_id=event_id,
        fingerprint=fp,
        derived_event=derived_event,
        investigation_id=investigation_id,
    )


__all__ = [
    "COOLDOWN_SECONDS",
    "MAX_PENDING_PER_WORKTREE",
    "POLICY_VERSION",
    "QUEUE",
    "RECORD_ONLY",
    "REJECT",
    "SUPPRESS",
    "Admission",
    "admit",
    "derive_failure",
    "error_signature",
    "fingerprint",
    "is_expected_nonzero",
    "normalize_argv",
    "test_runner",
]
