# Phase F5: Commit with Critique Hook - Research

**Researched:** 2026-05-22
**Domain:** Python CLI, git hooks, single-shot LLM critique, YAML config
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Constraint Format & Source**
- D-01: Natural language rules. `.voss/constraints.yml` contains a `rules:` list of plain English strings.
- D-02: System prompt injection. Constraints injected into system prompt alongside staged diff. One context window, no tool overhead.
- D-03: Constraints.yml only. Clean boundary — conventions.py NOT included.
- D-04: Skip silently if no constraints.yml. Hook exits 0 immediately.

**Hook Installation & Lifecycle**
- D-05: `voss hooks install` / `voss hooks uninstall` CLI commands.
- D-06: Thin shell shim — `#!/bin/sh\n# Installed by: voss hooks install\nexec voss consensus --staged`.
- D-07: Refuse if hook exists. Print error with `--force` option to overwrite.
- D-08: `voss consensus` is a real CLI command. Standalone callable.

**Critique Output & Gate Behavior**
- D-09: Configurable mode in constraints.yml. `mode: block` (exit 1) or `mode: warn` (exit 0, advisory only).
- D-10: Structured violations list — constraint text cited, file:line reference, explanation.
- D-11: Violations only in output. Clean constraints not printed. Summary shows totals.
- D-12: One-liner on clean pass: `✔ voss consensus: N constraints checked, 0 violations.`

**Agent Invocation Model**
- D-13: Single-shot prompt. One LLM call: constraints + diff → structured JSON → parse → print → exit.
- D-14: Same provider as configured. Reuse existing auth/config infrastructure.
- D-15: No budget cap.
- D-16: Fail open on LLM errors — print warning, exit 0.

### Claude's Discretion

None explicitly listed; all implementation details within the scope above.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Natural language rules in `.voss/constraints.yml` `rules:` list | YAML parsing with PyYAML `yaml.safe_load`; already in pyproject.toml deps |
| D-02 | Constraints + diff injected as single system prompt | `provider.complete()` pattern confirmed in `agent.py:_record_run_call` |
| D-03 | No conventions.py merge | Negative constraint — enforce by omission |
| D-04 | Skip silently if no constraints.yml | Path.exists() guard; exit 0 |
| D-05 | `voss hooks install/uninstall` CLI | `@click.group("hooks")` pattern, same as `skill_group`/`agent_group` |
| D-06 | Thin shell shim | Write literal 3-line script to `.git/hooks/pre-commit` |
| D-07 | Refuse if hook exists, offer `--force` | Path.exists() + `--force` flag |
| D-08 | `voss consensus` standalone CLI command | `@click.command("consensus")` added to `AGENT_COMMANDS` |
| D-09 | Configurable `mode: block\|warn` in constraints.yml | Parse from YAML, default to `warn` for safety |
| D-10 | Structured violations list (constraint, file:line, explanation) | Pydantic model for JSON response from LLM |
| D-11 | Violations only; clean constraints suppressed | Print filter on parsed response |
| D-12 | One-liner on clean pass | Conditional output branch |
| D-13 | Single-shot LLM call | `provider.complete()` with Pydantic `response_format` |
| D-14 | Reuse configured provider | `_resolve_auth_or_die("auto")` pattern |
| D-15 | No budget cap | No additional guard needed |
| D-16 | Fail open on LLM errors | `except Exception: click.echo(warning); sys.exit(0)` |
</phase_requirements>

---

## Summary

Phase F5 adds `voss consensus` (single-shot LLM critique of staged diffs against natural-language constraints) and `voss hooks install/uninstall` (git hook lifecycle management) to the harness CLI. The feature is scoped to the Python harness layer — no Rust, no new dependencies, no agentic loops.

The single-shot LLM call pattern already exists in `agent.py:_record_run_call` (lines ~1404-1453). That function calls `provider.complete(messages=[...], model=model, response_format=PydanticModel)` and handles exceptions silently. F5 follows this exact pattern. The structured JSON response contract (violations + summary) is enforced by a Pydantic model passed as `response_format`, which the provider materializes via a forced tool call.

