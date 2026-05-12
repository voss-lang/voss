from __future__ import annotations

import statistics

import pytest

from voss.eval.summary import _pearson


def test_pearson_matches_reference() -> None:
    rows = [
        {"confidence": 0.9, "success": True},
        {"confidence": 0.7, "success": True},
        {"confidence": 0.4, "success": False},
        {"confidence": 0.2, "success": False},
    ]

    r, n = _pearson(rows)

    assert n == 4
    assert r == pytest.approx(
        statistics.correlation([0.9, 0.7, 0.4, 0.2], [1.0, 1.0, 0.0, 0.0])
    )


def test_pearson_drops_null_rows() -> None:
    rows = [
        {"confidence": 0.9, "success": True},
        {"confidence": None, "success": False},
        {"confidence": 0.1, "success": None},
    ]

    r, n = _pearson(rows)

    assert n == 1
    assert r is None


def test_pearson_constant_returns_none() -> None:
    rows = [
        {"confidence": 0.5, "success": True},
        {"confidence": 0.5, "success": False},
    ]

    r, n = _pearson(rows)

    assert n == 2
    assert r is None


def test_pearson_empty_returns_none_zero() -> None:
    assert _pearson([]) == (None, 0)
