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
from voss_proofs.review import ReviewDataError, import_review, read_review, render as render_review, summarize as summarize_review
from voss_proofs.spec import CmdCheck, BUILTIN_CONFIGS, SCHEMAS, Config, load_bench, load_config, load_spec
from voss_proofs.store import Store, read_runs

ROOT = Path(__file__).resolve().parents[1]
REGRESSION = ROOT / "benchmarks" / "regression"
VOSS_SUITES = ROOT.parent / "tests" / "eval"
LOCKED_REVIEW = ROOT.parent / "evals" / "review-locked-2"
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


@pytest.mark.skipif(not LOCKED_REVIEW.is_dir(), reason="J4 review sets not checked out alongside")
def test_review_import_reproduces_the_locked_report_and_shows_both_acceptance_rates(tmp_path):
    store = Store(tmp_path / "rv")
    records = import_review(LOCKED_REVIEW, "test", store)
    assert read_review(store.root) == records
    summary = summarize_review(records)
    voss = json.loads((LOCKED_REVIEW / "reports" / "review-test.json").read_text())["metrics"]
    jev = summary["jev"]["pairs"]
    for ours, theirs in [("false_supported", "false_supported"), ("contradicted_recall", "contradicted_recall"),
                         ("abstention", "abstention")]:
        assert (jev[ours]["k"], jev[ours]["n"]) == (voss[theirs]["k"], voss[theirs]["n"]), ours
    assert jev["brier"] == pytest.approx(voss["brier"])
    b_passes = json.loads((LOCKED_REVIEW / "reports" / "review-compare.json").read_text())["reviewer_b_passes"]
    assert (summary["reviewer-b"]["false_accept"]["k"], summary["reviewer-b"]["false_accept"]["n"]) == (
        b_passes["k"], b_passes["n"])
    reject_all = summary["reject-all"]
    assert reject_all["false_accept"]["rate"] == 0 and reject_all["true_accept"]["rate"] == 0
    assert summary["reviewer-b"]["pairs"] is None and summary["reviewer-b"]["confidence_mean"] is not None
    text = render_review(records, "t")
    assert "true accept" in text and "underpowered" in text


@pytest.mark.skipif(not LOCKED_REVIEW.is_dir(), reason="J4 review sets not checked out alongside")
def test_review_import_refuses_fixtures_changed_after_freeze(tmp_path):
    root = tmp_path / "set"
    shutil.copytree(LOCKED_REVIEW, root)
    fixture = next((root / "fixtures").glob("*.jsonl"))
    fixture.write_text(fixture.read_text().replace('"gold": "contradicted"', '"gold": "supported"', 1))
    with pytest.raises(ReviewDataError, match="changed since freeze"):
        import_review(root, "test", Store(tmp_path / "rv"))


def test_review_dev_run_needs_live_and_never_reruns_a_locked_split(tmp_path):
    with pytest.raises(SystemExit, match="--live"):
        main(["import-review", str(tmp_path), "--split", "dev", "--run-dev", "--out", str(tmp_path / "o")])
    with pytest.raises(SystemExit, match="dev split only"):
        main(["import-review", str(tmp_path), "--split", "test", "--run-dev", "--live", "--out", str(tmp_path / "o")])


def test_judge_needs_a_live_config():
    with pytest.raises(ValueError, match="live"):
        Config(name="x", adapter="oracle", judge="jev")


def test_jev_judge_sees_only_visible_checks_and_never_overrides_verification(tmp_path):
    seen = tmp_path / "seen.json"
    fake = tmp_path / "voss"
    fake.write_text(f"""#!{sys.executable}
import json, pathlib, sys
args = sys.argv[1:]
checks = json.loads(pathlib.Path(args[args.index("--checks") + 1]).read_text())
criteria = pathlib.Path(args[args.index("--criteria-file") + 1]).read_text().split("\\n")
pathlib.Path({str(seen)!r}).write_text(json.dumps({{"hidden": pathlib.Path("hidden").exists(), "checks": checks}}))
ids = [f"AC-{{n}}" for n, line in enumerate(filter(None, criteria), 1)]
print(json.dumps({{"status": "answered", "model_returned": "jev-fake", "cost_usd": 0.0001,
                  "answers": {{c: {{"probabilities": {{"supported": 0.95, "contradicted": 0.0,
                                                      "insufficient_evidence": 0.05}}}} for c in ids}},
                  "detail": {{"labels": {{c: "supported" for c in ids}}}}}}))
""")
    fake.chmod(0o755)
    config = Config(name="null-jev", adapter="null", live=True, judge="jev", voss_bin=str(fake))
    task_dir, spec = _task("reg-py-005-leap-year-trap")
    store = Store(tmp_path / "exp")
    rec = run_one(task_dir, spec, config, store, run_idx=0, seed=0)
    store.append(rec)
    saw = json.loads(seen.read_text())
    assert saw["hidden"] is False
    assert saw["checks"] and all(c["name"] in {ch.run for ch in spec.checks} for c in saw["checks"])
    assert rec.judge.verdict == "accept" and rec.verified is False
    assert rec.judge.cost_usd == 0.0001 and "judge_receipt" in rec.artifacts
    text = render(read_runs(store.root), "t")
    assert "| null-jev | jev review | 1/1 = 100.0%" in text
