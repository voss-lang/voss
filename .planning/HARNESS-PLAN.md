# Voss Coding Harness — Plan

**Created:** 2026-05-08
**Updated:** 2026-05-10 — v0.1 scope lock rebaseline; harness-led MVP with `.voss` as control layer
**Status:** Active v0.1 planning reference
**One-liner:** A terminal-native coding harness for bounded, inspectable, resumable AI-assisted repo work, with `.voss` as the durable workflow control layer.

---

## 0. v0.1 Scope Lock

Source of truth: `.vscode/voss_v_0_1_scope_lock.md`.

Voss v0.1 should ship as an AI-native coding harness first and a programming language where it matters: defining, checking, and running AI-native development workflows. The immediate proof point is not a full Python fork or a general-purpose Python replacement. The proof point is:

> A developer can use Voss to safely plan, execute, inspect, and resume AI-assisted code work in a real repository, while the most important agent logic is expressible in Voss syntax.

The harness is the product surface. The language is the durable control plane.

### 0.1 M-prefixed roadmap

The v0.1 roadmap uses the scope-lock milestone names:

| Phase | Name | Purpose |
|---|---|---|
| M0 | Scope Lock | Align planning docs and naming around harness-led v0.1 |
| M1 | Harness Happy Path | `voss doctor`, `voss do`, `voss edit`, basic tools, permissions, session snapshot |
| M2 | Project Cognition | `.voss/` durable project brain and `.voss-cache/` rebuildable indexes/cache |
| M3 | Language Validation | `.voss` examples check/run as AI workflow control programs |
| M4 | Voss-authored Harness Loop | `voss/harness/agent/*.voss` dogfoods the language |
| M5 | Eval and Distribution Prep | Golden tasks, cost/success/confidence tracking, install polish |

### 0.2 Deferred work

Rust `crates/` is a **frozen spike** preserved in source control — not deleted, not active. v0.1 distribution is npm-wrapped Python (M6, pyright bundled-Python pattern). The Rust path resurrects only on a concrete dogfood signal: real startup-latency complaints or wheel-size friction. Until then, do not edit `crates/` or chase Python-API drift in it; leave it intact for future reactivation. MCP bridge, tree-sitter, VSCode marketplace, GitHub Linguist upstream, broad telemetry, public marketplace, team features, and web UI are also deferred from v0.1.

### 0.3 Naming rule

`voss run <file.voss>` executes `.voss` programs. `voss do "<task>"` executes natural-language agent tasks. Do not overload either command.

---

## 1. Why a Voss-First Harness

Every coding agent (Claude Code, Codex, Aider, Cursor, Pi CLI) reimplements the same five primitives: confidence checking on model output, context-window budgeting, prompt assembly, intent routing, and sub-agent orchestration. These are exactly the primitives Voss makes first-class.

Building the harness *in Voss* serves two ends:

1. **Dogfood.** The compiler's hardest user is an agent that calls itself thousands of times per session. If `ctx`, `within/fallback`, `gather`, `match similar`, and `ProbableValue` survive that load, they survive any production user.
2. **Differentiation.** Today's harnesses leak budget control into prompts ("respond in under 200 words"), leak confidence into regex, and leak routing into hardcoded if-chains. A Voss-native harness moves that load into the language. Boilerplate disappears, behavior becomes auditable.

This is *not* a Voss IDE. It is a CLI-first agent — a peer to `codex`, `claude`, `pi`, `aider` — that happens to be built on Voss and that biases its file-creation output toward `.voss`.

---

## 2. Product Surface

### 2.1 Binary

One binary, `voss`. `pyproject.toml` ships a single entry point:

```toml
[project.scripts]
voss = "voss.cli:main"
```

The CLI dispatches to compiler subcommands (PRD §6) or harness subcommands. Bare `voss` with no args launches the agent REPL — the most common entry path.

### 2.2 Top-level commands

Compiler verbs (PRD §6, unchanged):

```
voss compile <file.voss>           # .voss → .py
voss run <file.voss>               # compile + execute a Voss program
voss check <path>                  # lint without compiling
voss init <name>                   # scaffold a new Voss project
voss ast <file.voss>               # debug: print AST
```

Agent verbs (new):

