# Phase 7 Validation Architecture

**Status:** Documentation deliverable for Phase 7 (rust-port). Closes WARNING 5
(`nyquist_compliance`). This document is not a plan — it sits adjacent to
`07-01-PLAN.md` … `07-09-PLAN.md` and explains *which* test layer covers
*which* RUST-NN requirement, how CI is wired, and how Python ↔ Rust parity is
maintained.

Read order:
1. `07-PHASE.md` — phase intent + cross-cutting constraints.
2. `07-CONTEXT.md` — locked decisions D-01 … D-15.
3. This file — validation architecture and the test-parity table.
4. The individual `07-NN-PLAN.md` files — implementation tasks.

---

## 1. Validation Architecture

Each `RUST-NN` requirement in `ROADMAP.md` is owned by exactly one test layer.
A requirement is "validated" when its owning test passes and is wired into the
default `cargo test` matrix (or the documented opt-in matrix). No requirement
is allowed to ship without an owning test.

### 1.1 Layer map

| Layer | Where it lives | What it covers | When it runs |
|-------|----------------|----------------|--------------|
| **L0 — unit (Rust)** | `crates/<crate>/src/**` `#[test]` blocks | Pure functions, formatters, parsers, encoders. Fast, no I/O. | Every `cargo test` run. |
| **L1 — crate integration (Rust)** | `crates/<crate>/tests/*.rs` | One crate's public API end-to-end (e.g. `voss-providers/tests/anthropic_request_snapshot.rs`). May use `wiremock`, `tempfile`, `assert_cmd`. No real network. | Every `cargo test` run. |
| **L2 — workspace integration (Rust)** | `crates/voss-cli/tests/*.rs`, `crates/voss-agent/tests/*.rs` | Cross-crate flows: REPL, run_turn end-to-end with mocked provider, `voss-cli --help`, framing+round-trip across `voss-bridge`. | Every `cargo test` run. |
| **L3 — schema parity gate** | `crates/voss-providers/tests/schema_parity.rs`, `crates/voss-tools/tests/schema_parity.rs` | Compares `schemars`-derived Rust schemas against `pydantic`-derived Python schemas (via `scripts/dump_python_*_schema.py`). Skips with a printed notice if `python3` cannot import the `voss` package. | Every `cargo test` run **on CI** (where `python3 -m voss` is importable). Skipped on contributor laptops without the editable install. |
| **L4 — Python harness (parity reference)** | `tests/harness/*.py` (already exists) | The Python harness still ships in v1.2 alongside the Rust binary. Its `pytest` suite is the parity ground truth. | `pytest tests/harness -x` on CI. |
| **L5 — live smoke (opt-in)** | `crates/voss-providers/tests/live_anthropic.rs`, `crates/voss-providers/tests/live_openai_codex.rs` (R8) | Real network call against Anthropic / Codex using developer credentials. **Always early-returns** unless `VOSS_LIVE_SMOKES=1` is set. | Manual / nightly only — never on PR CI. |
| **L6 — perf gate (opt-in soft, hard cap firm)** | `crates/voss-cli/tests/version_perf.rs` | `voss-cli --version` cold-start budget. Hard cap = 5× target (250ms); above the 50ms target prints a `WARN:` but does not fail. | Every `cargo test --release` run on CI; the WARN line is grepped in the release job. |

### 1.2 Coverage table — which layer owns which RUST-NN

The plan numbers in column 4 are the wave that creates the tests. Many tests
also belong to a wave that *uses* them; that's expected — schema gates are
created in R3/R4 and re-asserted in R7/R8.

