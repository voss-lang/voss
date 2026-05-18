---
phase: M10
plan: 04
type: execute
wave: 3
depends_on: [M10-02, M10-03]
files_modified:
  - voss/harness/tools.py
  - voss/harness/cli.py
  - voss/harness/slash.py
  - voss/harness/code/service.py
  - voss/harness/code/models.py
  - tests/harness/test_code_tools.py
  - tests/harness/test_tools.py
  - tests/harness/test_permissions_modes.py
  - tests/harness/test_repl_slash.py
  - tests/e2e/test_slash_matrix.py
  - tests/harness/test_session_redaction.py
  - tests/harness/test_telemetry.py
autonomous: true
requirements: [CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]
must_haves:
  truths:
    - "Register exactly four new read-only tools: code_search, find_definition, find_references, code_refresh."
    - "Register exactly three slash commands: /symbol, /refs, /refresh."
    - "All code tools are is_mutating=False and is_network=False; permission modes plan/edit/auto allow them through existing rules."
    - "code_refresh writes only rebuildable cache under .voss-cache/code/ and remains read-only relative to project source."
    - "Tool and slash result snippets are bounded before recorder/session persistence."
    - "No reserved M8 slash command name is changed or reused."
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "Four CodeIntel ToolEntry registrations"
    - path: "voss/harness/cli.py"
      provides: "Slash handlers for /symbol, /refs, /refresh and grouped help placement"
    - path: "tests/e2e/test_slash_matrix.py"
      provides: "Slash matrix rows for all new slash commands"
  goal_backward_verification:
    - "CODE-04 and CODE-05 are user/agent surfaces; they must land only after backend fallback behavior exists."
    - "CODE-07 panel updates depend on slash/tool outputs being bounded and structured, so redaction and result envelopes are verified here."
---

<objective>
Expose code intelligence through the harness tool registry and slash command registry while preserving permission, redaction, and slash-matrix contracts.

Purpose: make the index, LSP, and search services reachable by agents and users without adding new permission semantics or mutating source files.

