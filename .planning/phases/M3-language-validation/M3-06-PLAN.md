---
phase: M3
plan: 06
type: execute
wave: 3
depends_on: [M3-01, M3-04, M3-05]
files_modified:
  - tests/examples/test_check_speed.py
  - README.md
  - docs/voss-vs-python.md
autonomous: true
requirements:
  - LANG-01
  - LANG-09
  - LANG-10
tags:
  - speed
  - framing
  - docs

must_haves:
  truths:
    - "tests/examples/test_check_speed.py adds a parametrized test_check_speed_under_ceiling(sample) that runs `voss check samples/<sample>.voss` twice (warmup + measured), asserts the measured wall-clock is below CHECK_CEILING_SECONDS, and asserts exit code 0."
    - "test_check_speed_under_ceiling parametrizes over [\"classify\", \"support\", \"research\"] and runs all three (after M3-01 + M3-04 land, the warm wall-clock per sample is comfortably under 2s)."
    - "README.md adds a 'What is .voss' H2 section between H1 and Install; the section uses the EXACT phrase 'AI workflow control' and explicitly states .voss is NOT a Python replacement. The exact negation phrasing chosen (to satisfy both D-14 'explicitly states' intent AND the M3-VALIDATION grep contract that forbids the substring 'Python replacement') is recorded verbatim in M3-06-SUMMARY.md so reviewers can audit intent preservation per D-14."
    - "README.md links to docs/voss-vs-python.md from BOTH the new 'What is .voss' section AND the existing Project Docs list (RESEARCH Q-5 two-link-to-one-doc recommendation)."
    - "README.md no longer contains the outdated 'Phase 1 status' blockquote (deleted or replaced)."
    - "docs/voss-vs-python.md exists at repo root; contains H1 + 3 H2 sample sections (classify/support/research) each pairing samples/*.voss with examples/raw_python/*.py via side-by-side fenced code blocks + a one-paragraph commentary explaining what .voss makes explicit."
    - "docs/voss-vs-python.md includes a LOC count table footer for the six paired files."
  artifacts:
    - path: "tests/examples/test_check_speed.py"
      provides: "parametrized wall-clock gate + retained M3-01 sentinel (D-03 + D-13)"
      contains: "test_check_speed_under_ceiling"
    - path: "README.md"
      provides: "What is .voss section + docs/voss-vs-python.md link + outdated banner removed (D-14); the exact negation phrase chosen (no literal substring 'Python replacement') MUST be quoted verbatim in M3-06-SUMMARY.md for D-14 intent-preservation audit"
      contains: "AI workflow control"
    - path: "docs/voss-vs-python.md"
      provides: "side-by-side .voss vs raw Python with LOC + commentary (D-15)"
      contains: "## Classify"
  key_links:
    - from: "tests/examples/test_check_speed.py::test_check_speed_under_ceiling"
      to: "tests.examples.helpers.run_voss + copy_example"
      via: "subprocess voss check + time.perf_counter measurement"
      pattern: "perf_counter"
    - from: "README.md"
      to: "docs/voss-vs-python.md"
      via: "two markdown links (inline What-is section + Project Docs list)"
      pattern: "docs/voss-vs-python.md"
    - from: "docs/voss-vs-python.md"
      to: "samples/*.voss + examples/raw_python/*.py"
      via: "fenced code block per sample"
      pattern: "samples/"
---

<objective>
Land the D-13 per-sample wall-clock speed gate (extending the test file M3-01 left for this plan) and the D-14 + D-15 framing surface: README "What is .voss" section + `docs/voss-vs-python.md` side-by-side document. This is the final M3 plan — after it lands, every CONTEXT decision D-01..D-15 has a code/doc artifact, every LANG-01..LANG-10 requirement has automated verification, and the phase verification step has a green target.

Purpose: The speed gate is the regression contract for D-03 / RESEARCH Pitfall 2 — any future code path that re-imports the encoder at check time fails this test loudly with a 60-second wait. The framing docs (LANG-01 + LANG-05) are the explicit "shorter, clearer than raw Python" deliverable (ROADMAP success criterion 5) and the user-facing surface that positions .voss correctly.

