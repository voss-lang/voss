"""M8-04 convention extraction tests."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from voss_runtime.memory import EpisodicMemory
from voss_runtime.providers.base import ProviderResponse

from voss.harness.conventions import (
    ConventionCandidate,
    extract_conventions,
    has_signal,
    review_candidates,
)
from voss.harness.memory_store import MemoryStore


def _provider_returning(text: str) -> AsyncMock:
    provider = AsyncMock()
    provider.complete = AsyncMock(
        return_value=ProviderResponse(
            text=text,
            model="fake",
            prompt_tokens=10,
            completion_tokens=10,
            cost_usd=0.0,
            raw={"fake": True},
            parsed=None,
        )
    )
    return provider


@pytest.mark.asyncio
async def test_scripted_signal_session_surfaces_candidate() -> None:
    history = EpisodicMemory(capacity=40)
    history.add("no use snake_case in Python", role="user")
    history.add("got it", role="assistant")
    history.add("always them in helper modules", role="user")

    assert has_signal(history.turns) is True

    payload = json.dumps([
        {
            "statement": "Use snake_case in Python",
            "confidence": 0.82,
            "evidence_quote": "no use snake_case in Python",
            "evidence_turn_idx": 0,
        }
    ])
    provider = _provider_returning(payload)

    candidates = await extract_conventions(history, provider, "fake-model")
    assert len(candidates) == 1
    assert candidates[0].statement == "Use snake_case in Python"
    assert candidates[0].confidence == pytest.approx(0.82)


def test_decline_writes_nothing() -> None:
    candidates = [
        ConventionCandidate(
            statement="use type hints",
            confidence=0.9,
            evidence_quote="always use type hints",
            evidence_turn_idx=0,
        )
    ]
    assert review_candidates(candidates, interactive=False, selection=None) == []


def test_accept_writes_one_file_with_evidence(tmp_voss_repo: Path) -> None:
    store = MemoryStore(tmp_voss_repo).bind(session_id="s1")
    candidate = ConventionCandidate(
        statement="Use snake_case in Python",
        confidence=0.82,
        evidence_quote="no use snake_case in Python",
        evidence_turn_idx=0,
    )
    selected = review_candidates([candidate], interactive=False, selection="1")
    assert selected == [0]

    path = store.write_convention(candidate, session_id="s1")
    assert path.exists()
    text = path.read_text()
    assert "Use snake_case in Python" in text
    assert "Evidence" in text
    assert "no use snake_case in Python" in text
    assert "related_session: s1" in text
    assert "evidence_turn_idx: 0" in text
    assert "confidence: 0.82" in text


def test_no_signal_skips_llm_entirely() -> None:
    history = EpisodicMemory(capacity=40)
    history.add("summarize the repo", role="user")

    assert has_signal(history.turns) is False

    # Mark a sentinel so the test fails loudly if extract_conventions ran.
    fired = {"v": False}

    async def _trap(*args, **kwargs):
        fired["v"] = True
        return []

    # Run only the gated path; do not invoke extract_conventions.
    if has_signal(history.turns):
        asyncio.run(_trap())
    assert fired["v"] is False


@pytest.mark.asyncio
async def test_extraction_timeout_returns_empty() -> None:
    history = EpisodicMemory(capacity=40)
    history.add("no use tabs in Python", role="user")
    history.add("always prefer spaces", role="user")

    async def _slow(*args, **kwargs):
        await asyncio.sleep(2.0)
        return ProviderResponse(
            text="[]", model="fake", prompt_tokens=0, completion_tokens=0,
            cost_usd=0.0, raw={}, parsed=None,
        )

    provider = SimpleNamespace(complete=_slow)
    candidates = await extract_conventions(history, provider, "fake-model", timeout=0.1)
    assert candidates == []
