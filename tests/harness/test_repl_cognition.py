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


def test_bad_yaml_loud_failure(git_repo) -> None:
    from voss.harness.cognition import load

    voss = git_repo / ".voss"
    voss.mkdir()
    (voss / "architecture.md").write_text(
        "---\ngit_head: abc\nanalyzed_at: 2026-05-10T00:00:00+00:00\n"
        "file_count: 1\nanalyzer_version: 1\n---\n# Arch\n"
    )
    (voss / "project.json").write_text(
        '{"name": "t", "primary_language": "python"}'
    )
    (voss / "constraints.yml").write_text("rules: [\n")  # malformed YAML

    b = load(git_repo)
    assert b.load_errors, "load_errors should be populated on malformed YAML"
    assert any("constraints.yml" in e for e in b.load_errors)
