---
phase: V21
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/harness/test_memory_global.py
  - tests/harness/conftest.py
autonomous: true
requirements: [VGMEM-01, VGMEM-02, VGMEM-03, VGMEM-04, VGMEM-05, VGMEM-06, VGMEM-07, VGMEM-08]
cross_phase_note: >
  V21 EXECUTES ONLY AFTER V19 SHIPS (hard dependency, RESEARCH Q1 RESOLVED).
  V19-04 owns recall_cmd in cli.py; V21-04 EXTENDS it. This Wave-0 plan creates
  RED test stubs only and has no V19 dependency itself, but the suite's recall
  test (test_recall_fusion_rrf) targets the as-built V19 recall_cmd seam.
must_haves:
  truths:
    - "tests/harness/test_memory_global.py exists and imports the real planned API (MemoryStore root_override, make_global_store, _global_memory_root, get_global_memory_enabled)"
    - "Every VGMEM requirement has at least one test stub that fails for the right reason (target API absent), never xfail(strict=False)"
    - "conftest.py has tmp_voss_global fixture (VOSS_HOME monkeypatch + layout mirror) reusable by all V21 plans"
  artifacts:
    - path: "tests/harness/test_memory_global.py"
      provides: "RED test stubs for all VGMEM-* requirements"
      contains: "from voss.harness.memory_store import"
    - path: "tests/harness/conftest.py"
      provides: "tmp_voss_global fixture"
      contains: "def tmp_voss_global"
  key_links:
    - from: "test_memory_global.py"
      to: "voss.harness.memory_store.make_global_store"
      via: "module-level import (RED until V21-02 lands)"
      pattern: "make_global_store"
    - from: "tmp_voss_global fixture"
      to: "VOSS_HOME env"
      via: "monkeypatch.setenv"
      pattern: "VOSS_HOME"
---

<objective>
Wave-0 RED scaffold (V-track precedent V19-01): create the test file and fixtures
that pin the V21 contract BEFORE any production code exists. Every VGMEM-* requirement
gets a failing-for-the-right-reason stub whose imports/signatures match the planned API
exactly (so later plans implement against a fixed target, not a moving one).

Purpose: lock the API surface and give every downstream task an `<automated>` verify that
exists from the first commit (Nyquist compliance; project anti-shallow rule).
Output: `tests/harness/test_memory_global.py` (all VGMEM stubs) + `conftest.py` amendment
(`tmp_voss_global` fixture).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md
@.planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md
@.planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md

<interfaces>
<!-- The planned API these stubs MUST import/call (RED until V21-02/03/04 land). -->
voss/harness/memory_store.py (V21-02 adds):
  MemoryStore(cwd, *, cap_bytes=..., root_override: Path | None = None)  # root_override is the V21 addition
  MemoryStore.recall(query, top_k=..., source=None) -> list[Hit]        # existing
  MemoryStore._rrf_merge(rankings, *, top_k, k=60) -> list[Hit]         # existing @staticmethod
  MemoryStore.forget(pattern, *, confirm=False) -> int                  # existing
  MemoryStore.vacuum() -> int                                          # existing
  _global_memory_root() -> Path | None                                 # module-level, V21-02
  make_global_store() -> MemoryStore | None                            # module-level, V21-02
  _repo_id(cwd: Path) -> str                                           # module-level, V21-02

voss/harness/config.py (V21-02 adds):
  get_global_memory_enabled() -> bool                                  # reads [memory] global from config.toml

CLI verbs (V21-03/04 add), invoked via subprocess `python -m voss.cli memory ...`:
  voss memory promote <locator> [--list] [--cwd P]
  voss memory forget <locator> [--global] [--yes] [--cwd P]
  voss memory vacuum [--global] [--cwd P]
  voss recall <query>           # V19-04 owns; V21-04 adds [global] corpus
</interfaces>

<!-- Analog test files to mirror exactly: tests/harness/test_memory_vacuum.py, test_memory_store.py -->
<!-- isolated_state fixture is autouse (conftest.py) — every test gets an XDG sandbox; do NOT request it. -->
</context>

<tasks>

