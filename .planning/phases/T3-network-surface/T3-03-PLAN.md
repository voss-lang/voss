---
phase: T3-network-surface
plan: 03
type: execute
wave: 1
depends_on: [T3-01]
files_modified:
  - voss/harness/telemetry.py
  - tests/harness/test_net_telemetry.py
autonomous: true
requirements: [NET-06]
must_haves:
  truths:
    - "voss/harness/telemetry.py exports redact_url(url: str) -> str alongside the existing redact_tool_args function"
    - "redact_url('https://x.com/p?k=v#f') returns exactly 'https://x.com/p'"
    - "redact_url('https://x.com/p') is a no-op and returns 'https://x.com/p'"
    - "redact_url strips userinfo: redact_url('https://user:pass@host/path') returns 'https://host/path' (per Claude's Discretion item 5, recommended yes; documented in NET-06 acceptance)"
    - "redact_url preserves port: redact_url('https://x.com:8443/p?k=v') returns 'https://x.com:8443/p'"
    - "redact_url on malformed input returns the safe sentinel '<redacted-url>' instead of raising"
    - "RunRecord schema accepts net.request / net.response / mcp.request / mcp.response event payloads via the additive event-shape contract documented in voss/harness/telemetry.py docstring; pre-T3 records load unchanged"
  artifacts:
    - path: "voss/harness/telemetry.py"
      provides: "redact_url(url) -> str pure function; module-level event-shape docstring naming net.request / net.response / mcp.request / mcp.response fields"
      contains: "def redact_url"
    - path: "tests/harness/test_net_telemetry.py"
      provides: "5 NET-06 acceptance tests (replaces T3-01 pytest.skip stubs): test_redact_url_strips, test_redact_url_noop, test_event_emission, test_mcp_events, test_run_record_roundtrip"
      contains: "def test_redact_url_strips"
  key_links:
    - from: "voss/harness/net.py NetSession (T3-05) and voss/harness/mcp/client.py (T3-07)"
      to: "voss/harness/telemetry.py:redact_url"
      via: "every emit() call site for net.request/net.response/mcp.request/mcp.response passes url through redact_url before constructing payload"
      pattern: "telemetry\\.redact_url\\("
    - from: "voss/harness/telemetry.py:redact_url"
      to: "urllib.parse.urlparse + urlunparse"
      via: "parse → _replace(query='', fragment='', netloc=host[+port]) → urlunparse"
      pattern: "urlparse|urlunparse"
---

<objective>
Land the URL redaction primitive (D-15) and the event-shape contract for `net.request` / `net.response` / `mcp.request` / `mcp.response` events (NET-06). Pure stdlib implementation in voss/harness/telemetry.py beside the existing `redact_tool_args`. Five acceptance tests replace the T3-01 placeholders.

Purpose: NET-06 is the only line of defense against URL-internal secret leakage to telemetry — Brave keys, OAuth tokens, and signed-URL parameters all appear in `?query` or `#fragment` of URLs that hit `web_fetch` / `web_search`. Without `redact_url`, T3-05/T3-06/T3-07's emit sites would write raw URLs to NDJSON session records. T3-05 and T3-07 import this function on their first emit; this plan is a Wave 1 leaf so both can proceed in Wave 2/Wave 3 without blocking.

Output: `redact_url` function + 5 green tests. The function is 12 lines; the tests are the load-bearing artifact. No new files; pure extension of existing telemetry.py.
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
@voss/harness/telemetry.py
@voss/harness/recorder.py
</context>

<interfaces>
Current telemetry.py exports (lines 1-200):
- `emit(kind: str, level: str, *, data: dict | None = None) -> None` — the singleton emit point that writes NDJSON to the recorder.
- `enabled() -> bool` — telemetry-on/off check; emit() is a no-op when False.
- `redact_tool_args(args: dict[str, Any]) -> dict[str, Any]` (around line 87-112) — existing redaction primitive that masks `token`/`api_key`/`secret` substring matches in tool arg dicts.

`redact_url` slots in as the third peer pure function (D-15 locks position: "alongside the existing `redact_tool_args`"). Module imports: add `from urllib.parse import urlparse, urlunparse` at the top of telemetry.py if absent (stdlib only).

