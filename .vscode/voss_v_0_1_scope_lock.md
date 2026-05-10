# Voss v0.1 Scope Lock

## Executive Summary

Voss v0.1 should ship as an **AI-native coding harness with a first-class programming language control layer**.

The MVP should not be framed as “a full Python fork” or “a general-purpose replacement for Python.” The more credible and useful wedge is:

> Voss helps developers and vibe coders control AI coding agents through persistent project memory, bounded execution, explainable decisions, and a compact `.voss` language for agent workflows.

The harness is the product surface. The language is the durable control plane.

This keeps the strongest parts of the current repo intact:

- `voss_runtime/` provides the AI workflow primitives.
- `voss/` provides parser, analyzer, codegen, diagnostics, and CLI compiler verbs.
- `voss/harness/` provides the Python harness implementation path.
- `crates/` provides the later Rust distribution path.
- `.voss` remains strategically important, especially for dogfooding the harness loop.

The immediate goal is to avoid splitting effort across too many fronts. v0.1 should prove one thing:

> A developer can use Voss to safely plan, execute, inspect, and resume AI-assisted code work in a real repository, while the most important agent logic is expressible in Voss syntax.

---

## Product Definition

### One-line Definition

Voss is an AI-native development harness and programming language for controlled agentic software development.

### Longer Definition

Voss combines a CLI coding harness, persistent project cognition, bounded agent execution, and a Python-targeting language designed around AI workflow primitives: confidence gates, context budgets, semantic routing, agents, memory, fallbacks, tools, and prompt structures.

The harness helps users operate AI coding agents safely. The language lets those workflows become explicit, inspectable, repeatable programs instead of prompt soup.

---

## Core User

### Primary User

The initial user is a technically capable builder who uses AI to write or modify software but does not want to babysit chaotic agents all day.

This includes:

- vibe coders
- solo founders
- product-minded builders
- PMs who can reason about systems but are not traditional full-stack engineers
- developers who use Claude Code, Codex, Cursor, Goose, Cline, or similar tools and feel the limitations

### Secondary User

Traditional developers who want safer agent workflows:

- scoped edits
- reproducible plans
- test gates
- session persistence
- diff inspection
- less context collapse

---

## Core Pain

Current AI coding harnesses are powerful but unstable across larger repo tasks.

The recurring pain points are:

1. **Context collapse**
   - Agents forget architecture decisions.
   - Long sessions drift.
   - Users manually re-explain project context.

2. **Broad unsafe edits**
   - Agents edit too many files.
   - Agents change unrelated systems.
   - Rollback and review are annoying.

3. **Architectural entropy**
   - Duplicate codepaths appear.
   - Existing patterns are ignored.
   - Generated code works locally but damages maintainability.

4. **Opaque reasoning**
   - The user cannot easily ask why an action was taken.
   - Confidence is not captured as a first-class runtime value.
   - Agent decisions are buried in chat history.

5. **Prompt soup**
   - Reusable AI workflows are stored as markdown, ad hoc prompts, or hidden code.
   - There is no compact language for AI-native control flow.

Voss v0.1 should attack these pains directly.

---

## MVP Promise

Voss v0.1 promises:

> Give the agent a repo task. Voss analyzes the project, creates a scoped plan, executes through controlled tools, validates the result, records decisions, and can resume later without starting from zero.

The language promise is:

> The agent loop and reusable AI workflows can be expressed in `.voss` using first-class constructs for agents, context budgets, confidence gates, semantic matching, tools, memory, and fallbacks.

---

## Positioning

### Do Say

- AI-native coding harness
- programming language for agent workflows
- controlled agentic development
- persistent project cognition
- bounded AI execution
- Python-targeting AI workflow language
- safer vibe coding

### Do Not Lead With

- Python fork
- general-purpose programming language
- new Python replacement
- autonomous coding agent
- full IDE replacement

### Preferred Framing

> Voss is a coding harness first and a programming language where it matters: defining, checking, and running AI-native development workflows.

---

## What Ships in v0.1

v0.1 should ship a tight vertical slice across five capabilities.

## 1. CLI Harness

Required commands:

```bash
voss                 # launch interactive harness REPL
voss chat            # explicit REPL alias
voss do "<task>"     # one-shot agent task
voss edit <path>     # scoped edit session
voss resume [id]     # resume a saved session
voss sessions        # list sessions
voss tools           # list registered tools
voss doctor          # diagnose setup
voss config          # open config
```

Compiler commands remain separate and should not be overloaded:

```bash
voss compile <file.voss>
voss run <file.voss>
voss check <path>
voss init <name>
voss ast <file.voss>
```

Important naming rule:

- `voss run` executes `.voss` programs.
- `voss do` executes natural-language agent tasks.

This avoids ambiguity and preserves the programming language as a real layer.

---

## 2. Persistent Project Cognition

Voss should create and maintain project-local state.

Recommended project structure:

```text
.voss/
├── project.json
├── architecture.md
├── constraints.yml
├── permissions.yml
├── validation.yml
├── decisions/
├── sessions/
├── plans/
├── checkpoints/
├── memory/
└── indexes/
```

Recommended cache structure:

```text
.voss-cache/
├── repo.idx
├── harness/
├── generated/
└── tmp/
```

Principle:

> `.voss/` is durable project knowledge. `.voss-cache/` is rebuildable machine state.

Every agent run should save useful structured memory:

- task goal
- plan
- files inspected
- files changed
- files explicitly avoided
- assumptions
- decisions
- risks
- validation commands
- failures
- final diff summary
- follow-up recommendations

---

## 3. Controlled Agent Execution

The harness should expose a small, safe tool registry.

Required v0.1 tools:

- `fs_read`
- `fs_glob`
- `fs_grep`
- `fs_write`
- `fs_edit`
- `shell_run`
- `git_status`
- `git_diff`
- `voss_check`

Execution should support three modes:

```text
plan  = read-only planning
edit  = scoped edits with approval
auto  = broader execution, still permissioned
```

Required controls:

- path jail rooted at `--cwd`
- permission prompts
- deny/allow/always choices
- diff preview before apply
- shell allowlist
- timeout on shell commands
- no provider API keys in session payloads

---

## 4. Voss Language Control Layer

The programming language remains part of the MVP, but its job is specific:

> `.voss` is the language for AI workflow control, not a general Python replacement.

v0.1 language constructs worth preserving:

- `probable<T>`
- confidence gates: `intent @ p >= 0.80`
- `ctx(budget: N tokens)`
- `within budget(...) { } fallback { }`
- `match similar(...)`
- `agent`
- `spawn`
- `gather`
- `memory.episodic`
- `memory.semantic`
- `memory.working`
- `@tool`
- `prompt`
- `try/catch`
- `use`

These are the constructs that make Voss materially different from Python plus prompts.

The target is not to support all Python syntax. The target is to make AI workflows shorter, safer, and compiler-checkable.

---

## 5. Dogfooded Harness Loop

The strategic milestone is:

```text
voss/harness/agent/
├── loop.voss
├── router.voss
├── planner.voss
├── executor.voss
└── reviewer.voss
```

This should not block the earliest harness MVP, but it should remain a core v0.1/v0.2 objective.

The strongest dogfood story is:

> The Voss harness is eventually authored in Voss.

That forces the language to solve real harness problems:

- routing user intent
- planning tool calls
- enforcing budgets
- handling fallbacks
- checking confidence
- coordinating agents
- calling tools
- maintaining memory

---

## Canonical Demo Workflow

The v0.1 demo should be repo-centric.

```bash
voss doctor
voss do "Analyze this repo and summarize the architecture"
voss do "Plan adding GitHub OAuth using the existing auth patterns" --mode plan
voss do "Apply the approved OAuth plan" --mode edit
voss check .
voss resume
```

Expected behavior:

1. Voss detects project type and important files.
2. Voss builds or updates `.voss/architecture.md`.
3. Voss creates a scoped plan under `.voss/plans/`.
4. Voss asks for approval before risky edits.
5. Voss applies edits only inside approved file scope.
6. Voss runs validation commands.
7. Voss records the session and decisions.
8. Voss can resume the task later.

---

