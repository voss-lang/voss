---
phase: V16-managed-docs-prompt-generation
plan: 04
type: execute
wave: 4
depends_on: ["V16-03"]
files_modified:
  - voss/sync.py
  - voss/harness/board/reviewer_a.py
  - voss/harness/board/reviewer_b.py
  - voss/harness/em/llm.py
  - voss/harness/prompt_override.py
  - tests/harness/test_prompt_override.py
  - tests/cli/test_sync.py
autonomous: true
requirements: [R5, R6]
must_haves:
  truths:
    - "Sync writes reviewer_a, reviewer_b, and em prompts as plain .txt files under .voss/prompts/ (jinja suffix stripped)"
    - "At runtime the prompt loader prefers the project copy when present, applying ${AGENT}/${PROJECT}/${WORKSPACE} substitution via plain str.replace"
    - "With no project copy, prompt-load behavior is byte-unchanged from today (package template)"
    - "Sync records a content hash per synced prompt in .voss/sync-state.json; an unedited prompt may be regenerated; an edited prompt (hash drift) is skipped with a warning naming the file"
    - "voss sync --force overwrites edited prompts; a missing manifest treats existing prompts as edited (skip+warn, --force to re-adopt)"
  artifacts:
    - path: "voss/harness/prompt_override.py"
      provides: "load_prompt(name, package_default) -> project copy (with ${} substitution) or package default"
      contains: "def load_prompt"
    - path: "voss/sync.py"
      provides: "prompt sync loop with hash-guard wired into sync()"
      contains: "prompts"
  key_links:
    - from: "voss/harness/board/reviewer_a.py"
      to: "voss/harness/prompt_override.py load_prompt"
      via: "load-time lookup replacing the module-level render_package_template constant"
      pattern: "load_prompt"
    - from: "voss/sync.py prompt loop"
      to: ".voss/sync-state.json"
      via: "sha256 hash-guard: skip+warn on drift, --force overwrites"
      pattern: "force"
---

<objective>
Land the stretch deliverable (R5/R6): sync the 3 reviewer/EM prompts into `.voss/prompts/` as editable plain-text copies that override package templates at load time, guarded by a content-hash so user edits are never silently clobbered.

Purpose: Makes Voss prompts project-tunable without Jinja knowledge — runtime substitution is plain `${}` string replace (D-18), and the hash-guard (R6) extends voss_md's machine-write-refuses-on-drift philosophy to prompts. This is the STRETCH plan; Plans 01-03 (the phase core) do not depend on it.
Output: `voss/harness/prompt_override.py` loader, the 3 render sites converted to load-time lookups, the prompt-sync hash-guard loop in `sync()`, and override/hash-guard tests.
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
<!-- The 3 render sites + substitution analog + hash-guard pattern. Extracted from codebase. -->

The 3 synced prompts (currently module-level constants, no override today):
  voss/harness/board/reviewer_a.py:38-42  -> REVIEWER_A_ROLE_PROMPT
    = render_package_template("voss", "templates/prompts/reviewer_a_role.txt.jinja", {})
  voss/harness/board/reviewer_b.py:45-49  -> REVIEWER_B_SYSTEM
    = render_package_template("voss", "templates/prompts/reviewer_b_system.txt.jinja", {})
  voss/harness/em/llm.py:16-20            -> EM_SYSTEM
    = render_package_template("voss", "templates/prompts/em_system.txt.jinja", {})
  The other 7 prompts stay package-internal — DO NOT touch them (SPEC out-of-scope).

runtime substitution analog — voss/harness/agent.py:358-360 _compose_loop_system:
  str.replace placeholder fill (NOT f-string, NOT Jinja). D-18: synced prompts use
  shell-style ${AGENT} / ${PROJECT} / ${WORKSPACE}, filled at load time by plain str.replace.
  Constraint: NOT Jinja at runtime so StrictUndefined cannot detonate on user edits.

