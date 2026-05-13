---
phase: M7-sdk-polish
plan: 03
type: execute
wave: 3
depends_on: []
files_modified:
  - voss/harness/views.py
  - voss/harness/__init__.py
autonomous: true
requirements:
  - SDK-03
must_haves:
  truths:
    - "Embedders can write `from voss.harness import SessionView, RunView, view_session` and the import succeeds."
    - "`view_session(record)` accepts a `SessionRecord` (per D-12 + R-06) and returns a `SessionView` instance."
    - "`SessionView.runs` is a `tuple[RunView, ...]` (not a list — frozen + tuple is the 'really read-only' idiom per D-13)."
    - "`SessionView` excludes sensitive/internal fields not in D-10's whitelist (no `turns`, no `decisions`, no `risks`, etc.)."
    - "`RunView` excludes internal RunRecorder semantics (no `inspected`, `changed`, `avoided`, `assumptions`, `decisions`, `risks`, `validation`, `failures`, `follow_ups`)."
    - "Projection reads run dicts defensively via `.get()` (R-05) — never via attribute access — so legacy session JSON missing fields produces `RunView` instances with safe defaults."
    - "`view_session` is a pure function: no I/O, no mutation of input."
  artifacts:
    - path: "voss/harness/views.py"
      provides: "Read-only SessionView + RunView frozen dataclasses, pure view_session projection"
      contains: "def view_session"
      min_lines: 30
    - path: "voss/harness/__init__.py"
      provides: "Re-exports SessionView, RunView, view_session; __all__ extended"
      contains: "SessionView"
    - path: "tests/harness/test_views.py"
      provides: "Unit coverage for projection, field exclusion, defensive .get reads"
      contains: "def test_view_session_excludes_sensitive_fields"
  key_links:
    - from: "voss/harness/views.py view_session"
      to: "voss.harness.session.SessionRecord (input shape only — no import coupling to RunRecord)"
      via: "attribute reads on SessionRecord top-level fields; .get() reads on run dicts"
      pattern: "record.runs"
    - from: "voss/harness/__init__.py"
      to: "voss/harness/views.py"
      via: "from .views import RunView, SessionView, view_session"
      pattern: "from .views import"
---

<objective>
Add a new module `voss/harness/views.py` that defines two frozen
dataclasses (`SessionView`, `RunView`) and one pure projection function
(`view_session`). Promote all three to `voss.harness.__all__`.

The projection takes a private-schema `SessionRecord` (from
`voss/harness/session.py`) and returns a stable embedder-facing view that
EXCLUDES internal/sensitive fields. This insulates embedders from the
on-disk schema — `SessionRecord` / `RunRecord` stay private and free to
change.

Purpose: Embedders that want to introspect sessions (id, cwd, per-run
timestamps/cost/confidence) currently must reach into the private
`voss.harness.session` module and bind to `SessionRecord` / `RunRecord`
directly. Closes the "Session record types" gap from `docs/sdk.md`
"Known gaps (closing in M7)". Closes SDK-03.

Output:
- `voss/harness/views.py` (new) — `SessionView`, `RunView`, `view_session`.
- `voss/harness/__init__.py` — `__all__` gains all three names; import
  line extended.
- `tests/harness/test_views.py` (new) — projection coverage.

This is a projection plan, not a feature plan. No new persistence, no
new I/O, no schema changes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/M7-sdk-polish/M7-CONTEXT.md
@.planning/phases/M7-sdk-polish/M7-RESEARCH.md
@.planning/phases/M7-sdk-polish/M7-PATTERNS.md
@voss/harness/session.py
@voss/harness/__init__.py

<interfaces>
Existing `SessionRecord` at `voss/harness/session.py:85-107` (do NOT
modify):
```python
@dataclass
class SessionRecord:
    id: str
    name: str
    cwd: str
    model: str
    started_at: str
    updated_at: str
    total_cost_usd: float = 0.0
    turns: list[dict] = field(default_factory=list)
    runs: list[dict] = field(default_factory=list)   # NOT list[RunRecord]
```

