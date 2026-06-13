---
phase: V22
slug: external-memory-docs-ingest
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-13
---

# Phase V22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from V22-RESEARCH.md `## Validation Architecture` (HIGH confidence). Test IDs are requirement-keyed; the planner binds them to task IDs at plan time.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, `pyproject.toml:L112`) |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/external_recall/ -q -x --ignore=tests/external_recall/test_golden_queries.py` |
| **Full suite command** | `.venv/bin/python -m pytest tests/external_recall/ tests/code_recall/ tests/memory/ -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~90 seconds (full incl. golden + embedding cold-load) |

*Use `.venv/bin/python` — bare python3 lacks deps (project convention).*

---

## Sampling Rate

- **After every task commit:** `quick run command` (excludes golden gate — embedding cold-load too slow per-commit)
- **After every plan wave:** `full suite command`
- **Before `/gsd-verify-work`:** Full suite green AND golden-query gate (`test_golden_queries.py`) passes — with and without chromadb
- **Max feedback latency:** ~30 seconds (quick)

---

## Per-Task Verification Map

Requirement-keyed (planner binds Task IDs). All ❌ W0 — Wave 0 RED scaffold creates the test files first. No threat refs (no `<threat_model>` surfaced — read-only ingest, no new network/auth surface; see Security note below).

| Req | Behavior | Test Type | Automated Command | File | Status |
|-----|----------|-----------|-------------------|------|--------|
| VXMEM-01 | Two `[[recall.sources]]` parse to 2 records (name/path/glob) | unit | `pytest tests/external_recall/test_config.py::test_parse_two_sources` | ❌ W0 | ⬜ |
| VXMEM-01 | No section → zero sources, zero I/O | unit | `pytest …test_config.py::test_no_section_zero_sources` | ❌ W0 | ⬜ |
| VXMEM-02 | `name="code"` → ValueError naming "code" | unit | `pytest …test_config.py::test_reserved_name_rejected` | ❌ W0 | ⬜ |
| VXMEM-02 | Duplicate names → ValueError | unit | `pytest …test_config.py::test_duplicate_name_rejected` | ❌ W0 | ⬜ |
| VXMEM-03 | `rm -rf .voss-cache/recall/` + re-ingest → working index (derived-cache) | integration (fake embed) | `pytest …test_incremental.py::test_derived_cache_rm_safe` | ❌ W0 | ⬜ |
| VXMEM-03 | Manifest: one hash entry per ingested file | unit (fake embed) | `pytest …test_incremental.py::test_manifest_has_hash_per_file` | ❌ W0 | ⬜ |
| VXMEM-04 | Multi-heading file splits on heading boundaries | unit | `pytest …test_chunker.py::test_heading_boundary_split` | ❌ W0 | ⬜ |
| VXMEM-04 | Heading-less file → exactly one chunk | unit | `pytest …test_chunker.py::test_headingless_one_chunk` | ❌ W0 | ⬜ |
| VXMEM-04 | Oversize section sub-splits (>800 chars → >1 chunk) | unit | `pytest …test_chunker.py::test_oversize_subsplit` | ❌ W0 | ⬜ |
| VXMEM-04 | `.txt` under glob NOT ingested | unit | `pytest …test_chunker.py::test_non_md_skipped` | ❌ W0 | ⬜ |
| VXMEM-04 | `#` inside code fence ≠ heading boundary | unit | `pytest …test_chunker.py::test_code_fence_heading_ignored` | ❌ W0 | ⬜ |
| VXMEM-05 | Touch one file → only its chunks re-embed (embed counter) | unit (fake embed + counter) | `pytest …test_incremental.py::test_touch_one_file_reembeds_only_it` | ❌ W0 | ⬜ |
| VXMEM-05 | Unchanged vault → zero embed calls (full re-embed = FAIL) | unit | `pytest …test_incremental.py::test_unchanged_zero_embeds` | ❌ W0 | ⬜ |
| VXMEM-05 | Deleted source file purges its chunks | unit (fake embed) | `pytest …test_incremental.py::test_deleted_file_purges_chunks` | ❌ W0 | ⬜ |
| VXMEM-06 | Session start does not block on ingest | unit (Event mock) | `pytest …test_background.py::test_session_does_not_block` | ❌ W0 | ⬜ |
| VXMEM-06 | Before-ready query → degraded/BM25, not error | unit | `pytest …test_background.py::test_degraded_before_ready` | ❌ W0 | ⬜ |
| VXMEM-06 | Source files byte-identical before/after ingest+recall (read-only) | unit (mtime+hash snapshot) | `pytest …test_background.py::test_source_files_readonly` | ❌ W0 | ⬜ |
| VXMEM-07 | `voss recall` shows `[<name>]`-labeled hits (plain) | CLI subprocess | `pytest …test_recall_cli.py::test_plain_labeled_hits` | ❌ W0 | ⬜ |
| VXMEM-07 | `voss recall --json` has correct `source` field | CLI subprocess | `pytest …test_recall_cli.py::test_json_source_field` | ❌ W0 | ⬜ |
| VXMEM-07 | chromadb uninstalled → BM25-only, no error | unit (chroma disabled) | `pytest …test_recall_cli.py::test_degradation_no_chromadb` | ❌ W0 | ⬜ |
| VXMEM-07 | Agent recall tool returns external hits | unit (agent tool call) | `pytest …test_agent_tool.py::test_agent_gets_external_hits` | ❌ W0 | ⬜ |
| VXMEM-08 | Golden gate: ~10 queries → expected `[<name>]` hit in top-5 | integration | `pytest tests/external_recall/test_golden_queries.py` | ❌ W0 | ⬜ |
| VXMEM-08 | Golden gate passes with chromadb uninstalled (BM25) | integration (chroma disabled) | `pytest …test_golden_queries.py -k bm25` | ❌ W0 | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · `pytest` = `.venv/bin/python -m pytest`*

