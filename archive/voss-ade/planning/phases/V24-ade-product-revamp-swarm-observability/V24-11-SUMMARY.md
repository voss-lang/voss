---
phase: V24-ade-product-revamp-swarm-observability
plan: 11
subsystem: full-stack
tags: [memory, server-route, contract, fastapi, vitest, pytest, vade2-11]

# Dependency graph
requires:
  - phase: V24-10
    provides: MemorySurface (honest-empty) + portal memory arm
provides:
  - GET /memory read-only server route (MemoryStore-backed)
  - regenerated contracts/openapi.json (drift gate green)
  - typed fetchMemory client + live MemorySurface (summary + recall search)
affects: [V24 verification, memory product surface, server contract]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-cwd read-only server route: GET /memory mirrors /sessions/saved's cwd query-param + bearer-auth shape; MemoryStore imported lazily inside the handler to avoid heavy boot import."
    - "Contract regen on route change: scripts/export_contract.py rewrites contracts/openapi.json so test_contract_drift stays green (.venv python required)."
    - "memorySlot thunk: App passes live baseUrl/token/cwd off vossClient() to MemorySurface (joins reviewSlot/contextSlot); prop-less mount = honest fallback."
---

# V24-11 — Memory server route + live surface (closes V24-10 deferral)

## What shipped
Upgraded Memory from honest-empty (V24-10) to live data by exposing the harness
memory store over HTTP and wiring the surface to it.

**Backend**
- `voss/harness/server/app.py`: `GET /memory?cwd=&q=&top_k=` (bearer-auth + CORS like
  every route). Returns `{v, summary, query, hits[]}` from `MemoryStore(cwd)` —
  `summary()` always (cheap fs walk, handles missing dirs); `recall()` hits only when
  `q` is given (`top_k` clamped 1..50). MemoryStore imported lazily in the handler.
- `contracts/openapi.json` regenerated via `scripts/export_contract.py` (+68 lines);
  the contract-drift gate stays green.
- `tests/harness/server/test_memory_route.py`: summary-without-query, recall-with-seeded-note
  returns hits, and 401-without-bearer. 6/6 green incl. drift gate.

**Frontend**
- `org/live/memoryClient.ts`: typed `fetchMemory(baseUrl, token, cwd, q?, topK)` →
  `MemoryResponse` (bearer GET, throws on non-OK, token never logged). + test (3).
- `surfaces/memory/MemorySurface.tsx`: `createResource`-driven. With a live server
  (baseUrl+token+cwd via `memorySlot`) it loads the summary and offers a recall search
  box that lists hits; loading/error states are honest; no server → the honest
  harness-backed fallback (kept from V24-10, still passes the prop-less portalA11y
  render). `memory.css` for the search + hit rows. + test (3).
- `portal/PortalShell.tsx`: added `memorySlot?` prop; memory arm = `memorySlot() ??
  <MemorySurface/>`.
- `App.tsx`: passes `memorySlot` building `<MemorySurface>` from `vossClient()?.baseUrl/
  token` + `workspacePath()`.

## Tests
- App suite: **906 passed / 5 skipped** (full green; the previously load-flaky
  ProtocolPane and the self-healed sidecar test both pass). `tsc --noEmit` clean.
- Python `tests/harness/server`: **6 passed** (3 memory route + 3 drift).

## Decisions
- Read-only by design — no write/forget over HTTP this phase (recall + summary cover
  the surface's needs; mutation stays CLI/slash-only).
- `recall()` only fires with a query, so the default surface load stays cheap (no
  chroma build on open).

## Manual smoke (pending, non-blocking)
Start a workspace session → open Memory → summary loads; type a query → hits list.
With no session → honest fallback mentioning `/memory`.
