# Phase M2: Project Cognition - Research

**Researched:** 2026-05-11
**Domain:** Project-local persistent state, per-turn run ledger, cognition auto-injection, pydantic-validated YAML config, hard-cut session storage
**Confidence:** HIGH (all decisions locked in CONTEXT.md; this research answers **how** to build, not **what** to build)

## Summary

M2 is a contained extension of the M1 harness. Every decision is locked in CONTEXT.md D-01..D-20 — research found no reason to relitigate any of them. The work decomposes into ten cleanly-sequenced units of integration into existing files. There are no new external deps required: pydantic v2 (`>=2.6,<3.0`), PyYAML 6.0, `litellm.token_counter` (for cognition token accounting), and `git ls-files` (already used via subprocess in M1) cover everything.

The two non-trivial risk areas are (1) the agent-self-reported `record_run` closing call, where reliability hinges on whether `record_run` is a public tool the agent picks vs. a privileged terminal call the harness dispatches, and (2) the secret-redaction guarantee extension to `RunRecord`. Both have concrete mitigation paths spelled out below.

**Primary recommendation:** Build in the order (1) `cognition.load(cwd)` + pydantic config schemas, (2) `session.py` per-project path resolution + `runs: list[RunRecord]` field, (3) `RunRecorder` mechanical capture wrapping `run_turn`, (4) `record_run` privileged closing tool + agent prompt update, (5) `/analyze` slash command + analyze prompt, (6) cognition auto-injection in `run_turn`, (7) drift detection at REPL boot, (8) `voss doctor` extension, (9) `voss sessions --all` legacy reader, (10) renderer cognition status + NDJSON event. Tests follow each unit and the schema-allowlist redaction test (M1 `tests/harness/test_session_redaction.py`) is extended to scan `RunRecord` fields after step 2.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| `/analyze` slash command dispatch | Harness CLI REPL (`voss/harness/cli.py:_run_repl`) | — | Slash commands already live in `_run_repl`; `/analyze` slots beside `/login`, `/model`, `/mode`. |
| Repo file walk + manifest build (`.voss-cache/repo.idx`) | Harness compiled-in Python (`voss/harness/cognition.py` — new) | `git ls-files` subprocess | Pure local I/O + git CLI; no agent involvement. |
| Architecture/project digest authoring | Agent (LLM via `run_turn`) | Harness writes via existing `fs_write` tool | D-06: agent writes all cognition files; tools are M1's `fs_write`/`fs_edit`. |
| Cognition file parsing + schema validation | Harness Python (`cognition.load(cwd) -> CognitionBundle`) | pydantic v2 | Loud-fail at REPL startup, not mid-turn. |
| Cognition injection into system prompt | Harness `run_turn` (`voss/harness/agent.py`) | — | Prepended before `PLAN_SYSTEM`; reserved 6k tokens within 60k budget. |
| Per-turn mechanical observation (inspected/changed/validation/failures/cost/timestamps/diff) | Harness `RunRecorder` collaborator | Wraps existing tool dispatch loop in `run_turn` | Auto-capture; agent cannot under- or over-report. |
| Per-turn semantic capture (goal/plan/avoided/assumptions/decisions/risks/follow_ups) | Agent (LLM) | Reported via privileged closing `record_run` tool dispatch | D-15: harness dispatches the closing call; agent populates from its own reasoning. |
| Session persistence (`.voss/sessions/<id>.json`) | Harness `session.py` (extended with `runs` field + per-cwd dir) | dataclass `asdict` allowlist | Same redaction guarantee as M1 D-16/D-17 extended to `RunRecord`. |
| Decision/plan markdown mirror | Harness post-turn hook in `_run_repl` / `run_turn` | Writes `.voss/decisions/*.md`, `.voss/plans/*.md` | Triggered after `RunRecord.decisions` populated; uses filename + frontmatter convention (D-08). |
| Drift detection on REPL launch | Harness CLI banner code (`_run_repl`) | Reads architecture.md frontmatter | Informational; never blocks (D-04). |
| `voss doctor` cognition rows | Harness `doctor_cmd` extension | — | Same "diagnose, don't fix" stance as M1. |
| `voss sessions --all` legacy read | Harness `sessions_cmd` extension | Reads both `.voss/sessions/` (current cwd) and `~/.local/state/voss/sessions/` | Read-only on legacy path. |
| Renderer cognition status line + NDJSON `cognition_loaded` event | `voss/harness/render.py` (small extension on each renderer) | — | Tty/Plain print dim line; Json emits event. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---|---|---|---|
| pydantic | `>=2.6,<3.0` (already a project dep) | YAML config schema validation; `Plan`/`RunRecord` schemas | Already used by M1 `agent.py:Plan`; same `BaseModel`+`model_validate` pattern. `[VERIFIED: pyproject.toml line 11]` |
| PyYAML | `>=6.0` (installed: 6.0.2) | Load `.yml` config files | Stdlib-adjacent; `yaml.safe_load` → dict → `Model.model_validate(dict)`. `[VERIFIED: python3 -c "import yaml; print(yaml.__version__)"]` |
| litellm | already a dep | `litellm.token_counter(model=..., text=...)` for cognition token accounting | Existing per-provider count_tokens used by `voss_runtime.context`. `[VERIFIED: voss_runtime/providers/litellm_provider.py:62]` |
| click | `8.2.1` (installed) | New `--all`/`--global` flag on `sessions_cmd` | Already in use; extend existing Command. `[VERIFIED]` |
| stdlib `subprocess` | — | `git ls-files`, `git rev-parse HEAD`, `git diff --stat` | Already used by M1 `_git_status` in cli.py and `_shell_capture` in tools.py. `[VERIFIED]` |
| stdlib `hashlib` | — | sha1 per file in `repo.idx` | No new dep. |

### Supporting
| Library | Version | Purpose | When to Use |
|---|---|---|---|
| PyYAML (`yaml.safe_dump`) | 6.0+ | Writing default `constraints.yml`/`permissions.yml`/`validation.yml` during `/analyze` bootstrap | When the agent's `fs_write` would otherwise need to emit YAML; in practice we hand the agent a starter template string and let `fs_write` save verbatim. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|---|---|---|
| `git ls-files` for repo manifest | `pathlib.Path.walk` with `.gitignore` parsing | git is faster, respects all .gitignore layers correctly; walk requires reimplementing gitignore matching. D-05 explicitly says git first, walk fallback only when not a git repo. |
| `litellm.token_counter` for cognition budget | `tiktoken` directly | litellm already abstracts per-model tokenizers; we use it consistently with `voss_runtime/context.py`. No need to call tiktoken directly. |
| pydantic v2 BaseModel for `RunRecord` | `@dataclass` like `SessionRecord` | RunRecord stays a dataclass to inherit the M1 schema-allowlist redaction guarantee verbatim. **Use dataclass.** `Plan` (already pydantic) remains pydantic because it crosses the provider response_format boundary. |
| ruamel.yaml (preserves comments) | PyYAML | Cognition files are agent-written and human-edited but we never round-trip with comment preservation; PyYAML is fine. |
| Separate `.voss/runs/<id>.json` files | Embed `runs` in session JSON | Locked by D-13. Reduces fan-out, keeps one-file-per-session mental model. |

**Installation:** No new packages needed. All deps are present in `pyproject.toml`.

**Version verification:**
- `pydantic` constraint already `>=2.6,<3.0` in pyproject.toml. `model_validate` API verified against `/pydantic/pydantic` docs (Context7). `[CITED: github.com/pydantic/pydantic/blob/main/docs/why.md]`
- `pyyaml 6.0.2` installed. `[VERIFIED]`
- `click 8.2.1` installed. `[VERIFIED]`

## Project Requirements

