# Phase O6 Validation Map

**Phase:** O6 Audit Product + Calibration + Liveness Hardening
**Date:** 2026-05-20
**Basis:** Derived `OAUD-01..08` requirements from roadmap/context because `O6-SPEC.md` does not exist.

## Requirement to Test Map

| Req | Validation | Test / Gate | Plan |
|---|---|---|---|
| OAUD-01 | O6 refuses to run against missing O1-O5 audit interfaces and reports exact missing surfaces. | `pytest tests/harness/audit/test_preflight.py -q` | O6-01 |
| OAUD-02 | Loader hydrates audit snapshots read-only from session-tree fixtures and does not add fields to `SessionRecord` / `RunRecord`. | `pytest tests/harness/audit/test_snapshot_loader.py -q`; redaction regression | O6-02 |
| OAUD-03 | Markdown + JSON review exports include tree lineage, killed cards, rescopes, routing rationale, reviewer outcomes, and liveness summary. | `pytest tests/harness/audit/test_report_export.py -q` | O6-03 |
| OAUD-04 | Approval is unavailable until killed-card, routing/misroute, calibration, liveness, and Leak-6 acknowledgements are present. | `pytest tests/harness/audit/test_signoff_gate.py -q` | O6-05 |
| OAUD-05 | Calibration metrics count A/B agreement, disagreement, slop rejection, B-block-after-A-pass, and deterministic spot-audit samples. | `pytest tests/harness/audit/test_calibration.py -q` | O6-04 |
| OAUD-06 | Liveness metrics flag reserve exhaustion, timeout-to-Blocked transitions, open nodes, and terminal completeness. | `pytest tests/harness/audit/test_liveness.py -q` | O6-04 |
| OAUD-07 | Leak-6 is either mitigated by an implemented assessment or recorded as an accepted gap requiring sign-off acknowledgement. | `pytest tests/harness/audit/test_leak6.py -q` | O6-06 |
| OAUD-08 | End-to-end fixture covers killed card, rescope, misroute, reviewer disagreement, timeout, and Leak-6 path. | `pytest tests/harness/audit/test_o6_acceptance.py -q` | O6-06 |

## Global Gates

- `python -m pytest tests/harness/audit/ -q`
- `python -m pytest tests/harness/test_session_redaction.py -q`
- `python -m pytest tests/harness/test_session_tree.py -q`
- `python -m compileall voss/harness/audit`
- `git diff --check`

## Nyquist Coverage Notes

- Failure surfaces are explicit: missing O1-O5 interfaces, malformed node JSON, missing acknowledgement buckets, non-terminal nodes, and Leak-6 accepted gap.
- Integration coverage is fixture-driven because live O3-O5 modules may not exist until preceding phases execute.
- Human review UX is validated through exported artifact content and sign-off gate behavior, not through a TUI visual test.