R-05 confirms: `SessionRecord.runs` is `list[dict]` (raw asdict'd
RunRecord), not `list[RunRecord]`. `_hydrate` (line 119) does NOT
rehydrate run entries. The projection MUST use `.get()` on each run
dict — attribute access raises `AttributeError`.

New types (per D-09, D-10, D-11, D-13):

```python
@dataclass(frozen=True)
class RunView:
    id: str
    started_at: str
    ended_at: str
    goal: str
    cost_usd: float
    confidence: float | None
    diff_summary: str

@dataclass(frozen=True)
class SessionView:
    id: str
    name: str
    cwd: str
    model: str
    started_at: str
    updated_at: str
    total_cost_usd: float
    runs: tuple[RunView, ...]
```

Field mapping for `RunView` from a run dict (per R-05 / M7-RESEARCH §Q6):

| RunView field | Source dict key | Default |
|---|---|---|
| `id` | `"id"` | `""` |
| `started_at` | `"started_at"` | `""` |
| `ended_at` | `"ended_at"` | `""` |
| `goal` | `"goal"` | `""` |
| `cost_usd` | `"cost_usd"` (coerce via `float(...)`) | `0.0` |
| `confidence` | `r.get("plan", {}).get("confidence")` (already `float \| None`) | `None` |
| `diff_summary` | `"diff_summary"` | `""` |

EXCLUDED from `RunView` (must not appear in the dataclass at all):
`inspected`, `changed`, `avoided`, `assumptions`, `decisions`, `risks`,
`validation`, `failures`, `follow_ups`, `plan` (raw blob).

EXCLUDED from `SessionView`: `turns` (raw chat transcript — too volatile
and large; D-10).

`view_session` (per D-12 + R-06) accepts only `SessionRecord` in M7.
Dict overload is v0.2 polish (R-06). Signature:
```python
def view_session(record: SessionRecord) -> SessionView: ...
```

