# Local Laravel memory: additive implementation plan

Date: 2026-09-12. Status: implementation proposal; no code implemented by this document.

User requirements: preserve existing FastAPI functionality without removal or deprecation until Laravel is confirmed working; integrate across the harness first; integrate the standalone Voss-ADE application afterward.

## Outcome and boundaries

A selected project can use Laravel for durable notes, conventions, and decisions through every supported harness entry point. Existing FastAPI clients continue to work. After harness verification, independent coding agents and standalone ADE use the same local memory service, including when the Python harness is stopped.

Proposed defaults:

- Build the Laravel service under `services/memory-api/` in Voss. Keep the service contract and Python integration in the same repository initially; do not create another repository to begin this work.
- Laravel + SQLite/FTS5; loopback HTTP. Use installed PHP for early local verification. Establish supported PHP/Composer versions and commit the dependency lock during authorized implementation.
- Move retained knowledge only. Transcripts, run ledgers, code indexes, context packing, agent execution, permission enforcement, and existing FastAPI task/event routes remain in Python.
- Existing memory is the default. Laravel availability does not enable it automatically. No installation, data migration, default switch, Git action, or external agent configuration is authorized merely by this planning document.
- No hosted memory, remote embeddings, automatic transcript ingestion, Redis, Postgres, general orchestration rewrite, or new desktop shell.

The Laravel API serves retained-memory operations. FastAPI remains the harness API, and can adapt its memory view to the selected backend. These responsibilities coexist even after successful Laravel adoption.

## Compatibility and ownership contract

| State | Retained-memory reads/writes | FastAPI behavior | Failure behavior |
|---|---|---|---|
| Legacy, default | Existing Python store | Existing routes and response shapes | Existing behavior; PHP need not be installed or running. |
| Isolated evaluation | Separate synthetic Laravel project; production projects stay legacy | Existing paths remain operational | Evaluation failure has no effect on legacy projects. |
| Laravel enabled for a project | Laravel owns that project's notes/conventions/decisions | Memory response adapts selected backend; task/session APIs remain Python | Visible unavailable/error state. Never write to legacy as an automatic fallback. |
| Explicit rollback | Export/reconcile Laravel changes, then switch project to legacy | Same client contract | Freeze writes during reconciliation; verify before reopening. |

Select `legacy` or `laravel` using a project-scoped retained-memory setting, default `legacy`; finalize its placement alongside existing `.voss/config.yml` conventions in Phase 0. Store the service address and local client authorization outside repository files. Global retained memory has its own explicit backend selection, initially legacy. Project switching must not silently switch global memory.

One writer implementation owns each project/category. No normal dual writes, no automatic fallback writes, and no independent PHP edits to Python memory files or indexes. During Laravel mode, retained records from the old project store are excluded from normal recall, including old semantic-index hits. Historical turns and ledgers remain eligible through their existing read paths.

Resolve project identity explicitly. Register an opaque project ID and approved roots/worktrees in the local mapping; existing `_repo_id` hashes checkout paths, so it cannot silently become a stable identity across worktrees. Different projects remain isolated; linking a worktree to an existing project is an explicit operation. Never accept arbitrary file paths as memory IDs.

Active sessions retain their resolved backend/project identity. Backend transitions require a quiescent project: stop accepting new memory writes, finish or interrupt current users, migrate/reconcile, switch atomically, then reopen. Other projects remain usable.

## Minimal shared contract

Create `contracts/memory-api.openapi.json` and small synthetic fixtures before implementing clients. Do not replace `contracts/openapi.json` for the existing harness.

| Operation | Proposed HTTP surface | Behavior to lock |
|---|---|---|
| Health/capabilities | `GET /v1/health` | API version, supported features, readiness; no sensitive configuration. |
| Register project | `POST /v1/projects` | Operator-owned identity registration; idempotent registration key. |
| Create retained item | `POST /v1/projects/{project}/memories` | Kind, body, provenance, request key; durable acknowledgement only after commit. |
| List/read | `GET .../memories`, `GET .../memories/{id}` | Bounded pagination/filtering; stable ID and revision. |
| Edit/pin/supersede | `PATCH .../memories/{id}` | Expected revision; atomic update; stale revision returns conflict. Supersession target must belong to the same scope. |
| Search | `POST .../search` | Query, kinds, bounded top-k; canonical ID/source/excerpt/revision; no inactive records. |
| Forget | `DELETE .../memories/{id}` | Idempotent removal from normal reads, pins, and search in one transaction. |

