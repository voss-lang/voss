from __future__ import annotations

import json
from pathlib import Path

from scripts.export_contract import FIXED_TOKEN
from voss.harness.server.app import create_app
from voss.harness.server.events import EventEnvelope

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
EVENT_REF_TEMPLATE = "#/components/schemas/{model}"


def _regenerate() -> tuple[str, str]:
    openapi_schema = create_app(FIXED_TOKEN).openapi()
    openapi_json = json.dumps(openapi_schema, indent=2, sort_keys=True) + "\n"

    event_schema = EventEnvelope.model_json_schema(ref_template=EVENT_REF_TEMPLATE)
    events_json = json.dumps(event_schema, indent=2, sort_keys=True) + "\n"

    return openapi_json, events_json


def test_openapi_snapshot_not_drifted() -> None:
    openapi_json, _ = _regenerate()
    committed = (CONTRACTS / "openapi.json").read_text()

    assert openapi_json == committed


def test_events_schema_not_drifted() -> None:
    _, events_json = _regenerate()
    committed = (CONTRACTS / "events.schema.json").read_text()

    assert events_json == committed


def test_drift_gate_detects_synthetic_drift() -> None:
    openapi_json, _ = _regenerate()
    committed = (CONTRACTS / "openapi.json").read_text()
    needle = '"title"'

    assert needle in openapi_json
    mutated = openapi_json.replace(needle, '"title_x"', 1)
    assert mutated != committed
