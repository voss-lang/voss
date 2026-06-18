---
phase: BOS3
slug: engineering-event-schema
status: draft
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

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

> Populated by the planner during planning. Validates contract artifacts:
> (1) JSON Schema is itself valid (Draft 2020-12 meta-schema), (2) bundled
> example events validate against the schema, (3) the D-03 mapping table
> covers every source enumerated in research + every Voss-emitted category,
> (4) the bitemporal invariant (event_time + ingest_time present; outcomes as
> separate events) is asserted by an example round-trip.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| (planner to fill) | | | BOS-DATA-01 | schema-validation | `(planner to fill)` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/bos/test_event_schema.py` — schema-valid + example round-trip stubs for BOS-DATA-01
- [ ] `tests/bos/__init__.py` / fixtures dir if absent
- [ ] `jsonschema` dependency available in `.venv` (likely present; planner confirms)

*Planner finalizes against the chosen schema representation (research recommends JSON Schema Draft 2020-12).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Forward-compat of reserved external-category envelope | BOS-DATA-01 | Correctness only provable when BOS12 ingestion lands | Human review: external categories slot in with zero `v` bump |

*Most contract properties have automated verification (schema lint + round-trip + mapping completeness).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
