# Roadmap: Voss Harness — v0.1 MVP + v0.2 Coding-Agent Phases + voss-app Desktop ADE

**Created:** 2026-05-10
**Mode:** Harness-led vertical slice → coding-agent expansion → daily-driver gap closure → desktop ADE scaffold
**Granularity:** M-prefixed milestone phases · T-prefixed gap-closure phases · **A-prefixed voss-app phases** (terminal-grid desktop ADE in `apps/voss-app/`) · **O-prefixed ADE-orchestration phases** (Caged Autonomous Eng Team — design in `.planning/ORCHESTRATION-PLAN.md`)
**Requirements covered:** 64 / 64 (v0.1 locked); v0.2 phases M8–M15 + T1–T8 (T-counts locked, M11–M15 TBD by SPEC.md); voss-app phases A1–A10 (counts TBD by SPEC.md)
**Source:** `.vscode/voss_v_0_1_scope_lock.md` (v0.1); `.planning/seeds/` (v0.2 M-phases); `.planning/notes/daily-driver-punch-list.md` (T-phases); `apps/voss-app/CONCEPT.md` + `apps/voss-app/FEATURES.md` (A-phases)
**Last updated:** 2026-05-17 — added O1–O6 ADE-orchestration phases (Caged Autonomous Eng Team); design + decision log in `.planning/ORCHESTRATION-PLAN.md`. | 2026-05-16 — added A1–A10 voss-app Layer-1 phases (terminal-grid scaffold). voss-app is a sibling deliverable to the harness; Layer 2 (Voss integration) and Layer 3 (.voss DSL) lock once L1 ships.

## Phase Order

| Phase | Name | Goal | Requirements | Success Criteria |
|---|---|---|---|---|
| M0 | Scope Lock | Align planning docs around harness-led v0.1 plus `.voss` as workflow control layer | SCOPE-01..04 | 3 |
| M1 | Harness Happy Path | Make the Python harness usable on a real repo with minimal persistence | CLIH-01..10, CTRL-01..09 | 6 |
| M2 | Project Cognition | Make Voss remember useful project facts across sessions | COG-01..08 | 5 |
| M3 | Language Validation | Prove `.voss` is useful for real AI workflow control | LANG-01..10 | 5 |
| M4 | Voss-authored Harness Loop | Dogfood the language on the harness itself | DOG-01..08 | 4 |
| M5 | Eval and Distribution Prep | Measure quality and prepare packaging after the Python loop works | EVAL-01..05 | 4 |
| M6 | npm Wrapper | Publish `voss` as an npm package that vendors Python + the v0.1 wheel | NPM-01..05 | 5 |
| M7 | SDK Polish | Close the four known public-API holes + stabilize provider registration | SDK-01..05 | 5 |
| M8 | Project Memory (MEM-01) | VOSS.md + cross-session recall layer for the harness using Voss runtime memory primitives | MEM-01..07 | 7 |
| M9 | TUI Shell (TUI-01) | Full-screen Textual interface — diff approval, slash palette, live workflow + budget view | TUI-01..10 | TBD |
| M10 | Codebase Intelligence (CAPS-01a) | LSP polyglot + ast-grep + project index — tools, slash, auto-injection, M9 TUI panel | CODE-01..07 | TBD |
| M11 | Voss-aware Tools (CAPS-01b) | Probable-value inspector, budget tracer, `.voss` lint-as-skill, `.voss`→Python diff viewer | VTOOL-01..05 | 5 |
| M12 | MCP Bridge (CAPS-01c, promotes DIST-03) | Consume external MCP tools + expose harness skills as MCP server | MCP-01..0N (TBD by SPEC.md) | TBD |
| M13 | Multi-agent in Chat (CAPS-01d) | Expose runtime `spawn`/`gather` to chat session; render via M9 `SubAgentPanel` | MAG-01..MAG-08 | 8 |
| M14 | Long-running Tasks + Watch (CAPS-01e) | Background job manager, file-watch-driven re-checks, M9 TUI bottom-pane status strip | WATCH-01..0N (TBD by SPEC.md) | TBD |
| M15 | Skill / Plugin Marketplace (CAPS-01f) | Third-party `.voss` skills installable via `voss skill add`; signed manifests + sandbox boundary | SKILL-01..06 | 6 plans, 5 waves |
| T6 | PRD §2.4 Slash Debt (v0.1.1 patch) | Ship the slash commands PRD §2.4 promised in v0.1 (`/diff /apply /discard /budget /resume /why /cost --by-`) | SLASH-01..07 | **Complete** (3/3 plans, 2026-05-18) |
| T1 | Iteration Loop + Streaming + Interrupt | Turn single-shot plan→exec→done into a real while-loop agent with streamed text + cancel | ITER-01..06 | TBD |
| T4 | Prompt Caching + Cost Truthfulness | Cache cognition prefix; honest `/cost` including cache reads | CACHE-01..04 | TBD |
| T2 | Parallel Tools + Multi-Edit | Read-only steps gather; `fs_edit_many` atomic batch | PAR-01..04 | TBD |
| T3 | Network Surface (WebFetch + WebSearch + MCP client) | Live docs + MCP ecosystem, gated at the boundary | NET-01..07 | TBD |
| T5 | Shell Ergonomics | 30KB output, background mode, monitor, signal, `voss jobs` | SHELL-01..05 | TBD |
| T7 | Skills Bootstrap | Ship 6 ready skills paired with M5 eval tasks | SKL-01..06 | TBD |
| T8 | Input Bar Ergonomics | Multi-line, `!cmd`, `#mem`, Ctrl-R, paste-image | INPUT-01..05 | **Complete** (5/5 plans, 2026-05-18) |
| A1 | voss-app Tauri Shell | Tauri + Solid empty window, titlebar + theme tokens, local build only (no release pipeline — deferred to A10) | SHL-01..06 | 4 plans, 4 waves |
| A2 | voss-app PTY Pane | One xterm pane wired to native PTY, full TTY support, scrollback, copy/paste | PTY-01..0N (TBD by SPEC.md) | TBD |
| A3 | voss-app Grid Engine | Binary-split tree, splits/focus/resize/close, `⌘1-9` nav, save/load layout | GRD-01..0N (TBD by SPEC.md) | TBD |
| A4 | voss-app Layout Presets | Fanout/pipeline/swarm/watchers visual templates, `⌘G` cycle, reorder w/o killing panes | LAY-01..0N (TBD by SPEC.md) | TBD |
| A5 | voss-app Project Open | Folder picker, recents, `.voss/` lazy create, git branch read, project-less mode | WS-01..0N (TBD by SPEC.md) | TBD |
| A6 | voss-app Session Persist | Pane tree + cwd + truncated scrollback restore across restart | PER-01..0N (TBD by SPEC.md) | TBD |
| A7 | voss-app Cmd Palette + Keymap | `⌘P`/`⌘⇧P`, VSCode-default profile + tmux additions, custom map via `.voss/keymap.json` | CMD-01..0N (TBD by SPEC.md) | TBD |
| A8 | voss-app Settings + Theme | Two-pane settings UI, JSON-backed, Variant B token system, font/shell config | CFG-01..0N (TBD by SPEC.md) | TBD |
| A9 | voss-app Status Bar | Project · branch · pane count · cost meter stub · notifications bell · click-to-popover | BAR-01..0N (TBD by SPEC.md) | TBD |
| A10 | voss-app Onboarding + Release Pipeline | First-run wizard, empty state, 24hr soak, **+ full release pipeline** (signing, 3 channels, auto-update). v0 SHIP GATE | OBD-01..0N + REL-01..0N (TBD by SPEC.md) | TBD |
| O1 | Session-Tree Substrate + Budget Fan-out | Parent→child session tree; per-card budget envelope; reserved drain budget; hard non-extendable caps (keystone) | OST-01..0N (TBD by SPEC.md) | TBD |
| O2 | `.voss team{}` Spec + Specialist Roster | `team{}` parser → enriched SubagentSpec (model/mode/scope/budget/tools); EM-immutable ceiling/p; backend/frontend/ui/ai roster | OTEAM-01..0N (TBD by SPEC.md) | TBD |
| O3 | Board State Machine + Gated Transitions | Columns, per-column WIP, gate predicates, →Done double gate, critic-loop ceiling+budget, timeout→Blocked | OBRD-01..0N (TBD by SPEC.md) | TBD |
| O4 | Reviewer A/B Split | Reviewer-A (idea→bar + tests/eval, `voss/eval/` reuse); Reviewer-B (independent tiered judge: slop/errors/correctness) | ORVW-01..0N (TBD by SPEC.md) | TBD |
| O5 | Engineering Manager Loop | EM full-authority autonomous loop; idea→tickets/AC/DoD; specialist dispatch + routing rationale; kill/re-scope lineage | OEM-01..0N (TBD by SPEC.md) | TBD |
| O6 | Audit Product + Calibration + Liveness | Session-tree review surface; killed-card + routing first-class; calibration telemetry; reserve/timeout; sign-off forcing function | OAUD-01..0N (TBD by SPEC.md) | TBD |

---

## Phase M0: Scope Lock

**Goal:** Align repo and planning docs around harness-led v0.1 plus language control layer.

**Requirements:** SCOPE-01, SCOPE-02, SCOPE-03, SCOPE-04

**Deliverables:**
- `.planning/PROJECT.md` reflects harness-led v0.1.
- `.planning/REQUIREMENTS.md` contains v0.1 harness requirements.
- `.planning/ROADMAP.md` uses M-prefixed phases.
- `.planning/HARNESS-PLAN.md` names the v0.1 direction and defers Rust.

**Success Criteria:**
1. No ambiguity remains between compiler verbs and harness verbs: `voss run` executes `.voss` programs; `voss do` executes natural-language agent tasks.
2. Planning docs clearly state that `.voss` remains central as an AI workflow control language.
3. Rust, MCP bridge, tree-sitter, VSCode marketplace, Linguist upstream, and full telemetry are deferred until the Python harness proves usage.

**Cross-cutting constraints:**
- This phase is planning-only; it should not implement harness behavior.
- Existing phase directories may remain as historical artifacts unless explicitly archived.
- `.vscode/voss_v_0_1_scope_lock.md` is the source of truth.

---

## Phase M1: Harness Happy Path

**Goal:** Make the harness usable on a real repo with minimal persistence.

**Requirements:** CLIH-01..10, CTRL-01..09

**Required commands:**

```bash
voss doctor
voss do "summarize this repo"
voss do "summarize this diff"
voss edit <file>
```

**Capabilities:**
- Provider auth works.
- `fs_*`, `git_*`, `shell_run`, and `voss_check` tools work.
- Permission modes `plan`, `edit`, and `auto` are available.
- Path jail rooted at `--cwd` is enforced.
- Status rendering and tool traces work.
- Basic session snapshot works without storing provider secrets.

**Success Criteria:**
1. `voss` and `voss chat` launch the interactive harness REPL.
2. `voss do "<task>"` runs one natural-language task and exits cleanly.
3. `voss edit <path>` constrains edits to the requested scope unless the user approves broader access.
4. `voss doctor` reports provider/config/tooling setup.
5. Risky filesystem or shell operations require permission prompts with deny, allow once, and allow always choices.
6. `voss run <file.voss>` remains a compiler command and is not overloaded for agent tasks.

**Cross-cutting constraints:**
- Harness can remain Python-authored in M1.
- Compiler commands remain available.
- No provider API keys or equivalent secrets may be written into session payloads.

**Plans:** 7 plans

Plans:
- [ ] M1-01-PLAN.md — Permission tiers + tool descriptors (is_mutating, mode_allows)
- [ ] M1-02-PLAN.md — voss doctor check registry + traffic-light table
- [ ] M1-03-PLAN.md — Session redaction guarantee + CI test
- [ ] M1-04-PLAN.md — voss edit scoped REPL + diff preview
- [ ] M1-05-PLAN.md — REPL /login, /model, /mode (+ --confirm) + config.toml
- [ ] M1-06-PLAN.md — voss tools + voss config commands
- [ ] M1-07-PLAN.md — Per-command mode defaults + happy-path integration + voss run guard

---

## Phase M2: Project Cognition

**Goal:** Make Voss remember useful project facts.

**Requirements:** COG-01..08

**Required commands:**

```bash
voss do "analyze this repo"
voss resume
voss sessions
```

**Project outputs:**
- `.voss/project.json`
- `.voss/architecture.md`
- `.voss/constraints.yml`
- `.voss/permissions.yml`
- `.voss/validation.yml`
- `.voss/plans/`
- `.voss/sessions/`
- `.voss/decisions/`
- `.voss-cache/repo.idx` or a simpler rebuildable file index

**Success Criteria:**
1. Repo analysis creates or updates `.voss/architecture.md`.
2. Agent plans are saved under `.voss/plans/`.
3. Sessions can be listed and resumed.
4. Decisions and validation commands are inspectable under `.voss/`.
5. Repeated sessions improve from stored project context rather than starting from zero.

**Cross-cutting constraints:**
- `.voss/` is durable project knowledge.
- `.voss-cache/` is rebuildable machine state.
- Stored memory must distinguish inspected, changed, and explicitly avoided files.

**Plans:** 7 plans

