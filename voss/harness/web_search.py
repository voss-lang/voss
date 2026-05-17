"""Brave Search backend for web_search tool. T3-06 / NET-02.

SPEC explicitly says Brave only; Tavily abstraction is OUT OF SCOPE per
CONTEXT.md Deferred Ideas.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class SearchResult:
    title: str
    url: str
    description: str


class BraveBackend:
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(
        self, api_key: str, *, client: httpx.AsyncClient | None = None
    ) -> None:
        if not api_key:
            raise ValueError("BraveBackend requires non-empty api_key")
        self._api_key = api_key
        self._client = client

    async def search(self, query: str, count: int) -> list[SearchResult] | str:
        """Return SearchResult objects or an <error: ...> envelope string."""
        headers = {
            "X-Subscription-Token": self._api_key,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        }
        params = {"q": query, "count": count}
        try:
            if self._client is None:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        self.BASE_URL,
                        headers=headers,
                        params=params,
                        timeout=30.0,
                    )
            else:
                resp = await self._client.get(
                    self.BASE_URL, headers=headers, params=params, timeout=30.0
                )
        except httpx.TimeoutException:
            return "<error: timeout after 30s>"
        except httpx.HTTPError as e:
            return f"<error: http: {e}>"
        except Exception as e:  # noqa: BLE001
            return f"<error: net: {type(e).__name__}: {e}>"

        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                return f"<error: rate limit: retry after {retry_after}s>"
            return "<error: http 429: rate limited by backend>"

        if resp.status_code >= 400:
            reason = resp.reason_phrase or "unknown"
            return f"<error: http {resp.status_code}: {reason}>"

        try:
            data = resp.json()
        except Exception:
            return "<error: brave: response was not JSON>"

        items = data.get("web", {}).get("results", []) or []
        return [
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                description=str(item.get("description", "")),
            )
            for item in items
        ]


def render_bundle(results: list[SearchResult]) -> str:
    if not results:
        return "<no results>"
    lines: list[str] = []
    for i, result in enumerate(results, start=1):
        lines.append(
            f"{i}. {result.title}\n"
            f"   {result.url}\n"
            f"   {result.description}\n"
        )
    return "\n".join(lines).rstrip() + "\n"
