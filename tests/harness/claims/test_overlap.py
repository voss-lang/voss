"""VBUS-01/02 glob + URI overlap unit cases.

GREEN as of V17-02 (overlap engine shipped in voss.harness.claims).
"""
from __future__ import annotations

from voss.harness.claims import glob_patterns_overlap, uri_overlap


class TestGlobOverlap:
    def test_glob_subtree_contains_file(self) -> None:
        assert glob_patterns_overlap("src/api/**", "src/api/handlers.py") is True

    def test_disjoint_subtrees_do_not_overlap(self) -> None:
        assert glob_patterns_overlap("src/api/**", "src/other/**") is False


class TestUriOverlap:
    def test_exact_match_conflicts(self) -> None:
        assert uri_overlap("card://123", "card://123") is True

    def test_sibling_ids_do_not_conflict(self) -> None:
        assert uri_overlap("card://123", "card://124") is False

    def test_prefix_at_slash_boundary_conflicts(self) -> None:
        # D-06: segment-aware prefix — bead://p covers bead://p/x.
        assert uri_overlap("bead://p/x", "bead://p") is True

    def test_string_prefix_without_segment_boundary_no_conflict(self) -> None:
        # D-06: card://12 is NOT a prefix of card://123 at a / boundary.
        assert uri_overlap("card://12", "card://123") is False
