"""Golden concept-query quality gate (D-08): real semantic queries against the
Voss repo itself, expected file in top-5.

@pytest.mark.slow — builds a real embedding index over the live repo (needs
the HF/ONNX model cache; minutes, not seconds).
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# (concept query, expected file) — concept phrasing, not literal symbol names.
GOLDEN_QUERIES: list[tuple[str, str]] = [
    ("merge bm25 and vector rankings with reciprocal rank fusion", "voss/harness/memory_store.py"),
    ("tokenize camelCase and snake_case text for lexical bm25 recall", "voss/harness/memory_store.py"),
    ("extract function and class symbols into the sqlite code index", "voss/harness/code/index.py"),
    ("discover repository files preferring git ls-files with a walk fallback", "voss/harness/code/index.py"),
    ("pack iteration records under a token budget with fold and digest eviction", "voss/harness/context_allocator.py"),
    ("append a token savings record to the session ledger jsonl", "voss/harness/recorder.py"),
    ("build a litellm provider bound to an openai compatible api base", "voss/harness/model_router.py"),
    ("compose the cacheable system prompt prefix with cache control blocks", "voss/harness/agent.py"),
    ("registry entry classifying tools as mutating with capability groups", "voss/harness/tools.py"),
    ("store and retrieve embeddings from a persistent chroma collection", "voss_runtime/memory/semantic.py"),
    ("deny mutating tool calls based on permission mode tiers", "voss/harness/permissions.py"),
    ("quotas and byte cap for memory sources like turns and decisions", "voss/harness/memory_store.py"),
]


@pytest.mark.slow
def test_golden_concept_queries():
    """≥10 (query, expected_file) pairs; recall@5 must be ≥80%.

    A 100%-must-hit gate on semantic retrieval is flaky CI — relevant test
    files legitimately outrank implementations for some concept queries.
    80% recall@5 is the quality bar (D-08); failures print for visibility.
    This test file embeds its own query strings, so its own chunks are
    excluded from hits (self-pollution guard).
    """
    assert len(GOLDEN_QUERIES) >= 10

    from voss.harness.code.index import build_index

    build_index(REPO_ROOT)

    from voss.harness.code.semantic_index import CodeIndex

    index = CodeIndex(REPO_ROOT)
    index.build(session_id="test-session")

    failures: list[str] = []
    for query, expected_file in GOLDEN_QUERIES:
        hits = [
            h
            for h in index.query(query, top_k=8)
            if "test_golden_queries" not in h.locator
        ][:5]
        locators = [h.locator for h in hits]
        if not any(expected_file in loc for loc in locators):
            failures.append(f"{query!r} → expected {expected_file}, got {locators}")

    recall = (len(GOLDEN_QUERIES) - len(failures)) / len(GOLDEN_QUERIES)
    assert recall >= 0.8, (
        f"golden recall@5 {recall:.0%} < 80%:\n" + "\n".join(failures)
    )
