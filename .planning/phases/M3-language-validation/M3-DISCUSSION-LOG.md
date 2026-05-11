# Phase M3: Language Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** M3-language-validation
**Areas discussed:** Hermetic run + check speed, LANG-07/08 sample coverage, Test surface scope, Framing surface

---

## Hermetic run + check speed

### Run provider strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-fallback to StubProvider | If RuntimeConfig.default_model resolves to no creds OR env VOSS_HERMETIC=1, runtime auto-registers __stub__. Zero-config CI. | ✓ |
| Explicit env var only | VOSS_PROVIDER=__stub__ required. No magic. CI sets it. Local-no-creds errors explicitly. | |
| Sample-header annotation | Samples opt-in with `# voss:provider=__stub__` directive. Per-sample control. | |

**User's choice:** Auto-fallback to StubProvider.
**Notes:** Mirrors M1 "diagnose-don't-fix" posture — silent stubbing avoided by mandatory stderr banner.

### Check speed strategy for SemanticMatcher

| Option | Description | Selected |
|--------|-------------|----------|
| Static-only check; defer encoder to run | voss check never instantiates SemanticMatcher. Encoder loads only at voss run. | ✓ |
| Stub encoder default in check | voss check uses deterministic fake encoder. Still exercises matcher path. | |
| Accept current behavior | Keep loading HF embeddings on check. Cache makes subsequent runs fast. | |

**User's choice:** Static-only check; defer encoder to run.
**Notes:** Splits "well-formed program" from "runnable program" — keeps check cheap enough to run on every edit.

### Stub fallback banner

| Option | Description | Selected |
|--------|-------------|----------|
| Stderr banner every run | Print `voss: no provider creds detected — using __stub__ (deterministic fake responses)` every invocation. | ✓ |
| Banner once per session/env | Track first invocation via tempfile/env. Quieter for CI logs. | |
| Silent when VOSS_HERMETIC=1, banner otherwise | Explicit CI opt-in suppresses banner; ambient fallback warns. | |

**User's choice:** Stderr banner every run.

### voss run success contract for LANG-10

| Option | Description | Selected |
|--------|-------------|----------|
| Exit 0 + non-empty stdout | Minimal CI-assertable contract. | ✓ |
| Exit 0 + parity vs examples/raw_python/ | Generated Python stdout matches hand-written raw Python under same StubProvider. Stronger correctness. | |
| Exit 0 + golden snapshot | Captured stdout snapshot per sample. CI diffs. | |

**User's choice:** Exit 0 + non-empty stdout.
**Notes:** Raw-python parity moves to per-test assertion in e2e suite (D-12), not the LANG-10 gate itself.

---

## LANG-07/08 sample coverage

### How to satisfy memory.* and try/catch + use

| Option | Description | Selected |
|--------|-------------|----------|
| Extend support.voss + research.voss | Add memory.episodic to support; try/catch + use to research. No new sample files. Keeps three canonical examples. | ✓ |
| Add 4th sample (assistant.voss) | Promote tests/parser/examples/assistant.voss to a 4th canonical sample. | |
| Test-only fixtures | Keep 3 samples minimal; cover LANG-02..08 via parser/analyzer/codegen test fixtures. | |

**User's choice:** Extend support.voss + research.voss.
**Notes:** Honors roadmap success criterion 1 ("three meaningful examples") verbatim.

### Where memory.* lands

| Option | Description | Selected |
|--------|-------------|----------|
| support.voss (memory.episodic prior tickets) | Episodic memory fits customer-support recall narrative. | ✓ |
| research.voss (memory.semantic / working) | Research agent benefits from cached findings + working scratchpad. | |
| Split: episodic in support, semantic in research | Both samples extended. More changes; richer demo. | |

**User's choice:** support.voss (memory.episodic prior tickets).

### Where try/catch + use lands

| Option | Description | Selected |
|--------|-------------|----------|
| research.voss — try/catch around webSearch + use voss.tools | Network is natural failure point. `use` imports tool module. | ✓ |
| support.voss — try/catch around refundFlow + use voss.memory | Business-logic failure path. | |
| Spread: try/catch in research, use in both | Maximum coverage; more sample churn. | |

**User's choice:** research.voss — try/catch around webSearch + use voss.tools.

### memory.working coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Test-fixture only | LANG-07 covered for memory.working by parser/analyzer/codegen snapshots only. | ✓ |
| Add to research.voss as scratch state | Working memory accumulates Synthesizer report fragments. | |
| All three in support.voss | Pile episodic + semantic + working into one sample. | |

**User's choice:** Test-fixture only.
**Notes:** memory.semantic also test-fixture-only by extension — keeps samples readable.

