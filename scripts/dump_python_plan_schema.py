"""Dump the Plan + ToolCall pydantic JSON schemas as canonical JSON.

Used by the Rust schema-parity gate
(`crates/voss-providers/tests/schema_parity.rs`) to detect drift between the
pydantic ground truth and the Rust schemars-derived schema.
"""

from __future__ import annotations

import json
import sys

from voss.harness.agent import Plan, ToolCall


def main() -> None:
    out = {
        "Plan": Plan.model_json_schema(),
        "ToolCall": ToolCall.model_json_schema(),
    }
    json.dump(out, sys.stdout, sort_keys=True, indent=2)


if __name__ == "__main__":
    main()
