# Phase V6: Reviewer A/B Split (supersedes O4) - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Source:** Direct synthesis from V6-SPEC.md (ambiguity 0.137; discuss-phase recommended answers applied — SPEC interview already locked direction). Decisions below resolve the three HOW questions the SPEC flagged for discuss-phase: review sidecar schema, Done-gate composition, review CLI layout.

<domain>
## Phase Boundary

Turn the **shipped O4 reviewers** (`voss/harness/board/reviewer_a.py`, `reviewer_b.py`, `verdict.py` — plans O4-01..04) into a coherent product flow. O4 already ships the reviewer *intelligence* (REV-01..05,07,08): A derives the bar from the original idea and authors+runs verification; B is an independent EM-narrative-blind tiered judge with Residual-2 block authority. V6 builds the four gaps and verifies the rest:

- **VREV-03/04/07 (board wiring)** — `Board` has a single `reviewer` slot; the Done gate must consume **two genuinely independent sources** (A's authored verification AND B's verdict).
- **VREV-06** — `ReviewerVerdict` lacks `domain_inferred`.
- **VREV-09** — A's verification + B's verdict are not durably persisted.
- **VREV-10** — no `voss review <run_id>` CLI.

V6 sits on the **V5 board** (`voss/harness/board/machine.py`, `gates.py`) and the **V4 session-tree keystone** (`voss/harness/session_tree.py`). It changes **no frozen record schema** and adds **no third-party deps**. Pure reviewer-wiring delta — no EM dispatch (V7), no ADE panel (V11), no calibration telemetry (V9).

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 requirements are locked** (delta on shipped O4). See `V6-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V6-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Wire both Reviewer-A + Reviewer-B into the board Done gate (two independent sources).
- `domain_inferred` on `ReviewerVerdict`.
- Persist A verification + B verdict under the card's session-tree node.
- `voss review <run_id>` read-only CLI.
- Verification/regression of shipped ReviewerA/B; mark O4 superseded.

**Out of scope (from SPEC.md):**
- ADE reviewer-verdict panel rendering — V11.
- Reviewer calibration telemetry + slop-rejection spot-audit — V9 / O6 residual register.
- EM routing / card creation — V7.
- Board state-machine changes beyond the reviewer wiring — V5.
- Any field change to `RunRecord`/`SessionRecord`/`voss_runtime.BudgetScope` — frozen.
- New third-party dependencies.

</spec_lock>

<decisions>
## Implementation Decisions

### Done-gate composition: two independent sources (VREV-03/04/07)
- **D-01:** `Board.__init__` / `Board.from_team_config` gain `reviewer_a` + `reviewer_b` parameters. Keep the legacy single `reviewer` parameter as an **optional back-compat alias** so existing O3/V5 construction and the `DeterministicReviewerStub` keep working (when only `reviewer` is passed, it satisfies both slots; tests that pass a stub stay green). New code passes A and B explicitly.
- **D-02:** A and B are **two separate gating sources at `InReview → Done`**, evaluated by **two distinct predicates** that each call their own reviewer once and cache to **separate** `GateContext` slots (`verdict_a`, `verdict_b`) — not the single shared `ctx.verdict`. A's predicate passes when A's **authored verification PASSES** (code: tests exit 0 → `verdict.verdict == "pass"`; AI: eval/judge ≥ threshold). B's predicate passes when **B's verdict == `pass`**. Both required; either failing refuses Done.
- **D-03:** **B `block` routes the card to Blocked**, not merely "refuse Done". The gate detects a B `block` verdict (Residual-2: A-verification diverges from the idea, or parse-fail fail-safe) and drives the card to **Blocked** via the existing terminal path (`_force_terminal` / `critic_step` block→terminal mapping already exists in `machine.py`). A plain A-fail or B-`fail` follows the existing critic-loop retry path; only `block` is terminal-at-gate.
- **D-04:** **B stays EM-narrative-blind** — verify-only, do not weaken `reviewer_b.py`'s structural 2-message isolation. A's context continues to exclude EM AC/DoD. A and B see **different context packets** (regression-protected).
- **D-05:** Reuse the existing `gates.py` predicate registry shape (`Gates.build_default`, the AI-vs-code Done swap by artifact introspection). The new A/B predicates extend the `("InReview","Done")` tuple; existing `scope_clean`/`conf`/`tests`/`eval` predicates are reused for A's verification arm.

### `ReviewerVerdict.domain_inferred` (VREV-06)
- **D-06:** Add `domain_inferred: Literal["code","ai","docs","unknown"] = "unknown"` as a **7th, defaulted field** on the board-local `ReviewerVerdict` (`verdict.py`). Defaulted ⇒ **additive**: all existing positional/keyword constructions in `reviewer_a.py`, `reviewer_b.py`, `stub.py`, and tests keep working unchanged.
- **D-07:** **B populates** it (extend `_ReviewerBOutput` + `_to_verdict` to carry the LLM-inferred domain, clamped to the allowed set; unknown/garbage → `"unknown"`). **A defaults** it (may map its known `card.domain` → `"code"`/`"ai"` when trivially available, else `"unknown"`).
- **D-08:** Preserve `verdict.py`'s **zero-transitive-harness-import contract** (the module may import only `typing`/`dataclasses`/`__future__`). `Literal` is already imported — no new imports. The O3 "frozen 6-field" test is expected to be updated to a 7-field shape; this is the one intended, scoped edit to that contract.

### Review-artifact persistence: sidecar file (VREV-09)
- **D-09:** Persist to a **per-card review sidecar JSON** at `.voss/sessions/<root_id>/<node_id>.review.json` (0o600, same dir/permissions as the node file). **Do NOT add fields to `SessionTreeNode`** — keeps the V4 substrate schema untouched and keeps review artifacts independently readable. (Alternative — a `reviews[]` node field like `transitions[]`/`retry_notes[]` — was considered and rejected to avoid touching the keystone node schema.)
- **D-10:** Sidecar payload per card: A's authored verification (test file path **or** rubric text, plus the run result/pass-fail), B's **full verdict** as a dict (`conf`/`source`/`tier`/`verdict`/`notes`/`evidence_refs`/`domain_inferred`), and the **final outcome** (`Done` / `Blocked`). Written at gate-evaluation time; re-readable without re-running review. Mirror the existing `_write_node_file` write/permission helper rather than inventing a new I/O path.

### `voss review <run_id>` CLI (VREV-10)
- **D-11:** Mirror `voss board [root_id]` **exactly** (V5 precedent, `cli.py`): a click command in `AGENT_COMMANDS`, **read-only from persisted** `.review.json` sidecars — no live `Board`/`SessionTreeManager` constructed. `<run_id>` == **root_id**; **defaults to the most-recent root dir** under `.voss/sessions/` when omitted.
- **D-12:** Output **per card**: A's verification (test/rubric + result) + B's verdict (verdict/conf/tier/domain/evidence/notes) + final Done/Blocked. Plain text, ordered by card; reuse `voss board`'s root-discovery + rendering conventions.
- **D-13:** Exit codes match `voss board`: `voss review` (no arg) → prints latest run's per-card A+B review, exits 0; **unknown run_id → non-zero exit + stderr message**.

### Verification / regression + supersession (VREV-05)
- **D-14:** Verify-only (no rebuild) of REV-01..05,07,08: A derives the bar from the **original idea only** (not EM AC/DoD); B is **EM-narrative-blind** and its context **differs from A's**; B retains **Residual-2** block authority; reviewers operate within budget/scope. Existing O4 reviewer tests regress green. Mark **O4 superseded** (ROADMAP bookkeeping; O4 artifacts retained as reference).
- **D-15:** `git diff` must show **zero field changes** on `RunRecord`/`SessionRecord`/`BudgetScope`.

### Claude's Discretion
- Exact predicate class names/shapes for the A and B Done-gate arms, and whether A/B run sequentially or the order within the `("InReview","Done")` tuple (cheap→expensive ordering preserved).
- Internal JSON key names within the `.review.json` sidecar (so long as A-verification, B-verdict-full, and final-outcome are all present and re-readable).
- `voss review` text-rendering layout (column widths, evidence-ref formatting) — match `voss board` house style.
- Test organization within `tests/harness/board/` conventions.
- Whether the sidecar is written by the board at gate time, by a small persistence helper, or both A and B contribute — as long as a single durable sidecar per card results.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements (read first)
- `.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-SPEC.md` — 5 locked requirements (VREV-03/04/06/07/09/10 delta), boundaries, acceptance criteria. **MUST read before planning.**

### Shipped O4 reviewers (the delta target — verify, don't rebuild)
- `voss/harness/board/reviewer_a.py` — bar authoring from original idea; code-card test-authoring via `run_turn` + `shell_run` (exit code → verdict); AI-card rubric + `judge_run`. Fresh `EpisodicMemory`/session per call.
- `voss/harness/board/reviewer_b.py` — independent tiered judge via one `provider.complete()`; structural 2-message EM-narrative-blind isolation; parse-fail → fail-safe `block`; Residual-2 authority. **Extend `_ReviewerBOutput` + `_to_verdict` for `domain_inferred`.**
- `voss/harness/board/verdict.py` — frozen `ReviewerVerdict` + `Reviewer` Protocol; **zero-transitive-harness-import contract** (add the defaulted `domain_inferred` field here).
- `voss/harness/board/stub.py` — `DeterministicReviewerStub` (must keep satisfying the Reviewer Protocol after the verdict field add).

### Board wiring (V5 substrate — two-source Done gate)
- `voss/harness/board/machine.py` — `Board.__init__` / `from_team_config` (single `reviewer` slot → add `reviewer_a`+`reviewer_b`), `move()` gate evaluation, `critic_step` (block→terminal mapping), `_force_terminal`, `_append_delta` (verdict_snapshot already written into transitions).
- `voss/harness/board/gates.py` — `GateContext` (mutable `verdict` slot; add `verdict_a`/`verdict_b`), predicate registry, `Gates.build_default`, `conf_meets_p` reviewer-cardinality rule, AI-vs-code Done predicate tuples.

### Session-tree substrate (V4 keystone — persistence target; do NOT change node schema)
- `voss/harness/session_tree.py` — `SessionTreeNode`, `_write_node_file` (0o600 write helper to mirror for the sidecar), `.voss/sessions/<root_id>/<node_id>.json` layout, `finalize_node`.

### CLI precedent (mirror exactly)
- `voss/harness/cli.py` — `sessions_cmd` (≈L2429) for click+discovery style; `AGENT_COMMANDS` tuple (≈L3777) + `register()` for command registration. **V5's `voss board [root_id]` is the direct template** for `voss review <run_id>` (read-only, latest-root default, unknown-root → non-zero exit).

### Eval reuse (A's AI-card path)
- `voss/eval/judge.py` — `Verdict`, `judge_run` (A's AI-card verdict source).
- `voss/eval/runner.py`, `voss/eval/suite.py`, `voss/eval/summary.py` — eval harness reused by A.

### Prior-phase context (carry-forward)
- `.planning/phases/V5-board-state-machine-supersedes-o3/V5-CONTEXT.md` — `voss board` CLI design (read-only/latest-root/exit-code conventions V6 mirrors); Card field additivity pattern; self-Done independent-reviewer guard that V6 now fulfills with real A+B.
- `.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-CONTEXT.md` — node persistence layout, additive-field discipline, frozen-schema invariant.
- `.planning/phases/O4-reviewer-a-b-split/O4-01..04-PLAN.md` + SUMMARYs — O4 design rationale (reference only; superseded by V6).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_write_node_file` (`session_tree.py`): 0o600 JSON write helper — mirror it for the `.review.json` sidecar instead of new I/O.
- `GateContext.verdict` caching pattern (`gates.py`): extend to two cached slots (`verdict_a`/`verdict_b`) so each reviewer is called at most once per move attempt.
- `critic_step` / `_force_terminal` (`machine.py`): block→Blocked terminal routing already exists — reuse for D-03 rather than adding new terminal logic.
- `voss board [root_id]` (V5, `cli.py`): exact template for `voss review`'s discovery, latest-root default, and exit-code behavior.
- `DeterministicReviewerStub` (`stub.py`): keeps reviewer tests fast/deterministic after the two-slot + verdict-field changes.

