# M5-05 Summary - Golden Eval Fixtures

## Status

Complete. Wave 4 now has the five stable golden task fixtures under `tests/eval/golden/`.

## Fixtures

| id | mode | auto approve | contract |
|---|---|---:|---|
| `01-analyze` | `edit` | true | Analyze a tiny Python CLI repo and write `.voss/architecture.md`. |
| `02-plan-only` | `plan` | false | Plan type hints for `calc.py` without modifying the fixture. |
| `03-approved-edit` | `edit` | true | Rename `add()` to `sum_two()` in both definition and call site. |
| `04-validation` | `edit` | true | Run `voss check sample.voss` and report exit 0. |
| `05-resume` | `plan` | false | Resume after the runner cancel/load path and summarize `notes.txt`. |

## Provenance

- `04-validation/fixture/sample.voss` is a verbatim copy of `samples/classify.voss`.
- `05-resume/fixture/notes.txt` uses a distinct Project Meridian status note with reporting period, completed engineering milestone, and deferred open items so judge verification has concrete facts to match.

## Resume Assumption

Task 05 relies on the M5-03 `_drive_resume` path: spawn a turn, cancel after `RESUME_CANCEL_DELAY_S`, save/load the session, then run the same prompt with prior history. The rubric remains outcome-based so it is not brittle to exact cancellation timing.

## Verification

- All five `task.toml` files validate against `TaskSpec`.
- `load_suite(Path("tests/eval/golden"), suite="")` returns exactly `01-analyze`, `02-plan-only`, `03-approved-edit`, `04-validation`, `05-resume`.
- `python3 -m voss.cli eval --stub --auth none --suite golden -k 1 --out /tmp/voss-eval-smoke` writes 5 JSONL rows.
- `pytest -q -m "not slow and not live" tests/eval/test_voss_eval_stub.py` -> `8 passed`
- `pytest tests/eval -q` -> `30 passed`
