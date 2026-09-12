"""Drift gate: regenerate contracts in memory and diff against committed files."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_contract import (
    generate_events_json,
    generate_observe_events_json,
    generate_openapi_json,
)

CONTRACTS = ROOT / "contracts"


def main() -> int:
    generated = {
        "openapi.json": generate_openapi_json,
        "events.schema.json": generate_events_json,
        "observe-events.schema.json": generate_observe_events_json,
    }
    drifted = []
    for name, generate in generated.items():
        path = CONTRACTS / name
        if not path.exists() or path.read_text() != generate():
            drifted.append(name)
    if drifted:
        print("contract drift detected: " + ", ".join(drifted))
        print("regenerate with: python scripts/export_contract.py")
        return 1
    print("contracts up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
