"""`voss serve` runtime (HYBRID-REFACTOR-PLAN H1.11 + H1.12).

Binds an ephemeral loopback port, prints the `{port, token}` handshake line
to stdout (race-free: bind before serve), then runs uvicorn. Self-terminates
when its parent process dies (getppid poll + stdin-EOF fallback) so a dropped
client never leaves a zombie server — macOS has no PR_SET_PDEATHSIG.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import signal
import socket
import sys
import threading


async def _watch_parent(orig_ppid: int) -> None:
    while True:
        await asyncio.sleep(2)
        if os.getppid() != orig_ppid:
            os.kill(os.getpid(), signal.SIGTERM)
            return


def _watch_stdin_eof() -> None:
    """Block on stdin; on EOF (parent/pipe closed) terminate. Daemon thread."""
    try:
        for _ in sys.stdin:
            pass
    except Exception:
        pass
    os.kill(os.getpid(), signal.SIGTERM)


def run_server(host: str = "127.0.0.1", port: int = 0, token: str | None = None) -> None:
    import uvicorn

    from .app import create_app

    token = token or secrets.token_urlsafe(32)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    chosen_port = sock.getsockname()[1]

    app = create_app(token)

    # Handshake line — the client reads exactly this to discover port + token.
    print(json.dumps({"v": 1, "port": chosen_port, "token": token}), flush=True)

    # stdin-EOF heartbeat only when stdin is piped (client supervises us);
    # skip for an interactive terminal so manual `voss serve` doesn't exit on
    # a stray newline.
    if not sys.stdin.isatty():
        threading.Thread(target=_watch_stdin_eof, daemon=True).start()

    config = uvicorn.Config(app, log_level="warning")
    server = uvicorn.Server(config)

    async def _serve() -> None:
        asyncio.create_task(_watch_parent(os.getppid()))
        await server.serve(sockets=[sock])

    asyncio.run(_serve())
