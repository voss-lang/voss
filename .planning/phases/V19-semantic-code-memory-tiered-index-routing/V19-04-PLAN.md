---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 04
type: execute
wave: 2
depends_on: [V19-02]
files_modified:
  - voss/harness/cli.py
autonomous: true
requirements: [VSEM-05]
must_haves:
  truths:
    - "`voss recall <query>` exits 0 and prints ranked hits across BOTH code and memory corpora"
    - "Every hit is labeled [code] or [memory]; code hits show path:line, memory hits show their locator"
    - "Fusion is RRF across the two corpora's ranked lists (rank-based, corpus-agnostic)"
    - "`--json` emits machine-readable hits including a `source` field per a documented schema"
    - "`--refresh` triggers an explicit reindex before querying"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "recall_cmd click command + registration in AGENT_COMMANDS"
      contains: "def recall_cmd"
  key_links:
    - from: "recall_cmd"
      to: "CodeIndex.query + MemoryStore.recall"
      via: "MemoryStore._rrf_merge([code_hits, mem_hits], top_k=...)"
      pattern: "_rrf_merge"
    - from: "recall_cmd"
      to: "AGENT_COMMANDS tuple"
      via: "registration alongside memory_group"
      pattern: "recall_cmd"
---

<objective>
Add the top-level `voss recall <query>` CLI verb (D-09 user-locked): a UNIFIED-corpus recall that queries the code index AND the memory store, RRF-fuses across both, labels every hit `[code]`/`[memory]`, and supports plain + `--json` output with a documented `source` field (VSEM-05).

Purpose: First human surface for semantic code query; memory recall was agent-tool-only. The agent-side `code_recall` tool stays code-only (VSEM-04); cross-corpus fusion lives ONLY here (D-05/D-09).
Output: `recall_cmd` registered in `AGENT_COMMANDS`. This plan owns the `recall_cmd` region of `cli.py`; the injection wiring in `do_cmd`/`chat_cmd` is V19-05 (sequenced after this to avoid cli.py conflicts).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-SPEC.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-CONTEXT.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md

<interfaces>
voss/harness/code/semantic_index.py (V19-02):
  CodeIndex(cwd).query(query, top_k) -> list[Hit]   # source="code", line_start/line_end set
  CodeIndex(cwd).build()                            # for --refresh

voss/harness/memory_store.py:
  MemoryStore(cwd).recall(query, top_k=..., source=None) -> list[Hit]   # source in turn/note/ledger/...
  MemoryStore._rrf_merge(rankings, *, top_k, k=60) -> list[Hit]   # @staticmethod, corpus-agnostic
  Hit(source, locator, score, excerpt, ..., line_start=None, line_end=None)

voss/harness/cli.py:
  AGENT_COMMANDS tuple — cli.py:4558-4594 (register recall_cmd here)
  _recall slash handler — cli.py:640-659 (hit-block output format to mirror)
  memory_group registration — already in AGENT_COMMANDS
</interfaces>

