---
phase: V21
plan: 02
type: execute
wave: 1
depends_on: [V21-01]
files_modified:
  - voss/harness/memory_store.py
  - voss/harness/config.py
autonomous: true
requirements: [VGMEM-01, VGMEM-07]
cross_phase_note: >
  V21 EXECUTES ONLY AFTER V19 SHIPS (hard dependency, RESEARCH Q1 RESOLVED).
  This plan is the foundation every later V21 plan imports (root_override factory,
  global-root resolver, config off-switch). It does not touch V19 code.
must_haves:
  truths:
    - "MemoryStore(cwd, root_override=P) sets self.root=P; all existing zero-kwarg callers unaffected"
    - "VOSS_HOME env overrides ~/.voss base; _global_memory_root() returns None when HOME unavailable (no crash)"
    - "make_global_store() returns None when [memory] global = false OR HOME absent — no chroma open in that case"
    - "_repo_id(cwd) is deterministic: basename + 8-char sha256 of resolved abs path"
    - "[memory] global = false in config.toml disables global participation everywhere via get_global_memory_enabled()"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "root_override param + _global_memory_root + make_global_store + _repo_id"
      contains: "root_override"
    - path: "voss/harness/config.py"
      provides: "_parse_memory_section + get_global_memory_enabled"
      contains: "get_global_memory_enabled"
  key_links:
    - from: "make_global_store"
      to: "get_global_memory_enabled"
      via: "early-return None when disabled (skip init entirely)"
      pattern: "get_global_memory_enabled"
    - from: "make_global_store"
      to: "MemoryStore(home, root_override=root)"
      via: "constructor with root_override"
      pattern: "root_override"
---

<objective>
Build the foundation for the global store: a second `MemoryStore` instance rooted at the
global path via an additive `root_override` constructor param (D-04/D-09), the
`_global_memory_root()` / `make_global_store()` / `_repo_id()` helpers, and the
`[memory] global = false` config off-switch (D-07). No new store type, no new schema —
the same class serves both roots.

Purpose: every other V21 plan (promote/forget/vacuum CLI in V21-03, recall fusion in V21-04)
imports these primitives. Off-switch must skip global init entirely, not just filter hits.
Output: `memory_store.py` gains 3 module-level helpers + 1 kwarg; `config.py` gains a
`[memory]` section parser + `get_global_memory_enabled()`.
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

<interfaces>
voss/harness/memory_store.py (existing, verified):
  class MemoryStore:
    def __init__(self, cwd: Path, *, cap_bytes: int = DEFAULT_CAP_BYTES) -> None   # L72; self.root = cwd/.voss/memory at L75
  def make_id(source, locator, seq=None) -> str   # L56 module-level
  imports already present: os (L11); hashlib NOT imported (add it); Path (L17)

voss/harness/config.py (existing, verified):
  def config_path() -> Path                        # L20 → $XDG_CONFIG_HOME or ~/.config /voss/config.toml
  _KV   = re.compile(...)  # L44 quoted-string KV, MULTILINE
  _KV_BARE = re.compile(...)  # L50 bare-token KV, MULTILINE
  def _parse_model_tiers_section(text) -> dict     # L233 — section-block regex pattern to mirror
  def _parse_tools_section(text) -> dict           # L77 — bare-boolean pattern to mirror
  def get_allow_net() -> bool                      # L344 — read-config-return-bool shape to mirror
</interfaces>

