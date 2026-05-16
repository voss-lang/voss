# Phase T3: Network Surface (WebFetch + WebSearch + MCP client) — Specification

**Created:** 2026-05-15
**Ambiguity score:** 0.13 (gate: ≤ 0.20)
**Requirements:** 7 locked

## Goal

Ship three network-capable tool surfaces — `web_fetch(url)`, `web_search(query)` (Brave-backed), and an MCP stdio client — gated behind a single opt-in network permission (`tools.allow_net = true` OR `voss --allow-net`), with per-tool token-bucket rate limiting, query-string-stripped URL telemetry, and a CI proof that `voss mcp call filesystem read_file` works out-of-the-box against the pinned Anthropic reference MCP server.

## Background

Today `voss` has zero agent-callable network tools. `httpx` is vendored but only consumed by `voss/harness/auth.py:24` (OAuth refresh) and `voss/harness/providers.py:13` (LLM API calls) — neither path is reachable from `ToolEntry` or `make_toolset(cwd)` (`voss/harness/tools.py:44`). The `tools.allow_net` config flag is declared in `HARNESS-PLAN §6` but unenforced — nothing in `PermissionGate` (`voss/harness/permissions.py:42`) inspects it, and no tool registration checks it.

`PermissionGate` modes are `plan | edit | auto`. The `is_mutating` axis on `ToolEntry` drives mode-tier denial. There is **no `is_network` axis** today — adding network access requires extending the gate's classification layer.

`permissions.yml` schema exists (`PermissionsConfig` in `voss/harness/cognition_schemas.py:51`) and lists project-level allow/deny entries. No per-server MCP scope language exists.

No MCP code is in the tree (`grep -r mcp voss/ voss_runtime/` returns zero hits). M12 (MCP bridge) was originally scoped as both client + server; this phase carves the client side out — M12 reduces to "expose harness as MCP server only".

Telemetry emits via `telemetry.emit(...)` (heavily used in `voss/harness/agent.py:275..585`). No `net.request` / `net.response` event types exist.

Reuse targets: `httpx.AsyncClient` lifecycle pattern at `voss/harness/providers.py:68–73` (lazy construct, `aclose()` on shutdown), `@tool` decorator + `ToolEntry(descriptor, is_mutating)` registration shape in `tools.py:15..44`, telemetry-redaction at `voss/harness/permissions.py:182` (`telemetry.redact_tool_args`), and the existing `PermissionGate.check` mode-tier flow.

## Requirements

1. **NET-01 `web_fetch(url)` tool**: New agent-callable tool performs HTTP GET via `httpx.AsyncClient`, gated by `tools.allow_net`, capped at 1 MB response body.
   - Current: No `web_fetch` tool registered. `tools.allow_net` config flag declared but unenforced.
   - Target: New tool registered in `make_toolset` with `is_mutating=False`, `is_network=True`. Signature: `web_fetch(url: str, timeout_s: float = 30.0) -> str`. Body returned as UTF-8 (best-effort decode; binary fails with `<error: binary response: content-type=...>`). Responses > 1 MB truncate at exactly 1 MB and append a truncation marker matching `shell_run` convention: `\n<truncated: response exceeded 1 MB cap (full size: N bytes)>`. `timeout_s` clamped to `[1.0, 120.0]`.
   - Acceptance: pytest (a) registering `web_fetch` sets `is_network=True`; (b) `web_fetch("https://...")` without `tools.allow_net=true` returns exactly `<error: net disabled: set tools.allow_net = true in harness.toml or pass --allow-net>`; (c) `httpx`-mocked 2 MB response truncates at byte 1,048,576 and appends the marker with full size; (d) `timeout_s=200` clamps to 120 and emits a `RuntimeWarning`; (e) HTTP 4xx/5xx return `<error: http {status}: {reason}>` without raising.

