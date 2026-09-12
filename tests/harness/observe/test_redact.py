from __future__ import annotations

from voss.harness.observe.redact import redact_argv, redact_mapping, redact_text


def test_env_assignment_secret_redacted() -> None:
    out = redact_text("AWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE detected")
    assert "AKIAIOSFODNN7EXAMPLE" not in out
    assert "AWS_SECRET_ACCESS_KEY=<redacted>" in out


def test_quoted_and_exported_secret_redacted() -> None:
    out = redact_text("export ANTHROPIC_API_KEY='sk-ant-xyz123'")
    assert "sk-ant-xyz123" not in out


def test_colon_assignment_redacted() -> None:
    out = redact_text("github_token: ghp_abcdef123")
    assert "ghp_abcdef123" not in out


def test_non_sensitive_text_preserved() -> None:
    text = "FAIL tests/test_app.py::test_login - assert 1 == 2"
    assert redact_text(text) == text


def test_url_credentials_and_query_stripped() -> None:
    out = redact_text("see https://user:pw@example.com/path?token=abc#frag for details")
    assert "user:pw" not in out
    assert "token=abc" not in out
    assert "https://example.com/path" in out


def test_redact_argv() -> None:
    out = redact_argv(["env", "GITHUB_TOKEN=ghp_secret", "pytest"])
    assert out[0] == "env"
    assert "ghp_secret" not in out[1]
    assert out[2] == "pytest"


def test_redact_mapping_delegates_to_telemetry() -> None:
    out = redact_mapping({"password": "hunter2", "note": "keep me"})
    assert out["password"] == "<redacted>"
    assert out["note"] == "keep me"
