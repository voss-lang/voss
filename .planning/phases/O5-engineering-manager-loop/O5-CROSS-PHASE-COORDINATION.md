# O5 Cross-Phase Coordination

Three coordination asks surfaced during O5 planning + execution. Each
is an actionable item for the downstream planner to resolve.

---

## C-01: Reviewer Protocol Signature

**Background:** O3-SPEC §7 locks `Reviewer.review(card: object) -> ReviewerVerdict`.
O4-01 Gate 3 found Card lacks original_idea / domain / artifact_path /
artifact_text / file_diff / a_verification_summary. O5 introduced `Ticket`
to wrap Card + EM-authored scaffolding.

**Ask:** O4 reviewers should accept a richer context object (the card-shaped
duck-typed object can carry Ticket fields). The `card: object` typing in
verdict.py already allows this — O4 implementations pass Ticket or a
SimpleNamespace with the required fields.

**Resolution path:** O4 already resolved this via duck-typing (O4-01 preflight
documented the finding; O4-02/O4-03 pass rich card-shaped objects to review()).
No O3 SPEC amendment needed — `card: object` is intentionally loose.

**Status:** RESOLVED (O4 shipped using duck-typed objects)

---

## C-02: ReviewerVerdict.domain_inferred Field

**Background:** OEM-09 misroute audit needs Reviewer-B's claimed domain to
diff against Ticket.worker_role. Without `domain_inferred`, the fallback
is regex on ReviewerVerdict.notes (worse fidelity).

**Ask:** O4 adds `domain_inferred: Optional[Literal["code","ai"]] = None`
to ReviewerVerdict (additive Optional field with None default — backwards
compatible).

**Resolution path:** O4 implementer adds the field to verdict.py; the O5
integration test `test_em_misroute_audit.py::test_misroute_diff_requires_domain_inferred`
uses `xfail(strict=True)` — when the field lands, the test flips to XPASS
and CI flags the coordination as resolved.

**Status:** OPEN — waiting on O4 amendment (or deferred to O6 if O4 ships
without the field; O6 falls back to notes-regex).

---

## C-03: EXIT_REASONS Additive Ordering

**Background:** O3 added `"timeout"` to EXIT_REASONS (O3-01). O5 added
`"killed"` (O5-01). Both additive; frozenset members are commutative.

**Ask:** No conflict. Both extensions landed via the same playbook:
one-line frozenset literal edit + inline comment citing the phase.

**Resolution path:** Already resolved. EXIT_REASONS now contains both
`"timeout"` and `"killed"`. No rebase needed.

**Status:** RESOLVED
