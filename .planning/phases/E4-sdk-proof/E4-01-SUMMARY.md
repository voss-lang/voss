---
phase: E4-sdk-proof
plan: 01
subsystem: testing
tags: [eval, sdk, typescript, go, rust, nyquist, consumer-subprograms]

requires:
  - phase: E3-surface-e2e
    provides: "surface Literal + dispatch chain + _live_env in voss/eval (E3-01/02); serve FAKE_TURN seam"
  - phase: M7
    provides: "published SDK client surfaces: @vosslang/sdk dist, sdk/go AttachClient, crates/voss-sdk VossClient"
provides:
  - "RED Nyquist scaffold tests/eval/test_sdk.py — xfail stubs 1:1 to EVSDK-01..08 (07/08 live-only skips)"
  - "Three committed public-API-only consumer subprograms that BUILD offline: ts (consumer.js), go (main.go), rust (examples/sdk_proof_consumer.rs)"
  - "Resolved all three RESEARCH open questions: TS file:-dep resolution, Go replace directive depth, Rust examples/ auto-discovery"
affects: [E4-sdk-proof plans 02-06, eval, sdk]

tech-stack:
  added: []
  patterns: ["committed node_modules symlink for offline file:-dep resolution", "consumer emits one structured-JSON stdout line {surface, session_id, final, saw_permission_gate, cost_usd, event_types_seen}"]

key-files:
  created:
    - tests/eval/test_sdk.py
    - tests/eval/sdk/consumers/ts/consumer.js
    - tests/eval/sdk/consumers/ts/package.json
    - tests/eval/sdk/consumers/ts/node_modules/@vosslang/sdk (committed symlink)
    - tests/eval/sdk/consumers/go/main.go
    - tests/eval/sdk/consumers/go/go.mod
    - tests/eval/sdk/consumers/go/go.sum
    - crates/voss-sdk/examples/sdk_proof_consumer.rs
  modified: []

key-decisions:
  - "TS file:-dep resolved via committed node_modules/@vosslang/sdk symlink (git add -f past node_modules/ ignore) — zero installs, offline, import stays `from \"@vosslang/sdk\"`"
  - "Go replace directive is 5 levels up (../../../../../sdk/go), not the 4 the plan sketch counted; go.sum committed from module cache via go mod tidy"
  - "Event-type discriminator recovered via serialize-and-read-type in go/rust (Go eventType() is unexported; Rust variant names ≠ wire tags)"

patterns-established:
  - "Build-verification tests as W0 de-risk gates: real (non-xfail) pytest tests run node/go/cargo builds, skipif toolchain absent, marked slow"
  - "Consumer env contract: VOSS_BASE_URL (exit 2 if missing), VOSS_TOKEN, VOSS_CWD, VOSS_PROMPT, VOSS_MODE"

requirements-completed: [EVSDK-01, EVSDK-02, EVSDK-03, EVSDK-04, EVSDK-05]

duration: 16min
completed: 2026-06-12
---

# Phase E4 Plan 01: SDK Proof Wave 0 Summary

**RED Nyquist scaffold (test_sdk.py, EVSDK-01..08) plus three buildable public-API-only SDK consumer subprograms (ts/go/rust) proving the external-consumer contract offline with zero new package installs**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-06-12T00:09Z
- **Completed:** 2026-06-12T00:25Z
- **Tasks:** 2
- **Files modified:** 9 created

## Accomplishments
- `tests/eval/test_sdk.py`: 6 xfail stubs (EVSDK-01..06), 2 live-only skips (EVSDK-07 permission gate, EVSDK-08 proof run), 3 real build-verification gates — module runs green (3 passed, 6 xfailed, 2 skipped), full `tests/eval/` suite no regression
- TS consumer resolves `@vosslang/sdk` from the index surface only (createVossClient/subscribeToEvents/replyPermission); env-guard probe exits 2 with no module-resolution error
- Go consumer builds with `replace github.com/vosslang/voss/sdk/go => ../../../../../sdk/go`; uses AttachClient + value-type event switch (PermissionUpdated/FinalEvent/SessionIdle), never Spawn
- Rust consumer auto-discovered as cargo example; VossClient::new + pinned event_stream + permission_reply, never the supervisor spawn path