| ID | Description | Research Support |
|---|---|---|
| COG-01 | Voss creates and maintains `.voss/project.json` | `/analyze` writes via `fs_write`; schema is small dataclass (name, type, primary_language, entry_points). `cognition.load(cwd)` reads + parses. |
| COG-02 | Voss creates or updates `.voss/architecture.md` from repo analysis | `/analyze` prompt instructs agent to produce the digest with YAML frontmatter (`git_head`, `analyzed_at`, `file_count`, `analyzer_version: 1`). D-03 fixes section order; D-04 fixes frontmatter. |
| COG-03 | Voss stores constraints, permissions, validation under `.voss/*.yml` | Three pydantic schemas in `voss/harness/cognition_schemas.py` (new). `yaml.safe_load` → `Model.model_validate`; `ValidationError` is shown to user with file:line via the dot-path helper from pydantic docs. `[CITED: pydantic.dev/concepts/errors]` |
| COG-04 | Plans under `.voss/plans/` | `YYYY-MM-DD-<slug>.md` naming + frontmatter helper in `cognition.py`. Written when user `/save`'s a plan or agent explicitly persists via a future tool (deferred from M2; M2 ships the write path through agent's `fs_write` against the helper-computed path). |
| COG-05 | Sessions under `.voss/sessions/` | Replace `_state_dir()` with `_sessions_dir(cwd)`; hard cut per D-10. Legacy reader at `_legacy_state_dir()` invoked only when `--all`/`--global` flag set. |
| COG-06 | Decisions under `.voss/decisions/` | Triggered when `RunRecord.decisions` is non-empty after a turn. Same `YYYY-MM-DD-<slug>.md` + frontmatter convention. `related_session` frontmatter field links back. |
| COG-07 | `.voss-cache/` for rebuildable state only | `repo.idx` lives here. `.voss-cache/` already in project root `.gitignore` (line 9); idempotent append still safe. `.voss/.gitignore` autogenerated to ignore `sessions/`. |
| COG-08 | Per-turn run record | `RunRecord` dataclass with 14 fields per D-14. `RunRecorder` populates mechanical fields; `record_run` privileged closing call populates semantic fields. Embedded in `SessionRecord.runs`. |

## Architecture Patterns

### System Architecture Diagram

```
                            ┌────────────────────────────────────────┐
                            │           REPL launch (voss/voss chat) │
                            │  ─ _run_repl() in cli.py               │
                            └──────────────────┬─────────────────────┘
                                               │
                                               ▼
                      ┌────────────────────────────────────────────────┐
                      │ cognition.load(cwd) -> CognitionBundle         │
                      │  • reads .voss/project.json                    │
                      │  • reads .voss/architecture.md (+frontmatter)  │
                      │  • parses *.yml via pydantic schemas (LOUD)    │
                      │  • drift check: git HEAD vs frontmatter        │
                      └──────────────────┬─────────────────────────────┘
                                               │
                          drift?────► prints "cognition stale … /analyze"
                                               │
                                               ▼
        per turn:    user types task ───►  run_turn(task, …, cognition=bundle)
                                               │
                                               ▼
                  ┌──────────────────────────────────────────────────────┐
                  │  prepend SYSTEM:                                      │
                  │    architecture.md (full)                             │
                  │    constraints.yml (rendered bullets)                 │
                  │    PLAN_SYSTEM                                        │
                  │  renderer.show_cognition(arch_tokens, constraints_n)  │
                  │   • Tty: dim line                                     │
                  │   • Json: cognition_loaded event                      │
                  │  if rendered > 6k: log cognition_overflow + truncate  │
                  └──────────────────┬───────────────────────────────────┘
                                               │
                                               ▼
                  ┌──────────────────────────────────────────────────────┐
                  │  RunRecorder(turn_id, t0)  ─ collaborator             │
                  │   • observes every tool dispatch                      │
                  │     ─ fs_read/glob/grep → inspected[]                 │
                  │     ─ fs_write/edit     → changed[]                   │
                  │     ─ shell_run/voss_check → validation[]             │
                  │     ─ tool error       → failures[]                  │
                  │   • on turn end: git_diff --stat → diff_summary       │
                  │   • dispatches `record_run(...)` PRIVILEGED CALL      │
                  │     to populate semantic fields from agent's reply    │
                  └──────────────────┬───────────────────────────────────┘
                                               │
                                               ▼
                  ┌──────────────────────────────────────────────────────┐
                  │  session.append_run(record, run); session.save()      │
                  │  if run.decisions: write decisions/YYYY-MM-DD-*.md    │
                  │  if user /save plan: write plans/YYYY-MM-DD-*.md      │
                  └──────────────────────────────────────────────────────┘

  /analyze slash command path
  ──────────────────────────
        user types /analyze
              │
              ▼
   build cognition.bootstrap_prompt() ── special user prompt for run_turn
              │
              ▼
   run_turn(prompt, cognition=None, …)   ← no auto-inject (bootstrap)
   agent emits Plan whose steps call fs_write on:
        .voss/project.json
        .voss/architecture.md  (with frontmatter)
        .voss/constraints.yml  .voss/permissions.yml  .voss/validation.yml
        .voss/.gitignore
              │
              ▼
   harness rebuilds .voss-cache/repo.idx from git ls-files (post-step)
              │
              ▼
   harness appends ".voss-cache/" to project-root .gitignore (idempotent)
              │
              ▼
   renderer.show_final("cognition initialized: <files>")
```

### Recommended Project Structure (new + modified)

```
voss/harness/
├── agent.py            # MODIFIED  — RunRecorder integration, cognition prepend
├── cli.py              # MODIFIED  — /analyze slash, --all on sessions, doctor rows
├── cognition.py        # NEW       — load(cwd), drift_check, write_*_helpers
├── cognition_schemas.py # NEW      — pydantic models for *.yml
├── recorder.py         # NEW       — RunRecorder collaborator
├── session.py          # MODIFIED  — per-cwd dir, runs field, RunRecord dataclass
├── render.py           # MODIFIED  — show_cognition(arch_tokens, constraints_n)
├── tools.py            # MODIFIED  — record_run tool descriptor (privileged)
└── skills/             # NEW dir
    └── analyze.py      # NEW       — bootstrap prompt + post-step indexing

tests/harness/
├── test_cognition.py            # NEW
├── test_cognition_schemas.py    # NEW
├── test_recorder.py             # NEW
├── test_session.py              # MODIFIED — per-cwd path, runs round-trip
├── test_session_redaction.py    # MODIFIED — extend pattern scan to runs[]
├── test_cli.py                  # MODIFIED — /analyze, sessions --all, doctor rows
└── test_repl_cognition.py       # NEW — drift line, status line, NDJSON event

.voss/                          # CREATED on first /analyze
├── project.json
├── architecture.md
├── constraints.yml
├── permissions.yml
├── validation.yml
├── .gitignore                  # auto: ignores sessions/
├── plans/
├── decisions/
└── sessions/                   # gitignored via .voss/.gitignore

.voss-cache/                    # already gitignored in project root
└── repo.idx
```

### Pattern 1: Pure cognition.load(cwd) -> CognitionBundle

**What:** Single pure function. Reads, validates, returns dataclass. No I/O during turns.
**When to use:** Once at REPL launch; once per `voss do` invocation.
**Example:**

```python
# Source: pattern mirrors voss/harness/auth.py:resolve() (M1)
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml
from pydantic import ValidationError
from .cognition_schemas import (
    ConstraintsConfig, PermissionsConfig, ValidationConfig, ProjectMeta,
)

@dataclass(frozen=True)
class ArchitectureFrontmatter:
    git_head: str
    analyzed_at: str
    file_count: int
    analyzer_version: int

@dataclass(frozen=True)
class CognitionBundle:
    initialized: bool                      # .voss/architecture.md exists
    project: Optional[ProjectMeta]
    architecture_md: Optional[str]         # full body (sans frontmatter)
    architecture_frontmatter: Optional[ArchitectureFrontmatter]
    constraints: Optional[ConstraintsConfig]
    permissions: Optional[PermissionsConfig]
    validation: Optional[ValidationConfig]
    architecture_tokens: int               # litellm.token_counter on body
    load_errors: list[str]                 # populated on YAML/schema failure

def load(cwd: Path, *, model: str = "claude-sonnet-4-5") -> CognitionBundle:
    root = cwd / ".voss"
    if not (root / "architecture.md").exists():
        return CognitionBundle(initialized=False, ...all-None...)
    # parse frontmatter + body
    # yaml.safe_load each *.yml, route through Model.model_validate
    # collect errors with file:line via _format_yaml_error helper
    # count arch tokens via litellm.token_counter
    return CognitionBundle(initialized=True, ...)
```

