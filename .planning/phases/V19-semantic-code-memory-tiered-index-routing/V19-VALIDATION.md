---
phase: V19
slug: semantic-code-memory-tiered-index-routing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase V19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `V19-RESEARCH.md` § Validation Architecture (full per-requirement test map lives there).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, `pyproject.toml:110`) |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/code_recall/ -q -x --ignore=tests/code_recall/test_golden_queries.py` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -q --ignore=tests/eval/golden --ignore=tests/eval/matrix` |
| **Estimated runtime** | quick ~10s (fake embedder); full suite ~minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** `.venv/bin/python -m pytest tests/code_recall/ tests/memory/ tests/harness/test_agent_packing.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green; golden-query gate (`-m slow`) runs on the wave that has a full index
- **Max feedback latency:** 60 seconds (quick command, fake embedder — no model load)

---

## Per-Task Verification Map

Plan/task IDs filled by planner. Requirement→test mapping locked from RESEARCH.md:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | VSEM-01..08 | — | — | unit stubs (RED) | `tests/code_recall/` scaffold | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VSEM-01 | — | chunk text never eval'd/exec'd | unit (fake embed) + integration | `pytest tests/code_recall/test_chunker.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VSEM-02 | — | N/A | unit (embed call counter) | `pytest tests/code_recall/test_incremental.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VSEM-03 | — | N/A | unit (threading) | `pytest tests/code_recall/test_background.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VSEM-04 | — | degradation never crashes | unit + perf | `pytest tests/code_recall/test_code_recall_tool.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | V19-03 | 2 | D-13 trigger #2 | — | re-hash only the written file | unit (per-file embed counter) | `pytest tests/code_recall/test_incremental.py::test_targeted_rehash_on_fs_write -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VSEM-05 | — | no secrets in JSON output | CLI subprocess | `pytest tests/code_recall/test_recall_cli.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VSEM-06 | — | injection capped/evictable | unit | `pytest tests/code_recall/test_injection.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VSEM-07 | — | fail-closed role resolution; zero LLM when off | unit (stub provider) | `pytest tests/code_recall/test_enrichment.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | VSEM-08 | — | budget cap aborts cleanly | unit (stub provider) | `pytest tests/code_recall/test_enrichment.py::test_budget_cap_abort -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | all (quality) | — | N/A | integration `-m slow` | `pytest tests/code_recall/test_golden_queries.py -x -m slow` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | all (coherence) | — | N/A | integration | existing `voss do`/`voss chat` regression suite | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/code_recall/__init__.py` — new test subdirectory
- [ ] `tests/code_recall/conftest.py` — shared fixtures: `fake_embed_fn`, `indexed_fixture_repo`, `chroma_disabled_env`, `stub_provider`
- [ ] `tests/code_recall/test_chunker.py` — VSEM-01 stubs
- [ ] `tests/code_recall/test_incremental.py` — VSEM-02 stubs + `test_targeted_rehash_on_fs_write` (D-13 trigger #2)
- [ ] `tests/code_recall/test_background.py` — VSEM-03 stubs
- [ ] `tests/code_recall/test_code_recall_tool.py` — VSEM-04 stubs
- [ ] `tests/code_recall/test_recall_cli.py` — VSEM-05 stubs
- [ ] `tests/code_recall/test_injection.py` — VSEM-06 stubs
- [ ] `tests/code_recall/test_enrichment.py` — VSEM-07/08 stubs
- [ ] `tests/code_recall/test_golden_queries.py` — quality gate stub
- [ ] `slow` marker added to `pyproject.toml [tool.pytest.ini_options]` markers list

**Wave-0 anti-pattern guard (project memory):** scaffold stubs MUST be written against the REAL module API surface (import paths, class/function names from the plans), not ad-libbed — verify imports resolve against planned module paths before xfail-gating; use `xfail(strict=True)` or plain failing asserts, never `xfail(strict=False)`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-model retrieval feel on Voss repo | quality | p95 + golden gate are automated, but ranking "feels right" sanity is human | build full index locally, run `voss recall "where do we handle retry backoff"`, eyeball top-5 |
| Ollama enrichment end-to-end | VSEM-07 | requires local Ollama daemon + pulled model | enable profile + `index_enrich` config, run reindex, confirm summaries + ledger line |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