## Language Demo Workflow

A parallel demo should prove the language layer.

```bash
voss init support-bot
cd support-bot
voss check samples/support.voss
voss run samples/support.voss
```

The sample should demonstrate:

- semantic routing with `match similar`
- confidence-gated intent classification
- `ctx` budget
- fallback handling
- an agent definition
- a tool annotation
- memory usage

Target story:

> What takes hundreds of lines of Python agent boilerplate becomes a readable `.voss` workflow.

---

## Required v0.1 Outputs

### CLI Outputs

- interactive REPL
- one-shot task execution
- tool traces
- compact status line
- JSON/NDJSON mode for automation
- session save/resume
- doctor checks

### Project Outputs

- `.voss/architecture.md`
- `.voss/plans/*.md`
- `.voss/sessions/*.json`
- `.voss/decisions/*.md`
- `.voss/permissions.yml`
- `.voss/validation.yml`

### Compiler Outputs

- `.voss` parse/check/compile/run works
- generated Python is readable
- analyzer emits useful warnings
- `voss check` is fast enough to run after edits

---

## What Does Not Ship in v0.1

Explicitly out of scope:

- full Python language parity
- native LLVM/Wasm compilation
- TypeScript target
- package manager
- debugger
- full LSP
- distributed/multi-machine agents
- fine-tuning or training loops
- cloud sync
- team collaboration
- account system
- web UI
- split-pane TUI
- Windows support
- public marketplace
- broad OSS launch campaign

Deferred but strategically relevant:

- Rust harness shell
- MCP bridge
- tree-sitter grammar
- VSCode marketplace release
- GitHub Linguist upstream PR
- full telemetry/eval system

---

## Current Repo Alignment

The current repo already has the bones for this direction.

### Keep as Core

```text
voss_runtime/
```

Purpose:

- runtime primitives for AI workflows
- provider abstraction
- budget/context/confidence primitives
- memory
- tools
- agents

This is essential.

```text
voss/
```

Purpose:

- parser
- analyzer
- codegen
- diagnostics
- compiler CLI
- bridge server

This is essential because the language layer remains a product pillar.

```text
voss/harness/
```

Purpose:

- Python harness implementation
- early product surface
- fastest path to dogfooding

This should be the near-term product focus.

```text
.planning/HARNESS-PLAN.md
```

Purpose:

- current harness roadmap
- should be updated to reflect harness-led MVP and language-as-control-layer framing

```text
samples/
```

Purpose:

- language examples
- future Linguist/sample assets
- product demos

### Keep, But Defer

```text
crates/
```

Purpose:

- later Rust shell
- distribution improvement
- startup performance

Do not delete this work, but do not let it pull attention away from the Python harness until the product loop is proven.

```text
site/
```

Purpose:

- docs and marketing

Keep minimal until v0.1 behavior is locked.

```text
vscode/
```

Purpose:

- syntax and icons

Useful but not MVP-critical.

---

## Recommended Milestones

## M0: Scope Lock

Goal:

- align repo and planning docs around harness-led MVP plus language control layer

Deliverables:

- this document
- updated `PROJECT.md`
- updated `HARNESS-PLAN.md`
- updated roadmap naming

Success criteria:

- no ambiguity between compiler verbs and harness verbs
- clear statement that `.voss` remains central
- Rust clearly deferred until Python harness works

---

## M1: Harness Happy Path

Goal:

- make the harness usable on a real repo with minimal persistence

Required:

```bash
voss doctor
voss do "summarize this repo"
voss do "summarize this diff"
voss edit <file>
```

Capabilities:

- provider auth works
- fs/git/shell tools work
- permissions work
- status rendering works
- basic session snapshot works

Language dependency:

- harness can still be Python-authored in M1
- compiler commands must remain available

---

## M2: Project Cognition

Goal:

- make Voss remember useful project facts

Required:

```bash
voss do "analyze this repo"
voss resume
voss sessions
```

Capabilities:

- `.voss/architecture.md`
- `.voss/plans/`
- `.voss/sessions/`
- `.voss/decisions/`
- semantic index or simpler file index

Success criteria:

- repeated sessions improve rather than restart
- user can inspect the saved project brain

---

## M3: Language Validation

Goal:

- prove `.voss` is useful for real AI workflows

Required:

```bash
voss check samples/classify.voss
voss check samples/support.voss
voss check samples/research.voss
voss run samples/classify.voss
```

Capabilities:

- parser supports representative syntax
- analyzer catches unguarded `probable<T>` usage
- codegen emits readable Python
- runtime examples pass

Success criteria:

- three meaningful `.voss` examples run end-to-end
- generated Python is understandable
- language makes AI workflow code materially shorter

---

## M4: Voss-authored Harness Loop

Goal:

- dogfood the language on the harness itself

Required:

```bash
voss check voss/harness/agent/
```

Capabilities:

- `loop.voss`
- `planner.voss`
- `executor.voss`
- `reviewer.voss`
- compile/cache under `.voss-cache/harness/`

Success criteria:

- bare `voss` can boot through compiled harness logic
- CI fails if harness `.voss` files stop checking
- language regressions hurt immediately, which is good

---

## M5: Eval and Distribution Prep

Goal:

- measure quality and prepare shipping

Capabilities:

- golden tasks
- mean cost tracking
- success rate tracking
- confidence correlation
- package install polish
- Homebrew and Rust deferred unless the Python harness proves real usage

---

## Product Architecture

### Runtime Layer

`voss_runtime/`

Responsibilities:

- `ProbableValue`
- `ContextScope`
- `BudgetScope`
- semantic matching
- memory primitives
- agent primitives
- provider abstraction
- tool schema support

Rule:

> Runtime should stay Python-first because the AI ecosystem is Python-first.

---

### Compiler Layer

`voss/`

Responsibilities:

- parse
- analyze
- generate Python
- check
- compile
- run
- ast debug
- init scaffold
- JSON bridge server

Rule:

> Compiler output should be readable Python that imports `voss_runtime`.

---

### Harness Layer

`voss/harness/`

Responsibilities:

- chat loop
- one-shot task loop
- session handling
- permissions
- tool execution
- rendering
- repo memory
- model routing

Rule:

> Harness should be the first product users actually feel.

---

### Rust Shell Layer

`crates/`

Responsibilities:

- future fast CLI shell
- native provider clients
- native tool sandbox
- renderer
- bridge to Python compiler

Rule:

> Rust should improve distribution and latency after the Python harness proves the workflow. It should not replace the Python compiler/runtime.

---

## `.voss` Language Scope

### Language Goal

The language should make AI workflow patterns first-class.

Voss should replace boilerplate like:

- confidence handling
- context-window compression
- model budget enforcement
- semantic route matching
- agent spawning
- tool schema construction
- memory setup
- fallbacks
- prompt class structure

It should not try to replace Python’s entire standard language surface.

---

## Required Language Constructs for Strategic Differentiation

### `probable<T>`

Purpose:

- make uncertainty explicit
- force confidence gates before plain-value use

Example:

```voss
let intent: probable<string> = classify(message)

if intent @ p >= 0.80 {
  return intent.value
} else {
  return "unknown"
}
```

Why it matters:

- most AI code treats uncertain output as certain
- Voss can warn at compile time

---

### `ctx(budget: N tokens)`

Purpose:

- make context windows explicit
- support compression
- make prompt construction inspectable

Example:

```voss
ctx(budget: 4000 tokens) {
  include repo_summary
  yield ask("Find the auth pattern")
}
```

Why it matters:

- current agent code hides context stuffing inside prompts
- Voss makes it visible and enforceable

---

### `within budget(...) fallback {}`

Purpose:

- runtime budget safety
- fallback behavior as language construct

Example:

```voss
within budget(tokens: 4000, latency: 30s, cost: $0.02) {
  return await expensive_analysis()
} fallback {
  return cached_summary
}
```

Why it matters:

- useful for both product AI apps and the coding harness

---

### `match similar(...)`

Purpose:

- semantic routing as language syntax

Example:

```voss
match message {
  case similar("refund request") => refund_flow(message)
  case similar("angry customer") => escalate(message)
  case _ => general_support(message)
}
```

