---
phase: T3-network-surface
plan: 06
type: execute
wave: 4
depends_on: [T3-05]
files_modified:
  - voss/harness/web_search.py
  - voss/harness/net.py
  - voss/harness/tools.py
  - tests/harness/test_web_search.py
autonomous: true
requirements: [NET-02]
must_haves:
  truths:
    - "voss/harness/web_search.py defines a BraveBackend(api_key, *, client=None) class with async def search(query, count) -> list[SearchResult]"
    - "BraveBackend issues GET https://api.search.brave.com/res/v1/web/search with X-Subscription-Token: <api_key> header and query params {q, count}"
    - "NetSession.search reads BRAVE_SEARCH_API_KEY from env at call time; when env var absent or empty, returns the disabled-error envelope <error: web_search disabled: set BRAVE_SEARCH_API_KEY env var> without constructing BraveBackend. BraveBackend.__init__ validates a non-empty api_key was passed by its caller and raises ValueError if empty."
    - "NetSession gains a search(query, count) method that constructs/caches BraveBackend lazily; reuses NetSession._http() AsyncClient (D-05 single-client invariant)"
    - "Tool body web_search short-circuits with '<error: web_search disabled: set BRAVE_SEARCH_API_KEY env var>' when env var is unset, regardless of allow_net"
    - "count argument clamps to [1, 20] with RuntimeWarning on out-of-range"
    - "Results render as a numbered string bundle: '1. {title}\\n   {url}\\n   {description}\\n\\n2. ...' in stable order matching API response order"
    - "Brave HTTP 429 with Retry-After header returns '<error: rate limit: retry after {Retry-After}s>'; without Retry-After returns '<error: http 429: rate limited by backend>'"
    - "Results dedup by URL (first occurrence wins; subsequent duplicates dropped) per Claude's Discretion item 6"
    - "All 4 NET-02 acceptance tests pass: no_key envelope, mocked happy path 10 results stable, count clamp + warning, 429 handling"
  artifacts:
    - path: "voss/harness/web_search.py"
      provides: "class BraveBackend(api_key, *, client) with async search(query, count) -> list[SearchResult]; SearchResult dataclass {title, url, description}; render_bundle(results) -> str"
      contains: "class BraveBackend"
    - path: "voss/harness/net.py"
      provides: "NetSession.search(query, count) method dispatching to BraveBackend; lazy backend cache"
      contains: "def search"
    - path: "voss/harness/tools.py"
      provides: "web_search tool body + ToolEntry(is_mutating=False, is_network=True) registration"
      contains: "web_search"
    - path: "tests/harness/test_web_search.py"
      provides: "4 NET-02 acceptance tests + dedup bonus test (replaces T3-01 stubs)"
      contains: "def test_no_key"
  key_links:
    - from: "voss/harness/web_search.py:BraveBackend.search"
      to: "https://api.search.brave.com/res/v1/web/search"
      via: "GET with X-Subscription-Token header; uses NetSession._http() shared AsyncClient"
      pattern: "api\\.search\\.brave\\.com"
    - from: "voss/harness/tools.py:web_search body"
      to: "voss/harness/net.py:NetSession.search"
      via: "env-key check → net is None check → net.search(query, count); failure returns disabled-error envelope"
      pattern: "await net\\.search"
---

