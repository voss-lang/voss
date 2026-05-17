# T4-01 Test Scaffold Summary

**Completed:** 2026-05-17T03:10:44Z
**Plan:** `T4-01-test-scaffold-PLAN.md`
**Wave:** 1

## Outcome

Landed the T4 Wave 0 red-test scaffold:

- Raised the `litellm` floor to `>=1.74.0` and added `vcrpy>=8.0.0,<9` under dev dependencies.
- Added nine harness pytest files covering CACHE-01 through CACHE-07 with hard-red `pytest.fail(...)` stubs.
- Added the cassette fixture README documenting the `VOSS_RECORD=1` re-record workflow and `filter_headers` redaction contract.
- Removed an unrelated T6 planning file that was accidentally introduced during subagent execution.

## Files Changed

- `pyproject.toml`
- `tests/harness/test_cache_tokens.py`
- `tests/harness/test_agent_caching.py`
- `tests/harness/test_cache_invalidation.py`
- `tests/harness/test_streaming_usage_cache.py`
- `tests/harness/test_provider_response.py`
- `tests/harness/test_cost_accounting.py`
- `tests/harness/test_cost_slash.py`
- `tests/harness/test_telemetry_cache_fields.py`
- `tests/harness/test_cache_integration.py`
- `tests/harness/fixtures/cassettes/README.md`
- `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-01-SUMMARY.md`

## Verification

- `grep -E '"litellm>=1\.74\.0"' pyproject.toml` passed.
- `grep -E '"vcrpy>=8\.0\.0,<9"' pyproject.toml` passed.
- `python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py tests/harness/test_streaming_usage_cache.py tests/harness/test_provider_response.py tests/harness/test_cost_accounting.py tests/harness/test_cost_slash.py tests/harness/test_telemetry_cache_fields.py tests/harness/test_cache_integration.py --collect-only -q` collected 22 tests.
- `python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py -x -q` returned red as intended, stopping on `Failed: T4-02 lands extract_cache_tokens`.
- `test -f tests/harness/fixtures/cassettes/README.md && grep -q "VOSS_RECORD=1" tests/harness/fixtures/cassettes/README.md && grep -q "filter_headers" tests/harness/fixtures/cassettes/README.md` passed.

## Deviations

- Subagent execution created commits even though the worker prompts said not to commit. The final worktree was reconciled without history rewriting.
- One unrelated file, `.planning/phases/T6-slash-debt/T6-PATTERNS.md`, was introduced by a subagent and removed during close-out.

## Self-Check: PASSED
