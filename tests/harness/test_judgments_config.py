import pytest

from voss.harness import config as harness_config


@pytest.fixture(autouse=True)
def isolated_judgments(monkeypatch):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.setattr("voss.harness.auth.load_provider_key", lambda env_key: None)


def _write_global(text):
    path = harness_config.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_defaults():
    assert harness_config.get_judgments_config() == {
        "model": "jev-1.13.0", "timeout_ms": 5000, "max_calls_per_turn": 4,
        "max_request_bytes": 24000, "max_cost_usd": 0.01,
    }


def test_overrides():
    _write_global('[judgments]\nmodel = "jev-latest"\ntimeout_ms = 1500 # deadline\nmax_calls_per_turn = 2\nmax_request_bytes = 8000\nmax_cost_usd = 0.02\n')
    assert harness_config.get_judgments_config() == {
        "model": "jev-latest", "timeout_ms": 1500, "max_calls_per_turn": 2,
        "max_request_bytes": 8000, "max_cost_usd": 0.02,
    }


@pytest.mark.parametrize("key,value", [
    ("timeout_ms", "0"), ("timeout_ms", "-5"), ("max_calls_per_turn", '"x"'),
    ("max_request_bytes", "1.5"), ("max_cost_usd", "0"), ("max_cost_usd", "-1"),
    ("max_cost_usd", "nan"), ("max_cost_usd", "inf"), ("model", '""'),
])
def test_bad_values_warn(key, value):
    _write_global(f"[judgments]\n{key} = {value}\n")
    with pytest.warns(RuntimeWarning, match=key):
        assert harness_config.get_judgments_config()[key] == harness_config.JUDGMENTS_DEFAULTS[key]


def test_no_global_enabled_key():
    _write_global("[judgments]\nenabled = true\ncode_recall = active\nreview = shadow\n")
    assert harness_config.get_judgments_config() == harness_config.JUDGMENTS_DEFAULTS


def test_other_sections_unaffected():
    _write_global("[instructions]\nbudget_tokens = 1234\n[judgments]\ntimeout_ms = 1500\n")
    assert harness_config.get_instructions_config()["budget_tokens"] == 1234
    assert harness_config.get_judgments_config()["timeout_ms"] == 1500


def _write_project(root, enabled):
    path = root / ".voss" / "config.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"judgments:\n  enabled: {str(enabled).lower()}\n")


@pytest.mark.parametrize("value", ["off", "OFF", "0", "false", " Off "])
def test_kill_switch_precedence(monkeypatch, tmp_path, value):
    from voss.harness import judgments as j
    from voss_runtime.judgments import JudgmentError

    _write_project(tmp_path, True)
    monkeypatch.setenv("VOSS_JUDGMENTS", value)
    monkeypatch.setattr(j.auth, "load_provider_key", lambda key: pytest.fail("key lookup forbidden"))
    monkeypatch.setattr(j, "make_client", lambda key: pytest.fail("client forbidden"))
    assert j.judgments_state(tmp_path) == "killed"
    for explicit in (True, False):
        with pytest.raises(JudgmentError, match=j.KILLED_MESSAGE) as caught:
            j.open_client(tmp_path, explicit=explicit)
        assert caught.value.outcome == "disabled"


def test_key_alone_not_enabled(monkeypatch, tmp_path):
    from voss.harness import judgments as j

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    assert j.judgments_state(tmp_path) == "disabled"
    monkeypatch.setenv("VOSS_JUDGMENTS", "on")
    assert j.judgments_state(tmp_path) == "disabled"
    _write_project(tmp_path, True)
    assert j.judgments_state(tmp_path) == "enabled"


def test_key_order(monkeypatch):
    from voss.harness import judgments as j

    calls = []
    monkeypatch.setattr(j.auth, "load_provider_key", lambda key: calls.append(key) or "kc-value")
    monkeypatch.setenv("TYPESAFE_API_KEY", " env-value ")
    assert j.resolve_api_key() == ("env-value", "env")
    assert calls == []
    monkeypatch.delenv("TYPESAFE_API_KEY")
    assert j.resolve_api_key() == ("kc-value", "keychain")
    assert calls == ["TYPESAFE_API_KEY"]
    monkeypatch.setenv("TYPESAFE_API_KEY", "   ")
    assert j.resolve_api_key() == ("kc-value", "keychain")
    monkeypatch.setattr(j.auth, "load_provider_key", lambda key: None)
    assert j.resolve_api_key() is None


