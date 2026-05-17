---
phase: T3-network-surface
plan: 05
status: complete
---

# T3-05 Summary — web_fetch end-to-end (NetSession keystone)

## NetSession public API

`voss/harness/net.py` (172 lines). Constants: `MAX_BYTES = 1_048_576`, `MIN_TIMEOUT = 1.0`, `MAX_TIMEOUT = 120.0`, `DEFAULT_TIMEOUT = 30.0`.

| Method | Signature | Behavior |
|---|---|---|
| `__init__` | `(*, client=None, rate_overrides=None)` | builds per-instance bucket dict from `DEFAULT_SPECS` + TOML overrides; calls `lifecycle.register_session(self)` |
| `_http` | `() -> httpx.AsyncClient` | lazy; `follow_redirects=True, max_redirects=5, verify=True, timeout=Timeout(30), http2=False` |
| `aclose` | `async () -> None` | awaits `client.aclose()`; idempotent (nulls `_client`) |
| `acquire` | `(tool_name) -> tuple[bool,float]` | `"__" in name` → `(True,0.0)` (MCP bypass); unknown → `(True,0.0)`; else `bucket.acquire()` |
| `emit_request` | `(tool,url,method,started_at)` | `net.request` event; url via `telemetry.redact_url` |
| `emit_response` | `(tool,url,status,bytes_,duration_ms)` | `net.response` event; url via `telemetry.redact_url` |
| `fetch` | `async (url, *, timeout_s=30.0) -> str` | clamp→rate-gate→emit_request→GET→4xx/5xx envelope→1 MB cap→UTF-8 strict→emit_response |

`fetch` envelopes (never raises): `<error: rate limit: retry after Ns>` (N=`math.ceil`), `<error: timeout after Ns>`, `<error: http: …>`, `<error: net: ClassName: …>`, `<error: http {status}: {reason}>`, `<error: binary response: content-type=…>`. 1 MB cap fires on raw bytes BEFORE decode; truncation marker `\n<truncated: response exceeded 1 MB cap (full size: N bytes)>`.

## tools.py / cli.py / agent.py wiring

- `voss/harness/tools.py`: `web_fetch` `@tool` added before return dict; body short-circuits `<error: net disabled: …>` when `net is None` (D-08). Registered `"web_fetch": ToolEntry(descriptor=web_fetch, is_mutating=False, is_network=True)`.
- `voss/harness/cli.py`: module-level `_NET_SESSION` + lazy `_get_net_session()` (imports net/config inside fn — test-import never allocates httpx). All **3** `make_toolset(cwd, renderer=renderer)` call sites (lines 1071, 1314, 1710 — do_cmd, chat REPL, resume path) now pass `net=_get_net_session()`.
- `voss/harness/agent.py`: **T3-02 audit closure** — the single tool-dispatch `gate.check` call (now ~line 1018) passes `is_mutating=entry.is_mutating, is_network=entry.is_network`. This is the only `gate.check` call in agent.py; audit complete.

## test_truncation byte boundary observed

2 MB body (`b"a" * 2097152`). Truncated head `result.split("\n<truncated:")[0]` → `head.encode("utf-8")` length **exactly 1048576** (== `MAX_BYTES`), byte-equal to `big_body[:MAX_BYTES]`. Marker text `<truncated: response exceeded 1 MB cap (full size: 2097152 bytes)>` present.

## pytest output (modified files)

`uv run pytest tests/harness/test_web_fetch.py tests/harness/test_allow_net.py tests/harness/test_rate_limit.py -x -q` → **24 passed**.

- `test_web_fetch.py`: 7 tests (5 NET-01 acceptance: registration / allow_net_gate / truncation / timeout_clamp / http_errors + bonus redact_url_in_emit + rate_limit_returns_envelope). `--collect-only` = 7.
- `test_allow_net.py::test_zero_socket_invariant`: extended to `async`; gate-level proof + MockTransport counter (calls==0 on `net=None` path) + counter-proof (calls==1 when session used directly).
- `test_rate_limit.py::test_mcp_bypasses_bucket`: un-skipped — exhausts web_fetch bucket, then 100× `acquire("filesystem__read_text_file")` all `(True, 0.0)`.

Skip counts: `test_web_fetch.py`=0, `test_rate_limit.py`=0, `test_allow_net.py`=0.

## Regression

- T3 subset (`-k net|web_fetch|allow_net|rate_limit|telemetry|lifecycle|tools`): **110 passed**.
- Full harness (`--ignore tui --ignore tools` dirs): **617 passed, 13 skipped, 1 xfailed** (up from 594/28 post-T3-04; web_fetch+mcp_bypass added, zero_socket extended).

Two follow-on fixes for additive-signature ripple (surgical, traced to T3-05 changes):
1. `tests/harness/test_tools.py::test_mutating_count`: non-mutating count 7→8 (web_fetch is the 8th non-mutating tool).
2. `tests/harness/test_permissions.py` ×3: `_wrapped` gate.check monkeypatch stubs gained `is_network=False` kwarg + forward — they must mirror the real `gate.check` signature now that agent.py passes `is_network`.

## Handoff to T3-06

T3-06 (web_search) extends `NetSession` with `async def search(query, count)` reusing this same NetSession instance (the lazy `_get_net_session()` singleton already threads through all 3 cli call sites). `web_search` bucket already provisioned in `_buckets` (DEFAULT_SPECS has `web_search: (10,10)`); `acquire("web_search")` works today. T3-06 registers a `web_search` ToolEntry (`is_network=True`) and un-skips `tests/harness/test_web_search.py` (4 stubs). MCP tests (7 stubs) remain for T3-07.
