"""Top-level test fixtures shared across the whole suite.

Test isolation for leaked provider API keys: `voss.harness.auth` injects
`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` into `os.environ` when it resolves
keyring credentials (so downstream LiteLLM / SDKs work without bespoke wiring).
In tests that resolve a stub credential, that export leaks into the *process*
environment and persists across tests in the same pytest worker. A leaked
`OPENAI_API_KEY` then routes every chroma-backed subsystem (memory recall,
code index, external recall) onto the OpenAI embedder instead of the offline
SentenceTransformer fallback — which 401s (and can hang) under a fake key.

This autouse fixture snapshots and restores both keys around every test so an
auth-resolving test cannot poison a later embedding-dependent test.
"""
from __future__ import annotations

import os

import pytest

_LEAK_PRONE_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")


@pytest.fixture(autouse=True)
def _restore_provider_env() -> None:
    saved = {k: os.environ.get(k) for k in _LEAK_PRONE_KEYS}
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
