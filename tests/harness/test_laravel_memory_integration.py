from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from voss.harness.memory_api_client import (
    MemoryApiClient,
    MemoryApiError,
    MemoryApiUnavailableError,
)
from voss.harness.server import app as appmod
from voss.harness.tools import attach_memory_tools


pytestmark = pytest.mark.integration

_MEMORY_TOKEN = "synthetic-memory-token-for-tests"
_HARNESS_TOKEN = "synthetic-harness-token-for-tests"


@pytest.fixture(autouse=True)
def disable_local_semantic_index(monkeypatch: pytest.MonkeyPatch) -> None:
    from voss.harness.memory_store import MemoryStore

    monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda self: None)


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _service_env(database: Path, token: str) -> dict[str, str]:
    blocked_fragments = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(fragment in key.upper() for fragment in blocked_fragments)
    }
    env.update(
        {
            "APP_ENV": "testing",
            "APP_DEBUG": "false",
            "APP_KEY": "",
            "APP_URL": "http://127.0.0.1",
            "CACHE_STORE": "array",
            "DB_CONNECTION": "sqlite",
            "DB_DATABASE": str(database),
            "FILESYSTEM_DISK": "local",
            "LOG_CHANNEL": "stderr",
            "MAIL_MAILER": "array",
            "QUEUE_CONNECTION": "sync",
            "SESSION_DRIVER": "array",
            "VOSS_MEMORY_API_TOKEN": token,
        }
    )
    return env


def _safe_process_output(path: Path, token: str) -> str:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return ""
    return text.replace(token, "<synthetic-token>")[-8000:]


@dataclass
class _LaravelService:
    root: Path
    database: Path
    token: str
    php: str
    port: int
    environment: dict[str, str]
    log_path: Path
    process: subprocess.Popen[bytes]

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def client(self) -> MemoryApiClient:
        return MemoryApiClient(self.base_url, self.token, timeout=3.0)

    def stop(self) -> None:
        pid = self.process.pid
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait(timeout=5)

    def restart(self) -> None:
        self.stop()
        self.process = _start_process(
            self.root,
            self.php,
            self.port,
            self.environment,
            self.log_path,
        )
        _wait_until_ready(self)


