"""Import `voss eval` runs.jsonl rows as run.v1 records (provenance kept, nothing re-scored)."""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from .spec import CheckResult, ConfigRef, Judge, RunRecord, Usage, VossInfo
from .store import Store


def from_voss_eval_row(row: dict, experiment_id: str) -> RunRecord:
    surface = row.get("surface", "internal")
    ident = json.dumps([surface, row.get("provider"), row.get("model")]).encode()
    tokens = row.get("input_tokens") or None
    return RunRecord(
        experiment_id=experiment_id,
        run_id=uuid.uuid4().hex,
        scenario_id=row["task_id"],
        config=ConfigRef(name=f"voss-eval:{surface}", adapter="voss-eval",
                         sha256=hashlib.sha256(ident).hexdigest()),
        voss=VossInfo(version=row.get("voss_version")),
        model=row.get("model"),
        provider=row.get("provider"),
        live=bool(row.get("live")),
        seed=int(row.get("seed") or 0),
        run_idx=int(row.get("run_idx") or 0),
        started_at=row.get("started_at") or "",
        duration_s=row.get("duration_s"),
        checks=[
            CheckResult(name=c.get("type", "check"), kind="visible", passed=bool(c.get("pass")),
                        detail=str(c.get("detail") or "")[:200])
            for c in row.get("checks") or []
        ],
        usage=Usage(input_tokens=tokens, cost_usd=row.get("cost_usd"),
                    cost_source="voss-eval" if row.get("cost_usd") is not None else None),
        exit_reason="capped" if row.get("capped") else None,
        skipped=bool(row.get("skipped")),
        skip_reason=row.get("skip_reason"),
        judge=Judge(verdict=row["judge_verdict"], confidence=row.get("judge_confidence"),
                    model=row.get("judge_model")) if row.get("judge_verdict") else None,
        evaluator_version="voss-eval",
    )


def import_voss_eval(runs_jsonl: Path, store: Store) -> list[RunRecord]:
    records = [
        from_voss_eval_row(json.loads(line), store.experiment_id)
        for line in runs_jsonl.read_text().splitlines() if line.strip()
    ]
    source = store.put(runs_jsonl.read_bytes())
    for r in records:
        r.artifacts["source_runs_jsonl"] = source
        store.append(r)
    return records