Output:
- `tests/examples/test_check_speed.py` — adds parametrized `test_check_speed_under_ceiling(sample)`. Keeps the M3-01 sentinel.
- `README.md` — top-of-file restructure: outdated banner removed, new "What is .voss" H2 section inserted between H1 and Install.
- `docs/voss-vs-python.md` — new file. H1 + framing paragraph + 3 H2 sample sections + LOC table.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M3-language-validation/M3-CONTEXT.md
@.planning/phases/M3-language-validation/M3-RESEARCH.md
@.planning/phases/M3-language-validation/M3-PATTERNS.md
@tests/examples/test_check_speed.py
@tests/examples/helpers.py
@samples/classify.voss
@samples/support.voss
@samples/research.voss
@examples/raw_python/classify.py
@examples/raw_python/support.py
@examples/raw_python/research.py
@README.md

<interfaces>
From tests/examples/test_check_speed.py (post-M3-01 — the file exists with the sentinel + CHECK_CEILING_SECONDS=2.0 constant; this plan extends it with the parametrized wall-clock gate):

```
"""D-03 + D-13 check-time invariants. ..."""
CHECK_CEILING_SECONDS = 2.0
REPO_ROOT = Path(__file__).resolve().parents[2]

def test_check_does_not_load_hf_encoder():
    ...
```

From tests/examples/helpers.py (post-M3-05 — SAMPLES_DIR repoint complete; run_voss + copy_example available):

```
SAMPLES_DIR = REPO_ROOT / "samples"
def copy_example(tmp_path: Path, name: str) -> Path: ...
def run_voss(args: list[str], *, cwd: Path, env=None, timeout=60.0) -> subprocess.CompletedProcess[str]: ...
```

From .planning/phases/M3-language-validation/M3-RESEARCH.md §"Pattern: tests/examples/test_check_speed.py (D-13, NEW)" — verbatim adaptation source for the parametrized gate.

From .planning/phases/M3-language-validation/M3-RESEARCH.md §"State of the Art" — README's outdated "Phase 1 status" banner is the line to delete.

