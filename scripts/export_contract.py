"""Export deterministic API and event contracts for SDK code generation."""

from __future__ import annotations

import json
from pathlib import Path

from voss.harness.server.app import create_app
from voss.harness.server.events import EventEnvelope

FIXED_TOKEN = "voss-contract-export-fixed-token-v1"


def main() -> None:
    contracts_dir = Path(__file__).resolve().parents[1] / "contracts"
    contracts_dir.mkdir(exist_ok=True)

    openapi_schema = create_app(FIXED_TOKEN).openapi()
    (contracts_dir / "openapi.json").write_text(
        json.dumps(openapi_schema, indent=2, sort_keys=True) + "\n"
    )

    event_schema = EventEnvelope.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    (contracts_dir / "events.schema.json").write_text(
        json.dumps(event_schema, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