The hooks install pattern is novel to the codebase but trivially simple: write a 3-line shell script to `.git/hooks/pre-commit` with a refusal guard for pre-existing hooks. The `diagnostics.check_git_on_path()` function provides the git-availability check to reuse as a pre-flight.

**Primary recommendation:** Implement as two new modules — `voss/harness/consensus.py` (single-shot critique logic + Pydantic models) and inline the hook lifecycle in `cli.py` via a `@click.group("hooks")` group, exactly mirroring the `skill_group` pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| constraints.yml parsing | CLI / harness (Python) | — | File reading is synchronous CLI concern |
| Staged diff capture | CLI / harness (Python) | — | `subprocess.run(["git", "diff", "--cached"])` |
| LLM critique call | CLI / harness (Python) | voss_runtime provider | Provider abstraction owns transport |
| Response parsing + output | CLI / harness (Python) | — | Pydantic model for structured output |
| Hook file write | CLI / harness (Python) | OS filesystem | `.git/hooks/pre-commit` write |
| Exit code gate | CLI / harness (Python) | — | `sys.exit(1)` on block mode violations |

---

## Standard Stack

### Core

No new dependencies. All required libraries are already in `pyproject.toml`:

| Library | Version (installed) | Purpose | Source |
|---------|---------------------|---------|--------|
| `pyyaml` | 6.0.3 | Parse `.voss/constraints.yml` | Already direct dep |
| `pydantic` | 2.13.4 | Structured LLM response schema (`response_format=`) | Already direct dep |
| `click` | 8.3.3 | CLI command + group registration | Already direct dep |

[VERIFIED: pyproject.toml] — all three libraries confirmed present and versions confirmed via `.venv/bin/python -c "import yaml; import pydantic; import click"`.

### No New Packages Required

This phase installs zero new packages. F5 is entirely implemented using existing harness infrastructure.

---

## Package Legitimacy Audit

> No packages are installed by this phase. This section is intentionally empty.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
User runs: git commit
     │
     ▼
.git/hooks/pre-commit (3-line shim)
     │   exec voss consensus --staged
     ▼
voss consensus --staged
     │
     ├─► .voss/constraints.yml exists?
     │       NO  → exit 0 (D-04)
     │       YES ↓
     │
     ├─► git diff --cached  (subprocess)
     │       empty diff → exit 0
     │
     ├─► Build system prompt:
     │       [constraints list] + [staged diff]
     │
     ├─► provider.complete(messages, response_format=CritiqueResponse)
     │       ← structured JSON {violations: [...], summary: {...}}
     │
     ├─► violations == 0?
     │       YES → print one-liner (D-12), exit 0
     │       NO  ↓
     │
     ├─► Print violations (D-10, D-11)
     │
     └─► mode == "block"?
             YES → exit 1
             NO  → exit 0 (warn mode)

On any LLM exception:
     └─► print warning (D-16), exit 0 (fail-open)
```

### Recommended Project Structure

Two new files, four modified:

```
voss/harness/
├── consensus.py          # NEW — critique logic, Pydantic models, diff capture
└── cli.py                # MODIFIED — add consensus_cmd + hooks_group to AGENT_COMMANDS

.voss/
└── constraints.yml       # NEW (user-created) — not in repo, created per-project
```

Tests:
```
tests/harness/
└── test_consensus.py     # NEW — unit tests (provider mocked)
```

### Pattern 1: Single-Shot LLM Call with Structured Output

**What:** Call `provider.complete()` with a Pydantic model as `response_format`. Provider forces a tool call and parses the JSON. Caller gets `resp.parsed` typed as the model.

**When to use:** Wherever a single LLM round-trip produces a machine-parseable response. No agentic loop, no tool use by the model.

**Example (from `agent.py:_record_run_call`):**

```python
# Source: voss/harness/agent.py:1404-1453 [VERIFIED: codebase]
resp = await provider.complete(
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ],
    model=model,
    response_format=CritiqueResponse,  # Pydantic BaseModel subclass
    temperature=0.0,
    max_tokens=2000,
)
# resp.parsed is typed CritiqueResponse | None
# resp.parsed is None when provider could not parse (treat as LLM error)
```

**F5 adaptation:** Replace `RunSemantics` with `CritiqueResponse`. Wrap the entire call in `try/except Exception` and fail-open per D-16.

### Pattern 2: Click Group with Subcommands

**What:** Register a `@click.group("name")` with `@groupname.command("subcommand")` children. Add the group to `AGENT_COMMANDS` in `cli.py`.

**When to use:** When a feature requires multiple related CLI verbs (e.g., `install`/`uninstall`).

**Example (from `cli.py:2596-2598`):**

```python
# Source: voss/harness/cli.py:2596 [VERIFIED: codebase]
@click.group("skill")
def skill_group() -> None:
    """Run registered skills."""

