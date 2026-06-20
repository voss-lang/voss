"""Projection helpers for BOS engineering events.

BOSI1 intentionally keeps this layer pure: it reads existing session/run/swarm
records and returns BOS-schema dictionaries. It does not write back to the
source records, append a ledger, or alter the server/SSE event plane.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

BOS_SCHEMA_VERSION = 1

_BOS_EXIT_REASON_MAP = {
    "done": "done",
    "timeout": "timeout",
    "interrupt": "interrupt",
    "budget": "budget",
    "error": "error",
    # BOS v1 groups runtime-specific exits into the analytic buckets above.
    "max-iter": "timeout",
    "batch-invariant": "error",
    "killed": "interrupt",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _get(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _required(record: Any, key: str) -> Any:
    value = _get(record, key)
    if value in (None, ""):
        raise ValueError(f"missing required BOS projection field: {key}")
    return value


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def _envelope(
    *,
    event_id: str,
    event_type: str,
    category: str,
    event_time: str,
    ingest_time: str,
    trace_id: str,
    parent_event_id: str | None,
    caused_by: str | None,
    actor: str | None,
    source: str,
    source_ref: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": BOS_SCHEMA_VERSION,
        "event_id": event_id,
        "event_type": event_type,
        "category": category,
        "event_time": event_time,
        "ingest_time": ingest_time,
        "trace_id": trace_id,
        "parent_event_id": parent_event_id,
        "caused_by": caused_by,
        "actor": actor,
        "source_ref": {"source": source, "ref": source_ref},
        "external_identity_ref": None,
        "payload": payload,
    }


def project_session_record(
    record: Any,
    *,
    ingest_time: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Project a SessionRecord-shaped object into a BOS session event."""

    session_id = str(_required(record, "id"))
    started_at = str(_get(record, "started_at") or ingest_time or _now_iso())
    parent_id = _get(record, "parent_id")
    payload = {
        "session_id": session_id,
        "parent_session_id": parent_id,
        "started_at": started_at,
        "ended_at": _get(record, "updated_at"),
        "model": _get(record, "model"),
        "total_cost_usd": _float(_get(record, "total_cost_usd")),
        "turn_count": len(_list(_get(record, "turns"))),
    }
    return _envelope(
        event_id=session_id,
        event_type="session.started",
        category="session",
        event_time=started_at,
        ingest_time=ingest_time or _now_iso(),
        trace_id=trace_id or session_id,
        parent_event_id=parent_id,
        caused_by=parent_id,
        actor=None,
        source="session",
        source_ref=session_id,
        payload=payload,
    )


def _normalized_exit_reason(reason: Any) -> str | None:
    if reason is None:
        return None
    return _BOS_EXIT_REASON_MAP.get(str(reason), "error")


def _plan_steps(plan: Any) -> list[dict[str, Any]]:
    if not isinstance(plan, Mapping):
        return []
    steps = plan.get("steps", [])
    if not isinstance(steps, list):
        return []
    return [dict(step) for step in steps if isinstance(step, Mapping)]


def project_run_record(
    record: Any,
    *,
    session_id: str | None = None,
    ingest_time: str | None = None,
    trace_id: str | None = None,
    parent_event_id: str | None = None,
) -> dict[str, Any]:
    """Project a RunRecord-shaped object into a BOS task event."""

    run_id = str(_required(record, "id"))
    event_time = str(
        _get(record, "ended_at")
        or _get(record, "started_at")
        or ingest_time
        or _now_iso()
    )
    payload = {
        "task_id": run_id,
        "session_id": session_id,
        "swarm_id": None,
        "run_id": run_id,
        "goal": str(_get(record, "goal", "")),
        "owned_files": [],
        "depends_on": [],
        "exit_reason": _normalized_exit_reason(_get(record, "exit_reason")),
        "changed": [str(path) for path in _list(_get(record, "changed")) if path],
        "summary": None,
        "cost_usd": _float(_get(record, "cost_usd")),
        "confidence": None,
        "plan_steps": _plan_steps(_get(record, "plan")),
    }
    return _envelope(
        event_id=run_id,
        event_type="task.completed",
        category="task",
        event_time=event_time,
        ingest_time=ingest_time or _now_iso(),
        trace_id=trace_id or session_id or run_id,
        parent_event_id=parent_event_id,
        caused_by=None,
        actor="agent",
        source="session",
        source_ref=run_id,
        payload=payload,
    )


def _avoided_path(item: Any) -> str | None:
    if isinstance(item, Mapping):
        for key in ("path", "target", "pattern"):
            value = item.get(key)
            if value:
                return str(value)
        return None
    if item:
        return str(item)
    return None


