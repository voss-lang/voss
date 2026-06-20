---
phase: BOS1-planning-audit-and-archive-map
plan: 02
type: execute
wave: 2
depends_on:
  - BOS1-01
files_modified:
  - .planning/archive/
  - .planning/AUDIT-INDEX.md
autonomous: false
requirements:
  - BOS-PLAN-02
must_haves:
  truths:
    - "No move or delete happens until AUDIT-INDEX.md exists and Ben has approved the classifications"
    - "Every archive-candidate move is approved per-item by Ben before execution"
    - "Every delete is approved per-item by Ben before execution (no batch auto-delete)"
    - "Moved docs land in .planning/archive/ (created if absent) — move is preferred over delete"
    - "AUDIT-INDEX.md is updated to reflect the new location/state of every doc that was moved or deleted"
  artifacts:
    - path: ".planning/archive/"
      provides: "Destination directory for archive-candidate docs kept-but-archived"
  key_links:
    - from: ".planning/AUDIT-INDEX.md"
      to: ".planning/archive/"
      via: "post-move location note in each moved doc's row"
      pattern: "archive/"
---

<objective>
Execute the approved cleanup: after Ben reviews `AUDIT-INDEX.md`, move
archive-candidate docs into `.planning/archive/` and delete only the
explicitly-signed-off dead docs — one item at a time, human-gated.

Purpose: Complete BOS-PLAN-02's "before archival, deletion, or supersession"
mandate by performing the archive/delete that the index now justifies. The
index-first + per-item-approval ordering is exactly what makes this NOT blind
deletion (PROJECT.md Out-of-Scope bar).

Output: docs relocated into `.planning/archive/` and/or removed per approval;
`AUDIT-INDEX.md` updated to record each doc's new location/state.

CRITICAL git-safety: this repo forbids git add/commit/mv/rm and any file
move/delete without explicit human confirmation. Every move/delete in this plan
is gated behind a blocking human checkpoint and executed only on per-item
approval. Nothing here runs autonomously.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/AUDIT-INDEX.md
@.planning/phases/BOS1-planning-audit-and-archive-map/BOS1-CONTEXT.md
@.planning/PROJECT.md
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 1: Approval gate — Ben reviews AUDIT-INDEX.md and authorizes per-item actions</name>
  <read_first>
    - .planning/AUDIT-INDEX.md (the full index produced by BOS1-01 — both tables + appendix + verification notes)
    - .planning/phases/BOS1-planning-audit-and-archive-map/BOS1-CONTEXT.md (D-04/D-05: index-first, per-item approval, move>delete)
  </read_first>
  <what-built>
    BOS1-01 produced .planning/AUDIT-INDEX.md: a two-axis classification of all 25
    loose docs + 10 phase tracks, plus an external appendix and BOS-PLAN-01/03
    verification notes. No files have been moved or deleted yet.
  </what-built>
  <how-to-verify>
    1. Open .planning/AUDIT-INDEX.md.
    2. Review every row classified `archive-candidate` — these are MOVE candidates
       (destination .planning/archive/).
    3. Identify any rows you want DELETED outright (clearly-dead docs only).
    4. For each archive-candidate, reply with one of: "move", "delete", or "keep".
    5. Anything not explicitly approved for move/delete stays in place.
  </how-to-verify>
  <acceptance_criteria>
    - Ben has explicitly stated, per archive-candidate item, whether to move, delete, or keep it.
    - No file has been touched before this approval is given.
    - The set of approved moves and the set of approved deletes are unambiguously recorded for Task 2/3.
  </acceptance_criteria>
  <resume-signal>Provide a per-item decision list (move / delete / keep). Type "none" to skip all cleanup this phase.</resume-signal>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 2: Execute approved MOVES into .planning/archive/</name>
  <files>.planning/archive/, .planning/AUDIT-INDEX.md</files>
  <read_first>
    - .planning/AUDIT-INDEX.md (the approved move list from Task 1)
    - .planning/phases/BOS1-planning-audit-and-archive-map/BOS1-CONTEXT.md (D-04 archive destination)
  </read_first>
  <action>
    For ONLY the items Ben approved for "move" in Task 1: create .planning/archive/
    if it does not already exist, then move each approved doc into .planning/archive/
    preserving filename. This requires a git/file write — present the exact command
    set (mkdir + the per-file moves) to Ben and execute only on explicit confirmation
    per the repo git-safety rule. Use `git mv` if Ben wants history-preserving moves
    AND has approved git writes; otherwise a plain filesystem move, with Ben staging
    the change himself. After each move, update that doc's row in AUDIT-INDEX.md to
    note the new path (e.g. append "→ archive/<name>" in the supersession/location
    cell or a status note). Do NOT move anything not on the approved list. Do NOT
    delete anything in this task.
  </action>
  <verify>
    <human-check>For each approved move: the file now exists under .planning/archive/ and no longer at its old path; its AUDIT-INDEX.md row reflects the new location. Items not approved for move are untouched.</human-check>
    <!-- Machine confirmation ALONGSIDE the human gate (human approval remains the gate; this just sanity-checks the result). Replace N with the count of items Ben approved for "move" in Task 1; the archive dir's file count must equal it. Then confirm the index recorded the new archive/ paths. -->
    <automated>test -d .planning/archive && echo "archive count: $(ls -1 .planning/archive/ | wc -l | tr -d ' ') (must equal approved-move count N)"; echo "index archive/ refs: $(grep -c 'archive/' .planning/AUDIT-INDEX.md) (must be >= approved-move count N)"</automated>
  </verify>
  <acceptance_criteria>
    - .planning/archive/ exists.
    - Every doc Ben approved for "move" is present under .planning/archive/ and absent from its original location.
    - The number of files in .planning/archive/ equals the count of items Ben approved for "move" (machine check: `ls .planning/archive/ | wc -l` == N).
    - No doc that was NOT approved for move has changed location.
    - No file was deleted by this task.
    - AUDIT-INDEX.md rows for moved docs record the new archive/ path (machine check: `grep -c 'archive/' AUDIT-INDEX.md` >= N).
  </acceptance_criteria>
  <done>All and only the approved docs are in .planning/archive/ (count matches approvals); index updated with archive/ paths; nothing deleted.</done>