@skill_group.command("run")
@click.option("--cwd", "cwd_str", default=".", ...)
def skill_run_cmd(...) -> None: ...
```

**F5 adaptation:** Create `hooks_group` with `install` and `uninstall` subcommands. Add to `AGENT_COMMANDS` alongside `hooks_cmd` (or just the group).

### Pattern 3: Provider Auth Resolution

**What:** Call `_resolve_auth_or_die("auto")` to get a `(Resolution, ModelProvider)` pair. The provider abstracts over Anthropic OAuth, OpenAI, and API key paths.

**When to use:** Any harness command that needs LLM access.

**Example (from `cli.py:1333`):**

```python
# Source: voss/harness/cli.py:401-453 [VERIFIED: codebase]
res, provider = _resolve_auth_or_die(auth_pref)
# provider is ModelProvider — call provider.complete() or provider.stream()
```

**F5 adaptation:** `voss consensus` takes `--auth` option with `AUTH_CHOICES` default `"auto"`, calls `_resolve_auth_or_die(auth_pref)` before the LLM call.

### Pattern 4: Staged Diff Capture

**What:** `subprocess.run(["git", "diff", "--cached"], ...)` — synchronous, text output, cwd-bound.

**Analog (from `recorder.py:430-443`):**

```python
# Source: voss/harness/recorder.py:430 [VERIFIED: codebase]
out = subprocess.run(
    ["git", "diff", "--cached"],
    cwd=str(cwd),
    capture_output=True,
    text=True,
    timeout=10,
)
```

**F5 specifics:** Add `--diff <REF>` and `--stdin` modes per D-08 (standalone usage modes beyond `--staged`). Each mode populates the same `diff_text: str` variable before the LLM call.

### Pattern 5: YAML Config Loading

**What:** `yaml.safe_load(path.read_text())` — synchronous, uses PyYAML already in deps. Validated with Pydantic.

**Analog (from `code/config.py:46`):**

```python
# Source: voss/harness/code/config.py:46 [VERIFIED: codebase]
raw = yaml.safe_load(defaults_path.read_text(encoding="utf-8")) or {}
```

**F5 specifics:** `safe_load` is mandatory (never `yaml.load`). Validate with Pydantic `ConstraintsConfig` model. Missing/invalid file → log warning and exit 0 (D-04 spirit).

### Anti-Patterns to Avoid

- **Using `run_turn` instead of `provider.complete`:** `run_turn` is the full agentic loop with tool calls and multi-turn. F5 is a single-shot — use `provider.complete` directly, same as `_record_run_call`.
- **Blocking commit on LLM infrastructure failures:** Any exception from `provider.complete` must produce a warning and exit 0 (D-16). Never propagate the exception.
- **Silently destroying existing hooks:** D-07 is explicit — if `.git/hooks/pre-commit` exists, print error and stop. Only `--force` overwrites.
- **Loading `yaml.load` without Loader:** Always use `yaml.safe_load` to avoid arbitrary Python object deserialization.
- **Calling `sys.exit(1)` on `mode: warn`:** Only `mode: block` exits 1. Default/unrecognized mode should behave as `warn` for safety.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output parsing | JSON regex on raw text | `provider.complete(response_format=PydanticModel)` | Provider forces tool-call; Pydantic validates; already tested |
| Provider selection / auth | Custom credential lookup | `_resolve_auth_or_die(auth_pref)` | Handles OAuth, API keys, auto-refresh, first-run wizard |
| Git availability check | `shutil.which("git")` inline | `diagnostics.check_git_on_path()` | Already unit-tested |
| YAML deserialization | Manual string parsing | `yaml.safe_load()` + Pydantic model | PyYAML already in deps, Pydantic validates schema |

---

## Common Pitfalls

### Pitfall 1: `resp.parsed` is None After Successful HTTP Call
**What goes wrong:** Provider returns 200 but the model produces a `text` block instead of a tool-call, or the JSON is malformed. `resp.parsed` is `None`.
**Why it happens:** Models occasionally produce prose instead of structured output even when `response_format` is set. LiteLLM path may differ from Anthropic OAuth path.
**How to avoid:** Always check `if resp.parsed is None:` after `provider.complete`. Treat `None` as an LLM error — print warning, exit 0 (D-16).
**Warning signs:** Tests that mock `resp.parsed = None` catching this case.

### Pitfall 2: Empty Staged Diff
**What goes wrong:** `git diff --cached` returns empty string. LLM receives no content to review, produces zero-violation response trivially, or errors.
**Why it happens:** Committing with no staged files (e.g., `git commit --allow-empty`).
**How to avoid:** Check `if not diff_text.strip(): print one-liner, exit 0` before calling LLM.
**Warning signs:** Empty diff in CI after `git add` was skipped.

### Pitfall 3: Overwriting Existing Hooks (D-07 violation)
**What goes wrong:** `voss hooks install` silently replaces a project's husky or lint-staged hook.
**Why it happens:** Forgetting the guard before writing `.git/hooks/pre-commit`.
**How to avoid:** `if hook_path.exists() and not force: click.echo(error); sys.exit(1)`.
**Warning signs:** A project's existing pre-commit tooling stops running after `voss hooks install`.

### Pitfall 4: Running Outside a Git Repo
**What goes wrong:** `git diff --cached` fails; `.git/hooks/` path doesn't exist.
**Why it happens:** `voss consensus --staged` invoked in a non-git directory.
**How to avoid:** Detect with `subprocess.run(["git", "rev-parse", "--git-dir"], ...)`. If non-zero, print clear error and exit non-zero (this is a user error, not an LLM error — fail loudly, not fail-open).
**Warning signs:** `returncode != 0` on git command with a clear stderr.

### Pitfall 5: Large Diff Exceeding Context Window
**What goes wrong:** A very large staged diff fills the context window, causing the LLM call to fail or return truncated output.
**Why it happens:** No diff size guard.
**How to avoid:** Truncate diff at ~30,000 characters with a `[diff truncated]` marker. The model can still critique visible changes. This is advisory output — partial critique is better than no critique.
**Warning signs:** Provider returns 400 with "max tokens exceeded" or similar.

### Pitfall 6: `yaml.load()` Instead of `yaml.safe_load()`
**What goes wrong:** Arbitrary Python object instantiation from YAML.
**Why it happens:** Copy-paste from old Python code.
**How to avoid:** Use `yaml.safe_load()` exclusively. Already the pattern in `code/config.py`.

---

## Code Examples

### Pydantic Models for LLM Response

```python
# Source: voss/harness/agent.py (RunSemantics pattern) [VERIFIED: codebase]
from pydantic import BaseModel, Field

