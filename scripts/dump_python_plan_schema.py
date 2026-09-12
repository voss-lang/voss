"""
Dump the Plan + ToolCall pydantic JSON schemas as canonical JSON.
Used by the Rust schema-parity gate
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
