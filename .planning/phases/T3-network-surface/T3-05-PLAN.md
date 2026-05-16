---
phase: T3-network-surface
plan: 05
type: execute
wave: 3
depends_on: [T3-01, T3-02, T3-03, T3-04]
files_modified:
  - voss/harness/net.py
  - voss/harness/tools.py
  - voss/harness/cli.py
  - tests/harness/test_web_fetch.py
  - tests/harness/test_allow_net.py
  - tests/harness/test_rate_limit.py
autonomous: true
requirements: [NET-01, NET-05, NET-07]
must_haves:
  truths:
    - "voss/harness/net.py exports NetSession with lazy httpx.AsyncClient(_http()), aclose(), acquire(tool_name), emit_request(tool, url, method, started_at), emit_response(tool, url, status, bytes, duration_ms), and an async fetch(url, timeout_s) method"
    - "NetSession registers itself with lifecycle.register_session at construction time so reap_all() invokes aclose()"
    - "NetSession constructor initializes per-instance TokenBucket dict {'web_fetch': make_default_bucket('web_fetch'), 'web_search': make_default_bucket('web_search')} with TOML overrides applied"
    - "voss/harness/tools.py registers web_fetch as a ToolEntry with is_mutating=False, is_network=True; body short-circuits to '<error: net disabled: ...>' when make_toolset called with net=None"
    - "web_fetch response > 1,048,576 bytes truncates at exactly that byte boundary and appends '\\n<truncated: response exceeded 1 MB cap (full size: N bytes)>'"
    - "web_fetch timeout_s outside [1.0, 120.0] clamps to bounds and emits RuntimeWarning"
    - "web_fetch HTTP 4xx/5xx returns '<error: http {status}: {reason}>' without raising"
    - "web_fetch on rate-limit returns '<error: rate limit: retry after Ns>' where N = ceil(retry_after_s)"
    - "cli.py bootstrap constructs NetSession(rate_overrides=get_net_rate_limits()) and passes it through to make_toolset where the agent loop wires it"
    - "Agent-loop tool dispatch site passes is_network=entry.is_network to gate.check (the T3-02 audit closure)"
    - "test_zero_socket_invariant in tests/harness/test_allow_net.py extends to httpx.MockTransport variant proving zero outbound calls when allow_net=False"
    - "test_mcp_bypasses_bucket in tests/harness/test_rate_limit.py un-skipped: a NetSession.acquire('filesystem__read_text_file') call always returns (True, 0.0) regardless of bucket state"
  artifacts:
    - path: "voss/harness/net.py"
      provides: "class NetSession with _http(), aclose(), acquire(tool_name), emit_request/emit_response, async fetch(url, timeout_s)"
      contains: "class NetSession"
    - path: "voss/harness/tools.py"
      provides: "web_fetch tool body using net.fetch; registration entry 'web_fetch': ToolEntry(descriptor=web_fetch, is_mutating=False, is_network=True)"
      contains: "web_fetch"
    - path: "voss/harness/cli.py"
      provides: "NetSession instance constructed at bootstrap; passed through to make_toolset wiring"
      contains: "NetSession"
    - path: "tests/harness/test_web_fetch.py"
      provides: "5 NET-01 acceptance tests (replaces T3-01 skips): registration, allow_net_gate, truncation, timeout_clamp, http_errors"
      contains: "def test_truncation"
    - path: "tests/harness/test_allow_net.py"
      provides: "test_zero_socket_invariant extended to use httpx.MockTransport counting transport"
      contains: "MockTransport"
    - path: "tests/harness/test_rate_limit.py"
      provides: "test_mcp_bypasses_bucket un-skipped: verifies NetSession.acquire returns (True, 0.0) for tool names matching MCP namespace pattern (server__tool)"
      contains: "def test_mcp_bypasses_bucket"
  key_links:
    - from: "voss/harness/net.py:NetSession.fetch"
      to: "httpx.AsyncClient.get + telemetry.redact_url + telemetry.emit"
      via: "acquire(tool) -> emit_request -> _http().get -> truncate at 1MB -> emit_response"
      pattern: "telemetry\\.redact_url|httpx\\.AsyncClient"
    - from: "voss/harness/tools.py:web_fetch body"
      to: "voss/harness/net.py:NetSession.fetch"
      via: "if net is None: return disabled-error; else return await net.fetch(url, timeout_s=timeout_s)"
      pattern: "await net\\.fetch"
    - from: "voss/harness/cli.py bootstrap"
      to: "voss/harness/net.py:NetSession"
      via: "net_session = NetSession(rate_overrides=get_net_rate_limits()); lifecycle.register_session(net_session); pass to make_toolset(cwd, net=net_session)"
      pattern: "NetSession\\("
