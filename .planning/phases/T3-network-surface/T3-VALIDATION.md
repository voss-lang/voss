---
phase: T3
slug: network-surface
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-15
---

# Phase T3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Detailed Req→Test map lives in `T3-RESEARCH.md` §"Validation Architecture".
> Plans MUST reference test IDs from that map in their `<automated>` blocks.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` testpaths = `["tests"]` |
| **Quick run command** | `pytest tests/harness/test_rate_limit.py tests/harness/test_net_telemetry.py -x --tb=short` |
| **Full suite command** | `pytest tests/harness/ -x --tb=short` |
| **Estimated runtime** | ~15 seconds quick / ~45 seconds full |

---

## Sampling Rate

- **After every task commit:** `pytest tests/harness/test_rate_limit.py tests/harness/test_net_telemetry.py -x --tb=short`
- **After every plan wave:** `pytest tests/harness/ -x --tb=short`
- **Before `/gsd:verify-work`:** `pytest tests/ -x` (full suite green)
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

See `T3-RESEARCH.md` §"Validation Architecture" → "Phase Requirements → Test Map" for the full
35-row table mapping NET-01..NET-07 acceptance bullets to test files and pytest commands.

Each PLAN.md task in T3 MUST cite one or more row IDs from that table in its `<automated>` block.
The planner is responsible for assigning task IDs to test rows; this file does not duplicate the
map to avoid drift.

| Source of Truth | Section | Rows |
|-----------------|---------|------|
| T3-RESEARCH.md | Validation Architecture / Phase Requirements → Test Map | 35 rows (NET-01a..NET-07e) |

---

## Wave 0 Requirements

All test files are missing — Wave 0 must install scaffolding before any feature task runs:

- [ ] `tests/harness/test_web_fetch.py` — NET-01 (5 cases)
- [ ] `tests/harness/test_web_search.py` — NET-02 (4 cases)
- [ ] `tests/harness/mcp/__init__.py` — make `tests/harness/mcp/` a test package
- [ ] `tests/harness/mcp/test_mcp_config.py` — NET-03 config loader
- [ ] `tests/harness/mcp/test_mcp_client.py` — NET-03 subprocess mock + handshake
- [ ] `tests/harness/mcp/test_mcp_scope.py` — NET-04 permission scope (4 cases)
- [ ] `tests/harness/test_allow_net.py` — NET-05 gate + zero-socket invariant (6 cases)
- [ ] `tests/harness/test_net_telemetry.py` — NET-06 redact_url + events (5 cases)
- [ ] `tests/harness/test_rate_limit.py` — NET-07 TokenBucket (5 cases)
- [ ] `.github/workflows/mcp-integration.yml` — CI integration job for NET-03d
- [ ] Verify `pyyaml` in `pyproject.toml` main deps (researcher open question)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `voss mcp list` pretty output renders legibly in real terminal | NET-03 (UX) | Pretty-print human readability not asserted in unit tests | Run `voss mcp list` after configuring a fixture server; eyeball that name/command/tool block is readable. |
| Brave API key happy-path against real endpoint | NET-02 | Real network call requires API key; not in CI by default | Set `BRAVE_API_KEY`, run `voss do "search for httpx docs"` with `--allow-net`. |

All other phase behaviors have automated verification via the Req→Test map in `T3-RESEARCH.md`.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (every row in the Req→Test map currently `❌ Wave 0`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (after Wave 0 ships and verify-work passes)

**Approval:** pending
