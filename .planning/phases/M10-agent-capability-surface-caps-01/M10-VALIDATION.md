---
phase: M10
slug: agent-capability-surface-caps-01
status: ready-for-verify-work
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-18
closed: 2026-05-18
---

# Phase M10 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest for harness/code-intel; pytest-textual-snapshot/Pillow for TUI snapshots; py_compile for syntax smoke |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python3 -m pytest tests/harness/test_code_config.py tests/harness/test_code_index.py tests/harness/test_code_lsp.py tests/harness/test_code_search.py tests/harness/test_code_tools.py tests/harness/test_code_context.py -q` |
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
| M9-08-01 | M9-08 | 8 | CODE-07 | T-M10-UI | CodeIntelPanel idle/results/focused states and SubAgentPanel precedence work | snapshot/unit | `python3 -m pytest tests/harness/tui/test_code_intel_panel.py tests/harness/tui/test_code_intel_region_share.py tests/harness/tui/test_live_visualization.py tests/harness/tui/test_no_new_runtime_hooks.py -q` | yes | green |
| M10-00-01 | 00 | 0 | CODE-07 | T-M10-GATE | M9-08 completed before M10 source work | source/test | `test -f .planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md && rg -n "Outcome: COMPLETE|M10 may now proceed" .planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md` | yes | green |
| M10-00-02 | 00 | 0 | CODE-01..07 | T-M10-SCOPE | Scope and memory-class guards pass against current baseline | source/test | `python3 -c 'from pathlib import Path; import re, sys; forbidden=re.compile(r"file.?watch|completion|hover|diagnostics|rename|M11|M12|M13|M14|M15|marketplace|MCP bridge|multi-agent in chat|long-running", re.I); allowed=re.compile(r"defer|deferred|out of scope|non-goal|forbidden|scope fence|No completion|No file watch|No file watcher|no file-watch|No new|No backend|not exposed|without file-watch|Security enforcement|Threat ID|long-running LSP server|installed-version diagnostics|test_code_|watchdog|watchfiles|codeAction|code_action", re.I); bad=[]; root=Path(".planning/phases/M10-agent-capability-surface-caps-01"); [bad.append(f"{p}:{i}:{line.strip()}") for p in root.glob("M10-*-PLAN.md") if p.name!="M10-00-PLAN.md" for i,line in enumerate(p.read_text().splitlines(),1) if forbidden.search(line) and not allowed.search(line)]; print("\n".join(bad)); sys.exit(1 if bad else 0)'` | yes | green |
| M10-01-01 | 01 | 1 | CODE-01 | T-M10-CACHE | Config defaults and SQLite index path are deterministic | unit/source | `python3 -m pytest tests/harness/test_code_config.py tests/harness/test_code_index.py -q` | yes | green |
| M10-01-02 | 01 | 1 | CODE-01 | T-M10-CACHE | SPEC is amended from `index.json` to `index.db`; fixtures exist under `tests/fixtures/code/` | source/smoke | `rg -n "index\\.db|SQLite" .planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md && rg -n "shared_entry|helper_value|main" tests/fixtures/code` | yes | green |
| M10-02-01 | 02 | 2 | CODE-02 | T-M10-PROC | LSP adapter and registry launch lazily, degrade cleanly, and reap processes | unit/integration | `python3 -m pytest tests/harness/test_code_lsp.py -q` | yes | green |
| M10-02-02 | 02 | 2 | CODE-02 | T-M10-LIVE | Optional live server smoke skips or reports installed versions clearly | live/optional | `python3 -m pytest tests/harness/test_code_lsp_live.py -q` | yes | green/skipped if servers absent |
| M10-03-01 | 03 | 3 | CODE-03 | T-M10-SUBPROC | ast-grep JSON parsing, timeout handling, and regex fallback work | unit/integration | `python3 -m pytest tests/harness/test_code_search.py -q` | yes | green |
| M10-04-01 | 04 | 4 | CODE-04 | T-M10-TOOLS | Code tools are read-only, permission-safe, and registered in the toolset | unit/integration | `python3 -m pytest tests/harness/test_code_tools.py tests/harness/test_tools.py tests/harness/test_permissions_modes.py -q` | yes | green |
| M10-04-02 | 04 | 4 | CODE-05 | T-M10-CLI | `/symbol`, `/refs`, `/refresh` register with help and execute against CodeIntelService | unit/e2e | `python3 -m pytest tests/harness/test_repl_slash.py tests/e2e/test_slash_matrix.py -q -k "symbol or refs or refresh or registry"` | yes | green |
| M10-04-03 | 04 | 4 | CODE-04 | T-M10-REDACT | Tool results are bounded, redaction-safe, and telemetry-safe before persistence | unit/integration | `python3 -m pytest tests/harness/test_code_tools.py tests/harness/test_session_redaction.py tests/harness/test_telemetry.py -q` | yes | green |
| M10-05-01 | 05 | 5 | CODE-06 | T-M10-CTX | `## Project Index` injection is bounded and absent when disabled | unit/integration | `python3 -m pytest tests/harness/test_code_context.py tests/harness/test_happy_path_integration.py -q -k "project_index or code_index or resume"` | yes | green |
| M10-05-02 | 05 | 5 | CODE-07 | T-M10-UI | Code-intel renderer bridge updates CodeIntelPanel without backend-to-TUI coupling | tui/integration | `python3 -m pytest tests/harness/tui/test_code_intel_integration.py tests/harness/tui/test_code_intel_region_share.py -q` | yes | green |
| M10-06-01 | 06 | 6 | CODE-01..07 | T-M10-E2E | Full code-intel happy path covers index, search, LSP fallback, tools, slash, and context injection | integration | `python3 -m pytest tests/harness/test_code_integration.py tests/harness/test_code_tools.py tests/harness/test_code_context.py tests/harness/tui/test_code_intel_integration.py -q` | yes | green |
| M10-06-02 | 06 | 6 | CODE-01/CODE-06 | T-M10-PERF | 10K/100K scan latency and partial-index warning behavior are measured | perf/manual | Recorded in M10-06 SUMMARY (manual checkpoint) | yes | green (measured) |
| M10-06-03 | 06 | 6 | CODE-01..07 | T-M10-REGRESS | Runtime/recorder/M8 invariants remain unchanged and no new harness memory classes exist beyond existing `MemoryStore` | source/test | `python3 -m pytest tests/harness/test_code_invariants.py tests/harness/tui/test_no_new_runtime_hooks.py -q` | yes | green |

*Status: pending / green / red / flaky.*

---

## Wave 0 Requirements

- [x] `tests/fixtures/code/` - minimal Python, JS/TS, Rust, and Go fixture repos with known definitions/references.
- [x] `tests/harness/test_code_index.py` - SQLite index schema, scan determinism, refresh.
- [x] `tests/harness/test_code_lsp.py` - LSP adapter lifecycle, missing-server fallback, orphan audit.
- [x] `tests/harness/test_code_search.py` - ast-grep JSON parsing and regex fallback.
- [x] `tests/harness/test_code_tools.py` - tool registry and read-only envelopes.
- [x] `tests/harness/test_code_context.py` - system-context injection size and disable path.
- [x] `tests/harness/tui/test_code_intel_panel.py` - CodeIntelPanel behavior and region-share precedence.
- [x] `tests/harness/test_code_integration.py`, `tests/harness/test_code_perf.py`, `tests/harness/test_code_invariants.py` - final integration, performance, and invariant closeout.

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
