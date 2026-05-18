---
phase: M10
plan: 03
type: execute
wave: 3
depends_on: [M10-02]
files_modified:
  - voss/harness/code/ast_grep.py
  - voss/harness/code/regex_fallback.py
  - voss/harness/code/service.py
  - voss/harness/code/models.py
  - voss/harness/code/index.py
  - tests/harness/test_code_search.py
autonomous: true
requirements: [CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]
must_haves:
  truths:
    - "ast-grep is invoked only as a subprocess CLI, never via ast-grep-py."
    - "ast-grep is a soft dependency; missing binary returns regex fallback results and logs code_search.fallback=regex."
    - "Regex fallback searches only indexed, cwd-jailed files."
    - "All search paths are bounded by max_results and snippet limits."
    - "No file watch, cross-repo search, rewrite/update ast-grep flags, or custom tree-sitter query system is introduced."
  artifacts:
    - path: "voss/harness/code/ast_grep.py"
      provides: "ast-grep CLI wrapper using `ast-grep run --json=stream` with timeout and JSONL parsing"
    - path: "voss/harness/code/regex_fallback.py"
      provides: "Bounded regex fallback over indexed files"
    - path: "voss/harness/code/service.py"
      provides: "Initial CodeIntelService search orchestration"
  goal_backward_verification:
    - "CODE-03 requires structural pattern search; this wave implements the subprocess backend and fallback before tool registration."
    - "CODE-04 and CODE-05 later call service.search(), so service.py must return stable source-tagged envelopes now."
---

<objective>
Implement structural search through the ast-grep CLI with a regex fallback that works when ast-grep is absent.

Purpose: satisfy CODE-03 and provide the search path used later by `code_search`, `/symbol` fallback behavior, and missing-LSP degradation.

