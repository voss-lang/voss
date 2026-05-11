"""
Stubs covering COG requirements:
COG-REC-01, COG-REC-02, COG-REC-03, COG-REC-04, COG-REC-05, COG-REC-06
"""
import pytest


@pytest.mark.skip(reason="Wave 1 — pending plan M2-02")
def test_inspect_captures_fs_read() -> None:
    pass


@pytest.mark.skip(reason="Wave 1 — pending plan M2-02")
def test_change_captures_fs_write() -> None:
    pass


@pytest.mark.skip(reason="Wave 1 — pending plan M2-02")
def test_validation_captures_exit_code() -> None:
    pass


@pytest.mark.skip(reason="Wave 1 — pending plan M2-02")
def test_failure_captures_tool_error() -> None:
    pass


@pytest.mark.skip(reason="Wave 1 — pending plan M2-02")
def test_diff_summary_from_git() -> None:
    pass


@pytest.mark.skip(reason="Wave 2 — pending plan M2-03")
def test_decisions_mirror_to_markdown() -> None:
    pass