### Pattern 2: pydantic v2 schema validation with loud error

**What:** Strict-mode `Model.model_validate(dict)` on `yaml.safe_load` output; transform `ValidationError.errors()` into `path: line — message` per the pydantic docs helper.
**When to use:** Every cognition YAML parse at REPL start.
**Example:**

```python
# Source: github.com/pydantic/pydantic/blob/main/docs/errors/errors.md (loc_to_dot_sep)
import yaml
from pydantic import BaseModel, Field, ValidationError

class ConstraintRule(BaseModel):
    model_config = {"extra": "forbid"}  # strict; reject unknown keys
    forbid: list[str] | None = None
    require_tests_for: list[str] | None = None
    max_file_size_lines: int | None = None
    custom: str | None = None

class ConstraintsConfig(BaseModel):
    model_config = {"extra": "forbid"}
    rules: list[ConstraintRule] = Field(default_factory=list)

def parse_constraints(path: Path) -> tuple[ConstraintsConfig | None, list[str]]:
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        return None, [f"{path}: invalid YAML: {e}"]
    try:
        return ConstraintsConfig.model_validate(raw), []
    except ValidationError as e:
        return None, [f"{path}: {_loc(err['loc'])}: {err['msg']}" for err in e.errors()]
```

`extra="forbid"` mirrors M1's strict-tier permission posture (D-05); unknown keys fail loud, no silent fallback.

### Pattern 3: RunRecorder collaborator

**What:** Lightweight context-manager / observer wrapping the tool-dispatch loop in `run_turn`. Captures mechanical fields without changing the agent surface.
**When to use:** Every `run_turn` invocation.
**Example:**

```python
# Source: pattern mirrors voss/harness/permissions.py:PermissionGate (observer over tool calls)
import uuid
from datetime import datetime, timezone

INSPECT_TOOLS = {"fs_read", "fs_glob", "fs_grep"}
CHANGE_TOOLS = {"fs_write", "fs_edit"}
VALIDATE_TOOLS = {"shell_run", "voss_check"}

@dataclass
class RunRecorder:
    id: str
    started_at: str
    inspected: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    validation: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    diff_summary: str = ""
    # semantic fields (populated by record_run dispatch)
    goal: str = ""
    plan: dict | None = None
    avoided: list[dict] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)

    @classmethod
    def start(cls) -> "RunRecorder":
        return cls(id=uuid.uuid4().hex[:12],
                   started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def observe(self, tool_name: str, args: dict, result: str, ok: bool) -> None:
        if not ok:
            self.failures.append({"tool": tool_name, "error": result[:200]})
            return
        if tool_name in INSPECT_TOOLS:
            p = args.get("path") or args.get("pattern") or ""
            if p: self.inspected.append(p)
        elif tool_name in CHANGE_TOOLS:
            p = args.get("path", "")
            if p: self.changed.append(p)
        elif tool_name in VALIDATE_TOOLS:
            # parse "[exit N]\n..." from result
            exit_code = _parse_exit(result)
            summary = result.splitlines()[0] if result else ""
            cmd = args.get("cmd") or f"{tool_name}({args})"
            self.validation.append({"cmd": cmd, "exit": exit_code, "summary": summary[:160]})

    def finalize(self, cwd: Path, cost_usd: float) -> "RunRecord":
        self.cost_usd = cost_usd
        self.diff_summary = _git_diff_stat(cwd)
        return RunRecord(
            id=self.id,
            started_at=self.started_at,
            ended_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **self._fields(),
        )
```

### Pattern 4: Privileged closing `record_run` dispatch (D-15)

**What:** Agent does not pick `record_run` from a tool list. Harness makes a second, smaller LLM call at end of turn whose only job is to emit the semantic fields. This makes population reliable.
**When to use:** At the end of every successful `run_turn` (skip on confidence-clarify exit).
**Example:**

```python
# Source: Claude's discretion in CONTEXT.md (D-15 + alt-shape note)
class RunSemantics(BaseModel):
    goal: str
    avoided: list[dict] = []
    assumptions: list[str] = []
    decisions: list[dict] = []
    risks: list[str] = []
    follow_ups: list[str] = []

RECORD_RUN_SYSTEM = """You are closing out an agent turn. Summarize it as a RunSemantics object.
- goal: one-line restatement of what the user asked for
- avoided: paths you considered but explicitly did NOT open, with a one-line `why`
- assumptions: things you took for granted
- decisions: choices worth preserving; each: {title, body, confidence:0-1}
- risks: what could go wrong with what you did
- follow_ups: next-session suggestions
Be terse. One bullet each."""

async def _record_run_call(provider, model, transcript: str) -> RunSemantics:
    resp = await provider.complete(
        messages=[{"role":"system","content":RECORD_RUN_SYSTEM},
                  {"role":"user","content":transcript}],
        model=model, response_format=RunSemantics,
        temperature=0.0, max_tokens=800,
    )
    return resp.parsed or RunSemantics(goal="(record_run failed)")
```

**Why privileged over public tool:** A public `record_run` tool requires the agent to choose to call it. The M1 `Plan` schema has no explicit terminal-call slot, and adding one requires either prompt discipline (unreliable) or a Plan schema change (broader blast radius). A privileged closing call is a small, isolated second LLM call dependent only on the transcript — robust, testable, and cheap (≤ 800 tokens out).

### Anti-Patterns to Avoid

- **Auto-injecting plans and decisions into every turn:** Rejected in deferred ideas. Blows the 6k cognition reserve. Agent reads via `fs_read` when needed.
- **Inferring `avoided` from `fs_grep`/`fs_glob` hits not opened:** Rejected by D-16 — too noisy. Explicit agent-reported only.
- **Mutating legacy session files at `~/.local/state/voss/sessions/`:** Legacy is read-only. Never write back. Never auto-migrate.
- **Truncating architecture.md to fit 6k:** Wrong order — D-18 says truncate constraints first, keep architecture intact, surface user hint.
- **Silently coercing YAML types:** Use `extra="forbid"` and strict mode where coercion would mask user typos.
- **Blocking on drift detection:** Print hint and continue; mirrors M1 D-13 "doctor diagnose, don't fix" stance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| .gitignore matching for repo walk | Custom `.gitignore` parser | `git ls-files` (D-05) | Handles nested `.gitignore`, `.git/info/exclude`, global core.excludesFile, symlink semantics. Reimplementing is a known footgun. |
| YAML frontmatter parsing | Regex `^---\n(.*?)\n---` then `yaml.safe_load` is fine | Use `yaml.safe_load(re_extract)` — short helper, not a new dep | A `python-frontmatter` package exists but ships no functionality we don't already have; one short helper keeps deps tight. **Exception to the rule: this is small enough to hand-roll.** |
| Schema validation for *.yml configs | Manual `isinstance` checks | pydantic v2 (already a dep) | Strict mode + `extra="forbid"` + ValidationError → friendly file:line. `[CITED: pydantic.dev/concepts/strict_mode]` |
| Token counting for cognition budget | Heuristic `len(text)/4` | `litellm.token_counter(model=..., text=...)` | Already used by `voss_runtime.context`; per-model accurate. `[VERIFIED: voss_runtime/providers/litellm_provider.py:62]` |
| Per-cwd session resolution | New global registry of cwd→session-ids | Filesystem layout (`<cwd>/.voss/sessions/<id>.json`) | The path **is** the index. `list_sessions(cwd)` is one `glob`. |
| File sha for `repo.idx` | Full content hashing | sha1 over file bytes via `hashlib.sha1` (stdlib) | Fast enough; matches git's own approach. No need for fancy chunked Merkle. |
| Decision/plan filename collision | Increment-and-retry race | Deterministic `-2, -3` suffix on collision (single-process REPL; no concurrent writers) | M2 is single-process; no race. |

