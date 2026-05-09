# Phase 7: rust-port - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 7 ports the Python harness shell (`voss/harness/*.py`, ~2122 LOC) to a
Rust binary (`crates/voss-cli/`) at functional parity, ships it as a single
static install across macOS arm64/x86_64 and Linux x86_64/arm64, and keeps
the Python compiler reachable through a long-lived JSON-RPC bridge
(`voss-bridge` crate ↔ a new `voss/bridge_server.py`).

**In scope:**
- New Cargo workspace at repo root with 7 member crates: `voss-cli` (binary),
  `voss-agent`, `voss-providers`, `voss-auth`, `voss-tools`, `voss-render`,
  `voss-bridge`.
- One new Python module: `voss/bridge_server.py` (~80 LOC). JSON-RPC over
  stdio server exposing `ast`, `check`, `compile`, `run` to Rust.
- Additive `--json` flags on read-only compiler verbs (already partly there
  for `ast`).
- `cargo-dist` distribution pipeline + Homebrew tap + Python dispatcher
  (`voss/_dispatcher.py`) that auto-downloads the matching binary on first
  agent verb invocation.

**Out of scope:**
- Native compilation of the Voss compiler / runtime to Rust (compiler stays
  Python forever).
- Voss-the-language port to a non-Python target.
- Windows distribution.
- IDE / editor integration.
- Embedded WASM build of `voss-cli`.

</domain>

<decisions>
## Implementation Decisions

### Bridge framing protocol
- **D-01:** `voss-bridge` ↔ `voss/bridge_server.py` uses **LSP-style framing**:
  `Content-Length: <n>\r\n\r\n<json-body>`. Standard in language servers
  (rust-analyzer, pyright). Robust against embedded newlines in tool output
  and source code that we'd otherwise have to escape. Slightly more parser
  code on both sides — accepted cost.
- **D-02:** Frame parser must reject negative or absent `Content-Length`,
  treat `Content-Length` as the only authoritative header, ignore unknown
  headers (forward compatibility).
- **D-03:** JSON body uses the existing versioned envelope shape
  (`{"v": 1, ...}`). Future protocol revisions bump the version; v1 readers
  must keep working.

### Auto-download UX
- **D-04:** When `pip install voss` is the entry path and the Rust
  `voss-cli` binary is missing on first agent verb invocation,
  `voss/_dispatcher.py` **prompts `[y/N]` once and persists the decision**
  to `~/.config/voss/config.toml` (key: `dispatcher.allow_autodownload`).
- **D-05:** On `y`: download the matching arch binary from the latest
  GitHub release into `~/.local/bin/voss-cli`, verify SHA256 against the
  release manifest, then `os.execvp` it. SHA mismatch → abort, never exec.
- **D-06:** On `N` or non-TTY stdin: refuse with an actionable error
  pointing at `brew install voss/tap/voss` or `curl ... | sh`. Exit 2.
  Decision persists for future runs in the same way.
- **D-07:** Compiler verbs (`compile`, `run`, `check`, `init`, `ast`) never
  trigger auto-download — they always run in Python.

### Status line cadence
- **D-08:** Status line (`model · tokens · $cost · ctx%`) renders **at end
  of turn only**, matching current Python behavior. One render after final
  answer in TTY mode. Suppressed in non-TTY / `--json` mode.
- **D-09:** Live streaming updates and always-pinned status are **deferred**
  to a future polish phase. Reason: lower scope, faster ship to parity, and
  raw-mode terminal handling has its own bug surface that doesn't belong in
  the port.
- **D-10:** Status line accent rules carry over from Python: yellow when
  `ctx% > 80%`, red when `cost > $1.00`. Audible bell on 90% budget.

### Sub-agent parallelism
- **D-11:** Plan execution in `voss-agent::run_turn` is **parallel by
  default** in Phase 7 — does not match Python's sequential behavior.
  Trade-off accepted: faster turns at the cost of strict ordering.
- **D-12:** Safety rule: **read-only tools fan out concurrently; mutating
  tools run serially**. Static rule, no model judgment required.
  - **Read-only set (parallel):** `fs_read`, `fs_glob`, `fs_grep`,
    `git_status`, `git_diff`, `voss_check`.
  - **Mutating set (serial):** `fs_write`, `fs_edit`, `shell_run`, plus any
    new tool that touches state. Tool definitions carry an explicit
    `is_mutating: bool` flag so the loop's classification is data-driven,
    not pattern-matched.
