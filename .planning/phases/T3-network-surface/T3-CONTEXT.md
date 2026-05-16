# Phase T3: Network Surface (WebFetch + WebSearch + MCP client) — Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**SPEC:** `T3-SPEC.md` — 7 requirements locked (NET-01..NET-07), ambiguity 0.13

<domain>
## Phase Boundary

Wire three new network-capable agent-callable surfaces — `web_fetch`, `web_search` (Brave-backed), and an MCP stdio client — through a single new permission axis (`is_network` on `ToolEntry`) and a single new opt-in gate (`tools.allow_net` config + `--allow-net` CLI flag), without breaking M1..T2 invariants. Add per-tool token-bucket rate limiting, query-stripped URL telemetry (`net.request`/`net.response`/`mcp.request`/`mcp.response`), and a CI proof that the pinned Anthropic reference MCP filesystem server works end-to-end via `npx`. Requirements (WHAT) are locked by SPEC.md. This document captures HOW.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**7 requirements are locked.** See `T3-SPEC.md` for full requirements (NET-01..NET-07), boundaries, constraints, and 13 acceptance criteria.

Downstream agents MUST read `T3-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- `web_fetch(url, timeout_s)` HTTP GET, 1 MB cap, agent-callable
- `web_search(query, count)` Brave backend, env-key opt-in
- MCP stdio client subsystem: `voss/harness/mcp/{client,config,registry}.py`
- `.voss/mcp.yml` schema + loader
- `voss mcp list` and `voss mcp call <server> <tool> [args...]` CLI subcommands
- New `is_network: bool` axis on `ToolEntry`
- Permission gate denies `is_network=True` tools when `allow_net=False`
- `RuntimeConfig.allow_net: bool` + loader + CLI `--allow-net`
- `[mcp]` block in `permissions.yml` for per-server scope (`plan | edit | auto`)
- Per-tool token bucket rate limiting with `[net.rate_limits]` config
- `net.request`/`net.response`/`mcp.request`/`mcp.response` telemetry with `redact_url`
- CI integration job: `@modelcontextprotocol/server-filesystem` end-to-end
- M5 eval task #6 "fetch + summarize" via stub transport

**Out of scope (from SPEC.md):**
- Harness-as-MCP-server (M12 keeps server side)
- Streaming web_fetch / SSE / WebSocket
- web_fetch response caching
- Tavily search backend
- DuckDuckGo HTML scraping
- HTTP MCP transport (stdio only)
- Additional reference MCP servers in CI (filesystem only)
- Per-host rate limiting (per-tool only)
- POST/PUT/DELETE in web_fetch
- Path-jail / shell-allowlist for network tools

</spec_lock>

<decisions>
## Implementation Decisions

### MCP subsystem shape

- **D-01:** Module layout = three files under `voss/harness/mcp/`: `client.py` (stdio JSON-RPC client, lift Codex's launcher pattern adapted to stdlib `asyncio.subprocess`), `config.py` (`.voss/mcp.yml` schema + loader), `registry.py` (`ToolEntry` adapter — turns advertised MCP tool descriptors into `is_network=True` `ToolEntry` records). Mirrors what `voss/harness/lsp/` will eventually look like when M10 ships. No deeper split — single-transport scope doesn't justify {transport,protocol,session,...}.
- **D-02:** Lazy-launch trigger = on first tool call for that server. Registry returns proxy `ToolEntry` records whose body calls `await McpClient.ensure_launched(server)` on entry. Unused servers in `.voss/mcp.yml` never spawn a subprocess. Mirrors LSP-on-first-symbol design (target pattern; not yet shipped).
- **D-03:** Reap-on-exit hook lives in a new `voss/harness/lifecycle.py` module (greenfield). Registers a single `atexit`-style cleanup that MCP (and future LSP) subscribers register subprocess handles into. SIGTERM with a 5.0-second deadline before SIGKILL fallback (matches SPEC NET-03 acceptance c). **Open question:** when M10 ships LSP, it migrates onto the same hook; T3 is the first user. Researcher: investigate whether `voss/harness/agent.py` shutdown path or `voss_runtime.configure` has an existing teardown registration point to attach to before adding a new module.
- **D-04:** `.voss/mcp.yml` schema features (all four ship in v0.2):
  - `${VAR_NAME}` env-var interpolation in `command` and `args` (raises if var unset and field is required).
  - `{cwd}` templating substituted by `Path.cwd()` at launch time.
  - Per-server `timeout_s: <float>` override for MCP stdio calls (defaults to 30.0 if absent).
  - Per-server `env: [PATH, HOME, ...]` allowlist — subprocess starts with empty env, only listed vars passed through. If `env` omitted, full parent env is inherited (back-compat default).

### httpx + tool plumbing

- **D-05:** Single shared `httpx.AsyncClient` instance for both `web_fetch` and `web_search`, lazily constructed on first net call, stored as `NetSession._client`. Lifetime tied to the same `lifecycle.py` reap hook from D-03 — `await NetSession.aclose()` runs alongside MCP subprocess reaping. Matches `voss/harness/providers.py:68–73` lazy pattern. Connection pooling reused across the two web tools.
- **D-06:** `NetSession` class lives in a new `voss/harness/net.py` module. Owns: lazy `AsyncClient`, per-tool `TokenBucket` registry, `redact_url` helper invocation, `telemetry.emit` wrappers for `net.request`/`net.response`. Tests at `tests/harness/test_net.py`. Sibling module to `tools.py`, parallel to `mcp/` package.
- **D-07:** Brave backend lives in a flat `voss/harness/web_search.py` with a single `BraveBackend(api_key)` class exposing `async def search(query, count) -> list[SearchResult]`. The `web_search` tool body (in `tools.py`) instantiates `BraveBackend` lazily, formats results into the deterministic bundle string per SPEC NET-02. **No `WebSearchBackend` protocol abstraction in T3** — SPEC explicitly says Brave only; abstraction lands when Tavily ships (v0.3+).
- **D-08:** `make_toolset(cwd)` gains an optional kwarg: `make_toolset(cwd, *, net: NetSession | None = None)`. When `net is None` (e.g., unit tests, non-net code paths), the three new net tools register but their bodies short-circuit to the disabled-error envelope (`<error: net disabled: ...>`). When `net` is provided by the runtime bootstrap, tools wire to the real session. Backward compatible — every existing `make_toolset(cwd)` call site keeps working unchanged.

### Permission gate integration

- **D-09:** `is_network: bool = False` is a stored field on the `ToolEntry` dataclass, set at registration time inside `make_toolset` (and the MCP `registry.py` adapter). Mirrors the existing `is_mutating` shape. Tests assert via `entry.is_network`. No name-prefix sniffing, no decorator metadata indirection. New axis is additive to `ToolEntry` — does NOT replace `is_mutating`; both are independent.
- **D-10:** `PermissionGate.check` order extends from `auto_yes → mode-tier (is_mutating) → deny-rules → prompt/diff` to `auto_yes → net-check (is_network + allow_net) → mode-tier → deny-rules → prompt/diff`. The net-check fires BEFORE the mode-tier check — if `tool_entry.is_network is True` and `runtime.allow_net is False`, return `(False, "net disabled: set tools.allow_net = true in harness.toml or pass --allow-net")` and emit NO telemetry (no `net.request` event on denial — the call never happened). Fail-fast before any allow_net=True path runs.
- **D-11:** MCP per-server scope (`permissions.yml` `mcp: { filesystem: edit }`) is applied at **registration time** inside the MCP `registry.py` adapter. When the MCP client launches a server and pulls its advertised tools, the adapter reads the `mcp:` block from the loaded `PermissionsConfig`:
  - Under default/`plan` scope: every advertised tool registers with `is_mutating=False`. Subsequent `PermissionGate.check` under `mode=plan` (which denies mutating tools by tier) still allows reads; mutation attempts are deniable but mostly never reach the gate because the advertised tool isn't registered as mutating.
  - Under `edit`/`auto` scope: the adapter consults the server's advertised tool descriptor `destructiveHint` (MCP protocol metadata). If `destructiveHint=true`, `is_mutating=True`. If absent or false, `is_mutating=False`. Default-to-`True` is the safe fallback when the field is absent — destructive operations are easier to deny than to undo.
  - `PermissionGate` itself remains MCP-unaware. Single source of truth for MCP-vs-builtin distinction is at registration.
- **D-12:** Denial UX = tool result string `<error: net disabled: ...>` (or `<error: denied by mcp scope: filesystem at plan, requires edit>` for MCP scope denial). Mirrors existing `<error: ...>` convention from `fs_read`/`fs_edit` denial paths. Agent observes the string in the next turn; `Recorder.tool_result` logs it with `ok: false`. No renderer banner. No new exception type to plumb. Identical to today's `denied by mode plan` flow.

### CLI + telemetry wiring

- **D-13:** CLI surface = argparse subparser at `voss mcp {list,call}`, matching existing `voss check` / `voss compile` style.
  - `voss mcp list` — pretty default (one server per block: name, command, advertised tools). `--json` flag emits machine-readable JSON.
  - `voss mcp call <server> <tool> [--arg key=value]...` — debug invocation. Bypasses `PermissionGate` (developer tool — implies explicit trust). Output printed to stdout, exit code 0 on success, 1 on protocol/transport error, 2 on server-side tool error.
- **D-14:** Tool-call kwarg syntax = `--arg key=value` repeatable. Values parsed as JSON when they look like JSON (`true`, `42`, `["a","b"]`, `null`); otherwise treated as raw strings. Example: `voss mcp call filesystem read_file --arg path=./README.md --arg encoding=utf-8`. Matches `kubectl --from-literal` ergonomics. JSON typing is parser-best-effort, not strict — invalid JSON-looking values fall back to string.
- **D-15:** `redact_url(url: str) -> str` lives as a pure function in `voss/harness/telemetry.py` alongside the existing `redact_tool_args`. Behavior: strip `?query` and `#fragment`; preserve scheme + netloc + path. `NetSession.emit_request(...)` and `NetSession.emit_response(...)` (the only call sites for `net.request`/`net.response` events) pass URL fields through `redact_url` before constructing the event payload. MCP variant: `mcp.request`/`mcp.response` events apply `redact_url` only to any URL fields in payloads (typical MCP stdio calls don't carry URLs — most events will have no redaction work to do). Pure-function tests assert the strip rule independent of emit plumbing.
- **D-16:** Rate-limit integration = `NetSession.acquire(tool_name: str) -> AcquireResult` called as the first line of each net tool body. Returns `AcquireResult.ok` (continue) or `AcquireResult.rate_limited(retry_after_s)`; the tool's body checks and returns `<error: rate limit: retry after Ns>` on the limited path. MCP tools do NOT call `acquire` (SPEC NET-07: MCP unlimited). Bucket registry keyed by tool name (`web_fetch`, `web_search`). Defaults from SPEC: `web_fetch = TokenBucket(rate_per_min=30, burst=30)`, `web_search = TokenBucket(10, 10)`. Override via `harness.toml` `[net.rate_limits]` parsed in `_config.py`. Buckets are per-`NetSession` instance — fresh per `voss` invocation (per-session reset).

