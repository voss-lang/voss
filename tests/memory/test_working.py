from voss_runtime.memory import WorkingMemory


def test_set_get_round_trip():
    wm = WorkingMemory()
    wm.set("foo", 42)
    assert wm.get("foo") == 42


def test_clear_empties_store():
    wm = WorkingMemory()
    wm.set("a", 1)
    wm.set("b", 2)
    wm.clear()
    assert list(wm.keys()) == []


def test_get_default_when_absent():
    wm = WorkingMemory()
    assert wm.get("missing", "fallback") == "fallback"


def test_get_no_default_returns_none():
    wm = WorkingMemory()
    assert wm.get("missing") is None


def test_contains_after_set():
    wm = WorkingMemory()
    wm.set("k", "v")
    assert "k" in wm
    assert "other" not in wm
