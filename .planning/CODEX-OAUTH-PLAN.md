# Codex OAuth (ChatGPT Subscription) — Implementation Plan

**Created:** 2026-05-09
**Status:** Spike → Implementation
**Depends on:** v1.1 H1 harness baseline (`voss/harness/providers.py:OpenAIOAuthProvider` skeleton already in place).

The harness already discovers Codex credentials and routes ChatGPT-mode tokens to `chatgpt.com/backend-api/codex/responses`. The endpoint accepts the bearer + account-id, but rejects every request body the harness has tried with HTTP 400 "The '<model>' model is not supported when using Codex with a ChatGPT account." This means: auth works, request shape doesn't.

ChatGPT-issued OAuth tokens are scoped to **Codex CLI's exact wire format**. Same posture as Anthropic OAuth requiring the Claude Code system preamble — but stricter. Closing the gap is a reverse-engineering task, not an SDK call.

---

## Phase A — Reverse-Engineer Codex CLI's Wire Shape

Three independent sources, all required.

### A1. Read the source
- Repo: `github.com/openai/codex` (Rust, MIT-licensed).
- Files of interest:
  - `codex-rs/core/src/client.rs` — request construction.
  - `codex-rs/core/src/chatgpt.rs` (or similar) — ChatGPT-account branch.
  - `codex-rs/core/src/protocol.rs` — request/response models.
  - `codex-rs/core/src/openai_tools.rs` — built-in tool definitions (`local_shell`, etc.).
- Capture: exact JSON payload shape, header set, allowed model names, presence/absence of `instructions`, `session_id`, `parallel_tool_calls`, `reasoning`, etc.

### A2. Capture real traffic
Two options, in order of preference:
- **mitmproxy.** Run `mitmproxy --mode reverse:https://chatgpt.com -p 8443`, set `OPENAI_API_BASE=http://localhost:8443` (or the Codex equivalent env knob — likely `CODEX_BASE_URL`), run a real `codex exec "ping"`. Capture the request. Dump body verbatim.
- **trace logging.** `RUST_LOG=codex=trace codex exec "ping" 2>&1 | grep -A50 "request body"`. Less reliable but no proxy setup.

Persist captures to `.planning/codex-fixtures/<timestamp>.{request,response}.json`. These become test fixtures.

### A3. Document the contract
Write `.planning/codex-fixtures/CONTRACT.md` listing:
- Endpoint: `POST https://chatgpt.com/backend-api/codex/responses`.
- Required headers: `authorization`, `chatgpt-account-id`, `originator`, `OpenAI-Beta`, `session_id`, plus any UA pattern Codex enforces.
- Required body fields (the unknowns we currently miss):
  - `model` — list of accepted names.
  - `instructions` — Codex preamble text (verbatim).
  - `session_id` — UUIDv4 per session.
  - `tools` — possibly required to include `local_shell` even when the harness won't use it.
  - `parallel_tool_calls`, `reasoning`, `prompt_cache_key`, `safety_identifier`, `store`, `stream` — flag set.
- Response shape: `output[]` blocks, including `reasoning` block emitted by GPT-5.

A1+A2+A3 together = ~1-2 days of work. No code changes yet.

---

## Phase B — Implement

### B1. Wire-format compatibility
Update `OpenAIOAuthProvider._payload` and `_headers` to match the captured contract:
- Add `session_id` (generated once per provider instance, UUIDv4).
- Add `instructions` set to the Codex preamble string copied verbatim from Codex CLI source. Treat this like the Claude Code preamble — it is a magic constant.
- Add `tools` always; include the `local_shell` tool definition even if the harness intercepts and refuses it.
- Add the missing flags (`store: false`, `stream: false`, `parallel_tool_calls: false`, `prompt_cache_key`, `reasoning: {effort: "medium"}` for GPT-5).
- Allowed models behind a constant: `{"gpt-5", "gpt-5-codex", "o3", "o4-mini"}` — pin the list, fail-fast for unknown ones.

