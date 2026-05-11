---
phase: M4
slug: voss-authored-harness-loop
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-11
---

# Phase M4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `M4-RESEARCH.md §Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x (auto mode) — pyproject.toml:25-26, 39-46 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/harness/test_voss_loop_parity.py tests/harness/test_voss_check_dir.py tests/harness/test_voss_compile_dir.py tests/harness/test_cache_freshness.py -q` |
| **Per-test run** | `pytest tests/harness/test_voss_loop_parity.py -q` |
| **Full M4 suite** | `pytest tests/harness/ tests/codegen/test_use_alias.py tests/codegen/test_await_use_import.py tests/parser/test_use_alias.py -q -m "not live"` |
| **Subprocess CLI** | `python -m voss.cli {check,compile,do} ...` |
| **Compiler sub-plan check** | `pytest tests/codegen/test_imports.py tests/codegen/test_use_alias.py tests/codegen/test_await_use_import.py tests/parser/test_use_alias.py -q` |
| **Estimated runtime** | ~60s quick, ~120s full M4 suite |

---

## Sampling Rate

- **After every task commit:** `pytest tests/harness/ tests/codegen/test_use_alias.py tests/codegen/test_await_use_import.py tests/parser/test_use_alias.py -q -m "not live"` (~30s)
- **After every plan wave:** quick run + `voss check voss/harness/agent/` + `voss compile voss/harness/agent/` + `VOSS_HARNESS=compiled voss do "<fixture>"` smoke (~60s)
- **Before `/gsd-verify-work`:** All four D-12 success criteria green — `voss check` exit 0 + `voss compile` produces 5 .py + `_manifest.json` + `VOSS_HARNESS=compiled voss do "<fixture>"` exit 0 + non-empty `TurnResult.final` + parity test passes. Full pytest suite passes `-m "not live"`.
- **Max feedback latency:** 60s quick / 180s full

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| grammar-use-alias | 01 | 0 | Pattern 1a / D-02 | — | Parser accepts `use foo::bar as alias` and emits `Use(path=["foo","bar"], alias="alias")` | unit | `pytest tests/parser/test_use_alias.py -q` | ❌ W0 | ⬜ pending |
| codegen-await-use | 01 | 0 | Pattern 1b / D-02 | — | Codegen emits `await` before calls to `use`-imported identifiers that resolve to coroutines | unit | `pytest tests/codegen/test_await_use_import.py -q` | ❌ W0 | ⬜ pending |
| sandbox-write-cache | 02 | 1 | D-15 | — | `voss/harness/sandbox.py:write_cache(project_root, relpath, text)` writes through `jail_path`; rejects paths outside cwd jail | unit | `pytest tests/harness/test_sandbox.py -q -k write_cache` | ❌ W1 | ⬜ pending |
| cli-check-dir-walk | 02 | 1 | D-05 / D-07 / DOG-06 | — | `voss check <dir>` rglobs `*.voss`, parses + analyzes each, aggregates `<file>:<line>:<col>: <severity> <msg>` grouped by file, prints `N errors, M warnings across K files` summary, exit non-zero on any error | unit | `pytest tests/harness/test_voss_check_dir.py -q` | ❌ W1 | ⬜ pending |
| cli-compile-dir-walk | 02 | 1 | D-05 / DOG-08 | — | `voss compile <dir>` emits one `.py` per `.voss` source under `.voss-cache/harness/`, writes `_manifest.json` per D-13 schema | unit | `pytest tests/harness/test_voss_compile_dir.py -q` | ❌ W1 | ⬜ pending |
| manifest-shape | 02 | 1 | D-13 / D-14 | — | `_manifest.json` matches `{ "version": 1, "voss_version": str, "compiled_at": iso, "sources": { "<rel>.voss": {"sha256": hex, "lines": int}, ... } }`; cache key derived from sha256 + voss_version (not git-head, not mtime) | unit | `pytest tests/harness/test_voss_compile_dir.py::test_manifest_schema -q` | ❌ W1 | ⬜ pending |
| stale-cache-error | 02 | 1 | D-10 / D-14 | T-M4-stale-silent | `StaleHarnessCacheError` raised on sha mismatch OR missing manifest; message exactly `compiled harness cache stale — run: voss compile voss/harness/agent/`; NO silent fallback to Python | unit | `pytest tests/harness/test_cache_freshness.py -q` | ❌ W1 | ⬜ pending |
| check-dir-static-only | 02 | 1 | D-06 / M3 D-03 | T-M4-hf-load | `voss check voss/harness/agent/` does NOT load `sentence_transformers` (carry-forward of M3 D-03) | unit | `pytest tests/harness/test_voss_check_dir.py::test_check_dir_does_not_load_hf_encoder -q` | ❌ W1 | ⬜ pending |
| loop-voss-file | 03 | 2 | DOG-01 | — | `voss/harness/agent/loop.voss` exists; contains `ctx(budget:` + control flow only; parses + analyzes via dir walker | file + unit | `test -f voss/harness/agent/loop.voss && python -m voss.cli check voss/harness/agent/loop.voss` | ❌ W2 | ⬜ pending |
| router-voss-file | 03 | 2 | DOG-02 | — | `router.voss` exists; uses `probable<Intent>` for slash-vs-natural classification | file + unit | `python -m voss.cli check voss/harness/agent/router.voss` | ❌ W2 | ⬜ pending |
| planner-voss-file | 03 | 2 | DOG-03 | — | `planner.voss` exists; uses `probable<Plan>` ask + confidence gate; `try/catch` or `fallback` branch when below threshold | file + unit | `python -m voss.cli check voss/harness/agent/planner.voss` | ❌ W2 | ⬜ pending |
| executor-voss-file | 03 | 2 | DOG-04 | — | `executor.voss` exists; dispatches `plan.steps` through Python helper (no `for` loop in .voss); codegen emits `await` for tool invocations | file + unit | `python -m voss.cli compile voss/harness/agent/executor.voss && grep -q "await " .voss-cache/harness/executor.py` | ❌ W2 | ⬜ pending |
| reviewer-voss-file | 03 | 2 | DOG-05 | — | `reviewer.voss` exists; synthesizes `final_when_done` from tool results | file + unit | `python -m voss.cli check voss/harness/agent/reviewer.voss` | ❌ W2 | ⬜ pending |
| run-step-loop-helper | 03 | 2 | D-04 / Q-2 | — | `voss/harness/agent.py:_run_step_loop(plan_steps, tools, permissions, renderer)` exists; `ToolEntry.invoke_dict(args: dict)` exists | unit | `pytest tests/harness/test_agent_integration.py -q -k run_step_loop` | ❌ W2 | ⬜ pending |
| boot-dispatch | 03 | 2 | D-08 / DOG-07 | T-M4-boot-spoof | `voss/harness/cli.py:_resolve_run_turn()` reads `VOSS_HARNESS` env → `[harness] backend` config → default `"python"`; swaps `run_turn` import accordingly; no silent fallback | unit | `pytest tests/harness/test_boot_dispatch.py -q` | ❌ W2 | ⬜ pending |
| parity-test | 04 | 3 | D-11 / DOG-07 | T-M4-parity-divergence | `tests/harness/test_voss_loop_parity.py` runs fixture task under both backends with `StubProvider`; asserts `python_result.final == voss_result.final` AND tool-call sequence identical | integration | `pytest tests/harness/test_voss_loop_parity.py -q` | ❌ W3 | ⬜ pending |
| dog-07-smoke | 04 | 3 | DOG-07 / D-12 | — | `VOSS_HARNESS=compiled python -m voss.cli do "noop summary of fixture.md"` exits 0; non-empty `TurnResult.final`; tool-call sequence matches Python path | integration | bash smoke test in `tests/harness/test_dog07_smoke.py` | ❌ W3 | ⬜ pending |
| ci-gate | 05 | 4 | DOG-06 | — | `.github/workflows/ci.yml` includes step `python -m voss.cli check voss/harness/agent/`; step fails CI on any error | grep | `grep -F "voss.cli check voss/harness/agent/" .github/workflows/ci.yml` | ❌ W4 | ⬜ pending |
| install-doc | 05 | 4 | D-16 | — | README install section mentions `voss compile voss/harness/agent/` as one-liner | grep | `grep -F "voss compile voss/harness/agent/" README.md` | ❌ W4 | ⬜ pending |
| doctor-cache-row | 05 | 4 | D-16 | — | `voss doctor` output includes a row for harness-cache freshness (informational; never blocking) | unit | `pytest tests/harness/test_doctor.py -q -k harness_cache` | ❌ W4 | ⬜ pending |

