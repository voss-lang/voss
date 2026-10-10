from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from ..tui.widgets.diff_modal import DiffDecision, Hunk
from . import events as E
from .renderer import EventBusRenderer

if TYPE_CHECKING:
    from .sessions import ServerSession

DIFF_EVENT_MAX_BYTES = 256 * 1024


class DiffReply(BaseModel):
    id: str
    decisions: list[Literal["accept", "reject", "skip"]]


@dataclass
class PendingDiff:
    count: int
    future: asyncio.Future[list[str]]


class DiffReviewRenderer(EventBusRenderer):
    def __init__(self, session: ServerSession, *, loop: asyncio.AbstractEventLoop):
        super().__init__(session.queue, session_id=session.id, loop=loop, model=session.model)
        self.session = session

    async def show_diff_modal(
        self, hunks: list[Hunk], *, timeout_s: float = 300.0,
    ) -> list[DiffDecision]:
        proposal = E.DiffProposed(
            id=uuid.uuid4().hex,
            hunks=[E.DiffHunk(file=h.file, start=h.start, lines=h.lines) for h in hunks],
        )
        # Never truncate an edit preview that the user is being asked to approve.
        if len(proposal.model_dump_json().encode()) > DIFF_EVENT_MAX_BYTES:
            self.emit(E.WarningEvent(message="Edit preview is too large. Split the edit into smaller changes."))
            return []
        future = asyncio.get_running_loop().create_future()
        self.session.pending_diffs[proposal.id] = PendingDiff(len(hunks), future)
        self.emit(proposal)
        try:
            choices = await asyncio.wait_for(future, timeout_s)
            return [DiffDecision(file=h.file, decision=d) for h, d in zip(hunks, choices)]
        except TimeoutError:
            return []
        finally:
            self.session.pending_diffs.pop(proposal.id, None)
            self.emit(E.DiffResolved(id=proposal.id))
