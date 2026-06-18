---
phase: BOS3-engineering-event-schema
plan: 02
type: execute
wave: 2
depends_on: ["BOS3-01-engineering-event-schema"]
files_modified:
  - .planning/schemas/examples/
  - tests/bos/__init__.py
  - tests/bos/test_event_schema.py
autonomous: true
requirements: [BOS-DATA-01]

must_haves:
  truths:
    - "The JSON Schema is proven valid against the Draft 2020-12 meta-schema by an automated test"
    - "At least one example event per live category, plus one reserved-stub example, round-trips against the schema"
    - "The bitemporal invariant (event_time + ingest_time present, ingest_time >= event_time) is enforced by a test over the examples"
    - "The D-03 mapping table in the prose spec is proven complete for every live category and every reserved category"
    - "All 9 taxonomy values are proven present in the schema's category enum"
  artifacts:
    - path: "tests/bos/test_event_schema.py"
      provides: "Contract-validation pytest suite (schema-valid, round-trip, bitemporal, taxonomy, mapping-completeness, correlation, reserved-hook, versioning)"
      contains: "Draft202012Validator"
      min_lines: 80
    - path: ".planning/schemas/examples"
      provides: "Bundled example events: one per live category (session/swarm/task/file) + one reserved-stub"
      min_lines: 0
  key_links:
    - from: "tests/bos/test_event_schema.py"
      to: ".planning/schemas/bos-events.schema.json"
      via: "loads + validates the schema and example events against it"
      pattern: "bos-events.schema.json"
    - from: "tests/bos/test_event_schema.py"
      to: ".planning/BOS-EVENT-SCHEMA.md"
      via: "parses the D-03 mapping table for completeness"
      pattern: "BOS-EVENT-SCHEMA.md"
---

<objective>
Build the contract-validation harness for the BOS event schema: bundled example
events (one per live category + a reserved stub) and a pytest suite that proves
the schema is valid, the examples round-trip, the bitemporal invariant holds, the
taxonomy is complete, the D-03 mapping table is complete, the correlation fields
and reserved BOS12 hook are present, and versioning is documented.

Purpose: BOS-DATA-01 — make the contract from BOS3-01 machine-verifiable so
downstream phases (BOS4/5/12) inherit a proven, regression-guarded substrate.
This is the Wave-0 validation listed in BOS3-VALIDATION.md, run against the real
artifacts authored in Wave 1.

Output:
- `.planning/schemas/examples/*.json` (example events)
- `tests/bos/test_event_schema.py` + `tests/bos/__init__.py`
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md

@.planning/phases/BOS3-engineering-event-schema/BOS3-RESEARCH.md
@.planning/phases/BOS3-engineering-event-schema/BOS3-VALIDATION.md
@.planning/phases/BOS3-engineering-event-schema/BOS3-01-PLAN.md

<interfaces>
<!-- The artifacts under test (authored by BOS3-01). Read them, do not re-author. -->
- .planning/schemas/bos-events.schema.json  -- normative JSON Schema (Draft 2020-12); source of truth
- .planning/BOS-EVENT-SCHEMA.md             -- prose spec; contains the D-03 mapping table to parse

Environment (VERIFIED 2026-06-18):
- `jsonschema` 4.26.0 is ALREADY installed in `.venv`. No install task, no package-legitimacy gate.
- Test runner: `.venv/bin/python -m pytest` (bare python3 lacks deps).
- `tests/` exists with a conftest.py; `tests/bos/` does NOT exist yet (create it).