<task type="auto">
  <name>Task 1: conftest.py — tmp_voss_global fixture</name>
  <read_first>
    - tests/harness/conftest.py (read tmp_voss_repo fixture ~lines 92-104 and the autouse isolated_state fixture ~lines 28-31 — mirror their shape; do NOT duplicate isolated_state)
    - .planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md (conftest section: exact tmp_voss_global body to copy, lines 574-589)
    - .planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md (Pattern 2 _global_memory_root: VOSS_HOME → $VOSS_HOME/memory)
  </read_first>
  <files>tests/harness/conftest.py</files>
  <action>Add a `tmp_voss_global` pytest fixture (params: `tmp_path: Path, monkeypatch: pytest.MonkeyPatch`). Body: set `global_home = tmp_path / "global_home" / "voss"`; `monkeypatch.setenv("VOSS_HOME", str(global_home))` so `_global_memory_root()` resolves to `global_home / "memory"`; create `mem = global_home / "memory"` and mkdir each subdir in `("turns", "ledgers", "decisions", "conventions", "notes", "chroma", ".locks")` with `parents=True, exist_ok=True`; `return mem`. Do NOT add an `isolated_state` — it is already autouse. Keep the existing `tmp_voss_repo` fixture untouched (V21 promote tests pair `tmp_voss_repo` source + `tmp_voss_global` target).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/conftest.py --collect-only -q 2>&1 | tail -3; .venv/bin/python -c "import ast,sys; src=open('tests/harness/conftest.py').read(); assert 'def tmp_voss_global' in src, 'fixture missing'; assert 'VOSS_HOME' in src; print('tmp_voss_global ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/conftest.py` defines `def tmp_voss_global` decorated `@pytest.fixture`
    - fixture body calls `monkeypatch.setenv("VOSS_HOME", ...)` and returns the `.../memory` path
    - fixture creates all 7 layout subdirs (turns, ledgers, decisions, conventions, notes, chroma, .locks)
    - no second `isolated_state` definition added (grep -c "def isolated_state" == 1)
    - existing `tmp_voss_repo` fixture unchanged (source review)
  </acceptance_criteria>
  <done>tmp_voss_global fixture exists, monkeypatches VOSS_HOME, mirrors project layout; conftest still collects.</done>
</task>

