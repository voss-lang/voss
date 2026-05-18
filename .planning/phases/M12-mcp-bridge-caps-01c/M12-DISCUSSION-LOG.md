# Phase M12 Discussion Log

**Date:** 2026-05-18
**Command:** `/gsd-discuss-phase M12`
**Output:** `M12-CONTEXT.md`

For human reference (audits, retrospectives). Not consumed by downstream agents.

---

## Prior Context Loaded

- `.planning/PROJECT.md` — v0.1 harness scope, .voss control layer.
- `.planning/STATE.md` — milestone v0.1.1; M11 (Voss-aware Tools) plans ready; T7 (skills bootstrap) complete; T3 (network surface) complete with MCP client shipped.
- `.planning/ROADMAP.md` lines 564-586 (M12 block) + 876-928 (T3 block).
- `.planning/phases/T3-network-surface/T3-CONTEXT.md` + `T3-SPEC.md` + `T3-07-SUMMARY.md` — the T3/M12 boundary carve: "M12 reduces to expose harness as MCP server only".
- Live source: `voss/harness/mcp/{__init__,config,client,registry}.py` (T3-shipped MCP client surface, frozen protocol `2025-11-25`); `voss/harness/tools.py:444-465` (curated tool table); `voss/harness/skill_registry.py` (T7 7-skill registry); `voss/harness/cli.py:2292-2398` (existing `voss mcp list`/`call` click group); `voss/harness/permissions.py:49-65` (mode-tier rules).

## Codebase Scout

- MCP **client side fully shipped** by T3-07: config + stdio JSON-RPC client + telemetry + registry adapter + `voss mcp list/call` CLI.
- 6 strictly read-only low-level tools live in `make_toolset` (`fs_read`/`fs_glob`/`fs_grep`/`voss_check`/`git_status`/`git_diff`).
- T7 left 7 skills in `default_skill_registry()` with correct `mutating` flags.
- Upstream Anthropic `mcp` Python SDK is importable in this env (`import mcp` succeeds) — viable for server-side stdio framing.

## Gray Areas Presented

User selected ALL of:
- Transport (stdio vs +HTTP)
- Tool surface (low-level vs skills)
- Server lifecycle + permission posture
- Audit trail shape (M2 integration)

## Discussion

### Area 1 — Transport
- **Q:** stdio only / stdio + streamable-HTTP / stdio + SSE?
- **A:** **stdio only.**
- Rationale: matches T3 client transport; matches how external hosts (Claude Desktop, Cursor, Continue) launch MCP servers as subprocesses. HTTP deferred not partially built. → **D-01**.

### Area 2 — Tool surface

**Q2a (low-level set):** 6 ROADMAP tools / +fs_read_many+shell_monitor / +web_fetch+web_search / +fs_write+fs_edit?
**A:** **6 ROADMAP tools** (`fs_read`, `fs_glob`, `fs_grep`, `voss_check`, `git_status`, `git_diff`). → **D-02 (low-level)**.

**Q2b (skills):** Defer / read-only skills only / all 7?
**A:** **All 7 with destructiveHint per registry.** Skills run server-side `run_turn` so LLM cost lands on the SERVER's provider config — flagged separately as **D-05** because of the cost-attribution implication. → **D-02 (skills)** + **D-05**.

**Q2c (destructiveHint convention):** Mirror is_mutating verbatim / mark voss_check as destructive / manual per-tool table?
**A:** **Mirror is_mutating verbatim.** Symmetric with T3 inbound rule. → **D-02 (mapping)**.

### Area 3 — Lifecycle + permission posture

**Q3a (invocation):** Foreground only / foreground + --daemon?
**A:** **Foreground only.** Host owns subprocess lifecycle. → **D-03 (invocation)**.

**Q3b (default mode):** plan / edit / refuse to start without --mode?
**A:** **Refuse without explicit --mode.** Deviates from T3 NET-04 "default plan" — accepted because T3 was OUTBOUND (Voss consuming external tools) and M12 is the INBOUND dual case; an MCP server warrants stricter conscious opt-in per launch. → **D-03 (default mode)**.

**Q3c (mcp.yml schema):** Add `server:` block / all-flags-no-config / `server:` + per-client allowlist?
**A:** **Add `server:` block.** Symmetric with T3's `servers:` (plural) outbound block. Per-client allowlist deferred (not in scope for v0.1 trust model). → **D-03 (config)**.

### Area 4 — Audit trail shape

**Q:** Telemetry only / one SessionRecord per server lifetime / one SessionRecord per connection?
**A:** **Telemetry only** (`mcp.server.request`/`mcp.server.response`, mirroring T3 inbound `mcp.request`/`mcp.response`). User-affirmed explicit divergence from ROADMAP wording "every MCP invocation logged through M2 RunRecorder" — rationale: writing a SessionRecord per RPC poke clutters `/sessions`; inspectable surfaces (`/probable`/`/btrace`) are designed around LLM turns, not raw tool calls. Re-open via `--record-sessions` flag if a real audit demand emerges. → **D-04**.

## Deferred Items Captured

See `<deferred>` in CONTEXT.md. Items: HTTP transport, daemon mode, mutating low-level tools in default surface, shell/network tools in default surface, per-client allowlist auth, full M2 SessionRecord per call, MCP catalog UI in M9, cross-org registry, encrypted transports, per-skill cost-attribution back to calling host.

## Claude's Discretion (not asked)

- Use of Anthropic `mcp` Python SDK vs hand-rolling: pushed to **open_questions** for the researcher rather than locking. Both options have merit; researcher should compare LOC + protocol-drift risk against `client.py` parity.
- `clientInfo` handling in telemetry: default to include (not secret); pushed to open_questions for telemetry redaction-policy check.
- Skill `CallToolResult` content shape: pushed to open_questions; need to inspect Claude Desktop's expectations.
- Subprocess reap on parent-host crash: pushed to open_questions; likely "exit clean on stdin EOF".

## Outcome

CONTEXT.md captures 5 implementation decisions (D-01..D-05) + 7 recommended `MCP-XX` mappings + 10 deferred ideas + 4 open research questions. Phase boundary tightened from ROADMAP literal "consume + expose" to "expose only" (T3 already shipped consume).
