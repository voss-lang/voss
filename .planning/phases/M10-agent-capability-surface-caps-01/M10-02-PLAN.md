---
phase: M10
plan: 02
type: execute
wave: 2
depends_on: [M10-01]
files_modified:
  - voss/harness/code/lsp.py
  - voss/harness/code/lsp_registry.py
  - voss/harness/code/config.py
  - voss/harness/code/models.py
  - voss/harness/lifecycle.py
  - tests/harness/test_code_lsp.py
  - tests/harness/test_code_lsp_live.py
autonomous: true
requirements: [CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]
must_haves:
  truths:
    - "pygls is allowed only behind a Voss-owned adapter; no pygls type leaks into tools, slash, TUI, or tests outside lsp.py."
    - "Language servers launch lazily on first semantic request and are reaped on session exit."
    - "Missing language servers return structured lsp_unavailable results and never crash the agent."
    - "Definition/reference support is limited to Python, JS/TS, Rust, and Go defaults plus user config overlays."
    - "No completion, hover, diagnostics, code actions, formatting, or rename APIs are exposed."
  artifacts:
    - path: "voss/harness/code/lsp.py"
      provides: "LspClientAdapter and pygls-backed implementation hidden behind Voss result types"
    - path: "voss/harness/code/lsp_registry.py"
      provides: "Session-scoped lazy server registry and cleanup"
    - path: "tests/harness/test_code_lsp.py"
      provides: "Fake-server lifecycle, fallback, and no-pygls-leak coverage"
  goal_backward_verification:
    - "CODE-02 requires LSP-backed definition/reference; therefore this wave proves lifecycle and adapter safety before tool registration."
    - "CODE-03 fallback needs structured lsp_unavailable envelopes; this wave defines them before ast-grep/search orchestration consumes them."
---

<objective>
Implement the LSP adapter and registry for code-intelligence semantic operations while keeping pygls isolated behind Voss-owned interfaces.

Purpose: provide lazy, cleanly reaped language-server access for `find_definition` and `find_references`, with graceful unavailable results when servers are missing.