def test_no_key_no_call(monkeypatch, tmp_path):
    from voss.harness import judgments as j
    from voss_runtime.judgments import JudgmentError

    monkeypatch.setattr(j, "make_client", lambda key: pytest.fail("client forbidden"))
    monkeypatch.setattr(j, "resolve_api_key", lambda: pytest.fail("lookup forbidden"))
    with pytest.raises(JudgmentError) as caught:
        j.open_client(tmp_path, explicit=False)
    assert caught.value.outcome == "disabled"
    monkeypatch.setattr(j, "resolve_api_key", lambda: None)
    _write_project(tmp_path, True)
    for explicit in (True, False):
        with pytest.raises(JudgmentError) as caught:
            j.open_client(tmp_path, explicit=explicit)
        assert caught.value.outcome == "unavailable"
        assert str(caught.value) == j.MISSING_KEY_MESSAGE


def test_explicit_ignores_project_flag(monkeypatch, tmp_path):
    from voss.harness import judgments as j

    client = object()
    _write_project(tmp_path, False)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(j, "make_client", lambda key: client)
    assert j.open_client(tmp_path, explicit=True) is client


def test_make_client_uses_config():
    from voss.harness import judgments as j

    _write_global('[judgments]\nmodel = "jev-latest"\ntimeout_ms = 1500\nmax_calls_per_turn = 2\nmax_request_bytes = 8000\nmax_cost_usd = 0.02\n')
    client = j.make_client("test-key")
    assert (client.model, client.timeout_ms, client.max_calls, client.max_request_bytes, client.max_cost_usd) == ("jev-latest", 1500, 2, 8000, 0.02)
    assert client._client is None


def _doctor(tmp_path, *args):
    from click.testing import CliRunner
    from voss.harness.cli import doctor_cmd

    return CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path), "--only", "judgments", *args])


def test_doctor_offline(monkeypatch, tmp_path):
    import json
    from voss.harness import judgments as j

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(j, "make_client", lambda key: pytest.fail("offline must not call"))
    result = _doctor(tmp_path, "--json")
    assert result.exit_code == 0, result.output
    checks = json.loads(result.stdout)["checks"]
    assert len(checks) == 1 and checks[0]["id"] == "judgments"
    assert checks[0]["status"] == "OK"
    assert checks[0]["detail"] == "key env; project disabled; model jev-1.13.0"
    assert "test-key" not in result.output


def test_doctor_offline_keychain_and_missing(monkeypatch, tmp_path):
    from voss.harness import judgments as j, diagnostics as diag

    monkeypatch.setattr(j.auth, "load_provider_key", lambda key: "kc-value")
    assert "key keychain" in diag.check_judgments(tmp_path).detail
    monkeypatch.setattr(j.auth, "load_provider_key", lambda key: None)
    check = diag.check_judgments(tmp_path)
    assert check.result is diag.CheckResult.OK and "key not set" in check.detail
    _write_project(tmp_path, True)
    check = diag.check_judgments(tmp_path)
    assert check.result is diag.CheckResult.WARN and j.MISSING_KEY_MESSAGE in check.detail


def test_doctor_killed(monkeypatch, tmp_path):
    from voss.harness import judgments as j, diagnostics as diag

    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    monkeypatch.setattr(j, "resolve_api_key", lambda: pytest.fail("disabled must not read key"))
    check = diag.check_judgments(tmp_path)
    assert check.result is diag.CheckResult.OK and check.detail == j.KILLED_MESSAGE


@pytest.fixture
def doctor_transport(monkeypatch):
    import httpx
    from tests.harness.test_judge_cli import response_body
    from voss.harness import judgments as j
    from voss_runtime.judgments import JevClient

    calls = []
    status = [200]

    def handler(request):
        calls.append(request)
        return httpx.Response(status[0], json=response_body(request))

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(j, "make_client", lambda key: JevClient(key, model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000, max_calls=4, max_cost_usd=0.01, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))))
    return calls, status


