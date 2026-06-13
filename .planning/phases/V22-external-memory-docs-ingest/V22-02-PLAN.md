---
phase: V22-external-memory-docs-ingest
plan: 02
type: execute
wave: 1
depends_on: [V22-01]
files_modified:
  - voss/harness/config.py
  - voss/harness/recall/external_index.py
autonomous: true
requirements: [VXMEM-01, VXMEM-02, VXMEM-04]
must_haves:
  truths:
    - "Two [[recall.sources]] entries parse to exactly two {name,path,glob} records"
    - "Missing section yields zero sources and zero index I/O"
    - "Reserved names code/memory/global and duplicate names are rejected at load"
    - "Markdown files chunk on heading boundaries; preamble is its own chunk; heading-less = one chunk; oversize subsplits; non-md skipped; # inside code fence is not a boundary"
  artifacts:
    - path: "voss/harness/config.py"
      provides: "get_recall_sources() via tomllib, isolated from regex parser"
      contains: "def get_recall_sources"
    - path: "voss/harness/recall/external_index.py"
      provides: "extract_md_chunks heading-boundary chunker"
      contains: "def extract_md_chunks"
  key_links:
    - from: "voss/harness/config.py"
      to: "tomllib"
      via: "tomllib.load on config_path() for [[recall.sources]]"
      pattern: "import tomllib"
    - from: "voss/harness/recall/external_index.py"
      to: "voss.harness.code.semantic_index._split_oversize"
      via: "oversize subsplit reuse (verbatim import)"
      pattern: "_split_oversize"
---

<objective>
Turn the config and chunker tests GREEN. Two independent, self-contained units:
1. `get_recall_sources()` in `config.py` — a `tomllib` parse path for `[[recall.sources]]` array-of-tables (VXMEM-01) with reserved-name/duplicate validation (VXMEM-02), fully isolated from the existing regex parser.
2. `extract_md_chunks()` in `external_index.py` — ATX heading-boundary markdown chunker reusing `_split_oversize` verbatim (VXMEM-04).

Purpose: These are the two pure functions every downstream wave depends on (the index builds chunks from `extract_md_chunks`; the service reads sources from `get_recall_sources`). They have defined I/O — strong TDD candidates.
Output: GREEN `test_config.py` (4 tests) + `test_chunker.py` (5 tests).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V22-external-memory-docs-ingest/V22-CONTEXT.md
@.planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md

<interfaces>
config.py existing helpers (reuse): `config_path() -> Path` (L20-23). Existing regex blocks must stay untouched.
external_index.py reuse (imported in V22-01): `_split_oversize(start, end, lines, max_chars=800)`.

