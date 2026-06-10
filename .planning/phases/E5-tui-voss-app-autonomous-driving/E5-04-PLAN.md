---
phase: E5-tui-voss-app-autonomous-driving
plan: 04
type: execute
wave: 3
depends_on: [E5-02, E5-03]
files_modified:
  - .github/workflows/voss-app-e2e.yml
autonomous: false
requirements: [D-04, D-06, D-07, D-08]
user_setup:
  - "GitHub Actions access to manually dispatch the voss-app-e2e workflow."
  - "Live TUI pytest output from E5-02 must be available for the human checkpoint."
must_haves:
  truths:
    - "D-04: voss-app-e2e.yml is workflow_dispatch only and has no push, pull_request, schedule, or release trigger"
    - "D-08: Workflow permissions are contents: read and the job is not a scheduled or blocking eval CI gate"
    - "D-04: Linux job installs WebKitWebDriver via webkit2gtk-driver, runs under xvfb, and installs tauri-driver with cargo install tauri-driver --locked"
    - "D-06: Workflow sets VOSS_SERVE_FAKE_TURN=1 and does not read provider secrets"
    - "D-07: Workflow uploads app e2e logs/artifacts even on failure"
    - "D-07: Human checkpoint reviews both live TUI pytest output and the GitHub Actions run link before E5 is marked complete"
  artifacts:
    - path: ".github/workflows/voss-app-e2e.yml"
      provides: "Manual Linux Tauri-driver e2e workflow for E5 desktop proof"
      contains: "workflow_dispatch"
  key_links:
    - from: ".github/workflows/voss-app-e2e.yml"
      to: "apps/voss-app/package.json test:e2e:tauri"
      via: "xvfb-run env TAURI_APP_BINARY=<debug binary> pnpm --dir apps/voss-app run test:e2e:tauri"
      pattern: "test:e2e:tauri"
    - from: ".github/workflows/voss-app-e2e.yml"
      to: "E5-CONTEXT.md D-08"
      via: "workflow_dispatch-only manual trigger, not scheduled or PR-gating"
      pattern: "workflow_dispatch"
---

<objective>
Add the manual Linux CI workflow and closeout checkpoint for E5 D-04, D-06, D-07, and D-08. The workflow must prove the desktop Tauri-driver contracts on Linux without becoming a PR gate, scheduled job, or live-model credential consumer.

Purpose: Produce the second E5 closeout artifact: a GitHub Actions run link with Tauri-driver/WebDriver contract evidence.
Output: `.github/workflows/voss-app-e2e.yml` plus a blocking human-verify checkpoint during execution.
</objective>

<execution_context>
@$HOME/.codex/get-shit-done/workflows/execute-plan.md
@$HOME/.codex/get-shit-done/templates/summary.md
@$HOME/.codex/get-shit-done/references/checkpoints.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-CONTEXT.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-RESEARCH.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-UI-SPEC.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-VALIDATION.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-PATTERNS.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-02-SUMMARY.md
@.planning/phases/E5-tui-voss-app-autonomous-driving/E5-03-SUMMARY.md

@.github/workflows/ci.yml
@.github/workflows/rust.yml
@apps/voss-app/package.json
@apps/voss-app/wdio.conf.mjs
@apps/voss-app/src-tauri/tauri.conf.json
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add manual Linux Tauri-driver workflow</name>
  <files>.github/workflows/voss-app-e2e.yml</files>
  <read_first>
    - .github/workflows/ci.yml (permissions/concurrency/action-pin style)
    - .github/workflows/rust.yml (Linux desktop dependencies)
    - apps/voss-app/package.json (test:e2e:tauri script from E5-03)
    - apps/voss-app/wdio.conf.mjs (TAURI_APP_BINARY requirement)
    - .planning/phases/E5-tui-voss-app-autonomous-driving/E5-RESEARCH.md (Tauri WebDriver docs addendum)
  </read_first>
  <action>
    Create `.github/workflows/voss-app-e2e.yml` with name `voss-app-e2e`. Set root `permissions: contents: read`. Use only `on: workflow_dispatch`; do not add `push`, `pull_request`, `schedule`, or `release`. Add concurrency group `${{ github.workflow }}-${{ github.ref }}` with `cancel-in-progress: false` so manual evidence runs are preserved.

    Add one `linux-tauri-driver` job on `ubuntu-latest` with a timeout of 45 minutes. Steps must: checkout with `actions/checkout@v6.0.2`; set up Node 20 with `actions/setup-node@v6`; set up Python 3.12 with `actions/setup-python@v6`; set up Rust with `dtolnay/rust-toolchain@stable`; use `Swatinem/rust-cache@v2`; enable pnpm through corepack; install Linux dependencies with `sudo apt-get install -y libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev webkit2gtk-driver xvfb`; run `pip install -e ".[dev]"`; run `pnpm install --frozen-lockfile`; run `cargo install tauri-driver --locked`; run `tauri-driver --version`; run `pnpm --dir apps/voss-app test`; run `pnpm --dir apps/voss-app build`; build the debug Tauri app with `pnpm --dir apps/voss-app tauri build --debug --no-bundle`; discover the binary with a shell command that checks `target/debug/voss-app` and `apps/voss-app/src-tauri/target/debug/voss-app` and writes `TAURI_APP_BINARY=<path>` to `$GITHUB_ENV`; then run the selected WDIO specs with `xvfb-run -a env VOSS_SERVE_FAKE_TURN=1 VOSS_HERMETIC=1 LITELLM_LOCAL_MODEL_COST_MAP=true TAURI_E2E=1 pnpm --dir apps/voss-app run test:e2e:tauri -- --spec e2e-tauri/command-palette.wdio.mjs,e2e-tauri/project-open.wdio.mjs,e2e-tauri/themes.wdio.mjs`.

    Add an upload-artifact step using `actions/upload-artifact@v5` with `if: always()` and name `voss-app-e2e-artifacts`. Include `apps/voss-app/test-results/**`, `apps/voss-app/.wdio/**`, `apps/voss-app/e2e-tauri/**`, and any log files produced by the workflow. Do not reference `secrets.ANTHROPIC_API_KEY`, `secrets.OPENAI_API_KEY`, or other provider secrets anywhere in the workflow.
  </action>
  <verify>
    <automated>python3 - <<'PY'
