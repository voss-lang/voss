"""J3-04 live smoke: one real Jev rerank over a synthetic 3-candidate pool."""
from __future__ import annotations

import os

import pytest

from voss.harness.code import rerank as rr
from voss_runtime.judgments import JudgmentLedger

from .conftest import make_candidates

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.environ.get("TYPESAFE_API_KEY"), reason="TYPESAFE_API_KEY not set"),
]


async def test_live_rerank_returns_a_permutation_with_one_receipt():
    pool = make_candidates(3, texts=[
        "def render_page(html):\n    return html.strip()\n",
        "def retry_backoff(attempt):\n    return min(2.0 ** attempt, 30.0)\n",
        "def parse_config(text):\n    return dict(line.split('=') for line in text.splitlines())\n",
    ])
    ledger = JudgmentLedger(4, 0.01)
    order = await rr.rerank(pool, task="Change how long the client waits between retries.", mode="active", ledger=ledger)

    assert sorted(order) == [0, 1, 2]
    [receipt] = ledger.receipts
    print(f"status={receipt.status} latency_ms={receipt.latency_ms:.0f} request_bytes={receipt.detail['request_bytes']} model_returned={receipt.model_returned}")
