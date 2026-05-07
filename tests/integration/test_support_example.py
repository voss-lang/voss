"""Integration test for examples/raw_python/support.py (PRD §7.2)."""
from __future__ import annotations

import importlib
import sys

import numpy as np
import pytest

import voss_runtime
from voss_runtime import configure, reset_config
from voss_runtime.providers.stub import StubProvider
from voss_runtime.semantic import SemanticMatcher


def _stub_encode(self, texts):
    out = []
    for t in texts:
        lo = t.lower()
        if any(w in lo for w in ("angry", "furious", "frustrat", "upset")):
            out.append([1.0, 0.0, 0.0])
        elif any(w in lo for w in ("refund", "money", "cancel")):
            out.append([0.0, 1.0, 0.0])
        elif any(w in lo for w in ("log in", "password", "locked", "auth")):
            out.append([0.0, 0.0, 1.0])
        else:
            out.append([0.1, 0.1, 0.1])
    return np.asarray(out, dtype=np.float32)


@pytest.fixture(scope="module")
def support_module():
    # Patch the encoder BEFORE importing the support module so that the
    # module-level `matcher = SemanticMatcher(...)` constructor uses the
    # synthetic encoder and does not download a real model.
    original_encode = SemanticMatcher._encode
    SemanticMatcher._encode = _stub_encode  # type: ignore[assignment]
    sys.modules.pop("examples.raw_python.support", None)
    try:
        mod = importlib.import_module("examples.raw_python.support")
        yield mod
    finally:
        SemanticMatcher._encode = original_encode  # type: ignore[assignment]
        sys.modules.pop("examples.raw_python.support", None)


@pytest.fixture
def stub_provider():
    stub = StubProvider(default_response="Pricing info here")
    voss_runtime.providers.register("__stub__", stub)
    configure(default_model="__stub__")
    yield stub
    reset_config()


@pytest.mark.asyncio
async def test_routes_to_escalate(support_module):
    result = await support_module.handle_message("I'm so angry, fix it")
    assert result == "[escalated] I'm so angry, fix it"


@pytest.mark.asyncio
async def test_routes_to_refund(support_module):
    result = await support_module.handle_message("Can I get a refund?")
    assert result == "[refund flow] Can I get a refund?"


@pytest.mark.asyncio
async def test_routes_to_auth(support_module):
    result = await support_module.handle_message("I can't log in")
    assert result == "[auth support] I can't log in"


@pytest.mark.asyncio
async def test_falls_through_to_context_scope(support_module, stub_provider):
    result = await support_module.handle_message(
        "What pricing tiers do you have?"
    )
    assert isinstance(result, str)
    assert result == "Pricing info here"
