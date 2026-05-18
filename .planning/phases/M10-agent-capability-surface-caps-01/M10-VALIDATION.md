---
phase: M10
slug: agent-capability-surface-caps-01
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-18
---

# Phase M10 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest for harness/code-intel; pytest-textual-snapshot/Pillow for TUI snapshots; py_compile for syntax smoke |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python3 -m pytest tests/harness/test_code_intel*.py tests/harness/test_cli_code_intel*.py -q` |
| **Full suite command** | `python3 -m pytest tests/harness tests/harness/tui -q` |
| **Estimated runtime** | ~60-180 seconds focused, environment dependent |

---

## Sampling Rate

- **After every task commit:** Run the task's focused pytest command plus `python3 -m py_compile` for any new module package.
- **After every plan wave:** Run `python3 -m pytest tests/harness tests/harness/tui -q`.
- **Before `/gsd:verify-work`:** Focused M10/M9-08 tests must be green; broader known non-M10 environmental blockers must be listed in the phase summary if still present.
- **Max feedback latency:** 180 seconds for focused code-intel/TUI feedback.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| M10-00-01 | 00 | 0 | CODE-07 | T-M10-UI | M9-08 side-region contract exists before M10 executes | source/test | `test -f .planning/phases/M9-tui-shell-tui-01/M9-08-PLAN.md && rg -n "CodeIntelPanel|SubAgentPanel" .planning/phases/M9-tui-shell-tui-01/M9-08-PLAN.md` | W0 | pending |
| M10-01-01 | 01 | 1 | CODE-01 | T-M10-CACHE | Cache path stays under `.voss-cache/code/`; schema is deterministic | unit | `python3 -m pytest tests/harness/test_code_index.py -q` | W0 | pending |
| M10-01-02 | 01 | 1 | CODE-01 | T-M10-CACHE | SPEC is amended from `index.json` to `index.db` | source | `rg -n "index\\.db|SQLite" .planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md` | yes | pending |
| M10-02-01 | 02 | 2 | CODE-02 | T-M10-PROC | LSP servers are lazy-launched and reaped on shutdown | unit/integration | `python3 -m pytest tests/harness/test_code_lsp.py -q` | W0 | pending |
| M10-02-02 | 02 | 2 | CODE-02 | T-M10-DEGRADE | Missing language server returns structured `lsp_unavailable` | unit | `python3 -m pytest tests/harness/test_code_lsp.py -q -k unavailable` | W0 | pending |
| M10-03-01 | 03 | 2 | CODE-03 | T-M10-SUBPROC | Missing `ast-grep` uses regex fallback, not an exception | unit/integration | `python3 -m pytest tests/harness/test_code_search.py -q` | W0 | pending |
| M10-04-01 | 04 | 3 | CODE-04 | T-M10-REDTACT | Tool results are bounded, read-only, and redaction-safe before persistence | unit/integration | `python3 -m pytest tests/harness/test_code_tools.py tests/harness/test_session_redaction.py -q` | W0 | pending |
| M10-05-01 | 05 | 3 | CODE-05 | T-M10-CLI | `/symbol`, `/refs`, `/refresh` have help and no reserved-name collision | unit/integration | `python3 -m pytest tests/harness/test_slash*.py -q -k "symbol or refs or refresh"` | W0 | pending |
| M10-06-01 | 06 | 3 | CODE-06 | T-M10-CTX | `## Project Index` injection is bounded and absent when disabled | unit/integration | `python3 -m pytest tests/harness/test_code_context.py -q` | W0 | pending |
| M10-07-01 | 07 | 4 | CODE-07 | T-M10-UI | CodeIntelPanel idle/results/focused states and SubAgentPanel precedence work | snapshot/unit | `python3 -m pytest tests/harness/tui/test_code_intel_panel.py tests/harness/tui/test_snapshots.py -q` | W0 | pending |
| M10-08-01 | 08 | 4 | CODE-01..07 | T-M10-REGRESS | Runtime/recorder/M8 invariants remain unchanged | source/test | `rg -n "class .*Memory" voss/harness || true; python3 -m pytest tests/harness/test_no_new_runtime_hooks.py -q` | yes | pending |

*Status: pending / green / red / flaky.*

---

## Wave 0 Requirements

- [ ] `tests/harness/fixtures/code/` - minimal Python, JS/TS, Rust, and Go fixture repos with known definitions/references.
- [ ] `tests/harness/test_code_index.py` - SQLite index schema, scan determinism, refresh.
- [ ] `tests/harness/test_code_lsp.py` - LSP adapter lifecycle, missing-server fallback, orphan audit.
- [ ] `tests/harness/test_code_search.py` - ast-grep JSON parsing and regex fallback.
- [ ] `tests/harness/test_code_tools.py` - tool registry and read-only envelopes.
- [ ] `tests/harness/test_code_context.py` - system-context injection size and disable path.
- [ ] `tests/harness/tui/test_code_intel_panel.py` - CodeIntelPanel behavior and region-share precedence.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Optional real language-server smoke for all four headline servers | CODE-02 | CI may not have `pyright`, `typescript-language-server`, `rust-analyzer`, and `gopls` installed | Install the four servers locally, run the focused live-LSP marker, and record installed versions plus pass/fail in the summary. |
| 100K-LoC latency budget | CODE-01/CODE-06 | Synthetic large fixture may be too expensive for routine focused runs | Run the generated large-fixture benchmark once before closeout; if it exceeds 30s, assert partial-index warning behavior. |

---

## Validation Sign-Off

- [x] All planned task areas have automated verify commands or Wave 0 test dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing test infrastructure references.
- [x] No watch-mode flags are required; M10 uses session-start and on-demand refresh only.
- [x] Feedback latency target is under 180 seconds for focused checks.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-05-18