Why it matters:

- AI workflows route by meaning, not just exact values

---

### `agent`, `spawn`, `gather`

Purpose:

- structured agent workflows
- local async orchestration

Example:

```voss
agent Researcher {
  system: "Research this topic and produce concise findings."
  tools: [web_search]
}

let tasks = topics.map(t => spawn Researcher(t))
let reports = gather(tasks, timeout: 30s)
```

Why it matters:

- makes multi-agent patterns readable without framework boilerplate

---

### `@tool`

Purpose:

- generate provider-compatible tool schema from typed functions

Example:

```voss
@tool
fn search_repo(query: string) -> string {
  return fs.grep(query)
}
```

Why it matters:

- tool schemas are repetitive and error-prone in normal Python

---

## Harness-Language Integration

The harness and language should reinforce each other.

### Harness Uses Compiler

When editing `.voss` files:

- run `voss check`
- parse diagnostics
- feed warnings into the next agent turn
- prevent invalid `.voss` edits from being applied automatically

### Compiler Uses Runtime

Generated Python imports `voss_runtime` for:

- confidence values
- budgets
- memory
- agents
- tools
- context

### Harness Eventually Uses Language

The agent loop should move from Python to `.voss` once compiler/codegen is strong enough.

This is the key dogfood loop.

---

## Critical Product Decisions

## Decision 1: Harness first, language always present

The MVP is harness-led, but the language is not shelved.

Reason:

- harness solves immediate pain
- language creates long-term differentiation
- dogfooding forces language realism

---

## Decision 2: Python compiler/runtime remain Python

The current Python compiler and runtime should stay Python.

Reason:

- Python AI ecosystem is strongest
- generated Python is inspectable
- faster iteration
- avoids premature systems rewrite

---

## Decision 3: Rust is distribution infrastructure, not product strategy yet

Rust port remains planned but deferred.

Reason:

- current risk is product clarity, not CLI cold start
- Rust rewrite before product proof creates drag
- later Rust shell can wrap the proven Python compiler/runtime

---

## Decision 4: `.voss/` is product memory, `.voss-cache/` is machine cache

Reason:

- users should inspect durable project cognition
- cache should be disposable
- keeps git hygiene clear

---

## Decision 5: `voss run` stays language-only

Reason:

- avoids command ambiguity
- reinforces `.voss` as a real programming layer
- `voss do` becomes the natural-language task verb

---

## Immediate Implementation Priorities

## Priority 1: Update Planning Docs

Update:

- `.planning/PROJECT.md`
- `.planning/HARNESS-PLAN.md`
- `.planning/ROADMAP.md`
- `PRD.md`

Goal:

- align language and harness under one product story
- avoid “compiler first vs harness first” confusion

---

## Priority 2: Build the Harness Happy Path

Implement or verify:

- `voss do`
- bare `voss` REPL
- `voss doctor`
- fs/git/shell tools
- permission tiers
- basic session save
- readable render output

---

## Priority 3: Add Project Cognition Files

Implement:

- `.voss/architecture.md`
- `.voss/plans/`
- `.voss/sessions/`
- `.voss/decisions/`
- `.voss/permissions.yml`
- `.voss/validation.yml`

Start with simple markdown and JSON. Do not overbuild embeddings first.

---

## Priority 4: Keep `.voss` Samples Green

Ensure these compile/check/run:

- `samples/classify.voss`
- `samples/support.voss`
- `samples/research.voss`

These are not just tests. They are the language product demo.

---

## Priority 5: Define Harness-in-Voss Target

Create placeholder files:

```text
voss/harness/agent/loop.voss
voss/harness/agent/planner.voss
voss/harness/agent/executor.voss
voss/harness/agent/reviewer.voss
```

They do not need to run immediately, but they should define the intended shape.

---

## Next 10 Implementation Tickets

### Ticket 1: Update Project Positioning Docs

**Goal:** Align Voss around harness-led MVP plus language control layer.

**Files:**

- `.planning/PROJECT.md`
- `.planning/HARNESS-PLAN.md`
- `.planning/ROADMAP.md`
- `README.md`

