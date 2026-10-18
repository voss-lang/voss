from dataclasses import FrozenInstanceError

import pytest

from voss_runtime import ConfidenceTooLowError, ProbableValue


def test_valid_construction():
    pv = ProbableValue(value="hello", confidence=0.9)
    assert pv.value == "hello"
    assert pv.confidence == 0.9


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_invalid_confidence_raises(bad):
    with pytest.raises(ValueError):
        ProbableValue(value="x", confidence=bad)


def test_gate_returns_value_at_or_above_threshold():
    pv = ProbableValue(value=42, confidence=0.8)
    assert pv.gate(0.8) == 42
    assert pv.gate(0.5) == 42


def test_gate_returns_none_below_threshold():
    pv = ProbableValue(value=42, confidence=0.5)
    assert pv.gate(0.8) is None


def test_matmul_returns_bool():
    pv = ProbableValue(value="x", confidence=0.9)
    result = pv @ 0.85
    assert isinstance(result, bool)
    assert result is True
    assert (pv @ 0.95) is False


def test_unwrap_below_threshold_raises():
    pv = ProbableValue(value="x", confidence=0.4)
    with pytest.raises(ConfidenceTooLowError):
        pv.unwrap(threshold=0.5)


def test_unwrap_at_or_above_threshold_returns_value():
    pv = ProbableValue(value="x", confidence=0.9)
    assert pv.unwrap(threshold=0.5) == "x"
    assert pv.unwrap() == "x"


def test_repr_format():
    pv = ProbableValue(value="hi", confidence=0.9)
    assert repr(pv) == "ProbableValue(value='hi', confidence=0.90)"


def test_frozen_value_assignment_raises():
    pv = ProbableValue(value=1, confidence=0.5)
    with pytest.raises(FrozenInstanceError):
        pv.value = 2  # type: ignore[misc]


def test_frozen_confidence_assignment_raises():
    pv = ProbableValue(value=1, confidence=0.5)
    with pytest.raises(FrozenInstanceError):
        pv.confidence = 0.9  # type: ignore[misc]


class _Reply:
    def __init__(self, confidence):
        self.confidence = confidence


OPS = ("==", "!=", "<", "<=", ">", ">=")


def _unknown(value="x"):
    return ProbableValue(value, None, source="unknown")


def test_source_defaults_to_given():
    assert ProbableValue("positive", 0.87).source == "given"


@pytest.mark.parametrize("source", ["jev", "self_report", "given"])
def test_measured_sources_keep_their_number(source):
    pv = ProbableValue("x", 0.5, source=source)
    assert pv.source == source
    assert pv.confidence == 0.5


def test_unknown_source_has_no_number():
    pv = _unknown()
    assert pv.confidence is None
    assert pv.source == "unknown"


@pytest.mark.parametrize(
    "args,kwargs",
    [
        (("x", None), {}),
        (("x", 0.5), {"source": "unknown"}),
        (("x", 0.5), {"source": "bogus"}),
        (("x", None), {"source": "jev"}),
    ],
)
def test_source_and_confidence_must_agree(args, kwargs):
    with pytest.raises(ValueError):
        ProbableValue(*args, **kwargs)


def test_source_is_keyword_only():
    with pytest.raises(TypeError):
        ProbableValue("x", 0.5, "jev")  # type: ignore[misc]


def test_from_reply_without_confidence_is_unknown():
    for value in ("text", None, _Reply(None), _Reply("high")):
        pv = ProbableValue.from_reply(value)
        assert pv.value is value
        assert pv.confidence is None
        assert pv.source == "unknown"


def test_from_reply_with_confidence_is_self_report():
    reply = _Reply(0.7)
    pv = ProbableValue.from_reply(reply)
    assert pv.value is reply
    assert pv.confidence == 0.7
    assert pv.source == "self_report"


@pytest.mark.parametrize(
    "op,threshold,expected",
    [
        ("==", 0.8, True), ("!=", 0.8, False), ("<", 0.8, False),
        ("<=", 0.8, True), (">", 0.8, False), (">=", 0.8, True),
        ("==", 0.5, False), ("!=", 0.5, True), ("<", 0.5, False),
        ("<=", 0.5, False), (">", 0.5, True), (">=", 0.5, True),
    ],
)
def test_meets_compares_known_confidence(op, threshold, expected):
    assert ProbableValue("x", 0.8).meets(op, threshold) is expected


@pytest.mark.parametrize("op", OPS)
@pytest.mark.parametrize("threshold", [0.0, 0.5, 1.0])
def test_meets_fails_on_unknown_for_every_operator(op, threshold):
    with pytest.warns(RuntimeWarning, match="ask\\(\\) does not measure confidence"):
        assert _unknown().meets(op, threshold) is False


def test_unknown_fails_every_gate_above_zero():
    pv = _unknown()
    with pytest.warns(RuntimeWarning):
        assert (pv @ 0.5) is False
    with pytest.warns(RuntimeWarning):
        assert pv.gate(0.5) is None
    with pytest.raises(ConfidenceTooLowError, match="unknown"):
        pv.unwrap(0.5)


def test_zero_threshold_sets_no_requirement_on_unknown():
    pv = _unknown("v")
    assert pv.gate(0.0) == "v"
    assert pv.unwrap(0.0) == "v"
    assert pv.unwrap() == "v"


def test_repr_shows_unknown_confidence():
    assert repr(_unknown("hi")) == "ProbableValue(value='hi', confidence=unknown)"
