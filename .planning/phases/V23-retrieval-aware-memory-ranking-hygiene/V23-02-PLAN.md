---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 02
type: execute
wave: 1
depends_on: ["V23-01"]
files_modified:
  - voss/harness/memory_store.py
  - voss/harness/tools.py
autonomous: true
requirements: [VRNK-01]

must_haves:
  truths:
    - "An agent-path recall records last_retrieved + retrieval_count per returned hit in .voss/memory/.retrieval.jsonl"
    - "A CLI recall records nothing"
    - "No recall path changes a memory file's bytes or mtime"
    - "Vacuum compacts .retrieval.jsonl into per-locator {count, last_retrieved}"
    - ".retrieval.jsonl is gitignored; .pins.json is NOT"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "_record_telemetry, _load_telemetry_compacted, _vacuum_telemetry, extended gitignore constant"
      contains: "_record_telemetry"
    - path: "voss/harness/tools.py"
      provides: "telemetry record call after memory_recall returns"
      contains: "_record_telemetry"
  key_links:
    - from: "voss/harness/tools.py"
      to: "MemoryStore._record_telemetry"
      via: "call after store.recall returns hits"
      pattern: "_record_telemetry\\(hits\\)"
    - from: "MemoryStore._record_telemetry"
      to: ".voss/memory/.retrieval.jsonl"
      via: "portalocker-guarded append"
      pattern: "\\.retrieval\\.jsonl"
---

<objective>
Implement VRNK-01 retrieval telemetry: a `.voss/memory/.retrieval.jsonl` append-log written ONLY by agent-path recall callers (never inside recall(), never on CLI paths), plus vacuum compaction. Memory files stay byte- and mtime-immutable.

Purpose: Telemetry is the data substrate for VRNK-03 rescore and VRNK-04 retrieval-aware eviction. Per D-01/D-03 it mirrors the `.tombstones.jsonl` lifecycle (append + vacuum compact) with skip-on-contention locking.
Output: telemetry methods on MemoryStore, one surgical record call in tools.py, gitignore extension, vacuum fourth pass.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-SPEC.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-CONTEXT.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-PATTERNS.md

<interfaces>
From voss/harness/memory_store.py (confirmed line numbers):
- _VOSS_MEMORY_GITIGNORE = "chroma/\n.locks/\n.tombstones.jsonl\n"  # line 37
- @contextmanager def _lock(self, source: str)  # line 134 — yields None on contention (skip-on-contention)
- def _load_tombstones(self) -> set[str]  # line 226 — corrupt-line-tolerant JSONL reader template
- @property def _tombstones_path(self) -> Path  # tombstone sidecar template
- def vacuum(self) -> int  # line 720 — three-pass; add fourth pass
- def recall(self, query, *, top_k=5, source=None) -> list[Hit]  # line 411 — DO NOT add telemetry here
- self.root  # = cwd/.voss/memory

