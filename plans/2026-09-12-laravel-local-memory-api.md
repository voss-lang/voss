# Laravel/PHP for local Voss memory

2026-09-12. Research proposal. User scope: a local service used by ADE and coding agents. No framework adoption or migration approved by this investigation.

Follow-up: [additive implementation plan](2026-09-12-laravel-memory-implementation-plan.md). The user's latest requirement sets the sequence: complete harness integration and verification before standalone ADE integration; preserve FastAPI and the legacy backend throughout. That plan supersedes the experiment ordering below.

## Recommendation

**Laravel is a credible choice for a shared, local memory service that works independently of the Python harness.** Prototype a narrow service for explicitly retained notes, conventions, and decisions. Keep agent execution, transcripts, context packing, and code indexing in the harness during the evaluation.

If the goal is only to expose today's `MemoryStore` through a few more endpoints, extending the existing Python server remains the simpler route. Laravel earns its additional runtime when memory becomes a product used equally by ADE, the harness, and other coding agents—even when `voss serve` is off.

This is an architectural judgment, not a measured speed or quality advantage for PHP. The user-facing benefit is shared, inspectable memory; either language can implement it.

## What Laravel contributes

| Need | Laravel fit | Actual workflow value |
|---|---|---|
| Structured memory records | Validation, database migrations, Eloquent, API resources | Consistent create/edit/read behavior, source provenance, and controlled schema changes. |
| Agent access | First-party Laravel MCP supports web and local command servers | ADE can use HTTP; agents can use memory tools over the same application behavior. |
| Local storage | Official SQLite support | One local database without requiring Postgres, Redis, or Docker for the first version. |
| Deferred processing | Database-backed queues are supported if indexing later needs them | Saving a note can remain quick while expensive work happens separately. No queue worker needed for initial CRUD/keyword search. |
| AI-assisted implementation | Laravel Boost supplies Laravel-specific agent guidance and documentation tools | A supported development workflow for building this service; not a runtime memory engine. |