</task>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 3: Execute approved DELETES (clearly-dead docs, per-item sign-off)</name>
  <files>.planning/AUDIT-INDEX.md</files>
  <read_first>
    - .planning/AUDIT-INDEX.md (the approved delete list from Task 1, plus any moves recorded by Task 2)
    - .planning/PROJECT.md (Out-of-Scope: no deletion without an audit/archive index — the index now exists, satisfying the gate)
  </read_first>
  <action>
    For ONLY the items Ben explicitly approved for "delete" in Task 1 (clearly-dead
    docs): present the exact per-file delete command(s) to Ben and execute each only
    on individual confirmation — no batch auto-delete, honoring the repo git-safety
    rule (no git rm / file removal without explicit confirmation). After each
    confirmed delete, update that doc's row in AUDIT-INDEX.md to mark it deleted
    (e.g. status note "deleted <date>, was archive-candidate") so the index remains
    the record of what happened. If Ben approved nothing for delete, this task is a
    no-op and the index is left as-is. Move is preferred over delete (D-04): if in
    doubt, it should already have been a move in Task 2, not a delete here.
  </action>
  <verify>
    <human-check>Every file Ben approved for deletion is gone; every file NOT approved for deletion still exists; AUDIT-INDEX.md records each deletion. If no deletes were approved, no files were removed and the index is unchanged.</human-check>
    <!-- Machine confirmation ALONGSIDE the human gate (human approval remains the gate). For each filename Ben approved for delete, confirm it no longer exists on disk; confirm the index records a "deleted" note for each. -->
    <automated>echo "for each approved-delete filename F: test ! -e .planning/F should pass"; echo "index deleted-notes: $(grep -ci 'deleted' .planning/AUDIT-INDEX.md) (must be >= approved-delete count; 0 if none approved)"</automated>
  </verify>
  <acceptance_criteria>
    - Only docs with explicit per-item delete sign-off were removed (machine check: each approved-delete path satisfies `test ! -e`).
    - No doc was deleted that lacked individual approval.
    - No delete occurred before AUDIT-INDEX.md existed and was approved (Task 1).
    - AUDIT-INDEX.md records each deletion as a status note (machine check: `grep -ci 'deleted' AUDIT-INDEX.md` >= approved-delete count; 0 when none approved).
  </acceptance_criteria>
  <done>Approved dead docs deleted with per-item sign-off (each confirmed gone on disk); index updated with deleted-notes; no unapproved removals.</done>
</task>

</tasks>

<verification>
- No move/delete occurred before Task 1's approval gate (structural: Tasks 2-3 depend on Task 1, whole plan is wave 2 behind BOS1-01).
- `.planning/archive/` contains exactly the approved-move docs (count == N).
- Only per-item-approved docs were deleted (each approved-delete path `test ! -e`).
- AUDIT-INDEX.md reflects every move (new archive/ path) and every delete (deleted note).
- `git status .planning/` changes correspond exactly to the approved action list — nothing extra.
</verification>

<success_criteria>
The cleanup BOS-PLAN-02 authorizes is done without any blind action: every move
and delete traces to a per-item approval against the index, machine checks confirm
the archive count and deletions match the approval list, the index records the
final state of each doc, archive is preferred over delete, and the repo git-safety
rule is honored throughout (no autonomous file/git writes — human approval stays
the gate).
</success_criteria>

<output>
Create `.planning/phases/BOS1-planning-audit-and-archive-map/BOS1-02-SUMMARY.md` when done.
</output>
