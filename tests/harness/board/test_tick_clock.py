"""O3-04 Task 1: FakeClock dual-form (Callable + Protocol)."""
from voss.harness.board.tick import FakeClock, MonotonicClock


class TestFakeClock:
    def test_initial_value(self):
        c = FakeClock(0.0)
        assert c() == 0.0
        assert c.now() == 0.0

    def test_advance(self):
        c = FakeClock(0.0)
        c.advance(30.0)
        assert c() == 30.0
        assert c.now() == 30.0

    def test_callable_form(self):
        c = FakeClock(10.0)
        assert callable(c)
        assert c() == 10.0


class TestMonotonicClock:
    def test_returns_positive_float(self):
        c = MonotonicClock()
        assert c() > 0
        assert c.now() > 0
