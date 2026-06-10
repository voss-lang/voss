---
phase: V15-live-plane-integration
plan: 06
type: execute
wave: 5
depends_on: ["V15-04", "V15-05"]
files_modified:
  - apps/voss-app/src/org/live/__tests__/liveSpine.ac.test.ts
  - apps/voss-app/src/org/live/__tests__/acSpawn.ts
  - .planning/phases/V15-live-plane-integration/V15-VALIDATION.md
autonomous: false
requirements: [VLIVE-08]
must_haves:
  truths:
    - "An automated AC suite spawns a real `voss serve` with the stub provider (no API key, no network) and drives the spine"
    - "The AC suite passes on a machine with no provider credentials"
    - "A human checkpoint performs one real-provider run confirming live label, structured rendering, and the permission loop end-to-end"
    - "PROTOCOL.md, contracts/*.json, sdk/typescript, and voss/ Python are byte-unchanged at phase close"
  artifacts:
    - path: "apps/voss-app/src/org/live/__tests__/liveSpine.ac.test.ts"
      provides: "Hermetic AC suite: gated on VOSS_AC_LIVE=1, spawns real voss serve (VOSS_HERMETIC=1 stub), drives handshake→client→SSE→render→permission→follow-up"
      contains: "VOSS_AC_LIVE"
    - path: "apps/voss-app/src/org/live/__tests__/acSpawn.ts"
      provides: "Test helper: spawn `voss serve --port 0` with the hermetic stub env, parse the {port,token} handshake, expose teardown"
      exports: ["spawnHermeticServe"]
  key_links:
    - from: "apps/voss-app/src/org/live/__tests__/liveSpine.ac.test.ts"
      to: "spawnHermeticServe → buildVossClientFromHandshake → connectLiveStream"
      via: "drives the full spine against a real server with the stub provider"
      pattern: "spawnHermeticServe"
---

<objective>
Prove the full live spine end-to-end two ways: (1) a hermetic automated AC suite that spawns a REAL `voss serve` with the stub provider (`VOSS_HERMETIC=1` — no API key, no network) and drives spawn→handshake→client construction→SSE subscription→structured render→permission reply→follow-up→overlay; (2) a single human checkpoint that walks the same spine on a REAL provider and signs off. Confirm the frozen surfaces are byte-unchanged.

Purpose: Close VLIVE-08. CI can verify the spine with zero credentials; a human confirms the real-model experience once. This is the phase gate.
Output: `acSpawn.ts` (hermetic spawn helper), `liveSpine.ac.test.ts` (the gated AC suite), the filled-in per-task statuses in V15-VALIDATION.md, and the recorded human sign-off.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/V15-live-plane-integration/V15-SPEC.md
@.planning/phases/V15-live-plane-integration/V15-VALIDATION.md
@.planning/phases/V15-live-plane-integration/V15-RESEARCH.md
@.planning/phases/V15-live-plane-integration/V15-SPIKE-sidecar.md
@apps/voss-app/src/org/live/vossClientBuild.ts
@apps/voss-app/src/org/live/sseClient.ts

<interfaces>
<!-- Contracts the executor needs. Extracted from codebase. -->

Hermetic stub provider (confirmed from voss/cli.py:351-361 + tests/cli/test_run_stub_fallback.py):
  - `VOSS_HERMETIC=1` forces the `__stub__` provider — "deterministic fake responses", NO creds, NO network.
  - Banner on stderr: "voss: no provider creds detected — using __stub__ (deterministic fake responses)".
  - The sidecar env already sets `LITELLM_LOCAL_MODEL_COST_MAP=true` + `PYDANTIC_DISABLE_PLUGINS=1`; ADD `VOSS_HERMETIC=1` for the AC spawn.

Spawn shape (from crates/voss-app-core/src/sidecar.rs / V15-SPIKE):
  - Command: `<python> -m voss.cli serve --port 0`, cwd = a temp dir; one-line stdout handshake `{"v":1,"port":…,"token":…}` (log lines do NOT false-parse).
  - Interpreter: `VOSS_PYTHON` > repo `.venv/bin/python` > `python3` (mirror python_path()). The AC helper resolves the SAME way.
  - 60s handshake budget (cold .pyc ~45s; warm ~1.5s). Drain stderr continuously. Hold stdin open as heartbeat; SIGKILL/close to reap.

