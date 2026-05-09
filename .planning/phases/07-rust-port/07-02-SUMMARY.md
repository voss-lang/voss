---
plan: 07-02
status: complete
date: 2026-05-09
---

# 07-02 — voss-auth + Doctor (R2) Summary

Wave R2 ports `voss/harness/auth.py` to the Rust `voss-auth` crate (Keychain
on macOS, file fallback for Linux, OAuth refresh for Anthropic + Codex,
preference-based resolution) and wires `voss-cli doctor` at structural parity
with `voss/harness/cli.py::doctor_cmd`.

## Crate layout

`crates/voss-auth/`
- `anthropic.rs` — `AnthropicOAuthCreds` + verbatim constants (client id
  `9d1c250a-e61b-44d9-88ed-5944d1962f5e`, token URL, beta header, keychain
  service name).
- `codex.rs` — `CodexCreds` + verbatim constants (client id
  `app_EMoamEEZ73f0CkXaXp7hrann`, token URL, ChatGPT backend base).
- `keychain.rs` — macOS `security-framework` read/write/delete, gated by
  `#[cfg(target_os = "macos")]` with no-op stubs elsewhere.
- `file_store.rs` — JSON read/write for `~/.claude/.credentials.json` (mode
  0600 on Unix) and `~/.codex/auth.json`.
- `refresh.rs` — `refresh_anthropic` (JSON body) and `refresh_codex` (form-
  encoded body), both persisting back to the source-of-truth.
- `resolve.rs` — `AuthPref` enum + `Resolution` enum + `resolve()`. Source
  identifiers match Python verbatim (`env-anthropic`, `env-openai`,
  `claude-oauth`, `codex`, `codex-oauth`, `none`).

## Keychain test strategy

macOS `set_generic_password` will prompt the user for authentication the
first time it touches a service it does not own — unacceptable in CI.
Two-pronged mitigation:

1. **`VOSS_DISABLE_KEYCHAIN=1` env switch.** When set, every Keychain
   function (read/write/delete) short-circuits. Tests that don't *need* a
   Keychain set this and let `refresh_anthropic` fall through to the
   file-store persist path.

2. **`VOSS_KEYCHAIN_SERVICE` override.** Honored by all Keychain calls so
   the live `keychain_round_trip` test uses a unique
   `voss-test-{pid}-{nanos}` service rather than the real `Claude
   Code-credentials` item. That test is `#[ignore]`-gated and runs only
   under `cargo test -- --ignored` (where the user can approve the prompt
   once).

Default `cargo test -p voss-auth` therefore never touches the user's
Keychain — only the file store and wiremock-served HTTP endpoints.

## HOME-override pattern

File-store and refresh tests serialize on a `static Mutex<()>` (env-var
mutation is process-global) and:

1. Save current `HOME` / `VOSS_DISABLE_KEYCHAIN`.
2. Set `HOME` to a fresh `tempfile::TempDir`.
3. Set `VOSS_DISABLE_KEYCHAIN=1`.
4. Run the body inside `panic::catch_unwind`.
5. Restore previous values whether or not the body panicked.

This keeps the tests hermetic without the brittleness of running the whole
suite single-threaded.

## Refresh wire shape

Both `refresh_anthropic` and `refresh_codex` are verified by `wiremock`
servers that match the request body exactly:

- Anthropic: `body_json({"grant_type":"refresh_token","refresh_token":"OLD_RT","client_id":"9d1c250a-e61b-44d9-88ed-5944d1962f5e"})`
  + `header("content-type", "application/json")`.
- Codex: `body_string_contains("client_id=app_EMoamEEZ73f0CkXaXp7hrann")` +
  `body_string_contains("grant_type=refresh_token")` +
  `body_string_contains("refresh_token=OLD_RT")` (form-encoded).

## Doctor parity

Output is 7 lines, in order, with each label left-padded to a 20-character
column followed by `: `:

```
default model       : <model>
ANTHROPIC_API_KEY   : set | unset
OPENAI_API_KEY      : set | unset
Claude Code OAuth   : found (<sub>, expires in <N>s) | not found
Codex creds         : found (<auth_mode>; <bits or 'empty'>) | not found
--auth=auto picks   : <source> — <detail>
voss_runtime        : importable | FAIL <reason>
```

`doctor_parity.rs` runs the binary with `HOME=<tempdir>`,
`VOSS_DISABLE_KEYCHAIN=1`, `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`
unset, and `VOSS_MODEL` unset. Asserts: 7 lines, prefixes match, env-key
lines report `unset`.

### Divergences from Python

- `default model`: Python reads the runtime's live config
  (`voss_runtime.get_config().default_model`). Rust reads
  `$VOSS_MODEL` and falls back to the literal `"claude-sonnet-4-5"` —
  matches Python's default when the runtime has not been reconfigured.
  When R3 wires the provider stack, this will switch to a runtime config
  read.
- `voss_runtime`: Python `try: import voss_runtime`. Rust cannot trivially
  import a Python module without re-introducing libpython linkage
  (forbidden by 07-CONTEXT.md). Instead, Rust checks whether the
  `voss_runtime/` package directory exists at the cwd or one/two parents
  up, mirroring "is the source tree available". Reports `importable` or
  `FAIL not found`.

These two are documented divergences; the line **structure** (label,
column, message format) matches Python exactly so downstream tooling that
greps doctor output is unaffected.

## Verification

```
cargo test --workspace --no-fail-fast    # 10 passed, 1 ignored, 0 failed
cargo run -p voss-cli -- doctor          # 7 lines, correct prefixes
grep -rn 'pyo3\|cpython' crates/voss-auth/   # no matches
grep -c '9d1c250a-e61b-44d9-88ed-5944d1962f5e' crates/voss-auth/src/anthropic.rs  # 1
grep -c 'app_EMoamEEZ73f0CkXaXp7hrann' crates/voss-auth/src/codex.rs              # 1
```
