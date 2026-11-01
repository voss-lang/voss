from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from voss.harness.server import app as appmod


def _preflight(origin: str):
    c = TestClient(appmod.create_app("cors-test-token"))
    return c.options(
        "/capabilities",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET",
                 "Access-Control-Request-Headers": "authorization"},
    )


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:8080", "http://[::1]:3000"])
def test_loopback_browser_origins_pass_preflight(origin) -> None:
    r = _preflight(origin)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", ["tauri://localhost", "https://tauri.localhost", "https://example.com"])
def test_other_origins_are_refused(origin) -> None:
    r = _preflight(origin)
    assert "access-control-allow-origin" not in r.headers
