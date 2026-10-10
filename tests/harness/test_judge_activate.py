import json
import os

import pytest
from click.testing import CliRunner

from voss.harness import judgments as j
from voss.harness.code.rerank import RUBRIC_VERSION

MODEL = "jev-1.13.0"
CONFIG = "# project config\nname: demo\njudgments:\n  # trial run\n  enabled: true\n  code_recall: shadow  # trial\nother: 1\n"


def gate_report(**overrides):
    report = {
        "schema_version": 1, "status": "complete", "split": "test", "commit": "abc", "model": MODEL,
        "rubric_version": RUBRIC_VERSION, "location": "home", "run_date": "2026-10-04",
        "ranking": {"mean_gain": 0.0412, "ci_low": 0.0105, "ci_high": 0.07, "recall_diff": 0.0, "passed": True},
        "latency": {"n": 120, "p50_ms": 400.0, "p95_ms": 870.0, "passed": True},
        "fallbacks": {}, "passed": True,
    }
    return {**report, **overrides}


def ab_report(**overrides):
    report = {
        "schema_version": 1, "setting": "recall", "a": "off", "b": "active", "jev_model": MODEL,
        "rubric_version": RUBRIC_VERSION, "generation_model": "gen",
        "compare": {"n_tasks": 30, "a_pass_rate": 0.6, "b_pass_rate": 0.7, "mean_diff": 0.1, "ci_low": 0.0,
                    "ci_high": 0.2, "regressions": 1, "unconfirmed": 0, "no_difference": 26, "passed": True},
        "passed": True,
    }
    return {**report, **overrides}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.setattr(j.auth, "load_provider_key", lambda env_key: None)
    monkeypatch.setattr(j.config, "get_judgments_config", lambda: {"model": MODEL})
    project = tmp_path / "project"
    (project / ".voss").mkdir(parents=True)
    (project / ".voss" / "config.yml").write_text(CONFIG)
    monkeypatch.chdir(project)
    return project


@pytest.fixture
def reports(tmp_path):
    path = tmp_path / "reports"
    path.mkdir()
    (path / "rerank-test.json").write_text(json.dumps(gate_report()))
    (path / "rerank-ab.json").write_text(json.dumps(ab_report()))
    return path


def config_bytes(project):
    return (project / ".voss" / "config.yml").read_bytes()


def activate(reports, answer="y"):
    return CliRunner().invoke(j.judge_cmd, ["activate", "code_recall", "--reports", str(reports)], input=answer)


def test_judge_help_lists_run_and_activate():
    from voss.cli import main

    result = CliRunner().invoke(main, ["judge", "--help"])
    assert result.exit_code == 0, result.output
    assert "run" in result.output and "activate" in result.output


def test_judge_without_arguments_keeps_the_usage_error():
    result = CliRunner().invoke(j.judge_cmd, [])
    assert result.exit_code == 2
    assert "provide either a request file or --demo" in result.output


@pytest.mark.parametrize("prefix", [[], ["run"]])
def test_judge_demo_and_run_demo_reach_the_same_command(monkeypatch, prefix):
    seen = []
    monkeypatch.setattr(j, "demo_request", lambda: seen.append("demo") or ("state", {}))
    monkeypatch.setattr(j, "open_client", lambda cwd, explicit: (_ for _ in ()).throw(j.JudgmentError("unavailable", "no key")))
    result = CliRunner().invoke(j.judge_cmd, [*prefix, "--demo"])
    assert result.exit_code == 1 and seen == ["demo"]
    assert "judgment unavailable: no key" in result.stderr


def test_judge_request_file_path_still_routes_to_run(tmp_path):
    path = tmp_path / "request.json"
    path.write_text("not JSON")
    result = CliRunner().invoke(j.judge_cmd, [str(path)])
    assert result.exit_code == 1 and "invalid request file" in result.stderr


@pytest.mark.parametrize("setup, reason", [
    (lambda r: [p.unlink() for p in r.iterdir()], "rerank-test.json is missing"),
    (lambda r: (r / "rerank-test.json").write_text(json.dumps({"schema_version": 1, "split": "test", "status": "started"})), "incomplete"),
    (lambda r: (r / "rerank-test.json").write_text(json.dumps(gate_report(passed=False))), "rerank-test.json did not pass"),
    (lambda r: (r / "rerank-test.json").write_text(json.dumps(gate_report(split="dev"))), "not test"),
    (lambda r: (r / "rerank-test.json").write_text(json.dumps(gate_report(model="jev-9"))), "'jev-9'"),
    (lambda r: (r / "rerank-test.json").write_text(json.dumps(gate_report(rubric_version="old"))), "rubric_version 'old'"),
    (lambda r: (r / "rerank-ab.json").unlink(), "rerank-ab.json is missing"),
    (lambda r: (r / "rerank-ab.json").write_text(json.dumps(ab_report(passed=False))), "rerank-ab.json did not pass"),
    (lambda r: (r / "rerank-ab.json").write_text(json.dumps(ab_report(rubric_version="old"))), "rerank-ab.json has rubric_version"),
    (lambda r: (r / "rerank-ab.json").write_text(json.dumps(ab_report(jev_model="jev-9"))), "rerank-ab.json was produced with Jev model"),
    (lambda r: (r / "rerank-test.json").write_text(json.dumps(gate_report(ranking={}))), "missing required fields"),
])
def test_activate_refuses_without_current_passing_evidence(isolated, reports, setup, reason):
    before = config_bytes(isolated)
    setup(reports)
    result = activate(reports)
    assert result.exit_code == 1
    assert "activate refused:" in result.stderr and reason in result.stderr
    assert config_bytes(isolated) == before


