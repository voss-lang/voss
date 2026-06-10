"""Shared server-lifecycle helper for the V17 bus test scaffold (V15-gated).

`bus_server_env` runs the harness FastAPI app (which V17-05 extends with
POST /bus/send, GET /bus/inbox, GET /bus/events) on a loopback port inside
the given cwd, yielding the discovery env (`VOSS_SERVER_PORT` /
`VOSS_SERVER_TOKEN`) the bus verbs resolve. Restartable: each `with` block
is one server lifetime over the same `.voss/bus/` journal (D-10 durability).
"""
from __future__ import annotations

import contextlib
import os
import socket
import threading
import time
from pathlib import Path
from typing import Iterator

BUS_TEST_TOKEN = "bus-test-token"


@contextlib.contextmanager
def bus_server_env(cwd: Path) -> Iterator[dict[str, str]]:
    import uvicorn

    from voss.harness.server.app import create_app

    app = create_app(token=BUS_TEST_TOKEN)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)

    prev_cwd = os.getcwd()
    os.chdir(cwd)  # journal lands under <cwd>/.voss/bus/ (D-10)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("bus test server did not start within 10s")
            time.sleep(0.05)
        yield {
            "VOSS_SERVER_PORT": str(port),
            "VOSS_SERVER_TOKEN": BUS_TEST_TOKEN,
        }
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        os.chdir(prev_cwd)
