---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 06
type: execute
status: complete
wave: 4
---

# V9-06 Summary — Sign-off Forcing Function

## Outcome

`team_run_cmd` gates approve behind a forced killed/misroute acknowledgement
recorded in a new `.signoff-ack.json`; `voss audit --approve` reads the ack back
and refuses when risks are unacknowledged. `test_signoff_forcing.py` GREEN.
**Full V9 audit suite: 78 passed, 0 RED.**

## Changes (`voss/harness/cli.py`)

- `_write_signoff_ack(cwd, root_id, *, killed_count, misroute_count) -> Path` —
  writes `{ack_ts, killed_count, misroute_count}` to a NEW
  `.voss/sessions/<root_id>/.signoff-ack.json` (0o600, mkdir+write+chmod
  mirroring `_persist_run_final`). root_id only from `rf.root_id` (no traversal).
- `_enforce_signoff_ack(cwd, root_id, *, killed_count, misroute_count)` —
  extracted gate: clean run (0/0) returns immediately (Pitfall 5); else displays
  the risk diff, prompts; non-"yes" → `Exit(1)` "acknowledgement required";
  "yes" → writes the ack.
- `team_run_cmd` — before the approve/reject prompt, computes `killed_count =
  rf.killed_count` and `misroute_count` from
  `load_audit_snapshot(cwd, run_id=rf.root_id).routings` (count
  `confidence_hint < 0.7`), then calls `_enforce_signoff_ack`. Existing
  approve/reject + `_persist_run_final` flow intact.
- `audit_cmd --approve` — reads `report.signoff_ack`; risks = kills present OR a
  routing `confidence_hint < 0.7`; risks AND no ack → stderr + `SystemExit(1)`;
  else "approve: permitted". Default (no `--approve`) render path unchanged.

## `voss/harness/audit/load.py` — third glob-landmine filter

`.signoff-ack.json` matches `*.json` and was read as a node (`AuditLoadError:
missing required 'id'`). Added it to the node-glob exclusion set alongside
`run-final.json` and `*.review.json`. Surfaced by the new audit `--approve`
readback test, which writes the ack then loads.

## Deviation: ack-gate test refactored to a testable surface

My V9-01 `test_approve_refused_without_ack` drove the gate through `team_run_cmd`
with simulated "no" input — but the deterministic `team run` produces a CLEAN
run (`killed=0`, card blocked-not-killed, no misroutes), so the gate correctly
SKIPS (Pitfall 5) and the risk path is never exercised. The honest testable
surface is the gate logic, so I extracted `_enforce_signoff_ack` and the tests
now cover, via a minimal click harness:
- refusal: risks + "no" → exit≠0, "acknowledg", approve never reached;
- accept: risks + "yes" → ack sidecar written (0o600), proceeds;
- clean: 0/0 → no prompt, falls through (Pitfall 5).
Plus audit-side readback tests (`--approve` refused without ack on the
killed-card fixture; permitted once the ack exists). This is the
gsd-scaffold-fictional-api correction: a Wave-0 scaffold pinned to an
unverifiable path, realigned to the real surface. No xfail.

## Verification

- `pytest tests/harness/audit/test_signoff_forcing.py tests/harness/audit/test_audit_cli.py` — green.
- `pytest tests/harness/audit/` — **78 passed, 0 failed** (entire V9 surface).
- `.signoff-ack.json` write touches neither run-final.json nor node JSONs (ack-is-new-file test).
- `voss.harness.cli` imports clean.

## Pre-existing unrelated failures (NOT V9)

Broader `tests/harness/` shows 7 failures untouched by V9: exit-reason constant
drift (`test_session_iterations`, `test_t1_acceptance` — present at pre-V9 HEAD
`804387e`), M10 project-index (`test_repl_slash`), and streaming/memory/dog07
integration tests. None import the audit surface; cli imports clean.

## Phase status

V9-01..V9-06 complete; the full VAUD requirement set (01/02/03/04/05/06/07/08/10/
SIGNOFF/CAL) is GREEN. V9-07 (frozen-schema / runtime-surface drift gate) remains
per the threat model (T-V9-06-02 references it).
