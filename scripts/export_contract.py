"""Export deterministic API and event contracts for SDK code generation."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "1")

from voss.harness.server.app import create_app
from voss.harness.server.events import EventEnvelope

FIXED_TOKEN = "voss-contract-export-fixed-token-v1"
EVENT_REF_TEMPLATE = "#/components/schemas/{model}"


def require_event_discriminators(schema: dict) -> dict:
    """Make Pydantic event variants typify-compatible.

    Pydantic emits the discriminator field as a const/default property but does
    not mark it required. typify needs `type` in `required` to generate
    `#[serde(tag = "type")]` instead of `#[serde(untagged)]`.
    """
    defs = schema.get("$defs", {})
    for definition in defs.values():
        _require_type_if_discriminated(definition)

    components = schema.get("components", {}).get("schemas", {})
    for definition in components.values():
        _require_type_if_discriminated(definition)

    return schema


def _require_type_if_discriminated(definition: dict) -> None:
    properties = definition.get("properties", {})
    type_property = properties.get("type", {})
    if "const" not in type_property:
        return

    required = definition.setdefault("required", [])
    if "type" not in required:
        required.append("type")


def main() -> None:
    contracts_dir = Path(__file__).resolve().parents[1] / "contracts"
    contracts_dir.mkdir(exist_ok=True)

    openapi_schema = require_event_discriminators(create_app(FIXED_TOKEN).openapi())
    (contracts_dir / "openapi.json").write_text(
        json.dumps(openapi_schema, indent=2, sort_keys=True) + "\n"
    )

    event_schema = EventEnvelope.model_json_schema(
        ref_template=EVENT_REF_TEMPLATE
    )
    event_schema = require_event_discriminators(event_schema)
    (contracts_dir / "events.schema.json").write_text(
        json.dumps(event_schema, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
