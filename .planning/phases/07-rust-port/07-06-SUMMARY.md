---
plan: 07-06
status: complete
date: 2026-05-09
---

# 07-06 — Sessions (R6) Summary

Wave R6 ports `voss/harness/session.py` (112 LOC) to
`crates/voss-cli/src/session.rs`, wires the `voss-cli sessions` and
`voss-cli resume` verbs, and proves cross-language wire-format parity in
both directions (Rust↔Python).

## ISO-8601 timestamp format

Chose the literal `chrono` strftime `"%Y-%m-%dT%H:%M:%S+00:00"`. This
matches Python's
`datetime.now(timezone.utc).isoformat(timespec="seconds")` byte-for-byte
(both produce `2026-05-09T15:30:00+00:00`). Notably:

- `chrono`'s `%:z` would emit `+00:00` but only when the offset is real;
  combined with `Utc` the timezone is always UTC, so a literal
  `+00:00` is safe and removes a class of "is the colon there" drift.
- Python `isoformat(timespec="seconds")` truncates fractional seconds.
  Rust's strftime `%S` truncates the same way. No trailing decimals.

The `rust_writes_python_reads` parity test asserts
`lines[4] == rec.started_at`, locking the format equality.

## Cross-language round-trip

Both directions verified by `crates/voss-cli/tests/session_parity.rs`:

- **Rust→Python**: Rust constructs a `SessionRecord` with two turns,
  serializes with `serde_json::to_vec_pretty`, writes to
  `<tempdir>/voss/sessions/<id>.json`. Python `voss.harness.session.load`
  reads + parses. Asserts `id`, `name`, `len(turns)`, `model`,
  `started_at` all round-trip identically.
- **Python→Rust**: Python `SessionRecord.new(...)` + `save(rec, mem)`
  with two `EpisodicMemory` turns. Rust `session::load` reads back.
  Asserts `name`, `len(turns)==2`, both turn `role`/`content` pairs.

Both tests serialize on a `Mutex<()>` (env-var mutation) and skip
gracefully (printing a reason, not failing) when Python `voss` is not
importable.

## `Turn::extra` flatten preservation

`Turn { role, content, #[serde(flatten)] extra: BTreeMap<String, Value> }`
preserves any unknown keys a Python session may carry through the
round-trip. Today Python's `EpisodicMemory.last(N)` only emits
`{role, content}` (verified at `voss_runtime/memory/episodic.py:36-37`),
so `extra` is always empty in current parity tests. The mechanism is in
place for future schema additions (e.g. `tool_results`, `cost_per_turn`)
without forcing a wire-format break.

## Verbs

- `voss-cli sessions` — output format mirrors Python verbatim:
  `  {id[:8]}  {updated_at}  {model:<28}  {first_task()}`. No name in
  the listing (matches Python; the name is stored in the record but only
  surfaces under `resume`).
- `voss-cli resume <id-prefix-or-name>` — resolves by id-prefix OR exact
  name match. Ambiguity → `InvalidInput`. Not-found → `NotFound`. R6
  prints identity (`name (id, N turns)` + `cwd:` + `model:`); R7 will
  hook the resolved record into the REPL.

## Skipped Python parity tests

None. Both directions ran live against the project's `.venv/bin/python`
and passed:
- `rust_writes_python_reads` ... ok
- `python_writes_rust_reads` ... ok

If a future CI runner lacks the Python `voss` package, the tests will
print `skipping ...: python failed: ...` and return without panicking.
This keeps the workspace test suite green on machines without the venv
while still failing loudly when the venv is present but parity drifts.

## Creds-leak prevention

`SessionRecord` has zero fields named `access_token`, `refresh_token`,
or `api_key`, and the verify step
(`grep -E 'access_token|refresh_token|api_key' crates/voss-cli/src/session.rs`)
returns no matches. Provider creds live exclusively in `voss-auth` and
are never threaded into the session-record path.

## Test inventory (R6)

- `crates/voss-cli/tests/session_parity.rs` — 2 cases
  (Rust→Python, Python→Rust).
- `crates/voss-cli/tests/sessions_cli.rs` — 4 cases (empty listing,
  populated listing, resume by id prefix, resume by name, resume
  unknown errors).

R6 total: 6 new tests, all passing. Workspace remains green.

## Verification

```
cargo test -p voss-cli --no-fail-fast
XDG_STATE_HOME=$(mktemp -d) cargo run -p voss-cli -- sessions    # "(no sessions)"
cargo run -p voss-cli -- resume nope ; echo $?    # 1, "resume failed: no session: nope"
grep -rE 'access_token|refresh_token|api_key' crates/voss-cli/src/session.rs    # no matches
```