Use a memory record with ID, project ID, kind, body, revision, timestamps, pin state, optional supersession reference, and source provenance. Provenance supports imported locator/session and future ADE pane/task references without copying transcripts. Preserve legacy locators as import aliases; native service records have IDs, not fabricated filesystem paths.

Global retained memory uses a separate `/v1/global/memories` and `/v1/global/search` scope with equivalent record operations. Its operator-controlled mutation permission is separate from project-write permission. The contract fixtures must prove that a project client cannot select global scope by changing a request parameter; cross-project reads also require explicit access.

Repeated mutation request keys with identical payload return the original result; reuse with a different payload returns conflict. Deletion removes active body/index content; keep only the minimal identity/revision marker required to prevent re-import resurrection. Existing legacy tombstones are respected on import. Superseded content remains explicitly inspectable but excluded from ordinary recall. Tests must distinguish these operations.

Local client authorization scopes reads/writes to registered projects. Agent clients cannot promote into global memory by default. HTTP/MCP entry points must use the same authorization and mutation behavior; adding an MCP tool must not bypass existing user write restrictions.

## Phase 0 — Freeze contracts and establish the baseline

**Deliver:** contract fixtures, an integration checklist, and baseline test/measurement results. No backend switching.

Tasks:

1. Inventory direct `MemoryStore` users, filesystem-return assumptions, pin helpers, source filters, external/global fusion, maintenance verbs, and both native/compiled harness entry paths.
2. Record default CLI output, FastAPI `/memory` response shape, global promotion permissions, and pinned-context behavior using synthetic projects only.
3. Create a deterministic corpus covering symbols, paths, prose/paraphrases, conflicting conventions, pins, forgotten items, and two projects. Label relevant results so retrieval comparisons have an objective target.
4. Define transport timeouts, maximum payloads, and readiness errors. Record measured baseline cold start, search latency, and process memory before selecting operational acceptance thresholds.

**Files:** new contract/fixtures and focused tests beside existing memory suites. Inspect `memory_store.py`, `memory_cli.py`, `cli.py`, `tools.py`, `conventions.py`, `server/app.py`, `swarm_store.py`, and config readers.

**Gate:** baseline expectations are recorded and existing selected checks pass, or pre-existing failures are identified explicitly. This is the evidence against which later phases are judged.

## Phase 1 — Implement the isolated Laravel service

**Deliver:** independently runnable local service with HTTP operations, SQLite persistence, and keyword search. No production Voss data or harness routing changes.

Tasks:

1. Scaffold `services/memory-api/` with ordinary Laravel controllers, request validation, API resources, models, and migrations. Use framework-native PHPUnit tests; avoid repository/service abstraction layers without a real second consumer.
2. Implement the locked contract and transactional FTS5 maintenance. Include symbol/path normalization comparable to the existing tokenizer; test punctuation and query escaping.
3. Add explicit start/status/stop instructions, local bind/auth, readiness/version checks, writable data location, and migration-on-start serialization. Reuse one service/database across clients; a disconnected client cannot shut the service down.
4. Keep application runtime data outside the source tree. No required embedding provider or queue worker in this phase.

**Gate:** actual HTTP tests plus restart/concurrent-client tests prove persistence, scope isolation, duplicate-request behavior, conflict handling, pins, supersession, and deletion. Acknowledged writes survive service restart. Confirm operation without network access to external services.

## Phase 2 — Add one harness routing boundary, legacy by default

**Deliver:** a Python memory gateway with legacy and Laravel retained-store implementations, selected once per project/session.

Proposed files: `voss/harness/memory_gateway.py`, `memory_api_client.py`, and narrowly scoped config additions. Keep `MemoryStore` itself available. The gateway composes existing history/code retrieval with the selected retained store; it does not replace `voss_runtime.memory` classes.

Tasks:

1. Introduce the smallest interface needed by actual consumers: retained save/read/list/update/search/pins/forget and legacy-compatible hit/reference values. Keep legacy display strings unchanged in legacy mode.
2. Adapt synchronous CLI and asynchronous tools/server callers without blocking the async event loop on HTTP. Reuse an existing HTTP dependency if suitable; otherwise select a minimal client implementation, with one bounded timeout policy and no recursive retries.
3. Retry ambiguous writes only with their original request key. A disconnected response must never create a second note or return an unverified success.
4. Add a doctor/status view of selected backend/readiness. Missing PHP or an unavailable Laravel service must have no effect on legacy mode.