From apps/voss-app/src/org/live/vossClientBuild.ts (Plan 02): buildVossClientFromHandshake({port,token}) → { client, runNativeClient, followUpClient, baseUrl, token }.
From apps/voss-app/src/org/live/sseClient.ts (Plan 02): connectLiveStream({baseUrl, sessionId, token, cardId, onEvent}) → { abort() }.
From sdk/typescript/src/client/rest.ts: client.createSession(cwd?) → string id; client.postMessage(id, text) → 202; client.listSessions().
From sdk/typescript/src/client/permission.ts: replyPermission(client, sessionId, {id, choice}).

Vitest can run Node APIs (child_process) in this repo (jsdom env, but Node globals available in test files). Gate the suite so the default `vitest run` SKIPS it (it spawns a real process): wrap the describe in `describe.skipIf(process.env.VOSS_AC_LIVE !== '1')`.
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| AC test → spawned server | the AC suite owns a real child process; must reap it deterministically (no orphan after the run) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V15-SC | Tampering | AC spawn env | mitigate | The AC suite runs `voss.cli serve` from the repo's own `.venv` (no network install); `VOSS_HERMETIC=1` guarantees the stub provider with no outbound calls. No package install occurs in this plan (zero new deps — SPEC). The spawn helper reaps the child in `afterAll` (kill + await) so no orphan survives the suite (mirrors the spike's reap proof). |
| T-V15-02 | Denial of Service | orphan AC server | mitigate | `afterAll` kills the child and awaits exit; a hard timeout on the handshake (60s) fails fast rather than hanging CI. |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Hermetic spawn helper + AC suite driving the full spine</name>
  <files>apps/voss-app/src/org/live/__tests__/acSpawn.ts, apps/voss-app/src/org/live/__tests__/liveSpine.ac.test.ts</files>
  <read_first>
    - crates/voss-app-core/src/sidecar.rs (the spawn env, handshake parse, interpreter resolution, stderr drain, stdin heartbeat — the AC helper reimplements the MINIMAL spawn in Node/TS for the test; the production spawn stays in Rust)
    - .planning/phases/V15-live-plane-integration/V15-SPIKE-sidecar.md (measurements + the VOSS_PYTHON > .venv > python3 chain + the env vars)
    - voss/cli.py (lines 345-365 — VOSS_HERMETIC handling + the stub-provider banner; confirm `serve` accepts `--port 0`)
    - tests/cli/test_run_stub_fallback.py (the __stub__ no-creds path — confirms VOSS_HERMETIC=1 forces deterministic fakes)
    - apps/voss-app/src/org/live/vossClientBuild.ts + sseClient.ts (the client + stream the suite drives — reuse, do not duplicate)
    - apps/voss-app/src/org/live/__tests__/mockSseStream.ts (the injected-stream fallback for the permission leg if the stub provider does not emit permission.updated)
  </read_first>
  <action>
    Create `apps/voss-app/src/org/live/__tests__/acSpawn.ts` exporting `async function spawnHermeticServe(cwd: string): Promise<{ port: number; token: string; kill: () => Promise<void> }>`. Resolve the interpreter the same way as `python_path()` (env `VOSS_PYTHON` → repo `.venv/bin/python` → `python3`). `child_process.spawn(python, ['-m','voss.cli','serve','--port','0'], { cwd, env: { ...process.env, VOSS_HERMETIC: '1', LITELLM_LOCAL_MODEL_COST_MAP: 'true', PYDANTIC_DISABLE_PLUGINS: '1' }, stdio: ['pipe','pipe','pipe'] })`. Read stdout line-by-line until a line parses as `{v,port,token}` (ignore non-JSON log lines); reject after a 60s timeout with the captured stderr tail. Drain stderr continuously into a buffer. Keep stdin open (heartbeat). `kill()` = `child.kill('SIGKILL')` + await `once('exit')`.

    Create `apps/voss-app/src/org/live/__tests__/liveSpine.ac.test.ts`, `describe.skipIf(process.env.VOSS_AC_LIVE !== '1')('VLIVE-08 live spine (hermetic)', …)` with `afterAll` reaping the server. The spine assertions, against the REAL spawned server with the stub provider:
    1. `spawnHermeticServe(tmpdir)` returns a `{port, token}` handshake (proves VLIVE-01 end-to-end from the test's POV).
    2. `buildVossClientFromHandshake({port,token})` → `client.createSession(tmpdir)` returns a non-empty string session id (proves VLIVE-02 createSession against a real server).
    3. `connectLiveStream({baseUrl, sessionId, token, cardId: sessionId, onEvent})` + `client.postMessage(sessionId, 'do something small')` (202) → collect events for a bounded window; assert at least one §6 event arrives and that the stream yields a terminal-ish event (`final` or `session.idle`) OR times out gracefully (proves VLIVE-03 live SSE on real events). Assert `liveLabel` was 'live' during the stream and 'snapshot' after teardown.
    4. Permission leg: IF the stub provider emits a `permission.updated` in the collected events, assert `replyPermission(client, sessionId, {id, choice:'a'})` resolves (200) and the turn proceeds. IF the stub does not emit one (deterministic-fake may not gate), drive the permission path against the real client transport by POSTing a known-id reply and asserting the server's response shape — and record in the summary that the stub-provider permission leg is covered by the unit gate (Plan 04 ProtocolPane test) plus this transport check, since the stub does not naturally request permission. (Honest-data: do not fabricate a permission event into the real stream.)
    5. Follow-up: a second `client.postMessage(sessionId, 'follow up')` returns 202 (proves VLIVE-02 follow-up).
    Keep each network wait bounded (per-step timeout ≤ 30s) so CI fails fast. Use the repo `.venv` (no install).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && VOSS_AC_LIVE=1 npx --no vitest run src/org/live/__tests__/liveSpine.ac.test.ts 2>&1 | tail -25</automated>
  </verify>
  <acceptance_criteria>
    - `acSpawn.ts` exports `spawnHermeticServe`; sets `VOSS_HERMETIC=1` + `LITELLM_LOCAL_MODEL_COST_MAP=true` + `PYDANTIC_DISABLE_PLUGINS=1` in the spawn env
    - `liveSpine.ac.test.ts` is `describe.skipIf(process.env.VOSS_AC_LIVE !== '1')` (default `vitest run` SKIPS it — verify the full suite does not spawn a process)
    - `VOSS_AC_LIVE=1 npx --no vitest run src/org/live/__tests__/liveSpine.ac.test.ts` exits 0 with no provider credentials configured (stub provider; no network)
    - The suite reaps the server in `afterAll` (no orphan: a follow-up `pgrep -f "voss.cli serve"` after the run finds none — T-V15-02/T-V15-SC)
    - Spine steps 1-3 + 5 assert against the REAL spawned server; the permission leg is honest (no fabricated event into the real stream)
    - Default suite unaffected: `npx --no vitest run src/org/live/__tests__/sseClient.test.ts` still exits 0 (the AC file is skipped without the env var)
  </acceptance_criteria>
  <done>A gated hermetic AC suite spawns a real `voss serve` (stub provider, no creds, no network), drives handshake→client→SSE→follow-up, asserts the live-label flip, and reaps the server — passing with zero credentials.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 2: Human real-provider spine walkthrough + frozen-surface check</name>
  <what-built>
    The full V15 live plane: sidecar Tauri command (Plan 01), client + sockets (Plan 02), structured ProtocolPane (Plan 03), inline permission gate + lifecycle states (Plan 04), attach surface (Plan 05), and the hermetic AC suite (this plan Task 1). This checkpoint confirms the experience on a REAL provider, which the hermetic suite cannot exercise.
  </what-built>
  <read_first>
    - .planning/phases/V15-live-plane-integration/V15-VALIDATION.md (the Manual-Only Verifications table — the exact 7-step spine to walk; fill in the per-task statuses to ✅ after each automated wave passed)
    - .planning/phases/V15-live-plane-integration/V15-SPEC.md (Acceptance Criteria — the human-checkpoint line + the frozen-surface line)
  </read_first>
  <action>
    First, the automated frozen-surface check (run before requesting the human): assert PROTOCOL.md, contracts/*.json, sdk/typescript, and voss/ are byte-unchanged by V15. Run `git diff --stat HEAD~<N> -- .planning/PROTOCOL.md contracts/ sdk/typescript/ voss/` (N = commits since phase start) — expect EMPTY. If any of those paths changed, STOP and flag (SPEC constraint violation: V15 is app-side-only).

    Then present the human checkpoint. With a real provider configured (API key + network), the operator performs the V15-VALIDATION Manual-Only spine:
    1. App open; RunCommandBar native target; enter a real goal; Start.
    2. Confirm the boot placeholder ("Starting…" + elapsed) appears, then the structured transcript begins (cold start shows the 60s-budget hint after 5s).
    3. Confirm the titlebar reads `● live · voss serve :<port>` while the run streams.
    4. Confirm structured rendering: task header, collapsed tool lines (click one to expand), plan prose, stream deltas settling, `final` row with conf/cost.
    5. When a permission gate appears, Allow once from the pane; confirm the turn proceeds AND the AttentionQueue row clears (dual-surface).
    6. Open the card drawer; post a follow-up comment; confirm it is accepted (202).
    7. Confirm the overlay (budget) updated during the run; then confirm the label returns to `snapshot` after `final`.
    Record the sign-off (approve / list issues) in the summary.
  </action>
  <how-to-verify>
    1. `cd apps/voss-app && npx --no vitest run` — full suite shows no NEW failures vs. the captured baseline.
    2. `cargo test -p voss-app-core sidecar::tests::cwd_validation` exits 0; `VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core sidecar` exits 0.
    3. `VOSS_AC_LIVE=1 npx --no vitest run src/org/live/__tests__/liveSpine.ac.test.ts` exits 0 (no creds).
    4. `git diff --stat` over PROTOCOL.md / contracts/ / sdk/typescript/ / voss/ since phase start is EMPTY (frozen-surface check).
    5. Launch the app with a real provider and walk steps 1-7 above; confirm each.
  </how-to-verify>
  <acceptance_criteria>
    - Frozen-surface git diff over PROTOCOL.md, contracts/, sdk/typescript/, voss/ is empty (no app-side-only violation)
    - Full vitest suite: no new failures vs. baseline; cargo sidecar tests green; hermetic AC suite green
    - Human sign-off recorded covering the full spine (intake → spawn → structured stream → inline permission → final → follow-up → overlay)
  </acceptance_criteria>
  <resume-signal>Type "approved" (with any notes) or describe the issues found during the spine walk.</resume-signal>
</task>

</tasks>

<verification>
- `VOSS_AC_LIVE=1 cd apps/voss-app && npx --no vitest run src/org/live/__tests__/liveSpine.ac.test.ts` exits 0 with no provider credentials
- Default `npx --no vitest run` does NOT spawn a server (AC file skipped without the env var); no new failures vs. baseline
- `git diff --stat` since phase start over PROTOCOL.md / contracts/ / sdk/typescript/ / voss/ is empty
- Human checkpoint sign-off recorded
</verification>

<success_criteria>
- Hermetic AC suite passes with no provider credentials and no network against a real `voss serve` (stub provider) (VLIVE-08)
- One human real-provider run walks the full spine and is signed off (VLIVE-08)
- PROTOCOL.md, contracts/*.json, sdk/typescript, voss/ are byte-unchanged (SPEC frozen-surface constraint)
- The spawned AC server is reaped (no orphan — T-V15-02/T-V15-SC)
</success_criteria>

<output>
Create `.planning/phases/V15-live-plane-integration/V15-06-SUMMARY.md` when done
</output>
