import json
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from voss_proofs import adapters, workspace
from voss_proofs.cli import main
from voss_proofs.evaluate import run_check
from voss_proofs.ingest import import_voss_eval
from voss_proofs.report import compare, render, wilson
from voss_proofs.runner import run_experiment, run_one
from voss_proofs.spec import CmdCheck, BUILTIN_CONFIGS, SCHEMAS, Config, load_bench, load_config, load_spec
from voss_proofs.store import Store, read_runs

ROOT = Path(__file__).resolve().parents[1]
REGRESSION = ROOT / "benchmarks" / "regression"
VOSS_SUITES = ROOT.parent / "tests" / "eval"
ORACLE, NULL = BUILTIN_CONFIGS["oracle"], BUILTIN_CONFIGS["null"]


def _task(name):
    task_dir = REGRESSION / name
    return task_dir, load_spec(task_dir)


@pytest.mark.skipif(not VOSS_SUITES.is_dir(), reason="voss eval suites not checked out alongside")
@pytest.mark.parametrize("suite", ["golden", "matrix", "surfaces"])
def test_existing_voss_eval_tasks_load_unchanged(suite):
    tasks = load_bench(VOSS_SUITES / suite)
    assert tasks, suite


def test_regression_scenarios_carry_provenance_and_hidden_tests():
    for task_dir, spec in load_bench(REGRESSION):
        assert spec.meta and spec.meta.synthetic and spec.meta.origin, task_dir.name
        assert spec.hidden_checks and (task_dir / "hidden").is_dir(), task_dir.name
        assert (task_dir / "reference.patch").is_file(), task_dir.name


def test_hidden_tests_and_secrets_are_absent_while_the_system_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-leak")
    seen = {}

    def spy(spec, task_dir, ws, env, config, store):
        seen["hidden"] = (ws.repo / "hidden").exists()
        seen["home"] = env["HOME"]
        seen["key"] = env.get("OPENAI_API_KEY")
        return adapters.AdapterResult(exit_reason="done")

    monkeypatch.setitem(adapters.ADAPTERS, "null", spy)
    task_dir, spec = _task("reg-py-005-leap-year-trap")
    rec = run_one(task_dir, spec, NULL, Store(tmp_path / "exp"), run_idx=0, seed=0)
    assert seen["hidden"] is False
    assert seen["key"] is None
    assert Path(seen["home"]) != Path.home()
    assert any(c.kind == "hidden" for c in rec.checks)


def test_visible_pass_is_not_verification_when_hidden_tests_fail(tmp_path):
    task_dir, spec = _task("reg-py-005-leap-year-trap")
    rec = run_one(task_dir, spec, NULL, Store(tmp_path / "exp"), run_idx=0, seed=0)
    by_kind = {c.kind: c.passed for c in rec.checks}
    assert by_kind["visible"] is True and by_kind["hidden"] is False
    assert rec.verified is False


def test_out_of_scope_edit_fails_verification_even_when_tests_pass(tmp_path, monkeypatch):
    def overreach(spec, task_dir, ws, env, config, store):
        result = adapters.oracle(spec, task_dir, ws, env, config, store)
        (ws.repo / "legacy_report.py").write_text("# cleaned up\n")
        return result

    monkeypatch.setitem(adapters.ADAPTERS, "oracle", overreach)
    task_dir, spec = _task("reg-py-004-pagination-scope")
    rec = run_one(task_dir, spec, ORACLE, Store(tmp_path / "exp"), run_idx=0, seed=0)
    scope = next(c for c in rec.checks if c.kind == "scope")
    assert not scope.passed and "legacy_report.py" in scope.detail
    assert all(c.passed for c in rec.checks if c.kind != "scope")
    assert rec.claimed_complete is True and rec.verified is False


def test_repeated_experiments_produce_identical_outcomes(tmp_path):
    bench = [_task("reg-py-001-items-endpoint"), _task("reg-py-002-slugify-regression")]
    runs = []
    for name in ("a", "b"):
        store = Store(tmp_path / name)
        run_experiment(bench, [ORACLE, NULL], store, k=2, log=lambda _: None)
        runs.append(read_runs(store.root))
    assert len(runs[0]) == 8
    assert compare(*runs) == []
    assert {r.verified for r in runs[0] if r.config.name == "oracle"} == {True}
    assert {r.verified for r in runs[0] if r.config.name == "null"} == {False}
    manifest = json.loads((tmp_path / "a" / "manifest.json").read_text())
    assert set(manifest["scenarios"]) == {"reg-py-001-items-endpoint", "reg-py-002-slugify-regression"}