### Established Patterns
- **Additive, defaulted fields** (V4/V5): every new field (`domain_inferred`, the two reviewer slots) ships with a default/back-compat alias so existing construction is untouched — the same discipline V4 Card/node and V5 Card used.
- **Read-only-from-persisted CLIs** (V4 `session tree`, V5 `board`): never construct a live manager; read the JSON the run already wrote.
- **Fail-safe at the gate** (`reviewer_b.py`): parse failure → `block`, not silent skip — preserve.

### Integration Points
- `Board.move()` `("InReview","Done")` predicate evaluation — where the two-source gate is composed.
- `.voss/sessions/<root_id>/` directory — where the new `<node_id>.review.json` sidecar lands alongside node files.
- `cli.py` `AGENT_COMMANDS` tuple — where `review_cmd` registers.

</code_context>

<specifics>
## Specific Ideas

- Sidecar filename: `<node_id>.review.json` (one per card, beside `<node_id>.json`).
- `domain_inferred` allowed set is exactly `{code, ai, docs, unknown}`; clamp anything else to `unknown`.
- Two cached verdict slots on `GateContext` so A and B are each invoked at most once per move attempt (preserve the existing reviewer-cardinality invariant).
- `voss review` with no arg = latest run (same root-discovery as `voss board`).
- No new third-party deps; pytest class-based tests under `tests/harness/board/`.

</specifics>

<deferred>
## Deferred Ideas

- ADE reviewer-verdict panel rendering → V11.
- Reviewer calibration telemetry + slop-rejection spot-audit → V9 (Audit Product) / O6 residual register.
- EM routing / card creation / `routing_rationale` → V7.
- Board state-machine changes beyond reviewer wiring → V5 (closed).
- Recursive/multi-level reviewer fan-out → out of track (no requirement).

None — discussion stayed within phase scope.

</deferred>

---

*Phase: V6-reviewer-a-b-split-supersedes-o4*
*Context gathered: 2026-06-06 — recommended answers applied direct from V6-SPEC.md (HOW decisions: Done-gate composition, verdict domain field, review sidecar schema, review CLI layout)*