Output: four read-only tools, three slash commands, grouped help and matrix coverage, permission tests, and session/telemetry redaction regressions.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-PATTERNS.md
@voss/harness/tools.py
@voss/harness/cli.py
@voss/harness/slash.py
@voss/harness/permissions.py
@voss/harness/session.py
@voss/harness/telemetry.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Register four read-only code-intel tools</name>
  <requirements>[CODE-01, CODE-02, CODE-03, CODE-04]</requirements>
  <files>voss/harness/tools.py, voss/harness/code/service.py, tests/harness/test_code_tools.py, tests/harness/test_tools.py, tests/harness/test_permissions_modes.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tools.py (ToolEntry, make_toolset, existing read-only registrations)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/permissions.py (mode_allows)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-PATTERNS.md (Tool Registry and Read-Only Tool Shape)
    - /Users/benjaminmarks/Projects/Voss/tests/harness/test_tools.py (read-only/mutating count assertions)
  </read_first>
  <action>
    In make_toolset(), lazily construct CodeIntelService with cwd and session_id. Register `code_search(pattern, path=".", max_results=50)`, `find_definition(symbol, path=None)`, `find_references(symbol, path=None, max_results=50)`, and `code_refresh(paths=None)`.

    Keep all four ToolEntry records `is_mutating=False` and `is_network=False`. `code_refresh` may rebuild `.voss-cache/code/index.db`, but it must not edit project source or durable `.voss/` memory. Update tool classification tests conservatively.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_tools.py tests/harness/test_tools.py tests/harness/test_permissions_modes.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -c "from voss.harness.tools import make_toolset; tools=make_toolset('.'); [print(name, tools[name].is_mutating, tools[name].is_network) for name in ('code_search','find_definition','find_references','code_refresh')]"</automated>
  </verify>
  <acceptance_criteria>
    - `voss tools` lists all four code tools with descriptions.
    - Tool registry tests prove all four are ToolEntry values, read-only, and non-network.
    - Permission-mode tests prove plan/edit/auto allow the code tools through existing non-mutating logic.
    - Tool count assertions are updated only for the four new read-only tools.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Register /symbol, /refs, and /refresh slash commands</name>
  <requirements>[CODE-05]</requirements>
  <files>voss/harness/cli.py, voss/harness/slash.py, tests/harness/test_repl_slash.py, tests/e2e/test_slash_matrix.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (_build_slash_registry, grouped help)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/slash.py
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/reserved_slash_names.py
    - /Users/benjaminmarks/Projects/Voss/tests/e2e/test_slash_matrix.py
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-PATTERNS.md (Slash Commands)
  </read_first>
  <action>
    Add handlers for `/symbol <name>`, `/refs <symbol>`, and `/refresh [paths...]` inside the existing slash registry construction style. Add help lines and place them in a new or existing grouped help bucket named "Code" or equivalent. Do not modify M8 reserved slash names and do not reuse `/save`, `/recall`, `/forget`, or `/memory`.

    Add slash matrix rows and focused tests for help output, missing-arg usage, success path using fixture service, and reserved-name non-collision.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_repl_slash.py tests/e2e/test_slash_matrix.py -q -k "symbol or refs or refresh or registry"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n '"/symbol"|"/refs"|"/refresh"|Code' voss/harness/cli.py tests/e2e/test_slash_matrix.py tests/harness/test_repl_slash.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! rg -n 'RESERVED_SLASH_NAMES.*symbol|RESERVED_SLASH_NAMES.*refs|RESERVED_SLASH_NAMES.*refresh' voss/harness/tui/reserved_slash_names.py</automated>
  </verify>
  <acceptance_criteria>
    - `/symbol --help`, `/refs --help`, and `/refresh --help` produce stable usage/help.
    - Missing args for `/symbol` and `/refs` return usage text without traceback.
    - Slash matrix coverage includes all three new commands.
    - M8 reserved names remain unchanged and no collision exists.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Bound tool/slash results before persistence and keep telemetry safe</name>
  <requirements>[CODE-03, CODE-04, CODE-05, CODE-07]</requirements>
  <files>voss/harness/code/service.py, voss/harness/code/models.py, tests/harness/test_code_tools.py, tests/harness/test_session_redaction.py, tests/harness/test_telemetry.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/agent.py (tool result persistence and recorder.observe path)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/session.py (fixed-field redaction contract)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/telemetry.py (redact_tool_args limitation)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-PATTERNS.md (Session Persistence And Redaction Boundaries)
  </read_first>
  <action>
    Centralize result serialization in CodeIntelService or models.py so every tool/slash payload caps snippets before agent.py can record the result. Cap snippets at 80 characters per line and 10 lines by default. Include source tags (`lsp`, `ast-grep`, `regex-fallback`) and truncated flags.

    Do not add new RunRecord or SessionRecord fields. Do not claim arbitrary content redaction. Preserve existing session redaction tests and telemetry arg redaction tests; add focused evidence that code-intel results are bounded before recorder/session persistence.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_tools.py tests/harness/test_session_redaction.py tests/harness/test_telemetry.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! rg -n "code_.*:" voss/harness/session.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "80|10|truncated|regex-fallback|ast-grep|lsp" voss/harness/code/service.py voss/harness/code/models.py tests/harness/test_code_tools.py</automated>
  </verify>
  <acceptance_criteria>
    - Tool and slash results are bounded before stringification.
    - Existing session redaction tests remain green.
    - No SessionRecord or RunRecord schema field is added for code-intel snippets.
    - Recorder/runtime emit points are not touched in this plan.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## ASVS L1 Gate

Security enforcement is on. High-severity permission bypass, unbounded persisted snippets, or slash collision blocks completion.

| Threat ID | Category | Component | Risk | Mitigation |
|-----------|----------|-----------|------|------------|
| T-M10-04-01 | Elevation of privilege | Tool registry | code_refresh writes cache and could be treated as source mutation. | Restrict writes to `.voss-cache/code/index.db`; tests prove no source/durable `.voss/` writes. |
| T-M10-04-02 | Information disclosure | Tool results | Snippets could persist large secrets in session records. | Bound snippets before recorder/session persistence; no new session fields. |
| T-M10-04-03 | Integrity | Slash registry | New slash names could collide with M8 reserved commands. | Reserved-name and slash-matrix tests. |
| T-M10-04-04 | Repudiation | Fallback behavior | Agent cannot tell if result came from fallback. | Include source tags and fallback markers in every result envelope. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_code_tools.py tests/harness/test_tools.py tests/harness/test_permissions_modes.py -q`
- `python3 -m pytest tests/harness/test_repl_slash.py tests/e2e/test_slash_matrix.py -q -k "symbol or refs or refresh or registry"`
- `python3 -m pytest tests/harness/test_session_redaction.py tests/harness/test_telemetry.py -q`
- `! rg -n "code_.*:" voss/harness/session.py`
- `git diff --check -- voss/harness/tools.py voss/harness/cli.py voss/harness/slash.py voss/harness/code tests/harness tests/e2e/test_slash_matrix.py`
</verification>

<success_criteria>
- Four code tools are visible, read-only, non-network, and permission-safe.
- Three slash commands are registered, documented, matrix-covered, and non-colliding.
- Tool/slash result snippets are bounded before persistence.
- Session and telemetry redaction regressions remain green.
</success_criteria>
