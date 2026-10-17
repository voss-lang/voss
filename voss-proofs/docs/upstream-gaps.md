# Upstream gaps

These are things in the Voss repositories that limit what VossProofs can measure. Each one is a proposal for an upstream issue. VossProofs does not patch Voss. It works around each gap where it can and reports the limit where it can't.

The list was checked against `origin/master` at `105a506b` (2026-10-17) unless a different branch is named.

| # | Gap | Effect on VossProofs | Current workaround |
|---|---|---|---|
| 1 | `voss eval` CLI, serve and SDK-client surfaces return an empty session record, so `cost_usd` and tokens come back null or zero. The Go and TS consumers print `cost_usd`, but the runner drops it. | Imported `voss eval` rows have unknown cost for those surfaces. | The `voss-serve` adapter reads `/session/{id}/cost` and the saved session record itself. |
| 2 | `voss eval` rows don't record output tokens. | Usage is incomplete in imported rows. | `output_tokens` stays null. Native runs read `completion_tokens` from the session record. |
| 3 | `voss do` builds a session record but never saves it. `--json` also forces auto-approve (`cli.py:2250`). | `voss do` can't serve as a measured Voss config. | Use `voss serve` for every Voss config. |
| 4 | The USD budget (`/budget`) is advisory. Only `token_budget` and `max_iterations` stop a run. `docs/protocol.md` advertises `POST /session/:id/budget` and `GET /session/:id/confidence`, and neither exists. | H5 (budget enforcement) can only be measured on tokens and turns. | Report the USD budget as not enforced. Measure overshoot against token budgets. |
| 5 | `voss team run` (board and EM) uses hardcoded deterministic reviewer and EM stubs, then blocks on an interactive `click.prompt` for approve/reject. The real Reviewer A and B are never instantiated outside `board/`. | Configuration C through the board can't run headlessly. | Phase 3 uses `POST /swarm` and `/swarm/{id}/run` for multi-agent configs. The board config is reported as "not evaluable". |
| 6 | Durable task replay (`/task-events`, `/capabilities`, `command_id`) exists only on the `go-tui-s4-session-memory` branch. | Can't rely on cursor replay or capability detection against master. | The adapter probes `/capabilities` (a 404 gives an empty list) and reads the legacy `/session/{id}/events` stream. |
| 7 | `budget.updated`, `confidence.updated` and `probable` events are defined in `contracts/events.schema.json` but never emitted. | No event-level budget or confidence telemetry. | Use per-run fields in the saved session record. |
| 8 | `voss.eval.runner.run_suite` resolves suites against the current directory and raises `click.UsageError`. Behavior depends on task-id prefixes: `05-` selects the resume path, and `py-`, `rust-` and `ts-` select the toolchain skip. | It can't be used as a library. | `voss eval` is called as a subprocess from a Voss checkout, and its `runs.jsonl` is imported. |
| 9 | J4's locked review result is being withdrawn on `fix/j4-locked-review-rerun`, which adds `evals/review-locked-2/` and rubric v2. | Phase 2 needs to know which locked set and rubric are authoritative. | Pin the merged locked set and record `rubric_version` on every review record. |
| 10 | voss-lang: `voss check` has no JSON output, and `voss-exec` runs workflows only through `cargo test`. Replay is its only binary command. | The runtime suite can use exit codes and replay parity only. | Phase 4 runtime suite: `voss-exec replay` over `tests/exec-fixtures`, plus `voss check` exit codes. |
| 11 | Voss-ADE: Tauri WebDriver isn't possible on macOS. Only `crates/core` can be tested headlessly. | No native UI evaluation. | An optional adapter for `cargo test -p voss-core`, labeled as not covering the UI. |
| 12 | Voss-OS runs only on Linux, through bubblewrap, Landlock and seccomp. | No OS-level sandbox for live runs on macOS. | Reported as a contamination threat (see methodology). A Linux VM adapter is optional in Phase 4+. |
| 13 | `voss/__init__.py` says `__version__ = "0.1.0"` while `pyproject.toml` says 0.1.2. | Run records carry an ambiguous Voss version. | Record what `voss --version` reports. A git SHA should be added once Voss exposes one. |
