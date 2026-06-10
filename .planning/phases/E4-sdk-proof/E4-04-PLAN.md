---
phase: E4-sdk-proof
plan: 04
type: execute
wave: 3
depends_on: [E4-02]
files_modified:
  - tests/eval/sdk/consumers/go/main.go
autonomous: true
requirements: [EVSDK-04]
must_haves:
  truths:
    - "The Go consumer decodes the typed event channel: it type-switches over <-chan TypedEvent and collects type strings (server.connected/final/session.idle/permission.updated)"
    - "The Go consumer reaches session.idle and stops ranging the channel (no hang); under FAKE_TURN it reports saw_permission_gate=false (permission gate is live-only)"
    - "The Go consumer has the PermissionUpdated->PermissionReply branch (choice from VOSS_PERMISSION_CHOICE, default a) ready for the live Allow/Deny scenarios"
    - "The Go consumer uses AttachClient (never Spawn) — it connects to the runner-spawned server via VOSS_BASE_URL/VOSS_TOKEN; the Go interpreterPath CWD pitfall is avoided"
    - "The Go consumer emits one valid JSON line (via json.Marshal) with all six keys {surface,session_id,final,saw_permission_gate,cost_usd,event_types_seen}"
    - "The Go consumer uses only the published client API and adds no per-runtime scoring"
  artifacts:
    - path: "tests/eval/sdk/consumers/go/main.go"
      provides: "Hardened Go consumer: AttachClient + Events type-switch + env-driven PermissionReply, six-key JSON emission"
      contains: "AttachClient"
  key_links:
    - from: "tests/eval/sdk/consumers/go/main.go"
      to: "(c *Client) Events <-chan TypedEvent"
      via: "for ev := range ch { switch e := ev.(type) ... } type-switch; PermissionReply on PermissionUpdated"
      pattern: "ev.\\(type\\)|range ch"
    - from: "tests/eval/sdk/consumers/go/main.go"
      to: "stdout structured JSON"
      via: "json.Marshal of the six-key struct; runner extracts final + scores via E1"
      pattern: "event_types_seen"
---

<objective>
Wave 2 (EVSDK-04): harden the Go consumer's typed-event channel loop so it consumes `<-chan TypedEvent` via a correct type-switch, terminates on SessionIdle without hanging, carries the env-driven PermissionReply branch (used live in W4), and emits the six-key structured JSON via the marshaller. The W0 skeleton already builds with the `replace` directive resolving the local `sdk/go` module; this plan makes the runtime behavior correct + robust.

This plan is PARALLEL with E4-03 (ts) and E4-05 (rust) — it touches ONLY `tests/eval/sdk/consumers/go/main.go`. Zero file overlap with the ts/rust consumer dirs OR with `tests/eval/test_sdk.py` (the consolidated end-to-end schema tests live in plan 06).

SCOPE GUARD (D-06, RESEARCH): the consumer uses the PUBLIC client API only — `AttachClient`/`CreateSession`/`Events`/`PostMessage`/`PermissionReply`/`Cost`. It MUST use `AttachClient` (NOT `Spawn`): `Spawn` calls `interpreterPath()` which resolves `.venv/bin/python` relative to CWD, and from `tests/eval/sdk/consumers/go/` that resolves wrong (RESEARCH Pitfall 2); the Python runner pre-spawns the server and passes `VOSS_BASE_URL`/`VOSS_TOKEN` (+ `VOSS_PYTHON`). No per-runtime scoring. Under FAKE_TURN there is NO permission.updated event (app.py:166-178), so `saw_permission_gate` is false in stub mode — that is correct.

Purpose: Make the Go external-consumer contract correct + robust (typed channel decode + env-driven reply + structured emission).
Output: hardened main.go (verified by go build + grep gates; exercised end-to-end in plan 06).
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
<!-- Go public exports (package voss; module github.com/vosslang/voss/sdk/go) -->
AttachClient(baseURL, token string) *Client                       // NOT Spawn (interpreterPath CWD pitfall)
(c *Client) CreateSession(ctx, cwd string) (string, error)
(c *Client) PostMessage(ctx, id, text, mode string) error
(c *Client) Events(ctx, sessionID string) (<-chan TypedEvent, error)
(c *Client) PermissionReply(ctx, sessionID, id, choice string) (bool, error)
(c *Client) Cost(ctx, id string) (CostInfo, error)
(c *Client) Close() error                                          // no-op for AttachClient; safe to defer

