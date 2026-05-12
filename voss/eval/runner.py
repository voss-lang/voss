"""Evaluation suite runner for `voss eval` (M5)."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from voss import __version__ as VOSS_VERSION
from voss.harness import auth as auth_mod
from voss.harness.agent import run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.render import PlainRenderer
from voss.harness.session import SessionRecord, load, save
from voss.harness.tools import make_toolset
from voss_runtime import EpisodicMemory, get_config
from voss_runtime.providers import StubProvider, get as get_provider
from voss_runtime.providers.base import ModelProvider

from .judge import judge_run
from .suite import TaskSpec, load_suite

SUITE_ROOT = Path("tests/eval")
RESUME_CANCEL_DELAY_S = float(os.environ.get("EVAL_RESUME_CANCEL_DELAY_S", "0.05"))
NO_CREDS_MESSAGE = "voss eval: no provider creds — pass --stub for hermetic smoke or run /login"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _prepare_fixture(task_dir: Path, tmp: Path) -> Path:
    cwd = tmp / "fixture"
    shutil.copytree(task_dir / "fixture", cwd)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=cwd, check=True)
    subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=eval@voss",
            "-c",
            "user.name=eval",
            "commit",
            "-q",
            "-m",
            "init",
        ],
        cwd=cwd,
        check=True,
    )
    return cwd


def _file_diff(cwd: Path) -> str:
    completed = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout if completed.returncode == 0 else ""


def _extract_signals(record: SessionRecord) -> tuple[float | None, float | None]:
    total = 0.0
    saw_cost = False
    confidence: float | None = None
    for run in record.runs:
        cost = run.get("cost_usd")
        if isinstance(cost, (int, float)) and cost > 0:
            total += float(cost)
            saw_cost = True
        plan = run.get("plan")
        if confidence is None and isinstance(plan, dict):
            value = plan.get("confidence")
            if isinstance(value, (int, float)):
                confidence = float(value)
    return (total if saw_cost else None), confidence


def _append_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _record_model(model: str | None) -> str:
    return model or get_config().default_model


def _add_run(record: SessionRecord, result) -> None:
    if result.run is None:
        return
    record.runs.append(asdict(result.run))
    record.total_cost_usd += result.cost_usd


async def _drive_resume(
    record: SessionRecord,
    spec: TaskSpec,
    *,
    cwd: Path,
    provider: ModelProvider,
    model: str | None,
    permissions: PermissionGate,
) -> tuple[SessionRecord, str]:
    history = EpisodicMemory(capacity=40)
    task = asyncio.create_task(
        run_turn(
            spec.prompt,
            tools=make_toolset(cwd),
            cwd=cwd,
            renderer=PlainRenderer(),
            model=model,
            provider=provider,
            history=history,
            permissions=permissions,
            session_id=record.id,
        )
    )
    await asyncio.sleep(RESUME_CANCEL_DELAY_S)
    task.cancel()
    try:
        result = await task
        _add_run(record, result)
    except asyncio.CancelledError:
        pass

    save(record, history)
    record, history = load(record.id, cwd=cwd)
    result = await run_turn(
        spec.prompt,
        tools=make_toolset(cwd),
        cwd=cwd,
        renderer=PlainRenderer(),
        model=model,
        provider=provider,
        history=history,
        permissions=permissions,
        session_id=record.id,
    )
    _add_run(record, result)
    return record, result.final


async def _drive_task(
    task_id: str,
    spec: TaskSpec,
    *,
    cwd: Path,
    provider: ModelProvider,
    model: str | None,
) -> tuple[SessionRecord, str, bool]:
    record = SessionRecord.new(cwd=cwd, model=_record_model(model), name=task_id)
    permissions = PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)
    try:
        if task_id.startswith("05-"):
            record, final = await _drive_resume(
                record,
                spec,
                cwd=cwd,
                provider=provider,
                model=model,
                permissions=permissions,
            )
        else:
            result = await run_turn(
                spec.prompt,
                tools=make_toolset(cwd),
                cwd=cwd,
                renderer=PlainRenderer(),
                model=model,
                provider=provider,
                permissions=permissions,
                session_id=record.id,
            )
            _add_run(record, result)
            final = result.final
    except Exception:  # noqa: BLE001 - eval records failures as rows
        return record, "", True
    return record, final, False


def _provider_for_eval(*, stub: bool, auth_pref: str) -> tuple[ModelProvider, auth_mod.Resolution | None]:
    if stub:
        return StubProvider(), None
    res = auth_mod.resolve(auth_pref, role="runner")
    if res.source == "none":
        click.echo(NO_CREDS_MESSAGE, err=True)
        raise click.exceptions.Exit(code=2)
    return get_provider(), res


def _judge_provider_for_eval(*, auth_pref: str) -> ModelProvider | None:
    res = auth_mod.resolve(auth_pref, role="judge")
    if res.source == "none":
        return None
    return get_provider()


def _write_summary_if_available(out: Path, rows: list[dict[str, Any]]) -> None:
    try:
        from .summary import write_summary  # type: ignore
    except ImportError:
        return
    write_summary(out, rows)


def run_suite(
    *,
    suite: str = "golden",
    stub: bool = False,
    live: bool = False,
    k: int = 1,
    out: Path | None = None,
    out_dir: Path | None = None,
    judge_model: str | None = None,
    task: str | None = None,
    task_id: str | None = None,
    auth_pref: str = "auto",
    model: str | None = None,
) -> Path:
    del live
    project_root = Path.cwd()
    out = out or out_dir or project_root / ".voss" / "eval" / _now_iso().replace(":", "")
    task = task or task_id
    suite_root = project_root / SUITE_ROOT / suite
    tasks = load_suite(suite_root, suite=suite)
    if task is not None:
        tasks = [(task_id, spec) for task_id, spec in tasks if task_id == task]

    provider, _ = _provider_for_eval(stub=stub, auth_pref=auth_pref)
    judge_provider = _judge_provider_for_eval(auth_pref=auth_pref)
    model_eff = "__stub__" if stub else model
    judge_model_eff = judge_model or model_eff or get_config().default_model

    runs_path = out / "runs.jsonl"
    rows: list[dict[str, Any]] = []
    if runs_path.exists():
        runs_path.unlink()

    for task_id, spec in tasks:
        for run_idx in range(k):
            started_at = _now_iso()
            start = time.monotonic()
            with tempfile.TemporaryDirectory(prefix=f"voss-eval-{task_id}-") as tmp:
                cwd = _prepare_fixture(suite_root / task_id, Path(tmp))
                record, final, crashed = asyncio.run(
                    _drive_task(
                        task_id,
                        spec,
                        cwd=cwd,
                        provider=provider,
                        model=model_eff,
                    )
                )
                diff = _file_diff(cwd)
                cost_usd, confidence = _extract_signals(record)

                verdict = None
                judge_verdict = "skipped"
                if not crashed and judge_provider is not None:
                    verdict, judge_verdict = asyncio.run(
                        judge_run(
                            provider=judge_provider,
                            model=judge_model_eff,
                            task_prompt=spec.prompt,
                            final=final,
                            file_diff=diff if "file_diff" in spec.judge_inputs else "",
                            rubric=spec.rubric,
                        )
                    )

                row = {
                    "task_id": task_id,
                    "run_idx": run_idx,
                    "success": False if crashed else (verdict.verdict == "pass" if verdict else None),
                    "cost_usd": cost_usd,
                    "confidence": confidence,
                    "duration_s": round(time.monotonic() - start, 3),
                    "judge_verdict": judge_verdict,
                    "judge_confidence": verdict.confidence if verdict else 0.0,
                    "judge_rationale": (
                        verdict.rationale if verdict else ("agent crashed" if crashed else "")
                    ),
                    "provider": provider.__class__.__name__,
                    "model": model_eff,
                    "judge_model": judge_model_eff,
                    "seed": run_idx,
                    "voss_version": VOSS_VERSION,
                    "started_at": started_at,
                }
                rows.append(row)
                _append_row(runs_path, row)

    _write_summary_if_available(out, rows)
    return out
