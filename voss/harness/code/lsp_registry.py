"""
LspRegistry – lazy, well-behaved language server management for M10.
"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from .config import LspServerConfig, load_lsp_config
from .lsp import LspClientAdapter, create_lsp_client, is_lsp_available
from .models import CodeLocation, ReferenceHit

try:
    from voss.harness import lifecycle
except Exception:
    lifecycle = None  # type: ignore


class LspRegistry:
    """Manages one language server per language for a session."""

    def __init__(self, cwd: Path, session_id: str = "default"):
        self.cwd = cwd
        self.session_id = session_id
        self._clients: dict[str, LspClientAdapter] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._config = load_lsp_config(cwd)

    async def _spawn(self, cfg: LspServerConfig) -> asyncio.subprocess.Process | None:
        cmd = shutil.which(cfg.command[0])
        if not cmd:
            return None

        full_cmd = [cmd] + cfg.args
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.cwd),
            )
            if lifecycle is not None:
                try:
                    lifecycle.register_subprocess(proc)
                except Exception:
                    pass
            return proc
        except Exception:
            return None

    async def get_adapter(self, language: str) -> LspClientAdapter | dict[str, Any]:
        if language not in self._config.servers:
            return self._make_unavailable(language, "not configured")

        server_cfg = self._config.servers[language]
        if server_cfg.disabled:
            return self._make_unavailable(language, "disabled")

        if language in self._clients:
            return self._clients[language]

        if not is_lsp_available():
            return self._make_unavailable(language, "LSP client library not available")

        proc = await self._spawn(server_cfg)
        if proc is None:
            return self._make_unavailable(language, "failed to start server")

        adapter = create_lsp_client(language)
        try:
            if hasattr(adapter, "connect"):
                await adapter.connect(proc)
            await adapter.initialize(str(self.cwd.as_uri()))
            self._clients[language] = adapter
            self._processes[language] = proc
            return adapter
        except Exception as exc:
            try:
                proc.terminate()
            except Exception:
                pass
            return self._make_unavailable(language, f"initialize failed: {exc}")

    async def find_definition(
        self, language: str, uri: str, line: int, character: int
    ) -> list[CodeLocation] | dict[str, Any]:
        adapter = await self.get_adapter(language)
        if isinstance(adapter, dict):
            return adapter
        return await adapter.find_definition(uri, line, character)

    async def find_references(
        self, language: str, uri: str, line: int, character: int
    ) -> list[ReferenceHit] | dict[str, Any]:
        adapter = await self.get_adapter(language)
        if isinstance(adapter, dict):
            return adapter
        return await adapter.find_references(uri, line, character)

    async def shutdown_all(self) -> None:
        for lang, adapter in list(self._clients.items()):
            try:
                await adapter.shutdown()
            except Exception:
                pass
            if lang in self._processes:
                try:
                    self._processes[lang].terminate()
                    await asyncio.wait_for(self._processes[lang].wait(), timeout=1.5)
                except Exception:
                    try:
                        self._processes[lang].kill()
                    except Exception:
                        pass
        self._clients.clear()
        self._processes.clear()

    def _make_unavailable(self, language: str, reason: str) -> dict[str, Any]:
        cfg = self._config.servers.get(language)
        hint = f"command: {cfg.command}" if cfg else ""
        return {
            "result": "lsp_unavailable",
            "language": language,
            "reason": reason,
            "fallback": "ast-grep",
            "hint": hint,
        }
