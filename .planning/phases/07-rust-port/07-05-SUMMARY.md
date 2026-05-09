---
plan: 07-05
status: complete
date: 2026-05-09
---

# 07-05 — Render + Permissions (R5) Summary

Wave R5 ports `voss/harness/render.py` (202 LOC) to the `voss-render` crate
(3 impls: TTY/Plain/NDJSON) and `voss/harness/permissions.py` (126 LOC) to
`voss-cli/src/permissions.rs`. Status-line accent rules and audible-bell
budget gate (D-08, D-09, D-10) are locked by tests; NDJSON wire format is
locked by 8 insta snapshots; persisted always-allow decisions round-trip
through `~/.config/voss/permissions.toml`.

## Renderer choice: crossterm, not ratatui

`RUST-PORT-PLAN.md` flagged `ratatui` as optional. **Chose crossterm.**
The harness UI is a stream of one-shot prints (banner / user / plan / tool
lines), not a stateful TUI with widgets, panes, or scrolling regions.
`ratatui` would add a frame loop + diff engine for no benefit. crossterm
gives us:
- terminal size for status-line width via `crossterm::terminal::size()`
- raw stdout writes that respect the user's terminal (no double-buffering)
- portability across platforms when we add Windows back in a later phase.

ANSI SGR codes (yellow `\x1b[33m`, red `\x1b[31m`, dim `\x1b[2m`) are
emitted directly by `status_line::format` instead of going through
crossterm's color API — keeps the function pure and trivially testable
(the existing `status_line.rs` tests grep for the exact byte sequences).

## NDJSON snapshot review

8 event snapshots written to `crates/voss-render/tests/snapshots/`. All
pass. Each line is a single JSON object with a `"v": 1` envelope key.
Verified shape:

| Event   | Required keys |
|---------|---------------|
| banner  | `type=banner`, `model`, `cwd`, `git`, `v` |
| user    | `type=user`, `task`, `v` |
| thinking| `type=thinking`, `label`, `v` |
| plan    | `type=plan`, `confidence`, `steps:[{name,args}]`, `cost_usd`, `v` |
| tool    | `type=tool`, `name`, `args`, `summary`, `state`, `v` |
| clarify | `type=clarify`, `question`, `confidence`, `v` |
| final   | `type=final`, `text`, `confidence`, `cost_usd`, `v` |
| status  | `type=status`, `model`, `tokens`, `cost_usd`, `ctx_pct`, `v` |

Two cosmetic notes (carried over from R3):
- `confidence: 0.8999999761581421` in the plan snapshot is the f32→f64
  widening artifact when serializing `f32` through `serde_json`. Same
  numeric value Python emits as `0.9`; Anthropic accepts both. Locked by
  the snapshot regardless.
- `serde_json` orders object keys alphabetically by default. Python's
  `json.dumps(default=str)` preserves insertion order. The Rust output
  is sorted (`{"cwd":...,"git":...,"model":...,"type":"banner","v":1}`),
  which is structurally identical and easier to parity-check in JSON
  pipelines. Documented here so the next reader doesn't chase it.

The standalone `every_event_has_v_field` test re-runs every event method
and asserts `v == 1` on each emitted line — guards against any future
event method that bypasses `emit()`.

## Status-line accent rules (D-08..D-10)

Locked by `crates/voss-render/tests/status_line.rs`:

- yellow accent emitted (SGR `\x1b[33m`) iff `ctx_pct > 0.8`
- red accent emitted (SGR `\x1b[31m`) iff `cost_usd > 1.0`
- audible bell `\x07` emitted iff `ctx_pct >= 0.9`

Boundary cases (`0.8`, `0.85`, `0.9`, `0.95`, `cost = 1.5`) all covered
in 5 unit tests. End-of-turn cadence (D-08) is enforced by the *agent
loop* (R7), not by the renderer — `TtyRender::status` is willing to
print whenever called. The agent calls it once per turn after `show_final`
in TTY mode, never in `--json` mode. Documented here so the R7 wave
doesn't accidentally invert the contract.

## Prompt mechanism: injected closure

Chose **closure injection** for `PermissionGate::check`. Signature:

```rust
pub fn check<F>(&mut self, tool_name: &str, args: &Value, prompt: F) -> (bool, &'static str)
where F: FnOnce(&str, &Value) -> char
```

Rationale:
- Tests inject a deterministic `|_, _| 'A'` closure. No global state to
  mutate, no boxed `Fn` trait objects to clean up between cases.
- Production callers pass `permissions::interactive_prompt` (a free
  function with the same signature), keeping the call site explicit:
  `gate.check(name, args, interactive_prompt)`. Mirrors Python's
  `prompt_fn` field but without the runtime cost of a stored boxed Fn.
- The default-deny semantics (Python's "non-interactive denial" branch
  at `permissions.py:101`) lives in the *caller* — production passes
  an isatty-checking closure that returns `'d'` when stdin is not a
  TTY. The tests are explicitly interactive (closure returns `'a'` /
  `'A'` / `'d'`) so they don't need the isatty branch.

## D-12 alignment

`permissions::READ_ONLY` matches `tests/schema_parity.rs::is_mutating_flags_match_d12`'s
expected read-only set: `{fs_read, fs_glob, fs_grep, git_status, git_diff,
voss_check}`. `WRITE = {fs_write, fs_edit}`, `SHELL = {shell_run}`. The
sets are duplicated as `&[&str]` constants in `voss-cli` and as the
`is_mutating()` bool on each tool in `voss-tools`; they're verified
separately but kept consistent at code-review time. (A cross-crate
parity test would require `voss-cli` to depend on `voss-tools` solely
for the registry, which is a circular import risk; the current single-
source-of-truth is the registry, with `voss-cli` as a hardcoded mirror.)

## Test inventory (R5)

- `crates/voss-render/tests/status_line.rs` — 5 cases.
- `crates/voss-render/tests/ndjson_snapshot.rs` — 8 snapshot tests + 1
  envelope test = 9 cases.
- `crates/voss-cli/tests/permissions_round_trip.rs` — 8 cases (load/save
  round-trip, signature shape, mode + auto_yes prompt rules,
  remember-on-A persistence).

R5 total: 22 new tests, 8 new snapshot fixtures, all passing. Workspace
total still green; no libpython linkage; no Keychain prompts.

## Verification

```
cargo test -p voss-render --no-fail-fast    # 5 status + 9 ndjson = 14 pass
cargo test -p voss-cli --test permissions_round_trip    # 8 pass
grep -c 'PROTOCOL_VERSION' crates/voss-render/src/ndjson.rs    # 2 (definition + use)
grep 'permissions.toml' crates/voss-cli/src/permissions.rs    # 1 match
```
