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

from . import __version__, sealed, workspace
from .adapters import ADAPTERS, AdapterResult
from .evaluate import EVALUATOR_VERSION, jev_review, run_check, scope_check, verdict
from .spec import BenchmarkSpec, Config, ConfigRef, RunRecord, Usage, scenario_id
from .store import Store


class BudgetExceeded(Exception):
    pass


def config_ref(config: Config) -> ConfigRef:
    sha = hashlib.sha256(config.model_dump_json().encode()).hexdigest()
    return ConfigRef(name=config.name, adapter=config.adapter, sha256=sha)


def contamination(artifacts: dict[str, str], store: Store, task_dir: Path) -> list[str]:
    """Signs the system read the benchmark's own files: its source path or answer file names in what it produced."""
    needles = [str(task_dir.resolve().parent), "reference.patch", sealed.SEALED]
    found = []
    for name, sha in sorted(artifacts.items()):
        text = store.get(sha).decode(errors="replace")
        found += [f"{name} mentions {n}" for n in needles if n in text]
    return found


def _merge(steps: list[AdapterResult]) -> AdapterResult:
    if len(steps) == 1:
        return steps[0]
    last = steps[-1]
    failed = next((r for r in steps if r.exit_reason != "done"), None)

    def total(key: str):
        values = [getattr(r.usage, key) for r in steps]
        return None if all(v is None for v in values) else sum(v or 0 for v in values)

    costs = [r.usage.cost_usd for r in steps]
    return AdapterResult(
        final=last.final,
        exit_reason=(failed or last).exit_reason,
        claimed_complete=last.claimed_complete if failed is None else None,
        usage=Usage(
            input_tokens=total("input_tokens"), output_tokens=total("output_tokens"),
            cache_creation_tokens=total("cache_creation_tokens"), cache_read_tokens=total("cache_read_tokens"),
            cost_usd=None if None in costs else sum(costs),
            cost_source="; ".join(sorted({r.usage.cost_source for r in steps if r.usage.cost_source})) or None,
        ),
        model=last.model, provider=last.provider, voss=last.voss,
        artifacts={f"{k}:step{n}": v for n, r in enumerate(steps, 1) for k, v in r.artifacts.items()},
        errors=[f"step {n}: {e}" for n, r in enumerate(steps, 1) for e in r.errors],
        session_id=last.session_id,
    )


def run_steps(spec: BenchmarkSpec, task_dir: Path, ws, env: dict[str, str], config: Config,
              store: Store) -> AdapterResult:
    """Run the prompt and each follow-up step in the same workspace. Oracle and null act once."""
    prompts = [spec.prompt, *spec.steps]
    if config.adapter in ("oracle", "null"):
        prompts = prompts[-1:]
    results: list[AdapterResult] = []
    for prompt in prompts:
        step = spec.model_copy(update={"prompt": prompt})
        resume = results[-1].session_id if results and config.memory == "resume" else None
        try:
            result = ADAPTERS[config.adapter](step, task_dir, ws, env, config, store,
                                              **({"resume": resume} if resume else {}))
        except Exception as exc:  # noqa: BLE001 - a crashed adapter is a recorded failed run
            result = AdapterResult(exit_reason="error", errors=[f"{type(exc).__name__}: {str(exc)[:300]}"])
        results.append(result)
        if result.exit_reason != "done":
            break
    return _merge(results)


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
        result = run_steps(spec, task_dir, ws, env, config, store)
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
        if config.judge == "jev":
            record.judge, ref = jev_review(spec.acceptance.criteria, checks, ws.repo, ws.root, env,
                                           config.voss_bin, store)
            if ref:
                record.artifacts["judge_receipt"] = ref
        if scope := scope_check(changed, spec.acceptance.allowed_paths):
            checks.append(scope)
        record.contamination = contamination(record.artifacts, store, task_dir)
        with sealed.answers(task_dir) as src:
            workspace.install_hidden(src, ws.repo)
        checks += [run_check(c, ws.repo, env, "hidden", store) for c in spec.hidden_checks]
        record.checks = checks
        record.verified = False if result.exit_reason == "error" else verdict(checks)
    finally:
        ws.cleanup()
    return record


def run_experiment(bench: list[tuple[Path, BenchmarkSpec]], configs: list[Config], store: Store,
                   *, k: int = 1, seed: int = 0, max_runs: int | None = None,
                   max_usd: float | None = None, log=print, frozen: dict | None = None) -> list[RunRecord]:
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
        "freeze": frozen and {k: frozen[k] for k in ("sha256", "frozen_at", "commit", "locked")},
    })
    records, spent = [], 0.0
    for n, (task_dir, spec, config, i) in enumerate(jobs, 1):
        if max_usd is not None and spent >= max_usd:
            log(f"stopping: known spend ${spent:.4f} reached --max-usd {max_usd}")
            break
        rec = run_one(task_dir, spec, config, store, run_idx=i, seed=seed)
        spent += (rec.usage.cost_usd or 0.0) + ((rec.judge and rec.judge.cost_usd) or 0.0)
        store.append(rec)
        records.append(rec)
        status = "skip" if rec.skipped else {True: "verified", False: "FAILED", None: "unknown"}[rec.verified]
        log(f"[{n}/{len(jobs)}] {rec.scenario_id} x {config.name}#{i}: {status}")
    return records