**Key insight:** Every "tempting to hand-roll" task in this phase already has a project dep that solves it. The cognition module is gluing existing pieces, not building new infrastructure.

## Runtime State Inventory

> M2 is partly a migration phase: session storage moves from global to per-project. This inventory captures runtime state.

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | Legacy session JSON at `~/.local/state/voss/sessions/*.json` (M1 location). These remain in place indefinitely (D-12). | Read-only legacy reader (`session._legacy_state_dir()`); no migration. Mark each as `[legacy]` in `voss sessions --all` output. |
| Live service config | None — Voss has no daemon, no external service. | None — verified by code inspection. |
| OS-registered state | None — Voss has no systemd, launchd, Task Scheduler, or pm2 process. | None — verified by absence in `voss/`, `pyproject.toml` `[project.scripts]`. |
| Secrets/env vars | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XDG_STATE_HOME`, `XDG_CONFIG_HOME` — all read by existing M1 code. M2 reads `XDG_STATE_HOME` only for the legacy reader path. | No new env vars introduced. Existing names unchanged. |
| Build artifacts / installed packages | `voss` console script entry (pyproject.toml `[project.scripts] voss = "voss.cli:main"`). M2 adds no new entry points. | None — no reinstall needed. |

**The canonical question — "After every file in the repo is updated, what runtime systems still have the old string cached/stored/registered?"** Answer for M2: legacy session JSONs in `~/.local/state/voss/sessions/`. They are deliberately left in place per D-12.

## Common Pitfalls

### Pitfall 1: Agent fails to call `record_run`
**What goes wrong:** Semantic fields (goal, plan, avoided, decisions, risks, follow_ups) all empty.
**Why it happens:** If `record_run` is a public tool, the agent omits it under pressure (one-shot `voss do`, ambiguous prompts). If it's a privileged closing call, the closing LLM call may itself fail (provider timeout, malformed response).
**How to avoid:** Use privileged closing call (D-15 Claude's discretion area). Wrap in try/except — on failure, log a warning and persist a `RunRecord` with mechanical fields only and `goal="(record_run failed)"`. Never crash the turn. Test pattern: feed a turn where the closing call returns malformed JSON; assert turn still completes and RunRecord persists with mechanical-only data.
**Warning signs:** `RunRecord.goal == ""` in test output, `failures[]` populated but `decisions[]`/`risks[]` empty across many sessions.

### Pitfall 2: Architecture.md exceeds 6k token budget
**What goes wrong:** Cognition block crowds out user task + tool results within the 60k `ContextScope`.
**Why it happens:** Agent writes a verbose architecture digest on `/analyze`, especially on large repos.
**How to avoid:** D-18 — truncate constraints first (keep architecture intact), log `cognition_overflow`, surface a user-visible hint "architecture.md is X tokens (over 6k budget) — /analyze can rewrite a tighter digest". The `/analyze` prompt itself constrains the agent to ≤ 1-2 pages (D-03 fixed sections).
**Warning signs:** `cognition_overflow` events in NDJSON; user sees the hint on REPL startup.

### Pitfall 3: Secret leaks into RunRecord
**What goes wrong:** `validation` field contains a `shell_run` invocation that echoed a secret env var; `failures` field contains a tool error whose message embedded a path with a token; `decisions[].body` contains agent free-form prose that quotes provider credentials.
**Why it happens:** Mechanical capture is verbatim from tool results. Tool results are not redacted.
**How to avoid:** Same schema-allowlist guarantee as M1: `RunRecord` is a fixed-field dataclass. Top-level keys cannot leak. **For value-level secrets,** extend `tests/harness/test_session_redaction.py` (D-17 pattern) to scan every saved `RunRecord` field for the six secret patterns from M1-03: `sk-ant-`, `sk-proj-`, `Bearer `, `oauth_token`, `access_token`, `Authorization`. The test must construct a synthetic clean turn, run it end-to-end with a stub provider, save the session, then assert patterns absent from the JSON.
**Warning signs:** Redaction CI test fails. Manual: searching `.voss/sessions/*.json` for `Bearer ` returns hits.

### Pitfall 4: Drift detection false-positive after rebase
**What goes wrong:** `git_head` in frontmatter no longer exists after rebase; HEAD comparison fails ungracefully.
**Why it happens:** D-04 compares HEAD by commit-count divergence (`git rev-list --count <frontmatter_head>..HEAD`). After force-rebase, `<frontmatter_head>` may be unreachable.
**How to avoid:** Wrap `git rev-list --count` in try/except. On nonzero exit ("unknown revision"), treat as drift (force-trigger the hint) but never raise. Add file-count and date checks as orthogonal triggers — any one of the three triggers the hint.
**Warning signs:** Exception traceback printed at REPL launch in a force-rebased repo.

### Pitfall 5: Per-cwd session resolution for `voss resume <id-prefix>`
**What goes wrong:** User runs `voss resume abc123` from project A but session `abc123…` lives under project B's `.voss/sessions/`. Current cwd-only lookup misses it.
**Why it happens:** D-11 says `voss sessions` (no flag) is cwd-scoped, but `voss resume <id>` is documented as resolving through both locations. The resume lookup must scan all `.voss/sessions/` under cwd AND the legacy global dir, choosing the highest-confidence match.
**How to avoid:** Implement `load(session_id_or_name, cwd: Path)` that first searches `<cwd>/.voss/sessions/`, then legacy `~/.local/state/voss/sessions/`. On the legacy hit, log a one-line note: `resuming legacy session from ~/.local/state/voss/sessions/<id>.json`. Test pattern: write a session under each path, assert resume finds both.
**Warning signs:** "no session: abc123" when user knows session exists.

### Pitfall 6: `.voss/.gitignore` and project-root `.gitignore` double-writing
**What goes wrong:** Every `/analyze` re-appends `.voss-cache/` to the project root `.gitignore`, producing duplicate lines.
**Why it happens:** Idempotence is in CONTEXT.md (D-09) but easy to miss.
**How to avoid:** Read the file, check `\n.voss-cache/\n` or `^.voss-cache/$` line membership, only append if absent. Single helper `append_gitignore_line_idempotent(path, line)` in `cognition.py`.
**Warning signs:** `.gitignore` git diff shows duplicate `.voss-cache/` lines.

### Pitfall 7: Legacy `SessionRecord.runs` deserialization
**What goes wrong:** Sessions saved by M1 (pre-runs field) fail to load after M2 lands.
**Why it happens:** M1 session JSONs lack the `runs` key; naive `SessionRecord(**data)` raises TypeError.
**How to avoid:** Use `field(default_factory=list)` on `runs` AND change the `load()` line `SessionRecord(**{k: v for k, v in data.items() if k != "turns"})` to also handle missing `runs` (defaults applied automatically). Confirmed in CONTEXT.md Claude's-Discretion list — "straightforward; pick the obvious default."
**Warning signs:** TypeError on `voss resume <legacy-id>`.

## Code Examples

### `cognition.py` skeleton

```python
# Source: pattern mirrors voss/harness/auth.py (M1) — pure resolution returns dataclass
"""Project cognition: load durable .voss/ state, drift-check, helpers."""
from __future__ import annotations
import re, yaml, subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from .cognition_schemas import (
    ProjectMeta, ConstraintsConfig, PermissionsConfig, ValidationConfig,
)

ANALYZER_VERSION = 1
DRIFT_COMMITS = 20
DRIFT_FILE_PCT = 0.10
DRIFT_DAYS = 7

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

@dataclass(frozen=True)
class ArchitectureFrontmatter:
    git_head: str
    analyzed_at: str
    file_count: int
    analyzer_version: int

@dataclass(frozen=True)
class CognitionBundle:
    initialized: bool
    project: Optional[ProjectMeta] = None
    architecture_md: Optional[str] = None
    architecture_frontmatter: Optional[ArchitectureFrontmatter] = None
    constraints: Optional[ConstraintsConfig] = None
    permissions: Optional[PermissionsConfig] = None
    validation: Optional[ValidationConfig] = None
    architecture_tokens: int = 0
    load_errors: list[str] = field(default_factory=list)

def voss_dir(cwd: Path) -> Path:
    return cwd / ".voss"

def cache_dir(cwd: Path) -> Path:
    return cwd / ".voss-cache"

def load(cwd: Path, *, token_count: callable = None) -> CognitionBundle:
    root = voss_dir(cwd)
    if not (root / "architecture.md").exists():
        return CognitionBundle(initialized=False)
    errors: list[str] = []
    proj = _load_json(root / "project.json", ProjectMeta, errors)
    arch_body, arch_fm = _load_arch(root / "architecture.md", errors)
    constraints = _load_yaml(root / "constraints.yml", ConstraintsConfig, errors)
    permissions = _load_yaml(root / "permissions.yml", PermissionsConfig, errors)
    validation = _load_yaml(root / "validation.yml", ValidationConfig, errors)
    tok = token_count(arch_body) if (token_count and arch_body) else 0
    return CognitionBundle(
        initialized=True, project=proj, architecture_md=arch_body,
        architecture_frontmatter=arch_fm, constraints=constraints,
        permissions=permissions, validation=validation,
        architecture_tokens=tok, load_errors=errors,
    )

@dataclass
class DriftStatus:
    is_stale: bool
    head_diverged_by: int
    file_count_delta: int
    days_elapsed: int
    reason: str = ""

def drift_check(cwd: Path, fm: ArchitectureFrontmatter) -> DriftStatus:
    head_div = _git_rev_list_count(cwd, fm.git_head)
    cur_files = _git_ls_files_count(cwd)
    file_delta = cur_files - fm.file_count
    days = _days_since(fm.analyzed_at)
    triggers = []
    if head_div >= DRIFT_COMMITS: triggers.append(f"HEAD +{head_div} commits")
    if abs(file_delta) / max(fm.file_count, 1) >= DRIFT_FILE_PCT:
        triggers.append(f"{'+' if file_delta>=0 else ''}{file_delta} files")
    if days >= DRIFT_DAYS: triggers.append(f"{days}d old")
    return DriftStatus(
        is_stale=bool(triggers), head_diverged_by=head_div,
        file_count_delta=file_delta, days_elapsed=days,
        reason=", ".join(triggers),
    )

def render_constraints_bullets(c: ConstraintsConfig | None) -> str:
    if not c or not c.rules: return ""
    lines = []
    for r in c.rules:
        if r.forbid: lines.append(f"- forbid: {', '.join(r.forbid)}")
        if r.require_tests_for: lines.append(f"- require tests for: {', '.join(r.require_tests_for)}")
        if r.max_file_size_lines: lines.append(f"- max file size: {r.max_file_size_lines} lines")
        if r.custom: lines.append(f"- {r.custom}")
    return "\n".join(lines)

def append_gitignore_line_idempotent(path: Path, line: str) -> bool:
    """Return True if appended, False if already present."""
    line_stripped = line.strip()
    if path.exists():
        for existing in path.read_text().splitlines():
            if existing.strip() == line_stripped: return False
    with path.open("a") as f:
        if path.exists() and path.read_text() and not path.read_text().endswith("\n"):
            f.write("\n")
        f.write(line.rstrip("\n") + "\n")
    return True

def slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:60] or "untitled"

def reserve_filename(dir_: Path, base: str, ext: str = ".md") -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p = dir_ / f"{today}-{base}{ext}"
    n = 2
    while p.exists():
        p = dir_ / f"{today}-{base}-{n}{ext}"
        n += 1
    return p
```

### `cognition_schemas.py` (pydantic v2 strict)

```python
# Source: pydantic v2 docs https://github.com/pydantic/pydantic/blob/main/docs/concepts/strict_mode.md
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

STRICT = {"extra": "forbid"}  # reject unknown keys; loud failures (D-07)

# project.json
class ProjectMeta(BaseModel):
    model_config = STRICT
    name: str
    type: str = "library"  # library|app|cli|service|other (free-form, recommended set)
    primary_language: str
    entry_points: list[str] = Field(default_factory=list)

# constraints.yml
class ConstraintRule(BaseModel):
    model_config = STRICT
    forbid: list[str] | None = None
    require_tests_for: list[str] | None = None
    max_file_size_lines: int | None = Field(default=None, gt=0)
    custom: str | None = None

class ConstraintsConfig(BaseModel):
    model_config = STRICT
    rules: list[ConstraintRule] = Field(default_factory=list)

# permissions.yml
class ToolPolicy(BaseModel):
    model_config = STRICT
    allow: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)

class PathScope(BaseModel):
    model_config = STRICT
    glob: str
    modes: list[Literal["plan", "edit", "auto"]]

class PermissionsConfig(BaseModel):
    model_config = STRICT
    tool_policy: ToolPolicy = Field(default_factory=ToolPolicy)
    path_scopes: list[PathScope] = Field(default_factory=list)

# validation.yml
class ValidationCommand(BaseModel):
    model_config = STRICT
    name: str
    run: str
    on: list[Literal["save", "pre_apply", "post_run"]]

class ValidationConfig(BaseModel):
    model_config = STRICT
    commands: list[ValidationCommand] = Field(default_factory=list)
```

### `session.py` extension (additive, redaction-safe)

```python
# Source: extends existing voss/harness/session.py while preserving M1 D-16/D-17 guarantees.
@dataclass
class RunRecord:
    id: str
    started_at: str
    ended_at: str
    goal: str = ""
    plan: dict | None = None
    inspected: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    avoided: list[dict] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)  # {title, body, confidence}
    risks: list[str] = field(default_factory=list)
    validation: list[dict] = field(default_factory=list)  # {cmd, exit, summary}
    failures: list[dict] = field(default_factory=list)    # {tool, error}
    diff_summary: str = ""
    follow_ups: list[str] = field(default_factory=list)
    cost_usd: float = 0.0

@dataclass
class SessionRecord:
    id: str
    name: str
    cwd: str
    model: str
    started_at: str
    updated_at: str
    total_cost_usd: float = 0.0
    turns: list[dict] = field(default_factory=list)
    runs: list[dict] = field(default_factory=list)   # NEW — asdict(run) per turn

def _sessions_dir(cwd: Path) -> Path:
    return (cwd / ".voss" / "sessions").resolve()

def _legacy_state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "voss" / "sessions"

def list_sessions(cwd: Path, *, include_legacy: bool = False) -> list[SessionRecord]:
    out: list[SessionRecord] = []
    d = _sessions_dir(cwd)
    if d.exists():
        out.extend(_read_dir(d))
    if include_legacy and _legacy_state_dir().exists():
        out.extend(_read_dir(_legacy_state_dir(), legacy=True))
    return sorted(out, key=lambda r: r.updated_at, reverse=True)

def load(session_id_or_name: str, cwd: Path | None = None) -> tuple[SessionRecord, EpisodicMemory]:
    """Resolve in per-cwd dir first, fall back to legacy."""
    candidates: list[Path] = []
    if cwd is not None:
        candidates += list(_sessions_dir(cwd).glob("*.json"))
    candidates += list(_legacy_state_dir().glob("*.json"))
    # match prefix or name; if ambiguous raise; legacy hits are read-only
    ...
```

### `record_run` privileged closing dispatch in `agent.py`

```python
# Source: integrates into existing run_turn at end-of-turn; D-15 reliability choice.
async def run_turn(task, *, tools, cwd, renderer, cognition=None, ...) -> TurnResult:
    rec = RunRecorder.start()
    # ... existing flow ...
    # cognition prepend:
    sys_prompt = PLAN_SYSTEM
    if cognition and cognition.initialized:
        sys_prompt = _compose_cognition_prompt(cognition) + "\n\n" + PLAN_SYSTEM
        renderer.show_cognition(cognition.architecture_tokens, len(cognition.constraints.rules) if cognition.constraints else 0)

    # ... plan call, tool loop, calling rec.observe(name, args, result, ok) inside ...

    # End-of-turn semantic capture (privileged closing call).
    transcript = _build_run_transcript(task, plan, results, rec)
    try:
        semantics = await _record_run_call(provider, model, transcript)
        rec.absorb(semantics, plan)
    except Exception as e:  # noqa: BLE001
        renderer.show_warning(f"record_run failed: {e}; persisting mechanical-only RunRecord")

    run = rec.finalize(cwd, cost_usd=total_cost)
    return TurnResult(plan=plan, confidence=plan.confidence, final=final,
                      tool_results=results, cost_usd=resp.cost_usd, run=run)
```

## State of the Art

| Old Approach (M1) | Current Approach (M2) | When Changed | Impact |
|---|---|---|---|
| `_state_dir()` reads `XDG_STATE_HOME` for sessions | `_sessions_dir(cwd)` for new sessions; `_legacy_state_dir()` only for `--all` reads | M2 D-10 | Per-project session truth; legacy stays readable in place |
| No structured per-turn record | `SessionRecord.runs: list[RunRecord]` (mechanical + semantic) | M2 D-13/D-14/D-15 | Inspectable run ledger; agent self-reports goals/decisions/risks |
| Free-form session JSON only | Same schema-allowlist invariant extended to RunRecord fields | M2 D-17 (extends M1) | Secret-leak surface widened but covered by extended redaction test |
| No cognition auto-injection | architecture.md + constraints.yml prepended to every system prompt | M2 D-17/D-18 | 6k token reservation; renderer status line; NDJSON event |
| `voss sessions` is global | `voss sessions` is cwd-scoped; `--all`/`--global` reads legacy | M2 D-11 | Cleaner mental model; legacy reachable |

**Deprecated/outdated:** None — M2 strictly extends M1, no retraction of M1 behavior except the session-storage path (which is a hard cut on new writes, but legacy reads remain).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | A privileged closing `record_run` LLM call yields more reliable semantic-field population than a public tool the agent must remember to call. | Pattern 4 | Higher cost per turn (~one extra small completion ≤ 800 output tokens). If wrong (public tool actually works fine), we waste ~$0.001-0.005/turn — recoverable, not blocking. CONTEXT.md flags this as Claude's-discretion. |
| A2 | `litellm.token_counter(model=..., text=text)` is the right token-count function for the cognition budget, matching how `voss_runtime/context.py` already measures tokens. | "Don't Hand-Roll" | If off by ±10% the 6k reserve is slightly inaccurate — overflow trigger fires earlier or later than intended. Self-correcting via the user-visible hint. |
| A3 | YAML files written by the agent via `fs_write` are well-formed enough for `yaml.safe_load` (i.e. the agent doesn't emit tabs-vs-spaces issues or unbalanced quotes). | Pattern 2 | If wrong, REPL boot prints a loud pointer to the offending file:line (D-07). User edits manually. Not silent. |
| A4 | M1 (currently 7 plans, ready-to-execute) lands before M2 execution starts — specifically M1-03 redaction test, M1-01 permission tiers, M1-05 slash-command registry. | Whole research | If M2 starts before M1 lands, the integration points (PermissionGate layering, slash-command registry, redaction test extension) don't exist yet. Mitigation: M2 plans declare `depends_on: M1` and Wave 0 verifies preconditions. |
| A5 | `git rev-list --count <frontmatter_sha>..HEAD` exits non-zero on unreachable SHAs (after force-rebase), allowing detection without an exception trace. | Pitfall 4 | If git silently returns 0, drift detection misses force-rebases. Test pattern explicitly force-rebases a fixture repo and asserts drift triggered. |
| A6 | `.voss/sessions/` per-cwd is unambiguous because `cwd` is captured at session-create time and resolves to an absolute path. Subsequent `voss resume` from any subdirectory of that cwd still finds the session (`.voss/sessions/` under the project root). | D-11 / Pitfall 5 | If a user runs `voss resume` from outside any project, both per-cwd and legacy paths come back empty. Fall back to scanning sibling `.voss/` dirs is **not** in scope; document "run from project root or use `--all`". |
| A7 | The 6k token cognition reserve is sufficient for `PLAN_SYSTEM` (≈400 tokens) + architecture.md (target ≤4k) + constraints bullets (target ≤1k). | D-18 | If a real-world architecture.md grows past 5k, constraints get truncated and the user sees the hint. The /analyze prompt enforces 1-2 page target. |

**Assumptions A1, A4 are the load-bearing ones.** A1 is a Claude's-discretion area in CONTEXT.md; A4 is a sequencing dependency the planner must respect.

## Open Questions

1. **`record_run` cost & reliability across providers**
   - What we know: privileged closing call costs ≤ 800 output tokens at temperature 0 with structured response_format. With Claude Sonnet 4.5 (~$0.003/1k out) that's ≤ $0.0024/turn.
   - What's unclear: whether all providers reliably honor `response_format=RunSemantics` with their OAuth flows. M1 ships Anthropic OAuth and Codex OAuth; reliability difference unknown until tested.
   - Recommendation: implement with provider-agnostic `response_format`; fall back to plain-text + post-parse JSON if `resp.parsed is None`. Add a test that injects a stub provider returning malformed JSON, asserts RunRecord persists with `goal="(record_run failed)"` and mechanical fields intact.

2. **Plan persistence trigger**
   - What we know: plans are persisted on user-accept or agent explicit save (deferred ideas item). M2 must ship at least the write helper.
   - What's unclear: whether M2 ships a `/save-plan` slash command or relies on agent-driven persistence via `fs_write` against a `cognition.plan_path(slug)` helper.
   - Recommendation: ship the helper, expose to the agent via the cognition bootstrap prompt ("use the provided `cognition.plan_path()` for filenames"); skip the `/save-plan` slash command until dogfood demands it. Planner can choose.

3. **`.voss/permissions.yml` layering precedence with M1 `PermissionGate`**
   - What we know: CONTEXT.md flags this as Claude's-discretion: "design so project rules layer additively (deny wins over allow); spell out conflict precedence when implementing."
   - What's unclear: does `permissions.yml` deny override session-level `--mode auto`?
   - Recommendation: deny-from-yml always wins; allow-from-yml is additive (cannot expand session permissions). Document in `permissions.py` module docstring. Test pattern: yml says `deny: [shell_run]`; session is `auto`; assert `shell_run` denied.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python | Whole project | ✓ | 3.13 (system); pyproject requires `>=3.11` | — |
| pydantic | cognition_schemas.py, agent.py Plan | ✓ (declared dep) | `>=2.6,<3.0` | — |
| PyYAML | cognition.py YAML parsing | ✓ (installed but **not declared in pyproject** — added implicitly via litellm or chromadb) | 6.0.2 | Planner MUST add `pyyaml>=6.0` to `pyproject.toml [project] dependencies`. |
| litellm | `litellm.token_counter` for cognition budget | ✓ (declared) | `>=1.50.0` | — |
| git CLI | `git ls-files`, `git rev-parse HEAD`, `git rev-list --count`, `git diff --stat` | ✓ | — | Walk fallback for non-git repos (D-05) |
| sha1 (hashlib) | repo.idx file hashes | ✓ | stdlib | — |
| click | sessions --all flag | ✓ (declared) | `>=8.1.0` | — |
| rich | renderer | ✓ (declared) | `>=13.0.0` | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- **PyYAML undeclared**: Currently importable due to transitive dep. **Planner action:** add `"pyyaml>=6.0"` to `pyproject.toml [project] dependencies`. This is a small but real risk if a future transitive dep drops PyYAML.

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest 8.x + pytest-asyncio (`asyncio_mode=auto`) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `pytest tests/harness/ -x` |
| Full suite command | `pytest -q --strict-markers` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| COG-01 | `/analyze` writes `.voss/project.json` matching `ProjectMeta` schema | integration | `pytest tests/harness/test_cognition.py::test_analyze_writes_project_json -x` | ❌ Wave 0 (new file) |
| COG-02 | `/analyze` writes `.voss/architecture.md` with valid frontmatter (git_head, analyzed_at, file_count, analyzer_version) | integration | `pytest tests/harness/test_cognition.py::test_architecture_md_frontmatter_well_formed -x` | ❌ Wave 0 |
| COG-02 | `cognition.load` parses architecture.md frontmatter back into `ArchitectureFrontmatter` | unit | `pytest tests/harness/test_cognition.py::test_load_parses_frontmatter -x` | ❌ Wave 0 |
| COG-02 | `drift_check` fires on +20 commits | unit | `pytest tests/harness/test_cognition.py::test_drift_commits_threshold -x` | ❌ Wave 0 |
| COG-02 | `drift_check` fires on 10% file count delta | unit | `pytest tests/harness/test_cognition.py::test_drift_file_count_threshold -x` | ❌ Wave 0 |
| COG-02 | `drift_check` fires on 7 days elapsed | unit | `pytest tests/harness/test_cognition.py::test_drift_days_threshold -x` | ❌ Wave 0 |
| COG-02 | `drift_check` is non-blocking (just returns status) | unit | included above | ❌ Wave 0 |
| COG-03 | `ConstraintsConfig` rejects unknown keys | unit | `pytest tests/harness/test_cognition_schemas.py::test_constraints_extra_forbid -x` | ❌ Wave 0 |
| COG-03 | `PermissionsConfig` parses tool_policy + path_scopes | unit | `pytest tests/harness/test_cognition_schemas.py::test_permissions_layered_with_gate -x` | ❌ Wave 0 |
| COG-03 | `ValidationConfig` accepts `on: [save|pre_apply|post_run]` only | unit | `pytest tests/harness/test_cognition_schemas.py::test_validation_on_enum -x` | ❌ Wave 0 |
| COG-03 | Malformed YAML at REPL startup prints file:line; doesn't crash | integration | `pytest tests/harness/test_repl_cognition.py::test_bad_yaml_loud_failure -x` | ❌ Wave 0 |
| COG-04 | Plan write helper produces `YYYY-MM-DD-<slug>.md` with frontmatter | unit | `pytest tests/harness/test_cognition.py::test_plan_filename_and_frontmatter -x` | ❌ Wave 0 |
| COG-04 | Slug collision on same day appends `-2`, `-3` | unit | `pytest tests/harness/test_cognition.py::test_reserve_filename_collision -x` | ❌ Wave 0 |
| COG-05 | New sessions write to `<cwd>/.voss/sessions/<id>.json` | unit | `pytest tests/harness/test_session.py::test_save_writes_per_cwd_path -x` | ✅ extend existing |
| COG-05 | `voss sessions` (no flag) lists only cwd-scoped sessions | integration | `pytest tests/harness/test_cli.py::test_sessions_cwd_scoped -x` | ✅ extend existing |
| COG-05 | `voss sessions --all` reads legacy `~/.local/state/voss/sessions/` and tags `[legacy]` | integration | `pytest tests/harness/test_cli.py::test_sessions_all_includes_legacy -x` | ✅ extend existing |
| COG-05 | `voss resume <id>` finds both per-cwd and legacy | unit | `pytest tests/harness/test_session.py::test_load_falls_back_to_legacy -x` | ✅ extend existing |
| COG-05 | Legacy session writes never trigger (read-only) | unit | `pytest tests/harness/test_session.py::test_legacy_path_never_written -x` | ✅ extend existing |
| COG-05 | Legacy sessions missing `runs` field default to `[]` (backward-compat) | unit | `pytest tests/harness/test_session.py::test_load_legacy_without_runs_field -x` | ✅ extend existing |
| COG-06 | Decisions mirrored to `.voss/decisions/<slug>.md` when `RunRecord.decisions` non-empty | integration | `pytest tests/harness/test_recorder.py::test_decisions_mirror_to_markdown -x` | ❌ Wave 0 |
| COG-06 | Decision frontmatter contains `related_session: <id>`, `confidence: <float>`, `status: active`, `created_at`, `id` | unit | `pytest tests/harness/test_cognition.py::test_decision_frontmatter -x` | ❌ Wave 0 |
| COG-07 | `.voss-cache/repo.idx` JSON manifest contains `version`, `git_head`, `files[]` with path/size/mtime/sha | unit | `pytest tests/harness/test_cognition.py::test_repo_idx_schema -x` | ❌ Wave 0 |
| COG-07 | `.voss-cache/` line appended idempotently to project-root `.gitignore` | unit | `pytest tests/harness/test_cognition.py::test_gitignore_idempotent -x` | ❌ Wave 0 |
| COG-07 | `.voss/.gitignore` autogenerated with `sessions/` | unit | `pytest tests/harness/test_cognition.py::test_voss_gitignore_autogenerated -x` | ❌ Wave 0 |
| COG-08 | `RunRecorder` captures `inspected` from `fs_read`/`fs_glob`/`fs_grep` | unit | `pytest tests/harness/test_recorder.py::test_inspect_captures_fs_read -x` | ❌ Wave 0 |
| COG-08 | `RunRecorder` captures `changed` from `fs_write`/`fs_edit` | unit | `pytest tests/harness/test_recorder.py::test_change_captures_fs_write -x` | ❌ Wave 0 |
| COG-08 | `RunRecorder` captures `validation` from `shell_run`/`voss_check` with exit codes | unit | `pytest tests/harness/test_recorder.py::test_validation_captures_exit_code -x` | ❌ Wave 0 |
| COG-08 | `RunRecorder` captures `failures` from tool exceptions | unit | `pytest tests/harness/test_recorder.py::test_failure_captures_tool_error -x` | ❌ Wave 0 |
| COG-08 | `RunRecord.diff_summary` is `git diff --stat` at end of turn | unit | `pytest tests/harness/test_recorder.py::test_diff_summary_from_git -x` | ❌ Wave 0 |
| COG-08 | Privileged `record_run` closing call populates semantic fields | integration (with stub provider) | `pytest tests/harness/test_agent_integration.py::test_record_run_populates_semantic_fields -x` | ✅ extend existing |
| COG-08 | If `record_run` closing call fails, RunRecord still persists with mechanical-only data + `goal="(record_run failed)"` | integration | `pytest tests/harness/test_agent_integration.py::test_record_run_failure_persists_mechanical -x` | ✅ extend existing |
| COG-08 | RunRecord secret redaction: clean turn produces JSON without any of the 6 secret patterns (`sk-ant-`, `sk-proj-`, `Bearer `, `oauth_token`, `access_token`, `Authorization`) | unit | `pytest tests/harness/test_session_redaction.py::test_run_record_no_secret_patterns -x` | ✅ extend existing (depends on M1-03) |
| COG-08 | RunRecord schema-allowlist: serialized run dict has exactly the 17 declared keys | unit | `pytest tests/harness/test_session_redaction.py::test_run_record_top_level_keys -x` | ✅ extend existing |
| Cognition auto-injection | architecture.md + constraints bullets prepended to system prompt every turn | integration | `pytest tests/harness/test_agent_integration.py::test_turn_injects_cognition -x` | ✅ extend existing |
| Cognition auto-injection | `cognition_overflow` event fires + constraints truncate when render exceeds 6k tokens | unit | `pytest tests/harness/test_repl_cognition.py::test_cognition_overflow_truncates_constraints -x` | ❌ Wave 0 |
| Cognition status line | Tty renderer prints `cognition: architecture (Xk) + N constraints` | unit | `pytest tests/harness/test_repl_cognition.py::test_cognition_status_line_tty -x` | ❌ Wave 0 |
| Cognition status line | NDJSON renderer emits `cognition_loaded` event | unit | `pytest tests/harness/test_repl_cognition.py::test_cognition_loaded_ndjson_event -x` | ❌ Wave 0 |
| `/analyze` slash command | `/analyze` routes to bootstrap handler | integration | `pytest tests/harness/test_cli.py::test_slash_analyze_routes -x` | ✅ extend existing |
| `/analyze` slash command | Natural-language "analyze repo" routes to same handler via intent classifier | integration | `pytest tests/harness/test_cli.py::test_natural_analyze_routes -x` | ✅ extend existing |
| Drift hint at REPL launch | Hint printed when drift threshold met; never blocks | integration | `pytest tests/harness/test_repl_cognition.py::test_drift_hint_printed_non_blocking -x` | ❌ Wave 0 |
| `voss doctor` extension | New rows: `.voss/ initialized`, `cognition staleness`, `legacy sessions detected` | integration | `pytest tests/harness/test_cli.py::test_doctor_cognition_rows -x` | ✅ extend existing |
| `voss resume` rehydration | "Prior context" block injected with most-recent `RunRecord.{goal,plan,decisions,follow_ups,risks}` | integration | `pytest tests/harness/test_agent_integration.py::test_resume_injects_prior_run_context -x` | ✅ extend existing |

### Sampling Rate
- **Per task commit:** `pytest tests/harness/ -x` (full harness suite ~30s)
- **Per wave merge:** `pytest tests/ -x` (full suite)
- **Phase gate:** Full suite green + `pytest -m live` not required (M2 uses stub provider exclusively)

### Wave 0 Gaps
- [ ] `tests/harness/test_cognition.py` — new file; covers COG-01, COG-02, COG-04, COG-06 frontmatter, COG-07 (idx + gitignore)
- [ ] `tests/harness/test_cognition_schemas.py` — new file; covers COG-03 schema validation
- [ ] `tests/harness/test_recorder.py` — new file; covers COG-08 mechanical capture
- [ ] `tests/harness/test_repl_cognition.py` — new file; covers drift, status line, NDJSON event, overflow, malformed YAML loud failure
- [ ] Test fixture: a tiny synthetic git repo (`tmp_path` + `git init` + commits) for drift tests and `git ls-files` walk — shared `conftest.py` fixture `git_repo` in `tests/harness/`
- [ ] Test fixture: a stub provider that returns a fixed `Plan` + fixed `RunSemantics` for cognition-injection and record_run tests (extend the existing fixture pattern in `test_agent_integration.py`)
- [ ] Framework install: none — pytest, pytest-asyncio already declared `dev`
- [ ] `pyproject.toml`: add `"pyyaml>=6.0"` to `[project] dependencies` (currently transitive)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no (M1 handles) | — |
| V3 Session Management | yes (M2 changes session storage layout) | Schema-allowlist serialization (M1 D-16); 0600 file mode (already in `session.save`); per-cwd path containment |
| V4 Access Control | yes (path jail + permissions.yml layering) | Reuse `sandbox.jail_path`; layer `permissions.yml` deny-wins-over-allow into `PermissionGate.check` |
| V5 Input Validation | yes (YAML config + agent-emitted markdown frontmatter) | pydantic v2 strict mode; `yaml.safe_load` (never `yaml.load`); fail loud at REPL boot, never mid-turn |
| V6 Cryptography | no (sha1 in repo.idx is content-fingerprint, not cryptographic) | — |
| V9 Communications | no (no network I/O introduced in M2) | — |

### Known Threat Patterns for Python harness writing project-local files

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Secret in tool result (e.g. `shell_run` echoes `$ANTHROPIC_API_KEY`) leaking into `RunRecord.validation[].summary` | Information Disclosure | Schema-allowlist (M1 D-16) + extended redaction CI test (M1 D-17 pattern); validation summaries truncated to 160 chars; CI scan all RunRecord field values for the six secret patterns. |
| Agent writes outside `.voss/` (e.g. `/etc/passwd`) via `fs_write` | Tampering | `sandbox.jail_path(cwd, target)` already rejects path escape; permissions.yml `path_scopes` can further restrict; M2 adds no new write surface outside cwd. |
| YAML deserialization gadget (`!!python/object`) | Tampering | `yaml.safe_load` only; never `yaml.load`. |
| Malformed git frontmatter triggers crash mid-turn (DoS) | Denial of Service | Drift check and load wrapped in try/except returning `load_errors`; user-visible error, never raises. |
| Symlink in `.voss/` pointing outside cwd (e.g. `.voss/architecture.md` → `/etc/shadow`) | Information Disclosure | `Path.resolve()` then `relative_to(cwd)` check; same pattern as `sandbox.jail_path`. |
| RunRecord `decisions[].body` agent free-form text contains user-pasted secret from prompt | Information Disclosure (acknowledged) | User-typed content is intentionally preserved (M1 D-17 carve-out: `TestUserPromptsArePassthrough`). Same posture applies to RunRecord. Document explicitly. |

## Project Constraints (from CLAUDE.md)

No project-level `./CLAUDE.md` exists in the Voss repo (`/Users/benjaminmarks/Projects/Voss/CLAUDE.md` does not exist). The user's global `~/.claude/CLAUDE.md` directives are general (think before coding, simplicity first, surgical changes, goal-driven execution) and do not impose Voss-specific constraints. The repo's source of truth is `.vscode/voss_v_0_1_scope_lock.md` already cited as a canonical reference.

The `/Users/benjaminmarks/CLAUDE.md` (a separate project named "benjaminmarks") describes QuadFlow and is unrelated to Voss — ignored.

## Sources

### Primary (HIGH confidence)
- `/pydantic/pydantic` Context7 docs — `model_validate`, strict mode, `extra="forbid"`, ValidationError handling. `[CITED]`
- `voss/harness/session.py` (M1) — `_state_dir`, `SessionRecord`, `save`/`load`/`list_sessions`. `[VERIFIED]`
- `voss/harness/agent.py` (M1) — `run_turn`, `Plan`, `PLAN_SYSTEM`, tool dispatch loop. `[VERIFIED]`
- `voss/harness/cli.py` (M1) — `_run_repl` slash-command registry, `_git_status` helper. `[VERIFIED]`
- `voss/harness/permissions.py` (M1) — `PermissionGate`, `PermissionStore`, modes. `[VERIFIED]`
- `voss/harness/tools.py` (M1) — tool registry, `_shell_capture`. `[VERIFIED]`
- `voss/harness/sandbox.py` (M1) — `jail_path`, `shell_allowed`. `[VERIFIED]`
- `voss/harness/render.py` (M1) — Tty/Plain/Json renderer protocol. `[VERIFIED]`
- `voss_runtime/providers/litellm_provider.py:62` — `litellm.token_counter(model, text)`. `[VERIFIED]`
- `.planning/phases/M1-harness-happy-path/M1-03-PLAN.md` — M1 redaction test pattern. `[VERIFIED]`
- `.planning/phases/M2-project-cognition/M2-CONTEXT.md` — D-01..D-20 locked decisions. `[VERIFIED]`
- `.planning/REQUIREMENTS.md` — COG-01..08 phase scope. `[VERIFIED]`
- `.vscode/voss_v_0_1_scope_lock.md` §2 §M2 — durable vs cache split. `[VERIFIED]`

### Secondary (MEDIUM confidence)
- pydantic v2 `extra="forbid"` and `ValidationError.errors()` shape. `[CITED: github.com/pydantic/pydantic/blob/main/docs/errors/errors.md]`
- `git ls-files` semantics for honoring `.gitignore` (standard git behavior). `[CITED: git-scm.com/docs/git-ls-files]`

### Tertiary (LOW confidence)
- None. All claims either verified against the codebase, pydantic Context7 docs, or locked in CONTEXT.md.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all deps already in `pyproject.toml`; versions verified.
- Architecture: **HIGH** — every component maps to an existing M1 pattern; no novel structure.
- Pitfalls: **HIGH** — pitfalls 1, 3, 5, 7 are explicitly named in CONTEXT.md Claude's-discretion; pitfalls 2, 4, 6 are derived from D-04/D-09/D-18.
- Validation Architecture: **HIGH** — every COG-XX requirement mapped to ≥1 test, framework already in place.
- Security domain: **HIGH** — extends M1 D-16/D-17 redaction guarantee verbatim; no new attack surface.

**Research date:** 2026-05-11
**Valid until:** 2026-06-10 (30 days; M2 scope is stable, pydantic v2 stable, no fast-moving dependencies in play)
