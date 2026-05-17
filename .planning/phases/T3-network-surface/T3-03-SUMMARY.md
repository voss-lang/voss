---
phase: T3-network-surface
plan: 03
status: complete
---

# T3-03 Summary — redact_url + event-shape contract

## redact_url signature + location

`voss/harness/telemetry.py:133` — `def redact_url(url: str) -> str:` placed immediately after `redact_tool_args` (the documented peer position).

Implementation (stdlib only):

```python
def redact_url(url: str) -> str:
    if not isinstance(url, str):
        return "<redacted-url>"
    try:
        p = urlparse(url)
        host = p.hostname or ""
        netloc = host if p.port is None else f"{host}:{p.port}"
        clean = p._replace(query="", fragment="", netloc=netloc)
        out = urlunparse(clean)
        return out if isinstance(out, str) else "<redacted-url>"
    except Exception:
        return "<redacted-url>"
```

Imports: `from urllib.parse import urlparse, urlunparse` added at line 35 (top of stdlib imports block).

Strips query + fragment + userinfo. Preserves scheme + host + port + path. Non-str input or any parse failure returns `'<redacted-url>'`. Verified cases:

| Input | Output |
|---|---|
| `https://x.com/p?k=v#f` | `https://x.com/p` |
| `https://x.com/p` | `https://x.com/p` (no-op) |
| `https://user:pass@host/path` | `https://host/path` |
| `https://x.com:8443/p?k=v` | `https://x.com:8443/p` |
| `https://user:pass@host:8443/p?k=v#f` | `https://host:8443/p` |
| `None` / `12345` | `<redacted-url>` |
| `""` | `""` |
| `not-a-url` | `not-a-url` (urllib parses as path; pinned) |

## Event-shape contract docstring

Lines 10–28 of `voss/harness/telemetry.py` document the four T3 event kinds:

| kind | required data fields |
|---|---|
| `net.request`  | `tool: str, url: <redacted>, method: str, started_at: float` |
| `net.response` | `tool: str, url: <redacted>, status: int, bytes: int, duration_ms: int` |
| `mcp.request`  | `server: str, tool: str, args: dict (redact_tool_args), started_at: float` |
| `mcp.response` | `server: str, tool: str, status: "ok"|"error", duration_ms: int, error: str|None` |

D-15 invariant captured in the docstring: MCP stdio calls emit `mcp.*` only; HTTP/HTTPS calls emit `net.*` only — no overlap.

## 5 NET-06 tests — pytest output

```
$ uv run pytest tests/harness/test_net_telemetry.py -x -q
.....                                                                    [100%]
5 passed
```

1. `test_redact_url_strips` — NET-06a (query, fragment, userinfo stripped; userinfo+port combo).
2. `test_redact_url_noop` — NET-06b (clean URLs unchanged; port preserved; bad input → sentinel; pinned `not-a-url` behavior).
3. `test_event_emission` — NET-06c (net.request + net.response emitted with redacted url; secret never appears in payload).
4. `test_mcp_events` — NET-06d (mcp.request + mcp.response shape; D-15 invariant — no `net.*` events present in MCP-only capture).
5. `test_run_record_roundtrip` — NET-06e (pre-T3 RunRecord serializes via `asdict` → `json` and rehydrates without missing-field errors; iterations default-factory list preserved).

Regression: `uv run pytest tests/harness/test_telemetry.py tests/harness/test_net_telemetry.py tests/harness/test_allow_net.py tests/harness/test_lifecycle.py -x -q` → 21 passed. No existing telemetry test regressed; emit() / redact_tool_args signatures unchanged.

## Downstream consumers

- **T3-05 (web_fetch)** must `from voss.harness.telemetry import redact_url` and route every URL through it before constructing the `net.request` / `net.response` payloads per the docstring contract.
- **T3-06 (web_search)** ditto.
- **T3-07 (MCP)** uses `redact_tool_args` for `mcp.request.args` and emits `mcp.request` / `mcp.response` per the docstring contract; MCP stdio has no URL so `redact_url` is not required on that path.

The contract is documentation, not runtime validation — emit() remains generic on `data: dict`. T3-05/06/07 are responsible for constructing payloads that match the table.

## Schema-additivity invariant

NET-06e proves the additive contract: a pre-T3 `RunRecord` (no net.*/mcp.* events anywhere) round-trips through `asdict` + `json.dumps` + `json.loads` + `RunRecord(**…)` without raising. New event kinds live on the NDJSON sink (where emit writes), not on the `RunRecord` dataclass itself, so no schema migration is required.
