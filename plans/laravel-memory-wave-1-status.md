# Laravel memory implementation — first wave

Date: 2026-09-12
Branch: `feat/laravel-memory-api`, created from local `master` at `57abd1c5`.

## Scope

This branch adds an opt-in local retained-memory service for project notes,
conventions, and decisions. Existing FastAPI stays in place. Projects without
`memory.retained_backend: laravel` continue using the existing store.

The harness resolves the backend for CLI do/chat, extension memory tools,
unified recall, and FastAPI memory reads/server turns. Remote saves return a
canonical `memory:<project>:<id>` reference after acknowledgement. Network
failure reports an error; it does not save to legacy files. Required pinned
memory failure stops a server turn before the model runs. Async agent tools
perform HTTP calls off the event loop.

Project administrative commands that still depend on legacy filesystem
operations reject Laravel mode explicitly. Global memory remains independent
and unchanged. Changing configuration back to legacy restores access to the
old corpus; it does not migrate records created in Laravel.

## Remaining rollout gates

- Complete and verify migration/export/rollback tooling before moving real data.
- Integrate the remaining administrative commands and child-agent entry points.
- Add MCP access and then integrate the standalone ADE application.
- Evaluate retrieval quality against representative coding tasks; this first
  service uses lexical SQLite FTS5, without semantic retrieval parity.
- Keep Laravel opt-in until those checks pass. Retiring FastAPI or the legacy
  store requires a separate decision.

## Verification

Root review ran nine new routing tests successfully, covering off-thread saves,
truthful errors, pinned-context failure, legacy mutation protection, the FastAPI error response, and malformed pin-list responses.

51 existing memory/server tests passed with optional Chroma disabled in the
invoking test process (`sys.modules['chromadb'] = None`). The initial run with
Chroma enabled had five failures because it attempted hosted embeddings and
received quota errors. This is not evidence of semantic retrieval parity.

The combined new Python suite passed 39 tests: 25 client/gateway tests, nine
routing checks, and five real Laravel HTTP integration tests. The live tests
cover authenticated project access, revisions/idempotency, search/deletion,
restart persistence, harness save to FastAPI read, and service failure without
legacy fallback. Ruff passed for all changed/new Python source and tests.

A final combined run passed all 90 selected Python checks (new integration
coverage plus existing memory/server regressions), with Chroma disabled.
Final PHP verification passed 12 feature tests with 123 assertions. Pint and
strict Composer validation passed. Unused generated frontend, Boost/agent
configuration, sample users, and example tests were removed. The dependency
lock changed only by removing 11 unused packages; no packages were upgraded.

Local startup and opt-in instructions: `services/memory-api/README.md`.
No records were imported and no default was switched.
