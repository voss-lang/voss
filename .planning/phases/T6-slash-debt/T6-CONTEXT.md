# Phase T6: PRD §2.4 Slash Debt — Context

**Gathered:** 2026-05-16
**Status:** Complete (2026-05-18) — 3/3 plans executed and verified
**SPEC:** None — requirements drawn from ROADMAP.md T6 (SLASH-01..SLASH-07 proposed)
**Versioning:** v0.1.1 patch (closes a documented v0.1 contract bug — NOT a v0.2 feature)

<domain>
## Phase Boundary

Ship the slash commands PRD §2.4 promised. **Critical finding from codebase scout: all 7 slashes ALREADY have implementations** in `voss/harness/cli.py:569-790` (`_build_slash_registry`). T6 is therefore a **HARDEN + TEST + DISCOVERABILITY** phase, not greenfield:

- 5 functional: `/cost --by-model` (cli.py:592-610), `/budget` (622-653), `/why` (655-673), `/diff` via `git diff` (675-702), `/discard` via `git checkout` (715-752), `/resume` live-REPL (754-782).
- 2 honest-stubs: `/apply` (704-713 — message only), `/cost --by-tool` (585-591 — currently says "lands with T4").

T6 closes the contract by: hardening the stubs to honest-but-useful behavior, adding ≥1 integration test per slash (SC#1), wiring grouped `/help` discoverability (SC#3), and reconciling the T4↔T6 `--by-tool` ownership overlap. The phase ships BEFORE T1–T5 (it is the v0.1.1 patch lead), so any slash whose "real" semantics depend on later infra (T1 pending-edit queue, M9-05 DiffModal) ships a v0.1.1-truthful behavior now and is upgraded by the later phase.

</domain>

<decisions>
## Implementation Decisions

### SLASH-07 `/cost --by-tool` — derived approximation, no new persistence (D-01)

Provider bills per LLM **turn**, not per tool call (`RunRecorder.cost_usd` is per-iteration at recorder.py:35,121; one turn → many tool calls). True per-tool cost does not exist and cannot without a fabricated model. T6 ships a **derived, explicitly-labeled approximation**:

- For each run/iteration with `cost_usd > 0` and a non-empty `tool_results` list, attribute `cost_usd` **evenly** across that iteration's tool calls (byte-weighting was rejected — it implies a precision/cost-model that equally doesn't exist; even split is the honest floor).
- Aggregate per tool name across the session.
- Output every line tagged `~approx (turn cost ÷ N tool calls)` so the caveat is unmissable.
- Derived entirely from **existing** `RunRecord`/`tool_results` data — **zero new persistence**, honoring the T6 cross-cutting constraint.
- The current `_cost` honest-stub branch (cli.py:585-591, "lands with T4") is REPLACED by this real approximation output, not a deferral message.

### SLASH-01/02/03 `/diff` `/apply` `/discard` — keep git-tree semantics (D-02)

The pending-edit queue lands in **T1** (v0.2) + M9-05 DiffModal — AFTER this v0.1.1 patch. T6 does NOT fake a queue:

- `/diff` stays `git diff` against the working tree (+ `--staged`/`--cached` + optional path filter) — already coded, real, useful.
- `/discard` stays `git checkout --` against the last run's `changed` files, `--confirm`-gated, lists files otherwise — already coded.
- `/apply` stays an **honest stub**: prints that v0.1 applies edits immediately under `PermissionGate`, queued per-hunk apply lands with T1 + M9-05, suggests `/mode plan` → `/mode edit`. Registered (closes the contract slash) without simulating a non-existent queue.
- T1 later upgrades `/diff` + `/apply` to real queue semantics — T6 leaves the surface stable for that.

### SLASH-05 `/resume` — live-REPL only, warn-and-proceed cross-cwd (D-03)

Keep current `_resume` behavior (cli.py:754-782): swap `ctx.record` / `ctx.history` / `ctx.total_cost` / `ctx.prior_context` in-process via `session_store.load(target, cwd=ctx.cwd)`. Gate/cognition/tools stay bound to the live cwd. Cross-cwd: print a warning, stay in the current cwd, point the user to `voss resume <id>` (the cross-cwd CLI path, cli.py:1648). T6 work: add tests + verify `/resume <name>` resolves alongside `/resume <id>` (`session_store.load` takes a `target` — confirm name-vs-id resolution in research). NO in-process cwd/gate/tool rebind (out of patch posture).

