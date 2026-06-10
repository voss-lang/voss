---
phase: V16-managed-docs-prompt-generation
plan: 02
type: execute
wave: 2
depends_on: ["V16-01"]
files_modified:
  - voss/templates/docs/cheatsheet.md.jinja
  - voss/templates/docs/commands.md.jinja
  - voss/templates/docs/review.md.jinja
  - voss/templates/docs/voss_md_fence.md.jinja
  - tests/harness/test_doc_templates.py
autonomous: true
requirements: [R3, R4]
must_haves:
  truths:
    - "Three doc templates render from a SyncContext-shaped context via render_package_template"
    - "Each generated doc carries a 'generated — do not edit' header"
    - "Command invocations in commands.md differ correctly between repo-root and worktree layout contexts"
    - "review.md content is conditional on review.enabled (D-08)"
    - "The fence-body template renders to a string carrying project name/type, enabled tools, review config, install/check commands, generated doc list, layout vars"
  artifacts:
    - path: "voss/templates/docs/cheatsheet.md.jinja"
      provides: "agent operating guide (D-06, imperative voice D-09)"
      contains: "do not edit"
    - path: "voss/templates/docs/commands.md.jinja"
      provides: "layout-adjusted voss command reference (D-07)"
      contains: "do not edit"
    - path: "voss/templates/docs/review.md.jinja"
      provides: "review workflow doc, conditional on review.enabled (D-08)"
      contains: "do not edit"
    - path: "voss/templates/docs/voss_md_fence.md.jinja"
      provides: "VOSS.md workflow fence body rendered to string (R4)"
      min_lines: 8
  key_links:
    - from: "voss/templates/docs/commands.md.jinja"
      to: "SyncContext command prefixes / layout vars"
      via: "Jinja {{ }} interpolation of layout-derived invocation prefix"
      pattern: "{{"
    - from: "voss/templates/docs/review.md.jinja"
      to: "review.enabled"
      via: "{% if %} conditional gating"
      pattern: "review"
---

<objective>
Author the four Jinja templates `voss sync` renders: three workflow docs (cheatsheet, command reference, review workflow) for `.voss/docs/`, and the VOSS.md workflow fence body. All render from the single `SyncContext` (Plan 01) through `render_package_template`.

Purpose: These are the machine-owned artifacts that make Voss "feel installed" (R3, R4). Layout-awareness (different invocations per layout) and graceful omission of absent facts live entirely in these templates' Jinja logic.
Output: Four `.jinja` templates under `voss/templates/docs/` plus a rendering test that feeds two fixture contexts (repo-root vs worktree, review on vs off).
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
<!-- Rendering entrypoint + template analogs. Extracted from codebase. -->

render_package_template — voss/template_render.py:22-28:
  render_package_template("voss", "templates/docs/cheatsheet.md.jinja", ctx)
  Cached Environment per package: StrictUndefined, trim_blocks, lstrip_blocks,
  keep_trailing_newline, autoescape=False. (D-17 / constraint: this is the ONLY
  render path — no second Environment, no ad-hoc Template(...).)

doc analog — voss/templates/init/README.md.jinja: plain markdown + {{ }} interpolation.
fence-body-to-string analog — voss/templates/agent/cognition_block.md.jinja, rendered at
  voss/harness/agent.py:101-110 with {% if with_constraints %} conditionals (mirror for
  D-04 graceful omission of absent facts).