<task type="auto">
  <name>Task 2: test_memory_global.py — RED stubs for all VGMEM-* requirements</name>
  <read_first>
    - tests/harness/test_memory_vacuum.py (lines 1-36: header imports, standard test body shape, reclaimed-bytes assertion style)
    - tests/harness/test_memory_store.py (lines 58-70: chroma_disabled_env usage + subprocess CLI invocation pattern)
    - .planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md (the Decision→Test map: exact test function names per requirement — use these names verbatim)
    - .planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md (test section: test_root_override, test_voss_home_env, test_promote_rejects_turn_ledger bodies to copy, lines 547-603)
    - .planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md (Phase Requirements → Test Map for behavior each stub asserts)
  </read_first>
  <files>tests/harness/test_memory_global.py</files>
  <action>Create the file with header `"""V21 global memory tests (VGMEM-* requirements)."""` then `from __future__ import annotations`, imports of `os`, `subprocess`, `sys`, `Path`, `pytest`, and `from voss.harness.memory_store import MemoryStore, make_global_store, _global_memory_root, _repo_id` plus `from voss.harness.config import get_global_memory_enabled`. Define one test function per VGMEM behavior using EXACTLY these names from VALIDATION.md: `test_root_override` (VGMEM-01: `MemoryStore(cwd, root_override=P).root == P` and `.cwd == cwd`), `test_voss_home_env` (VGMEM-01: `VOSS_HOME` → `_global_memory_root() == .../memory`), `test_global_layout_mirror` (VGMEM-01: global store bind() creates same source dirs as project), `test_agent_cannot_write_global` (VGMEM-02: inspect `attach_memory_tools` — global_store is never passed to a write path; assert `memory_remember` writes only to project store), `test_promote_copies_with_provenance` (VGMEM-03: promote copies file + chroma add carries `promoted_from`), `test_promote_dedup_on_repromote` (VGMEM-03: re-promote same locator updates, count stays 1), `test_promote_rejects_turn_ledger` (VGMEM-03: subprocess `python -m voss.cli memory promote turn:s1:000` returns 1, stderr contains "cannot be promoted"), `test_promote_list` (VGMEM-03: `--list` prints note/decision/convention locators only), `test_forget_global_tombstones_global` (VGMEM-04: forget --global tombstones global root, project untouched), `test_forget_project_default` (VGMEM-04: no flag → project scope), `test_vacuum_global` (VGMEM-05: vacuum --global reclaims bytes from global root), `test_concurrent_promote_lock` (VGMEM-05: portalocker blocks 2nd concurrent promoter — subprocess integration), `test_recall_fusion_rrf` (VGMEM-06: fused hits contain both project and global entries), `test_global_label_in_recall` (VGMEM-06: global hits labeled `[global]` in agent memory_recall output), `test_global_off_switch_no_init` (VGMEM-07: with `[memory] global = false`, `get_global_memory_enabled()` is False AND `make_global_store()` returns None — no chroma open), `test_voss_recall_global_corpus` (VGMEM-08: `voss recall` output includes `[global]`-labeled hits when global store has entries). Each stub: assert against the REAL planned API per the interfaces block — these MUST fail now because the API/behavior does not exist yet. Do NOT use `pytest.xfail` or `xfail(strict=False)`; a plain failing assertion (or ImportError surfacing) is the correct RED. Use `tmp_voss_repo` for project source and `tmp_voss_global` for global target where a global store is needed; use `chroma_disabled_env` where chroma is not under test (per analog).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_memory_global.py --collect-only -q 2>&1 | tail -20; .venv/bin/python -c "src=open('tests/harness/test_memory_global.py').read(); names=['test_root_override','test_voss_home_env','test_global_layout_mirror','test_agent_cannot_write_global','test_promote_copies_with_provenance','test_promote_dedup_on_repromote','test_promote_rejects_turn_ledger','test_promote_list','test_forget_global_tombstones_global','test_forget_project_default','test_vacuum_global','test_concurrent_promote_lock','test_recall_fusion_rrf','test_global_label_in_recall','test_global_off_switch_no_init','test_voss_recall_global_corpus']; missing=[n for n in names if ('def '+n) not in src]; assert not missing, f'missing stubs: {missing}'; assert 'xfail' not in src, 'xfail forbidden in Wave-0 scaffold'; print('all 16 stubs present, no xfail')"</automated>
  </verify>
  <acceptance_criteria>
    - all 16 named test functions present (grep each `def test_...` name)
    - module imports `make_global_store, _global_memory_root, _repo_id` from `voss.harness.memory_store` and `get_global_memory_enabled` from `voss.harness.config`
    - NO occurrence of `xfail` in the file (strict project rule: stubs target real API and fail honestly)
    - collection succeeds (pytest --collect-only exits 0); the suite as a whole FAILS when run (RED — target API absent), proving stubs are not false-green
    - subprocess CLI tests invoke `python -m voss.cli memory promote ...` (real CLI entrypoint, not a mock)
  </acceptance_criteria>
  <done>16 RED stubs covering every VGMEM-* requirement, importing the real planned API, no xfail; collection green, execution red.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test process → VOSS_HOME tmp dir | fixture writes a controlled tmp global root; no real ~/.voss touched |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V21-01-01 | Tampering | tmp_voss_global writing outside tmp | mitigate | fixture roots everything under pytest `tmp_path`; VOSS_HOME monkeypatched to tmp — production ~/.voss never touched by tests |
| T-V21-01-02 | Information Disclosure | test asserting on secret-shaped strings | accept | tests assert on Hit fields (source/locator/score/excerpt) only; no secrets in fixtures |
| T-V21-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: zero new deps; all four pre-existing on PyPI) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py --collect-only -q` — collection succeeds (0 collection errors)
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q` — FAILS RED (target API absent) — this is the correct Wave-0 state
- Coherence guard: `.venv/bin/python -m pytest tests/harness/ -q -k "vacuum or store" 2>&1 | tail -3` — existing memory tests unaffected by conftest amendment
</verification>

<success_criteria>
- 16 RED stubs, one+ per VGMEM-* requirement, importing the real planned API
- `tmp_voss_global` fixture present and VOSS_HOME-isolated
- No xfail anywhere; collection green, execution red
</success_criteria>

<output>
Create `.planning/phases/V21-global-cross-project-memory/V21-01-SUMMARY.md` when done
</output>