M3-VALIDATION grep contracts for the framing surface:
- `grep -F "AI workflow control" README.md` MUST return at least one match
- `! grep -i "Python replacement" README.md` MUST be TRUE (i.e., the phrase "Python replacement" must NOT appear EXCEPT in a clearly-negated form like "not a Python replacement")
- `test -f docs/voss-vs-python.md` MUST be TRUE
- `grep -F "docs/voss-vs-python.md" README.md` MUST return at least one match
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add parametrized wall-clock speed gate to tests/examples/test_check_speed.py (D-13)</name>
  <files>tests/examples/test_check_speed.py</files>
  <read_first>
    - tests/examples/test_check_speed.py (post-M3-01 — confirm CHECK_CEILING_SECONDS constant + sentinel test already present; do NOT remove either)
    - tests/examples/helpers.py (post-M3-05 — confirm SAMPLES_DIR + run_voss + copy_example)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern: tests/examples/test_check_speed.py (D-13, NEW)" — the verbatim code template; §"Open Question Q-3" — warm-only recommendation; §"Pitfall 2" — speed gate IS the regression gate)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/examples/test_check_speed.py (NEW) — D-03 sentinel + D-13 wall-clock" — the parametrize-over-samples pattern)
    - .planning/phases/M3-language-validation/M3-CONTEXT.md (§D-13 — locked decision: hard wall-clock ceiling; 2s starting target, tune up if CI variance demands)
  </read_first>
  <behavior>
    - tests/examples/test_check_speed.py adds a new function test_check_speed_under_ceiling(tmp_path, sample) decorated with `@pytest.mark.parametrize("sample", ["classify", "support", "research"])`.
    - The test copies the named sample into tmp_path via copy_example, runs `voss check <sample>.voss` once as warmup (return ignored), then measures a second run with time.perf_counter().
    - Asserts the measured run exits 0 AND elapsed < CHECK_CEILING_SECONDS. Error message identifies the sample and the elapsed time and points at D-03 as the likely culprit.
    - The M3-01 sentinel test (test_check_does_not_load_hf_encoder) remains intact.
    - `pytest tests/examples/test_check_speed.py -v` reports 4 passed total (1 sentinel + 3 parametrized).
    - If a sample exceeds 2.0s on the developer machine, the developer raises CHECK_CEILING_SECONDS to a value that is still a meaningful gate (e.g., 3.5s) and notes the new ceiling + rationale in the M3-06 summary; the ceiling MUST remain a real assert, never log-only (D-13 locked).
  </behavior>
  <action>
    1. Open tests/examples/test_check_speed.py (created by M3-01). The current top of the file has CHECK_CEILING_SECONDS = 2.0 and the sentinel test.
    2. Add the following imports if not present: `import time`, `import pytest`. From tests.examples.helpers import `copy_example`, `run_voss`.
    3. After the sentinel test function, add:
       - decorator `@pytest.mark.parametrize("sample", ["classify", "support", "research"])`.
       - function `def test_check_speed_under_ceiling(tmp_path, sample):`.
       - Body steps in order:
         a. `copy_example(tmp_path, sample)` — copies samples/<sample>.voss into tmp_path.
         b. `run_voss(["check", f"{sample}.voss"], cwd=tmp_path)` — warmup; return ignored. Per RESEARCH Q-3 (warm-only recommended).
         c. `start = time.perf_counter()`.
         d. `result = run_voss(["check", f"{sample}.voss"], cwd=tmp_path)`.
         e. `elapsed = time.perf_counter() - start`.
         f. `assert result.returncode == 0, result.stderr` (failure surfaces stderr in the pytest report).
         g. `assert elapsed < CHECK_CEILING_SECONDS, f"voss check {sample}.voss took {elapsed:.2f}s (ceiling {CHECK_CEILING_SECONDS}s) — D-03 regression?"`.
    4. Test docstring (one-liner above the function): `"""D-13: voss check must complete under CHECK_CEILING_SECONDS for each sample."""`.
    5. Run `pytest tests/examples/test_check_speed.py -v`. If any of the three parametrized cases fails on elapsed time, INSPECT:
       a. If the failure is on support.voss only and elapsed is in the 5-10s range, M3-01's analyzer fix may not have landed correctly — re-run `time python3 -m voss.cli check samples/support.voss` outside pytest. If still slow, escalate to the M3-01 SUMMARY for fix instructions.
       b. If the failure is across all three at low elapsed (e.g., 2.2s on classify which used to be 1.4s), CI variance — bump CHECK_CEILING_SECONDS to 3.5s. Document the change in the M3-06 SUMMARY.
       c. Never silence the test (`pytest.mark.skip`, log-only) — D-13 is locked.
    6. Do NOT change CHECK_CEILING_SECONDS unless step 5b applies. Do NOT remove or modify the sentinel test. Do NOT add cold-start measurement (Q-3 recommends warm-only).
    7. Do NOT add a `voss check --speed-budget` CLI flag (CONTEXT deferred ideas).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/examples/test_check_speed.py -v --no-header 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "test_check_speed_under_ceiling" tests/examples/test_check_speed.py` returns at least 1.
    - `grep -c "@pytest.mark.parametrize" tests/examples/test_check_speed.py` returns 1.
    - `grep -c "test_check_does_not_load_hf_encoder" tests/examples/test_check_speed.py` returns 1 (sentinel preserved).
    - `grep -c "perf_counter" tests/examples/test_check_speed.py` returns at least 1.
    - `grep -c "D-03 regression" tests/examples/test_check_speed.py` returns 1 (the assertion error message).
    - `pytest tests/examples/test_check_speed.py -v` reports 4 passed (1 sentinel + 3 parametrized).
    - `pytest tests/examples/test_check_speed.py::test_check_speed_under_ceiling -v` reports 3 passed.
    - `time pytest tests/examples/test_check_speed.py -q 2>&1 | tail -5` total wall-clock under 30s (well within feedback latency target).
  </acceptance_criteria>
  <done>Per-sample wall-clock gate lands; sentinel preserved; D-13 regression contract is enforced.</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite README.md top section with "What is .voss" + remove outdated Phase 1 banner + link docs/voss-vs-python.md (D-14)</name>
  <files>README.md</files>
  <read_first>
    - README.md (full file 1-66 — current shape; identify the "Phase 1 status" blockquote at line 5 + the Quickstart code block + the Project Docs list at lines 60-65)
    - samples/classify.voss (post-M3-04 — for any in-README link reference)
    - .planning/phases/M3-language-validation/M3-CONTEXT.md (§D-14 — locked framing surface)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"State of the Art" — outdated banner identification; §"Open Question Q-5" — two-links-to-one-doc placement recommendation)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"README.md — D-14 + D-15 link" — adaptation notes incl. exact grep contracts from M3-VALIDATION)
  </read_first>
  <behavior>
    - README.md line 5 (the "Phase 1 status" blockquote) is removed or replaced by the new "What is .voss" section.
    - A new H2 section "## What is .voss" sits between the H1 "# Voss" + opening paragraph and the existing "## Install" section.
    - The section content describes .voss as the AI workflow control layer; lists the first-class primitives (probable values + confidence gates, ctx budgets, semantic routing via match similar, agents/spawn/gather, memory primitives, within/fallback, try/catch); EXPLICITLY states .voss is not intended as a Python replacement; links to `samples/` (existing dir) and `docs/voss-vs-python.md` (new file from Task 3).
    - The "Project Docs" list at the bottom of README.md adds a second entry pointing to docs/voss-vs-python.md (per RESEARCH Q-5 two-link-to-one-doc).
    - The Quickstart code block + Install + Tests sections are unchanged in this task.
    - Grep contracts hold: `grep -F "AI workflow control" README.md` finds ≥1; the substring "Python replacement" appears ONLY in clearly negated form (e.g., "not a Python replacement" or "not a general Python replacement"); `grep -F "docs/voss-vs-python.md" README.md` finds at least 2.
  </behavior>
  <action>
    1. Read the current README.md fully. Identify the line numbers of:
       - The H1 `# Voss` line.
       - The opening paragraph after the H1.
       - The "Phase 1 status:" blockquote (currently line 5 starting with `>`).
       - The "## Install" header.
       - The "## Project Docs" header at the bottom.
    2. DELETE the "Phase 1 status:" blockquote line (and its surrounding blank lines).
    3. AFTER the opening paragraph (which currently ends "...auditable and predictable instead of vibes-based.") and BEFORE the "## Install" section, INSERT a new H2 section. The H2 header is `## What is .voss`. Section body should contain: (a) an opening sentence describing .voss as an AI workflow control layer that compiles to readable Python AND explicitly stating it is not a general Python replacement (the exact phrase "AI workflow control" must appear at least once); (b) a bulleted list of the primitives — probable values + confidence gates with `probable<T>` and `@ p >= 0.80`; context budgets with `ctx(budget: N tokens)` and `within budget fallback`; semantic routing with `match similar`; agents with `spawn` and `gather`; memory primitives `memory.episodic` / `memory.semantic` / `memory.working`; recovery with `try/catch` and `use voss_runtime::tools::tool`; (c) a closing sentence linking to `samples/` (markdown link to `samples/`) and to `docs/voss-vs-python.md` (markdown link). Hard constraints (per the grep contracts in acceptance criteria): the literal substring "AI workflow control" appears at least once; the literal substring "docs/voss-vs-python.md" appears at least once in this section; and the section never contains the literal substring "Python replacement" (use phrasing like "complement to Python" or "not intended to replace Python" — see action step 8). Claude's discretion on exact prose otherwise.
    4. In the existing "## Project Docs" list at the bottom, ADD a new bullet (preserve list ordering — likely append at the end or place alphabetically): `- [docs/voss-vs-python.md](docs/voss-vs-python.md) — side-by-side .voss vs raw Python with LOC counts`.
    5. Confirm the Quickstart code block referencing `examples/raw_python/classify.py` etc. (current lines 17-21 list) is preserved — it doubles as a Quickstart navigation aid. The new "What is .voss" section can also reference these via the samples/ link.
    6. Do NOT remove the existing PRD.md or .planning/* references in Project Docs.
    7. After editing, the M3-VALIDATION row `framing-readme` greps MUST pass: `grep -F "AI workflow control" README.md` exits 0; `! grep -i "Python replacement" README.md` exits 0 (i.e., no UNNEGATED occurrence — verify by visually reading the file).
    8. Caveat: if `grep -i "Python replacement"` finds the phrase even in negated form ("not a Python replacement"), the M3-VALIDATION grep is too strict. Reframe the negation as "complement to Python, not a replacement" or similar wording that omits the literal "Python replacement" string. Confirm with a final grep after editing.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && grep -F "AI workflow control" README.md && grep -c "docs/voss-vs-python.md" README.md | grep -qE "^[2-9]" && ! grep -i "Python replacement" README.md && ! grep -F "Phase 1 status" README.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -F "AI workflow control" README.md` returns at least 1 match.
    - `grep -c "docs/voss-vs-python.md" README.md` returns at least 2 (inline link in What-is + Project Docs entry per Q-5).
    - `grep -i "Python replacement" README.md` returns 0 matches (per M3-VALIDATION row `framing-readme`; if negation requires using the phrase, reword to avoid it — see action step 8).
    - `grep -F "Phase 1 status" README.md` returns 0 matches.
    - `grep -c "^## What is .voss$" README.md` returns 1.
    - `grep -c "^## Install$" README.md` returns 1 (existing section preserved).
    - `grep -c "^## Project Docs$" README.md` returns 1.
    - `python -c "import re; s = open('README.md').read(); h1 = s.index('# Voss'); whatis = s.index('## What is .voss'); install = s.index('## Install'); assert h1 < whatis < install, f'section order broken: {h1} {whatis} {install}'"` exits 0.
  </acceptance_criteria>
  <done>README opens with current, accurate framing; the section ordering keeps onboarding flow (overview → install → tests); both links to docs/voss-vs-python.md present.</done>
</task>

<task type="auto">
  <name>Task 3: Create docs/voss-vs-python.md side-by-side comparison with LOC table (D-15)</name>
  <files>docs/voss-vs-python.md</files>
  <read_first>
    - samples/classify.voss (post-M3-04 — full file for fenced-block content)
    - samples/support.voss (post-M3-04 — full file)
    - samples/research.voss (post-M3-04 — full file)
    - examples/raw_python/classify.py (full file)
    - examples/raw_python/support.py (post-M3-04 — full file)
    - examples/raw_python/research.py (post-M3-04 — full file)
    - README.md (post-Task-2 — confirm the link target docs/voss-vs-python.md exists; this task creates that file)
    - .planning/phases/M3-language-validation/M3-CONTEXT.md (§D-15 — locked deliverable)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"docs/voss-vs-python.md (NEW) — D-15" — adaptation notes; "no analog" — greenfield prose, structure cribbed from README)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§Code Examples — confirms target sample shapes; §"State of the Art" — `docs/voss-vs-python.md` is the success-criterion-5 artifact)
  </read_first>
  <behavior>
    - docs/voss-vs-python.md exists at the repo-root-relative path `docs/voss-vs-python.md`.
    - The file opens with an H1 title (e.g., `# Voss vs raw Python`).
    - First paragraph frames the doc: ".voss compiles to readable Python. Below, the three canonical samples are paired with their hand-written Python equivalents..." (Claude's discretion on exact wording).
    - Three H2 sections: `## Classify`, `## Support`, `## Research`. Each section:
      (a) one-paragraph commentary on what .voss makes explicit (confidence gate / context budgets / try-catch fallback / memory.episodic / agent spawn semantics) that raw Python leaves implicit;
      (b) side-by-side fenced code blocks — `samples/<name>.voss` first (```voss), `examples/raw_python/<name>.py` second (```python).
    - A footer LOC counts table with one row per sample showing `samples/<name>.voss` LOC vs `examples/raw_python/<name>.py` LOC. Numbers computed via `wc -l` once at write time and embedded as a static markdown table (not re-computed dynamically per RESEARCH §"Pattern: docs/voss-vs-python.md").
    - File ends with a single trailing newline.
  </behavior>
  <action>
    1. Create the `docs/` directory at the repo root if it does not exist.
    2. Compute LOC counts: `wc -l samples/classify.voss samples/support.voss samples/research.voss examples/raw_python/classify.py examples/raw_python/support.py examples/raw_python/research.py` — capture the six numbers.
    3. Create docs/voss-vs-python.md with the following structure (Claude's discretion on exact prose; the SECTION HEADERS and CONTENT SHAPE are fixed):
       
       Top-of-file H1: `# Voss vs raw Python`
       
       Framing paragraph (1-2 sentences): explains what the doc is, links to README.md, mentions that voss compiles to readable Python and these pairs demonstrate brevity / explicit-not-implicit.
       
       H2 `## Classify` section:
       - One-paragraph commentary about probable<T> + confidence gates being explicit in .voss vs implicit-or-missing in raw Python.
       - Code block 1 labeled "`samples/classify.voss`": fenced `voss` block containing the FULL current content of samples/classify.voss (post-M3-04 — with header comment line 2).
       - Code block 2 labeled "`examples/raw_python/classify.py`": fenced `python` block containing the FULL current content of examples/raw_python/classify.py.
       
       H2 `## Support` section:
       - One-paragraph commentary about match similar (semantic routing) + memory.episodic being explicit in .voss; raw Python uses SemanticMatcher + manual EpisodicMemory wiring + ctx.add.
       - Code block 1 labeled "`samples/support.voss`": fenced `voss` block, full content.
       - Code block 2 labeled "`examples/raw_python/support.py`": fenced `python` block, full content.
       
       H2 `## Research` section:
       - One-paragraph commentary about agent/spawn/gather, within/fallback, and try/catch being first-class in .voss; raw Python uses VossAgent + asyncio.gather + manual try/except wrapping.
       - Code block 1 labeled "`samples/research.voss`": fenced `voss` block, full content.
       - Code block 2 labeled "`examples/raw_python/research.py`": fenced `python` block, full content.
       
       H2 `## LOC` (or `## Line counts`) footer section: a markdown table with header `| Sample | .voss | raw Python |` and three rows, one per sample. Use the wc -l numbers from step 2.
    4. Trailing newline single (no double).
    5. Do NOT generate the content dynamically; the file is a static document. If the samples change in M4+, this doc gets re-generated manually.
    6. Do NOT include the U+2014 em-dash in the document if it complicates downstream tooling — ASCII hyphens are fine here (the em-dash is only locked in the .voss sample header comments per M3-04 and the D-02 banner per M3-02).
    7. After saving, run `wc -l docs/voss-vs-python.md` — confirm the file is non-trivial (likely 80-150 LOC).
    8. Confirm the README link from Task 2 now resolves: `test -f docs/voss-vs-python.md` exits 0.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && test -f docs/voss-vs-python.md && grep -F "docs/voss-vs-python.md" README.md && grep -c "^## Classify" docs/voss-vs-python.md && grep -c "^## Support" docs/voss-vs-python.md && grep -c "^## Research" docs/voss-vs-python.md && grep -c '```voss' docs/voss-vs-python.md && grep -c '```python' docs/voss-vs-python.md && wc -l docs/voss-vs-python.md</automated>
  </verify>
  <acceptance_criteria>
    - `test -f docs/voss-vs-python.md` exits 0.
    - `grep -c "^# Voss vs raw Python" docs/voss-vs-python.md` returns 1.
    - `grep -c "^## Classify" docs/voss-vs-python.md` returns 1.
    - `grep -c "^## Support" docs/voss-vs-python.md` returns 1.
    - `grep -c "^## Research" docs/voss-vs-python.md` returns 1.
    - `grep -c '^```voss$' docs/voss-vs-python.md` returns 3 (one per sample).
    - `grep -c '^```python$' docs/voss-vs-python.md` returns 3 (one per raw_python file).
    - `grep -c "samples/classify.voss" docs/voss-vs-python.md` returns at least 1 (the code-block label).
    - `grep -c "examples/raw_python/classify.py" docs/voss-vs-python.md` returns at least 1.
    - `grep -E "^\\| .*\\| .*\\| .*\\|" docs/voss-vs-python.md | wc -l` returns at least 4 (table header + separator + 3 rows).
    - `wc -l docs/voss-vs-python.md | awk '{print $1}'` returns at least 60 (non-trivial document).
    - `grep -F "docs/voss-vs-python.md" README.md` returns at least 2 lines (both links from Task 2 still resolve).
  </acceptance_criteria>
  <done>Side-by-side comparison doc exists; LOC table populated from real wc -l counts; both README links resolve; LANG-01 + LANG-05 framing surface complete.</done>
</task>

</tasks>

<verification>
- `pytest tests/examples/test_check_speed.py -v --no-header 2>&1 | tail -10` reports 4 passed (1 sentinel + 3 parametrized).
- `VOSS_HERMETIC=1 pytest tests/examples/ tests/parser tests/analyzer tests/codegen tests/cli -q -m "not live" --no-header 2>&1 | tail -10` exits 0 (full M3 suite green).
- `grep -F "AI workflow control" README.md && test -f docs/voss-vs-python.md && grep -F "docs/voss-vs-python.md" README.md` all succeed (M3-VALIDATION rows framing-readme + framing-vs-python-doc).
- `! grep -i "Python replacement" README.md` exits 0 (negation absent or reworded).
- `time python3 -m voss.cli check samples/classify.voss; time python3 -m voss.cli check samples/support.voss; time python3 -m voss.cli check samples/research.voss` — each warm time below CHECK_CEILING_SECONDS.
</verification>

<success_criteria>
- D-13 regression contract enforced via per-sample wall-clock assert; D-03 reversion in any future plan fails this gate inside 60s of feedback.
- D-14: README framing surface delivered; outdated banner removed; "What is .voss" section between H1 and Install.
- D-15: docs/voss-vs-python.md ships; ROADMAP success criterion 5 ("Docs and sample framing describe .voss as AI workflow control, not a Python replacement") satisfied with a concrete reviewable artifact.
- LANG-01 + LANG-05 framing surfaces complete; LANG-09 speed gate green for all three samples.
- M3 is execution-complete after this plan; the phase-verify step has a green target across all 22 task rows in M3-VALIDATION.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| wall-clock timing → CI variance | Real-time measurement is sensitive to noisy CI runners; a 2s ceiling is the floor for catching D-03 regressions (~13s baseline) but not so tight it false-positives on a slow ARM runner. |
| documentation strings → grep contracts | M3-VALIDATION encodes exact-string greps; any rewording must preserve those exact phrases. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M3-23 | Denial of Service | Speed test false-positives on a slow CI runner → flakes; team disables the test → D-03 regression slips in undetected | mitigate | CHECK_CEILING_SECONDS is a constant in code, easily tunable per CONTEXT D-13. If a flake occurs, bump to 3.5s or 5.0s, never disable. Task 1 action step 5b documents the procedure. |
| T-M3-24 | Tampering | A future README edit accidentally restores the "Phase 1 status" framing or removes "AI workflow control" | mitigate | M3-VALIDATION row framing-readme greps remain in the verification table; a phase-verify rerun catches the regression. |
| T-M3-25 | Information Disclosure | docs/voss-vs-python.md leaks internal-only file paths (e.g., developer's $HOME) in code blocks | mitigate | All code-block content is read from samples/ and examples/raw_python/ which are tracked-in-repo paths with no developer-machine leakage. wc -l output is stripped to just integers in the table. |
| T-M3-26 | Repudiation | The "Python replacement" grep contract is satisfied by a negated mention ("not a Python replacement") that the M3-VALIDATION test treats as a violation | mitigate | Task 2 action step 8 explicitly reworks the negation if the literal substring leaks; final grep result is the contract. |
| T-M3-27 | Tampering | LOC counts in the table go stale as samples evolve | accept | M3-04 was the last sample-extension wave in this phase; if M4 alters the samples, doc regeneration is in M4 scope. The table footer can optionally include the regeneration command (`wc -l samples/*.voss examples/raw_python/*.py`) for future devs. |
</threat_model>

<output>
After completion, create `.planning/phases/M3-language-validation/M3-06-SUMMARY.md` documenting: (1) the final CHECK_CEILING_SECONDS value used (2.0 default, or higher with rationale), (2) the three measured warm wall-clock times for classify/support/research (paste-from-test-output), (3) the README.md diff summary (what was removed, what was added, the two link locations) INCLUDING the exact verbatim sentence chosen for the D-14 negation (the phrase that explicitly states .voss is not a Python replacement WITHOUT containing the substring "Python replacement" per the M3-VALIDATION grep contract) — this is the D-14 intent-preservation audit record, (4) the docs/voss-vs-python.md table (paste-from-file), (5) confirmation that all M3-VALIDATION rows are now green (paste the verification grep results), (6) the M3 phase-verification handoff: `/gsd-verify-work` target command and the success criterion grid (every LANG-01..10 has an automated test).
</output>