- **D-13:** When a parallel batch contains both classes, the loop runs the
  read-only group concurrently first, awaits all, then runs each mutating
  step in plan order. Concurrency cap: 8 in-flight reads (tunable).
- **D-14:** Permission gate is consulted **per step before scheduling**, not
  after. A denied step in a parallel batch does not block siblings.
- **D-15:** Schema parity matters here — Python today is sequential; if
  v1.1 Python ever needs to match Rust's parallel default, that's a Python
  follow-up. Phase 7 does not force a Python change.

### Claude's Discretion
- Crate boundaries inside the workspace (which types live in `voss-agent`
  vs `voss-providers`) — implementation detail.
- HTTP client tuning (connect timeout, read timeout, retry backoff) — pick
  reasonable defaults; tune if observed.
- Test fixture organization inside each crate — follow Rust conventions
  (`tests/` dir, `#[cfg(test)]` modules).
- Concurrency cap for the parallel read group — start at 8, tune.
- Exact `cargo-dist` config knobs (PR / release flow) — pick the standard
  recipe.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 7 design
- `.planning/RUST-PORT-PLAN.md` — full design: workspace layout, crate
  boundaries, dependency picks, R1-R9 phasing, perf targets, risks. The
  authoritative source for everything Rust.
- `.planning/CODEX-OAUTH-PLAN.md` — wire-format reverse-engineering plan
  for Codex ChatGPT subscription. R8 hard-blocks on Phase A of this plan
  (captured fixtures in `.planning/codex-fixtures/`).
