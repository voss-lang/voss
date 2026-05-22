# Phase F5: Commit with Critique Hook - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** F5-commit-with-critique-hook
**Areas discussed:** Constraint format & source, Hook installation & lifecycle, Critique output & gate behavior, Agent invocation model

---

## Constraint Format & Source

### Q1: What should constraints look like in .voss/constraints.yml?

| Option | Description | Selected |
|--------|-------------|----------|
| Natural language rules | Plain English statements. Agent interprets like a reviewer. Simple to author. | ✓ |
| Structured rule objects | Typed rules with severity, scope globs. More machine-parseable, more ceremony. | |
| Mixed — natural language + optional metadata | Plain string rules work. Optionally expand to object. Low floor, high ceiling. | |

**User's choice:** Natural language rules

### Q2: How should the agent consume constraints?

| Option | Description | Selected |
|--------|-------------|----------|
| System prompt injection | Read constraints, inject into prompt alongside diff. One context window. | ✓ |
| Tool-callable lookup | Agent calls get_constraints tool. Adds round trip. | |
| Both — inject + tool for follow-up | Inject in prompt, also expose tool for re-query. | |

**User's choice:** System prompt injection

### Q3: Should critique also read conventions from memory?

| Option | Description | Selected |
|--------|-------------|----------|
| Constraints.yml only | Clean boundary. Single source of truth. | ✓ |
| Constraints + conventions merged | Load both. Broader but blurs boundary. | |
| You decide | Planner discretion. | |

**User's choice:** Constraints.yml only

### Q4: What if .voss/constraints.yml doesn't exist?

| Option | Description | Selected |
|--------|-------------|----------|
| Skip silently | Exit 0 immediately. Opt-in via creating file. | ✓ |
| Warn and pass | Print hint, exit 0. | |
| Critique with general best practices | Run agent with generic rules. | |

**User's choice:** Skip silently

---

## Hook Installation & Lifecycle

### Q1: How should the pre-commit hook get installed?

| Option | Description | Selected |
|--------|-------------|----------|
| voss hooks install command | Explicit CLI. Writes .git/hooks/pre-commit. Clear opt-in. | ✓ |
| Auto during voss init | Installs alongside .voss/ creation. Potentially surprising. | |
| Git hookPath in .voss/hooks/ | Ship scripts in .voss/hooks/, user sets core.hooksPath. Team-shareable. | |

**User's choice:** voss hooks install command

### Q2: What should the hook file contain?

| Option | Description | Selected |
|--------|-------------|----------|
| Thin shim that calls voss consensus | 3-line shell script: exec voss consensus --staged. All logic in harness. | ✓ |
| Inline Python script | Python importing voss internals. Faster but couples to install path. | |
| You decide | Planner discretion. | |

**User's choice:** Thin shim

### Q3: Handle existing pre-commit hooks?

| Option | Description | Selected |
|--------|-------------|----------|
| Refuse if hook exists | Print error with --force option. Safe default. | ✓ |
| Chain — rename existing, call both | Preserves existing hooks. | |
| Overwrite silently | Simple but destructive. | |

**User's choice:** Refuse if exists

### Q4: Callable standalone?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — voss consensus is a real CLI command | Works standalone, in CI, via pipe. Hook is one entry point. | ✓ |
| Hook-only | Internal to hook. Simpler but less flexible. | |

**User's choice:** Yes, real CLI command
**Notes:** User specified command name should be `voss consensus` (not `critique`).

---

## Critique Output & Gate Behavior

### Q1: Should commit be blocked on violations?

| Option | Description | Selected |
|--------|-------------|----------|
| Block by default, --force to override | Exit 1 on violations. Strong enforcement. | |
| Warn only — never block | Always exit 0. Advisory. | |
| Configurable in constraints.yml | mode: block or mode: warn. Per-project choice. | ✓ |

**User's choice:** Configurable mode

### Q2: Output format?

| Option | Description | Selected |
|--------|-------------|----------|
| Structured violations list | Per-violation: constraint, file:line, explanation. Summary at bottom. | ✓ |
| Prose summary | Natural-language paragraph. Harder to parse. | |
| You decide | Planner discretion. | |

**User's choice:** Structured violations list

### Q3: Show clean constraints?

| Option | Description | Selected |
|--------|-------------|----------|
| Violations only | Quiet output. Summary shows totals. | ✓ |
| Show all | Every constraint with ✔/✖ status. | |
| Verbose flag | Violations by default, --verbose for all. | |

**User's choice:** Violations only

### Q4: Zero violations output?

| Option | Description | Selected |
|--------|-------------|----------|
| One-liner confirmation | Short success message. Confirms it ran. | ✓ |
| Silent — exit 0, no output | Unix convention. | |
| You decide | Planner discretion. | |

**User's choice:** One-liner confirmation

---

## Agent Invocation Model

### Q1: Full agentic turn or single-shot?

| Option | Description | Selected |
|--------|-------------|----------|
| Single-shot prompt | One LLM call. ~2-5s. No tools. | ✓ |
| Agentic turn (like summarize_diff) | Full run_turn with tools. 5-15s+. | |
| You decide | Planner discretion. | |

**User's choice:** Single-shot prompt

### Q2: Model/provider?

| Option | Description | Selected |
|--------|-------------|----------|
| Same as configured provider | Reuse voss config. No separate setup. | ✓ |
| Hardcode cheap/fast model | Always cheapest available. | |
| Configurable in constraints.yml | Optional model field. | |

**User's choice:** Same as configured provider

### Q3: Budget cap?

| Option | Description | Selected |
|--------|-------------|----------|
| No cap | Single-shot inherently bounded. | ✓ |
| Configurable max cost | Optional field in constraints.yml. | |
| Hard token limit on diff size | Skip if diff too large. | |

**User's choice:** No cap

### Q4: LLM failure handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Pass through — allow commit | Print warning, exit 0. Never block on infra issues. | ✓ |
| Fail closed — block on error | Exit 1 on any error. Strict. | |
| Configurable | fail_open field in constraints.yml. | |

**User's choice:** Pass through (fail open)

---

## Claude's Discretion

None — user made all decisions explicitly.

## Deferred Ideas

None — discussion stayed within phase scope.