Contracts to implement (from V22-01 skeleton):
```python
def get_recall_sources() -> list[dict]:  # ordered [{name,path,glob}]; ValueError on reserved/duplicate
def extract_md_chunks(content: str) -> list[tuple[int, int, str]]:  # heading-boundary regions
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement get_recall_sources() tomllib parse path with validation</name>
  <read_first>
    - voss/harness/config.py:1-35 (module top, config_path, regex block patterns — confirm no tomllib import exists; the new path must NOT touch the regex functions)
    - .planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md Q3 (~L187-242) + Code Examples (~L696-740) — the verified get_recall_sources implementation shape
    - tests/external_recall/test_config.py (the RED tests to satisfy)
  </read_first>
  <files>voss/harness/config.py</files>
  <behavior>
    - test_parse_two_sources: a config with two `[[recall.sources]]` entries returns exactly 2 ordered dicts with correct name/path/glob (glob defaults to `**/*.md` when omitted)
    - test_no_section_zero_sources: config with no `[recall]` section (or no file) returns `[]` and performs zero index I/O
    - test_reserved_name_rejected: `name="code"` raises ValueError whose message contains "code"
    - test_duplicate_name_rejected: two entries with `name="docs"` raises ValueError naming the duplicate
  </behavior>
  <action>
    Add `import tomllib` at `config.py` module top (stdlib, Python ≥3.11 — floor confirmed). Add module constant `_RESERVED_SOURCE_NAMES = frozenset({"code", "memory", "global"})` (D-03). Implement `get_recall_sources()` per RESEARCH Q3/Code-Examples: read `config_path()`; if absent return `[]`; `tomllib.load(open(p,"rb"))` inside try/except `(OSError, tomllib.TOMLDecodeError)` → warn (RuntimeWarning) + return `[]`; pull `data.get("recall", {}).get("sources", [])`; if not a list return `[]`; iterate entries collecting `{name, path, glob}` with `glob` defaulting to `**/*.md`; raise `ValueError` on reserved name (message contains the offending name + lists the reserved set) and on duplicate name. Do NOT modify any existing regex parser function — this is a wholly separate function reading the same file independently (RESEARCH confirms no conflict: regex `[^\[]*` stops before `[[`).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/external_recall/test_config.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    `.venv/bin/python -m pytest tests/external_recall/test_config.py -x -q` passes all 4 tests. Existing config tests still pass: `.venv/bin/python -m pytest tests/ -k "config" -q` green (regex parser untouched).
  </acceptance_criteria>
  <done>get_recall_sources() parses array-of-tables via tomllib; reserved/duplicate names rejected; absent section → []; regex parser unaffected; 4 config tests GREEN.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement extract_md_chunks() heading-boundary chunker</name>
  <read_first>
    - voss/harness/code/semantic_index.py:36-89 (_split_oversize + extract_chunks — the boundary-then-subsplit pattern to mirror; preamble handling)
    - .planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md Q4 (~L244-320) + Pattern 2 (~L507-552) — verified algorithm, fence tracking, level-comparison rule
    - tests/external_recall/test_chunker.py (the RED tests to satisfy)
  </read_first>
  <files>voss/harness/recall/external_index.py</files>
  <behavior>
    - test_heading_boundary_split: a multi-heading string splits into the expected number of regions on heading boundaries (section runs to next heading of same-or-higher level per D-06/D-14)
    - test_headingless_one_chunk: a string with no ATX heading yields exactly one chunk (whole file, before any oversize split)
    - test_oversize_subsplit: a single section whose body exceeds 800 chars yields >1 chunk (via _split_oversize)
    - test_non_md_skipped: a `.txt` path is not ingested — assert at the ingest filter level (suffix in {.md,.markdown})
    - test_code_fence_heading_ignored: a `#`-prefixed line inside a ``` or ~~~ fence does NOT create a heading boundary
  </behavior>
  <action>
    Replace the `extract_md_chunks` NotImplementedError body with the RESEARCH Q4/Pattern-2 algorithm: split `content.splitlines(keepends=True)`; empty → `[]`. Walk lines tracking `in_fence` toggled on lines matching `^(?:```|~~~)`; skip heading detection while in fence (Pitfall 3). Collect ATX headings via `^(#{1,6})\s` with level = len of `#` run. No headings → `_split_oversize(1, total_lines, lines)`. Preamble before first heading → its own `_split_oversize` region. Each heading's section ends at the next heading whose level ≤ current level (same-or-higher closes; deeper continues — D-06/D-14), else EOF; emit via `_split_oversize`. Use the imported `_split_oversize` (do not reimplement). Setext headings out of scope (D-14: ATX is the floor).

    Also add the markdown suffix filter used by ingest (`{".md", ".markdown"}`) as a module constant `_MD_SUFFIXES` so `test_non_md_skipped` and the W2 build can both reference it — the chunker itself takes content, but the file-type gate lives beside it.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/external_recall/test_chunker.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    `.venv/bin/python -m pytest tests/external_recall/test_chunker.py -x -q` passes all 5 tests including `test_code_fence_heading_ignored` and `test_oversize_subsplit`. `_split_oversize` is imported, not redefined (grep: `grep -c "def _split_oversize" voss/harness/recall/external_index.py` returns 0).
  </acceptance_criteria>
  <done>extract_md_chunks splits on ATX heading boundaries with fence-aware detection, preamble chunk, heading-less single chunk, oversize subsplit via reused _split_oversize; .md/.markdown gate constant present; 5 chunker tests GREEN.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/external_recall/test_config.py tests/external_recall/test_chunker.py -q` → 9 GREEN
- `.venv/bin/python -m pytest tests/ -k "config" -q` → existing config tests still GREEN (regex parser untouched)
</verification>

<success_criteria>
Config parse + chunker are GREEN and reuse-faithful (`_split_oversize` imported verbatim, regex parser isolated). Downstream waves can build chunks and read sources.
</success_criteria>

<output>
Create `.planning/phases/V22-external-memory-docs-ingest/V22-02-SUMMARY.md` when done.
</output>
