---
phase: T4-prompt-caching-cost-truthfulness
plan: 06
type: execute
wave: 5
depends_on: ["T4-01", "T4-02", "T4-03", "T4-04"]
files_modified:
  - tests/harness/test_cache_integration.py
  - tests/harness/fixtures/cassettes/cache_two_turn_session.yaml
autonomous: false
requirements: [CACHE-05, CACHE-07]
user_setup:
  - service: anthropic-api
    why: "One-time cassette recording requires a live ANTHROPIC_API_KEY with access to claude-sonnet-4-5 (or current default). After recording, CI replays from the committed YAML — no live key needed in normal runs."
    env_vars:
      - name: ANTHROPIC_API_KEY
        source: "https://console.anthropic.com/settings/keys (Voss developer's personal key — never committed)"
      - name: VOSS_RECORD
        source: "Set to `1` ONLY during the one-time recording run; absent during normal pytest invocation"

must_haves:
  truths:
    - "Two consecutive harness turns within a single session — via the LiteLLM path — write a vcrpy cassette to tests/harness/fixtures/cassettes/cache_two_turn_session.yaml."
    - "CI replay (without VOSS_RECORD) shows turn 1 with cache_creation_input_tokens > 0 AND cache_read_input_tokens == 0 (CACHE-07 first-turn invariant)."
    - "CI replay shows turn 2 with cache_read_input_tokens > 0 (CACHE-05 cross-turn cache HIT)."
    - "The committed cassette YAML carries no API key (filter_headers redacts x-api-key, authorization, anthropic-api-key, cookie, set-cookie)."
  artifacts:
    - path: "tests/harness/test_cache_integration.py"
      provides: "Two green pytest tests asserting first-turn write + second-turn read via the recorded cassette."
    - path: "tests/harness/fixtures/cassettes/cache_two_turn_session.yaml"
      provides: "vcrpy YAML cassette of a two-turn Anthropic conversation; redacted headers."
  key_links:
    - from: "tests/harness/test_cache_integration.py"
      to: "tests/harness/fixtures/cassettes/cache_two_turn_session.yaml"
      via: "vcr.use_cassette(...) context manager with record_mode='none' in CI"
      pattern: "vcr.use_cassette"
---

<objective>
Record one vcrpy cassette covering a two-turn Anthropic conversation against the LiteLLM path, commit it, and land two green pytest tests that replay it to prove (a) the first turn writes the cache (CACHE-07 invariant: cache_creation > 0 AND cache_read == 0), and (b) the second turn reads it (CACHE-05: cache_read > 0). CI runs in replay-only mode — no live network calls.

Purpose: End-to-end falsifiability anchor for the entire T4 phase. Unit tests cover individual surfaces (extractor, composer, telemetry, recorder, cost); this cassette-driven integration proves the full path from `_compose_system_blocks` → LiteLLM `translate_system_message` → Anthropic API → `extract_cache_tokens` → IterationRecord → assertion actually delivers cache HIT.
Output: One recorded YAML cassette + two green tests. Includes one blocking human-action checkpoint for the one-time recording (the only step Claude literally cannot self-serve — it requires a live ANTHROPIC_API_KEY plus 2+ minutes of session activity that cannot be cassette-bootstrapped).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-SPEC.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-CONTEXT.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-RESEARCH.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-PATTERNS.md
@.planning/phases/T4-prompt-caching-cost-truthfulness/T4-VALIDATION.md
@tests/harness/test_anthropic_stream.py
@tests/harness/fixtures/cassettes/README.md
@voss_runtime/providers/litellm_provider.py
@voss/harness/agent.py

<interfaces>
<!-- The integration surface this test exercises end-to-end. -->

LiteLLM path (NOT OAuth — per RESEARCH.md Pitfall 3): the test must drive `LiteLLMProvider.complete` (or a streaming counterpart) against `claude-sonnet-4-5`. The LiteLLM stack under the hood uses httpx → httpcore — vcrpy 8 patches httpcore.

Cassette context manager pattern (RESEARCH.md Pattern 3, copied verbatim into T4-PATTERNS.md "test_cache_integration.py"):
```python
def _cassette(name: str):
    record_mode = "new_episodes" if os.environ.get("VOSS_RECORD") == "1" else "none"
    return vcr.use_cassette(
        str(_CASSETTE_DIR / f"{name}.yaml"),
        record_mode=record_mode,
        filter_headers=[
            "x-api-key", "authorization", "anthropic-api-key",
            "cookie", "set-cookie",
        ],
    )
```

Cassette name (RESEARCH.md Open Question 5): one cassette per fixture trace, NOT per test function. Both tests use the same `cache_two_turn_session` cassette name.

Two-turn invariant the cassette must encode:
- Turn 1 prompt: "Hello, identify yourself and the model you are."  (small, cheap; the prompt body matters less than the >1024-token cached prefix Voss prepends).
- Turn 2 prompt: "Now describe one project you've helped with." (same session continues — same composed prefix → cache should HIT).
- Both turns within 5 minutes (Anthropic TTL).

