# Phase M4: Voss-authored Harness Loop - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** M4-voss-authored-harness-loop
**Areas discussed:** File decomposition + Python/.voss seam, voss check <dir> + CI gate shape, Boot path (DOG-07) + parity oracle, Cache layout + invalidation (DOG-08), Scope bound for DOG-07

---

## File Decomposition

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline split (one stage per file) | loop=orchestration, router=intent, planner=ask, executor=tool dispatch, reviewer=synth. Linear pipeline; each 20–40 LOC. | ✓ |
| Concern split (router = top-level; rest per-action) | router dispatches between chat/do/edit/slash; loop/planner/executor/reviewer are stand-alone sub-flows. | |
| Other / I'll describe it | — | |

**User's choice:** Pipeline split.
**Notes:** Mirrors the pseudo-`.voss` comment block already inside `voss/harness/agent.py:114–125` — the design target is essentially pre-written; M4 ships it as real `.voss`.

---

## Python/.voss Seam

| Option | Description | Selected |
|--------|-------------|----------|
| Thin .voss — control flow only | `.voss` owns only `ctx`, `probable<T>`, gates, fallback. Python keeps models, prompts, providers, tools, permissions. Files 15–25 LOC. | ✓ |
| Thick .voss — inline prompts + tool decls | `.voss` declares `prompt PlanSystem`, `@tool`, Plan type. Python reduces to transport + permission. Files 40–80 LOC. | |
| Other / I'll describe it | — | |

**User's choice:** Thin .voss.
**Notes:** Keeps the existing pydantic models, `PLAN_SYSTEM`, and permission gate authoritative. `.voss` imports Python symbols via `use voss.harness as h` (researcher confirms parser surface).

---

## Orchestration Direction

| Option | Description | Selected |
|--------|-------------|----------|
| Python imports compiled .voss functions | `voss compile loop.voss` produces `.voss-cache/harness/loop.py` exporting `async def run_turn(...)`; harness CLI imports it. Python is entry; .voss is implementation. | ✓ |
| `.voss` is the entry point | Bare `voss` does `voss run loop.voss` with task injected. Cleaner dogfood signal but requires new runtime contract. | |
| Other / I'll describe it | — | |

**User's choice:** Python imports compiled .voss functions.
**Notes:** Smallest diff. No new runtime entry shape. `voss run` stays reserved for `.voss` programs in the M1 D-* sense.

---

## voss check <dir> + CI Gate

| Option | Description | Selected |
|--------|-------------|----------|
| Extend `voss check` to walk dirs; static-only | Glob `*.voss` recursively, parse+analyze each, aggregate diagnostics. Matches M3 D-03. Compile+stub-run lives in separate pytest. | ✓ |
| Extend dir support AND add compile-stub-run smoke inside the gate | Also runs `voss compile` + smoke import in CI. Stronger regression signal, slower CI. | |
| CI wrapper script (no CLI changes) | `scripts/check_harness.sh` loops `voss check` over each file. Keeps dir support out of public CLI. | |
| Other / I'll describe it | — | |

**User's choice:** Extend `voss check` to walk dirs; static-only.
**Notes:** Per-file diagnostics aggregated; compile-and-stub-run lives in `tests/harness/test_voss_loop_parity.py`, not inside `voss check`.

---

## Boot Path (DOG-07) + Parity Oracle

| Option | Description | Selected |
|--------|-------------|----------|
| Env flag opt-in; agent.py stays as oracle | `VOSS_HARNESS=compiled` flips import. Default Python. agent.py kept as M3 D-12-style oracle. Parity test asserts equivalent TurnResult. | ✓ |
| Auto-detect: use compiled when cache fresh | Silent backend swap when `.voss-cache/harness/loop.py` exists + sha matches. Zero-config dogfood; risk of silent fallback masking regressions. | |
| Always-Python; .voss is shadow validation only | DOG-07 satisfied via `--harness=compiled` flag only; default never runs compiled. Lowest risk, weakest dogfood. | |
| Other / I'll describe it | — | |

**User's choice:** Env flag opt-in; agent.py stays as oracle.
**Notes:** Loud failure on stale cache (D-10) matches M1 D-13 diagnose-don't-fix posture. Auto-detect was explicitly rejected because silent backend swaps mask regressions.

---

## Cache Layout + Invalidation (DOG-08)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-file artifacts, sha keyed, eager `voss compile` | Five `.py` files + `_manifest.json`. Cache key: source sha + voss version. Eager compile via install hook or `voss doctor --fix`. | ✓ |
| Per-file artifacts, lazy compile on first import | Same layout but JIT compile on first bare-voss boot when cache empty/stale. Zero install ceremony, slower first boot. | |
| Bundled single module, git-head watermark | `harness.py` exporting `run_turn`. Cache key: git HEAD + file count. Simpler import; harder per-file regression isolation. | |
| Other / I'll describe it | — | |

**User's choice:** Per-file artifacts, sha keyed, eager compile.
**Notes:** Per-file isolation makes per-file regressions traceable. sha (not mtime) is reliable across checkouts. Stale cache is a loud structured error, never silent.

---

## Scope Bound for DOG-07

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal real turn under stub provider | `VOSS_HARNESS=compiled voss do "<fixture>"` exits 0 with non-empty TurnResult; parity test passes under StubProvider. Live providers deferred. | ✓ |
| Symbolic only — check + import; no real turn | `voss check` passes, compiled artifacts import cleanly. Cheapest, weakest dogfood. | |
| Full parity — compiled equals Python on all M1 commands, live + stub | Largest scope; overflows M4 into M5+. | |
| Other / I'll describe it | — | |

**User's choice:** Minimal real turn under stub provider.
**Notes:** Real dogfood, bounded. `voss edit` / `voss chat` / live providers stay on Python until proven; deferred to M5 or a dedicated hardening phase.

---

## Claude's Discretion

- Exact syntax of `use voss.harness as h` in `.voss` — researcher confirms parser surface; if absent, a small grammar/codegen extension precedes the `.voss` files.
- Exact `probable<Intent>` representation in `router.voss`.
- `voss compile <dir>` flag-compatibility with single-file form.
- Whether to add `--harness={python,compiled}` CLI flag alongside env var.
- `StaleHarnessCacheError` exception class location (`voss/harness/diagnostics.py` natural).
- Fixture task content for the parity test.
- `voss doctor` reporting shape for harness-cache freshness.

## Deferred Ideas

- Live-provider compiled parity — M5 or hardening phase.
- `voss edit` / `voss chat` compiled paths — deferred until `voss do` proves out.
- `/analyze` rewritten in `.voss` — M2 D-02 already deferred this.
- Auto-detect boot path / silent fallback — rejected.
- JIT compile-on-import — rejected.
- Bundled-module cache layout — rejected.
- Retiring `voss/harness/agent.py` — not M4.
- Codegen-snapshot tests on `.voss-cache/harness/*.py` — inherited M3 deferral.
- Compile-and-stub-run inside `voss check` — moved to pytest, not the gate.
- `voss check --speed-budget` flag — inherited M3 deferral.
- Rust harness shell — explicitly post-v0.1.
