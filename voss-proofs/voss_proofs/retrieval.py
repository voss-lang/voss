"""J3 code-recall retrieval set: frozen-hash check and import of a finished rerank report."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .review import ReviewDataError
from .store import Store


def verify_freeze(root: Path) -> dict:
    frozen = json.loads((root / "freeze.json").read_text())
    paths = [root / "corpus.json"] + [p for sub in ("queries", "baseline", "labels")
                                      for p in sorted((root / sub).rglob("*")) if p.is_file()]
    actual = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    if actual != frozen["files"]:
        raise ReviewDataError(f"{root}: query, baseline or label files changed since freeze.json was written")
    return frozen


def import_retrieval(root: Path, split: str, store: Store) -> dict:
    """Copy a finished rerank report's results, after checking the set is unchanged. Nothing is re-scored."""
    root = root.resolve()
    frozen = verify_freeze(root)
    path = root / "reports" / f"rerank-{split}.json"
    report = json.loads(path.read_text()) if path.exists() else {}
    if report.get("status") != "complete" or report.get("commit") != frozen["commit"]:
        raise ReviewDataError(f"{path}: needs a complete run on the frozen commit")
    summary = {
        "dataset": root.name, "split": split, "commit": frozen["commit"],
        "rubric_version": report["rubric_version"], "model": report["model"], "run_date": report["run_date"],
        "ranking": report["ranking"], "latency": report["latency"], "passed": report["passed"],
        "thresholds": frozen["thresholds"], "queries": frozen["splits"][split]["queries"],
    }
    store.write_manifest({
        "experiment_id": store.experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv,
        "dataset": str(root),
        "freeze_files": frozen["files"],
        "artifacts": {"report": store.put(path.read_bytes())},
        "summary": summary,
    })
    return summary


def render(s: dict) -> str:
    r, lat = s["ranking"], s["latency"]
    return "\n".join([
        f"# Code recall reranking: {s['dataset']} ({s['split']})", "",
        f"Frozen at `{s['commit'][:12]}`, rubric `{s['rubric_version']}`, model `{s['model']}`, run {s['run_date']}. "
        f"{s['queries']} queries. Imported from the finished run; nothing was re-scored.", "",
        "| measure | value | release threshold |", "|---|---|---|",
        f"| nDCG@5 gain over the stored baseline ranking | {r['mean_gain']:+.3f} "
        f"(paired bootstrap 95% CI {r['ci_low']:+.3f} to {r['ci_high']:+.3f}) "
        f"| ≥ {s['thresholds']['ndcg_gain_min']} with CI lower bound > 0 |",
        f"| recall@5 (files) difference | {r['recall_diff']:+.3f} | drop ≤ {s['thresholds']['recall_drop_max']} |",
        f"| latency p50 / p95 | {lat['p50_ms']:.0f} / {lat['p95_ms']:.0f} ms over {lat['n']} calls "
        f"| J3 latency check {'passed' if lat['passed'] else 'failed'} |",
        f"| J3 release gate | {'passed' if s['passed'] else 'failed'} | |", "",
        "This measures one memory component: how well Voss ranks code for a query. It says nothing about whether "
        "memory carries facts from one task to the next. The memory sequence scenarios measure that.", "",
    ])