| RUST-NN | Description (abbrev.) | Owning layer | Owning plan(s) | Test artifact |
|---------|----------------------|--------------|-----------------|---------------|
| RUST-01 | Cargo workspace builds clean | L1 | 07-01 | `cargo build --workspace` in `.github/workflows/rust.yml` |
| RUST-02 | LSP framing parser/writer | L0 + L1 | 07-01 | `crates/voss-bridge/tests/framing.rs` |
| RUST-03 | bridge round-trip via spawned Python | L2 | 07-01 | `crates/voss-bridge/tests/round_trip.rs` |
| RUST-04 | `voss-cli ast` parity with Python | L2 | 07-01 | `crates/voss-cli/tests/repl_smoke.rs` (help-lists-ast) + manual ad-hoc parity |
| RUST-05 | macOS Keychain round-trip | L1 | 07-02 | `crates/voss-auth/tests/keychain_round_trip.rs` (gated `#[cfg(target_os="macos")]`) |
| RUST-06 | Linux file-store round-trip | L1 | 07-02 | `crates/voss-auth/tests/file_round_trip.rs` |
| RUST-07 | refresh_anthropic + refresh_codex | L1 | 07-02 | `crates/voss-auth/tests/refresh.rs` (wiremock) |
| RUST-08 | doctor parity with Python | L2 | 07-02 | `crates/voss-cli/tests/doctor_parity.rs` (compares stdout to `python -m voss doctor`) |
| RUST-09 | ModelProvider trait + Plan struct | L0 | 07-03 | `cargo build -p voss-providers -p voss-agent` + schema_parity (L3) |
| RUST-10 | AnthropicOAuthProvider preamble + tool-use | L1 | 07-03 | `crates/voss-providers/tests/anthropic_request_snapshot.rs` (insta snapshot) |
| RUST-11 | refresh-on-401 retry | L1 | 07-03 | `crates/voss-providers/tests/anthropic_refresh_on_401.rs` (wiremock, asserts counter == 2) |
| RUST-12 | schema parity Python ↔ Rust (Plan + ToolCall) | L3 | 07-03 | `crates/voss-providers/tests/schema_parity.rs` |
| RUST-13 | sandbox jail + shell allowlist | L1 | 07-04 | `crates/voss-tools/tests/sandbox.rs` |
| RUST-14 | 9 tools with `is_mutating` flag | L1 | 07-04 | `crates/voss-tools/tests/fs_tools.rs`, `crates/voss-tools/tests/shell_tools.rs` |
| RUST-15 | tool schema parity Python ↔ Rust | L3 | 07-04 | `crates/voss-tools/tests/schema_parity.rs` |
| RUST-16 | sandbox allowlist persistence | L1 | 07-04 | `crates/voss-tools/tests/sandbox.rs` (round-trip via tempdir + XDG override) |
| RUST-17..23 | Render + session + permissions (R5/R6) | L1 + L2 | 07-05, 07-06 | per-crate `tests/*.rs` |
| RUST-24 | run_turn parity with Python | L2 | 07-07 | `crates/voss-agent/tests/run_turn.rs::high_confidence_plan_executes_steps` |
| RUST-25 | confidence gate + clarify | L2 | 07-07 | `crates/voss-agent/tests/run_turn.rs::low_confidence_emits_clarify` |
| RUST-26 | parallel-by-default with `is_mutating` partitioning + concurrency cap + denied-step isolation (D-11..D-14) | L2 | 07-07 | `crates/voss-agent/tests/parallel_dispatch.rs` (≥5 cases) |
| RUST-27 | REPL + slash commands + status line (D-08) | L2 | 07-07 | `crates/voss-cli/tests/repl_smoke.rs`; `crates/voss-agent/tests/run_turn.rs::tty_mode_emits_status_once`; `…::json_mode_suppresses_status` |
| RUST-28..30 | Codex provider + REPL Codex auth path (R8) | L1 + L2 | 07-08 | `crates/voss-providers/tests/openai_codex_*.rs`, `crates/voss-cli/src/cli/auth_to_provider.rs` (extended Codex variants) |
| RUST-31 | cargo-dist + brew tap | L1 (config) + manual ship | 07-09 | `dist-workspace.toml` + `.github/workflows/release.yml` |
| RUST-32 | pip dispatcher D-04..D-07 + perf | L1 (Python) + L6 | 07-09 | `tests/test_dispatcher.py` (≥6 cases); `crates/voss-cli/tests/version_perf.rs` |

