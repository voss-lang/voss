# Rust Port Plan — `voss-cli` (Harness Shell)

**Created:** 2026-05-09
**Status:** Proposal — execute after v1.1 H1–H5 close
**Codename:** R1–R9
**Scope:** Port the Python harness shell (`voss/harness/`) to a Rust binary. **Do not** port the compiler or `voss_runtime` — they stay Python. The Rust binary subprocess-shells to Python for compiler verbs.

---

## 1. Why port

| Problem today | After Rust port |
|---|---|
| Cold start ~700ms (pydantic + rich + click + httpx + lark imports) | ~30ms — single static binary |
| Distribution = `pip install voss` + Python 3.11+ + arch-matched wheels | `brew install voss/tap/voss` or `curl ...` — single binary, no runtime |
| macOS Keychain via `subprocess security` (fragile, fork-per-call) | `security-framework` crate — direct API |
| Concurrent sub-agents bound by GIL on CPU-bound prompt work | tokio multiplex, no GIL |
| 80MB+ PyInstaller bundle for distribution | ~8–12MB stripped Rust binary |
| Phase 5 packaging tests fragile across multi-Python macOS | irrelevant — one binary |

Reference set: Codex CLI (Rust), Pi CLI (Rust), Claude Code (Bun-compiled Node). Voss should match.

## 2. What ports vs. what stays

```
┌──────────────────────────── stays Python ─┐
│  voss/                                     │
│  ├── parser.py        (Lark grammar)       │
│  ├── analyzer.py                            │
│  ├── codegen.py                             │
│  ├── ast_nodes.py                           │
│  └── cli.py           (compiler-only shell) │
│  voss_runtime/        (entire pkg)          │
│  ├── probable.py                            │
│  ├── context.py                             │
│  ├── budget.py                              │
│  ├── semantic.py                            │
│  ├── memory/*.py                            │
│  ├── providers/*.py                         │
│  └── tools.py                               │
└────────────────────────────────────────────┘

┌──────────────────────────── ports to Rust ┐
│  voss/harness/                             │
│  ├── cli.py        →  src/main.rs +       │
│  │                     src/cli/*.rs        │
│  ├── agent.py      →  src/agent/loop.rs    │
│  ├── auth.py       →  src/auth/{kc,file}.rs│
│  ├── providers.py  →  src/providers/{...}  │
│  ├── tools.py      →  src/tools/*.rs       │
│  ├── sandbox.py    →  src/sandbox.rs       │
│  ├── permissions.py→  src/permissions.rs   │
│  ├── render.py     →  src/render/*.rs      │
│  ├── session.py    →  src/session.rs       │
│  └── tests/        →  tests/{integration}/ │
└────────────────────────────────────────────┘
```

Hard rule: Rust binary never imports or links libpython. Any Python interaction is `std::process::Command`.

## 3. Repo layout

Cargo workspace at repo root:

```
Voss/                           (existing)
├── voss/                       (Python — unchanged)
├── voss_runtime/               (Python — unchanged)
├── pyproject.toml              (unchanged)
├── Cargo.toml                  (workspace)
├── crates/
│   ├── voss-cli/               (binary crate — entry point)
│   │   ├── Cargo.toml
│   │   ├── src/main.rs
│   │   └── src/...
│   ├── voss-agent/             (lib — agent loop, planner, tool dispatch)
│   ├── voss-providers/         (lib — Anthropic OAuth, OpenAI OAuth, API key)
│   ├── voss-auth/              (lib — keychain + file cred discovery + refresh)
│   ├── voss-tools/             (lib — fs, shell, git, voss bridge)
│   ├── voss-render/             (lib — TTY + NDJSON renderers)
│   └── voss-bridge/            (lib — Python compiler subprocess client)
└── .planning/RUST-PORT-PLAN.md
```

Splitting into crates buys: parallel compilation, clear ownership of each subsystem, ability to publish individual crates if useful, and forces a clean public API per layer.

## 4. Dependency choices