- `.planning/HARNESS-PLAN.md` — original harness design (the Python target
  we're porting). Reference for behavior we must preserve.

### Roadmap + state
- `.planning/ROADMAP.md` §"Milestone v1.2 — Rust Harness Shell" — phase
  goals, success criteria, RUST-NN requirement IDs.
- `.planning/PROJECT.md` — milestone v1.0 context (Voss compiler). Out of
  scope for Phase 7 except as the binary the bridge talks to.

### Python source being ported (read-only during this phase)
- `voss/harness/agent.py` (237 LOC) — `run_turn` and `Plan` schema. Maps to
  `voss-agent` crate.
- `voss/harness/auth.py` (329 LOC) — Keychain + file discovery + refresh.
  Maps to `voss-auth` crate.
- `voss/harness/cli.py` (484 LOC) — Click dispatcher. Maps to `voss-cli`
  binary `cli/` modules.
- `voss/harness/permissions.py` (126 LOC) — gate + persistence. Maps to
  `voss-cli/src/permissions.rs`.
- `voss/harness/providers.py` (401 LOC) — `AnthropicOAuthProvider`,
  `OpenAIOAuthProvider`. Maps to `voss-providers` crate.
- `voss/harness/render.py` (202 LOC) — Tty/Plain/Ndjson renderers. Maps to
  `voss-render` crate.
- `voss/harness/sandbox.py` (49 LOC) — jail + allowlist. Maps to
  `voss-tools/src/sandbox.rs`.
- `voss/harness/session.py` (112 LOC) — save/load sessions. Maps to
  `voss-cli/src/session.rs`.
- `voss/harness/tools.py` (170 LOC) — 9 tool implementations. Maps to
  `voss-tools` crate.

### Python tests being ported
- `tests/harness/test_agent_integration.py`
- `tests/harness/test_auth.py`
- `tests/harness/test_cli.py`
- `tests/harness/test_oauth_provider.py`
- `tests/harness/test_openai_oauth.py`
- `tests/harness/test_sandbox.py`
- `tests/harness/test_session.py`
- `tests/harness/test_tools.py`

### External protocols / standards
- LSP base protocol (Microsoft) — for D-01 framing format. Public spec.
- JSON-RPC 2.0 (jsonrpc.org) — request/response shape over the framed bytes.
- Anthropic Messages API + `anthropic-beta: oauth-2025-04-20` — captured in
  `voss/harness/providers.py:AnthropicOAuthProvider` already; no new spec
  needed.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Python harness (`voss/harness/*.py`)**: ~2122 LOC of working,
  test-covered code. Defines exact behavior the Rust port must match.
  Treat as the parity contract.
- **Test fixtures (`tests/harness/test_*.py`)**: 67 tests including
  `httpx.MockTransport` patterns for OAuth providers. The same mock
  responses port as `wiremock::Mock` matchers in Rust.
- **`voss/cli.py:main`**: existing Click group. Phase 7 adds a dispatcher
  block that detects + execs the Rust binary for agent verbs while keeping
  Python in-process for compiler verbs.
- **`pyproject.toml [project.scripts] voss = "voss.cli:main"`**: stays
  unchanged. The Rust binary is invoked through this entry point via
  `os.execvp`, never replacing the script.
- **`voss_runtime` and `voss/parser.py|analyzer.py|codegen.py`**: read-only
  for this phase. The bridge calls these via existing public APIs through
  the new `voss/bridge_server.py`.

### Established Patterns
- **Confidence-gated planning**: `Plan` schema ships pydantic JSON Schema
  to providers; `schemars::JsonSchema` derive in Rust must produce the same
  schema bytes. Snapshot test enforces equivalence.
- **Tool descriptor pattern**: Python `@tool` decorator → `ToolDescriptor`
  with `name`, `description`, `parameters` (JSON Schema), `invoke()`. Rust
  trait `Tool` + per-tool struct mirrors this 1:1.
- **Provider protocol**: `voss_runtime.providers.base.ModelProvider` (async
  `complete`, sync `count_tokens`). Rust trait is the same shape; both
  HTTP-direct (no SDK) and snapshot-tested.
- **Subscription auth quirks**: Anthropic OAuth requires the Claude Code
  preamble (already captured in `providers.py`); Codex ChatGPT mode requires
  full Codex CLI wire shape (R8 dependency). Both are non-obvious and must
  port verbatim.

### Integration Points
- **Bridge boundary**: `voss-bridge` crate is the only place Rust and
  Python interact. One long-lived `tokio::process::Child` running
  `python -m voss.bridge_server` over LSP-framed JSON-RPC. Pay Python
  startup once per session.
- **Auth boundary**: `voss-auth` is the only place we touch the Keychain
  (`security-framework`) or `~/.codex/auth.json`. All other crates take
  resolved creds as input.
- **Provider boundary**: `voss-providers` is the only place we make HTTPS
  calls to Anthropic / OpenAI. All other crates work with the
  `ModelProvider` trait, never the network.
- **Distribution boundary**: `voss/_dispatcher.py` is the only place that
  decides "use Rust binary or fall back to Python." `voss.cli:main` calls
  it once at the top of agent verbs.

</code_context>

<specifics>
## Specific Ideas

- **Reference harnesses**: Codex CLI (Rust + tokio), Pi CLI (Rust), Claude
  Code (Bun-compiled Node). Phase 7 should match their cold-start, binary
  size, and install UX. Targets in `.planning/RUST-PORT-PLAN.md` §12.
- **Codex preamble fidelity**: when Phase A captures real Codex CLI traffic,
  preserve the system instructions string verbatim. Same posture as the
  Anthropic Claude Code preamble — magic constant, do not paraphrase.
- **Schemars over hand-rolled schemas**: derive JSON Schema from arg structs
  via `schemars::JsonSchema`. Compare against pydantic schemas in CI;
  drift = build failure.
- **Insta over manual snapshot files**: every provider request body, every
  renderer output method, every NDJSON event uses `insta` for snapshot
  testing. Locks behavior across refactors.

</specifics>

<deferred>
## Deferred Ideas

- **Live streaming status line + always-pinned status** (raised in Area 3,
  decided against for ship velocity). Future polish phase post-v1.2.
- **Sequential-by-default + parallel-on-explicit-flag** (raised in Area 4
  as a less-aggressive alternative). Phase 7 picks parallel-by-default with
  static safety rule instead. If parallel-default proves error-prone in
  practice, revisit by lowering the concurrency cap or moving to opt-in
  parallel groups.
- **`gather`-style language-level parallel sub-agents** (HARNESS-PLAN H3
  introduces this when `gather` keyword is lowered to Rust). Phase 7's
  parallel default is data-driven from the Plan schema, not from
  language-level `gather`. v1.3 lowers `gather` and joins them up.
- **Telemetry / usage reporting** (mentioned in RUST-PORT-PLAN §13). Stays
  off in Phase 7 even when added later — not a v1.2 ship blocker.
- **Windows distribution** (RUST-PORT-PLAN §16). DPAPI for credential
  storage, MSIX or scoop package. Post-v1.2.
- **WASM build of `voss-cli`** for browser harness use. Future milestone.
- **MessagePack framing** (raised in Area 1 as binary alternative). Stays
  deferred — JSON+LSP is debuggable; MessagePack only matters at scale we
  don't have.
- **Silent auto-download** (raised in Area 2). Stays deferred — explicit
  prompt is the privacy/trust default. Re-evaluate if onboarding friction
  becomes a measured problem.

</deferred>

---

*Phase: 07-rust-port*
*Context gathered: 2026-05-09*
