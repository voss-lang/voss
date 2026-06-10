---
phase: E4-sdk-proof
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/eval/test_sdk.py
  - tests/eval/sdk/consumers/ts/consumer.js
  - tests/eval/sdk/consumers/ts/package.json
  - tests/eval/sdk/consumers/go/main.go
  - tests/eval/sdk/consumers/go/go.mod
  - crates/voss-sdk/examples/sdk_proof_consumer.rs
autonomous: true
requirements: [EVSDK-01, EVSDK-02, EVSDK-03, EVSDK-04, EVSDK-05]
must_haves:
  truths:
    - "A RED test module tests/eval/test_sdk.py exists with xfail-marked stubs for each minted EVSDK requirement before any driver code is written (Nyquist seed)"
    - "The TS consumer subprogram BUILDS: `node tests/eval/sdk/consumers/ts/consumer.js` resolves the @vosslang/sdk import without ERR_MODULE_NOT_FOUND (exits on missing VOSS_BASE_URL, proving import + parse succeeded)"
    - "The Go consumer subprogram BUILDS: `go build ./...` in tests/eval/sdk/consumers/go succeeds with the replace directive resolving github.com/vosslang/voss/sdk/go to the local module"
    - "The Rust consumer subprogram BUILDS: `cargo build --example sdk_proof_consumer --manifest-path crates/voss-sdk/Cargo.toml` succeeds (example auto-discovered, no Cargo.toml [[example]] edit needed)"
    - "The TS consumer imports ONLY from @vosslang/sdk (the index/dist surface), never from @vosslang/sdk/node — VossLauncher is not referenced (timeout pitfall)"
    - "The Go consumer uses AttachClient, never Spawn (interpreterPath CWD pitfall)"
  artifacts:
    - path: "tests/eval/test_sdk.py"
      provides: "RED Nyquist scaffold — xfail stubs per EVSDK requirement; build-verification tests for the three consumer subprograms"
      contains: "xfail"
    - path: "tests/eval/sdk/consumers/ts/consumer.js"
      provides: "TS consumer subprogram (public-API-only; createVossClient/subscribeToEvents/replyPermission)"
      contains: "createVossClient"
    - path: "tests/eval/sdk/consumers/ts/package.json"
      provides: "ESM module type + file: dep on the prebuilt @vosslang/sdk dist"
      contains: "@vosslang/sdk"
    - path: "tests/eval/sdk/consumers/go/main.go"
      provides: "Go consumer subprogram (AttachClient + Events type-switch + PermissionReply)"
      contains: "AttachClient"
    - path: "tests/eval/sdk/consumers/go/go.mod"
      provides: "module + replace directive to local sdk/go"
      contains: "replace github.com/vosslang/voss/sdk/go"
    - path: "crates/voss-sdk/examples/sdk_proof_consumer.rs"
      provides: "Rust consumer subprogram (VossClient::new + event_stream)"
      contains: "VossClient::new"
  key_links:
    - from: "tests/eval/sdk/consumers/ts/consumer.js"
      to: "@vosslang/sdk"
      via: "ESM import of createVossClient/subscribeToEvents/replyPermission (NOT @vosslang/sdk/node)"
      pattern: "from \"@vosslang/sdk\""
    - from: "tests/eval/sdk/consumers/go/go.mod"
      to: "sdk/go"
      via: "replace directive → ../../../../sdk/go"
      pattern: "replace github\\.com/vosslang/voss/sdk/go"
    - from: "crates/voss-sdk/examples/sdk_proof_consumer.rs"
      to: "voss_sdk"
      via: "use voss_sdk::{event_stream, VossClient}"
      pattern: "voss_sdk::"
---

<objective>
Wave 0: lay the RED Nyquist scaffold and prove the three client consumer subprograms BUILD before any driver logic exists. This resolves the three RESEARCH open questions up front (TS `file:` dep vs relative dist import; Go `go.mod` `replace` directive; Rust `examples/` auto-discovery) so the W2 consumer-logic plans are not blocked on toolchain wiring.