### Runtime
| Crate | Version | Purpose |
|---|---|---|
| `tokio` | 1.x, full | async runtime, multiplexed IO |
| `clap` | 4.x, derive | CLI parsing — replaces click |
| `reqwest` | 0.12, default-tls=false, rustls-tls | HTTP client (Anthropic + OpenAI providers) |
| `serde`, `serde_json` | latest | JSON for plans, NDJSON, sessions |
| `schemars` | 0.8 | derive JSON Schema from `Plan` struct (analog of pydantic.model_json_schema) |
| `dirs` | 5 | XDG paths for config/state |
| `directories` | 5 | platform-specific dirs |
| `time`, `chrono` | latest | timestamps for sessions |
| `uuid` | 1 | session ids |
| `regex` | latest | grep tool |
| `walkdir` | 2 | glob tool |
| `globset` | 0.4 | glob matching |
| `crossterm` | 0.28 | TTY raw mode, colors, bell |
| `anstyle` + `anstyle-query` | latest | ANSI detection (no-color, NO_COLOR honor) |
| `ratatui` | 0.28 | OPTIONAL — drop in if status line / live diff needs more than crossterm |
| `is-terminal` | 0.4 | TTY detection |
| `thiserror` | 1 | error enums |
| `anyhow` | 1 | application errors |
| `tracing`, `tracing-subscriber` | latest | structured logging — emit on stderr only |

### Platform
| Crate | Purpose |
|---|---|
| `security-framework` (macOS only) | direct Keychain API — replace `subprocess security` |
| `secret-service` (Linux, optional) | dbus secret service for `~/.claude/.credentials.json` fallback |
| `windows` (Windows, future) | DPAPI / credential vault — out of scope v1 |

### Testing
| Crate | Purpose |
|---|---|
| `assert_cmd` | spawn the binary in tests |
| `predicates` | output assertions |
| `tempfile` | isolated cwd / state dirs |
| `wiremock` | mock the Anthropic / OpenAI HTTP servers |
| `insta` | snapshot tests for renderer output |

### Build
| Crate | Purpose |
|---|---|
| `cargo-dist` | release pipeline + signed binaries + brew formula |

## 5. The Python bridge

`voss-bridge` crate is the only place that talks to Python. Purpose: invoke compiler verbs and parse JSON output.

Surface:

```rust
pub struct VossPython {
    python: PathBuf,        // resolved Python interpreter
}

impl VossPython {
    pub fn discover() -> Result<Self> { ... }   // PATH lookup, .venv awareness
    pub async fn check(&self, path: &Path) -> Result<CheckReport> { ... }
    pub async fn ast(&self, path: &Path) -> Result<serde_json::Value> { ... }
    pub async fn compile(&self, path: &Path, out: &Path) -> Result<CompileReport> { ... }
    pub async fn run(&self, path: &Path) -> Result<ProcessOutput> { ... }
}
```

Wire contract — `voss` Python CLI must support `--json` on all read-only verbs:

```
$ python -m voss check foo.voss --json
{"v":1,"diagnostics":[{"severity":"warning","file":"...","line":12,"message":"..."}]}

$ python -m voss ast foo.voss --json --compact
{"v":1,"program":{"kind":"Program","body":[...]}}

$ python -m voss compile foo.voss --output bar.py --json
{"v":1,"output":"bar.py","ok":true,"warnings":[...]}
```

`--json` already partly exists for `ast`. R1 must add `--json` to `check` and `compile` if not present. **This is the only Python change required by the port** — and it's a strict superset, so it lands first as a non-breaking patch.

## 6. Rust API surface — module by module

### 6.1 `voss-cli` (binary)

```rust
// src/main.rs
#[tokio::main]
async fn main() -> ExitCode { voss_cli::run(std::env::args()).await }

// src/lib.rs — public for integration tests
pub async fn run(argv: impl IntoIterator<Item = OsString>) -> ExitCode { ... }
```

`clap` derive defines all subcommands:

```rust
#[derive(Parser)]
#[command(name = "voss", version, about = "voss — compiler and agent")]
struct Cli {
    #[command(subcommand)]
    cmd: Option<Cmd>,        // None ⇒ launch chat
    #[arg(long, global = true)] cwd: Option<PathBuf>,
    #[arg(long, global = true)] model: Option<String>,
    #[arg(long, global = true, value_enum, default_value_t = AuthPref::Auto)] auth: AuthPref,
    #[arg(long, global = true)] json: bool,
    #[arg(long, global = true, value_enum, default_value_t = Mode::Edit)] mode: Mode,
}

#[derive(Subcommand)]
enum Cmd {
    // Agent verbs (Rust-implemented)
    Do { task: Vec<String>, #[arg(long)] yes: bool },
    Chat,
    Resume { session_id_or_name: String },
    Sessions,
    Tools,
    Doctor,
    Config,

    // Compiler verbs (proxied to Python)
    Compile { source: PathBuf, #[arg(short, long)] output: Option<PathBuf>, #[arg(long)] verbose: bool },
    Run     { source: PathBuf, #[arg(long)] verbose: bool },
    Check   { source: PathBuf },
    Init    { target: PathBuf, #[arg(long)] force: bool },
    Ast     { source: PathBuf, #[arg(long)] compact: bool },
}
```

### 6.2 `voss-auth`

```rust
pub struct AnthropicOauth { pub access_token: String, pub refresh_token: String, pub expires_at: SystemTime, pub subscription: String }
pub struct CodexCreds     { pub api_key: Option<String>, pub access_token: Option<String>, pub refresh_token: Option<String>, pub account_id: Option<String>, pub auth_mode: String }

pub fn load_anthropic_oauth() -> Option<AnthropicOauth>;   // keychain on macOS, file fallback
pub fn load_codex() -> Option<CodexCreds>;
pub async fn refresh_anthropic(creds: &mut AnthropicOauth) -> Result<()>;
pub async fn refresh_codex(creds: &mut CodexCreds) -> Result<()>;

pub enum Resolution { EnvAnthropic(String), EnvOpenAI(String), ClaudeOAuth(AnthropicOauth), Codex(CodexCreds), CodexOAuth(CodexCreds), None(String) }
pub fn resolve(pref: AuthPref) -> Resolution;
```

macOS Keychain access:
```rust
use security_framework::passwords::get_generic_password;
let blob = get_generic_password("Claude Code-credentials", &whoami::username())?;
```
No subprocess. ~10x faster than `security` invocation.

### 6.3 `voss-providers`

```rust
#[async_trait]
pub trait ModelProvider: Send + Sync {
    async fn complete(&mut self, req: CompleteRequest) -> Result<ProviderResponse>;
    fn count_tokens(&self, text: &str, model: &str) -> usize { text.len() / 4 }
}

pub struct AnthropicOauthProvider { creds: AnthropicOauth, client: reqwest::Client, base: String }
pub struct OpenAIOauthProvider    { creds: CodexCreds,     client: reqwest::Client, base: String, session_id: Uuid }
pub struct LiteLLMShim            { ... }   // wraps a Python subprocess if user picks --auth=api with a non-Anthropic/OpenAI provider; otherwise direct HTTP
```

Anthropic provider:
- Auto-prepends `"You are Claude Code, Anthropic's official CLI for Claude."` to system blocks (already proven in Python).
- `anthropic-beta: oauth-2025-04-20` header.
- Translates `response_format: schema` to forced tool call (`submit_response`).
- `tokio::sync::Mutex<AnthropicOauth>` to allow refresh-on-401.

OpenAI provider:
- ChatGPT mode → `chatgpt.com/backend-api/codex/responses` with full Codex CLI wire format (per `.planning/CODEX-OAUTH-PLAN.md`).
- API-key mode → `api.openai.com/v1/responses`.
- JSON schema `text.format` for structured output.

Both providers expose snapshot tests against `wiremock` capturing the exact request bytes.

### 6.4 `voss-tools`

