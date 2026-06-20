---
phase: BOS3
slug: engineering-event-schema
status: planned
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-18
---

# Phase BOS3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Docs-first schema-contract phase: "tests" validate the CONTRACT artifacts
> (JSON Schema lints, example-event round-trip, mapping-table completeness),
> not runtime behavior. See BOS3-RESEARCH.md §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing repo suite; `.venv/bin/python`) |
| **Config file** | existing repo pytest config |
| **Quick run command** | `.venv/bin/python -m pytest tests/bos/test_event_schema.py -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/bos/ -q` |
| **Estimated runtime** | ~10 seconds |

> Note: `jsonschema` 4.26.0 confirmed installed in `.venv` (2026-06-18) — no install
> task, no package-legitimacy gate required.

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

> Validates contract artifacts: (1) JSON Schema is itself valid (Draft 2020-12
> meta-schema), (2) bundled example events round-trip against the schema, (3) the
> D-03 mapping table covers every live category + every reserved category, (4) the
> bitemporal invariant (event_time + ingest_time; ingest_time >= event_time;
> outcomes as separate later events) is asserted over the examples.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 01-1 author JSON Schema | BOS3-01 | 1 | BOS-DATA-01 | schema-lint + taxonomy | `.venv/bin/python -c "import json,jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('.planning/schemas/bos-events.schema.json')))"` | ⬜ pending |
| 01-2 author prose spec | BOS3-01 | 1 | BOS-DATA-01 | content + mapping-table assertions | `.venv/bin/python -c "t=open('.planning/BOS-EVENT-SCHEMA.md').read(); assert all(c in t for c in ['session','swarm','task','file','review','ci','validation','deploy','incident']) and 'ingest_time' in t and 'bos-events.schema.json' in t"` | ⬜ pending |
| 02-1 bundle example events | BOS3-02 | 2 | BOS-DATA-01 | example round-trip + bitemporal | `.venv/bin/python -c "import json,glob,jsonschema; s=json.load(open('.planning/schemas/bos-events.schema.json')); v=jsonschema.Draft202012Validator(s); [v.validate(json.load(open(f))) for f in glob.glob('.planning/schemas/examples/*.json')]"` | ⬜ pending |
| 02-2 contract pytest suite | BOS3-02 | 2 | BOS-DATA-01 | full 8-check contract suite | `.venv/bin/python -m pytest tests/bos/test_event_schema.py -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

The 8 checks in `tests/bos/test_event_schema.py` (02-2): `test_schema_is_valid`,
`test_examples_validate`, `test_bitemporal_invariant`, `test_taxonomy_complete`,
`test_mapping_table_complete`, `test_correlation_invariant`,
`test_external_identity_hook`, `test_versioning_present`.

---

## Wave 0 Requirements

> The normative artifacts under test are authored in Wave 1 (BOS3-01), so the
> Wave-2 tests (BOS3-02) validate REAL artifacts, not scaffolds. No xfail/skip
> scaffolding is needed: the schema + spec exist before the tests run.

- [ ] `.planning/schemas/bos-events.schema.json` — normative JSON Schema (BOS3-01 Task 1)
- [ ] `.planning/BOS-EVENT-SCHEMA.md` — normative prose spec (BOS3-01 Task 2)
- [ ] `.planning/schemas/examples/*.json` — >=6 example events (BOS3-02 Task 1)
- [ ] `tests/bos/__init__.py` + `tests/bos/test_event_schema.py` — 8-check contract suite (BOS3-02 Task 2)
- [x] `jsonschema` available in `.venv` — confirmed 4.26.0 (no install needed)

*Schema representation: JSON Schema Draft 2020-12 (research recommendation, adopted).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Forward-compat of reserved external-category envelope | BOS-DATA-01 | Correctness only fully provable when BOS12 ingestion lands | Human review: external categories slot in with zero `schema_version` bump. (Partially auto-covered: reserved-stub example round-trips today.) |

*Most contract properties have automated verification (schema lint + round-trip + mapping completeness).*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter (flipped by BOS3-02 Task 2 on green suite)

**Approval:** planned — nyquist_compliant flips true when `tests/bos/test_event_schema.py` is green.