class Violation(BaseModel):
    constraint: str          # exact text of the violated rule
    file: str = ""           # file path (empty if not file-specific)
    line: int | None = None  # line number (None if not determinable)
    explanation: str         # why this violates the constraint

class CritiqueSummary(BaseModel):
    total_checked: int
    violation_count: int

class CritiqueResponse(BaseModel):
    violations: list[Violation] = Field(default_factory=list)
    summary: CritiqueSummary
```

### constraints.yml Schema

```yaml
# .voss/constraints.yml (D-01, D-09)
mode: block   # or: warn
rules:
  - "Never commit directly to main branch."
  - "All new functions must have a docstring."
  - "Do not introduce print() statements in production code."
```

Parsed with:
```python
# Pydantic model for validation
class ConstraintsConfig(BaseModel):
    mode: str = "warn"          # default: warn (safe fallback if omitted)
    rules: list[str] = Field(default_factory=list)
```

### Fail-Open Error Handling Pattern

```python
# Source: agent.py:_record_run_call pattern [VERIFIED: codebase]
try:
    resp = await provider.complete(
        messages=messages,
        model=model,
        response_format=CritiqueResponse,
        temperature=0.0,
        max_tokens=2000,
    )
except Exception as exc:  # noqa: BLE001
    click.echo(
        f"⚠ voss consensus: LLM request failed ({type(exc).__name__}). "
        "Skipping critique. Commit proceeds.",
        err=True,
    )
    sys.exit(0)

