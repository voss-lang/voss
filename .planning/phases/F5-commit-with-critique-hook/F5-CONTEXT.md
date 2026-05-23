# Phase F5: Commit with Critique Hook - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Git pre-commit hook that invokes a Voss agent to critique staged diffs against natural-language project constraints in `.voss/constraints.yml`. Ships as `voss consensus` CLI command (callable standalone or via hook) with `voss hooks install/uninstall` lifecycle. Single-shot LLM call — no agentic turns, no tool use. Configurable block/warn mode.

</domain>

<decisions>
## Implementation Decisions

### Constraint Format & Source
- **D-01:** **Natural language rules.** `.voss/constraints.yml` contains a `rules:` list of plain English strings. Agent interprets them like a human reviewer reading guidelines. Simple to author, flexible.
- **D-02:** **System prompt injection.** Constraints are read from file and injected into the system prompt alongside the staged diff. One context window, no tool overhead.
- **D-03:** **Constraints.yml only.** Clean boundary — conventions from memory system (conventions.py) are NOT included. Constraints file is the single source of truth for commit critique.
- **D-04:** **Skip silently if no constraints.yml.** Hook exits 0 immediately. No noise. User opts in by creating the file.

### Hook Installation & Lifecycle
- **D-05:** **`voss hooks install` / `voss hooks uninstall` CLI commands.** Explicit opt-in. Writes `.git/hooks/pre-commit`.
- **D-06:** **Thin shell shim.** Hook file is a 3-line script: `#!/bin/sh` + comment + `exec voss consensus --staged`. All logic lives in the harness CLI.
- **D-07:** **Refuse if hook exists.** Print error with `--force` option to overwrite. Safe default — never silently destroy existing hooks (husky, lint-staged, etc).
- **D-08:** **`voss consensus` is a real CLI command.** Callable standalone: `voss consensus --staged`, `voss consensus --diff HEAD~3`, `git diff | voss consensus --stdin`. Hook is just one entry point.

### Critique Output & Gate Behavior
- **D-09:** **Configurable mode in constraints.yml.** `mode: block` (exit 1 on violations) or `mode: warn` (exit 0, advisory only). Per-project choice.
- **D-10:** **Structured violations list.** Each violation: constraint text cited, file:line reference, explanation. Summary line at bottom: "N violations / M constraints."
- **D-11:** **Violations only in output.** Clean constraints not printed. Summary line shows total checked count for context.
- **D-12:** **One-liner on clean pass.** `✔ voss consensus: N constraints checked, 0 violations.`

### Agent Invocation Model
- **D-13:** **Single-shot prompt.** One LLM call: constraints + diff in prompt → structured JSON response → parse → print → exit code. No tool use, no multi-turn. ~2-5s latency.
- **D-14:** **Same provider as configured.** Reuse whatever provider + model the user configured for voss. No separate config for consensus.
- **D-15:** **No budget cap.** Single-shot is inherently bounded (~$0.01-0.05 per commit). No cap mechanism needed.
- **D-16:** **Fail open on LLM errors.** On any LLM failure (network, auth, rate limit): print warning, exit 0. Never block a commit because of infrastructure issues.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Harness CLI (command registration)
- `voss/harness/cli.py` — CLI entry points (`do_cmd`, `edit_cmd`, `doctor_cmd`, etc). F5 adds `consensus_cmd` and `hooks_cmd` here.

### Existing Diff Skill (pattern source)
- `voss/harness/skills/summarize_diff.py` — Agentic diff summarizer. F5 follows a simpler pattern (no `run_turn`, just direct LLM call) but same domain: reading diffs and producing structured output.

### Agent & Provider Infrastructure
- `voss/harness/agent.py` — Agent loop, `run_turn()`. F5 does NOT use `run_turn` (single-shot instead) but needs provider/auth setup from same infrastructure.
- `voss/harness/auth.py` — Provider authentication. F5 reuses this for LLM access.
- `voss/harness/config.py` — Config loading, `config_path()`. F5 reads provider config from here.

### Convention System (boundary reference — NOT used by F5)
- `voss/harness/conventions.py` — Convention extraction from conversations. F5 explicitly does NOT merge conventions. Clean boundary.

### Project State
- `.voss/constraints.yml` — New file created by user. F5 reads this. Does not exist by default.

### Feature Plan
- `.planning/Feature Plan.md` §5 — Original feature proposal for "Commit with Critique Hook."

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `summarize_diff.py` skill — pattern for structured diff analysis prompt + output parsing
- `auth.py` + `config.py` — provider auth + config loading, reuse for LLM access
- `cli.py` Click command registration — add `consensus_cmd` and `hooks_cmd` following existing patterns
- `diagnostics.py` — `check_git_on_path()` verifiable, reuse for hook install pre-checks

### Established Patterns
- **Click CLI commands** — all harness commands use Click decorators with `@click.command()`, `@click.option()`. F5 follows same pattern.
- **Skills as single-file modules** — `voss/harness/skills/*.py` each expose a `run()` function. F5's consensus logic could follow this or live directly in cli.py.
- **Structured JSON output from LLM** — `summarize_diff` uses stable section headers as contract. F5 uses structured JSON response format for machine-parseable violations.

### Integration Points
- **cli.py command group** — Register `voss consensus` and `voss hooks` as new Click commands
- **`.git/hooks/pre-commit`** — F5 writes this file via `voss hooks install`
- **`.voss/constraints.yml`** — F5 reads this file at runtime. New convention in `.voss/` project state directory.
- **Provider auth flow** — F5 needs authenticated LLM access. Reuse existing `auth.py` provider resolution.

</code_context>

<specifics>
## Specific Ideas

- Command name is `voss consensus` (not `critique`). Matches the product language.
- Hook shim: `#!/bin/sh\n# Installed by: voss hooks install\nexec voss consensus --staged`
- Structured JSON response schema from LLM: `{violations: [{constraint, file, line, explanation}], summary: {total_checked, violation_count}}`
- constraints.yml schema: `{mode: "block"|"warn", rules: [string, ...]}`
- Clean pass output: `✔ voss consensus: 4 constraints checked, 0 violations.`
- Fail-open warning: `⚠ voss consensus: LLM request failed (timeout). Skipping critique. Commit proceeds.`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: F5-commit-with-critique-hook*
*Context gathered: 2026-05-22*