def test_doctor_live(doctor_transport, tmp_path):
    import json

    calls, _ = doctor_transport
    result = _doctor(tmp_path, "--live", "--json")
    assert result.exit_code == 0, result.output
    check = json.loads(result.stdout)["checks"][-1]
    assert (check["id"], check["status"], check["category"]) == ("judgments-live", "OK", "auth")
    assert "jev-1.13.0; tokens in 10 out 0;" in check["detail"]
    assert len(calls) == 1
    questions = json.loads(calls[0].content)["questions"]
    assert len(questions) == 1 and questions["probe"]["type"] == "noul"


def test_doctor_live_missing_key(monkeypatch, tmp_path):
    import json
    from voss.harness import judgments as j

    monkeypatch.setattr(j, "make_client", lambda key: pytest.fail("no key must not call"))
    result = _doctor(tmp_path, "--live", "--json")
    assert result.exit_code == 1, result.output
    check = json.loads(result.stdout)["checks"][-1]
    assert check["status"] == "FAIL" and check["detail"] == j.MISSING_KEY_MESSAGE


def test_doctor_live_killed(doctor_transport, monkeypatch, tmp_path):
    import json
    from voss.harness import judgments as j

    calls, _ = doctor_transport
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    result = _doctor(tmp_path, "--live", "--json")
    assert result.exit_code == 0, result.output
    check = json.loads(result.stdout)["checks"][-1]
    assert check["status"] == "WARN" and j.KILLED_MESSAGE in check["detail"]
    assert calls == []


def test_doctor_live_failure(doctor_transport, tmp_path):
    import json

    calls, status = doctor_transport
    status[0] = 401
    result = _doctor(tmp_path, "--live", "--json")
    assert result.exit_code == 1, result.output
    check = json.loads(result.stdout)["checks"][-1]
    assert check["status"] == "FAIL" and check["detail"].startswith("unavailable")
    assert len(calls) == 1


def test_key_never_leaks(monkeypatch, tmp_path, caplog):
    import asyncio
    import logging
    import traceback
    import httpx
    from click.testing import CliRunner
    from tests.harness.test_judge_cli import response_body
    from voss.harness import judgments as j
    from voss_runtime.judgments import JevClient, JudgmentError

    sentinel = "tsk-SENTINEL-9f3c-DO-NOT-PRINT"
    monkeypatch.setenv("TYPESAFE_API_KEY", sentinel)
    caplog.set_level(logging.DEBUG)
    status = [200]
    clients, outputs = [], []

    def handler(request):
        if status[0] != 200:
            return httpx.Response(status[0], text=f"{sentinel} ECHO-ME-BODY")
        return httpx.Response(200, json=response_body(request))

    def make(key):
        client = JevClient(key, model="jev-1.13.0", timeout_ms=5000, max_request_bytes=24000, max_calls=4, max_cost_usd=0.01, client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        clients.append(client)
        return client

    monkeypatch.setattr(j, "make_client", make)
    runner = CliRunner()
    for code, args in ((200, ["--demo"]), (200, ["--demo", "--json"]), (401, ["--demo"]), (500, ["--demo"])):
        status[0] = code
        result = runner.invoke(j.judge_cmd, args)
        assert result.exit_code == (0 if code == 200 else 1), result.output
        outputs.extend([result.stdout, result.stderr])
    for code, args in ((200, []), (200, ["--json", "--live"]), (401, ["--live"])):
        status[0] = code
        result = _doctor(tmp_path, *args)
        assert result.exit_code == (0 if code == 200 else 1), result.output
        outputs.extend([result.stdout, result.stderr])
    state, questions = j.demo_request()
    with pytest.raises(JudgmentError) as caught:
        asyncio.run(make(sentinel).evaluate(state, questions))
    outputs.extend([str(caught.value), repr(caught.value), "".join(traceback.format_exception(caught.value))])
    monkeypatch.delenv("TYPESAFE_API_KEY")
    monkeypatch.setattr(j.auth, "load_provider_key", lambda key: sentinel)
    for args in ([], ["--json"]):
        result = _doctor(tmp_path, *args)
        assert result.exit_code == 0
        outputs.extend([result.stdout, result.stderr])
    outputs.extend(repr(client) for client in clients)
    outputs.append(caplog.text)
    assert all(sentinel not in output and "ECHO-ME-BODY" not in output for output in outputs)
