# M5-03 Summary — Eval CLI + Runner

## Status

Complete. Wave 2 now has the `voss eval` command, suite runner, JSONL writer, stub smoke tests, and live-signal gates.

## Changed

- Added `voss/eval/runner.py` with `run_suite`, fixture preparation, resume drive path, signal extraction, JSONL append, and crash rows that skip the judge.
- Re-exported `run_suite` from `voss/eval/__init__.py`.
- Registered `voss eval` through `voss/harness/cli.py` `AGENT_COMMANDS`, with flags `--suite`, `--stub`, `--live`, `-k`, `--out`, `--judge-model`, `--task`, and `--auth`.
- Replaced the inline fixture helper test with the runner helper.
- Added CLI help, stub subprocess smoke, stub-null-cost, no-creds loud-failure, and live gated signal tests.
- Updated `M5-VALIDATION.md` to mark Wave 2 complete.

## Verification

- `pytest tests/eval/test_cli_options.py tests/eval/test_fixture_isolation.py tests/eval/test_voss_eval_stub.py tests/eval/test_live_signals.py -q` → `5 passed, 6 skipped`
- `pytest tests/eval -q` → `15 passed, 7 skipped`
- `python3 -m voss.cli eval --help` shows all required eval flags.

## Notes

- `--stub --auth none` keeps smoke tests hermetic and writes `cost_usd: null`.
- Without `--out`, `run_suite` writes under `.voss/eval/<timestamp>`.
- Live tests remain gated on provider credentials and skip when repo-level golden fixtures are not present.
