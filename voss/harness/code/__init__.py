"""
voss.harness.code Code intelligence subsystem
This package provides the project index, LSP-backed semantic search
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
