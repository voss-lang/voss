# Phase T6: PRD §2.4 Slash Debt — Discussion Log

**Date:** 2026-05-16
**Mode:** discuss (default)
**Human reference only — NOT consumed by downstream agents.**

---

## Scout Finding (drove the framing)

All 7 slashes ALREADY implemented in `voss/harness/cli.py:569-790`. 5 functional, 2 honest-stubs (`/apply`, `/cost --by-tool`). Reframed T6 from greenfield → harden+test+discoverability. Presented to user as such.

---

## Areas Selected

User multi-selected all 4: SLASH-07 --by-tool scope, /apply+/diff queue-dependency, /resume scope, help discoverability.

---

## Area 1 — SLASH-07 /cost --by-tool scope

**Context given:** provider bills per-turn not per-tool; `RunRecorder.cost_usd` per-iteration; true per-tool cost is fabricated; T4 deferred here saying it needs `Recorder.tool_result.cost_usd` (= new persistence, violates T6 constraint).

**Options:** Derived approximation labeled (Rec) / Honest stub stays / Real per-tool attribution

**Selected:** Derived approximation, labeled

**→ D-01.** Even split of turn cost across that turn's tool_results, aggregated per tool name, `~approx` labeled, from existing RunRecord. Even-split chosen over byte-weight (byte-weight implies a nonexistent precision model). Replaces the current "lands with T4" stub branch.

---

## Area 2 — /apply + /diff queue-dependency

**Context given:** pending-edit queue is T1 (v0.2), ships AFTER this v0.1.1 patch; current /diff=git diff, /discard=git checkout, /apply=stub.

**Options:** Keep git-tree + honest /apply stub (Rec) / Pull minimal queue into T6 / Drop /apply

**Selected:** Keep git-tree semantics + honest /apply stub

**→ D-02.** /diff + /discard stay git-tree (already coded, real). /apply stays honest stub. T1 upgrades /diff+/apply later. No fake queue.

---

## Area 3 — /resume scope

**Context given:** `_resume` swaps state in live REPL, warns + proceeds on cross-cwd, defers true cross-cwd to `voss resume <id>` CLI (cli.py:1648).

**Options:** Keep live-REPL + cross-cwd warning (Rec) / Hard-block cross-cwd / Full cross-cwd rebind

**Selected:** Keep live-REPL-only + cross-cwd warning

**→ D-03.** Keep current behavior. T6 adds tests + verifies `/resume <name>` resolves alongside `<id>`. No in-process cwd/gate/tool rebind.

---

## Area 4 — Help discoverability (SC#3)

**Context given:** slashes are REPL constructs not CLI subcommands; SC#3 wants `voss --help` to list them + "match Codex."

**Options:** /help canonical + CLI signpost (Rec) / Duplicate list into voss --help / Generate both from one registry

**Selected:** In-REPL /help canonical; CLI --help points to it

**→ D-04.** /help grouped (Editing/Session/Insight/Control) + one-line desc each. `voss --help` epilog one signpost line. "Matches Codex" = grouped+described, not a layout clone. No two-place duplication.

---

## Derived Decisions (not directly asked)

- **D-05** T6 = harden+test+register-verify, not greenfield (scout finding).
- **D-06** T4↔T6 --by-tool ownership: T6 ships first (v0.1.1) → owns both --by-model + --by-tool; T4 D-09 placeholder edit obsolete. T6 only notes it; edits no T4 file.
- **D-07** /why already meets SC#2 (no provider call). Research must confirm PRD ProbableValue breakdown expectation vs current single confidence float (PRD .vscode/voss_v_0_1_scope_lock.md:712,1213).
- **D-08** No new persistence end-to-end (cross-cutting honored).

---

## Deferred / Scope-Redirected

CONTEXT `<deferred>`: real per-tool attribution, pending-edit queue (T1), cross-cwd rebind, shared slash-spec table, byte/token-weighted --by-tool, Codex-format clone. No scope creep raised by user.

---

## Claude's Discretion Items

CONTEXT `<decisions>` § Claude's Discretion: exact /help group names, zero-tool-result iteration skip, ~approx label placement, /resume id/name disambiguation order, test-file choice (extend test_repl_slash.py vs new test_t6_slashes.py — `test_cost_by_tool_is_honest_stub` MUST be updated since D-01 de-stubs --by-tool).
