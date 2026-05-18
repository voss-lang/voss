"""
LSP Client Adapter for Voss (M10-02).

Public surface uses only Voss-owned types (from .models).
pygls is an implementation detail and must never leak outside this file.

Design:
- LspClientAdapter: abstract interface used by the registry and higher layers.
- _PyglsLspClient: private implementation that talks to pygls.
- All public methods return CodeLocation / SymbolHit / ReferenceHit or structured
  error dicts like {"result": "lsp_unavailable", "language": "...", "hint": "..." }.

This module does **not** manage server processes — that is the job of LspRegistry.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import CodeLocation, ReferenceHit, SymbolHit

# ------------------------------------------------------------------
# Public Interface (never mentions pygls)
# ------------------------------------------------------------------

class LspClientAdapter(ABC):
    """Voss-owned interface for talking to a language server."""

    @abstractmethod
    async def initialize(self, root_uri: str) -> None:
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        ...

    @abstractmethod
    async def find_definition(
        self, uri: str, line: int, character: int
    ) -> list[CodeLocation] | dict[str, Any]:
        ...

    @abstractmethod
    async def find_references(
        self, uri: str, line: int, character: int
    ) -> list[ReferenceHit] | dict[str, Any]:
        ...

    @abstractmethod
    async def workspace_symbol(self, query: str) -> list[SymbolHit] | dict[str, Any]:
        ...


# ------------------------------------------------------------------
# Private pygls-backed implementation
# (All pygls imports must stay inside this block / this file only)
# ------------------------------------------------------------------

try:
    from pygls.client import JsonRPCClient
    from pygls.protocol import LanguageServerProtocol
    from pygls.uris import from_fs_path, to_fs_path
    _PYGLS_AVAILABLE = True
except ImportError:
    JsonRPCClient = None  # type: ignore
    LanguageServerProtocol = None  # type: ignore
    _PYGLS_AVAILABLE = False


class _PyglsLspClient(LspClientAdapter):
    """Concrete adapter that talks to a language server via pygls."""

    def __init__(self, language: str):
        self.language = language
        self._client: Any = None
        self._initialized = False

    async def initialize(self, root_uri: str) -> None:
        if not _PYGLS_AVAILABLE:
            return

        # We expect the caller (registry) to have already started the server
        # process and wired its stdin/stdout to us.
        # For now this is a stub that will be driven by the registry.
        self._initialized = True

    async def shutdown(self) -> None:
        if self._client is not None:
            try:
                await self._client.shutdown()
                await self._client.exit()
            except Exception:
                pass
        self._initialized = False

    async def find_definition(
        self, uri: str, line: int, character: int
    ) -> list[CodeLocation] | dict[str, Any]:
        if not self._initialized or not _PYGLS_AVAILABLE:
            return self._unavailable()

        # Placeholder – real implementation will call the pygls client
        # and convert results to CodeLocation.
        return []

    async def find_references(
        self, uri: str, line: int, character: int
    ) -> list[ReferenceHit] | dict[str, Any]:
        if not self._initialized or not _PYGLS_AVAILABLE:
            return self._unavailable()
        return []

    async def workspace_symbol(self, query: str) -> list[SymbolHit] | dict[str, Any]:
        if not self._initialized or not _PYGLS_AVAILABLE:
            return self._unavailable()
        return []

    def _unavailable(self) -> dict[str, Any]:
        return {
            "result": "lsp_unavailable",
            "language": self.language,
            "fallback": "ast-grep",
            "hint": f"Install a language server for {self.language}",
        }


def create_lsp_client(language: str) -> LspClientAdapter:
    """Factory that returns the best available adapter for the language."""
    return _PyglsLspClient(language)


# ------------------------------------------------------------------
# Convenience: check whether we can even attempt LSP for a language
# ------------------------------------------------------------------

def is_lsp_available(language: str) -> bool:
    """Lightweight check used by the registry before spawning."""
    # In a real implementation this would also consult config to see if
    # the language is disabled.
    return _PYGLS_AVAILABLE
