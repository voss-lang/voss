---
phase: V2-principles-layer
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/principles.py
  - tests/harness/test_principles_config.py
autonomous: true
requirements: [VPRIN-01, VPRIN-03, VPRIN-05, VPRIN-06]
must_haves:
  truths:
    - "A valid .voss/principles.yml loads into a frozen PrinciplesConfig"
    - "Mutating a PrinciplesConfig raises (FrozenInstanceError)"
    - "A malformed principles.yml raises a clear, non-silent VossPrinciplesConfigError"
    - "With no project file, the six defaults are the active principles each labeled source=default"
    - "A project file adding key X yields six defaults + X(source=project); overriding `tests` replaces its string; disable:[scope] removes scope while non-disabled defaults remain"
  artifacts:
    - path: "voss/harness/principles.py"
      provides: "PrinciplesConfig (frozen) + load_principles loader + merge + six DEFAULT_PRINCIPLES + VossPrinciplesConfigError"
      contains: "class PrinciplesConfig"
      min_lines: 80
    - path: "tests/harness/test_principles_config.py"
      provides: "loader/merge/immutability/defaults tests"
      contains: "def test_"
  key_links:
    - from: "voss/harness/principles.py:load_principles"
      to: ".voss/principles.yml"
      via: "yaml.safe_load + .voss/ path"
      pattern: "yaml\\.safe_load"
    - from: "voss/harness/principles.py:merge"
      to: "DEFAULT_PRINCIPLES"
      via: "additive override + explicit disable"
      pattern: "DEFAULT_PRINCIPLES"
---

<objective>
Create the principles config substrate: a frozen `PrinciplesConfig`, the six shipped default principles, a `.voss/principles.yml` loader that reuses the existing pyyaml/pydantic stack (no new deps) and is loud on malformed input, and the additive-override + explicit-disable merge. This is the foundation every downstream plan (injection, `show`) consumes.

Purpose: Principles become a first-class immutable config object with stable order and opaque text, mirroring the `TeamConfig` frozen-config + `VossTeamConfigError` loud-error precedent.
Output: `voss/harness/principles.py` + `tests/harness/test_principles_config.py`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V2-principles-layer/V2-SPEC.md
@.planning/phases/V2-principles-layer/V2-CONTEXT.md

<interfaces>
<!-- Precedent to mirror — frozen config + loud error (voss/harness/team.py) -->
From voss/harness/team.py:
- `class VossTeamConfigError(Exception)` (L33) — clear, non-silent compile error precedent.
- `@dataclass(frozen=True, slots=True) class TeamConfig` (L211) — frozen/slots immutable value object precedent. Frozen dataclass mutation raises `dataclasses.FrozenInstanceError`.