---

<objective>
Ship `web_fetch` end-to-end (NET-01) by landing NetSession (D-05, D-06, D-08, D-16) — the shared httpx.AsyncClient owner that wires together everything T3-02/03/04 prepared. Five NET-01 acceptance tests un-skipped (registration, allow_net gate, 1 MB truncation, timeout clamp, HTTP error envelope). Two cross-plan placeholders un-skipped: NET-05f extends from gate-level to httpx-MockTransport-level proof; NET-07e (test_mcp_bypasses_bucket) proves MCP namespaced tool names skip the bucket.

Purpose: web_fetch is the first agent-callable network tool. It exercises every NET-* axis except the MCP subsystem: allow_net gate (T3-02), redact_url + emit (T3-03), TokenBucket (T3-04), 1 MB cap + timeout + HTTP error envelope (NET-01 SPEC). The lifecycle hook (T3-01) is the shared shutdown point. T3-05 is the keystone Wave 3 plan — once green, web_search (T3-06) is a thin extension reusing NetSession.

Output: voss/harness/net.py (~150 lines); web_fetch tool registered in tools.py; cli.py bootstrap constructs NetSession; 5 NET-01 + 1 NET-05 + 1 NET-07 test bodies un-skipped.
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
@.planning/phases/T3-network-surface/T3-01-PLAN.md
@.planning/phases/T3-network-surface/T3-02-PLAN.md
@.planning/phases/T3-network-surface/T3-03-PLAN.md
@.planning/phases/T3-network-surface/T3-04-PLAN.md
@voss/harness/tools.py
@voss/harness/providers.py
@voss/harness/lifecycle.py
@voss/harness/rate_limit.py
@voss/harness/telemetry.py
@voss/harness/cli.py
</context>

<interfaces>
NetSession public API (this plan defines):

```
class NetSession:
    def __init__(self, *, client: httpx.AsyncClient | None = None, rate_overrides: dict[str, dict[str, int]] | None = None) -> None:
        # client param injectable for tests (mirrors providers.py pattern lines 139-148)
        self._client: httpx.AsyncClient | None = client
        # Build per-instance bucket registry from DEFAULT_SPECS + TOML overrides
        self._buckets: dict[str, TokenBucket] = {}
        for tool_name in DEFAULT_SPECS:
            override = (rate_overrides or {}).get(tool_name)
            if override is not None:
                self._buckets[tool_name] = TokenBucket(rate_per_min=override["rate"], burst=override["burst"])
            else:
                self._buckets[tool_name] = make_default_bucket(tool_name)
        # Register for lifecycle reap
        lifecycle.register_session(self)

    def _http(self) -> httpx.AsyncClient: ...   # lazy construct
    async def aclose(self) -> None: ...         # called by lifecycle.reap_all

    def acquire(self, tool_name: str) -> tuple[bool, float]:
        # MCP bypass: namespaced names (containing '__') skip the bucket entirely (D-16 + NET-07e)
        if "__" in tool_name:
            return True, 0.0
        bucket = self._buckets.get(tool_name)
        if bucket is None:
            return True, 0.0  # unknown tool — no limit configured
        return bucket.acquire()

    def emit_request(self, tool: str, url: str, method: str, started_at: float) -> None: ...
    def emit_response(self, tool: str, url: str, status: int, bytes_: int, duration_ms: int) -> None: ...

    async def fetch(self, url: str, *, timeout_s: float = 30.0) -> str:
        # 1. Clamp timeout_s to [1.0, 120.0] with RuntimeWarning on out-of-range
        # 2. acquire("web_fetch") — return rate-limit envelope on (False, retry_after)
        # 3. emit_request("web_fetch", url, "GET", time.monotonic())
        # 4. await _http().get(url, timeout=clamped_timeout, follow_redirects=True is set in constructor)
        # 5. Read body bytes; if len > 1_048_576: truncate to first 1_048_576 bytes, append truncation marker with original size
        # 6. Decode UTF-8 (errors="replace"); if response is binary, return <error: binary response: content-type=...>
        # 7. On HTTP 4xx/5xx: return <error: http {status}: {reason}>
        # 8. emit_response("web_fetch", url, resp.status_code, len(body), duration_ms)
        # 9. Return body string
        # All exceptions (httpx.ConnectError, TimeoutException, etc.) returned as <error: {exception class}: {message}>
```

