# Phase T3 — Discussion Log

**Discussion date:** 2026-05-15
**Status:** Complete — CONTEXT.md written
**SPEC:** `T3-SPEC.md` (NET-01..NET-07, 7 reqs, ambiguity 0.13)
**Decisions captured:** D-01..D-16 (16 decisions across 4 areas)

This log is for human reference only — auditing, retrospectives, decision provenance. Downstream agents (researcher, planner, executor) read CONTEXT.md, not this file.

---

## Areas Selected

User selected all 4 candidate gray areas (multi-select):

- ☑ MCP subsystem shape
- ☑ httpx + tool plumbing
- ☑ Permission gate integration
- ☑ CLI + telemetry wiring

---

## Area 1: MCP subsystem shape

### Q1 — Module layout for MCP client?

**Options presented:**
1. `voss/harness/mcp/{client,config,registry}.py` (3 files) — *Recommended.* Mirror M10 LSP layout. (selected)
2. Single `voss/harness/mcp.py` file — risk of 600+ LOC monolith.
3. Deeper split `{transport,protocol,session,config,registry,errors}.py` — overengineered for single-transport scope.

**Selected:** Option 1. → **D-01** locked in CONTEXT.md.

### Q2 — Lazy-launch trigger — when does a server subprocess spawn?

**Options presented:**
1. On first tool call for that server — *Recommended.* Proxy ToolEntry triggers `ensure_launched`. (selected)
2. Eager at session start — all servers in mcp.yml launch on boot.
3. Eager on first `voss mcp list` only — hybrid, confusing semantics.

**Selected:** Option 1. → **D-02** locked.

### Q3 — Reap-on-exit hook — where does cleanup live?

**Options presented:**
1. Register via existing M10 LSP cleanup hook — *Recommended.* Find M10's atexit/SIGTERM handler. (selected)
2. Per-subsystem atexit handlers — two paths to maintain.
3. Tie to `RunRecorder.end_session()` — couples lifecycle to recorder.

**Selected:** Option 1.

**Note added during reflection:** `voss/harness/lsp/` does NOT exist yet (M10 not shipped). T3 must pioneer the shared `voss/harness/lifecycle.py` hook. Open question flagged for researcher: locate any existing teardown hook on `voss/harness/agent.py` shutdown path or `voss_runtime.configure` before adding a new module. → **D-03** locked with open-question annotation.

### Q4 — `.voss/mcp.yml` schema features (multi-select)?

**Options presented:**
1. Env-var interpolation `${VAR_NAME}` in command/args — (selected)
2. `{cwd}` templating — (selected)
3. Per-server timeout override — (selected)
4. Per-server env-var allowlist `env: [PATH, HOME, ...]` — (selected)

**Selected:** All four. → **D-04** locked.

---

## Area 2: httpx + tool plumbing

### Q1 — httpx AsyncClient lifecycle for web tools?

**Options presented:**
1. Single shared AsyncClient for web_fetch + web_search — *Recommended.* (selected)
2. Per-tool AsyncClient instances — loses connection pooling.
3. Per-call AsyncClient — anti-pattern per httpx docs.

**Selected:** Option 1. → **D-05** locked.

### Q2 — Where does NetSession live?

**Options presented:**
1. New `voss/harness/net.py` module — *Recommended.* (selected)
2. Attach to `voss_runtime.configure()` singleton — bloats runtime config.
3. Per-Agent instance attribute — wider plumbing change.

**Selected:** Option 1. → **D-06** locked.

### Q3 — Brave backend module shape?

**Options presented:**
1. Flat `voss/harness/web_search.py` with `BraveBackend` class — *Recommended.* (selected)
2. Pluggable `WebSearchBackend` protocol from day one — abstraction premature when only Brave ships.
3. Inline Brave call directly in tools.py — hard to test backend independently.

**Selected:** Option 1. → **D-07** locked.

### Q4 — Tool registration site?

**Options presented:**
1. `make_toolset(cwd, *, net: NetSession | None = None)` — *Recommended.* Backward compatible. (selected)
2. Separate `make_net_toolset(cwd, net)` merged at call site — two factories.
3. Auto-register at import via decorator side-effects — import-order coupling.

**Selected:** Option 1. → **D-08** locked.

---

## Area 3: Permission gate integration

### Q1 — `is_network` axis: stored or computed?

**Options presented:**
1. Stored field on `ToolEntry` — *Recommended.* Mirrors `is_mutating`. (selected)
2. Computed from tool-name prefix — brittle, fails for MCP namespacing.
3. Decorator metadata `@tool(network=True)` — more decorator surface.