### Claude's Discretion

These were not asked but are implementation-natural; downstream agents may pick reasonable shapes:

- Exact MCP JSON-RPC protocol version (latest stable at execute time).
- Exact `httpx.AsyncClient` constructor kwargs (`http2=True/False`, `verify=True`, `follow_redirects=True` with sane max-hops).
- `voss mcp list --json` exact JSON shape (suggest: `{"servers": [{"name": ..., "command": [...], "tools": [...]}]}`).
- `tests/perf/` vs `tests/harness/` placement for the rate-limit deterministic-clock tests.
- Whether `redact_url` strips userinfo (`https://user:pass@host/path`) — recommend yes; not in SPEC.
- Whether `web_search` deduplicates result URLs — SPEC silent; recommend yes (dedup-by-url, preserve first occurrence).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase artifacts (locked)

- `.planning/phases/T3-network-surface/T3-SPEC.md` — **Locked requirements (NET-01..NET-07) — MUST read before planning. 13 pass/fail acceptance criteria.**
- `.planning/ROADMAP.md` §"Phase T3 — Network Surface" — phase goal and cross-cutting constraints.
- `.planning/REQUIREMENTS.md` SCOPE-04, DIST-03 — original defer-MCP-bridge decisions that T3 unwinds for the client side.

### Codebase anchors (read before touching)

