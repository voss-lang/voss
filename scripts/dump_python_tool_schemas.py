"""Dump the parameter JSON schemas for each Python tool descriptor.

Used by the Rust tool-schema parity gate
(`crates/voss-tools/tests/schema_parity.rs`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from voss.harness.tools import make_toolset


def main() -> None:
    cwd = Path.cwd()
    toolset = make_toolset(cwd)
    out: dict[str, dict] = {}
    for name, td in toolset.items():
        params = getattr(td, "parameters", None) or {}
        out[name] = {
            "description": getattr(td, "description", "") or "",
            "parameters": params,
        }
    json.dump(out, sys.stdout, sort_keys=True, indent=2)


if __name__ == "__main__":
    main()
