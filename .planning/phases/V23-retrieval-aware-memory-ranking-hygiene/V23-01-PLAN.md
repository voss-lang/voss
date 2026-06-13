---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/memory/test_retrieval_ranking.py
  - tests/memory/conftest.py
autonomous: true
requirements: [VRNK-01, VRNK-02, VRNK-03, VRNK-04, VRNK-05, VRNK-06, VRNK-07, VRNK-08]

must_haves:
  truths:
    - "Running the V23 test module collects and executes (no import/collection error)"
    - "Every VRNK-01..08 behavior has at least one named RED test"
    - "tests/memory/ test files can use tmp_voss_repo + chroma_disabled_env fixtures"
  artifacts:
    - path: "tests/memory/test_retrieval_ranking.py"
      provides: "RED scaffold for all 8 VRNK requirements"
      contains: "def test_"
      min_lines: 120
    - path: "tests/memory/conftest.py"
      provides: "Fixture bridge so tests/memory/ inherits tests/harness/ fixtures"
      contains: "pytest_plugins"
  key_links:
    - from: "tests/memory/test_retrieval_ranking.py"
      to: "voss.harness.memory_store.MemoryStore"
      via: "import + instantiate"
      pattern: "from voss.harness.memory_store import"
    - from: "tests/memory/conftest.py"
      to: "tests/harness/conftest.py"
      via: "pytest_plugins re-export"
      pattern: "pytest_plugins"
---

<objective>
Create the Wave 0 RED test scaffold that pins all eight V23 requirements (VRNK-01..08) BEFORE any feature code exists. This is the tests-first gate: every later plan turns one or more of these RED tests GREEN.

Purpose: Locks the Nyquist validation contract (V23-VALIDATION.md) into executable form so feature plans have a concrete, falsifiable target.
Output: `tests/memory/test_retrieval_ranking.py` (RED stubs for all 8 reqs) + `tests/memory/conftest.py` (fixture bridge to `tests/harness/conftest.py`).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-SPEC.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-VALIDATION.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-PATTERNS.md

<interfaces>
<!-- Confirmed live signatures the scaffold targets. No exploration needed. -->

From voss/harness/memory_store.py:
- class Hit (dataclass) — fields include: source, locator, score, excerpt
- def make_id(source: str, locator: str, seq: int | None = None) -> str
- class MemoryStore:
    def __init__(self, cwd, *, cap_bytes=..., root_override: Path | None = None)  # root_override added by V21
    def bind(self, *, session_id: str) -> "MemoryStore"
    def recall(self, query, *, top_k=5, source=None) -> list[Hit]
    def vacuum(self) -> int
    def _maybe_evict(self, source, *, est_bytes=0) -> None
    self.root  # = cwd/.voss/memory
    self.cwd

Fixtures (tests/harness/conftest.py — NOT auto-visible under tests/memory/):
- tmp_voss_repo(tmp_path) -> Path  # creates .voss/memory/{turns,ledgers,decisions,conventions,notes,chroma,.locks}
- chroma_disabled_env(monkeypatch)  # forces chromadb None for BM25-only paths
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bridge tests/harness fixtures into tests/memory/</name>
  <read_first>
    - tests/harness/conftest.py:88-105 (tmp_voss_repo definition), :277-291 (chroma_disabled_env) — the fixtures to expose
    - tests/memory/ — currently has __init__.py + test_episodic/semantic/working.py, NO conftest.py (confirmed)
    - V23-PATTERNS.md:428-465 (fixture usage notes)
  </read_first>
  <action>
    Create `tests/memory/conftest.py`. It must make `tmp_voss_repo` and `chroma_disabled_env` (defined only in `tests/harness/conftest.py`) available to test files under `tests/memory/`. Use `pytest_plugins = ["tests.harness.conftest"]` at module top so pytest loads the harness conftest as a plugin for this directory. Do NOT redefine the fixtures (no copy-paste) — single source of truth stays in tests/harness/conftest.py. Add a one-line module docstring naming V23 as the reason. Verify the package path `tests.harness.conftest` is importable (tests/ and tests/harness/ both have __init__.py or are collectable as packages — if `tests/harness/__init__.py` is absent, the plugin string still resolves via rootdir; confirm collection succeeds in the verify step).
  </action>
  <acceptance_criteria>
    - File `tests/memory/conftest.py` exists and contains the literal token `pytest_plugins`
    - The string references `tests.harness.conftest` (or the resolvable equivalent)
    - No `def tmp_voss_repo` or `def chroma_disabled_env` redefinition appears in the new file (grep: `grep -c "def tmp_voss_repo\|def chroma_disabled_env" tests/memory/conftest.py` == 0)
    - `.venv/bin/python -m pytest tests/memory/ --collect-only -q` exits 0 (no collection error)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/ --collect-only -q 2>&1 | tail -5</automated>
  </verify>
  <done>tests/memory/ test files can request tmp_voss_repo and chroma_disabled_env without redefining them; collection passes.</done>