def test_artifacts_are_content_addressed(tmp_path):
    task_dir, spec = _task("reg-py-002-slugify-regression")
    store = Store(tmp_path / "exp")
    rec = run_one(task_dir, spec, ORACLE, store, run_idx=0, seed=0)
    diff = store.get(rec.artifacts["diff"]).decode()
    assert diff == (task_dir / "reference.patch").read_text()


def test_wilson_interval_matches_reference_values():
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-4)
    lo, hi = wilson(5, 10)
    assert (lo, hi) == (pytest.approx(0.2366, abs=1e-4), pytest.approx(0.7634, abs=1e-4))


def test_voss_eval_rows_import_with_unknown_cost_kept_missing(tmp_path):
    store = Store(tmp_path / "imported")
    records = import_voss_eval(ROOT / "tests" / "fixtures" / "voss_eval_stub_runs.jsonl", store)
    assert [r.scenario_id for r in records] == ["01-analyze", "02-plan-only"]
    assert all(r.usage.cost_usd is None and r.verified is None for r in records)
    assert records[0].checks[0].passed is False
    assert "unknown cost" in render(read_runs(store.root), "t")


def test_live_configs_require_explicit_opt_in():
    with pytest.raises(SystemExit, match="--live"):
        main(["run", "--bench", str(REGRESSION), "--config", "voss-serve-auto",
              "--configs-dir", str(ROOT / "configs")])
    with pytest.raises(SystemExit, match="--max-runs"):
        main(["run", "--bench", str(REGRESSION), "--config", "voss-serve-auto", "--live",
              "--configs-dir", str(ROOT / "configs")])


def test_committed_schemas_match_models():
    for name, model in SCHEMAS.items():
        committed = json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text())
        assert committed == model.model_json_schema(), name


@pytest.mark.skipif(shutil.which("voss") is None, reason="voss not installed")
def test_voss_serve_fake_turn_records_events_without_a_model(tmp_path):
    config = load_config("voss-serve-fake", ROOT / "configs")
    task_dir, spec = _task("reg-py-005-leap-year-trap")
    store = Store(tmp_path / "exp")
    rec = run_one(task_dir, spec, config, store, run_idx=0, seed=0)
    assert rec.errors == []
    events = [json.loads(line) for line in store.get(rec.artifacts["events"]).decode().splitlines()]
    assert events[-1]["type"] == "session.idle"
    assert rec.usage.cost_usd is None
    assert rec.voss and rec.voss.version
    assert rec.verified is False


def test_workspace_diff_includes_new_files_and_ignores_runtime_and_build_state(tmp_path):
    ws = workspace.prepare(REGRESSION / "reg-py-005-leap-year-trap", "t")
    try:
        (ws.repo / "new_module.py").write_text("x = 1\n")
        (ws.repo / ".voss" / "sessions").mkdir(parents=True)
        (ws.repo / ".voss" / "sessions" / "s.json").write_text("{}")
        (ws.repo / "__pycache__").mkdir()
        (ws.repo / "__pycache__" / "m.cpython-313.pyc").write_bytes(b"\0")
        (ws.repo / ".voss-cache").mkdir()
        (ws.repo / ".voss-cache" / "index.db").write_bytes(b"\0")
        assert workspace.changed_paths(ws.repo) == ["new_module.py"]
    finally:
        ws.cleanup()


def test_turn_routed_to_ambient_chat_is_reported_not_counted_as_done():
    ambient = [{"type": "status", "phase": "ambient"},
               {"type": "stream.delta", "text": "\n[error: provider missing]\n"},
               {"type": "session.idle"}]
    assert adapters.turn_problems(ambient) == ["[error: provider missing]", adapters.NO_RUN]
    ran = [{"type": "status", "phase": "run"}, {"type": "status", "phase": "ambient"}]
    assert adapters.turn_problems(ran) == []