Test functions to implement (from BOS3-VALIDATION / RESEARCH §Validation Architecture):
  test_schema_is_valid          -- Draft202012Validator.check_schema passes
  test_examples_validate        -- every examples/*.json validates against envelope + its category
  test_bitemporal_invariant     -- every example has event_time AND ingest_time; ingest_time >= event_time
  test_taxonomy_complete        -- category enum == the 9 locked values (4 live + 5 reserved)
  test_mapping_table_complete   -- parse BOS-EVENT-SCHEMA.md: each live category has >=1 named source row; each reserved marked external/BOS12
  test_correlation_invariant    -- every non-root example carries trace_id; file events carry parent_event_id
  test_external_identity_hook   -- envelope schema defines nullable external_identity_ref
  test_versioning_present       -- schema_version on envelope; spec has a migration-notes section
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Bundle example events (one per live category + a reserved stub)</name>
  <files>.planning/schemas/examples/session.example.json, .planning/schemas/examples/swarm.example.json, .planning/schemas/examples/task.example.json, .planning/schemas/examples/file.example.json, .planning/schemas/examples/reserved-ci.example.json, .planning/schemas/examples/outcome-later.example.json</files>
  <read_first>
    - .planning/schemas/bos-events.schema.json (authored in BOS3-01 — examples MUST validate against it)
    - .planning/BOS-EVENT-SCHEMA.md (field semantics + bitemporal rules)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-RESEARCH.md (real source field values to make examples realistic; §Bitemporal invariant 2 for the retroactive-outcome example)
  </read_first>
  <action>
    Create `.planning/schemas/examples/` with one valid example event per LIVE category
    (session, swarm, task, file) plus one RESERVED-stub example (e.g. `reserved-ci.example.json`
    using `category: "ci"` with an empty/minimal payload) plus one RETROACTIVE-OUTCOME example
    (`outcome-later.example.json`) whose `ingest_time` is strictly later than its `event_time`
    to exercise the D-02 "outcomes arrive as separate later events" invariant.
    Each example MUST be a complete envelope per bos-events.schema.json: all required common fields
    populated (schema_version=1, event_id, event_type namespaced e.g. "task.completed", category,
    event_time + ingest_time as ISO-8601 with ingest_time >= event_time, trace_id, source_ref with a
    real source enum value, external_identity_ref: null, payload per category). The file example MUST
    carry a non-null parent_event_id (a file event is never orphaned — RESEARCH OQ3). Use realistic
    field values drawn from the enumerated sources (e.g. swarm example: swarm_id, task_id, roster;
    task example: goal + exit_reason from the EXIT_REASONS set + changed[]).
    Do NOT modify the schema or the spec; these examples are consumers of the contract.
  </action>
  <verify>
    <automated>.venv/bin/python -c "import json,glob,jsonschema; s=json.load(open('.planning/schemas/bos-events.schema.json')); v=jsonschema.Draft202012Validator(s); fs=glob.glob('.planning/schemas/examples/*.json'); assert len(fs)>=6, f'need >=6 examples got {len(fs)}'; [v.validate(json.load(open(f))) for f in fs]; outc=json.load(open('.planning/schemas/examples/outcome-later.example.json')); assert outc['ingest_time']>outc['event_time'], 'retroactive outcome must have ingest_time>event_time'; print(f'{len(fs)} examples valid; retroactive outcome ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/schemas/examples/` contains >=6 example JSON files: one each for session/swarm/task/file, one reserved-category stub, one retroactive-outcome.
    - Every example validates against `bos-events.schema.json` via `jsonschema.Draft202012Validator` (no validation errors).
    - Every example has both `event_time` and `ingest_time` with `ingest_time >= event_time`; the outcome example has `ingest_time > event_time`.
    - The file example carries a non-null `parent_event_id`; every example carries `trace_id` and `external_identity_ref: null`.
    - `git diff --quiet .planning/schemas/bos-events.schema.json` exits 0 (schema unchanged) and `git diff --quiet .planning/PROTOCOL.md` exits 0.
  </acceptance_criteria>
  <done>At least 6 example events exist, all validate against the JSON Schema, and they exercise the bitemporal + correlation + reserved-category + retroactive-outcome invariants; no contract artifact modified.</done>
</task>

<task type="auto">
  <name>Task 2: Author tests/bos/test_event_schema.py (8-check contract validation suite)</name>
  <files>tests/bos/__init__.py, tests/bos/test_event_schema.py</files>
  <read_first>
    - .planning/phases/BOS3-engineering-event-schema/BOS3-VALIDATION.md (Per-Task Verification Map + the 8 test functions + automated commands)
    - .planning/phases/BOS3-engineering-event-schema/BOS3-RESEARCH.md (§Validation Architecture Req->Test map)
    - .planning/schemas/bos-events.schema.json + .planning/BOS-EVENT-SCHEMA.md (the artifacts under test)
    - tests/conftest.py (repo pytest conventions — match existing style)
  </read_first>
  <action>
    Create `tests/bos/__init__.py` (empty) and `tests/bos/test_event_schema.py` implementing the 8
    test functions listed in <interfaces>, using pathlib to locate the repo-root artifacts
    (`.planning/schemas/bos-events.schema.json`, `.planning/schemas/examples/*.json`,
    `.planning/BOS-EVENT-SCHEMA.md`) relative to the repo root, and `jsonschema.Draft202012Validator`
    for validation. Specifically:
    - test_schema_is_valid: load schema; `Draft202012Validator.check_schema(schema)` raises nothing.
    - test_examples_validate: glob examples/*.json; each validates against the schema (parametrize over files).
    - test_bitemporal_invariant: each example has non-empty event_time AND ingest_time; assert ingest_time >= event_time (ISO-8601 string compare is safe for zero-padded UTC, or parse with datetime.fromisoformat).
    - test_taxonomy_complete: extract the category enum from the schema; assert it equals exactly the 9 locked values.
    - test_mapping_table_complete: read BOS-EVENT-SCHEMA.md; locate the D-03 mapping table; assert every live category (session/swarm/task/file) has a row naming >=1 source token (swarm_log|session|audit|sse|watch) and every reserved category (review/ci/validation/deploy/incident) row is marked external/BOS12. When counting source tokens, EXCLUDE markdown comment/heading lines (strip lines starting with '#') so prose cannot self-satisfy the gate.
    - test_correlation_invariant: each non-root example carries trace_id; the file-category example carries a non-null parent_event_id.
    - test_external_identity_hook: the envelope schema defines `external_identity_ref` and it permits null.
    - test_versioning_present: schema defines `schema_version`; BOS-EVENT-SCHEMA.md contains a migration-notes / versioning section heading.
    Match the existing tests/ pytest style. Do NOT modify the schema, spec, or any voss/harness/** file.
    Then update BOS3-VALIDATION.md: fill the Per-Task Verification Map rows with these task IDs +
    automated commands, set `wave_0_complete: true` and `nyquist_compliant: true` in its frontmatter.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/bos/test_event_schema.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `tests/bos/test_event_schema.py` and `tests/bos/__init__.py` exist.
    - `.venv/bin/python -m pytest tests/bos/test_event_schema.py -q` exits 0 with all 8 test functions passing (none skipped, none xfailed).
    - The mapping-completeness test strips markdown comment/heading lines before counting source tokens (no self-invalidating grep gate).
    - The suite proves: schema valid (Draft 2020-12), examples round-trip, bitemporal invariant, 9-value taxonomy, D-03 mapping completeness, correlation invariant, reserved external_identity_ref hook, versioning present.
    - BOS3-VALIDATION.md Per-Task Verification Map rows are filled and its frontmatter has `wave_0_complete: true` and `nyquist_compliant: true`.
    - `git diff --quiet .planning/schemas/bos-events.schema.json .planning/BOS-EVENT-SCHEMA.md .planning/PROTOCOL.md` exits 0 and `git diff --quiet voss/` exits 0.
  </acceptance_criteria>
  <done>An 8-check pytest contract suite passes green against the real BOS3-01 artifacts, proving every BOS-DATA-01 invariant; BOS3-VALIDATION.md is updated and marked nyquist-compliant; no contract or harness source modified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| example events -> schema validator | Examples are untrusted input proving the schema's validation surface; the test boundary catches malformed events. No runtime/network crosses here. |
| test author -> contract + harness source | Tests must NOT modify the schema, spec, PROTOCOL.md, or voss/harness/** (read-only). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-BOS3-04 | Tampering | self-invalidating grep/parse gate | mitigate | The mapping-completeness test strips comment/heading lines before counting source tokens (grep-gate hygiene), so spec prose cannot accidentally satisfy the gate. |
| T-BOS3-05 | Tampering | contract + harness source files | mitigate | Acceptance criteria assert `git diff --quiet` for schema, spec, PROTOCOL.md, and voss/; tests are consumers only. |
| T-BOS3-06 | Information disclosure | example event payloads | mitigate | Examples use synthetic, non-sensitive field values only; no secrets/credentials/PII (inherits PROJECT.md + global sensitive-data rule). |
| T-BOS3-SC | Tampering | package installs | accept | No installs; `jsonschema` 4.26.0 already present in `.venv`. No legitimacy gate needed. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/bos/test_event_schema.py -q` — all 8 tests green.
- `.venv/bin/python -m pytest tests/bos/ -q` — full BOS suite green (per-wave merge check).
- `git diff --quiet .planning/PROTOCOL.md && git diff --quiet voss/` — no source modified.
</verification>

<success_criteria>
- >=6 example events bundled, all round-trip against the JSON Schema.
- 8-check pytest suite green, proving every BOS-DATA-01 invariant (schema-valid, round-trip, bitemporal, taxonomy, mapping-completeness, correlation, reserved-hook, versioning).
- BOS3-VALIDATION.md updated and marked nyquist_compliant + wave_0_complete.
- PROTOCOL.md, the contract artifacts, and voss/harness/** unchanged by this plan's test code (examples are new consumers).
</success_criteria>

<output>
Create `.planning/phases/BOS3-engineering-event-schema/BOS3-02-SUMMARY.md` when done.
</output>