</task>

<task type="auto">
  <name>Task 2: RED scaffold covering VRNK-01..08</name>
  <read_first>
    - V23-VALIDATION.md:39-51 (per-task verification map — the -k filter keywords each test must match) and :43-60 (Wave 0 requirements + byte-identical baseline)
    - V23-RESEARCH.md:796-836 (Phase Requirements → Test Map — exact behaviors + test names per req)
    - V23-PATTERNS.md:466-533 (os.utime mtime seeding, byte-identical pattern, CliRunner pattern)
    - tests/harness/test_memory_eviction.py (store setup + os.utime seeding analog)
    - tests/harness/test_agent_packing.py:202-208 (test_no_pack_byte_identical — byte-identical assertion analog)
    - V23-SPEC.md:97-109 (the 11 acceptance criteria each test must encode)
  </read_first>
  <action>
    Create `tests/memory/test_retrieval_ranking.py` as the single consolidated V23 RED scaffold (path mandated by V23-VALIDATION.md). Write executable test functions — NOT bare `pytest.skip` stubs — that assert the target post-V23 behavior so they fail RED today and flip GREEN as feature plans land. Each test must contain a keyword matching its V23-VALIDATION `-k` filter (telemetry, floor, rescore, byte_identical, evict, reindex, drift, pin, cli). Required test functions, one-or-more per requirement:
      - VRNK-01: `test_telemetry_recorded_on_agent_recall` (asserts sidecar `.voss/memory/.retrieval.jsonl` gains a line / `retrieval_count==1` for a returned locator after the agent-path record call), `test_telemetry_not_recorded_on_cli_recall` (CLI recall leaves count 0), `test_recall_does_not_mutate_memory_file_mtime` (capture file stat mtime+size before/after recall, assert identical).
      - VRNK-02: `test_no_match_query_returns_zero_hits_with_floor` (junk query → 0 hits, floors default-on), `test_floor_disabled_restores_fill` (chroma_floor=0 + bm25_floor_ratio=0 → pre-V23 fill).
      - VRNK-03: `test_rescore_deterministic_under_fixture` (fixed `.retrieval.jsonl` telemetry → asserted re-ranking), `test_rescore_off_byte_identical` (default config → recall output order+scores+excerpts byte-identical to a captured baseline), `test_empty_telemetry_rescore_on_is_noop` (rescore on + no telemetry → identical ordering).
      - VRNK-04: `test_retrieval_aware_eviction_evicts_never_retrieved_first` (over-quota: old-but-recently-retrieved survives, newer-never-retrieved evicts), `test_eviction_mtime_fallback_no_sidecar` (no `.retrieval.jsonl` → mtime ordering unchanged).
      - VRNK-05: `test_reindex_check_detects_drift` (hand-edit conventions file → `--check` style call exit 1 + stale locator listed), `test_reindex_repairs_then_check_clean` (reindex → re-embed count ≥1 → subsequent check exit 0), `test_reindex_chroma_absent_exit_0` (chroma_disabled_env → both verbs exit 0 with notice).
      - VRNK-06: `test_pinned_memory_always_injected` (pinned text present in assembled-context string for a query that never recalls it), `test_pinned_survives_over_quota_eviction`, `test_pin_cap_overflow_warns`.
      - VRNK-07: `test_pin_unpin_list_cli` (CliRunner: pin → list --pinned shows → unpin → empty), `test_show_displays_telemetry`, `test_cli_unknown_locator_exits_1`.
      - VRNK-08: `test_rescore_off_byte_identical` already covers the baseline lock; add `test_existing_memory_suites_marker` as a thin sentinel only if needed (prefer relying on the regression command in V23-08).
    Use `tmp_voss_repo` for store setup and `chroma_disabled_env` for BM25-only / chroma-absent paths. Use `os.utime` for deterministic mtime seeding (PATTERNS.md analog). Reference target APIs that do not yet exist (`store._record_telemetry`, `store._load_telemetry_compacted`, `store.reindex(...)`, `store._load_pins`, the `pin/unpin/list/show/reindex` CLI verbs in `voss.harness.memory_cli.memory_group`) — these RED references are intentional and define the contract for later plans. Where an API is genuinely V21-gated (global-store pin injection per D-09), write the test against the project-store path now and add ONE `@pytest.mark.xfail(reason="V21 global-store dual fusion not yet merged", strict=False)` test stub for the global path labeled clearly — do not let it false-green (strict=False so it is XFAIL not XPASS surprise; the wiring plan V23-06 un-xfails it). Do NOT ad-lib fake module APIs that diverge from the confirmed signatures above (memory: GSD scaffold fictional API hazard) — verify each referenced symbol name against the <interfaces> block + PATTERNS.md before writing.
  </action>
  <acceptance_criteria>
    - File `tests/memory/test_retrieval_ranking.py` exists with ≥ 15 `def test_` functions
    - Every V23-VALIDATION keyword resolves to ≥1 test: `for kw in telemetry floor rescore byte_identical evict reindex drift pin cli; do .venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "$kw" --collect-only -q | grep -q "test" || echo "MISSING:$kw"; done` prints nothing
    - Module collects without ImportError: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py --collect-only -q` exits 0
    - Suite runs RED (failures/errors expected, NOT all-pass, NOT all-skip): running the module yields ≥1 failing test and 0 unexpected passes among feature tests
    - At most ONE xfail marker, and it names V21 global-store as the reason (grep: `grep -c "xfail" tests/memory/test_retrieval_ranking.py` <= 1)
    - No bare `pytest.skip()` used to dodge RED (grep: `grep -c "pytest.skip(" tests/memory/test_retrieval_ranking.py` == 0)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py --collect-only -q 2>&1 | tail -3 && for kw in telemetry floor rescore byte_identical evict reindex drift pin cli; do .venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "$kw" --collect-only -q 2>/dev/null | grep -q "test" || echo "MISSING:$kw"; done</automated>
  </verify>
  <done>All 8 VRNK requirements have named RED tests in tests/memory/test_retrieval_ranking.py; module collects; tests fail RED (feature code absent); every VALIDATION -k keyword matches a test.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none new) | Test-only plan; creates no runtime surface, no external input crosses any boundary |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V23-01-01 | Tampering | test scaffold false-greens (skip/xfail hides RED) | mitigate | Acceptance gates forbid `pytest.skip()` and cap xfail at 1 with mandated V21 reason; collection + per-keyword presence asserted |
| T-V23-01-SC | Tampering | npm/pip/cargo installs | mitigate | No installs in this plan; all deps pre-existing (RESEARCH Package Legitimacy Audit — zero new packages) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/memory/ --collect-only -q` exits 0
- `tests/memory/test_retrieval_ranking.py` runs RED (feature code not yet present)
- Every VRNK-01..08 keyword maps to ≥1 test
</verification>

<success_criteria>
RED scaffold exists and is collectable; all 8 requirements represented; fixture bridge in place; no false-green skips.
</success_criteria>

<output>
Create `.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-01-SUMMARY.md` when done.
</output>
