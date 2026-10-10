import json

import httpx
import pytest

from voss.harness.mcp.client import McpClient
from voss.harness.mcp.config import McpConfig, McpServerConfig, McpConfigError


@pytest.mark.asyncio
@pytest.mark.parametrize("sse", [False, True])
async def test_http_discovery_and_call_use_session_and_auth(monkeypatch, sse):
    requests = []

    def respond(request):
        requests.append(request)
        message = json.loads(request.content)
        if message["method"] == "notifications/initialized":
            return httpx.Response(202)
        if message["method"] == "initialize":
            result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}}}
        elif message["method"] == "tools/list":
            result = {"tools": [{"name": "read", "inputSchema": {"type": "object"}}]}
        else:
            result = {"content": [{"type": "text", "text": "synthetic result"}]}
        value = {"jsonrpc": "2.0", "id": message["id"], "result": result}
        if sse:
            return httpx.Response(200, headers={"content-type": "text/event-stream", "mcp-session-id": "test-session"},
                                  text="data: " + json.dumps(value) + "\n\n")
        return httpx.Response(200, json=value, headers={"mcp-session-id": "test-session"})

    original = httpx.AsyncClient
    monkeypatch.setattr("voss.harness.mcp.http.httpx.AsyncClient", lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    monkeypatch.setenv("TEST_TOKEN", "synthetic-token")
    client = McpClient(McpConfig(servers={"remote": McpServerConfig(
        url="https://example.test/mcp", bearer_token_env_var="TEST_TOKEN",
    )}))
    try:
        assert (await client.list_tools("remote"))[0]["name"] == "read"
        result = await client.call_tool("remote", "read", {})
        assert result["content"][0]["text"] == "synthetic result"
        assert requests[-1].headers["mcp-session-id"] == "test-session"
        assert requests[-1].headers["mcp-protocol-version"] == "2025-11-25"
        assert requests[-1].headers["authorization"] == "Bearer synthetic-token"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_oauth_required_is_reported_without_exposing_url(monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setattr("voss.harness.mcp.http.httpx.AsyncClient", lambda **kw: original(
        transport=httpx.MockTransport(lambda request: httpx.Response(401)), **kw,
    ))
    client = McpClient(McpConfig(servers={"remote": McpServerConfig(url="https://example.test/mcp?token=synthetic")}))
    with pytest.raises(McpConfigError, match="authentication required") as error:
        await client.list_tools("remote")
    assert "synthetic" not in str(error.value)


@pytest.mark.asyncio
async def test_transport_errors_do_not_expose_connection_details(monkeypatch):
    def fail(request):
        raise httpx.ConnectError("https://example.test/?token=synthetic-secret")

    original = httpx.AsyncClient
    monkeypatch.setattr("voss.harness.mcp.http.httpx.AsyncClient", lambda **kw: original(
        transport=httpx.MockTransport(fail), **kw,
    ))
    client = McpClient(McpConfig(servers={"remote": McpServerConfig(url="https://example.test/mcp")}))
    with pytest.raises(McpConfigError, match="transport failed") as error:
        await client.list_tools("remote")
    assert "synthetic-secret" not in str(error.value)
