---
phase: 07-rust-port
plan: 07-08
subsystem: providers
tags: [rust, codex, openai, oauth, sse, wiremock]
requires:
  - phase: 07-rust-port
    provides: Codex auth resolution, refresh_codex, and prior OpenAI provider scaffold
provides:
  - Codex CLI ChatGPT fixture capture
  - Codex fixture replay projection test
  - Codex refresh-on-401 provider test
  - Opt-in live Codex smoke test
affects: [voss-providers, voss-cli, codex-auth]
tech-stack:
  added: []
  patterns: [wiremock replay, SSE response parsing fallback, VOSS_LIVE_SMOKES gated live smoke]
key-files:
  created:
    - .planning/codex-fixtures/codex-cli-chatgpt-success.json
    - crates/voss-providers/tests/codex_fixture_replay.rs
    - crates/voss-providers/tests/codex_refresh_on_401.rs
    - crates/voss-providers/tests/live_codex.rs
    - crates/voss-providers/tests/snapshots/codex/.gitkeep
  modified:
    - crates/voss-providers/src/openai.rs
key-decisions:
  - "Use Codex CLI 0.130.0's real SSE request/response capture as the fixture source."
  - "Replay the Voss-representable Codex protocol projection rather than byte-identical full CLI context."
patterns-established:
  - "Codex fixtures may be combined request/response JSON objects with SSE string response bodies."
requirements-completed: [RUST-28, RUST-29, RUST-30]
duration: 70min
completed: 2026-05-09
---

# Phase 07-08 Summary

**Codex ChatGPT fixture capture with Rust OpenAI provider SSE parsing, fixture replay, refresh retry, and live-smoke coverage**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-05-09T17:59:00-07:00
- **Completed:** 2026-05-09T18:12:00-07:00
- **Tasks:** 4
- **Files modified:** 6 plus fixture artifact

## Accomplishments

- Captured a successful real Codex CLI ChatGPT-mode request/response fixture with credentials redacted.
- Added fixture replay coverage for the current Codex protocol fields: SSE, `stream: true`, `parallel_tool_calls`, `reasoning`, `prompt_cache_key`, and `local_shell` tool presence.
- Added Codex 401-refresh retry coverage and a `VOSS_LIVE_SMOKES`-gated live smoke.
- Updated `OpenAIOAuthProvider` response handling so SSE bodies are parsed even when mock responses omit a `content-type`.

## Files Created/Modified

- `.planning/codex-fixtures/codex-cli-chatgpt-success.json` - Redacted combined fixture from Codex CLI 0.130.0 using ChatGPT OAuth.
- `crates/voss-providers/src/openai.rs` - SSE response fallback parses raw SSE bodies before attempting JSON.
- `crates/voss-providers/tests/codex_fixture_replay.rs` - Replays the captured Codex fixture through wiremock and asserts supported protocol projection.
- `crates/voss-providers/tests/codex_refresh_on_401.rs` - Verifies 401 triggers `refresh_codex` and one retry.
- `crates/voss-providers/tests/live_codex.rs` - Opt-in live Codex smoke gated by `VOSS_LIVE_SMOKES=1`.
- `crates/voss-providers/tests/snapshots/codex/.gitkeep` - Keeps Codex snapshot directory present.

## Fixture Shape

Phase A produced one combined fixture:

```json
{
  "captured_at": "...",
  "upstream": "https://chatgpt.com/backend-api/codex/responses",
  "request": { "method": "POST", "url": "...", "headers": {}, "body": {} },
  "response": { "status": 200, "headers": {}, "body": "event: response.created\n..." }
}
```

The response body is an SSE string, not JSON. Credential-bearing headers are redacted.

## Dynamic Fields

The replay test does not compare the full captured body byte-for-byte because the Codex CLI request includes CLI-only developer prompt context, tool definitions, session ids, thread ids, timestamps, installation ids, and current skill/tool metadata that `CompleteRequest` cannot represent.

Instead, the test locks the Voss-representable protocol projection:

- `model`
- `store`
- `stream`
- `parallel_tool_calls`
- `prompt_cache_key` presence
- `reasoning` presence
- `local_shell` compatibility tool presence
- `originator`, `OpenAI-Beta`, and `chatgpt-account-id` headers

Dynamic fixture fields include session/thread/request ids, timestamps, prompt cache key values, Codex installation id, full CLI developer context, and full Codex tool catalog.

## Decisions Made

- Preserved `originator: codex_cli_rs` per the phase plan and existing Python parity, even though Codex CLI 0.130.0 emits `originator: codex_exec` in the captured fixture.
- Did not add a user-facing experimental warning in Rust CLI wiring; the existing base branch already wired Codex auth to `OpenAIOAuthProvider`.
- Treated the pre-existing OpenAI provider and CLI wiring as prior work and limited this execution to fixture capture, SSE parsing, and tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adapted fixture replay to actual Codex fixture shape**
- **Found during:** Task 2
- **Issue:** The plan expected a single JSON response body, but current Codex CLI returns SSE and the full request includes CLI-only fields not representable by Voss provider input.
- **Fix:** Fixture replay asserts the supported protocol projection and parses SSE response text.
- **Files modified:** `crates/voss-providers/tests/codex_fixture_replay.rs`, `crates/voss-providers/src/openai.rs`
- **Verification:** `cargo test -p voss-providers --test codex_fixture_replay`

**2. [Rule 3 - Blocking] SSE parsing now falls back on body prefix**
- **Found during:** Task 2
- **Issue:** Wiremock returned the SSE fixture with a header form that did not satisfy the provider's strict content-type check, so it tried JSON parsing.
- **Fix:** Read successful responses as text first, then parse as SSE when content type or body prefix indicates SSE.
- **Files modified:** `crates/voss-providers/src/openai.rs`
- **Verification:** `cargo test -p voss-providers --no-fail-fast`

---

**Total deviations:** 2 auto-fixed.
**Impact on plan:** Required to make tests reflect the real Codex CLI capture. No unrelated scope was added.

## Issues Encountered

- The first local capture only caught analytics traffic because `chatgpt_base_url` did not route the model call as expected.
- The internal `codex responses-api-proxy` produced request dumps but dummy-token upstream responses were 401.
- A final localhost proxy forwarded the real ChatGPT access token to upstream and wrote only redacted fixture data, producing the successful fixture.

## Verification

- `cargo test -p voss-providers --test codex_fixture_replay`
- `cargo test -p voss-providers --test codex_refresh_on_401`
- `VOSS_LIVE_SMOKES= cargo test -p voss-providers --test live_codex`
- `cargo test -p voss-providers --no-fail-fast`
- `cargo build -p voss-cli`
- `cargo run -p voss-cli -- doctor 2>&1 | grep -E 'Codex|codex'`
- `grep -n 'codex_cli_rs\|OpenAI-Beta\|chatgpt-account-id' crates/voss-providers/src/openai.rs`

## User Setup Required

None. Live Codex testing remains opt-in with `VOSS_LIVE_SMOKES=1`.

## Next Phase Readiness

Codex provider coverage is ready for downstream REPL/dispatcher verification. The remaining risk is protocol drift in future Codex CLI versions, especially `originator`, tool catalog, and SSE event names.

---
*Phase: 07-rust-port*
*Completed: 2026-05-09*
