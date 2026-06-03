"""Server session manager (HYBRID-REFACTOR-PLAN H1.4).

Holds per-session server state: the event queue drained by SSE, the
`SessionRecord` + `EpisodicMemory` reused from the existing session store,
the in-flight turn task (for abort + one-turn-per-session), the resolved
provider, and the pending-permission future registry (H1.9).

The session id is the existing `SessionRecord.id` (`uuid4().hex[:12]`) so
on-disk persistence (`session.save/load`) and the protocol id are the same.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from voss_runtime import EpisodicMemory

from .. import session as session_store

QUEUE_MAXSIZE = 256


@dataclass
class ServerSession:
    id: str
    cwd: Path
    model: str
    provider: Any  # ModelProvider; resolved at create, reused per turn
    record: session_store.SessionRecord
    history: EpisodicMemory
    queue: "asyncio.Queue[Any]" = field(
        default_factory=lambda: asyncio.Queue(maxsize=QUEUE_MAXSIZE)
    )
    task: asyncio.Task | None = None
    pending: dict[str, Future] = field(default_factory=dict)
    title: str = ""
    # M2: prior RunRecords from a resumed session, surfaced on the first turn
    # then cleared (deep history thereafter flows via `history`).
    prior_context: Any = None

    @property
    def busy(self) -> bool:
        return self.task is not None and not self.task.done()


class SessionManager:
    """In-memory registry of active server sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, ServerSession] = {}

    def create(
        self,
        *,
        cwd: Path,
        model: str,
        provider: Any,
        title: str = "",
    ) -> ServerSession:
        record = session_store.SessionRecord.new(cwd=cwd, model=model, name=title)
        session = ServerSession(
            id=record.id,
            cwd=cwd,
            model=model,
            provider=provider,
            record=record,
            history=EpisodicMemory(capacity=40),
            title=title,
        )
        self._sessions[session.id] = session
        return session

    def adopt(
        self,
        *,
        record: session_store.SessionRecord,
        history: EpisodicMemory,
        provider: Any,
        prior_context: Any = None,
    ) -> ServerSession:
        """Register a session resumed from disk (reuses the saved id + history)."""
        session = ServerSession(
            id=record.id,
            cwd=Path(record.cwd),
            model=record.model,
            provider=provider,
            record=record,
            history=history,
            title=record.name,
            prior_context=prior_context,
        )
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> ServerSession | None:
        return self._sessions.get(session_id)

    def list(self) -> list[ServerSession]:
        return list(self._sessions.values())

    def delete(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        if session.busy and session.task is not None:
            session.task.cancel()
        return True
