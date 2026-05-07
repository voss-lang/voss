from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .._config import get_config
from ..providers import get as get_provider
from ..providers.base import ModelProvider


@dataclass
class Turn:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class EpisodicMemory:
    capacity: int = 20
    summary: str = ""
    turns: list[Turn] = field(default_factory=list)
    provider: Optional[ModelProvider] = None
    model: Optional[str] = None

    @property
    def _model(self) -> str:
        return self.model or get_config().default_model

    @property
    def _provider(self) -> ModelProvider:
        return self.provider or get_provider(self._model)

    def add(self, content: str, *, role: str = "user") -> None:
        self.turns.append(Turn(role=role, content=content))

    def last(self, n: int) -> list[dict]:
        return [{"role": t.role, "content": t.content} for t in self.turns[-n:]]

    async def summarize(self) -> str:
        if not self.turns:
            return self.summary
        transcript = "\n".join(f"{t.role}: {t.content}" for t in self.turns)
        preamble = f"Existing summary:\n{self.summary}\n\n" if self.summary else ""
        prompt = (
            f"{preamble}Update the summary with these new turns. "
            f"Keep it under 200 tokens, factual.\n\n{transcript}"
        )
        resp = await self._provider.complete(
            messages=[{"role": "user", "content": prompt}], model=self._model
        )
        self.summary = resp.text
        self.turns = []
        return self.summary

    async def maybe_summarize(self) -> None:
        if len(self.turns) > self.capacity:
            await self.summarize()

    def render(self) -> list[dict]:
        messages: list[dict] = []
        if self.summary:
            messages.append(
                {"role": "system", "content": f"Conversation summary so far:\n{self.summary}"}
            )
        messages.extend({"role": t.role, "content": t.content} for t in self.turns)
        return messages
