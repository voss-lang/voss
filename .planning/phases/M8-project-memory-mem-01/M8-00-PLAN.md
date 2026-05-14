---
phase: M8
plan: 00
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - voss/harness/cli.py
  - voss/harness/voss_md.py
  - voss/harness/memory_store.py
  - voss/harness/conventions.py
  - voss/harness/memory_cli.py
  - tests/harness/conftest.py
  - tests/harness/test_voss_md_injection.py
  - tests/harness/test_voss_md_migration.py
  - tests/harness/test_voss_md_fence.py
  - tests/harness/test_memory_store.py
  - tests/harness/test_recall_eval.py
  - tests/harness/test_conventions.py
  - tests/harness/test_slash_recall.py
  - tests/harness/test_slash_forget.py
  - tests/harness/test_slash_memory.py
  - tests/harness/test_slash_save_note.py
  - tests/harness/test_memory_eviction.py
  - tests/harness/test_memory_vacuum.py
  - tests/harness/test_memory_runtime_reuse.py
  - tests/harness/test_repl_slash.py
autonomous: true
requirements: [MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, MEM-06, MEM-07]
tags: [memory, scaffold]
must_haves:
  truths:
    - "All M8 test files exist as importable stubs that fail with NotImplementedError or pytest.skip"
    - "Module skeletons voss_md.py, memory_store.py, conventions.py, memory_cli.py exist with public API signatures defined but no behavior"
    - "Existing /save slash command renamed to /save-session at cli.py:473; downstream tests pinning the old name updated"
    - "portalocker>=2.8 added to core dependencies in pyproject.toml"
    - "BLOCKING pitfalls 1 (/save collision) and 3 (Windows fcntl) resolved before any behavioral plan starts"
  artifacts:
    - path: "voss/harness/voss_md.py"
      provides: "Module skeleton with parse/read_and_inject/ensure_migrated signatures"
    - path: "voss/harness/memory_store.py"
      provides: "Module skeleton with MemoryStore class signatures (bind/recall/forget/write_turn/write_ledger/write_note/vacuum)"
    - path: "voss/harness/conventions.py"
      provides: "Module skeleton with ConventionCandidate pydantic model + run_on_clean_exit/has_signal stubs"
    - path: "voss/harness/memory_cli.py"
      provides: "Click group skeleton memory_group with vacuum/adopt/size command stubs"
    - path: "tests/harness/conftest.py"
      provides: "Fixtures tmp_voss_repo, fake_session_corpus, chroma_disabled_env, pre_m8_session_json, pre_m8_architecture_md"
    - path: "pyproject.toml"
      contains: "portalocker>=2.8"
  key_links:
    - from: "voss/harness/cli.py:473"
      to: "_save_session handler"
      via: "renamed slash registration"
      pattern: "SlashCommand\\(\"/save-session\""
    - from: "tests/harness/test_*.py"
      to: "pytest collection"
      via: "import voss.harness.voss_md / memory_store / conventions / memory_cli"
      pattern: "from voss.harness import (voss_md|memory_store|conventions|memory_cli)"
---

<objective>
Wave 0 scaffold for M8. Land all new module skeletons, all test file stubs, the portalocker dependency, and the `/save` collision rename so subsequent waves can attach behavior without dependency-resolution churn.

Purpose: Resolve the two BLOCKING pitfalls from RESEARCH.md (Pitfall 1 `/save` collision, Pitfall 3 cross-platform locking) and seed every test file referenced by RESEARCH §Validation Architecture so subsequent plans have a place to drop assertions.
Output: 4 new module skeletons, 13 new test files (12 stubs + extended conftest + test_repl_slash extension), portalocker dep, /save renamed to /save-session.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M8-project-memory-mem-01/M8-SPEC.md
@.planning/phases/M8-project-memory-mem-01/M8-CONTEXT.md
@.planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md
@.planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md
@.planning/phases/M8-project-memory-mem-01/M8-VALIDATION.md
@voss/harness/cli.py
@voss/harness/slash.py
@pyproject.toml

<interfaces>
<!-- Existing slash registry pattern: cli.py:464-483 is a flat tuple loop of SlashCommand entries.
     Existing /save handler signature at cli.py:411-417 takes (ctx: ReplContext, args: list[str], _line: str) -> None
     and renames record + saves; this is the snapshot-save handler that must be renamed _save_session. -->