from pathlib import Path
p = Path('.github/workflows/voss-app-e2e.yml')
text = p.read_text()
assert 'workflow_dispatch' in text
for forbidden in ('pull_request:', 'push:', 'schedule:', 'release:', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY'):
    assert forbidden not in text, forbidden
for required in ('contents: read', 'webkit2gtk-driver', 'xvfb', 'cargo install tauri-driver --locked', 'VOSS_SERVE_FAKE_TURN=1', 'test:e2e:tauri', 'actions/upload-artifact'):
    assert required in text, required
PY</automated>
  </verify>
  <acceptance_criteria>
    - `.github/workflows/voss-app-e2e.yml` contains `workflow_dispatch` and does not contain `pull_request:`, `push:`, `schedule:`, or `release:`.
    - The workflow contains `permissions:` with `contents: read`.
    - The Linux dependency install includes `webkit2gtk-driver` and `xvfb`.
    - The workflow runs `cargo install tauri-driver --locked` and `tauri-driver --version`.
    - The workflow sets `VOSS_SERVE_FAKE_TURN=1` for the e2e run.
    - The workflow never references provider secrets.
    - The static Python verification exits 0.
  </acceptance_criteria>
  <done>The manual GitHub Actions workflow exists and is structurally safe for E5's non-blocking desktop proof.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>E5 TUI live proof and voss-app manual Linux Tauri-driver proof.</what-built>
  <how-to-verify>Review the output from `python3 -m pytest tests/harness/tui/test_e5_live_journeys.py -q -m live` and a GitHub Actions run for `voss-app-e2e.yml`. Confirm the live TUI run has at least three live-marked journeys and the workflow run shows the three selected app contracts green with artifacts uploaded.</how-to-verify>
  <resume-signal>Type "approved" with the live pytest output location and GitHub Actions run URL, or describe the failing artifact.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
| --- | --- |
| GitHub Actions runner -> desktop app | The runner launches the Tauri app under WebKitWebDriver through tauri-driver. |
| workflow env -> app/test process | CI environment variables distinguish fake/local proof from live provider work. |
| human evidence -> phase closeout | Operator reviews artifacts before marking E5 complete. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
| --- | --- | --- | --- | --- |
| T-E5-11 | Elevation | workflow permissions | mitigate | Root workflow permissions are `contents: read`; no write scopes. |
| T-E5-12 | Information Disclosure | provider secrets | mitigate | Workflow references no provider secrets and sets `VOSS_SERVE_FAKE_TURN=1`. |
| T-E5-13 | Denial of Service | scheduled/PR CI cost | mitigate | `workflow_dispatch` only; no scheduled or PR trigger. |
| T-E5-14 | Repudiation | missing closeout evidence | mitigate | Upload artifacts with `if: always()` and require a human checkpoint with run URL plus live pytest output. |
</threat_model>

<verification>
- Static workflow check in Task 1 exits 0.
- On GitHub Actions, manually dispatch `voss-app-e2e.yml`; the `linux-tauri-driver` job exits 0.
- Job logs show `tauri-driver --version`, `VOSS_SERVE_FAKE_TURN=1`, and the three selected e2e specs.
- `actions/upload-artifact` creates `voss-app-e2e-artifacts` even if a test fails.
- Human checkpoint records the live TUI pytest output and CI run URL in `E5-04-SUMMARY.md`.
</verification>

<success_criteria>
- D-04: manual Linux CI uses `tauri-driver` under `workflow_dispatch`.
- D-06: desktop CI uses fake/local turn seam and no live credentials.
- D-07: phase closeout includes reviewed TUI live proof plus voss-app CI proof.
- D-08: the workflow is not scheduled, not a PR gate, and not a push/release gate.
</success_criteria>

<output>
Create `.planning/phases/E5-tui-voss-app-autonomous-driving/E5-04-SUMMARY.md` when done.
</output>