---

## Test surface scope

### Test plan size

| Option | Description | Selected |
|--------|-------------|----------|
| Legacy phase-06 plan, slimmed | helpers + 3 per-sample e2e + cli_matrix + check_speed. Drops test_helpers meta-suite and live path. ~5 files. | ✓ |
| Minimal CLI smoke | One parametrized test — check + run on each sample under VOSS_HERMETIC=1. ~1 file. | |
| Legacy plan in full | Everything legacy phase-06 prescribed including meta-tests, --live, package smoke. ~8 files. | |

**User's choice:** Legacy phase-06 plan, slimmed.

### Raw-python parity treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Keep + assert stdout matches | Generated python and hand-written raw_python share StubProvider; stdout must match. | ✓ |
| Keep as documentation, no parity assertion | raw_python/ stays as readability oracle for LANG-03; not tested. | |
| Retire raw_python/ | Replace with codegen snapshots under tests/codegen/snapshots/. | |

**User's choice:** Keep + assert stdout matches.
**Notes:** raw-python files do double duty as parity oracles AND LANG-03 readability references.

### Speed regression test

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — hard ceiling per sample | test_check_speed.py asserts each sample's voss check finishes under ~2s. Concrete LANG-09 quality gate. | ✓ |
| Yes — soft assertion, log only | Time runs, print to stderr, no assertion. | |
| No speed test | Skipping encoder load already handles the biggest cost; don't add CI complexity. | |

**User's choice:** Yes — hard ceiling per sample.
**Notes:** 2s is a starting target; tune during execution if CI variance demands a higher number but keep it a gate.

### Test directory path

| Option | Description | Selected |
|--------|-------------|----------|
| tests/examples/ | Matches legacy plan, mirrors samples/ directory. | ✓ |
| tests/language/ | Reflects M3 "Language Validation" framing; decouples from "examples" word. | |
| tests/m3/ | Phase-tagged for .planning/ traceability. | |

**User's choice:** tests/examples/.

---

## Framing surface

### Where framing copy lives

| Option | Description | Selected |
|--------|-------------|----------|
| README + sample headers | "What is .voss" README section + per-sample comment blocks naming primitives demonstrated. | ✓ |
| README only | Single source of truth; samples stay code-first. | |
| PROJECT.md + samples only, no README | Avoids touching public README until M5 distribution prep. | |

**User's choice:** README + sample headers.

### Brevity demo deliverable

| Option | Description | Selected |
|--------|-------------|----------|
| Side-by-side doc — docs/voss-vs-python.md | Each sample paired with raw_python equivalent. LOC + readability commentary. Links from README. | ✓ |
| README table only | Sample / .voss LOC / raw python LOC / what it adds. | |
| Skip explicit doc | raw_python/ and samples/ sit side-by-side; reader compares. | |

**User's choice:** Side-by-side doc — docs/voss-vs-python.md.
**Notes:** Concrete artifact for roadmap success criterion 5 ("language demo shows shorter, clearer workflow code").

---

## Claude's Discretion

- Exact phrasing of README "What is .voss" section and per-sample header comments.
- Exact wall-clock ceiling in test_check_speed.py (2s is starting target).
- Mechanism by which auto-StubProvider detection wires in (env-var probe vs. cred-resolver hook).
- Fake encoder + fake index implementation for support.voss semantic-routing tests.
- RuntimeConfig default for __stub__ model name + interaction with sample-supplied model annotations.
- Whether stub-fallback banner suppresses under a quiet flag.
- Exact try/catch syntax in research.voss — researcher must confirm parser surface first against voss/grammar.lark; if grammar lacks try/catch, implementation plan extends grammar/parser/analyzer/codegen before sample extension lands.

## Deferred Ideas

- A 4th canonical sample showcasing memory.* + try/catch + use end-to-end.
- memory.semantic and memory.working surfaced in runnable samples (test-fixture-only for M3).
- Live-provider e2e tests in CI (manual only per legacy phase-06 plan).
- pytest -m live marker / opt-in live path.
- tests/examples/test_helpers.py meta-tests on helpers themselves.
- voss check --speed-budget=Ns flag for tunable speed gate.
- VOSS_QUIET=1 suppressing stub-fallback banner.
- Authoring /analyze or any harness skill in .voss (M4).
- Embeddings / semantic index beyond M2's flat repo.idx.
- Renaming tests/examples/ to tests/language/ or phase-tagged paths.
- Retiring examples/raw_python/ in favor of generated-python snapshots.
- Broader codegen-snapshot test coverage beyond per-construct coverage fixtures.
- voss init <template> scaffolds covering AI workflow templates.
