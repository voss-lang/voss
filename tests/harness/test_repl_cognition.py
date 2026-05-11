"""
Stubs covering COG requirements:
COG-REPL-01, COG-REPL-02, COG-REPL-03, COG-REPL-04, COG-REPL-05
"""
import pytest


@pytest.mark.skip(reason="Wave 3 — pending plan M2-05")
def test_cognition_overflow_truncates_constraints() -> None:
    pass


@pytest.mark.skip(reason="Wave 3 — pending plan M2-05")
def test_cognition_status_line_tty() -> None:
    pass


@pytest.mark.skip(reason="Wave 3 — pending plan M2-05")
def test_cognition_loaded_ndjson_event() -> None:
    pass


@pytest.mark.skip(reason="Wave 4 — pending plan M2-06")
def test_drift_hint_printed_non_blocking() -> None:
    pass


@pytest.mark.skip(reason="Wave 1 — pending plan M2-01")
def test_bad_yaml_loud_failure() -> None:
    pass
