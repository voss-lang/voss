---
phase: V24-ade-product-revamp-swarm-observability
plan: 11
type: execute
wave: 8
depends_on: ["V24-10"]
autonomous: true
requirements: [VADE2-11]
files_modified:
  - voss/harness/server/app.py
  - contracts/openapi.json
  - tests/harness/server/test_memory_route.py
  - apps/voss-app/src/org/live/memoryClient.ts
  - apps/voss-app/src/org/live/__tests__/memoryClient.test.ts
  - apps/voss-app/src/surfaces/memory/MemorySurface.tsx
  - apps/voss-app/src/surfaces/memory/__tests__/MemorySurface.test.tsx
  - apps/voss-app/src/surfaces/memory/memory.css
  - apps/voss-app/src/portal/PortalShell.tsx
  - apps/voss-app/src/App.tsx
must_haves:
  truths:
    - "The voss serve server exposes GET /memory?cwd=&q=&top_k= (bearer-auth, same as every route) returning {v, summary, query, hits[]} from MemoryStore(cwd) — summary() always; recall() hits only when q is given."
    - "contracts/openapi.json is regenerated so the contract-drift gate (tests/harness/server/test_contract_drift.py) stays green with the new route."
    - "MemorySurface fetches /memory when the app has a live server (baseUrl+token+cwd) and renders the memory summary + a search box that lists recall hits; with no live server it shows the honest harness-backed fallback (no crash, no fabricated rows)."
    - "Full apps/voss-app vitest + the Python harness/server tests are green; tsc --noEmit clean."
  artifacts:
    - path: "voss/harness/server/app.py"
      provides: "GET /memory route on the loopback server, MemoryStore-backed"
      contains: "/memory"
    - path: "apps/voss-app/src/org/live/memoryClient.ts"
      provides: "Typed fetchMemory(baseUrl, token, cwd, q?, topK?) → MemoryResponse"
      contains: "fetchMemory"
    - path: "apps/voss-app/src/surfaces/memory/MemorySurface.tsx"
      provides: "Live memory surface: summary + recall search; honest fallback when no server"
      contains: "fetchMemory"
  key_links:
    - from: "apps/voss-app/src/surfaces/memory/MemorySurface.tsx"
      to: "voss/harness/server/app.py GET /memory"
      via: "fetchMemory(baseUrl, token, cwd) bearer fetch; props passed from App via memorySlot off vossClient()"
      pattern: "/memory"
---

<objective>
Upgrade Memory from the honest-empty state (V24-10) to live data by giving the
loopback `voss serve` server a read-only `/memory` route and wiring MemorySurface
to it. Memory already exists in the harness (`voss/harness/memory_store.py` —
`summary()`, `recall()`); the only gap is HTTP exposure. Closes the V24-10 deferral
(VADE2-11).

Backend: `GET /memory?cwd=&q=&top_k=` → `{v, summary, query, hits[]}` from
`MemoryStore(cwd)` (bearer-auth + CORS like every route). Regenerate the committed
contract so the drift gate stays green.

Frontend: a typed `fetchMemory` client + MemorySurface that loads the summary (and a
recall search box) when the app has a live server, falling back to the honest
harness-backed copy when it does not. No fabricated rows.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
<interfaces>
<!-- Verified 2026-06-16. -->

Backend (voss/harness/server/app.py):
- Routes are defined inside `create_app(token)`; `Path`, `os`, `HTTPException`,
  `get_config` already imported. Auth via `_BearerASGI`; CORS already added. The
  per-cwd query-param pattern is `@app.get("/sessions/saved") def …(cwd: str = ".")`.
- MemoryStore (voss/harness/memory_store.py): `MemoryStore(cwd)` ctor;
  `.summary(*, source=None) -> str` (rendered markdown; handles missing dirs → zeros);
  `.recall(query, *, top_k=5, source=None) -> list[Hit]`. `Hit` fields: source,
  locator, score, excerpt, session_id, ts, line_start, line_end. recall() lazily
  builds chroma; summary() is a cheap fs walk. _SOURCES = turns/ledgers/decisions/
  conventions/notes.

Contract gate (tests/harness/server/test_contract_drift.py):
- Asserts `contracts/openapi.json` equals `create_app(FIXED_TOKEN).openapi()` (sorted,
  indent=2). Adding a route DRIFTS it. Regenerate via
  `.venv/bin/python scripts/export_contract.py` (writes openapi.json + events.schema.json).
  Use .venv python (bare python3 lacks deps).

