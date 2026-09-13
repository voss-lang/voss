# Voss / Voss ADE Repository Split — Execution Plan

**Created:** 2026-09-12
**Branch:** `ade-extraction` (rebase onto `master` @ `c45274b9`, which includes PR #134)
**Status:** Audit complete, decisions locked, work not started
**Input:** "Extract Voss ADE from the Original Voss Repository" brief (12 phases, 13 acceptance criteria), amended 2026-09-12: the app is **archived in-tree**, not deleted
**Related:** `.planning/PROTOCOL.md`, `.planning/adr/`, `docs/sdk.md`, `docs/native-embedding.md`, `docs/ADE-CANVAS-HANDOFF.md`

> Not run through GSD. Each work package below is one PR. A package is done when every DoD box is checked and every verification command has run green on the branch.

---

## 0. Decisions (locked 2026-09-12)

| # | Decision | Value | Why |
|---|---|---|---|
| 1 | PR #134 sequencing | **Resolved.** #134 merged as `c45274b9`. Rebase `ade-extraction` onto it before any work. | Engine-side observe code (`voss/harness/observe/`, observe routes, contracts) is on master. No engine code in #134 references the app; only four docs do. |
| 2 | App disposition | **Archive in-tree at `archive/voss-ade/`.** `apps/voss-app` → `archive/voss-ade/apps/voss-app`, `crates/voss-app-core` → `archive/voss-ade/crates/voss-app-core`. Not a Cargo member, not a pnpm package, not in CI, not imported by anything live. Frozen: not buildable in place (both manifests inherit `*.workspace = true` fields that no longer resolve). | Ben's call 2026-09-12. History stays greppable and cherry-pickable from a path; the live workspace stops knowing it exists. |
| 3 | ADE planning history | **Same archive root:** `archive/voss-ade/planning/` (phase dirs, research, redesign docs, sketches) and `archive/voss-ade/docs/`. One `README.md` at `archive/voss-ade/` explains what, when, why, and that nothing under it is built or tested. | One archive, one index. Keeps `.planning/` for live planning only. |
| 4 | ADR location | **`docs/architecture/0004-voss-ade-repository-split.md`.** Leave `.planning/adr/0001–0003` where they are. | Brief prefers a stable docs path. Moving the observe ADRs is unrelated scope. |
| 5 | Protocol doc location | **`docs/protocol.md`** is authoritative. `.planning/PROTOCOL.md` becomes a 3-line pointer. | One contract. Pointer keeps old links and `events.py` / Go drift-test comments resolvable. |
| 6 | SDK launch resolution order (Rust + TS) | **explicit executable → `VOSS_BIN` env → `voss` on PATH.** Dev-only fallback (`VOSS_PYTHON` + `python -m voss.cli`) behind an explicit `dev` module / cargo feature, never in the default path. | Brief §6. Today both SDKs and the TUI resolve a Python interpreter relative to `CARGO_MANIFEST_DIR` / `PYTHON_BIN`, which is meaningless outside this checkout. |
| 7 | `voss-tui` dedupe scope | **Launch only.** `voss-tui/src/server.rs` → `voss_sdk::Supervisor`. `net.rs` (HttpClient + SSE) stays. | Brief §10: reduce duplication, don't refactor the TUI. |
| 8 | Root `package.json` deps | **Remove `@solidjs/router`, `d3-force`, `chromadb`, `litellm` and the `@xterm/xterm` override.** | Grep on master finds zero importers outside `apps/voss-app`. Re-prove in PR-2 before deleting. The archived app keeps its own `package.json`; nothing installs it. |
| 9 | Codecov `javascript` flag | **Drop the upload.** Add `archive/**` to `codecov.yml` ignore. | Coverage source (`apps/voss-app/coverage/lcov.info`) goes away with the CI step. |

---

## 1. Coupling map (audit result, master @ `c45274b9`)

Search terms from the brief were run repo-wide excluding `node_modules`, `target`, lockfiles, `.voss/sessions`, `graphify-out`, `repomix-output.xml`, SBOM/VEX. Classification drives every edit below.

### 1.1 Build system

| Location | Coupling | Class | Action |
|---|---|---|---|
| `Cargo.toml` members `crates/voss-app-core`, `apps/voss-app/src-tauri` | Workspace membership | APP-SPECIFIC | Remove both members. Add `exclude = ["archive"]` so cargo never treats the archived crates as stray members. `voss-app-core` has exactly one dependent: the Tauri crate, which moves with it. |
| `Cargo.lock` | Tauri/xterm-adjacent crate graph | SHARED BUILD RESIDUE | Regenerates on next `cargo build`. Commit the diff. |
| `pnpm-workspace.yaml` `apps/*` | Only member is `apps/voss-app` | APP-SPECIFIC | Narrow to `sdk/typescript` only. |
| `package.json` deps + `@xterm/xterm` override | Zero importers outside the app | APP-SPECIFIC (prove) | Remove after re-grep. |
| `pnpm-lock.yaml`, `package-lock.json` | Lock residue | SHARED BUILD RESIDUE | Regenerate with `pnpm install`; delete `package-lock.json` if nothing at root uses npm (check `npm/` scripts first). |
| `.gitignore` line 6 `apps/voss-app/coverage/` | Ignore rule | SHARED BUILD RESIDUE | Remove line. |
| `codecov.yml` | No app path | — | Add `archive/**` to `ignore`. |
| `pyproject.toml` (`testpaths = ["tests"]`, ruff targets `voss voss_runtime tests`) | No app path | ENGINE | No edit. The archive contains no Python. |
| `.github/dependabot.yml` | Ecosystems at `/`, `/npm`, `/site` only | ENGINE | No edit. |
| `dist-workspace.toml` | No app references | ENGINE | Keep. |

### 1.2 CI (`.github/workflows/`)

| Workflow | Job / step | Class | Action |
|---|---|---|---|
| `lint.yml` `typescript` | `pnpm -C apps/voss-app exec tsc --noEmit`, `pnpm -C apps/voss-app test:coverage`, codecov upload of app lcov | APP-SPECIFIC | Delete the three app steps. Keep `pnpm install` + `pnpm -C sdk/typescript typecheck`; add `pnpm -C sdk/typescript test`. |
| `lint.yml` `rust`, `rust.yml` `build-test` | "Install Linux desktop dependencies" (webkit2gtk, appindicator, rsvg, xdo) | SHARED BUILD RESIDUE | Delete the apt step once Tauri leaves the workspace. Keep `libssl-dev` only if a remaining crate needs it (reqwest is rustls; expect no). |
| `ci.yml`, `mcp-integration.yml`, `publish-container.yml`, `release.yml` | No app references | ENGINE | Keep unchanged. |

### 1.3 Engine source touching the app

| File | Coupling | Class | Action |
|---|---|---|---|
| `tests/harness/test_coherence_guard.py` | VBUS-08 asserts the file set of `apps/voss-app/src/swarm/` and that `apps/voss-app/package.json` adds no fs-watcher dep | APP-SPECIFIC test in engine | Delete the two app-facing tests. Keep any engine-side assertions. This test **fails** the moment the directory moves. |
| `voss/harness/swarm_agents.py:30` | Comment: "Mirrors MODEL_PRESETS in apps/voss-app/src/agents/modelPrefs.ts" | ENGINE (comment) | Rewrite: the ADE mirrors this table, not the reverse. Engine table stays authoritative. |
| `docs/canvas-perf.md`, `docs/ADE-CANVAS-HANDOFF.md` | App-only docs | APP-SPECIFIC | Move to `archive/voss-ade/docs/`. |
| `docs/shell-integration.md`, `docs/s3-observe-verification.md` | Engine docs (shell init snippets, observe verification) that mention app paths | ENGINE | Keep; repoint app path mentions to `archive/voss-ade/...` or drop them. |
| `voss/harness/server/**` | "sidecar" naming (236 files) | ENGINE | Keep. "Sidecar" is the harness's own name for `voss serve` as a child process. |

### 1.4 SDK and protocol surface

| Location | Finding | Class | Action |
|---|---|---|---|
| `crates/voss-sdk/src/supervisor.rs` | `python_path()`: `VOSS_PYTHON` → `env!("CARGO_MANIFEST_DIR")/../../.venv/bin/python` → `python3`; spawns `python -m voss.cli serve --port 0` | SDK (broken for external use) | Replace with `LaunchOptions` (PR-1). |
| `crates/voss-sdk/src/{client,auth,stream}.rs` | `VossClient::new(base, token)`, `Handshake::from_line`, `event_stream` | PUBLIC CONTRACT | Keep. Already satisfies brief §7 "connect to existing server". |
| `crates/voss-tui/src/server.rs` | Duplicate of `python_path()` + spawn; `voss-tui` does not depend on `voss-sdk` | TUI | Depend on `voss-sdk`, delete the duplicate (PR-1). |
| `crates/voss-tui/src/net.rs` | Own `HttpClient` + SSE | TUI | Keep (decision 7). |
| `sdk/typescript/src/launcher/launcher.ts:39` | `options.python ?? process.env.PYTHON_BIN ?? "python3"` then `-m voss.cli serve` | SDK (same defect) | Same resolution order as Rust (PR-1). |
| `sdk/typescript/src/index.ts` | Exports `VossApiError`, generated types, `client/rest`, `client/sse`, `client/permission`; `./node` exports `VossLauncher` | PUBLIC CONTRACT | Audit only: confirm session/doctor/cost types reach the root export (they come via `generated/types`). |
| `apps/voss-app/src/org/live/sidecarClient.ts`, `attentionQueue.ts` | `../../../../../sdk/typescript/src/client/...` deep imports | APP-SPECIFIC | Move with the app. They will dangle at the new depth; the archive README says so. Do not rewire. |
| `tests/eval/sdk/consumers/ts/package.json`, `go/go.mod` | `file:../../../../../sdk/typescript` and Go replace | SDK eval consumers (legit) | Keep. Whitelist in the final grep. |
| `contracts/*.json` (openapi, events, decision-ledger, outcomes, observe-events) | Committed contract artifacts | PUBLIC CONTRACT | Keep. Gated by `tests/harness/server/test_contract_drift.py`, `sdk/go/internal/drift`, `scripts/check_contracts.py`, TS `codegen`. No app dependency. |
| `.planning/PROTOCOL.md` (189 lines) | Referenced by `voss/harness/server/events.py` docstrings, `sdk/go/internal/drift/drift_test.go`, `docs/native-embedding.md`, `docs/check-native-embedding-refs.sh` | PUBLIC CONTRACT in a planning path | Promote to `docs/protocol.md` (PR-3). |

### 1.5 Historical planning → `archive/voss-ade/planning/`

| Path | Class | Action (PR-3) |
|---|---|---|
| `.planning/phases/A1…A13-voss-app-*` (12 dirs), `999.1-voss-app-agents-launcher`, `999.2-voss-app-pane-resize-keybind` | belongs to ADE | Move |
| `.planning/phases/E5-tui-voss-app-autonomous-driving` | belongs to ADE | Move; note TUI driving stays valid if re-scoped |
| `.planning/phases/V11-ade-org-integration`, `V14-ade-run-cockpit-*`, `V15-live-plane-integration`, `V24-ade-product-revamp-*` | belongs to ADE, with engine-side protocol decisions inside | Extract enduring protocol/SDK decisions into `docs/protocol.md` first, then move |
| `.planning/phases/V13*, V13.1–V13.4` | still relevant to Voss (SDK surfaces) | Keep |
| `.planning/research/voss-ade/` (10 files), `.planning/research/ade-ui-design-contract-research.md` | historically useful | Move |
| `.planning/ADE-REDESIGN.md`, `VOSS-ADE-DEEP-DIVE-JUL19.md`, `VOSS-OBSERVE-IMPLEMENTATION-BRIEF.md`, `CANVAS-OBSERVE-INSTRUCTIONS-PLAN.md` | belongs to ADE (observe engine half is engine; the ADR references the brief's engine sections) | Move |
| `.planning/sketches/`, `.planning/notes/plan-grid-drag-rearrange.md`, `notes/seed-structured-pane-rendering.md` | belongs to ADE | Move |
| `.planning/ROADMAP.md` A-track section (line 1230+, 154 ADE refs), `STATE.md` (43), `PROJECT.md` (7), `REQUIREMENTS.md` (5), `MILESTONES.md` (1) | active roadmap implying Voss owns ADE | Replace A-track section with a pointer paragraph to the ADR; scrub "voss-app is an active track" language |
| `.planning/adr/0001–0003` | observe decisions, engine-side | Keep |
| Root PNGs `voss-ade-desktop.png`, `orchestra-launch-panel.png`, `voss-home-*.png` | zero references outside `.voss/sessions` | If tracked and unreferenced, move to `archive/voss-ade/docs/`; if untracked, leave alone |

### 1.6 Discrepancies between brief and repo

- **README has no ADE content.** It carries a stale line ("A native Rust shell is preserved in `crates/` as a frozen spike") that misdescribes `voss-tui`/`voss-sdk`/`voss-cli`. Fix that line.
- **`docs/architecture/` does not exist.** ADRs live in `.planning/adr/`. Decision 4.
- **Brief's final grep for `../../../../../sdk` always hits `tests/eval/sdk/consumers/`.** Intended SDK consumer fixtures. Whitelist them.
- **`voss-tui` does not depend on `voss-sdk` at all today.**
- **Brief says delete; Ben says archive.** Every "remove" in the brief's §2 becomes "move under `archive/voss-ade/` and detach from every build/CI/test surface".

---

## 2. Work packages

### PR-0 — Rebase (no code)

```
git switch master && git pull --ff-only
git branch -f ade-extraction master && git switch ade-extraction
```
`ade-extraction` has no commits yet, so a force-move is equivalent to a rebase.

### PR-1 — SDK launch contract (`crates/voss-sdk`, `crates/voss-tui`, `sdk/typescript`)

**Tasks**

1. `crates/voss-sdk/src/supervisor.rs`
   - Add `pub struct LaunchOptions { executable: Option<PathBuf>, args: Vec<String>, cwd: Option<PathBuf>, env: Vec<(String, String)>, handshake_timeout: Duration }` with `Default`.
   - Add `pub fn resolve_executable(explicit: Option<&Path>) -> Result<PathBuf, VossError>`: explicit → `VOSS_BIN` → `voss` on PATH. New `VossError::NoExecutable`.
   - `Supervisor::spawn(opts: LaunchOptions)` runs `<exe> serve --port 0`. Keep stdin heartbeat, stderr drain, 60s handshake, `kill_on_drop`.
   - Move the Python path logic to `pub mod dev` behind `#[cfg(feature = "dev-launch")]`, off by default. Only place `VOSS_PYTHON` / `.venv` may appear.
   - Delete free functions `spawn()` and `spawn_with()`; re-point `bad_interpreter_yields_typed_error` at a bad `executable`.
2. `crates/voss-sdk/src/lib.rs` — re-export `LaunchOptions`, `Supervisor`, `VossClient`, `Handshake`, `event_stream`.
3. `crates/voss-tui/Cargo.toml` — add `voss-sdk = { path = "../voss-sdk", features = ["dev-launch"] }`. `src/server.rs` becomes a thin call into `voss_sdk::Supervisor::spawn`; delete its `python_path` copy. `main.rs` keeps `--python` but maps it to `LaunchOptions.executable` only when set, else `dev::python_launch()` only when `VOSS_BIN`/PATH resolution fails.
4. `sdk/typescript/src/launcher/launcher.ts` — `VossLauncherOptions.executable?: string`; resolve explicit → `VOSS_BIN` → `"voss"`. Remove `python` option and `PYTHON_BIN`. Args become `["serve", "--port", "0"]`. Add a `dev` escape hatch only if `tests/eval/test_sdk.py` needs it; check first.
5. `docs/sdk.md` — new section "Launching `voss serve` from a client": resolution order and the two use cases (connect vs supervise) for Rust and TS.

**DoD**
- [ ] `grep -rn "CARGO_MANIFEST_DIR\|\.venv\|PYTHON_BIN" crates/voss-sdk/src crates/voss-tui/src sdk/typescript/src` hits only inside the `dev-launch`-gated module.
- [ ] `voss-tui` has no supervisor code of its own.
- [ ] `docs/sdk.md` documents `LaunchOptions` and `VOSS_BIN`.

**Verify**
```
cargo test -p voss-sdk -p voss-tui -p voss-cli
cargo build -p voss-tui --no-default-features
pnpm -C sdk/typescript typecheck && pnpm -C sdk/typescript test
.venv/bin/python -m pytest tests/eval/test_sdk.py -q
VOSS_BIN=$(pwd)/.venv/bin/voss cargo run -p voss-tui -- --help
```

### PR-2 — Archive the desktop app and detach it from every live surface

**Tasks**

1. `git mv apps/voss-app archive/voss-ade/apps/voss-app` and `git mv crates/voss-app-core archive/voss-ade/crates/voss-app-core`. Remove `apps/` if now empty.
2. `archive/voss-ade/README.md`: frozen at `c45274b9` (last commit that built it in this workspace), what lives here (app, core crate, later: planning + docs from PR-3), why (ADR-0004), and that nothing under `archive/` is built, linted, tested, or installed. State the two known dangling references inside it: `voss-app-core = { path = "../../../crates/voss-app-core" }` in the Tauri manifest (now resolves to `archive/voss-ade/crates/voss-app-core` by accident of layout, but the `*.workspace = true` fields don't) and the `../../../../../sdk` deep imports in `src/org/`. Do not rewire either.
3. Root `Cargo.toml` — drop the two members; add `exclude = ["archive"]`. `cargo build --workspace` to regenerate `Cargo.lock`; commit.
4. Root `package.json` — for each of `@solidjs/router`, `d3-force`, `chromadb`, `litellm`, `@xterm/xterm`: run `grep -rIl "<dep>" --exclude-dir=node_modules --exclude-dir=target --exclude-dir=.planning --exclude-dir=archive .` and paste the (expected empty) result in the PR body. Remove `dependencies` and `pnpm.overrides`. `pnpm-workspace.yaml` → `sdk/typescript` only. `pnpm install` to regenerate the lock. Decide `package-lock.json` (check `npm/` scripts).
5. `.gitignore` — drop `apps/voss-app/coverage/`. `codecov.yml` — add `archive/**` to `ignore`.
6. `.github/workflows/lint.yml` — `typescript` job: remove the three app steps and the codecov upload; add `pnpm -C sdk/typescript test`. `rust` job + `rust.yml`: remove the apt "desktop dependencies" step.
7. `tests/harness/test_coherence_guard.py` — delete the VBUS-08 file-set test and the package.json watcher test.
8. `voss/harness/swarm_agents.py:30` — reword comment.
9. `git mv docs/canvas-perf.md docs/ADE-CANVAS-HANDOFF.md archive/voss-ade/docs/`. Repoint app paths in `docs/shell-integration.md` and `docs/s3-observe-verification.md`.

**DoD**
- [ ] `cargo metadata --no-deps --format-version 1 | jq -r '.packages[].name'` lists no `voss-app-core`, no `voss-app`.
- [ ] `pnpm ls -r --depth -1` lists only the root and `@vosslang/sdk`.
- [ ] Live-tree grep for `apps/voss-app|voss-app-core` returns only `archive/**`, `.planning/**`, and this plan.
- [ ] No workflow installs webkit2gtk / appindicator; no workflow path contains `apps/` or `archive/`.
- [ ] `archive/voss-ade/README.md` exists and names the frozen commit.

**Verify**
```
cargo build --workspace --release && cargo test --workspace --no-fail-fast
cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings
pnpm install --frozen-lockfile && pnpm -C sdk/typescript typecheck && pnpm -C sdk/typescript test
.venv/bin/python -m pytest tests/harness -q -m "not slow"
.venv/bin/python -m pytest tests/harness/server/test_contract_drift.py tests/harness/test_coherence_guard.py -q
cd sdk/go && go test ./...
actionlint .github/workflows/*.yml
grep -rIn --exclude-dir=node_modules --exclude-dir=target --exclude-dir=.git --exclude-dir=.planning --exclude-dir=archive -E "apps/voss-app|voss-app-core|\.\./\.\./\.\./\.\./\.\./sdk" . | grep -v "tests/eval/sdk/consumers"
```
Last command must print nothing.

### PR-3 — Boundary docs, protocol promotion, planning archive

**Tasks**

1. `docs/architecture/0004-voss-ade-repository-split.md` — ADR following the brief's §4: Voss responsibility, ADE responsibility, integration model (`voss serve` + REST + SSE + versioned protocol + SDK), explicit non-goals both directions, the two distinctions (terminal/pane session vs orchestration session; raw CLI process state vs protocol event state), and a "What moved" list pointing at `archive/voss-ade/README.md`.
2. `git mv .planning/PROTOCOL.md docs/protocol.md`. Content unchanged except the title line and a "Status: product contract, version `v=1`" header. New 3-line `.planning/PROTOCOL.md` pointer. Update references: `voss/harness/server/events.py` (docstring lines 4, 26), `sdk/go/internal/drift/drift_test.go:48`, `docs/native-embedding.md`, `docs/check-native-embedding-refs.sh`.
3. Before moving V14/V15/V24, grep their SUMMARY/PLAN files for envelope, event type, or endpoint decisions not already in `docs/protocol.md`; fold them in with a one-line provenance note.
4. `git mv` every path in §1.5 marked Move into `archive/voss-ade/planning/` (preserve subpaths: `phases/`, `research/`, `notes/`, `sketches/`). Extend `archive/voss-ade/README.md` with one line per moved item: original path, "superseded by ADR-0004".
5. `.planning/ROADMAP.md` — replace the A-track section body with: "Desktop ADE is a separate repository as of 2026-09-12. See `docs/architecture/0004-voss-ade-repository-split.md`. Frozen in-tree copy and history: `archive/voss-ade/`." Scrub `STATE.md`, `PROJECT.md`, `REQUIREMENTS.md`, `MILESTONES.md` lines that present `voss-app` as an active Voss track. Keep V-track and BOS-track references to "ADE" only where they describe a protocol consumer.
6. `README.md` — replace the "frozen spike" sentence with a short "What ships" list: Python harness + `.voss` language, `voss` CLI, `voss serve` local API (REST + SSE, `docs/protocol.md`), SDKs (`sdk/typescript`, `sdk/go`, `crates/voss-sdk`), `voss-tui`. One sentence: a separate Voss ADE desktop app integrates through the local protocol; a frozen copy of the original in-repo app lives under `archive/voss-ade/`.
7. `docs/sdk.md` — pointer to `docs/protocol.md` and the ADR.

**DoD**
- [ ] `grep -rn "\.planning/PROTOCOL.md" --exclude-dir=.planning --exclude-dir=node_modules --exclude-dir=target --exclude-dir=archive .` returns nothing outside the pointer file.
- [ ] `ls .planning/phases | grep -E "^(A[0-9]|999|E5|V11|V14|V15|V24)"` returns nothing.
- [ ] `grep -c "voss-app" .planning/ROADMAP.md .planning/STATE.md` is at most the pointer lines.
- [ ] README describes engine, CLI, server, SDK, TUI; mentions ADE once.

**Verify**
```
.venv/bin/python -m pytest tests/harness/server -q
cd sdk/go && go test ./internal/drift/...
bash docs/check-native-embedding-refs.sh
```

---

## 3. Acceptance mapping

| Brief AC | Satisfied by |
|---|---|
| 1, 2 — repo no longer builds/owns the app; app crates out of workspace | PR-2 (archived, excluded, not built) |
| 3 — README/docs describe an engine platform | PR-3 |
| 4 — protocol is a product contract | PR-3 (`docs/protocol.md`) |
| 5 — contract artifacts authoritative and drift-tested | Already true on master; PR-2 verification re-runs the gates |
| 6, 7 — `voss-sdk` usable outside the tree; connect or supervise | PR-1 |
| 8 — `voss-tui` thin first-party client | PR-1 |
| 9 — no monorepo-relative TS SDK imports in live code | PR-2 (app archived); eval consumers whitelisted |
| 10 — app CI gone | PR-2 |
| 11 — planning no longer implies Voss owns ADE | PR-3 |
| 12 — tests/builds pass | Each PR's Verify block |
| 13 — ADE can depend on executable + SDK + protocol only | PR-1 + PR-3; hand the ADE repo: `VOSS_BIN` contract, `docs/protocol.md`, `docs/sdk.md`, contract JSON paths |

---

## 4. Handoff note for the ADE repository (write at the end of PR-3)

- Launch: set `VOSS_BIN` or pass `LaunchOptions.executable`; SDK runs `<exe> serve --port 0`, reads the one-line handshake from stdout, holds stdin open as heartbeat.
- Protocol: `docs/protocol.md`, `v=1`; contracts at `contracts/openapi.json`, `contracts/events.schema.json`, `decision-ledger`, `outcomes`, `observe-events`.
- Rust: `voss-sdk` crate (path or git dep by tag); TypeScript: `@vosslang/sdk` root export + `@vosslang/sdk/node` for `VossLauncher`.
- Source of the original app for porting: `archive/voss-ade/apps/voss-app` and `archive/voss-ade/crates/voss-app-core`, frozen at `c45274b9` (includes S3 canvas/observe app-side work).
- What is NOT provided: PTY, tmux, xterm, canvas, layouts, themes, keymaps, app SQLite. Those never round-trip through Voss.
- `MODEL_PRESETS` in `voss/harness/swarm_agents.py` is authoritative; the ADE's `modelPrefs.ts` must mirror it, not the reverse.

---

## 5. Out of scope (explicit)

- Any change inside the ADE repository.
- Making the archived app buildable in place (rewiring `workspace = true` inheritance or deep SDK imports).
- Replacing `voss-tui/src/net.rs` with `voss-sdk` client types.
- Moving `.planning/adr/0001–0003` to `docs/architecture/`.
- Adding TS SDK coverage to Codecov.
- Updating the SecondBrain wiki pages that still list `apps/voss-app` as an active surface (do via `/save` after PR-3 merges).
