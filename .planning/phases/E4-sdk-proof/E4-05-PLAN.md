---
phase: E4-sdk-proof
plan: 05
type: execute
wave: 3
depends_on: [E4-02]
files_modified:
  - crates/voss-sdk/examples/sdk_proof_consumer.rs
autonomous: true
requirements: [EVSDK-05]
must_haves:
  truths:
    - "The Rust consumer decodes the typed AgentEvent stream: it matches AgentEvent variants and collects type strings (ServerConnected/FinalEvent/SessionIdle/PermissionUpdated)"
    - "The Rust consumer reaches SessionIdle and stops consuming the stream (no hang); under FAKE_TURN it reports saw_permission_gate=false (permission gate is live-only)"
    - "The Rust consumer has the PermissionUpdated->permission_reply branch (choice from VOSS_PERMISSION_CHOICE, default a) ready for the live Allow/Deny scenarios"
    - "The Rust consumer uses VossClient::new (never spawn_with) — it connects to the runner-spawned server via VOSS_BASE_URL/VOSS_TOKEN"
    - "The Rust consumer emits one valid JSON line with all six keys {surface,session_id,final,saw_permission_gate,cost_usd,event_types_seen}"
    - "The example is auto-discovered from crates/voss-sdk/examples/ and builds with cargo build --example sdk_proof_consumer (no Cargo.toml [[example]] edit and no new [dependencies])"
  artifacts:
    - path: "crates/voss-sdk/examples/sdk_proof_consumer.rs"
      provides: "Hardened Rust consumer: VossClient::new + event_stream match + env-driven permission_reply, six-key JSON emission"
      contains: "VossClient::new"
  key_links:
    - from: "crates/voss-sdk/examples/sdk_proof_consumer.rs"
      to: "event_stream(client, session_id) Stream<Item=Result<AgentEvent,VossError>>"
      via: "while stream.next(): match AgentEvent variants; permission_reply on PermissionUpdated"
      pattern: "AgentEvent::"
    - from: "crates/voss-sdk/examples/sdk_proof_consumer.rs"
      to: "stdout structured JSON"
      via: "one-line JSON with the six-key schema; runner extracts final + scores via E1"
      pattern: "event_types_seen"
---

<objective>
Wave 2 (EVSDK-05): harden the Rust consumer's typed `AgentEvent` stream loop so it matches the stream variant-by-variant, stops on `SessionIdle` without hanging, carries the env-driven `permission_reply` branch (used live in W4), and emits the six-key structured JSON. The W0 skeleton already builds as a cargo example (auto-discovered from `crates/voss-sdk/examples/`); this plan makes the runtime behavior correct + robust.

This plan is PARALLEL with E4-03 (ts) and E4-04 (go) — it touches ONLY `crates/voss-sdk/examples/sdk_proof_consumer.rs`. Zero file overlap with the ts/go consumer dirs OR with `tests/eval/test_sdk.py` (the consolidated end-to-end schema tests live in plan 06).

RUST IN SCOPE (D-01, user-approved): the CONTEXT/RESEARCH confirmed `crates/voss-sdk` is the FULL V13.2 client SDK (not just a spawn helper). D-02's earlier "not in `sdk/`" deferral was a directory-location error; the user approved adding `sdk:rust` as the fourth surface. The crate has `VOSS_SERVE_FAKE_TURN` integration tests as the reference.