<!-- TypedEvent interface (sdk/go/events.go) — concrete structs, switch on the type: -->
type TypedEvent interface{ eventType() string }
// concrete: ServerConnected, SessionIdle, PermissionUpdated, FinalEvent, ToolEvent, ThinkingEvent, ... (read events.go for fields)
// PermissionUpdated has an ID field; FinalEvent has a Text field — VERIFY exact field names in events.go before use
// eventType() is UNEXPORTED — to record type strings from package main, append a literal per switch case (or use a public accessor if events.go has one)

<!-- env contract from _drive_sdk_client (plan 02): VOSS_BASE_URL, VOSS_TOKEN, VOSS_CWD, VOSS_PROMPT, VOSS_MODE, VOSS_PYTHON -->
<!-- plan 07 forwards VOSS_PERMISSION_CHOICE (default "a") so the same consumer drives Allow + Deny -->
<!-- structured-result schema (last stdout line): {surface, session_id, final, saw_permission_gate, cost_usd, event_types_seen} -->
<!-- FAKE_TURN final text = "echo: <prompt>"; emits server.connected -> final -> session.idle, NO permission.updated -->
<!-- Run command (set by the runner): `go run .` with cwd=tests/eval/sdk/consumers/go (so go.mod is found) -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Harden Go consumer typed-channel loop + structured emission</name>
  <files>tests/eval/sdk/consumers/go/main.go</files>
  <read_first>
    - tests/eval/sdk/consumers/go/main.go (the W0 skeleton — current AttachClient + lifecycle; harden the channel loop here)
    - sdk/go/events.go (FULL — the TypedEvent interface + EVERY concrete struct and its fields; get the EXACT names: PermissionUpdated.ID, FinalEvent.Text, SessionIdle — do not guess; note eventType() is unexported)
    - sdk/go/sse.go (lines 20-47 — `Events` returns `<-chan TypedEvent`; how ctx cancel closes the channel)
    - sdk/go/client.go (lines 29-35 `AttachClient`; the Close() no-op behavior for attach)
    - sdk/go/rest.go (lines 54-141 — CreateSession/PostMessage/PermissionReply/Cost signatures; CostInfo field names)
    - sdk/go/client_test.go (lines 119-145 `TestAttachRoundTrip` — the canonical AttachClient->CreateSession->Events->PostMessage->type-switch loop; lines 78-91 no-orphan Close)
    - voss/harness/server/app.py (lines 166-178 — FAKE_TURN event sequence in stub mode)
    - .planning/phases/E4-sdk-proof/E4-PATTERNS.md (Go consumer section lines 411-483 — full structure incl. the AttachClient note + JSON emission; Pitfall 2 guard)
  </read_first>
  <action>
    Harden tests/eval/sdk/consumers/go/main.go (built buildable in W0; now make the channel loop correct + robust):
      - Keep the env read + the early `os.Exit(2)` (with an error line) when VOSS_BASE_URL == "".
      - Read `choice := os.Getenv("VOSS_PERMISSION_CHOICE"); if choice == "" { choice = "a" }` (so plan 07's Deny scenario drives "d" through this same file).
      - Build the client with AttachClient(os.Getenv("VOSS_BASE_URL"), os.Getenv("VOSS_TOKEN")) and defer client.Close() (no-op for attach, safe).
      - Create a ctx with a 120s timeout (context.WithTimeout) so a stuck stream cannot hang the process; defer cancel.
      - CreateSession(ctx, os.Getenv("VOSS_CWD")); on err, emit an error JSON line + os.Exit(1).
      - Open the stream BEFORE posting: ch, err := client.Events(ctx, id); then client.PostMessage(ctx, id, prompt, mode).
      - Initialize finalText, sawGate=false, eventTypes []string. Range the channel with a type-switch over the concrete structs. For each event append a type-string literal corresponding to the case (because eventType() is unexported), set sawGate + call PermissionReply(ctx, id, e.ID, choice) on PermissionUpdated, capture e.Text on FinalEvent, and cancel+break on SessionIdle. Use the EXACT concrete struct names + field names from events.go (read them; do not guess). Ensure the loop terminates on SessionIdle (cancel the ctx so the channel closes, then break).
      - Cost(ctx, id) for cost_usd (read the CostInfo total field name).
      - Emit the JSON via encoding/json: a struct with json tags surface/session_id/final/saw_permission_gate/cost_usd/event_types_seen, surface hardcoded "sdk:go", json.Marshal + newline to stdout (do NOT hand-format the JSON string — use the marshaller for correctness).
      - MUST use AttachClient, never Spawn. Keep the file minimal and auditable.
  </action>
  <verify>
    <automated>.venv/bin/python -c "import subprocess,sys; r=subprocess.run(['go','build','./...'],cwd='tests/eval/sdk/consumers/go',capture_output=True,text=True); print(r.stderr); sys.exit(r.returncode)"</automated>
  </verify>
  <acceptance_criteria>
    - `go build ./...` in tests/eval/sdk/consumers/go exits 0 after hardening (vet-clean preferred).
    - `grep -c "AttachClient" tests/eval/sdk/consumers/go/main.go` >= 1 and `grep -c "Spawn(" tests/eval/sdk/consumers/go/main.go` == 0 (AttachClient, not Spawn — interpreterPath pitfall).
    - The channel type-switch + permission branch present: `grep -c "ev.(type)\|range ch" tests/eval/sdk/consumers/go/main.go` >= 1 and `grep -c "PermissionReply" tests/eval/sdk/consumers/go/main.go` >= 1.
    - The reply choice is env-driven: `grep -c "VOSS_PERMISSION_CHOICE" tests/eval/sdk/consumers/go/main.go` >= 1.
    - SessionIdle terminates the loop: `grep -c "SessionIdle" tests/eval/sdk/consumers/go/main.go` >= 1.
    - The six-key schema is emitted via json.Marshal: `grep -c "event_types_seen" tests/eval/sdk/consumers/go/main.go` >= 1 and `grep -c "json.Marshal\|encoding/json" tests/eval/sdk/consumers/go/main.go` >= 1.
    - No per-runtime scoring: `grep -c "jsonl\|judge" tests/eval/sdk/consumers/go/main.go` == 0.
  </acceptance_criteria>
  <done>Go consumer decodes the typed event channel via a type-switch, has the env-driven PermissionReply branch, terminates on SessionIdle without hang, and emits the six-key JSON via the marshaller; AttachClient only; public API only. End-to-end FAKE_TURN exercise is in plan 06.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Go consumer -> sdk/go public API | consumer is committed in-repo; built from the local module via the go.mod replace directive (no remote module fetch) |
| go run subprocess -> loopback serve | consumer uses AttachClient against 127.0.0.1:{port} with a bearer token from env; the runner owns the server |
| consumer stdout JSON -> runner parse | last-line JSON parsed under try/except by the runner; malformed -> "" , never a crash |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E4-12 | Tampering | Go consumer calling Spawn (spawns its own server, wrong python path) | mitigate | Consumer uses AttachClient against the runner-spawned server; grep gate asserts 0 references to Spawn(; runner also sets VOSS_PYTHON |
| T-E4-13 | Integrity | go run fetching modules from the network at build | mitigate | go.mod replace directive points to the local ../../../../sdk/go; module cache populated in W0 (go mod download/tidy); no remote pull |
| T-E4-14 | Denial | Go consumer hanging on the event channel | mitigate | context.WithTimeout(120s) + cancel-on-SessionIdle; the runner runs the consumer with a subprocess timeout and kills serve in finally |
| T-E4-SC | Tampering | npm/pip/cargo installs | accept | E4 introduces zero new packages; the Go consumer depends only on the in-repo sdk/go via replace; no install task |
</threat_model>

<verification>
- `go build ./...` in the consumer dir clean; AttachClient only, no Spawn
- typed channel decoded (type-switch over TypedEvent); env-driven PermissionReply branch; six-key JSON via json.Marshal
- no per-runtime scoring in the consumer (single E1 substrate)
- end-to-end FAKE_TURN schema/decode assertion is consolidated in plan 06 (which owns tests/eval/test_sdk.py)
</verification>

<success_criteria>
- EVSDK-04: sdk:go consumer drives a turn via the public client API + typed event channel, has the env-driven PermissionReply branch, emits the six-key structured JSON
- Go-AttachClient-not-Spawn pitfall encoded (grep-gated); public-API-only; permission gate exercised live (plan 07)
- Parallel-safe: touches only the go consumer file (no overlap with ts/rust plans or test_sdk.py)
</success_criteria>

<output>
Create `.planning/phases/E4-sdk-proof/E4-04-SUMMARY.md` when done
</output>
