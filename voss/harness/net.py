"""NetSession owns the shared httpx.AsyncClient + per-tool TokenBucket
registry + telemetry emit wrappers for net.request / net.response
(T3-05, NET-01).

Lifecycle: __init__ registers self with lifecycle.register_session so
reap_all() awaits aclose() at interpreter shutdown. The httpx client is
lazily constructed (mirrors providers.py) so test-import never opens a
socket.
"""

from __future__ import annotations

import math
import os
import time
import warnings

import httpx

from voss.harness import lifecycle, telemetry
from voss.harness.rate_limit import DEFAULT_SPECS, TokenBucket, make_default_bucket
from voss.harness.web_search import BraveBackend, SearchResult, render_bundle

MAX_BYTES = 1_048_576  # 1 MB cap per NET-01 SPEC
MIN_TIMEOUT = 1.0
MAX_TIMEOUT = 120.0
DEFAULT_TIMEOUT = 30.0


class NetSession:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        rate_overrides: dict[str, dict[str, int]] | None = None,
    ) -> None:
        self._client: httpx.AsyncClient | None = client
        self._brave_backend: BraveBackend | None = None
        self._brave_api_key: str | None = None
        self._buckets: dict[str, TokenBucket] = {}
        for tool_name in DEFAULT_SPECS:
            override = (rate_overrides or {}).get(tool_name)
            if override is not None:
                self._buckets[tool_name] = TokenBucket(
                    rate_per_min=override["rate"], burst=override["burst"]
                )
            else:
                self._buckets[tool_name] = make_default_bucket(tool_name)
        lifecycle.register_session(self)

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                follow_redirects=True,
                max_redirects=5,
                verify=True,
                timeout=httpx.Timeout(DEFAULT_TIMEOUT),
                http2=False,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def acquire(self, tool_name: str) -> tuple[bool, float]:
        # MCP namespaced names (server__tool) bypass the bucket entirely
        # per D-16 + NET-07e.
        if "__" in tool_name:
            return True, 0.0
        bucket = self._buckets.get(tool_name)
        if bucket is None:
            return True, 0.0  # unknown tool — no limit configured
        return bucket.acquire()

    def emit_request(
        self, tool: str, url: str, method: str, started_at: float
    ) -> None:
        if telemetry.enabled():
            telemetry.emit(
                "net.request",
                "info",
                data={
                    "tool": tool,
                    "url": telemetry.redact_url(url),
                    "method": method,
                    "started_at": started_at,
                },
            )

    def emit_response(
        self,
        tool: str,
        url: str,
        status: int,
        bytes_: int,
        duration_ms: int,
    ) -> None:
        if telemetry.enabled():
            telemetry.emit(
                "net.response",
                "info",
                data={
                    "tool": tool,
                    "url": telemetry.redact_url(url),
                    "status": status,
                    "bytes": bytes_,
                    "duration_ms": duration_ms,
                },
            )

    async def fetch(self, url: str, *, timeout_s: float = DEFAULT_TIMEOUT) -> str:
        """HTTP GET a URL. UTF-8 strict decode (binary → error envelope so
        callers never get mojibake). 1 MB cap fires on raw bytes before
        decode; timeout clamped to [1, 120]s; HTTP 4xx/5xx and all
        exceptions return an <error: ...> envelope, never raise."""
        if timeout_s < MIN_TIMEOUT or timeout_s > MAX_TIMEOUT:
            warnings.warn(
                f"web_fetch timeout_s={timeout_s} outside "
                f"[{MIN_TIMEOUT}, {MAX_TIMEOUT}]; clamping",
                RuntimeWarning,
                stacklevel=2,
            )
            timeout_s = max(MIN_TIMEOUT, min(MAX_TIMEOUT, timeout_s))

        ok, retry_after = self.acquire("web_fetch")
        if not ok:
            return f"<error: rate limit: retry after {math.ceil(retry_after)}s>"

        started = time.monotonic()
        self.emit_request("web_fetch", url, "GET", started)
        try:
            resp = await self._http().get(url, timeout=timeout_s)
            duration_ms = int((time.monotonic() - started) * 1000)
        except httpx.TimeoutException:
            return f"<error: timeout after {timeout_s}s>"
        except httpx.HTTPError as e:
            return f"<error: http: {e}>"
        except Exception as e:  # noqa: BLE001
            return f"<error: net: {type(e).__name__}: {e}>"

        if resp.status_code >= 400:
            reason = resp.reason_phrase or "unknown"
            self.emit_response(
                "web_fetch", url, resp.status_code, 0, duration_ms
            )
            return f"<error: http {resp.status_code}: {reason}>"

        body_bytes = resp.content
        original_size = len(body_bytes)
        if original_size > MAX_BYTES:
            body_bytes = body_bytes[:MAX_BYTES]
            truncation_suffix = (
                f"\n<truncated: response exceeded 1 MB cap "
                f"(full size: {original_size} bytes)>"
            )
        else:
            truncation_suffix = ""

        try:
            text = body_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            ct = resp.headers.get("content-type", "unknown")
            self.emit_response(
                "web_fetch", url, resp.status_code, len(body_bytes), duration_ms
            )
            return f"<error: binary response: content-type={ct}>"

        self.emit_response(
            "web_fetch", url, resp.status_code, len(body_bytes), duration_ms
        )
        return text + truncation_suffix

    async def search(self, query: str, count: int) -> str:
        """Search the web via Brave and return a rendered result bundle."""
        api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
        if not api_key:
            return "<error: web_search disabled: set BRAVE_SEARCH_API_KEY env var>"

        ok, retry_after = self.acquire("web_search")
        if not ok:
            return f"<error: rate limit: retry after {math.ceil(retry_after)}s>"

        if count < 1 or count > 20:
            warnings.warn(
                f"web_search count={count} outside [1, 20]; clamping",
                RuntimeWarning,
                stacklevel=2,
            )
            count = max(1, min(20, count))

        if self._brave_backend is None or self._brave_api_key != api_key:
            self._brave_backend = BraveBackend(api_key, client=self._http())
            self._brave_api_key = api_key

        started = time.monotonic()
        self.emit_request(
            "web_search", BraveBackend.BASE_URL + f"?q={query}", "GET", started
        )
        result = await self._brave_backend.search(query, count)
        duration_ms = int((time.monotonic() - started) * 1000)
        if isinstance(result, str):
            self.emit_response(
                "web_search", BraveBackend.BASE_URL, -1, len(result), duration_ms
            )
            return result

        seen: set[str] = set()
        deduped: list[SearchResult] = []
        for search_result in result:
            if search_result.url in seen:
                continue
            seen.add(search_result.url)
            deduped.append(search_result)

        bundle = render_bundle(deduped)
        self.emit_response(
            "web_search", BraveBackend.BASE_URL, 200, len(bundle), duration_ms
        )
        return bundle