Cross-cutting invariants (not numbered RUST-NN but enforced):

| Invariant | Owning layer | Owning plan | Test artifact |
|-----------|--------------|-------------|---------------|
| voss-agent Cargo.toml has zero voss-cli dep (cycle prevention) | L1 grep gate | 07-07 | `! grep -q '^voss-cli' crates/voss-agent/Cargo.toml` in 07-07 task verifies |
| `PermissionCheck` lives in voss-agent | L0 | 07-07 | `grep -q 'pub trait PermissionCheck' crates/voss-agent/src/run_turn.rs` |
| `GateAdapter` lives in voss-cli/src/cli/repl.rs | L0 | 07-07 | `grep -q 'struct GateAdapter' crates/voss-cli/src/cli/repl.rs` |
| AGENT_VERBS is exactly `{do, chat, doctor, sessions, resume}` (no `tools`, no `config`) | L1 (Python) | 07-09 | `tests/test_dispatcher.py::test_agent_verbs_set_is_exactly_five` |

---

## 2. CI Matrix

Three jobs in `.github/workflows/rust.yml` (created in 07-01, extended in 07-09):

### 2.1 Job `rust-test` (default, blocks merge)

```
cargo build --workspace
cargo test --workspace --no-fail-fast
```

Runs L0, L1, L2 layers. Includes the **schema_parity** gate (L3) — passes
because the GH runner's checkout includes the Python `voss` package and an
editable install step (`pip install -e .[harness]`) precedes `cargo test`.

Live smokes (L5) are NOT executed: `VOSS_LIVE_SMOKES` is unset, and the test
bodies early-return.

### 2.2 Job `python-harness` (default, blocks merge)

```
pip install -e .[harness]
pytest tests/harness -x
```

Runs L4 (Python harness parity reference). Until the harness is removed
post-v1.2, this gate must stay green to ensure the Rust port hasn't introduced
behavior drift in the Python side.

### 2.3 Job `release-perf` (release builds only, soft warn + hard cap)

```
cargo build --release -p voss-cli
cargo test --release -p voss-cli --test version_perf
```

Runs L6. The test prints `WARN:` if `voss-cli --version` exceeds 50ms; the
release job greps for `WARN:` and surfaces it in the GH summary. The test
**fails** only above 250ms (5× hard cap).

### 2.4 Live smokes — nightly / manual only

A separate workflow (out of v1.2 scope unless trivially added) can run:

```
VOSS_LIVE_SMOKES=1 cargo test -p voss-providers --test live_anthropic
VOSS_LIVE_SMOKES=1 cargo test -p voss-providers --test live_openai_codex
```

This MUST NOT run on PR builds. See §3.

---

## 3. Live-Smoke Opt-In Policy

**Policy:** Live smokes against real provider APIs (Anthropic / OpenAI Codex)
are NEVER executed by default. They are gated behind:

1. **Env var:** `VOSS_LIVE_SMOKES=1`. Without it, every live test body
   returns early with a printed `skipping: set VOSS_LIVE_SMOKES=1 to run`
   notice.

2. **Credentials:** the test loads creds via the same `voss_auth::load_*`
   path the production binary uses. Missing creds → the test panics with a
   clear "run `claude login`" message; this is intentional, since the live
   harness must NEVER silently no-op when the env var is set.

3. **CI default:** the GitHub Actions `rust-test` job does not set
   `VOSS_LIVE_SMOKES`. Only a separate manually-triggered or scheduled
   nightly workflow may set it.

4. **Documentation:** once `CONTRIBUTING.md` exists (post-v1.2), it must
   document the env-var, the required credentials, and the explicit warning
   that live smokes consume real API quota.

