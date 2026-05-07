import pytest

from voss_runtime.memory import EpisodicMemory
from voss_runtime.providers import StubProvider


def test_add_appends_with_role():
    em = EpisodicMemory(provider=StubProvider(), model="stub")
    em.add("hello", role="user")
    em.add("hi there", role="assistant")
    assert len(em.turns) == 2
    assert em.turns[0].role == "user"
    assert em.turns[0].content == "hello"
    assert em.turns[1].role == "assistant"


def test_last_returns_dicts():
    em = EpisodicMemory(provider=StubProvider(), model="stub")
    em.add("a", role="user")
    em.add("b", role="assistant")
    em.add("c", role="user")
    assert em.last(2) == [
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ]


@pytest.mark.asyncio
async def test_summarize_clears_turns_and_sets_summary():
    stub = StubProvider(default_response="STUB SUMMARY")
    em = EpisodicMemory(provider=stub, model="stub")
    em.add("x", role="user")
    em.add("y", role="assistant")
    result = await em.summarize()
    assert result == "STUB SUMMARY"
    assert em.summary == "STUB SUMMARY"
    assert em.turns == []


@pytest.mark.asyncio
async def test_maybe_summarize_triggers_when_over_capacity():
    stub = StubProvider(default_response="SUM")
    em = EpisodicMemory(capacity=2, provider=stub, model="stub")
    em.add("a")
    em.add("b")
    em.add("c")
    await em.maybe_summarize()
    assert em.turns == []
    assert em.summary == "SUM"


def test_render_includes_summary_and_turns():
    em = EpisodicMemory(provider=StubProvider(), model="stub")
    em.summary = "prior context"
    em.add("hello", role="user")
    rendered = em.render()
    assert rendered[0] == {
        "role": "system",
        "content": "Conversation summary so far:\nprior context",
    }
    assert rendered[1] == {"role": "user", "content": "hello"}
