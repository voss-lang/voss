import json
import shutil
from pathlib import Path

import pytest

from voss_proofs import adapters, workspace
from voss_proofs.cli import main
from voss_proofs.ingest import import_voss_eval
from voss_proofs.report import compare, render, wilson
from voss_proofs.runner import run_experiment, run_one
from voss_proofs.spec import BUILTIN_CONFIGS, SCHEMAS, load_bench, load_config, load_spec
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


def test_workspace_diff_includes_new_files_and_ignores_voss_runtime_state(tmp_path):
    ws = workspace.prepare(REGRESSION / "reg-py-005-leap-year-trap", "t")
    try:
        (ws.repo / "new_module.py").write_text("x = 1\n")
        (ws.repo / ".voss" / "sessions").mkdir(parents=True)
        (ws.repo / ".voss" / "sessions" / "s.json").write_text("{}")
        assert workspace.changed_paths(ws.repo) == ["new_module.py"]
    finally:
        ws.cleanup()