From voss/harness/tools.py:
- async def memory_recall(query, top_k=5, source=None) -> str  # line 178; hits = store.recall(...) at line 183
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Telemetry sidecar methods + gitignore + vacuum compaction on MemoryStore</name>
  <read_first>
    - voss/harness/memory_store.py:37 (gitignore constant), :133-149 (_lock pattern — copy verbatim usage), :222-244 (_load_tombstones corrupt-line-tolerant reader template), :720-788 (vacuum three-pass structure)
    - V23-RESEARCH.md:209-258 (Pattern 1 Telemetry Append — _record_telemetry shape, gitignore extension), :759-762 (vacuum fourth-pass recommendation)
    - V23-PATTERNS.md:88-114 (tombstone sidecar template), :221-234 (vacuum fourth pass), :536-560 (shared portalocker + corrupt-line-tolerant patterns)
    - V23-CONTEXT.md D-01/D-03/D-15/D-16 (sidecar = .retrieval.jsonl append-log; sync-append skip-on-contention; compaction = count summation + max timestamp; event schema = locator + ts minimal)
  </read_first>
  <behavior>
    - After _record_telemetry([hit]) the file .voss/memory/.retrieval.jsonl contains one JSON line {locator, ts} for the hit
    - _record_telemetry([]) (empty hits) is a no-op (no file write)
    - On lock contention (_lock yields None) _record_telemetry returns without writing (D-03 skip-on-contention)
    - _load_telemetry_compacted() folds all lines per locator → {locator: {count, last_retrieved}}: count = number of events, last_retrieved = max ts (D-15)
    - _load_telemetry_compacted() returns {} when file absent or all lines corrupt (corrupt-line tolerant)
    - vacuum() rewrites .retrieval.jsonl to one compacted line per locator and the post-vacuum _load_telemetry_compacted() yields identical counts/timestamps
    - _record_telemetry never opens or stats any memory file (turns/notes/conventions/decisions/ledgers) — only the sidecar
  </behavior>
  <action>
    In voss/harness/memory_store.py:
    1. Extend `_VOSS_MEMORY_GITIGNORE` (line 37) to append `.retrieval.jsonl\n.reindex-manifest.json\n` — do NOT add `.pins.json` (D-02: committed). Place the manifest entry here now even though reindex lands in V23-05; it is a one-line constant and avoids a later edit to the same line.
    2. Add `@property _retrieval_path(self) -> Path` returning `self.root / ".retrieval.jsonl"`.
    3. Add `_record_telemetry(self, hits: list[Hit]) -> None`: empty-hits guard; compute `ts = datetime.now(timezone.utc).isoformat(timespec="seconds")`; acquire `self._lock("retrieval")`; if the lock yields None, return (skip-on-contention per D-03); mkdir parents; append one `json.dumps({"locator": h.locator, "ts": ts})` line per hit. Event schema is minimal locator+ts (D-16). Wrap filesystem work in try/except so telemetry failure never propagates to recall callers (BLE001 pattern).
    4. Add `_load_telemetry_compacted(self) -> dict`: corrupt-line-tolerant reader (template = `_load_tombstones`); fold per locator into `{"count": int, "last_retrieved": str}` where count is event count and last_retrieved is the max ISO ts seen (string max is correct for fixed-width ISO with timespec seconds). Return `{}` on missing file / all-corrupt.
    5. Add `_vacuum_telemetry(self) -> None`: under `self._lock("retrieval")` (skip if None), read+compact via the same fold, then atomically rewrite the file to one line per locator carrying `{locator, count, last_retrieved}`. Make `_load_telemetry_compacted` tolerant of BOTH raw event lines `{locator, ts}` and compacted lines `{locator, count, last_retrieved}` so a post-vacuum read still works.
    6. Call `_vacuum_telemetry()` inside `vacuum()` as a fourth pass (after chroma tombstone delete, before tombstones truncation per RESEARCH recommendation). Do NOT change vacuum's return value semantics beyond what the existing byte accounting already does.
    Import additions at top of file if missing: none new required for this task (json, datetime, timezone, portalocker already imported). Do NOT touch `recall()`. Do NOT mutate any memory file.
  </action>
  <acceptance_criteria>
    - `grep -c '\.retrieval\.jsonl' voss/harness/memory_store.py` >= 2 (gitignore constant + _retrieval_path)
    - `.pins.json` does NOT appear in `_VOSS_MEMORY_GITIGNORE` (grep: `grep -n '_VOSS_MEMORY_GITIGNORE' voss/harness/memory_store.py` line does not contain `.pins.json`)
    - `recall(` method body unchanged: `git diff voss/harness/memory_store.py` shows no edit inside the recall() function (lines ~411-428)
    - Telemetry tests pass: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k telemetry -q` GREEN
    - mtime-invariant test passes: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "mtime or telemetry" -q` GREEN
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k telemetry -q 2>&1 | tail -5</automated>
  </verify>
  <done>Telemetry methods exist, vacuum compacts the sidecar, gitignore extended (pins excluded), recall() untouched, telemetry RED tests now GREEN.</done>
