<div align="center">

<img src="site/branding/voss-mark-ignite-2048.png" alt="Voss" width="96" />

# Voss

**A language for confidence-aware, budget-bounded LLM programs.**

[![CI](https://github.com/voss-lang/voss/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/voss-lang/voss/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/voss-lang/voss/branch/master/graph/badge.svg)](https://codecov.io/gh/voss-lang/voss)
[![npm version](https://img.shields.io/npm/v/@vosslang/cli.svg)](https://www.npmjs.com/package/@vosslang/cli)
[![npm downloads](https://img.shields.io/npm/dm/@vosslang/cli.svg)](https://www.npmjs.com/package/@vosslang/cli)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Node 18+](https://img.shields.io/badge/node-18+-brightgreen.svg)](https://nodejs.org/)

</div>

Voss makes probabilistic values, context windows, and per-call budgets first-class so that AI-augmented code is auditable and predictable instead of vibes-based.

Voss v0.1 ships as a Python harness and the `.voss` workflow-control language, a local `voss serve` API (REST + SSE, `docs/protocol.md`), a Go TUI, and client SDKs in `sdk/` and `crates/voss-sdk`. npm (M6) distributes the same Python harness with a vendored interpreter. A separate Voss ADE desktop application integrates through the local protocol; the original in-repo app is frozen under `archive/voss-ade/` (`docs/architecture/0004-voss-ade-repository-split.md`).

## What is .voss

.voss is an **AI workflow control** layer that compiles to readable Python. It is a complement to Python, not a replacement: write your data structures, business logic, and integrations in Python as usual, and reach for .voss when you need first-class control over LLM-shaped concerns.

First-class primitives:

- Probable values + confidence gates: `let intent: probable<string> = ask(...)` with `if intent @ p >= 0.80 { ... }`
- Context budgets: `ctx(budget: 4000 tokens) { include ... yield ask(...) }` and `within budget(tokens: N, latency: Ts) { ... } fallback { ... }`
- Semantic routing: `match userMessage { case similar("angry customer") => ... case _ => ... }`
- Agents, spawn, gather: `spawn Researcher(topic)` + `gather(researchers, timeout: 60s)`
- Memory primitives: `memory.episodic(capacity: N turns)`, `memory.semantic(source: "...")`, `memory.working(capacity: N)`
- Recovery + imports: `try { ... } catch e { ... }` and `use voss_runtime::tools::tool`

See the [`samples/`](samples/) directory for the three canonical programs, and [`docs/voss-vs-python.md`](docs/voss-vs-python.md) for side-by-side comparisons against the raw-Python equivalents.

## Install

### Recommended: npm

```bash
npm i -g @vosslang/cli
```

Brings the Voss CLI with a vendored Python 3.12 + the v0.1 voss wheel + all dependencies. Zero manual Python setup. Works on macOS (arm64, x64), Linux (x64, arm64), and Windows (x64). After install run `voss doctor` to verify provider credentials, the vendored Python, and config paths.

### Alternative: pip

If you already manage Python 3.11+ yourself, install from PyPI:

```bash
pip install voss
```

Semantic memory (`memory.semantic`, `match similar(...)`) is an optional extra — it pulls torch + sentence-transformers + chromadb:

```bash
pip install 'voss[search]'
```

### Container image

Voss also publishes a CLI container image to GitHub Container Registry:

```bash
docker pull ghcr.io/voss-lang/voss:latest
docker run --rm ghcr.io/voss-lang/voss:latest --help
```

Mount a repo into `/workspace` when running project-scoped commands:

```bash
docker run --rm -v "$PWD:/workspace" ghcr.io/voss-lang/voss:latest doctor
```

First run — verify the install and check provider auth, git, and config paths:

```bash
voss doctor
```

Explore the canonical programs in [`samples/`](samples/) and run a representative harness command:

```bash
voss check samples/classify.voss
voss compile samples/classify.voss
voss do "summarize this repo"
```

Core harness commands: `voss doctor`, `voss do`, `voss chat`, `voss edit`, `voss sessions`, `voss resume` (see the [CLI reference](https://docs.tryvoss.dev/reference/cli) for the full surface).

Optionally opt into the compiled harness with `VOSS_HARNESS=compiled` by populating the local harness cache after install. The default Python harness path works without this step.

```bash
voss compile voss/harness/agent/
```

### Development install

```bash
pip install -e ".[dev]"
```

## Go terminal client

Bare `voss` opens the Go client when its binary is installed. From a checkout:

```bash
(cd tui && go build -o voss-tui .)
voss
```

Editable Python installs and `npm link` automatically use this local build.
`VOSS_TUI_BIN` can select a different binary explicitly.

The npm platform packages include `voss-tui`. Use `VOSS_USE_TUI=0 voss` for
Textual; it also remains the fallback when the Go binary is missing. `voss ui`
launches Go explicitly. `/resume` opens a saved-session picker; `/resume <id-or-name>`
and `voss ui resume <id-or-name>` resume directly. Earlier conversation context
is restored on the server, and saved messages appear in the transcript. The picker
shows and searches each session's first prompt. `/clear` drops active conversation
memory while keeping the visible transcript. Saved history updates on the next turn.
Use `/memory` for a workspace summary and `/recall <query> [--top N]` to search it.
Use `/model` (or `/models`) to search models and `/auth` to choose Claude, Codex,
or API authentication. `/model gpt-6.1-sol` and `/auth claude` switch directly.
Subscription choices reuse your local Claude/Codex login; API choices require a
configured key. Successful switches update the footer and persist across launches
and saved-session resumes. `voss ui --auth codex` overrides auth for a launch.
The remaining slash commands are available through Textual.

## Local MCP servers and skills

Voss discovers MCP definitions from Claude's `~/.claude.json` and project
`.mcp.json`, plus Codex's `~/.codex/config.toml` and project `.codex/config.toml`.
`CODEX_HOME` is respected. Project entries override user entries; Codex wins
same-scope collisions, followed by Claude's project-local entries.
`~/.config/voss/mcp.yml` and project `.voss/mcp.yml` override imported servers
(the user directory follows `XDG_CONFIG_HOME`). Set `enabled: false` in a Voss
server entry to disable it. Stdio and Streamable HTTP are supported.

Skills come from user and project `.claude/skills`, `.codex/skills`, and
`.agents/skills` folders. Project skills override user skills with the same name;
Voss's user `skills` folder and project `.voss/skills` take precedence.
Skill instructions and references are read on demand through `skill_read`.

```bash
voss mcp list --configured   # show sources without connecting
voss mcp list                # connect and list advertised tools
voss skills
voss chat --allow-net
```

In Textual, use `/skill <name> <task>` or `$name <task>`. In either TUI, ask
to use a skill by name. MCP calls retain Voss's network and permission checks;
set `[tools] allow_net = true` in Voss's `config.toml` for network tools in Go.
Requests about open PRs, GitHub, MCP, or skills enter the tool-enabled run.

Discovery does not transfer remote MCP OAuth sessions or enable host-managed
plugins and app connectors. HTTP servers can use configured headers or token
environment variables. Legacy SSE endpoints require a Streamable HTTP endpoint.

## First run · `voss login`

Run `voss login` to configure credentials before opening the Go client.
Textual also opens the sign-in wizard automatically when credentials are
missing, and supports `/login` inside its REPL.

```text
╭ voss · sign in ──────────────────────────────────────────╮
│ reason: no credentials found                              │
│                                                           │
│   1  Claude Code OAuth      [ready]                       │
│   2  Codex / ChatGPT OAuth  [needs `codex` CLI]           │
│   3  Paste an API key       [Anthropic or OpenAI]         │
│   q  Quit                                                 │
╰───────────────────────────────────────────────────────────╯
choice [1/2/3/q]:
```

Three paths:

- **Claude Code OAuth** — spawns the `claude` CLI so you can run `/login` inside it,
  then polls `~/.claude/.credentials.json` for the new tokens.
- **Codex / ChatGPT OAuth** — runs `codex login`, then polls `~/.codex/auth.json`.
- **Paste an API key** — Anthropic or OpenAI. The key is stored in the OS
  keychain via [`keyring`](https://pypi.org/project/keyring/) (macOS Keychain,
  Windows Credential Locker, Linux Secret Service). Remove it later with
  `voss logout anthropic` or `voss logout openai`.

Resolution order under `--auth=auto`: voss-stored keychain creds → env vars
(`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) → Claude Code OAuth → Codex auth.
Keychain wins so a forgotten shell export does not silently shadow the key
you set in the wizard.

In non-interactive contexts (CI, piped stdin) the wizard is skipped and
voss exits 2 with the original credential-missing error — set the env vars
or pre-populate the keychain for scripted use.

## Quickstart

The runtime exposes `ProbableValue`, `ContextScope`, `BudgetScope`, `SemanticMatcher`, `VossAgent`, `gather`, `@tool`, and the three memory primitives. See:

- [`examples/raw_python/classify.py`](examples/raw_python/classify.py) — PRD §7.1, confidence-gated classification
- [`examples/raw_python/support.py`](examples/raw_python/support.py) — PRD §7.2, semantic routing + ContextScope fallback
- [`examples/raw_python/research.py`](examples/raw_python/research.py) — PRD §7.3, agent swarm with `gather` + `run_with_budget` fallback

```python
import asyncio
from voss_runtime import ContextScope, ProbableValue

async def classify(text: str) -> str:
    async with ContextScope(token_budget=1000) as ctx:
        await ctx.add(f"Classify: {text}")
        intent: ProbableValue = await ctx.ask(
            "Return only the intent label.", return_type=ProbableValue
        )
        return intent.value if intent @ 0.80 else "unknown"

print(asyncio.run(classify("I want to cancel my subscription")))
```

## Tests

Default (stub providers, hermetic, fast):

```bash
pytest -q -m "not live"
```

With coverage:

```bash
pytest -q -m "not live" --cov=voss_runtime --cov-report=term-missing
```

Live mode (real Anthropic / OpenAI / Ollama — requires API keys + Ollama service):

```bash
pytest -q -m live
```

Live mode runs nightly in CI; stub mode runs on every PR.

## Project Docs

- [Language documentation](https://docs.tryvoss.dev/language/overview) — language overview and constructs
- [docs/sdk.md](docs/sdk.md) — embedding Voss in Python apps: `voss_runtime` + `voss.harness` public API contract
- [docs/voss-vs-python.md](docs/voss-vs-python.md) — side-by-side .voss vs raw Python with LOC counts
