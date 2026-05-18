"""
LspRegistry – lazy per-language language server management (M10-02 Task 2).

Responsibilities:
- Own one LspClientAdapter per (language, session/cwd)
- Lazy start: only spawn the server process on first actual request
- Register the subprocess with voss.harness.lifecycle for clean reaping
- Return structured `lsp_unavailable` envelopes when a server is missing or disabled
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .config import load_lsp_config
from .lsp import LspClientAdapter, create_lsp_client, is_lsp_available
from .models import CodeLocation, ReferenceHit

# We will import register_subprocess from lifecycle when we actually spawn


class LspRegistry:
    """Session-scoped registry of language servers."""

    def __init__(self, cwd: Path, session_id: str):
        self.cwd = cwd
        self.session_id = session_id
        self._clients: dict[str, LspClientAdapter] = {}
        self._config = load_lsp_config(cwd)

    async def get_client(self, language: str) -> LspClientAdapter | dict[str, Any]:
        """Return a ready client or a structured unavailable result."""
        if language not in self._config.servers:
            return self._unavailable(language, "unknown language in config")

        server_cfg = self._config.servers[language]
        if server_cfg.disabled:
            return self._unavailable(language, "disabled in .voss/lsp.yml")

        if not is_lsp_available(language):
            return self._unavailable(language, "pygls not installed (pip install voss[code])")

        if language not in self._clients:
            client = create_lsp_client(language)
            # TODO in Task 2: actually spawn the process from server_cfg.command + args
            # and wire it to the client, then register the Process with lifecycle.
            self._clients[language] = client

        return self._clients[language]

    async def find_definition(
        self, language: str, uri: str, line: int, character: int
    ) -> list[CodeLocation] | dict[str, Any]:
        client_or_error = await self.get_client(language)
        if isinstance(client_or_error, dict):
            return client_or_error
        return await client_or_error.find_definition(uri, line, character)

    # Similar wrappers for find_references, etc. will be added.

    def _unavailable(self, language: str, reason: str) -> dict[str, Any]:
        cfg = self._config.servers.get(language)
        hint = ""
        if cfg:
            hint = f"Try: {' '.join(cfg.command)}"
        return {
            "result": "lsp_unavailable",
            "language": language,
            "reason": reason,
            "fallback": "ast-grep",
            "hint": hint,
        }

    async def shutdown_all(self) -> None:
        for client in self._clients.values():
            try:
                await client.shutdown()
            except Exception:
                pass
        self._clients.clear()
