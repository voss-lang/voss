"""V12-03 factory fallback audit (VSAFE-05).

Additive, redacted evidence for every safety strict-procedure route; old run
records without the field stay readable; capability audit semantics unchanged.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
from types import SimpleNamespace

from voss.harness.agent import _invoke_step_with_gate
from voss.harness.cognition_schemas import SafetyConfig
from voss.harness.permissions import PermissionGate
from voss.harness.recorder import RunRecorder
from voss.harness.session import RunRecord
from voss.harness.tools import ToolEntry
from voss_runtime import ToolDescriptor


# --- Task 1: recorder + RunRecord -------------------------------------------


def test_observe_factory_fallback_appends_full_event() -> None:
    rec = RunRecorder.start()
    rec.observe_factory_fallback(
        "shell_run",
        label="factory_only_operation",
        classes=["deploy"],
        trigger_rule="git-push",
        runbook="prod-deploy",
        pipeline=None,
        actor_role="backend",
        actor_model_tier="strong",
        confirmation_required=False,
        confirmed=False,
        outcome="denied",
        args={"cmd": "git push origin main"},
    )
    assert len(rec.factory_fallbacks) == 1
    ev = rec.factory_fallbacks[0]
    assert ev["label"] == "factory_only_operation"
    assert ev["classes"] == ["deploy"]
    assert ev["trigger_rule"] == "git-push"
    assert ev["runbook"] == "prod-deploy"
    assert ev["actor_role"] == "backend"
    assert ev["outcome"] == "denied"


def test_factory_fallback_redacts_secret_args() -> None:
    rec = RunRecorder.start()
    rec.observe_factory_fallback(
        "shell_run",
        label="factory_only_operation",
        runbook="prod-deploy",
        args={"cmd": "deploy", "token": "supersecret-value"},
    )
    ev = rec.factory_fallbacks[0]
    assert "supersecret-value" not in json.dumps(ev["args"])


def test_observe_factory_fallback_never_raises_on_bad_args() -> None:
    rec = RunRecorder.start()
    rec.observe_factory_fallback(
        "x", label="factory_only_path", args=None  # type: ignore[arg-type]
    )
    assert rec.factory_fallbacks[0]["args"] is None


def test_finalize_forwards_factory_fallbacks(tmp_path) -> None:
    rec = RunRecorder.start()
    rec.observe_factory_fallback("shell_run", label="latency_pipeline", pipeline="fast-path")
    record = rec.finalize(tmp_path, cost_usd=0.0, exit_reason="done")
    assert len(record.factory_fallbacks) == 1
    assert record.factory_fallbacks[0]["pipeline"] == "fast-path"


def test_run_record_factory_fallbacks_defaults_empty() -> None:
    rr = RunRecord(id="a", started_at="t0", ended_at="t1")
    assert rr.factory_fallbacks == []


def test_old_run_record_without_factory_fallbacks_hydrates() -> None:
    # Simulate an old persisted run JSON that predates the field.
    old_dict = {
        "id": "deadbeef",
        "started_at": "2026-01-01T00:00:00+00:00",
        "ended_at": "2026-01-01T00:01:00+00:00",
        "goal": "legacy",
        "capability_invocations": [{"name": "fs_read"}],
    }
    rr = RunRecord(**old_dict)
    assert rr.factory_fallbacks == []
    # round-trips back out with the additive field present
    assert "factory_fallbacks" in dataclasses.asdict(rr)


# --- Task 2: wiring through the tool invocation path ------------------------


class _NullRenderer:
    def show_tool_call(self, *a, **k):
        return None


def _entry(name: str, *, is_mutating: bool, result: str = "RESULT") -> ToolEntry:
    async def invoke(**kwargs):
        return result

    desc = ToolDescriptor(
        name=name,
        description="stub",
        parameters={"type": "object", "properties": {}, "required": []},
        func=invoke,
    )
    return ToolEntry(descriptor=desc, is_mutating=is_mutating, group="shell", scope_requirements=("shell",))


def _policy() -> SafetyConfig:
    return SafetyConfig.model_validate(
        {
            "runbooks": [{"name": "prod-deploy", "steps": ["plan", "apply"]}],
            "factory_only_operations": [
                {
                    "id": "git-push",
                    "tool": "shell_run",
                    "pattern": "git push *",
                    "runbook": "prod-deploy",
                    "classes": ["deploy"],
                }
            ],
        }
    )


def test_safety_denied_call_records_both_rows() -> None:
    tools = {"shell_run": _entry("shell_run", is_mutating=True)}
    gate = PermissionGate(mode="auto", auto_yes=True, safety_policy=_policy())
    rec = RunRecorder.start()
    step = SimpleNamespace(name="shell_run", args={"cmd": "git push origin main"})
    out = asyncio.run(_invoke_step_with_gate(step, tools, gate, _NullRenderer(), rec))
    assert out.startswith("<denied:")
    # both the capability denial row AND the factory fallback row exist
    assert len(rec.capability_invocations) == 1
    assert rec.capability_invocations[0]["ok"] is False
    assert len(rec.factory_fallbacks) == 1
    fb = rec.factory_fallbacks[0]
    assert fb["runbook"] == "prod-deploy"
    assert fb["outcome"] == "denied"


def test_normal_call_records_no_factory_fallback() -> None:
    tools = {"shell_run": _entry("shell_run", is_mutating=True)}
    gate = PermissionGate(mode="auto", auto_yes=True, safety_policy=_policy())
    rec = RunRecorder.start()
    step = SimpleNamespace(name="shell_run", args={"cmd": "echo hello"})
    out = asyncio.run(_invoke_step_with_gate(step, tools, gate, _NullRenderer(), rec))
    assert out == "RESULT"
    assert rec.factory_fallbacks == []
    assert len(rec.capability_invocations) == 1


def test_no_safety_policy_records_no_factory_fallback() -> None:
    tools = {"shell_run": _entry("shell_run", is_mutating=True)}
    gate = PermissionGate(mode="auto", auto_yes=True)  # no safety policy
    rec = RunRecorder.start()
    step = SimpleNamespace(name="shell_run", args={"cmd": "git push origin main"})
    asyncio.run(_invoke_step_with_gate(step, tools, gate, _NullRenderer(), rec))
    assert rec.factory_fallbacks == []


def test_audit_report_exposes_factory_marker_field() -> None:
    from voss.harness.audit.model import AuditReport, AuditSnapshot, Leak6Assessment

    snap = AuditSnapshot(
        root_id="r",
        nodes=(),
        cards=(),
        kills=(),
        rescopes=(),
        routings=(),
        verdicts=(),
        liveness=(),
        leak6=Leak6Assessment(status="ok", evidence="", mitigation_present=True),
    )
    rep = AuditReport(
        run_id="r",
        idea="i",
        principles=(),
        team_config={},
        snapshot=snap,
        review_sidecars={},
        run_final=None,
        signoff_ack=None,
        calibration=_dummy_calibration(),
        sections_missing=(),
    )
    assert rep.factory_fallbacks == ()  # defaults empty → old snapshots hydrate


def _dummy_calibration():
    from voss.harness.audit.model import CalibrationReport

    return CalibrationReport(
        total_pairs=0,
        false_pass_count=0,
        slop_rejection_count=0,
        false_pass_rate=0.0,
        slop_rejection_rate=0.0,
        spot_audit_paths=(),
    )