## Task Commits

1. **Task 1: RED Nyquist scaffold tests/eval/test_sdk.py** - `1c33092` (test)
2. **Task 2: Three buildable consumer subprograms (ts/go/rust)** - `1e83b68` (feat)

## Files Created/Modified
- `tests/eval/test_sdk.py` - RED scaffold + three build gates
- `tests/eval/sdk/consumers/ts/{consumer.js,package.json,node_modules/@vosslang/sdk}` - TS consumer + file: dep + committed resolution symlink
- `tests/eval/sdk/consumers/go/{main.go,go.mod,go.sum,.gitignore}` - Go consumer module (binary ignored)
- `crates/voss-sdk/examples/sdk_proof_consumer.rs` - Rust consumer example

## Decisions Made
- **Open Q (TS) resolved:** `file:` dep alone does not resolve at runtime without an install step; committed a relative symlink `node_modules/@vosslang/sdk → ../../../../../../../sdk/typescript` instead so resolution is offline, install-free, and survives fresh checkouts. `package.json` keeps the `file:../../../../../sdk/typescript` dep as the declared relationship.
- **Open Q (Go) resolved:** replace path is `../../../../../sdk/go` (5 ups from the consumer dir). `go mod tidy` (module cache, offline) generated go.sum; both committed.
- **Open Q (Rust) resolved:** `examples/sdk_proof_consumer.rs` auto-discovered; no Cargo.toml change. serde_json/tokio/futures-util all in [dependencies], so no manual-JSON fallback needed.
- Added EVSDK-08 live-only skip stub (plan listed stubs only for 01..07) so the scaffold maps 1:1 to all eight minted requirements per success criteria.

## Deviations from Plan

**1. [Rule 1 - Bug] Go replace-directive depth corrected (4 → 5 ups)**
- **Found during:** Task 2 (go.mod)
- **Issue:** Plan/PATTERNS counted `../../../../sdk/go`; actual depth from `tests/eval/sdk/consumers/go/` to repo root is 5 levels
- **Fix:** `replace ... => ../../../../../sdk/go`; verified by `go build ./...` exit 0
- **Committed in:** 1e83b68

**2. [Rule 2 - Missing critical] Committed node_modules symlink for TS resolution**
- **Found during:** Task 2 (TS consumer)
- **Issue:** A `file:` dependency only takes effect after `npm install`; plan demanded zero installs AND `from "@vosslang/sdk"` imports
- **Fix:** Committed `node_modules/@vosslang/sdk` relative symlink (`git add -f` past the global `node_modules/` ignore); resolution proven by the env-guard probe
- **Committed in:** 1e83b68

**3. [Rule 1 - Bug] Pitfall-guard greps initially tripped by comments**
- **Found during:** Task 2 acceptance loop
- **Issue:** Doc comments mentioned "VossLauncher"/"spawn_with", violating the ==0 grep gates
- **Fix:** Reworded comments; gates re-run green
- **Committed in:** 1e83b68

**Total deviations:** 3 auto-fixed (2 Rule 1, 1 Rule 2). **Impact:** all necessary for the build-resolution de-risk; no scope creep.

## Issues Encountered
- `go build ./...` drops a `sdk-go-consumer` binary in the module dir — added a local `.gitignore` for it.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- W1 (plan 02: surface Literal + `_drive_sdk_python`; plan 03: `_drive_sdk_client`) unblocked — toolchain wiring proven, consumers ready to be driven
- xfail stubs in test_sdk.py are the flip-targets for W1/W2/W3

---
*Phase: E4-sdk-proof*
*Completed: 2026-06-12*
