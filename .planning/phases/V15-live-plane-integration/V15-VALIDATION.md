---
phase: V15
slug: live-plane-integration
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-09
---

# Phase V15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Three test surfaces: vitest (frontend), cargo (Rust sidecar command),
> and a hermetic stub-provider AC suite that spawns a real `voss serve`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (frontend)** | Vitest 4.1.6 + jsdom |
| **Framework (Rust)** | cargo test (gated integration via `VOSS_SIDECAR_SPIKE=1`) |
| **Config file** | `apps/voss-app/vitest.config.ts` (frontend); workspace `Cargo.toml` (Rust) |
| **Quick run command** | `cd apps/voss-app && npx --no vitest run src/org/live/__tests__/ src/org/attention/__tests__/ src/org/cockpit/__tests__/ src/pane/__tests__/` |
| **Full suite command** | `cd apps/voss-app && npx --no vitest run` |
| **Rust sidecar test** | `VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core sidecar` |
| **Hermetic AC suite** | `cd apps/voss-app && VOSS_AC_LIVE=1 npx --no vitest run src/org/live/__tests__/liveSpine.ac.test.ts` |
| **Estimated runtime** | frontend quick ~8s · full ~25s · Rust sidecar ~5s warm (60s cold budget) · AC suite ~20s (real spawn) |

**Pre-existing failure baseline (do NOT block on these):** the full suite shows
~77 failing / ~387 passing before V15 — failures concentrated in
`chords.test.ts` and `windowEffects.test.ts` (unrelated to V15 scope). A V15
task is GREEN when its own targeted test files pass and it adds no NEW failures
to the baseline. Capture the baseline failing-test count at Wave 0 and compare.

---

## Sampling Rate

