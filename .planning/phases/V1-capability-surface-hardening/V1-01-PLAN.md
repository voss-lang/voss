---
phase: V1-capability-surface-hardening
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/tools.py
  - voss/harness/subagents.py
  - voss/harness/multiagent.py
  - tests/harness/test_capability_metadata.py
autonomous: true
requirements: [VCAP-01, VCAP-02, VCAP-03, VCAP-06]
must_haves:
  truths:
    - "Every ToolEntry in make_toolset carries an explicit group, scope_requirements, audit_behavior, and is_stateful value"
    - "Every ToolEntry constructed OUTSIDE make_toolset (memory, subagent, task, multiagent) is also hand-tagged with an explicit group"
    - "ToolEntry exposes a normalized capability view (name, description, input schema, output schema, mutability, network, scope, audit behavior, stateful)"
    - "All capability groups are drawn from exactly nine allowed values"
    - "Pre-existing is_mutating / is_network classification is preserved unchanged on every entry"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "Extended ToolEntry dataclass + hand-tagged native registry + memory tools"
      contains: "scope_requirements"
    - path: "voss/harness/subagents.py"
      provides: "Hand-tagged subagent_run / task ToolEntry"
      contains: "group="
    - path: "voss/harness/multiagent.py"
      provides: "Hand-tagged subagent_spawn/steer/status/gather ToolEntry"
      contains: "group="
    - path: "tests/harness/test_capability_metadata.py"
      provides: "Registry-wide metadata completeness assertions (incl. attached tools)"
      contains: "def test_"
  key_links:
    - from: "make_toolset entries"
      to: "ToolEntry new fields"
      via: "explicit per-entry literals"
      pattern: "group=\"(fs|git|test|shell|net|code|memory|review|mcp)\""
    - from: "ToolEntry"
      to: "CAPABILITY_GROUPS"
      via: "group field constrained to nine values"
      pattern: "CAPABILITY_GROUPS"
---

<objective>
Extend the frozen `ToolEntry` dataclass in `voss/harness/tools.py` with normalized capability metadata (CAP-01/02/03/06) and hand-tag EVERY `ToolEntry` construction with explicit literals (D-01) — both the `make_toolset` native block AND the attach-time call sites in `tools.py` (memory tools), `subagents.py`, and `multiagent.py`. This is the schema foundation; consumers (CLI, MCP unification, recorder) build on it in wave 2+.

Purpose: A mis-grouped or mis-classified mutating tool is a security bug — explicit per-entry tagging makes mutability/group/scope auditable data at registration, not name-pattern guesswork. Because `ToolEntry` is constructed in attach-time helpers as well as `make_toolset`, a required `group` field would TypeError live sessions and a defaulted `group` would silently mislabel them (violating D-01) — so every call site must be tagged.
Output: Extended `ToolEntry`, the nine-group constant, fully tagged registry (native + attached), and a registry-wide completeness test that exercises the attach helpers.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V1-capability-surface-hardening/V1-CONTEXT.md

<interfaces>
<!-- Current ToolEntry (voss/harness/tools.py L56-89), frozen dataclass to EXTEND not replace: -->
<!-- fields today: descriptor: ToolDescriptor; is_mutating: bool; is_network: bool = False -->
<!-- properties: name, description, parameters (== descriptor.parameters); methods invoke / invoke_dict -->
<!-- descriptor.parameters is the input JSON schema (CAP-02 input schema source per D-discretion). -->

