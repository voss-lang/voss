---
plan: 07-01
status: complete
date: 2026-05-09
---

# 07-01 — Walking Skeleton (R1) Summary

Wave R1 stood up the Cargo workspace, the LSP-framed JSON-RPC bridge to a new
`voss/bridge_server.py` Python module, and an end-to-end `voss-cli ast`
round-trip that reaches structural parity with the Python `voss ast` command.

## Workspace layout

Root `Cargo.toml` declares `resolver = "2"` and 7 members:

| crate            | type | depends on                                                        |
|------------------|------|-------------------------------------------------------------------|
| `voss-cli`       | bin+lib | voss-agent, voss-providers, voss-auth, voss-tools, voss-render, voss-bridge, clap, tokio |
| `voss-agent`     | lib  | serde, serde_json, thiserror, anyhow                              |
| `voss-providers` | lib  | serde, serde_json, thiserror, anyhow                              |
| `voss-auth`      | lib  | serde, serde_json, thiserror, anyhow                              |
| `voss-tools`     | lib  | serde, serde_json, thiserror, anyhow                              |
| `voss-render`    | lib  | serde, serde_json, thiserror, anyhow                              |
| `voss-bridge`    | lib  | tokio, serde, serde_json, thiserror, anyhow                       |

`voss-cli` is the only binary; all other crates are libraries with placeholder
`version()` exports until later waves wire them up.

`[workspace.dependencies]` pins every runtime dep called out in
`RUST-PORT-PLAN.md §4`. Crates pull deps through `{ workspace = true }`.

## Bridge protocol specifics

`voss-bridge` exposes `PyBridge` (`crates/voss-bridge/src/jsonrpc.rs`). It
spawns one long-lived `python -m voss.bridge_server` child and dispatches
JSON-RPC over LSP-style framing.

Framing rules (`crates/voss-bridge/src/framing.rs`):
- Header lines terminated by `\r\n`; header block terminated by an empty line.
- Header names are matched case-insensitively (`content-length`, `Content-Length`,
  `CONTENT-LENGTH` are all recognised).
- Lines without a colon are silently ignored; unknown headers are tolerated
  (D-02 forward-compat).
- `Content-Length` is parsed as `i64`; missing, negative, or non-numeric
  values surface as `io::ErrorKind::InvalidData`.

Wire envelope (D-03): every successful response wraps the method's payload in
`{"v": 1, ...}`. The Python side hard-codes `PROTOCOL_VERSION = 1`; the Rust
test asserts `result.v == 1`.

Method shapes implemented this wave:
- `ast`     → `{"v": 1, "program": <to_dict(program)>}`
- `check`   → `{"v": 1, "ok": bool, "diagnostics": [...]}`
- `compile` → `{"v": 1, "output": "<path>", "ok": true}` (writes the .py file)
- `run`     → stub (`{"v": 1, "ok": true, "note": "stub"}`); R3 will wire the runtime path.

Errors are surfaced as JSON-RPC `error` objects (`code: -32000` for handler
exceptions, `-32601` for unknown methods, `-32700` for parse errors).

## AST node-kind key

The existing serializer in `voss/ast_serializer.py` emits node kinds under the
`_node` key (e.g. `"_node": "Program"`), not `"kind"` as PLAN.md prose
sometimes implies. Tests assert `program._node == "Program"` to match the
real serialized shape; no changes were made to the serializer.

## Python interpreter discovery

`PyBridge::discover()` looks at, in order:
1. `$VOSS_PYTHON`
2. `.venv/bin/python` relative to CWD
3. `python3` on PATH

Tests use `PyBridge::with_python(...)` to inject an absolute interpreter path
(picking up `.venv/bin/python` from the repo root regardless of cargo's CWD).

## Fixture path

The bridge round-trip and CLI parity tests both consume
`samples/classify.voss`, an existing repository fixture. No new test data was
added.

## CI

`.github/workflows/rust.yml` runs on `macos-14` and `ubuntu-latest`:
1. `actions/setup-python@v5` with Python 3.11
2. `pip install -e .` so `voss.bridge_server` is importable for the round-trip
3. `cargo build --workspace --release`
4. `cargo test --workspace --no-fail-fast` with `VOSS_LIVE_SMOKES=0`

No Windows matrix entry (deferred per RUST-PORT-PLAN §16). No `--live` test
invocation.

## Deviations from RUST-PORT-PLAN.md

None of substance. Two notes:
- The plan referenced `kind` for the AST node discriminator; the serializer
  uses `_node`. Tests follow the code, not the prose.
- `voss-cli ast` accepts both `--json` and `--compact`. Today the output is
  always JSON (the bare envelope from PyBridge); `--compact` toggles
  pretty-printing. `--json` is accepted as a no-op for parity with the
  expected stable surface.

## Verification

Local on macOS arm64:
- `cargo build --workspace --release` — clean.
- `cargo test --workspace --no-fail-fast` — 7 tests pass (5 framing,
  1 round_trip, 1 ast_parity), 0 failed.
- `cargo run -p voss-cli -- ast samples/classify.voss --json --compact`
  pipes into `python3 -c "..."` and asserts `v == 1` and
  `program._node == "Program"`.
- `grep -rn 'pyo3\|cpython' crates/` — no matches (constraint upheld).