Each tool is a struct implementing:
```rust
#[async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    fn schema(&self) -> serde_json::Value;     // JSON Schema for the model
    async fn invoke(&self, args: serde_json::Value) -> Result<String>;
}

pub fn default_toolset(cwd: &Path) -> Vec<Arc<dyn Tool>> { ... }
```

Concrete tools — port one-for-one from Python:
- `FsRead`, `FsGlob`, `FsGrep`, `FsWrite`, `FsEdit`
- `ShellRun` (allowlist + cwd jail; uses `tokio::process::Command`)
- `GitStatus`, `GitDiff`
- `VossCheck`, `VossCompile`, `VossAst` (delegate to `voss-bridge`)

`schema()` produced via `schemars::JsonSchema` derive on the args struct. No more hand-rolled JSON schemas.

### 6.5 `voss-agent`

Mirrors `agent.py:run_turn` 1:1:

```rust
pub async fn run_turn(
    task: &str,
    tools: &[Arc<dyn Tool>],
    cwd: &Path,
    renderer: &mut dyn Renderer,
    provider: &mut dyn ModelProvider,
    history: &mut EpisodicMemory,
    permissions: &mut PermissionGate,
    cfg: TurnConfig,
) -> Result<TurnResult> { ... }
```

`Plan` is a Rust struct deriving `Deserialize, JsonSchema`. The schema is what we send to providers; deserialization parses what comes back.

```rust
#[derive(Serialize, Deserialize, JsonSchema, Debug)]
pub struct Plan {
    pub rationale: String,
    pub steps: Vec<ToolCall>,
    pub confidence: f32,
    pub open_question: Option<String>,
    pub final_when_done: String,
}
```

Confidence gate stays as the `>=` predicate. `gather` for parallel sub-agents lands when we tackle H3 (Voss-loop port) — until then, sequential `for step in plan.steps`.

### 6.6 `voss-render`

Trait + three implementations:
```rust
pub trait Renderer: Send {
    fn banner(&mut self, model: &str, cwd: &Path, git: &str);
    fn show_user(&mut self, task: &str);
    fn show_thinking(&mut self, label: &str);
    fn show_plan(&mut self, plan: &Plan, cost_usd: f64);
    fn show_tool_call(&mut self, name: &str, args: &serde_json::Value, summary: &str, state: ToolState);
    fn show_clarify(&mut self, q: &str, conf: f32);
    fn show_final(&mut self, text: &str, conf: f32, cost_usd: f64);
    fn status(&mut self, model: &str, tokens: usize, cost: f64, ctx_pct: f32);
}

pub struct TtyRenderer    { ... }   // crossterm
pub struct PlainRenderer  { ... }   // raw stdout/stderr
pub struct NdjsonRenderer { ... }   // one event per line, versioned envelope
```

Glyphs unchanged: `▌ ❯ ⏵ ⚠`. Single accent color (cyan). No emoji.

### 6.7 `voss-bridge` (Python interop)

```rust
pub struct PyBridge { python: PathBuf }

impl PyBridge {
    pub async fn check(&self, path: &Path) -> Result<CheckReport> { ... }
    pub async fn ast(&self, path: &Path, compact: bool) -> Result<serde_json::Value> { ... }
    pub async fn compile(&self, src: &Path, out: Option<&Path>) -> Result<CompileReport> { ... }
    pub async fn run(&self, src: &Path) -> Result<ProcessOutput> { ... }
}
```

Discovery order:
1. `$VOSS_PYTHON` env var.
2. `.venv/bin/python` relative to cwd.
3. `python3` on PATH (sanity-check by running `python3 -c "import voss"` — abort if missing).
4. Fallback: error with actionable message ("install voss-py: pipx install voss-py").

Spawns are cached for the duration of a session: keep a single `tokio::process::Child` running `python -m voss.bridge_server` (a long-lived JSON-RPC over stdio process), avoiding cold-start overhead per call. Only the *first* compile pays the Python startup cost; subsequent calls are cheap.

This requires a small new Python module: `voss/bridge_server.py`. ~80 LOC. Read-loop on stdin, dispatch to existing `voss.cli` functions, write JSON responses on stdout. One of the few new Python files this port adds.