The consumer subprograms are committed, minimal, and use ONLY the published SDK client API — they prove the external-consumer contract. This plan writes the consumer SKELETONS (full structure, correct imports, AttachClient/createVossClient/VossClient::new, the SSE event loop, the structured-JSON stdout emission) and verifies each one COMPILES/RESOLVES with zero new package installs. The consumers are functionally complete enough to build; W3 (suite scenarios) exercises them against a live/stub server through the Python driver added in W1.

DEPENDENCY NOTE (Option a — already satisfied): E3-01 and E3-02 are EXECUTED on this checkout. `voss/eval/suite.py:55` already carries the `surface` Literal and `voss/eval/runner.py` has the dispatch chain + `_live_env` + the additive `"surface"` JSONL row. E4 extends the E3-01-owned Literal additively (plan 02) — E3-01 solely owns the `suite.py:55` literal, so there is no merge conflict. This plan touches NO Python runner/suite code; it only creates test scaffolding + consumer subprograms.

## Minted Requirements (EVSDK-01..08 — no SPEC; seeded from CONTEXT D-01..D-08)

| ID | Decision | Behavior |
|----|----------|----------|
| EVSDK-01 | D-05 | `surface` dispatch: Literal accepts `sdk:python\|ts\|go\|rust`; runner routes via `_drive_sdk_python` / `_drive_sdk_client` |
| EVSDK-02 | D-04 | `sdk:python` in-process driver calls `run_turn` via public `voss.harness`/`voss_runtime` symbols; returns `TurnResult.final` |
| EVSDK-03 | D-06 | `sdk:ts` consumer subprogram: `createVossClient`/`subscribeToEvents`/`replyPermission` against pre-spawned serve; emits structured JSON |
| EVSDK-04 | D-06 | `sdk:go` consumer subprogram: `AttachClient`/`Events`/`PermissionReply` against pre-spawned serve; emits structured JSON |
| EVSDK-05 | D-01/D-06 | `sdk:rust` consumer subprogram: `VossClient::new`/`event_stream`/`permission_reply` against pre-spawned serve; emits structured JSON |
| EVSDK-06 | D-05/D-07 | sdk task.tomls in `tests/eval/sdk/<NN>/`; `voss eval --suite sdk` loads + hybrid-scores; single E1 scoring substrate; one simple shape-agnostic fixture |
| EVSDK-07 | D-03 | Permission-gate live scenario per client: Allow round-trip reaches final; Deny degrades without hang |
| EVSDK-08 | D-08 | One documented live codex run: ≥1 scenario/surface, ≥80% gate_pass, 0 capped, permission scenario among passers; human checkpoint |

Purpose: De-risk the three build/resolution open questions and seed Nyquist coverage before driver code.
Output: RED test module + three buildable consumer subprograms (ts/go/rust).
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
<!-- TS public surface (sdk/typescript/src/index.ts re-exports; import from @vosslang/sdk) -->
createVossClient(baseUrl: string, token: string) -> { createSession, postMessage, getCost, getSession, deleteSession, abort, listSessions }
subscribeToEvents(baseUrl, sessionId, token, signal?) -> AsyncIterable<AgentEvent>   // AgentEvent.type === "permission.updated" | "final" | "session.idle" | ...
replyPermission(client, sessionId, { id, choice })   // choice: "a"|"A"|"d"|"y"|"n"
// DO NOT import VossLauncher from @vosslang/sdk/node — HANDSHAKE_TIMEOUT_MS=10_000 (dist/node.js:644); cold litellm is 15-45s.