**Gate:** a synthetic project exercises both adapters. The legacy suite remains green with Laravel absent. Laravel failures surface explicitly and produce zero writes in legacy retained categories.

## Phase 3 — Integrate every harness memory surface

**Deliver:** Laravel mode works consistently throughout the harness, with the existing FastAPI contract intact.

| Surface | Files / responsibility | Verification |
|---|---|---|
| Agent remember/recall | `tools.py`; replace Path-only save assumption and direct store dependency | Acknowledged save is retrievable through another harness entry point; errors never say remembered. |
| Chat, one-shot, resume, exposed compiled path | `cli.py`, runtime/session setup call sites | Same backend/project context after resume; no path silently reverts to legacy. |
| `/save`, `/recall`, unified code/memory search | `cli.py` | Stable legacy output; Laravel IDs render honestly; code/history results remain available. |
| Convention extraction/adoption | `conventions.py`, adoption in `memory_cli.py` | Only approved candidates persist through the selected backend. |
| List/show/pin/unpin/forget | `memory_cli.py` | Replace retained-category direct file inspection; pin and deletion visible across tool/CLI/server paths. |
| Global recall/promotion | `make_global_store` consumers and `memory_cli.py` | Global setting remains independent; promotion is explicit and idempotent. |
| Context injection | CLI pinned helpers and server turn assembly | Same retained pins in CLI and FastAPI sessions under the same context budget. |
| Swarm recall | `swarm_store.py`, server swarm context | Project scope enforced; relevant retained conventions can accompany owned-file code context without granting write access. |
| FastAPI memory endpoint | `server/app.py` | Preserve `/memory` URL, auth and existing response fields; selected-backend results retain source/locator/excerpt compatibility. |
| Size/vacuum/reindex and telemetry | `memory_cli.py`, gateway, store internals | Report by backend/category. Legacy maintenance never purges the rollback source; Laravel uses supported database/index operations and labels unsupported metrics rather than faking them. |

Global promotion into Laravel must also be possible before claiming full backend coverage, but its default remains unchanged. Historical turn/ledger pins remain Python-owned; combined pin rendering retains the established token limits and distinguishes storage sources.

Search fusion must deduplicate by canonical project/item identity, preserve provenance/source filtering, and exclude old retained aliases. Optional Chroma and external/code retrieval remain enabled where currently supported. FTS5-only search is not accepted as automatic semantic-search parity: if the labelled corpus regresses materially, add a derived semantic index over Laravel-authoritative retained items before production cutover, or keep that project on legacy. Index failures/deletions cannot resurrect inactive content.

Required pinned instructions unavailable at turn start must prevent a mutating turn from starting without them. Optional recall can return an explicit unavailable result while ordinary non-memory work continues. Do not silently replay stale retained data as authoritative context.

**Gate:** each row passes in legacy and Laravel modes, including a cross-entry-point scenario: save → recall → pin → start/resume → forget. FastAPI task/session/event regression checks pass. No ADE feature is needed to pass this gate.

## Phase 4 — Confirm harness reliability and rehearse migration/rollback

**Deliver:** verification report and repeatable import/export tooling; explicit project-by-project enablement procedure.

Tasks:

1. Run the labelled retrieval corpus, real HTTP integration tests, concurrent writes, service restarts, timeouts, incompatible versions, and read/write permission checks. Repeat accepted workflows across multiple harness sessions; record failures and actual measurements.
2. Implement dry-run manifest export/import for selected, approved retained records. Include identity aliases, body checksums, revision, provenance, pins, supersession, and tombstones. No bulk transcript/code/production-data import.
3. Rehearse cutover on synthetic data: quiesce writes → snapshot → import idempotently → compare records/pins/inactive exclusions → switch project → verify all readers/writers.
4. Rehearse rollback after new Laravel writes, updates, and deletes: freeze → export current canonical state → reconcile into legacy files/pins/tombstones → rebuild affected derived indexes → verify → switch. Preserve service-only metadata in the migration manifest; do not pretend legacy supports every new field natively.
5. Keep the legacy implementation, FastAPI routes, tests, and documentation supported. Confirmation means passing evidence and the operator's acceptance of the concrete project cutover—not code compilation alone.

**Gate:** no lost acknowledged records, duplicate IDs, cross-project leaks, stale deleted hits, or stale pins in the synthetic acceptance corpus; retrieval evaluation and operational measurements accepted; rollback drill restores usable current data. Only then propose enabling a selected real project with explicitly approved non-sensitive records.

