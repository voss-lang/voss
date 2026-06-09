"""Unit tests for voss/harness/repair.py — the `voss doctor --fix` engine.

Engine policy under test: candidate filtering (non-OK + repairable +
non-MANUAL), tier gating under --yes, exception containment, re-check
verification via REGISTRY, and post-repair result merging.
"""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from voss.harness import diagnostics as diag
from voss.harness import repair as repair_mod
from voss.harness.cli import doctor_cmd


def _check(
    name: str,
    result: diag.CheckResult,
    *,
    repair=None,
    tier: diag.RepairTier = diag.RepairTier.MANUAL,
) -> diag.Check:
    return diag.Check(name, result, id=name, tier=tier, repair=repair)


def _ok_repair() -> diag.RepairResult:
    return diag.RepairResult(ok=True, detail="done")


# ---------------------------------------------------------------------------
# repair_candidates
# ---------------------------------------------------------------------------


class TestRepairCandidates:
    def test_filters_ok_manual_and_unrepairable(self):
        checks = [
            _check("ok", diag.CheckResult.OK, repair=_ok_repair, tier=diag.RepairTier.SAFE),
            _check("manual", diag.CheckResult.WARN, repair=_ok_repair),  # MANUAL tier
            _check("no-repair", diag.CheckResult.FAIL, tier=diag.RepairTier.SAFE),
            _check("safe", diag.CheckResult.WARN, repair=_ok_repair, tier=diag.RepairTier.SAFE),
            _check("confirm", diag.CheckResult.FAIL, repair=_ok_repair, tier=diag.RepairTier.CONFIRM),
        ]
        names = [c.name for c in repair_mod.repair_candidates(checks)]
        assert names == ["safe", "confirm"]


# ---------------------------------------------------------------------------
# execute_repairs
# ---------------------------------------------------------------------------


def _fake_registry(monkeypatch, recheck_result: diag.CheckResult):
    """REGISTRY with one spec ('fixme') whose re-run yields recheck_result."""
    spec = diag.CheckSpec(
        "fixme",
        diag.Category.PROJECT,
        lambda cwd: diag.Check("fixme", recheck_result),
    )
    monkeypatch.setattr(repair_mod, "REGISTRY", (spec,))