From voss/harness/slash.py:
SlashCommand is a frozen dataclass with fields: name (str), help (str), handler (Callable[[Any, list[str], str], None]), aliases (tuple[str, ...]), mutating (bool), hidden (bool).

From voss_runtime/memory/__init__.py:
Exports Turn, EpisodicMemory (from .episodic), SemanticMemory (from .semantic).

From voss_runtime/memory/semantic.py:
SemanticMemory constructor takes keyword-only persist_dir (str) and collection_name (str, default "memory"). Methods: add(text, *, metadata=None, id=None) -> None; retrieve(query, *, top_k=5) -> list[dict]. Raises ModuleNotFoundError from __post_init__ if chromadb is not installed.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rename existing /save to /save-session and add portalocker dep</name>
  <files>voss/harness/cli.py, pyproject.toml, tests/harness/test_repl_slash.py</files>
  <read_first>
    - voss/harness/cli.py (lines 411–484 for the _save handler + slash registration block)
    - tests/harness/test_repl_slash.py (existing slash registry tests; verify which assert against "/save")
    - pyproject.toml (lines 10–40 for dependencies + [search] extra layout)
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §Pitfall 1 + §Pitfall 3
  </read_first>
  <action>
    Per RESEARCH Pitfall 1 + Pitfall 3 + A1 + A7:
    (a) In voss/harness/cli.py: rename the function `_save` (currently at cli.py:411–~426, the session-snapshot handler that mutates ctx.record.name) to `_save_session`. Update the SlashCommand registration at cli.py:473 from name `/save` (help "persist session snapshot", handler `_save`, mutating=True) to name `/save-session` (handler `_save_session`, mutating=True, same help). Do NOT add the new `/save` memory-note command in this task — that lands in M8-06.
    (b) In pyproject.toml: add `portalocker>=2.8` to the `dependencies` list at line 10 (NOT the [search] extra). Place it alphabetically after the existing pydantic entry. portalocker is pure-Python, ~80KB, cross-platform — resolves Pitfall 3 without a Windows-specific code branch.
    (c) In tests/harness/test_repl_slash.py: grep for any assertion on the literal `/save` name and update to `/save-session`. If a test asserts the full list of registered slash command names, substitute `/save` -> `/save-session` in that list. Do NOT add tests for the new memory `/save` (those live in tests/harness/test_slash_save_note.py created in Task 3 of this same plan).
    Constraint: do NOT introduce any reference to memory_store, voss_md, or the new memory `/save` handler in this task — they don't exist yet.
  </action>
  <verify>
    <automated>pytest tests/harness/test_repl_slash.py -x -q && python -c "from voss.harness.cli import _save_session" && python -c "import portalocker; print(portalocker.__version__)"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "/save-session" voss/harness/cli.py` returns at least one match in the slash registration block.
    - `grep -nE 'SlashCommand\("/save"' voss/harness/cli.py` returns ZERO matches (the bare `/save` slot is reserved for memory-note in M8-06).
    - `grep -v '^#' pyproject.toml | grep -c "portalocker>=2.8"` returns >= 1 (comment-stripped grep per planner hygiene rule).
    - `pip install -e .` succeeds in a fresh venv; `python -c "import portalocker"` succeeds.
    - `pytest tests/harness/test_repl_slash.py -x` is green (no stale `/save` assertions remain).
  </acceptance_criteria>
  <done>
    Existing `/save` handler renamed to `/save-session` everywhere; portalocker added to core deps; pre-existing slash registry tests pass; the bare `/save` slot is free for M8-06 to register the new memory-note handler.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create module skeletons for voss_md, memory_store, conventions, memory_cli</name>
  <files>voss/harness/voss_md.py, voss/harness/memory_store.py, voss/harness/conventions.py, voss/harness/memory_cli.py</files>
  <read_first>
    - .planning/phases/M8-project-memory-mem-01/M8-PATTERNS.md (full — defines analog + signatures for each new module)
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §"Recommended Project Structure" + §Pattern 1, 2, 3
    - voss/harness/cognition.py lines 1–50 (regex pattern + dataclass conventions)
    - voss/harness/recorder.py lines 1–170 (per-source FS mirror pattern + slug usage)
    - voss_runtime/memory/semantic.py (full — for SemanticMemory contract)
    - voss/harness/cli.py lines 1064–1085 (Click group pattern for memory_cli)
  </read_first>
  <action>
    Create four NEW module files. Each file exports the public symbols required by downstream waves so they can import without behavior. All function bodies raise NotImplementedError("M8-NN") where NN is the plan owning behavior implementation. No real logic except where noted concretely.

    (a) voss/harness/voss_md.py — top-level module. Owned by M8-01 (loader/migration) and M8-05 (cognition rewire helpers).
      Exports (signatures only, bodies raise NotImplementedError):
      - Module constants FENCE_BEGIN, FENCE_HASH, FENCE_END as re.compile patterns from PATTERNS.md "Regex constants" — define concretely now so M8-01 can use them.
      - @dataclass(frozen=True) class Block with fields kind (str), id (str | None), body (str), recorded_hash (str | None).
      - class HashMismatch(Exception) with __init__(fence_id, *, recorded, actual, on_disk) storing all three on self.
      - def parse(text: str) -> list[Block] — raises NotImplementedError("M8-01").
      - def read_and_inject(cwd: Path) -> str | None — raises NotImplementedError("M8-01"). Docstring: "Return verbatim VOSS.md bytes for D-08 system-context injection; None if file absent (Req 1 silent degradation)."
      - def ensure_migrated(cwd: Path) -> bool — raises NotImplementedError("M8-01"). Docstring: "Idempotent migration of .voss/architecture.md into VOSS.md id=architecture fence; archive byte-identical per Req 2(a) sha256 gate."
      - def read_fence_body(path: Path, *, fence_id: str) -> str | None — raises NotImplementedError("M8-01"). Docstring: "Return fence body text; raises HashMismatch if recorded != computed sha256."
      - def write_fence_body(path: Path, *, fence_id: str, body: str) -> None — raises NotImplementedError("M8-01"). Docstring: "Write body into id=<fence_id>; recompute hash; raises HashMismatch on baseline drift."
      - def machine_fence_path_or_marker(cwd: Path, *, fence_id: str) -> Path — raises NotImplementedError("M8-01"). Docstring: "Return the VOSS.md path used by fence writers (consumed by analyze.py via M8-05)."

    (b) voss/harness/memory_store.py — orchestrator over voss_runtime.memory + .voss/memory/. Owned by M8-02 (MEM-03 + MEM-07).
      Imports MUST include `from voss_runtime.memory import EpisodicMemory, SemanticMemory, Turn`. No subclassing of these types (Req 7).
      Exports:
      - @dataclass class Hit with fields source (str), locator (str), score (float), excerpt (str), session_id (str | None), ts (str | None).
      - Module constant SOURCE_QUOTAS = {"turns": 0.60, "ledgers": 0.20, "decisions": 0.10, "conventions": 0.10} per D-14.
      - Module constant DEFAULT_CAP_BYTES = 100 * 1024 * 1024.
      - def make_id(source: str, locator: str, seq: int | None = None) -> str — raises NotImplementedError("M8-02"). Docstring: "D-04 composite ID format <source>:<locator>:<seq>."
      - class MemoryStore: constructor __init__(self, cwd: Path, *, cap_bytes: int = DEFAULT_CAP_BYTES) stores cwd + cap_bytes ONLY (Pitfall 4: NO chroma instantiation here — lazy init); set self.root = cwd / ".voss" / "memory", self._chroma = None, self._size_cache: dict[str, int] = {}, self._session_id: str | None = None.
        Methods (all raise NotImplementedError("M8-02") with appropriate docstrings): bind(self, *, session_id: str) -> "MemoryStore"; recall(self, query: str, *, top_k: int = 5, source: str | None = None) -> list[Hit]; forget(self, pattern: str, *, confirm: bool = False) -> int; write_turn(self, *, role: str, content: str, session_id: str, turn_idx: int) -> None; write_ledger(self, run, *, session_id: str) -> None; write_note(self, text: str, *, session_id: str) -> Path; write_convention(self, candidate, *, session_id: str) -> Path; vacuum(self) -> int; summary(self, *, source: str | None = None) -> str.

    (c) voss/harness/conventions.py — extraction service. Owned by M8-03 (MEM-04).
      Imports: `from pydantic import BaseModel, Field, ValidationError`, `import re`, `import asyncio`.
      Exports:
      - class ConventionCandidate(BaseModel) with fields statement (str, min_length=1, max_length=500), confidence (float, ge=0.0, le=1.0), evidence_quote (str, min_length=1), evidence_turn_idx (int, ge=0). This IS behavior — define concretely (pydantic schema, no NotImplementedError).
      - Module constant _SIGNAL_RE = re.compile pattern for the D-09 signal regex (cover "no use", "always", "never", "prefer", "let's", "don't" — IGNORECASE, word-bounded). Define concretely.
      - Module constant DEFAULT_EXTRACTION_TIMEOUT_SECONDS = 8.0 per D-12.
      - def has_signal(turns) -> bool — raises NotImplementedError("M8-03"). Docstring: "D-09 pre-filter; True if any user turn matches _SIGNAL_RE OR repeat-edit detection fires on run.changed."
      - async def extract_conventions(history, provider, model: str, *, timeout: float = DEFAULT_EXTRACTION_TIMEOUT_SECONDS) -> list[ConventionCandidate] — raises NotImplementedError("M8-03"). Docstring: "D-10 LLM call wrapped in asyncio.wait_for(timeout); on TimeoutError returns []."
      - def review_candidates(candidates, *, interactive: bool = True, selection: str | None = None) -> list[int] — raises NotImplementedError("M8-03"). Docstring: "D-11 numbered list UX; returns selected 0-based indices."
      - def run_on_clean_exit(ctx, *, history, record, memory_store) -> int — raises NotImplementedError("M8-03"). Docstring: "End-of-session hook; returns count of conventions persisted. Wraps in try/except; never raises out of REPL exit."

    (d) voss/harness/memory_cli.py — Click subcommand group. Owned by M8-04 (MEM-06).
      Imports: `import click`, `from pathlib import Path`.
      Exports:
      - memory_group: click.Group decorated with @click.group("memory"), docstring "Manage Voss project memory store." — STRUCTURAL, define concretely.
      - memory_vacuum_cmd: @memory_group.command("vacuum") with --cwd option (default ".", type click.Path(file_okay=False)) — body raises NotImplementedError("M8-04").
      - memory_adopt_cmd: @memory_group.command("adopt") with --cwd option AND --id (required) option for fence_id — body raises NotImplementedError("M8-04"). (D-07 hash-mismatch resolution surface.)
      - memory_size_cmd: @memory_group.command("size") with --cwd option — body raises NotImplementedError("M8-04").

    Common file-header for all four modules: `from __future__ import annotations` as the first non-empty line.
  </action>
  <verify>
    <automated>python -c "from voss.harness import voss_md, memory_store, conventions, memory_cli" && python -c "from voss.harness.voss_md import Block, HashMismatch, parse, read_and_inject, ensure_migrated, read_fence_body, write_fence_body, machine_fence_path_or_marker, FENCE_BEGIN, FENCE_HASH, FENCE_END" && python -c "from voss.harness.memory_store import MemoryStore, Hit, make_id, SOURCE_QUOTAS, DEFAULT_CAP_BYTES" && python -c "from voss.harness.conventions import ConventionCandidate, has_signal, extract_conventions, review_candidates, run_on_clean_exit, _SIGNAL_RE, DEFAULT_EXTRACTION_TIMEOUT_SECONDS" && python -c "from voss.harness.memory_cli import memory_group, memory_vacuum_cmd, memory_adopt_cmd, memory_size_cmd" && python -c "from pathlib import Path; from voss.harness.memory_store import MemoryStore; MemoryStore(Path('.'))" && python -c "from voss.harness.conventions import ConventionCandidate; ConventionCandidate(statement='x', confidence=0.5, evidence_quote='y', evidence_turn_idx=0)"</automated>
  </verify>
  <acceptance_criteria>
    - All imports in verify succeed without ImportError.
    - MemoryStore(Path('.')) construction succeeds without instantiating chromadb (Pitfall 4 lazy invariant).
    - ConventionCandidate(...) construction succeeds (pydantic model concretely defined).
    - `grep -v '^#' voss/harness/voss_md.py voss/harness/conventions.py voss/harness/memory_cli.py | grep -cE "^class [A-Za-z_]+Memory"` returns 0 (Req 7 grep-gate posture).
    - `grep -v '^#' voss/harness/memory_store.py | grep -cE "^class MemoryStore"` returns 1 (orchestrator exists; not a Memory subclass — "MemoryStore" ends differently from `*Memory`).
    - `python -c "from voss.harness.voss_md import parse; parse('test')"` raises NotImplementedError (skeleton invariant).
  </acceptance_criteria>
  <done>
    Four new module files exist with full public-API surface. All imports succeed. Pydantic ConventionCandidate is fully defined. Regex constants in voss_md.py are concretely defined. All behavior-bearing methods raise NotImplementedError with the owning-plan ID. Lazy chroma init pre-staged per Pitfall 4.
  </done>
</task>

<task type="auto">
  <name>Task 3: Create test file stubs + extend conftest with shared fixtures</name>
  <files>tests/harness/conftest.py, tests/harness/test_voss_md_injection.py, tests/harness/test_voss_md_migration.py, tests/harness/test_voss_md_fence.py, tests/harness/test_memory_store.py, tests/harness/test_recall_eval.py, tests/harness/test_conventions.py, tests/harness/test_slash_recall.py, tests/harness/test_slash_forget.py, tests/harness/test_slash_memory.py, tests/harness/test_slash_save_note.py, tests/harness/test_memory_eviction.py, tests/harness/test_memory_vacuum.py, tests/harness/test_memory_runtime_reuse.py</files>
  <read_first>
    - .planning/phases/M8-project-memory-mem-01/M8-RESEARCH.md §"Validation Architecture" + §"Wave 0 Gaps" (lines ~617–680)
    - .planning/phases/M8-project-memory-mem-01/M8-VALIDATION.md §"Wave 0 Requirements"
    - tests/harness/conftest.py (existing — extend, do not replace)
    - tests/harness/test_session.py lines 1–80 (existing fixture style for pre-M8 session JSON reference)
    - voss/harness/session.py lines 110–200 (SessionRecord shape used by pre_m8_session_json fixture)
  </read_first>
  <action>
    Create test stubs and extend conftest. Each behavioral test function body MUST be `pass` under a module-level `pytestmark = pytest.mark.skip(reason="M8-NN — pending behavior implementation")` where NN names the owning plan. Each file must collect cleanly (no ImportError). The point: land the file list referenced by RESEARCH §Validation Architecture so subsequent waves drop assertions into named places.

    (a) Extend tests/harness/conftest.py — APPEND fixtures (do not overwrite existing):
      - tmp_voss_repo(tmp_path) -> Path: creates tmp_path/.voss/, tmp_path/.voss/memory/, and subdirs turns/ledgers/decisions/conventions/notes/chroma/.locks under .voss/memory/. Returns tmp_path. Used by Reqs 3/4/5/6/7.
      - pre_m8_architecture_md(tmp_voss_repo) -> Path: writes a realistic .voss/architecture.md with FRONTMATTER_RE-matching frontmatter (git_head, analyzed_at, file_count, analyzer_version fields per cognition.py:38 schema), body "# Architecture\n\nThis is fixture content.\n". Returns the path. Used by test_voss_md_migration.
      - pre_m8_session_json(tmp_voss_repo) -> Path: writes a .voss/sessions/<uuid>.json matching the M2 SessionRecord schema (id, cwd, name, runs: []) with NO memory_* fields. Returns path. Used for Pitfall 6 backward-compat tests.
      - fake_session_corpus(tmp_voss_repo) -> dict: SHAPE-ONLY placeholder for Wave 0 — returns `{"q": "id"}` and emits a pytest.warns or simply a comment "M8-02 fills this with real seeded content." M8-02 fills body in.
      - chroma_disabled_env(monkeypatch) -> None: monkeypatches `sys.modules["chromadb"] = None` to force ImportError on subsequent imports; reloads voss_runtime.memory.semantic if already imported. Used by Req 3 + Pitfall 4 fallback tests.

    (b) For each of the 13 test files below, create with this skeleton:
        from __future__ import annotations
        import pytest
        pytestmark = pytest.mark.skip(reason="M8-NN — pending behavior implementation")
      Then define the listed test function names below; each body is `pass`. The module-level skip covers all tests in that file.

      Files (owner plan in parens) + required test function names:
      - test_voss_md_injection.py (M8-05 wires; behavior M8-01): test_voss_md_loaded_in_system_context, test_missing_file_degrades_silently.
      - test_voss_md_migration.py (M8-05; M8-01 helpers): test_archive_sha256_matches_pre_migration, test_voss_md_contains_pre_migration_content, test_re_analyze_preserves_human_sections.
      - test_voss_md_fence.py (M8-01): test_parse_human_blocks, test_parse_machine_blocks, test_hash_mismatch_raises, test_write_fence_body_round_trip.
      - test_memory_store.py (M8-02): test_recall_hits_tagged_with_source, test_no_chroma_no_import_error, test_lazy_chroma_init_no_eager_import.
      - test_recall_eval.py (M8-02): test_chroma_top3_hit_rate_80pct, test_keyword_fallback_top3_hit_rate_60pct (parametrized via fake_session_corpus).
      - test_conventions.py (M8-03): test_scripted_signal_session_surfaces_candidate, test_decline_writes_nothing, test_accept_writes_one_file_with_evidence, test_no_signal_skips_llm_entirely, test_extraction_timeout_returns_empty.
      - test_slash_recall.py (M8-06): test_recall_command_registered, test_recall_returns_top_n_with_source_filter.
      - test_slash_forget.py (M8-06): test_forget_tombstones_matching_ids, test_forget_requires_yes_noninteractive.
      - test_slash_memory.py (M8-06): test_memory_summary_renders_counts_per_source.
      - test_slash_save_note.py (M8-06): test_save_note_writes_to_memory_notes_dir, test_save_note_does_not_rename_session (regression for Pitfall 1 collision).
      - test_memory_eviction.py (M8-04 vacuum; M8-02 inline evict): test_inline_evict_when_source_over_quota, test_post_write_size_under_cap, test_oldest_evicted_first_within_source.
      - test_memory_vacuum.py (M8-04): test_vacuum_reclaims_tombstoned_bytes, test_vacuum_deletes_tombstoned_files.
      - test_memory_runtime_reuse.py (M8-02): test_no_harness_memory_class_definitions_outside_runtime, test_semantic_memory_init_called_on_recall.

      EXCEPTION: test_memory_runtime_reuse.py::test_no_harness_memory_class_definitions_outside_runtime ships with REAL behavior (NOT skipped). Implementation: pathlib.Path walk over voss/harness/**/*.py, regex match against `^class\s+[A-Za-z_]+Memory\b` (only top-level class declarations whose class name ENDS in "Memory" — exclude "MemoryStore" since it ends in "Store", not "Memory"), filter out comments and string literals, assert count == 0. This protects Req 7's grep gate from day one. Do NOT apply the module-level pytestmark.skip to this file — instead apply skip to the OTHER function (test_semantic_memory_init_called_on_recall) using @pytest.mark.skip on that specific function.

    (c) Update tests/harness/test_repl_slash.py (EXISTING file, do not recreate): append `def test_memory_commands_not_yet_registered(): pass` decorated with @pytest.mark.skip(reason="M8-06 — will assert /recall, /forget, /memory, /save are registered"). This pre-stages the future contract in the surface map without breaking green.

    Critical constraint: Do NOT add behavioral assertions beyond the one grep-gate test. The point of Wave 0 is collection + the static check, not green tests. Subsequent waves remove the module-level skip and fill in bodies.
  </action>
  <verify>
    <automated>pytest tests/harness/ --collect-only -q 2>&1 | grep -cE "test_(voss_md|memory_store|recall_eval|conventions|slash_recall|slash_forget|slash_memory|slash_save_note|memory_eviction|memory_vacuum|memory_runtime_reuse)" | awk '$1 >= 13 { exit 0 } { exit 1 }' && pytest tests/harness/test_memory_runtime_reuse.py::test_no_harness_memory_class_definitions_outside_runtime -x -q && pytest tests/harness/ --collect-only -q > /dev/null</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/ --collect-only` exits 0 (all 13 new test files collect cleanly, no ImportError).
    - At least 13 test function ids matching the M8 file-name prefixes are discovered.
    - `pytest tests/harness/test_memory_runtime_reuse.py::test_no_harness_memory_class_definitions_outside_runtime -x` is GREEN (the static grep gate passes against the Wave 0 skeleton state — MemoryStore class name ends in "Store" not "Memory").
    - All other 12 M8 test files report as SKIPPED (module-level skip in effect).
    - test_repl_slash.py still passes; new `test_memory_commands_not_yet_registered` is skipped.
    - tests/harness/conftest.py has the 5 new fixtures importable: `pytest --fixtures tests/harness/ | grep -E "tmp_voss_repo|pre_m8_architecture_md|pre_m8_session_json|fake_session_corpus|chroma_disabled_env"` returns 5 matches.
  </acceptance_criteria>
  <done>
    13 new test files exist as collectable stubs (12 fully skipped, 1 grep-gate test runs green). Conftest extended with 5 shared fixtures. Existing test_repl_slash.py extended with the future-contract placeholder. Wave 0 grep-gate locks in Req 7 invariant from day one.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| developer-edited pyproject.toml -> pip install | new dep (portalocker) crosses the build boundary; trusted source PyPI |
