# Roadmap: Voss v0.1 Harness MVP

**Created:** 2026-05-10
**Mode:** Harness-led vertical slice
**Granularity:** M-prefixed milestone phases
**Requirements covered:** 59 / 59
**Source:** `.vscode/voss_v_0_1_scope_lock.md`
**Last updated:** 2026-05-12 — added M6 npm wrapper phase

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
- [ ] M5-06-PLAN.md — Wave 5 wheel-in-tempvenv smoke + README install polish

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
| **Total** |  | **59 / 59** |

All v0.1 requirements mapped.
