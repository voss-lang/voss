"""VBUS-01/02 glob + URI overlap unit cases — Wave 0 RED scaffold.

Targets the overlap helpers in voss.harness.claims (lands in V17-02).
Module-level import guard + xfail(strict=False) per V17-01: tests RUN and
xfail today, XPASS once the helpers ship, then the mark is removed.
"""
from __future__ import annotations

import pytest

try:
    from voss.harness.claims import glob_patterns_overlap, uri_overlap
    _CLAIMS_AVAILABLE = True
except ImportError:
    glob_patterns_overlap = None  # type: ignore[assignment]
    uri_overlap = None  # type: ignore[assignment]
    _CLAIMS_AVAILABLE = False

pytestmark = pytest.mark.xfail(
    reason="claims module not yet implemented (V17-02/03)", strict=False
)


def _require_claims() -> None:
    if not _CLAIMS_AVAILABLE:
        pytest.fail("voss.harness.claims not importable yet (V17-02/03)")


class TestGlobOverlap:
    def test_glob_subtree_contains_file(self) -> None:
        _require_claims()
        assert glob_patterns_overlap("src/api/**", "src/api/handlers.py") is True

    def test_disjoint_subtrees_do_not_overlap(self) -> None:
        _require_claims()
        assert glob_patterns_overlap("src/api/**", "src/other/**") is False


class TestUriOverlap:
    def test_exact_match_conflicts(self) -> None:
        _require_claims()
        assert uri_overlap("card://123", "card://123") is True

    def test_sibling_ids_do_not_conflict(self) -> None:
        _require_claims()
        assert uri_overlap("card://123", "card://124") is False

    def test_prefix_at_slash_boundary_conflicts(self) -> None:
        # D-06: segment-aware prefix — bead://p covers bead://p/x.
        _require_claims()
        assert uri_overlap("bead://p/x", "bead://p") is True

    def test_string_prefix_without_segment_boundary_no_conflict(self) -> None:
        # D-06: card://12 is NOT a prefix of card://123 at a / boundary.
        _require_claims()
        assert uri_overlap("card://12", "card://123") is False