- `voss/harness/tools.py:14..200` — `ToolEntry`, `make_toolset`, existing `@tool` decorator pattern, `is_mutating` axis (D-09 extends this).
- `voss/harness/permissions.py:42..200` — `PermissionGate.check`, `Mode = Literal["plan","edit","auto"]`, `PermissionsConfig` consumer site (D-10/D-11 modify ordering here).
- `voss/harness/providers.py:55..80` — lazy `httpx.AsyncClient` pattern to mirror in `NetSession` (D-05).
- `voss/harness/auth.py:24,185..260` — existing httpx sync usage (do NOT copy this pattern; net tools must be async per SPEC threading invariant).
- `voss/harness/telemetry.py` — `emit`, `redact_tool_args`; add `redact_url` alongside (D-15).
- `voss/harness/cognition_schemas.py:51` — `PermissionsConfig` pydantic model (D-11 extends with `mcp: dict[str, McpScope]`).
- `voss/harness/agent.py:275..585` — `telemetry.emit` call sites for reference shape.
- `voss_runtime/_config.py` — `RuntimeConfig` dataclass to extend with `allow_net: bool = False` (NET-05) and `[net.rate_limits]` parsing (D-16).
- `voss/harness/cli.py` (path inferred from T2-02 plans) — bootstrap site for `--allow-net` flag.

