# Voss memory API

Opt-in local Laravel service for project notes, conventions, and decisions.
SQLite FTS5 provides lexical search. Existing FastAPI, legacy memory, history,
and global memory remain supported. No data is imported automatically.

Requires PHP 8.3+, Composer, and SQLite with FTS5. PHP feature tests require
PHP 8.3+ and the extensions requested by Composer.

## Run locally

Run these commands from `services/memory-api`:

```sh
composer install
cp .env.example .env
mkdir -p storage/memory
touch storage/memory/memory.sqlite
export DB_DATABASE="$PWD/storage/memory/memory.sqlite"
export VOSS_MEMORY_API_TOKEN="$(openssl rand -hex 32)"
php artisan migrate --force
php artisan serve --host=127.0.0.1 --port=8766
```

Use a private local token supplied through your shell or credential manager.
Keep the same token available to the harness process through its environment.
The generated example above lasts only for the current shell; do not commit it
or print it into a shared transcript. No application encryption key is required
for these stateless API routes.

Health is public at `/v1/health` and checks SQLite/search-table readiness. All
other endpoints require the configured bearer token. An unset token denies
access. This first version has one trusted local operator credential that can
access every registered project; it does not provide per-agent credentials.
The harness's existing write permission gate still applies to agent tools.

## Register and opt in

In a shell with the service token available, register an explicit project ID:

```sh
export VOSS_MEMORY_API_URL=http://127.0.0.1:8766
curl --fail-with-body "$VOSS_MEMORY_API_URL/v1/projects" \
  -H "Authorization: Bearer $VOSS_MEMORY_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"id":"my-project","name":"My project"}'
```

Set these project settings in `.voss/config.yml`:

```yaml
memory:
  retained_backend: laravel
  service_project: my-project
```

Run the harness from that project with `VOSS_MEMORY_API_URL` and
`VOSS_MEMORY_API_TOKEN` in its environment. The URL excludes `/v1` and accepts
only a loopback host; the Python client disables proxies and redirects.

Harness `/save`, memory agent tools, recall, remote pins, and FastAPI `/memory`
use this backend. A successful save returns `memory:<project>:<uuid>`.
An unavailable service returns an error without writing to legacy memory.
Required pinned-memory failure prevents a server model turn from starting.

Project administrative commands that still depend on legacy files explicitly
reject Laravel mode. Migration, the remaining administrative and child-agent
callers, MCP access, and standalone ADE integration are subsequent work.

## Mutation and rollback behavior

The versioned contract is `../../contracts/memory-api.openapi.json`. Writes
require `Idempotency-Key`; updates and deletes also require `expected_revision`.
Reuse the same key for an uncertain HTTP retry. The client does not retry
mutations automatically. A newly issued harness save uses a new key, so recall
first after an uncertain save before issuing another save.

A repeated mutation returns its acknowledged result while its revision is
current. Intervening edits yield `stale_replay`; deletion yields
`memory_deleted`. Delete replay returns only the tombstone. Deletion clears
body, provenance, pins, and the search entry. Receipts store hashes and result
identity, without cached bodies.

To return a project to its previous corpus, stop its harness session and set
`retained_backend: legacy` (or remove the setting), then start a new session.
This changes routing only. It does not export Laravel records into legacy
files. Preserve the SQLite database until migration/rollback tooling is ready.
FastAPI and legacy memory are not deprecated by this service.

## Verify

```sh
vendor/bin/phpunit
vendor/bin/pint --test
```

From the repository root, with Python development dependencies installed:

```sh
python -m pytest tests/harness/test_memory_api_client.py \
  tests/harness/test_memory_gateway.py \
  tests/harness/test_memory_backend_routing.py \
  tests/harness/test_laravel_memory_integration.py
```

The live tests start a loopback PHP process with temporary SQLite and synthetic
credentials. They cover auth, revisions, idempotency, deletion, restart,
harness-to-FastAPI visibility, and failure without legacy fallback.
