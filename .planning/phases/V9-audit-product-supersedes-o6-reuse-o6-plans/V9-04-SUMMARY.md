---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 04
type: execute
status: complete
wave: 3
---

# V9-04 Summary — Renderers + `voss audit` CLI

## Outcome

Deterministic `render.py`, V9 package exports, and the read-only `voss audit`
command wired into `AGENT_COMMANDS`. `test_audit_render.py` + `test_audit_cli.py`
fully GREEN. Audit suite: **66 passed, 8 RED** (calibration 4 + signoff 3 +
calibration-import guard 1 → V9-05/V9-06).

## Changes

### `voss/harness/audit/render.py` (new)
- `_to_dict(obj)` — recursive dataclass/tuple/dict → JSON-friendly (tuples →
  lists, documented).
- `render_json(report)` — `json.dumps(_to_dict(report), sort_keys=True, indent=2)`;
  deterministic, byte-identical across calls.
- `render_markdown(report)` — one `## §N <Section>` header for all 15 PRD §9
  sections (ORCHESTRATION_LAYERS.md §9). Reviewer-A (§10) / Reviewer-B (§11) in
  separate sections; unsupported EM claims tagged `[UNSUPPORTED CLAIM]` inline in
  §6 Work Cards; sections in `report.sections_missing` (+ always diff_summary /
  tests_evals) render `_none_`.
- `render_text(report)` — compact stable plain-text (default `--format text`).
- All collections sorted by stable key (node id / section order). No
  `now()`/random/mtime. Import-clean (gate = 0).

### `voss/harness/audit/__init__.py`
- Exports `AuditReport`, `CalibrationReport`, `build_audit_report`,
  `render_text/markdown/json`. Docstring "O6 audit product" → "V9 audit product".

### `voss/harness/cli.py`
- `audit_cmd` modeled on `review_cmd`: `@click.argument("run_id", required=False)`,
  `--cwd`, `--format text|json|markdown`, `--output`. Traversal guard (reject
  `/`, `\`, `..`; resolved `candidate.parent == sessions_dir.resolve()`) BEFORE
  any FS read; unknown run_id → stderr + `SystemExit(1)`; latest-by-mtime default
  via `_latest_root_id`. Calls `build_audit_report` + renderer; `--output` writes
  to the named path, else `click.echo`. Audit/calibration imports are
  function-local (mirrors `team_run_cmd`).
- `audit_cmd` registered in `AGENT_COMMANDS` (after `board_cmd`).

## Notes

- Calibration wiring is **forward-compatible**: `audit_cmd` attempts
  `from voss.harness.audit.calibration import compute_calibration` inside a
  try/except and passes `None` when V9-05 hasn't landed (`build_audit_report`
  tolerates None). Once V9-05 ships, the CLI picks it up with no further change.
- No deviations from the plan this wave.

## Verification

- `pytest tests/harness/audit/test_audit_render.py tests/harness/audit/test_audit_cli.py` — 10 passed.
- `pytest tests/harness/audit/ -k "not calibration and not signoff"` — green (loader+report+render+cli+baseline).
- `audit_cmd in AGENT_COMMANDS` — True.
- Import-clean grep gate (board/em/cli) on render.py = 0.

## Remaining RED (later waves)

calibration compute (4, V9-05), signoff gate (3, V9-06), calibration-import
guard (1, V9-05).
