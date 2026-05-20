# Phase O6 Patterns

**Phase:** O6 Audit Product + Calibration + Liveness Hardening
**Date:** 2026-05-20

## Pattern 1: Audit Snapshot Is O6-owned

Create O6 dataclasses under `voss/harness/audit/` instead of extending session schemas.

Recommended files:

- `voss/harness/audit/model.py`
- `voss/harness/audit/load.py`
- `voss/harness/audit/report.py`
- `voss/harness/audit/metrics.py`
- `voss/harness/audit/signoff.py`
- `voss/harness/audit/leak6.py`

The loader may read session-tree node files and O3-O5 event payloads, but it returns O6-owned `AuditSnapshot` data. It must not mutate `.voss/sessions/`.

## Pattern 2: Preflight Before Implementation

O6 depends on O1-O5. Start execution by checking the exact imports/fields that O6 consumes. If missing, stop with a blocking summary instead of adding compatibility code into O6.

Minimum expected surfaces:

- `voss.harness.session_tree.SessionTreeNode`
- O3 board transition / timeout data on session-tree nodes or equivalent persisted event payloads.
- O4 Reviewer-A verification and Reviewer-B verdict records.
- O5 routing rationale, kill record, rescope record, and run-final metadata.

## Pattern 3: Export First, UI Later

Use Markdown + JSON as the first human review product.

- Markdown is the human artifact.
- JSON is the machine-verifiable artifact and future UI input.
- TUI/ADE rendering can consume the same JSON later, but O6 acceptance should not depend on a live UI shell.

## Pattern 4: Acknowledgement Buckets

Represent sign-off as named buckets:

- `killed_cards`
- `routing_misroutes`
- `calibration`
- `liveness`
- `leak6`

Approval is allowed only when all required buckets are acknowledged for the current audit snapshot digest.

## Pattern 5: Deterministic Sampling

Human spot-audit sampling should be deterministic in tests and stable in real reports. Prefer sorted candidate ids and a deterministic seed from `root_id` over global randomness.

## Pattern 6: Severity Labels Are Operational

Use a small enum or literal set for audit severity:

- `ok`
- `warning`
- `blocked`
- `accepted_gap`

Avoid inventing a second workflow state machine. O3 owns board state; O6 reports audit status.

## Pattern 7: Leak-6 Closure Is a First-class Section

The Leak-6 assessment must appear even when no mitigation is implemented. If accepted, include:

- residual id: `Leak-6`
- status: `accepted_gap`
- evidence: why runtime mitigation was out of scope or no writer exists yet
- required acknowledgement bucket: `leak6`

## Pattern 8: Keep CLI Thin

If a CLI command is added, make it a thin wrapper over pure functions:

- load snapshot
- compute metrics
- render report
- evaluate sign-off gate
- optionally persist sign-off

Do not bury audit logic in `voss/harness/cli.py`.