2. **NET-02 `web_search(query)` tool — Brave backend**: New agent-callable tool searches via the Brave Search API, gated by `tools.allow_net` AND `BRAVE_SEARCH_API_KEY` env var.
   - Current: No `web_search` tool. No backend abstraction.
   - Target: New tool registered with `is_mutating=False`, `is_network=True`. Signature: `web_search(query: str, count: int = 10) -> str`. Returns a deterministic formatted bundle: one numbered section per result with `title`, `url`, and `snippet`. `count` clamped to `[1, 20]`. If `BRAVE_SEARCH_API_KEY` is unset, the tool returns `<error: web_search disabled: set BRAVE_SEARCH_API_KEY env var>` — even if `tools.allow_net=true`. Backend lives at `voss/harness/web_search.py` (greenfield module). No Tavily backend ships in T3 (deferred to v0.3 if demand surfaces).
   - Acceptance: pytest (a) `web_search("foo")` without key returns the disabled-error envelope; (b) with key + `tools.allow_net=true`, an `httpx`-mocked Brave response renders 10 results in stable order matching API order; (c) `count=50` clamps to 20 + `RuntimeWarning`; (d) Brave HTTP 429 returns `<error: rate limit: retry after Ns>` if `Retry-After` header present, else `<error: http 429: rate limited by backend>`.

3. **NET-03 MCP stdio client + `.voss/mcp.yml` config**: New MCP client subsystem launches MCP servers as stdio subprocesses, parses `.voss/mcp.yml` for server definitions, exposes each server's tools through the existing `ToolEntry` registry.
   - Current: Zero MCP code in tree. No `.voss/mcp.yml` schema.
   - Target: New module `voss/harness/mcp/` containing `client.py` (stdio JSON-RPC client lifted from Codex's `mcp/launcher.py` pattern, adapted to `httpx`-free stdio), `config.py` (`.voss/mcp.yml` schema + loader), and `registry.py` (turns advertised MCP tools into `ToolEntry` records with `is_network=True`). Each MCP server is launched lazily on first call to one of its tools. Process lifecycle: spawned on first use, reaped on session exit via the same `atexit`-style hook M10 uses for LSP processes (`voss/harness/lsp/*` — find and mirror). Per-server tools register with a `{server_name}__{tool_name}` namespaced key (e.g. `filesystem__read_file`) to prevent collisions with built-in tools.
   - Acceptance: pytest (a) `.voss/mcp.yml` loader parses the fixture `{"servers": {"filesystem": {"command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "{cwd}"]}}}` into a `McpServerConfig`; (b) launching the mocked filesystem server registers exactly the advertised tool names (`filesystem__read_file`, `filesystem__write_file`, `filesystem__list_directory`) in the toolset; (c) on session exit, all spawned MCP subprocesses receive SIGTERM within 5s and exit code is captured in telemetry; (d) a CI integration job runs `voss mcp call filesystem read_file path=./README.md` against the real pinned npm reference server and asserts non-empty output.

4. **NET-04 MCP permission scopes**: MCP tools default to `plan` scope (read-only); mutation requires per-server opt-in via a new `mcp` block in `permissions.yml`.
   - Current: `PermissionGate` has no MCP-aware logic. `permissions.yml` has no `mcp` block.
   - Target: Extend `PermissionsConfig` with `mcp: dict[str, McpScope]` where `McpScope = Literal["plan", "edit", "auto"]`. Default if a server is absent from the block: `"plan"` (read-only — all advertised MCP tools registered as `is_mutating=False`, mutation attempts denied). To allow mutation, user writes `mcp: { filesystem: edit }` in `permissions.yml` — the registry then re-classifies that server's advertised mutating tools as `is_mutating=True`. The MCP tool's "mutating" flag is sourced from the server's advertised tool descriptor metadata (MCP protocol's `destructiveHint` / annotations field); if absent, default to `is_mutating=True` (safe default).
   - Acceptance: pytest (a) loading `permissions.yml` with no `mcp` block keeps all MCP tools at `is_mutating=False`; (b) loading `mcp: { filesystem: edit }` flips `filesystem__write_file` (advertised destructive) to `is_mutating=True`; (c) calling `filesystem__write_file` under default scope returns `<error: denied by mcp scope: filesystem at plan, requires edit>`; (d) `mode=auto` + `mcp scope=plan` still denies mutating MCP tools — `auto` does NOT override per-server scope.