| user-typed slash command -> renamed handler | renamed `/save` -> `/save-session`; existing handler logic unchanged; no new untrusted input surface |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M8-00-01 | Tampering | portalocker dep supply chain | accept | pinned ">=2.8" pulls latest stable; pyproject pin matches existing dep posture (no lockfile in repo); risk equivalent to any existing core dep (pydantic, click) |
| T-M8-00-02 | Denial of Service | broken rename of /save handler | mitigate | Task 1 acceptance asserts pytest tests/harness/test_repl_slash.py is green AND `grep ZERO matches` on bare /save registration; renames are atomic in one edit |
| T-M8-00-03 | Information Disclosure | new module skeletons leak internal types | accept | NotImplementedError stubs expose only the public API surface that downstream waves implement; no secrets, no env reads |
| T-M8-00-04 | Tampering | stale assertions in test_repl_slash.py | mitigate | Task 1 sub-step (c) explicitly searches and updates all /save literal references; verify command runs the file as a regression check |
</threat_model>

<verification>
- `pytest tests/harness/test_repl_slash.py -x` (Task 1 — green after rename)
- `python -c "from voss.harness import voss_md, memory_store, conventions, memory_cli"` (Task 2 — imports succeed)
- `pytest tests/harness/ --collect-only` (Task 3 — all stubs collect cleanly)
- `pytest tests/harness/test_memory_runtime_reuse.py -x` (Task 3 — grep-gate test green)
- `python -c "import portalocker"` (Task 1 — new dep installed)
</verification>

