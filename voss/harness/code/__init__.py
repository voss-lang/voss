"""voss.harness.code — Code intelligence subsystem (M10).

This package provides the project index, LSP-backed semantic search,
ast-grep structural search, and related surfaces. It is intentionally
lazy: importing submodules does not require pygls or ast-grep to be
installed (those live only under the optional `voss[code]` extra).

Public surface is re-exported here for convenience.
"""

from __future__ import annotations

# Models are always importable (pure data)
from .models import (
    CodeLocation,
    IndexSummary,
    ReferenceHit,
    SearchHit,
    SymbolHit,
)

__all__ = [
    "CodeLocation",
    "IndexSummary",
    "ReferenceHit",
    "SearchHit",
    "SymbolHit",
]

# config is importable without the heavy deps
from . import config as config  # noqa: F401