## Phase 5 — Expose verified memory to independent coding agents

**Depends on:** Phase 4 harness verification.

**Deliver:** Laravel MCP tools over the verified application operations. Use the service's loopback HTTP MCP endpoint initially; add a local stdio launcher only if a target client needs it.

Tasks: add `app/Mcp/` tools/resources and `routes/ai.php`; read/search/inspect first, permission-controlled retained mutations next. Document opt-in client registration, project selection, and service lifecycle. Authentication secrets are neither put into repository files nor tool output. No automatic editing of the user's agent settings.

**Gate:** a separately launched agent reads an approved synthetic note while FastAPI is stopped; harness and agent observe identical IDs/revisions/pins; project boundaries and mutation permissions hold. MCP must not reimplement persistence behavior.

## Phase 6 — Integrate standalone Voss-ADE

**Depends on:** Phase 4 and the stable client contract; Phase 5 supplies the cross-client acceptance check.

**Deliver:** optional local memory integration independently usable from ADE's Python harness integration.

Files in `Voss-ADE`: add `crates/core/src/memory/` client/status module; Tauri memory commands; settings; `web/src/context.js` and `memory-page.js` per Sprint 15; extend `scripts/check.sh`. Add a focused Rust memory client in Voss's `crates/voss-sdk` if it can remain independent of the harness Supervisor; otherwise keep the small adapter in ADE rather than importing lifecycle coupling.

Tasks:

1. Add an optional Cargo `memory` feature distinct from `harness`, with an independent setting/readiness check. Memory client connects/reuses the service and does not stop it when ADE closes. Start with explicit service startup; automate on-demand startup only with single-instance ownership proved.
2. Implement selected note/text → save → list/search → provenance → pin/forget. Explicitly register/link projects; never assume the focused pane authorizes arbitrary project access.
3. Integrate attachment selection and context chips. Active attachments remain distinct from retained memories. Report queued/sent/included appropriately; do not claim full external-agent context visibility.
4. Keep ordinary terminals/workspaces usable with both features off. Existing local drafts, if present by then, promote explicitly/idempotently rather than dual-write to a second authoritative memory table.
5. Update ADE S15 and bridge dependencies before implementation. This is a targeted extension of the optional-memory boundary, not another orchestration engine.

**Gate:** build/test neither feature, harness-only, memory-only, and both. With FastAPI stopped, save in ADE, retrieve through an agent, pin, restart ADE, and forget; all clients agree. With Laravel unavailable, memory state is honestly unavailable and terminals remain usable. Existing harness features still work through FastAPI.

## Phase 7 — Default selection and any later retirement are separate decisions

After acceptance, propose opt-in expansion or a default change with recorded evidence. No phase here deletes or deprecates FastAPI or the legacy memory backend. Any later retirement needs a separate, explicitly approved plan covering remaining consumers, data conversion, compatibility, and recovery.

## Verification commands and evidence

Phase 0 should run and record the existing suites below before changing their behavior. These commands are planned checks, not claims of having run them in this planning pass:

```sh
.venv/bin/python -m pytest -q tests/harness/test_memory_store.py tests/harness/test_memory_tools.py tests/harness/test_memory_global.py tests/harness/test_slash_memory.py tests/harness/test_slash_recall.py tests/harness/test_conventions.py tests/harness/test_memory_runtime_reuse.py tests/harness/server/test_memory_route.py -m 'not live'
```

Expand with existing pin/eviction/vacuum/context and CLI E2E suites when their corresponding Phase 3 surfaces change. Add transport-level Laravel feature tests in `services/memory-api/tests/Feature/`, cross-process Python tests under existing harness integration conventions, and a shared synthetic corpus consumed by both. No live providers are needed for correctness fixtures. Provider-dependent retrieval evaluations must be separately explicit and use approved synthetic material.

Store phase evidence in a dedicated validation report alongside this plan: commands, exit codes, environment, feature/backend combinations, measured values, failures, and unresolved items. Do not reduce acceptance to a count of passing tests.

## Why this sequence

Laravel supports the proposed SQLite and MCP foundations and HTTP testing without requiring the harness to move languages. [Database support](https://laravel.com/framework/docs/13.x/database), [MCP](https://laravel.com/framework/docs/13.x/mcp), [HTTP testing](https://laravel.com/framework/docs/13.x/http-tests).

The hard work is preserving one truth across existing Python callers and new clients. A harness-first rollout proves that boundary before ADE adds another interface, while keeping the working FastAPI path available throughout.
