---
phase: V16-managed-docs-prompt-generation
plan: 03
type: execute
wave: 3
depends_on: ["V16-01", "V16-02"]
files_modified:
  - voss/sync.py
  - voss/cli.py
  - tests/cli/test_sync.py
autonomous: true
requirements: [R1, R3, R4]
must_haves:
  truths:
    - "voss sync run from a project root generates/updates .voss/docs/ and the VOSS.md workflow fence — all rendering through render_package_template, one SyncContext, fence body via write_fence_body (D-17)"
    - "Manifest .voss/sync-state.json (path -> sha256) written by sync, deterministic content, committed to the repo (D-10, D-12)"
    - "--force accepted in the sync() signature but scoped to prompts only; fence HashMismatch keeps its own flow, docs always regen (D-16)"
    - "A second consecutive voss sync on an unchanged project modifies zero files (byte-identical, R1)"
    - ".voss/docs/ contains cheatsheet, command reference (and review workflow when review.enabled) each with the generated header"
    - "A manual edit to a generated doc is overwritten by the next sync (machine-owned, R3)"
    - "VOSS.md workflow fence inserted when absent, regenerated when present, prose outside fence byte-identical, drift hits the existing HashMismatch path (R4)"
    - "voss sync --dry-run prints would-be statuses and writes nothing (D-14)"
    - "Output is per-file status lines + detected-facts block + trailing summary; exit 0 for all non-error outcomes (D-13/D-15)"
  artifacts:
    - path: "voss/sync.py"
      provides: "sync(cwd, *, dry_run, force) orchestrator: build SyncContext, render+diff+write docs, render+write fence, manifest bookkeeping"
      contains: "def sync"
    - path: "voss/cli.py"
      provides: "voss sync command registered on main group with --dry-run and --force flags"
      contains: "sync"
    - path: ".voss/sync-state.json"
      provides: "manifest: path -> sha256 bookkeeping (written by sync, committed per D-12)"
  key_links:
    - from: "voss/sync.py"
      to: "voss/harness/voss_md.py write_fence_body"
      via: "render fence body string then write_fence_body(adopt not passed)"
      pattern: "write_fence_body"
    - from: "voss/sync.py"
      to: "render_package_template"
      via: "render each doc + fence body from SyncContext"
      pattern: "render_package_template"
    - from: "voss/cli.py"
      to: "voss/sync.py sync"
      via: "@main.command('sync') delegates to sync()"
      pattern: "sync"
---

<objective>
Build the `voss sync` orchestrator and CLI: assemble the `SyncContext`, render the docs and fence body, diff against disk, apply per-artifact write policy (docs machine-owned, fence via write_fence_body), maintain the `.voss/sync-state.json` manifest, and emit greppable status output — idempotently.

Purpose: This is the phase's core deliverable (R1, R3, R4). Idempotency is the anchor: a second run on an unchanged tree must produce zero file changes. Prompt sync (R5/R6) is the stretch and lands in Plan 04 — this plan must NOT depend on it.
Output: `sync()` in `voss/sync.py`, the `voss sync` command in `voss/cli.py`, and an idempotency-anchored CLI test.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V16-managed-docs-prompt-generation/V16-SPEC.md
@.planning/phases/V16-managed-docs-prompt-generation/V16-CONTEXT.md
@.planning/phases/V16-managed-docs-prompt-generation/V16-PATTERNS.md
@voss/sync.py

<interfaces>
<!-- Reuse targets + CLI registration style. Extracted from codebase. -->

write_fence_body — voss/harness/voss_md.py:206-270:
  write_fence_body(path, fence_id="workflow", body=rendered_string)
  Inserts fence when absent (appends at EOF), regenerates in place when present,
  preserves content outside the fence, raises HashMismatch on drift unless adopt=True.
  D-16: sync does NOT pass adopt=True — fence drift resolution stays in `voss memory adopt`.

render_package_template — voss/template_render.py:22-28 (single entrypoint, D-17).

_scaffold_target render loop — voss/cli.py:445-473: template map -> render -> path-traversal
  guard `dest.is_relative_to(target_resolved)` -> write. Sync mirrors this loop + adds a
  diff/skip stage (read existing -> compare rendered string -> write only on difference).
  MIRROR the is_relative_to guard for every .voss/docs write (security: path traversal).

