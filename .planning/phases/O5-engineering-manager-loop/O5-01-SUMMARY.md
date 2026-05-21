---
phase: O5-engineering-manager-loop
plan: 01
status: complete
completed_at: 2026-05-20
commits: []
depends_on: [O5-00]
requirements: [OEM-01, OEM-07, OEM-10]
---

# O5-01 Summary — EM Data Model (Wave 1)

## Objective

Land the foundational EM data model: 5 frozen-slots dataclasses (Ticket, KillRecord, RescopeRecord, RoutingRationale, RunFinal), the typed EMCageViolation exception, the `voss/harness/em/` package skeleton, and the additive `"killed"` extension to `EXIT_REASONS`.

## Files changed

- `voss/harness/em/__init__.py` -- **new**: package docstring + re-exports of all 5 records + EMCageViolation via `__all__`.
- `voss/harness/em/tickets.py` -- **new** (131 lines): 5 frozen-slots dataclasses with `kind: Literal["em.*"]` discriminators and `__post_init__` validators (confidence_hint range, self-parented kill, self-rescope, non-negative counts).
- `voss/harness/em/errors.py` -- **new** (21 lines): `EMCageViolation(Exception)` with structured `.op` and `.reason` attributes.
- `voss/harness/session.py` -- `EXIT_REASONS` extended additively with `"killed"` (7 members total: done, max-iter, budget, interrupt, batch-invariant, timeout, killed).
- `tests/harness/em/__init__.py` -- **new**: package marker.
- `tests/harness/em/test_em_tickets.py` -- **new** (10 tests): Ticket + RoutingRationale construction, frozen-mutation refusal, L-02 kind check, L-03 L2-vocab scan, confidence_hint range guard.
- `tests/harness/em/test_em_lineage.py` -- **new** (10 tests): KillRecord, RescopeRecord, RunFinal construction; bidirectional pointers; L-04 append-not-delete; counts-non-negative guard.
- `tests/harness/em/test_em_exit_reasons.py` -- **new** (4 tests): "killed" membership; existing 5 members retained; RunRecord construction with exit_reason="killed" succeeds; frozenset type preserved.

## Test counts

| File | Tests |
|------|-------|
| `test_em_tickets.py` | 10 |
| `test_em_lineage.py` | 10 |
| `test_em_exit_reasons.py` | 4 |
| **Total (new)** | **24** |

## Key facts

- **tickets.py import set:** `typing` + `dataclasses` only -- mirrors O3 verdict.py zero-deps discipline. No transitive harness imports.
- **kind discriminator (L-02):** Each record carries `kind: Literal["em.<type>"]` with a runtime `__post_init__` assert as defense-in-depth. Tests reject `kind="board.*"`.
- **L-03 scan:** Tests build one of each record with realistic copy and scan every `str` field value for banned substrings (model/cost/token/provider). Zero hits.
- **L-04 append-not-delete:** Tests construct KillRecord + RescopeRecord referencing a Ticket and assert the original Ticket value is unchanged post-construction (frozen records are pure appends, never in-place mutation).
- **EXIT_REASONS:** Now `frozenset({"done", "max-iter", "budget", "interrupt", "batch-invariant", "timeout", "killed"})` -- both O3's "timeout" and O5's "killed" landed additively.
- **RescopeRecord bidirectional pointers:** `predecessor_card_id` on the rescope + `successor_card_id` on the kill allow O(1) lineage traversal in either direction.

## Deviations from plan

- **Test count higher than plan implied:** Plan described 3 test files with broad behavior lists; execution expanded to 24 tests by splitting each assertion into its own test function.
- **EXIT_REASONS includes "timeout":** Plan expected "timeout" was not yet present (O3's responsibility). By execution time, O3-01 had already shipped "timeout" additively. The extension is still additive and non-conflicting.

## Unchanged

- `tests/harness/test_session_redaction.py` -- unmodified; still passes (proves the EXIT_REASONS extension is truly additive).

## Next

W2 lands EMBoardHandle -- the cage-bounded facade with 11 legal verbs.
