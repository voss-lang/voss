---
phase: V1-capability-surface-hardening
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/tools.py
  - tests/harness/test_capability_metadata.py
autonomous: true
requirements: [VCAP-01, VCAP-02, VCAP-03, VCAP-06]
must_haves:
  truths:
    - "Every ToolEntry in make_toolset carries an explicit group, scope_requirements, audit_behavior, and is_stateful value"
    - "ToolEntry exposes a normalized capability view (name, description, input schema, output schema, mutability, network, scope, audit behavior, stateful)"
    - "All capability groups are drawn from exactly nine allowed values"
    - "Pre-existing is_mutating / is_network classification is preserved unchanged on every entry"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "Extended ToolEntry dataclass + hand-tagged native registry"
      contains: "scope_requirements"
    - path: "tests/harness/test_capability_metadata.py"
      provides: "Registry-wide metadata completeness assertions"
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
Extend the frozen `ToolEntry` dataclass in `voss/harness/tools.py` with normalized capability metadata (CAP-01/02/03/06) and hand-tag every native registry entry in `make_toolset` with explicit literals (D-01). This is the schema foundation; consumers (CLI, MCP unification, recorder) build on it in wave 2+.

Purpose: A mis-grouped or mis-classified mutating tool is a security bug — explicit per-entry tagging makes mutability/group/scope auditable data at registration, not name-pattern guesswork.
Output: Extended `ToolEntry`, the nine-group constant, fully tagged native registry, and a registry-wide completeness test.
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
    - ToolEntry still constructs with only descriptor + is_mutating (+ is_network) — every new field has a default so existing call sites at L635-713 keep compiling unchanged.
    - ToolEntry.group accepts exactly one of: fs, git, test, shell, net, code, memory, review, mcp. Any other string fails a validation/test.
    - ToolEntry exposes a capability view (a method or property, e.g. `as_capability()`/`capability_dict()`) returning name, description, input_schema (== descriptor.parameters), output_schema, is_mutating, is_network, group, scope_requirements, audit_behavior, is_stateful.
    - is_stateful defaults False (CAP-03 order-agnostic-unless-stateful).
    - audit_behavior defaults "full" and is one of full | redact_args | metadata_only.
  </behavior>
  <action>
    Add a module-level `CAPABILITY_GROUPS` tuple/frozenset with EXACTLY the nine D-05 values: `fs`, `git`, `test`, `shell`, `net`, `code`, `memory`, `review`, `mcp`. Extend the existing frozen `ToolEntry` dataclass (do NOT create a parallel class) with new fields, each defaulted so the ~30 current `ToolEntry(...)` call sites keep working: `group: str` (no safe default — but to preserve call sites give it a sentinel default like `"shell"` ONLY if needed; prefer making it required and updating all call sites in Task 2, which is the safer path — choose required + update-all-sites), `scope_requirements: tuple[str, ...] = ()` (coarse permission buckets per D-03, values from CAPABILITY_GROUPS), `audit_behavior: str = "full"`, `is_stateful: bool = False`, `output_schema: dict | None = None`. Keep `descriptor`, `is_mutating`, `is_network` exactly as-is. Add a `__post_init__` (allowed on frozen dataclass via object.__setattr__-free validation — raise ValueError) that asserts `group in CAPABILITY_GROUPS` and every element of `scope_requirements in CAPABILITY_GROUPS` and `audit_behavior in {"full","redact_args","metadata_only"}`. Add a method `capability_dict()` returning the normalized CAP-02 view dict (name, description, input_schema=self.parameters, output_schema=self.output_schema, is_mutating, is_network, group, scope_requirements=list, audit_behavior, is_stateful). Reuse the existing `name`/`description`/`parameters` properties. Write the RED test first in tests/harness/test_capability_metadata.py asserting: (a) `CAPABILITY_GROUPS` has the nine exact values; (b) constructing a ToolEntry with an unknown group raises ValueError; (c) `capability_dict()` returns all nine keys; (d) a default ToolEntry has is_stateful False + audit_behavior "full".
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_capability_metadata.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -c "from voss.harness.tools import CAPABILITY_GROUPS; assert tuple(CAPABILITY_GROUPS)==('fs','git','test','shell','net','code','memory','review','mcp')"` exits 0
    - Source assertion: `ToolEntry` in voss/harness/tools.py declares `group`, `scope_requirements`, `audit_behavior`, `is_stateful` fields (grep finds all four)
    - Constructing `ToolEntry(descriptor=..., is_mutating=False, group="bogus")` raises ValueError
    - `capability_dict()` returns a dict containing keys: name, description, input_schema, output_schema, is_mutating, is_network, group, scope_requirements, audit_behavior, is_stateful
  </acceptance_criteria>
  <done>ToolEntry extended (not replaced), nine-group constant present, validation rejects bad groups, capability view method returns the full CAP-02 shape, RED test green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Hand-tag every native registry entry</name>
  <files>voss/harness/tools.py, tests/harness/test_capability_metadata.py</files>
  <read_first>
    - voss/harness/tools.py (L634-713: the `result = {...}` native registry block + the four `result["code_*"]` lines)
    - voss/harness/permissions.py (L45-47 READ_ONLY / WRITE / SHELL sets — sanity-check group/scope assignment against existing tier classification)
    - .planning/phases/V1-capability-surface-hardening/V1-CONTEXT.md (D-01 explicit literals, no name-prefix derivation)
  </read_first>
  <behavior>
    - Every entry in the native `result` dict (fs_*, shell_*, git_*, voss_*, record_run, web_*, code_*) carries an explicit `group=` and `scope_requirements=` literal.
    - Group assignment: fs_read/fs_read_many/fs_glob/fs_grep/fs_write/fs_edit/fs_edit_many/fs_watch/fs_watch_poll → "fs"; shell_run/shell_run_background/shell_monitor/shell_signal → "shell"; git_status/git_diff → "git"; voss_check/voss_probable_inspect/voss_budget_trace/voss_py_diff → "test"; record_run → "review"; web_fetch/web_search → "net"; code_search/find_definition/find_references/code_refresh → "code".
    - scope_requirements names the buckets the capability needs: fs tools → ("fs",); shell tools → ("shell",); net tools → ("net",); a tool that both reads files and runs nothing else lists only its own bucket. record_run → ("review",) (or ("memory",) if it writes run records to memory — pick per descriptor behavior and justify in summary).
    - is_stateful = True only for genuinely order-dependent tools (e.g. shell_run_background / shell_monitor / shell_signal which reference a background job id, and fs_watch / fs_watch_poll which reference a watch handle). All read/write one-shot tools stay is_stateful=False.
    - is_mutating / is_network values are NOT changed from their current literals.
  </behavior>
  <action>
    Edit each `ToolEntry(...)` in the native registry block (L635-670) and the four `result["code_*"]` assignments (L710-713) to add the new literals. Do NOT auto-derive group from the name prefix (D-01) — write each literal explicitly even though the prefix often matches. Preserve every existing `descriptor=`, `is_mutating=`, `is_network=` argument verbatim. Assign `group` per the behavior mapping, `scope_requirements` as the coarse bucket tuple (D-03 group-level only, NO per-path/per-host), `audit_behavior="full"` (default; only set explicitly if a tool needs redact_args/metadata_only — e.g. consider record_run="metadata_only" if it would otherwise echo large run payloads, justify in summary), and `is_stateful=True` only for the background/watch handle tools named in behavior. Extend tests/harness/test_capability_metadata.py with a registry-wide completeness test: build `make_toolset(tmp_path)`, iterate ALL entries, assert each has `group in CAPABILITY_GROUPS`, `scope_requirements` non-checking-empty-allowed but every member in CAPABILITY_GROUPS, `audit_behavior` in the allowed set; assert the set of groups present is a subset of the nine; assert known anchors (fs_write group=="fs" mutating True, git_diff group=="git" mutating False, web_fetch group=="net" network True).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_capability_metadata.py tests/harness/test_tools.py -q</automated>
  </verify>
  <acceptance_criteria>
    - Registry-wide test asserts every `make_toolset` entry has a valid group/scope/audit_behavior and passes
    - `grep -v '^#' voss/harness/tools.py | grep -c 'group="fs"'` ≥ 9 (the nine fs_* tools tagged)
    - Source assertion: every `ToolEntry(` in the L635-713 block includes a `group=` literal (no untagged native entry remains)
    - `tests/harness/test_tools.py` still exits 0 (no call-site regression)
    - fs_write tagged group="fs" is_mutating=True; git_diff group="git" is_mutating=False; web_fetch group="net" is_network=True (asserted in test)
  </acceptance_criteria>
  <done>All ~30 native + 4 code registry entries hand-tagged with explicit group/scope/audit/stateful literals; mutability/network unchanged; registry-completeness test green; no existing test regressed.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_capability_metadata.py tests/harness/test_tools.py tests/harness/test_tools_config_cmds.py -q` exits 0
- No `ToolEntry` call site outside make_toolset broke (grep call sites; cli.py tools_cmd still imports/builds make_toolset)
</verification>

<success_criteria>
- ToolEntry extended in place with group / scope_requirements / audit_behavior / is_stateful / output_schema
- CAPABILITY_GROUPS = the nine D-05 values, enforced by validation
- Every native registry entry hand-tagged; is_mutating/is_network preserved
- capability_dict() yields the normalized CAP-02 view for downstream CLI/recorder consumers
</success_criteria>

<output>
Create `.planning/phases/V1-capability-surface-hardening/V1-01-SUMMARY.md` when done
</output>