Output: LspClientAdapter, pygls implementation, lazy registry, lifecycle cleanup integration, fake-server tests, and optional live-server acceptance tests.
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
@voss/harness/lifecycle.py
@voss/harness/code/config.py
@voss/harness/code/models.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add Voss-owned LSP adapter and pygls spike tests</name>
  <requirements>[CODE-02]</requirements>
  <files>voss/harness/code/lsp.py, voss/harness/code/models.py, tests/harness/test_code_lsp.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md (pygls Finding)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/code/models.py
    - pygls docs for BaseLanguageClient, JsonRPCClient, initialize, shutdown, text_document_definition, text_document_references, and start_io
  </read_first>
  <action>
    Define an LspClientAdapter protocol or base class that exposes only Voss-owned async methods: initialize(root_uri), shutdown(), find_definition(uri, line, character), find_references(uri, line, character), and workspace_symbol(query). Result values must be CodeLocation/SymbolHit/ReferenceHit or structured unavailable/error envelopes from models.py.

    Implement a pygls-backed adapter in the same module or a private class. Keep pygls imports local to the implementation so importing voss.harness.code.lsp without the optional extra can still expose unavailable errors instead of ImportError. Add fake stdio JSON-RPC server tests for initialize/shutdown/definition/reference.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_lsp.py -q -k "adapter or fake_server"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m py_compile voss/harness/code/lsp.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! rg -n "pygls" voss/harness/code --glob '!lsp.py'</automated>
  </verify>
  <acceptance_criteria>
    - Fake server tests prove initialize, shutdown, definition, and references request paths.
    - `from voss.harness.code.lsp import LspClientAdapter` succeeds without importing pygls at module import time.
    - No pygls classes appear in public result models or tests outside the LSP adapter tests.
    - Adapter errors are structured envelopes, not raw exceptions crossing tool boundaries.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Add lazy server registry, lifecycle cleanup, and unavailable fallback</name>
  <requirements>[CODE-02, CODE-03]</requirements>
  <files>voss/harness/code/lsp_registry.py, voss/harness/code/config.py, voss/harness/code/lsp.py, voss/harness/lifecycle.py, tests/harness/test_code_lsp.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/lifecycle.py (register_subprocess, reap_all, process cleanup patterns)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md (Server lifecycle + orphan prevention, Soft-dependency degradation contract)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-PATTERNS.md (LSP lifecycle responsibility map)
  </read_first>
  <action>
    Implement LspRegistry with one lazy server process per language per session/cwd. Resolve config through `.voss/lsp.yml` overlay, then shutil.which(command). Missing or disabled commands return `{result: "lsp_unavailable", language, fallback: "ast-grep", hint}` envelopes.

    Register spawned subprocesses with the existing lifecycle manager or add a minimal code-intel registration wrapper if lifecycle.py needs a typed helper. Shutdown must call LSP shutdown/exit where possible, then terminate/wait/kill fallback. Keep cleanup safe on SIGINT and normal session exit.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_lsp.py -q -k "registry or unavailable or cleanup"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "lsp_unavailable|register.*subprocess|terminate|kill" voss/harness/code/lsp_registry.py voss/harness/lifecycle.py</automated>
  </verify>
  <acceptance_criteria>
    - Registry does not spawn a server until first semantic request.
    - Repeated requests for the same language reuse one adapter/server for the session.
    - Missing command returns `lsp_unavailable` with language, fallback, and install hint.
    - Cleanup tests prove terminate/wait/kill fallback and no registered process remains.
    - No completion/hover/diagnostics/rename methods exist in the adapter or registry.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Add optional live-server acceptance smoke</name>
  <requirements>[CODE-02]</requirements>
  <files>tests/harness/test_code_lsp_live.py, tests/harness/test_code_lsp.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md (Manual-only real language-server smoke)
    - /Users/benjaminmarks/Projects/Voss/tests/fixtures/code
  </read_first>
  <action>
    Add optional pytest-marked live tests that run only when the relevant server command is present on PATH and an explicit live marker/env is enabled. The tests should cover Python, JS/TS, Rust, and Go definitions against the fixture repos when possible, and should skip clearly with installed-version diagnostics when unavailable.

    These tests are acceptance evidence, not a default CI blocker unless the environment opts in.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_lsp_live.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_lsp.py -q</automated>
  </verify>
  <acceptance_criteria>
    - Live tests skip when servers are missing unless the opt-in marker/env requests strict mode.
    - If servers are installed, definitions resolve to known fixture file/range locations.
    - Skip output identifies the missing command and install hint.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## ASVS L1 Gate

Security enforcement is on. Any high-severity process orphan, arbitrary command launch beyond config, or pygls type leak blocks completion.

| Threat ID | Category | Component | Risk | Mitigation |
|-----------|----------|-----------|------|------------|
| T-M10-02-01 | Elevation of privilege | .voss/lsp.yml command | Config can launch arbitrary local commands. | Treat as explicit project config; never auto-install; surface command/hint; require cwd jailing for file paths. |
| T-M10-02-02 | DoS | LSP process | Server can hang or outlive Voss. | Lazy launch, request timeouts, shutdown/terminate/kill cleanup, lifecycle tests. |
| T-M10-02-03 | Information disclosure | LSP result payload | Server may return file paths outside cwd. | Normalize and jail result paths before returning to tools/slash/TUI. |
| T-M10-02-04 | Integrity | API surface | pygls classes leaking out couples users to unstable internals. | Adapter boundary and grep tests. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_code_lsp.py -q`
- `python3 -m pytest tests/harness/test_code_lsp_live.py -q`
- `python3 -m py_compile voss/harness/code/lsp.py voss/harness/code/lsp_registry.py`
- `! rg -n "pygls" voss/harness/code --glob '!lsp.py'`
- `! rg -n "completion|hover|diagnostic|rename|formatting|code_action|codeAction" voss/harness/code/lsp.py voss/harness/code/lsp_registry.py`
- `git diff --check -- voss/harness/code voss/harness/lifecycle.py tests/harness/test_code_lsp.py tests/harness/test_code_lsp_live.py`
</verification>

<success_criteria>
- LSP calls are available through Voss-owned adapter methods only.
- Language servers launch lazily and clean up on normal and interrupted exit.
- Missing servers return structured `lsp_unavailable` envelopes with fallback and hint.
- Optional live-server tests exist without making default CI depend on external language servers.
</success_criteria>
