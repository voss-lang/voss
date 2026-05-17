# T4-06 Cassette Integration Summary

**Completed:** 2026-05-17T17:31:45Z
**Plan:** `T4-06-cassette-integration-PLAN.md`
**Wave:** 5
**Implementation commits:** `80312ad`, `2d428a7`, `a089934`, `c5d7635`, `fab7de7`

## Outcome

Completed the cassette-driven cache integration proof using Claude OAuth, per operator direction:

- Added real `tests/harness/test_cache_integration.py` replay/record tests.
- Patched `AnthropicOAuthProvider` to preserve list-based system content blocks, including `cache_control`.
- Patched Anthropic OAuth streaming usage capture to carry cache creation/read tokens from `message_start` into the final streaming `Usage` event.
- Recorded `tests/harness/fixtures/cassettes/cache_two_turn_session.yaml` through Claude OAuth.
- Verified replay mode with no live request.
- Verified the cassette has no `sk-ant-`, `x-api-key:`, `authorization: Bearer`, `cookie:`, or `set-cookie:` matches.
- Added response-header redaction for cookie/set-cookie headers.
- Removed incidental test tool exposure so the cassette only proves cache lifecycle rather than model-selected tool calls.

## Files Changed

- `voss/harness/providers.py`
- `tests/harness/test_cache_integration.py`
- `tests/harness/fixtures/cassettes/cache_two_turn_session.yaml`
- `tests/harness/test_t1_acceptance.py`
- `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-06-SUMMARY.md`

## Verification

- `VOSS_RECORD=1 python3 -m pytest tests/harness/test_cache_integration.py -x -s` passed with 2 tests and recorded the cassette.
- `python3 -m pytest tests/harness/test_cache_integration.py -x -q` passed with 2 tests in replay mode.
- `python3 -m pytest tests/harness/test_anthropic_stream.py tests/harness/test_cache_integration.py -x -q` passed with 6 tests.
- `python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_provider_response.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py tests/harness/test_streaming_usage_cache.py tests/harness/test_telemetry_cache_fields.py tests/harness/test_cost_accounting.py tests/harness/test_cost_slash.py tests/harness/test_cache_integration.py -x -q` passed with 24 tests.
- `python3 -m pytest tests/harness/test_t1_acceptance.py::test_iter_02_iter_n_plus_one_receives_prior_results -q` passed.
- `python3 -m py_compile voss/harness/providers.py tests/harness/test_cache_integration.py` passed.
- `grep -iE 'sk-ant-|x-api-key:|authorization: Bearer|cookie:|set-cookie:' tests/harness/fixtures/cassettes/cache_two_turn_session.yaml || true` returned no matches.
- `git diff --check` passed.

## Deviations from Plan

- **Operator-directed provider change:** The original plan targeted the LiteLLM API-key path. The operator explicitly requested OAuth instead, so T4-06 now proves the Claude OAuth path.
- **OAuth support fix required:** OAuth cache support required preserving `cache_control` system blocks and extracting cache usage from `message_start`. These were implemented in `voss/harness/providers.py`.
- **Broader harness residual:** `python3 -m pytest tests/harness/ -x -q` now gets past a stale T1 block-list assertion fixed in `fab7de7`, then fails on the pre-existing TUI budget modal `#budget-title` issue.

**Total deviations:** 2 implementation deviations, 1 residual verification gap. **Impact:** T4-06 cache lifecycle proof is green in replay mode; the remaining full-harness failure is outside T4 cache behavior and was already observed in earlier T4 work.

## Notes

- The first OAuth recording attempt reused Anthropic's short-lived server-side cache from a prior attempt, causing `cache_read_input_tokens > 0` on the nominal first turn. The final cassette uses a bumped stable prefix string (`OAuth cache integration v2...`) to force a fresh first-turn cache write.
- The cassette records OAuth traffic, not API-key traffic. This intentionally supersedes the original T4-06 LiteLLM/API-key plan based on the operator request.

## Self-Check: PASSED
