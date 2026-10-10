from __future__ import annotations

from pathlib import Path
import re

import httpx
import pytest

from voss_runtime import judgments as j

SDK_DOC = Path(__file__).resolve().parents[1] / "docs" / "sdk.md"


def _section_blocks() -> list[str]:
    text = SDK_DOC.read_text()
    match = re.search(r"^### Explicit judgments\n(.*?)(?=^##)", text, re.M | re.S)
    assert match, "docs/sdk.md is missing the '### Explicit judgments' section"
    return re.findall(r"^```python\n(.*?)^```", match.group(1), re.M | re.S)


@pytest.mark.parametrize("p,expected", [(0.79, "unknown"), (0.81, "billing")])
def test_explicit_judgments_doc_example_runs(monkeypatch, capsys, p, expected):
    blocks = _section_blocks()
    assert len(blocks) == 1
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={
            "model": "jev-1.13.0",
            "answers": {"route": {"type": "choice", "choice": "billing", "probabilities": {"billing": p, "other": round(1 - p, 2)}, "confidence": 0.5}},
            "usage": {"input_tokens": 10, "output_tokens": 0},
        })

    def factory(api_key, cfg, ledger):
        return j.JevClient(
            api_key, model=cfg.judgments_model, timeout_ms=cfg.judgments_timeout_ms,
            max_request_bytes=cfg.judgments_max_request_bytes, max_calls=cfg.judgments_max_calls_per_turn,
            max_cost_usd=cfg.judgments_max_cost_usd, client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
            ledger=ledger,
        )

    monkeypatch.setattr(j, "_new_client", factory)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    exec(compile(blocks[0], str(SDK_DOC), "exec"), {"__name__": "sdk_docs_example"})
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["answered 1", expected]
    assert len(requests) == 1
