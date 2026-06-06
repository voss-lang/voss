# Phase V5: Board State Machine (supersedes O3) - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Source:** Direct synthesis from V5-SPEC.md (ambiguity 0.137; discuss-phase skipped — SPEC interview already locked direction)

<domain>
## Phase Boundary

Close the delta between the **shipped O3 board package** (`voss/harness/board/`, plans O3-01..04 with SUMMARYs) and PRD BOARD-01..10. O3 already shipped the state machine (6 columns, per-column WIP, gate registry, Done double-gate, timeout/critic→Blocked, transition persistence, Card↔node 1:1). V5 builds the three gaps and verifies the rest:

- **VBOARD-10** — `voss board [root_id]` read-only CLI (no `board` command exists in `cli.py`).
- **VBOARD-03** — `Card` field completeness (add `idea`/`role`/`acceptance_criteria`/`verification_requirement`; derive `status`/`budget`).
- **VBOARD-07** — self-Done guard: a card cannot reach Done without an **independent reviewer verdict**.

Reviewer A/B *intelligence* (bar authoring, judge) is explicitly deferred to **V6** — V5 keeps the existing `Reviewer`/`ReviewerVerdict` interface and enforces only the *independence requirement*. V5 sits on the **V4 session-tree keystone**; it adds **no budget enforcement** of its own (that's V4).

Pure board delta — no reviewer intelligence, no EM dispatch, no ADE panel.

</domain>

<decisions>
## Implementation Decisions

### Scope: delta-only on shipped O3
- Build only the 3 gaps (CLI, Card fields, self-Done guard); verify/regress BOARD-01/02/04/05/06/08/09.
- O3 marked superseded (bookkeeping); O3 artifacts retained as reference design.

### `voss board [root_id]` CLI (VBOARD-10)
- **Read-only from persisted** `.voss/sessions/<root>/*.json` node files — no live `Board`/`SessionTreeManager` instance constructed.
- `root_id` **defaults to the most-recent root** (latest root dir under `.voss/sessions/`).
- Renders the **6 columns** (Backlog/Planned/InProgress/InReview/Blocked/Done) with their cards: **id, role, risk, status, budget (spent/limit)**.
- **Column** for a card derives from the card's node's **latest `transitions[]` entry** (the persisted move log).
- **Budget** derives from the node **envelope** (`limit`/`spent`).
- Exit codes: `voss board` (no arg) → renders latest run + exits 0; `voss board <root_id>` → renders that root; **unknown root → non-zero exit + stderr message**.

### Card field completeness (VBOARD-03)
- Add `idea`, `role`, `acceptance_criteria`, `verification_requirement` to `Card` — **additive with back-compat defaults** (existing O3 `Card` construction in `machine.py` keeps working unchanged).
- `status` **derives from the current column** (not a stored field).
- `budget` **derives from the node envelope** (not a stored field).
- `Card` already carries `node_id`/`risk_tier`/`scope`/`artifact` — these stay.

### Self-Done guard (VBOARD-07)
- A `move(card, "Done")` **without an independent reviewer verdict raises `BoardGateError`**.
- The verdict must originate from the **Board's injected `Reviewer`** (the reviewer role) — a **worker/EM-authored verdict is rejected**.
- **Independence is enforced via the existing `Reviewer` interface**: the Done gate's verdict is the one produced by calling the injected `reviewer.review(card)` (already wired through `conf_meets_p` / `GateContext.verdict` in `gates.py`); a verdict supplied by any other path (self-authored) does not satisfy the gate.
- V5 adds **no reviewer intelligence** — `Reviewer`/`ReviewerVerdict` interface unchanged; real A/B split is **V6**.
- A valid reviewer verdict (with the other Done-gate predicates passing) **permits Done**.

### Shipped-surface verification (regress)
- Verify after V5 changes: 6 columns; per-column WIP overflow raises `BoardWIPError`; unmet gate raises `BoardGateError`; Done double-gate (code: `tests_pass`; ai: `eval_meets_threshold`) intact; timeout/critic-exhaustion → Blocked; each `move` appends to the node's `transitions[]`; Card↔`SessionTreeNode` 1:1 backing (`Card.node_id` = the `allocate_child` node).

### Bookkeeping: O3 supersession + V4 dependency
- ROADMAP/STATE mark O3 superseded by V5.
- Confirm the board operates on the **V4 session-tree substrate** (`SessionTreeManager`/`SessionTreeNode` as node source); the V4 pre-emptive budget guard sits beneath it.
- **V5 introduces zero budget-enforcement logic** (that's V4).

### Claude's Discretion
- Exact module placement of the `voss board` render (new `voss/harness/board/cli_view.py` vs inline in `cli.py`) and the column-render/table format.
- Exact shape of the persisted-node→column reader (how the latest `transitions[]` entry maps to a column label; how the most-recent root dir is selected — e.g. mtime vs lexical root_id).
- Exact enforcement site of the self-Done independence check within `Board.move` / the Done gate predicate set.
- Default values chosen for the additive `Card` fields (empty string vs `None`) consistent with existing O3 field conventions.
- Test organization within `tests/harness/` conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Shipped board package (the delta target)
- `voss/harness/board/machine.py` — `Board`, `Card` (1:1 `SessionTreeNode` via `allocate_child`), `Column` (6), `RiskTier`, per-column WIP, `Board.move` with gate enforcement + transition-delta emission (the file V5 extends for Card fields + self-Done guard).
- `voss/harness/board/gates.py` — 8 predicate classes / 7 stable names; `conf_meets_p` calls `reviewer.review(card)` at-most-once (cached on `GateContext.verdict`); Done double-gate variants.
- `voss/harness/board/verdict.py` — `Reviewer` Protocol + `ReviewerVerdict` (frozen 6-field; `source` Literal["A","B"]). **Zero-transitive-import contract — do NOT add imports beyond typing/dataclasses/__future__.**
- `voss/harness/board/reviewer_a.py`, `reviewer_b.py`, `stub.py` — reviewer stubs (V5 keeps interface; intelligence → V6).
- `voss/harness/board/errors.py` — `BoardWIPError`, `BoardGateError`, timeout error. `tick.py` — timeout/critic→Blocked.
- `voss/harness/board/__init__.py` — package exports.

### Session-tree substrate (V4 keystone — node source)
- `voss/harness/session_tree.py` — `SessionTreeNode` (`transitions[]`, envelope `limit`/`spent`, scope/role), `SessionTreeManager.allocate_child`/`get_node`/`finalize_node`, persisted node JSON at `.voss/sessions/<root_id>/<node_id>.json`.

### CLI surface (where `voss board` lands)
- `voss/cli.py` and/or `voss/harness/cli.py` — existing command dispatch (e.g. the `voss session tree` command from V4 is the closest analog for a read-only persisted-node CLI view).

### Frozen schemas (do NOT modify any field)
- `RunRecord`, `SessionRecord`, `voss_runtime.BudgetScope` — frozen; `git diff` must show zero field changes. `SessionTreeNode` changes are owned by V4, not V5.

### Prior-phase + spec reference
- `.planning/phases/O3-board-state-machine/` — O3 SPEC/RESEARCH/PATTERNS/CONTEXT + O3-01..04 SUMMARYs (design rationale; retained as reference).
- `.planning/phases/V5-board-state-machine-supersedes-o3/V5-SPEC.md` — locked requirements VBOARD-03/07/10 + verify + bookkeeping, 6 acceptance criteria.
- `.planning/phases/V4-.../V4-CONTEXT.md` — V4 substrate decisions (the keystone V5 sits on).
- `docs/ORCHESTRATION_LAYERS.md` — PRD BOARD-01..10 source.

</canonical_refs>

<specifics>
## Specific Ideas

- `voss board` data path: list root dirs under `.voss/sessions/` → pick latest (or the given `root_id`) → load each `<node_id>.json` → derive column from latest `transitions[]` entry, budget from envelope → bucket into the 6 columns → render table (id/role/risk/status/budget spent-limit).
- Self-Done guard: the Done gate's verdict must be the one returned by the injected `Reviewer`; the worker/EM cannot inject a self-authored `ReviewerVerdict` that satisfies the gate. Independence is structural (verdict exists ⇔ injected reviewer ran), enforced at the `InReview→Done` transition.
- `Card` additions are additive dataclass fields with back-compat defaults; `status`/`budget` are **derived** (property/helper), not new stored columns.
- Tests: pytest, class-based, `tests/harness/` conventions; regress the existing O3 board test suite. **No new third-party deps.**

</specifics>

<deferred>
## Deferred Ideas

- Reviewer A/B intelligence (bar authoring, judge, real A/B split) → **V6** (V5 keeps interface + independence guard only).
- EM card creation / dispatch / routing → **V7**.
- ADE board panel rendering → **V11** (V5 ships the CLI view only).
- Pre-emptive budget enforcement / `SessionTreeNode` changes → **V4** (the keystone V5 sits on).
- Any field change to `RunRecord`/`SessionRecord`/`BudgetScope` — frozen.

</deferred>

---

*Phase: V5-board-state-machine-supersedes-o3*
*Context synthesized: 2026-06-06 direct from V5-SPEC.md (discuss-phase skipped per locked SPEC interview)*