```
voss                               # launch interactive agent REPL (default)
voss chat                          # explicit form of bare `voss`
voss do "<task>"                   # one-shot agent turn; prints final answer; exits
voss edit <path>                   # scoped edit session against a single file
voss resume [<session-id>]         # rehydrate prior session from episodic snapshot
voss sessions                      # list saved sessions with timestamps + first task
voss tools                         # list registered tools and their permission tier
voss config                        # open ~/.config/voss/config.toml in $EDITOR
voss doctor                        # diagnose env: provider keys, compiler, cache
voss --version
voss --help
```

**Disambiguation rule.** `voss run` is reserved for the compiler (executes a `.voss` file). The agent's one-shot is `voss do`. This keeps `voss run foo.voss` unambiguous and avoids the trap where a string task could collide with a path.

`voss do` is pipe-aware:

```
git diff | voss do "summarize changes for a PR description"
voss do "rename UserToken to AuthToken across the repo" --auto
```

### 2.3 Flags (global)

| Flag | Default | Meaning |
|---|---|---|
| `--model <id>` | from config | Override default model for this invocation. |
| `--budget <usd>` | unbounded | Hard `BudgetScope` ceiling for the session. |
| `--mode <plan\|edit\|auto>` | `edit` | Permission tier (see §6). |
| `--no-color` | off | Disable ANSI; auto-detected when stdout is not a TTY. |
| `--json` | off | Emit NDJSON events on stdout (machine consumers). |
| `--cwd <path>` | `.` | Project root for sandbox + memory. |
| `--seed <n>` | — | Deterministic provider responses where supported (testing). |
| `--quiet` / `-q` | off | Suppress tool traces; show only final answer. |
| `--verbose` / `-v` | off | Stream every tool argument and result. |

### 2.4 Slash commands (inside REPL)

```
/help              show this list
/model <id>        switch model mid-session
/budget <usd>      raise/lower remaining budget
/mode <plan|edit|auto>  change permission tier
/tools             list available tools + last-call latency
/clear             drop episodic memory; keep semantic
/save [name]       persist session snapshot
/resume <id|name>  load a prior session
/diff              show pending unapplied edits
/apply             apply pending edits
/discard           discard pending edits
/cost              breakdown by model + tool
/why               explain last decision (uses last ProbableValue rationale)
/exit              quit (also Ctrl-D)
```

`/why` is the killer feature — every model call returns `ProbableValue<T>` with a rationale string, so the harness can always explain *why* it picked an action and at what confidence.

---

## 3. CLI Aesthetic

Reference points: Codex CLI's minimal banner + inline tool boxes; Claude Code's permission prompts and status line; Pi CLI's color discipline (one accent, lots of dim). Goal is "sharp, monospace, no chrome we don't need."

### 3.1 Launch banner

```
  ╭──────────────────────────────────────────────────────╮
  │                                                      │
  │   voss · agent                                       │
  │   sonnet-4.7 · ~/Projects/Voss · clean               │
  │                                                      │
  │   Type a task, or /help.                             │
  │                                                      │
  ╰──────────────────────────────────────────────────────╯

▌
```

- Box drawn with rounded corners (`╭╮╰╯`), single line weight, no shadows.
- Three lines of metadata only: model, cwd shortened with `~`, git status (`clean` / `+3 -1` / `detached`).
- Cursor glyph is `▌` (block) on a dim line; switches to `❯` while a turn is in flight.
- Banner suppressed in non-TTY mode and behind `--quiet`.

### 3.2 Turn rendering

User input echoes verbatim above; agent text streams below in default fg. Tool calls render as collapsed one-liners that expand on `--verbose` or `/why`:

```
▌ rename UserToken to AuthToken across the repo

  Plan
  • find every reference to `UserToken`
  • emit a single diff covering symbol + imports + tests
  • run voss check + pytest before applying

  ⏵ ast.search(symbol="UserToken")          14 hits · 28ms
  ⏵ fs.read("voss_runtime/agent.py")        4.2KB
  ⏵ fs.edit("voss_runtime/agent.py")        +3 −3
  ⏵ fs.edit("tests/test_agent.py")          +5 −5
  ⏵ voss.check(".")                         ✓ 0 warnings
  ⏵ shell.run("pytest -q -m 'not live'")    ✓ 142 passed · 1.8s

  Renamed 14 references across 6 files. All checks pass.
  Confidence 0.94. /diff to review, /apply to commit.
```

- Tool glyph `⏵` (right-pointing triangle), dim color.
- Status field right-aligned, dim.
- `✓` green, `✗` red, `…` yellow for in-flight. One accent color for success per session.
- Diffs render with `+` green / `-` red and 1-line context, never full files unless asked.

### 3.3 Permission prompt