### SC#3 help discoverability — in-REPL `/help` canonical, CLI epilog signposts (D-04)

Slashes are REPL constructs, not `voss` CLI subcommands. Therefore:

- `/help` (cli.py `_help` → `_print_slash_help`) is the canonical, complete listing — **grouped** with a one-line description per slash. Suggested groups: **Editing** (`/diff` `/apply` `/discard`), **Session** (`/resume` `/budget` `/cost` `/clear`), **Insight** (`/why` `/tools` `/analyze`), **Control** (`/help` `/exit` `/mode`). Planner finalizes exact grouping against the live registry.
- `voss --help` epilog gains ONE signpost line: e.g. `Interactive commands: run \`voss chat\`, then /help`. No full slash list in the CLI (avoids two-place drift).
- "Matches Codex discoverability" is operationalized as: every slash appears in `/help`, grouped, with a one-line description — not a literal Codex format clone.

### Derived / cross-phase decisions

- **D-05 — T6 is harden+test, not greenfield.** Every slash already has code. The phase's deliverable per slash = (a) audit impl against PRD §2.4 intent, (b) apply the D-01..D-04 hardening, (c) add ≥1 integration test exercising the happy path (SC#1), (d) ensure the name is registered in `_build_slash_registry` so M9-03 SlashPalette autocomplete picks it up (cross-cutting constraint).
- **D-06 — T4↔T6 `--by-tool` ownership reconciliation.** ROADMAP: "overlaps T6 SLASH-07; ship whichever lands first." T6 is v0.1.1 and ships first → T6 OWNS both `/cost --by-model` (already coded) and `/cost --by-tool` (D-01 approximation). T4-CONTEXT D-09 (a single-line edit changing the placeholder to reference "T6") becomes a **no-op / obsolete** once T6 ships the real approximation — flag this in T6's plan + note for whoever executes T4 later so they don't re-introduce a stub. Planner adds a note; no T4 file is edited by T6.
- **D-07 — `/why` (SLASH-06, PRD "killer feature") already satisfies SC#2.** `_why` (cli.py:655-673) reads `ctx.last_plan` only, no provider call, renders `plan.rationale` + `plan.confidence` + per-step `step.why` + `open_question` + `final_when_done`. T6 adds the test. Research MUST confirm whether PRD §2.4's "`ProbableValue` confidence breakdown" expects richer output than the current single `confidence:.2f` float (PRD ref at `.vscode/voss_v_0_1_scope_lock.md:712` `ProbableValue`, ticket at :1213) — if so, that delta is the only real `/why` code change in T6.
- **D-08 — No new persistence (cross-cutting honored end-to-end).** `--by-tool` derives from existing RunRecord; `/resume` uses existing `session_store.load`; `/diff`+`/discard` shell out to git; `/help` reads the live registry. Nothing adds a disk field, schema, or store.

### Claude's Discretion