<!-- RESEARCH Pitfall 1: _load_memory_config reads self.cwd/.voss/config.yml; for global store cwd=~ → returns {} (correct, no change). -->
<!-- RESEARCH Pitfall 6: Path.home() raises RuntimeError when $HOME unset → catch, return None. -->
<!-- config.toml (TOML, config_path) holds [memory] global; .voss/config.yml (YAML) holds quotas — NEVER mix parsers. -->
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: memory_store.py — root_override param + global-root/factory/repo-id helpers</name>
  <read_first>
    - voss/harness/memory_store.py (lines 6-24 imports; 56-79 make_id + __init__/self.root; 322-357 write_note chmod 0o600 pattern; 623-636 _locator_from_path)
    - tests/harness/test_memory_global.py (test_root_override, test_voss_home_env, test_global_layout_mirror — implement to make these GREEN)
    - .planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md (memory_store.py section: exact bodies for root_override, _global_memory_root, make_global_store, _repo_id — lines 41-195)
    - .planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md (Pattern 1, Pattern 2, Code Examples: Global Root Resolution / Global Store Factory)
  </read_first>
  <files>voss/harness/memory_store.py</files>
  <behavior>
    - test_root_override: MemoryStore(tmp, root_override=tmp/"custom"/"memory").root == that path; .cwd == tmp
    - test_voss_home_env: VOSS_HOME=tmp/"vh" → _global_memory_root() == tmp/"vh"/"memory" (resolved)
    - test_global_layout_mirror: make_global_store().bind(session_id="global") creates notes/decisions/conventions/turns/ledgers dirs under the global root
    - HOME-less: _global_memory_root() returns None (no RuntimeError) when VOSS_HOME unset and Path.home() raises
  </behavior>
  <action>Add `import hashlib` to the import block (os already imported). On `__init__` (L72), add a keyword-only param `root_override: Path | None = None` AFTER `cap_bytes`; change the `self.root` assignment (L75) to `self.root = root_override if root_override is not None else cwd / ".voss" / "memory"`. Touch nothing else in `__init__` (self.cwd stays = cwd; config lookup self-corrects to `{}` for the global instance per RESEARCH Pitfall 1 — note this in the param docstring). Add three module-level helpers near `make_id`: (1) `_global_memory_root() -> Path | None` — read `os.environ.get("VOSS_HOME")`; if set, return `Path(voss_home).resolve() / "memory"` (the `.resolve()` is the path-traversal mitigation, threat T-V21-02-01); else `try: return Path.home() / ".voss" / "memory"` `except RuntimeError: return None` (HOME-less CI, RESEARCH Pitfall 6). (2) `make_global_store() -> "MemoryStore | None"` — `from voss.harness.config import get_global_memory_enabled`; `if not get_global_memory_enabled(): return None` (off-switch skips init ENTIRELY — no chroma open, D-07); `root = _global_memory_root()`; `if root is None: return None`; `try: home = Path.home()` `except RuntimeError: return None`; `return MemoryStore(home, root_override=root)`. (3) `_repo_id(cwd: Path) -> str` — `h = hashlib.sha256(str(cwd.resolve()).encode()).hexdigest()[:8]; return f"{cwd.resolve().name}-{h}"` (deterministic, D-10). Do NOT modify _lock, write_note, forget, vacuum, _rrf_merge, recall — they already operate purely on self.root and serve the global root unchanged.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_memory_global.py::test_root_override tests/harness/test_memory_global.py::test_voss_home_env tests/harness/test_memory_global.py::test_global_layout_mirror -x -q 2>&1 | tail -10; .venv/bin/python -c "from voss.harness.memory_store import MemoryStore, _global_memory_root, make_global_store, _repo_id; from pathlib import Path; import os; os.environ['VOSS_HOME']='/tmp/vh_probe'; assert _global_memory_root()==Path('/tmp/vh_probe').resolve()/'memory'; a=_repo_id(Path('.')); b=_repo_id(Path('.')); assert a==b and '-' in a; print('helpers ok:', a)"</automated>
  </verify>
  <acceptance_criteria>
    - `MemoryStore.__init__` has keyword-only `root_override: Path | None = None`; `self.root` honors it (source review + test_root_override green)
    - `_global_memory_root()` returns `$VOSS_HOME/memory` (resolved) when set, `~/.voss/memory` else, `None` when Path.home() raises RuntimeError
    - `make_global_store()` returns None when `get_global_memory_enabled()` is False (no chroma open) and when root is None
    - `_repo_id(Path('.'))` is deterministic across calls and matches `<basename>-<8 hex>`
    - all existing zero-kwarg `MemoryStore(cwd)` callers still construct (grep -n "MemoryStore(" voss/harness/ shows no caller passes a positional past cwd)
    - test_root_override, test_voss_home_env, test_global_layout_mirror pass
  </acceptance_criteria>
  <done>root_override param + _global_memory_root + make_global_store + _repo_id landed; layout-mirror test green; no existing caller broken.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: config.py — [memory] section parser + get_global_memory_enabled off-switch</name>
  <read_first>
    - voss/harness/config.py (lines 20-21 config_path; 44-50 _KV/_KV_BARE; 77-91 _parse_tools_section bare-boolean shape; 233-239 _parse_model_tiers_section block-regex shape; 344-366 get_allow_net read-and-return-bool shape)
    - tests/harness/test_memory_global.py (test_global_off_switch_no_init — implement to make GREEN)
    - .planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md (config.py section: exact _parse_memory_section + get_global_memory_enabled bodies — lines 332-402)
    - .planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md (Pattern 5: config [memory] section parser; Pitfall: TOML vs YAML file confusion)
  </read_first>
  <files>voss/harness/config.py</files>
  <behavior>
    - test_global_off_switch_no_init: with config.toml containing `[memory]` + `global = false`, get_global_memory_enabled() is False AND make_global_store() returns None
    - default (no config / no [memory] section / no `global` key): get_global_memory_enabled() returns True
    - unparseable value (e.g. `global = maybe`): warns RuntimeWarning, defaults to True
  </behavior>
  <action>Add a module-level `_MEMORY_BLOCK = re.compile(r"^\[memory\][^\[]*", re.MULTILINE)` near the other block regexes. Add `_parse_memory_section(text: str) -> dict[str, str]`: search `_MEMORY_BLOCK`; if no match return `{}`; over the matched block, collect `_KV.findall(block)` into a dict, then iterate `_KV_BARE.findall(block)` with `out.setdefault(k, v)` (bare token must NOT overwrite a quoted match) — mirrors `_parse_tools_section` since `global = false` is a bare boolean. Add `get_global_memory_enabled() -> bool`: `p = config_path()`; `if not p.exists(): return True`; `try: text = p.read_text()` `except OSError: return True`; `section = _parse_memory_section(text)`; `raw = section.get("global")`; `if raw is None: return True`; normalize `raw.strip().lower()`; return False if `"false"`, True if `"true"`, else `warnings.warn(..., RuntimeWarning, stacklevel=2)` and return True. Reads `~/.config/voss/config.toml` via existing `config_path()` — NOT `.voss/config.yml` (which is YAML for quotas; never mix per RESEARCH Pitfall).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_memory_global.py::test_global_off_switch_no_init -x -q 2>&1 | tail -10; .venv/bin/python -c "from voss.harness.config import _parse_memory_section, get_global_memory_enabled; d=_parse_memory_section('[memory]\nglobal = false\n'); assert d.get('global')=='false', d; d2=_parse_memory_section('[other]\nx=1\n'); assert d2=={}, d2; print('memory section parser ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `_MEMORY_BLOCK` regex + `_parse_memory_section` + `get_global_memory_enabled` exist in config.py (source review)
    - `_parse_memory_section('[memory]\nglobal = false\n')` returns `{'global': 'false'}`; a non-memory block returns `{}`
    - `get_global_memory_enabled()` returns True by default (no config / no section / no key), False only when value normalizes to `false`
    - non-boolean value emits RuntimeWarning and defaults True
    - reads `config_path()` (config.toml), never `.voss/config.yml` (source review)
    - test_global_off_switch_no_init passes (now that make_global_store from Task 1 + this off-switch are both present)
  </acceptance_criteria>
  <done>[memory] section parser + get_global_memory_enabled off-switch landed; off-switch test green; TOML/YAML kept separate.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| environment (VOSS_HOME) → global root path | operator/CI-controlled env var crosses into filesystem path construction |