Frontend:
- BuiltVossClient (org/live/vossClientBuild.ts) exposes `baseUrl: string` + `token: string`.
  App holds `vossClient()` signal + `workspacePath()`. The existing fetch pattern sends
  `Authorization: Bearer ${token}` to `${baseUrl}/<route>`.
- PortalShell mounts `<MemorySurface/>` directly today; add a `memorySlot?: () => JSX.Element`
  thunk (mirrors contextSlot/reviewSlot) so App can pass baseUrl/token/cwd off vossClient().
- The V24-10 portalA11y gate renders `<MemorySurface />` prop-less → it MUST still render
  the honest fallback (role=tabpanel aria-label=Memory, mentions /memory) with no props.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend GET /memory route + contract regen + test</name>
  <files>voss/harness/server/app.py, contracts/openapi.json, tests/harness/server/test_memory_route.py</files>
  <read_first>
    - voss/harness/server/app.py (route patterns, the /sessions/saved cwd-query shape)
    - voss/harness/memory_store.py (summary/recall/Hit)
  </read_first>
  <action>
    Add inside create_app (near the other @app.get routes):
      `@app.get("/memory")` `def get_memory(cwd: str = ".", q: str | None = None, top_k: int = 5) -> dict:`
      build `store = MemoryStore(Path(cwd).resolve())`; `out = {"v": 1, "summary":
      store.summary(), "query": q, "hits": []}`; if `q`: map `store.recall(q, top_k=top_k)`
      Hits → list of dicts (source/locator/score/excerpt/session_id/ts/line_start/line_end);
      return out. Import MemoryStore at module top (or lazily inside the fn to avoid heavy
      import at server boot — prefer lazy `from voss.harness.memory_store import MemoryStore`).
      Clamp top_k to a sane max (e.g. min(top_k, 50)).
    Regenerate the contract: `.venv/bin/python scripts/export_contract.py`.
    Add tests/harness/server/test_memory_route.py: FastAPI TestClient with the bearer
    token; assert GET /memory?cwd=<tmp> 200 + has "summary" + hits==[] without q; with a
    seeded note (store.write_note) + q, hits is non-empty and carries the Hit fields;
    assert 401 without the bearer header (auth still enforced).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/server/test_memory_route.py tests/harness/server/test_contract_drift.py -q 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - GET /memory returns {v,summary,query,hits}; q drives recall; bearer auth enforced.
    - contracts/openapi.json regenerated; test_contract_drift green.
    - New route test green.
  </acceptance_criteria>
  <done>The server exposes memory read-only; the contract snapshot matches.</done>
</task>

<task type="auto">
  <name>Task 2: Typed fetchMemory client + test</name>
  <files>apps/voss-app/src/org/live/memoryClient.ts, apps/voss-app/src/org/live/__tests__/memoryClient.test.ts</files>
  <read_first>
    - apps/voss-app/src/org/live/vossClientBuild.ts (baseUrl/token shape + existing fetch style)
  </read_first>
  <action>
    Export `interface MemoryHit { source; locator; score; excerpt; session_id; ts;
    line_start; line_end }`, `interface MemoryResponse { v: number; summary: string;
    query: string | null; hits: MemoryHit[] }`, and
    `async function fetchMemory(baseUrl, token, cwd, q?, topK = 5): Promise<MemoryResponse>`
    that GETs `${baseUrl}/memory?cwd=…(&q=…&top_k=…)` with `Authorization: Bearer ${token}`,
    throws on non-OK, returns the parsed JSON. Never log the token.
    Test: mock fetch; assert URL + query params + bearer header; returns parsed body;
    throws on 401/500.
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- memoryClient 2>&1 | tail -10; npx tsc --noEmit 2>&1 | tail -5 && echo TSC_OK</automated>
  </verify>
  <acceptance_criteria>
    - fetchMemory issues the right authed GET and returns a typed MemoryResponse; throws on error.
  </acceptance_criteria>
  <done>The app has a typed memory client.</done>
</task>

