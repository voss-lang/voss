# Wave 1 implementation contract

Legacy and FastAPI remain supported and default. Implement project retained memory only in this wave; global memory stays legacy. No real memory imports, service credentials, or transcript inspection.

## HTTP contract

Base service URL includes no version. All routes /v1. GET /v1/health unauthenticated returns {api_version: 1, status: "ready"}. All other routes require Authorization: Bearer configured VOSS_MEMORY_API_TOKEN (missing configured token denies access; never allow blank token). Token provided by environment at runtime, not stored in repo. Bind to loopback when running.

POST /v1/projects body {id: string, name?: string} registers operator-selected project identity. IDs restricted to ASCII letters/digits/underscore/hyphen, 1..64. Return {data: {id, name}}; repeat same registration succeeds without duplicate. This personal service has one trusted local operator credential for now, not multi-tenant authorization. Agent mutation restrictions remain at harness permission gate; do not advertise scoped third-party credentials yet.

POST /v1/projects/{project}/memories body {kind: "note"|"convention"|"decision", body: nonempty string max 65536 bytes, provenance?: object}. Header Idempotency-Key required (1..128 safe characters). Response {data: memory}, 201; replay the acknowledged response while the record remains at that revision. A replay after an intervening revision returns 409 stale_replay; after deletion returns 409 memory_deleted. Same key with different operation/payload => 409. IDs generated UUID. memory fields: id, project_id, kind, body, revision (starts 1), pinned (false), status (active|superseded|deleted), superseded_by (nullable), provenance, created_at, updated_at. No arbitrary filesystem paths used to resolve records.

GET /v1/projects/{project}/memories?kind=&pinned=&limit=50&cursor=... returns {data:[memory], next_cursor:null|string}. Active only by default, bounded limit 1..100. Cursor offset opaque to consumers. GET .../memories/{id} returns {data:memory}; deleted returns 404. Different project =>404.

PATCH .../memories/{id} body {expected_revision:int, body?:string, pinned?:bool, superseded_by?:id}. Idempotency-Key required. Revision compare transaction; stale =>409. Supersession target active, same project, different item. Active content/pin update only. Superseding unpins, sets status; revision increments. Do not silently remove unspecified fields.

DELETE .../memories/{id} body {expected_revision:int}, Idempotency-Key required. Removes body, provenance, and search eligibility, unpins; leaves minimal tombstone, increments revision. Replay same request returns original. Response {data:{id,revision,status:"deleted"}}. Do not retain deleted body in mutation request cache; use request hash and non-content mutation receipt. A replay after intervening delete must not return old deleted content.

POST /v1/projects/{project}/search body {query:string, kinds?:[kind], top_k?:int 1..50} returns {data:[{id,project_id,kind,body,revision,pinned,status,provenance,score,...timestamps}]}. Active only, SQLite FTS5, query terms escaped, symbol splitting underscore/camelCase as practical. Empty query =>422. Missing project =>404. Errors {error:{code,message}}; validation 422, auth 401, conflict 409, unknown 404, unavailable 503. Envelope error messages must not expose credentials.

## Harness contract

Project .voss/config.yml memory.retained_backend = legacy (default) or laravel; memory.service_project = explicitly registered ID when laravel. Service URL from VOSS_MEMORY_API_URL, authorization from VOSS_MEMORY_API_TOKEN. No import/registration or fallback writes automatically. Reject non-loopback URLs; no secret-bearing URLs, redirects and environment proxies disabled. No model changes.

Gateway composes MemoryStore with remote retained backend; history/turn/ledger reads and code search remain Python. In Laravel mode filter old retained notes/conventions/decisions from legacy recall so no duplicates or stale resurrection. Global corpus remains existing legacy and clearly independent. Same Hit shapes source plural (notes/conventions/decisions), locator service identity e.g. memory:<project>:<uuid>, session provenance mapped to the existing Hit shape. Saved reference is not a fabricated Path: update caller display only where needed; legacy path outputs unchanged. Network errors are explicit, never report save success or write to legacy fallback. Shared gateway factory must avoid constructing network client in legacy mode.

MCP, imports/rollback tooling, full administrative CLI maintenance, semantic indexing parity, global backend cutover, ADE integration are subsequent waves. Record these incomplete gates honestly. This wave should prove real Laravel HTTP + Python + existing FastAPI compatibility using synthetic data.
