"""Shared T8 TUI test fixtures."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from voss_runtime.memory.episodic import EpisodicMemory
from voss_runtime.providers.base import ProviderResponse


@pytest.fixture
def seeded_history():
    def _seeded_history(*user_prompts: str) -> EpisodicMemory:
        memory = EpisodicMemory(capacity=40)
        for prompt in user_prompts:
            memory.add(prompt, role="user")
        return memory

    return _seeded_history


@pytest.fixture
def stub_provider():
    class StubProvider:
        async def complete(self, *args, **kwargs) -> ProviderResponse:
            return ProviderResponse(text="stub completion")

    return StubProvider()


@pytest.fixture
def mock_recorder_bridge() -> MagicMock:
    bridge = MagicMock()
    bridge.emit = MagicMock()
    bridge.recorder = SimpleNamespace()
    return bridge