### Cross-phase context

- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-04-PLAN.md` — `[agent]` TOML loader pattern; T3 extends with `[tools]` + `[net.rate_limits]` block (mirror the regex + range-fallback shape).
- `.planning/phases/T2-parallel-tools-multi-edit/T2-02-PLAN.md` — `agent.max_parallel_reads` config-knob flow (T3 mirrors for `tools.allow_net`).
- `.planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md` D-15 — confirms "T2 owns config-loader extensions, T3 extends further with `[tools]` namespace".

### External protocol

- MCP protocol spec — Anthropic-published. Researcher pins the exact version + URL at research time. Specifically the JSON-RPC framing, the tool-discovery `tools/list` request, and the `destructiveHint` field in tool descriptor metadata (referenced in D-11).
- Brave Search API docs — endpoint `https://api.search.brave.com/res/v1/web/search`, `X-Subscription-Token` auth header, response shape. Researcher pins.
- Anthropic reference MCP filesystem server: `@modelcontextprotocol/server-filesystem` on npm. Version pin in CI fixture is chosen at SPEC-write time and bumped manually.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`httpx.AsyncClient` lazy-init pattern** at `voss/harness/providers.py:55–73` — exact shape `NetSession` should adopt for its shared client.
- **`@tool` decorator + `ToolEntry` dataclass** at `voss/harness/tools.py:14–44` — extends additively with `is_network` field (D-09).
- **`telemetry.emit` + `redact_tool_args`** at `voss/harness/telemetry.py` — `redact_url` slots in alongside as a peer pure function (D-15).
- **`PermissionGate.check` mode-tier flow** at `voss/harness/permissions.py:155–185` — net-check inserts after `auto_yes`, before mode-tier (D-10).
- **`PermissionsConfig` pydantic schema** at `voss/harness/cognition_schemas.py:51` — extends with `mcp: dict[str, McpScope] = Field(default_factory=dict)`.
- **`RuntimeConfig` config-load pattern** (established by T1-04, extended by T2-02) — `voss_runtime/_config.py` adds `allow_net: bool = False` and `[net.rate_limits]` block parsing.
- **`make_toolset(cwd)` factory** at `voss/harness/tools.py:44` — gains `*, net: NetSession | None = None` kwarg (D-08); existing call sites unaffected.

### Established Patterns

- **`<error: ...>` envelopes** as tool result strings — `fs_read`, `fs_edit`, denied-by-mode all use this. Net tools follow suit (D-12).
- **`is_mutating` boolean on ToolEntry** drives mode-tier denial. `is_network` is the parallel new axis (D-09).
- **Lazy + reap pattern** — providers.py constructs `AsyncClient` lazily and `aclose()`s on shutdown. T3 generalizes via `lifecycle.py` (D-03) so MCP subprocesses + the NetSession client share one shutdown path.
- **Stdlib-only async I/O** — `asyncio.subprocess` for MCP, `httpx.AsyncClient` for web tools. No new external deps (SPEC Constraints).
- **Per-session state on a singleton owned by the bootstrap** — `voss_runtime.configure(...)` already holds `RuntimeConfig`; NetSession is a peer runtime singleton attached via the bootstrap (D-06).