### 6.8 `voss-cli` glue

`main()` only knows about clap, dispatch, and exit codes. Each subcommand is a function in `src/cli/<verb>.rs` that owns its argument struct and orchestrates the right sub-crates.

## 7. Plan flow at runtime

```
                ┌─ user types: voss do "fix the build"
                ▼
       voss-cli (Rust)
                ▼
   resolve_auth() → ClaudeOAuth(creds)
                ▼
   AnthropicOauthProvider::new(creds)
                ▼
   default_toolset(cwd) — Rust tool structs
                ▼
   run_turn(task, tools, ..., provider, ...)
                ▼
   provider.complete({Plan schema})  ←─── HTTPS to api.anthropic.com
                ▼
   Plan parsed (serde) — confidence 0.91
                ▼
   for step in plan.steps:
       gate.check(...)  → ask user via crossterm if needed
       tool.invoke(args)  → e.g. VossCheck → PyBridge::check(...)
                ▼                            ▼
          renderer.show_tool_call()    voss-bridge speaks
                                       JSON-RPC to python -m
                                       voss.bridge_server
                ▼
   renderer.show_final(...)
                ▼
   ExitCode::SUCCESS
```

## 8. Phasing

Each phase is independently mergeable. Each ends with the binary compiling, all prior tests passing, and a runnable demo.

### R1 — Workspace + clap skeleton + bridge (2 days)

- Cargo workspace, all 7 crates with empty modules.
- `voss-cli`: clap CLI with every verb as a stub printing `unimplemented`.
- `voss-bridge`: `PyBridge::ast` working — one round-trip to Python, JSON parsed.
- New Python module `voss/bridge_server.py` shipped — ~80 LOC.
- CI: `cargo build --release` on macOS arm64 + Linux x86_64 in GitHub Actions.
- **Demo**: `voss-cli ast foo.voss --json` returns identical bytes to `python -m voss ast foo.voss --json`.

### R2 — Auth port (2 days)

- `voss-auth`: macOS keychain via `security-framework`, file fallback, refresh for both Anthropic + Codex.
- Doctor verb works end-to-end: prints both cred sources, picks the right one.
- Hermetic tests using temp HOME and `wiremock` for refresh endpoints.
- **Demo**: `voss-cli doctor` matches Python `voss doctor` output line-for-line.

### R3 — Anthropic OAuth provider (2 days)

- `voss-providers`: full Anthropic OAuth provider — preamble, headers, tool-use translation, refresh-on-401.
- Snapshot tests (insta) of the request bytes.
- **Demo**: `voss-cli do "what is 2+2?" --auth=claude --yes` returns "4" against live Anthropic via Claude OAuth.

### R4 — Sandbox + tools (2 days)

- `voss-tools`: all 9 tools ported. Allowlist + jail mirror Python.
- `schemars` derives schemas; verify byte-identical to Python's hand-rolled.
- Hermetic tests with `tempfile` for fs tools, `tokio::process` mocks for shell.
- **Demo**: `voss-cli do "list python files" --yes` runs end-to-end with `fs_glob`.

### R5 — Renderer + permissions (2 days)

- `voss-render`: Tty + Plain + Ndjson all present. crossterm-based.
- Permission gate: interactive prompt via crossterm raw mode, persisted decisions.
- **Demo**: `voss-cli do --mode=plan` prompts before running shell tools.

### R6 — Sessions (1 day)

- `voss-cli sessions` / `voss-cli resume <id>` / `/save` slash command.
- JSON format wire-compatible with Python — same files round-trip both ways.
- **Demo**: `python -m voss chat` saves a session, `voss-cli resume <id>` rehydrates it.

### R7 — Agent loop + slash commands (2 days)

- `voss-agent`: full `run_turn` parity with Python's behavior.
- `chat` REPL with line editing (rustyline or `reedline`), slash commands, status line.
- All harness tests in `tests/harness/test_agent_integration.py` ported to Rust integration tests.
- **Demo**: `voss-cli` (bare) drops into REPL, runs a multi-turn session against Claude OAuth.

