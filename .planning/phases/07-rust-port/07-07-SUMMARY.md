---
plan: 07-07
status: complete
date: 2026-05-09
---

# 07-07 — Agent Loop + REPL (R7) Summary

Wave R7 ports `voss/harness/agent.py::run_turn` to `voss-agent::run_turn`,
adds D-11..D-14 parallel-by-default execution, and ships the chat REPL +
`do` verb in `voss-cli`. Build-graph cycle prevented via the trait-in-
voss-agent / impl-in-voss-cli pattern.

## Build-graph cycle resolution

Two cycles were prevented in this wave:

### voss-agent ↔ voss-render

Initial setup had `voss-render` depending on `voss-agent` (for `Plan` in
`Render::show_plan(&Plan, ...)`). Once R7 added `voss-render` to
`voss-agent`'s deps for the renderer trait, Cargo detected the cycle.

**Fix.** Pulled `voss-agent` out of `voss-render`'s `[dependencies]` and
added a new primitive view type `PlanStepView<'a> { name, args, why }` in
`voss-render`. `Render::show_plan` now takes `(rationale, &[PlanStepView],
confidence, cost_usd)` — primitive, no domain types. `voss-render` keeps
`voss-agent` only in `[dev-dependencies]` for the snapshot tests, which
Cargo allows (dev-dep cycles are not enforced).

Trade-off: caller (run_turn) builds the view list manually:
```rust
let step_args: Vec<Value> = plan.steps.iter()
    .map(|s| Value::Object(s.args.clone())).collect();
let step_views: Vec<PlanStepView> = plan.steps.iter().zip(step_args.iter())
    .map(|(s, a)| PlanStepView { name: &s.name, args: a, why: &s.why })
    .collect();
renderer.show_plan(&plan.rationale, &step_views, plan.confidence, cost);
```
Acceptable cost for keeping `voss-render` domain-agnostic.

### voss-cli ↔ voss-agent (PermissionCheck)

`voss-cli` owns `PermissionGate` (R5). `voss-agent::run_turn` needs to
consult it. Naïvely placing `PermissionCheck` trait in `voss-cli` would
force `voss-agent` to depend on `voss-cli`.

**Fix.** Defined `pub trait PermissionCheck` in `voss-agent` itself
(`crates/voss-agent/src/run_turn.rs`). `voss-cli`'s `cli/repl.rs` provides
`pub struct GateAdapter<'a> { gate: &'a mut PermissionGate }` that
implements `voss_agent::PermissionCheck` by delegating to `PermissionGate`.
One-way dep: voss-cli → voss-agent. `voss-agent`'s `Cargo.toml` has zero
mention of `voss-cli`.

Verified by:
```
! grep -q '^voss-cli' crates/voss-agent/Cargo.toml
cargo build -p voss-agent     # builds standalone
```

## rustyline vs reedline

Chose **rustyline 14**. Reasons:
- Mature, ~10 years in Rust ecosystem; battle-tested edge cases (UTF-8,
  IME, terminal resize).
- `DefaultEditor::new()` zero-config — gets ↑/↓ history, ←/→ word
  navigation, Ctrl-A/E, Ctrl-D EOF, Ctrl-C cancel out of the box.
- Pure Rust, no extra C deps (vs `rustyline-derive` etc — we don't need
  derive-based completers in v1.2).
- API stability — reedline's API is still in flux through 0.x.

R7 only uses the line-editor primitive. Phase H4+ may revisit reedline
for richer completions / history files / multiline edit, but for v1.2
chat REPL the simpler choice wins.

## `voss_auth::Resolution` variant mapping

`crates/voss-cli/src/cli/auth_to_provider.rs::build` maps each variant
the R2 enum exposes:

| Variant         | Behavior in R7                                                |
|-----------------|----------------------------------------------------------------|
| `ClaudeOAuth`   | ✓ wraps in `AnthropicOAuthProvider::new(creds)`.               |
| `Codex`         | error referencing wave 07-08.                                   |
| `CodexOAuth`    | error referencing wave 07-08.                                   |
| `EnvAnthropic`  | error: env-key paths not in v1.2 chat scope. Use Claude OAuth. |
| `EnvOpenAI`     | error: env-key paths not in v1.2 chat scope. Use Claude OAuth. |
| `None`          | error including the resolver's `detail` reason.                 |