Pure projection: NO I/O, NO mutation of `record`.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create views.py with SessionView, RunView, view_session + tests</name>
  <files>voss/harness/views.py, tests/harness/test_views.py</files>
  <behavior>
    - `test_view_session_top_level_fields`: build a `SessionRecord` with id="abc", name="my-session", cwd="/tmp", model="claude", started_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:01:00Z", total_cost_usd=0.42, runs=[], turns=[{"role": "user", "content": "x"}]. Call `view_session(record)`. Assert all 7 top-level scalar fields project correctly. Assert `view.runs == ()` (empty tuple). Assert `not hasattr(view, "turns")` (sensitive field excluded).
    - `test_view_session_run_projection_full_run_dict`: build a `SessionRecord` whose `runs=[{"id":"r1","started_at":"t0","ended_at":"t1","goal":"do x","cost_usd":0.5,"plan":{"confidence":0.8},"diff_summary":"+1 -0"}]`. Call `view_session`. Assert `view.runs[0].id == "r1"`, `.confidence == 0.8`, `.cost_usd == 0.5`, `.diff_summary == "+1 -0"`.
    - `test_view_session_run_projection_legacy_run_dict_missing_fields`: build a run dict with ONLY `{"id":"old"}` (legacy pre-M2 shape). Assert `view.runs[0]` is a `RunView` with `id="old"`, `started_at=""`, `ended_at=""`, `goal=""`, `cost_usd=0.0`, `confidence is None`, `diff_summary=""`. Proves R-05 defensive `.get()` reads.
    - `test_view_session_excludes_sensitive_fields`: build a run dict with `{"id":"r1","decisions":[{"text":"...","why":"..."}],"risks":["secret-leak"],"validation":[{"ok":True}],"failures":[{"e":"oops"}],"inspected":["a.py"],"changed":["b.py"],"avoided":[{"p":"c"}],"assumptions":["asm"],"follow_ups":["fu"]}`. Project. Assert `not hasattr(view.runs[0], "decisions")`, `not hasattr(view.runs[0], "risks")`, etc. for each sensitive field. (Use `dataclasses.fields(view.runs[0])` to enumerate the field names and check the EXCLUDED set against it.)
    - `test_view_session_no_plan_means_confidence_none`: run dict missing `plan` key → `RunView.confidence is None`. Run dict with `plan={}` → `RunView.confidence is None`. Run dict with `plan={"confidence": 0.0}` → `RunView.confidence == 0.0` (zero is a valid confidence, must not coerce to None).
    - `test_view_session_is_pure`: build a record, project it twice, assert the two `SessionView` instances compare equal (frozen dataclass `__eq__`) AND that `record.runs` is unchanged after projection (no mutation).
    - `test_view_session_runs_is_tuple_not_list`: assert `isinstance(view.runs, tuple)` and `not isinstance(view.runs, list)` per D-13.
    - `test_session_view_is_frozen`: assert `dataclasses.is_dataclass(SessionView)` AND attempting `view.id = "other"` raises `dataclasses.FrozenInstanceError`. Same for `RunView`.
    - `test_session_view_dataclass_fields_exact`: enumerate `dataclasses.fields(SessionView)` and assert the field name set is exactly `{"id","name","cwd","model","started_at","updated_at","total_cost_usd","runs"}`. Enumerate `dataclasses.fields(RunView)` and assert the set is exactly `{"id","started_at","ended_at","goal","cost_usd","confidence","diff_summary"}`. Regression-pin against accidentally exposing private fields.
  </behavior>
  <action>
    Per D-09, D-10, D-11, D-12, D-13, R-05, R-06 — create
    `voss/harness/views.py` (new file). Module docstring: one-paragraph
    summary describing the projection contract — "read-only embedder
    view; SessionRecord / RunRecord stay private; pure projection, no
    I/O".

    Imports:
    - `from __future__ import annotations`
    - `from dataclasses import dataclass`
    - `from .session import SessionRecord` (typing-only import is also
      acceptable behind `TYPE_CHECKING` since the runtime only reads
      attributes; either is fine — keep it simple: regular import).

    Define `RunView` as `@dataclass(frozen=True)` with the 7 fields
    listed in `<interfaces>`. NO extra fields. NO methods.

    Define `SessionView` as `@dataclass(frozen=True)` with the 8 fields
    listed in `<interfaces>`. The `runs` field is typed as
    `tuple[RunView, ...]`. NO extra fields. NO methods.

    Define `view_session(record: SessionRecord) -> SessionView`:
    1. For each `r` in `record.runs` (each `r` is a dict per R-05):
       - Build `RunView` via `.get()` reads per the field-mapping table
         in `<interfaces>`. Use `float(r.get("cost_usd", 0.0))` for the
         numeric coercion (matches `RunRecord.cost_usd: float`).
       - Confidence: `plan = r.get("plan") or {}; confidence = plan.get("confidence")`. Confidence is `None` when `plan` is absent OR `plan` is an empty/None dict OR `confidence` key is absent. A literal `0.0` value MUST be preserved (do NOT use `or None` truthiness short-circuiting).
    2. Pack into a `tuple(...)` (per D-13).
    3. Construct `SessionView` from `record` top-level attributes
       (attribute access is safe — `SessionRecord` IS a typed dataclass)
       plus the runs tuple.
    4. Return. Do not mutate `record`.

    Function body: ~10-15 LOC. Pure projection, no I/O, no logging.

    Create `tests/harness/test_views.py` with the nine behavior bullets
    above. Use plain `def test_*` (no asyncio needed — projection is
    sync). Build `SessionRecord` instances directly (don't go through
    `SessionRecord.new` so the test stays hermetic and deterministic).
  </action>
  <verify>
    <automated>pytest tests/harness/test_views.py -x -q</automated>
  </verify>
  <done>
    `tests/harness/test_views.py` passes all nine tests.
    `voss/harness/views.py` exists with `SessionView`, `RunView`,
    `view_session` defined. Both dataclasses are frozen. `SessionView.runs`
    is a tuple. No I/O performed by `view_session`. Run dicts read
    defensively via `.get()`. Sensitive fields excluded.
  </done>