From voss/harness/consensus.py (the `.voss/*.yml` load precedent to reuse — no new deps):
```python
import yaml
from pydantic import ValidationError
def load_constraints(cwd: Path) -> Optional[ConstraintsConfig]:
    path = cwd / ".voss" / "constraints.yml"
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return ConstraintsConfig.model_validate(raw)
    except (yaml.YAMLError, ValidationError):
        return None
```
NOTE divergence: `load_constraints` swallows errors to None. Principles must do the OPPOSITE on malformed input — RAISE `VossPrinciplesConfigError` (D-02, non-silent). Missing file is fine (→ defaults only); malformed YAML / non-string value is NOT (→ raise).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: PrinciplesConfig + six defaults + loader</name>
  <files>voss/harness/principles.py, tests/harness/test_principles_config.py</files>
  <read_first>
    - voss/harness/team.py (L33 VossTeamConfigError, L204-218 frozen/slots dataclasses) — frozen-config + loud-error precedent
    - voss/harness/consensus.py (L59-68 load_constraints) — `.voss/*.yml` yaml.safe_load reuse pattern
    - .planning/phases/V2-principles-layer/V2-SPEC.md (Requirements 1, 2, 4; Acceptance Criteria)
    - .planning/phases/V2-principles-layer/V2-CONTEXT.md (D-01, D-02; six default strings under "Six shipped defaults")
  </read_first>
  <behavior>
    - Test: `PrinciplesConfig` is `@dataclass(frozen=True, slots=True)`; mutating any field raises `dataclasses.FrozenInstanceError`.
    - Test: `DEFAULT_PRINCIPLES` contains exactly the six keys diff/evidence/tests/scope/review/reversibility with the EXACT strings from D-02 (assert each key→string equality).
    - Test: a valid `.voss/principles.yml` with `{foo: "bar"}` loads via `load_principles(cwd)` into a `PrinciplesConfig` whose ordered items include `("foo", "bar")`.
    - Test: a malformed file (invalid YAML, e.g. `": :"` or a top-level list, or a non-string value like `tests: 5`) raises `VossPrinciplesConfigError` (NOT silent, NOT None).
    - Test: a missing `.voss/principles.yml` does NOT raise — `load_principles` returns the project layer as empty (defaults applied by merge in Task 2).
  </behavior>
  <action>
    Create `voss/harness/principles.py`. Define `VossPrinciplesConfigError(Exception)` mirroring `VossTeamConfigError` (clear message, non-silent). Define `DEFAULT_PRINCIPLES` as an ordered constant (use a `tuple[tuple[str, str], ...]` or dict with insertion order) holding the SIX exact pairs from V2-CONTEXT.md D-02: diff="Make the smallest diff that solves the task.", evidence="No factual claim without evidence.", tests="Tests prove behavior, not coverage theater.", scope="Do not edit outside assigned scope.", review="Review intent and correctness before style.", reversibility="Prefer reversible changes unless the user approves risk." Define `PrinciplesConfig` as `@dataclass(frozen=True, slots=True)` storing principles as an immutable ordered mapping — use `principles: tuple[tuple[str, str], ...]` (key,text pairs) so order is stable for injection + show and mutation raises. Add a helper property/method (e.g. `as_mapping()` returning a dict, and `keys()`/iteration) for consumers. Implement `load_principles(cwd: Path) -> dict[str, object]` (or a small dataclass) that reads `cwd / ".voss" / "principles.yml"`, returns an empty project-layer + empty disable-list when the file is absent, and on a present file does `yaml.safe_load`; the parsed top level MUST be a mapping — extract an optional top-level `disable: [keys]` list (validate it is a list of strings) and treat all OTHER `key: "string"` pairs as the project principles. RAISE `VossPrinciplesConfigError` with a clear message when: YAML fails to parse (catch `yaml.YAMLError`), the top level is not a mapping, a principle value is not a string, or `disable` is present but not a list of strings. Do NOT swallow to None/defaults on malformed input (this is the deliberate divergence from `load_constraints`). Reuse `import yaml` + project pydantic if a schema helps — NO new third-party deps. Decision to lock here (Claude's discretion): defaults live as the `DEFAULT_PRINCIPLES` constant IN this module (no shipped `.voss/principles.default.yml` file) — simpler, single source of truth. Write `tests/harness/test_principles_config.py` covering every bullet in <behavior>.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_principles_config.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `PrinciplesConfig` is `frozen=True, slots=True`; a test asserting mutation raises `FrozenInstanceError` passes.
    - `DEFAULT_PRINCIPLES` has exactly six keys with the exact D-02 strings (test asserts equality per key).
    - A valid `.voss/principles.yml` loads without error; a malformed file raises `VossPrinciplesConfigError`; a missing file does not raise.
    - `.venv/bin/python -m pytest tests/harness/test_principles_config.py -x -q` exits 0.
  </acceptance_criteria>
  <done>principles.py exports PrinciplesConfig (frozen), DEFAULT_PRINCIPLES (six exact pairs), VossPrinciplesConfigError, and load_principles; loader is loud on malformed input and silent (defaults-path) on missing file; tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Additive-override + explicit-disable merge</name>
  <files>voss/harness/principles.py, tests/harness/test_principles_config.py</files>
  <read_first>
    - voss/harness/principles.py (Task 1 output — DEFAULT_PRINCIPLES, PrinciplesConfig, load_principles)
    - .planning/phases/V2-principles-layer/V2-SPEC.md (Requirement 5 — additive override + explicit disable)
    - .planning/phases/V2-principles-layer/V2-CONTEXT.md (D-04 merge semantics; D-06 note that show needs per-principle source)
  </read_first>
  <behavior>
    - Test: no project file → merged active set is exactly the six defaults, in default order, each tagged source="default".
    - Test: project file adding key `bias` → merged set is six defaults + bias; bias tagged source="project", defaults tagged source="default".
    - Test: project file overriding `tests` with a new string → merged `tests` text is the project string, tagged source="project"; the other five defaults unchanged.
    - Test: project file with `disable: [scope]` → merged set omits `scope`; the other five defaults remain (source="default").
    - Test: project file setting `review: null` → merged set omits `review` (null-value disable path, equivalent to disable list).
    - Test: a disabled key that is ALSO redefined later behaves per D-04 (define + assert one deterministic rule; document it in a comment).
  </behavior>
  <action>
    In `voss/harness/principles.py` add `merge_principles(defaults, project_layer, disable) -> PrinciplesConfig` (and/or a top-level `resolve_principles(cwd) -> PrinciplesConfig` that calls `load_principles` then merges). Implement D-04: start from `DEFAULT_PRINCIPLES` (ordered); layer the project mapping ON TOP by key — a project key not in defaults ADDS (appended after defaults, preserving project insertion order), a project key matching a default REPLACES that default's string IN PLACE (keeping the default's ordinal position so order is stable); a default is REMOVED only when explicitly disabled — either its project value is `null`/`None`, OR its key appears in the top-level `disable: [keys]` list. Non-disabled defaults ALWAYS remain. So the result is a `PrinciplesConfig` whose ordered `principles` tuple reflects this. ALSO expose source provenance for `voss principles show` (D-06): provide a parallel accessor — e.g. `resolve_with_sources(cwd) -> tuple[tuple[str, str, str], ...]` returning `(key, text, source)` where source ∈ {"default","project"} (a key is "project" if the project layer supplied or overrode it, else "default"). Keep principle text strictly opaque — do NOT branch on any individual key/string anywhere; the merge is key-agnostic set algebra only (the guard test in V2-03 will assert this). Extend `tests/harness/test_principles_config.py` with every bullet in <behavior>.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_principles_config.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - No file → six defaults, source=default. Adding key X → six defaults + X(source=project). Overriding `tests` → replaced string, position stable. `disable:[scope]` and `scope: null` both remove scope; non-disabled defaults remain.
    - `resolve_with_sources(cwd)` returns `(key,text,source)` triples with correct source labels (consumed by V2-03 `show`).
    - Merge code contains zero conditionals keyed on any of the six principle key strings or their text (key-agnostic algebra only).
    - `.venv/bin/python -m pytest tests/harness/test_principles_config.py -x -q` exits 0.
  </acceptance_criteria>
  <done>merge implements additive override + null/disable removal with stable order; a source-labeled resolver exists for `show`; principle text never drives control flow; tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| filesystem → loader | `.voss/principles.yml` is user/project-authored untrusted YAML crossing into the harness config. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V2-01 | Tampering | `load_principles` YAML parse | mitigate | Use `yaml.safe_load` only (never `yaml.load`); reject non-mapping top level + non-string values with `VossPrinciplesConfigError`. |
| T-V2-02 | Denial of Service | unbounded principles.yml | accept | Size bound is enforced downstream by the ~1k-token cap in V2-02; loader itself reads one small project file. |
| T-V2-03 | Tampering | new dependency drift | mitigate | Reuse existing pyyaml/pydantic stack; add ZERO new third-party deps (verify `git diff pyproject.toml` empty). |
| T-V2-SC | Tampering | npm/pip installs | mitigate | No package installs in this plan; no install tasks → legitimacy gate N/A. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_principles_config.py -q` passes.
- `git diff --stat pyproject.toml` shows no change (no new deps).
- `grep -n "yaml.safe_load" voss/harness/principles.py` confirms safe loader (no bare `yaml.load`).
</verification>

<success_criteria>
- Frozen `PrinciplesConfig`, six exact defaults, loud-on-malformed loader, and additive/disable merge with source provenance all exist and are tested green.
- Zero new dependencies.
- VPRIN-01 (loader), VPRIN-03 (frozen/immutable — guard test lands in V2-03), VPRIN-05 (six defaults), VPRIN-06 (merge) substrate complete.
</success_criteria>

<output>
Create `.planning/phases/V2-principles-layer/V2-01-SUMMARY.md` when done.
</output>