def _start_process(
    root: Path,
    php: str,
    port: int,
    environment: dict[str, str],
    log_path: Path,
) -> subprocess.Popen[bytes]:
    log = log_path.open("ab")
    try:
        return subprocess.Popen(
            [php, "artisan", "serve", "--host=127.0.0.1", f"--port={port}"],
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        log.close()


def _wait_until_ready(service: _LaravelService) -> None:
    deadline = time.monotonic() + 20
    client = service.client()
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        if service.process.poll() is not None:
            output = _safe_process_output(service.log_path, service.token)
            raise AssertionError(
                f"Laravel service exited with {service.process.returncode}:\n{output}"
            )
        try:
            assert client.health() == {"api_version": 1, "status": "ready"}
        except (AssertionError, MemoryApiError, OSError) as exc:
            last_error = exc
            time.sleep(0.1)
            continue
        return
    output = _safe_process_output(service.log_path, service.token)
    raise AssertionError(f"Laravel health did not become ready: {last_error}\n{output}")


@pytest.fixture(scope="module")
def laravel_service(tmp_path_factory: pytest.TempPathFactory) -> Any:
    php = shutil.which("php")
    if php is None:
        pytest.skip("php is unavailable; Laravel integration tests require PHP")

    root = Path(__file__).resolve().parents[2] / "services" / "memory-api"
    if not (root / "artisan").exists():
        pytest.skip("services/memory-api is unavailable")
    if not (root / "vendor" / "autoload.php").exists():
        pytest.skip("Laravel dependencies are not installed")

    runtime = tmp_path_factory.mktemp("laravel-memory-runtime")
    database = runtime / "memory.sqlite"
    database.touch()
    environment = _service_env(database, _MEMORY_TOKEN)
    migration = subprocess.run(
        [php, "artisan", "migrate:fresh", "--force"],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if migration.returncode != 0:
        details = (migration.stdout + migration.stderr).replace(
            _MEMORY_TOKEN, "<synthetic-token>"
        )
        raise AssertionError(f"Laravel migrations failed ({migration.returncode}):\n{details}")

    port = _free_loopback_port()
    service = _LaravelService(
        root=root,
        database=database,
        token=_MEMORY_TOKEN,
        php=php,
        port=port,
        environment=environment,
        log_path=runtime / "server.log",
        process=None,  # type: ignore[arg-type]
    )
    service.process = _start_process(root, php, port, environment, service.log_path)
    try:
        _wait_until_ready(service)
        yield service
    finally:
        service.stop()


@dataclass(frozen=True)
class _Project:
    root: Path
    project_id: str
    client: MemoryApiClient
    service: _LaravelService


@pytest.fixture
def laravel_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    laravel_service: _LaravelService,
) -> _Project:
    project_id = f"pytest-{uuid.uuid4().hex[:16]}"
    (tmp_path / ".voss").mkdir()
    (tmp_path / ".voss" / "config.yml").write_text(
        "memory:\n"
        "  retained_backend: laravel\n"
        f"  service_project: {project_id}\n"
    )
    monkeypatch.setenv("VOSS_MEMORY_API_URL", laravel_service.base_url)
    monkeypatch.setenv("VOSS_MEMORY_API_TOKEN", laravel_service.token)
    client = laravel_service.client()
    registered = client.register_project(project_id, name="Synthetic integration project")
    assert registered == {"id": project_id, "name": "Synthetic integration project"}
    return _Project(tmp_path, project_id, client, laravel_service)


def _raw_json_request(
    url: str,
    *,
    method: str,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return int(response.status), json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return int(exc.code), json.loads(exc.read().decode())


def test_real_health_is_public_but_project_routes_require_bearer(
    laravel_project: _Project,
) -> None:
    service = laravel_project.service
    assert laravel_project.client.health() == {"api_version": 1, "status": "ready"}

    status, payload = _raw_json_request(
        f"{service.base_url}/v1/projects",
        method="POST",
        payload={"id": "unauthorized-project"},
    )
    assert status == 401
    assert set(payload) == {"error"}
    assert isinstance(payload["error"]["code"], str)
    assert isinstance(payload["error"]["message"], str)

    status, payload = _raw_json_request(
        f"{service.base_url}/v1/projects",
        method="POST",
        token="wrong-synthetic-token",
        payload={"id": "unauthorized-project"},
    )
    assert status == 401
    assert isinstance(payload["error"]["code"], str)
    assert isinstance(payload["error"]["message"], str)
    assert _MEMORY_TOKEN not in json.dumps(payload)


def test_python_client_covers_idempotency_scope_search_and_revision_conflicts(
    laravel_project: _Project,
) -> None:
    project = laravel_project
    body = "SQLite retained memory preserves snake_case symbols for this synthetic project."
    created = project.client.create_memory(
        project.project_id,
        "note",
        body,
        provenance={"source": "synthetic-test", "session_id": "session-1"},
        idempotency_key="create-note-1",
    )
    replayed = project.client.create_memory(
        project.project_id,
        "note",
        body,
        provenance={"source": "synthetic-test", "session_id": "session-1"},
        idempotency_key="create-note-1",
    )
    assert replayed == created
    assert created["revision"] == 1
    assert created["pinned"] is False
    assert created["status"] == "active"
    assert created["provenance"]["source"] == "synthetic-test"

    with pytest.raises(MemoryApiError) as conflict:
        project.client.create_memory(
            project.project_id,
            "note",
            "different synthetic payload",
            idempotency_key="create-note-1",
        )
    assert conflict.value.status == 409

    other_project = f"other-{uuid.uuid4().hex[:16]}"
    assert project.client.register_project(other_project, name="Other synthetic project")["id"] == other_project
    with pytest.raises(MemoryApiError) as cross_project:
        project.client.get_memory(other_project, created["id"])
    assert cross_project.value.status == 404

    hits = project.client.search(project.project_id, "snake_case symbols", top_k=5)
    assert hits
    assert hits[0]["id"] == created["id"]
    assert hits[0]["project_id"] == project.project_id
    assert hits[0]["status"] == "active"
    assert isinstance(hits[0]["score"], (int, float))

    pinned = project.client.patch_memory(
        project.project_id,
        created["id"],
        expected_revision=1,
        pinned=True,
        idempotency_key="pin-note-1",
    )
    assert pinned["revision"] == 2
    assert pinned["pinned"] is True
    assert project.client.patch_memory(
        project.project_id,
        created["id"],
        expected_revision=1,
        pinned=True,
        idempotency_key="pin-note-1",
    ) == pinned

    revised = project.client.patch_memory(
        project.project_id,
        created["id"],
        expected_revision=2,
        body="Revised synthetic snake_case symbols memory.",
        idempotency_key="revise-note-1",
    )
    assert revised["revision"] == 3
    assert revised["pinned"] is True
    with pytest.raises(MemoryApiError) as stale:
        project.client.patch_memory(
            project.project_id,
            created["id"],
            expected_revision=1,
            pinned=True,
            idempotency_key="pin-note-1",
        )
    assert stale.value.status == 409
    assert stale.value.code == "stale_replay"

    replacement = project.client.create_memory(
        project.project_id,
        "convention",
        "Synthetic replacement convention for supersession.",
        idempotency_key="create-replacement-1",
    )
    superseded = project.client.patch_memory(
        project.project_id,
        created["id"],
        expected_revision=3,
        superseded_by=replacement["id"],
        idempotency_key="supersede-note-1",
    )
    assert superseded["status"] == "superseded"
    assert superseded["pinned"] is False
    assert superseded["superseded_by"] == replacement["id"]
    active = project.client.list_memories(project.project_id)
    assert created["id"] not in {item["id"] for item in active["data"]}
    assert replacement["id"] in {item["id"] for item in active["data"]}


def test_python_client_forget_removes_search_and_persists_across_restart(
    laravel_project: _Project,
) -> None:
    project = laravel_project
    created = project.client.create_memory(
        project.project_id,
        "decision",
        "Synthetic deletion marker for restart verification.",
        idempotency_key="create-delete-1",
    )
    deleted = project.client.delete_memory(
        project.project_id,
        created["id"],
        expected_revision=1,
        idempotency_key="delete-memory-1",
    )
    assert deleted == {"id": created["id"], "revision": 2, "status": "deleted"}
    replayed = project.client.delete_memory(
        project.project_id,
        created["id"],
        expected_revision=1,
        idempotency_key="delete-memory-1",
    )
    assert replayed == deleted
    with pytest.raises(MemoryApiError) as deleted_replay:
        project.client.create_memory(
            project.project_id,
            "decision",
            "Synthetic deletion marker for restart verification.",
            idempotency_key="create-delete-1",
        )
    assert deleted_replay.value.status == 409
    assert deleted_replay.value.code == "memory_deleted"
    with pytest.raises(MemoryApiError) as missing:
        project.client.get_memory(project.project_id, created["id"])
    assert missing.value.status == 404
    assert all(item["id"] != created["id"] for item in project.client.search(project.project_id, "deletion marker"))

    survivor = project.client.create_memory(
        project.project_id,
        "convention",
        "Synthetic convention survives a service process restart.",
        idempotency_key="create-survivor-1",
    )
    project.service.restart()
    restored = project.client.get_memory(project.project_id, survivor["id"])
    assert restored == survivor


def test_gateway_save_pin_and_fastapi_memory_route_share_remote_record(
    laravel_project: _Project,
) -> None:
    from voss.harness.memory_gateway import MemoryGateway, open_memory_store

    project = laravel_project
    gateway = open_memory_store(project.root, session_id="synthetic-session")
    assert isinstance(gateway, MemoryGateway)
    tools: dict[str, Any] = {}
    attach_memory_tools(tools, store=gateway, session_id="synthetic-session")

    body = "Synthetic gateway note is visible through FastAPI and remote pins."
    remembered = asyncio.run(tools["memory_remember"].invoke(text=body))
    prefix = f"remembered: memory:{project.project_id}:"
    assert remembered.startswith(prefix)
    memory_id = remembered[len(prefix):]
    record = project.client.get_memory(project.project_id, memory_id)
    assert record["body"] == body
    assert record["provenance"]["session_id"] == "synthetic-session"

    project.client.patch_memory(
        project.project_id,
        memory_id,
        expected_revision=record["revision"],
        pinned=True,
        idempotency_key="gateway-pin-1",
    )
    pinned_text = gateway.render_pinned_memory_text(model="synthetic-model")
    assert body in pinned_text
    assert not list((project.root / ".voss" / "memory" / "notes").glob("*.md"))

    with TestClient(appmod.create_app(_HARNESS_TOKEN)) as fastapi:
        response = fastapi.get(
            "/memory",
            params={"cwd": str(project.root), "q": "gateway FastAPI remote pins", "top_k": 5},
            headers={"Authorization": f"Bearer {_HARNESS_TOKEN}"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"].startswith(f"Backend: laravel (project {project.project_id})")
    hit = next(item for item in payload["hits"] if item["locator"] == f"memory:{project.project_id}:{memory_id}")
    assert hit["source"] == "notes"
    assert body in hit["excerpt"]


def test_gateway_surfaces_service_outage_without_local_note_fallback(
    laravel_project: _Project,
) -> None:
    from voss.harness.memory_gateway import MemoryGateway, open_memory_store

    project = laravel_project
    gateway = open_memory_store(project.root, session_id="synthetic-outage-session")
    assert isinstance(gateway, MemoryGateway)
    notes_dir = project.root / ".voss" / "memory" / "notes"
    body = "Synthetic outage must not be written locally."

    project.service.stop()
    try:
        with pytest.raises(MemoryApiUnavailableError) as unavailable:
            gateway.write_note(body)
        assert unavailable.value.code == "unavailable"
        assert not list(notes_dir.glob("*.md"))
    finally:
        project.service.restart()
    assert all(
        item["body"] != body
        for item in project.client.list_memories(project.project_id)["data"]
    )
