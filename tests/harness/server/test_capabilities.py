from fastapi.testclient import TestClient

from voss.harness.server import app as appmod


def test_capabilities_require_transport_auth_but_no_provider_login(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def unexpected(*args, **kwargs):
        raise AssertionError("capability discovery must not resolve provider credentials")

    monkeypatch.setattr(appmod, "_resolve_provider", unexpected)
    monkeypatch.setattr(appmod.auth_mod, "resolve", unexpected)
    app = appmod.create_app("synthetic-capabilities-token")
    client = TestClient(app)
    assert client.get("/capabilities").status_code == 401
    response = client.get(
        "/capabilities", headers={"Authorization": "Bearer synthetic-capabilities-token"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["v"] == 1
    assert body["engine_version"]
    assert set(body["capabilities"]) == {"sessions.v1", "swarms.v1", "diagnostics.v1", "tasks.replay.v1", "tasks.graph.v1", "harness.availability.v1"}
    assert app.state.sessions.list() == []
    assert not list(tmp_path.iterdir())