<task type="auto">
  <name>Task 3: MemorySurface live data + honest fallback + wiring</name>
  <files>apps/voss-app/src/surfaces/memory/MemorySurface.tsx, apps/voss-app/src/surfaces/memory/memory.css, apps/voss-app/src/surfaces/memory/__tests__/MemorySurface.test.tsx, apps/voss-app/src/portal/PortalShell.tsx, apps/voss-app/src/App.tsx</files>
  <read_first>
    - apps/voss-app/src/surfaces/memory/MemorySurface.tsx (current honest fallback to keep as the no-server branch)
    - apps/voss-app/src/portal/PortalShell.tsx (memory Match arm + slot pattern)
    - apps/voss-app/src/App.tsx (PortalShell mount; vossClient()/workspacePath())
  </read_first>
  <action>
    MemorySurface: add props `{ baseUrl?: string; token?: string; cwd?: string }`.
    - No baseUrl/token/cwd → render the EXISTING honest fallback (harness-backed, /memory
      slash command). Keep role=tabpanel aria-label=Memory + the "/memory" mention so the
      prop-less portalA11y render still passes.
    - With a live server → createResource/onMount fetchMemory(summary); render the summary
      (mono/pre block) + a search `<input aria-label="Search memory">` that on submit
      refetches with q and lists hits (.surface-row style: locator + source + excerpt).
      Show a spinner while loading and an honest error state on failure (no fabricated rows).
    PortalShell: add `memorySlot?: () => JSX.Element`; memory Match arm renders
    `props.memorySlot ? props.memorySlot() : <MemorySurface/>` (prop-less fallback).
    App: pass `memorySlot={() => <MemorySurface baseUrl={vossClient()?.baseUrl}
    token={vossClient()?.token} cwd={workspacePath() ?? undefined} />}`.
    Test: mock fetchMemory; with props it renders summary + a hit on search; prop-less it
    renders the honest fallback mentioning /memory and no rows.
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test -- MemorySurface portalA11y 2>&1 | tail -15; npx tsc --noEmit 2>&1 | tail -5 && echo TSC_OK</automated>
  </verify>
  <acceptance_criteria>
    - With a live server MemorySurface shows the summary + recall search/hits; with none it shows the honest fallback.
    - portalA11y prop-less render still green; no fabricated rows anywhere.
  </acceptance_criteria>
  <done>Memory shows live data when the server is up, honest fallback otherwise.</done>
</task>

<task type="auto">
  <name>Task 4: Full regression + docs + summary</name>
  <files>apps/voss-app/PRODUCT.md, .planning/phases/V24-ade-product-revamp-swarm-observability/V24-UI-SPEC.md</files>
  <action>
    Run the full app suite + tsc + the Python harness/server tests. Update PRODUCT.md IA
    row 8 (Memory) + UI-SPEC surface-wiring note: Memory is now live via GET /memory
    (summary + recall), honest fallback when no server. Create V24-11-SUMMARY.md. Flip the
    ROADMAP V24-11 checkbox.
  </action>
  <verify>
    <automated>cd apps/voss-app && npm test 2>&1 | tail -8; cd /Users/benjaminmarks/Projects/Voss && .venv/bin/python -m pytest tests/harness/server -q 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - Full app suite + Python server tests green; tsc clean; docs + roadmap updated.
  </acceptance_criteria>
  <done>VADE2-11 met; Memory is live end-to-end.</done>
</task>

</tasks>

<threat_model>
| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-V24-11-AUTH | Info disclosure | GET /memory | mitigate | Route rides the existing `_BearerASGI` bearer gate + loopback-only CORS — same as every route. Test asserts 401 without the token. |
| T-V24-11-TOK | Info disclosure | fetchMemory | mitigate | Bearer token rides the Authorization header, never logged/stringified (T-V15-10 discipline). |
| T-V24-11-PATH | Tampering | cwd query param | accept | `Path(cwd).resolve()` + MemoryStore reads only under the repo's memory root; read-only (summary/recall), no writes via this route. |
| T-V24-11-FS | Verification integrity | MemorySurface | mitigate | Renders only server-returned hits; on error/no-server shows honest states, never fabricated rows. |
</threat_model>

<success_criteria>
GET /memory is a bearer-authed read-only route returning MemoryStore summary + recall
hits; the contract snapshot is regenerated and the drift gate is green; MemorySurface
renders live memory (summary + recall search) when the app has a server and the honest
harness-backed fallback otherwise, with no fabricated rows; the full app suite, the Python
server tests, and tsc are all green (VADE2-11 met).
</success_criteria>

<output>
Create `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-11-SUMMARY.md`.
Manual smoke (non-blocking): start a workspace session, open Memory, confirm the summary
loads and a recall search lists hits; with no session, confirm the honest fallback.
</output>