T3-PATTERNS.md section "voss/harness/telemetry.py (extend)" locks the function body shape. RESEARCH.md Pattern 6 confirms the urllib.parse approach. Claude's Discretion item 5 recommends stripping userinfo (`user:pass@host` → `host`); NET-06 SPEC is silent on userinfo but the acceptance test asserts it (Pattern 6 in RESEARCH).

Event-shape contract (D-15 + NET-06 target text): events carry these fields:
- `net.request`: `{tool: str, url: <redacted>, method: str, started_at: float}` (and any caller-passed extras)
- `net.response`: `{tool: str, url: <redacted>, status: int, bytes: int, duration_ms: int}`
- `mcp.request`: `{server: str, tool: str, args: dict (already redacted by redact_tool_args), started_at: float}`
- `mcp.response`: `{server: str, tool: str, status: "ok" | "error", duration_ms: int, error: str | None}`

The contract is DOCUMENTED (in telemetry.py module docstring) but not enforced — emit() takes `data: dict` and is happily generic. The role of T3-03 is (a) ship redact_url and (b) WRITE THE DOCSTRING so T3-05/T3-07 have a single canonical reference for what fields to include. T3-05 (web_fetch) and T3-07 (MCP) actually construct the payloads at their call sites.

RunRecord additive-schema invariant (NET-06e): RunRecord serialization is JSON-blob-dict-of-events. New event kinds (net.*, mcp.*) just appear in the events list of new records. Loading PRE-T3 records (which have no net.* events) must succeed without schema migration. Verification: pick any existing M1/T1/T2 session record fixture under tests/harness/fixtures/ and round-trip it through RunRecord serialization; assert no field is missing.