class TestExecuteRepairs:
    def test_success_verified_by_recheck(self, monkeypatch, tmp_path: Path):
        _fake_registry(monkeypatch, diag.CheckResult.OK)
        c = _check("fixme", diag.CheckResult.WARN, repair=_ok_repair, tier=diag.RepairTier.SAFE)
        [o] = repair_mod.execute_repairs([c], tmp_path, assume_yes=False)
        assert o.executed
        assert o.result is not None and o.result.ok
        assert o.recheck is not None and o.recheck.result is diag.CheckResult.OK
        assert o.verified

    def test_repair_ok_but_recheck_still_bad_is_not_verified(self, monkeypatch, tmp_path: Path):
        _fake_registry(monkeypatch, diag.CheckResult.WARN)
        c = _check("fixme", diag.CheckResult.WARN, repair=_ok_repair, tier=diag.RepairTier.SAFE)
        [o] = repair_mod.execute_repairs([c], tmp_path, assume_yes=False)
        assert o.executed
        assert not o.verified

    def test_repair_exception_contained(self, monkeypatch, tmp_path: Path):
        _fake_registry(monkeypatch, diag.CheckResult.OK)

        def boom() -> diag.RepairResult:
            raise RuntimeError("kaput")

        c = _check("fixme", diag.CheckResult.FAIL, repair=boom, tier=diag.RepairTier.SAFE)
        [o] = repair_mod.execute_repairs([c], tmp_path, assume_yes=False)
        assert o.executed
        assert o.result is not None and not o.result.ok
        assert "kaput" in o.result.detail
        assert o.recheck is None
        assert not o.verified

    def test_confirm_tier_skipped_under_yes(self, monkeypatch, tmp_path: Path):
        _fake_registry(monkeypatch, diag.CheckResult.OK)
        c = _check("fixme", diag.CheckResult.FAIL, repair=_ok_repair, tier=diag.RepairTier.CONFIRM)
        [o] = repair_mod.execute_repairs([c], tmp_path, assume_yes=True)
        assert not o.executed
        assert "confirm" in o.skipped_reason

    def test_confirm_tier_runs_without_yes(self, monkeypatch, tmp_path: Path):
        _fake_registry(monkeypatch, diag.CheckResult.OK)
        c = _check("fixme", diag.CheckResult.FAIL, repair=_ok_repair, tier=diag.RepairTier.CONFIRM)
        [o] = repair_mod.execute_repairs([c], tmp_path, assume_yes=False)
        assert o.executed
        assert o.verified

    def test_unknown_id_recheck_is_none(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(repair_mod, "REGISTRY", ())
        c = _check("ghost", diag.CheckResult.WARN, repair=_ok_repair, tier=diag.RepairTier.SAFE)
        [o] = repair_mod.execute_repairs([c], tmp_path, assume_yes=False)
        assert o.executed
        assert o.recheck is None
        assert not o.verified


# ---------------------------------------------------------------------------
# merge_results
# ---------------------------------------------------------------------------


class TestMergeResults:
    def test_recheck_replaces_original(self, monkeypatch, tmp_path: Path):
        _fake_registry(monkeypatch, diag.CheckResult.OK)
        bad = _check("fixme", diag.CheckResult.FAIL, repair=_ok_repair, tier=diag.RepairTier.SAFE)
        other = _check("other", diag.CheckResult.OK)
        outcomes = repair_mod.execute_repairs([bad], tmp_path, assume_yes=False)
        merged = repair_mod.merge_results([bad, other], outcomes)
        assert [c.result for c in merged] == [diag.CheckResult.OK, diag.CheckResult.OK]
        assert diag.aggregate_exit_code(merged) == 0

    def test_failed_repair_keeps_original(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(repair_mod, "REGISTRY", ())

        def fail_repair() -> diag.RepairResult:
            return diag.RepairResult(ok=False, detail="nope")

        bad = _check("fixme", diag.CheckResult.FAIL, repair=fail_repair, tier=diag.RepairTier.SAFE)
        outcomes = repair_mod.execute_repairs([bad], tmp_path, assume_yes=False)
        merged = repair_mod.merge_results([bad], outcomes)
        assert merged[0].result is diag.CheckResult.FAIL
        assert diag.aggregate_exit_code(merged) == 1


# ---------------------------------------------------------------------------
# doctor --fix CLI flow
# ---------------------------------------------------------------------------


def _patch_single_warn(monkeypatch, *, tier=diag.RepairTier.SAFE, repair=_ok_repair):
    """All checks OK except harness cache, which is repairable."""
    fns = {
        "check_python_version": lambda: diag.Check("python", diag.CheckResult.OK),
        "check_voss_import": lambda: diag.Check("voss import", diag.CheckResult.OK),
        "check_provider_auth": lambda: diag.Check("provider auth", diag.CheckResult.OK),
        "check_git_on_path": lambda: diag.Check("git", diag.CheckResult.OK),
        "check_cwd_writable": lambda _cwd: diag.Check("cwd writable", diag.CheckResult.OK),
        "check_config_dirs_creatable": lambda: diag.Check("config dirs", diag.CheckResult.OK),
        "check_project_dirs": lambda _cwd: diag.Check("project dirs", diag.CheckResult.OK),
        "check_cognition": lambda _cwd: diag.Check("cognition", diag.CheckResult.OK),
        "check_legacy_sessions": lambda: diag.Check("legacy sessions", diag.CheckResult.OK),
        "check_third_party_skills": lambda _cwd: diag.Check(
            "third-party skills", diag.CheckResult.OK
        ),
        "check_keyring": lambda: diag.Check("keyring", diag.CheckResult.OK),
        "check_codex_auth": lambda: diag.Check("codex auth", diag.CheckResult.OK),
        "check_model_prefs": lambda: diag.Check("model prefs", diag.CheckResult.OK),
        "check_session_store": lambda _cwd: diag.Check("session store", diag.CheckResult.OK),
        "check_toolchain": lambda: diag.Check("toolchain", diag.CheckResult.OK),
    }
    for name, fn in fns.items():
        monkeypatch.setattr(diag, name, fn)
    state = {"fixed": False}

    def do_repair() -> diag.RepairResult:
        state["fixed"] = True
        return repair()

    def cache_check(_cwd):
        if state["fixed"]:
            return diag.Check("harness cache", diag.CheckResult.OK, detail="fresh")
        return diag.Check(
            "harness cache",
            diag.CheckResult.WARN,
            detail="stale",
            fix="voss compile voss/harness/agent/",
            tier=tier,
            repair=do_repair,
        )

    monkeypatch.setattr(diag, "check_harness_cache", cache_check)
    return state


class TestDoctorFixCli:
    def test_fix_with_confirmation_repairs_and_exits_zero(self, monkeypatch, tmp_path: Path):
        state = _patch_single_warn(monkeypatch)
        r = CliRunner().invoke(
            doctor_cmd, ["--cwd", str(tmp_path), "--fix"], input="y\n"
        )
        assert r.exit_code == 0
        assert state["fixed"]
        assert "planned repairs" in r.output
        assert "repaired" in r.output

    def test_fix_declined_runs_nothing(self, monkeypatch, tmp_path: Path):
        state = _patch_single_warn(monkeypatch)
        r = CliRunner().invoke(
            doctor_cmd, ["--cwd", str(tmp_path), "--fix"], input="n\n"
        )
        assert r.exit_code == 0  # WARN-only still exits 0 (D-14)
        assert not state["fixed"]

    def test_fix_yes_runs_safe_without_prompt(self, monkeypatch, tmp_path: Path):
        state = _patch_single_warn(monkeypatch)
        r = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path), "--fix", "--yes"])
        assert r.exit_code == 0
        assert state["fixed"]
        assert "repair(s)?" not in r.output  # no confirmation prompt under --yes

    def test_fix_yes_skips_confirm_tier(self, monkeypatch, tmp_path: Path):
        state = _patch_single_warn(monkeypatch, tier=diag.RepairTier.CONFIRM)
        r = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path), "--fix", "--yes"])
        assert r.exit_code == 0
        assert not state["fixed"]
        assert "skipped" in r.output

    def test_fix_with_nothing_repairable(self, monkeypatch, tmp_path: Path):
        state = _patch_single_warn(monkeypatch)
        monkeypatch.setattr(
            diag, "check_harness_cache",
            lambda _cwd: diag.Check("harness cache", diag.CheckResult.OK),
        )
        r = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path), "--fix"])
        assert r.exit_code == 0
        assert "no machine-repairable issues" in r.output
        assert not state["fixed"]

    def test_without_fix_never_repairs(self, monkeypatch, tmp_path: Path):
        state = _patch_single_warn(monkeypatch)
        r = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert r.exit_code == 0
        assert not state["fixed"]
        assert "planned repairs" not in r.output


# ---------------------------------------------------------------------------
# repair_harness_cache (real repair, failure path)
# ---------------------------------------------------------------------------


def test_repair_harness_cache_no_sources(tmp_path: Path):
    res = diag.repair_harness_cache(tmp_path)
    assert not res.ok
    assert "no .voss sources" in res.detail


def test_repair_model_prefs_prunes_dangling(monkeypatch, tmp_path: Path):
    import json

    from voss.harness import model_catalog, model_prefs, model_router

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    p = model_prefs.prefs_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {"recent": [["prov", "live"], ["prov", "gone"]], "favorites": [["prov", "gone"]]}
        )
    )
    monkeypatch.setattr(model_catalog, "_read_cache", lambda _p: ({"d": 1}, 1.0))
    monkeypatch.setattr(model_catalog, "parse_catalog", lambda _d: [])
    monkeypatch.setattr(
        model_router,
        "find_entry",
        lambda _g, _prov, model_id: object() if model_id == "live" else None,
    )

    res = diag.repair_model_prefs()
    assert res.ok
    assert "pruned 2" in res.detail
    assert model_prefs.recent() == [("prov", "live")]
    assert model_prefs.favorites() == []