5. **NET-05 Network off by default**: `tools.allow_net` defaults to `false`. CLI flag `--allow-net` sets it true for the session. Config-file `[tools] allow_net = true` sets it true persistently. Without either, all `is_network=True` tools return the disabled-error envelope.
   - Current: Flag declared in HARNESS-PLAN §6, not enforced. No CLI plumbing.
   - Target: `RuntimeConfig.allow_net: bool = False` (greenfield field, mirrors T2's `max_parallel_reads` add pattern in `voss_runtime/_config.py`). Loader `get_allow_net()` reads `[tools] allow_net` from `harness.toml`. `cli.py` bootstrap reads CLI `--allow-net` flag (argparse store_true) and writes `configure(allow_net=True)`. CLI flag takes precedence over config file. The check fires at `PermissionGate.check` — when `tool_entry.is_network is True` and `runtime.allow_net is False`, return `(False, "net disabled: set tools.allow_net = true in harness.toml or pass --allow-net")` BEFORE the per-step prompt/diff flow.
   - Acceptance: pytest (a) default `RuntimeConfig().allow_net == False`; (b) `harness.toml` `[tools] allow_net = true` → loader returns True; (c) CLI `voss --allow-net do "..."` overrides config-file `false` to True; (d) `voss --allow-net=false` (explicit false) overrides config-file `true` to False; (e) `PermissionGate.check` on a `web_fetch` tool with `allow_net=False` returns `(False, "net disabled: ...")` BEFORE prompt logic fires; (f) integration test: `voss do "fetch example.com"` with no flag and no config never opens a socket (verified by `httpx` mock transport intercept counting zero calls).

6. **NET-06 Network telemetry events with redacted URLs**: New telemetry event types `net.request` and `net.response` emitted around every network tool call, with URL query strings and fragments stripped.
   - Current: No `net.*` event types. `telemetry.redact_tool_args` redacts args but not URL-internal secrets.
   - Target: New helper `telemetry.redact_url(url: str) -> str` strips `?query` and `#fragment`, preserving scheme + host + path. Example: `https://api.example.com/v1/search?token=abc#section` → `https://api.example.com/v1/search`. Emitted around every `web_fetch`, `web_search`, and MCP HTTP-class call (stdio MCP calls emit `mcp.request` / `mcp.response` instead — distinguished event names, same redaction rule applied to any URL fields in payloads). Events carry: `kind: "net.request"`, `tool: str`, `url: <redacted>`, `method: str`, `started_at: float`. Response event carries `status: int`, `bytes: int`, `duration_ms: int`. Both events go through existing `RunRecord` serialization additively.
   - Acceptance: pytest (a) `redact_url("https://x.com/p?k=v#f")` returns exactly `"https://x.com/p"`; (b) `redact_url("https://x.com/p")` is a no-op; (c) a `web_fetch("https://api.example.com/v1?token=secret")` call produces exactly one `net.request` event with `url == "https://api.example.com/v1"` and one `net.response` event; (d) MCP stdio call produces `mcp.request`/`mcp.response` events (NOT `net.*`); (e) `RunRecord` round-trip preserves both event types; pre-T3 records load unchanged (additive schema).

7. **NET-07 Per-tool token-bucket rate limiting**: Each network tool has an independent token bucket. Hitting the limit returns a fail-fast error envelope; no in-tool sleep.
   - Current: No rate limiting anywhere in the harness.
   - Target: New module `voss/harness/rate_limit.py` implementing `TokenBucket(rate_per_min: int, burst: int)`. Defaults: `web_fetch = TokenBucket(30, 30)`, `web_search = TokenBucket(10, 10)`, MCP tools = unbounded (backend's own limits apply). Each web tool acquires one token before issuing the request; on empty bucket, the call returns `<error: rate limit: retry after Ns>` where `N` is `ceil(seconds_until_next_token)`. Configurable per-tool via `harness.toml` `[net.rate_limits]` block: e.g. `web_fetch = "60/min"` or `web_fetch = { rate = 60, burst = 120 }`. Buckets are per-session (reset on new `voss` invocation).
   - Acceptance: pytest (a) `TokenBucket(60, 60)` permits 60 calls in a tight loop then errors on call 61 with the rate-limit envelope; (b) after 1.0s of wall-clock advance (test uses `monotonic` mock), one token replenishes; (c) `harness.toml` `[net.rate_limits] web_fetch = "60/min"` overrides the default; (d) `[net.rate_limits] web_fetch = { rate = 60, burst = 120 }` parses both fields; (e) MCP tool calls do NOT pass through the bucket (verified by counting non-rate-limited successful calls past the web_fetch default).

## Boundaries

**In scope:**
- `web_fetch(url, timeout_s)` agent-callable tool (HTTP GET only, full-body response, 1 MB cap)
- `web_search(query, count)` agent-callable tool (Brave backend, env-key opt-in)
- MCP stdio client subsystem: `voss/harness/mcp/{client,config,registry}.py`
- `.voss/mcp.yml` schema + loader
- `voss mcp list` CLI subcommand — prints registered servers + advertised tool names
- `voss mcp call <server> <tool> [args...]` CLI subcommand — debug invocation, bypasses agent loop
- New `is_network: bool` axis on `ToolEntry`
- New permission gate check: `is_network=True` AND `allow_net=False` → deny with fixed error envelope
- `RuntimeConfig.allow_net: bool` field + loader + CLI `--allow-net` flag
- New `[mcp]` block in `permissions.yml` schema with per-server scope (`plan | edit | auto`)
- Per-tool token-bucket rate limiting with `[net.rate_limits]` config block
- `net.request` / `net.response` / `mcp.request` / `mcp.response` telemetry events with `redact_url`
- CI integration job exercising the pinned Anthropic reference MCP filesystem server end-to-end via `npx`
- M5 eval gains task #6 "fetch + summarize" requiring `web_fetch` (Success Criteria #3 from ROADMAP)

**Out of scope:**
- **Expose harness AS MCP server (server side)** — M12 keeps server-side; T3 is client-side only
- **Streaming web_fetch / SSE / WebSocket** — HTTP GET, full body only. Streaming protocols defer to T3b or later (new tool-result protocol needed, plus mid-stream interrupt machinery)
- **web_fetch response caching** — no HTTP cache, no ETag handling, no offline replay. Each call goes out
- **Tavily search backend** — Brave only ships in T3. Tavily added in v0.3 if demand surfaces
- **DuckDuckGo HTML scraping backend** — rejected (fragile + rate-limited)
- **HTTP MCP transport** — stdio only in T3. HTTP MCP is newer spec, validate after stdio settles
- **Additional reference MCP servers in CI** — only the filesystem reference server is validated end-to-end. GitHub/Slack/etc. work as a side-effect but aren't gated by CI
- **Per-host rate limiting** — per-tool only. Per-host aggregation is more accurate but adds complexity; defer
- **POST / PUT / DELETE in web_fetch** — GET only. Write methods open a much bigger threat surface and aren't needed for the "live docs" use case
- **Path-jail or shell-allowlist applied to network tools** — sandbox is per-tool-class (ROADMAP cross-cutting constraint). Network tools use `allow_net` gate + URL redaction; no path or command allowlist

## Constraints

- **Response size cap (web_fetch):** exactly 1,048,576 bytes (1 MB). Over-cap truncates at the byte boundary and appends the truncation marker.
- **Network timeout default:** 30.0 seconds. Per-call override via `timeout_s` kwarg, clamped to `[1.0, 120.0]`. Out-of-range emits `RuntimeWarning` and falls back.
- **MCP stdio call timeout:** 30.0 seconds default, no per-call override in v0.2 (server-defined ceilings respected).
- **Rate-limit defaults:** `web_fetch` 30/min, `web_search` 10/min, MCP unlimited. Buckets are per-session, reset on new `voss` invocation.
- **URL redaction rule:** query string + fragment stripped. Path + host + scheme preserved. Applied uniformly to telemetry payloads, recorded session events, and any user-facing render of URLs that aren't the original user-supplied argument.
- **Brave API key location:** environment variable `BRAVE_SEARCH_API_KEY` only. No `harness.toml` storage (secrets in env-only convention from `auth.py`).
- **MCP reaping deadline:** SIGTERM on session exit, hard SIGKILL fallback after 5.0 seconds. Mirror M10 LSP-process cleanup pattern.
- **MCP filesystem reference server pin:** `@modelcontextprotocol/server-filesystem@<exact-version>` pinned in CI fixture. Version chosen at SPEC-write time; bump policy = manual.
- **No external Python dependencies added.** httpx already vendored. MCP stdio client uses stdlib `asyncio.subprocess`. Rate limiter is stdlib `time.monotonic`-based.
- **Threading invariant:** all network I/O routed through `asyncio` (no `httpx.Client` sync calls — only `AsyncClient`, matching `providers.py` pattern).

## Acceptance Criteria

- [ ] `pytest tests/harness/test_web_fetch.py -x` passes (all NET-01 cases: registration, off-default error, truncation, timeout clamp, HTTP error envelope)
- [ ] `pytest tests/harness/test_web_search.py -x` passes (all NET-02 cases: no-key error, Brave-mocked happy path, count clamp, 429 handling)
- [ ] `pytest tests/harness/mcp/ -x` passes (NET-03 + NET-04: config load, lazy launch, namespaced registration, scope enforcement, SIGTERM reaping)
- [ ] `pytest tests/harness/test_allow_net.py -x` passes (NET-05: default false, config load, CLI override precedence, gate denial, zero-socket invariant)
- [ ] `pytest tests/harness/test_net_telemetry.py -x` passes (NET-06: `redact_url` unit, event emission, MCP variant, RunRecord round-trip)
- [ ] `pytest tests/harness/test_rate_limit.py -x` passes (NET-07: TokenBucket unit, default rates, config override, MCP bypass)
- [ ] CI job `mcp-integration` runs `voss mcp call filesystem read_file path=./README.md` against the pinned `@modelcontextprotocol/server-filesystem` via `npx -y` and asserts the README content appears in output
- [ ] `voss mcp list` with no `.voss/mcp.yml` exits 0 with `<no MCP servers configured>` and exit code stays 0
- [ ] `voss mcp list` with a populated `.voss/mcp.yml` prints each server's name + advertised tool names
- [ ] `voss do "fetch httpbin.org"` with no flag and no `tools.allow_net` produces zero outbound sockets (integration test via `httpx` MockTransport count assertion)
- [ ] `voss --allow-net do "fetch httpbin.org"` with `BRAVE_SEARCH_API_KEY` unset succeeds for `web_fetch` and fails web_search with the disabled-error envelope
- [ ] No pre-T3 session record fails to load (additive schema invariant verified by replaying M1..T2 session fixtures through `RunRecord.from_dict`)
- [ ] M5 eval suite gains task #6 with a `task.toml` requiring `web_fetch` to succeed; `voss eval --stub` covers it via `httpx` stub transport

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                  |
|--------------------|-------|------|--------|------------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | 3 surfaces locked; backend pinned (Brave); single MCP ref server       |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | 10-item out-of-scope list, streaming/caching/Tavily/HTTP-MCP excluded  |
| Constraint Clarity | 0.85  | 0.65 | ✓      | 1MB cap, 30s timeout, redaction rule, rate-limit defaults all numeric  |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | 13 pass/fail checkboxes; every NET-* requirement has a pytest target   |
| **Ambiguity**      | 0.13  | ≤0.20| ✓      | All dimensions above minimum; gate solidly cleared                     |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                                                                |
|-------|-------------------|---------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| 1     | Researcher        | Ship all 3 surfaces or split? Search backend? MCP pattern? | All 3 ship together; web_search backend deferred to round 2 (user asked for market context); lift Codex MCP pattern |
| 2     | Simplifier + Boundary | Search backend (post-context); MCP server scope; out-of-scope multi-select | Brave only; Anthropic reference filesystem only; multi-select returned empty — re-asked round 3                |
| 3     | Boundary Keeper   | Out-of-scope confirm; size cap; timeout           | Caching OUT; 1 MB cap; 30s default / 120s ceiling                                                              |
| 4     | Failure Analyst   | Off-default proof; MCP CI proof; URL redaction; rate-limit + streaming IN/OUT | Pytest gate test; real npm CI server; query+fragment strip; rate-limit IN, streaming IN (reversed round 5) |
| 5     | Seed Closer       | Rate-limit granularity; rate-limit error shape; streaming shape | Per-tool token bucket (web_fetch 30/min, web_search 10/min, MCP unlimited); fail-fast `<error: rate limit: retry after Ns>`; streaming OUT (reverses round 4) |

---

*Phase: T3-network-surface*
*Spec created: 2026-05-15*
*Next step: /gsd:discuss-phase T3 — implementation decisions (how to build what's specified above)*