Output: ast-grep subprocess wrapper, regex fallback, search orchestration in CodeIntelService, and tests for JSON stream parsing, missing binary fallback, timeout, bad pattern, max-results, and source-tagged envelopes.
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
@voss/harness/code/index.py
@voss/harness/tools.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add ast-grep CLI wrapper with JSON-stream parser and strict flags</name>
  <requirements>[CODE-03]</requirements>
  <files>voss/harness/code/ast_grep.py, voss/harness/code/models.py, tests/harness/test_code_search.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md (ast-grep Finding, recommended command)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tools.py (_shell_capture timeout and cap behavior)
    - ast-grep CLI docs for `run`, `--pattern`, and `--json=stream`
  </read_first>
  <action>
    Implement an async ast-grep wrapper that resolves `ast-grep` with shutil.which, runs `ast-grep run --pattern <pattern> --json=stream --color never --threads 0 <path>`, and parses newline-delimited JSON matches into SearchHit models. Reject or ignore any rewrite/update arguments; M10 search is read-only.

    Add timeout, stdout/stderr byte caps, malformed JSON handling, non-zero exit envelopes, and max_results truncation. Missing binary must not raise FileNotFoundError; it must return a structured unavailable result that CodeIntelService can route to regex fallback.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_search.py -q -k "ast_grep or json_stream or timeout"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m py_compile voss/harness/code/ast_grep.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! rg -n "ast_grep_py|ast-grep-py|rewrite|update-all|--rewrite|--update" voss/harness/code/ast_grep.py</automated>
  </verify>
  <acceptance_criteria>
    - Parser tests convert representative `--json=stream` lines into SearchHit values with file/range/text/source fields.
    - Timeout and malformed JSON produce structured error envelopes without crashing.
    - Missing binary returns an unavailable value, not FileNotFoundError.
    - Wrapper command contains no ast-grep rewrite/update flags.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Add regex fallback over the SQLite index</name>
  <requirements>[CODE-01, CODE-03]</requirements>
  <files>voss/harness/code/regex_fallback.py, voss/harness/code/index.py, voss/harness/code/models.py, tests/harness/test_code_search.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/code/index.py
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tools.py (fs_grep bounded behavior)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/sandbox.py (path jailing)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md (Soft-dependency degradation contract)
  </read_first>
  <action>
    Implement a bounded regex fallback that searches indexed files only. The fallback may translate simple ast-grep placeholders conservatively for baseline parity tests, but it must never claim full ast-grep semantics. Bad regex returns a structured error. Each hit snippet is capped to 80 chars per line and 10 lines maximum before persistence.

    Ensure every file path read from the index is re-jailed under cwd before opening. Add a fallback event/result marker `code_search.fallback=regex` that later telemetry can surface without requiring new recorder emit points.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_search.py -q -k "regex or fallback or bad_pattern"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "code_search\\.fallback=regex|max_results|80|10" voss/harness/code/regex_fallback.py tests/harness/test_code_search.py</automated>
  </verify>
  <acceptance_criteria>
    - PATH-stripped test returns regex fallback hits and includes `code_search.fallback=regex`.
    - Fallback reads only files present in index.db and rejects DB paths outside cwd.
    - Bad regex returns structured error and does not crash.
    - Snippets are bounded before result serialization.
    - Baseline Python fixture has hit-count parity between ast-grep and regex fallback when ast-grep is available.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Add initial CodeIntelService search orchestration</name>
  <requirements>[CODE-01, CODE-03, CODE-04]</requirements>
  <files>voss/harness/code/service.py, voss/harness/code/ast_grep.py, voss/harness/code/regex_fallback.py, tests/harness/test_code_search.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-PATTERNS.md (Recommended tool hook shape and service facade)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/code/index.py
    - /Users/benjaminmarks/Projects/Voss/voss/harness/code/models.py
  </read_first>
  <action>
    Implement CodeIntelService.for_cwd(cwd, session_id=None, renderer=None) and `search(pattern, path=".", max_results=50)`. The service must ensure the index exists or builds it, try ast-grep when available, fallback to regex when missing/unavailable, and return a source-tagged structured text/envelope suitable for tools and slash commands.

    Keep service imports lazy and optional-extra safe. Do not register tools or slash commands in this plan.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_search.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m py_compile voss/harness/code/service.py voss/harness/code/regex_fallback.py</automated>
  </verify>
  <acceptance_criteria>
    - `CodeIntelService.for_cwd(...).search("def $NAME($$$)")` returns source-tagged hits for the Python fixture.
    - With ast-grep missing, the service returns regex fallback results and limitation marker.
    - `max_results` truncates results with an explicit truncated flag.
    - No tool/slash registry changes are made in this plan.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## ASVS L1 Gate

Security enforcement is on. High-severity subprocess misuse, unbounded output, or path escape blocks completion.

| Threat ID | Category | Component | Risk | Mitigation |
|-----------|----------|-----------|------|------------|
| T-M10-03-01 | Elevation of privilege | ast-grep subprocess | Search wrapper could accidentally allow rewrite/update flags. | Hard-code read-only `ast-grep run` argv and grep-test forbidden flags. |
| T-M10-03-02 | DoS | ast-grep output | Huge output could exhaust memory. | JSON streaming parser, byte caps, timeout, max_results truncation. |
| T-M10-03-03 | Information disclosure | snippets | Search results could persist large source blocks. | Cap snippets before serialization; no raw auto-injection. |
| T-M10-03-04 | Tampering | regex fallback paths | index.db could point outside cwd. | Re-jail every path before reading. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_code_search.py -q`
- `python3 -m py_compile voss/harness/code/ast_grep.py voss/harness/code/regex_fallback.py voss/harness/code/service.py`
- `! rg -n "ast_grep_py|ast-grep-py|rewrite|update-all|--rewrite|--update" voss/harness/code/ast_grep.py`
- `rg -n "code_search\\.fallback=regex|max_results" voss/harness/code tests/harness/test_code_search.py`
- `git diff --check -- voss/harness/code tests/harness/test_code_search.py`
</verification>

<success_criteria>
- Structural search works through ast-grep CLI when available.
- Missing ast-grep gracefully falls back to bounded regex search over indexed files.
- Search results are source-tagged, bounded, jailed, and safe for later tool/slash persistence.
- No hard dependency on ast-grep exists outside the optional extra.
</success_criteria>
