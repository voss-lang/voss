from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.observe.enrollment import (
    DEFAULT_POLICY,
    EnrollmentFile,
    RepoEnrollment,
    enrollment_path,
    get_repo_enrollment,
    load_enrollment,
    load_repo_policy,
    set_repo_enrollment,
)


def test_missing_enrollment_file_is_empty(tmp_path: Path) -> None:
    enrollment = load_enrollment(tmp_path)
    assert enrollment.repositories == {}
    assert get_repo_enrollment("repo-1", tmp_path) is None


def test_enrollment_round_trip(tmp_path: Path) -> None:
    repo = RepoEnrollment(
        enabled=True,
        capture=True,
        analysis=True,
        provider="claude-agent",
        disclosure=True,
        budget_usd=5.0,
    )
    path = set_repo_enrollment("repo-1", repo, tmp_path)
    assert path == enrollment_path(tmp_path)
    loaded = get_repo_enrollment("repo-1", tmp_path)
    assert loaded == repo
    assert loaded is not None and loaded.paused is False


def test_enrollment_update_preserves_other_repos(tmp_path: Path) -> None:
    set_repo_enrollment("repo-1", RepoEnrollment(enabled=True), tmp_path)
    set_repo_enrollment("repo-2", RepoEnrollment(enabled=True, paused=True), tmp_path)
    enrollment = load_enrollment(tmp_path)
    assert set(enrollment.repositories) == {"repo-1", "repo-2"}
    assert enrollment.repositories["repo-2"].paused is True


def test_corrupt_enrollment_file_warns_and_defaults(tmp_path: Path) -> None:
    path = enrollment_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{not json")
    with pytest.warns(RuntimeWarning):
        enrollment = load_enrollment(tmp_path)
    assert enrollment == EnrollmentFile()


def test_repo_policy_defaults_without_file(tmp_path: Path) -> None:
    result = load_repo_policy(tmp_path)
    assert result.policy == DEFAULT_POLICY
    assert result.warnings == []
    assert result.path is None


def _write_policy(repo: Path, text: str) -> None:
    (repo / ".voss").mkdir(parents=True, exist_ok=True)
    (repo / ".voss" / "observe.yml").write_text(text)


def test_capture_limit_narrows(tmp_path: Path) -> None:
    _write_policy(tmp_path, "observe:\n  capture:\n    max_output_bytes: 1024\n")
    result = load_repo_policy(tmp_path)
    assert result.policy.capture.max_output_bytes == 1024
    assert result.warnings == []


def test_capture_limit_cannot_widen(tmp_path: Path) -> None:
    _write_policy(tmp_path, "observe:\n  capture:\n    max_output_bytes: 9999999\n")
    result = load_repo_policy(tmp_path)
    assert result.policy.capture.max_output_bytes == DEFAULT_POLICY.capture.max_output_bytes
    assert len(result.warnings) == 1
    assert "clamped" in result.warnings[0]


def test_investigation_limits_narrow_only(tmp_path: Path) -> None:
    _write_policy(
        tmp_path,
        "observe:\n  investigation:\n    max_model_calls: 2\n"
        "    timeout_seconds: 900\n    max_specialists: 0\n",
    )
    result = load_repo_policy(tmp_path)
    assert result.policy.investigation.max_model_calls == 2
    assert result.policy.investigation.timeout_seconds == 90
    assert result.policy.investigation.max_specialists == 1
    assert any("timeout_seconds" in w for w in result.warnings)
    assert any("max_specialists" in w for w in result.warnings)


def test_exclude_paths_added(tmp_path: Path) -> None:
    _write_policy(tmp_path, "observe:\n  exclude_paths:\n    - .env\n    - secrets/**\n")
    result = load_repo_policy(tmp_path)
    assert result.policy.exclude_paths == [".env", "secrets/**"]


def test_commands_allowlist_narrows(tmp_path: Path) -> None:
    _write_policy(
        tmp_path,
        "observe:\n  commands:\n    test:\n      argv: [pnpm, test]\n"
        "      failure_kind: test.failed\n",
    )
    result = load_repo_policy(tmp_path)
    assert result.policy.commands is not None
    command = result.policy.commands["test"]
    assert command.argv == ["pnpm", "test"]
    assert command.failure_kind == "test.failed"


def test_commands_invalid_failure_kind_ignored(tmp_path: Path) -> None:
    _write_policy(
        tmp_path,
        "observe:\n  commands:\n    test:\n      argv: [pnpm, test]\n"
        "      failure_kind: shell.run\n",
    )
    result = load_repo_policy(tmp_path)
    assert result.policy.commands == {}
    assert any("commands.test" in w for w in result.warnings)


def test_malformed_yaml_falls_back_to_defaults(tmp_path: Path) -> None:
    _write_policy(tmp_path, "observe: [unclosed\n")
    result = load_repo_policy(tmp_path)
    assert result.policy == DEFAULT_POLICY
    assert len(result.warnings) == 1


def test_unsupported_version_falls_back(tmp_path: Path) -> None:
    _write_policy(tmp_path, "version: 2\nobserve:\n  capture:\n    max_output_bytes: 1\n")
    result = load_repo_policy(tmp_path)
    assert result.policy == DEFAULT_POLICY
    assert "version" in result.warnings[0]


def test_unknown_keys_warned_not_applied(tmp_path: Path) -> None:
    _write_policy(tmp_path, "observe:\n  enabled: true\n  provider: openai\n")
    result = load_repo_policy(tmp_path)
    assert result.policy == DEFAULT_POLICY
    assert len(result.warnings) == 2


def test_bare_mapping_without_observe_wrapper(tmp_path: Path) -> None:
    _write_policy(tmp_path, "version: 1\ncapture:\n  max_output_bytes: 2048\n")
    result = load_repo_policy(tmp_path)
    assert result.policy.capture.max_output_bytes == 2048
