---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 04
subsystem: cli
tags: [recall, cross-corpus, rrf, json-schema, redaction]
requires:
  - "V19-02 (CodeIndex.query/build)"
provides:
  - "voss recall <query> top-level verb — unified code+memory RRF recall, [code]/[memory] labels"
  - "--json documented schema: source/locator/path/line_start/line_end/score/excerpt"
  - "--refresh explicit reindex (D-13 trigger #3); secret-shape excerpt redaction (T-V19-04)"
affects: [V19-05]
tech-stack:
  added: []
  patterns:
    - "cross-corpus fusion = MemoryStore._rrf_merge([code_hits, mem_hits]) — rank-based, corpus-agnostic (D-09); code: prefix prevents locator collision (Pitfall 8)"
key-files:
  created: []
  modified:
    - voss/harness/cli.py
    - voss/harness/code/semantic_index.py
    - tests/code_recall/test_chunker.py
key-decisions:
  - "Excerpt redaction via secret-shape regexes (AKIA/sk-/ghp_/xox/key-value heuristic) applied to plain AND json output — excerpts are raw source, the only leak vector in the schema"
  - "--refresh rebuilds M10 (best-effort) before CodeIndex.build() so chunk boundaries refresh with symbols"
  - "MemoryStore.recall failure degrades to code-only hits (missing/corrupt memory store never kills the verb)"
requirements-completed: [VSEM-05]
duration: 15 min
completed: 2026-06-12
---

# Phase V19 Plan 04: `voss recall` CLI Verb Summary

Top-level `voss recall` (D-09 user-locked): queries CodeIndex AND MemoryStore, fuses via `MemoryStore._rrf_merge`, labels every hit `[code]`/`[memory]`, block-per-hit plain output with `path:line` headers (D-10), `--json` with the documented source-field schema, `--refresh` explicit reindex, registered in `AGENT_COMMANDS` beside `memory_group`.

- Duration: ~15 min (commit c173005, 2026-06-12)
- Tasks: 1/1
- Files: 3 modified

## Verification Log (acceptance gates)

- `test_recall_cli.py` 2/2 (exit-0 labeled; json schema + NO secret strings) — PASS
- `recall_cmd` in `AGENT_COMMANDS` (after memory_group) — PASS
- fusion via `MemoryStore._rrf_merge` (no hand-rolled merge) — PASS
- `--refresh` → best-effort M10 `build_index` then `code_index.build()` — PASS
- plain output block-per-hit, `path:line_start` headers for code hits — PASS
- live run: `voss recall "reciprocal rank fusion merge" --top 3` on this repo exits 0 with `[code] path:line` hits — PASS
- coherence: `tests/harness/ -k cli` 130 passed in 10.7s; chunker suite 5/5 — PASS

## Deviations from Plan

- **[Rule 1 - V19-02 bug] `_split_oversize` infinite recursion** — Found during: live-repo coherence run | a single line >800 chars (minified/long-literal files in this repo) recursed forever: line-midpoint splitting cannot subdivide one line, and 2-line oversize regions produced an identical left half | Fix: `end <= start` base case returns the line whole (embedding window truncates), `mid` clamped to `end-1` so both halves strictly shrink | Files: semantic_index.py + regression test `test_oversize_single_long_line` | Note: the flaw is verbatim in the RESEARCH "verified algorithm" — verified-for-schema ≠ verified-for-termination | Commit c173005.
- **[Rule 2 - missing critical] excerpt secret redaction** — the json test asserts no secret strings, but excerpts ARE raw source; emitting "only Hit fields" (the plan's wording) was insufficient. Added `_redact_recall_text` secret-shape pass over excerpts in both output modes.

**Total deviations:** 2 auto-fixed. **Impact:** recall robust on real-world files; T-V19-04 actually mitigated rather than assumed.

## Next Phase Readiness

V19-05 (injection) owns the `do_cmd`/`chat_cmd` wiring + `_render_code_recall_text` + `[code_recall]` config — its 3 RED tests (`test_token_cap`, `test_evictable`, `test_off_switch`) plus V19-06's enrichment trio are the only failures left in `tests/code_recall/`.

## Self-Check: PASSED