**Acceptance Criteria:**

- Voss is described as an AI-native development harness and programming language.
- `.voss` is described as the workflow control language.
- Python fork language is not the lead framing.
- Rust port is marked deferred until Python harness proves workflow.

---

### Ticket 2: Add `.voss/` Project Brain Contract

**Goal:** Define and scaffold durable project cognition.

**Files:**

- `voss/harness/session.py`
- `voss/harness/cli.py`
- `voss/templates/init/`
- tests under `tests/harness/`

**Acceptance Criteria:**

- `voss init` creates `.voss/` files.
- `.voss-cache/` remains gitignored.
- Durable files are human-readable.
- No API keys are written.

---

### Ticket 3: Implement `voss do` One-shot Task

**Goal:** Run one natural-language repo task through the harness.

**Acceptance Criteria:**

- `voss do "summarize this repo"` works.
- Tool calls are visible.
- Final answer is printed cleanly.
- `--json` emits NDJSON events.
- `--mode plan|edit|auto` works.

---

### Ticket 4: Implement Permission Modes

**Goal:** Prevent unsafe broad edits.

**Acceptance Criteria:**

- `plan` mode cannot write.
- `edit` mode requires approval for writes.
- `auto` mode can apply approved classes of actions.
- shell commands are allowlisted or prompted.
- denied tool calls are recorded.

---

### Ticket 5: Add Plan Artifact Generation

**Goal:** Make planning inspectable.

**Acceptance Criteria:**

- `voss do "plan X" --mode plan` writes `.voss/plans/<id>.md`.
- Plan includes goal, files to inspect, allowed edits, risks, validation, rollback.
- User can feed the plan back into a later run.

---

### Ticket 6: Add Session Save/Resume

**Goal:** Attack context collapse.

**Acceptance Criteria:**

- session JSON saved under `.voss/sessions/` or local state.
- `voss sessions` lists sessions.
- `voss resume <id>` restores prior context.
- session excludes secrets.

---

### Ticket 7: Add `/why` Decision Explanation

**Goal:** Make agent reasoning inspectable.

**Acceptance Criteria:**

- last major decision can be explained.
- explanation includes confidence if available.
- explanation references tool outputs or plan constraints where possible.

---

### Ticket 8: Keep Compiler Verbs Stable

**Goal:** Preserve language product surface.

**Acceptance Criteria:**

- `voss check`, `voss compile`, `voss run`, `voss ast`, `voss init` remain green.
- harness does not hijack `voss run`.
- check diagnostics can be consumed by harness.

---

### Ticket 9: Create Harness-in-Voss Prototype Files

**Goal:** Define the dogfood target.

**Acceptance Criteria:**

- `voss/harness/agent/*.voss` exists.
- Files use real Voss constructs.
- `voss check voss/harness/agent/` is target behavior, even if not fully green immediately.

---

### Ticket 10: Add Golden Harness Tasks

**Goal:** Measure useful behavior.

**Acceptance Criteria:**

- at least 5 local golden tasks exist
- tasks do not require live providers by default
- pass/fail criteria are explicit
- cost and tool count are tracked where possible

---

## Success Criteria for v0.1

Voss v0.1 is successful when:

1. A user can run `voss doctor` and get clear setup guidance.
2. A user can run `voss do "summarize this repo"` in a real project and get useful output.
3. A user can run a scoped edit task with permissioned tools and inspect the diff before applying.
4. A user can resume a prior session without re-explaining the entire repo.
5. Voss writes useful project memory under `.voss/`.
6. `.voss` examples compile/check/run and demonstrate AI-native language constructs.
7. The harness can consume `voss check` diagnostics when editing `.voss` files.
8. The codebase has a clear boundary between runtime, compiler, harness, and future Rust shell.
9. The product is explainable in one sentence.
10. The author can use Voss on Voss itself.

---

## Final Scope Statement

Voss v0.1 should not choose between “harness” and “language.” It should choose the correct relationship between them.

The harness is the user-facing wedge.

The language is the control plane.

The runtime is the semantic foundation.

The compiler makes workflows checkable.

The later Rust shell makes it distributable.

Build in that order.

