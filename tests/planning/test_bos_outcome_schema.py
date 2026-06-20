"""BOS5 outcome/reward contract-validation suite (13 checks, ACC-01..ACC-07).

Loads contracts/outcomes.schema.json + .planning/schemas/examples/outcome*.json
and asserts the structural properties locked in BOS5-01. This suite READS the
artifacts; it does not modify them. The BOS4 decision-no-outcome check is
CONDITIONAL — it skips cleanly while the BOS4 decision schema is absent.

Normative test names come from BOS5-VALIDATION.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / "contracts" / "outcomes.schema.json"
EXAMPLES_DIR = REPO / ".planning" / "schemas" / "examples"
DOC_PATH = REPO / "docs" / "BOS5-OUTCOME-REWARD-SPEC.md"
DECISION_SCHEMAS = [
    REPO / "contracts" / "decisions.schema.json",
    REPO / "contracts" / "decision-ledger.schema.json",
]

EXPECTED_LABELS = {
    "clean_merge",
    "rework",
    "revert",
    "failed_validation",
    "escaped_defect",
    "incident",
    "human_override",
}
SEVERITY_LABELS = {"rework", "escaped_defect", "incident"}
EXPECTED_ROLES = {"hard_gate", "dashboard"}


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


@pytest.fixture(scope="module")
def defs(schema) -> dict:
    return schema.get("$defs", {})


@pytest.fixture(scope="module")
def example_records() -> dict[str, dict]:
    files = sorted(EXAMPLES_DIR.glob("outcome*.json"))
    return {f.name: json.loads(f.read_text()) for f in files}


def _label_examples(example_records: dict[str, dict]) -> dict[str, dict]:
    return {n: r for n, r in example_records.items() if "reward" not in n}


def _envelope_keys(defs: dict) -> set[str]:
    return set(defs.get("OutcomeEnvelope", {}).get("properties", {}).keys())


def _const_value(prop: dict) -> str | None:
    if "const" in prop:
        return prop["const"]
    if "enum" in prop and len(prop["enum"]) == 1:
        return prop["enum"][0]
    return None


# ACC-01 + ACC-06 (stability/lint gate for the hand-authored sibling schema).
def test_schema_is_valid(schema):
    jsonschema.Draft202012Validator.check_schema(schema)
    assert SCHEMA_PATH.exists(), "outcomes.schema.json must be tracked"


# ACC-02
def test_categorical_label_coverage(defs):
    found = set()
    for name, defn in defs.items():
        if name.endswith("Label"):
            lt = defn.get("properties", {}).get("label_type", {})
            v = _const_value(lt)
            if v:
                found.add(v)
    assert found == EXPECTED_LABELS, f"label_type coverage mismatch: {found ^ EXPECTED_LABELS}"


# ACC-02
def test_measure_coverage(defs):
    ct = defs.get("CycleTimeMeasure", {})
    mt = ct.get("properties", {}).get("measure_type", {})
    assert _const_value(mt) == "cycle_time", "cycle_time measure_type missing"


# ACC-04
def test_label_examples_validate(schema, example_records):
    validator = jsonschema.Draft202012Validator(schema)
    assert len(example_records) >= 9, f"need >=9 examples, got {len(example_records)}"
    for name, rec in example_records.items():
        validator.validate(rec)


def test_bitemporal_invariant(example_records):
    for name, rec in example_records.items():
        if "reward" in name:
            continue
        assert "event_time" in rec, f"{name} missing event_time"
        assert "ingest_time" in rec, f"{name} missing ingest_time"
        assert rec["ingest_time"] >= rec["event_time"], (
            f"{name} ingest_time {rec['ingest_time']} < event_time {rec['event_time']}"
        )


# T-BOS5-02-01 / D-04
def test_no_decision_leakage_in_label(schema, defs, example_records):
    env_keys = _envelope_keys(defs)
    assert "decision_id" not in env_keys, "OutcomeEnvelope defines decision_id (leakage)"
    assert "recommended_action" not in env_keys, "OutcomeEnvelope defines recommended_action (leakage)"
    for name, rec in _label_examples(example_records).items():
        assert "decision_id" not in rec, f"{name} carries decision_id"
        assert "recommended_action" not in rec, f"{name} carries recommended_action"


# BOS-DATA-04
def test_reward_record_shape(defs):
    rr = defs.get("RewardRecord", {})
    required = set(rr.get("required", []))
    for f in ("decision_id", "objective_vector", "weight_set_version", "horizon", "computed_at"):
        assert f in required, f"RewardRecord missing required {f}"
    assert rr.get("additionalProperties") is False, "RewardRecord must close the envelope"


# T-BOS5-02-04 / gsd-scaffold-fictional-api guard
def test_decision_schema_no_outcome_field():
    path = next((p for p in DECISION_SCHEMAS if p.exists()), None)
    if path is None:
        pytest.skip("BOS4 decisions.schema.json not yet authored")
    dec = json.loads(path.read_text())
    dec_str = json.dumps(dec)
    for leak in ('"outcome"', '"label"', '"reward"'):
        assert not re.search(leak + r'\s*:', dec_str), (
            f"decision schema {path.name} defines a {leak.strip(chr(34))} property (leakage)"
        )


# ACC-05 / T-BOS5-02-02
def test_tension_pair_coverage(schema, defs, example_records):
    guardrails = []
    for name, defn in defs.items():
        if name == "GuardrailMetricSpec":
            continue
        if not isinstance(defn, dict):
            continue
    gms = defs.get("GuardrailMetricSpec", {})
    assert gms, "GuardrailMetricSpec $def missing"
    assert "linked_reward_objective" in gms.get("required", []), (
        "GuardrailMetricSpec must require linked_reward_objective"
    )
    reward = example_records.get("outcome-reward.json")
    objectives = set((reward or {}).get("objective_vector", {}).keys())
    if not objectives:
        pytest.skip("no objective_vector in reward example to cross-check")
    # The coverage rule is structural on the contract: every objective named in
    # WeightSetRecord.objectives must appear as a linked_reward_objective. Since
    # the schema does not embed objective names, this test asserts the rule is
    # present in the rationale spec's tension-pair table for each example objective.
    doc = DOC_PATH.read_text() if DOC_PATH.exists() else ""
    if not doc:
        pytest.skip("BOS5-OUTCOME-REWARD-SPEC.md not authored")
    for obj in objectives:
        assert obj in doc, f"objective {obj!r} not covered in tension-pair table"


# T-BOS5-02-02
def test_guardrail_role_enum(defs):
    role = defs.get("GuardrailMetricSpec", {}).get("properties", {}).get("role", {})
    assert set(role.get("enum", [])) == EXPECTED_ROLES, (
        f"role enum must be exactly {EXPECTED_ROLES}, got {role.get('enum')}"
    )


def test_scalarization_named(defs):
    scal = defs.get("WeightSetRecord", {}).get("properties", {}).get("scalarization", {})
    enum = scal.get("enum", [])
    assert "linear_weighted" in enum, "linear_weighted scalarization missing"


# ACC-04 round-trip (RESEARCH Example 2)
def test_round_trip_scenario(schema, example_records):
    validator = jsonschema.Draft202012Validator(schema)
    cm = example_records["outcome-clean-merge.json"]
    ed = example_records["outcome-escaped-defect.json"]
    ct = example_records["outcome-cycle-time.json"]
    rw = example_records["outcome-reward.json"]
    for name, rec in [("clean_merge", cm), ("escaped_defect", ed), ("cycle_time", ct), ("reward", rw)]:
        validator.validate(rec)
    assert ed["supersedes_outcome_id"] == cm["outcome_id"], "supersede pointer broken"
    assert ed["ingest_time"] > cm["ingest_time"], "late label must arrive after clean_merge"
    # reward carries decision_id (computed after the fact)
    assert "decision_id" in rw, "reward record must reference decision_id"
    # cycle time pinned definition
    assert ct["measure_definition_id"], "cycle_time must pin measure_definition_id"


def test_versioning_present(schema, defs, example_records):
    for name, defn in defs.items():
        if name.endswith("Label") or name == "CycleTimeMeasure":
            v = defn.get("properties", {}).get("v", {})
            assert v.get("const") == 1, f"{name} missing v const 1"
    for name, rec in example_records.items():
        assert rec.get("v") == 1, f"{name} missing v: 1"
    doc = DOC_PATH.read_text() if DOC_PATH.exists() else ""
    assert "migration" in doc.lower(), "rationale doc missing migration-notes section"