SyncContext fields available to templates (from Plan 01, voss/sync.py): project_name,
  project_root, is_worktree, command prefixes, workspace paths, type, install_command,
  check_command, tools (list), review {enabled, reviewers}, capabilities. Per D-04 absent
  facts are explicit absent-markers — templates use {% if field %} to omit them, never
  reference an undefined name (StrictUndefined would raise).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Three workflow doc templates (cheatsheet, commands, review)</name>
  <files>voss/templates/docs/cheatsheet.md.jinja, voss/templates/docs/commands.md.jinja, voss/templates/docs/review.md.jinja, tests/harness/test_doc_templates.py</files>
  <read_first>
    - voss/templates/init/README.md.jinja (plain-markdown {{ }} analog)
    - voss/templates/agent/cognition_block.md.jinja ({% if %} conditional analog for graceful omission)
    - voss/sync.py (SyncContext field names — templates must reference only declared fields)
    - .planning/phases/V16-managed-docs-prompt-generation/V16-CONTEXT.md (D-06 cheatsheet content, D-07 command subset, D-08 review-conditional, D-09 imperative voice)
  </read_first>
  <behavior>
    - cheatsheet.md.jinja rendered with a full context produces an agent operating guide: repo layout facts, where things live (.voss/, VOSS.md fences), active Voss capabilities, do/don't conventions — terse imperative (D-06/D-09).
    - commands.md.jinja rendered with the repo-root fixture vs the worktree fixture produces DIFFERENT command invocations (layout-adjusted interpreter/cwd prefix, D-07).
    - review.md.jinja rendered with review.enabled=True produces review-workflow content; the orchestrator (Plan 03) skips writing it entirely when review.enabled is False (D-08) — the template itself need not be rendered when disabled.
    - Every rendered doc begins with a "generated — do not edit" header.
    - Rendering a context with an absent optional fact (e.g. no check_command) omits that section without raising StrictUndefined.
  </behavior>
  <action>
    Create three templates under voss/templates/docs/ rendered via render_package_template("voss", "templates/docs/<name>", ctx). cheatsheet.md.jinja: agent operating guide per D-06 (repo layout, where things live, active capabilities, do/don't), imperative CLAUDE.md-style voice per D-09 ("Use X. Never Y. Run Z before W."). commands.md.jinja: only the project-relevant subset of voss commands per D-07, with invocations adjusted by the layout context's command prefix (correct interpreter path / cwd prefix) — the same command must render differently for repo-root vs worktree fixtures. review.md.jinja: the review workflow doc; gate optional internals on {% if review.enabled %} but note the orchestrator skips writing this file when review is disabled (D-08). Every template's first line(s) must emit a "generated — do not edit" header comment (R3 / constraints). Use {% if field %} blocks for every optional fact (D-04) so absent-markers omit cleanly under StrictUndefined; never reference a field not declared on SyncContext. Write tests/harness/test_doc_templates.py that builds two SyncContext fixtures (repo-root vs worktree; review enabled vs disabled), renders each template via render_package_template, and asserts the behaviors above (header present, invocations differ across layouts, absent-fact omission does not raise).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_doc_templates.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - tests/harness/test_doc_templates.py passes under .venv/bin/python.
    - `grep -rl "do not edit" voss/templates/docs/cheatsheet.md.jinja voss/templates/docs/commands.md.jinja voss/templates/docs/review.md.jinja` lists all three (generated header present in each).
    - Test asserts commands.md renders a different invocation string for the repo-root context vs the worktree context (layout-adjusted, D-07).
    - Test renders a context missing an optional fact and asserts no jinja2.UndefinedError is raised (D-04 omission works).
    - Every template renders ONLY through render_package_template (no test or template constructs a bare Template(...)); `grep -rn "Template(" voss/templates/docs/ tests/harness/test_doc_templates.py` returns nothing.
  </acceptance_criteria>
  <done>Three layout-aware, machine-owned doc templates render from SyncContext with generated headers and graceful absent-fact omission; tests prove layout-divergence and StrictUndefined safety.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: VOSS.md workflow fence-body template</name>
  <files>voss/templates/docs/voss_md_fence.md.jinja, tests/harness/test_doc_templates.py</files>
  <read_first>
    - voss/templates/agent/cognition_block.md.jinja (rendered-to-string fence-body analog)
    - voss/harness/voss_md.py (write_fence_body lines 206-270 — consumer of this rendered string; the body is rendered FIRST then handed to write_fence_body)
    - voss/sync.py (SyncContext fields)
    - .planning/phases/V16-managed-docs-prompt-generation/V16-SPEC.md (R4 fence body inputs)
  </read_first>
  <behavior>
    - voss_md_fence.md.jinja rendered from a SyncContext produces a workflow fence body string carrying: project name/type, enabled tools, review config, install/check commands, generated doc list, and layout vars.
    - When review.enabled is False, the rendered fence omits the review-doc link (D-08).
    - When the generated doc list excludes review.md (review disabled), the fence's doc list reflects that.
    - Rendering with absent optional facts omits them without raising.
  </behavior>
  <action>
    Create voss/templates/docs/voss_md_fence.md.jinja — the body that Plan 03 renders to a string and hands to voss_md.write_fence_body (D-17: Jinja produces the string, write_fence_body owns VOSS.md structure; this template must NOT emit any voss:begin/voss:hash/voss:end markers — those belong to write_fence_body). Per R4 the body carries: project name/type, enabled tools, review config, install/check commands, the generated doc list, and layout vars. Gate the review-doc link on {% if review.enabled %} (D-08). Use {% if %} for every optional fact (D-04). Extend tests/harness/test_doc_templates.py (or add cases) rendering the fence body from the repo-root + review-on and review-off fixtures, asserting the review link appears only when enabled and that no fence markers are present in the output.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_doc_templates.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Test renders voss_md_fence.md.jinja via render_package_template and asserts the body contains project name and at least one layout/install fact.
    - Test asserts the review-doc link is present when review.enabled=True and absent when False (D-08).
    - Rendered fence body contains NO fence markers: `grep -n "voss:begin\\|voss:hash\\|voss:end" voss/templates/docs/voss_md_fence.md.jinja` returns nothing (markers are write_fence_body's responsibility, D-17).
    - tests/harness/test_doc_templates.py passes under .venv/bin/python.
  </acceptance_criteria>
  <done>The fence-body template renders the full R4 context struct to a marker-free string ready for write_fence_body; review link is config-conditional.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| SyncContext (user-influenced facts) -> rendered docs | config-provided values (install_command, tools, project name) flow into doc/fence text |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V16-04 | Injection | template rendering of user-influenced config into docs/fence | accept | output is markdown docs for human/agent reading, not executed; autoescape=False is intentional (markdown, not HTML); no shell/SQL/HTML sink — config values rendered as literal text. Low risk: no code-execution surface in generated docs. |
| T-V16-05 | Tampering | StrictUndefined bypass via undefined field reference | mitigate | templates reference only SyncContext-declared fields; {% if field %} guards every optional fact so absent-markers omit rather than detonate; test proves no UndefinedError on absent facts |
| T-V16-SC | Tampering | npm/pip/cargo installs | accept | no new dependencies; jinja2 already in tree; no install task |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_doc_templates.py -q` green.
- `grep -rn "Template(" voss/templates/docs/` returns nothing (single Jinja entrypoint constraint).
- All four templates exist under voss/templates/docs/.
</verification>

<success_criteria>
- Four templates exist; three docs carry the generated header; commands.md is layout-aware; review content is config-conditional.
- Fence-body template renders the full R4 struct as a marker-free string.
- All rendering routed through render_package_template; absent facts omit safely under StrictUndefined.
</success_criteria>

<output>
Create `.planning/phases/V16-managed-docs-prompt-generation/V16-02-SUMMARY.md` when done
</output>
