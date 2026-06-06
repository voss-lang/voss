# Phase V5: Board State Machine (supersedes O3) — Research

**Researched:** 2026-06-06
**Domain:** Python board state machine delta — Card dataclass extension, self-Done independence guard, read-only CLI over persisted session-tree nodes
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from V5-CONTEXT.md)

### Locked Decisions
- Build only the 3 gaps (CLI, Card fields, self-Done guard); verify/regress BOARD-01/02/04/05/06/08/09.
- O3 marked superseded (bookkeeping); O3 artifacts retained as reference design.
- `voss board [root_id]` is **read-only from persisted** `.voss/sessions/<root>/*.json` node files — no live `Board`/`SessionTreeManager` instance constructed.
- `root_id` **defaults to the most-recent root** (latest root dir under `.voss/sessions/`).
- Renders the **6 columns** with cards: id, role, risk, status, budget (spent/limit).
- **Column** for a card derives from the card's node's **latest `transitions[]` entry** (the persisted move log).
- **Budget** derives from the node **envelope** (`limit`/`spent`).
- Exit codes: no arg → renders latest run + exits 0; `<root_id>` → renders that root; **unknown root → non-zero exit + stderr message**.
- Add `idea`, `role`, `acceptance_criteria`, `verification_requirement` to `Card` — **additive with back-compat defaults**.
- `status` **derives from the current column** (not a stored field).
- `budget` **derives from the node envelope** (not a stored field).
- A `move(card, "Done")` **without an independent reviewer verdict raises `BoardGateError`**.
- The verdict must originate from the **Board's injected `Reviewer`** — a **worker/EM-authored verdict is rejected**.
- **Independence is enforced via the existing `Reviewer` interface** — verdict exists ⟺ injected reviewer ran; a self-authored path has no access to inject a valid verdict.
- V5 adds **no reviewer intelligence** — `Reviewer`/`ReviewerVerdict` interface unchanged.
- **V5 introduces zero budget-enforcement logic** (that's V4).
- ROADMAP/STATE mark O3 superseded by V5.

### Claude's Discretion
- Exact module placement of the `voss board` render (new `voss/harness/board/cli_view.py` vs inline in `cli.py`) and the column-render/table format.
- Exact shape of the persisted-node→column reader (how the latest `transitions[]` entry maps to a column label; how the most-recent root dir is selected — e.g. mtime vs lexical root_id).
- Exact enforcement site of the self-Done independence check within `Board.move` / the Done gate predicate set.
- Default values chosen for the additive `Card` fields (empty string vs `None`) consistent with existing O3 field conventions.
- Test organization within `tests/harness/` conventions.

### Deferred Ideas (OUT OF SCOPE)
- Reviewer A/B intelligence (bar authoring, judge, real A/B split) → V6.
- EM card creation / dispatch / routing → V7.
- ADE board panel rendering → V11 (V5 ships the CLI view only).
- Pre-emptive budget enforcement / `SessionTreeNode` changes → V4.
- Any field change to `RunRecord`/`SessionRecord`/`BudgetScope` — frozen.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VBOARD-10 | `voss board [root_id]` read-only CLI renders 6 columns + cards from persisted node files; default latest root; unknown root → non-zero + stderr | Column-derivation rule pinned (§ Research Focus 3); dispatch insertion point identified (§ Standard Stack) |
| VBOARD-03 | `Card` field completeness: add `idea`/`role`/`acceptance_criteria`/`verification_requirement`; `status` derives from column; `budget` derives from envelope | Additive dataclass pattern confirmed; all construction sites enumerated (§ Research Focus 2) |
| VBOARD-07 | Self-Done guard: `move(card,"Done")` without independent reviewer verdict raises `BoardGateError`; worker/EM verdict rejected; valid reviewer verdict permits Done | Guard site pinned; independence model analyzed (§ Research Focus 1) |
| verify | Shipped BOARD-01/02/04/05/06/08/09 regress green after V5 changes | Existing test suite confirmed at 91/92 passing; 1 pre-existing failure is unrelated to V5 scope (§ Verification Surface) |
| bookkeeping | Mark O3 superseded; confirm board operates on V4 session-tree substrate | File paths identified; V4 contracts confirmed intact |
</phase_requirements>

---

## Summary

V5 is a tight delta on O3's shipped board package. The three gaps (CLI read-only view, Card field completeness, self-Done independence guard) are individually small but each touches a different architectural layer: the CLI dispatcher, the frozen dataclass definition, and the gate predicate evaluation path.

The most important finding is the **self-Done guard analysis** (highest risk per the research brief). The current gate design is **structural but implicit**: the `InReview→Done` gate calls `conf_meets_p`, which calls `ctx.reviewer.review(card)` on the Board's injected `Reviewer`. The reviewer is injected at `Board.__init__` — there is no other path to populate `ctx.verdict`. A "worker/EM-authored verdict" in this codebase means a `ReviewerVerdict` value that was NOT produced by calling `board._reviewer.review(card)`. The current gate does NOT explicitly fail when `reviewer` is `None` — `conf_meets_p.evaluate` returns `False` if `ctx.reviewer is None` (gate refused, but with "conf" as the failure name, not a meaningful error). V5 must add an explicit guard that: (a) requires a Reviewer to be injected, and (b) forbids direct `ctx.verdict` injection from outside `conf_meets_p`. Mechanically, `ctx.verdict` is the only verdict slot, and it is only populated by `conf_meets_p` calling `ctx.reviewer.review()`. The guard is structural — the planner can add a thin enforcement layer in `Board.move` before gate evaluation for the `InReview→Done` transition.

The **`voss board` CLI** read-only reader pattern is already present in `voss/harness/audit/load.py` (`_build_card`, column-from-transitions logic at lines 206–220). The column-derivation rule is: iterate `transitions[]`, accumulate last `board.transition` event's `to` value; override with terminal_state when present. The CLI can mirror this exactly.

The **Card field additions** are straightforward: `Card` is a `frozen=True, slots=True` dataclass (line 80 `machine.py`). Adding fields with keyword-only defaults after the last field with a default keeps all existing positional construction working. `scope: Optional[...] = None` and `artifact: Optional[object] = None` are the existing default-carrying fields (lines 92–93). New fields with `None` defaults should follow this pattern.

**Primary recommendation:** Implement V5 as three sequentially dependent tasks: (1) extend `Card` dataclass + derive `status`/`budget` helpers; (2) add the self-Done independence guard in `Board.move`; (3) add `voss board` CLI reading from persisted nodes, dispatched via `AGENT_COMMANDS`. All changes are in `voss/harness/board/machine.py`, `voss/harness/cli.py` (or new `voss/harness/board/cli_view.py`), and `tests/harness/board/`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Card field completeness (`idea`/`role`/`acceptance_criteria`/`verification_requirement`) | Board library (machine.py) | — | Card is a pure board value object; fields live alongside existing board-owned fields |
| `status` derived from column | Board library (machine.py) | — | Column is already a Card field; status is a view over it (property or helper) |
| `budget` derived from node envelope | Board library (machine.py) | Session tree (session_tree.py) | Envelope lives in SessionTreeNode; Card exposes it as a derived read; no new field on node |
| Self-Done independence guard | Board library (machine.py / gates.py) | — | Gate enforcement lives in `Board.move`; adding a pre-check before gate iteration at `InReview→Done` is the correct tier |
| `voss board` CLI renderer | CLI dispatcher (harness/cli.py) | Board library (new cli_view.py) | CLI groups live in harness/cli.py; rendering logic can be a new board-owned module (Claude's discretion) |
| Read-only session-tree node reader | Board library (new cli_view.py) | Session tree (session_tree.py) | Reads persisted JSON without constructing live Board/Manager; mirrors audit/load.py pattern |
| Column derivation from transitions | Board library (cli_view.py) | — | Transitions format owned by board; derivation logic belongs in board tier |
| O3 supersession bookkeeping | Planning docs (STATE.md, ROADMAP) | — | Pure documentation update; no code tier involved |

---

## Standard Stack

### Core (no new deps — V5 adds nothing beyond what O3 already imports)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `click` | already in pyproject.toml | CLI command group for `voss board` | All voss CLI commands use click [VERIFIED: codebase] |
| `dataclasses` | stdlib | `Card` is a frozen dataclass; additive field extension | Existing O3 pattern [VERIFIED: codebase] |
| `pathlib.Path` | stdlib | `.voss/sessions/<root>/*.json` traversal | Already used in session_tree.py [VERIFIED: codebase] |
| `json` | stdlib | Read persisted node JSON files | Already used in audit/load.py [VERIFIED: codebase] |

**No new third-party dependencies.** [VERIFIED: V5-SPEC.md Constraints]

### Installation

No new packages to install.

---

## Package Legitimacy Audit

No external packages are introduced by V5. This section is N/A.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
voss board [root_id]
         │
         ▼
  harness/cli.py (board_cmd)
         │
         ▼
  board/cli_view.py  (read-only reader — new module)
         │
  ┌──────┴──────────────────────────────────┐
  │  .voss/sessions/<root_id>/<node_id>.json │  (persisted by Board.move → _append_delta → _write_node_file)
  └──────────────────────────────────────────┘
         │
  For each node JSON:
    - column ← last board.transition "to" in transitions[]
              (override by terminal_state.exit_reason when present)
    - budget ← envelope["spent"] / envelope["limit"]
    - role   ← card.role (new Card field; node JSON carries it after V5)
    - risk   ← node JSON em.ticket "risk_tier" (fallback "med")
         │
         ▼
  Render 6-column table (stdout, exit 0)
  Unknown root → stderr + exit 1
```

For the live-board path (tests, not CLI):
```
Board.move(card, "Done")
    │
    ├─ 1. Unknown-column check
    ├─ 2. WIP check
    ├─ 3. [NEW] Independence pre-check: InReview→Done requires board._reviewer is not None
    │         (raises BoardGateError("no reviewer injected") if None)
    └─ 4. Gate predicate loop
              │
              └─ conf_meets_p.evaluate(ctx)
                    │
                    └─ ctx.reviewer.review(card)  ← only path to populate ctx.verdict
                              │
                              └─ ReviewerVerdict (source="A"|"B")
```

### Recommended Project Structure

```
voss/harness/board/
├── machine.py          # MODIFY: Card fields + self-Done guard
├── cli_view.py         # NEW: read-only board CLI renderer
├── gates.py            # VERIFY (no change needed)
├── verdict.py          # DO NOT TOUCH (zero-import contract)
├── errors.py           # VERIFY (no change needed)
├── tick.py             # VERIFY (no change needed)
├── stub.py             # VERIFY (no change needed)
├── reviewer_a.py       # VERIFY (no change needed)
├── reviewer_b.py       # VERIFY (no change needed)
└── __init__.py         # POSSIBLY UPDATE: export new Card fields if needed

voss/harness/cli.py     # MODIFY: add board_cmd + board_group, add to AGENT_COMMANDS

tests/harness/board/
├── test_card_fields_v5.py      # NEW: VBOARD-03 — Card field completeness
├── test_self_done_guard.py     # NEW: VBOARD-07 — independence guard
├── test_board_cli.py           # NEW: VBOARD-10 — CLI exit codes + column render
└── [existing tests]            # VERIFY: must all still pass
```

### Pattern 1: Additive frozen dataclass field extension

The existing `Card` in `machine.py` lines 80–94 is `@dataclass(frozen=True, slots=True)`. New fields with defaults must appear AFTER all existing fields that already have defaults. Current last-field-with-default is `eval_threshold: float = 1.0` (line 94).

**Critical constraint with `slots=True`:** In Python 3.10+ with `slots=True`, all new fields with defaults are fine as long as they follow existing defaulted fields. The `Optional` typing with `None` default is the existing pattern (`scope`, `artifact`).

[VERIFIED: codebase machine.py:80-94]

```python
# Source: voss/harness/board/machine.py lines 80-94
@dataclass(frozen=True, slots=True)
class Card:
    node_id: str
    column: Column
    risk_tier: RiskTier
    retry_count: int
    deadline: float
    scope: Optional[TeamRoleScope] = None
    artifact: Optional[object] = None
    eval_threshold: float = 1.0
    # V5 additions — additive, back-compat defaults:
    idea: str = ""
    role: str = ""
    acceptance_criteria: str = ""
    verification_requirement: str = ""
```

### Pattern 2: Derived status and budget (NOT stored fields)

`status` = human-readable form of `card.column` (they're the same; a property `card.status` just returns `card.column`).
`budget` = a helper that reads from a node envelope dict, NOT a Card field. The CLI reader passes envelope data directly. The `Board` API can expose a helper method or the caller reads `card.node_id` → `manager.get_node()` → `node.envelope`.

For the **CLI reader** (read-only, no live Board): `budget = (node["envelope"]["spent"], node["envelope"]["limit"])` — direct from the persisted JSON dict.

For the **live Board**: `card.status` is a `@property` returning `card.column` (same value, just a named accessor).

[VERIFIED: codebase — envelope shape confirmed in session_tree.py:48-55, machine.py:511-512]

### Pattern 3: Column derivation from persisted transitions (read-only reader)

The exact rule is already implemented in `voss/harness/audit/load.py` lines 206–220 [VERIFIED: codebase]:

```python
# Source: voss/harness/audit/load.py:206-220
column = "Backlog"
for t in transitions:
    if t.get("kind") == "board.transition":
        column = t.get("to", column)

terminal = data.get("terminal_state")
if terminal is not None:
    exit_reason = terminal.get("exit_reason", "")
    if exit_reason == "timeout":
        column = "Blocked"
    elif exit_reason == "killed":
        column = "Blocked"
    elif exit_reason == "done":
        column = "Done"
```

The `voss board` CLI reader must use this exact rule. No deviation.

### Pattern 4: Latest root selection

"Most recent root" = the most-recently-modified directory under `.voss/sessions/`. Use `sorted(sessions_dir.iterdir(), key=lambda d: d.stat().st_mtime)[-1]` for mtime-based ordering. Alternatively, lexical sort by directory name (root IDs are hex timestamps via `uuid.uuid4().hex[:12]`). **mtime is more reliable** because it reflects actual write time, not sort order. The audit loader uses lexical sort (line 255 `load.py`) — that is for deterministic audit loading, not for "latest." The CLI should use mtime.

[VERIFIED: codebase — _write_node_file writes to `<cwd>/.voss/sessions/<root_id>/<node_id>.json`; session_tree.py:98-101]

### Pattern 5: CLI command registration

All agent commands are registered via `AGENT_COMMANDS` tuple in `harness/cli.py` (line 3777) and added to `main` via `register()` (line 3810). The `voss.cli` then calls `_register_agent_commands(main)` (line 445-447) to attach them to the top-level `voss` group.

```python
# Source: voss/harness/cli.py:3740-3741 (principles_group pattern)
@click.group("board")
def board_group() -> None:
    """Inspect the current board (read-only from persisted node files)."""

@board_group.command("show")   # voss board show [root_id]
# OR: bare click.command("board") for voss board [root_id]
```

The spec says `voss board [root_id]` — this is a simple `click.command("board")` with an optional `root_id` argument, not a group. See how `doctor_cmd`, `sessions_cmd` etc. are standalone commands added directly to `AGENT_COMMANDS`.

[VERIFIED: codebase — harness/cli.py:3777-3807]

### Pattern 6: Self-Done independence guard placement

The guard belongs in `Board.move` in `machine.py`, inserted between step 2 (WIP check) and step 3 (gate predicate loop), specifically gated on `to == "Done"` and `card.column == "InReview"` (or equivalently, `transition == ("InReview", "Done")`).

**What "worker/EM-authored verdict" means in this codebase:** `ReviewerVerdict` is a frozen dataclass. The ONLY way a verdict enters `GateContext.verdict` is via `conf_meets_p.evaluate(ctx)` calling `ctx.reviewer.review(card)`. There is no other injection path in the current code. A "self-authored" verdict would be one that somehow bypassed this — e.g., if `ctx.reviewer` is `None` (guard returns False, not a meaningful independence error) or if a caller directly sets `ctx.verdict` before passing it to the gate loop (not currently possible since `GateContext` is constructed fresh in `Board.move` at line 379).

**The smallest correct V5 guard:** In `Board.move`, before the gate loop, when `to == "Done"`:
```python
# At machine.py approx line 377, before ctx = GateContext(...)
if to == "Done" and self._reviewer is None:
    self._append_delta(card, from_col=card.column, to_col=to,
                       outcome="refused", failing_clauses=["no-reviewer"])
    raise BoardGateError("Done requires an independent reviewer",
                         failing_clauses=["no-reviewer"])
```

This is necessary but not sufficient. The spec also requires "a worker/EM-authored verdict is rejected." In the current architecture, this cannot happen because `GateContext` is always constructed fresh with `reviewer=self._reviewer`. The independence is already structural. The guard V5 adds is the one for `reviewer is None` — that is the case where someone tried to move a card to Done without injecting a reviewer.

If the spec requires testing that a verdict authored by the worker/EM is rejected (not just that reviewer=None fails), then the test must verify that calling `Board.move(card, "Done")` with a Board constructed WITHOUT a reviewer raises `BoardGateError`. The fact that the only valid reviewer is the injected one is the independence guarantee.

[VERIFIED: codebase machine.py:336-425, gates.py:88-98]

### Anti-Patterns to Avoid

- **Adding fields to `verdict.py`:** The zero-import contract test (`test_verdict_imports.py`) will fail. V5 must not touch `verdict.py`.
- **Adding a `status` stored field to `Card`:** `status` must be derived from `column`, not stored. Storing it would create a sync hazard.
- **Adding a `budget` stored field to `Card`:** `budget` must be derived from the node envelope on demand, not stored. Storing it would go stale.
- **Constructing a live `Board` in the CLI reader:** The spec says read-only from persisted files. No `SessionTreeManager` or `Board` construction in the CLI path.
- **Changing `SessionTreeNode` fields:** V4 owns that; V5 must not add fields to it.
- **Changing `RunRecord`/`SessionRecord`/`BudgetScope` fields:** Frozen. The `git diff` must show zero changes on these.
- **Adding reviewer intelligence:** V6 owns this. V5 keeps the `DeterministicReviewerStub` / `Reviewer` interface unchanged.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reading persisted node JSON | Custom JSON reader | Mirror `audit/load.py:_read_node_file` and `_build_card` | The column-derivation rule is already battle-tested and includes terminal_state overrides |
| Column derivation from transitions | Re-derive logic | Copy the exact rule from `audit/load.py:206-220` | Any divergence creates inconsistency between `voss board` and the audit view |
| CLI table rendering | Custom formatter | `click.echo` + fixed-width string formatting | No deps; existing CLI commands all use `click.echo` with manual formatting |
| Reviewer independence enforcement | Custom reviewer protocol extension | Thin `reviewer is None` check in `Board.move` before gate loop | Independence is already structural; the guard is a one-liner |

**Key insight:** `voss/harness/audit/load.py` is the ground truth for reading persisted session-tree nodes. The `voss board` CLI is a simpler view over the same data. Re-implementing the traversal differently risks divergence.

---

## Research Focus 1: Self-Done Independence Guard (RESOLVED)

**The guard is partially structural, partially missing.** Here is the exact current state:

- `Board.move` (machine.py:362-425) constructs `GateContext(reviewer=self._reviewer)` — the reviewer is always the Board's injected reviewer, never the worker/EM.
- `conf_meets_p.evaluate` (gates.py:88-98) returns `False` (not an error) when `ctx.reviewer is None`.
- There is **no explicit error** when someone attempts `move(card, "Done")` with `reviewer=None` — the gate just fails with `failing_clauses=["conf"]`.
- The spec requires: "a `move(card, 'Done')` without a reviewer verdict raises `BoardGateError`." Currently it does raise `BoardGateError` (because `conf_meets_p` fails), but the `failing_clauses` are `["conf"]` not `["no-reviewer"]`. This is technically correct behavior but not an explicit independence guarantee.

**The V5 guard to add (machine.py, inside `Board.move`, before the gate predicate loop):**

```python
# VBOARD-07 independence guard (machine.py approx line 377)
if to == "Done" and self._reviewer is None:
    self._append_delta(card, from_col=card.column, to_col=to,
                       outcome="refused", failing_clauses=["no-reviewer"])
    raise BoardGateError(
        "Done requires an independent reviewer verdict",
        failing_clauses=["no-reviewer"],
    )
```

This is the minimum correct implementation. The test must verify:
1. `Board.with reviewer=None` → `move(card, "Done")` raises `BoardGateError` with "no-reviewer" in `failing_clauses`.
2. `Board.with reviewer=stub` → `move(card, "Done")` with passing artifact proceeds.
3. Indirectly, the test documents the structural guarantee: "worker/EM cannot inject a verdict" because `GateContext` is always constructed fresh with `reviewer=self._reviewer`.

**What a "worker/EM-authored verdict" looks like in this codebase:** There is no `Board.move` overload that accepts an external `ReviewerVerdict`. The only path to populate `ctx.verdict` is `conf_meets_p` calling `ctx.reviewer.review(card)`. A hypothetical attacker would need to either (a) construct a `Board` with a fake `Reviewer` that always returns a passing verdict, or (b) somehow inject into `GateContext.verdict`. Path (a) is the legitimate A/B reviewer swap (V6 concern). Path (b) is not possible from outside `Board.move`.

**Confidence: HIGH** [VERIFIED: codebase machine.py:362-425, gates.py:80-98]

---

## Research Focus 2: Card Field Additions (RESOLVED)

**All `Card(...)` construction sites in production code:**

1. `machine.py:325-333` — `Board.spawn_card` — keyword construction, always specifies `node_id`, `column`, `risk_tier`, `retry_count`, `deadline`, optionally `scope` and `artifact`. New fields get defaults → SAFE.
2. `machine.py:407` — `dataclasses.replace(card, column=to)` — replace only touches `column`; other fields carry over. SAFE.
3. `machine.py:524` — `dataclasses.replace(card, column="Blocked")` — same. SAFE.
4. `machine.py:557-560` — `dataclasses.replace(card, column="InProgress", retry_count=new_retry)` — same. SAFE.

**All `Card(...)` construction sites in tests:**

Tests use `board.spawn_card()` (async), which internally uses construction site (1) above. None of the test files construct `Card(...)` directly in a way that would be broken by adding optional fields. [VERIFIED: codebase grep]

**Default value choice:** `""` (empty string) for `idea`, `role`, `acceptance_criteria`, `verification_requirement`. This matches the existing non-`Optional` field convention. Using `None` would require `Optional[str]` and None-checks everywhere; the empty string is the simpler sentinel for "not yet set." The existing `scope: Optional[TeamRoleScope] = None` uses `None` because `None` is meaningful (no scope constraint). For string fields, `""` is cleaner.

**`status` as derived property:** `card.status` returns `card.column`. Implementation: either a `@property` (not natively supported on `slots=True` frozen dataclasses without a custom descriptor, but Python does support it via `__slots__` with a property defined in the class body) OR a standalone helper function `def card_status(card: Card) -> str: return card.column`. The safest choice is a module-level helper to avoid `slots=True` + `@property` interaction complexity.

Actually, `@dataclass(frozen=True, slots=True)` DOES support `@property` in Python 3.10+ — the property is defined normally in the class body and `slots=True` only affects instance variables, not properties. [ASSUMED — training knowledge on slots+property interaction; low risk since a simple module function is equally valid]

The simplest correct approach (zero risk of slots interaction): `card_status(card)` as a module-level function in `machine.py`. Alternatively, document `card.column` as the status accessor in docstring.

**`budget` as derived helper:** The CLI reader reads directly from the node JSON dict: `node["envelope"]`. The live Board path can use `board._manager.get_node(card.node_id).envelope`. No Card field needed. A module-level helper `card_budget(card, node)` is the cleanest interface for tests.

**Confidence: HIGH** [VERIFIED: codebase machine.py:80-94, machine.py:325-333, machine.py:407, machine.py:524, machine.py:557]

---

## Research Focus 3: `voss board` Read-Only Reader (RESOLVED)

**Data path (pinned):**

```
.voss/sessions/                          # cwd / .voss / sessions /
├── <root_id_1>/                         # sorted by mtime DESC → pick first for "latest"
│   ├── <root_node_id>.json              # root node (is_root = id == root_id)
│   └── <child_node_id>.json             # child nodes (one per card)
└── <root_id_2>/
    └── ...
```

**Column derivation rule (pinned, from `audit/load.py:206-220`):**
1. Iterate `transitions[]`; for each entry where `kind == "board.transition"`, set `column = entry["to"]`.
2. After loop: if `terminal_state` is present, override: `timeout` or `killed` → `"Blocked"`; `done` → `"Done"`.
3. Default if no transitions: `"Backlog"`.

**Root selection rule:**
- Named root: `sessions_dir / root_id` — exists? → use it. Does not exist? → non-zero exit + stderr.
- Default (no arg): `sorted(sessions_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)[0]` — most-recently-modified directory.
- No sessions dir or empty: non-zero exit + stderr.

**"role" field for display:** V5 adds `role` to `Card`. For the CLI reader, role comes from the new `role` field written to the node's `transitions[]` when the card was created (via `spawn_card`). But wait — `spawn_card` does not write `role` to transitions. The role is a Card field in memory only; it is not currently in the node JSON. For the CLI reader to display role, either: (a) `spawn_card` must write role to a `board.card_created` transition entry, or (b) the CLI reader falls back to `""` for legacy nodes that don't have role in transitions.

**Resolution:** The SPEC says `Card` gets `role` as an additive field. The CLI reader shows "role" in the column table. For nodes created BEFORE V5, role will be `""` (empty). For nodes created AFTER V5, `spawn_card` should write the role into the initial `board.card_created` delta (a new transition kind). BUT — V5-SPEC says the node JSON format (SessionTreeNode) is V4-owned and V5 must not add fields to SessionTreeNode. The role can be stored in `transitions[]` as a new `board.card_created` entry (not a new field on the node struct, just a new dict in the existing list). [ASSUMED — the V5 spec does not explicitly say how role gets into the persisted format; this is a design decision for the planner]

**Render format (Claude's discretion):** The spec says render "id, role, risk, status, budget spent-limit." A simple `click.echo` table with fixed columns is sufficient:

```
Backlog (2)
  abc123def456  worker       low   Backlog     0/100000
  ...

InProgress (1)
  ...
```

**CLI dispatch insertion point:**
- New `board_cmd = click.command("board")` in `harness/cli.py` (or `board_group` if sub-commands are wanted later).
- Add to `AGENT_COMMANDS` tuple at line 3777 of `harness/cli.py`.
- The rendering logic can live in a new `voss/harness/board/cli_view.py` module (clean separation).

**Exit codes:**
- Success (rendered): `sys.exit(0)` (default click behavior)
- Unknown root: `click.echo(..., err=True)` + `raise click.exceptions.Exit(code=1)`
- No sessions at all: same as unknown root

**Confidence: HIGH for data path and column rule** [VERIFIED: codebase audit/load.py:206-220, session_tree.py:97-101]
**Confidence: MEDIUM for role persistence** [ASSUMED — design decision not locked in CONTEXT.md]

---

## Research Focus 4: Verification Surface (RESOLVED)

**Existing O3 board test suite status:** 91/92 pass. The one failing test is:

```
FAILED tests/harness/board/test_session_tree_additive.py::TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3
```

This test asserts `EXIT_REASONS == {"done", "max-iter", "budget", "interrupt", "batch-invariant"} | {"timeout"}`. The actual `EXIT_REASONS` in `session.py:74` also includes `"killed"` (added in O5). This test has a pre-existing failure unrelated to V5.

**V5 must not introduce new test failures beyond this pre-existing one.** The V5 plan should NOT fix this pre-existing failure (it is out of scope — V5 must not modify session.py's EXIT_REASONS).

**Tests that cover the existing shipped surface (BOARD-01/02/04/05/06/08/09):**

| File | What it tests | Maps to BOARD-## |
|------|--------------|------------------|
| `test_columns_and_unknown.py` | 6 columns + unknown column rejection | BOARD-03/04 |
| `test_wip_cap.py` | Per-column WIP overflow raises `BoardWIPError` | BOARD-03 |
| `test_gate_predicates_basic.py` | 8 predicates, 7 stable names, registry shape | BOARD-04/05 |
| `test_stub_full_lifecycle.py` | Backlog→Done lifecycle, transition deltas | BOARD-01/02/06/08 |
| `test_card_node_wiring.py` | Card↔node 1:1, frozen invariant | BOARD-01/02 |
| `test_board_lifecycle.py` | start/stop, tick loop forces timeout | BOARD-09 |
| `test_timeout_tick.py` | Timeout forces Blocked | BOARD-09 |
| `test_budget_tick.py` | Budget exhaustion forces Blocked | BOARD-09 |
| `test_critic_loop.py` | Retry → Blocked on ceiling | BOARD-09 |
| `test_reviewer_integration.py` | A+B lifecycle via Board | BOARD-06/07 |
| `test_transition_count_invariant.py` | Every move appends to transitions | BOARD-08 |
| `test_dry_run_gate.py` | dry_run_gate non-destructive | BOARD-05 |
| `test_risk_thresholds.py` | Risk tier thresholds | BOARD-06 |
| `test_session_tree_additive.py` | SessionTreeNode fields additive | V4 substrate |
| `test_verdict_imports.py` | verdict.py zero-import contract | BOARD-07 |
| `test_verdict.py` | ReviewerVerdict shape | BOARD-07 |
| `test_stub.py` | DeterministicReviewerStub | BOARD-07 |
| `test_reviewer_a.py` | ReviewerA protocol conformance | BOARD-07 |
| `test_reviewer_b.py` | ReviewerB protocol conformance | BOARD-07 |
| `test_board_factory.py` | Board.from_team_config | BOARD-02 |
| `test_artifact_only_confidence.py` | conf only on artifact transitions | BOARD-05 |
| `test_tick_clock.py` | FakeClock mechanics | BOARD-09 |
| `test_100_card_stress.py` | 100-card stress test | BOARD-03/04 |

**Commands to run regression suite:**
```bash
.venv/bin/python -m pytest tests/harness/board/ -q --tb=short
```
Expected: 91 pass, 1 fail (pre-existing `test_exit_reasons_is_sorted_superset_of_pre_o3`).

**New tests needed for V5 gaps:**

| Requirement | New test file | Test class / description |
|-------------|--------------|--------------------------|
| VBOARD-03 | `tests/harness/board/test_card_fields_v5.py` | `TestCardFieldsV5` — idea/role/AC/VR present with defaults; old construction paths still work; status property returns column |
| VBOARD-07 | `tests/harness/board/test_self_done_guard.py` | `TestSelfDoneGuard` — reviewer=None raises BoardGateError("no-reviewer"); reviewer=stub allows Done when other gates pass |
| VBOARD-10 | `tests/harness/board/test_board_cli.py` | `TestBoardCLI` — click CliRunner: renders latest root exit 0; renders named root exit 0; unknown root exit non-zero with stderr; no sessions dir exit non-zero |

**Confidence: HIGH** [VERIFIED: codebase test collection above]

---

## Research Focus 5: Frozen-Schema Guard (RESOLVED)

**Files that must NOT be changed by V5:**

| File | Fields frozen |
|------|--------------|
| `voss/harness/session.py` — `RunRecord` | All fields including `exit_reason` |
| `voss/harness/session.py` — `SessionRecord` | All fields |
| `voss_runtime` — `BudgetScope` | All fields |
| `voss/harness/session_tree.py` — `SessionTreeNode` | All fields (V4 owns) |

**V5 modifies only:**
- `voss/harness/board/machine.py` — `Card` dataclass (additive fields only)
- `voss/harness/cli.py` — new `board_cmd`, addition to `AGENT_COMMANDS`
- `voss/harness/board/cli_view.py` — new module (no existing code)
- `tests/harness/board/` — new test files
- `.planning/` — bookkeeping docs

**Acceptance criterion:** `git diff --name-only HEAD` after V5 implementation must show ZERO changes to `voss/harness/session.py`, `voss_runtime/`, or `voss/harness/session_tree.py`.

**Confidence: HIGH** [VERIFIED: codebase — all frozen files identified]

---

## Common Pitfalls

### Pitfall 1: `slots=True` + `@property` interaction

**What goes wrong:** Adding a `@property` to a `frozen=True, slots=True` dataclass can fail if a `__slots__` conflict is introduced. Python 3.10+ generally handles this, but it's a subtle area.

**Why it happens:** `slots=True` generates `__slots__` for all instance variables. A `@property` defined in the class body is NOT an instance variable — it is a class attribute. No conflict exists as long as the property name does not shadow a slot name.

**How to avoid:** Use a standalone module-level function `def card_status(card: Card) -> str: return card.column` instead of a `@property`. This is equivalent and simpler.

**Warning signs:** `AttributeError` on `card.status` at import time or test time.

### Pitfall 2: Breaking the 1-transition-per-move invariant

**What goes wrong:** Adding the V5 independence guard could double-append a transition delta if the guard raises AFTER `_append_delta` was already called by something else.

**Why it happens:** `Board.move` calls `_append_delta` in step 4 (success) and in step 3's `if failing:` block. The new guard must call `_append_delta` only once (for the refused delta) before raising.

**How to avoid:** Insert the guard BEFORE the `GateContext` is constructed (between WIP check and `ctx = GateContext(...)`). Emit one `_append_delta` with `outcome="refused"` and `failing_clauses=["no-reviewer"]`. Then raise. This mirrors the existing pattern at lines 396-405 of machine.py.

**Warning signs:** `node.transitions` has an extra entry in `test_transition_count_invariant.py`.

### Pitfall 3: "latest root" by lexical sort is wrong

**What goes wrong:** `sorted(sessions_dir.iterdir())` sorts by name (hex strings). Hex UUIDs are roughly time-ordered but not guaranteed — the truncated hex from `uuid4().hex[:12]` can collide on ordering.

**Why it happens:** UUID4 is random, not time-based. The hex representation is NOT guaranteed to sort chronologically.

**How to avoid:** Use `key=lambda d: d.stat().st_mtime, reverse=True` to sort by mtime. The most recently written root directory is unambiguous.

**Warning signs:** CLI returns wrong root in tests where two roots are created in rapid succession.

### Pitfall 4: `voss board` CLI constructed without a `cwd`

**What goes wrong:** The CLI must know `cwd` to find `.voss/sessions/`. If `cwd` defaults to `"."` but the user runs `voss board` from a different directory, no sessions are found.

**Why it happens:** Other CLI commands accept `--cwd` for the project root.

**How to avoid:** Add `@click.option("--cwd", ...)` defaulting to `"."` (same pattern as `principles_show_cmd`, `doctor_cmd`, etc.). Resolve the path.

**Warning signs:** `FileNotFoundError` or "no sessions" error when running from a subdirectory.

### Pitfall 5: Pre-existing test failure masking new failures

**What goes wrong:** The `test_exit_reasons_is_sorted_superset_of_pre_o3` test was already failing before V5. If the planner marks all failures as "pre-existing," a real V5-introduced failure could be missed.

**Why it happens:** The test asserts `EXIT_REASONS == pre_o3 | {"timeout"}` but the actual set also includes `"killed"` from O5.

**How to avoid:** Run `pytest tests/harness/board/ -q` BEFORE any V5 changes and record the baseline failure count (1). After V5, the failure count must still be 1 (same test, no new failures).

**Warning signs:** `pytest` reports 2 failures after V5.

---

## Code Examples

### `Card` dataclass extension (VBOARD-03)

```python
# Source: voss/harness/board/machine.py:80-94 (current), V5 target
@dataclass(frozen=True, slots=True)
class Card:
    """A board card mapped 1:1 to a SessionTreeNode (OBRD-01)."""
    node_id: str
    column: Column
    risk_tier: RiskTier
    retry_count: int
    deadline: float
    scope: Optional[TeamRoleScope] = None
    artifact: Optional[object] = None
    eval_threshold: float = 1.0
    # V5: additive field completeness (VBOARD-03)
    idea: str = ""
    role: str = ""
    acceptance_criteria: str = ""
    verification_requirement: str = ""


# Derived helpers (NOT stored fields)
def card_status(card: "Card") -> str:
    """Derives from the current column (VBOARD-03)."""
    return card.column


def card_budget(node_envelope: dict) -> tuple[int, int]:
    """Returns (spent, limit) from a node's persisted envelope."""
    return node_envelope.get("spent", 0), node_envelope.get("limit", 0)
```

### Self-Done independence guard (VBOARD-07)

```python
# Source: voss/harness/board/machine.py:336 (Board.move), V5 insertion
def move(self, card: Card, to: str) -> Card:
    # 1. Unknown column rejection
    ...
    # 2. WIP enforcement
    ...
    # 2.5 VBOARD-07: Done requires an independent reviewer (inserted here)
    if to == "Done" and self._reviewer is None:
        self._append_delta(
            card, from_col=card.column, to_col=to,
            outcome="refused", failing_clauses=["no-reviewer"],
        )
        raise BoardGateError(
            "Done requires an independent reviewer",
            failing_clauses=["no-reviewer"],
        )
    # 3. Gate predicate evaluation
    ...
```

### Column derivation for CLI reader (VBOARD-10)

```python
# Source: voss/harness/audit/load.py:206-220 (pattern to mirror)
# In voss/harness/board/cli_view.py (new module)

_COLUMNS = ("Backlog", "Planned", "InProgress", "InReview", "Blocked", "Done")

def _derive_column(node_data: dict) -> str:
    column = "Backlog"
    for t in node_data.get("transitions", []):
        if t.get("kind") == "board.transition":
            column = t.get("to", column)
    terminal = node_data.get("terminal_state")
    if terminal is not None:
        er = terminal.get("exit_reason", "")
        if er in ("timeout", "killed"):
            column = "Blocked"
        elif er == "done":
            column = "Done"
    return column
```

### CLI command registration (VBOARD-10)

```python
# Source: voss/harness/cli.py:3740-3741 (principles_group pattern), V5 analog
@click.command("board")
@click.argument("root_id", required=False, default=None)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def board_cmd(root_id: str | None, cwd_str: str) -> None:
    """Render the board in read-only view from persisted session-tree nodes."""
    from voss.harness.board.cli_view import render_board
    cwd = Path(cwd_str).resolve()
    rc = render_board(cwd, root_id=root_id)
    raise click.exceptions.Exit(code=rc)

# Add board_cmd to AGENT_COMMANDS in harness/cli.py line 3777
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| O3 board with no CLI view | V5 adds `voss board [root_id]` read-only CLI | V5 (now) | Board is inspectable without writing test code |
| `Card` with 4 fields | `Card` with 8 fields (+ 4 new + derived status/budget) | V5 (now) | Full PRD BOARD-03 field coverage |
| Self-Done gate relies on implicit structural guarantee | V5 adds explicit `reviewer is None` BoardGateError guard | V5 (now) | Clearer error message; independence guarantee is explicit |
| O3 phase active | O3 superseded by V5 | V5 (now) | ROADMAP/STATE bookkeeping |

**Deprecated/outdated:**
- O3 as the active phase designation: V5 supersedes it. O3 artifacts are retained as reference.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `@property` on `frozen=True, slots=True` dataclass works cleanly in Python 3.10+; fallback is a module function | Research Focus 2 | Low — module function fallback eliminates this risk entirely |
| A2 | `role` for persisted CLI display should be stored in a `board.card_created` transition entry when `spawn_card` creates the node; CLI reader falls back to `""` for legacy nodes | Research Focus 3 | Medium — planner must decide whether `spawn_card` emits a creation delta or role stays in-memory only (acceptable for V5 if CLI just shows `""` for all nodes from current sprint) |
| A3 | mtime-based "latest root" selection is correct | Research Focus 3 | Low — worst case: wrong root shown when two roots created in same second; acceptable for V5 |

**If this table is empty of blockers:** A1 is mitigated by the module-function fallback. A2 needs a planner decision. A3 is acceptable.

---

## Open Questions

1. **Does `role` need to survive in the persisted node JSON for `voss board` to display it?**
   - What we know: `Card.role` is a new field. The CLI reader reads from `*.json`. The current JSON contains `envelope`, `transitions`, `terminal_state` etc. — no `role` key.
   - What's unclear: Should `spawn_card` write a `board.card_created` transition entry with the role? Or does V5 accept that `voss board` shows `""` for role on all nodes from this sprint?
   - Recommendation: **RESOLVED** (planning decision) — accept `""` for role in the CLI for V5 (all existing nodes have no role anyway); `spawn_card` can write a `board.card_created` delta in a future phase when role population is driven by EM dispatch (V7). This keeps V5 minimal.

2. **Should `voss board` be `voss board [root_id]` (standalone command) or `voss board show [root_id]` (group)?**
   - What we know: The spec says `voss board [root_id]`. The principles group uses `voss principles show`.
   - What's unclear: Whether future board sub-commands (create, move, etc.) are planned.
   - Recommendation: **Standalone `click.command("board")`** for V5 since no sub-commands exist. Can be promoted to a group in V7/V11 if needed (click groups support adding sub-commands later without breaking the standalone usage if `invoke_without_command=True` is used).
   - **(RESOLVED)** — Use standalone command for V5.

3. **The pre-existing `test_exit_reasons_is_sorted_superset_of_pre_o3` failure — document or fix?**
   - What we know: Test asserts `EXIT_REASONS == pre_o3 | {"timeout"}` but actual set includes `"killed"`. This is a stale test from O5 adding "killed".
   - What's unclear: V5 should not touch `session.py`. Can V5 update the test to account for "killed"?
   - Recommendation: **Yes — update the test in `test_session_tree_additive.py` line 83-85** to use `issubset` check rather than equality. This is a trivial one-line fix that does NOT change `session.py` and unblocks the regression gate. Include it in V5 Wave 0 / bookkeeping task.
   - **(RESOLVED)** — Fix the stale test assertion as part of V5 verify task.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `.venv` | All board tests | ✓ | confirmed (tests ran) | — |
| `pytest` + `pytest-asyncio` | Board test suite | ✓ | confirmed (91 tests ran) | — |
| `click` | `voss board` CLI | ✓ | already in pyproject.toml | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (with pytest-asyncio for async Board methods) |
| Config file | pyproject.toml (root) |
| Quick run command | `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short` |
| Full suite command | `.venv/bin/python -m pytest tests/harness/board/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VBOARD-03 | `Card` carries `idea`/`role`/`acceptance_criteria`/`verification_requirement` with defaults | unit | `.venv/bin/python -m pytest tests/harness/board/test_card_fields_v5.py -x` | ❌ Wave 0 |
| VBOARD-03 | Existing `Card` construction paths still work | unit | `.venv/bin/python -m pytest tests/harness/board/test_card_node_wiring.py tests/harness/board/test_stub_full_lifecycle.py -x` | ✅ |
| VBOARD-03 | `status` derives from column | unit | `.venv/bin/python -m pytest tests/harness/board/test_card_fields_v5.py::TestCardStatus -x` | ❌ Wave 0 |
| VBOARD-07 | `move(card,"Done")` with `reviewer=None` raises `BoardGateError` with "no-reviewer" | unit | `.venv/bin/python -m pytest tests/harness/board/test_self_done_guard.py -x` | ❌ Wave 0 |
| VBOARD-07 | Valid reviewer verdict permits Done | unit | `.venv/bin/python -m pytest tests/harness/board/test_self_done_guard.py::TestSelfDoneGuard::test_valid_reviewer_allows_done -x` | ❌ Wave 0 |
| VBOARD-10 | `voss board` renders latest root + exits 0 | smoke/integration | `.venv/bin/python -m pytest tests/harness/board/test_board_cli.py::TestBoardCLI::test_default_latest -x` | ❌ Wave 0 |
| VBOARD-10 | `voss board <root_id>` renders named root + exits 0 | smoke | `.venv/bin/python -m pytest tests/harness/board/test_board_cli.py::TestBoardCLI::test_named_root -x` | ❌ Wave 0 |
| VBOARD-10 | Unknown root → non-zero exit + stderr | smoke | `.venv/bin/python -m pytest tests/harness/board/test_board_cli.py::TestBoardCLI::test_unknown_root_exit_code -x` | ❌ Wave 0 |
| verify | Shipped board surface (BOARD-01..09) regresses green | regression | `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short` | ✅ (91 pass) |
| verify | `test_exit_reasons_is_sorted_superset_of_pre_o3` stale test fixed | unit | `.venv/bin/python -m pytest tests/harness/board/test_session_tree_additive.py -x` | ✅ (fix 1 line) |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short`
- **Per wave merge:** `.venv/bin/python -m pytest tests/harness/board/ -v`
- **Phase gate:** Full suite green (91+new tests pass, pre-existing failure fixed) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/harness/board/test_card_fields_v5.py` — covers VBOARD-03 (Card field completeness + status derivation)
- [ ] `tests/harness/board/test_self_done_guard.py` — covers VBOARD-07 (independence guard)
- [ ] `tests/harness/board/test_board_cli.py` — covers VBOARD-10 (CLI exit codes + column rendering via click CliRunner)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes | Self-Done independence guard (the guard IS the access control: a worker/EM cannot self-transition to Done) |
| V5 Input Validation | yes | CLI `root_id` argument — Path traversal check: root_id must not contain `/` or `..`; constructed path must be under `.voss/sessions/` |
| V6 Cryptography | no | — |

### STRIDE Threat Model for Self-Done Guard

| Threat | STRIDE | What the attacker attempts | Standard Mitigation in V5 |
|--------|--------|---------------------------|--------------------------|
| Worker self-Done without review | Elevation of Privilege | Construct a `Board(reviewer=None)` and move card to Done | V5 guard: `reviewer is None` → `BoardGateError("no-reviewer")` |
| Worker injects fake verdict | Spoofing | Set `GateContext.verdict` directly before gate loop | NOT POSSIBLE: `GateContext` is constructed fresh in `Board.move`; caller cannot pre-populate `verdict` |
| Malicious `root_id` in CLI | Tampering | Pass `root_id = "../../etc/passwd"` to escape `.voss/sessions/` | Path must be resolved under `.voss/sessions/`; if resolved path is outside, raise error |
| CLI reads in-flight (partial) node JSON | Tampering | Read a half-written node file | JSON decode failure → skip or error; `_read_node_file` wraps in try/except |

### Known Trust Boundaries
- `Board._reviewer` is the trust anchor for independence. V5 makes this explicit with the guard.
- CLI root_id is user-supplied; must be validated as a simple directory name (no path separators).

---

## Sources

### Primary (HIGH confidence)
- `voss/harness/board/machine.py` — complete review; all construction sites, move logic, gate context wiring [VERIFIED: codebase]
- `voss/harness/board/gates.py` — complete review; `conf_meets_p`, `GateContext.verdict` wiring [VERIFIED: codebase]
- `voss/harness/board/verdict.py` — zero-import contract confirmed [VERIFIED: codebase]
- `voss/harness/session_tree.py` — `SessionTreeNode` envelope shape, `_write_node_file` path pattern [VERIFIED: codebase]
- `voss/harness/audit/load.py` — column derivation rule (lines 206-220), root directory traversal pattern [VERIFIED: codebase]
- `voss/harness/cli.py` — `AGENT_COMMANDS`, `register()`, command registration pattern (lines 3777-3813) [VERIFIED: codebase]
- `tests/harness/board/` — full test collection (23 files, 92 tests) [VERIFIED: pytest --collect-only]

### Secondary (MEDIUM confidence)
- `V5-SPEC.md` and `V5-CONTEXT.md` — locked requirements and decisions [VERIFIED: planning docs]

### Tertiary (LOW confidence)
- Assumption A2 (role persistence strategy) — design decision needed from planner

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all existing imports verified in codebase
- Architecture (guard site): HIGH — exact lines in machine.py identified and analyzed
- Architecture (CLI pattern): HIGH — exact audit/load.py pattern to mirror identified
- Architecture (Card fields): HIGH — all construction sites verified
- Pitfalls: HIGH — derived from direct code inspection
- Assumption A2 (role persistence): LOW — unresolved design decision

**Research date:** 2026-06-06
**Valid until:** 2026-07-06 (30 days — stable internal codebase)

---

## RESEARCH COMPLETE

**Phase:** V5 — Board State Machine (supersedes O3)
**Confidence:** HIGH

### Key Findings

1. **Self-Done guard is missing the explicit check.** `conf_meets_p` returns `False` (not a meaningful error) when `reviewer is None`. V5 must add a 5-line pre-check in `Board.move` before the gate loop, specifically for `to == "Done"`, that raises `BoardGateError("no-reviewer")`. The independence is otherwise structurally guaranteed by the design.

2. **Card field additions are clean.** `Card` is `frozen=True, slots=True`. Four new fields with `""` defaults appended after `eval_threshold: float = 1.0` are fully back-compatible. All 4 construction sites use keyword arguments or `dataclasses.replace` — none break. Prefer module-level helper functions for `card_status` and `card_budget` over `@property` to avoid slots complexity.

3. **`voss board` CLI mirrors existing audit/load.py pattern.** Column derivation rule is pinned (from audit/load.py lines 206-220). The CLI reader is a simpler version of the existing audit snapshot loader. Add `board_cmd` as a standalone `click.command("board")` with optional `root_id` argument, add to `AGENT_COMMANDS` in harness/cli.py. New module `voss/harness/board/cli_view.py` is recommended for the rendering logic.

4. **One pre-existing test failure must be fixed.** `test_exit_reasons_is_sorted_superset_of_pre_o3` asserts the exact set of EXIT_REASONS and is stale since O5 added "killed". V5 verify task should update the assertion to `issubset` check.

5. **V5 is safe for the frozen schemas.** Zero changes to `RunRecord`, `SessionRecord`, `BudgetScope`, `SessionTreeNode`. Confirmed by code inspection.

### File Created
`.planning/phases/V5-board-state-machine-supersedes-o3/V5-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | No new deps; all existing imports verified |
| Architecture (guard) | HIGH | Exact machine.py lines identified |
| Architecture (CLI) | HIGH | Pattern from audit/load.py directly reusable |
| Architecture (Card fields) | HIGH | All 4 construction sites verified |
| Pitfalls | HIGH | Derived from direct code inspection |
| Role persistence (A2) | LOW | Planner must decide; safe default is `""` for V5 |

### Open Questions Remaining
- A2 (role persistence): Accept `""` for V5 CLI display? Recommended: yes.

### Ready for Planning
Research complete. Planner can now create PLAN.md files.