def test_zero_cost_reported_for_a_token_using_run_is_recorded_as_unknown():
    record = {"runs": [{"exit_reason": "done", "iterations": [
        {"prompt_tokens": 2, "completion_tokens": 389,
         "cache_creation_input_tokens": 213233, "cache_read_input_tokens": 10}]}]}
    res = adapters.AdapterResult()
    res.usage.cost_usd, res.usage.cost_source = 0.0, "serve:/cost"
    adapters.usage_from_record(record, res)
    assert res.usage.cost_usd is None and res.usage.cost_source.startswith("unknown")
    assert (res.usage.cache_creation_tokens, res.usage.cache_read_tokens) == (213233, 10)
    assert res.claimed_complete is True


def test_hidden_files_planted_by_the_system_are_replaced_before_grading(tmp_path, monkeypatch):
    def plant(spec, task_dir, ws, env, config, store):
        (ws.repo / "hidden").mkdir()
        (ws.repo / "hidden" / "__init__.py").write_text(
            "import calendar_utils\n"
            "calendar_utils.is_leap_year = lambda y: y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)\n"
        )
        return adapters.AdapterResult(exit_reason="done")

    monkeypatch.setitem(adapters.ADAPTERS, "null", plant)
    task_dir, spec = _task("reg-py-005-leap-year-trap")
    rec = run_one(task_dir, spec, NULL, Store(tmp_path / "exp"), run_idx=0, seed=0)
    assert next(c for c in rec.checks if c.kind == "hidden").passed is False
    assert rec.verified is False


def test_crashing_adapter_is_recorded_and_the_experiment_continues(tmp_path, monkeypatch):
    def crash(*args):
        raise FileNotFoundError("no such voss binary")

    monkeypatch.setitem(adapters.ADAPTERS, "null", crash)
    store = Store(tmp_path / "exp")
    bench = [_task("reg-py-005-leap-year-trap")]
    records = run_experiment(bench, [NULL, ORACLE], store, log=lambda _: None)
    crashed = next(r for r in records if r.config.name == "null")
    assert crashed.exit_reason == "error" and crashed.verified is False
    assert "FileNotFoundError" in crashed.errors[0]
    assert next(r for r in records if r.config.name == "oracle").verified is True


def test_check_timeout_kills_the_whole_process_group(tmp_path):
    check = CmdCheck(type="cmd", run="sleep 30 & echo $! > child.pid; wait", timeout=1)
    result = run_check(check, tmp_path, {"PATH": "/bin:/usr/bin"}, "visible", Store(tmp_path / "s"))
    assert result.passed is False and result.detail == "timeout 1s"
    child = int((tmp_path / "child.pid").read_text())
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        os.kill(child, 9)
        pytest.fail("timed-out check left its child process running")


def test_wall_budget_timeout_is_not_overwritten_by_the_session_record():
    res = adapters.AdapterResult(exit_reason="timeout")
    adapters.usage_from_record({"runs": [{"exit_reason": "done", "iterations": []}]}, res)
    assert res.exit_reason == "timeout" and res.claimed_complete is False


def test_sse_heartbeats_reach_the_deadline_check_but_are_not_recorded():
    class Stream:
        def iter_lines(self):
            yield from [": ping - 2026-10-17", "", "event: final", 'data: {"text": "hi"}', ""]

    events = list(adapters._sse(Stream()))
    assert events[0] is adapters.PING
    assert events[1] == {"type": "final", "text": "hi"}


FAKE_AGENT = """#!{python}
import json, os, pathlib, sys, time
name = pathlib.Path(sys.argv[0]).name
pathlib.Path({seen!r}).write_text(json.dumps({{"argv": sys.argv[1:], "stdin": sys.stdin.read(),
    "env": sorted(k for k in os.environ if k.startswith(("CLAUDE", "CODEX_COMPANION")))}}))
if os.environ.get("FAKE_SLEEP"):
    time.sleep(60)
pathlib.Path("leap.py").write_text("def is_leap_year(y):\\n    return y % 4 == 0\\n")
if name == "claude":
    print(json.dumps({{"subtype": "success", "is_error": False, "result": "done", "total_cost_usd": 0.12,
                      "usage": {{"input_tokens": 3, "output_tokens": 40, "cache_creation_input_tokens": 900,
                                "cache_read_input_tokens": 5000}}, "modelUsage": {{"claude-x": {{}}}}}}))
else:
    print(json.dumps({{"type": "item.completed", "item": {{"type": "agent_message", "text": "fixed"}}}}))
    print(json.dumps({{"type": "turn.completed", "usage": {{"input_tokens": 100, "cached_input_tokens": 60,
                                                         "output_tokens": 7}}}}))
"""