SCOPE GUARD (D-06, RESEARCH): the consumer uses the PUBLIC crate API only — `VossClient::new`/`create_session`/`post_message`/`permission_reply`/`cost` + `event_stream`. It MUST use `VossClient::new` (NOT `spawn_with`): the Python runner owns the server lifecycle. No per-runtime scoring. Keep the example self-contained: do NOT add new `[dependencies]` to Cargo.toml; if `serde_json`/`tokio` are dev-only and unavailable to examples, build the JSON line with `format!`/manual escaping rather than pulling a dependency (minimal change surface). Under FAKE_TURN there is NO `permission.updated` event (app.py:166-178; confirmed by the crate's own integration.rs:224 comment), so `saw_permission_gate` is false in stub mode — that is correct.

Purpose: Make the Rust external-consumer contract correct + robust (typed AgentEvent stream decode + env-driven reply + structured emission).
Output: hardened sdk_proof_consumer.rs example (verified by cargo build + grep gates; exercised end-to-end in plan 06).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E4-sdk-proof/E4-CONTEXT.md
@.planning/phases/E4-sdk-proof/E4-RESEARCH.md
@.planning/phases/E4-sdk-proof/E4-PATTERNS.md
@.planning/phases/E4-sdk-proof/E4-VALIDATION.md

<interfaces>
<!-- Rust public exports (crate voss_sdk; crates/voss-sdk/src/lib.rs pub use) -->
VossClient::new(base: String, token: String) -> Self              // NOT spawn_with (runner owns serve)
client.create_session(cwd: &str) -> Result<String, VossError>
client.post_message(sid: &str, text: &str, mode: &str) -> Result<(), VossError>
client.permission_reply(sid: &str, id: &str, choice: &str) -> Result<_, VossError>
client.cost(sid: &str) -> Result<CostInfo, VossError>
client.base_url() -> &str
event_stream(client, session_id) -> impl Stream<Item = Result<AgentEvent, VossError>>

<!-- AgentEvent variants (crates/voss-sdk/src/types/events.rs) — match on the variant: -->
//   AgentEvent::ServerConnected(_) | AgentEvent::PermissionUpdated(e) {e.id} | AgentEvent::FinalEvent(e) {e.text/.final}
//   | AgentEvent::SessionIdle(_) | ... — VERIFY exact variant + field names in types/events.rs before use
// futures_util::StreamExt provides .next() on the stream

<!-- env contract from _drive_sdk_client (plan 02): VOSS_BASE_URL, VOSS_TOKEN, VOSS_CWD, VOSS_PROMPT, VOSS_MODE -->
<!-- plan 07 forwards VOSS_PERMISSION_CHOICE (default "a") so the same consumer drives Allow + Deny -->
<!-- structured-result schema (last stdout line): {surface, session_id, final, saw_permission_gate, cost_usd, event_types_seen} -->
<!-- FAKE_TURN final text = "echo: <prompt>"; emits server.connected -> final -> session.idle, NO permission.updated -->
<!-- Run command (set by the runner): cargo run --manifest-path crates/voss-sdk/Cargo.toml --example sdk_proof_consumer --quiet -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Harden Rust consumer stream loop + structured emission</name>
  <files>crates/voss-sdk/examples/sdk_proof_consumer.rs</files>
  <read_first>
    - crates/voss-sdk/examples/sdk_proof_consumer.rs (the W0 skeleton — current VossClient::new + lifecycle; harden the stream loop here)
    - crates/voss-sdk/src/types/events.rs (the AgentEvent enum — EVERY variant + its struct fields; get the EXACT names: PermissionUpdated id field, the final-event variant name + its text field — do not guess)
    - crates/voss-sdk/src/client.rs (lines 29-170 — VossClient::new + create_session/post_message/permission_reply/cost signatures; CostInfo field names; base_url)
    - crates/voss-sdk/src/stream.rs (the `event_stream` function — its Item type Result<AgentEvent, VossError> and how the stream ends)
    - crates/voss-sdk/tests/integration.rs (lines 1-8 imports incl. futures_util::StreamExt; lines 136-154 event_stream collect; lines 247-279 permission roundtrip match; line 224 the FAKE_TURN-no-permission comment)
    - crates/voss-sdk/Cargo.toml (the [dependencies] + [dev-dependencies] — determine if serde_json/tokio/futures-util are available to examples; examples see [dependencies]+[dev-dependencies])
    - voss/harness/server/app.py (lines 166-178 — FAKE_TURN event sequence in stub mode)
    - .planning/phases/E4-sdk-proof/E4-PATTERNS.md (Rust consumer section lines 486-551 — full structure incl. VossClient::new + event_stream + JSON emission; the FAKE_TURN-no-permission note)
  </read_first>
  <action>
    Harden crates/voss-sdk/examples/sdk_proof_consumer.rs (built buildable in W0; now make the stream loop correct + robust):
      - Keep the `#[tokio::main] async fn main()` entry + the early eprintln + std::process::exit(2) when VOSS_BASE_URL is absent.
      - let choice = std::env::var("VOSS_PERMISSION_CHOICE").unwrap_or_else(|_| "a".into()) (so plan 07's Deny scenario drives "d" through this same example).
      - let client = VossClient::new(env VOSS_BASE_URL, env VOSS_TOKEN). let sid = client.create_session(&cwd).await? (or emit an error JSON + exit(1) on Err).
      - client.post_message(&sid, &prompt, &mode).await before consuming the stream.
      - let mut stream = event_stream(client.clone(), sid.clone()); use futures_util::StreamExt. Initialize final_text=String::new(), saw_gate=false, event_types: Vec<String>. while let Some(item) = stream.next().await: on Ok(event) match the AgentEvent variant — append a type-string literal per variant, on PermissionUpdated(e) set saw_gate=true and client.permission_reply(&sid, &e.id, &choice).await (ignore/log the result), on the final-event variant capture its text into final_text, on SessionIdle break; on Err(e) log + break. Use the EXACT variant + field names from types/events.rs (read them; do not guess). Ensure the loop ends on SessionIdle.
      - let cost = client.cost(&sid).await.map(|c| c.total field).unwrap_or(0.0) (read CostInfo's total field name).
      - Emit ONE JSON line to stdout: surface="sdk:rust", session_id=sid, final=final_text, saw_permission_gate=saw_gate, cost_usd=cost, event_types_seen=event_types. If serde_json is available to the example, use serde_json::json!{...}.to_string(); otherwise build the line with format! and manual string escaping of final_text (no new dependency). println! the line.
      - MUST use VossClient::new, never spawn_with. Do NOT add new [dependencies] to Cargo.toml; if a dep is missing for examples, fall back to format!-based JSON. Keep the file minimal/auditable.
  </action>
  <verify>
    <automated>.venv/bin/python -c "import subprocess,sys; r=subprocess.run(['cargo','build','--example','sdk_proof_consumer','--manifest-path','crates/voss-sdk/Cargo.toml','--quiet'],capture_output=True,text=True); print(r.stderr[-800:]); sys.exit(r.returncode)"</automated>
  </verify>
  <acceptance_criteria>
    - `cargo build --example sdk_proof_consumer --manifest-path crates/voss-sdk/Cargo.toml --quiet` exits 0 after hardening.
    - `grep -c "VossClient::new" crates/voss-sdk/examples/sdk_proof_consumer.rs` >= 1 and `grep -c "spawn_with" crates/voss-sdk/examples/sdk_proof_consumer.rs` == 0 (VossClient::new, not spawn_with).
    - The stream match + permission branch present: `grep -c "AgentEvent::" crates/voss-sdk/examples/sdk_proof_consumer.rs` >= 2 and `grep -c "permission_reply" crates/voss-sdk/examples/sdk_proof_consumer.rs` >= 1.
    - The reply choice is env-driven: `grep -c "VOSS_PERMISSION_CHOICE" crates/voss-sdk/examples/sdk_proof_consumer.rs` >= 1.
    - SessionIdle ends the loop: `grep -c "SessionIdle" crates/voss-sdk/examples/sdk_proof_consumer.rs` >= 1.
    - The six-key schema is emitted: `grep -c "event_types_seen" crates/voss-sdk/examples/sdk_proof_consumer.rs` >= 1 and `grep -c "saw_permission_gate" crates/voss-sdk/examples/sdk_proof_consumer.rs` >= 1.
    - No new crate dependency added: `git diff crates/voss-sdk/Cargo.toml` shows no added line under [dependencies] (examples reuse existing deps or format!-based JSON).
    - No per-runtime scoring: `grep -c "jsonl\|judge" crates/voss-sdk/examples/sdk_proof_consumer.rs` == 0.
  </acceptance_criteria>
  <done>Rust consumer matches the typed AgentEvent stream variant-by-variant, has the env-driven permission_reply branch, stops on SessionIdle without hang, and emits the six-key JSON; VossClient::new only; auto-discovered example with no Cargo.toml dependency change. End-to-end FAKE_TURN exercise is in plan 06.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Rust consumer -> voss-sdk crate public API | example is committed in-repo; built against the in-repo crate (no remote crate fetch beyond existing locked deps) |
| cargo run subprocess -> loopback serve | consumer uses VossClient::new against 127.0.0.1:{port} with a bearer token from env; the runner owns the server |
| consumer stdout JSON -> runner parse | last JSON-decodable line parsed under try/except by the runner; malformed -> "" , never a crash |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E4-15 | Tampering | Rust consumer calling spawn_with (spawns its own server) | mitigate | Consumer uses VossClient::new against the runner-spawned server; grep gate asserts 0 references to spawn_with |
| T-E4-16 | Integrity | cargo fetching crates from the network at build | mitigate | Example builds against the in-repo crate + its already-locked deps (Cargo.lock); no new [dependencies]; CARGO_NET_OFFLINE may be set by the runner env if needed |
| T-E4-17 | Denial | Rust consumer hanging on the AgentEvent stream | mitigate | Loop breaks on SessionIdle; the runner runs the consumer with a subprocess timeout and kills serve in finally |
| T-E4-SC | Tampering | npm/pip/cargo installs | accept | E4 introduces zero new packages; the Rust example adds no new [dependencies] (reuses existing or format!-based JSON); no install task |
</threat_model>

<verification>
- `cargo build --example sdk_proof_consumer` clean; VossClient::new only, no spawn_with; no Cargo.toml dependency change
- typed AgentEvent stream decoded (variant match); env-driven permission_reply branch; six-key JSON
- no per-runtime scoring in the consumer (single E1 substrate)
- end-to-end FAKE_TURN schema/decode assertion is consolidated in plan 06 (which owns tests/eval/test_sdk.py)
</verification>

<success_criteria>
- EVSDK-05: sdk:rust consumer drives a turn via the public crate API + typed AgentEvent stream, has the env-driven permission_reply branch, emits the six-key structured JSON
- Rust-VossClient::new-not-spawn_with encoded (grep-gated); public-API-only; permission gate exercised live (plan 07)
- Example auto-discovered with no Cargo.toml dependency change; parallel-safe (touches only the rust example, no overlap with ts/go plans or test_sdk.py)
</success_criteria>

<output>
Create `.planning/phases/E4-sdk-proof/E4-05-SUMMARY.md` when done
</output>
