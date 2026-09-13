# Laravel memory baseline

Date: 2026-09-12


Interpreter: `python`

The baseline was run from a temporary clean `HEAD` export so the uncommitted
Laravel client, gateway, callers, contract, and integration tests could not
change the comparison. The selected command was:

```sh
python -m pytest -q \
  tests/harness/test_memory_store.py \
  tests/harness/test_memory_tools.py \
  tests/harness/test_memory_global.py \
  tests/harness/test_slash_memory.py \
  tests/harness/test_slash_recall.py \
  tests/harness/test_conventions.py \
  tests/harness/test_memory_runtime_reuse.py \
  tests/harness/server/test_memory_route.py \
  -m 'not live'
```

Collection reported 49 tests: 3 server-route, 6 conventions, 17 global-memory,
2 runtime-reuse, 13 store, 4 memory-tools, 1 slash-memory, and 3 slash-recall.

With a temporary `chromadb.py` import-error shim prepended to `PYTHONPATH` (and
`sys.modules["chromadb"] = None` in the invoking pytest process), the command
exited 0 with **49 passed**. This keeps the baseline local and avoids hosted
embedding calls, including the subprocesses used by global-promotion tests.
The only warning was the existing Starlette `httpx` deprecation warning.

With the installed Chroma package and the same clean export, the command exited
1 with **46 passed and 3 failed**:

- `tests/harness/test_memory_global.py::test_promote_copies_with_provenance`
- `tests/harness/test_memory_global.py::test_promote_dedup_on_repromote`
- `tests/harness/test_memory_global.py::test_concurrent_promote_lock`

Each failure reached `voss_runtime/memory/semantic.py` while a promotion
subprocess called Chroma's OpenAI embedding function and received HTTP 429
`insufficient_quota` (`You have no credits remaining`). These are provider- and
environment-dependent failures from the clean baseline; no live provider is
needed for the Laravel contract or local integration checks.

The baseline did not modify source files, inspect real data, or perform Git
writes. Only synthetic fixtures were used; the initial Chroma-enabled run
attempted hosted embedding calls and hit the quota errors above. Laravel
service migration and readiness completed for the live run. The real
cross-process suite was:

```sh
python -m pytest -q \
  tests/harness/test_laravel_memory_integration.py
```

It exited 0 with **5 passed** and the existing Starlette `httpx` deprecation
warning. The fixture launched `php artisan serve` on `127.0.0.1` with a
temporary SQLite database and synthetic bearer token, exercised the Python
client, the Laravel gateway, and the existing FastAPI `/memory` route, then
terminated and restarted the service to verify persistence. The outage case
confirmed an explicit unavailable error and no local Markdown fallback.

Final root verification after service review and scaffold cleanup: `vendor/bin/phpunit`
passed **12 tests with 123 assertions**. Earlier pagination/search test failures
were resolved. Unused scaffold example tests were removed, and malformed
cursor validation was added. Pint and strict Composer validation passed.