<!-- ToolEntry construction sites OUTSIDE the make_toolset native block (all must be hand-tagged): -->
<!--   tools.py L165-166  attach_memory_tools: memory_recall (is_mutating=False), memory_remember (is_mutating=True) -->
<!--   tools.py L769-772  make_toolset code_* (already in this plan's make_toolset scope): code_search/find_definition/find_references/code_refresh -->
<!--   subagents.py L331  attach_subagent_tool: subagent_run (is_mutating=True) -->
<!--   subagents.py L365  attach_subagent_tool: task (is_mutating=True) -->
<!--   multiagent.py L523-532 attach_multiagent_tools: subagent_spawn(True), subagent_steer(True), subagent_status(False), subagent_gather(True) -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend ToolEntry schema + nine-group constant</name>
  <files>voss/harness/tools.py, tests/harness/test_capability_metadata.py</files>
  <read_first>
    - voss/harness/tools.py (L56-89 ToolEntry; L1-22 imports/module top for where to place the constant)
    - .planning/phases/V1-capability-surface-hardening/V1-CONTEXT.md (D-01, D-03, D-05, Claude's-discretion locks)
    - .planning/docs/ORCHESTRATION_LAYERS.md §"Phase 1" (CAP-01/02/03/06 rows)
  </read_first>
  <behavior>
    - ToolEntry still constructs with only descriptor + is_mutating (+ is_network) — `is_network`/`scope_requirements`/`audit_behavior`/`is_stateful`/`output_schema` have defaults; `group` is REQUIRED (no default) so every call site must supply it explicitly (D-01) and any untagged site fails loudly at construction rather than mislabeling silently.
    - ToolEntry.group accepts exactly one of: fs, git, test, shell, net, code, memory, review, mcp. Any other string fails a validation/test.
    - ToolEntry exposes a capability view (a method or property, e.g. `as_capability()`/`capability_dict()`) returning name, description, input_schema (== descriptor.parameters), output_schema, is_mutating, is_network, group, scope_requirements, audit_behavior, is_stateful.
    - is_stateful defaults False (CAP-03 order-agnostic-unless-stateful).
    - audit_behavior defaults "full" and is one of full | redact_args | metadata_only.
  </behavior>
  <action>
    Add a module-level `CAPABILITY_GROUPS` tuple/frozenset with EXACTLY the nine D-05 values: `fs`, `git`, `test`, `shell`, `net`, `code`, `memory`, `review`, `mcp`. Extend the existing frozen `ToolEntry` dataclass (do NOT create a parallel class) with new fields: make `group: str` REQUIRED (no default — Task 2 + the attach-site edits supply it at every construction; a missing group must TypeError, not silently default, per D-01). Because a frozen dataclass forbids a required field after a defaulted one, place `group` immediately after the existing required `is_mutating` and BEFORE `is_network` (i.e. field order: descriptor, is_mutating, group, then defaulted is_network/scope_requirements/audit_behavior/is_stateful/output_schema) — update every call site to pass `group` (Task 2 + attach sites). Add the remaining fields with defaults: `scope_requirements: tuple[str, ...] = ()` (coarse permission buckets per D-03, values from CAPABILITY_GROUPS), `audit_behavior: str = "full"`, `is_stateful: bool = False`, `output_schema: dict | None = None`. Keep `descriptor`, `is_mutating`, `is_network` semantics as-is. Add a `__post_init__` (validate then raise ValueError) asserting `group in CAPABILITY_GROUPS`, every element of `scope_requirements in CAPABILITY_GROUPS`, and `audit_behavior in {"full","redact_args","metadata_only"}`. Add a method `capability_dict()` returning the normalized CAP-02 view dict (name, description, input_schema=self.parameters, output_schema=self.output_schema, is_mutating, is_network, group, scope_requirements=list, audit_behavior, is_stateful). Reuse the existing `name`/`description`/`parameters` properties. Write the RED test first in tests/harness/test_capability_metadata.py asserting: (a) `CAPABILITY_GROUPS` has the nine exact values; (b) constructing a ToolEntry with an unknown group raises ValueError; (c) `capability_dict()` returns all ten keys; (d) a default ToolEntry has is_stateful False + audit_behavior "full"; (e) constructing a ToolEntry WITHOUT a group raises TypeError (proves group is required, catching untagged regressions).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_capability_metadata.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -c "from voss.harness.tools import CAPABILITY_GROUPS; assert tuple(CAPABILITY_GROUPS)==('fs','git','test','shell','net','code','memory','review','mcp')"` exits 0
    - Source assertion: `ToolEntry` in voss/harness/tools.py declares `group`, `scope_requirements`, `audit_behavior`, `is_stateful` fields (grep finds all four)
    - Constructing `ToolEntry(descriptor=..., is_mutating=False, group="bogus")` raises ValueError
    - Constructing a ToolEntry with no `group` raises TypeError (group is required, not defaulted)
    - `capability_dict()` returns a dict containing keys: name, description, input_schema, output_schema, is_mutating, is_network, group, scope_requirements, audit_behavior, is_stateful
  </acceptance_criteria>
  <done>ToolEntry extended (not replaced), nine-group constant present, `group` required, validation rejects bad groups, capability view method returns the full CAP-02 shape, RED test green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Hand-tag every ToolEntry construction (native registry + memory + subagent + multiagent)</name>
  <files>voss/harness/tools.py, voss/harness/subagents.py, voss/harness/multiagent.py, tests/harness/test_capability_metadata.py</files>
  <read_first>
    - voss/harness/tools.py (L165-166 attach_memory_tools memory_recall/memory_remember; L634-713 native `result = {...}` block + the four `result["code_*"]` lines at L769-772)
    - voss/harness/subagents.py (L288 attach_subagent_tool; L331 subagent_run ToolEntry; L365 task ToolEntry)
    - voss/harness/multiagent.py (L279 attach_multiagent_tools; L523-532 subagent_spawn/steer/status/gather ToolEntry)
    - voss/harness/permissions.py (L45-47 READ_ONLY / WRITE / SHELL sets — sanity-check group/scope assignment against existing tier classification)
    - .planning/phases/V1-capability-surface-hardening/V1-CONTEXT.md (D-01 explicit literals, no name-prefix derivation; D-05 exactly nine groups)
  </read_first>
  <behavior>
    - EVERY `ToolEntry(...)` construction across tools.py (native block + the four code_* + the two memory tools), subagents.py (subagent_run, task), and multiagent.py (subagent_spawn, subagent_steer, subagent_status, subagent_gather) carries an explicit `group=` (and `scope_requirements=` where a bucket applies) literal.
    - Group assignment (native): fs_read/fs_read_many/fs_glob/fs_grep/fs_write/fs_edit/fs_edit_many/fs_watch/fs_watch_poll → "fs"; shell_run/shell_run_background/shell_monitor/shell_signal → "shell"; git_status/git_diff → "git"; voss_check/voss_probable_inspect/voss_budget_trace/voss_py_diff → "test"; record_run → "review"; web_fetch/web_search → "net"; code_search/find_definition/find_references/code_refresh → "code".
    - Group assignment (attached): memory_recall/memory_remember → "memory"; subagent_run, task (subagents.py) and subagent_spawn/subagent_steer/subagent_status/subagent_gather (multiagent.py) → "review". Rationale to record in the action/summary: none of the nine D-05 groups is a literal "orchestration" bucket (D-05 locks exactly nine — do NOT add one); the subagent/task family delegates a unit of agent work whose RESULT the parent inspects/reviews/gathers (subagent_gather is literally a review-and-collect step), so it maps to the same "review" bucket already used for record_run (the run-artifact / meta-work bucket). This keeps scope filtering meaningful: a role granted "review" can run reviewer-style meta-tooling including spawning/collecting subagents.
    - scope_requirements: fs tools → ("fs",); shell tools → ("shell",); net tools → ("net",); memory tools → ("memory",); subagent/task tools → ("review",). Group-level only (D-03 — NO per-path/per-host).
    - is_stateful = True only for genuinely order-dependent tools: shell_run_background / shell_monitor / shell_signal (background job id), fs_watch / fs_watch_poll (watch handle), and the multiagent.py handle-referencing tools subagent_steer / subagent_status / subagent_gather (they reference a spawned subagent handle id from subagent_spawn). All one-shot read/write tools and subagent_run/task stay is_stateful=False.
    - is_mutating / is_network values are NOT changed from their current literals at ANY site (e.g. subagent_run/task stay True; subagent_status stays False; memory_remember stays True; memory_recall stays False).
  </behavior>
  <action>
    Edit each `ToolEntry(...)` construction to add the new literals, preserving every existing `descriptor=`, `is_mutating=`, `is_network=` argument verbatim. Do NOT auto-derive group from the name prefix (D-01) — write each literal explicitly. (1) tools.py native block (L635-670) + the four `result["code_*"]` assignments (L769-772): assign `group` per the native mapping, `scope_requirements` as the coarse bucket tuple, `audit_behavior="full"` (default; only set explicitly if a tool needs redact_args/metadata_only — consider record_run="metadata_only" if it would echo large run payloads, justify in summary), `is_stateful=True` only for the background/watch tools named in behavior. (2) tools.py L165-166 attach_memory_tools: `memory_recall` → `group="memory", scope_requirements=("memory",)`; `memory_remember` → `group="memory", scope_requirements=("memory",)` (keep is_mutating True). (3) subagents.py L331 `subagent_run` and L365 `task`: add `group="review", scope_requirements=("review",)`, keep is_mutating=True, is_stateful default False. (4) multiagent.py L523-532: `subagent_spawn` → `group="review", scope_requirements=("review",)` (is_mutating True); `subagent_steer` → `group="review", scope_requirements=("review",), is_stateful=True` (is_mutating True); `subagent_status` → `group="review", scope_requirements=("review",), is_stateful=True` (is_mutating False); `subagent_gather` → `group="review", scope_requirements=("review",), is_stateful=True` (is_mutating True). Extend tests/harness/test_capability_metadata.py with TWO completeness tests: (a) a make_toolset-wide test (build `make_toolset(tmp_path)`, iterate ALL entries, assert each has `group in CAPABILITY_GROUPS`, every member of `scope_requirements in CAPABILITY_GROUPS`, `audit_behavior` in the allowed set; assert anchors fs_write group=="fs" mutating True, git_diff group=="git" mutating False, web_fetch group=="net" network True); (b) an attach-helper test (see Task-2 test note) that invokes `attach_memory_tools`, `attach_subagent_tool`/`attach_task_tool`, and `attach_multiagent_tools` against stubs and asserts every resulting entry's `group in CAPABILITY_GROUPS` — this is what actually catches the out-of-block regression that pure make_toolset coverage misses.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_capability_metadata.py tests/harness/test_tools.py -q</automated>
  </verify>
  <acceptance_criteria>
    - make_toolset-wide test asserts every entry has a valid group/scope/audit_behavior and passes
    - attach-helper test invokes attach_memory_tools + attach_subagent_tool/attach_task_tool + attach_multiagent_tools (against stubs) and asserts every produced entry's group ∈ CAPABILITY_GROUPS — and passes
    - `grep -v '^#' voss/harness/tools.py | grep -c 'group="fs"'` ≥ 9 (the nine fs_* tools tagged)
    - Source assertion: every `ToolEntry(` in tools.py (native + memory), subagents.py, and multiagent.py includes a `group=` literal (no untagged construction remains in any of the three files)
    - memory_recall/memory_remember tagged group="memory"; subagent_run/task/subagent_spawn/steer/status/gather tagged group="review"
    - fs_write group="fs" is_mutating=True; git_diff group="git" is_mutating=False; web_fetch group="net" is_network=True (asserted in test)
    - `tests/harness/test_tools.py` still exits 0 (no call-site regression)
  </acceptance_criteria>
  <done>Every ToolEntry construction across tools.py (native + memory), subagents.py, and multiagent.py is hand-tagged with explicit group/scope/audit/stateful literals; mutability/network unchanged; BOTH the make_toolset-wide and attach-helper completeness tests green; no existing test regressed.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_capability_metadata.py tests/harness/test_tools.py tests/harness/test_tools_config_cmds.py -q` exits 0
- No `ToolEntry` call site (make_toolset, attach_memory_tools, attach_subagent_tool/attach_task_tool, attach_multiagent_tools) broke — the attach-helper test exercises all of them
- `.venv/bin/python -m voss.harness tools --cwd .` still exits 0 (make_toolset builds; required `group` supplied everywhere)
</verification>

<success_criteria>
- ToolEntry extended in place with required `group` + scope_requirements / audit_behavior / is_stateful / output_schema
- CAPABILITY_GROUPS = the nine D-05 values, enforced by validation; no tenth "orchestration" group added
- Every ToolEntry construction hand-tagged (native registry, memory, subagent, multiagent); is_mutating/is_network preserved
- Attach-helper completeness test catches any future untagged construction
- capability_dict() yields the normalized CAP-02 view for downstream CLI/recorder consumers
</success_criteria>

<output>
Create `.planning/phases/V1-capability-surface-hardening/V1-01-SUMMARY.md` when done
</output>