### R8 — Codex OAuth (2 days)

- `voss-providers`: OpenAI provider with full Codex CLI wire format.
- Depends on `.planning/CODEX-OAUTH-PLAN.md` Phase A (reverse-engineered fixtures).
- Snapshot tests using captured fixtures.
- **Demo**: `voss-cli do --auth=codex --yes "what is 2+2?"` works against live ChatGPT subscription.

### R9 — Distribution + cutover (1 day)

- `cargo-dist` config: signed binaries for macOS arm64, macOS x86_64, Linux x86_64, Linux arm64.
- Brew tap formula at `voss/homebrew-tap`.
- `pyproject.toml` adds optional dep `voss-cli` (downloads matching binary on first agent verb invocation if not on PATH).
- `voss.cli:main` (Python) detects whether `voss-cli` binary is reachable; if so, exec it for agent verbs; if not, fall back to in-process Python harness.
- **Demo**: `brew install voss/tap/voss && voss do "..."` works without a Python runtime visible to the user (Python is bundled in `pip install voss` for compiler use only).

## 9. Migration / cutover strategy

Both stay in tree during the transition:

- `voss/harness/` (Python) — kept until R9 ships and stable for one release.
- `crates/voss-cli/` (Rust) — added in R1, evolves to feature parity through R7.
- Dispatcher in `voss/cli.py` (Python) chooses:
  ```python
  if shutil.which("voss-cli"):
      os.execvp("voss-cli", ["voss-cli", "do", *args])
  else:
      from voss.harness.cli import do_cmd
      do_cmd(args)
  ```
- Once Rust is the default for ≥1 month with no rollbacks, delete `voss/harness/`.

This keeps the Python harness as a working fallback for users who don't have the Rust binary yet, and lets us release the Rust binary independently of Python package versioning.

## 10. Testing strategy

| Test layer | What it covers | Example |
|---|---|---|
| Unit (cargo test in each crate) | Pure logic — tool arg parsing, sandbox jail, plan deserialization | `voss-tools/tests/sandbox.rs` |
| Snapshot (`insta`) | Request bytes for each provider, renderer output | `voss-providers/tests/anthropic_snapshot.rs` |
| HTTP mock (`wiremock`) | Full provider request/response cycle, refresh-on-401 | `voss-providers/tests/oauth_refresh.rs` |
| Bridge | Python subprocess round-trip — `voss-bridge` against real `voss/cli.py` | `voss-bridge/tests/check.rs` |
| End-to-end (`assert_cmd`) | Spawn `voss-cli` binary, assert exit codes + stdout | `voss-cli/tests/cli.rs` |
| Parity (`compare_python_rust.rs`) | For every read-only verb, run both binaries; assert byte-identical output | `tests/parity/` |
| Live (`#[ignore]` by default) | Smoke against real providers — opt-in, nightly | `voss-providers/tests/live/` |

CI matrix: macOS arm64 (primary), macOS x86_64, Linux x86_64, Linux arm64. Windows deferred.

## 11. Distribution

| Artifact | Channel | Notes |
|---|---|---|
| `voss-cli` static binary | `cargo-dist`-signed releases on GitHub | Per-arch downloads in CI, attached to release tag. |
| `voss/tap/voss` | Homebrew tap | Auto-published by `cargo-dist`. Includes both binary + Python compiler dep. |
| `pip install voss` | PyPI | Python-only install — compiler + Python harness fallback. Detects + downloads `voss-cli` binary on first run if not present. |
| `pipx install voss` | PyPI via pipx | Same as above; recommended for users who want isolated install. |

Release signing policy: macOS signing is for Developer ID distribution outside the Mac App Store, not App Store submission. The purpose is to reduce Gatekeeper friction, bind public binaries to an identifiable Apple Developer account, and make tampering detectable alongside SHA256 release checksums. Early/internal releases may skip signing with known macOS warning friction, but public Rust-as-default releases should use Developer ID signing; notarization can be wired separately if the release channel requires Gatekeeper-clean first launch.

