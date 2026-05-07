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
