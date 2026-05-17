# T4-03 Agent Composition Summary

**Completed:** 2026-05-17T06:43:45Z
**Plan:** `T4-03-agent-composition-PLAN.md`
**Wave:** 3

## Outcome

Implemented the CACHE-01 / CACHE-06 agent-side prompt caching shape:

- Added `voss.harness.agent._compose_system_blocks(...)`.
- Changed `run_turn` static system prefix composition from a joined `sys_prompt` string to a typed text block list assigned to `messages[0]["content"]`.
- Kept the per-iteration rider as the separate uncached `messages[1]` string.
- Turned `test_agent_caching.py` green for marker shape and empty-input behavior.
- Turned `test_cache_invalidation.py` green for the four locked drift triggers using deterministic `json.dumps(..., sort_keys=True).encode()`.
- Updated existing system-prompt inspection tests to read text from both string and block-list message content.

## Files Changed

- `voss/harness/agent.py`
- `tests/harness/test_agent_caching.py`
- `tests/harness/test_cache_invalidation.py`
- `tests/harness/test_agent_loop.py`
- `tests/harness/test_agent_integration.py`
- `tests/harness/test_voss_md_injection.py`
- `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-03-SUMMARY.md`

## Verification

- `python3 -m pytest tests/harness/test_agent_caching.py -x -q` passed with 2 tests.
- `python3 -m pytest tests/harness/test_cache_invalidation.py -x -q` passed with 4 tests.
- `python3 -m pytest tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py -x -q` passed with 6 tests.
- `python3 -m pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py tests/harness/test_agent_integration.py tests/harness/test_agent_caching.py -x -q` passed with 39 tests.
- `python3 -m pytest tests/harness/test_voss_md_injection.py tests/harness/test_agent_integration.py::test_turn_injects_cognition tests/harness/test_agent_integration.py::test_resume_injects_prior_run_context -x -q` passed with 4 tests.
- `python3 -m pytest tests/harness/test_agent_loop.py tests/harness/test_agent_loop_helpers.py tests/harness/test_agent_integration.py tests/harness/test_voss_md_injection.py -x -q` passed with 39 tests.
- `python3 -m pytest tests/harness/test_provider_response.py tests/harness/test_cache_tokens.py -x -q` passed with 8 tests.
- `python3 -m py_compile voss/harness/agent.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py tests/harness/test_agent_loop.py tests/harness/test_agent_integration.py tests/harness/test_voss_md_injection.py` passed.
- `grep -n 'sys_prompt' voss/harness/agent.py | grep -v '^#'` returned no matches.
- `grep -nE '_compose_system_blocks\b' voss/harness/agent.py` returned one definition and one call site.
- `python3 -c "from voss.harness.agent import _compose_system_blocks; b=_compose_system_blocks(voss_md_block='A', cognition_text='B', prior_context_text='C', loop_system='D'); assert len(b)==4 and b[-1]['cache_control']=={'type':'ephemeral'}"` passed.
- `git diff --check` passed.

## Notes

- Existing tests that introspected `messages[*]["content"]` as a string were updated to render block-list content to text for assertions.
- OAuth-provider cache marker preservation remains out of T4 scope per `T4-RESEARCH.md` Pitfall 3. `AnthropicOAuthProvider._payload` reconstructs text chunks and would drop markers from list-typed content; that is a follow-up, not part of this LiteLLM-path caching plan.
- During execution, unrelated T6/site commits appeared in the branch history. They were not part of this T4-03 close-out.

## Self-Check: PASSED
