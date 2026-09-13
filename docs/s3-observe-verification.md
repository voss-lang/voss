# S3 Observe capture verification

Date: 2026-09-12. Branch: `s3-canvas-observe`, working-tree changes over
`391ae2d8`. Scope: S3 and repairs needed to run its S0–S2 prerequisites.

S3 implementation is wired through shell hooks, PTY reader, desktop transport,
authenticated sidecar, local Observe store, and BOS ledger. Focused checks pass.
This is not a claim that the entire repository or native desktop release is green.

## Changes

- New supported shell panes source hooks when shell integration is enabled.
  Bash/Zsh/Fish snippets generate UUID4 metadata with stdlib JSON encoding.
  Re-sourcing is idempotent; Bash preserves exit status before prompt commands.
- The reader retains OSC markers split across reads, with a bounded incomplete
  marker buffer and the existing 192 KiB head / 64 KiB tail evidence cap.
- Desktop retries preserve event IDs, retry without another command, recover
  after enrollment, and retain the correct survivors when an in-flight item drops.
- Canonical Git discovery serves both desktop identity and ingestion scope checks.
  Ingestion computes repository state, enforces repository policy, redacts argv
  and evidence, applies output limits, and atomically persists evidence/admission.
- BOS delivery runs after ingestion, retries periodically, and recovers on startup.
  Observe events validate against the shared BOS envelope schema. Settings reject
  invalid partial updates without corrupting enrollment.

The starting revision had removed prerequisite imports/helpers and restored the
retired grid app over the canvas host. Necessary desktop, Tauri, harness, and test
code was recovered from `8437006c`; this accounts for much of the diff. The SDK
was regenerated from the current contract and its exhaustive event check updated.
No dependencies were added. No Git write actions were performed.

## Acceptance evidence

| Criterion | Evidence |
|---|---|
| AC-S3-1: failed test capture and causality | Real interactive Bash/Zsh hook tests capture `pnpm test`, cwd, UUID4, output, and exit 1. Rust lifecycle/wire tests check reader events. Desktop client tests check envelope/evidence forwarding. Route tests check one completed event, one derived `test.failed`, and `caused_by`. These are layered checks, not a native desktop end-to-end walkthrough. |
| AC-S3-2: cooldown | Admission and route tests check repeated failure suppression and both admission decisions. Route regression proves code changes break cooldown while BOS writes do not. |
| AC-S3-3: duplicate event | Route tests check duplicate rows and immutable evidence; client regression proves a lost-response retry uses the same event ID. |
| AC-S3-4: expected nonzero | Admission tests check grep exit 1 is record-only; route regression checks grep exit 2 still queues a failure. |
| AC-S3-5: bounded evidence | Rust tracker tests check head/tail truncation. Route test submits 1 MiB and checks stored 256 KiB head/tail bytes and truncated flag, plus a smaller repository cap. |
| AC-S3-6: shell edge cases | Interactive Bash/Zsh tests cover pipelines, background launch, and nested shells. Behavior and Bash history limitation are documented in `shell-integration.md`. Fish runtime cases skip because Fish is unavailable. |
| AC-S3-7: sidecar outage | Client tests check queue cap 200, oldest drops, recovery order, no rejected caller, automatic retry, and in-flight eviction. StatusBar tests check dropped counts. Rust spawn test checks shell integration opt-in. |
| AC-S3-8: enrollment | Route test rejects unenrolled repositories without stored rows; CLI tests check enrollment/status. Client regression proves enrollment after rejection resumes capture. |
| AC-S3-9: redaction | Route tests inspect persisted evidence bytes and argv; redaction unit tests cover assignment and URL patterns. |
| AC-S3-10: SSE replay | Route tests stream 1,000 events in sequence and reconnect without gaps or duplicates, including Last-Event-ID support. |

Additional regressions cover subdirectory/symlink identity, linked-worktree identity
helpers, forged scope, path/command policy, repository-ID traversal, server ingest
time, live delivery failure followed by startup recovery, and zero provider imports
in the Observe package.

## Checks run

| Check | Result |
|---|---|
| Focused Python command below | 196 passed, 4 skipped (Fish runtime), 0 failures/errors |
| Principles/session-redaction guards | 13 passed |
| Desktop `pnpm test` | 876 passed, 5 skipped |
| Desktop `pnpm build` and `pnpm check:xterm-pin` | Passed; xterm 5.5.0 |
| `cargo test -p voss-app-core` (crate now archived under `archive/voss-ade/`) | 182 passed; isolated shell-spawn child check also passed |
| `cargo check -p voss-app` | Passed |
| Browser Playwright suite on port 5189 | 24 passed, 39 native-only checks skipped |
| `.venv/bin/python scripts/check_contracts.py` | Passed |
| SDK `pnpm run typecheck` | Passed |
| SDK `PYTHON_BIN=/Users/benjaminmarks/Projects/Voss/.venv/bin/python pnpm test` | 8 passed |
| `git diff --check` | Passed |

Focused Python command, run from repository root:

```sh
.venv/bin/python -m pytest \
  tests/harness/observe \
  tests/harness/server/test_observe_routes.py \
  tests/harness/test_observe_cli.py \
  tests/harness/test_shell_init_capture.py \
  tests/harness/test_permissions_observe.py \
  tests/harness/test_observe_mode_run.py \
  tests/harness/test_instructions.py \
  tests/harness/test_instructions_injection.py \
  tests/harness/test_instructions_cli.py \
  tests/harness/test_bos_event_projection.py \
  tests/harness/test_bos_event_ledger.py

.venv/bin/python -m pytest \
  tests/harness/test_principles_guard.py \
  tests/harness/test_session_redaction.py
```

Browser checks used a dedicated Vite server, because port 5173 was occupied:

```sh
# From archive/voss-ade/apps/voss-app (frozen), separate terminals:
pnpm exec vite --host 127.0.0.1 --port 5189
VOSS_APP_URL=http://127.0.0.1:5189 pnpm exec playwright test
```

## Remaining verification limits

- Fish snippets are generated and checked, but the four interactive Fish cases
  were skipped. Run `tests/harness/test_shell_init_capture.py` where Fish is installed.
- Native desktop manual verification was not performed. Run the shell walkthrough
  in a real Voss pane to certify the complete native path; browser checks cannot
  substitute for Tauri/PTY runtime checks.
- SDK integration tests must use the project Python environment. The initial run
  used system Python and failed server startup; rerunning with `PYTHON_BIN` set to
  `.venv/bin/python` passed all eight tests.
- The broad `tests/harness` run collected 2,516 tests and recorded 374 failures,
  11 errors, and 15 skips. It started before the final guard/doc corrections;
  those 13 guard tests subsequently passed. Remaining failures span file tools,
  ambient shell, memory, MCP, and TUI. Their baseline attribution was not established.
  Full harness success is not claimed, and these failures need a separate audit.
- Capture queues are in memory and per pane; closing a pane discards queued events.
  Persistence across restarts belongs to S9. Repository state reflects ingestion
  time when an offline event is delivered. No S4–S9 completion is implied.

Local evidence: `/tmp/voss-s3-py.xml`, `/tmp/voss-s3-guards.xml`,
`/tmp/voss-s3-harness-final.xml`, `/tmp/voss-s3-vitest.log`,
`/tmp/voss-s3-build.log`, `/tmp/voss-s3-rust-all.log`,
`/tmp/voss-s3-tauri.log`, `/tmp/voss-s3-sdk.log`, and `/tmp/voss-s3-e2e-all.log`.
