from __future__ import annotations

import pytest

from voss.harness.decision_review import Criterion, parse_criteria
from voss_runtime.judgments import SAFE_ID


def _pairs(source):
    return [(c.id, c.text) for c in parse_criteria(source)]


def test_explicit_ac_ids_are_kept():
    assert _pairs("AC-1: a\nAC-2: b") == [("AC-1", "a"), ("AC-2", "b")]


def test_bullets_and_separators_are_stripped_around_explicit_ids():
    source = "- S4.1: Assemble a packet\n* R2) keep ids\n• D-07 – newline join\nAC-4. last"
    assert _pairs(source) == [
        ("S4.1", "Assemble a packet"),
        ("R2", "keep ids"),
        ("D-07", "newline join"),
        ("AC-4", "last"),
    ]


def test_id_like_first_word_without_separator_keeps_full_text():
    source = "MP3 files must play\nHTTP2 is supported\nS4.1 Assemble a packet"
    assert _pairs(source) == [
        ("AC-1", "MP3 files must play"),
        ("AC-2", "HTTP2 is supported"),
        ("AC-3", "S4.1 Assemble a packet"),
    ]


def test_separator_without_following_space_is_not_an_id():
    assert _pairs("AC-1:a") == [("AC-1", "AC-1:a")]
    assert _pairs("first\nR7:b") == [("AC-1", "first"), ("AC-2", "R7:b")]


def test_numbered_list_markers_are_not_ids():
    assert _pairs("1. first\n2) second") == [("AC-1", "first"), ("AC-2", "second")]


def test_single_line_with_commas_stays_one_criterion():
    assert _pairs("handles a, b, and c") == [("AC-1", "handles a, b, and c")]


def test_list_items_are_never_split_and_blank_items_skipped():
    assert _pairs(["x, y", "  ", "z"]) == [("AC-1", "x, y"), ("AC-2", "z")]
    assert _pairs(["a\nb"]) == [("AC-1", "a\nb")]


def test_duplicate_explicit_id_keeps_text_with_generated_id():
    assert _pairs("plain\nAC-1: dup") == [("AC-1", "plain"), ("AC-2", "dup")]


def test_generated_ids_follow_position_after_explicit_ids():
    assert _pairs("R2: x\nsecond") == [("R2", "x"), ("AC-2", "second")]


def test_generated_id_skips_taken_ids():
    assert _pairs("AC-2: a\nb") == [("AC-2", "a"), ("AC-3", "b")]


def test_id_without_text_keeps_whole_line():
    assert _pairs("AC-3:") == [("AC-1", "AC-3:")]


def test_unsafe_explicit_id_falls_back():
    long_id = "S" + "1" * 70
    assert _pairs(f"{long_id}: too long") == [("AC-1", f"{long_id}: too long")]


@pytest.mark.parametrize("source", ["", "   \n\t\n", [], ["", "  "]])
def test_empty_input_returns_empty_tuple(source):
    assert parse_criteria(source) == ()


def test_ids_are_safe_and_unique_and_no_line_is_dropped():
    source = "AC-1: a\nAC-1: b\n- \n1. c\nS4.1 d\nAC-1:e\nR2) f\nR2) g\nplain, with commas"
    criteria = parse_criteria(source)
    assert all(isinstance(c, Criterion) for c in criteria)
    assert all(SAFE_ID.fullmatch(c.id) for c in criteria)
    assert len({c.id for c in criteria}) == len(criteria)
    assert len(criteria) == len([line for line in source.splitlines() if line.strip()])
