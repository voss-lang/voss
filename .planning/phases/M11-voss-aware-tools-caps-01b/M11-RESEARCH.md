# Phase M11: Voss-aware Tools (CAPS-01b) - Research

**Researched:** 2026-05-18
**Domain:** Recorded-run inspectors, Voss lint schema consumption, `.voss` to Python diff surface, TUI modal reuse
**Confidence:** HIGH

---

## Summary

M11 is a wiring phase. The existing runtime and harness already record enough
state for useful read-only product surfaces, but not enough for the literal
"propagation graph" and per-`ctx(budget:)` frame language in the roadmap. The
plan therefore preserves the M11-CONTEXT downgrade:

- Probable inspector = confidence-annotated decision sequence from
  `RunRecord.decisions[]`.
- Budget tracer = per-agent-iteration token timeline from
  `RunRecord.iterations[]`.
- `.voss` lint-as-skill = consume and verify the T7 `voss-lint-as-skill`
  schema unchanged.
- `.voss` to Python diff = on-demand two-pane/source-vs-generated view, no
  source map.

No new emit points are needed. `voss/harness/recorder.py` and
`voss_runtime/{probable,budget,agent}.py` remain read-only and are protected by
the existing runtime-surface hash test.

Graphify query was attempted first per repo navigation policy, but this repo
has no `graphify-out/graph.json`; research fell back to SecondBrain project
wiki plus live source reads.

---

## Locked Inputs

### From M11-CONTEXT

- D-01 no-new-emit constraint is binding.
- D-02 `.voss` lint-as-skill is verify/expose only; do not rebuild T7 SKL-06.
- D-03 CLI-first, TUI via read-only modals, no M9 region amendment.
- D-04 probable and budget shapes are session/run inspectors.
- D-05 `.voss` to Python diff is on-demand only and dogfood-capable.
- D-06 all M11 tools are read-only and inherit existing redaction posture.
- D-07 proposed slash names were `/probable`, `/budget`, `/vdiff`; `/budget`
  required collision confirmation.

### Collision Result

`/budget` is already registered in `voss/harness/cli.py` as the T6 USD budget
slash. M11 must not reuse it. Chosen replacement: `/btrace`.

Reserved M8 names remain:
`("/recall", "/forget", "/memory", "/save")`.

---

## Live Code Findings

### Recorded Data Source

`voss/harness/session.py`:

- `RunRecord.decisions: list[dict]`.
- `RunRecord.iterations: list[IterationRecord]`.
- `IterationRecord` carries `prompt_tokens`, `completion_tokens`,
  `cache_creation_input_tokens`, `cache_read_input_tokens`, `cost_usd`,
  `exit_reason`, and `batches`.
- `SessionRecord.runs` persists runs as dictionaries after JSON round-trip.

`voss/harness/recorder.py`:

- `RunRecorder.absorb()` copies semantic `decisions` from model output.
- `write_decisions_md()` consumes only `title`, `body`, and `confidence`.
- No lineage, source refs, DAG edges, or `ctx(budget:)` scope identifiers are
  present.

Implication: inspector/tracer code must normalize both dataclass and dict
records and must not assume richer fields.

### Slash Registry

`voss/harness/cli.py` owns `_build_slash_registry()`. Current relevant slashes:

- `/budget` exists and shows or sets the session USD ceiling.
- `/why` renders the last plan rationale and confidence.
- `/cost` has `--by-model` and an approximate `--by-tool`.
- `/skill` already runs registered skills.

M11 should add:

- `/probable <session-id> [--decision N]`
- `/btrace <session-id>`
- `/vdiff <file.voss>`

### Tool Registry

`voss/harness/tools.py` builds a `dict[str, ToolEntry]` in `make_toolset()`.
Current count tests expect 7 mutating and 10 read-only tools. Adding M11 tools
requires updating `tests/harness/test_tools.py` count expectations and explicit
read-only membership.

Recommended M11 tool names:

- `voss_probable_inspect`
- `voss_budget_trace`
- `voss_py_diff`

All three are `is_mutating=False`. They read session/cache/source data and
return strings.

### Lint Skill

`voss/harness/skills/voss_lint_as_skill.py` already emits the frozen M11
schema:

```json
{
  "version": 1,
  "findings": [
    {
      "file": "...",
      "line": 1,
      "col": 1,
      "rule": "PARSE",
      "severity": "error",
      "msg": "...",
      "hint": null
    }
  ]
}
```

M11 should add a tiny schema consumer/validator for downstream inspector use,
but must not edit the producer unless a bug is found.

### Codegen and Cache Pairing

`voss.codegen.generate_python(program, source_path=..., cache_dir=...,
project_root=...)` returns a `CodegenResult` with generated Python source.

`voss compile <dir>` writes compiled harness artifacts to
`.voss-cache/harness/<name>.py` and `_manifest.json` for
`voss/harness/agent/`.

M11 diff pairing should:

1. Prefer existing `.voss-cache/harness/<stem>.py` when the source is under
   `voss/harness/agent/` and the cached artifact exists.
2. Otherwise parse/analyze/codegen on demand and diff the source against the
   generated Python text without writing new durable files.
3. Never promise a line-level source map.

### TUI Reuse

Existing reusable widgets:

- `ConfidenceBar` locked 16-cell output.
- `BudgetMeter` locked empty-budget placeholder behavior.
- `BudgetExhaustedModal` is interactive and exhaustion-specific; M11 should
  not repurpose it for read-only trace details.
- `DiffModal` is approval/hunk-shaped; M11 should not repurpose it. Add a
  read-only sibling for `.voss` to Python output.

Recommended widgets:

- `ProbableInspectModal` uses `ConfidenceBar`.
- `BudgetTraceModal` uses `BudgetMeter`.
- `VossPyDiffModal` follows `DiffModal` visual density but has no accept/reject
  actions.

### Redaction and Persistence

`SessionRecord` and `RunRecord` are fixed-field dataclasses. M11 adds no
persisted fields. Inspector output reads existing persisted user/run data and
prints it; no new persistence path is introduced. If an M11 handler appends
anything to session state later, it must route through existing session save
semantics and not add secret-shaped fields.

---

## Recommended Plan Shape

Five serial plans keep shared-file overlap manageable:

1. Core recorded-data inspector module and tests.
2. Probable/budget CLI, slash, and tool surfaces.
3. Lint schema consumer and integration tests.
4. `.voss` to Python diff core, CLI, slash, and tool surface.
5. TUI read-only modals plus final no-emit acceptance guards.

The dominant implementation risk is overbuilding. Every plan includes a
negative acceptance item that forbids new recorder/runtime emit points.

---

## Open Questions

None blocking.

Resolved during research:

- `/budget` collision? Yes, collision exists. Use `/btrace`.
- Need a new SPEC before planning? No. M11-CONTEXT plus ROADMAP is adequate
  and mirrors T6/T7 precedent.
- Need new package dependencies? No.