hash-guard analog — voss/harness/voss_md.py:241-249 (HashMismatch "refuse without hash
  evidence") + sha256 line 232. D-11: missing manifest => treat existing prompt as edited
  => skip+warn, --force to re-adopt. Never clobber without hash evidence.

sync() + manifest — voss/sync.py (Plan 03): the sync orchestrator + .voss/sync-state.json
  (path -> sha256) already exist; this plan adds the prompt loop into the same status flow.
  --force is already in sync()'s signature (Plan 03) and applies to prompts ONLY (D-16).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: prompt_override loader + convert the 3 render sites to load-time lookup</name>
  <files>voss/harness/prompt_override.py, voss/harness/board/reviewer_a.py, voss/harness/board/reviewer_b.py, voss/harness/em/llm.py, tests/harness/test_prompt_override.py</files>
  <read_first>
    - voss/harness/board/reviewer_a.py (REVIEWER_A_ROLE_PROMPT constant 38-42)
    - voss/harness/board/reviewer_b.py (REVIEWER_B_SYSTEM constant 45-49)
    - voss/harness/em/llm.py (EM_SYSTEM constant 16-20)
    - voss/harness/agent.py (_compose_loop_system str.replace analog 358-360)
    - voss/template_render.py (render_package_template — package default path)
    - .planning/phases/V16-managed-docs-prompt-generation/V16-CONTEXT.md (D-18 ${} syntax)
  </read_first>
  <behavior>
    - load_prompt(name) with a project copy at .voss/prompts/<name>.txt present returns the project copy's content with ${AGENT}/${PROJECT}/${WORKSPACE} replaced by the provided runtime values (plain str.replace).
    - load_prompt(name) with NO project copy returns the package-template render — byte-identical to today's constant (R5 "absent copy = unchanged behavior").
    - Each of the 3 consumers (reviewer_a, reviewer_b, em) resolves its prompt through load_prompt at load time, so a project copy is honored.
    - The other 7 package prompts are untouched.
  </behavior>
  <action>
    Create voss/harness/prompt_override.py with load_prompt(name, *, resource, cwd=None, runtime_vars=None) -> str: if a project copy exists at <voss_dir(cwd)>/prompts/<name>.txt, read it and apply plain str.replace for ${AGENT}/${PROJECT}/${WORKSPACE} from runtime_vars (D-18 — NOT Jinja, so user edits cannot trigger StrictUndefined); otherwise fall back to render_package_template("voss", resource, {}) so behavior is byte-identical to today when no project copy exists (R5). Convert the 3 render sites: in reviewer_a.py, reviewer_b.py, and em/llm.py, replace the module-level render_package_template(...) constants with load-time lookups via load_prompt (a function call or lazy accessor — the project copy must be checked at load, per PATTERNS "Module-level constants become lazy/load-time lookups"). Preserve the existing exported names/usage so callers are unaffected; where runtime values (${AGENT} etc.) are not known at module import, the load_prompt call must happen where those values are available (the render/consumption site), not frozen at import — executor chooses the minimal seam that keeps current call sites working. Do NOT alter the other 7 prompts. Write tests/harness/test_prompt_override.py: (1) project copy present -> load_prompt returns substituted project content; (2) no project copy -> returns the package render byte-identical to render_package_template of the same resource; (3) ${} placeholders are filled by str.replace (assert a literal ${AGENT} in a project copy becomes the supplied value).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_prompt_override.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/test_prompt_override.py passes under .venv/bin/python.
    - Test asserts no-project-copy load_prompt output equals render_package_template("voss", resource, {}) (R5 unchanged-behavior).
    - Test asserts a project copy containing ${AGENT} renders with the literal replaced (str.replace, D-18); `grep -n "str.replace\\|\\.replace(" voss/harness/prompt_override.py` confirms plain replace, and `grep -n "render_package_template\\|Template(" voss/harness/prompt_override.py` shows only the package-default fallback uses render_package_template (no second Jinja env, no runtime Jinja on the project copy).
    - reviewer_a.py, reviewer_b.py, em/llm.py each reference load_prompt: `grep -ln "load_prompt" voss/harness/board/reviewer_a.py voss/harness/board/reviewer_b.py voss/harness/em/llm.py` lists all three.
    - The other 7 prompts under voss/templates/prompts/ are not newly wired: only the 3 named files import load_prompt.
  </acceptance_criteria>
  <done>load_prompt prefers the project copy with ${}-substitution and falls back byte-identically to the package template; the 3 render sites resolve through it at load time; the other 7 prompts untouched.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: prompt-sync hash-guard loop in sync() + force/skip tests</name>
  <files>voss/sync.py, tests/cli/test_sync.py</files>
  <read_first>
    - voss/sync.py (Plan 03 sync() orchestrator + manifest write + force param)
    - voss/harness/voss_md.py (sha256 line 232, HashMismatch refuse-on-drift philosophy 241-249)
    - voss/templates/prompts/ (reviewer_a_role.txt.jinja, reviewer_b_system.txt.jinja, em_system.txt.jinja — the 3 to sync)
    - tests/cli/test_sync.py (Plan 03 fixture project + CliRunner pattern)
    - .planning/phases/V16-managed-docs-prompt-generation/V16-CONTEXT.md (D-10 manifest, D-11 missing-manifest, D-16 --force prompts-only)
  </read_first>
  <behavior>
    - sync() writes the 3 synced prompts as plain .txt under .voss/prompts/ (jinja suffix stripped), records each file's sha256 in .voss/sync-state.json.
    - Re-sync on an unedited prompt (manifest hash matches on-disk) regenerates/leaves it unchanged (status unchanged/written), still idempotent.
    - Editing a synced prompt then re-running sync: the edited file's on-disk hash != recorded hash -> skipped with a warning naming the file (status "skipped (edited)"), file left unchanged.
    - `voss sync --force` overwrites edited prompts (status written), refreshing the manifest hash.
    - A missing manifest treats existing prompt files as edited: skip+warn, --force re-adopts (D-11).
    - Prompt skip is a warning, not a failure: exit code stays 0 (D-15).
  </behavior>
  <action>
    Extend sync() in voss/sync.py with a prompt-sync loop (after the doc/fence loops, reusing the same SyncContext + manifest). For each of the 3 prompts: render the package template to a string (sync-time Jinja bakes project facts; ${} runtime placeholders pass through untouched), target .voss/prompts/<name>.txt (strip the .jinja suffix). Apply the hash-guard (R6/D-11): compute sha256 of the on-disk file (if present); compare against the recorded hash in .voss/sync-state.json. If the file is absent -> write it (status written) and record the hash. If present and on-disk hash == recorded hash (unedited) -> regenerate via the same diff pass (write only if rendered differs; else unchanged). If present and on-disk hash != recorded hash (edited) OR the manifest is missing/has no entry for it (D-11 treat-as-edited) -> SKIP and emit a warning naming the file via click.echo(..., err=True) (status "skipped (edited)"), unless force=True (D-16) in which case overwrite and record the new hash. After the loop, write the refreshed manifest (atomic). dry_run performs the same hash comparisons and statuses but writes nothing (consistent with Plan 03). Prompt skips are warnings, never failures -> exit 0 (D-15). Extend tests/cli/test_sync.py: (a) first sync writes the 3 prompts + records hashes; (b) edit a synced prompt, re-run sync -> file unchanged + warning naming it + exit 0; (c) re-run with --force -> file regenerated + manifest hash updated; (d) delete the manifest, re-run -> existing prompts treated as edited (skip+warn), --force re-adopts (D-11); (e) idempotency still holds: two clean syncs in a row leave the prompt files byte-identical.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/cli/test_sync.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - tests/cli/test_sync.py passes under .venv/bin/python (including the prompt hash-guard cases).
    - Test asserts the 3 prompts are written to .voss/prompts/ with the .jinja suffix stripped (plain .txt).
    - Test asserts editing a synced prompt then re-syncing leaves it byte-unchanged, emits a warning naming the file, and exits 0 (R6, D-15).
    - Test asserts `voss sync --force` overwrites the edited prompt and updates its manifest hash (R6/D-16).
    - Test asserts a missing manifest causes existing prompts to be treated as edited (skip+warn), and --force re-adopts (D-11).
    - `grep -nE "sha256|\\.replace\\(|hexdigest" voss/sync.py` shows the prompt hash-guard uses sha256; `grep -n "adopt=True" voss/sync.py` still returns nothing (fence semantics unchanged).
  </acceptance_criteria>
  <done>sync() writes the 3 synced prompts with a sha256 hash-guard: unedited regenerate, edited skip+warn (exit 0), --force overwrites, missing manifest treats prompts as edited; idempotency preserved.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .voss/prompts/<name>.txt (user-editable) -> runtime prompt loader | user-edited prompt text loaded and ${}-substituted into the agent/reviewer/EM system prompt |
| .voss/sync-state.json -> prompt hash-guard | manifest drives clobber decisions; malformed/missing manifest must fail safe (treat as edited) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V16-08 | Tampering | silent clobber of user-edited prompt | mitigate | sha256 hash-guard: edited (hash drift) or missing-manifest => skip+warn, never overwrite without --force (D-11/R6); extends voss_md refuse-on-drift philosophy |
| T-V16-09 | Injection | runtime substitution of user prompt text | mitigate | plain str.replace of fixed ${AGENT}/${PROJECT}/${WORKSPACE} placeholders only (D-18); NOT Jinja at runtime so user edits cannot trigger template execution / StrictUndefined; no eval, no format-string injection |
| T-V16-10 | Tampering | manifest JSON parse for hash-guard | mitigate | malformed/missing manifest treated as "no recorded hash" => fail-safe to skip+warn (never clobber on a parse error) |
| T-V16-SC | Tampering | npm/pip/cargo installs | accept | no new dependencies; no install task |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_prompt_override.py tests/cli/test_sync.py -q` green.
- `grep -ln "load_prompt" voss/harness/board/reviewer_a.py voss/harness/board/reviewer_b.py voss/harness/em/llm.py` lists all three sites.
- `grep -n "adopt=True" voss/sync.py` empty (fence drift semantics unchanged).
</verification>

<success_criteria>
- The 3 reviewer/EM prompts sync to .voss/prompts/ as editable .txt; load_prompt prefers the project copy with ${} substitution, falls back byte-identically when absent (R5).
- Hash-guard: unedited regenerate, edited skip+warn (exit 0), --force overwrite, missing manifest treats prompts as edited (R6/D-11/D-16).
- Runtime substitution is plain str.replace, never Jinja (D-18); the other 7 prompts untouched; idempotency preserved.
</success_criteria>

<output>
Create `.planning/phases/V16-managed-docs-prompt-generation/V16-04-SUMMARY.md` when done
</output>