The destructured field names match what R2 produced
(`ClaudeOAuth { creds, .. }`, `Codex { .. }`, `None { detail }`); no
renaming required.

## Plan execution divergence from Python

Python `run_turn` executes steps strictly serially:
```python
for i, step in enumerate(plan.steps):
    # tool dispatch, error handling, etc.
```

Rust `run_turn` partitions per D-11..D-14:

1. **All steps** are gate-checked up-front (per-step, before scheduling).
   Denied/unknown slots are filled immediately and rendered in plan order.
2. **Read-only steps** (where `tool.is_mutating() == false`) execute
   concurrently in chunks of `parallel_cap` (default 8). Within a chunk,
   the renderer prints "running…" for all, awaits `join_all`, then prints
   final state per-step in plan-order.
3. **Mutating steps** then execute serially in plan order.

This intentionally diverges from Python's strict-sequential reference for
the read-only path, matching D-13's `parallel-by-default` directive.
Mutating order parity is preserved. Tests in `tests/parallel_dispatch.rs`
lock all five invariants:
- `read_only_runs_concurrently` — peak concurrency == step count.
- `mutating_runs_serially_in_order` — non-overlapping spans, plan order.
- `denied_step_does_not_block_siblings` — step idx 1 denied; idxs 0+2
  still execute.
- `unknown_tool_is_error` — surfaces `<error: unknown tool ...>`.
- `parallel_cap_respected` — 10 read-only steps with cap=3 → peak ≤ 3.

## D-08 status invariant

`run_turn` accepts `suppress_status: bool`. Caller passes `true` for
`--json` mode, `false` otherwise. Renderer's `status()` is invoked exactly
once at end-of-turn iff `suppress_status == false`. Locked by:
- `json_mode_suppresses_status` — counts zero `"type":"status"` events.
- `tty_mode_emits_status_once` — counts exactly one.

The REPL's loop calls `run_turn` per turn with `json_mode` plumbed
through, so the status-once-per-turn rule holds across any number of
turns.

## REPL slash-command parity

| Slash         | Behavior                                          |
|---------------|---------------------------------------------------|
| `/help`       | print command list                                |
| `/exit /quit` | exit code 0; also Ctrl-D and Ctrl-C exit clean   |
| `/clear`      | drop EpisodicMemory                                |
| `/cost`       | print accumulated session cost                     |
| `/tools`      | list registered tool name + description            |
| `/sessions`   | list saved sessions (id-prefix, updated, name)    |
| `/save [name]`| persist current state via `session::save`         |

Unknown `/foo` prints `unknown command: /foo. /help for list.` and
continues — matches Python.

## Bare invocation behavior

`voss-cli` (no subcommand) defaults to `Cmd::Chat { json: false, mode: "edit", auth: "auto" }`.
The chat dispatcher resolves auth and:
- `Resolution::ClaudeOAuth` → drops into `run_repl`.
- anything else → exits 2 with the message produced by
  `auth_to_provider::build` (which references either `claude login` or
  the wave that will land the missing path).

`bare_invocation_without_auth_exits_2_with_message` verifies this in a
hermetic `HOME=tempdir` + `VOSS_DISABLE_KEYCHAIN=1` environment.

## Test inventory (R7)

- `crates/voss-agent/tests/run_turn.rs` — 4 cases.
- `crates/voss-agent/tests/parallel_dispatch.rs` — 5 cases.
- `crates/voss-cli/tests/repl_smoke.rs` — 4 cases.

R7 total: 13 new tests, all passing. Workspace remains green
(no cycle, no libpython, no Keychain prompts). Anthropic provider
ndjson_snapshot tests required updating for the new `show_plan`
signature; they still pass without snapshot churn since the underlying
JSON shape is unchanged.

## Verification

```
cargo build -p voss-agent           # standalone, no voss-cli compiled
cargo test --workspace --no-fail-fast    # all green
grep -q 'pub trait PermissionCheck' crates/voss-agent/src/run_turn.rs    # ok
grep -q 'struct GateAdapter' crates/voss-cli/src/cli/repl.rs    # ok
grep -q 'impl.*PermissionCheck for GateAdapter' crates/voss-cli/src/cli/repl.rs    # ok
! grep -q '^voss-cli' crates/voss-agent/Cargo.toml    # ok
voss-cli --help    # lists 6 subcommands
```