**Selected:** Option 1. → **D-09** locked.

### Q2 — Where does `allow_net` check fire in `PermissionGate.check`?

**Options presented:**
1. BEFORE is_mutating tier-mode check, after auto_yes — *Recommended.* Fail-fast. No telemetry on denial. (selected)
2. Inside per-mode block — code duplication.
3. At tool body entry, not in gate — every new net tool re-implements.

**Selected:** Option 1. → **D-10** locked.

### Q3 — MCP scope re-classification timing?

**Options presented:**
1. At MCP server registration time — *Recommended.* Single source of truth in `registry.py`. PermissionGate stays MCP-unaware. (selected)
2. At `PermissionGate.check` time — gate becomes MCP-aware, leaky abstraction.
3. Hybrid (descriptor metadata + dynamic gate lookup) — most flexible, most complex.

**Selected:** Option 1. → **D-11** locked. Includes `destructiveHint` fallback to `is_mutating=True` (safe default) when MCP descriptor lacks the field.

### Q4 — Error envelope rendering?

**Options presented:**
1. Tool result string `<error: net disabled: ...>` — *Recommended.* Matches existing `<error: ...>` convention. (selected)
2. Raise `NetDeniedError` to iteration loop + renderer banner — agent doesn't see denial as tool result; loop-blind risk.
3. Both string + banner — redundant.

**Selected:** Option 1. → **D-12** locked.

---

## Area 4: CLI + telemetry wiring

### Q1 — `voss mcp` CLI subparser shape?

**Options presented:**
1. argparse subparser at `voss mcp {list,call}` — *Recommended.* Matches `voss check`/`voss compile` style. (selected)
2. Click-based CLI — adds dependency, inconsistent with existing CLI.
3. Single interactive REPL — heavyweight for debug surface.

**Selected:** Option 1. → **D-13** locked. `voss mcp list` defaults to pretty; `--json` for machine output. `voss mcp call` bypasses PermissionGate (debug tool, implicit trust).

### Q2 — `voss mcp call` arg syntax?

**Options presented:**
1. `--arg key=value` repeatable, JSON-typed when parseable — *Recommended.* kubectl `--from-literal` ergonomics. (selected)
2. Positional JSON blob — awkward quoting.
3. stdin JSON pipe — awkward for one-offs.

**Selected:** Option 1. → **D-14** locked.

### Q3 — `redact_url` placement?

**Options presented:**
1. Helper in `voss/harness/telemetry.py`; `NetSession` wraps before emit — *Recommended.* Pure function alongside `redact_tool_args`. (selected)
2. Auto-applied inside `telemetry.emit()` on `url` field — magic; surprises non-net events.
3. Per-tool call site — easy to forget; leak-by-omission risk.

**Selected:** Option 1. → **D-15** locked.

### Q4 — Rate-limit integration site?

**Options presented:**
1. Inside `NetSession.acquire(tool_name)` called by each net tool body — *Recommended.* MCP skips. (selected)
2. Gate-level — gate becomes net-aware in a third way; leaky.
3. Decorator `@rate_limited("web_fetch")` — magic; complicates @tool composition.

**Selected:** Option 1. → **D-16** locked.

---

## Done check

**Q:** All 4 areas covered. 16 decisions captured. More questions or write CONTEXT.md?
**A:** "I'm ready for context" — proceed to write.

---

## Scope creep redirects

None — discussion stayed strictly within phase boundaries. Every option presented was a HOW-question, never WHETHER-to-add. SPEC.md lock prevented scope drift.

## Deferred ideas captured

11 ideas deferred (see CONTEXT.md `<deferred>` section). Notable:
- Streaming web_fetch (pulled in mid-spec, pushed back out by round 5)
- Tavily backend (v0.3+)
- HTTP MCP transport
- Per-host rate limiting
- MCP tool descriptor caching

## Open questions for researcher

- **OQ-01 (D-03 reap hook):** locate existing teardown hook in `voss/harness/agent.py` shutdown path or `voss_runtime.configure` before adding new `voss/harness/lifecycle.py` module. May already exist; if not, T3 pioneers it.
- **OQ-02 (D-11 destructiveHint):** pin exact MCP protocol version where `destructiveHint` field appears in tool descriptor metadata. Confirm Anthropic reference filesystem server populates it.
- **OQ-03 (specifics):** Codex's MCP launcher pattern — upstream repo path and exact stdio framing. Adapt to voss's stdlib-only constraint.

---

*Discussion conducted via default discuss-phase mode — 4 questions per area, single AskUserQuestion per area.*
