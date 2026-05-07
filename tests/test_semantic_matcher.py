from __future__ import annotations

import numpy as np
import pytest

from voss_runtime.semantic import Case, SemanticMatcher


def _make_matcher(cases, embeddings, threshold=0.75):
    return SemanticMatcher(cases, threshold=threshold, embeddings=embeddings)


def test_construct_with_synthetic_embeddings():
    cases = [Case("refund", "refund"), Case("greeting", "greeting")]
    embeddings = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    matcher = _make_matcher(cases, embeddings)
    # Stub the query encoder so no model download is required
    matcher._encode = lambda texts: np.array([[1.0, 0.0, 0.0]], dtype=np.float32)

    assert matcher.match("anything") == "refund"
    assert matcher._encoder is None


def test_first_match_wins():
    # Both above threshold; first listed should win even though second has higher score
    cases = [Case("first", "first"), Case("second", "second")]
    embeddings = np.array(
        [[0.8, 0.6, 0.0], [1.0, 0.0, 0.0]], dtype=np.float32
    )
    # Normalize first row to unit length so dot product is a valid cosine
    embeddings[0] = embeddings[0] / np.linalg.norm(embeddings[0])
    matcher = _make_matcher(cases, embeddings, threshold=0.75)
    matcher._encode = lambda texts: np.array([[1.0, 0.0, 0.0]], dtype=np.float32)

    # Sims: first ~0.8, second = 1.0; first wins because order-sensitive
    assert matcher.match("query") == "first"


def test_no_match():
    cases = [Case("refund", "refund"), Case("greeting", "greeting")]
    embeddings = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    matcher = _make_matcher(cases, embeddings, threshold=0.5)
    matcher._encode = lambda texts: np.array([[0.0, 0.0, 1.0]], dtype=np.float32)

    assert matcher.match("orthogonal") is None


def test_index_roundtrip(tmp_path):
    cases = [Case("refund", "money back"), Case("greeting", "hello there")]
    embeddings = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    matcher = SemanticMatcher(
        cases, threshold=0.6, model="my-model", embeddings=embeddings
    )

    index_path = tmp_path / "index.json"
    matcher.write_index(index_path)

    loaded = SemanticMatcher.from_index(index_path)
    assert loaded._encoder is None
    assert loaded.threshold == 0.6
    assert loaded.model_name == "my-model"
    assert [c.label for c in loaded.cases] == ["refund", "greeting"]
    assert [c.description for c in loaded.cases] == ["money back", "hello there"]
    np.testing.assert_array_equal(loaded._embeddings, embeddings)


@pytest.mark.live
def test_live_real_encoder():
    matcher = SemanticMatcher(
        [
            ("I want my money back", "refund"),
            ("hello there", "greeting"),
        ],
        threshold=0.5,
    )
    assert matcher.match("I want a refund") == "refund"