Shown inline, blocks input. Borrows Claude Code's pattern:

```
  ⚠  shell.run("rm -rf .voss-cache")
     This will delete cached compile artifacts (12 files, 4.1MB).

     [a] allow once    [A] allow always    [d] deny    [e] edit command
```

Single keystroke. `e` opens the command in `$EDITOR` for tweak before approve.

### 3.4 Status line

Pinned to bottom row when stdin is a TTY, redrawn each token:

```
─ sonnet-4.7 · 12.4k / 200k tok · $0.038 · ctx 6% · ⏱ 4.2s ──────
```

- Em-dash padding, dim throughout.
- `ctx %` = current `ContextScope` fill; when it crosses 80%, accent flips to yellow.
- Cost tracks the active `BudgetScope`; flips red and audible-bell at 90%.

### 3.5 Diff preview

`/diff` (or auto in `plan` mode) renders pending edits in a compact unified format:

```
  voss_runtime/agent.py
  ────────────────────────────────────────────────────
   class VossAgent(ABC):
  -    system_prompt: str
  +    system_prompt: str = ""
       tools: list = []

  3 files changed, +12 −7
  /apply  /discard  /diff <path>
```

### 3.6 Color & type

- Palette: fg default, dim (60% gray), one accent (cyan), success green, warn yellow, error red. No gradients, no emoji except the four glyphs above (`▌ ❯ ⏵ ⚠`).
- Font assumption: monospace, 2-cell box-drawing supported. Fallback to ASCII when `LANG` lacks UTF-8 or `--no-color` is set.
- Streaming respects soft-wrap at terminal width; never hard-wraps mid-word.

### 3.7 Non-TTY mode

When stdout is piped or `--json` is set:

- No banner, no status line, no ANSI.
- `--json` emits NDJSON events: `{"type":"text","delta":"..."}`, `{"type":"tool_call",...}`, `{"type":"tool_result",...}`, `{"type":"final","answer":"..."}`. One event per line. Stable schema, versioned via `{"v":1}` envelope.
- Default piped mode (no `--json`) emits plain text answer only; tool traces redirected to stderr.

---

## 4. Architecture

```
┌──────────────────────────────────────────────────────────┐
│  voss CLI (Python entry, Click)                          │
│   • dispatcher: compiler verbs vs agent verbs            │
│   • TTY renderer (rich) ─┐                               │
│   • NDJSON renderer ─────┼─ chosen by isatty / --json   │
│   • permission gate      ┘                               │
└──────────────────────────────────────────────────────────┘
                       │ invokes
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Agent loop  (Voss source → compiles to Python)          │
│   harness/voss/loop.voss        main turn                │
│   harness/voss/router.voss      match similar(...)       │
│   harness/voss/planner.voss     ProbableValue<Plan>      │
│   harness/voss/executor.voss    gather(spawn ToolAgent)  │
│   harness/voss/reviewer.voss    confidence-gated apply   │
└──────────────────────────────────────────────────────────┘
                       │ uses
                       ▼
┌──────────────────────────────────────────────────────────┐
│  voss_runtime  (Python runtime primitives)               │
│   ContextScope · BudgetScope · ProbableValue ·           │
│   SemanticMatcher · VossAgent · gather · memory.*        │
└──────────────────────────────────────────────────────────┘
                       │ exposes tools via
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Tool adapters (Python, decorated @tool)                 │
│   fs.{read,write,edit,glob,grep}                         │
│   shell.run (allowlist + cwd jail)                       │
│   git.{status,diff,log,branch,commit}                    │
│   ast.{search,outline}        (voss ast --json first;    │
│                                tree-sitter later)        │
│   compiler.{compile,check,run,ast} (self-hosting hook —  │
│       calls into voss.cli compiler verbs in-process)     │
│   net.{fetch}                 (off by default)           │
└──────────────────────────────────────────────────────────┘
                       │ talks to
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Providers  (voss_runtime/providers/*)                   │
│   anthropic · openai · ollama (local fallback)           │
└──────────────────────────────────────────────────────────┘
```

### 4.1 Repo layout

The harness lives under the existing `voss/` compiler package so a single `voss.cli:main` can route both worlds:

```
voss/
├── cli.py                # Click root: dispatches compile/run/check/init/ast
│                         # AND chat/do/edit/resume/sessions/tools/doctor.
│                         # Bare invocation → agent REPL.
├── grammar.lark          # (existing) compiler
├── parser.py             # (existing)
├── analyzer.py           # (existing)
├── codegen.py            # (existing)
└── harness/
    ├── __init__.py
    ├── repl.py           # interactive loop (`voss`, `voss chat`)
    ├── one_shot.py       # `voss do`, pipe handling
    ├── render/
    │   ├── tty.py        # rich-based renderer
    │   ├── ndjson.py     # machine output
    │   └── theme.py      # palette + glyphs
    ├── permissions.py    # allowlist, prompts, persistence
    ├── sandbox.py        # cwd jail, env scrub, shell allowlist
    ├── session.py        # save/load episodic snapshots
    ├── adapters/
    │   ├── fs.py
    │   ├── shell.py
    │   ├── git.py
    │   ├── ast.py
    │   ├── compiler.py   # in-process bridge to voss.cli compile/check/run
    │   └── net.py
    ├── agent/            # agent loop authored in Voss
    │   ├── loop.voss
    │   ├── router.voss
    │   ├── planner.voss
    │   ├── executor.voss
    │   ├── reviewer.voss
    │   └── prompts/*.voss
    └── tests/
        ├── test_cli.py
        ├── test_permissions.py
        ├── test_render.py
        └── golden/       # eval tasks (see §9)
```

The agent's own `.voss` source lives under `voss/harness/agent/`. The compiler compiles its own harness — strongest possible dogfood loop.

### 4.2 Loop sketch (Voss)

```voss
use voss::memory
use harness::tools::{fs, shell, git, voss, ast}

let history: memory.episodic(capacity: 40 turns)
let repo:    memory.semantic(source: ".", model: "all-MiniLM-L6-v2")

@tool fn read(path: string) -> string  { fs.read(path) }
@tool fn edit(path: string, diff: string) -> bool { fs.edit(path, diff) }
@tool fn check() -> string             { voss.check(".") }
@tool fn run(cmd: string) -> string    { shell.run(cmd) }

agent ToolAgent(step: Step) -> StepResult {
    system: "Execute one planned step. Return result + confidence."
    tools:  [read, edit, check, run]
    retries: 2
}

fn turn(userTask: string) -> Answer {
    history.add(userTask, role: "user")
    let chunks = repo.retrieve(userTask, top_k: 8)

    ctx(budget: 60000 tokens) {
        include history.last(20)
        include chunks

        let plan: probable<Plan> = ask(
            "Plan tool calls. Return Plan with rationale.",
            return_type: Plan
        )

        if plan @ p >= 0.75 {
            let handles = plan.value.steps.map(s => spawn ToolAgent(s))
            let results = gather(handles, timeout: 120s)

            within budget(cost: $0.05) {
                yield review(results, model: "sonnet-4.7")
            } fallback {
                yield review(results, model: "haiku-4.5")
            }
        } else {
            yield Answer.clarify(plan.value.openQuestion)
        }
    }
}
```

Hard-wins this expresses that a Python harness has to re-derive every session: budget tier-down, parallel sub-agent fan-out with a typed gather, confidence-gated path selection, and an explicit context window with included memory.

### 4.3 Sandbox model

- Tools run in the user's process; no docker. Isolation comes from a strict allowlist + path jail, matching Claude Code's posture.
- `shell.run` rejects commands not on the allowlist (configurable per project). Default allow: `ls, cat, head, tail, grep, rg, find, git, pytest, python, voss, npm, node`. Default deny: anything with `rm -rf`, `sudo`, `curl http://`, `nc`, `>` outside cwd.
- `fs.*` operations canonicalize paths via `realpath` and reject anything not inside `cwd`.
- `net.fetch` is **off by default**. Enable per-session via `/mode auto` or per-invocation via `--allow-net`.

### 4.4 Sessions & memory

- Episodic transcript persists to `~/.local/state/voss/sessions/<uuid>.json` on `/save` or `/exit`.
- Semantic repo index lives in `<cwd>/.voss-cache/repo.idx` (chunked source + symbols, rebuilt on git head change).
- `voss resume <id>` reloads episodic; semantic always rebuilds if stale.
- `voss sessions` reads the dir, prints `id · started · model · first task line`.

---

## 5. Permission Tiers

Three modes, chosen at launch (`--mode`) and switchable mid-session (`/mode`):

| Mode | Behavior |
|---|---|
| `plan` | Read-only tools auto-approved. Every write/shell prompts. No edits applied without explicit `/apply`. |
| `edit` *(default)* | Reads + scoped writes inside cwd auto-approved. Shell + net always prompt. |
| `auto` | All allowlisted tools auto-approved. Destructive patterns (`rm -rf`, force push, `git reset --hard`) still prompt. |

