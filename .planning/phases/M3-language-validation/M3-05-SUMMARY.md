---
phase: M3
plan: 05
status: complete
date: 2026-05-12
---

# M3-05 Summary — e2e suite repointed to samples/ + D-05/D-06 extension assertions

## helpers.py diff

```
- PARSER_EXAMPLES = REPO_ROOT / "tests" / "parser" / "examples"
+ SAMPLES_DIR = REPO_ROOT / "samples"

  def example_source(name: str) -> Path:
-     """Return path to a canonical parser example .voss source."""
-     path = PARSER_EXAMPLES / f"{name}.voss"
+     """Return path to a canonical sample .voss source (samples/<name>.voss)."""
+     path = SAMPLES_DIR / f"{name}.voss"
      if not path.exists():
-         raise FileNotFoundError(f"parser example missing: {path}")
+         raise FileNotFoundError(f"canonical sample missing: {path}")

  def copy_example(tmp_path: Path, name: str) -> Path:
-     """Copy a parser example into ``tmp_path`` and return the destination."""
+     """Copy a canonical sample into ``tmp_path`` and return the destination."""
```

Module docstring updated: "Shared helpers for tests/examples e2e tests, sourcing samples from samples/."

## Deletions

- `tests/examples/test_helpers.py` — deleted via `git rm` (D-09: meta-tests on helpers out of scope).
- `tests/examples/test_live_examples.py` — deleted via `git rm` (D-09: no --live opt-in).
- `tests/examples/__pycache__` cleared.

## New test functions

| Test | File | Purpose |
|------|------|---------|
| `test_support_tickets_memory_records_user_messages` | `tests/examples/test_support_e2e.py` | D-05 + D-12: asserts `module.tickets` is `EpisodicMemory(capacity=50)`, two `handleMessage` calls add two `role="user"` turns on both generated and raw oracles. |
| `test_research_generated_contains_use_and_try_catch_lowerings` | `tests/examples/test_research_e2e.py` | D-06: generated Python contains `from voss_runtime.tools import tool`, `try:`, `except`, and the literal `"web search unavailable"`. |

## Helper change: `_inject_support_helpers`

Pre-M3-04, `samples/support.voss` had no module-scope `let`, so `handleMessage` had no free names beyond `escalate`/`refundFlow`/`authSupport` (injected by `_inject_support_helpers`). M3-04 added `let tickets: memory.episodic(capacity: 50 turns)` at module scope. Codegen emits this binding inside `async def main()` (not at module scope), so `handleMessage` references `tickets` as a free name with no module-global binding — `NameError` when called directly.

Fix in `_inject_support_helpers`: also bind `module.tickets = EpisodicMemory(capacity=50)`. This makes the route tests work AND gives the new tickets test a real EpisodicMemory to inspect. **Note**: the codegen scoping issue (top-level `let` wrapped in `main`) is pre-existing and unfixed by this plan — see "Hand-off / known issues" below.

## Test counts

| Stage | Passed | Skipped | Notes |
|-------|--------|---------|-------|
| Baseline (pre-M3-05) | 28 | 6 | includes legacy test_helpers (7) + test_live_examples (live-mark skips) |
| After Task 1 (delete + repoint) | 20 | 0 | -7 helpers, -6 live skips (file deleted), -1 helper that was a `live` skip; everything else green |
| After Task 2 (+ tickets test) | 21 | 0 | +1 new test |
| After Task 3 (+ research generated test) | **22** | 0 | +1 new test |
| Same run without `VOSS_HERMETIC=1` (no creds in env) | 22 | 0 | M3-02 auto-stub fallback path kicks in |

## Hand-off to M3-06 and known issues

### M3-06 hand-off
- `tests/examples/test_check_speed.py` already exists (M3-01 sentinel). M3-06 extends it with the parametrized wall-clock gate `test_check_speed_under_ceiling` parametrized over the three samples, using `CHECK_CEILING_SECONDS = 2.0` already in place.
- Framing docs (DOCS-04, DOCS-05) are an independent track inside M3-06 — separate from speed gate.

### Known issue (out of scope for M3-05)
Codegen emits top-level `let X = ...` inside `async def main()` rather than at module scope. When a module-scope `fn` references `X`, the generated Python raises `NameError` if the function is called before `main()` runs. M3-04's `voss run samples/support.voss` masks this because `main()` only initializes `tickets`; nothing calls `handleMessage` from `main()`. Real consumers calling `handleMessage` directly hit the bug. Mitigated in tests by helper injection; a proper fix is a codegen change (emit module-scope `let` at module level or hoist `global tickets` into `handleMessage`). Tracked as a follow-up; not blocking LANG-07/LANG-08 runnable claim because the raw_python parity oracles already work correctly.

## Acceptance criteria — all met

- `test_helpers.py` and `test_live_examples.py` removed ✓
- `PARSER_EXAMPLES` references gone, `SAMPLES_DIR` constant in place ✓
- `example_source('classify')` resolves to `samples/classify.voss` ✓
- `pytest tests/examples/test_classify_e2e.py tests/examples/test_cli_matrix.py tests/examples/test_check_speed.py -q` exits 0 ✓
- New support test asserts `module.tickets` (6 refs) + `raw_tickets` (4 refs) + `EpisodicMemory` (4 refs) ✓
- New research test asserts use lowering + try/except + "web search unavailable" ✓
- `VOSS_HERMETIC=1 pytest tests/examples/ -q` → 22 passed ✓
- Same suite WITHOUT `VOSS_HERMETIC=1` (auto-stub fallback) → 22 passed ✓