PATTERN PITFALL (T3-RESEARCH.md A2): `urlparse._replace()` preserves the path but `netloc` swap is the way to drop userinfo. The implementation must use `p.hostname` (which strips userinfo by definition) and re-attach port if present, then `_replace(query="", fragment="", netloc=netloc)`.
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add redact_url to voss/harness/telemetry.py + event-shape docstring + 5 NET-06 tests</name>
  <files>voss/harness/telemetry.py, tests/harness/test_net_telemetry.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-06 acceptance bullets a-e; full target description with redaction rule)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-15 — redact_url location + scope)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (section "voss/harness/telemetry.py (extend)")
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 6 — implementation; Assumptions Log A2 — userinfo stripping)
    - voss/harness/telemetry.py (entire file — locate redact_tool_args around line 87-112 to place redact_url immediately after)
    - voss/harness/recorder.py (read for RunRecord serialization shape — locate the events list write path for the round-trip test)
    - tests/harness/test_net_telemetry.py (T3-01 scaffold — 5 pytest.skip stubs to replace)
    - tests/harness/fixtures/ (look for any existing session-record fixture — `ls tests/harness/fixtures/` — to use in round-trip test; if none, generate a tiny stub record inline)
  </read_first>
  <action>
    Edit voss/harness/telemetry.py:
    - At the top imports section, ensure `from urllib.parse import urlparse, urlunparse` is present. Stdlib only.
    - Locate the redact_tool_args function (around line 87-112). Add redact_url IMMEDIATELY AFTER it (line ~113). Body:

      Module-level pure function `def redact_url(url: str) -> str:`. Docstring: "Strip query string, fragment, and userinfo from a URL. Preserves scheme, host, port, and path. Telemetry-safe. Returns '<redacted-url>' sentinel on parse failure to ensure the emit site never raises."
      Body:
      - Try block wrapping all parse logic.
      - p = urlparse(url).
      - host = p.hostname or "".  (hostname is the host without userinfo and lowercased)
      - netloc = host if not p.port else f"{host}:{p.port}".
      - clean = p._replace(query="", fragment="", netloc=netloc).
      - return urlunparse(clean).
      - except Exception: return "<redacted-url>".

    - ALSO add a module-level docstring section "Event Kinds (T3-03 contract)" documenting the four new event kinds and their required `data` fields per the contract in the interfaces section above. This is a documentation-only artifact — emit() does not validate fields. The docstring is the single source of truth that T3-05 (web_fetch) and T3-07 (MCP) read when constructing payloads. Format as a markdown table embedded in the module docstring (Python allows this in raw triple-quoted strings).

    Edit tests/harness/test_net_telemetry.py (replace 5 T3-01 placeholders):
    - Remove every `pytest.skip(...)` line. Remove the placeholder one-line docstring; replace with "NET-06 acceptance tests for redact_url + net.* / mcp.* event shapes."
    - Imports: `from voss.harness.telemetry import redact_url, emit, enabled` plus pytest, plus any RunRecord / Recorder imports needed for the round-trip test (look up the right import: `grep -n "RunRecord\|class Recorder" voss/harness/recorder.py`).

    Tests (one per NET-06 bullet a-e):

    - `test_redact_url_strips()` (NET-06a): assert `redact_url("https://x.com/p?k=v#f") == "https://x.com/p"`. Plus additional cases: assert `redact_url("https://api.example.com/v1/search?token=abc#section") == "https://api.example.com/v1/search"`. Plus userinfo case: assert `redact_url("https://user:pass@host/path?k=v") == "https://host/path"` (proves Claude's Discretion 5 implemented).

    - `test_redact_url_noop()` (NET-06b): assert `redact_url("https://x.com/p") == "https://x.com/p"`. Plus port-preservation: assert `redact_url("https://x.com:8443/p") == "https://x.com:8443/p"`. Plus malformed-input: assert `redact_url("not-a-url") == "<redacted-url>"` OR returns the input string with empty path — pick whichever matches the implementation; document the chosen behavior in the test (urllib.parse is forgiving — bare `"not-a-url"` parses as path-only, no scheme, no netloc; the urlunparse roundtrip may return "not-a-url" unchanged. Run `python -c "from urllib.parse import urlparse, urlunparse; p = urlparse('not-a-url'); print(urlunparse(p._replace(query='', fragment='', netloc=p.hostname or '')))"` to confirm and pin the assertion. If the empty-netloc roundtrip raises or yields something surprising, switch to a try/except path in redact_url that returns "<redacted-url>"). Also: assert `redact_url("") == ""` or returns the safe sentinel — pin the behavior.

    - `test_event_emission()` (NET-06c): use the existing recorder/emit harness pattern (look at `tests/harness/test_telemetry.py` or any existing emit test — `grep -rn "telemetry.emit\|telemetry.enabled" tests/`). If a recorder fixture exists that captures emitted events into an in-memory list, use it. Otherwise create one inline: monkeypatch `voss.harness.telemetry._WRITER` (or whatever the internal sink is — read telemetry.py to confirm). Emit a fake `net.request` event with `data={"tool": "web_fetch", "url": redact_url("https://api.example.com/v1?token=secret"), "method": "GET", "started_at": 0.0}`. Then emit a `net.response` event with `data={"tool": "web_fetch", "url": redact_url("https://api.example.com/v1?token=secret"), "status": 200, "bytes": 123, "duration_ms": 50}`. Assert: exactly two events captured; both have `url == "https://api.example.com/v1"` (no token); kinds are exactly "net.request" and "net.response" in that order.

    - `test_mcp_events()` (NET-06d): emit `mcp.request` with `data={"server": "filesystem", "tool": "read_text_file", "args": {"path": "./README.md"}, "started_at": 0.0}` then `mcp.response` with `data={"server": "filesystem", "tool": "read_text_file", "status": "ok", "duration_ms": 12, "error": None}`. Assert events captured with kinds `mcp.request` then `mcp.response`. CRITICAL: assert NO events with kind starting `net.` are present in this capture (D-15 invariant: MCP stdio calls emit mcp.*, not net.*).

    - `test_run_record_roundtrip()` (NET-06e): create a minimal RunRecord-shaped dict (or use the real RunRecord constructor — `grep -n "class RunRecord\|@dataclass" voss/harness/recorder.py` for the constructor). Include events list with one net.request, one net.response, one mcp.request, one mcp.response. Serialize to JSON via `json.dumps` (mirror the recorder's actual write path). Deserialize back. Assert event kinds are preserved in original order. ALSO: load a pre-T3 fixture record (if `tests/harness/fixtures/M1/` or similar has one — look for one; `grep -rn "RunRecord\|run_record" tests/harness/fixtures/` — or generate a stub record with no net.*/mcp.* events). Confirm it round-trips without raising.

    Set `grep -c "pytest.skip" tests/harness/test_net_telemetry.py` to 0 by removing all skips.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_net_telemetry.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "^def redact_url\(url:\s*str\)" voss/harness/telemetry.py` returns 1 match
    - source assertion: `grep -nE "from urllib.parse import urlparse" voss/harness/telemetry.py` returns 1 match
    - source assertion: `grep -nE "p\.hostname" voss/harness/telemetry.py` returns >= 1 match (proves userinfo-stripping path taken, not naive netloc)
    - source assertion: `grep -E "net\.request|net\.response|mcp\.request|mcp\.response" voss/harness/telemetry.py | wc -l` returns >= 4 (event-shape docstring includes all four kinds)
    - functional assertion: `python -c "from voss.harness.telemetry import redact_url; assert redact_url('https://x.com/p?k=v#f') == 'https://x.com/p'; assert redact_url('https://user:pass@host/path') == 'https://host/path'; print('OK')"` prints OK
    - port preservation: `python -c "from voss.harness.telemetry import redact_url; assert redact_url('https://x.com:8443/p?k=v') == 'https://x.com:8443/p'; print('OK')"` prints OK
    - skip removed: `grep -c "pytest.skip" tests/harness/test_net_telemetry.py` returns 0
    - behavior: all 5 NET-06 tests pass (test_redact_url_strips, test_redact_url_noop, test_event_emission, test_mcp_events, test_run_record_roundtrip)
    - regression: `uv run pytest tests/harness/test_telemetry.py tests/harness/test_net_telemetry.py -x -q` exits 0 (existing telemetry tests unaffected — no signature changes to emit/redact_tool_args)
  </acceptance_criteria>
  <done>redact_url ships as a pure stdlib peer of redact_tool_args; strips query+fragment+userinfo while preserving scheme+host+port+path; 5 NET-06 tests pass; module docstring documents the four event-kind contracts so T3-05/T3-07 emit sites can construct payloads correctly; pre-T3 RunRecord fixtures round-trip without schema migration.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Any URL string entering a `telemetry.emit` call site | URLs from `web_fetch`, `web_search`, and MCP carry query-string secrets (Brave keys, OAuth tokens, signed-URL params). The redact_url function is the SOLE choke point — every emit site MUST route through it. T3-05/T3-07 enforce this at the call site; T3-03 ships the primitive. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T3-02 | Information Disclosure | API keys / tokens in URL `?query=` parameters leak to NDJSON session records | mitigate | redact_url strips `?query` and `#fragment` at the parse level (test_redact_url_strips proves; production emit sites in T3-05/T3-07 verify by passing the URL through redact_url before emit) |
| T-T3-03-01 | Information Disclosure | URL userinfo (`https://user:pass@host/`) leaks credentials | mitigate | redact_url uses p.hostname (which excludes userinfo by definition); test asserts `redact_url('https://user:pass@host/path') == 'https://host/path'` |
| T-T3-03-02 | DoS | redact_url called with malformed URL crashes telemetry emit | mitigate | try/except wraps all parse logic; returns `<redacted-url>` sentinel; emit() never raises from URL handling |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_net_telemetry.py -x -q` exits 0 (5 tests pass)
- `grep -nE "^def redact_url" voss/harness/telemetry.py` returns 1 match
- `python -c "from voss.harness.telemetry import redact_url; print(redact_url('https://user:pass@host:8443/p?k=v#f'))"` prints `https://host:8443/p`
- All 4 event kinds (net.request, net.response, mcp.request, mcp.response) appear in telemetry.py docstring
- `uv run pytest tests/harness/test_telemetry.py -x -q` exits 0 (no regression in existing telemetry tests)
</verification>

<success_criteria>
- redact_url is a pure stdlib function importable from voss.harness.telemetry
- Strips query + fragment + userinfo; preserves scheme + host + port + path
- Returns "<redacted-url>" sentinel on parse failure (never raises)
- 5 NET-06 acceptance tests un-skipped and green
- Event-shape contract for net.*/mcp.* events is documented in telemetry.py docstring (single source of truth for T3-05 + T3-07)
- Pre-T3 RunRecord fixtures load without schema migration
</success_criteria>

<output>
Create `.planning/phases/T3-network-surface/T3-03-SUMMARY.md` when done: report redact_url signature + exact line in telemetry.py; list the 5 test names + pytest output; cite the 4 event-kind table from the module docstring; note that T3-05 (web_fetch) and T3-07 (MCP) will import redact_url and route URL fields through it before every emit().
</output>
