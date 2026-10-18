"""Experiment execution: scenarios x configs x k, isolated, evidence-recorded."""
from __future__ import annotations

import hashlib
import random
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, workspace
from .adapters import ADAPTERS, AdapterResult
from .evaluate import EVALUATOR_VERSION, run_check, scope_check, verdict
from .spec import BenchmarkSpec, Config, ConfigRef, RunRecord, scenario_id
from .store import Store


class BudgetExceeded(Exception):
    pass


def config_ref(config: Config) -> ConfigRef:
    sha = hashlib.sha256(config.model_dump_json().encode()).hexdigest()
    return ConfigRef(name=config.name, adapter=config.adapter, sha256=sha)


def run_one(task_dir: Path, spec: BenchmarkSpec, config: Config, store: Store,
            *, run_idx: int, seed: int) -> RunRecord:
    sid = scenario_id(task_dir, spec)
    meta = spec.meta
    record = RunRecord(
        experiment_id=store.experiment_id,
        run_id=uuid.uuid4().hex,
        scenario_id=sid,
        scenario_version=meta.version if meta else 1,
        scenario_sha256=workspace.scenario_hash(task_dir),
        dataset=meta.dataset if meta else None,
        category=meta.category if meta else None,
        synthetic=meta.synthetic if meta else None,
        config=config_ref(config),
        live=config.live,
        seed=seed,
        run_idx=run_idx,
        started_at=datetime.now(timezone.utc).isoformat(),
        evaluator_version=EVALUATOR_VERSION,
        budget=spec.budget,
    )
    missing = [tool for tool in spec.requires if shutil.which(tool) is None]
    if missing:
        record.skipped, record.skip_reason = True, "missing toolchain: " + ", ".join(missing)
        return record

    ws = workspace.prepare(task_dir, sid)
    t0 = time.monotonic()
    try:
        env = workspace.env(ws, live=config.live)
        try:
            result = ADAPTERS[config.adapter](spec, task_dir, ws, env, config, store)
        except Exception as exc:  # noqa: BLE001 - a crashed adapter is a recorded failed run
            result = AdapterResult(exit_reason="error", errors=[f"{type(exc).__name__}: {str(exc)[:300]}"])
        record.duration_s = round(time.monotonic() - t0, 3)
        record.exit_reason = result.exit_reason
        record.claimed_complete = result.claimed_complete
        record.usage = result.usage
        record.model, record.provider, record.voss = result.model, result.provider, result.voss
        record.errors = result.errors
        record.artifacts = dict(result.artifacts)
        record.artifacts["diff"] = store.put(workspace.diff(ws.repo))
        if result.final:
            record.artifacts["final"] = store.put(result.final)
        changed = workspace.changed_paths(ws.repo)

        checks = [run_check(c, ws.repo, env, "visible", store) for c in spec.checks]
        if scope := scope_check(changed, spec.acceptance.allowed_paths):
            checks.append(scope)
        workspace.install_hidden(task_dir, ws.repo)
        checks += [run_check(c, ws.repo, env, "hidden", store) for c in spec.hidden_checks]
        record.checks = checks
        record.verified = False if result.exit_reason == "error" else verdict(checks)
    finally:
        ws.cleanup()
    return record


def run_experiment(bench: list[tuple[Path, BenchmarkSpec]], configs: list[Config], store: Store,
                   *, k: int = 1, seed: int = 0, max_runs: int | None = None,
                   max_usd: float | None = None, log=print) -> list[RunRecord]:
    jobs = [(t, s, c, i) for t, s in bench for c in configs for i in range(k)]
    random.Random(seed).shuffle(jobs)
    if max_runs is not None and len(jobs) > max_runs:
        raise BudgetExceeded(f"{len(jobs)} runs planned, --max-runs is {max_runs}")
    store.write_manifest({
        "experiment_id": store.experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "proofs_version": __version__,
        "python": sys.version.split()[0],
        "argv": sys.argv,
        "k": k,
        "seed": seed,
        "configs": {c.name: {**config_ref(c).model_dump(), "body": c.model_dump()} for c in configs},
        "scenarios": {scenario_id(t, s): workspace.scenario_hash(t) for t, s in bench},
    })
    records, spent = [], 0.0
    for n, (task_dir, spec, config, i) in enumerate(jobs, 1):
        if max_usd is not None and spent >= max_usd:
            log(f"stopping: known spend ${spent:.4f} reached --max-usd {max_usd}")
            break
        rec = run_one(task_dir, spec, config, store, run_idx=i, seed=seed)
        spent += rec.usage.cost_usd or 0.0
        store.append(rec)
        records.append(rec)
        status = "skip" if rec.skipped else {True: "verified", False: "FAILED", None: "unknown"}[rec.verified]
        log(f"[{n}/{len(jobs)}] {rec.scenario_id} x {config.name}#{i}: {status}")
    return records
