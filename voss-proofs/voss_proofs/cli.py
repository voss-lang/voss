"""`proofs` command line."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .ingest import import_voss_eval
from .report import compare, write_report
from .runner import BudgetExceeded, run_experiment
from .spec import BUILTIN_CONFIGS, SCHEMAS, load_bench, load_config, scenario_id
from .store import Store, read_runs


def _bench(args) -> list:
    bench = load_bench(Path(args.bench))
    if args.task:
        bench = [(d, s) for d, s in bench if scenario_id(d, s) in args.task or d.name in args.task]
    if not bench:
        sys.exit(f"no scenarios found in {args.bench}")
    return bench


def _out(arg: str | None) -> Path:
    return Path(arg) if arg else Path("results") / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def cmd_run(args) -> int:
    configs = [load_config(n, Path(args.configs_dir)) for a in args.config for n in a.split(",") if n]
    live = [c.name for c in configs if c.live]
    if live and not args.live:
        sys.exit(f"configs {live} call live models; pass --live (and --max-runs) to opt in")
    if live and args.max_runs is None:
        sys.exit("live runs need an explicit --max-runs cap")
    store = Store(_out(args.out))
    try:
        run_experiment(_bench(args), configs, store, k=args.k, seed=args.seed,
                       max_runs=args.max_runs, max_usd=args.max_usd)
    except BudgetExceeded as exc:
        sys.exit(str(exc))
    print(f"report: {write_report(store.root)}")
    return 0


def cmd_validate(args) -> int:
    """Every scenario must be solvable (oracle verified) and non-trivial (null not verified)."""
    with tempfile.TemporaryDirectory(prefix="proofs-validate-") as tmp:
        store = Store(Path(tmp) / "validate")
        records = run_experiment(_bench(args), [BUILTIN_CONFIGS["oracle"], BUILTIN_CONFIGS["null"]],
                                 store, log=lambda _: None)
    bad = []
    for r in records:
        if r.skipped:
            print(f"skip  {r.scenario_id}: {r.skip_reason}")
            continue
        expected = r.config.name == "oracle"
        if r.verified is not expected:
            failing = [c.name for c in r.checks if not c.passed]
            bad.append(f"{r.scenario_id}: {r.config.name} verified={r.verified} "
                       f"(expected {expected}) errors={r.errors} failing={failing}")
    ok = sorted({r.scenario_id for r in records if not r.skipped} - {b.split(":")[0] for b in bad})
    for sid in ok:
        print(f"ok    {sid}")
    for b in bad:
        print(f"BAD   {b}")
    return 1 if bad else 0


def cmd_report(args) -> int:
    print(write_report(Path(args.results)))
    return 0


def cmd_compare(args) -> int:
    diffs = compare(read_runs(Path(args.a)), read_runs(Path(args.b)))
    for d in diffs:
        print(d)
    print(f"{len(diffs)} outcome differences")
    return 1 if diffs else 0


def cmd_import(args) -> int:
    store = Store(_out(args.out))
    records = import_voss_eval(Path(args.runs_jsonl), store)
    print(f"imported {len(records)} rows -> {store.runs}")
    print(f"report: {write_report(store.root)}")
    return 0


def cmd_schema(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMAS.items():
        (out / f"{name}.schema.json").write_text(json.dumps(model.model_json_schema(), indent=2) + "\n")
    print(f"wrote {len(SCHEMAS)} schemas to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="proofs", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def bench_args(sp):
        sp.add_argument("--bench", required=True, help="benchmark directory")
        sp.add_argument("--task", action="append", help="limit to scenario id (repeatable)")

    r = sub.add_parser("run", help="run scenarios x configs")
    bench_args(r)
    r.add_argument("--config", action="append", required=True, help="name or path; comma list ok")
    r.add_argument("--configs-dir", default="configs")
    r.add_argument("-k", type=int, default=1, help="runs per scenario per config")
    r.add_argument("--seed", type=int, default=0, help="job-order shuffle seed")
    r.add_argument("--out")
    r.add_argument("--live", action="store_true", help="allow configs that call live models")
    r.add_argument("--max-runs", type=int)
    r.add_argument("--max-usd", type=float)
    r.set_defaults(fn=cmd_run)

    v = sub.add_parser("validate", help="oracle must pass and null must fail on every scenario")
    bench_args(v)
    v.set_defaults(fn=cmd_validate)

    rp = sub.add_parser("report", help="re-render report.md for a results directory")
    rp.add_argument("results")
    rp.set_defaults(fn=cmd_report)

    c = sub.add_parser("compare", help="outcome differences between two experiments")
    c.add_argument("a")
    c.add_argument("b")
    c.set_defaults(fn=cmd_compare)

    i = sub.add_parser("import-voss-eval", help="ingest a `voss eval` runs.jsonl")
    i.add_argument("runs_jsonl")
    i.add_argument("--out")
    i.set_defaults(fn=cmd_import)

    s = sub.add_parser("schema", help="export JSON Schemas")
    s.add_argument("--out", default="schemas")
    s.set_defaults(fn=cmd_schema)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
