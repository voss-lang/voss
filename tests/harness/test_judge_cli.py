from dataclasses import asdict
import json

import httpx
import pytest
from click.testing import CliRunner

from voss.harness import judgments as j
from voss.harness.cli import AGENT_COMMANDS
from voss_runtime.judgments import JevClient, JudgmentResult, parse_response


def response_body(request):
    answers = {}
    for qid, question in json.loads(request.content)["questions"].items():
        if question["type"] == "choice":
            options = list(question["criteria"])
            probabilities = {option: 0.12 / (len(options) - 1) for option in options}
            probabilities[options[0]] = 0.88
            answers[qid] = {"type": "choice", "choice": options[0], "probabilities": probabilities, "confidence": 0.81}
        elif question["type"] == "score":
            probabilities = {str(i): float(i == 1) for i in range(len(question["criteria"]))}
            answers[qid] = {"type": "score", "score": 1.0, "probabilities": probabilities, "confidence": 1.0}
        else:
            answers[qid] = {"type": "noul", "noul": 0.95}
    return {"model": "jev-1.13.0", "answers": answers, "usage": {"input_tokens": 10, "output_tokens": 0}}


@pytest.fixture(autouse=True)
def isolated_judgments(monkeypatch, tmp_path):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.setattr(j.auth, "load_provider_key", lambda env_key: None)
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def transport(monkeypatch):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=response_body(request))

    def make(key):
        return JevClient(key, model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000, max_calls=4, max_cost_usd=0.01, client=httpx.AsyncClient(transport=httpx.MockTransport(handler)), clock=lambda: 1.0)

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(j, "make_client", make)
    return seen


def test_command_registered():
    from voss.cli import main

    assert j.judge_cmd in AGENT_COMMANDS and j.judge_cmd.name == "judge"
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "judge" in result.output


def test_demo(transport):
    result = CliRunner().invoke(j.judge_cmd, ["--demo"])
    assert result.exit_code == 0, result.output
    assert len(transport) == 1
    questions = json.loads(transport[0].content)["questions"]
    assert [q["type"] for q in questions.values()] == ["choice", "score", "noul"]


def test_main_judge_resolves_keychain_without_startup_bridge(transport, monkeypatch):
    from voss.cli import main

    monkeypatch.delenv("TYPESAFE_API_KEY")
    lookups = []
    monkeypatch.setattr(j.auth, "load_provider_key", lambda key: lookups.append(key) or "keychain-test-key")
    monkeypatch.setattr(j, "bridge_judgments_env", lambda: pytest.fail("startup bridge must not run"))
    result = CliRunner().invoke(main, ["judge", "--demo"])
    assert result.exit_code == 0, result.output
    assert lookups == ["TYPESAFE_API_KEY"]
    assert len(transport) == 1
    assert transport[0].headers["Authorization"] == "Bearer keychain-test-key"
    assert "keychain-test-key" not in result.output


def test_request_file(transport, tmp_path):
    payload = {"state": {"code": "return 1"}, "questions": {"pick": {"type": "choice", "instructions": "Pick", "criteria": {"a": None, "b": "B"}}}}
    path = tmp_path / "request.json"
    path.write_text(json.dumps(payload))
    result = CliRunner().invoke(j.judge_cmd, [str(path)])
    assert result.exit_code == 0, result.output
    sent = json.loads(transport[0].content)
    assert sent["state"] == payload["state"] and sent["questions"] == payload["questions"]


@pytest.mark.parametrize("content", [
    "not JSON", "[]", '{"state": "x"}', '{"state":"x","questions":{}}',
    '{"questions":{"q":{"type":"noul","instructions":"?"}}}',
    '{"state":"x","questions":{"q":{"type":"rank","instructions":"?"}}}',
    '{"state":"x","questions":{"q":{"type":"choice","instructions":"?","criteria":{"one":null}}}}',
    '{"state":"x","questions":{"q":{"type":"noul"}}}',
    '{"state":"x","questions":{"q":{"type":[],"instructions":"?"}}}',
    '{"state":NaN,"questions":{"q":{"type":"noul","instructions":"?"}}}',
])
def test_request_file_invalid(transport, tmp_path, content):
    path = tmp_path / "request.json"
    path.write_text(content)
    result = CliRunner().invoke(j.judge_cmd, [str(path)])
    assert result.exit_code == 1, result.output
    assert "invalid request file" in result.stderr
    assert transport == []


def test_table_output(transport):
    result = CliRunner().invoke(j.judge_cmd, ["--demo"])
    assert result.exit_code == 0
    for text in ("next_step", "risk", "needs_tests", "run_tests", "0.880", "edit_code", "ask_user", "insufficient_evidence", "score", "1.000", "P(yes)", "0.950", "0.050", "jev-1.13.0", "in 10", "out 0", "ms", "attempts 1", "$"):
        assert text in result.stdout


def test_json_output(transport):
    result = CliRunner().invoke(j.judge_cmd, ["--demo", "--json"])
    assert result.exit_code == 0, result.output
    _, questions = j.demo_request()
    answers, model, input_tokens, output_tokens = parse_response(response_body(transport[0]), questions)
    expected = JudgmentResult(answers, model, input_tokens, output_tokens, 0.0, 10 * 0.042 / 1_000_000, 1)
    assert json.loads(result.stdout) == asdict(expected)


def test_judge_ignores_project_flag(transport, tmp_path):
    (tmp_path / ".voss").mkdir()
    (tmp_path / ".voss" / "config.yml").write_text("judgments:\n  enabled: false\n")
    result = CliRunner().invoke(j.judge_cmd, ["--demo"])
    assert result.exit_code == 0 and len(transport) == 1


def test_judge_killed(transport, monkeypatch):
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    result = CliRunner().invoke(j.judge_cmd, ["--demo"])
    assert result.exit_code == 1 and j.KILLED_MESSAGE in result.stderr
    assert transport == []


def test_missing_key(monkeypatch):
    monkeypatch.setattr(j, "make_client", lambda key: pytest.fail("must not dispatch"))
    result = CliRunner().invoke(j.judge_cmd, ["--demo"])
    assert result.exit_code == 1
    assert j.MISSING_KEY_MESSAGE in result.stderr


def test_usage_errors(tmp_path):
    path = tmp_path / "request.json"
    path.write_text("{}")
    assert CliRunner().invoke(j.judge_cmd, []).exit_code == 2
    assert CliRunner().invoke(j.judge_cmd, [str(path), "--demo"]).exit_code == 2


def test_failure_outcome(transport, monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(529, headers={"Retry-After": "0"})

    monkeypatch.setattr(j, "make_client", lambda key: JevClient(key, model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000, max_calls=4, max_cost_usd=0.01, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))))
    result = CliRunner().invoke(j.judge_cmd, ["--demo"])
    assert result.exit_code == 1 and "unavailable" in result.stderr
    assert result.stdout == "" and len(calls) == 2