httpx.AsyncClient constructor kwargs (from RESEARCH Pattern 4):
- follow_redirects=True (Pitfall 3)
- max_redirects=5
- verify=True
- timeout=httpx.Timeout(30.0) — overridden per-call in fetch()
- http2=False (no dependency complexity)

Truncation marker (NET-01 SPEC exact wording):
```
\n<truncated: response exceeded 1 MB cap (full size: N bytes)>
```
where N is the ORIGINAL byte count from Content-Length or the actual streamed-bytes total. Truncate at byte offset 1,048,576 exactly (1024 * 1024).

CLI bootstrap (cli.py): T3-02 already added `configure(allow_net=get_allow_net())` to the boot configure() call. Extend that boot site to ALSO:
- import `from voss.harness.net import NetSession` and `from voss.harness.config import get_net_rate_limits`
- after configure(): `_NET_SESSION = NetSession(rate_overrides=get_net_rate_limits())` stored at module level
- in do_cmd / chat_cmd, locate the existing `make_toolset(cwd)` call (probably in _resolve_run_turn at line 174 — `grep -n "make_toolset" voss/harness/cli.py` to confirm). Replace with `make_toolset(cwd, net=_NET_SESSION)`. If make_toolset is called inside another module (e.g., agent.py), thread `net` through that module's API surface.

Agent-loop tool dispatch site: `grep -n "gate.check\|permission_gate.check" voss/harness/agent.py` to find call sites. For each tool dispatch, change `gate.check(name, args, is_mutating=entry.is_mutating)` to `gate.check(name, args, is_mutating=entry.is_mutating, is_network=entry.is_network)`. This is the audit closure T3-02 left for T3-05.

Network-binary fallback: response content-type starting with `image/`, `application/octet-stream`, `application/pdf`, or any content where UTF-8 decode with errors='strict' would raise — return `<error: binary response: content-type={ct}>`. SPEC NET-01 says "Body returned as UTF-8 (best-effort decode; binary fails with `<error: binary response: content-type=...>`)". Use bytes() length not str() length for the 1 MB cap so binary check fires first OR truncation happens first — order matters. Decision: 1 MB cap fires FIRST on raw bytes (so over-cap responses always truncate, even binary), THEN UTF-8 decode is attempted on the truncated bytes. If decode fails, return the binary-error envelope.