</task>

<task type="auto">
  <name>Task 2: Promote SessionView, RunView, view_session in voss.harness.__all__</name>
  <files>voss/harness/__init__.py</files>
  <action>
    Add to the import block:
    `from .views import RunView, SessionView, view_session` (alphabetical
    grouping — place after `.tools` import, before `.cli` import, or in
    whatever order the existing file uses; current file uses
    `agent, cli, permissions, tools` so add `.views` alphabetically
    after `.tools`).

    Extend `__all__` with three names in their alphabetical positions:
    `"RunView"`, `"SessionView"`, `"view_session"`. After this plan,
    `__all__` size is 11 (8 baseline + 3). If M7-01 and M7-02 have
    already merged, the combined `__all__` is 14 (8 + 2 + 1 + 3) —
    matching the final M7 target per R-12.

    Do NOT touch the stability docstring (Wave 6 / M7-06).
  </action>
  <verify>
    <automated>python -c "from voss.harness import SessionView, RunView, view_session; print('ok')" | grep -q "^ok$"</automated>
  </verify>
  <done>
    `from voss.harness import SessionView, RunView, view_session` succeeds.
    All three names appear in `voss.harness.__all__`. The existing 8
    names still present.
  </done>
</task>

</tasks>

<verification>
- `pytest tests/harness/test_views.py -x` passes (Task 1 behavior).
- `python -c "from voss.harness import SessionView, RunView, view_session; from voss.harness.session import SessionRecord; r = SessionRecord(id='a', name='n', cwd='/', model='m', started_at='t', updated_at='t'); v = view_session(r); print(type(v).__name__, len(v.runs))"` prints `SessionView 0`.
- `python -c "import dataclasses; from voss.harness import SessionView, RunView; print(sorted(f.name for f in dataclasses.fields(SessionView)))"` prints the exact 8-field list, no extras.
- Manual grep: `grep -c "view_session\|SessionView\|RunView" voss/harness/__init__.py` returns at least `4` (one import line, three `__all__` entries).
- No changes to `voss/harness/session.py` whatsoever (regression check: `git diff voss/harness/session.py` empty).
</verification>

<success_criteria>
- `voss/harness/views.py` exists with `SessionView`, `RunView`, `view_session`.
- Both dataclasses are `@dataclass(frozen=True)` (D-13).
- `SessionView.runs: tuple[RunView, ...]` (not list).
- All sensitive/internal fields (`decisions`, `risks`, `validation`, `failures`, `inspected`, `changed`, `avoided`, `assumptions`, `follow_ups`, `turns`, raw `plan`) are EXCLUDED from the view types.
- `view_session` is a pure function — no I/O, no mutation of the input record.
- Run dicts are read defensively via `.get()` (R-05).
- A literal `confidence == 0.0` is preserved (no truthiness coercion to `None`).
- `voss.harness.__all__` contains `"SessionView"`, `"RunView"`, `"view_session"`.
- No changes to `SessionRecord` / `RunRecord` (they stay private per D-12).
- No changes to `tests/packaging/test_public_api.py` (Wave 6 / M7-06).
- No changes to `docs/sdk.md` (Wave 6 / M7-06).
</success_criteria>

<output>
After completion, create `.planning/phases/M7-sdk-polish/M7-03-SUMMARY.md`
documenting the field mapping table, the `.get()`-vs-attribute decision
rationale (R-05), and the nine test cases.
</output>
