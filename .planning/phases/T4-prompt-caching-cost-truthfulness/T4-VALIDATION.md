---
phase: T4
slug: prompt-caching-cost-truthfulness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-16
---

# Phase T4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project standard) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| **Quick run command** | `python3 -m pytest tests/harness/test_cache_tokens.py tests/harness/test_agent_caching.py tests/harness/test_cache_invalidation.py -x` |
| **Full suite command** | `python3 -m pytest tests/harness/ -x` |
| **Estimated runtime** | ~30 seconds (quick); ~2 min (full) |

---

## Sampling Rate

- **After every task commit:** Run quick command (`test_cache_tokens.py`, `test_agent_caching.py`, `test_cache_invalidation.py`)
- **After every plan wave:** Run full suite command (`pytest tests/harness/ -x`)
- **Before `/gsd:verify-work`:** Full suite green + manual smoke (`voss chat` → turn 2 cache_read > 0 in RunRecord)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Populated by planner. Each task in PLAN.md gets an `<automated>` block whose command appears here with `requirement` ID, `test type`, and `file exists` status.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _populated by planner_ | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Test files / fixtures that must exist before Wave 1 begins. Drawn from RESEARCH.md §Wave 0 Gaps.

- [ ] `tests/harness/test_cache_tokens.py` — D-04 `extract_cache_tokens` extractor (3 shapes: Anthropic, OpenAI, missing)
- [ ] `tests/harness/test_agent_caching.py` — CACHE-01 marker shape + position on `messages[0]["content"]`
- [ ] `tests/harness/test_cache_invalidation.py` — CACHE-06 four parametrized drift triggers (VOSS.md, cognition, max_iterations, prior_context)
- [ ] `tests/harness/test_cache_integration.py` — CACHE-05 + CACHE-07 first-turn (cassette-driven)
- [ ] `tests/harness/test_cost_accounting.py` — CACHE-03 cache-aware cost differential (extend if file exists)
- [ ] `tests/harness/test_cost_slash.py` — CACHE-04 `--by-model` 4-decimal sum + `--by-tool` placeholder
- [ ] `tests/harness/test_streaming_usage_cache.py` — CACHE-02 streaming half via mocked stream
- [ ] `tests/harness/test_telemetry_cache_fields.py` — CACHE-07 `provider.response` payload + RunRecord round-trip
- [ ] `tests/harness/test_provider_response.py` — CACHE-02 non-streaming half (extend if file exists)
- [ ] `tests/harness/fixtures/cassettes/cache_two_turn_session.yaml` — vcrpy cassette (recorded once via `VOSS_RECORD=1`, committed)
- [ ] `tests/harness/fixtures/cassettes/README.md` — document `VOSS_RECORD=1` re-record workflow
- [ ] `pyproject.toml` — add `vcrpy>=8.0.0,<9` to dev deps; raise `litellm` floor to `>=1.74.0`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real `voss chat` session shows turn-2 cache_read > 0 in RunRecord | SPEC final acceptance bullet | Requires live ANTHROPIC_API_KEY + 5-min TTL window | `ANTHROPIC_API_KEY=… voss chat`, send 2 turns ≤5 min apart, inspect latest `.voss/sessions/*.json` for second iteration's `cache_read_input_tokens > 0` |
| Cassette re-recording when prompt structure drifts | CACHE-05 | One-time recording requires live network | `VOSS_RECORD=1 ANTHROPIC_API_KEY=… python3 -m pytest tests/harness/test_cache_integration.py -x`; commit resulting cassette YAML |

---

## Drift Triggers (CACHE-06 byte-diff comparison)

Each test case mutates exactly one slice of the prefix between A and B versions and asserts `json.dumps(blocks_a, sort_keys=True).encode() != json.dumps(blocks_b, sort_keys=True).encode()`:

| Trigger | Source | Test parametrize ID |
|---------|--------|---------------------|
| VOSS.md text changes | `voss_md_block` | `voss_md` |
| Cognition changes | `cognition_text` (architecture or constraints) | `cognition` |
| `[agent] max_iterations` config change | `_compose_loop_system(max_iterations)` output | `max_iters` |
| `prior_context` block change | `prior_context_text` (M8 project memory feed) | `prior_ctx` |

Model swap is documented but NOT separately tested (inherent to Anthropic per-model cache keying).

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for quick command
- [ ] `nyquist_compliant: true` set in frontmatter once populated

**Approval:** pending