<!-- Go public surface (package voss; module github.com/vosslang/voss/sdk/go) -->
AttachClient(baseURL, token string) *Client          // NOT Spawn — Spawn's interpreterPath() resolves python relative to CWD
(c *Client) CreateSession(ctx, cwd) (string, error)
(c *Client) PostMessage(ctx, id, text, mode) error
(c *Client) Events(ctx, sessionID) (<-chan TypedEvent, error)   // TypedEvent interface; concrete: PermissionUpdated, FinalEvent, SessionIdle (sdk/go/events.go)
(c *Client) PermissionReply(ctx, sessionID, id, choice) (bool, error)
(c *Client) Cost(ctx, id) (CostInfo, error)

<!-- Rust public surface (crate voss_sdk; crates/voss-sdk/src/lib.rs pub use) -->
VossClient::new(base: String, token: String) -> Self          // NOT spawn_with — runner owns serve lifecycle
client.create_session(cwd: &str) -> Result<String, VossError>
client.post_message(sid, text, mode) -> Result<(), VossError>
client.permission_reply(sid, id, choice) -> Result<_, VossError>
client.cost(sid) -> Result<CostInfo, VossError>
event_stream(client, session_id) -> impl Stream<Item = Result<AgentEvent, VossError>>   // AgentEvent::ServerConnected/SessionIdle/PermissionUpdated/FinalEvent
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: RED Nyquist scaffold tests/eval/test_sdk.py</name>
  <files>tests/eval/test_sdk.py</files>
  <read_first>
    - tests/eval/test_surface_drivers.py (FULL — the analog: how E3 stub-mode driver tests invoke `_drive_*` directly with a TaskSpec and assert the `(final, crash_reason, capped)` tuple; the `stub_live_env` monkeypatch fixture)
    - tests/eval/conftest.py (FULL — the `_set_voss_dev` autouse fixture + `collect_ignore_glob`; the sdk consumer dirs must NOT match golden/matrix globs)
    - tests/eval/test_voss_eval_stub.py (lines 11-35 REQUIRED_FIELDS sentinel — E4 adds NO new JSONL fields; sentinel stays as-is; lines 42-53 `_run_eval` subprocess helper)
    - .planning/phases/E4-sdk-proof/E4-PATTERNS.md (test_sdk_drivers.py section lines 555-611 — the runner-invocation + stub-mode assertion pattern)
    - .planning/phases/E4-sdk-proof/E4-VALIDATION.md (Phase Requirements → Test Map lines 814-828 — exact test names per EVSDK requirement)
  </read_first>
  <action>
    Create tests/eval/test_sdk.py as the RED Nyquist scaffold. It MUST import cleanly and run, with every not-yet-built behavior marked `@pytest.mark.xfail(reason="...", strict=False)` so the module is green-but-pending (the W1/W2/W3 plans flip these to real assertions, removing xfail).

    Module header docstring states: "RED scaffold for E4 SDK proof. xfail stubs map 1:1 to EVSDK-01..08; W1 adds drivers, W2 adds consumers, W3 adds scenarios. Permission-gate behavior is live-only (FAKE_TURN emits no permission.updated — app.py:166-178), so EVSDK-07 stays xfail/skip in automated runs." Use `grep -v '^#'`-safe markers — do not rely on comment-counting grep gates.

    Add xfail stub test functions (one per requirement; bodies may `assert False` or reference a not-yet-existing symbol inside the xfail):
      test_surface_accepts_sdk_python_ts_go_rust (EVSDK-01) — will import `from voss.eval.suite import TaskSpec` and assert `TaskSpec(prompt="x", mode="plan", rubric="r", surface="sdk:python").surface == "sdk:python"` for each of the four values; xfail now because the Literal does not yet include sdk:* (W1 plan 02 removes xfail).
      test_drive_sdk_python_stub (EVSDK-02) — xfail: `_drive_sdk_python` not yet defined.
      test_drive_sdk_client_ts_stub (EVSDK-03) — xfail.
      test_drive_sdk_client_go_stub (EVSDK-04) — xfail.
      test_drive_sdk_client_rust_stub (EVSDK-05) — xfail.
      test_sdk_suite_loads (EVSDK-06) — xfail: `tests/eval/sdk/<NN>/task.toml` scenarios not yet created (W3 plan 06).
      test_permission_gate_live (EVSDK-07) — `@pytest.mark.skip(reason="live-only: FAKE_TURN emits no permission.updated; run via --suite sdk --auth codex")`. NOT xfail — it is permanently skipped in automated runs (operator checkpoint covers it).

    Add the THREE build-verification tests as REAL (non-xfail) tests guarded by toolchain availability (these are the de-risking gates for the open questions; they must pass NOW because Task 2 builds the consumers):
      test_ts_consumer_resolves — `@pytest.mark.skipif(not shutil.which("node"), ...)`: run `node tests/eval/sdk/consumers/ts/consumer.js` with NO env; assert the process exits with a clear "VOSS_BASE_URL" error (proving the @vosslang/sdk import resolved + parsed — NOT ERR_MODULE_NOT_FOUND / ERR_PACKAGE_PATH_NOT_EXPORTED). Assert "ERR_MODULE_NOT_FOUND" not in stderr and "Cannot find" not in stderr.
      test_go_consumer_builds — `@pytest.mark.skipif(not shutil.which("go"), ...)`: run `go build ./...` with cwd=tests/eval/sdk/consumers/go; assert returncode == 0.
      test_rust_consumer_builds — `@pytest.mark.skipif(not shutil.which("cargo"), ...)`: run `cargo build --example sdk_proof_consumer --manifest-path crates/voss-sdk/Cargo.toml --quiet`; assert returncode == 0.

    Use `subprocess.run(..., capture_output=True, text=True)` and absolute repo-root-relative paths via a `_repo_root()` helper copied from test_voss_eval_stub.py. These three build tests are SLOW (go/cargo compile) — mark them with `@pytest.mark.slow` if that marker exists in pyproject; otherwise leave unmarked (they are the load-bearing de-risk).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_sdk.py -q --no-header -k "not builds and not resolves" 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `tests/eval/test_sdk.py` imports cleanly: `.venv/bin/python -c "import ast; ast.parse(open('tests/eval/test_sdk.py').read())"` exits 0.
    - The xfail-only subset runs green (xfail counts as pass): `.venv/bin/python -m pytest tests/eval/test_sdk.py -k "not builds and not resolves" -q` reports 0 failed (xfailed/skipped are acceptable).
    - `grep -c "xfail" tests/eval/test_sdk.py` >= 6 (one per EVSDK-01..06) and `grep -c "skip" tests/eval/test_sdk.py` >= 1 (EVSDK-07 live-only).
    - The three build tests exist by name: `grep -E "def test_ts_consumer_resolves|def test_go_consumer_builds|def test_rust_consumer_builds" tests/eval/test_sdk.py` returns 3 lines.
    - No regression in the rest of the eval suite import surface: `.venv/bin/python -c "import voss.eval.runner, voss.eval.suite"` exits 0.
  </acceptance_criteria>
  <done>RED Nyquist scaffold exists; EVSDK-01..06 are xfail stubs, EVSDK-07 is live-only-skip, and three real build-verification tests are wired (they go green once Task 2 builds the consumers).</done>