<objective>
Land `web_search` end-to-end (NET-02) as a thin layer atop the NetSession scaffolding T3-05 established. BraveBackend in a flat module per D-07 (no protocol abstraction — Tavily is explicitly deferred). NetSession gains a `search` method that shares the same httpx.AsyncClient (D-05 single-client invariant) and the same TokenBucket (web_search bucket established in T3-04). Four NET-02 acceptance tests un-skipped plus a dedup bonus test (Claude's Discretion 6).

Purpose: web_search closes the second of the three SPEC network surfaces. The pattern is intentionally thin — Brave returns JSON, we render a deterministic numbered bundle string. Env-var gating (BRAVE_SEARCH_API_KEY) is the second axis on top of allow_net; both must be true for the tool to fire. This is the second-to-last consumer of the T3-02/03/04/05 foundation.

Output: voss/harness/web_search.py (~80 lines); NetSession.search extension (~20 lines); web_search tool registration in tools.py; 4 NET-02 + 1 dedup test green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T3-network-surface/T3-SPEC.md
@.planning/phases/T3-network-surface/T3-CONTEXT.md
@.planning/phases/T3-network-surface/T3-RESEARCH.md
@.planning/phases/T3-network-surface/T3-PATTERNS.md
@.planning/phases/T3-network-surface/T3-05-PLAN.md
@voss/harness/net.py
@voss/harness/tools.py
@voss/harness/providers.py
@voss/harness/telemetry.py
</context>

<interfaces>
SearchResult dataclass (voss/harness/web_search.py):
```
@dataclass
class SearchResult:
    title: str
    url: str
    description: str
```

BraveBackend class (D-07):
```
class BraveBackend:
    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, *, client: httpx.AsyncClient | None = None) -> None:
        if not api_key:
            raise ValueError("BraveBackend requires non-empty api_key")
        self._api_key = api_key
        self._client = client  # caller-owned; BraveBackend never calls aclose

    async def search(self, query: str, count: int) -> list[SearchResult] | str:
        # Returns list[SearchResult] on success, OR an <error: ...> envelope string on failure.
        # The string sentinel lets the caller (NetSession.search / tools.web_search body)
        # propagate the envelope without exception plumbing — matches tools.py convention.
        ...
```

Request shape (T3-RESEARCH Pattern 3, verified vs official Brave docs):
```
headers = {"X-Subscription-Token": api_key, "Accept": "application/json", "Accept-Encoding": "gzip"}
params = {"q": query, "count": count}
resp = await client.get(BraveBackend.BASE_URL, headers=headers, params=params, timeout=30.0)
```

Response parsing (RESEARCH Pattern 3):
- HTTP 200: `data = resp.json(); items = data.get("web", {}).get("results", [])`
- For each item: `SearchResult(title=item.get("title", ""), url=item.get("url", ""), description=item.get("description", ""))`
- HTTP 429: if `Retry-After` header present: return `f"<error: rate limit: retry after {retry_after}s>"`. Else: `"<error: http 429: rate limited by backend>"`.
- Other 4xx/5xx: `f"<error: http {status}: {reason}>"`
- Network exception: `f"<error: net: {type(e).__name__}: {e}>"` (mirrors NetSession.fetch convention)

Dedup (Claude's Discretion 6 — RECOMMENDED YES):
- After parsing items into SearchResult list, walk in order keeping a `seen: set[str]` of URLs. Skip any duplicate URL on second appearance. Preserve first-occurrence order.

Bundle rendering (NET-02 SPEC stable order):
```
def render_bundle(results: list[SearchResult]) -> str:
    lines = []
    for i, r in enumerate(results, start=1):
        lines.append(f"{i}. {r.title}\n   {r.url}\n   {r.description}\n")
    return "\n".join(lines).rstrip() + "\n"
```
(Trailing newline standardization optional; pick one convention and pin via test.)

NetSession.search extension:
```
def __init__(self, ...):  # extend existing
    ...
    self._brave_backend: BraveBackend | None = None

async def search(self, query: str, count: int) -> str:
    # Returns the rendered bundle string OR an <error: ...> envelope.
    import os
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    if not api_key:
        return "<error: web_search disabled: set BRAVE_SEARCH_API_KEY env var>"
    # Rate-limit gate
    ok, retry = self.acquire("web_search")
    if not ok:
        import math
        return f"<error: rate limit: retry after {math.ceil(retry)}s>"
    # Clamp count to [1, 20]
    if count < 1 or count > 20:
        import warnings
        warnings.warn(f"web_search count={count} outside [1, 20]; clamping", RuntimeWarning, stacklevel=2)
        count = max(1, min(20, count))
    # Lazy backend cache
    if self._brave_backend is None:
        self._brave_backend = BraveBackend(api_key, client=self._http())
    started = time.monotonic()
    self.emit_request("web_search", BraveBackend.BASE_URL + f"?q={query}", "GET", started)
    result = await self._brave_backend.search(query, count)
    duration_ms = int((time.monotonic() - started) * 1000)
    if isinstance(result, str):
        # Error envelope from backend; pass through. emit_response with status=-1 sentinel
        self.emit_response("web_search", BraveBackend.BASE_URL, -1, len(result), duration_ms)
        return result
    # Dedup
    seen = set(); deduped = []
    for r in result:
        if r.url in seen: continue
        seen.add(r.url); deduped.append(r)
    bundle = render_bundle(deduped)
    self.emit_response("web_search", BraveBackend.BASE_URL, 200, len(bundle), duration_ms)
    return bundle
```

Tool body in tools.py:
```
@tool(name="web_search", description="Search the web via Brave Search. Requires --allow-net and BRAVE_SEARCH_API_KEY env var. Returns a numbered bundle of {count} results.")
async def web_search(query: str, count: int = 10) -> str:
    if net is None:
        return "<error: net disabled: set tools.allow_net = true in harness.toml or pass --allow-net>"
    return await net.search(query, count)
```

Registration entry (append to tools.py registration block after web_fetch):
```
"web_search": ToolEntry(descriptor=web_search, is_mutating=False, is_network=True),
```

Test scaffolding: mirror test_web_fetch.py's MockTransport pattern from T3-05 Task 2. Brave-specific fixture:
```
BRAVE_HAPPY_RESPONSE = {
    "web": {
        "results": [
            {"title": f"Title {i}", "url": f"https://example.com/{i}", "description": f"Desc {i}"}
            for i in range(10)
        ]
    }
}

def make_brave_handler(response_dict, status=200, headers=None):
    def handler(request):
        return httpx.Response(status, json=response_dict, headers=headers or {})
    return handler
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Create voss/harness/web_search.py (BraveBackend) + extend NetSession.search + register web_search tool</name>
  <files>voss/harness/web_search.py, voss/harness/net.py, voss/harness/tools.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-02 — full target + 4 acceptance bullets)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-07 — BraveBackend flat module; D-05 — single client; Claude's Discretion 6 — dedup)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 3 — Brave request/response shape; State of the Art table for any current-API notes)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (section "voss/harness/web_search.py")
    - voss/harness/net.py (post T3-05 — NetSession to extend; locate fetch() to place search() beside it)
    - voss/harness/tools.py (post T3-05 — web_fetch registration; add web_search registration after it)
    - voss/harness/providers.py lines 139-148 (AnthropicOAuthProvider __init__ injection pattern)
  </read_first>
  <action>
    Create voss/harness/web_search.py:
    - Top: `"""Brave Search backend for web_search tool. T3-06 / NET-02. SPEC explicitly says Brave only; Tavily abstraction is OUT OF SCOPE per CONTEXT.md Deferred Ideas."""`
    - Imports: `from __future__ import annotations; from dataclasses import dataclass; import httpx`
    - `@dataclass` `SearchResult` with title/url/description fields, all str.
    - `class BraveBackend` per the interfaces block above. Methods: `__init__(api_key, *, client)`, `async search(query, count) -> list[SearchResult] | str`. 
      - search() implementation:
        - headers = {"X-Subscription-Token": self._api_key, "Accept": "application/json", "Accept-Encoding": "gzip"}.
        - params = {"q": query, "count": count}.
        - try: resp = await self._client.get(self.BASE_URL, headers=headers, params=params, timeout=30.0).
        - except httpx.TimeoutException: return "<error: timeout after 30s>".
        - except httpx.HTTPError as e: return f"<error: http: {e}>".
        - except Exception as e: return f"<error: net: {type(e).__name__}: {e}>".
        - if resp.status_code == 429:
          - retry_after = resp.headers.get("Retry-After")
          - if retry_after: return f"<error: rate limit: retry after {retry_after}s>"
          - return "<error: http 429: rate limited by backend>"
        - if resp.status_code >= 400: reason = resp.reason_phrase or "unknown"; return f"<error: http {resp.status_code}: {reason}>".
        - try: data = resp.json(); except Exception: return "<error: brave: response was not JSON>".
        - items = data.get("web", {}).get("results", []) or [].
        - return [SearchResult(title=str(it.get("title", "")), url=str(it.get("url", "")), description=str(it.get("description", ""))) for it in items].
    - `def render_bundle(results: list[SearchResult]) -> str`: numbered bundle per the interfaces block. Empty results: return "<no results>".

    Edit voss/harness/net.py:
    - Add `from voss.harness.web_search import BraveBackend, SearchResult, render_bundle` at top.
    - Add to NetSession.__init__: `self._brave_backend: "BraveBackend | None" = None`.
    - Add NetSession.search method per the interfaces block. Critically: pass `self._http()` (the shared AsyncClient) to BraveBackend constructor — proves D-05 single-client invariant.
    - Refactor: emit_request URL argument should be just `BraveBackend.BASE_URL` (NOT the full URL with `?q=` — the query string would defeat redact_url, since redact_url strips the entire `?` portion. But the redact_url contract IS to strip the query. So passing the full URL is fine — redact_url will strip the q= param. Pick: pass `BraveBackend.BASE_URL + f"?q={query}"` to emit_request and let redact_url strip the query — proves redact_url applies on the search path too. This makes the test_redact_url_in_emit-style coverage natural for web_search).

    Edit voss/harness/tools.py:
    - Add web_search tool body in make_toolset (alongside web_fetch from T3-05). Body matches the interfaces block.
    - Add registration entry: `"web_search": ToolEntry(descriptor=web_search, is_mutating=False, is_network=True)`.
    - Confirm tool docstring mentions both --allow-net AND BRAVE_SEARCH_API_KEY for agent self-doc.
  </action>
  <verify>
    <automated>uv run python -c "from voss.harness.web_search import BraveBackend, SearchResult, render_bundle; r = [SearchResult('T','https://x.com/1','D'), SearchResult('T2','https://x.com/2','D2')]; print(render_bundle(r))" 2>&amp;1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "^class BraveBackend" voss/harness/web_search.py` returns 1 match
    - source assertion: `grep -cE "api\.search\.brave\.com" voss/harness/web_search.py` returns >= 1
    - source assertion: `grep -cE "X-Subscription-Token" voss/harness/web_search.py` returns 1
    - source assertion: `grep -nE "ValueError" voss/harness/web_search.py | wc -l` >= 1 (empty-key check)
    - source assertion: `grep -nE "async def search" voss/harness/net.py | wc -l` >= 1
    - tool registration: `grep -nE '"web_search":\s*ToolEntry\(.*is_network=True' voss/harness/tools.py` returns 1
    - dedup logic: `grep -nE "seen\s*=\s*set\(\)|if r\.url in seen" voss/harness/net.py | wc -l` >= 1
    - shared client invariant: `grep -nE "BraveBackend\(api_key,\s*client=self\._http\(\)\)" voss/harness/net.py` returns 1 match (proves D-05 single-client)
    - smoke: `python -c "from voss.harness.tools import make_toolset; from pathlib import Path; ts = make_toolset(Path('.')); e = ts['web_search']; print(e.is_network, e.is_mutating)"` prints `True False`
    - regression: `uv run pytest tests/harness/test_web_fetch.py tests/harness/test_rate_limit.py tests/harness/test_allow_net.py -x -q` exits 0
  </acceptance_criteria>
  <done>BraveBackend class in flat web_search.py module; NetSession.search method dispatches with shared AsyncClient + rate-limit gate + count clamp + dedup; web_search registered as ToolEntry with is_network=True; existing T3-05 tests still pass.</done>
</task>

<task type="auto">
  <name>Task 2: 4 NET-02 web_search acceptance tests + dedup bonus test</name>
  <files>tests/harness/test_web_search.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-02 acceptance bullets a-d)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 3 — Brave response shape; 429 handling)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (Shared Patterns — MockTransport reuse from test_web_fetch.py)
    - voss/harness/net.py (NetSession.search just landed)
    - voss/harness/web_search.py (BraveBackend just landed)
    - tests/harness/test_web_fetch.py (T3-05 — MockTransport helper to mirror)
    - tests/harness/test_web_search.py (T3-01 scaffold — 4 pytest.skip stubs)
  </read_first>
  <action>
    Edit tests/harness/test_web_search.py — replace all 4 pytest.skip stubs.

    Imports: `import os, httpx, pytest, warnings, json; from voss.harness.net import NetSession; from voss.harness.tools import make_toolset; from voss.harness.web_search import BraveBackend, SearchResult, render_bundle; from voss_runtime import configure, reset_config`.

    Fixture: `@pytest.fixture(autouse=True) def _setup(monkeypatch): reset_config(); configure(allow_net=True); yield; reset_config()`.

    Helper:
    ```
    BRAVE_10_RESULTS = {
        "web": {"results": [
            {"title": f"Title {i}", "url": f"https://example.com/{i}", "description": f"Desc {i}"}
            for i in range(10)
        ]}
    }

    def make_session(handler, *, api_key="test-key") -> NetSession:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport)
        return NetSession(client=client)

    def make_handler(*, status=200, response=None, headers=None):
        def handler(request):
            if response is not None:
                return httpx.Response(status, json=response, headers=headers or {})
            return httpx.Response(status, headers=headers or {})
        return handler
    ```

    Tests:

    - `async def test_no_key(monkeypatch, tmp_path)` (NET-02a): monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False). `session = make_session(make_handler())`. `result = await session.search("python asyncio", 10)`. Assert `result == "<error: web_search disabled: set BRAVE_SEARCH_API_KEY env var>"`. ALSO assert allow_net=True (configure already set in fixture) doesn't suppress this — the env-key check fires regardless of allow_net.

    - `async def test_mocked_results(monkeypatch, tmp_path)` (NET-02b): monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key"). `session = make_session(make_handler(response=BRAVE_10_RESULTS))`. `result = await session.search("python", 10)`. Assert result is a string (rendered bundle); assert "1. Title 0" in result; assert "https://example.com/0" in result; assert "Desc 0" in result; assert "10. Title 9" in result; assert each of Title 0..9 appears in order (test the stable-order invariant by extracting `re.findall(r"^\d+\. Title (\d+)", result, re.MULTILINE)` and asserting it == ["0","1","2","3","4","5","6","7","8","9"]).

    - `async def test_count_clamp(monkeypatch)` (NET-02c): monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key"). Capture request to verify clamped count is what got sent. Build a handler that records the request: `captured = []; def handler(req): captured.append(req); return httpx.Response(200, json=BRAVE_10_RESULTS)`. Call `session.search("foo", count=50)` while capturing warnings. Assert exactly one RuntimeWarning emitted containing "outside [1, 20]" or "clamping". Assert that the captured request URL has `count=20` in its query params (parse via `urllib.parse.parse_qs(captured[0].url.query.decode())` or `captured[0].url.params`). Repeat for count=0 (clamps to 1).

    - `async def test_429_handling(monkeypatch)` (NET-02d): monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key"). First case: `session = make_session(make_handler(status=429, headers={"Retry-After": "30"}))`. result = await session.search("foo", 10). Assert `result == "<error: rate limit: retry after 30s>"`. Second case: 429 with no Retry-After header. Assert `result == "<error: http 429: rate limited by backend>"`.

    Bonus: `async def test_dedup_url(monkeypatch)`: monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key"). Response with duplicate URLs:
    ```
    {"web": {"results": [
        {"title": "A", "url": "https://x.com/", "description": "first"},
        {"title": "B", "url": "https://y.com/", "description": "second"},
        {"title": "C", "url": "https://x.com/", "description": "DUP"},
    ]}}
    ```
    Call `session.search("foo", 10)`. Assert result includes "first" + "second"; assert result does NOT include "DUP"; assert "1. A" + "2. B" present; assert no "3." numbered line present (only 2 deduped results rendered).

    Bonus: `async def test_disabled_when_net_is_none(tmp_path, monkeypatch)`: monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "fake-key"). toolset = make_toolset(tmp_path, net=None). result = await toolset["web_search"].invoke_dict({"query": "foo"}). Assert result startswith "<error: net disabled:". Proves D-08 short-circuit even when env key is set.

    Skip count: `grep -c "pytest.skip" tests/harness/test_web_search.py` should be 0 after edit.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_web_search.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - skip removed: `grep -c "pytest.skip" tests/harness/test_web_search.py` returns 0
    - test count: `uv run pytest tests/harness/test_web_search.py --collect-only -q 2>&amp;1 | tail -5` shows 6 tests (4 NET-02 acceptance + test_dedup_url + test_disabled_when_net_is_none)
    - all NET-02 pass: `uv run pytest tests/harness/test_web_search.py -x -q 2>&amp;1 | tail -3` shows "6 passed"
    - stable-order assertion: test_mocked_results verifies the numbered prefix sequence 1-10 matches API order
    - clamp assertion: test_count_clamp captures the OUTGOING request and asserts count=20 (the actually-sent clamped value)
    - 429-with and 429-without: both branches verified in test_429_handling
    - dedup: test_dedup_url proves Claude's Discretion 6 implementation
    - regression: `uv run pytest tests/harness/test_web_fetch.py tests/harness/test_web_search.py tests/harness/test_rate_limit.py -x -q` exits 0
  </acceptance_criteria>
  <done>4 NET-02 acceptance tests + 2 bonus tests in test_web_search.py pass; stable-order render verified; count clamp captures outgoing query param; 429 with and without Retry-After both produce correct envelopes; dedup-by-URL preserves first occurrence; D-08 net=None short-circuit fires even when env key is set.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Local env var BRAVE_SEARCH_API_KEY → outgoing X-Subscription-Token header | Env var is user-owned. Header is sent to api.search.brave.com only. Never written to telemetry (T3-RESEARCH Security Domain). |