- **After every task commit:** Run the **Quick run command** (affected modules).
- **After every plan wave:** Run the **Full suite command** + `tsc --noEmit` (no new failures vs. baseline).
- **Before `/gsd-verify-work`:** Full vitest (no new failures) + `VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core sidecar` green + hermetic AC suite green.
- **Max feedback latency:** 25 seconds (full frontend suite).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| V15-01-01 | 01 | 1 | VLIVE-01 | T-V15-01 | `cwd` canonicalized + rejected if outside workspace roots before spawn | integration (cargo) | `VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core sidecar` | ✅ sidecar.rs | ✅ green |
| V15-01-02 | 01 | 1 | VLIVE-01 | T-V15-02 | reuse-if-alive: stale `pid()==None` entry respawned, no orphan on exit | integration (cargo) + unit | `cargo test -p voss-app-core reuse_if_alive` ; `cd apps/voss-app && npx --no vitest run src/org/live/__tests__/sidecarCommand.test.ts` | ✅ created | ✅ green |
| V15-02-01 | 02 | 2 | VLIVE-02 | T-V15-03 | client built with Bearer token from handshake; no token logged | unit (vitest) | `cd apps/voss-app && npx --no vitest run src/org/live/__tests__/clientBuild.test.ts src/org/cockpit/__tests__/runCommandBar.test.tsx` | ✅ created | ✅ green |
| V15-02-02 | 02 | 2 | VLIVE-02, VLIVE-03 | T-V15-04 | sidecar-absent path renders disabled-with-reason unchanged (no silent enable) | unit (vitest) | `cd apps/voss-app && npx --no vitest run src/org/live/__tests__/sseClient.test.ts src/org/__tests__/feedbackWritePath.test.ts` | ✅ extends existing | ✅ green |
| V15-03-01 | 03 | 2 | VLIVE-04 | T-V15-05 | every §6 union member renders a row; out-of-set member → generic row, nothing dropped | unit (vitest) | `cd apps/voss-app && npx --no vitest run src/pane/__tests__/ProtocolPane.test.tsx` | ✅ created | ✅ green |
| V15-03-02 | 03 | 2 | VLIVE-04 | T-V15-06 | PTY pane suite passes unmodified (protocol branch additive) | regression (vitest) | `cd apps/voss-app && npx --no vitest run src/pane/__tests__/` | ✅ existing | ✅ green (suite unmodified) |
| V15-04-01 | 04 | 3 | VLIVE-05 | T-V15-07 | permission reply requires valid Bearer (server 401 without); one reply clears both surfaces | unit (vitest) | `cd apps/voss-app && npx --no vitest run src/pane/__tests__/ProtocolPane.test.tsx src/org/attention/__tests__/attentionQueue.test.tsx` | ✅ extended | ✅ green |
| V15-04-02 | 04 | 3 | VLIVE-06 | T-V15-08 | attach via live `GET /session` only; respawn sidecar before list; no transcript fabrication | unit (vitest) | `cd apps/voss-app && npx --no vitest run src/org/cockpit/__tests__/serverSessions.test.ts` | ✅ created | ✅ green |
| V15-05-01 | 05 | 3 | VLIVE-07 | T-V15-09 | server death → label 'snapshot', ended state, write disabled-with-reason; next run respawns | unit (vitest) | `cd apps/voss-app && npx --no vitest run src/pane/__tests__/ProtocolPane.test.tsx src/org/live/__tests__/sseClient.test.ts` | ✅ extended | ✅ green |
| V15-06-01 | 06 | 4 | VLIVE-08 | T-V15-SC | AC suite spawns real `voss serve` (stub provider, no creds, no network) and drives the spine | integration (vitest + real spawn) | `cd apps/voss-app && VOSS_AC_LIVE=1 npx --no vitest run src/org/live/__tests__/liveSpine.ac.test.ts` | ✅ created | ✅ green (5/5, credless, no orphan) |
| V15-06-02 | 06 | 4 | VLIVE-08 | — | human walks full spine on a real provider; sign-off recorded | manual (human-verify) | N/A — checkpoint | ❌ N/A | ⬜ pending (checkpoint presented 2026-06-10) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 scaffolds the MISSING test files before implementation. Each new test
file starts with `it.todo` / failing-stub assertions that encode the requirement
behavior, then implementation turns them green (RED→GREEN). All Wave 0 files are
created inside the FIRST task of the plan that owns the requirement (no separate
Wave 0 plan — scaffolds ride the owning task's first commit).

- [x] `apps/voss-app/src/org/live/__tests__/sidecarCommand.test.ts` — VLIVE-01 frontend `invoke('start_voss_serve')` contract (mocked invoke), handshake shape `{port:number, token:string}` (owned by Plan 01)
- [x] `apps/voss-app/src/org/live/__tests__/clientBuild.test.ts` — VLIVE-02 `buildVossClientFromHandshake` adapter: createSession string→`{id}` wrap; baseUrl `http://127.0.0.1:<port>` (owned by Plan 02)
- [x] `apps/voss-app/src/pane/__tests__/ProtocolPane.test.tsx` — VLIVE-04/05/07 transcript rows, generic fallback, inline gate, boot/ended/error states (owned by Plan 03; extended by Plans 04, 05)
- [x] `apps/voss-app/src/org/cockpit/__tests__/serverSessions.test.ts` — VLIVE-06 session-list signal + attach handler (owned by Plan 04)
- [x] `apps/voss-app/src/org/live/__tests__/liveSpine.ac.test.ts` — VLIVE-08 hermetic AC suite, gated on `VOSS_AC_LIVE=1`, spawns real `voss serve` stub provider (owned by Plan 06)
- [x] Rust: extend `crates/voss-app-core/src/sidecar.rs` `#[cfg(test)] mod tests` with `reuse_if_alive` + `cwd_validation` gated cases (owned by Plan 01)

Existing infrastructure (`sseClient.test.ts`, `attentionQueue.test.tsx`,
`runCommandBar.test.tsx`, `mockSseStream.ts`, the gated sidecar spike test)
covers the remaining requirement assertions via extension.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full live spine on a real provider | VLIVE-08 | A real LLM provider (API key, network) cannot run in hermetic CI; the human checkpoint confirms the end-to-end spine with real model output | 1. Launch the app with a configured provider. 2. In RunCommandBar, native target, enter a real goal, Start. 3. Confirm: boot placeholder → structured transcript appears → live label reads `● live · voss serve :<port>`. 4. When a permission gate appears, Allow once from the pane; confirm the turn proceeds AND the AttentionQueue row clears. 5. Confirm `final` row renders with conf/cost. 6. Open the card drawer, post a follow-up comment; confirm it is accepted (202). 7. Confirm the overlay (budget) updated during the run. Record sign-off (approve/issues). |
| Cold-start affordance visual + 60s budget | VLIVE-07 / D-10 | Cold-start timing (up to 60s `.pyc` compile) is environment-dependent and not reliably reproducible in CI | Covered inside the VLIVE-08 human checkpoint: on the first native run after app launch (cold), confirm "Starting…" + elapsed counter shows and the "Cold start takes up to 60s" hint appears after 5s, then the transcript begins. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (V15-06-02 is the single sanctioned human checkpoint per VLIVE-08)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (only the final checkpoint is manual)
- [x] Wave 0 covers all MISSING references (5 new test files + 2 Rust cases enumerated above)
- [x] No watch-mode flags (`vitest run`, never bare `vitest`)
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready (planner) — 2026-06-09