if resp.parsed is None:
    click.echo(
        "⚠ voss consensus: could not parse LLM response. "
        "Skipping critique. Commit proceeds.",
        err=True,
    )
    sys.exit(0)
```

### Hook Shim Content (D-06)

```python
HOOK_SHIM = "#!/bin/sh\n# Installed by: voss hooks install\nexec voss consensus --staged\n"
```

### Input Modes for `voss consensus` (D-08)

```python
@click.command("consensus")
@click.option("--staged", "mode", flag_value="staged", default=True,
              help="Critique staged (--cached) diff.")
@click.option("--diff", "ref", default=None, metavar="REF",
              help="Critique diff against a git ref (e.g. HEAD~3).")
@click.option("--stdin", "mode", flag_value="stdin",
              help="Read diff from stdin (pipe: git diff | voss consensus --stdin).")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--auth", "auth_pref", type=click.Choice(AUTH_CHOICES), default="auto")
def consensus_cmd(...): ...
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Agentic `run_turn` for diff analysis | Single-shot `provider.complete` | F5 uses the simpler path — no multi-turn needed |
| `summarize_diff.py` (agentic, tool call) | `consensus.py` (single-shot, no tools) | Different complexity tier for different use case |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `voss consensus` should resolve model via `get_config().default_model` (same as `do_cmd`) | Code Examples | Minor — model selection could differ; easily overridden with `--model` flag |
| A2 | Default `mode` when `mode:` key absent from constraints.yml should be `warn` (not `block`) | Code Examples | Low — a `block` default would be surprising; `warn` is safe |
| A3 | Max diff truncation at ~30,000 chars is safe for all supported providers | Pitfall 5 | Low — conservative threshold; could be tuned if specific provider limits are known |

---

## Open Questions

1. **Should `voss consensus` accept a `--model` flag?**
   - What we know: All other harness commands with LLM access accept `--model`. D-14 says "same provider as configured."
   - What's unclear: Whether Ben wants model override capability or strict config-only.
   - Recommendation: Add `--model` with `default=None` (same as `do_cmd`). No harm, consistent UX.

2. **Should `voss hooks install` support non-git-root cwd?**
   - What we know: `.git/` may be in a parent directory (monorepos).
   - What's unclear: Should the hook find the git root automatically?
   - Recommendation: Use `git rev-parse --show-toplevel` to find git root; write hook there. Print the path so user sees where it landed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | Diff capture, hook install | Yes | 2.50.1 | None — required |
| pyyaml | constraints.yml parsing | Yes | 6.0.3 | None — already in pyproject.toml |
| pydantic | Structured LLM response | Yes | 2.13.4 | None — already in pyproject.toml |
| click | CLI commands | Yes | 8.3.3 | None — already in pyproject.toml |
| LLM provider (configured) | `voss consensus` critique | Checked at runtime | — | Fail-open (D-16) |