Test fixture: httpx.MockTransport pattern from RESEARCH Pattern 4. Inject a custom transport that returns canned responses:
```
def make_mock_client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, follow_redirects=True, max_redirects=5)

def make_mock_session(handler) -> NetSession:
    return NetSession(client=make_mock_client(handler))
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Create voss/harness/net.py with NetSession + register web_fetch in tools.py + cli.py wire-in</name>
  <files>voss/harness/net.py, voss/harness/tools.py, voss/harness/cli.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-01 — full text including all 5 acceptance bullets; NET-05f zero-socket; NET-07a-e rate limiting)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-05, D-06, D-08, D-16)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 4 — httpx.AsyncClient constructor; Architecture Patterns — system diagram; Anti-Patterns list)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (section "voss/harness/net.py" — providers.py analog; section "voss/harness/tools.py (extend)" — web_fetch body shape)
    - voss/harness/providers.py lines 139-170 (AnthropicOAuthProvider — _http + aclose pattern to mirror)
    - voss/harness/tools.py (entire file as of post-T3-02 state — registration block lines 196-207 to extend)
    - voss/harness/lifecycle.py (T3-01 — register_session signature)
    - voss/harness/rate_limit.py (T3-04 — DEFAULT_SPECS, TokenBucket, make_default_bucket)
    - voss/harness/telemetry.py (T3-03 — redact_url, emit, event-shape docstring)
    - voss/harness/cli.py (locate the boot configure() block + the make_toolset call sites — `grep -n "make_toolset\|configure(.*allow_net" voss/harness/cli.py`)
    - voss/harness/agent.py (locate gate.check call sites — `grep -n "gate.check\|permission_gate" voss/harness/agent.py`)
  </read_first>
  <action>
    Create voss/harness/net.py. Top of file:
    - `"""NetSession owns the shared httpx.AsyncClient + per-tool TokenBucket registry + telemetry emit wrappers for net.request/net.response (T3-05, NET-01)."""`
    - `from __future__ import annotations`
    - `import time`
    - `import warnings`
    - `import httpx`
    - `from voss.harness import lifecycle, telemetry`
    - `from voss.harness.rate_limit import DEFAULT_SPECS, TokenBucket, make_default_bucket`

    Constants:
    - `MAX_BYTES = 1_048_576  # 1 MB cap per NET-01 SPEC`
    - `MIN_TIMEOUT = 1.0`
    - `MAX_TIMEOUT = 120.0`
    - `DEFAULT_TIMEOUT = 30.0`

    Class `NetSession`. Implementation:
    - `__init__(self, *, client=None, rate_overrides=None)`: store client; build self._buckets per the interfaces block above; call `lifecycle.register_session(self)`.
    - `def _http(self) -> httpx.AsyncClient`: lazy construct with follow_redirects=True, max_redirects=5, verify=True, timeout=httpx.Timeout(DEFAULT_TIMEOUT), http2=False (mirrors providers.py:162-169 + adds redirect/verify).
    - `async def aclose(self) -> None`: if self._client is not None: await self._client.aclose(); self._client = None.
    - `def acquire(self, tool_name: str) -> tuple[bool, float]`: if `"__" in tool_name`: return (True, 0.0). Else: bucket = self._buckets.get(tool_name); if bucket is None: return (True, 0.0); return bucket.acquire().
    - `def emit_request(self, tool, url, method, started_at)`: if telemetry.enabled(): telemetry.emit("net.request", "info", data={"tool": tool, "url": telemetry.redact_url(url), "method": method, "started_at": started_at}).
    - `def emit_response(self, tool, url, status, bytes_, duration_ms)`: similar shape, kind="net.response".
    - `async def fetch(self, url: str, *, timeout_s: float = DEFAULT_TIMEOUT) -> str`:
      - clamp timeout_s: if timeout_s < MIN_TIMEOUT or timeout_s > MAX_TIMEOUT: emit warnings.warn(f"web_fetch timeout_s={timeout_s} outside [{MIN_TIMEOUT}, {MAX_TIMEOUT}]; clamping", RuntimeWarning, stacklevel=2); timeout_s = max(MIN_TIMEOUT, min(MAX_TIMEOUT, timeout_s)).
      - rate-limit check: ok, retry_after = self.acquire("web_fetch"); if not ok: import math; return f"<error: rate limit: retry after {math.ceil(retry_after)}s>".
      - started = time.monotonic(); self.emit_request("web_fetch", url, "GET", started).
      - try:
        - resp = await self._http().get(url, timeout=timeout_s).
        - duration_ms = int((time.monotonic() - started) * 1000).
      - except httpx.TimeoutException: return f"<error: timeout after {timeout_s}s>".
      - except httpx.HTTPError as e: return f"<error: http: {e}>".
      - except Exception as e: return f"<error: net: {type(e).__name__}: {e}>".
      - On 4xx/5xx: if resp.status_code >= 400: reason = resp.reason_phrase or "unknown"; self.emit_response("web_fetch", url, resp.status_code, 0, duration_ms); return f"<error: http {resp.status_code}: {reason}>".
      - body_bytes = resp.content (raw bytes).
      - original_size = len(body_bytes).
      - if original_size > MAX_BYTES: body_bytes = body_bytes[:MAX_BYTES]; truncated = True; truncation_suffix = f"\n<truncated: response exceeded 1 MB cap (full size: {original_size} bytes)>".
      - else: truncated = False; truncation_suffix = "".
      - try: text = body_bytes.decode("utf-8", errors="strict").
      - except UnicodeDecodeError: ct = resp.headers.get("content-type", "unknown"); self.emit_response("web_fetch", url, resp.status_code, len(body_bytes), duration_ms); return f"<error: binary response: content-type={ct}>".
      - self.emit_response("web_fetch", url, resp.status_code, len(body_bytes), duration_ms).
      - return text + truncation_suffix.

    Decode strategy choice: SPEC says "best-effort decode". Pick strict for now so binary content cleanly triggers the binary-error envelope. Document the choice in fetch()'s docstring.

    Edit voss/harness/tools.py:
    - At top, remove the TYPE_CHECKING forward-ref dance from T3-02 (or keep it; both work — see below) and add a runtime import OR use the TYPE_CHECKING-only import T3-02 added. Decision: keep TYPE_CHECKING-only for `NetSession`, because make_toolset still accepts None and the type hint is the only consumer.
    - In make_toolset body (post-existing tool definitions, BEFORE the return dict), add a new tool definition:
      ```
      @tool(name="web_fetch", description="Fetch a URL via HTTP GET. Requires --allow-net. Body returned as UTF-8 text; responses >1 MB truncate; timeout clamped to [1, 120] seconds.")
      async def web_fetch(url: str, timeout_s: float = 30.0) -> str:
          if net is None:
              return "<error: net disabled: set tools.allow_net = true in harness.toml or pass --allow-net>"
          return await net.fetch(url, timeout_s=timeout_s)
      ```
    - In the registration return dict (lines 196-207), add the entry: `"web_fetch": ToolEntry(descriptor=web_fetch, is_mutating=False, is_network=True)`. Place after the existing `voss_check` or whichever is last; preserve dict ordering for telemetry consistency.

    Edit voss/harness/cli.py:
    - Add imports at top: `from voss.harness.net import NetSession; from voss.harness.config import get_net_rate_limits`.
    - At module level, AFTER the existing `configure(max_iterations=..., max_parallel_reads=..., allow_net=...)` call from T3-02, add: `_NET_SESSION: "NetSession | None" = None` and a lazy constructor:
      ```
      def _get_net_session() -> "NetSession":
          global _NET_SESSION
          if _NET_SESSION is None:
              _NET_SESSION = NetSession(rate_overrides=get_net_rate_limits())
          return _NET_SESSION
      ```
      Rationale for laziness: prevents test-import-time httpx allocation; matches T1-04/T2-02 boot-configure-but-not-construct pattern.
    - Locate every `make_toolset(cwd)` call site (`grep -n "make_toolset" voss/harness/`). At least one is in cli.py's _resolve_run_turn (line ~174 — read to confirm); there may be more in agent.py. Update each cli.py call site to: `make_toolset(cwd, net=_get_net_session())`. If make_toolset is called from agent.py, the call site must be adapted too — thread `net` through the runner API (or accept that agent.py reads `_get_net_session()` from cli at the dispatch site).

    Edit voss/harness/agent.py:
    - Audit every `gate.check(name, args, is_mutating=...)` call. Find with `grep -n "gate.check\|permission_gate.check\|\.check(" voss/harness/agent.py`. For each call inside the tool dispatch flow (where `entry` is the resolved ToolEntry from the toolset), change to: `gate.check(name, args, is_mutating=entry.is_mutating, is_network=entry.is_network)`. If a call site does NOT have access to `entry`, add the lookup. Closing T3-02's audit explicitly: this is the wiring task.
  </action>
  <verify>
    <automated>uv run python -c "from voss.harness.net import NetSession; s = NetSession(); print(type(s).__name__, list(s._buckets.keys()))" 2>&amp;1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "^class NetSession" voss/harness/net.py` returns 1 match
    - source assertion: `grep -cE "MAX_BYTES = 1_048_576" voss/harness/net.py` returns 1
    - source assertion: `grep -cE "follow_redirects=True" voss/harness/net.py` returns 1 (Pitfall 3 mitigated)
    - source assertion: `grep -cE "max_redirects=5" voss/harness/net.py` returns 1
    - source assertion: `grep -cE "lifecycle\.register_session" voss/harness/net.py` returns 1
    - source assertion: `grep -nE "telemetry\.redact_url" voss/harness/net.py | wc -l` >= 2 (used in emit_request + emit_response)
    - tools registration: `grep -nE '"web_fetch":\s*ToolEntry\(.*is_network=True' voss/harness/tools.py` returns 1 match
    - cli wire-in: `grep -nE "make_toolset\(.*net=" voss/harness/cli.py` >= 1 match
    - cli construction: `grep -nE "NetSession\(rate_overrides=" voss/harness/cli.py` returns 1 match
    - agent.py audit: `grep -nE "gate\.check.*is_network=" voss/harness/agent.py | wc -l` returns >= 1 (at least one tool-dispatch site passes is_network)
    - import smoke: `python -c "from voss.harness.net import NetSession; s = NetSession(); assert set(s._buckets.keys()) == {'web_fetch', 'web_search'}; print('OK')"` prints OK
    - regression: `uv run pytest tests/harness/test_lifecycle.py tests/harness/test_rate_limit.py tests/harness/test_allow_net.py -x -q` exits 0 (T3-01/02/04 tests still pass after import-time NetSession registration with lifecycle)
  </acceptance_criteria>
  <done>voss/harness/net.py exists with NetSession exporting _http, aclose, acquire, emit_request, emit_response, fetch; web_fetch registered as ToolEntry with is_network=True; cli.py lazily constructs NetSession and wires through make_toolset(cwd, net=_NET_SESSION); agent.py audit complete — all tool-dispatch gate.check calls pass is_network=entry.is_network; lifecycle reaping integrates cleanly via register_session.</done>
</task>

<task type="auto">
  <name>Task 2: 5 NET-01 web_fetch acceptance tests + extend test_zero_socket_invariant + un-skip test_mcp_bypasses_bucket</name>
  <files>tests/harness/test_web_fetch.py, tests/harness/test_allow_net.py, tests/harness/test_rate_limit.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-01 acceptance bullets a-e; NET-05f zero-socket; NET-07e MCP bypass)
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 4 — MockTransport pattern; Common Pitfall 3 — redirect default; Pitfall 5 — zero-socket bypass)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (Shared Patterns "asyncio.run() Wrapper for Sync Test Invocation"; PermissionGate Structural Denial Test Pattern)
    - voss/harness/net.py (just created in Task 1)
    - voss/harness/tools.py (post-Task-1 — web_fetch registration)
    - tests/harness/test_web_fetch.py (T3-01 scaffold — 5 placeholder skips to replace)
    - tests/harness/test_allow_net.py (T3-02 — test_zero_socket_invariant currently has gate-only proof; THIS plan extends it with MockTransport)
    - tests/harness/test_rate_limit.py (T3-04 left test_mcp_bypasses_bucket skipped; un-skip now)
    - tests/harness/test_tools.py (for asyncio_mode = auto pattern + existing make_toolset test invocation shape — `grep -n "make_toolset\|asyncio" tests/harness/test_tools.py | head -20`)
  </read_first>
  <action>
    Edit tests/harness/test_web_fetch.py — replace all 5 pytest.skip stubs.

    Imports: `import asyncio, httpx, pytest, warnings; from voss.harness.net import NetSession, MAX_BYTES; from voss.harness.tools import make_toolset; from voss_runtime import configure, reset_config; from pathlib import Path`.

    Helper at top of test file:
    ```
    def make_mock_handler(*, status=200, body=b"", content_type="text/plain", reason="OK", headers=None):
        def handler(request):
            hdr = {"content-type": content_type}
            if headers: hdr.update(headers)
            return httpx.Response(status_code=status, content=body, headers=hdr)
        return handler

    def make_session(handler) -> NetSession:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport, follow_redirects=True, max_redirects=5)
        return NetSession(client=client)
    ```

    Fixture: `@pytest.fixture(autouse=True) def _reset(): reset_config(); configure(allow_net=True); yield; reset_config()`.

    Tests:

    - `async def test_registration(tmp_path)` (NET-01a): `toolset = make_toolset(tmp_path, net=make_session(make_mock_handler(body=b"x")))`. Assert `"web_fetch" in toolset` and `toolset["web_fetch"].is_network is True` and `toolset["web_fetch"].is_mutating is False`.

    - `async def test_allow_net_gate(tmp_path)` (NET-01b): reset configure(allow_net=False). `toolset = make_toolset(tmp_path, net=None)` (simulates make_toolset call with no NetSession — D-08 path). `result = await toolset["web_fetch"].invoke_dict({"url": "https://x.com"})`. Assert result starts with `"<error: net disabled:"`. ALSO assert NO outbound socket: use a counting MockTransport that fails the test if handle_async_request is called.

    - `async def test_truncation(tmp_path)` (NET-01c): build 2 MB body: `big_body = b"a" * (2 * 1024 * 1024)`. `session = make_session(make_mock_handler(body=big_body))`. `result = await session.fetch("https://x.com")`. Assert `len(result.encode("utf-8")) >= MAX_BYTES`. Assert truncation marker present: `"<truncated: response exceeded 1 MB cap (full size: 2097152 bytes)>" in result`. Assert the first MAX_BYTES bytes of result encode to exactly the first MAX_BYTES bytes of big_body.

    - `async def test_timeout_clamp(tmp_path)` (NET-01d): call `await session.fetch("https://x.com", timeout_s=200.0)` while capturing warnings: `with warnings.catch_warnings(record=True) as w: warnings.simplefilter("always"); ... ;` Assert that exactly one RuntimeWarning was emitted, that the warning message contains "clamping" or "outside [", and that the call succeeded (returned a string, not an error envelope). Also test below-range: `timeout_s=0.0` clamps to 1.0 with warning. Also test in-range timeout_s=15.0 emits zero warnings.

    - `async def test_http_errors(tmp_path)` (NET-01e): `session = make_session(make_mock_handler(status=404, reason="Not Found"))`. `result = await session.fetch("https://x.com")`. Assert `result == "<error: http 404: Not Found>"`. Repeat for 500 ("Internal Server Error"), 503 ("Service Unavailable"). NO httpx.HTTPStatusError raised; envelope returned in all cases.

    Bonus tests (cement the contract):
    - `async def test_redact_url_in_emit(tmp_path)`: monkeypatch telemetry.emit to capture calls. Call `session.fetch("https://api.example.com/v1?token=secret")`. Assert NO captured emit event payload contains the substring "token=secret"; assert at least one payload contains "https://api.example.com/v1" (proves redact_url applied).

    - `async def test_rate_limit_returns_envelope(tmp_path)`: configure NetSession with a tight-bucket override: `session = NetSession(client=..., rate_overrides={"web_fetch": {"rate": 1, "burst": 1}})`. Call fetch twice in rapid succession. Assert first call succeeds; second call returns `"<error: rate limit: retry after 60s>"` (or close — use a regex match `r"<error: rate limit: retry after \d+s>"`).

    Edit tests/harness/test_allow_net.py — extend test_zero_socket_invariant:
    - Keep the existing gate-only proof body (added by T3-02). APPEND a second section with the MockTransport-counting variant:
      ```
      # Belt-and-suspenders: prove no HTTP call escapes when allow_net=False
      calls = [0]
      def counter(request):
          calls[0] += 1
          return httpx.Response(200, content=b"should-not-be-reached")
      transport = httpx.MockTransport(counter)
      client = httpx.AsyncClient(transport=transport)
      session = NetSession(client=client)
      # web_fetch tool body short-circuits at the disabled-error layer before reaching session.fetch
      reset_config(); configure(allow_net=False)
      toolset = make_toolset(tmp_path, net=None)  # D-08 None-path
      result = await toolset["web_fetch"].invoke_dict({"url": "https://x.com"})
      assert result.startswith("<error: net disabled:")
      assert calls[0] == 0  # zero-socket invariant proved at transport level
      ```
    - Add a second variant: configure(allow_net=True) but call gate.check directly first; even with allow_net=True, if the test bypasses tool dispatch and calls fetch directly through a session with the counter, the counter SHOULD increment to exactly 1. Document both paths in test docstring.

    Edit tests/harness/test_rate_limit.py — un-skip test_mcp_bypasses_bucket:
    - Remove the `pytest.skip("pending T3-05")` line.
    - Body: construct `session = NetSession(rate_overrides={"web_fetch": {"rate": 1, "burst": 1}})` (tight bucket). Exhaust web_fetch bucket: `ok, _ = session.acquire("web_fetch"); assert ok; ok, _ = session.acquire("web_fetch"); assert not ok`. Now call MCP-namespaced tool: `for _ in range(100): ok, retry = session.acquire("filesystem__read_text_file"); assert ok and retry == 0.0`. Proves MCP names (containing `__`) bypass the bucket entirely per D-16 + NET-07e.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_web_fetch.py tests/harness/test_allow_net.py tests/harness/test_rate_limit.py -x -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - skip count: `grep -c "pytest.skip" tests/harness/test_web_fetch.py tests/harness/test_rate_limit.py tests/harness/test_allow_net.py | head -3` returns 0 in each file
    - test count: `uv run pytest tests/harness/test_web_fetch.py --collect-only -q 2>&amp;1 | tail -5` shows 7 tests (5 acceptance + test_redact_url_in_emit + test_rate_limit_returns_envelope)
    - zero-socket assertion: `uv run pytest tests/harness/test_allow_net.py::test_zero_socket_invariant -x -q 2>&amp;1 | tail -5` exits 0 with "1 passed"
    - mcp bypass: `uv run pytest tests/harness/test_rate_limit.py::test_mcp_bypasses_bucket -x -q 2>&amp;1 | tail -5` exits 0
    - all NET-01: `uv run pytest tests/harness/test_web_fetch.py -x -q 2>&amp;1 | tail -3` shows all tests pass
    - regression: `uv run pytest tests/harness/test_lifecycle.py tests/harness/test_net_telemetry.py tests/harness/test_agent_config.py -x -q` exits 0
    - smoke command: `uv run pytest tests/harness/ -k "net or web_fetch or allow_net or rate_limit or telemetry or lifecycle" -x -q` exits 0
  </acceptance_criteria>
  <done>5 NET-01 acceptance tests + 2 bonus tests in test_web_fetch.py pass; test_zero_socket_invariant extended with MockTransport counter (transport-level zero-socket proof); test_mcp_bypasses_bucket un-skipped and green; Pitfall 3 (redirect default) and Pitfall 5 (zero-socket bypass) both covered by tests.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent loop calling web_fetch → outbound HTTP to arbitrary URL | The user's agent decides the URL. allow_net=False (T3-02) is the first defense; redact_url (T3-03) sanitizes telemetry; TokenBucket (T3-04) bounds frequency; 1 MB cap + 120s timeout (this plan) bound resource consumption per call. |
| Provider response → in-process buffer | Response bytes flow into a single bytes object; the 1 MB cap is enforced AT THE TOOL LEVEL before decode. httpx.AsyncClient default max-redirects=5 (set in constructor) bounds redirect-loop DoS. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T3-04 | DoS | web_fetch response unbounded → memory exhaustion | mitigate | MAX_BYTES = 1,048,576 enforced after resp.content read; original_size truncation marker preserved for transparency; test_truncation proves boundary |
| T-T3-05-01 | DoS | redirect loop via misbehaving server | mitigate | httpx.AsyncClient(max_redirects=5) constructor kwarg; httpx raises on exceed; raised exception returned as <error: http: ...> envelope (RESEARCH Pitfall 3) |
| T-T3-05-02 | DoS | hostile server hangs response indefinitely | mitigate | per-call timeout clamped to [1, 120] seconds; httpx.TimeoutException returns <error: timeout after Ns>; never raises |
| T-T3-05-03 | Info Disclosure | URL `?api_key=...` in telemetry | mitigate | every emit_request / emit_response calls telemetry.redact_url(url); test_redact_url_in_emit proves no `token=secret` substring escapes |
| T-T3-05-04 | DoS | binary payload (PDF, image) consumed as text | mitigate | UTF-8 strict decode + UnicodeDecodeError catch returns <error: binary response: content-type=...> envelope |
| T-T3-01 (revisit) | Elevation | allow_net default = True bypass | mitigate | NET-05f extended at transport level: MockTransport.call_count == 0 when allow_net=False (test_zero_socket_invariant variant) |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_web_fetch.py tests/harness/test_allow_net.py tests/harness/test_rate_limit.py -x -q` exits 0
- `grep -nE "MAX_BYTES\s*=\s*1_048_576" voss/harness/net.py` returns 1 match
- `grep -nE "follow_redirects=True|max_redirects=5" voss/harness/net.py | wc -l` returns 2 (both kwargs present)
- `grep -nE "telemetry\.redact_url" voss/harness/net.py | wc -l` returns >= 2 (used in both emit_request + emit_response)
- agent.py audit: `grep -nE "gate\.check.*is_network" voss/harness/agent.py | wc -l` >= 1
- `python -c "from voss.harness.tools import make_toolset; from pathlib import Path; ts = make_toolset(Path('.')); e = ts['web_fetch']; print(e.is_network, e.is_mutating)"` prints `True False`
</verification>

<success_criteria>
- NetSession ships with all 6 surface methods (_http, aclose, acquire, emit_request, emit_response, fetch)
- web_fetch tool registered with is_network=True; body short-circuits to disabled-error when net is None (D-08)
- All 5 NET-01 acceptance tests pass; 2 bonus tests cover redaction + rate-limit envelope shape
- NET-05f zero-socket invariant proved at transport level (MockTransport.call_count == 0)
- NET-07e test_mcp_bypasses_bucket un-skipped (MCP-namespaced names bypass acquire)
- cli.py boots NetSession lazily; make_toolset wired through; agent.py gate.check audit closed
- lifecycle.register_session called by NetSession.__init__ — reap_all() will close the AsyncClient
</success_criteria>

<output>
Create `.planning/phases/T3-network-surface/T3-05-SUMMARY.md` when done: report NetSession public API + exact line counts; list which agent.py call sites were audited and updated; cite test_truncation exact byte boundary observed in the truncated output; pytest output for all three modified test files; note that T3-06 (web_search) will extend NetSession with `async def search(query, count)` reusing this NetSession instance.
</output>