<!-- D-10: one block per hit — clickable path:line header, score, 2-3 line excerpt. No table/card in v1. -->
<!-- Pitfall 8: code: prefix on chunk ids guarantees no locator collision with memory turn:/note: ids in _rrf_merge dedup. -->
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: recall_cmd — unified cross-corpus recall with plain + --json output</name>
  <read_first>
    - tests/code_recall/test_recall_cli.py (RED tests: test_exit_0_labeled, test_json_schema — read the exact JSON schema fields asserted)
    - voss/harness/cli.py (lines 640-659 _recall slash handler hit-format; 4558-4594 AGENT_COMMANDS tuple + register())
    - voss/harness/memory_cli.py (click command structure + --cwd option convention)
    - voss/harness/memory_store.py (MemoryStore.recall signature; _rrf_merge; Hit fields)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md (cli.py recall_cmd section: click options, RRF-reuse, hit formatting)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-CONTEXT.md (D-09, D-10 — locked behavior)
  </read_first>
  <files>voss/harness/cli.py</files>
  <action>Add a top-level `@click.command("recall")` named `recall_cmd` with options: `@click.argument("query", nargs=-1, required=False)`, `--json/json_out` (is_flag), `--top/top_k` (default 10, int), `--refresh/do_refresh` (is_flag), `--cwd/cwd_str` (default ".", Path(file_okay=False)). Body: resolve cwd; build `CodeIndex(cwd)`; if `do_refresh` call `code_index.build()` first (explicit-refresh trigger, D-13 #3); construct `MemoryStore(cwd)`. Run `code_hits = code_index.query(query_str, top_k=top_k*3)` and `mem_hits = store.recall(query_str, top_k=top_k*3)`; fuse `fused = MemoryStore._rrf_merge([code_hits, mem_hits], top_k=top_k)` (RRF is corpus-agnostic — D-09 rationale; code: prefix prevents locator collision per Pitfall 8). PLAIN output (D-10): one block per hit — a header line `[{source-label}] {locator-display} (score {score:.2f})` where source-label is `code` if `hit.source` starts with "code" else `memory`, and locator-display is `{path}:{line_start}` for code hits (derive path from `hit.locator` `code:<path>:<seq>` + `hit.line_start`) or `hit.locator` for memory hits — followed by a 2-3 line excerpt indented. JSON output (`--json`): emit a list of objects with EXACTLY the fields the test schema asserts — at minimum `source` ("code"|"memory"), `locator`, `path` (code only, else null), `line_start`/`line_end` (code only, else null), `score`, `excerpt`. SECURITY: never include any key/secret/env value in the JSON — only the Hit fields above (threat T-V19-04). Exit 0 on success; if query empty, print usage and exit 0. Register `recall_cmd` in the `AGENT_COMMANDS` tuple (cli.py:4558) alongside `memory_group` so `voss recall` resolves as a top-level verb.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/test_recall_cli.py -x -q 2>&1 | tail -15; .venv/bin/python -m voss.cli recall --help 2>&1 | head -5 || .venv/bin/python -c "from voss.harness.cli import recall_cmd; print('recall_cmd ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `test_recall_cli.py::test_exit_0_labeled` passes: `voss recall <q>` exits 0 with hits labeled `[code]`/`[memory]`
    - `test_recall_cli.py::test_json_schema` passes: `--json` output is valid JSON with a `source` field (and the documented fields) and contains NO secret/key-shaped strings
    - `recall_cmd` is in the `AGENT_COMMANDS` tuple (source review / `grep -n "recall_cmd" voss/harness/cli.py`)
    - fusion uses `MemoryStore._rrf_merge([code_hits, mem_hits], ...)` — not a hand-rolled merge (source review)
    - `--refresh` calls `code_index.build()` before querying (source review)
    - plain output is block-per-hit with a `path:line` header for code hits (D-10) — source review
  </acceptance_criteria>
  <done>`voss recall` registered; unified RRF cross-corpus recall with labeled plain + --json (source field, no secrets); CLI RED tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| operator → `voss recall` CLI | untrusted query string crosses into both corpora |
| recall result → stdout / --json | hits leave the process to the terminal / future A-track panel |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V19-04-01 | Information Disclosure | `--json` output | mitigate | JSON contains ONLY Hit fields (source, locator, path, line_start/end, score, excerpt); never embeds provider keys/env/secrets; test_json_schema asserts no secret-shaped strings (ASVS — no secrets in CLI output) |
| T-V19-04-02 | Tampering | excerpt rendering | mitigate | Excerpts are raw repo source already in the operator's scope; printed as text, never executed/eval'd (ASVS V5) |
| T-V19-04-03 | Spoofing | cross-corpus dedup collision | mitigate | code: id prefix guarantees no locator collision with memory turn:/note:/ledger: ids in `_rrf_merge` dedup (Pitfall 8) — no hit silently dropped/mislabeled |
| T-V19-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: zero new deps) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/code_recall/test_recall_cli.py -q` — green
- Coherence guard: `voss recall "test"` exits 0 on this repo; existing CLI suite `.venv/bin/python -m pytest tests/harness/ -q -k cli` green (recall_cmd registration non-breaking)
</verification>

<success_criteria>
- `voss recall` exits 0, ranked labeled hits across code+memory, RRF-fused
- `--json` validates against documented schema incl. source field, no secrets
- `--refresh` triggers explicit reindex
</success_criteria>

<output>
Create `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-04-SUMMARY.md` when done
</output>
