from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from pydantic import BaseModel, ValidationError

from ._config import get_config
from .exceptions import ParseError, ProviderError
from .providers import get as get_provider
from .providers.base import ModelProvider
from .tools import ToolDescriptor


class VossAgent:
    system_prompt: str = ""
    tools: Sequence[ToolDescriptor] = ()
    model: Optional[str] = None
    retries: int = 1
    return_type: Optional[type] = None

    @property
    def _model(self) -> str:
        return self.model or get_config().default_model

    @property
    def _provider(self) -> ModelProvider:
        return get_provider(self._model)

    async def _ask(self, user_prompt: str) -> Any:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        tools_payload = [t.schema() for t in self.tools] or None
        response_format = (
            self.return_type
            if (
                self.return_type is not None
                and inspect.isclass(self.return_type)
                and issubclass(self.return_type, BaseModel)
            )
            else None
        )

        last_exc: ProviderError | ParseError | None = None
        for _ in range(max(1, self.retries + 1)):
            try:
                resp = await self._provider.complete(
                    messages=messages,
                    model=self._model,
                    response_format=response_format,
                    tools=tools_payload,
                )
                if response_format is not None:
                    return resp.parsed
                return resp.text
            except ValidationError as exc:
                last_exc = ParseError(str(exc))
            except (ProviderError, ParseError) as exc:
                last_exc = exc

        assert last_exc is not None
        raise last_exc

    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Subclasses override. Default: pass first positional arg to the model."""
        payload = args[0] if args else kwargs.get("input", "")
        return await self._ask(str(payload))

    def spawn(self, *args: Any, **kwargs: Any) -> AgentHandle:
        task = asyncio.create_task(self.run(*args, **kwargs))
        return AgentHandle(task=task, agent=self)


@dataclass(frozen=True)
class AgentHandle:
    task: asyncio.Task[Any]
    agent: VossAgent

    async def result(self) -> Any:
        return await self.task

    async def cancel(self) -> None:
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass


async def gather(
    handles: Sequence[AgentHandle],
    *,
    timeout: Optional[float] = None,
) -> list[Any]:
    if not handles:
        return []

    tasks = [h.task for h in handles]
    done, pending = await asyncio.wait(tasks, timeout=timeout)

    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    results: list[Any] = []
    for task in tasks:
        if task not in done or task.cancelled():
            results.append(None)
            continue
        try:
            results.append(task.result())
        except Exception:
            results.append(None)
    return results