Mode persists per `cwd` in `~/.config/voss/permissions.json` so common project-local approvals stick across sessions.

---

## 6. Configuration

`~/.config/voss/harness.toml`:

```toml
[default]
model = "claude-sonnet-4-7"
mode  = "edit"
theme = "dark"   # dark | light | mono

[budgets]
session_usd = 5.00
turn_tokens = 60000

[providers.anthropic]
api_key_env = "ANTHROPIC_API_KEY"

[providers.openai]
api_key_env = "OPENAI_API_KEY"

[providers.ollama]
host = "http://localhost:11434"

[tools]
allow_net = false
shell_allowlist = ["ls","cat","head","tail","grep","rg","find","git","pytest","python","voss","npm","node"]
```

Project override at `.voss-cache/harness.toml` (gitignored by default; promotable to checked-in `voss.toml` for team-shared settings).

---

## 7. Build Phases

Each phase ends with a runnable demo. Each phase is independently usable.

### M1 — Harness Happy Path

- `voss do "<task>"` works against `voss_runtime` directly (Python loop, no `.voss` source yet — compiler not ready).
- Bare `voss` enters REPL.
- Adapters: `fs`, `shell` (allowlist), `git`, `compiler.{check,compile,run}` (in-process call into existing compiler verbs).
- TTY renderer with banner, streaming, tool boxes, status line.
- Permission prompts (one-shot allow / always / deny).
- Episodic memory in-process; no persistence yet.
- `--json` NDJSON output path.
- Smoke test: "summarize this PRD section."

### M2 — Project Cognition

- Persistent sessions (`/save`, `voss resume`, `voss sessions`).
- Semantic repo index (chromadb, rebuilt on git head change).
- Slash commands (`/model`, `/budget`, `/mode`, `/diff`, `/apply`, `/discard`, `/cost`, `/why`).
- Diff preview + apply flow.
- Cross-platform: macOS, Linux. Windows deferred.

### M3 — Language Validation

- `voss check samples/classify.voss`, `samples/support.voss`, and `samples/research.voss` pass.
- At least one representative sample runs through `voss run`.
- Generated Python is readable and imports `voss_runtime`.
- Docs and samples frame `.voss` as AI workflow control, not Python replacement.

### M4 — Voss-authored Harness Loop

- Rewrite Python loop → `loop.voss` + `router.voss` + `planner.voss` + `executor.voss` + `reviewer.voss` under `voss/harness/agent/`.
- CI gate: `voss check voss/harness/agent/` runs on every PR. If the compiler regresses on its own harness, that's a P0.
- Boot path: agent CLI verbs lazily compile `voss/harness/agent/loop.voss`, cached under `.voss-cache/harness/`.

### M5 — Eval and Distribution Prep

- Golden tasks (see §9) run nightly; track success rate, mean cost, mean confidence on success vs. failure.
- Package install polish verifies compiler and harness commands ship together.
- Local eval outputs track success rate, mean cost, and confidence correlation.
- Rust/Homebrew/MCP distribution work stays deferred unless Python harness usage proves the need.

---

## 8. Tooling Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language for harness shell | Python (Click + Rich) | Same toolchain as compiler; one repo, one venv. |
| Renderer | `rich` for TTY, plain stdout for pipe/`--json` | Battle-tested; good streaming primitives. |
| Provider abstraction | Use `voss_runtime/providers/*` as-is | One source of truth for model calls. |
| Concurrency | `asyncio` (matches `voss_runtime/agent.py`) | No new runtime. |
| Sandbox | cwd jail + cmd allowlist | No docker dep; matches Claude Code posture. |
| Memory backend | chromadb local for semantic; JSON for episodic | Already a runtime dep; zero-config. |
| Diff format | unified diff via `difflib`; apply with `patch` | Standard, reviewable, undo-able with `git`. |
| Edit primitive | `fs.edit(path, anchor, replacement)` | Anchor-based, no line numbers in prompt; matches what models reliably emit. |
| Auth | env vars first | Lowest friction; secrets stay in shell. |
| Update channel | `pip install -U` first; auto-update deferred | Avoid surprise mutations. |

---

## 9. Eval Suite

Five golden tasks, run headless in CI, scored by exit code + diff comparison against committed reference outputs:

1. **classify-port** — given a Python implementation of PRD §7.1, produce a `.voss` equivalent. Pass if `voss compile && python out.py` matches reference output.
2. **rename-symbol** — rename `ProbableValue` → `Probable` across `voss_runtime/`. Pass if pytest still green and no orphan imports.
3. **add-test** — given a public function with no test, write one. Pass if it runs, asserts, and fails on a planted bug.
4. **fix-budget-warning** — codebase has a `ctx` block that overflows its declared budget; analyzer warns. Pass if warning gone and behavior preserved.
5. **summarize-diff** — pipe `git diff main..HEAD` in; produce a PR description. Pass if rouge-L > 0.6 against reference.

Track three numbers per nightly run: pass rate, mean cost-to-pass, mean reported confidence on passes vs. fails. Fail-with-high-confidence is the regression signal that matters most.

---

## 10. Risks & Open Questions

### Risks

- **Compiler debt blocks M4.** Mitigation: M1+M2 ship on raw `voss_runtime`. Migration to `.voss` is contained to one phase.
- **Calibrated confidence is hard.** Anthropic doesn't expose logprobs. Plan: model-self-reported confidence wrapped in `ProbableValue`, validated against eval suite. If correlation between reported confidence and success rate < 0.5, fall back to ensemble agreement.
- **Embedding boot cost.** sentence-transformers ~80MB and slow first call. Lazy-load in a background thread on REPL start; first `match similar(...)` may block for ~1s on cold cache. Cache to `~/.cache/voss/embeddings/`.
- **Tree-sitter grammar is deferred.** `ast.search` falls back to `voss ast --json` until then.
- **Windows.** Deferred. Path canonicalization, ANSI, and shell allowlist all need rework.

### Open questions (flag, do not silently decide)

1. Should the agent require a Voss project (presence of `voss.toml`), or work in any directory? Default: any directory. Voss-specific tools no-op gracefully outside a project.
2. Should we ship a built-in `web.search` tool? Pro: agents need facts. Con: every harness ships a different one; users have preferences. Default: off, document MCP integration as the path.
3. How should multi-turn `voss edit <file>` differ from REPL? Proposal: same loop, but the file is auto-included in every `ctx` block and writes outside the file are denied unless promoted.
4. Telemetry consent UX. Default off, but where does the prompt live? Proposal: first run only, single y/N, stored in config.

---

## 11. Success Criteria

The harness is shipping when:

- A new user runs `pip install voss && voss` and reaches a working agent in under 60 seconds (provider key already in env).
- The agent loop is authored in `.voss`, compiled by the project's own compiler, and `voss check` is clean.
- All five golden eval tasks pass at ≥ 80% success rate with mean cost < $0.05/task.
- A non-trivial Voss program (the support bot from PRD §7.2 plus episodic memory plus an escalation agent) can be authored end-to-end through `voss` in a single session, in under 60 lines of Voss, with no manual edits afterward.
- The CLI passes the "looks like Codex/Claude/Pi" smell test on a fresh terminal: clean banner, monochrome-friendly, single accent, no emoji clutter, status line that doesn't lie about cost.

---

## 12. Out of Scope (v0.1 Harness)

- Web UI / TUI panes / split views.
- IDE integration (VSCode, JetBrains). MCP bridge is deferred.
- Multi-machine / distributed agents. `gather` stays local.
- Fine-tuning, training data collection, RLHF loops.
- Account system, cloud sync, team-shared sessions.
- Voice input/output.
- Anything that requires running a daemon.

---

## 13. Dependencies (delta over compiler)

```toml
[project.optional-dependencies]
harness = [
  "click>=8.1.0",          # already in compiler deps
  "rich>=13.0.0",          # streaming, boxes, status line
  "prompt_toolkit>=3.0",   # REPL line editing, history
  "watchdog>=4.0",         # repo index invalidation on git head change
  "platformdirs>=4.0",     # cross-platform config/cache paths
]
```

Provider SDKs, sentence-transformers, and chromadb already come from the compiler's `voss_runtime` deps.

---

## 14. Build Order Summary

1. **M0** — scope lock and planning realignment.
2. **M1** — harness happy path; `voss do`, `voss edit`, and bare-`voss` REPL.
3. **M2** — project cognition; `.voss/` durable state and `.voss-cache/` rebuildable state.
4. **M3** — language validation; representative `.voss` examples check and run as workflow programs.
5. **M4** — port harness loop to `.voss`; CI gate locks dogfooding.
6. **M5** — eval suite and packaging polish.

The harness becomes the compiler's hardest user. Every regression in the language shows up in `voss` first.