### Integration Points

- **`PermissionGate.check`** — net check inserts before mode-tier check; MCP unaware (D-10, D-11).
- **`make_toolset`** — accepts `net` kwarg; new tools register with `is_network=True` (D-08, D-09).
- **`voss_runtime.configure`** — gains `allow_net` and `net_rate_limits` knobs; CLI bootstrap reads `--allow-net` and writes through (NET-05, D-16).
- **`telemetry.emit`** — receives `net.request`/`net.response`/`mcp.request`/`mcp.response` events from `NetSession`; payloads pre-redacted (D-15).
- **`atexit`-style cleanup** — new `lifecycle.py` reap hook owns MCP subprocess SIGTERM + NetSession.aclose() (D-03, D-05).
- **`permissions.yml`** — extended `mcp:` block per server scope (D-11) flows into MCP `registry.py` at server-launch time.

</code_context>

<specifics>
## Specific Ideas

- **Lift Codex's MCP launcher pattern** (Round 1 decision). Researcher: identify the upstream Codex repo file path, extract the stdio framing logic, adapt to voss's stdlib-only constraint (no Codex-specific deps).
- **Anthropic reference filesystem server validates "MCP works"** (SPEC Success Criteria #2). CI job invokes `npx -y @modelcontextprotocol/server-filesystem@<pinned-version>` against the project root and reads back `README.md` via `filesystem__read_file`.
- **kubectl `--from-literal` ergonomics** for `voss mcp call --arg` syntax (D-14). JSON-typed values when they parse, string fallback otherwise.
- **Failure-mode demo:** `voss do "fetch httpbin.org"` with no `--allow-net` and no `tools.allow_net = true` must produce **zero outbound sockets** — verified by `httpx` `MockTransport` interceptor counting zero calls (SPEC AC bullet). This is the load-bearing safety invariant.

</specifics>

<deferred>
## Deferred Ideas

- **Tavily search backend** — Brave-only ships in T3. Add Tavily + `WebSearchBackend` protocol abstraction when demand surfaces (v0.3+ candidate phase).
- **HTTP MCP transport** — stdio only in T3. HTTP MCP spec stabilizes later; validate after stdio settles in production.
- **Per-host rate-limiting** — per-tool only in T3. Per-host aggregation more accurate to backend limits but more complex; v0.3+.
- **Streaming web_fetch / SSE / WebSocket** — pulled back into scope mid-discussion (Round 4), then pushed back out (Round 5). Tool-result protocol shape (incremental events) is too disruptive for v0.2; revisit when a real streaming use case lands.
- **Response caching** — explicit out-of-scope. v0.3+ if cost-tracking on the agent loop shows repeated fetches dominating cost.
- **POST/PUT/DELETE web_fetch** — explicit out-of-scope. Threat surface much larger than GET; not needed for "live docs" use case.
- **MCP error-envelope normalization** — discussed as a potential 5th gray area, declined. Planner picks: distinguish transport errors (`<error: mcp transport: connection lost>`) from server-side tool errors (`<error: mcp tool: {server.error.message}>`).
- **MCP tool descriptor caching** — declined. Each session re-discovers tools on launch. Caching adds invalidation complexity.
- **`web_fetch` redirect handling** — declined as gray area. Planner picks: `follow_redirects=True`, max 5 hops, same-origin or cross-origin both allowed (HTTP GET only — read-only).
- **`web_search` result dedup / snippet truncation** — declined. Listed in Claude's Discretion above.
- **Reload `permissions.yml` mid-session for MCP scope changes** — out of scope. Scope is read at server-registration time only (D-11). Session restart required to change.

</deferred>

---

*Phase: T3-network-surface*
*Context gathered: 2026-05-15*
*Next step: /gsd:plan-phase T3 — research and plan*