*Status: ⬜ pending · ✓ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

**Wave 0 (compiler sub-plan — must land before any `.voss` authoring):**
- [ ] `tests/parser/test_use_alias.py` — `use foo::bar as alias` parses; AST records `alias`
- [ ] `tests/codegen/test_await_use_import.py` — `use`-imported callees auto-await
- [ ] `voss/grammar.lark` — extend `use_path` rule with optional `("as" IDENT)?`
- [ ] `voss/parser.py:714-715` — propagate alias into the `Use` AST node
- [ ] `voss/codegen.py:441-446` — extend auto-await to also cover `use`-imported names

**Wave 1 (CLI dir-walk + cache infra):**
- [ ] `voss/harness/cache.py` (NEW, ~80 LOC) — manifest helpers (read/write/sha256/check_fresh)
- [ ] `voss/harness/sandbox.py` (MODIFY, +15 LOC) — `write_cache(project_root, relpath, text)`
- [ ] `voss/harness/diagnostics.py` (MODIFY) — `StaleHarnessCacheError` + cache-freshness doctor row
- [ ] `voss/cli.py:check` (~line 209) — dir-walk mode with `rglob("*.voss")`
- [ ] `voss/cli.py:compile` (~line 147) — dir-walk mode + manifest emission
- [ ] `tests/harness/test_voss_check_dir.py` (NEW)
- [ ] `tests/harness/test_voss_compile_dir.py` (NEW)
- [ ] `tests/harness/test_cache_freshness.py` (NEW)