The Voss harness composes >1024-token cached prefix automatically from VOSS.md + cognition + loop system → the >1024-token Anthropic cache eligibility threshold is satisfied without any test-side padding (verified by inspection of `PLAN_LOOP_SYSTEM` length).
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: [BLOCKING-HUMAN-ACTION] Record the two-turn cassette with a live ANTHROPIC_API_KEY</name>
  <what-built>
    All upstream T4 plans (01-05) are merged: agent.py emits the multi-block system content with one trailing cache_control marker; LiteLLMProvider populates cache fields; pyproject pins are raised; vcrpy is available. The system is wire-ready for a recording run.
  </what-built>
  <how-to-verify>
    Run a one-time live recording (Claude cannot self-serve — requires a personal Anthropic API key plus a 2-turn live session). Suggested script (paste into a shell, replacing the placeholder):

    1. Confirm pre-reqs:
       ```
       python3 -c "import vcr; print(vcr.__version__)"   # expect 8.x
       python3 -c "import litellm; print(litellm.__version__)"  # expect ≥1.74.0
       ```
    2. Set up the recording env:
       ```
       export ANTHROPIC_API_KEY=sk-ant-...    # your personal key — never committed
       export VOSS_RECORD=1
       ```
    3. Run the cassette test in recording mode:
       ```
       python3 -m pytest tests/harness/test_cache_integration.py -x -s
       ```
       The tests will execute the two-turn conversation against claude-sonnet-4-5 and write `tests/harness/fixtures/cassettes/cache_two_turn_session.yaml`.
    4. Unset the recording env so subsequent local runs use the committed cassette:
       ```
       unset VOSS_RECORD ANTHROPIC_API_KEY
       ```
    5. Re-run the test in REPLAY mode to confirm the cassette works:
       ```
       python3 -m pytest tests/harness/test_cache_integration.py -x
       ```
       This must pass without network access.

    Inspect the committed cassette to verify redaction:
    ```
    grep -i 'sk-ant-\|x-api-key:\|authorization: Bearer' tests/harness/fixtures/cassettes/cache_two_turn_session.yaml
    ```
    Expected: zero matches. If any match appears, the recording leaked a secret — DELETE the cassette and re-record with a stricter `filter_headers` list.

    Both tests in the file must be green in replay mode before approving.
  </how-to-verify>
  <resume-signal>
    Type `approved` after: (a) cassette YAML committed to `tests/harness/fixtures/cassettes/cache_two_turn_session.yaml`, (b) replay-mode run of test_cache_integration.py exits 0, (c) cassette is verified secret-free. OR type the error message + the cassette path so Claude can re-attempt the test layer.
  </resume-signal>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement test_cache_integration.py against the committed cassette</name>
  <files>tests/harness/test_cache_integration.py</files>
  <behavior>
    - `test_first_turn_writes_cache` (CACHE-07 invariant): replay the cassette, capture turn 1's IterationRecord (or ProviderResponse depending on which surface the test drives), assert `cache_creation_input_tokens > 0 AND cache_read_input_tokens == 0`.
    - `test_second_turn_reads_cache` (CACHE-05): replay the same cassette, capture turn 2's IterationRecord, assert `cache_read_input_tokens > 0`.
    - Both tests share the SAME cassette name `cache_two_turn_session` (RESEARCH.md Open Question 5).
    - When `VOSS_RECORD=1`, record_mode is `new_episodes`; otherwise `none` (CI default).
  </behavior>
  <action>
    Convert the T4-01 red stubs in `tests/harness/test_cache_integration.py` to working tests per RESEARCH.md Pattern 3 + T4-PATTERNS.md "test_cache_integration.py":

    Module docstring: `"""CACHE-05 + CACHE-07: end-to-end cassette-driven proof that the cached static prefix is written on turn 1 and read on turn 2. Replay-only in CI."""`

    Imports: `import os`, `import pytest`, `from pathlib import Path`. Inside `pytest.importorskip("vcr")` for the `import vcr` so a missing vcrpy install doesn't crash collection.

    Helper `_cassette(name)`: reuse the verbatim block from T4-PATTERNS.md.

    Per-test scaffolding — driving the harness end-to-end (NOT just LiteLLMProvider in isolation, because CACHE-07 requires the IterationRecord round-trip):
    1. Build a minimal test driver that invokes the Voss harness's `run_turn` (or the equivalent two-turn loop) inside the `_cassette` context manager. Use a minimal cwd (e.g., `tmp_path`) with no VOSS.md so the cached prefix is just `cognition + loop_system` (still well over 1024 tokens — RESEARCH.md confirms PLAN_LOOP_SYSTEM size).
    2. After turn 1 completes, inspect `rec._iterations[-1]` (RunRecorder internal) OR the finalized RunRecord's `iterations[-1]` and assert the cache field values.
    3. After turn 2, repeat with the second iteration.
    4. If two tests share the same cassette but each test runs only one turn (vcrpy is request-scoped), structure it as ONE async test function that runs both turns sequentially under the same cassette context, asserting both invariants in one body. (Two functions both opening the same cassette and replaying the SAME first request twice is fine for replay mode but wasteful — collapse to one test function if the executor finds that simpler.)

    Recommended structure (one test function, two assertion groups):
    ```python
    @pytest.mark.asyncio
    async def test_two_turn_cache_lifecycle(tmp_path):
        with _cassette("cache_two_turn_session"):
            turn1_rec = await _run_one_turn(cwd=tmp_path, prompt="Hello, ...")
            turn2_rec = await _run_one_turn(cwd=tmp_path, prompt="Now describe ...")
        # CACHE-07 first-turn invariant
        assert turn1_rec.cache_creation_input_tokens > 0
        assert turn1_rec.cache_read_input_tokens == 0
        # CACHE-05 second-turn HIT
        assert turn2_rec.cache_read_input_tokens > 0
    ```

    Alternatively keep them as two functions if vcrpy in record_mode='none' tolerates re-playing the same cassette from two test invocations — verify locally during recording. Either structure is acceptable; one function is simpler and recommended.

    Model selection: use `claude-sonnet-4-5` (current default per RESEARCH.md A7; aliased through `_MODEL_ALIASES`).

    Critical: this test drives the LiteLLM path, NOT the OAuth path (Pitfall 3 deferral). If the harness's default provider resolution picks OAuth, force the LiteLLM path via the same mechanism existing harness tests use (search `tests/harness/` for a pattern; if none, override via a kwarg or monkeypatch on `voss_runtime.providers.get_provider`).

    The cassette YAML is recorded in Task 1; this Task 2 only writes the test code that consumes it. If Task 1 is rejected (replay fails), Task 2 cannot land — feedback loop with the human.
  </action>
  <verify>
    <automated>python3 -m pytest tests/harness/test_cache_integration.py -x -q</automated>
  </verify>
  <done>
    Both assertion groups (CACHE-07 first-turn invariant + CACHE-05 second-turn HIT) pass against the committed cassette in replay-only mode. No live network access made. The cassette file is committed under tests/harness/fixtures/cassettes/.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Anthropic API → committed cassette → CI replay | Cassette must NOT carry API keys; `filter_headers` redacts them at record time. |