def test_activate_refuses_when_killed(isolated, reports, monkeypatch):
    before = config_bytes(isolated)
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    result = activate(reports)
    assert result.exit_code == 1 and j.KILLED_MESSAGE in result.stderr
    assert config_bytes(isolated) == before


def test_activate_never_turns_judgments_on(isolated, reports):
    path = isolated / ".voss" / "config.yml"
    path.write_text("judgments:\n  enabled: false\n  code_recall: shadow\n")
    before = config_bytes(isolated)
    result = activate(reports)
    assert result.exit_code == 1 and "judgments.enabled is not true" in result.stderr
    assert config_bytes(isolated) == before


def test_activate_shows_evidence_and_no_leaves_config_unchanged(isolated, reports):
    before = config_bytes(isolated)
    result = activate(reports, "n\n")
    assert result.exit_code != 0
    for text in ("0.0412", "0.0105", "recall diff 0.0000", "n 120", "p95 870 ms", "off 0.600", "active 0.700",
                 "regressions 1", MODEL, RUBRIC_VERSION, "sends the task text and candidate code chunks to Jev"):
        assert text in result.output
    assert config_bytes(isolated) == before


def test_activate_yes_edits_only_the_code_recall_line(isolated, reports):
    result = activate(reports, "y\n")
    assert result.exit_code == 0, result.output
    assert config_bytes(isolated).decode() == CONFIG.replace("code_recall: shadow  # trial", "code_recall: active  # trial")


def test_activate_default_answer_is_no(isolated, reports):
    before = config_bytes(isolated)
    result = activate(reports, "\n")
    assert result.exit_code != 0
    assert config_bytes(isolated) == before


def test_activate_already_active_writes_nothing(isolated, reports):
    path = isolated / ".voss" / "config.yml"
    path.write_text("judgments:\n  enabled: true\n  code_recall: active\n")
    before = path.stat().st_mtime_ns
    result = activate(reports, "")
    assert result.exit_code == 0 and "already active" in result.output
    assert path.stat().st_mtime_ns == before


def test_activate_mode_is_active_after_activation(isolated, reports, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    assert j.code_recall_mode(isolated) == "shadow"
    assert activate(reports, "y\n").exit_code == 0
    assert j.code_recall_mode(isolated) == "active"


def test_activate_edit_inserts_after_enabled_when_absent():
    text = "# top\njudgments:\n    enabled: true   # on\n    other: 2\nkeep: [1, 2]\n"
    assert j._set_code_recall_line(text) == "# top\njudgments:\n    enabled: true   # on\n    code_recall: active\n    other: 2\nkeep: [1, 2]\n"


def test_activate_edit_preserves_crlf():
    text = "judgments:\r\n  enabled: true\r\n  code_recall: off\r\nx: 1\r\n"
    assert j._set_code_recall_line(text) == "judgments:\r\n  enabled: true\r\n  code_recall: active\r\nx: 1\r\n"
    assert j._set_code_recall_line("judgments:\r\n  enabled: true\r\n") == "judgments:\r\n  enabled: true\r\n  code_recall: active\r\n"


@pytest.mark.parametrize("text", [
    "judgments: {enabled: true}\n",
    "judgments:\n  enabled: true\n  code_recall: shadow\n  code_recall: off\n",
    "project:\n  judgments:\n    enabled: true\n",
    "judgments:\n  enabled: true\n  code_recall: [unclosed\n",
    "judgments:\n  enabled: true\njudgments:\n  enabled: true\n",
    "judgments:\n  nested:\n    enabled: true\n",
])
def test_activate_edit_refuses_unusual_shapes(text):
    with pytest.raises(ValueError):
        j._set_code_recall_line(text)


def test_activate_cli_refuses_unusual_shape_unchanged(isolated, reports):
    path = isolated / ".voss" / "config.yml"
    path.write_text("judgments: {enabled: true, code_recall: shadow}\n")
    before = config_bytes(isolated)
    result = activate(reports, "y\n")
    assert result.exit_code == 1 and "cannot edit" in result.stderr
    assert config_bytes(isolated) == before


def test_activate_atomic_write_leaves_original_when_replace_fails(isolated, reports, monkeypatch):
    before = config_bytes(isolated)
    mode = 0o640
    os.chmod(isolated / ".voss" / "config.yml", mode)

    def fail(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(j.os, "replace", fail)
    result = activate(reports, "y\n")
    assert result.exit_code != 0
    assert config_bytes(isolated) == before
    assert sorted(p.name for p in (isolated / ".voss").iterdir()) == ["config.yml"]


def test_activate_write_keeps_file_mode(isolated, reports):
    path = isolated / ".voss" / "config.yml"
    os.chmod(path, 0o640)
    assert activate(reports, "y\n").exit_code == 0
    assert path.stat().st_mode & 0o777 == 0o640
    assert sorted(p.name for p in path.parent.iterdir()) == ["config.yml"]
