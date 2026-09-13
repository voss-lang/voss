# Phase E5: TUI + voss-app Autonomous Driving - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** E5-tui-voss-app-autonomous-driving
**Areas discussed:** TUI driving level, TUI live-model wiring, voss-app route, Proof criteria

**Note:** invoked as `/gsd-discuss-phase 5`; "5" resolved to legacy executed phase 05-cli-packaging-linguist — user confirmed E5 was intended.

---

## TUI driving level

| Option | Description | Selected |
|--------|-------------|----------|
| Textual Pilot in-process | app.run_test() + press/click + snapshots; extends existing tests/harness/tui/ | ✓ |
| PTY subprocess (pexpect) | Truest e2e incl. terminal layer; brittle, slow | |
| Both (Pilot + 1 PTY smoke) | Pilot journeys + pexpect boot smoke | |

---

## TUI live-model wiring

| Option | Description | Selected |
|--------|-------------|----------|
| Live-marked pytest journeys | @pytest.mark.live + creds gate; stub twins hermetic; no TaskSpec contortion | ✓ |
| E1 surface="tui" scenarios | One scoring system but async Pilot ≠ subprocess TaskSpec model | |

---

## voss-app route

| Option | Description | Selected |
|--------|-------------|----------|
| Linux CI tauri-driver job | workflow_dispatch manual; un-skip existing 11 contracts; FAKE_TURN, no creds on CI | ✓ |
| Browser + mocked Tauri IPC on macOS | Frontend-only proof, weaker claim | |
| Both | CI + local browser layer; most work | |
| Defer desktop | TUI only | |

---

## Proof criteria

| Option | Description | Selected |
|--------|-------------|----------|
| TUI live + app CI green | ≥3 Pilot journeys live + ≥3/11 contracts green on CI; human checkpoint | ✓ |
| TUI live only | App job stretch | |
| All 11 contracts | Heavy (perf specs) | |

---

## Claude's Discretion

- Which 3+ contracts to un-skip first (lightest-first advisory)
- Snapshot-baseline policy
- CI job internals (runner, caching, trace artifacts, driver versions)
- Stub-provider scripting for journey twins

## Deferred Ideas

- PTY/pexpect smoke
- Remaining 8 contracts incl. perf specs
- Live-creds desktop driving
- Scheduled/PR-gating CI for app e2e
