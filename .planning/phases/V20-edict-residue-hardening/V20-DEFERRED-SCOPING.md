# V20 Deferred — Scoping Stubs (no plans; operator promotes individually)

Each item below was confirmed real during the V20 audit but is NOT in V20 scope. One
paragraph each. Promote with its own phase (`/gsd-phase add`) when picked.

## D1 — Mid-task 429 failover on the DEFAULT path (the real model gap)
`FallbackProvider` exists and is sound (voss_runtime/providers/fallback.py:43 — candidate
chain, retryable-marker detection, backoff) but the OAuth subscription providers that are the
de-facto default (`--auth=claude`, `--auth=codex`) are never wrapped by it, and on HTTP ≥400
they raise bare `RuntimeError` (voss/harness/providers.py:280-290, :648-658) rather than a
typed `ProviderError` — so even if a cascade wrapped them, it couldn't distinguish retryable
429/overload from fatal auth failure. Scope: (a) typed error taxonomy on both OAuth providers
(status, retry-after, retryable flag); (b) wrap default auth resolution in FallbackProvider
with a real candidate list (e.g. claude-sub → codex-sub → API-key); (c) extend failover
triggers beyond status codes to empty-output, hung-stream (no token for N s), and mid-stream
disconnect — chain-not-pool today, and mid-stream is currently unrecoverable. Likely touches
auth resolution, both provider classes, fallback.py, and agent stream loop; medium-large
phase, needs fault-injection tests.

## D2 — Board/EM crash-recovery rehydrate
The session-tree spine is write-only for live runs: `team_run` always
`SessionTreeNode.create_root` fresh (voss/harness/cli.py:4421) and `Board._cards` is never
rebuilt from persisted nodes, even though `audit/load.py:276` (`load_audit_snapshot`) already
reads every node JSON back into typed records. A crashed EM run is money spent with zero
resumability. Scope: a `--resume <run_id>` path on team_run that loads the audit snapshot,
reconstructs Board cards/tickets/columns + budget ledgers from deltas, and restarts the EM
loop from the surviving state; needs invariants for half-dispatched cards (in-flight subagent
at crash → route to retry or Blocked) and a rehydrate-equivalence test (snapshot of rebuilt
board == snapshot pre-crash). Read machinery exists; this is mostly state reconstruction +
edge semantics.

## D3 — Coordination bus (claims = lock half is built; bus half unbuilt)
claims.py ships TTL scope locks, but the V17 coordination-surface spec's bus verbs —
send/inbox/wait + `coord:*` labels — are specced and unbuilt, and even the existing
claims/bus click groups aren't fully wired into the harness CLI. Workers can avoid collisions
(claims) and, after V20-03, see siblings at dispatch — but they still cannot hand work to each
other mid-flight. Scope: per the V17 SPEC (plans 05/06, currently V15-gated per project
memory): sqlite-backed message rows next to the claims DB, blocking `wait` with timeout, CLI
verbs, and un-xfail of the existing bus tests + contract/SDK regen when it lands. Promote only
when a concrete multi-worker workflow needs handoff, not before.

## D4 — Gate-before-spend in EM loop
`em_loop` calls `em_agent.plan(...)` every iteration unconditionally (voss/harness/em/
loop.py:115-120) even when board state admits only `NoopOp` (all cards terminal-or-blocked,
WIP-capped, or pending-human after V20-04), and `tick.py:54` sleeps a fixed interval with no
idle backoff — so a stalled board burns model calls at full cadence. Scope: a pure
`legal_ops(snapshot)` precheck that short-circuits the plan call when only Noop is legal
(log a skipped-iteration marker for audit), plus exponential idle backoff on consecutive
no-op ticks with reset on any board delta. Small phase; main risk is liveness (must wake
promptly on human approval or budget refill — tie backoff reset to delta/event, not time).

## D5 — PTY stuck-detection + health badges
Fully absent: nothing watches a worker PTY/stream for silence, loops, or runaway output —
the only safety net is the budget viable-floor, which catches stuck agents late (after the
budget drains) and reports nothing about WHY. Scope: per-agent liveness heartbeat (last
token/tool-call timestamp), simple stuck classifiers (no output for N s; same tool+args ≥k
times; output rate explosion), a `health` field surfaced on session-tree nodes + board
snapshot (badge in TUI/voss-app later), and a policy hook (warn → soft-interrupt → kill+route
Blocked) that respects the existing kill/Blocked routing. Pairs naturally with D1's
hung-stream trigger; if D1 is promoted first, build the detection primitive there and only
the surfacing here.