---

## Wave 0 Requirements

- [ ] `voss/harness/recall/__init__.py` — new package
- [ ] `voss/harness/recall/external_index.py` — `ExternalSourceIndex`, `ExternalRecallService`, `extract_md_chunks` (imports `_split_oversize`/`_file_hash`/`_effective_embedding_model` from `code/semantic_index.py`)
- [ ] `tests/external_recall/__init__.py` + `conftest.py` — `fake_embed_fn` (copy from `tests/code_recall/conftest.py`), `fixture_vault_path`, `indexed_fixture_vault`, `chroma_disabled_env`
- [ ] `tests/external_recall/test_config.py` — VXMEM-01, VXMEM-02 (RED stubs)
- [ ] `tests/external_recall/test_chunker.py` — VXMEM-04 (RED stubs)
- [ ] `tests/external_recall/test_incremental.py` — VXMEM-03, VXMEM-05 (RED stubs)
- [ ] `tests/external_recall/test_background.py` — VXMEM-06 (RED stubs)
- [ ] `tests/external_recall/test_recall_cli.py` — VXMEM-07 CLI (RED stubs)
- [ ] `tests/external_recall/test_agent_tool.py` — VXMEM-07 agent tool (RED stubs)
- [ ] `tests/external_recall/test_golden_queries.py` — VXMEM-08 (RED stubs)
- [ ] `tests/fixtures/recall_vault/{getting-started,api-reference,changelog}.md` + `concepts/chunking.md` — committed fixture corpus, distinct vocab per file, deterministic heading structure

*`slow` marker already registered (`pyproject.toml:L114`) — no addition needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real operator vault (e.g. SecondBrain) ingests + recalls | VXMEM-03/07 | Real external vaults are machine-specific, not committable | Declare a `[[recall.sources]]` pointing at a real local vault; `voss recall <known-term>`; confirm `[<name>]` hit + source files untouched (`git status` clean in vault) |

*All phase-internal behaviors have automated verification; only real-vault smoke is manual.*

---

## Security Note

No `<threat_model>` block required: ingest is **read-only** (VXMEM-06 asserts zero source writes), introduces no new network/auth surface, and `path` is operator-declared (not attacker-controlled). Prompt-injection from ingested markdown is bounded — chunks are retrieved context, never executed (same posture as V19 code chunks). Symlink/path-escape under a declared source path is the one residual surface (research Pitfall 7 / assumption A2) — Wave 0 read-only test + `follow_symlinks=False` discovery cover it.

---

## Validation Sign-Off

- [x] All requirements have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive requirements without automated verify
- [x] Wave 0 covers all MISSING references (all test files + fixture vault)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (quick)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending (planner binds Task IDs; executor flips ❌→✅ per RED→GREEN)