5. **Determinism:** each live test makes a single, low-cost call (e.g. "what
   is 2+2?", `max_tokens=64`, `temperature=0.0`) so quota cost is bounded.

**Rationale:** PR CI must remain deterministic, free, and offline. Live
smokes catch wire-format regressions that `wiremock` snapshots cannot (e.g.
silent provider behavior changes), but they are confirmation tools, not gate
tools.

---

## 4. Python ↔ Rust Test Parity Table

Each Python harness test in `tests/harness/test_*.py` maps to a Rust
integration test (or a set of unit tests) that asserts the equivalent
behavior on the Rust side. The Python tests stay in tree until v1.2 ships —
they are the parity ground truth.

| Python test file | Python coverage | Rust equivalent | Owning plan |
|------------------|-----------------|-----------------|-------------|
| `tests/harness/test_auth.py` | macOS Keychain + Linux file store + refresh | `crates/voss-auth/tests/keychain_round_trip.rs` + `crates/voss-auth/tests/file_round_trip.rs` + `crates/voss-auth/tests/refresh.rs` | 07-02 |
| `tests/harness/test_oauth_provider.py` | Anthropic OAuth provider — preamble, tool-use, refresh-on-401 | `crates/voss-providers/tests/anthropic_request_snapshot.rs` + `crates/voss-providers/tests/anthropic_refresh_on_401.rs` | 07-03 |
| `tests/harness/test_openai_oauth.py` | OpenAI Codex OAuth provider | `crates/voss-providers/tests/openai_codex_*.rs` (created in 07-08) | 07-08 |
| `tests/harness/test_sandbox.py` | jail_path + shell_allowed + allowlist persistence | `crates/voss-tools/tests/sandbox.rs` | 07-04 |
| `tests/harness/test_tools.py` | All 9 tools, `is_mutating` flag, schema shape | `crates/voss-tools/tests/fs_tools.rs` + `crates/voss-tools/tests/shell_tools.rs` + `crates/voss-tools/tests/schema_parity.rs` | 07-04 |
| `tests/harness/test_session.py` | Session save / load / list | `crates/voss-cli/tests/session_*.rs` (R6) | 07-06 |
| `tests/harness/test_agent_integration.py` | run_turn end-to-end against canned provider | `crates/voss-agent/tests/run_turn.rs` (4 tests) + `crates/voss-agent/tests/parallel_dispatch.rs` (≥5 tests) | 07-07 |
| `tests/harness/test_cli.py` | Click `voss` CLI behavior | `crates/voss-cli/tests/repl_smoke.rs` + `crates/voss-cli/tests/doctor_parity.rs` | 07-02 + 07-07 |

**Parity verification recipe** (run locally before declaring a wave done):

```bash
# 1. Python side passes.
pytest tests/harness -x

# 2. Rust side passes.
cargo test --workspace --no-fail-fast

# 3. Schema parity gate (the only test that talks to both).
cargo test -p voss-providers --test schema_parity
cargo test -p voss-tools --test schema_parity

# 4. Spot-check `voss doctor` parity.
diff <(python -m voss doctor) <(cargo run -p voss-cli -- doctor)
```

Any divergence in step 3 or 4 is a parity violation and must block the wave.

---

## 5. Out-of-Scope (post-v1.2)

The following validation work is acknowledged but not in Phase 7:

- **Windows targets** — Phase 7 defers Windows. No CI matrix entry.
- **Property-based tests / fuzz** — sandbox `jail_path` would benefit from
  proptest, but v1.2 ships with example-based tests only.
- **Long-running soak / chaos** — no flakiness budget is enforced; CI re-runs
  on transient failure are acceptable for v1.2.
- **`tools` and `config` agent verbs** — explicitly NOT in v1.2 AGENT_VERBS;
  see 07-09 plan + `test_agent_verbs_set_is_exactly_five`.
- **`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` env-key paths in the chat REPL** —
  intentionally not wired in 07-07; the REPL exits 2 with a documented
  message pointing at later milestones (see 07-07 must_haves for exact
  behavior).