Sources: [validation](https://laravel.com/framework/docs/13.x/validation), [API resources](https://laravel.com/framework/docs/13.x/eloquent-resources), [Laravel MCP](https://laravel.com/framework/docs/13.x/mcp), [SQLite configuration](https://laravel.com/framework/docs/13.x/database), [queues](https://laravel.com/framework/docs/13.x/queues), [Boost](https://laravel.com/framework/docs/13.x/boost).

## What the existing Voss implementation makes expensive

`voss/harness/memory_store.py` is more than a database wrapper: it manages Markdown/JSONL source records, IDs, advisory file locks, optional Chroma indexing, keyword/semantic retrieval, pins, telemetry, quotas, reindexing, and tombstones. `tools.py`, `conventions.py`, `cli.py`, and the server instantiate or consume it directly.

Consequently, replacing only `GET /memory` does not move memory ownership to Laravel. Python callers would still write the old store. A PHP wrapper around the existing implementation also needs a usable Python API underneath, which is currently the missing work.

Do not have PHP and Python independently edit `.pins.json`, tombstones, memory files, or Chroma internals. One implementation must own each canonical record and its updates. Reuse the existing source formats for explicit imports/exports where useful, not concurrent cross-language writes.

## Options

| Approach | Benefit | Cost | Recommendation |
|---|---|---|---|
| Extend Python API | Fastest path to ADE memory controls; reuses existing semantics | Memory remains coupled to Python deployment | Baseline to compare against. |
| Laravel proxies Python | Laravel-shaped interface | Two services, still need Python endpoints, little independence | Avoid as the permanent design. |
| Laravel owns retained notes/decisions/conventions | Independent memory usable by every client | New runtime plus client integration and a bounded migration | Best Laravel experiment. |
| Laravel replaces all memory and retrieval | One new implementation owns everything | Porting transcript storage, indexes, ranking, pins, CLI callers, and recovery behavior | Too broad for this decision. |

Plain PHP could implement a tiny API, but routing, validation, persistence conventions, and agent tooling become choices to maintain yourself. If choosing PHP for an expanding memory service, Laravel offers a more consistent foundation. For only six endpoints, Python still has the strongest simplicity advantage in this repository.

## Proposed boundary

ADE and coding agents access one local Laravel application. ADE uses its HTTP API; compatible agents use its MCP tools. Both transports call the same application operations. The Python harness becomes another client for retained memory.

**Laravel owns:** approved retained items, stable identity, project scope, provenance, pin state, replacement/supersession, search, and forgetting.

**Python retains:** agent loops, working conversation history, run records, context compression, code search/indexing, and decisions about what to include in a particular turn. A remembered decision is a selected knowledge item; a raw run ledger remains execution history.

**ADE owns:** canvas/pane state, attachment selection, presentation, and delivery visibility. Its planned local memory table should not become a second permanent editable copy when the service is enabled. Offline drafts, if later needed, require explicit pending state and idempotent promotion.

MCP access does not itself grant permission to save arbitrary content. Keep the existing distinction between agent-readable retained knowledge and explicit user authorization for durable/project-global writes. Initial fixtures contain synthetic notes only; no transcript ingestion or repository-memory migration runs in this research.

## Smallest useful service

- Create, inspect/list, revise, pin/unpin, search, and forget a retained item.
- Each item carries project identity, kind, text, revision, and enough provenance to identify its source. Session/pane references are optional and do not require importing a conversation.
- A revision check prevents two agents silently overwriting one another. Repeated create requests with the same request key return the same record.
- Project scope is mandatory for project operations. Cross-project promotion stays an explicit action. Resolve known project IDs rather than trusting arbitrary filesystem paths from clients.
- Start with SQLite plus FTS5 keyword search. Include exact symbols/path-like queries in tests; default full-text tokenization is not equivalent to Voss's existing symbol tokenizer or hybrid ranking.
- Bind the service locally with client authentication. Keep database ownership, schema migrations, and app startup inside the Laravel application; Rust and Python access the API rather than editing its database.
- Define the service lifecycle independently of a particular ADE window. Closing a canvas must not unexpectedly remove memory access from a separate coding-agent session. Prove start/reuse/shutdown behavior before bundling.

Laravel supports SQLite; SQLite FTS5 provides full-text search and ranking. Laravel's database support alone does not automatically create or maintain an FTS5 index: add and test the migrations and indexing behavior explicitly. [SQLite database support](https://laravel.com/framework/docs/13.x/database), [FTS5](https://www.sqlite.org/fts5.html).

## Semantic search is a separate decision

Laravel's AI SDK supports embeddings and reranking. Its documented vector-column integration includes PostgreSQL/pgvector and MariaDB; that is not proof of an equivalent built-in SQLite vector path. It also supports compatible local provider endpoints, but those still require an actual embedding model/server. Conversation-history persistence is not the same feature as durable project memory. [Laravel AI SDK](https://laravel.com/framework/docs/13.x/ai-sdk).

Begin the prototype without an AI SDK dependency or embedding provider. Keyword retrieval is enough to test shared ownership and usability, but not to claim parity with existing hybrid recall. If semantic queries materially improve the evaluation, compare retaining Python as a read-only indexing/search worker against a local embedding endpoint or another local index. Canonical text/pin/deletion state stays in Laravel; derived indexes must filter deleted or superseded records and can be rebuilt.

Do not silently switch to hosted embeddings to make a local prototype work. No remote memory sync or embedding calls are part of this proposal.

## Local operation and packaging

Verified on this machine: PHP 8.5.7; PHP SQLite 3.53.3; PDO SQLite, SQLite3, mbstring, OpenSSL, cURL, DOM, fileinfo, and XML extensions present. Composer is on PATH. An in-memory FTS5 table was successfully created. FrankenPHP was not found on PATH. These checks establish basic prerequisites, not full Laravel dependency compatibility or performance.

Laravel 13 documentation lists PHP 8.3+ and required extensions. The initial personal experiment can use the installed PHP/Composer environment; packaged distribution is separate work. Laravel documents FrankenPHP as a server, and FrankenPHP documents embedding applications into standalone binaries, including a macOS build path. Code signing, writable database/cache locations, startup time, and bundled extensions must still be proven for Voss-ADE. No need to replace Tauri or adopt another desktop shell. [Laravel deployment](https://laravel.com/framework/docs/13.x/deployment), [FrankenPHP embedding](https://frankenphp.dev/docs/embed/).

## Bounded feasibility experiment

1. **Build against synthetic data only.** Laravel + SQLite, HTTP endpoints and MCP tools for the same memory operations. No background workers or embeddings initially.
2. **Connect one ADE action and one agent tool.** Save an explicitly selected synthetic note through HTTP; retrieve the identical revision through MCP while `voss serve` is stopped.
3. **Connect one Python consumer.** Read retained memory and pins through the API; do not allow a fallback write into the old store if the service is unavailable.
4. **Exercise correctness.** Restart persistence, project isolation, duplicate requests, concurrent edits, supersession, pin visibility, and forgetting across both transports. Memory save failure must be visible.
5. **Compare against Python baseline.** Measure cold start, resident memory, create/search latency, maintenance surface, and retrieval behavior on representative synthetic queries. Record actual values before setting product targets.
6. **Decide before migrating.** Proceed if independent use by ADE/agents feels materially simpler and local operation is acceptable. Otherwise expose Python directly and retain the same client contract.

If adopted, migrate only explicitly selected retained records. Preserve source IDs/provenance, verify record and pin counts, switch all writers for that project/category together, and make the old category read-only. Rollback needs an export of newly written records; flipping a feature flag alone is insufficient after new data accumulates.

## Decision

Investigate Laravel as an independent local knowledge service, not as a cosmetic replacement for the current endpoint. It fits the broader ADE/agent workflow and has credible tooling. Adoption remains conditional on a small working demonstration and an explicit decision to own retained memory outside the harness.

Research only: no Laravel installation, service startup, MCP registration, data migration, or application code change occurred. Official documentation was checked; only local PHP/SQLite prerequisites were executed.