def project_run_file_events(
    record: Any,
    *,
    session_id: str | None = None,
    ingest_time: str | None = None,
    trace_id: str | None = None,
    parent_event_id: str | None = None,
) -> list[dict[str, Any]]:
    """Project RunRecord file lists into BOS file events."""

    run_id = str(_required(record, "id"))
    event_time = str(
        _get(record, "ended_at")
        or _get(record, "started_at")
        or ingest_time
        or _now_iso()
    )
    rows: list[tuple[str, str]] = []
    rows.extend(
        ("modified", str(path)) for path in _list(_get(record, "changed")) if path
    )
    rows.extend(
        ("inspected", str(path))
        for path in _list(_get(record, "inspected"))
        if path
    )
    for item in _list(_get(record, "avoided")):
        path = _avoided_path(item)
        if path:
            rows.append(("avoided", path))

    out: list[dict[str, Any]] = []
    for index, (operation, path) in enumerate(rows):
        event_id = f"{run_id}:file:{operation}:{index}"
        payload = {
            "path": path,
            "operation": operation,
            "src_path": None,
            "task_id": run_id,
            "session_id": session_id,
            "run_id": run_id,
            "swarm_id": None,
            "ts_ms": None,
            "diff_summary": _get(record, "diff_summary") or None,
            "tool_name": None,
        }
        out.append(
            _envelope(
                event_id=event_id,
                event_type=f"file.{operation}",
                category="file",
                event_time=event_time,
                ingest_time=ingest_time or _now_iso(),
                trace_id=trace_id or session_id or run_id,
                parent_event_id=parent_event_id or run_id,
                caused_by=run_id,
                actor="agent",
                source="session",
                source_ref=f"{run_id}:{operation}:{index}:{path}",
                payload=payload,
            )
        )
    return out


def _role_names(roster: Any) -> list[str]:
    names: list[str] = []
    for role in _list(roster):
        if isinstance(role, Mapping):
            name = role.get("name")
        else:
            name = getattr(role, "name", role)
        if name:
            names.append(str(name))
    return names


def project_swarm_log_event(
    event: Mapping[str, Any],
    *,
    ingest_time: str | None = None,
    trace_id: str | None = None,
    parent_event_id: str | None = None,
    caused_by: str | None = None,
) -> dict[str, Any]:
    """Project one SwarmStore JSONL envelope into a BOS event."""

    source_type = str(_required(event, "type"))
    swarm_id = str(_required(event, "swarm_id"))
    source_id = str(_get(event, "id") or f"{swarm_id}:{source_type}")
    payload_src = dict(_get(event, "payload", {}) or {})
    event_time = str(_get(event, "ts") or ingest_time or _now_iso())
    actor = _get(event, "actor")

    if source_type == "swarm.create":
        category = "swarm"
        event_type = "swarm.create"
        payload = {
            "swarm_id": swarm_id,
            "task_id": None,
            "session_id": None,
            "goal": payload_src.get("goal"),
            "cwd": payload_src.get("cwd"),
            "roster": _role_names(payload_src.get("roster", [])),
        }
    elif source_type == "swarm.assign":
        category = "swarm"
        event_type = "swarm.assign"
        payload = {
            "swarm_id": swarm_id,
            "task_id": payload_src.get("task_id"),
            "session_id": payload_src.get("session_id"),
        }
    elif source_type == "swarm.task":
        category = "task"
        event_type = "task.created"
        task_id = str(_required(payload_src, "task_id"))
        payload = {
            "task_id": task_id,
            "session_id": None,
            "swarm_id": swarm_id,
            "run_id": None,
            "goal": str(payload_src.get("goal", "")),
            "owned_files": [
                str(path) for path in _list(payload_src.get("owned_files")) if path
            ],
            "depends_on": [
                str(dep) for dep in _list(payload_src.get("depends_on")) if dep
            ],
        }
    elif source_type == "swarm.worker_done":
        category = "task"
        event_type = "task.completed"
        task_id = str(_required(payload_src, "task_id"))
        payload = {
            "task_id": task_id,
            "session_id": payload_src.get("session_id"),
            "swarm_id": swarm_id,
            "run_id": None,
            "goal": str(payload_src.get("goal", "")),
            "owned_files": [],
            "depends_on": [],
            "summary": payload_src.get("summary"),
        }
    else:
        raise ValueError(f"unsupported swarm event type: {source_type}")

    return _envelope(
        event_id=f"swarm-log:{source_id}",
        event_type=event_type,
        category=category,
        event_time=event_time,
        ingest_time=ingest_time or _now_iso(),
        trace_id=trace_id or swarm_id,
        parent_event_id=parent_event_id,
        caused_by=caused_by,
        actor=str(actor) if actor else None,
        source="swarm_log",
        source_ref=f"{swarm_id}:{source_id}",
        payload=payload,
    )


__all__ = [
    "BOS_SCHEMA_VERSION",
    "project_run_file_events",
    "project_run_record",
    "project_session_record",
    "project_swarm_log_event",
]
