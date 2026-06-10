---
phase: E2
slug: golden-tasks-repo-matrix
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase E2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Generated from `E2-RESEARCH.md` §Validation Architecture. Per-task map filled by the planner.
> Requirements are CONTEXT-decision-driven (D-01..D-04) — no locked EVGLD-* IDs yet (no SPEC).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Interpreter** | `.venv/bin/python` (bare `python3` lacks deps — REQUIRED) |
| **Quick run command** | `.venv/bin/python -m pytest tests/eval/ -k matrix -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/eval/ -q` |
| **Matrix stub run** | `VOSS_DEV=1 .venv/bin/python -m voss.eval... --suite matrix --stub` (hermetic, no model calls) |
| **Toolchains required** | python3+pytest · cargo · node (all verified present 2026-06-10; no global tsc → TS uses `node --experimental-strip-types --test`) |
| **Estimated runtime** | quick <15s · matrix-stub bounded by fixture count |

---

## Sampling Rate

- **After every task commit:** quick command (matrix-scoped).
- **After every plan wave:** full `tests/eval/` suite.
- **Before `/gsd-verify-work`:** matrix stub run green for all available-toolchain cells; skipped cells explicitly recorded (never silent-green).
- **Live proof run:** manual, `VOSS_DEV=1 --auth codex`, within turn caps — NOT in the automated sampling loop (subscription-gated).

---

## Per-Task Verification Map

*Filled by the planner. Keyed to CONTEXT decisions D-01..D-04 + matrix cells. Seed rows:*

| Area | Decision | Test Type | Automated Command (stub/hermetic) | Status |
|------|----------|-----------|-----------------------------------|--------|
| Synthetic fixtures exist | D-01 | structural | `pytest -k matrix_fixtures_present` (manifest+module+test per lang) | ⬜ pending |
| Fixtures build/test natively | D-01 | toolchain | `pytest -k fixture_toolchain_green` (pytest/cargo test/node --test exit 0) | ⬜ pending |
| Matrix suite loads | D-02 | unit | `pytest -k matrix_suite_loads` (load_suite('matrix') → 12 cells) | ⬜ pending |
| Per-language gates wired | D-04 | unit | `pytest -k matrix_checks_present` (each shape cell has ≥1 cmd-exit-0 + edit file-contains) | ⬜ pending |
| Cognition check | D-04 | unit | `pytest -k cognition_architecture_token` (analyze cell file-contains lang tooling token) | ⬜ pending |
| Toolchain skip recorded | D-03 | unit | `pytest -k toolchain_absent_skip` (missing tool → `skipped: toolchain-absent`, not green) | ⬜ pending |
| Preflight prints availability | D-03 | behavior | `pytest -k preflight_toolchain_print` (run header lists py/rust/ts ✓/✗) | ⬜ pending |
| `--require-all-toolchains` strict | D-03 | unit | `pytest -k require_all_toolchains_fails` (missing tool → run fails) | ⬜ pending |
| summary.md skipped column | D-03 | unit | `pytest -k summary_skipped_column` | ⬜ pending |
| Matrix stub end-to-end | D-01..04 | integration | matrix `--stub` run executes all available cells, no model calls | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/eval/test_matrix.py` — RED stubs for fixture-present / suite-loads / checks-present / cognition / skip / preflight / summary
- [ ] Reuse existing eval conftest (`VOSS_DEV=1`, stub provider) — no new framework
- [ ] Toolchains preverified present (cargo/node/pytest) — gate cells on `shutil.which`

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Live cognition + edit correctness per language | D-04 | live model output varies; subscription-gated | `VOSS_DEV=1 ... --suite matrix --auth codex` within caps; confirm shape-sensitive cells gate_pass, skipped cells recorded |

---

## Validation Sign-Off

- [ ] All matrix cells have an automated stub-mode assertion or Wave 0 dependency
- [ ] Skipped-toolchain cells provably recorded (not silent-green)
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s (quick)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
