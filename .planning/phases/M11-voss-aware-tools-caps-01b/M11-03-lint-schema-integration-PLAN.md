---
phase: M11-voss-aware-tools-caps-01b
plan: 03
type: execute
wave: 3
depends_on: [M11-01]
files_modified:
  - voss/harness/voss_lint_schema.py
  - tests/harness/test_voss_lint_schema.py
  - tests/skills/test_skills_smoke.py
autonomous: true
requirements: [VTOOL-01, VTOOL-05]
---

<objective>
Consume and verify the T7 `voss-lint-as-skill` output contract without
rebuilding the linter. This plan proves the skill is first-class reachable and
adds a small M11 schema consumer for downstream surfaces.
</objective>

<context>
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-CONTEXT.md
@.planning/phases/M11-voss-aware-tools-caps-01b/M11-RESEARCH.md
@.planning/phases/T7-skills-bootstrap/T7-CONTEXT.md

Read first:
- `voss/harness/skills/voss_lint_as_skill.py`
- `voss/harness/skill_registry.py`
- `tests/skills/test_skills_smoke.py`
</context>

<threat_model>
The schema consumer must not loosen or silently reshape the T7 lint contract.
Reject missing or extra fields in tests. Do not add a `.voss` skill execution
path, do not bypass the existing skill registry, and do not turn a read-only
lint surface into a mutating tool.
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add frozen schema consumer</name>
  <action>
    Create `voss/harness/voss_lint_schema.py` with:

    - `FINDING_FIELDS = ("file", "line", "col", "rule", "severity", "msg", "hint")`
    - `LintFinding` dataclass with those fields
    - `parse_lint_json(text: str) -> list[LintFinding]`
    - `render_lint_summary(findings: list[LintFinding]) -> str`

    `parse_lint_json()` must require top-level `version == 1`, require
    `findings` to be a list, reject missing fields, and reject extra finding
    fields. This is a consumer contract. Do not edit
    `voss_lint_as_skill.py`.
  </action>
  <verify>
    <automated>python3 -m py_compile voss/harness/voss_lint_schema.py</automated>
  </verify>
  <done>Consumer module validates the frozen schema exactly.</done>
</task>

<task type="auto">
  <name>Task 2: Add schema tests and skill reachability checks</name>
  <action>
    Create `tests/harness/test_voss_lint_schema.py`.

    Cover:
    - valid version-1 JSON parses
    - missing field fails
    - extra field fails
    - bad version fails
    - `default_skill_registry().get("voss-lint-as-skill")` is present and
      `mutating is False`
    - running the existing skill against a seeded bad `.voss` emits JSON that
      parses with the new consumer
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/test_voss_lint_schema.py</automated>
  </verify>
  <done>M11 consumes the T7 schema unchanged and proves first-class reachability.</done>
</task>

<task type="auto">
  <name>Task 3: Preserve T7 smoke tests</name>
  <action>
    If T7 smoke coverage already asserts the exact schema fields, leave it
    unchanged. If it only checks a subset, add one assertion that the finding
    key order/set is exactly `file,line,col,rule,severity,msg,hint`. Do not
    weaken existing T7 assertions.
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/skills/test_skills_smoke.py -k "voss_lint or registry_count"</automated>
  </verify>
  <done>T7 lint contract remains green.</done>
</task>

</tasks>

<verification>
Run:

```bash
python3 -m pytest -q tests/harness/test_voss_lint_schema.py tests/skills/test_skills_smoke.py -k "voss_lint or registry_count"
python3 -m pytest -q tests/harness/tui/test_no_new_runtime_hooks.py
git diff --check
```
</verification>

<success_criteria>
- VTOOL-01 is satisfied by consuming the existing skill schema unchanged.
- No `.voss` skill execution path is added.
- No runtime/recorder emit point is added.
</success_criteria>