_write_text_atomic — voss/cli.py:99-115: mkstemp in dest dir -> write -> os.replace -> cleanup.
  Use for .voss/docs/* and .voss/sync-state.json. (write_fence_body self-handles VOSS.md atomically.)

sha256 — voss/harness/voss_md.py:232: hashlib.sha256(body.encode()).hexdigest() (manifest entries).

CLI registration — voss/cli.py:200-206 (main group), 476-488 (init command):
  @main.command("sync"); @click.option("--dry-run", is_flag=True); @click.option("--force", is_flag=True).
  Exit codes (D-15): exit 0 for changed/no-changes/skipped; raise click.exceptions.Exit(code=1)
  (voss/cli.py:421) or click.ClickException (voss/cli.py:451) ONLY on real failures (HashMismatch, IO).
  Status output via click.echo (stdout); warnings via click.echo(..., err=True).

SyncContext + build_sync_context — voss/sync.py (Plan 01).
Templates — voss/templates/docs/{cheatsheet,commands,review,voss_md_fence}.md.jinja (Plan 02).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: sync() orchestrator — docs render/diff/write + fence + manifest</name>
  <files>voss/sync.py</files>
  <read_first>
    - voss/sync.py (Plan 01 SyncContext + build_sync_context — extend, do not replace)
    - voss/cli.py (_scaffold_target render loop 445-473, _write_text_atomic 99-115, is_relative_to guard 466)
    - voss/harness/voss_md.py (write_fence_body 206-270, HashMismatch, sha256 line 232)
    - voss/templates/docs/ (the four templates from Plan 02 — resource paths + context fields they expect)
    - .planning/phases/V16-managed-docs-prompt-generation/V16-CONTEXT.md (D-08 review-skip, D-10/11/12 manifest, D-13 status, D-16 force scope)
  </read_first>
  <behavior>
    - sync(cwd) on a fresh project writes cheatsheet.md + commands.md (+ review.md only when review.enabled, D-08) under .voss/docs/, inserts the VOSS.md workflow fence, and writes .voss/sync-state.json — returning a per-artifact status list.
    - sync(cwd) called twice on an unchanged tree: the second call writes zero files (every artifact diffs equal -> status "unchanged"). [R1 anchor]
    - A manual edit to a generated doc is overwritten on the next sync (docs are machine-owned, status "written"). [R3]
    - VOSS.md prose outside the fence is byte-identical before/after sync; fence inserted when absent, regenerated when present (via write_fence_body). [R4]
    - sync(cwd, dry_run=True) computes the same statuses but writes nothing (no file mtime/content change). [D-14]
    - When review.enabled is False, review.md is neither rendered nor written and the fence's doc list excludes it (D-08).
    - Manifest records sha256 for written docs/fence bookkeeping; missing manifest does not block doc regeneration (docs are always machine-owned).
  </behavior>
  <action>
    Extend voss/sync.py with sync(cwd: Path, *, dry_run: bool = False, force: bool = False) -> a status result (list of per-artifact status records: path + one of written/unchanged/skipped/fence-updated, plus the detected-facts block from Plan 01's detection markers, D-03/D-13). Build the SyncContext via build_sync_context(cwd). Render each doc through render_package_template("voss", "templates/docs/<name>", asdict-or-context), targeting .voss/docs/ resolved via cognition.voss_dir(cwd); for every write, MIRROR the _scaffold_target is_relative_to path-traversal guard against the resolved .voss dir before writing (security). Diff stage (R1 idempotency): read the existing file if present, compare the rendered string byte-for-byte, and write via _write_text_atomic ONLY when different — equal => status "unchanged", no write. Docs are machine-owned (R3): always render+diff+write regardless of manifest/edits; no hash-guard on docs (that is prompts-only, Plan 04). Skip review.md entirely when review.enabled is False (D-08), and ensure the fence's generated-doc-list reflects the actual files written. Fence (R4): render voss_md_fence.md.jinja to a string, then call voss_md.write_fence_body(voss_md_path, fence_id="workflow", body=rendered) — do NOT pass adopt (D-16); let HashMismatch propagate. If VOSS.md is absent, write_fence_body creates it (it appends a fully-formed fence). Manifest (D-10/12): write .voss/sync-state.json (path -> sha256 via hashlib.sha256(body.encode()).hexdigest()) atomically; deterministic content so re-sync is no-churn. dry_run (D-14): run the identical diff pass and build statuses but perform zero writes (no doc write, no fence write, no manifest write). force is accepted in the signature but applies to prompts only (D-16) — it is wired in Plan 04; in this plan it has no effect on docs/fence. Do NOT implement prompt sync here (R5/R6 = Plan 04).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/cli/test_sync.py -x -q -k "orchestrator or idempot or fence or docs" 2>/dev/null || .venv/bin/python -c "from voss.sync import sync; import inspect; assert 'dry_run' in inspect.signature(sync).parameters and 'force' in inspect.signature(sync).parameters"</automated>
  </verify>
  <acceptance_criteria>
    - `voss.sync.sync` exists with `dry_run` and `force` keyword parameters.
    - `grep -n "is_relative_to" voss/sync.py` confirms the path-traversal guard is mirrored for .voss/docs writes (security T-V16-03).
    - `grep -n "write_fence_body" voss/sync.py` shows the fence is written via voss_md (no parallel marker logic); `grep -n "adopt=True" voss/sync.py` returns nothing (D-16).
    - `grep -n "render_package_template" voss/sync.py` shows every artifact rendered through the single entrypoint; `grep -n "Template(" voss/sync.py` returns nothing.
    - sync writes .voss/sync-state.json via _write_text_atomic (or equivalent atomic helper): `grep -nE "sync-state.json" voss/sync.py` returns a match.
    - No prompt-sync logic in this plan: `grep -nE "\\.voss/prompts|reviewer_a|em_system" voss/sync.py` returns nothing.
  </acceptance_criteria>
  <done>sync() renders+diffs+writes the machine-owned docs, writes the VOSS.md fence via write_fence_body, maintains the manifest, supports dry-run, and is byte-idempotent on unchanged trees.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: voss sync CLI command + idempotency/fence tests</name>
  <files>voss/cli.py, tests/cli/test_sync.py</files>
  <read_first>
    - voss/cli.py (init command 476-488, main group 200-206, Exit/ClickException usage 421/451)
    - voss/sync.py (sync() signature + status result shape from Task 1)
    - tests/cli/test_init.py (CliRunner + isolated_filesystem pattern)
    - tests/harness/test_voss_md_fence.py (fence fixtures, pytest.raises(HashMismatch))
    - .planning/phases/V16-managed-docs-prompt-generation/V16-CONTEXT.md (D-13 status lines, D-14 dry-run, D-15 exit codes)
  </read_first>
  <behavior>
    - `voss sync` from a project root prints per-file status lines + a detected-facts block + a trailing summary count, exit 0 (D-13/D-15).
    - `voss sync` run twice in a fixture project: the second run reports no changes and no files are modified (mtime/content unchanged). [R1 acceptance]
    - `voss sync --dry-run` prints would-be statuses and writes nothing. [D-14]
    - Editing a generated doc then re-running `voss sync` overwrites the doc (machine-owned). [R3 acceptance]
    - Fence: inserted when VOSS.md/fence absent, regenerated when present, prose outside the fence byte-identical; corrupting the fence hash triggers the existing HashMismatch refusal path (nonzero exit), not silent overwrite. [R4 acceptance]
    - Exit 0 for changed / no-changes / skipped outcomes; nonzero only on HashMismatch / IO failure. [D-15]
  </behavior>
  <action>
    Register @main.command("sync") in voss/cli.py mirroring the init command: --dry-run and --force as click.option(is_flag=True, default=False). The command resolves the project root (cwd) and delegates to voss.sync.sync(cwd, dry_run=dry_run, force=force). Render the status result as per-file status lines via click.echo (stdout) — one of written/unchanged/skipped (edited)/fence-updated per file — plus the detected-facts block (e.g. `project.type: python (detected)`, D-03) and a trailing summary count (D-13). Emit warnings via click.echo(..., err=True). Exit codes (D-15): return/exit 0 for all non-error outcomes (changes, no-changes, skipped-edited); on voss_md HashMismatch raised by sync(), surface it as a failure (catch and raise click.ClickException with the fence-id + the `voss memory adopt` remediation, or let it propagate to a nonzero exit) — warnings are NOT failures. Write tests/cli/test_sync.py using CliRunner + isolated_filesystem (per test_init.py): (1) idempotency — invoke sync twice in a fixture project, assert second run's output reports no changes and the doc files + VOSS.md are byte-identical between runs (R1); (2) machine-owned — edit a generated doc, re-run, assert it is overwritten (R3); (3) fence insert-when-absent and regenerate-when-present with prose-outside-fence byte-identical (R4); (4) fence drift — corrupt the recorded fence hash, run sync, assert nonzero exit / HashMismatch path (R4); (5) --dry-run writes nothing (D-14); (6) exit code 0 on the no-changes second run (D-15). Build a worktree-free fixture project (init scaffold or a tmp dir with a minimal .voss/config.yml + VOSS.md).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/cli/test_sync.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - tests/cli/test_sync.py passes under .venv/bin/python.
    - Test invokes `voss sync` twice and asserts the second invocation produces byte-identical doc files AND byte-identical VOSS.md (R1 idempotency anchor).
    - Test asserts editing a generated doc then re-syncing overwrites it (R3 machine-owned).
    - Test asserts fence inserted when absent + regenerated when present + prose outside fence unchanged (R4).
    - Test asserts corrupting the fence hash yields a nonzero exit (HashMismatch path, R4/D-15) rather than silent overwrite.
    - Test asserts `voss sync --dry-run` leaves files unmodified (D-14) and that the no-changes run exits 0 (D-15).
    - `voss sync --help` runs: `.venv/bin/python -m voss sync --help` exits 0 (command registered).
  </acceptance_criteria>
  <done>`voss sync` is registered, emits greppable status + detected-facts + summary, exits 0 on non-errors and nonzero on fence drift, and is proven byte-idempotent across two runs.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| sync write targets -> project filesystem | rendered docs/manifest written into .voss/ under the project root |
| VOSS.md fence -> on-disk human-edited file | machine write into a file users also edit; hash gate guards drift |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V16-03 | Tampering | .voss/docs + manifest write paths | mitigate | mirror _scaffold_target `dest.is_relative_to(voss_dir)` guard before every write; refuse writes resolving outside the project .voss dir; atomic _write_text_atomic prevents partial writes |
| T-V16-06 | Tampering | VOSS.md fence overwrite | mitigate | all fence writes route through write_fence_body (no regex surgery); drift triggers HashMismatch refusal (adopt not passed, D-16); content outside fence provably byte-identical (test) |
| T-V16-07 | Tampering | .voss/sync-state.json manifest parse on re-sync | mitigate | manifest read tolerates missing/malformed JSON (treat as absent); deterministic content prevents churn; docs regenerate regardless of manifest state |
| T-V16-SC | Tampering | npm/pip/cargo installs | accept | no new dependencies; click/jinja2/pyyaml already present; no install task |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/cli/test_sync.py -q` green (idempotency + machine-owned + fence insert/regenerate/drift + dry-run + exit codes).
- `.venv/bin/python -m voss sync --help` exits 0.
- `grep -n "write_fence_body" voss/sync.py` present; `grep -n "Template(" voss/sync.py` empty.
</verification>

<success_criteria>
- `voss sync` regenerates .voss/docs + the VOSS.md workflow fence + manifest; second run on unchanged tree changes zero files (R1).
- Generated docs are machine-owned (edits overwritten, R3); fence insert/regenerate/prose-preservation/drift-refusal behave per R4.
- --dry-run writes nothing; exit codes follow D-15; status output follows D-13.
- All rendering through render_package_template; all fence writes through write_fence_body.
- No dependency on prompt sync (R5/R6) — that lands in Plan 04.
</success_criteria>

<output>
Create `.planning/phases/V16-managed-docs-prompt-generation/V16-03-SUMMARY.md` when done
</output>