</task>

<task type="auto">
  <name>Task 2: Wire telemetry record at the agent-path recall site in tools.py</name>
  <read_first>
    - voss/harness/tools.py:178-194 (memory_recall tool; hits = store.recall(...) at line 183) — the ONLY agent-path site in scope this plan
    - V23-RESEARCH.md:251-258 (telemetry record point), :538 + :571-575 + :607-611 (Anti-pattern: never inside recall(); Pitfall 1 & 7: CLI no-touch)
    - V23-PATTERNS.md:354-376 (tools.py surgical addition — one line after recall returns)
    - V23-CONTEXT.md D-01 (agent paths only; voss recall cli.py is NO-TOUCH)
  </read_first>
  <action>
    In voss/harness/tools.py, inside the `memory_recall` tool, immediately after the successful `hits = store.recall(...)` return and the `if not hits` early-return guard, add a single guarded call `store._record_telemetry(hits)` (agent-path only). Keep it defensive — if `_record_telemetry` somehow raises it must not break the tool response (it is already internally try/excepted from Task 1, but do not introduce a second swallow that hides real bugs; a bare call is fine). Do NOT touch `voss/harness/cli.py` `recall_cmd` (line 4811) — that is the no-touch CLI path (Pitfall 1). Do NOT touch any `/recall` slash command. The post-V21 global-store auto-injection site (`global_store._record_telemetry(global_hits)`) is OUT OF SCOPE here — it is wired in V23-06 once V21 is merged; add a code comment at the tools.py site noting "V23-06 wires global_store telemetry post-V21".
  </action>
  <acceptance_criteria>
    - `grep -c '_record_telemetry' voss/harness/tools.py` == 1
    - `grep -c '_record_telemetry' voss/harness/cli.py` == 0 (CLI path stays no-touch)
    - CLI no-touch test passes: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "telemetry and (cli or not_recorded)" -q` GREEN
    - memory_recall tool still returns its hit-list string (existing tool tests green): `.venv/bin/python -m pytest tests/harness/test_memory_tools.py -q` GREEN
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k telemetry -q tests/harness/test_memory_tools.py -q 2>&1 | tail -6</automated>
  </verify>
  <done>Agent-path memory_recall records telemetry; CLI recall does not; existing tool tests stay green; all VRNK-01 tests GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| agent recall → .retrieval.jsonl | hit locators (derived from project's own memory files) written to a local sidecar |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V23-02-01 | Tampering | malformed/corrupt lines in .retrieval.jsonl | mitigate | corrupt-line-tolerant reader (try/except json.JSONDecodeError per line, template _load_tombstones) — never crashes recall/eviction |
| T-V23-02-02 | Tampering | telemetry mutating memory files corrupts mtime eviction ordering | mitigate | _record_telemetry writes ONLY the sidecar; acceptance asserts recall() body unchanged + mtime-invariant test |
| T-V23-02-03 | Information disclosure | committing telemetry leaks local recall patterns to git | mitigate | .retrieval.jsonl added to _VOSS_MEMORY_GITIGNORE (gitignored per D-01) |
| T-V23-02-SC | Tampering | npm/pip/cargo installs | accept | No installs; all deps pre-existing (zero new packages per RESEARCH audit) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k telemetry -q` GREEN
- `.venv/bin/python -m pytest tests/harness/test_memory_tools.py tests/harness/test_memory_vacuum.py -q` GREEN (no regression)
- `git diff voss/harness/memory_store.py` shows no edit inside recall()
</verification>

<success_criteria>
VRNK-01 fully GREEN; CLI path no-touch; memory files mtime/bytes immutable; vacuum compacts the sidecar; pins excluded from gitignore.
</success_criteria>

<output>
Create `.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-02-SUMMARY.md` when done.
</output>