@pytest.fixture
def fake_agents(tmp_path, monkeypatch):
    seen = tmp_path / "seen.json"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name in ("claude", "codex"):
        (bindir / name).write_text(FAKE_AGENT.format(python=sys.executable, seen=str(seen)))
        (bindir / name).chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "parent")
    return seen


def test_cli_claude_runs_sandboxed_without_user_settings_or_the_parent_session(tmp_path, fake_agents):
    config = load_config("cli-claude", ROOT / "configs")
    task_dir, spec = _task("reg-py-005-leap-year-trap")
    rec = run_one(task_dir, spec, config, Store(tmp_path / "exp"), run_idx=0, seed=0)
    seen = json.loads(fake_agents.read_text())
    assert "bypassPermissions" not in seen["argv"] and "acceptEdits" in seen["argv"]
    assert json.loads(seen["argv"][seen["argv"].index("--settings") + 1])["sandbox"]["enabled"] is True
    assert seen["argv"][seen["argv"].index("--setting-sources") + 1] == "project,local"
    assert "--strict-mcp-config" in seen["argv"] and seen["env"] == []
    assert rec.claimed_complete is True and rec.verified is False
    assert (rec.usage.cache_creation_tokens, rec.usage.cost_usd, rec.model) == (900, 0.12, "claude-x")


def test_cli_codex_gets_closed_stdin_and_unknown_cost(tmp_path, fake_agents):
    config = load_config("cli-codex", ROOT / "configs")
    task_dir, spec = _task("reg-py-005-leap-year-trap")
    rec = run_one(task_dir, spec, config, Store(tmp_path / "exp"), run_idx=0, seed=0)
    seen = json.loads(fake_agents.read_text())
    assert seen["stdin"] == "" and "workspace-write" in seen["argv"]
    assert rec.claimed_complete is True and rec.usage.input_tokens == 100
    assert rec.usage.cost_usd is None and "unknown" in rec.usage.cost_source


def test_cli_agent_wall_budget_kills_the_agent(tmp_path, fake_agents, monkeypatch):
    monkeypatch.setenv("FAKE_SLEEP", "1")
    task_dir, spec = _task("reg-py-005-leap-year-trap")
    spec = spec.model_copy(update={"budget": spec.budget.model_copy(update={"wall_s": 1})})
    t0 = time.monotonic()
    rec = run_one(task_dir, spec, load_config("cli-claude", ROOT / "configs"), Store(tmp_path / "exp"),
                  run_idx=0, seed=0)
    assert time.monotonic() - t0 < 30
    assert rec.exit_reason == "timeout" and rec.claimed_complete is None and rec.verified is False


def test_cli_agent_config_names_its_agent():
    with pytest.raises(ValueError, match="agent"):
        Config(name="x", adapter="cli-agent")
    with pytest.raises(ValueError, match="agent"):
        Config(name="x", adapter="null", agent="claude")


@pytest.mark.skipif(shutil.which("voss") is None, reason="voss not installed")
def test_voss_swarm_records_a_failed_task_split_as_an_error_not_a_claim(tmp_path):
    task_dir, spec = _task("reg-py-004-pagination-scope")
    store = Store(tmp_path / "exp")
    rec = run_one(task_dir, spec, load_config("voss-swarm-fake", ROOT / "configs"), store, run_idx=0, seed=0)
    assert rec.exit_reason == "error" and rec.claimed_complete is False and rec.verified is False
    assert any("decompose_failed" in e for e in rec.errors)
    assert json.loads(store.get(rec.artifacts["swarm"]))["swarm"]["goal"] == spec.prompt