Plans:
- [ ] M2-00-PLAN.md — Wave 0 test scaffold + pyyaml dep + shared git_repo fixture
- [ ] M2-01-PLAN.md — cognition.py load+drift+repo.idx + strict pydantic YAML schemas
- [ ] M2-02-PLAN.md — Per-cwd session storage + RunRecord + RunRecorder mechanical capture
- [ ] M2-03-PLAN.md — RunRecorder wired into run_turn + record_run privileged close + decisions/*.md mirror
- [ ] M2-04-PLAN.md — /analyze slash + natural-language route + bootstrap + repo.idx rebuild + .gitignore writes
- [ ] M2-05-PLAN.md — Cognition auto-injection in run_turn (6k budget) + renderer surfaces + voss resume prior-context
- [ ] M2-06-PLAN.md — Drift hint + voss sessions --all + doctor cognition rows + permissions.yml layering

---

## Phase M3: Language Validation

**Goal:** Prove `.voss` is useful for real AI workflows.

**Requirements:** LANG-01..10

**Required commands:**

```bash
voss check samples/classify.voss
voss check samples/support.voss
voss check samples/research.voss
voss run samples/classify.voss
```

**Capabilities:**
- Parser supports representative AI workflow syntax.
- Analyzer catches unguarded `probable<T>` usage.
- Codegen emits readable Python.
- Runtime examples pass.
- Language demo shows shorter, clearer workflow code than equivalent Python boilerplate.

**Success Criteria:**
1. Three meaningful `.voss` examples pass `voss check`.
2. At least one representative `.voss` example runs end-to-end.
3. Generated Python is understandable and imports `voss_runtime`.
4. Confidence gates, context budgets, semantic routing, tools, memory, agents, and fallbacks remain first-class.
5. Docs and sample framing describe `.voss` as AI workflow control, not a Python replacement.

**Cross-cutting constraints:**
- Do not chase full Python syntax parity.
- Default verification should stay hermetic with stub providers/fake indexes where possible.
- `voss check` should be fast enough to run after edits.

**Plans:** 6 plans

Plans:
- [ ] M3-01-PLAN.md — Analyzer D-03 static-only check guard + sentinel test
- [ ] M3-02-PLAN.md — Auto-StubProvider fallback + stderr banner + hermetic env propagation
- [ ] M3-03-PLAN.md — D-07 coverage fixtures for memory.semantic + memory.working (parser/analyzer/codegen)
- [ ] M3-04-PLAN.md — Sample extensions (support memory.episodic; research try/catch + use) + raw_python parity + D-14 headers
- [ ] M3-05-PLAN.md — tests/examples repoint to samples/ + slim legacy + extend support/research e2e for raw-parity
- [ ] M3-06-PLAN.md — D-13 per-sample speed gate + README "What is .voss" + docs/voss-vs-python.md

---

## Phase M4: Voss-authored Harness Loop

**Goal:** Dogfood the language on the harness itself.

**Requirements:** DOG-01..08

**Required command:**

```bash
voss check voss/harness/agent/
```

**Target files:**

```text
voss/harness/agent/
├── loop.voss
├── router.voss
├── planner.voss
├── executor.voss
└── reviewer.voss
```

**Success Criteria:**
1. `voss/harness/agent/*.voss` exists and models the harness loop.
2. `voss check voss/harness/agent/` passes in CI.
3. Compiled harness artifacts cache under `.voss-cache/harness/`.
4. Bare `voss` can boot through compiled harness logic once the dogfood loop is enabled.

**Cross-cutting constraints:**
- This should not block the earliest Python harness MVP.
- Harness self-hosting should expose language regressions quickly.
- Python fallback may remain until the compiled harness path is proven.

**Plans:** 5 plans

Plans:
- [x] M4-01-PLAN.md — Wave 0 compiler sub-plan: grammar `use ... as` + codegen auto-await for use-imported callees
- [x] M4-02-PLAN.md — Wave 1 CLI dir-walk + cache infra: sandbox.write_cache, cache.py manifest, StaleHarnessCacheError, voss check/compile <dir>
- [x] M4-03-PLAN.md — Wave 2 `.voss` authoring + boot dispatch: 5 .voss files, _run_step_loop extraction, ToolEntry.invoke_dict, _resolve_run_turn
- [x] M4-04-PLAN.md — Wave 3 parity test + DOG-07 smoke: session-scoped pre-compile fixture, FakeProvider parity, subprocess smoke
- [x] M4-05-PLAN.md — Wave 4 CI gate + docs: voss check CI step, README eager-compile one-liner, doctor harness-cache row

---

## Phase M5: Eval and Distribution Prep

**Goal:** Measure quality and prepare shipping.

**Requirements:** EVAL-01..05

**Capabilities:**
- Golden repo tasks for the canonical demo workflow.
- Success rate tracking.
- Mean cost tracking.
- Confidence correlation tracking.
- Package install polish.

**Success Criteria:**
1. Golden tasks cover repo analysis, plan-only change, approved edit, validation, and resume.
2. Eval output records success rate, mean cost, and confidence correlation.
3. Packaging smoke verifies the Python harness and compiler commands install together.
4. Rust/Homebrew work remains deferred unless the Python harness proves real usage.

**Cross-cutting constraints:**
- Full telemetry is deferred; keep v0.1 eval practical and local-first.
- Distribution work should not pull focus from harness behavior.
- Any public-facing docs should reflect the harness-first positioning.

**Plans:** 6 plans

Plans:
- [ ] M5-01-PLAN.md — Wave 0 suite loader + TaskSpec pydantic + fixture isolation helper
- [ ] M5-02-PLAN.md — Wave 1 Verdict + judge_run + auth.resolve role kwarg
- [ ] M5-03-PLAN.md — Wave 2 voss eval CLI + runner + JSONL writer
- [ ] M5-04-PLAN.md — Wave 3 summary.md + stdlib Pearson + .voss/.gitignore guard
- [ ] M5-05-PLAN.md — Wave 4 five golden task fixtures (01-analyze..05-resume)
- [x] M5-06-PLAN.md — Wave 5 wheel-in-tempvenv smoke + README install polish

---

## Phase M6: npm Wrapper

**Goal:** Publish `voss` as an npm package that vendors a pinned Python interpreter + the v0.1 wheel so JS-ecosystem developers can `npm i -g voss` (or `npx voss`) and run the harness without managing Python themselves.

**Requirements:** NPM-01..05

**Required commands (post-install):**

```bash
npx voss --help
npx voss doctor
npx voss check <file-or-dir>
npx voss compile <file>
npx voss do "<task>"
```

**Capabilities:**
- npm package named `voss` (or `@voss/cli`) — naming locked during M6 discuss.
- Bundled-Python distribution pattern (mirrors pyright). Per-platform Python interpreter vendored via postinstall download OR per-platform optionalDependencies subpackages.
- Supported platforms in v0.1: darwin-arm64, darwin-x64, linux-x64, linux-arm64, win32-x64.
- Node-side `bin/voss.js` shim forwards all argv to the vendored `python -m voss.cli` with full exit-code, stdio, and signal passthrough.
- v0.1 wheel from M5 is the source of truth — npm package vendors the same wheel; no parallel implementation.
- Smoke test in a fresh Node project verifies the post-install command surface (see "Required commands").

**Success Criteria:**
1. `npm i -g voss` installs the CLI on at least the five supported platforms.
2. `npx voss --help`, `npx voss doctor`, `npx voss check <sample>`, and `npx voss compile <sample>` all exit 0 immediately after install in a fresh Node project, with no manual Python setup.
3. `voss` bin shim is signal-safe (Ctrl-C interrupts the underlying Python process) and exit-code-faithful.
4. README primary install path is `npm i -g voss`; `pip install voss` is listed as the secondary path.
5. npm package version tracks the Python wheel version 1:1 — publishing `voss@0.1.0` requires `voss==0.1.0` on PyPI (or vendored at the same git tag).

**Cross-cutting constraints:**
- This is distribution work, NOT reimplementation. Python code under `voss/`, `voss_runtime/`, and `voss/harness/` is unchanged by M6.
- DIST-01 (Rust harness shell) stays deferred — M6 buys npm distribution without it. If startup latency under bundled-Python proves painful in M6 dogfood, that's the signal to revisit DIST-01.
- M5 wheel smoke is a prerequisite — M6 vendors the same wheel M5 verifies.
- Windows support enters v0.1 ONLY through npm (REQUIREMENTS "Out of Scope" lists Windows defer for core, but npm wrapper inherits cross-platform Node assumptions). If win32 vendoring proves expensive, drop to mac+linux in v0.1 and document.
- npm publish credentials and `@voss` org reservation happen during M6 — not before.
- No JS reimplementation of the harness, compiler, or runtime in M6. Pure wrapper.

**Plans:** 5 plans

Plans:
- [ ] M6-01-PLAN.md — Wave 1 npm name reservation (@voss org + 6 placeholders at 0.0.0) + delete cargo-dist release.yml + freeze rust.yml + scaffold npm/ directory tree
- [ ] M6-02-PLAN.md — Wave 2 Node bin shim (npm/bin/voss.js) per Biome pattern + per-platform package.json amendments + fast pytest pinning shim invariants
- [ ] M6-03-PLAN.md — Wave 2 build scripts (prune_pbs.py, build_platform.py, bump_version.py) + pbs_manifest.json + unit tests + [BLOCKING] host-platform size-budget verification before M6-04 fan-out
- [ ] M6-04-PLAN.md — Wave 3 release.yml (5-platform GHA matrix + npm publish) + ci.yml version-sync gate + 0.1.0 version bump + [BLOCKING] test-tag exercise of the workflow
- [ ] M6-05-PLAN.md — Wave 4 NPM-04 packaging smoke (tests/packaging/test_npm_install.py) + README.md npm-primary install (NPM-05) + test_readme.py invariants + [BLOCKING] final v0.1.0 release approval

---

## Phase M7: SDK Polish

**Goal:** Close the four known public-API holes documented in `docs/sdk.md` (Known gaps) plus stabilize the provider-registration entry point so third-party embedders and providers can use Voss without reaching into private modules.

**Requirements:** SDK-01..05

**Required surface (post-phase):**

```python
# voss.harness public additions
from voss.harness import (
    Renderer,                    # SDK-01: protocol
    NullRenderer,                # SDK-01: silent default
    tool_entry_from_callable,    # SDK-02: factory
    SessionView,                 # SDK-03: read-only embedder view
)

# voss_runtime public additions
from voss_runtime import (
    RuntimeConfig,               # gains .from_toml(path) and .default() — SDK-04
)
from voss_runtime.providers import register as register_provider  # SDK-05
```

**Capabilities:**
- Embedders can author silent or custom rendering without importing from `voss.harness.render`.
- Embedders can wrap a plain Python callable as a `ToolEntry` with a single factory call — no manual descriptor authoring.
- Embedders can introspect sessions (id, cwd, per-run timestamps/cost/confidence) via a stable read-only view without binding to the on-disk `SessionRecord`/`RunRecord` schema.
- Embedders can load harness config from `~/.config/voss/config.toml` (or a custom path) and overlay env overrides in one call.
- Third-party providers can be registered via a public, documented entry point.

**Success Criteria:**
1. Each new public name appears in the relevant package `__all__` AND in `tests/packaging/test_public_api.py` EXPECTED_*_PUBLIC_API set.
2. `docs/sdk.md` "Known gaps" list shrinks by exactly the five items shipped (SDK-01..05). No private-path workaround examples remain for those five.
3. A new test file exercises the embedding surface end-to-end: build a fake tool from a callable, drive a turn with `NullRenderer`, introspect resulting session via `SessionView`, configure via `RuntimeConfig.from_toml`, register a custom provider — all from `voss.harness.__all__` / `voss_runtime.__all__` symbols only.
4. The on-disk `SessionRecord`/`RunRecord` schemas remain private (not promoted by accident).
5. Stability docstrings updated on `voss.harness/__init__.py` and `voss_runtime/__init__.py` to reflect the expanded public surface.

**Cross-cutting constraints:**
- M7 promotes existing internals; it does not invent new behavior. If a feature isn't shippable as a pure rename + re-export + docstring + test, it doesn't belong in M7.
- No new private surface introduced as a side effect. Every helper added must be either covered by `__all__` or marked `_private` from day one.
- Pre-1.0 versioning carve-out (docs/sdk.md §Versioning) allows shipping M7 in a 0.x minor release without a major bump.
- Ordering: M7 ideally lands BEFORE the first `voss==0.1.0` PyPI publish + `voss@0.1.0` npm publish so the public surface stabilizes before any external caller pins it. If M6 ships first, M7 lands as `0.1.1` and `docs/sdk.md` "Versioning" rules still hold (minor pre-1.0 may break; this would be a minor bump). Plan against both orderings.
- TS/JS SDK, HTTP/remote SDK, formal plug-in framework with entry-points and sandboxing remain explicitly OUT of M7 — those are independent v0.2+ candidates with their own triggers.

---

## Phase M8: Project Memory (MEM-01)

**Goal:** Give the Voss harness a persistent project-memory layer so it stops re-learning the repo every session. Two tiers: a human-curated `VOSS.md` (analog to `CLAUDE.md`) and an agent-curated cross-session recall store built on Voss's own runtime memory primitives (`memory.episodic`, `memory.semantic`).

**Requirements:** MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, MEM-06, MEM-07

**Seed source:** [`seeds/project-memory-voss-md.md`](seeds/project-memory-voss-md.md)
**Thesis context:** [`notes/voss-agent-unfair-advantage.md`](notes/voss-agent-unfair-advantage.md)

**Headline deliverables (subject to SPEC.md refinement):**
- `VOSS.md` loader — read at session start, inject into harness system context. Section conventions (project, build, style, do/don't). Hierarchical resolution (root + per-directory) decided in SPEC.
- Cross-session recall store under `.voss/memory/` — episodic + semantic, file-backed, indexed. Reuses runtime memory primitives.
- Slash command surfaces (`/recall <query>`, `/forget`) — minimal CLI form for v0.1; richer surface lands with [[tui-shell-textual]] (M9).
- End-of-session prompt: agent extracts candidate decisions/conventions from the turn history; user picks what to persist.
- Privacy-first defaults — nothing leaves the repo; no cloud sync in this phase.

**Cross-cutting constraints:**
- Must run with the existing v0.1 harness surface (`voss chat`, `voss resume`, `voss sessions`). No TUI dependency.
- Reuse runtime memory primitives — do not build a parallel store. Phase doubles as proof that `memory.*` earns its keep.
- Hard cap memory store size + provide a vacuum/forget path before shipping.
- Integration with `voss sessions` / `voss resume` (CLIH-05/06/07) must remain backwards compatible — existing session files must continue to load.

**Success Criteria:** TBD by `08-SPEC.md`. Spec-phase will produce pass/fail acceptance checkboxes.

**Out of scope (this phase):**
- Cross-project memory sharing.
- Cloud-backed memory store.
- TUI surfaces for browsing memory (lands in M9).
- Multi-agent memory partitioning (lands in M10).

**Plans:** 7 plans

Plans:
- [ ] M8-00-PLAN.md — Wave 0 scaffold: /save -> /save-session rename, portalocker dep, 4 module skeletons (voss_md/memory_store/conventions/memory_cli), 13 test stubs + conftest fixtures, Req 7 grep-gate test live from day one
- [ ] M8-01-PLAN.md — MEM-01 VOSS.md loader (parse/read_and_inject/read_fence_body/write_fence_body/HashMismatch) + system-context injection in _run_repl + do_cmd + run_turn sys_prompt
- [ ] M8-02-PLAN.md — MEM-02 architecture.md→VOSS.md byte-identical migration + cognition._load_arch read-path rewire + skills/analyze.py write-path rewire (Pitfall 2 closed)
- [ ] M8-03-PLAN.md — MEM-03 + MEM-07 MemoryStore (bind/recall/forget/write_turn/write_ledger/write_note/write_convention/summary) + chroma lazy init + keyword fallback + portalocker per-source locking + 80%/60% hit-rate eval + grep-gate runtime-reuse mock
- [ ] M8-04-PLAN.md — MEM-04 conventions extraction (has_signal D-09 + Pitfall 5 quorum / extract_conventions D-10 strict-JSON / review_candidates D-11 / run_on_clean_exit D-12 8s timeout + config.yml toggle)
- [ ] M8-05-PLAN.md — MEM-05 4 slash commands wired (/recall, /forget --yes gate, /memory, /save manual note + Pitfall 1 regression test) + ctx.memory_store boot binding
- [ ] M8-06-PLAN.md — MEM-06 _maybe_evict per-source quotas D-14/D-16 + MemoryStore.vacuum + voss memory vacuum/adopt/size CLI subcommand group + memory_group registration in AGENT_COMMANDS + voss_md.write_fence_body adopt=True

---

## Phase M9: TUI Shell (TUI-01)

**Goal:** Replace the current `rich`-based line-streamed CLI for `voss chat` / `voss do` with a full-screen TUI (Textual or equivalent). Match Claude Code / Aider interaction depth and expose Voss's language primitives — probable values, budgets, spawn/gather — directly in the UI.

**Requirements:** TUI-01, TUI-02, TUI-03, TUI-04, TUI-05, TUI-06, TUI-07, TUI-08, TUI-09, TUI-10

**Seed source:** [`seeds/tui-shell-textual.md`](seeds/tui-shell-textual.md)

**Headline deliverables (subject to SPEC.md refinement):**
- Textual app shell — header (session id, budget remaining), main turn-history pane, input bar with slash-command palette + autocomplete, modal pane for diff approval + permission prompts.
- Per-hunk diff approval — user accept/reject individual hunks instead of blind apply.
- Live workflow visualization — probable-value confidence bars, `ctx(budget:)` token meter, `spawn`/`gather` sub-agent panels rendered from the recorder stream (`voss/harness/recorder.py`).
- Session resume UX — scroll prior turns, fork from any turn, branch sessions.
- Keybindings — vim-ish navigation, `/` slash palette, `?` help overlay.
- `--plain` flag — preserve current line mode for pipes / CI.

**Cross-cutting constraints:**
- Library choice (Textual vs prompt_toolkit vs hand-rolled) gated by SPEC.md and discuss-phase.
- Must work over the M6 npm wrapper's vendored Python on macOS, Linux, and Windows console.
- Must not regress headless (`--plain`) CLI exit codes, stdout shape, or pipe behavior.
- M8 memory surfaces (`/recall`, memory browser) plug into TUI panels — TUI-01 reserves UI hooks but does not require M8 to ship.

**Success Criteria:** TBD by `09-SPEC.md`.

**Out of scope (this phase):**
- Editor / VSCode integration (EDIT-01/02 track).
- Web UI.
- New runtime hooks — TUI reads from the existing recorder. If hooks need extending, that lands in a follow-up phase.

**Plans:** 7 plans

Plans:
- [ ] M9-01-PLAN.md — Library-choice gate + Textual dep + --plain plumbing + pre-M9 stdout byte baseline (idempotent, locked FakeProvider)
- [ ] M9-02-PLAN.md — Textual app shell (region grid) + TextualRenderer (Renderer-protocol) + locked glyph + locked color stylesheet + ConfidenceBar (16-cell locked) / BudgetMeter (em-dash on zero-total) widgets
- [ ] M9-03-PLAN.md — SlashPalette + HelpOverlay + KEYMAP table + reserved slash names for M8 (4 names: /recall, /forget, /memory, /save) + live `/save` → `/snapshot` rename with deprecation alias
- [ ] M9-04-PLAN.md — Live workflow visualization: SubAgentPanel + RecorderBridge (read-only) + SPAWN_TOOL_NAME constant + runtime-surface hash baseline regression test (4 files)
- [ ] M9-05-PLAN.md — DiffModal (per-hunk) + PermissionModal + BudgetExhaustedModal + permissions_bridge (injects modal-driven prompt_fn)
- [ ] M9-06-PLAN.md — Fork-from-turn data model + backward-compat session schema (additive optional parent_id, parent_turn_index) + ForkConfirmModal + action_fork_turn handler
- [ ] M9-07-PLAN.md — cli.py default-path flip to TextualRenderer + install_tui_permissions wire-up + accent allow-list audit + --no-unicode flag/env + Windows console strategy + phase-final human-verify checkpoint

---

## Phase M10: Codebase Intelligence (CAPS-01a)

**Goal:** Add a codebase-intelligence layer to the Voss harness — polyglot LSP-backed semantic operations + ast-grep-backed structural pattern search, exposed via harness tools, slash commands, system-context auto-injection, and an M9 TUI side panel. Originally the CAPS-01 seed bundled six capabilities; M10 SPEC scope-cut to codebase intel only. The other five capabilities are formal follow-on phases M11–M15.

**Requirements:** CODE-01..07 (minted in `M10-SPEC.md`).

**Seed source:** [`seeds/agent-capability-surface.md`](seeds/agent-capability-surface.md)
**SPEC:** [`phases/M10-agent-capability-surface-caps-01/M10-SPEC.md`](phases/M10-agent-capability-surface-caps-01/M10-SPEC.md)
**Thesis context:** [`notes/voss-agent-unfair-advantage.md`](notes/voss-agent-unfair-advantage.md)

**Headline deliverables (locked in SPEC):**
- Project index — session-start scan + on-demand refresh, persisted under `.voss-cache/code/`. No file-watch (deferred to M14).
- LSP client + server registry (Python via pyright, JS/TS via typescript-language-server, Rust via rust-analyzer, Go via gopls). Config-driven through `.voss/lsp.yml`.
- ast-grep / tree-sitter structural-search backend with regex fallback when ast-grep absent.
- Four new harness tools: `code_search`, `find_definition`, `find_references`, `code_refresh`.
- Three new slash commands: `/symbol`, `/refs`, `/refresh`.
- Auto-injection: `## Project Index` section in system context (≤ 1500 tokens).
- M9 TUI amendment: `CodeIntelPanel` widget reserving the side region (mode-shares with `SubAgentPanel`).

**Cross-cutting constraints:**
- M9 amendment (Req 7) MUST land + pass plan-checker BEFORE M10 execute. Schedule as `M9-08-PLAN.md` or amendment to `M9-02`.
- ast-grep is a soft dependency via `voss[code]` extra. Tools must function without it via regex fallback.
- LSP servers lazy-launched, reaped on session exit. No orphan processes.
- Session-start scan latency budget: ≤ 5s @ 10K LoC; ≤ 30s @ 100K LoC (partial-index warning beyond).
- Index storage under `.voss-cache/` (rebuildable), not `.voss/` (durable) — matches M2 COG-07.

**Success Criteria:** 17 pass/fail criteria locked in `M10-SPEC.md`.

**Out of scope:** Voss-aware tools (M11), MCP bridge (M12 — promotes DIST-03), multi-agent in chat (M13), long-running/watch tasks (M14), skill marketplace (M15). File-watch-driven refresh, cross-repo search, LSP completion/hover/diagnostics, languages beyond the four headline servers.

---

## Phase M11: Voss-aware Tools (CAPS-01b)

**Goal:** Build the Voss-language-aware tooling that turns the harness's own runtime primitives into visible product surfaces — probable-value inspector, budget tracer, `.voss` lint-as-skill, `.voss` → Python diff viewer. This is the "unfair advantage" axis per [`notes/voss-agent-unfair-advantage.md`](notes/voss-agent-unfair-advantage.md): every feature exposes a runtime primitive to the user.

**Requirements:** VTOOL-01..05 — locked by `M11-CONTEXT.md` + `M11-VALIDATION.md` (no separate SPEC; user declined SPEC during discuss-phase).

**Seed source:** [`seeds/agent-capability-surface.md`](seeds/agent-capability-surface.md) (capability 2)
**Thesis context:** [`notes/voss-agent-unfair-advantage.md`](notes/voss-agent-unfair-advantage.md) (the primary "why" for this phase)

**Headline deliverables:**
- `.voss` lint/type-check exposed as a first-class agent skill (callable from `.voss` workflows, not just `voss check`).
- Probable-value inspector — show confidence + propagation graph for a chosen value at a recorded runtime point.
- Budget tracer — visualize `ctx(budget:)` token consumption across a workflow run, frame-by-frame.
- `.voss` → Python diff viewer — when the agent edits a `.voss` file, user sees both sides synchronized.
- M9 TUI panels for each (render in main pane or modal — M9 region grid permitting).

**Planning note (2026-05-18):** `M11-CONTEXT.md` constrains the roadmap wording to existing recorded data only: "propagation graph" ships as a confidence-annotated decision sequence from `RunRecord.decisions[]`, and "frame-by-frame budget" ships as a per-agent-iteration token timeline from `RunRecord.iterations[]`. True lineage DAGs and per-`ctx(budget:)` frames require new emit points and are out of M11.

**Cross-cutting constraints:**
- Depends on M9 TUI shell for visual surfaces; can ship CLI-only first if M9 incomplete.
- Reuses `voss_runtime/{probable,budget,agent}.py` read-only (M9-baselined; no new emit points).
- Pairs with M4 dogfood compound — inspectors must work on the harness's OWN `.voss` workflows.

**Success Criteria:**
1. `voss-lint-as-skill` remains first-class reachable and M11 consumes its frozen version-1 JSON schema unchanged.
2. Probable inspector is available through CLI, slash, tool, and read-only TUI modal surfaces using recorded decisions only.
3. Budget tracer is available through CLI, slash, tool, and read-only TUI modal surfaces using recorded iterations only.
4. `voss vdiff voss/harness/agent/planner.voss` shows `.voss` source beside generated Python without source-map claims.
5. No changes land in `voss/harness/recorder.py` or `voss_runtime/{probable,budget,agent}.py`; all M11 tools are `is_mutating=False`.

**Plans:** 5 plans across 5 waves

Plans:
- [ ] M11-01-recorded-data-inspect-core-PLAN.md — Recorded decision sequence + budget timeline core helpers and tests.
- [ ] M11-02-probable-budget-surfaces-PLAN.md — Read-only tools, `voss inspect probable/budget`, `/probable`, `/btrace`.
- [ ] M11-03-lint-schema-integration-PLAN.md — Consume and verify T7 SKL-06 frozen JSON schema.
- [ ] M11-04-voss-python-diff-PLAN.md — `voss vdiff`, `/vdiff`, and `voss_py_diff` over source-vs-generated Python.
- [ ] M11-05-tui-and-final-guards-PLAN.md — Read-only TUI modals and phase-level no-emit acceptance guards.

**Out of scope:** Languages other than `.voss` (Python ecosystem handled by M10). Editor extensions (separate EDIT track). Live-replay debugger.

---

## Phase M12: MCP Bridge (CAPS-01c, promotes DIST-03)

**Goal:** Bridge Voss into the Model Context Protocol ecosystem — consume external MCP tools as harness tools, and expose harness skills as an MCP server so other agent runtimes can invoke Voss capabilities. Promotes the existing v0.2 candidate **DIST-03**.

**Requirements:** MCP-01..0N — TBD by `M12-SPEC.md`.

**Seed source:** [`seeds/agent-capability-surface.md`](seeds/agent-capability-surface.md) (capability 3)
**Original candidate:** DIST-03 (see "Coding-agent v0.2 phases" section below; DIST-03 retired in favor of this formal phase).

**Headline deliverables (to be refined in SPEC):**
- MCP client — speak MCP over stdio + HTTP, surface remote tools through `voss/harness/tools.py` registry.
- MCP server mode — expose a curated subset of harness tools (`code_search`, `fs_read`, `voss_check`, etc.) as MCP endpoints for external clients.
- `.voss/mcp.yml` config — declare client connections + server-exposed surface.
- Permission scope — MCP tools default to `plan` mode (read-only); upgrade to `edit`/`auto` requires explicit user opt-in per server.

**Cross-cutting constraints:**
- Lazy connect — MCP servers connected on first tool invocation, not session start.
- Token/permission isolation — MCP tools execute in their own permission scope; never inherit unrestricted access.
- Audit trail — every MCP invocation logged through M2 RunRecorder.

**Success Criteria:** TBD by `M12-SPEC.md`.

**Out of scope:** MCP UI for browsing remote tool catalogs (could be M9 TUI panel follow-up). Cross-org MCP service registry. Encrypted MCP transports beyond what the protocol mandates.

---

## Phase M13: Multi-agent in Chat (CAPS-01d)

**Goal:** Expose the runtime `spawn`/`gather` primitives (`voss_runtime/agent.py`) to the user-facing chat session. A `voss chat` user can say "research X" → harness spawns sub-agent in a side panel (M9 `SubAgentPanel`), each sub-agent has its own budget meter, message bus is visible in the TUI.

**Requirements:** MAG-01..MAG-08 (locked by `M13-SPEC.md`).

**Plans:** 6 plans across 5 waves (W0→W1→W2[2 parallel]→W3→W4)

Plans:
- [ ] M13-01-PLAN.md — Wave 0 red scaffolds: shared scripted multi-agent provider conftest fixture + 5 new test files (fanout/steer/recursion/reveal/e2e) + additive keymap-baseline rows; back-compat guard
- [ ] M13-02-PLAN.md — `voss/harness/multiagent.py` foundation: `M13Allocator` (asyncio.Lock check-and-allocate, exactly-once release, viable-floor denial) + `ChildHandle` + `ChildRegistry`; resolves RESEARCH OQ-A1 (reserve/floor defaults)
- [ ] M13-03-PLAN.md — Wave 2A harness fan-out: non-blocking spawn/steer/status/gather tools + `PanelBridgeRenderer` + additive `steer_inbox` kwarg & line-830 drain in `agent.py`
- [ ] M13-04-PLAN.md — Wave 2B TUI bridge + reveal: wire dead `renderer.py:203` seam, `action_toggle_subagent_detail`, quiet-by-default panel body, `ctrl+o` keymap row
- [ ] M13-05-PLAN.md — Wave 3 recursion: slice-scoped sub-allocator handed to child toolset; depth>1 nested budget + nested panels (no depth constant)
- [ ] M13-06-PLAN.md — Wave 4 chat integration: additive `attach_multiagent_tools` in `cli.py` + headline stub-provider `voss chat` e2e

**Seed source:** [`seeds/agent-capability-surface.md`](seeds/agent-capability-surface.md) (capability 4)
**Existing infra:** `voss/harness/subagents.py` (SubagentSpec/Registry, `attach_subagent_tool`); `voss_runtime/agent.py` (`VossAgent.spawn`, `AgentHandle`, `gather`).

**Headline deliverables (to be refined in SPEC):**
- Sub-agent invocation surface in `voss chat` — slash command + natural-language route.
- M9 `SubAgentPanel` populated by live sub-agent state — running, budget remaining, latest tool call, exit status.
- Cross-agent message bus visible in TUI.
- Budget partitioning — parent agent's `ctx(budget:)` budget split across spawned children, accounted in real time.

**Cross-cutting constraints:**
- Depends on M9 `SubAgentPanel` region (already in M9 plans).
- Compounds with M4 dogfood — the harness's own `.voss` workflows already use spawn/gather; this phase exposes that capability to USER `.voss` workflows + chat-initiated tasks.

**Success Criteria:** TBD by `M13-SPEC.md`.

**Out of scope:** Cross-machine distributed agents (deferred well beyond v0.2). Agent-to-agent direct messaging without harness mediation. Multi-agent memory partitioning beyond per-agent budgets.

---

## Phase M14: Long-running Tasks + Watch (CAPS-01e)

**Goal:** Voss gains a `watchdog`-backed file-watch backend exposed as an `fs_watch` agent tool emitting recorder events, plus a `voss watch <command>` CLI that re-runs a command on watched-file change with an opt-in `--daemon` flag — built on the existing T5 background job engine, headless-only this phase (M9 TUI status strip and M10 `code_refresh` hookback explicitly deferred per M14-SPEC.md).

**Requirements:** WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05 (locked in `M14-SPEC.md`).

**Seed source:** [`seeds/agent-capability-surface.md`](seeds/agent-capability-surface.md) (capability 5)

**Headline deliverables (to be refined in SPEC):**
- Background job manager — start/stop/status of long-running processes with structured handles.
- File-watch — register watchers on globs; emit events into the recorder stream for tool consumption.
- Dev-server / test-watcher integrations — `voss watch <command>` keeps a process alive across session lifecycle.
- M9 TUI bottom-pane status strip — running jobs, last-tick result, recent errors.
- M10 hookback — `code_refresh` can subscribe to file-watch events for live index updates.

**Cross-cutting constraints:**
- Depends on M9 TUI shell for status strip; ships headless first if M9 incomplete.
- Background jobs reaped on session exit unless explicitly daemonized via opt-in flag.
- File-watch backend cross-platform: `watchdog` Python lib for macOS/Linux/Windows.

**Success Criteria:** Per `M14-SPEC.md` acceptance criteria — watchdog pinned + importable; matching-glob edit yields exactly one coalesced recorder event in the debounce window; non-matching edit yields zero; `fs_watch` registered in one turn readable via cursor in a later turn; `voss watch 'pytest -q'` re-runs on change; non-daemon reaped on session exit (TERM <=2s/KILL <=5s); `--daemon` survives session exit; WATCH event tests green on macOS + Linux CI; shell allowlist enforced.

**Plans:** 4 plans across 4 waves (serial spine; W3 runs M14-03 ∥ M14-04 file-disjoint).

Plans:
- [x] M14-01-PLAN.md — Wave 0 scaffold: pin watchdog, 10 RED WATCH tests + reset/daemon-PID fixtures, macOS+Linux CI matrix (+ blocking package-legitimacy checkpoint pending before M14-02)
- [x] M14-02-PLAN.md — lifecycle spine: `_WATCHERS` registry + `WatcherRecord` + shared `_read_log_cursor` factor (D-02/D-04, OQ-1) + `watch/backend.py` watchdog Observer/Debouncer/asyncio bridge (D-01) + reap wiring
- [ ] M14-03-PLAN.md — `fs_watch` + `fs_watch_poll` agent tools in make_toolset, both `is_mutating=False` (WATCH-02, OQ-2)
- [ ] M14-04-PLAN.md — `voss watch` CLI (allowlist + re-run via T5 register_job) + `watch/daemon.py` `start_new_session` detach with `--_is-worker` guard (WATCH-03/04, OQ-3)

**Out of scope:** Distributed task scheduling. Cron-like recurring tasks (separate concern). Notification delivery (push/email/etc.).

---

## Phase M15: Skill / Plugin Marketplace (CAPS-01f)

**Goal:** Make third-party `.voss` skills installable via a `voss skill add <name>` workflow with signed manifests, a sandbox boundary, and a permission scope per skill. Build atop the existing `voss/harness/plugins.py` scaffold.

**Requirements:** SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, SKILL-06 (6 locked — `M15-SPEC.md`).

**Plans:** 6 plans across 5 waves (planned 2026-05-19).

Plans:
- [ ] M15-01-PLAN.md — Wave 0: RED skill test suite + cryptography direct dep + signed example bundle (human gate)
- [ ] M15-02-PLAN.md — Wave 1: trust.py — Ed25519 detached-sig verify + pinned-key trust store [SKILL-03]
- [ ] M15-03-PLAN.md — Wave 1: scope.py — declared scopes → existing PermissionGate (no new engine) [SKILL-04]
- [ ] M15-04-PLAN.md — Wave 2: fetch + manifest schema + install/remove/update gating (staging→verify→copy) [SKILL-01, SKILL-05]
- [ ] M15-05-PLAN.md — Wave 3: VossSkillAdapter + registry + voss skill CLI + RunRecorder audit [SKILL-02]
- [ ] M15-06-PLAN.md — Wave 4: e2e fixture-cycle CI test + documented confinement limitation [SKILL-06]

**Seed source:** [`seeds/agent-capability-surface.md`](seeds/agent-capability-surface.md) (capability 6)
**Existing infra:** `voss/harness/plugins.py` (`PluginManifest`, user/project plugin dirs, enablement TOML) — scaffold present, unused.

**Headline deliverables (to be refined in SPEC):**
- `voss skill add <name>` / `voss skill remove <name>` / `voss skill list` CLI surface.
- Skill manifest schema — capabilities declared, permission scopes required, dependency declaration.
- Sandbox boundary — third-party skill code runs with a restricted toolset (read-only by default; mutating tools require explicit user grant per skill).
- Manifest signing — cryptographic signature verification before install; trust roots configurable.
- Registry source — initial v0.2 ships GitHub-based registry (skills as repos with `voss-skill.yml` manifest); central registry is later.

**Cross-cutting constraints:**
- Hard prerequisite: sandbox + permission story BEFORE any third-party code runs. This is the highest-risk surface in the v0.2 cycle.
- Coordinates with M1 permission tiers (`plan`/`edit`/`auto`) — skills declare which tier they need.
- Audit trail — every skill invocation logged through M2 RunRecorder.

**Success Criteria:** The 10 acceptance criteria in `M15-SPEC.md` (add/list/run/trust/tamper-refuse/scope-deny/remove/update-tamper-intact/e2e-fixture/no-forbidden-subsystem).

**Out of scope:** Paid skills. Cross-org skill discovery (post-v0.2). Hot-reload of skills mid-session. Skill GUIs beyond TUI palette registration.

---

## T-prefixed phases: Daily-Driver Gap Closure

T-phases close known competitive gaps against Claude Code / Codex / Pi on
the surface that already exists. They add no new product surface — they
make `voss do` / `voss chat` feel like a coding agent users would reach
for daily. Full audit, sequencing rationale, and per-phase requirements
in [`notes/daily-driver-punch-list.md`](notes/daily-driver-punch-list.md).

**Versioning split:**
- **v0.1.1 patch** — T6 only. PRD §2.4 promised those slashes; shipping
  them is closing a contract bug, not adding a feature.
- **v0.2.0 minor** — T1–T5, T7, T8 (alongside M8 + M9 + M10). Daily-driver
  table stakes complete.
- **v0.3.0+** — M11–M15. Unfair-advantage features (Voss-aware tools,
  MCP server, multi-agent in chat, watch, marketplace).
- **v1.0.0** — API lock once dogfood signals public surface is stable.

### Phase T6 — PRD §2.4 Slash Debt *(v0.1.1 patch)*

**Goal:** Ship the slash commands the PRD promised and the user expects.
Most are 20-line wrappers around existing data. Closes M1's PRD-conformance
gap. Treated as a v0.1.1 patch rather than v0.2 minor because each missing
slash is a documented contract bug from v0.1, not a new capability.

**Requirements (proposed):** SLASH-01..07

- SLASH-01 `/diff` — show pending unapplied edits.
- SLASH-02 `/apply` — apply pending edits explicitly (plan mode).
- SLASH-03 `/discard` — drop pending edits.
- SLASH-04 `/budget <usd>` — adjust remaining session budget at runtime.
- SLASH-05 `/resume <id|name>` — load a prior session into the live REPL.
- SLASH-06 `/why` — render last plan's rationale + `ProbableValue`
  confidence breakdown (PRD's "killer feature").
- SLASH-07 `/cost --by-model` / `--by-tool` flags.

**Success Criteria (Met — 2026-05-18):**
1. **SC#1** — Each slash in PRD §2.4 has ≥1 integration test exercising the happy path (T6-03 completed the set; `/discard` confirmed pre-covered).
2. **SC#2** — `/why` renders confidence + rationale from the most recent `Plan` with **no** provider call (D-07 audit test + existing `_why` implementation).
3. **SC#3** — Grouped in-REPL `/help` (Editing/Session/Insight/Control + Other long-tail) + one-line signpost in **both** production `voss --help` and `python -m voss.harness --help` (T6-02). No slash-list duplication.

All three criteria verified. T6 (v0.1.1 patch) **complete**.

**Cross-cutting constraints:**
- No new persistence. Slashes operate on the live `ReplContext`.
- M9 SlashPalette autocomplete includes all seven (M9-03 reserves slot
  names already).

---

### Phase T1 — Iteration Loop + Streaming + Interrupt *(v0.2 lead)*

**Goal:** Replace the single-shot plan→execute→done flow with a real agent
loop that re-plans on tool results, streams text as it arrives, and
cancels cleanly on user interrupt.

**Requirements (proposed):** ITER-01..06

- ITER-01 `_run_turn_exec` is a while-loop. Exits on agent-emitted `done`,
  max-iteration cap, or budget exhaustion.
- ITER-02 Tool results feed back into model context for next iteration.
- ITER-03 Provider switches from `complete` to `stream`; TurnView renders
  incremental deltas.
- ITER-04 `action_interrupt` (`tui/app.py:79`) cancels the in-flight
  asyncio task and surfaces "interrupted" in the recorder.
- ITER-05 Confidence gate moves from per-turn to per-loop-exit. Mid-loop
  low confidence triggers another iteration, not `/clarify`.
- ITER-06 Telemetry records iteration count, per-iteration cost, exit
  reason (done / max-iter / budget / interrupt).

**Success Criteria (proposed):**
1. M5 golden task #2 ("rename-symbol") completes in one `voss do` without
   user re-prompting.
2. First visible token in TurnView ≤ 500ms after provider acceptance.
3. `action_interrupt` cancels an in-flight turn and produces a closed
   recorder entry within 100ms.
4. Default max iteration = 8, configurable via `harness.toml`. Hit-cap
   produces structured "halted: max-iter" final, not a crash.

**Cross-cutting constraints:**
- Each iteration is a sub-record under one Turn (not N Turns) — preserves
  M2 `RunRecord` schema for `voss resume` compatibility.
- `_substitute_placeholders` is removed. Prior results flow via context.
- This phase is the **breaking behavior change** that justifies v0.2.

**Plans:** 7 plans across 5 waves

Plans:
- [ ] T1-01-PLAN.md — Schema substrate: IterationRecord + additive RunRecord fields + RunRecorder.begin_iteration/end_iteration
- [ ] T1-02-PLAN.md — ProviderStreamEvent union + StreamingProvider Protocol + ParsedPlan terminal event (placeholder stream() bodies)
- [ ] T1-03-PLAN.md — Concrete AnthropicOAuthProvider.stream() + OpenAIOAuthProvider.stream() with OAuth refresh + graceful httpx aclose + parity test
- [ ] T1-04-PLAN.md — TurnView.stream_delta/finalize_stream + RuntimeConfig.max_iterations + [agent] section TOML loader
- [ ] T1-05-PLAN.md — Rewrite _run_turn_exec as while-loop, delete _substitute_placeholders, PLAN_LOOP_SYSTEM + per-iter rider, per-iter telemetry
- [ ] T1-06-PLAN.md — VossTUIApp.active_turn_task + action_interrupt body + CancelledError handler in _run_turn_exec + cli.py register_turn_task
- [ ] T1-07-PLAN.md — SPEC 12-checkbox acceptance suite + grep gate + M5 golden #2 one-shot + CI workflow step

---

### Phase T4 — Prompt Caching + Cost Truthfulness *(v0.2)*

**Goal:** Stop rebuilding the system prompt every turn. Track cost
honestly including cache reads.

**Requirements (proposed):** CACHE-01..04

- CACHE-01 Anthropic provider adds `cache_control: {type: "ephemeral"}`
  to the cognition block + VOSS.md block.
- CACHE-02 Cost accounting reads `cache_creation_input_tokens` +
  `cache_read_input_tokens` from response, prices at Anthropic rates.
- CACHE-03 `/cost` gains `--by-model` / `--by-tool` (overlaps T6 SLASH-07;
  ship whichever lands first).
- CACHE-04 OpenAI provider adopts equivalent caching when model reports
  eligibility.

**Success Criteria (proposed):**
1. Two consecutive turns in a `voss chat` session show
   `cache_read_input_tokens > 0` on the second turn.
2. `/cost --by-model` matches `sum(per-turn cost_usd by model)` to 4
   decimals.
3. Reported cost includes cache cost, not just non-cached input.

**Cross-cutting constraints:**
- Cache key stable across turns; VOSS.md drift invalidates the cache
  (acceptable).
- Cache TTL = 5 minutes (Anthropic default); documented in `harness.toml`.

**Plans:** 6 plans

Plans:
- [x] T4-01-test-scaffold-PLAN.md — Wave 0: 9 failing test stubs + cassette README + pyproject pin bumps (litellm>=1.74.0, vcrpy>=8,<9)
- [x] T4-02-extractor-and-non-streaming-PLAN.md — `_cache_tokens.extract_cache_tokens` + `ProviderResponse` additive fields + LiteLLMProvider wiring (CACHE-02 non-streaming)
- [x] T4-03-agent-composition-PLAN.md — `_compose_system_blocks` + multi-block `messages[0]` + four-drift invalidation tests (CACHE-01, CACHE-06)
- [x] T4-04-streaming-telemetry-recorder-PLAN.md — Usage variant + agent.py Usage consumer + provider.response telemetry payload + IterationRecord round-trip (CACHE-02 streaming, CACHE-07 telemetry/round-trip)
- [x] T4-05-cost-truth-and-cli-PLAN.md — D-09 placeholder edit + LiteLLM cost-differential test + /cost --by-model 4-decimal verification (CACHE-03, CACHE-04)
- [x] T4-06-cassette-integration-PLAN.md — [BLOCKING human-action] one-time live cassette recording + two-turn replay test (CACHE-05, CACHE-07 invariant)


---

### Phase T2 — Parallel Tools + Multi-Edit Primitive *(v0.2)*

**Goal:** Read-only steps execute in parallel (bounded by
`agent.max_parallel_reads`). Mutations stay strictly serialized. File
edits can batch multiple replacements atomically through the M9-05
DiffModal. Prove ≥40% wall-clock drop on a self-contained 6-read
micro-benchmark (M5 eval baseline is empty — own benchmark replaces it).

**Requirements (locked via T2-SPEC.md):** PAR-01..06

- PAR-01 `_run_step_loop` partitions steps into read-only batches +
  mutating singletons. Read-only batches run via `asyncio.gather`
  bounded by `asyncio.Semaphore(agent.max_parallel_reads)`.
- PAR-02 Partition-time invariant: every step in a multi-step batch has
  `ToolEntry.is_mutating == False`; violation raises
  `BatchInvariantError` (additive 5th exit_reason value).
- PAR-03 New tool `fs_edit_many(path, edits=[{old, new}, ...])` —
  validate-then-write-once atomicity through M9-05 DiffModal; reject-any
  or skip-any → batch denied.
- PAR-04 New tool `fs_read_many(paths=[...])` — bundled response
  `=== {path} ===\n{content}\n` per slot, per-slot error envelopes,
  30KB per-file cap, partial-result semantics.
- PAR-05 `harness.toml [agent] max_parallel_reads = 8` (range 1-32,
  out-of-range falls back with RuntimeWarning) + self-contained
  micro-benchmark proving ≥40% wall-clock drop.
- PAR-06 `batch.start` / `batch.end` telemetry events for multi-step
  batches only; per-step `tool.call` / `tool.result` preserved
  unchanged; `IterationRecord.batches: list[BatchRecord]` additive
  M2-compatible schema.

**Success Criteria:**
1. `tests/perf/test_parallel_read_speedup.py` micro-benchmark passes:
   parallel wall-clock ≤ 60% of serial baseline (≥40% drop) on a
   stub-timed 6-read batch.
2. `fs_edit_many` rejects entire batch if any `old` doesn't match
   uniquely; recorder logs offending index; file byte-for-byte unchanged
   on disk after rejection.
3. Mutation step in a read batch raises `BatchInvariantError`; partitioner
   never produces such a batch from author-order input.
4. Read-only steps from a real `voss do` invocation produce visible
   `batch.start`/`batch.end` telemetry events and populate
   `RunRecord.iterations[i].batches`.

**Cross-cutting constraints:**
- Diff modal (M9-05) handles multi-edit via per-hunk approval — `fs_edit_many`
  builds list[Hunk] itself and calls `renderer.show_diff_modal` directly;
  PermissionGate stays single-edit (D-01).
- Mutation classification checked at registration via `ToolEntry.is_mutating`
  (M1 D-06 invariant); no tool-name pattern matching.
- `RunRecord` schema additions are additive-only; pre-T2 records round-trip
  unchanged (M2 + T1 invariant).
- Author order non-negotiable: a read step never executes before a write
  authored earlier in `plan.steps`; reads after a write run in the NEXT
  batch, never hoisted.
- `agent.max_parallel_reads` config knob co-locates with T1's
  `agent.max_iterations` in the same `[agent]` block of
  `~/.config/voss/config.toml`.

**Plans:** 6 plans across 5 waves

Plans:
- [ ] T2-01-PLAN.md — Schema substrate: BatchRecord dataclass + IterationRecord.batches additive field + RunRecorder.begin_batch/end_batch capture API
- [ ] T2-02-PLAN.md — Config knob: RuntimeConfig.max_parallel_reads + get_max_parallel_reads loader (range 1-32 + fallback warning) + cli.py bootstrap wire-in
- [ ] T2-03-PLAN.md — Partition scheduler rewrite + BatchInvariantError + batch.start/end telemetry + recorder wiring + _run_turn_exec exit_reason="batch-invariant" handler
- [ ] T2-04-PLAN.md — fs_edit_many tool (atomic validate-then-write-once, M9-05 DiffModal integration with strict skip-is-deny semantics)
- [ ] T2-05-PLAN.md — fs_read_many tool (bundled response, per-slot error envelopes, 30KB per-file cap, partial-result semantics)
- [ ] T2-06-PLAN.md — Self-contained micro-benchmark (≥40% wall-clock drop) + phase-final human-verify checkpoint

---

### Phase T3 — Network Surface (WebFetch + WebSearch + MCP client) *(v0.2)*

**Goal:** Give the agent access to live documentation and external tools
without inventing a new protocol. Gate network at the harness boundary.

**Requirements (proposed):** NET-01..07

- NET-01 New tool `web_fetch(url)` via `httpx`. Honors `tools.allow_net`
  config flag (HARNESS-PLAN §6 — currently declared, unenforced).
- NET-02 New tool `web_search(query)`. Default no built-in backend; opt-in
  Brave / Tavily via API key. (DuckDuckGo HTML rejected — fragile +
  rate-limited.)
- NET-03 MCP client over stdio — lift Codex's launcher pattern. Configure
  via `.voss/mcp.yml`.
- NET-04 MCP tool permission scope defaults to `plan` (read-only).
  Mutation requires explicit user opt-in per server in `permissions.yml`.
- NET-05 Network tools off by default; `voss --allow-net` or
  `tools.allow_net = true` opts in.

**Required commands:**
```
voss mcp list                   # registered MCP servers
voss mcp call <server> <tool>   # debug: invoke directly
```

**Success Criteria (proposed):**
1. Default install has no network access; opt-in is one config line.
2. `voss mcp call` works against the Anthropic reference MCP filesystem
   server out of the box.
3. M5 eval gains task #6 "fetch + summarize" requiring `web_fetch`.

**Cross-cutting constraints:**
- Path-jail + shell allowlist do not apply to network tools — sandbox is
  per-tool-class.
- MCP server processes reaped on session exit (mirror M10 LSP pattern).
- Network telemetry events `net.request` / `net.response` with redacted URLs.
- This phase reduces M12's scope to "expose harness as MCP server only" —
  the client side ships here.


**Plans:** 9 plans across 6 waves

Plans:
- [ ] T3-01-PLAN.md — Wave 0 scaffolding: lifecycle.py SIGTERM+5s+SIGKILL reap + 9 NET-XX placeholder test files (32 named test stubs)
- [ ] T3-02-PLAN.md — Permission gate net-check + RuntimeConfig.allow_net + [tools] allow_net loader + --allow-net CLI flag (NET-05; ToolEntry.is_network axis)
- [ ] T3-03-PLAN.md — telemetry.redact_url + net.request/response + mcp.request/response event-shape contract (NET-06)
- [ ] T3-04-PLAN.md — rate_limit.py TokenBucket primitive + [net.rate_limits] TOML parser w/ escaped-dot regex (NET-07)
- [ ] T3-05-PLAN.md — net.py NetSession + web_fetch tool (1 MB cap, timeout clamp, error envelopes) + transport-level zero-socket proof (NET-01)
- [ ] T3-06-PLAN.md — web_search.py BraveBackend + NetSession.search + dedup-by-URL + count clamp + 429 handling (NET-02)
- [ ] T3-07-PLAN.md — mcp/{__init__,config,client,registry}.py: ${VAR}/{cwd}/env-allowlist loader + 2025-11-25 handshake + lazy launch + destructiveHint scope mapping (NET-03, NET-04)
- [ ] T3-08-PLAN.md — voss mcp {list,call} click group + --arg JSON-with-string-fallback parsing (NET-03 CLI surface)
- [ ] T3-09-PLAN.md — .github/workflows/mcp-integration.yml CI job + M5 eval task #6 fetch+summarize + httpx MockTransport stub injection (BLOCKING human-verify checkpoint for npm version + read-tool-name pin)

---

### Phase T5 — Shell Ergonomics *(v0.2)*

**Goal:** Real builds and test runs survive the shell tool. Long-running
tasks don't block the agent.

**Requirements (proposed):** SHELL-01..05

- SHELL-01 `shell_run` default output cap raised 4KB → 30KB.
- SHELL-02 New `shell_run_background(cmd) -> handle` — detached process,
  reaped on session exit.
- SHELL-03 New `shell_monitor(handle, since_ms=0) -> chunk` — incremental
  stream.
- SHELL-04 New `shell_signal(handle, signal="INT"|"TERM")`.
- SHELL-05 `voss jobs` CLI lists running background processes for the
  current session.

**Success Criteria (proposed):**
1. A 20-second background job is observable via `shell_monitor` from a
   second agent turn.
2. Orphaned background jobs get SIGTERM within 2s, SIGKILL at 5s on
   session exit.
3. Per-process cap: 100MB memory, 30s no-output watchdog kills the job;
   recorder logs.

**Cross-cutting constraints:**
- Shell allowlist still applies to background commands.
- Background jobs do not inherit the agent's TTY.
- This is the headless half of M14 (file-watch). M14 layers `watchdog`
  on top.

**Plans:** 5 plans

Plans:
- [x] T5-01-test-scaffold-and-psutil-dep-PLAN.md — Wave 1: failing test surface (SHELL-01..05 + SC#1/#2/#3) + emit.py fixture + `_JOBS` reset + `30720` source guard + [BLOCKING human-verify] psutil legitimacy gate then `psutil>=5.9,<8` dep add
- [x] T5-02-shell-run-cap-raise-PLAN.md — Wave 2: SHELL-01 cap 4096→30720 in both `shell_run` AND `_shell_capture` (Flag 1: raise both); envelope + 30s timeout untouched
- [x] T5-03-job-registry-and-background-spawn-PLAN.md — Wave 3: JobRecord + atomic `.meta.json` sidecar + `_JOBS` registry + `register_job`/`reap_jobs`/`signal_job` + single supervisor task (pump+30s+100MB) + `start_new_session`/killpg + `shell.background.reap` + `shell_run_background` (SHELL-02, SC#2/#3, D-01/02/05/08/09/10/11)
- [x] T5-04-monitor-signal-and-permissions-PLAN.md — Wave 4: `shell_monitor` cursor read + `shell_signal` INT/TERM + 2 ToolEntry regs + D-12 edit-mode deny (explicit name-set) + permissions_bridge verbs (SHELL-03/04, SC#1, D-03/06/12)
- [x] T5-05-voss-jobs-cli-and-active-session-PLAN.md — Wave 5: production `make_toolset(session_id=record.id)` wiring (cli.py:1314 `_run_repl` only — closes the cross-process contract; other 5 sites deliberate `_nosession`) + `jail_path` import + `voss jobs` table/`--json` sidecar read + AGENT_COMMANDS + `.active-session` try/finally lifecycle + `--keep-logs` + explicit `reap_jobs()` (SHELL-02/05, D-04/09/11, A4)

---

### Phase T7 — Skills Bootstrap *(v0.2)*

**Goal:** Ship 6 ready-to-use skills so the registry isn't just a hook.

**Requirements (proposed):** SKL-01..06

- SKL-01 `rename-symbol` — anchor + scope-aware rename across the repo.
- SKL-02 `add-test` — locate a public function, generate a unit test.
- SKL-03 `summarize-diff` — pipe `git diff` → PR description.
- SKL-04 `port-py-to-voss` — Python → `.voss` for classify/support/research
  sample shapes.
- SKL-05 `audit-cognition` — re-run analyze against drift; propose a
  paragraph update to `architecture.md`.
- SKL-06 `voss-lint-as-skill` — wraps `voss check` with structured
  diagnostic output. Foundation for M11.

**Success Criteria (proposed):**
1. Every skill invokable via `/skill <id>`, runs to completion on a
   reference repo without permission escalation.
2. Skills pair 1:1 with M5 eval tasks where applicable.

**Cross-cutting constraints:**
- Skills authored in `.voss` where the language expresses them; otherwise
  Python with a `.voss` lint pass demonstrating composability.
- Unblocks M15 (marketplace) but doesn't require it.

---

### Phase T8: Input Bar Ergonomics (v0.2)

**Goal:** The input bar stops being the slowest part of the loop.

**Requirements (proposed):** INPUT-01..05

- INPUT-01 Multi-line input via `Shift-Enter`; `Enter` submits.
- INPUT-02 `!<cmd>` prefix runs an allowlisted shell command without
  spawning a turn.
- INPUT-03 `#<text>` prefix appends a memory note to `VOSS.md` without
  spawning a turn.
- INPUT-04 `Ctrl-R` reverse-search through episodic history.
- INPUT-05 Paste-image detection — if clipboard has an image and the
  model supports it, attach as a vision input.

**Success Criteria (proposed):**
1. All five behaviors covered by Textual snapshot tests.
2. `!` and `#` shortcuts emit recorder events (`shell.local` /
   `memory.note`) and bypass `run_turn`.

**Status:** Complete (5/5 plans summarized, 2026-05-18). Focused T8 verification: 53 tests / 11 snapshots passed.

**Cross-cutting constraints:**
- M9 keymap (`tui/keymap.py`) is the source of truth — this phase only
  adds bindings.

**Plans:** 5 plans across 4 waves (W0 scaffold → W1 TextArea swap → W2 prefix-dispatch ‖ TUI-submit-wiring → W3 Ctrl-R + paste-image)
- [x] T8-01-PLAN.md — Wave 0: pytest-textual-snapshot + hermetic fixtures + `.value`→`.text` migration + red scaffolds (INPUT-01..05 substrate)
- [x] T8-02-PLAN.md — INPUT-01: Input→TextArea swap, Enter/Shift+Enter inversion, autogrow 1-5, slash guard, additive `ctrl+r` keymap line
- [x] T8-03-PLAN.md — INPUT-02/03: `!cmd` via existing T5-D12 gate + `#note` to `## Notes` human section; run_turn bypass; `shell.local`/`memory.note` recorder events
- [x] T8-04-PLAN.md — Enabling deliverable (RESEARCH A4): `on_input_bar_submitted`→run_turn wiring + `_run_repl` interactive Textual loop + `app.history` for Ctrl-R corpus
- [x] T8-05-PLAN.md — INPUT-04 Ctrl-R inline reverse-i-search (per-project episodic) + INPUT-05 paste-image attach / no-vision transient notice

**Scope note (RESEARCH A4 — recorded):** `make_renderer` builds `TextualRenderer(VossTUIApp())` but `app.run()` is never called and `_run_repl` uses synchronous `input()`. Without the T8-04 submit→run_turn wiring INPUT-01..05 are structurally unobservable in a real session. T8-04 is an in-scope ENABLING deliverable (planner option a), not scope creep.

---

## A-prefixed phases: voss-app Desktop ADE

**Track:** voss-app — terminal-grid desktop ADE in `apps/voss-app/`. Sibling deliverable to the Python harness. Tauri (Rust core) + Solid (webview UI) + xterm.js + `portable-pty`.

**Layering** (full detail in `apps/voss-app/CONCEPT.md`):
- **Layer 1 / v0 = A1–A10** — terminal-grid scaffold. **Zero Voss code in binary.** Ships as competitive Warp/Wezterm alternative.
- **Layer 2 / v1 = A11+** — Voss harness substrate. Promote-to-cell, streaming render, permissions, reviewer-as-pair-programmer demo. Locks once L1 ships.
- **Layer 3 / v2 = A20+** — `.voss` DSL features (hot-reload, inter-cell DSL wiring, curated loop library).
- **Layer 4+ / deferred** — Monaco editor pane, file tree, SCM, search. Uncommitted; evaluate post-L3.

**Reference design:** sketch 001 Variant B (Minimal Tile) — `.planning/sketches/001-voss-grid-shell/`. 22px headers, thin 1px borders, mono everywhere, glyph-prefix lines, inset-shadow focus.

**Cross-A constraints:**
- v0 must be usable as a daily terminal without the word "Voss" appearing in the UI beyond the app name.
- `.voss/` directory is forward-compat only in L1 (empty unless user customizes settings) — schema versioned `{"version": 1}`.
- Cost meter in status bar is stubbed `$0.00` in L1; comes alive in L2.
- All A phases share the Variant B aesthetic tokens — no per-phase visual re-exploration.
- Project-wide spec-blocking questions **closed 2026-05-16** — full decisions in `apps/voss-app/CONCEPT.md` §10. Highlights: ship name = **Voss ADE** (Q1); auto-`$SHELL` on pane open (Q2); banner + restart on exit (Q3); pure-visual presets in L1 (Q4); first-class project-less mode (Q5); no cost meter in L1 (Q6); lazy `.voss/` creation (Q7); three distribution channels — Direct + Homebrew + npm subcommand (Q8); telemetry OFF default, opt-in (Q9).

---

### Phase A1: voss-app Tauri Shell

**Goal:** Tauri + Solid empty window builds and runs locally on the dev's platform with custom titlebar and theme tokens applied. **No release pipeline, no signing, no distribution channels** — that work is consolidated into A10 (release is a final gate; the app does not ship until A1–A9 are built).

**Requirements (locked at SPEC):** SHL-01..06
- SHL-01 Tauri version pinned (2.x recommended; SPEC confirms).
- SHL-02 Solid + Tailwind UI scaffolded with Variant B theme tokens.
- SHL-03 Custom titlebar with project-name placeholder, layout-preset switcher (visual only, no behavior yet). No cost-meter slot (Q6).
- SHL-04 Window: traffic lights (mac) · standard close/min/max (linux/win) · zoom · fullscreen · multi-monitor.
- SHL-05 `pnpm tauri dev` runs the app locally; `pnpm tauri build` produces an **unsigned local artifact** for the dev's own platform (smoke-test only — not a release artifact).
- SHL-06 Window title + About dialog use the **Voss ADE** ship name (Q1); `voss-app` retained only as repo / npm-package slug.

**Success Criteria (proposed):**
1. `voss-app` launches as an empty Tauri window on the dev's platform.
2. Titlebar renders Variant B tokens; theme swappable via config file.
3. `pnpm tauri build` produces a runnable unsigned local artifact.


**Plans:** 4 plans across 4 waves (sequential — each layer compiles on the prior; VALIDATION.md sampling rule favors a compile/smoke check between layers)
- [ ] A1-01-PLAN.md — Monorepo wiring + Tauri/Solid/Tailwind scaffold + pinned versions; empty 'Voss ADE' window (SHL-01, SHL-06)
- [ ] A1-02-PLAN.md — Full Variant B token system + Tailwind @theme inline + Rust get_theme_overrides settings seam (SHL-02)
- [ ] A1-03-PLAN.md — Custom 22px titlebar + macOS traffic-light controls + visual-only preset switcher (SHL-03, SHL-04)
- [ ] A1-04-PLAN.md — Hardened CSP + unsigned `pnpm tauri build` smoke + About-panel ship name + A10 cert-procurement clock (SHL-05, SHL-06)

**Cross-cutting constraints:**
- No xterm, no PTY, no grid in A1 — pure window scaffolding.
- **No release/CI/signing/Homebrew/npm work in A1** — moved to A10.
- Settings load from `~/.config/voss-app/settings.json` if present; else baked defaults.
- `apps/voss-app/src-tauri/` is a new Rust crate consuming `crates/voss-app-core/` (created empty here, populated by later A phases).

---

### Phase A2: voss-app PTY Pane

**Goal:** A single xterm.js pane wired to a native PTY (`portable-pty`) with full TTY support, scrollback, copy/paste, and OSC sequence handling. Replaces the empty window from A1 with one working terminal.

**Requirements (locked at SPEC):** PTY-01..0N
- PTY-01 `portable-pty` spawns user's `$SHELL` with `TERM=xterm-256color`, `COLORTERM=truecolor`.
- PTY-02 xterm.js renders the PTY; bidirectional stream (stdin / stdout / stderr).
- PTY-03 10k-line scrollback default, configurable. `⌘F` search in scrollback. `⌘⇧K` clear.
- PTY-04 Copy/paste: `⌘C` selection or interrupt (configurable), `⌘V` w/ bracketed-paste safety, `⌘⇧V` literal.
- PTY-05 OSC 8 hyperlinks (`⌘+click` opens URL). File-path auto-detection in output → `⌘+click` opens in OS.
- PTY-06 Process indicator in pane header (foreground command parsed from OSC 0).
- PTY-07 Shell exit behavior — pane shows `[exited N]` banner with "restart" button (assumes Q3 closes this way; SPEC reconfirms).
- PTY-08 Alt-screen apps (`vim`, `htop`, `less`, `tmux`) render correctly inside the pane.

**Success Criteria (proposed):**
1. Run `vim`, `htop`, `tmux`, `less` inside the pane — alt-screen + TTY signals work.
2. Scrollback persists across pane resize.
3. Copy from one OS app, paste into pane (bracketed-paste warns on multi-line).
4. Hyperlink click opens browser.

**Cross-cutting constraints:**
- Single pane only in A2 — multi-pane is A3.
- Pane occupies the whole window minus titlebar + status bar (status bar stubbed; A9 finishes it).

**Plans:** 5 plans across 4 waves
- [ ] A2-01-PLAN.md — Wave 0 scaffold: red test suite, xterm v5.5.0 pin, voss-app-core crate, D-01/legitimacy gate (W1)
- [ ] A2-02-PLAN.md — Rust PTY core: spawn/stream/resize/exit/backpressure/SIGINT + pgid fallback (W2)
- [ ] A2-03-PLAN.md — Solid pane + Tauri Channel IPC + D-02 rAF coalescing & watermark (W2)
- [ ] A2-04-PLAN.md — Paste-guard, ⌘C/SIGINT, find/clear, OSC8 links, fg-header, exit/restart (W3)
- [ ] A2-05-PLAN.md — D-02 flood-perf build-failing gate + PTY-08 alt-screen manual matrix (W4)

---

### Phase A3: voss-app Grid Engine

**Goal:** Multi-pane grid layout — binary-split tree, splits/focus/resize/close, `⌘1-9` numeric nav, an **in-memory Solid→Rust layout mirror (no disk persistence in A3 — A4/A6 own file I/O)**. Each pane is an independent PTY from A2.

**Requirements (locked at SPEC):** GRD-01..0N
- GRD-01 Pane tree model: binary splits (horizontal/vertical), tmux-style.
- GRD-02 `⌘\` split horizontal, `⌘⇧\` split vertical, `⌘D` fork (duplicate cwd + shell), `⌘W` close (confirm if running).
- GRD-03 Focus: `⌘1`-`⌘9` numeric, `⌘⌥` arrow directional, click-to-focus, `⌘[`/`⌘]` cycle.
- GRD-04 Resize: drag border, `⌘⌥⇧` arrow 5% increments, `⌘=` equalize.
- GRD-05 Per-pane min size (cols × rows) enforced.
- GRD-06 22px Variant B pane header: `●` dot · index · cwd basename · shell · process indicator · `⋯` menu.
- GRD-07 Focused pane indicated by inset shadow + bg lift (no border ring).
- GRD-08 Layout state stored in Solid signals, mirrored to Rust core for persistence.

**Success Criteria (proposed):**
1. 2×2 grid created via 3 splits; each pane runs an independent shell.
2. Focus follows click and `⌘1-4`. Directional focus works.
3. Resize via drag and keyboard.
4. Close pane: confirm if process running, no-confirm if idle.

**Cross-cutting constraints:**
- Grid model decision (binary-tree vs css-grid vs flex) closes at SPEC.
- No layout presets in A3 — that's A4.

**Plans:** 6 plans across 5 waves
- [ ] A3-01-PLAN.md — Binary-split tree model + Solid store + voss-app-core Rust mirror + sync seam (GRD-01, GRD-08)
- [ ] A3-02-PLAN.md — Split/fork/close/equalize mutations + 20×5 floor guard + D-04 close (GRD-02, GRD-05)
- [ ] A3-03-PLAN.md — Numeric/i3-directional/click/cycle focus + drag/keyboard resize w/ 20×5 clamp (GRD-03, GRD-04, GRD-05)
- [ ] A3-04-PLAN.md — Recursive renderer + drag handles + global keymap + inset-shadow focus treatment (GRD-01, GRD-03, GRD-04, GRD-07)
- [ ] A3-05-PLAN.md — 22px Variant B header (index + ⋯) + 5-item menu + foreground-gated close-confirm (GRD-02, GRD-06, GRD-07)
- [ ] A3-06-PLAN.md — App integration + e2e acceptance + 9-pane Canvas perf/flood benchmark + mirror parity (GRD-01..08)

---

### Phase A4: voss-app Layout Presets

**Goal:** Visual layout templates — `fanout · pipeline · swarm · watchers`. `⌘G` cycles. Switching reorders existing panes, never kills them. Save/load named layouts.

**Requirements (locked at SPEC):** LAY-01..0N
- LAY-01 Four presets: fanout (1 source left, N receivers right column) · pipeline (left-to-right equal row) · swarm (N×N equal grid, default 2×2 up to 4×4) · watchers (main top, 2-3 thin watchers bottom).
- LAY-02 Titlebar switcher widget (sketch 001 Variant B styling).
- LAY-03 `⌘G` cycles presets in order.
- LAY-04 Switching preset reorders existing pane tree; never destroys panes.
- LAY-05 If pane count doesn't match preset capacity, panes added/preserved gracefully (no panes destroyed).
- LAY-06 "Save layout as…" + "Load layout…" in command palette (palette delivered in A7; stub command exists earlier).
- LAY-07 Layout file format: `.voss/layouts/<name>.json` with versioned schema.
- LAY-08 L1 semantics: pure visual templates. Layer 2 will overlay behavior — L1 must not couple.

**Success Criteria (proposed):**
1. Switch between all 4 presets with `⌘G`; layout reorders predictably.
2. Save a named layout, modify, reload — geometry restored.
3. Open a project with a saved default layout in `.voss/layouts/default.json`.

**Cross-cutting constraints:**
- Preset semantics question (CONCEPT §10 Q4) must close before SPEC — L1 visual-only is the recommendation.

**Plans:** 6 plans across 5 waves (planned 2026-05-19; A4-00 blocks on A3-06 substrate).

Plans:
- [ ] `A4-00-PLAN.md` — Blocking A3-06 substrate preflight; verify GridRoot is live in App, Rust grid sync commands are registered, and A3 integration/perf summary exists before A4 changes begin.
- [ ] `A4-01-PLAN.md` — Pure preset transform model for fanout/pipeline/swarm/watchers, fixed cycle order, count-weighted ratios, and id-preserving capacity handling.
- [ ] `A4-02-PLAN.md` — Controlled titlebar switcher, `custom` state, `Cmd+G` cycle injection, and GridRoot/App ownership wiring.
- [ ] `A4-03-PLAN.md` — Rust versioned layout schema plus safe `.voss/layouts/<name>.json` save/load/list/default commands.
- [ ] `A4-04-PLAN.md` — Frontend save/load command wrappers, exact command copy, loaded-layout remap semantics, and default-layout apply path.
- [ ] `A4-05-PLAN.md` — Requirement-level acceptance, e2e smoke, full verification, and manual Variant B visual sign-off.

---

### Phase A5: voss-app Project Open

**Goal:** Folder picker, recent workspaces list, `.voss/` directory lazy creation, git branch detection, optional project-less mode.

**Requirements (locked at SPEC):** WS-01..0N
- WS-01 `⌘O` folder picker; drag-drop folder onto app icon to open.
- WS-02 Recent workspaces list (last 10, pinned favorites). Stored at `~/.config/voss-app/recents.json`.
- WS-03 `.voss/` dir lazily created on first action that needs it (settings write, layout save) — never auto on project open in L1.
- WS-04 Git branch read via `git2` Rust crate (no shelling out). Surfaced in status bar (A9).
- WS-05 Project-less mode supported — app launches and runs without any folder open.
- WS-06 New panes inherit project cwd; project-less panes inherit `$HOME`.
- WS-07 Switch project via palette ("Open recent", "Close project").

**Success Criteria (proposed):**
1. Open folder picker → select folder → panes inherit cwd.
2. Quit + reopen most-recent project from start screen.
3. Launch without a project → fully functional empty-pane workflow.
4. `.voss/` doesn't appear until a setting changes or layout is saved.

**Cross-cutting constraints:**
- CONCEPT §10 Q5 (project-less) and Q7 (`.voss/` timing) must close before SPEC.

---

### Phase A6: voss-app Session Persist

**Goal:** Pane tree, per-pane cwd + shell choice, and truncated scrollback restore across app restart. Live processes are NOT auto-relaunched in L1.

**Requirements (locked at SPEC):** PER-01..0N
- PER-01 On quit: pane tree (geometry + cwds + shells), focused pane, active layout preset, last 2k scrollback lines per pane → `.voss/session.json`.
- PER-02 On launch with project: read `session.json`, reconstruct panes with stored geometry. Each pane shows `[restored]` banner with scrollback truncated to 2k lines; user re-runs commands manually.
- PER-03 Project-less mode persists at `~/.config/voss-app/global-session.json`.
- PER-04 Schema versioned `{"version": 1}` with forward-migration policy (unknown future versions decline gracefully).
- PER-05 Storage format: JSON in L1 (SQLite reserved for L2 cells.sqlite).
- PER-06 Concurrent-app safety: portalocker or equivalent flock on session file write.

**Success Criteria (proposed):**
1. Quit app with 4 panes open across 2 splits → reopen → exact layout restored.
2. Project-less session restores last-used pane on launch.
3. Corrupted `session.json` falls back to default layout with non-fatal toast.

**Cross-cutting constraints:**
- Scrollback cap (2k lines) configurable in settings but locked default.
- No live-process restart in L1 — that's an explicit non-feature.

---

### Phase A7: voss-app Command Palette + Keymap

**Goal:** Command palette (`⌘P` quick-open, `⌘⇧P` all commands), VSCode-default keymap profile with tmux-friendly additions, user custom-map override via `.voss/keymap.json`.

**Requirements (locked at SPEC):** CMD-01..0N
- CMD-01 `⌘P` opens fuzzy folder picker (file-open deferred to L4 editor pane). v0 stretch: jump-to-layout by name.
- CMD-02 `⌘⇧P` opens command palette with all commands, fuzzy-matched.
- CMD-03 v0 command catalog covers: Window · Pane · Layout · Project · Settings · Help.
- CMD-04 Recent commands sticky in fuzzy ranking.
- CMD-05 Keymap profiles: VSCode-default ships; tmux-friendly adds `⌘B` prefix mode; user override via `.voss/keymap.json`.
- CMD-06 Keymap JSON validated on load; invalid entries surfaced as toast.
- CMD-07 Palette renders Variant B aesthetic — mono, dim/bright, glyph affordances for command category.

**Success Criteria (proposed):**
1. Every v0 command (per FEATURES §L1.5.3 catalog) findable via palette.
2. Customize one keybinding via `.voss/keymap.json` and reload → new binding active.
3. Switch to tmux profile → `⌘B`-then-`%` splits vertically.

**Cross-cutting constraints:**
- Command implementation = web component (not Tauri-native menus) — decision locked at SPEC.
- Native OS menus (mac menubar, win/linux menu) wrap the same command registry.

---

### Phase A8: voss-app Settings + Theme

**Goal:** Two-pane settings UI (search + categories left, form right) backed by JSON files. Variant B token system applied as theme. Font, shell, telemetry-consent UX all live here.

**Requirements (locked at SPEC):** CFG-01..0N
- CFG-01 User settings: `~/.config/voss-app/settings.json`. Workspace settings: `.voss/settings.json`. Workspace wins.
- CFG-02 Two-pane UI: search + nav left (Appearance · Terminal · Layout · Keybindings · Project · Updates · Telemetry), form right.
- CFG-03 Each form value has "Edit as JSON" link → opens raw settings file in OS default editor.
- CFG-04 Theme tokens delivered as CSS variables (sketch 001 Variant B canonical set). Token override via `.voss/theme.css` or settings.
- CFG-05 Font (family + size + line-height), cursor shape, scrollback size, default shell all configurable.
- CFG-06 Telemetry section: all toggles OFF default. Crash reports + usage analytics opt-in, both clearly labelled.
- CFG-07 Settings hot-reload: change → next pane open uses new defaults; live panes ask before retroactive changes.

**Success Criteria (proposed):**
1. Change theme tokens via UI → all panes + chrome update without restart.
2. Change default shell via UI → next new pane uses it.
3. Telemetry toggles persist; off-state prevents any network call.

**Cross-cutting constraints:**
- CONCEPT §10 Q9 (telemetry policy) must close before SPEC.
- Settings schema validated by JSONSchema or similar (decision at SPEC).

---

### Phase A9: voss-app Status Bar

**Goal:** Bottom status bar: project · branch · active pane info · pane count · cost-meter stub · notifications bell. Click any cluster for popover detail.

**Requirements (locked at SPEC):** BAR-01..0N
- BAR-01 Left cluster: project name (click → recents), git branch (read-only display).
- BAR-02 Center cluster: focused pane cwd · shell · pid.
- BAR-03 Right cluster: pane count `▢ N`, notifications bell with badge, settings cog. **No cost meter slot in L1** (Q6 decision — added in L2 with cell promotion).
- BAR-04 Click clusters → popovers with full detail (focus history, branch switcher placeholder, notification log).
- BAR-05 Status bar height fixed (22px Variant B), single dense line, mono font.
- BAR-06 Updates on every focus change + every git ref change (file watcher).
- BAR-07 Notifications bell shows last 100 events, clearable.
- BAR-08 Project-less mode: left cluster shows "no project · ⌘O to open" instead of name/branch.

**Success Criteria (proposed):**
1. Branch updates within 500ms of `git checkout` in any pane.
2. Pane count updates instantly on split/close.
3. Project-less status bar renders without branch/project clusters.
4. Notification log persists across restart (last 50).

**Cross-cutting constraints:**
- Q6 closed: no cost meter in L1. L2 status bar work will add the slot (planned minor reflow accepted).

---

### Phase A10: voss-app Onboarding + Release Pipeline (v0 SHIP GATE)

**Goal:** First-run wizard, empty-state UI, soak-test hardening, AND the entire release pipeline (signing + 3 distribution channels + auto-update + version-sync). This is the final gate — the app does not release until A1–A9 are built and stable. All distribution work deferred from A1 lands here.

**Requirements (locked at SPEC):**

*Onboarding + polish — OBD-01..0N:*
- OBD-01 First-run wizard: welcome → pick theme → pick shell → done. No API keys requested (L1 has no Voss).
- OBD-02 Empty-state UI for project-less new window: prompt "Open folder" or "Start without a project".
- OBD-03 Empty pane area shows keyboard hint `⌘\` split / `⌘O` open project.
- OBD-04 Keybind cheatsheet modal via Help menu, scrollable, categorized.
- OBD-05 In-app docs link to website docs; changelog modal.
- OBD-06 Crash reporter pipeline (off by default; opt-in CFG-06): captures stderr + last 500 log lines + system info on panic, queues for upload.
- OBD-07 24-hour soak test: 8 panes, mixed alt-screen + scrolling output, no PTY leaks, no memory growth > 100MB.
- OBD-08 Bug-report flow: Help → "Report Issue" opens prefilled GitHub issue with app version + platform.

*Release pipeline — REL-01..0N (deferred from A1 per 2026-05-16 decision):*
- REL-01 CI matrix builds on tag: mac-13 (arm64 + x64), ubuntu-22 (x64 + arm64), windows-2022 (x64).
- REL-02 Code-signing: mac Developer ID + notarization, win Authenticode. Certs procured (procurement is a blocking sub-task — start early).
- REL-03 Direct-download channel: signed DMG / AppImage / MSI on GitHub Releases.
- REL-04 Tauri auto-updater wired against GitHub Releases for the direct channel.
- REL-05 Homebrew cask channel: `brew install --cask voss-ade`, auto-bumped on release via separate tap repo.
- REL-06 npm channel: `@vosslang/cli voss app` subcommand launches the GUI; wrapper downloads/bundles the platform binary on first invoke; version-pinned against the M6 npm wrapper.
- REL-07 Single GitHub release tag fans out to all three channels, version-synced; channel-specific release notes generated.
- REL-08 All artifacts + store metadata use **Voss ADE** ship name (Q1).

**Success Criteria (proposed):** **THE v0 SHIP GATE** (mirrors FEATURES §L1 acceptance checklist):
1. Install on mac/linux/win from a **signed** artifact (direct channel).
2. `brew install --cask voss-ade` works on mac.
3. `npm i -g @vosslang/cli && voss app` launches the GUI.
4. Auto-updater pulls a newer release and prompts user.
5. All three channels resolve to the same version from one release tag.
6. Open app → empty state works.
7. Open folder → status bar populates.
8. 2×2 grid via 3 splits, all independent shells.
9. `⌘1-4` focus + click focus works.
10. Switch layout preset → reorder, no kill.
11. Resize via mouse + keyboard.
12. Save + reload layout via palette.
13. `vim`/`htop`/`tmux` work inside a pane.
14. Copy/paste across panes.
15. Quit + reopen restores layout.
16. Settings persist (theme + font + shell + keybind).
17. 24hr soak with 8 panes — no crashes, no PTY leaks.
18. Crash reporter activates if app panics (opt-in pipeline tested).
19. Bug-report flow opens prefilled GH issue.

**Cross-cutting constraints:**
- A10 is the integration + release phase — assumes A1–A9 complete and stable.
- Cert procurement (REL-02) is the long-pole — kick off procurement during A1, even though the wiring lands in A10.
- Failing any acceptance criterion = v0 doesn't ship.

---

## O-prefixed phases: Caged Autonomous Eng Team (ADE Orchestration)

**Track:** Multi-agent orchestration layer on the Python harness. Full design, decision log (21 decisions), `.voss` strawman, and residual-risk register in **`.planning/ORCHESTRATION-PLAN.md`**.

**Thesis:** Every autonomous agent-team product today is an unbounded blackbox. Voss already ships per-call budgets, confidence gates, write-scope locks, and replayable audit. The ADE orchestrator is the showcase: **a fully autonomous AI engineering team inside a *provable* cage — hard budget, global scope ceiling, an independent judge gating every state transition, fully replayable.** "Audit the cage," not "trust the swarm."

**Not a pivot.** Showcase skin on the harness, not a parallel build. Single-agent harness must be boring-solid first. The orchestrator + board + rituals are expressed in `.voss`; the harness owns execution. Builds on M13 (raw `spawn`/`gather`) — O-phases add the cage.

**Roles:** Human (idea + final sign-off) · **Engineering Manager** (LLM lead: idea→tickets/AC/DoD, runs board, dispatches specialists) · **Engineer roster** (backend/frontend/ui/ai, per-role scope+tools) · **Reviewer-A** (re-derives bar + authors tests/eval from the *original idea*) · **Reviewer-B** (independent tiered judge: slop/errors/correctness, EM-narrative-blind).

**Cross-O cage invariants (the product is these or it is theater):**
- Budget = security boundary: hard, pre-committed, non-extendable by EM; fans out parent→card.
- Scope: per-card `edit_scope` + global ceiling; union of card scopes ≤ ceiling.
- Confidence is independent (Reviewer-B); threshold `p` is per-card-risk, human-declared, EM-immutable.
- Audit bar = the **original human idea** (Reviewer-A re-derives), never EM-authored AC.
- Engineers cannot author the verification that gates them (Reviewer-A owns tests/eval).
- Liveness guaranteed: reserved non-spendable drain budget + timeout→Blocked.
- The session-tree recorder **is** the human review product, not telemetry.

**Open residual risks (carried, none fatal — full register in ORCHESTRATION-PLAN.md §7):**
- Standup→`semantic.memory` poisoning (Leak 6) — **unaddressed**, O6 mitigation candidate.
- Reviewer-A misread propagates — requires a written invariant: Reviewer-B may fail idea-divergent A-verification.
- Human sign-off is overloaded (correctness + misroute + killed-card review) — O6 forcing-function candidate.
- "~80% reuse" is false — real build is substantial across O1–O6; do not plan against the reuse number.

**Dependency chain:** O1 (keystone) → O2 → O3 → O4 → O5 → O6.

---

### Phase O1: Session-Tree Substrate + Budget Fan-out

**Goal:** Parent→child session tree in `recorder.py`/`session.py` so every spawned agent is a first-class recorded node with its own budget, scope, and audit. The keystone — every other O-phase renders off this.

**Scope:** Parent→card budget fan-out (`(envelope − reserve) / total WIP` floor); reserved non-spendable drain budget guaranteeing every in-flight card reaches a verdict; hard non-extendable caps (no "ask for more tokens" path); session-tree recorder schema. Reuses/extends `RunRecorder`, `SessionRecord`.

**Requirements (locked at SPEC):** SPEC-1 (harness session tree + parent linkage), SPEC-2 (per-card budget allocation + fan-out invariant), SPEC-3 (reserved drain → terminal finalize), SPEC-4 (non-extendable cap + recorded attempts), SPEC-5 (strict harness-additive blast radius) — 5 locked in `O1-SPEC.md`.

**Plans:** 2 plans, 2 waves

Plans:
- [ ] O1-01-PLAN.md — Session-tree substrate: SessionTreeNode + SessionTreeManager allocator (fan-out invariant) + D-04 guarded mutator + per-node file persistence (D-01/D-02/D-04)
- [ ] O1-02-PLAN.md — D-03 always-finalize boundary in run_subagent: finalize_node guard + reserved-drain terminal finalize + parent linkage at spawn (D-03)

**Cross-cutting:** No board, no reviewers, no EM in O1 — pure substrate. `subagents.py` gains budget/scope/recorder plumbing it lacks today.

---

### Phase O2: `.voss team{}` Spec + Specialist Roster

**Goal:** A `.voss team{}` block parser that compiles to an enriched `SubagentRegistry` + specialist roster, with `ceiling`/`p` declared above the EM and immutable to it (the cage is syntax).

**Scope:** `SubagentSpec` extended with model/mode/scope/budget/tools per role; backend/frontend/ui/ai roster; EM-immutable `ceiling`/`p` blocks; per-role permission/tool profile (AI role gets `net`). Depends O1 (specs carry budget/scope that need the tree).

**Requirements:** OTEAM-01..0N — TBD by `O2-SPEC.md`.

---

### Phase O3: Board State Machine + Gated Transitions

**Goal:** The Kanban board as the orchestrator state machine — columns, per-column WIP, gated transitions.

**Scope:** `Backlog→Planned→InProgress→InReview→Blocked→Done`; per-column WIP (backpressures reviewer cost); confidence gate only on artifact transitions; →Done double gate (code: tests; AI: eval); critic loop ceiling(≈3)+budget→Blocked; column/card timeout→Blocked liveness. Depends O1, O2.

**Requirements:** OBRD-01..0N — TBD by `O3-SPEC.md`.

---

### Phase O4: Reviewer A/B Split

**Goal:** Independent bar/verification authoring (A) cleanly split from independent judgment (B), restoring two independent sources at →Done.

**Scope:** Reviewer-A re-derives the bar from the original idea + authors verification (deterministic tests for code; eval harness for AI via `voss/eval/` reuse). Reviewer-B: independent session/model, no shared memory with A or EM, tiered (fast intermediate / strong at →Done), checks slop/errors/correctness, sees `[artifact, acceptance, repo, original_idea]`, **explicit authority to fail a card whose A-verification diverges from the idea** (residual-2 invariant). Depends O2, O3.

**Requirements:** ORVW-01..0N — TBD by `O4-SPEC.md`.

---

### Phase O5: Engineering Manager Loop

**Goal:** The EM autonomous lead loop — idea in, board run to Done, human sign-off only.

**Scope:** Full-authority autonomous loop; idea→tickets/AC/DoD (worker scaffolding, not the audit bar); specialist dispatch from roster + `routing_rationale` per card; kill/re-scope with preserved lineage; board mutation bounded by the cage (cannot rewrite `ceiling`/`p`, cannot invent agents). Depends O1–O4.

**Requirements:** OEM-01..0N — TBD by `O5-SPEC.md`.

---

### Phase O6: Audit Product + Calibration + Liveness Hardening

**Goal:** The human review product + the monitoring that keeps the cage honest.

**Scope:** Session-tree as primary review surface; killed/re-scoped cards + routing rationale foregrounded first-class; reviewer calibration telemetry (B-verdict vs. A-verification, now independent) + sampled human slop-rejection spot-audit; reserve/timeout liveness wiring surfaced; **sign-off forcing function** (mandatory killed-card + misroute diff before approve is available); Leak-6 (`semantic.memory` poisoning) mitigation candidate. Depends O5.

**Requirements:** OAUD-01..0N — TBD by `O6-SPEC.md`.

**Cross-cutting:** O6 closes (or explicitly defers) the residual-risk register from `ORCHESTRATION-PLAN.md §7`. Leak 6 may remain a documented accepted gap if mitigation proves out-of-scope.

---

## Coverage

| Phase | Requirements | Count |
|---|---|---:|
| M0 | SCOPE-01..04 | 4 |
| M1 | CLIH-01..10, CTRL-01..09 | 19 |
| M2 | COG-01..08 | 8 |
| M3 | LANG-01..10 | 10 |
| M4 | DOG-01..08 | 8 |
| M5 | EVAL-01..05 | 5 |
| M6 | NPM-01..05 | 5 |
| M7 | SDK-01..05 | 5 |
| **v0.1 Total** |  | **64 / 64** |
| M8 | MEM-01..07 | 7 |
| M9 | TUI-01..10 | 10 |
| M10 | CODE-01..07 | 7 |
| M11 | VTOOL-01..05 | 5 |
| M12 | MCP-01..0N | TBD by `M12-SPEC.md` |
| M13 | MAG-01..MAG-08 | 8 |
| M14 | WATCH-01..0N | TBD by `M14-SPEC.md` |
| M15 | SKILL-01..06 | 6 |
| **T-phases (daily-driver gap closure)** | | |
| T6 (v0.1.1 patch) | SLASH-01..07 | 7 (Complete) |
| T1 | ITER-01..06 | 6 |
| T4 | CACHE-01..04 | 4 |
| T2 | PAR-01..04 | 4 |
| T3 | NET-01..07 | 7 |
| T5 | SHELL-01..05 | 5 |
| T7 | SKL-01..06 | 6 |
| T8 | INPUT-01..05 | 5 |
| **T-total** | | **42** |
| **A-phases (voss-app desktop ADE Layer 1)** | | |
| A1 | SHL-01..0N | TBD by `A1-SPEC.md` |
| A2 | PTY-01..0N | TBD by `A2-SPEC.md` |
| A3 | GRD-01..0N | TBD by `A3-SPEC.md` |
| A4 | LAY-01..0N | TBD by `A4-SPEC.md` |
| A5 | WS-01..0N | TBD by `A5-SPEC.md` |
| A6 | PER-01..0N | TBD by `A6-SPEC.md` |
| A7 | CMD-01..0N | TBD by `A7-SPEC.md` |
| A8 | CFG-01..0N | TBD by `A8-SPEC.md` |
| A9 | BAR-01..0N | TBD by `A9-SPEC.md` |
| A10 | OBD-01..0N + REL-01..0N | TBD by `A10-SPEC.md` |
| **A-total (Layer 1)** | | **TBD per SPEC** |
| **O-phases (ADE orchestration — Caged Autonomous Eng Team)** | | |
| O1 | OST-01..0N | TBD by `O1-SPEC.md` |
| O2 | OTEAM-01..0N | TBD by `O2-SPEC.md` |
| O3 | OBRD-01..0N | TBD by `O3-SPEC.md` |
| O4 | ORVW-01..0N | TBD by `O4-SPEC.md` |
| O5 | OEM-01..0N | TBD by `O5-SPEC.md` |
| O6 | OAUD-01..0N | TBD by `O6-SPEC.md` |
| **O-total** | | **TBD per SPEC** |

All v0.1 requirements mapped. v0.2 requirement IDs are minted by `/gsd-spec-phase` per phase. T-phase requirement IDs locked in this roadmap; full SPEC pending per-phase `/gsd-spec-phase`. A-phase requirement IDs are placeholder prefixes; per-phase SPEC locks the count + exact text.

---

## v0.2 Candidate Phases

Identified but **not committed to a milestone**. Each lands when its trigger
condition fires — usually real-user demand surfacing during v0.1 dogfood.

> **Note:** M7 (SDK Polish) was originally listed here as a v0.2 candidate
> on 2026-05-12; it was promoted to a formal v0.1 phase on 2026-05-13. See
> "Phase M7: SDK Polish" above.

### Other v0.2 candidates (not yet phased)

- **DIST-01** Rust harness shell — trigger: bundled-Python (M6) startup
  latency or wheel size proves painful in real use.
- **DIST-02** Homebrew distribution — trigger: macOS install friction
  surfaces despite npm wrapper.
- **DIST-03** MCP bridge — **RETIRED 2026-05-14.** Promoted to formal phase
  **M12 MCP Bridge (CAPS-01c)** — see "Phase M12" above.
- **EDIT-01/02** Tree-sitter + VSCode marketplace — trigger: language users
  ask for editor support beyond the existing scratch extension.
- **LING-01** GitHub Linguist upstream PR — trigger: enough public `.voss`
  code exists for syntax recognition to matter.
- **JS-SDK** TS/JS library — trigger: real JS-side embedders ask for a
  library API (not just `npx voss`).
- **TEAM-*** / **WEB-*** — far post-v0.1.

### Coding-agent v0.2 phases *(planted 2026-05-14 via /gsd-explore, promoted to formal phases same day)*

The three CAPS/TUI/MEM seeds were promoted to formal phases on 2026-05-14.
After `M10-SPEC.md` scope-cut M10 to codebase intelligence only, the other
five capabilities from the original CAPS-01 seed were also promoted to
formal follow-on phases M11–M15. Seed files remain in `.planning/seeds/`
as the source brainstorm; the thesis note remains in `.planning/notes/`
as cross-phase context.

- **MEM-01 → M8 Project Memory** — see
  [`seeds/project-memory-voss-md.md`](seeds/project-memory-voss-md.md).
- **TUI-01 → M9 TUI Shell** — see
  [`seeds/tui-shell-textual.md`](seeds/tui-shell-textual.md).
- **CAPS-01 → M10–M15** — see
  [`seeds/agent-capability-surface.md`](seeds/agent-capability-surface.md).
  Originally one bundled phase; split during M10-SPEC into:
  - **M10 Codebase Intelligence (CAPS-01a)** — locked SPEC, ready to discuss.
  - **M11 Voss-aware Tools (CAPS-01b)** — scaffolded, no SPEC yet.
  - **M12 MCP Bridge (CAPS-01c)** — scaffolded, no SPEC yet; subsumes retired DIST-03.
  - **M13 Multi-agent in Chat (CAPS-01d)** — scaffolded, no SPEC yet.
  - **M14 Long-running Tasks + Watch (CAPS-01e)** — scaffolded, no SPEC yet.
  - **M15 Skill / Plugin Marketplace (CAPS-01f)** — scaffolded, no SPEC yet.
- **Thesis note** (not a phase) — Voss agent unfair advantage. See
  [`notes/voss-agent-unfair-advantage.md`](notes/voss-agent-unfair-advantage.md).
  Re-read before scoping M8 / M9 / M10–M15.

These do NOT block v0.1 ship. Listed so the roadmap has a memory of what's
next without forcing premature commitment.

## Backlog

Unsequenced parking-lot ideas (999.x). Promote with `/gsd:review-backlog`.

### Phase 999.1: voss-app Agents launcher + manager (BACKLOG)

**Goal:** A titlebar/navbar "Agents" affordance to manage and spawn agents, plus
shippable launch prefixes that open a new terminal pane and launch a specific
agent CLI — named targets: Claude (`claude`), Codex, Gemini, OpenCode.
**Requirements:** TBD
**Plans:** 0 plans

Context: validated when Claude Code ran interactively inside the A2 PTY pane
(header showed `claude.exe` via OSC title). Candidate **A-track phase AFTER
A3** — agent panes are grid panes, so the A3 Grid Engine (Warp-style locked
tiling) must land first. Likely shape: (a) agent registry config
(name → launch command + cwd), (b) titlebar "Agents" panel to manage/spawn,
(c) prefix dispatch spawning a new A3 grid pane running the agent CLI (reuse
A2 `PtyTransport` + A3 split). See session memory
`voss-agents-launcher-feature`, `voss-app-grid-warp-parity`,
`voss-app-track-build-order`.

Plans:
- [ ] TBD (promote with /gsd:review-backlog when ready)

### Phase 999.2: voss-app focused-pane resize keybind ⌘/Win +/− (BACKLOG)

**Goal:** `⌘ +` / `⌘ -` (Windows key on Windows — reuse the A1-03
`@tauri-apps/plugin-os` platform gate) grows/shrinks the **focused** terminal
pane within the tiling grid.
**Requirements:** TBD (fold into A3 keymap when A3 executes)
**Plans:** 0 plans

Context: this belongs to **A3 (Grid Engine)**, which already plans
split/fork/close/equalize + focus+resize (`⌘=` global equalize). This entry
exists so the `⌘+`/`⌘-` focused-pane grow/shrink keybind is not lost — when
A3 is executed (or replanned), add it to the A3 keymap/requirements rather
than building a standalone phase. Snap-locked tiling, no free-canvas resize
(memory `voss-app-grid-warp-parity`).

Plans:
- [ ] TBD (fold into A3 keymap on A3 execution / promote with /gsd:review-backlog)