</task>

<task type="auto">
  <name>Task 2: Three buildable consumer subprograms (ts / go / rust)</name>
  <files>tests/eval/sdk/consumers/ts/consumer.js, tests/eval/sdk/consumers/ts/package.json, tests/eval/sdk/consumers/go/main.go, tests/eval/sdk/consumers/go/go.mod, crates/voss-sdk/examples/sdk_proof_consumer.rs</files>
  <read_first>
    - sdk/typescript/src/client/rest.ts (lines 41-133 — `createVossClient` return shape + `VossClient` type), src/client/sse.ts (lines 12-67 — `subscribeToEvents` async iterator), src/client/permission.ts (lines 11-30 — `replyPermission` signature + choice values)
    - sdk/typescript/package.json (the `@vosslang/sdk` name + `"type":"module"` + `exports` map — confirms what `file:` dep resolves to)
    - sdk/go/client_test.go (lines 119-145 `TestAttachRoundTrip` — the AttachClient → CreateSession → Events → PostMessage → type-switch lifecycle; the no-orphan Close at lines 78-91), sdk/go/events.go (TypedEvent interface + concrete structs PermissionUpdated/FinalEvent/SessionIdle and their fields), sdk/go/sse.go (lines 20-47 `Events` channel), sdk/go/client.go (lines 29-35 `AttachClient`)
    - sdk/go/go.mod (module path `github.com/vosslang/voss/sdk/go`, go 1.24.3 — the consumer go.mod mirrors the go directive)
    - crates/voss-sdk/tests/integration.rs (lines 1-8 imports; lines 136-154 `event_stream` collect pattern; lines 247-279 permission roundtrip type-match; line 70 `VossClient::new` direct-construct), crates/voss-sdk/src/lib.rs (pub use exports), crates/voss-sdk/src/client.rs (lines 29-170 method signatures), crates/voss-sdk/src/types/events.rs (AgentEvent variants)
    - voss/harness/server/app.py (lines 166-178 — FAKE_TURN emits `echo: {text}` final, NO permission.updated; hermetic consumers must tolerate `saw_permission_gate: false`)
    - .planning/phases/E4-sdk-proof/E4-PATTERNS.md (consumer sections: ts lines 313-407, go lines 411-483, rust lines 486-551 — full structure to copy, including the structured-result JSON schema)
    - .planning/phases/E4-sdk-proof/E4-RESEARCH.md (Pitfall 1 TS timeout lines 355-360, Pitfall 4 go.mod lines 376-381, Pitfall 5 TS package.json lines 382-387; Open Questions lines 750-763)
  </read_first>
  <action>
    Create three minimal, committed, public-API-only consumer subprograms. Each reads server coordinates from env (VOSS_BASE_URL, VOSS_TOKEN, VOSS_CWD, VOSS_PROMPT, VOSS_MODE — set by the W1 `_drive_sdk_client` driver), drives one turn, and emits ONE JSON line to stdout with the schema: {surface, session_id, final, saw_permission_gate, cost_usd, event_types_seen}. NONE of them spawn or score — the Python runner owns serve lifecycle + scoring (single E1 substrate).

    TS consumer (tests/eval/sdk/consumers/ts/):
      - package.json: `{"type":"module","dependencies":{"@vosslang/sdk":"file:../../../../../sdk/typescript"}}`. Count the path segments from `tests/eval/sdk/consumers/ts/` to repo root (5 levels: ts→consumers→sdk→eval→tests→ROOT) then to `sdk/typescript` — verify the relative depth by resolving it; if `file:` resolution fails at build time, fall back to a direct relative import `from "../../../../../sdk/typescript/dist/index.js"` in consumer.js and drop the dep (RESEARCH Open Q3 / Assumption A1). Whichever resolves, the import statement MUST reference @vosslang/sdk public exports only.
      - consumer.js (ESM): import { createVossClient, subscribeToEvents, replyPermission } from "@vosslang/sdk". Read env; if VOSS_BASE_URL missing, `console.error("VOSS_BASE_URL required"); process.exit(2)` (this is the build-resolution probe Task 1 asserts). Otherwise: createVossClient(baseUrl, token) → createSession(cwd) → postMessage(sessionId, prompt, mode) → for-await subscribeToEvents(baseUrl, sessionId, token, ac.signal): push event.type to event_types_seen; on "permission.updated" set saw_permission_gate=true and `await replyPermission(client, sessionId, {id: event.id, choice: "a"})`; on "final" capture event.text; on "session.idle" abort + break. Then getCost (catch → {total_usd:0}); write the JSON line. MUST NOT import from "@vosslang/sdk/node" or reference VossLauncher (timeout pitfall).

    Go consumer (tests/eval/sdk/consumers/go/):
      - go.mod: `module sdk-go-consumer` / `go 1.24` / `require github.com/vosslang/voss/sdk/go v0.0.0` / `replace github.com/vosslang/voss/sdk/go => ../../../../sdk/go`. Verify the replace target depth resolves (go→consumers→sdk→eval→tests is 4 levels up to repo root, then `sdk/go`; the path is `../../../../sdk/go`). Run `go mod tidy` if the SDK's transitive deps need resolution (Assumption A5 — module cache may need `go mod download`); the consumer must `go build ./...` clean offline.
      - main.go (package main): AttachClient(os.Getenv("VOSS_BASE_URL"), os.Getenv("VOSS_TOKEN")). If VOSS_BASE_URL == "", print error JSON and os.Exit(2). Else: CreateSession(ctx, VOSS_CWD) → Events(ctx, id) channel → PostMessage(ctx, id, prompt, mode) → `for ev := range ch { switch e := ev.(type) { case PermissionUpdated: sawGate=true; PermissionReply(ctx, id, e.ID, "a"); case FinalEvent: finalText=e.Text; case SessionIdle: goto done } }`. (Use the EXACT concrete struct names + field names from sdk/go/events.go — read them; do not guess.) Cost(ctx, id) for cost_usd. Emit the JSON line via json.Marshal of a struct with the six fields. Use AttachClient, never Spawn.

    Rust consumer (crates/voss-sdk/examples/sdk_proof_consumer.rs):
      - This is a cargo example (auto-discovered from examples/ — NO Cargo.toml [[example]] entry needed; verify `cargo build --example sdk_proof_consumer` discovers it). Confirm the crate's existing dev-dependencies (tokio, futures-util, serde_json) are available to examples; if serde_json is only a dev-dependency it is NOT available to examples — examples use the [dependencies] + [dev-dependencies] set, so check Cargo.toml and, if serde_json/tokio are dev-only, either add them under [dev-dependencies] (examples see dev-deps) or build the JSON string manually with format!. Prefer manual format!-based JSON if it avoids a Cargo.toml dependency change (keep the change surface minimal).
      - main: `#[tokio::main] async fn main()`. Read env; if VOSS_BASE_URL absent, eprintln + std::process::exit(2). Else: VossClient::new(base, token) → create_session(cwd) → post_message(sid, prompt, mode) → consume event_stream(client.clone(), sid): collect event variant names into event_types_seen; on AgentEvent::PermissionUpdated(e) set saw_gate + `client.permission_reply(&sid, &e.id, "a").await`; on AgentEvent::FinalEvent(e) capture text; break on AgentEvent::SessionIdle. cost(sid) for cost_usd. Print the JSON line. Use VossClient::new, never spawn_with. (Use the EXACT AgentEvent variant + field names from src/types/events.rs — read them.)

    All three: the structured-result `surface` field is hardcoded to the consumer's own surface string ("sdk:ts"/"sdk:go"/"sdk:rust"). Keep each file under ~80 lines — minimal + auditable (D-06 specifics).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/eval/test_sdk.py -q -k "test_ts_consumer_resolves or test_go_consumer_builds or test_rust_consumer_builds" 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - TS resolves: `node tests/eval/sdk/consumers/ts/consumer.js` (no env) exits non-zero with stderr mentioning VOSS_BASE_URL and NOT containing "ERR_MODULE_NOT_FOUND" / "ERR_PACKAGE_PATH_NOT_EXPORTED" / "Cannot find module" (the @vosslang/sdk import resolved).
    - `grep -c "VossLauncher" tests/eval/sdk/consumers/ts/consumer.js` == 0 and `grep -c "@vosslang/sdk/node" tests/eval/sdk/consumers/ts/consumer.js` == 0 (timeout pitfall encoded).
    - Go builds: `cd tests/eval/sdk/consumers/go && go build ./...` exits 0; `grep -c "AttachClient" tests/eval/sdk/consumers/go/main.go` >= 1 and `grep -c "\.Spawn\|Spawn(" tests/eval/sdk/consumers/go/main.go` == 0 (uses AttachClient, not Spawn).
    - go.mod has the replace: `grep -c "replace github.com/vosslang/voss/sdk/go" tests/eval/sdk/consumers/go/go.mod` >= 1.
    - Rust builds: `cargo build --example sdk_proof_consumer --manifest-path crates/voss-sdk/Cargo.toml --quiet` exits 0; `grep -c "VossClient::new" crates/voss-sdk/examples/sdk_proof_consumer.rs` >= 1 and `grep -c "spawn_with" crates/voss-sdk/examples/sdk_proof_consumer.rs` == 0.
    - The three Task-1 build tests now PASS: `.venv/bin/python -m pytest tests/eval/test_sdk.py -k "test_ts_consumer_resolves or test_go_consumer_builds or test_rust_consumer_builds" -q` reports 0 failed.
    - Each consumer emits the six-key schema: `grep -E "saw_permission_gate" tests/eval/sdk/consumers/ts/consumer.js tests/eval/sdk/consumers/go/main.go crates/voss-sdk/examples/sdk_proof_consumer.rs` returns 3 matches.
  </acceptance_criteria>
  <done>Three committed public-API-only consumer subprograms BUILD with zero new package installs; TS avoids VossLauncher, Go uses AttachClient, Rust uses VossClient::new; the three build-verification tests are green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| consumer subprogram → SDK public client API | consumer code is committed in-repo; built + run from a committed dir; no remote fetch |
