# Roadmap: Voss v0.1 Harness MVP

**Created:** 2026-05-10
**Mode:** Harness-led vertical slice
**Granularity:** M-prefixed milestone phases
**Requirements covered:** 54 / 54
**Source:** `.vscode/voss_v_0_1_scope_lock.md`

## Phase Order

| Phase | Name | Goal | Requirements | Success Criteria |
|---|---|---|---|---|
| M0 | Scope Lock | Align planning docs around harness-led v0.1 plus `.voss` as workflow control layer | SCOPE-01..04 | 3 |
| M1 | Harness Happy Path | Make the Python harness usable on a real repo with minimal persistence | CLIH-01..10, CTRL-01..09 | 6 |
| M2 | Project Cognition | Make Voss remember useful project facts across sessions | COG-01..08 | 5 |
| M3 | Language Validation | Prove `.voss` is useful for real AI workflow control | LANG-01..10 | 5 |
| M4 | Voss-authored Harness Loop | Dogfood the language on the harness itself | DOG-01..08 | 4 |
| M5 | Eval and Distribution Prep | Measure quality and prepare packaging after the Python loop works | EVAL-01..05 | 4 |

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
| **Total** |  | **54 / 54** |

All v0.1 requirements mapped.
