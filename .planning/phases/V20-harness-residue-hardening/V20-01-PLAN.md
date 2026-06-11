---
phase: V20-harness-residue-hardening
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/sync.py
  - voss/cli.py
  - tests/cli/test_sync.py
autonomous: true
requirements: [VRES-01]
must_haves:
  truths:
    - "A hand-edited managed doc makes `voss sync --check` exit non-zero and name the stale artifact; clean state exits 0"
    - "`--check` writes NOTHING — no doc, no fence, no prompt, no sync-state.json mutation (byte-compare tree before/after)"
    - "Plain `voss sync` no longer silently clobbers a hand-edited managed doc: it warns + skips like the prompt path, --force overwrites"
  artifacts:
    - path: "voss/sync.py"
      provides: "check mode + managed-doc edit-guard mirroring the prompt guard at sync.py:303"
      contains: "def check"
    - path: "voss/cli.py"
      provides: "--check flag on sync_cmd, mutually exclusive with --force, non-zero exit on drift"
      contains: "--check"
    - path: "tests/cli/test_sync.py"
      provides: "RED-first tests: edited-doc drift detected, nothing written, clobber-guard honored"
      contains: "test_sync_check_detects_edited_managed_doc"
  key_links:
    - from: "voss/cli.py"
      to: "voss.sync.check"
      via: "sync_cmd --check branch raising SystemExit(1) with stale list"
      pattern: "check"
---

<objective>
Turn the write-only sync-state.json manifest into an enforceable drift gate, and close the
managed-doc silent-clobber hole.

Today hashes are persisted (sync.py manifest writes for docs ~256, fence ~278, prompts ~320)
but only the prompt loop ever reads them back (sync.py:303). `voss sync` has no verify mode:
--dry-run always exits 0 (cli.py:491), so CI cannot gate on "generated artifacts match
templates + nobody hand-edited a machine-owned doc". Worse, the managed-docs loop regenerates
via _diff_write with no edit-guard — user edits to machine-owned docs are silently destroyed,
while prompts get the polite hash-guard treatment.
</objective>

<context>
- Manifest read: `_read_manifest` voss/sync.py:180, loaded at :235 as `recorded_hashes`.
- Prompt guard to mirror: voss/sync.py:298-320 (`edited = recorded is None or on_disk_hash != recorded`).
- Managed docs loop (no guard): voss/sync.py:254-267. Fence: voss/sync.py:278-285 — fence
  already has its own HashMismatch guard via voss_md.write_fence_body; --check must report
  fence drift WITHOUT raising.
- CLI: sync_cmd voss/cli.py:491-523.
- Existing tests: tests/cli/test_sync.py — extend, match its fixtures/tmp-project style.
</context>

<tasks>

## Task 1 — RED tests (commit 1: `test(sync): RED drift-gate + clobber-guard cases`)
In tests/cli/test_sync.py add failing tests:
1. `test_sync_check_detects_edited_managed_doc` — run sync, hand-edit a managed doc under
   docs_dir, run `voss sync --check` via CliRunner → exit code != 0, output names the doc path.
2. `test_sync_check_clean_exits_zero` — fresh sync then `--check` → exit 0, "in sync" style line.
3. `test_sync_check_writes_nothing` — snapshot mtimes/bytes of .voss tree + docs + VOSS.md,
   run `--check` against drifted state, assert byte-identical tree (including sync-state.json).
4. `test_sync_check_detects_stale_template_output` — bump a value feeding ctx_map (or monkeypatch
   template render) so rendered != recorded → `--check` non-zero (catches outdated artifacts,
   not just hand edits).
5. `test_sync_skips_edited_managed_doc_without_force` — hand-edit managed doc, plain `voss sync`
   → doc content preserved, status `skipped (edited)`, warning on stderr; `--force` overwrites.
6. `test_sync_check_reports_fence_drift` — hand-edit the VOSS.md fence body → `--check` non-zero
   listing `VOSS.md#<fence_id>`, no HashMismatch traceback, no adopt-prompt requirement.

## Task 2 — `check()` in voss/sync.py (commit 2: `feat(sync): --check drift gate`)
- Add `check(cwd: Path) -> CheckResult` (statuses list + `drifted: list[str]`). Reuse the
  render pipeline read-only: render every managed doc + fence + prompt, compute three-way
  comparison per artifact against `recorded_hashes` and on-disk bytes:
  - missing on disk → `missing`
  - on-disk hash != recorded → `edited` (hand edit)
  - rendered hash != recorded → `stale` (templates/config moved on)
  - all equal → `ok`
- NO writes anywhere on this path (no manifest rewrite, no fence write, no unlink of stale
  review.md — report it as `stale` instead).
- Refactor shared render-and-hash enumeration out of `sync()` into a helper both paths call,
  rather than duplicating the doc/fence/prompt loops. Keep `sync()` behavior byte-identical
  (existing tests are the guard).

## Task 3 — managed-doc edit-guard (same commit as Task 2 or separate `fix(sync): guard managed docs`)
- In the managed-docs loop (sync.py:254-267): before `_diff_write`, if dest exists and
  on-disk hash != recorded hash for that rel path (and != new rendered hash), treat as edited:
  warn + `skipped (edited)` + keep recorded hash in manifest (mirror prompt semantics
  sync.py:303-312 exactly, incl. --force override and D-11 no-evidence=>edited rule).

## Task 4 — CLI wiring (commit 3: `feat(cli): voss sync --check`)
- Add `--check` flag to sync_cmd (voss/cli.py:491). `--check` + `--force` → UsageError.
  `--check` + `--dry-run` → UsageError (check is already read-only).
- On drift: echo one line per drifted artifact (`<path>: <edited|stale|missing>`), summary
  line `N artifact(s) drifted`, exit 1. Clean: `all artifacts in sync`, exit 0.

## Task 5 — GREEN + suite
- `.venv/bin/python -m pytest tests/cli/test_sync.py` green; full suite spot:
  `.venv/bin/python -m pytest tests/cli tests/harness/test_voss_md*.py -q` (fence guard untouched).
</tasks>

<verification>
- Hand-edited managed doc → `voss sync --check` exits non-zero listing it (the phase's
  headline verify line).
- `--check` provably write-free (test 3).
- Prompt-guard parity: managed docs now honor the same D-11 hash-evidence rule.
</verification>