| go/cargo build → module/crate cache | Go `replace` directive + Cargo path resolution = local-only; no network module pull at build |
| TS `file:` dep → prebuilt dist | resolves to the in-repo `sdk/typescript/dist`; no npm registry fetch (dep already installed) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E4-01 | Tampering | consumer fetching code from network at build | mitigate | Go `replace` → local `../../../../sdk/go`; Rust example builds against the in-repo crate; TS `file:` dep → in-repo dist. No registry/remote URLs in any manifest. |
| T-E4-02 | Tampering | TS consumer importing the node launcher (VossLauncher) | mitigate | Consumer imports ONLY from @vosslang/sdk (not /node); grep gate asserts 0 references to VossLauncher / @vosslang/sdk/node |
| T-E4-03 | Information Disclosure | consumer leaking server token via build logs | accept | Token is not present at build time (only at run time via env, added in W1); build phase has no token |
| T-E4-SC | Tampering | npm/pip/cargo installs | accept | E4 introduces zero new packages (RESEARCH Package Legitimacy Audit: not applicable). The TS `file:` dep references an already-installed in-repo package; Go/Rust use existing module/crate. No install task. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/eval/test_sdk.py -q` → xfail stubs pending, three build tests green, EVSDK-07 skipped (live-only)
- All three consumers BUILD offline with zero new package installs
- TS imports @vosslang/sdk only (no VossLauncher); Go uses AttachClient (no Spawn); Rust uses VossClient::new (no spawn_with)
- Existing eval suite import surface unchanged: `.venv/bin/python -c "import voss.eval.runner, voss.eval.suite"` clean
</verification>

<success_criteria>
- RED Nyquist scaffold (`test_sdk.py`) maps 1:1 to EVSDK-01..08; permission gate is live-only-skip
- Three consumer subprograms build (resolves the TS file:-dep, Go replace-directive, Rust examples open questions)
- Pitfall guards encoded: TS-no-VossLauncher, Go-AttachClient-not-Spawn, public-API-only
- Zero new package installs
</success_criteria>

<output>
Create `.planning/phases/E4-sdk-proof/E4-01-SUMMARY.md` when done
</output>
