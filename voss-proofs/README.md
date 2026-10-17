# VossProofs

VossProofs is an evaluation and research harness for the Voss ecosystem. It runs engineering scenarios against Voss and against comparison baselines. Every run records evidence you can inspect: the diff, check logs, the event stream and the session record. The question it answers is when Voss's architecture produces better verified outcomes, and at what cost.

VossProofs is independent of the harness. It drives Voss only through public surfaces: `voss serve` over HTTP+SSE, and the CLI. It never imports `voss` internals, so it can evaluate any installed Voss version.

## Quickstart

```sh
cd voss-proofs
uv venv .venv && VIRTUAL_ENV=.venv uv pip install -e ".[dev]" -e "..[server]"

proofs validate --bench benchmarks/regression          # oracle must pass, null must fail
proofs run --bench benchmarks/regression \
  --config oracle,null,voss-serve-fake -k 2 --out results/smoke-1
proofs run --bench benchmarks/regression \
  --config oracle,null,voss-serve-fake -k 2 --out results/smoke-2
proofs compare results/smoke-1 results/smoke-2         # 0 outcome differences
open results/smoke-1/report.md
```

None of the commands above call a live model. To run real Voss sessions you have to opt in, and the run count must be capped:

```sh
proofs run --bench benchmarks/regression --config voss-serve-auto --live --max-runs 8 --max-usd 2
```

Other commands:

- `proofs import-voss-eval <runs.jsonl>` converts `voss eval` output into run.v1 records.
- `proofs report <results>` re-renders a report.
- `proofs schema` exports the JSON Schemas.

## Concepts

- **Scenario** (`benchmarks/<set>/<id>/`). Each scenario has four parts:
  - `task.toml`: a superset of the `voss eval` task spec.
  - `fixture/`: the starting repository.
  - `reference.patch`: the gold solution.
  - `hidden/`: acceptance tests. These are copied into the workspace only after the system under test exits.
- **Config** (`configs/*.toml`, plus built-in `oracle` and `null`). A config names the system under test: its adapter, mode, auth, model and env.
- **Run record** (`schemas/run.v1.schema.json`). One JSON line per run in `results/<exp>/runs.jsonl`. Every artifact is referenced by sha256 into `results/<exp>/objects/`.
- **Verified vs claimed.** `verified` is true only when every visible, hidden and scope check passes. `claimed_complete` records what the system said about its own run. The report counts runs where these disagree.

See [docs/PRD.md](docs/PRD.md) for the roadmap, [docs/methodology.md](docs/methodology.md) for how results are computed, [docs/upstream-gaps.md](docs/upstream-gaps.md) for what Voss would need to change, and [docs/dataset-policy.md](docs/dataset-policy.md) for what may go into a corpus.
