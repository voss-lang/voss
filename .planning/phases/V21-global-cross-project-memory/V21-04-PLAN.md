---
phase: V21
plan: 04
type: execute
wave: 2
depends_on: [V21-02]
files_modified:
  - voss/harness/tools.py
  - voss/harness/cli.py
  - .planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md
autonomous: true
requirements: [VGMEM-02, VGMEM-06, VGMEM-08]
cross_phase_note: >
  HARD V19 DEPENDENCY (RESEARCH Q1 RESOLVED): V21 EXECUTES ONLY AFTER V19 SHIPS.
  Task 3 EXTENDS the as-built V19-04 `recall_cmd` in cli.py — it does NOT create
  recall_cmd. The executor MUST read the as-built recall_cmd in cli.py before editing;
  if recall_cmd is absent (V19 not yet shipped), STOP and report the ordering violation
  rather than reimplementing it. Parallel with V21-03 in Wave 2 (no file overlap:
  this owns tools.py+cli.py, V21-03 owns memory_cli.py).
must_haves:
  truths:
    - "agent memory_recall tool fuses project + global hits via _rrf_merge; global hits labeled [global]"
    - "global locators are namespaced (global:<locator>) before _rrf_merge so project/global hits with the same stem do not collapse"
    - "do_cmd and chat_cmd pass global_store=make_global_store() (None when disabled) to attach_memory_tools — all 3 call sites updated"
    - "global_store is NEVER passed to any write tool — memory_remember/write_note stay project-only (D-08 by construction)"
    - "voss recall surfaces [global]-labeled hits, fused as a third ranking into the existing V19 RRF"
    - "global recall failure degrades to project-only hits, never crashes the turn/CLI"
    - "on full V21 suite green, V21-VALIDATION.md frontmatter is flipped to nyquist_compliant: true + wave_0_complete: true (final-plan phase-completion gate)"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "attach_memory_tools global_store param + dual-store fusion in memory_recall"
      contains: "global_store"
    - path: "voss/harness/cli.py"
      provides: "global_store wiring at 3 attach_memory_tools sites + recall_cmd global corpus"
      contains: "make_global_store"
  key_links:
    - from: "memory_recall tool"
      to: "MemoryStore._rrf_merge([proj_hits, g_hits])"
      via: "namespaced global hits, [global] source label"
      pattern: "_rrf_merge"
    - from: "do_cmd / chat_cmd"
      to: "attach_memory_tools(..., global_store=make_global_store())"
      via: "read-only global store reference (never a write path)"
      pattern: "global_store="
    - from: "recall_cmd"
      to: "global_store.recall fused into existing code+memory RRF"
      via: "[global] label, third ranking"
      pattern: "global"
---

<objective>
Surface global hits everywhere recall exists (D-07): the agent-side `memory_recall` tool and
the `voss recall` CLI both fuse the global corpus via the existing `_rrf_merge` (equal RRF,
rank decides — D-06), labeled `[global]`. Wire `global_store=make_global_store()` into all 3
`attach_memory_tools` call sites in `cli.py`. The global store reference is READ-ONLY — never
passed to a write tool (D-08 enforced by construction). `voss recall` extends the as-built
V19-04 `recall_cmd` with a third ranking — it does NOT reimplement it.

As the FINAL plan in the phase, this plan also flips the VALIDATION.md phase-completion gate
(`nyquist_compliant` + `wave_0_complete`) once the full V21 suite is green.

Purpose: a promoted fact becomes visible in every recall surface, with no weighting knobs and
a single off-switch. Output: `tools.py` dual-store fusion + `cli.py` wiring & recall_cmd extension.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md
@.planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-04-PLAN.md

<interfaces>
voss/harness/memory_store.py (existing + V21-02 additions):
  MemoryStore.recall(query, top_k=..., source=None) -> list[Hit]
  MemoryStore._rrf_merge(rankings, *, top_k, k=60) -> list[Hit]   # @staticmethod, dedups by hit.locator
  make_global_store() -> MemoryStore | None                       # V21-02
  Hit dataclass: source, locator, score, excerpt, line_start, line_end  # dataclasses.replace to relabel