### B2. Response handling
Codex responses include a `reasoning` block before the `message`. Update extraction:
- Iterate every `output` element.
- For `type == "reasoning"`: drop or surface as renderer "thinking" (optional, dev-mode only).
- For `type == "message"`: extract `output_text`/`text`.
- For `type == "tool_use"` / `type == "function_call"`: same translation as Anthropic — match the harness's `Plan` schema or the requested `local_shell` tool.

### B3. Refresh flow
`auth.refresh_codex` already targets `auth.openai.com/oauth/token`. Verify the refresh response actually returns `access_token`, `refresh_token`, `id_token` — Codex rotates the id_token too. Persist all three back to `~/.codex/auth.json` so subsequent `codex` CLI invocations don't break.

### B4. Tool schema translation
The harness's `Plan` requires forced JSON output. Two paths:
- **Path 1 (preferred): JSON schema response_format.** Already in the payload (`text.format.json_schema`). Test whether Codex's ChatGPT mode honors it.
- **Path 2 (fallback): forced tool call.** Define a `submit_plan` function tool with the Plan schema, set `tool_choice: {"type": "function", "name": "submit_plan"}`. Same trick we use for Anthropic.

Decide based on what A2 captures show.

---

## Phase C — Test

### C1. Hermetic
Create `tests/harness/test_codex_chatgpt_wire.py` using captured fixtures from A2:
- Replay the recorded request body, assert byte-exact match against our payload builder.
- Replay the recorded response, assert harness extracts the same `text` and `parsed Plan`.
- One fixture per accepted model.

### C2. Live (skipped in CI)
Add `tests/harness/live/test_codex_oauth_live.py` with `@pytest.mark.live`:
- `voss do --auth codex --yes "what is 2+2?"` → exit 0, output contains `4` or `four`.
- `voss do --auth codex --yes "list python files"` → uses fs_glob, returns list.
- Run nightly only; gated on a real `~/.codex/auth.json` existing.

### C3. Refresh
Force expiry by mutating the persisted `tokens.access_token` to a short-lived value, then run a turn. Assert refresh fired and the file was rewritten.

---

## Phase D — Polish

### D1. Drop the experimental warning
Once C1+C2 pass, remove the `[warning: codex-oauth ... is experimental]` banner from `voss/harness/cli.py`.

### D2. Doctor improvements
`voss doctor` should distinguish Codex modes clearly:
```
Codex creds         : found
  auth_mode         : ChatGPT
  account_id        : acct_42
  api_key           : (none — ChatGPT subscription only)
  oauth tokens      : present (refresh available)
  protocol          : codex-cli (chatgpt.com/backend-api/codex)
```

### D3. Documentation
Update `HARNESS-PLAN.md` §10 risks: remove "Codex ChatGPT mode unsupported," add "Codex protocol may break on Codex CLI updates — pin tested wire format, surface clear errors."

---

## Risks

| Risk | Mitigation |
|---|---|
| Codex wire format changes between releases | Pin tested format, snapshot fixtures, set up nightly live test as canary. |
| ToS — OpenAI's terms scope ChatGPT tokens to first-party clients (Codex CLI) | Personal-use only, document loudly, keep `--auth=api` as the supported path for distribution. |
| Token refresh fails silently in offline scenarios | Detect 401 + no network → fall back to `--auth=api` if any API key available, print actionable error otherwise. |
| `local_shell` tool injected by Codex protocol confuses our agent loop | Intercept and refuse `local_shell` invocations; the harness handles its own shell via the `shell_run` tool. |

---

## Effort Estimate

| Phase | Engineer-days |
|---|---|
| A — Reverse-engineer + document contract | 1-2 |
| B — Implement wire compat + response handling + refresh | 1-2 |
| C — Tests (hermetic + live + refresh) | 1 |
| D — Polish + docs | 0.5 |
| **Total** | **3.5-5.5 days** |

---

## Acceptance Criteria

1. `voss do --auth codex --yes "<task>"` against a real ChatGPT subscription returns a useful answer with confidence ≥ 0.6 on at least three smoke prompts (math, code listing, file edit).
2. Hermetic test suite replays captured fixtures byte-exact and parses the response.
3. 401 → refresh → retry path covered by hermetic test.
4. `voss doctor` clearly reports Codex mode and protocol.
5. The experimental warning is removed.
