# Phase E5: TUI + voss-app Autonomous Driving - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

E5 proves the two interactive surfaces work end-to-end: the Textual TUI driven autonomously through full journeys (boot → prompt → turn → diff approval → exit) including live-model runs, and the voss-app desktop driven through its existing-but-skipped Playwright e2e contracts via a Linux CI tauri-driver job. Today the TUI has only component-level Pilot tests (`tests/harness/tui/`) and voss-app's 11 e2e specs are all `test.skip` stubs blocked by the macOS WebDriver gap (A2-04 decision).

</domain>

<decisions>
## Implementation Decisions

### TUI driving (level + live wiring)
- **D-01:** TUI journeys driven via **Textual Pilot in-process** (`app.run_test()` + `pilot.press/click` + snapshot/state asserts) — extends the existing `tests/harness/tui/` Pilot patterns to full journeys. No PTY/pexpect layer in E5.
- **D-02:** Live-model TUI journeys live as **`@pytest.mark.live` pytest tests** (codex auth, on-demand, creds-gated skip) — NOT forced into E1's TaskSpec/eval-runner model (async Pilot doesn't fit the subprocess driver shape). Each live journey has a hermetic twin running on a stub provider that runs in the normal suite.
- **D-03:** Journey set (minimum): (a) boot → prompt → streamed turn → final rendered → quit; (b) edit flow with diff-approval modal (approve + reject variants); (c) slash-command flow (e.g. /cost or /models). Snapshot baselines via existing `pytest-textual-snapshot`.

### voss-app driving
- **D-04:** Route = **Linux CI `tauri-driver` job** (GitHub Actions, `workflow_dispatch` manual trigger only — keeps E-track's on-demand posture; no scheduled runs, not a PR gate). WebKitWebDriver + tauri-driver on ubuntu runner builds the app and runs Playwright against it.
- **D-05:** Un-skip the existing 11 e2e contracts in `apps/voss-app/e2e/` **incrementally** — contracts stay as written (A2-04 preserved their names + assertion intent for exactly this). E5 target: ≥3 un-skipped and green (start with command-palette, project-open, themes — lightest); perf-heavy specs (flood-perf, grid-perf, 10k scrollback) explicitly NOT required for E5.
- **D-06:** Voss-native panes in CI use the **`VOSS_SERVE_FAKE_TURN=1` seam** — no subscription creds on CI ever. Live-model desktop driving is out of scope for E5 (TUI carries the live proof).

### Proof criteria (closes the phase)
- **D-07:** (1) ≥3 TUI Pilot journeys pass **live** on codex auth locally (and their stub twins green in the normal suite); (2) the Linux CI job runs end-to-end with ≥3/11 contracts un-skipped and green on FAKE_TURN; (3) human checkpoint reviews both artifacts (pytest live output + CI run link) — mirrors E1-05/E3-04 checkpoint pattern.

### Posture notes
- **D-08:** The CI job does not violate the E-track "no CI" decision — that decision rejected scheduled/blocking CI for *eval* runs. This job is manual-dispatch infra for a platform-blocked surface, runs no live models, and gates nothing.
- **D-09:** `VOSS_DEV` gate not needed for pytest journeys (live tests already creds-gated + live-marked); reuse the `live` pytest marker conventions from `tests/eval/test_live_signals.py`.

### Claude's Discretion
- Which 3+ of the 11 contracts to un-skip first (lightest-first recommended above is advisory).
- Snapshot-baseline management policy (regen command, committed baselines).
- CI job details: runner image, caching, artifact upload (Playwright traces), tauri-driver/WebKitWebDriver versions.
- Stub-provider scripting for journey twins (reuse deterministic StubProvider from tests/e2e or examples helpers).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contracts + prior decisions
- `.planning/notes/e-track-eval-decisions.md` — E-track posture (on-demand, internal-only; D-08 above scopes the CI exception).
- `apps/voss-app/e2e/pty.spec.ts` (header comment) — the A2-04 decision + contract-preservation rationale; all 11 specs follow it.
- `.planning/phases/E3-surface-e2e/E3-RESEARCH.md` — `VOSS_SERVE_FAKE_TURN=1` seam details (app.py), serve handshake (if CI panes attach to a real serve).

### TUI surface
- `voss/harness/tui/app.py` — the Textual app under test (boot, prompt, streaming, modals).
- `tests/harness/tui/` — existing Pilot component tests (palette, permission modal, help overlay, subagent reveal) — the patterns journeys extend.
- `pyproject.toml` — `textual>=0.58,<9.0`, `pytest-textual-snapshot>=1.1.0` already pinned.
- `tests/eval/test_live_signals.py` — live-marker + creds-gating conventions to reuse.

### voss-app surface
- `apps/voss-app/playwright.config.ts` + `apps/voss-app/e2e/*.spec.ts` — the 11 skip-stubbed contracts (names + assertion intent locked).
- `apps/voss-app/package.json` — `test:e2e` script, Playwright 1.60 pinned.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Pilot test harness patterns in `tests/harness/tui/` — fixtures, app construction, key-press idioms.
- `pytest-textual-snapshot` — snapshot assertion plugin already installed.
- Deterministic StubProvider wiring (`tests/e2e/runner.py` sitecustomize / `tests/examples/helpers`) — for hermetic journey twins.
- `VOSS_SERVE_FAKE_TURN=1` (server) — canned turn without provider, for CI app panes.
- 11 Playwright contracts with assertion intent documented in comments — un-skip targets, not new authorship.

### Established Patterns
- `@pytest.mark.live` + creds-detection skip (`_has_live_creds`) — live tests never break hermetic runs.
- A2-04: interaction logic verified by vitest/cargo/tsc on macOS; browser-integration layer deferred to Linux — E5 finally lands that deferred layer.
- Codex auth quirks (gpt-5.x only, no temperature) — live TUI journeys inherit.

### Integration Points
- TUI journeys construct the real Textual app with a real (live) or stub provider — find the app's provider injection seam in `voss/harness/tui/app.py`.
- CI job: new `.github/workflows/` file (manual dispatch), builds Tauri app on ubuntu, installs tauri-driver + WebKitWebDriver, runs `npm run test:e2e` subset.

</code_context>

<specifics>
## Specific Ideas

- The diff-approval journey (D-03b) is the marquee TUI proof — modal interaction + file mutation + approve/reject branches with a real model turn behind it.
- CI run link + live pytest output are the two artifacts the human checkpoint reviews (E1-05/E3-04 pattern).

</specifics>

<deferred>
## Deferred Ideas

- PTY/pexpect smoke of the real terminal binary — revisit if Pilot misses a class of bug.
- Remaining 8 Playwright contracts incl. perf specs (flood-perf, grid-perf, 10k scrollback) — un-skip over time post-E5.
- Live-model desktop driving (real creds in app panes) — only if a desktop-specific model bug class appears.
- Scheduled CI runs / PR gating for the app e2e job — against E-track posture for now.

</deferred>

---

*Phase: E5-tui-voss-app-autonomous-driving*
*Context gathered: 2026-06-10*
