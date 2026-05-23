---
phase: F5-commit-with-critique-hook
plan: 01
status: complete
---

# F5-01 Summary — Consensus Module + CLI + Tests

## What shipped

1. **`voss/harness/consensus.py`** — new module with:
   - Pydantic models: `Violation`, `CritiqueSummary`, `CritiqueResponse`, `ConstraintsConfig` (all `extra="ignore"`)
   - `load_constraints(cwd)` — reads `.voss/constraints.yml` via `yaml.safe_load`, returns `None` when missing
   - `capture_diff(mode, cwd, ref)` — staged/ref/stdin modes, git repo pre-flight, `MAX_DIFF_CHARS=30_000` truncation
   - `build_prompt(constraints, diff_text)` — numbered rules + diff injection
   - `run_critique(provider, model, constraints, diff_text)` — single `provider.complete` call, fail-open on exception/None
   - `format_violations(result)` — structured output with constraint text, file:line, explanation

2. **`voss/harness/cli.py`** — `consensus_cmd` Click command registered in `AGENT_COMMANDS`:
   - Options: `--staged` (default), `--diff REF`, `--stdin`, `--cwd`, `--auth`, `--model`
   - Exits 0 silently when no constraints.yml (D-04)
   - Exits 0 on empty diff (Pitfall 2)
   - Fail-open on LLM failure: exit 0 + stderr warning (D-16)
   - Exits 1 only when mode=block AND violations found (D-09)

3. **`tests/harness/test_consensus.py`** — 23 tests covering:
   - D-01 (YAML loading), D-03 (no conventions import), D-04 (skip when missing)
   - D-08 (staged/ref input modes), D-09 (block/warn exit codes)
   - D-10/D-11 (violation formatting), D-12 (clean pass output)
   - D-13 (single-shot, response_format=CritiqueResponse)
   - D-16 (fail-open on error, fail-open on None parsed)
   - Pitfall 2 (empty diff), Pitfall 5 (large diff truncation)
   - CLI integration: --help shows consensus, block exits 1, warn exits 0, fail-open

## Verification

| Check | Result |
|-------|--------|
| `consensus` in `voss --help` | ✓ |
| 23 tests GREEN | ✓ |
| test_cli.py regression (14 pass) | ✓ |
| `conventions` grep = 0 (D-03) | ✓ |
| `run_turn` grep = 0 (D-13) | ✓ |
| No new deps in pyproject.toml | ✓ |
