from __future__ import annotations

import inspect
import json

import httpx

from voss.harness import judgments
from voss_runtime.judgments import JevClient

SUPPORTED = {"supported": 0.9, "contradicted": 0.05, "insufficient_evidence": 0.05}


def choice_body(request: httpx.Request, overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    answers = {}
    for qid in json.loads(request.content)["questions"]:
        override = overrides.get(qid, SUPPORTED)
        if isinstance(override, dict) and "type" not in override:
            choice = max(override, key=override.get)
            answers[qid] = {"type": "choice", "choice": choice, "probabilities": override, "confidence": override[choice]}
        else:
            answers[qid] = override
    return {"model": "jev-1.13.0", "answers": answers, "usage": {"input_tokens": 100, "output_tokens": 0}}


def install_jev(monkeypatch, handler, *, timeout_ms: int = 5000) -> list:
    seen: list[httpx.Request] = []
    default_timeout_ms = timeout_ms

    async def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        response = handler(request)
        return await response if inspect.isawaitable(response) else response

    def make(key, *, timeout_ms=None, ledger=None):
        return JevClient(
            key, model="jev-1.13.0", timeout_ms=default_timeout_ms if timeout_ms is None else timeout_ms,
            max_request_bytes=24000, max_calls=4, max_cost_usd=0.01,
            client=httpx.AsyncClient(transport=httpx.MockTransport(record)), ledger=ledger,
        )

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(judgments.auth, "load_provider_key", lambda env_key: None)
    monkeypatch.setattr(judgments, "make_client", make)
    return seen