**Missing dependencies with no fallback:** None — all dependencies present.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | `pyproject.toml` / existing pytest config |
| Quick run command | `.venv/bin/python -m pytest tests/harness/test_consensus.py -q` |
| Full suite command | `.venv/bin/python -m pytest tests/harness/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01/D-02/D-03 | Constraints loaded from YAML, injected into prompt, no conventions | unit | `pytest tests/harness/test_consensus.py::test_constraints_loaded_and_injected` | ❌ Wave 0 |
| D-04 | Skip silently when no constraints.yml | unit | `pytest tests/harness/test_consensus.py::test_skip_when_no_constraints_file` | ❌ Wave 0 |
| D-09 | `mode: block` exits 1 on violations; `mode: warn` exits 0 | unit | `pytest tests/harness/test_consensus.py::test_block_mode_exits_1` | ❌ Wave 0 |
| D-12 | One-liner output on clean pass | unit | `pytest tests/harness/test_consensus.py::test_clean_pass_output` | ❌ Wave 0 |
| D-13 | Single-shot — provider.complete called exactly once | unit | `pytest tests/harness/test_consensus.py::test_single_shot_one_call` | ❌ Wave 0 |
| D-16 | LLM exception → warning on stderr, exit 0 | unit | `pytest tests/harness/test_consensus.py::test_fail_open_on_llm_error` | ❌ Wave 0 |
| D-05/D-06/D-07 | hooks install writes shim; refuses if exists; --force overwrites | unit | `pytest tests/harness/test_consensus.py::test_hooks_install_*` | ❌ Wave 0 |
| D-08 | `--staged`, `--diff REF`, `--stdin` modes all work | unit | `pytest tests/harness/test_consensus.py::test_diff_input_modes` | ❌ Wave 0 |
| CLI reg | `voss consensus` and `voss hooks` appear in `voss --help` | unit | `pytest tests/harness/test_cli.py::TestUnifiedVossCli::test_voss_help_lists_agent_verbs` | ✅ modify existing |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/harness/test_consensus.py -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/harness/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/test_consensus.py` — covers all D-01..D-16 requirements
- [ ] `voss/harness/consensus.py` — new module (stub or full implementation)
- [ ] `cli.py` additions: `consensus_cmd`, `hooks_group` registered in `AGENT_COMMANDS`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Hook is local; no auth surface |
| V3 Session Management | No | Stateless single-shot |
| V4 Access Control | No | No user roles |
| V5 Input Validation | Yes | `yaml.safe_load()` + Pydantic model for constraints; diff content is untrusted |
| V6 Cryptography | No | No secrets stored |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious constraints.yml content (YAML deserialization) | Tampering | `yaml.safe_load()` — no arbitrary Python object instantiation |
| Large diff exhausting context / causing provider error | Denial | Truncate diff at ~30k chars before sending |
| Hook overwrite without user consent | Tampering | D-07: refuse if exists; require `--force` |
| LLM response containing injected exit codes or commands | Spoofing | Response parsed as Pydantic model only — text fields never executed |
| API key / OAuth token leak via diff content | Information Disclosure | No mitigation at this layer (diff is user's content; provider transport is already HTTPS) |

---

## Sources

### Primary (HIGH confidence)

- `voss/harness/cli.py` — CLI patterns, `AGENT_COMMANDS`, `_resolve_auth_or_die`, `AUTH_CHOICES`, click group patterns. All patterns verified by direct code inspection.
- `voss/harness/agent.py:_record_run_call` (lines 1404-1453) — Single-shot `provider.complete` with `response_format` Pydantic model. Exact pattern F5 reuses.
- `voss/harness/providers.py:249-310` — `provider.complete()` signature and `resp.parsed` semantics. Verified.
- `voss/harness/code/config.py:46` — `yaml.safe_load` pattern. Verified.
- `voss/harness/recorder.py:430-443` — `subprocess.run(["git", "diff", "--cached"])` pattern. Verified.
- `voss/harness/diagnostics.py:115-124` — `check_git_on_path()` reuse. Verified.
- `pyproject.toml` — PyYAML 6.0.3, Pydantic 2.13.4, click 8.3.3 confirmed present.

### Secondary (MEDIUM confidence)

- `voss/harness/skills/summarize_diff.py` — Domain reference for diff analysis prompt structure. Confirms single-shot is simpler than agentic; provides prompt structure inspiration.
- `tests/harness/test_cli.py` — Test patterns for CLI command registration verification.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already installed, patterns directly lifted from codebase
- Architecture: HIGH — patterns verified line-by-line in existing code
- Pitfalls: HIGH — pitfalls derived from existing patterns + codebase precedents

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (stable infrastructure, no external moving parts)