| developer local recording → repo | The recording shell session uses a live ANTHROPIC_API_KEY; the committed YAML must not. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T4-06-01 | Information Disclosure | cache_two_turn_session.yaml | mitigate | `filter_headers=['x-api-key','authorization','anthropic-api-key','cookie','set-cookie']` redacts at record time; checkpoint Task 1 includes a `grep -i 'sk-ant-\|x-api-key:'` verification step before approval. |
| T-T4-06-02 | Repudiation | stale cassette masking real API drift | mitigate | `record_mode='none'` raises on signature drift (RESEARCH.md Pitfall 5); the cassette-not-found failure is the documented signal to re-record. README.md (from T4-01) documents the workflow. |
| T-T4-06-03 | Tampering | cassette replay forging cache HIT | mitigate | CACHE-07 first-turn invariant (`cache_creation > 0 AND cache_read == 0`) — a degenerate cassette that fakes cache_read on turn 1 would FAIL this test. Falsifiability anchor against bogus cassettes. |
| T-T4-06-04 | Tampering | cassette schema drift across vcrpy versions | accept | pin `vcrpy>=8.0.0,<9` (set in T4-01); v9 may break the cassette format and require a re-record. README.md documents the re-record workflow. |
| T-T4-06-SC | Tampering | vcrpy install | mitigate | vcrpy in Package Legitimacy Audit as Approved; pin floor set in T4-01. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_cache_integration.py -x -q` exits 0 with no live network access (test the second time on a machine without ANTHROPIC_API_KEY set).
- `test -f tests/harness/fixtures/cassettes/cache_two_turn_session.yaml` exists.
- `grep -iE 'sk-ant-|x-api-key:|authorization: Bearer' tests/harness/fixtures/cassettes/cache_two_turn_session.yaml` returns zero matches.
- `python3 -m pytest tests/harness/ -x -q` — full T4 suite green (all CACHE-NN tests including this one).
</verification>

<success_criteria>
- Cassette `cache_two_turn_session.yaml` exists at the documented path with redacted headers.
- `test_cache_integration.py` runs green in replay-only mode (CI-equivalent: no `VOSS_RECORD`, no `ANTHROPIC_API_KEY`).
- CACHE-07 first-turn invariant proven: turn 1 writes cache (`creation > 0, read == 0`).
- CACHE-05 cross-turn HIT proven: turn 2 reads cache (`read > 0`).
- Full T4 phase suite (`pytest tests/harness/ -x` plus the manual smoke from SPEC) is green.
- Blocking human-action checkpoint completed and approved (one-time cost; never repeated unless prompt structure drifts).
</success_criteria>

<output>
Create `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-06-SUMMARY.md` when done. Note any cassette re-record drift triggers observed during recording (if the executor noticed any prompt-prefix instability worth flagging for the SPEC final manual smoke).
</output>