- Exact `/help` group names + ordering (lock against the live `_build_slash_registry` contents at plan time).
- Whether `--by-tool` even-split skips iterations with zero `tool_results` (recommend: skip — a turn with no tool calls contributes nothing to per-tool aggregation).
- Whether the `~approx` label is a header line vs per-row suffix (recommend: header line once + a short legend, rows clean).
- `/resume <name>` disambiguation when a name collides with an id-shaped string (recommend: try id first, fall back to name — but confirm `session_store.load`'s existing resolution order in research rather than changing it).
- Test harness: extend the existing slash test file (scout for `tests/harness/test_repl_slash.py` — referenced in T4/T5 plan-checker findings as containing `test_cost_by_tool_is_honest_stub` at ~:225) vs a new `test_t6_slashes.py`. The existing `test_cost_by_tool_is_honest_stub` asserting `"T4" in out` MUST be updated/replaced because D-01 changes `--by-tool` from stub to real approximation.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase artifacts (locked)

- `.planning/ROADMAP.md` §"Phase T6 — PRD §2.4 Slash Debt" — goal, SLASH-01..07, Success Criteria #1/#2/#3, cross-cutting constraints (no new persistence; M9-03 SlashPalette reserves slot names).
- `.planning/ROADMAP.md` §"Versioning split" (lines 654-661) — T6 = v0.1.1 patch shipping BEFORE T1–T5/T7/T8; the patch-vs-feature framing is load-bearing for scope decisions.

### PRD source

- `.vscode/voss_v_0_1_scope_lock.md` §2.4 — the PRD section that promised these slashes (the "documented contract bug"). Specific anchors: `ProbableValue` at line 712 (relevant to D-07 `/why` confidence breakdown), "Ticket 7: Add `/why` Decision Explanation" at line 1213, session save/resume at line 391. Researcher MUST read §2.4 verbatim to confirm each slash's promised behavior + the exact `/why` ProbableValue expectation.

### Codebase anchors (read before touching)

- `voss/harness/cli.py:569-790` — `_build_slash_registry`, all 7 slash impls. THE primary work site.
  - `_cost` 582-620 (SLASH-07: --by-model done; --by-tool stub → D-01 replaces).
  - `_budget` 622-653 (SLASH-04, functional).
  - `_why` 655-673 (SLASH-06, functional; D-07 confirm ProbableValue).
  - `_diff` 675-702 (SLASH-01, git-tree; D-02 keep).
  - `_apply` 704-713 (SLASH-02, honest stub; D-02 keep).
  - `_discard` 715-752 (SLASH-03, git checkout; D-02 keep).
  - `_resume` 754-782 (SLASH-05, live-REPL; D-03 keep).
- `voss/harness/cli.py:575-576` — `_help` → `_print_slash_help` (SC#3 / D-04 grouping site).
- `voss/harness/cli.py` — `_print_slash_help` definition (grep for it; D-04 modifies).
- `voss/harness/cli.py:189` — `budget_usd` ReplContext field (SLASH-04 backing state).
- `voss/harness/cli.py:1317,1588,1708` — `_build_slash_registry()` call sites (REPL, `voss do`, others) — ensure parity.
- `voss/harness/cli.py:1648` — `session_store.load(session_id_or_name, ...)` — the cross-cwd `voss resume` CLI path D-03 points users to.
- `voss/harness/cli.py:26` — `from . import session as session_store`.
- `voss/harness/recorder.py:28-35,116-146,191-215` — `RunRecorder`, per-iteration `cost_usd`, `tool_results` list — the EXISTING data D-01 derives `--by-tool` from.
- `voss/harness/session.py` — `session_store.load` target resolution (id vs name) for D-03; `SessionRecord` shape.
- `tests/harness/test_repl_slash.py` — existing slash test file; contains `test_cost_by_tool_is_honest_stub` (~:225, asserts `"T4" in out`) which D-01 OBSOLETES — must be updated.

### Cross-phase context

- `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-CONTEXT.md` D-09 + lines 35,167,190 — T4 defers `/cost --by-tool` + per-tool attribution to T6. D-06 reconciles: T6 ships first, so T4's placeholder-edit becomes obsolete. Whoever executes T4 later must not re-stub `--by-tool`.
- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md` — T1 brings the real pending-edit queue + (via M9-05) DiffModal that upgrades `/diff`+`/apply` post-T6. T6 must leave that surface stable.
- `.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md` — M9-03 SlashPalette autocomplete reserves the seven slot names; T6's registration is what M9 keys off (cross-cutting constraint).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (all already built — T6 hardens, not rebuilds)

- **`_build_slash_registry()` + `SlashRegistry`** (cli.py:569) — the registration mechanism; all handlers are local closures over `ReplContext`.
- **`ReplContext`** — carries `record`, `history`, `total_cost`, `budget_usd`, `last_plan`, `prior_context`, `cwd`, `tools`, `slash_registry`. Every slash operates on this live object (matches "no new persistence" constraint).
- **`session_store.load(target, cwd=)`** (session.py via cli.py:26) — used by both `/resume` (live) and `voss resume` (CLI cross-cwd). Reused verbatim for D-03.
- **`RunRecord.runs[*].cost_usd` + `.tool_results`** (recorder.py) — the existing per-iteration data D-01 derives `--by-tool` from. No schema change.
- **`git diff` / `git checkout` subprocess pattern** (cli.py:684-702, 736-752) — `_diff`/`_discard` already use it with timeout + stderr handling. Pattern reused, not extended.
- **`plan.rationale/confidence/steps[].why/open_question/final_when_done`** (cli.py:662-673) — `/why` already renders the full breakdown with no provider call (SC#2 already met).

### Established Patterns

- **Honest-stub-with-clear-message** — `/apply` and the old `/cost --by-tool` model: register the slash, print exactly what v0.1 does + where the real version lands. D-02 keeps `/apply` in this mode; D-01 promotes `--by-tool` out of it.
- **`--confirm`-gated destructive ops** — `/discard` lists files then requires `--confirm`. Preserve.
- **Subprocess with timeout + stderr surfacing** — `_diff`/`_discard` (15s timeout, stderr to err). Any new shell-out follows this.
- **Slash handler signature** `(ctx, args, line) -> None`, `click.echo` for output, `err=True` for errors. All new/modified handlers conform.

### Integration Points

- `_print_slash_help` — SC#3/D-04 grouping (the one real new rendering work).
- `_cost` `--by-tool` branch — D-01 replaces stub with derived approximation (the one real new logic).
- `tests/harness/test_repl_slash.py` — `test_cost_by_tool_is_honest_stub` updated; new per-slash happy-path tests added (SC#1).
- M9-03 SlashPalette — consumes registry names; T6 ensures all 7 present (no M9 file edited by T6).

### Anti-patterns to Avoid

- **Faking a pending-edit queue** in T6 (D-02 rejected — T1 owns it; a fake queue would diverge from T1's real one).
- **Fabricated per-tool cost precision** (D-01 — even-split + loud `~approx` label; never byte-weight or imply real attribution).
- **Duplicating the slash list** into `voss --help` (D-04 — single canonical `/help`, CLI epilog signposts only).
- **In-process cwd/gate/tool rebind** for cross-cwd `/resume` (D-03 — out of patch posture; `voss resume` CLI already handles it).
- **Editing T4 files from T6** (D-06 — T6 only notes the reconciliation; T4 executes later independently).

</code_context>

<specifics>
## Specific Ideas

- The phase is mostly **test debt + two real changes** (`--by-tool` approximation logic, `/help` grouping). Everything else is audit + register-verify + happy-path test. This keeps the "20-line wrapper / v0.1.1 patch" framing honest.
- `/why` is PRD's named "killer feature" — the single highest-value verification is SC#2's "renders confidence + rationale with no provider call," already true; the research question is only whether PRD's `ProbableValue` breakdown wants more than the current single float.
- The `test_cost_by_tool_is_honest_stub` test asserting `"T4" in out` is a tripwire: D-01 deliberately changes that behavior, so the test change is a required, expected part of T6 (not a regression).
- "Ship whichever lands first" (ROADMAP, --by-tool) resolves cleanly: T6 is the v0.1.1 patch and ships before T4 — T6 owns it; T4's D-09 placeholder edit is dead on arrival.

</specifics>

<deferred>
## Deferred Ideas

- **Real per-tool cost attribution** (cost field on tool_result records + attribution model) — rejected for T6 (breaks no-new-persistence + patch posture). v0.3+ if a real costing model emerges.
- **Pending-edit queue / queued `/apply` / `/diff` of queued edits** — T1 territory (v0.2). T6 keeps git-tree + honest stub.
- **Cross-cwd in-process `/resume` rebind** (gate/cognition/tools re-bound to resumed session's cwd) — out of patch posture; `voss resume <id>` CLI covers cross-cwd.
- **Generating `/help` + `voss --help` from one shared slash-spec table** (drift-proof) — past "20-line wrapper" for a patch; revisit if the slash set grows materially.
- **Byte-weighted or token-weighted `--by-tool`** — implies a cost model that doesn't exist; even-split is the honest floor. Revisit only with a real attribution model (same gate as the first item).
- **Codex-format-clone `/help`** — SC#3 is satisfied by grouped + one-line-desc discoverability, not a literal Codex layout copy.

</deferred>

---

*Phase: T6-slash-debt*
*Context gathered: 2026-05-16 via /gsd:discuss-phase T6*
*Next step: /gsd:plan-phase T6 — research (confirm PRD §2.4 + ProbableValue) and plan*
