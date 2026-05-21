---
phase: F2-hybrid-semantic-search
plan: 03
type: execute
wave: 3
depends_on: [F2-02]
files_modified:
  - pyproject.toml
  - uv.lock
  - tests/harness/test_recall_eval.py
autonomous: true
requirements: [FSRCH-03, FSRCH-04]

must_haves:
  truths:
    - "rank-bm25 is a base project dependency, not only a search extra"
    - "Chroma and sentence-transformers remain optional search dependencies"
    - "The lockfile matches pyproject dependency placement"
    - "Targeted recall regression commands pass after dependency and wording updates"
  artifacts:
    - path: "pyproject.toml"
      provides: "Base dependency declaration for the BM25 lexical retriever"
      contains: ["rank-bm25>=0.2.2"]
    - path: "uv.lock"
      provides: "Resolved dependency graph that installs rank-bm25 with base voss"
      contains: ["rank-bm25"]
    - path: "tests/harness/test_recall_eval.py"
      provides: "Recall eval wording aligned with BM25 fallback semantics"
      contains: ["BM25"]
  key_links:
    - from: "pyproject.toml [project].dependencies"
      to: "voss.harness.memory_store"
      via: "from rank_bm25 import BM25Okapi"
      pattern: "rank-bm25>=0.2.2"
---

<objective>
Close out dependency placement and verification for hybrid semantic search so the implementation works from a normal base install and the targeted recall tests document BM25 semantics.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/F2-hybrid-semantic-search/F2-CONTEXT.md
@.planning/phases/F2-hybrid-semantic-search/F2-RESEARCH.md
@.planning/phases/F2-hybrid-semantic-search/F2-PATTERNS.md
@.planning/phases/F2-hybrid-semantic-search/F2-VALIDATION.md
@.planning/phases/F2-hybrid-semantic-search/F2-01-PLAN.md
@.planning/phases/F2-hybrid-semantic-search/F2-02-PLAN.md
</context>

<threat_model>
| Threat | Severity | Mitigation |
|---|---|---|
| Base install fails at import time because `rank_bm25` is still optional | high | Move `rank-bm25>=0.2.2` into `[project].dependencies` and verify import |
| Search extra accidentally becomes required because Chroma dependencies move to base | medium | Only move `rank-bm25`; leave `chromadb` and `sentence-transformers` under `search` and `dev` |
| Lockfile drifts from `pyproject.toml` | medium | Refresh `uv.lock` with the project lock command rather than hand-editing it |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Move rank-bm25 to base dependencies</name>
  <files>
    pyproject.toml
  </files>
  <read_first>
    pyproject.toml
    .planning/phases/F2-hybrid-semantic-search/F2-CONTEXT.md
    .planning/phases/F2-hybrid-semantic-search/F2-RESEARCH.md
  </read_first>
  <action>
    Add `rank-bm25>=0.2.2` to `[project].dependencies`. Remove the duplicate `rank-bm25>=0.2.2` entries from the `search` and `dev` optional dependency lists because base installs now provide BM25. Do not move `chromadb` or `sentence-transformers`; those stay optional due to their large transitive dependency footprint.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "import tomllib; data=tomllib.load(open('pyproject.toml','rb')); deps=data['project']['dependencies']; optional=data['project']['optional-dependencies']; assert 'rank-bm25>=0.2.2' in deps; assert 'rank-bm25>=0.2.2' not in optional['search']; assert 'rank-bm25>=0.2.2' not in optional['dev']"</automated>
  </verify>
  <acceptance_criteria>
    - `[project].dependencies` contains `rank-bm25>=0.2.2`
    - `search` optional dependencies do not contain `rank-bm25>=0.2.2`
    - `dev` optional dependencies do not contain `rank-bm25>=0.2.2`
    - `search` optional dependencies still contain `chromadb>=0.5.0`
    - `search` optional dependencies still contain `sentence-transformers>=2.7.0`
  </acceptance_criteria>
  <done>BM25 is installable without the heavyweight search extra.</done>
</task>

<task type="auto">
  <name>Task 2: Refresh dependency lock state</name>
  <files>
    uv.lock
  </files>
  <read_first>
    pyproject.toml
    uv.lock
  </read_first>
  <action>
    Refresh the lockfile using the repository's package manager command. Prefer `uv lock` when `uv` is available. Do not hand-edit `uv.lock`. If the lock command is unavailable in the environment, leave `uv.lock` unchanged and record the blocker in the plan execution summary rather than fabricating lock output.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && uv lock --check</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "from rank_bm25 import BM25Okapi; print(BM25Okapi.__name__)"</automated>
  </verify>
  <acceptance_criteria>
    - `uv lock` or equivalent project lock command completes successfully
    - `uv lock --check` completes successfully when available
    - `python -c "from rank_bm25 import BM25Okapi"` succeeds in the project environment
  </acceptance_criteria>
  <done>Lock state agrees with base dependency placement and BM25 imports successfully.</done>
</task>

<task type="auto">
  <name>Task 3: Run final targeted recall verification</name>
  <files>
    tests/harness/test_recall_eval.py
  </files>
  <read_first>
    tests/harness/test_memory_store.py
    tests/harness/test_chroma_unavailable.py
    tests/harness/test_recall_eval.py
    tests/harness/test_memory_runtime_reuse.py
    tests/harness/test_slash_memory.py
    tests/harness/test_slash_recall.py
    .planning/phases/F2-hybrid-semantic-search/F2-VALIDATION.md
  </read_first>
  <action>
    Update remaining recall eval comments or docstrings that describe the old keyword fallback so they refer to BM25 or hybrid recall. Then run the quick and full targeted verification commands from `F2-VALIDATION.md`. Do not lower recall thresholds to make the suite pass; if a threshold fails, inspect ranking behavior from Plans 01 and 02.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py tests/harness/test_memory_runtime_reuse.py tests/harness/test_slash_memory.py tests/harness/test_slash_recall.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `test_recall_eval.py` does not describe the fallback path as naive keyword search
    - Quick F2 validation command passes
    - Full targeted F2 validation command passes
    - No recall eval threshold is lowered as part of this phase
  </acceptance_criteria>
  <done>Dependency closeout and targeted recall regressions are verified for F2.</done>
</task>

</tasks>

<verification>
Run:
- `cd /Users/benjaminmarks/Projects/Voss && python -c "import tomllib; data=tomllib.load(open('pyproject.toml','rb')); deps=data['project']['dependencies']; optional=data['project']['optional-dependencies']; assert 'rank-bm25>=0.2.2' in deps; assert 'rank-bm25>=0.2.2' not in optional['search']; assert 'rank-bm25>=0.2.2' not in optional['dev']"`
- `cd /Users/benjaminmarks/Projects/Voss && uv lock --check`
- `cd /Users/benjaminmarks/Projects/Voss && python -c "from rank_bm25 import BM25Okapi; print(BM25Okapi.__name__)"`
- `cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py tests/harness/test_recall_eval.py tests/harness/test_memory_runtime_reuse.py tests/harness/test_slash_memory.py tests/harness/test_slash_recall.py -q`
</verification>

<success_criteria>
- Base installs include BM25 without installing Chroma or sentence-transformers.
- Lockfile validation passes or the unavailable lock tool is recorded as an execution blocker.
- F2 quick and full targeted validation commands pass.
- Planning and tests consistently describe the fallback path as BM25, not naive keyword scan.
</success_criteria>