| Brave response JSON → bundle string returned to agent | Untrusted external content; consumer is the agent reading the string. No script execution; no HTML rendering — plain string with predictable shape. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T3-08 | Info Disclosure | Brave API key visible in env / on `ps` listing | mitigate | env-var only (no CLI flag, no config file); auth.py convention. Key never appears in telemetry — redact_url strips ?q= and any other query params; header is not in URL |
| T-T3-06-01 | DoS | malicious Brave response with massive count of results | mitigate | count param clamped to [1, 20]; even if Brave returns more, render_bundle iterates only what's in the dedup-passed list; bundle string size is bounded by max(20) results × ~500 bytes each |
| T-T3-06-02 | Info Disclosure | Brave response contains URLs with secrets in query strings | mitigate | results are returned to the agent (which is also the user's local process); the URLs are NOT routed through telemetry except as the redacted BASE_URL of the search call itself; per-result URLs are agent-visible by design (that's the tool's purpose) — risk accepted at this boundary |
| T-T3-06-03 | Tampering | Brave returns 429 to throttle, agent loops retrying | mitigate | <error: rate limit: retry after Ns> envelope provides agent guidance; web_search bucket (10/min) bounds retry frequency; agent loop's max_iterations cap (T1) bounds total attempts |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_web_search.py -x -q` exits 0 (6 tests pass)
- `grep -nE "BRAVE_SEARCH_API_KEY" voss/harness/net.py voss/harness/web_search.py | wc -l` >= 1 (env var read site)
- `grep -nE "X-Subscription-Token" voss/harness/web_search.py` returns 1 match
- `python -c "from voss.harness.tools import make_toolset; from pathlib import Path; ts = make_toolset(Path('.')); print('web_search' in ts and ts['web_search'].is_network)"` prints `True`
- `python -c "import os; os.environ.pop('BRAVE_SEARCH_API_KEY', None); import asyncio; from voss.harness.net import NetSession; print(asyncio.run(NetSession().search('q', 10)))"` prints the disabled-error envelope
</verification>

<success_criteria>
- BraveBackend in flat module (no protocol abstraction per D-07)
- NetSession.search reuses _http() AsyncClient (D-05 single-client invariant)
- count clamp to [1, 20] enforced on outgoing query param
- 429 with Retry-After preserves the value verbatim in the envelope
- Dedup-by-URL implemented (Claude's Discretion 6)
- env-var gate fires regardless of allow_net (orthogonal gates)
- 4 NET-02 acceptance tests pass + 2 bonus tests pass
</success_criteria>

<output>
Create `.planning/phases/T3-network-surface/T3-06-SUMMARY.md` when done: report BraveBackend public API + render_bundle output sample for 3 fake results; NetSession.search line numbers; pytest output showing 6 tests green; note that web_search now shares the SAME httpx.AsyncClient as web_fetch (D-05 invariant satisfied — single connection pool).
</output>