| config.toml → global enable/disable | on-disk config governs whether the global store opens at all |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V21-02-01 | Tampering | VOSS_HOME path traversal | mitigate | `_global_memory_root()` calls `Path(voss_home).resolve()` before appending `/memory` — normalizes `..` segments; downstream store writes (V21-03) chmod 0o600 (ASVS V5 input validation) |
| T-V21-02-02 | Denial of Service | HOME-less env crash | mitigate | `Path.home()` wrapped in try/except RuntimeError → returns None → global gracefully disabled, no crash (RESEARCH Pitfall 6) |
| T-V21-02-03 | Elevation of Privilege | global store init when operator disabled it | mitigate | `make_global_store()` early-returns None when `get_global_memory_enabled()` is False — no chroma open, no lock churn, no participation (D-07/D-08 by construction) |
| T-V21-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: zero new deps; portalocker/chromadb/rank-bm25/click all pre-existing on PyPI) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q -k "root_override or voss_home or layout_mirror or off_switch" 2>&1 | tail -8` — these 4 green
- Coherence guard: `.venv/bin/python -m pytest tests/harness/ tests/memory/ -q 2>&1 | tail -5` — no regression in existing memory/config suites (additive change)
- Coherence guard: `.venv/bin/python -c "from voss.harness.cli import do_cmd; print('cli import ok')"` — additive param did not break import graph
</verification>

<success_criteria>
- root_override param threads through; same class serves project + global root
- VOSS_HOME override + HOME-less graceful-disable both correct
- [memory] global = false skips global init entirely (no chroma open)
- _repo_id deterministic; existing callers unbroken
</success_criteria>

<output>
Create `.planning/phases/V21-global-cross-project-memory/V21-02-SUMMARY.md` when done
</output>