**Wave 2 (.voss authoring + boot dispatch):**
- [ ] `voss/harness/agent/{loop,router,planner,executor,reviewer}.voss` (5 NEW files, 20-40 LOC each)
- [ ] `voss/harness/agent.py` — extract `_run_step_loop(plan_steps, tools, permissions, renderer)` helper
- [ ] `voss/harness/tools.py:ToolEntry.invoke_dict(args: dict)` helper
- [ ] `voss/harness/cli.py:_resolve_run_turn()` — env → config → default dispatch
- [ ] `voss/harness/config.py` — *(no code change required: existing `load_harness_config` already returns the `backend` key when present in `[harness]`; `_resolve_run_turn` reads it via `.get("backend")`)*
- [ ] `tests/harness/test_boot_dispatch.py` (NEW)

**Wave 3 (parity + DOG-07 smoke):**
- [ ] `tests/harness/test_voss_loop_parity.py` (NEW)
- [ ] `tests/harness/test_dog07_smoke.py` (NEW)

**Wave 4 (CI gate + docs):**
- [ ] `.github/workflows/ci.yml` — add `voss check voss/harness/agent/` step
- [ ] `README.md` — install one-liner `voss compile voss/harness/agent/`
- [ ] `voss/harness/diagnostics.py` — harness-cache freshness row in `run_all_checks`
- [ ] `tests/harness/test_doctor.py` (MODIFY) — assert cache-freshness row appears

*(No framework install needed — pytest + pytest-asyncio already pinned in `[project.optional-dependencies].dev`.)*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live-provider parity under `VOSS_HARNESS=compiled` | M4 out-of-scope; defers to M5 | Live providers cost money + require creds; M4 bar is StubProvider parity | Manual: `VOSS_HARNESS=compiled ANTHROPIC_API_KEY=... voss do "<task>"`; compare `TurnResult.final` against Python path; record date + sanitized output |
| Generated `.py` readability in `.voss-cache/harness/` | LANG-03 carry-forward | Subjective readability beyond runtime parity | Reviewer inspects `.voss-cache/harness/{loop,router,planner,executor,reviewer}.py`; confirms idiomatic async Python; no leaked AST node names |
| `voss/harness/agent/*.voss` reads as thin control flow (D-02) | D-02 | Editorial judgment on Python-vs-`.voss` boundary | Reviewer reads all 5 files; confirms only `ctx`, `probable<T>`, gates, `try/catch`, `fallback`, `use ... as` constructs appear; no pydantic models, no prompt strings, no tool registration in `.voss` |

---

## Validation Sign-Off

- [x] All tasks have automated verification or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references (parser test + codegen test + grammar/parser/codegen patches)
- [x] No watch-mode flags
- [x] Feedback latency < 60s quick / < 180s full
- [x] Default tests hermetic (StubProvider + `VOSS_HERMETIC=1` per M3 D-01; no real provider; no HF encoder load)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-11
