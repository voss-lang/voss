from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class ProviderResponse:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    # T4 CACHE-02 (D-01): symmetric with ProviderStreamEvent.Usage; additive defaults preserve pre-T4 fixtures
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    raw: dict = field(default_factory=dict)
    parsed: Optional[Any] = None

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@runtime_checkable
class ModelProvider(Protocol):
    async def complete(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> ProviderResponse: ...

    def count_tokens(self, *, text: str, model: str) -> int: ...
