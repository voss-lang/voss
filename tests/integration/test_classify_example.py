"""Integration test for examples/raw_python/classify.py (PRD §7.1)."""
from __future__ import annotations

import pytest

import voss_runtime
from voss_runtime import configure, reset_config
from voss_runtime.providers.stub import StubProvider

from examples.raw_python.classify import classify_intent


@pytest.fixture
def stub_cancel():
    stub = StubProvider(default_response="cancel_subscription")
    voss_runtime.providers.register("__stub__", stub)
    configure(default_model="__stub__")
    yield stub
    reset_config()


@pytest.fixture
def stub_empty():
    stub = StubProvider(default_response="")
    voss_runtime.providers.register("__stub__", stub)
    configure(default_model="__stub__")
    yield stub
    reset_config()


@pytest.mark.asyncio
async def test_classify_returns_intent_when_confident(stub_cancel):
    result = await classify_intent("I want to cancel my subscription")
    assert result == "cancel_subscription"


@pytest.mark.asyncio
async def test_classify_returns_unknown_when_low_confidence(stub_empty):
    result = await classify_intent("I want to cancel my subscription")
    assert result == "unknown"