<success_criteria>
- All 4 new module files (voss_md.py, memory_store.py, conventions.py, memory_cli.py) exist and are importable from voss.harness.
- 13 new test files exist; 12 are SKIPPED at module level; 1 (test_memory_runtime_reuse.py) has a green grep-gate test pinning Req 7.
- conftest.py has 5 new shared fixtures available to the whole tests/harness/ suite.
- Existing `/save` slash command is renamed to `/save-session`; pre-existing slash-registry tests still pass.
- portalocker>=2.8 listed in pyproject.toml core dependencies; pip install succeeds; `import portalocker` works.
- Pre-existing tests/harness/ tests remain green; no regressions.
- The bare `/save` name is unclaimed (no SlashCommand registration), reserved for M8-06.
- MemoryStore(Path('.')) constructor succeeds without instantiating chromadb (Pitfall 4 lazy invariant).
</success_criteria>

<output>
After completion, create `.planning/phases/M8-project-memory-mem-01/M8-00-SUMMARY.md` summarizing:
- Files created (4 modules + 13 tests + conftest extension)
- Pitfalls resolved (1, 3)
- Symbols exposed for downstream waves (full public API of voss_md, memory_store, conventions, memory_cli)
- Fixture catalog added to conftest.py
- Any deviations from the plan (none expected)
</output>