## 12. Performance targets

| Metric | Python today | Rust target | Stretch |
|---|---|---|---|
| `voss --version` | ~700ms | ≤50ms | ≤20ms |
| `voss doctor` | ~1.1s | ≤80ms | ≤50ms |
| `voss do "<task>"` first byte | ~1.4s + provider | ≤200ms + provider | ≤120ms |
| `voss compile foo.voss` (cold) | ~900ms | ≤300ms (Python warmup) | ≤200ms |
| `voss compile foo.voss` (warm via bridge) | n/a | ≤30ms | ≤15ms |
| Binary size | n/a | ≤12MB stripped | ≤8MB |
| Memory at idle REPL | ~120MB | ≤25MB | ≤15MB |

If R7 closes outside these targets, profile before declaring done.

## 13. Risks

| Risk | Mitigation |
|---|---|
| `voss-bridge` adds startup cost | Long-lived JSON-RPC server (stdin/stdout) — pay Python warmup once per session, not per call. |
| Python+Rust dual-tree confuses contributors | One README in each crate; root README points at both. CI enforces both stay green. |
| Schema drift between Python pydantic models and Rust serde structs | Single source of truth: derive schemas with `schemars` in Rust, dump as JSON, snapshot-test against Python's pydantic schemas. CI fails if they diverge. |
| Anthropic / OpenAI wire formats drift | Snapshot fixtures against captured real traffic, refresh quarterly, surface clear error messages on 4xx so we notice fast. |
| `security-framework` API surface changes between macOS versions | Pin crate version; CI runs on macOS 14, 15. |
| Rust learning curve for contributors used to Python | Public API surface is small per crate; most contributions are tool/provider additions which follow simple patterns. README per crate. |
| Single-binary distribution + signing | `cargo-dist` + Apple Developer ID signing for public macOS binaries. This is outside-App-Store trust/integrity, not App Store submission. Notarization is separate and can be added when release channel policy requires Gatekeeper-clean first launch. Document keychain setup once. |

## 14. Effort

| Phase | Days |
|---|---|
| R1 — workspace + bridge | 2 |
| R2 — auth port | 2 |
| R3 — Anthropic OAuth | 2 |
| R4 — sandbox + tools | 2 |
| R5 — renderer + permissions | 2 |
| R6 — sessions | 1 |
| R7 — agent loop + slash commands | 2 |
| R8 — Codex OAuth | 2 |
| R9 — distribution + cutover | 1 |
| **Total focused** | **16 days** |
| Buffer (20%) | +3 |
| **Realistic** | **~19 days / ~4 weeks** |

## 15. Acceptance criteria for v1.2 ship

1. `voss --version` returns in ≤50ms cold.
2. Every Python harness test in `tests/harness/` has a Rust integration equivalent and passes.
3. Parity suite passes byte-identical for `--help`, `doctor`, `sessions`, `--json` output of agent verbs.
4. Live smokes pass against Anthropic OAuth and Codex OAuth (the latter pending `CODEX-OAUTH-PLAN.md` Phase A).
5. `brew install voss/tap/voss` lands a single binary that works without Python on PATH for agent verbs (compiler verbs require Python, fail with actionable error when missing).
6. `pip install voss` still works and auto-downloads the matching `voss-cli` binary on first agent verb invocation.
7. README + `voss --help` documents the dual-binary architecture.
8. Python harness directory `voss/harness/` deletable without breaking any user-visible feature.

---

## 16. Out of scope for v1.2

- Native compilation of the **compiler** to Rust (Lark-equivalent parser, semantic analyzer, codegen). Stays Python forever — no value in porting.
- Voss-the-language port to a non-Python target. Out of language scope.
- Windows support. Add post-1.2.
- IDE / editor integration. Separate workstream.
- Embedded WASM build of `voss-cli` for browser harnesses. Future.

---

*Plan created: 2026-05-09. Starts when v1.1 H1–H5 ship.*
