"""Tests for voss.harness.consensus — D-01..D-04, D-08..D-16."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from voss.harness.consensus import (
    ConstraintsConfig,
    CritiqueResponse,
    CritiqueSummary,
    Violation,
    build_prompt,
    capture_diff,
    format_violations,
    load_constraints,
    run_critique,
)

SAMPLE_DIFF = """\
diff --git a/foo.py b/foo.py
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,5 @@
+def helper():
+    print("debug")
 def main():
     pass
"""


def _write_constraints(tmp_path: Path, mode: str = "block", rules: list[str] | None = None):
    voss_dir = tmp_path / ".voss"
    voss_dir.mkdir(exist_ok=True)
    data = {
        "mode": mode,
        "rules": rules or ["No print statements", "All functions need docstrings"],
    }
    (voss_dir / "constraints.yml").write_text(yaml.dump(data), encoding="utf-8")


def _make_mock_provider(result: CritiqueResponse | None = None, *, raise_exc: bool = False):
    """Return a mock provider whose complete method returns a canned response."""

    async def fake_complete(**_kwargs):
        if raise_exc:
            raise RuntimeError("LLM boom")
        return SimpleNamespace(parsed=result)

    provider = SimpleNamespace(complete=fake_complete)
    return provider


# ── D-01: load constraints from YAML ─────────────────────────────────


def test_load_constraints_from_yaml(tmp_path: Path) -> None:
    _write_constraints(tmp_path, mode="block", rules=["No TODOs", "Max 80 cols"])
    cfg = load_constraints(tmp_path)
    assert cfg is not None
    assert cfg.mode == "block"
    assert cfg.rules == ["No TODOs", "Max 80 cols"]


# ── D-04: skip when no constraints file ──────────────────────────────


def test_skip_when_no_constraints_file(tmp_path: Path) -> None:
    assert load_constraints(tmp_path) is None


# ── D-03: no conventions import ──────────────────────────────────────


def test_constraints_no_conventions_import() -> None:
    src = Path(__file__).resolve().parent.parent.parent / "voss" / "harness" / "consensus.py"
    text = src.read_text(encoding="utf-8")
    assert "conventions" not in text


# ── D-13: single-shot, one provider.complete call ────────────────────


def test_single_shot_one_call() -> None:
    call_count = 0

    async def counting_complete(**_kwargs):
        nonlocal call_count
        call_count += 1
        return SimpleNamespace(
            parsed=CritiqueResponse(
                violations=[],
                summary=CritiqueSummary(total_checked=2, violation_count=0),
            )
        )

    provider = SimpleNamespace(complete=counting_complete)
    cfg = ConstraintsConfig(mode="warn", rules=["r1", "r2"])
    asyncio.run(run_critique(provider, "test-model", cfg, SAMPLE_DIFF))
    assert call_count == 1


def test_response_format_is_critique_response() -> None:
    captured_kwargs: dict = {}

    async def spy_complete(**kwargs):
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            parsed=CritiqueResponse(
                violations=[],
                summary=CritiqueSummary(total_checked=1, violation_count=0),
            )
        )

    provider = SimpleNamespace(complete=spy_complete)
    cfg = ConstraintsConfig(mode="warn", rules=["r1"])
    asyncio.run(run_critique(provider, "test-model", cfg, SAMPLE_DIFF))
    assert captured_kwargs.get("response_format") is CritiqueResponse


# ── D-12: clean pass output ──────────────────────────────────────────


def test_clean_pass_output() -> None:
    result = CritiqueResponse(
        violations=[],
        summary=CritiqueSummary(total_checked=3, violation_count=0),
    )
    text, has = format_violations(result)
    assert not has
    assert "0 violations" in text
    assert "\u2713" in text  # checkmark


# ── D-10, D-11: violation output format ──────────────────────────────


def test_violation_output_format() -> None:
    result = CritiqueResponse(
        violations=[
            Violation(
                constraint="No print statements",
                file="foo.py",
                line=2,
                explanation="print() call found",
            ),
        ],
        summary=CritiqueSummary(total_checked=2, violation_count=1),
    )
    text, has = format_violations(result)
    assert has
    assert "No print statements" in text
    assert "foo.py:2" in text
    assert "print() call found" in text
    assert "1 violations / 2 constraints checked" in text


# ── D-16: fail open on LLM error ────────────────────────────────────


def test_fail_open_on_llm_error() -> None:
    provider = _make_mock_provider(raise_exc=True)
    cfg = ConstraintsConfig(mode="block", rules=["r1"])
    result = asyncio.run(run_critique(provider, "test-model", cfg, SAMPLE_DIFF))
    assert result is None


def test_fail_open_on_none_parsed() -> None:
    provider = _make_mock_provider(result=None)
    cfg = ConstraintsConfig(mode="block", rules=["r1"])
    result = asyncio.run(run_critique(provider, "test-model", cfg, SAMPLE_DIFF))
    assert result is None


# ── D-08: diff input modes ──────────────────────────────────────────


def test_diff_input_staged(monkeypatch, tmp_path: Path) -> None:
    called_with: list[list[str]] = []
    original_run = subprocess.run

    def spy_run(cmd, **kwargs):
        called_with.append(list(cmd))
        if cmd[:3] == ["git", "rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        if cmd[:2] == ["git", "diff"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=SAMPLE_DIFF, stderr="")
        return original_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy_run)
    text = capture_diff("staged", tmp_path)
    assert text == SAMPLE_DIFF
    diff_cmds = [c for c in called_with if c[:2] == ["git", "diff"]]
    assert any("--cached" in c for c in diff_cmds)


def test_diff_input_ref(monkeypatch, tmp_path: Path) -> None:
    called_with: list[list[str]] = []

    def spy_run(cmd, **kwargs):
        called_with.append(list(cmd))
        if cmd[:3] == ["git", "rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        if cmd[:2] == ["git", "diff"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="diff ref", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", spy_run)
    text = capture_diff("ref", tmp_path, ref="HEAD~3")
    assert text == "diff ref"
    diff_cmds = [c for c in called_with if c[:2] == ["git", "diff"]]
    assert any("HEAD~3" in c for c in diff_cmds)


# ── Pitfall 2: empty diff exits without LLM call ────────────────────


def test_empty_diff_returns_empty(monkeypatch, tmp_path: Path) -> None:
    def spy_run(cmd, **kwargs):
        if cmd[:3] == ["git", "rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", spy_run)
    text = capture_diff("staged", tmp_path)
    assert text == ""


# ── Pitfall 5: large diff truncation ────────────────────────────────


def test_large_diff_truncated(monkeypatch, tmp_path: Path) -> None:
    big = "x" * 40_000

    def spy_run(cmd, **kwargs):
        if cmd[:3] == ["git", "rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=".git\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=big, stderr="")

    monkeypatch.setattr(subprocess, "run", spy_run)
    text = capture_diff("staged", tmp_path)
    assert len(text) < 40_000
    assert "[diff truncated]" in text


# ── D-09: block mode vs warn mode (via format + exit logic) ──────────


def test_block_mode_has_violations() -> None:
    result = CritiqueResponse(
        violations=[Violation(constraint="r1", explanation="bad")],
        summary=CritiqueSummary(total_checked=1, violation_count=1),
    )
    _text, has = format_violations(result)
    assert has  # caller uses this + mode to decide exit code


def test_warn_mode_clean_pass() -> None:
    result = CritiqueResponse(
        violations=[],
        summary=CritiqueSummary(total_checked=1, violation_count=0),
    )
    _text, has = format_violations(result)
    assert not has


# ── Not-a-git-repo raises RuntimeError ───────────────────────────────


def test_not_git_repo_raises(monkeypatch, tmp_path: Path) -> None:
    def spy_run(cmd, **kwargs):
        if cmd[:3] == ["git", "rev-parse", "--git-dir"]:
            return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="fatal")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", spy_run)
    with pytest.raises(RuntimeError, match="not a git repository"):
        capture_diff("staged", tmp_path)


# ── build_prompt includes constraints and diff ───────────────────────


def test_build_prompt_contents() -> None:
    cfg = ConstraintsConfig(mode="warn", rules=["No TODOs", "Max 80 cols"])
    prompt = build_prompt(cfg, SAMPLE_DIFF)
    assert "1. No TODOs" in prompt
    assert "2. Max 80 cols" in prompt
    assert "def helper" in prompt


# ── Pydantic extra="ignore" on models ────────────────────────────────


def test_pydantic_extra_ignore() -> None:
    v = Violation.model_validate(
        {"constraint": "r1", "explanation": "x", "bogus_field": 99}
    )
    assert v.constraint == "r1"
    assert not hasattr(v, "bogus_field")


# ── Default mode is warn ─────────────────────────────────────────────


def test_default_mode_is_warn() -> None:
    cfg = ConstraintsConfig()
    assert cfg.mode == "warn"


# ── CLI integration: consensus in voss --help ────────────────────────


def test_consensus_in_voss_help() -> None:
    from click.testing import CliRunner
    from voss.cli import main as voss_main

    r = CliRunner().invoke(voss_main, ["--help"])
    assert r.exit_code == 0
    assert "consensus" in r.output


# ── CLI integration: block mode exits 1 ──────────────────────────────


def test_block_mode_exits_1(monkeypatch, tmp_path: Path) -> None:
    from click.testing import CliRunner
    from voss.harness.cli import consensus_cmd

    _write_constraints(tmp_path, mode="block", rules=["No print statements"])

    # Mock capture_diff to return a diff
    monkeypatch.setattr(
        "voss.harness.consensus.capture_diff",
        lambda mode, cwd, ref=None: SAMPLE_DIFF,
    )

    violation_resp = CritiqueResponse(
        violations=[Violation(constraint="No print statements", file="foo.py", line=2, explanation="print found")],
        summary=CritiqueSummary(total_checked=1, violation_count=1),
    )

    async def fake_critique(provider, model, constraints, diff_text):
        return violation_resp

    monkeypatch.setattr("voss.harness.consensus.run_critique", fake_critique)

    # Mock auth
    from types import SimpleNamespace as NS

    monkeypatch.setattr(
        "voss.harness.cli._resolve_auth_or_die",
        lambda pref: (NS(source="api"), NS(complete=None)),
    )
    monkeypatch.setattr("voss.harness.cli._resolve_default_model", lambda m: None)

    r = CliRunner().invoke(consensus_cmd, ["--staged", "--cwd", str(tmp_path)])
    assert r.exit_code == 1


# ── CLI integration: warn mode exits 0 ───────────────────────────────


def test_warn_mode_exits_0(monkeypatch, tmp_path: Path) -> None:
    from click.testing import CliRunner
    from voss.harness.cli import consensus_cmd

    _write_constraints(tmp_path, mode="warn", rules=["No print statements"])

    monkeypatch.setattr(
        "voss.harness.consensus.capture_diff",
        lambda mode, cwd, ref=None: SAMPLE_DIFF,
    )

    violation_resp = CritiqueResponse(
        violations=[Violation(constraint="No print statements", file="foo.py", line=2, explanation="print found")],
        summary=CritiqueSummary(total_checked=1, violation_count=1),
    )

    async def fake_critique(provider, model, constraints, diff_text):
        return violation_resp

    monkeypatch.setattr("voss.harness.consensus.run_critique", fake_critique)

    from types import SimpleNamespace as NS

    monkeypatch.setattr(
        "voss.harness.cli._resolve_auth_or_die",
        lambda pref: (NS(source="api"), NS(complete=None)),
    )
    monkeypatch.setattr("voss.harness.cli._resolve_default_model", lambda m: None)

    r = CliRunner().invoke(consensus_cmd, ["--staged", "--cwd", str(tmp_path)])
    assert r.exit_code == 0


# ── CLI integration: fail-open on LLM error ──────────────────────────


def test_cli_fail_open_on_llm_error(monkeypatch, tmp_path: Path) -> None:
    from click.testing import CliRunner
    from voss.harness.cli import consensus_cmd

    _write_constraints(tmp_path, mode="block", rules=["r1"])

    monkeypatch.setattr(
        "voss.harness.consensus.capture_diff",
        lambda mode, cwd, ref=None: SAMPLE_DIFF,
    )

    async def failing_critique(provider, model, constraints, diff_text):
        return None

    monkeypatch.setattr("voss.harness.consensus.run_critique", failing_critique)

    from types import SimpleNamespace as NS

    monkeypatch.setattr(
        "voss.harness.cli._resolve_auth_or_die",
        lambda pref: (NS(source="api"), NS(complete=None)),
    )
    monkeypatch.setattr("voss.harness.cli._resolve_default_model", lambda m: None)

    r = CliRunner().invoke(consensus_cmd, ["--staged", "--cwd", str(tmp_path)])
    assert r.exit_code == 0
    assert "fail-open" in (r.output + (r.output or ""))