voss/harness/tools.py (existing, verified):
  def attach_memory_tools(tools, *, store, session_id) -> None    # L159 — add global_store=None kwarg
  memory_recall tool body (recall + format loop)
  memory_remember tool body — store.write_note (PROJECT ONLY; never receives global_store)

voss/harness/cli.py (existing, verified):
  attach_memory_tools call sites: L1862 (do_cmd), L2171 (chat path), L3386 (third path)
  AGENT_COMMANDS tuple: L4642
  recall_cmd: OWNED BY V19-04 — read the as-built command in cli.py; extend, do not recreate
</interfaces>

<!-- RESEARCH Pitfall 3: _rrf_merge dedups by hit.locator. Namespace global hits `global:<locator>` BEFORE merge or a project+global note with the same stem collapses to one hit. Relabel source="global" via dataclasses.replace (NO brackets in the field). -->
<!-- RESEARCH §dual-store fusion: catch global recall exceptions, fall back to project-only hits, log to stderr — never crash the turn. -->
<!-- D-08: global_store is read-only in attach_memory_tools; memory_remember/write_note never see it. test_agent_cannot_write_global asserts this. -->
<!-- Label storage (warning fix): Hit.source field holds the bare string "global" (NO brackets). The existing format loop wraps it as `[{h.source}]` → renders [global]. Locator stays `global:<loc>`. Do NOT store "[global]" in the field or the loop would double-wrap to [[global]]. -->
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: tools.py — attach_memory_tools global_store param + dual-store fusion (D-06/D-07/D-08)</name>
  <read_first>
    - voss/harness/tools.py (lines 159-215 attach_memory_tools: memory_recall recall+format loop, memory_remember write path; check whether `import dataclasses` / `import sys` already present)
    - voss/harness/memory_store.py (_rrf_merge L426 dedup-by-locator; Hit dataclass fields; recall signature)
    - tests/harness/test_memory_global.py (test_recall_fusion_rrf, test_global_label_in_recall, test_agent_cannot_write_global — implement to make GREEN)
    - .planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md (tools.py section: attach_memory_tools dual-store fusion + D-08 guard — lines 406-480)
    - .planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md (Pattern 6 + Code Examples: dual-store fusion; Pitfall 3 namespacing)
  </read_first>
  <files>voss/harness/tools.py</files>
  <behavior>
    - test_recall_fusion_rrf: a project store with hit A + a global store with hit B → fused memory_recall output contains both A and B
    - test_global_label_in_recall: global hits render with the literal `[global]` label in memory_recall output
    - test_agent_cannot_write_global: memory_remember writes to the PROJECT store only; the global_store reference is never passed to a write path (source + behavior assertion)
  </behavior>
  <action>Add `global_store=None` as a keyword-only param to `attach_memory_tools` (after `session_id`). Ensure `import dataclasses` and `import sys` are present at the top of tools.py (add if missing). In the `memory_recall` tool body: run `proj_hits = store.recall(query, top_k=top_k * 3, source=source)` (widen to top_k*3 for fusion headroom). If `global_store is not None`: in a `try`, run `g_hits_raw = global_store.recall(query, top_k=top_k * 3, source=source)`; build `g_hits = [dataclasses.replace(h, source="global", locator=f"global:{h.locator}") for h in g_hits_raw]` — set the `source` field to the BARE string `"global"` with NO brackets, and namespace the locator `global:<loc>` to avoid _rrf_merge dedup collision (RESEARCH Pitfall 3); `from .memory_store import MemoryStore as _MS`; `hits = _MS._rrf_merge([proj_hits, g_hits], top_k=top_k)`; on `except Exception as exc`: `hits = proj_hits[:top_k]` and `print(f"memory: global recall failed ({exc}); using project-only", file=sys.stderr)` (never crash the turn — RESEARCH §dual-store fallback). Else `hits = proj_hits[:top_k]`. Keep the existing format loop UNCHANGED — it already prints `[{h.source}] {h.locator} ...`, so a global hit whose `source` field is `"global"` renders exactly `[global]` via the loop's wrap (D-07). Do NOT store `"[global]"` in the source field and do NOT add a second bracket-stripping pass — the bare `"global"` string + the existing `[{h.source}]` wrap is the single source of the brackets. D-08 GUARD: do NOT pass `global_store` to `memory_remember` or any `write_*`; the global reference stays read-only inside this function. Register the tool entries unchanged.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_memory_global.py -x -q -k "recall_fusion or global_label or agent_cannot_write" 2>&1 | tail -15; .venv/bin/python -c "import inspect; from voss.harness.tools import attach_memory_tools; sig=inspect.signature(attach_memory_tools); assert 'global_store' in sig.parameters, sig; print('global_store param ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `attach_memory_tools` signature has keyword-only `global_store=None` (inspect.signature check)
    - memory_recall fuses project + global hits via `MemoryStore._rrf_merge` when global_store present (test_recall_fusion_rrf green)
    - global hits render exactly `[global]` in output (test_global_label_in_recall green) — produced by source field `"global"` (no brackets stored) + the existing `[{h.source}]` format wrap (source review: no `"[global]"` literal stored in Hit.source, no double-wrap)
    - global locators namespaced `global:` before merge (source review — prevents dedup collision)
    - memory_remember / write path never receives global_store (test_agent_cannot_write_global green; source review confirms D-08 by construction)
    - global recall exception falls back to project-only hits, logs to stderr, does not raise
  </acceptance_criteria>
  <done>attach_memory_tools dual-store fusion with [global] label (bare "global" source + format wrap) + namespacing + read-only D-08 guard + graceful fallback; 3 tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: cli.py — wire global_store into all 3 attach_memory_tools call sites</name>
  <read_first>
    - voss/harness/cli.py (lines 53 tools import; 1861-1862 do_cmd attach site; 2171 second site; 3386-3388 third site — read each MemoryStore(cwd).bind(...) preamble)
    - voss/harness/memory_store.py (make_global_store — V21-02)
    - tests/harness/test_memory_global.py (test_global_off_switch_no_init — make_global_store returns None path; test_do_cmd_wires_global_store — 17th stub, dispatch pass-through assertion; ensure wiring tolerates None)
    - .planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md (cli.py section: 3-line change per attach site — lines 484-523)
  </read_first>
  <files>voss/harness/cli.py</files>
  <action>Add `make_global_store` to the existing memory_store import (or import at top: `from .memory_store import make_global_store`). At EACH of the 3 `attach_memory_tools` call sites (≈L1862 do_cmd, ≈L2171, ≈L3386): immediately before the call, add `_global_store = make_global_store()` and `if _global_store is not None: _global_store.bind(session_id="global")` (bind creates layout dirs; None when off-switch/HOME-absent), then add `global_store=_global_store,` as a keyword arg to the `attach_memory_tools(...)` call. Do NOT change the existing `store=`/`session_id=` args. The off-switch path (`make_global_store()` returns None) must be a no-op — no chroma open, no bind, `global_store=None` passed through (D-07). Keep edits surgical — three identical 3-line insertions, nothing else in cli.py touched by this task. Then make `test_do_cmd_wires_global_store` (V21-01 17th stub) GREEN: it mocks `make_global_store` + `attach_memory_tools` and asserts the do_cmd dispatch path passes the constructed `global_store` through to `attach_memory_tools` (runtime pass-through, not just static AST count).</action>
  <verify>
    <automated>.venv/bin/python -c "import ast; src=open('voss/harness/cli.py').read(); assert src.count('global_store=_global_store')==3, src.count('global_store=_global_store'); assert 'make_global_store' in src; print('3 attach sites wired')"; .venv/bin/python -m pytest tests/harness/test_memory_global.py -x -q -k "off_switch_no_init or do_cmd_wires_global_store" 2>&1 | tail -10; .venv/bin/python -m voss.cli do --help 2>&1 | head -3 || .venv/bin/python -c "from voss.harness.cli import do_cmd; print('cli import ok')"</automated>
  </verify>
  <acceptance_criteria>
    - all 3 `attach_memory_tools` calls pass `global_store=_global_store` (`grep -c "global_store=_global_store" == 3`)
    - each site guards `if _global_store is not None: _global_store.bind(session_id="global")` (source review)
    - `make_global_store` imported once (grep)
    - `test_do_cmd_wires_global_store` green — runtime test mocks make_global_store + attach_memory_tools and asserts do_cmd dispatch passes global_store through (not a static count only)
    - cli.py imports cleanly; `voss do --help` / module import succeeds (off-switch path tolerated — None passed through)
  </acceptance_criteria>
  <done>3 attach_memory_tools sites pass global_store; do_cmd dispatch pass-through asserted by test_do_cmd_wires_global_store; off-switch None path is a clean no-op; cli imports.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: cli.py — extend the as-built V19-04 recall_cmd with the [global] corpus (D-06/VGMEM-08) + flip phase-completion gate</name>
  <read_first>
    - voss/harness/cli.py (the AS-BUILT recall_cmd — locate via `grep -n "def recall_cmd\|recall_cmd" voss/harness/cli.py`; if ABSENT, STOP: V19 has not shipped, report ordering violation, do not create recall_cmd)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-04-PLAN.md (recall_cmd interface, RRF fusion of code+memory, [code]/[memory] label scheme, --json schema)
    - voss/harness/memory_store.py (_rrf_merge; make_global_store; Hit fields)
    - tests/harness/test_memory_global.py (test_voss_recall_global_corpus — implement to make GREEN)
    - .planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md (frontmatter gate flipped at end of this task)
    - .planning/phases/V21-global-cross-project-memory/V21-PATTERNS.md (cli.py recall_cmd extension: third ranking + [global] label — lines 525-539)
    - .planning/phases/V21-global-cross-project-memory/V21-RESEARCH.md (Pattern 7: voss recall CLI global corpus)
  </read_first>
  <files>voss/harness/cli.py, .planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md</files>
  <behavior>
    - test_voss_recall_global_corpus: with a global store holding an entry matching the query, `voss recall <q>` output includes a `[global]`-labeled hit
    - existing V19 behavior preserved: code+memory still fused and labeled [code]/[memory]; --json schema unchanged plus global hits carry source "global"
  </behavior>
  <action>Inside the AS-BUILT recall_cmd (V19-04 owns it — EXTEND, do not rewrite): after the existing `mem_hits = store.recall(query_str, top_k=top_k*3)` line, add `g_store = make_global_store()` and `g_hits_raw = (g_store.recall(query_str, top_k=top_k*3) if g_store is not None else [])`; namespace + relabel `g_hits = [dataclasses.replace(h, source="global", locator=f"global:{h.locator}") for h in g_hits_raw]` (bare `"global"` source field, NO brackets — the display label logic adds the brackets); fold into the memory ranking BEFORE the code fusion: `all_mem = MemoryStore._rrf_merge([mem_hits, g_hits], top_k=top_k*3) if g_hits else mem_hits`; then use `all_mem` in place of `mem_hits` in the existing code+memory `_rrf_merge([code_hits, all_mem], top_k=top_k)` call (D-06 equal RRF — rank decides; no weighting). Extend the display label logic so a hit renders `[global]` when `hit.source == "global"`, `[code]` when `hit.source` starts with "code", else `[memory]` (preserve V19's existing label branches). Extend the `--json` source field accordingly — `"global"` for global hits — without removing any existing V19 json field. SECURITY: do not add any new field that could carry a secret/env value; only Hit fields (threat T-V21-04-01, inherited from V19-04 T-V19-04-01). Reuse the `dataclasses` import (add at top of cli.py only if not already present). FINAL STEP (phase-completion gate — this is the last plan in V21): after the recall test is green, run the FULL V21 suite `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q`; when it is fully green, edit `.planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md` frontmatter to set `nyquist_compliant: true` and `wave_0_complete: true` (and `status: complete`). Do not flip the gate if any V21 test is red.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_memory_global.py::test_voss_recall_global_corpus -x -q 2>&1 | tail -12; .venv/bin/python -m voss.cli recall "probe" 2>&1 | head -5 || .venv/bin/python -c "from voss.harness.cli import recall_cmd; print('recall_cmd present')"; .venv/bin/python -m pytest tests/harness/test_memory_global.py -q 2>&1 | tail -3; .venv/bin/python -c "import re; fm=open('.planning/phases/V21-global-cross-project-memory/V21-VALIDATION.md').read().split('---')[1]; assert 'nyquist_compliant: true' in fm and 'wave_0_complete: true' in fm, fm; print('phase gate flipped')"</automated>
  </verify>
  <acceptance_criteria>
    - executor confirmed recall_cmd already exists (V19 shipped) before editing; did NOT recreate it
    - `voss recall <q>` surfaces a `[global]`-labeled hit when the global store matches (test_voss_recall_global_corpus green)
    - global ranking folded via `MemoryStore._rrf_merge([mem_hits, g_hits], ...)` then into the existing code+memory fusion (source review — equal RRF, D-06)
    - global hits store bare `"global"` in Hit.source; display logic renders `[global]`; --json source field is `"global"` (no brackets stored)
    - existing V19 [code]/[memory] labels + --json schema preserved (no V19 regression)
    - no new --json field carries env/secret values (source review, T-V21-04-01)
    - FULL V21 suite green, THEN V21-VALIDATION.md frontmatter flipped to `nyquist_compliant: true` + `wave_0_complete: true` (+ `status: complete`); gate NOT flipped if any V21 test is red
  </acceptance_criteria>
  <done>recall_cmd extended with [global] corpus as a third RRF ranking; V19 behavior preserved; recall global test green; phase-completion gate flipped on full-suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| global store hits → agent tool output / turn context | global content enters the model's context across projects |
| global store hits → `voss recall` stdout / --json | hits leave the process to terminal / future A-track panel |
| agent write tools ↔ global store | D-08 boundary: write tools must NOT cross into the global store |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V21-04-01 | Information Disclosure | recall / --json output | mitigate | global hits expose only Hit fields (source/locator/score/excerpt); no new field carries env/secret; inherits V19-04 T-V19-04-01 json-no-secrets assertion (ASVS — no secrets in output) |
| T-V21-04-02 | Elevation of Privilege | agent write path reaching global store | mitigate | `global_store` is read-only in attach_memory_tools; never passed to memory_remember/write_*; test_agent_cannot_write_global asserts it (D-08 by construction) |
| T-V21-04-03 | Spoofing | project/global locator collision in _rrf_merge | mitigate | global hits namespaced `global:<locator>` before merge — no silent hit collapse/mislabel (RESEARCH Pitfall 3) |
| T-V21-04-04 | Denial of Service | global recall failure crashing the turn | mitigate | global branch wrapped try/except → falls back to project-only hits, logs stderr, never raises |
| T-V21-04-05 | Tampering | excerpt rendering | accept | excerpts are operator's own promoted note text; printed as text, never executed (inherits V19-04 T-V19-04-02) |
| T-V21-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: zero new deps) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q -k "recall_fusion or global_label or agent_cannot_write or voss_recall_global or do_cmd_wires_global_store" 2>&1 | tail -8` — all green
- Coherence guard: `.venv/bin/python -m pytest tests/harness/ tests/memory/ -q 2>&1 | tail -5` — existing tool/recall suites unaffected
- Coherence guard: `.venv/bin/python -m voss.cli recall "test" 2>&1 | head -3` exits 0 (recall_cmd functional, V19+V21 fused)
- Phase gate: full V21 suite green — `.venv/bin/python -m pytest tests/harness/test_memory_global.py -q` — THEN V21-VALIDATION.md frontmatter flipped (nyquist_compliant + wave_0_complete true)
</verification>

<success_criteria>
- agent memory_recall + voss recall both fuse global hits labeled [global], equal RRF
- global_store wired at all 3 attach sites; read-only (D-08); off-switch = clean no-op
- recall_cmd EXTENDED (not recreated); V19 behavior preserved
- global recall failure degrades gracefully; no secrets in output
- V21-VALIDATION.md phase-completion gate flipped to true on full-suite green (final-plan responsibility)
</success_criteria>

<output>
Create `.planning/phases/V21-global-cross-project-memory/V21-04-SUMMARY.md` when done
</output>
</content>
</invoke>
