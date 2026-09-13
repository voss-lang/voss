from __future__ import annotations

import json
import urllib.error
from dataclasses import dataclass

import pytest

from voss.harness.memory_api_client import (
    MemoryApiClient,
    MemoryApiConfigurationError,
    MemoryApiError,
    MemoryApiRedirectError,
    MemoryApiResponse,
    MemoryApiUnavailableError,
)


@dataclass
class FakeOpener:
    response: object

    def __post_init__(self) -> None:
        self.requests: list[tuple[object, float]] = []

    def open(self, request, *, timeout: float):
        self.requests.append((request, timeout))
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


def response(payload: object, *, status: int = 200) -> MemoryApiResponse:
    return MemoryApiResponse(status, json.dumps(payload).encode())


def test_health_uses_unauthenticated_request_and_bounded_timeout() -> None:
    opener = FakeOpener(response({"api_version": 1, "status": "ready"}))
    client = MemoryApiClient("http://127.0.0.1:8765", "secret", timeout=2.5, opener=opener)

    assert client.health() == {"api_version": 1, "status": "ready"}
    request, timeout = opener.requests[0]
    assert request.full_url == "http://127.0.0.1:8765/v1/health"
    assert request.get_header("Authorization") is None
    assert timeout == 2.5


def test_create_memory_sends_contract_body_and_idempotency_key() -> None:
    opener = FakeOpener(
        response(
            {
                "data": {
                    "id": "m-1",
                    "project_id": "demo",
                    "kind": "note",
                    "body": "remember",
                }
            },
            status=201,
        )
    )
    client = MemoryApiClient("http://localhost:9000/", "token", opener=opener)

    record = client.create_memory(
        "demo",
        "note",
        "remember",
        provenance={"session_id": "s1"},
        idempotency_key="request-1",
    )

    assert record["id"] == "m-1"
    request, _ = opener.requests[0]
    assert request.full_url == "http://localhost:9000/v1/projects/demo/memories"
    assert request.get_header("Authorization") == "Bearer token"
    assert request.get_header("Idempotency-key") == "request-1"
    assert json.loads(request.data) == {
        "kind": "note",
        "body": "remember",
        "provenance": {"session_id": "s1"},
    }


def test_explicit_empty_idempotency_key_is_rejected() -> None:
    client = MemoryApiClient("http://127.0.0.1:9000", "token", opener=FakeOpener(response({})))

    with pytest.raises(ValueError):
        client.create_memory("demo", "note", "remember", idempotency_key="")


@pytest.mark.parametrize(
    "url",
    [
        "https://example.test",
        "http://127.0.0.1:8000/v1",
        "http://user:password@127.0.0.1:8000",
        "http://127.0.0.1:8000/?token=secret",
        "http://127.0.0.1:not-a-port",
    ],
)
def test_base_url_must_be_loopback_without_credentials_or_version(url: str) -> None:
    with pytest.raises(MemoryApiConfigurationError):
        MemoryApiClient(url, "token")


def test_missing_token_denies_authenticated_routes_but_health_can_probe() -> None:
    opener = FakeOpener(response({"api_version": 1, "status": "ready"}))
    client = MemoryApiClient("http://127.0.0.1:8765", None, opener=opener)

    assert client.health()["status"] == "ready"
    with pytest.raises(MemoryApiConfigurationError):
        client.search("demo", "query")
    assert len(opener.requests) == 1


def test_error_messages_redact_bearer_and_do_not_include_url() -> None:
    opener = FakeOpener(
        response(
            {"error": {"code": "unauthorized", "message": "Bearer secret-token denied"}},
            status=401,
        )
    )
    client = MemoryApiClient("http://127.0.0.1:8765", "secret-token", opener=opener)

    with pytest.raises(MemoryApiError) as raised:
        client.search("demo", "query")

    assert raised.value.status == 401
    assert raised.value.code == "unauthorized"
    assert "secret-token" not in str(raised.value)
    assert "127.0.0.1" not in str(raised.value)


def test_redirects_are_reported_without_following() -> None:
    opener = FakeOpener(MemoryApiResponse(302, b""))
    client = MemoryApiClient("http://127.0.0.1:8765", "token", opener=opener)

    with pytest.raises(MemoryApiRedirectError):
        client.search("demo", "query")
    assert len(opener.requests) == 1


@pytest.mark.parametrize("exc", [TimeoutError(), urllib.error.URLError("offline")])
def test_transport_failures_are_explicit_unavailable_errors(exc: BaseException) -> None:
    client = MemoryApiClient(
        "http://127.0.0.1:8765", "token", opener=FakeOpener(exc), timeout=1
    )

    with pytest.raises(MemoryApiUnavailableError):
        client.search("demo", "query")


def test_default_opener_disables_proxy_and_redirect_handlers() -> None:
    client = MemoryApiClient("http://127.0.0.1:8765", "token")
    handler_names = {type(handler).__name__ for handler in client._opener.handlers}

    assert "ProxyHandler" not in handler_names
    assert "_NoRedirect" in handler_names
