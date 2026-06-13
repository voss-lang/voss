---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 07
type: execute
wave: 5
depends_on: ["V23-05", "V23-02"]
files_modified:
  - voss/harness/memory_cli.py
autonomous: true
requirements: [VRNK-07]

must_haves:
  truths:
    - "voss memory pin <locator> then list --pinned shows the row; unpin then list --pinned is empty"
    - "voss memory show <locator> prints full text + telemetry (nonzero retrieval_count for a recalled row)"
    - "voss memory list prints locator, source, retrieval_count, last_retrieved, pin flag (filterable by --source/--pinned)"
    - "Unknown locator on pin/unpin/show exits 1 with a stderr message"
    - "voss memory reindex [--check] mirrors the sync --check exit contract (0 clean / 1 + stale list)"
    - "All verbs accept --global (project default) per V21 convention"
  artifacts:
    - path: "voss/harness/memory_cli.py"
      provides: "pin, unpin, list, show, reindex commands under memory_group"
      contains: "memory_group.command"
  key_links:
    - from: "voss/harness/memory_cli.py"
      to: "MemoryStore._load_pins/_save_pins/reindex/_load_telemetry_compacted"
      via: "verb handlers delegate to store methods"
      pattern: "store\\.(reindex|_load_pins|_save_pins)"
---

<objective>
Implement VRNK-07 CLI verbs under the existing `voss memory` click group: `pin`/`unpin <locator>`, `list [--source] [--pinned] [--json]`, `show <locator>`, and `reindex [--check]`. They surface the pins (V23-05) and telemetry (V23-02) that would otherwise be operator-invisible, and expose the reindex drift gate with the `voss sync --check` exit contract. All verbs accept `--global` (project default) per the V21 verb convention (D-12).

Purpose: Without these verbs, telemetry and pins are invisible and the drift gate is unreachable. This is the operator surface for the whole phase.
Output: five new commands in `voss/harness/memory_cli.py`, each delegating to store methods.
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
From voss/harness/memory_cli.py (confirmed):
- @click.group("memory") def memory_group()  # line 18
- existing verb pattern (vacuum, line ~23-40): @memory_group.command("vacuum") + --cwd option (default ".", click.Path(file_okay=False)); store = MemoryStore(cwd); if not store.root.exists(): echo err + sys.exit(1); store.bind(session_id="vacuum")
- imports: hashlib, sys, Path, click, voss_md, MemoryStore  # lines 1-16

From voss/harness/memory_store.py (V23-05 + V23-02):
- _load_pins(self) -> set[str]; _save_pins(self, pins) -> None; _pins_path schema {"pins":[{locator, pinned_at}]}
- reindex(self, *, check=False) -> result(stale: list[str], reembedded: int, chroma_available: bool)
- _load_telemetry_compacted(self) -> dict  # {locator: {count, last_retrieved}}
- _locator_from_path(self, source_dir, path) -> str  # locator vocabulary; valid prefixes turn:/ledger:/decision:/convention:/note:
- MemoryStore(cwd, *, root_override=None)  # V21 — --global resolves a global root_override

From voss/cli.py:519-522 — sync --check exit contract (echo + raise SystemExit(1) on drift; else echo in-sync)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: pin / unpin / show verbs (with locator validation + exit 1)</name>
  <read_first>
    - voss/harness/memory_cli.py:1-40 (imports + group + vacuum verb pattern to copy: --cwd option, store.root.exists() guard, sys.exit(1))
    - V23-RESEARCH.md:511-532 (Pattern 7 CLI verb registration — verb list + --cwd/--global pattern), :849-851 (V5 input validation — validate locator against make_id prefixes before writing .pins.json)
    - V23-PATTERNS.md:277-349 (memory_cli analogs — command pattern, missing-store exit 1, unknown-locator exit 1)
    - V23-CONTEXT.md D-02 (.pins.json committed), D-12 (--global flag, project default), D-14 (show output: full text + telemetry)
    - V23-SPEC.md VRNK-07 acceptance (pin→list shows; show→nonzero count; unknown locator exit 1)
  </read_first>
  <action>
    Add three commands to `memory_group` in voss/harness/memory_cli.py, copying the existing `vacuum` command structure (--cwd default ".", store.root.exists() guard → sys.exit(1)):
    - `pin <locator>` [--cwd] [--global]: resolve store (MemoryStore(cwd) or root_override for --global per D-12); VALIDATE the locator against known make_id prefixes (turn:/ledger:/decision:/convention:/note: — RESEARCH security V5) AND that it corresponds to an existing memory row; unknown/invalid → `click.echo(f"unknown locator: {locator}", err=True); sys.exit(1)`. Otherwise add `{locator, pinned_at: now-ISO}` to `.pins.json` via `_load_pins`/`_save_pins` (idempotent — pinning an already-pinned locator is a no-op success). Print confirmation.
    - `unpin <locator>` [--cwd] [--global]: remove the locator from `.pins.json`; unknown/not-pinned locator → exit 1 with stderr message (per VRNK-07 unknown-locator contract). Print confirmation.
    - `show <locator>` [--cwd] [--global]: print the full memory body for the locator + its telemetry (retrieval_count, last_retrieved from `_load_telemetry_compacted`) + pin flag; unknown locator → exit 1 stderr. Full text, not excerpt (D-14).
    Pitfall 6: store/resolve locators using exactly `_locator_from_path` vocabulary so pins match eviction exemption. Use `click.testing.CliRunner` mentally as the test harness target.
  </action>
  <acceptance_criteria>
    - `grep -c 'memory_group.command("pin")\|memory_group.command("unpin")\|memory_group.command("show")' voss/harness/memory_cli.py` == 3
    - pin/unpin/show + unknown-locator-exit-1 tests pass: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "pin or cli or show or unknown" -q` GREEN (or `-k cli`)
    - Each verb has --global option (grep: `grep -c "'--global'\|--global" voss/harness/memory_cli.py` >= 3)
    - Unknown locator path calls sys.exit(1) (grep: `grep -c 'sys.exit(1)' voss/harness/memory_cli.py` increased)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "cli or pin" -q 2>&1 | tail -5</automated>
  </verify>
  <done>pin/unpin/show verbs delegate to store pin + telemetry methods; locator validated; unknown locator exits 1; --global supported.</done>
</task>

<task type="auto">
  <name>Task 2: list + reindex verbs (telemetry columns + sync-check exit contract)</name>
  <read_first>
    - voss/harness/memory_cli.py:23-40 (vacuum verb pattern)
    - voss/cli.py:519-522 (sync --check exit contract to mirror — echo + raise SystemExit(1))
    - V23-RESEARCH.md:460-470 (reindex exit contract code), :762-767 (Open Q: list output for no-memory-store / no-pins → empty not error)
    - V23-PATTERNS.md:332-349 (reindex --check exit contract for memory)
    - V23-CONTEXT.md D-12 (--global), D-14 (list output: table, columns locator/source/retrieval_count/last_retrieved/pin flag, optional --json), D-10/D-11 (reindex file-based sources, manifest)
    - V23-SPEC.md VRNK-05 acceptance (--check exit 1 + stale list; reindex repairs; chroma absent exit 0 + notice) and VRNK-07 (list filterable by --source/--pinned)
  </read_first>
  <action>
    Add two commands to `memory_group`:
    - `list` [--cwd] [--source SRC] [--pinned] [--json] [--global]: build rows from the store — for each memory locator, columns = locator, source, retrieval_count, last_retrieved (from `_load_telemetry_compacted`, default 0 / "—"), pinned flag (from `_load_pins`). Filter by `--source` and `--pinned`. Default = readable table following existing CLI output conventions (D-14); `--json` emits a structured array. Empty result (no pins / no telemetry) → print empty / "(none)" and exit 0 — only exit 1 if the store root is missing (RESEARCH Open Q 3).
    - `reindex` [--cwd] [--check] [--global]: call `store.reindex(check=check)`. Mirror the `voss sync --check` exit contract (voss/cli.py:519-522):
        * chroma absent (result.chroma_available False) → `click.echo("chroma not installed — reindex is a no-op")`; return (exit 0).
        * `--check` with stale list non-empty → echo each stale locator to stderr, then `raise SystemExit(1)`. Empty → `click.echo("memory index in sync")`; return (exit 0).
        * bare reindex → echo `f"re-embedded: {result.reembedded}"`; exit 0.
      All verbs resolve --global via the V21 root_override convention (D-12).
    Confirm the full VRNK-05 CLI flow: hand-edit → `reindex --check` exit 1 naming the locator → `reindex` re-embeds → `reindex --check` exit 0 (the scaffold drift/reindex tests assert this through CliRunner).
  </action>
  <acceptance_criteria>
    - `grep -c 'memory_group.command("list")\|memory_group.command("reindex")' voss/harness/memory_cli.py` == 2
    - list shows telemetry + pin columns; pin→list--pinned→unpin→empty flow passes: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "cli or pin" -q` GREEN
    - reindex --check exit contract tests pass: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "reindex or drift" -q` GREEN
    - reindex raises SystemExit(1) on drift (grep: `grep -c 'SystemExit(1)' voss/harness/memory_cli.py` >= 1)
    - All VRNK-07 + VRNK-05-CLI tests GREEN
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "cli or pin or reindex or drift" -q 2>&1 | tail -6</automated>
  </verify>
  <done>list surfaces telemetry + pin columns (filterable, --json); reindex verb mirrors sync --check exit contract incl. chroma-absent no-op; all VRNK-07 tests GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI arg (locator) → .pins.json write | operator-supplied locator string crosses into a committed sidecar file |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V23-07-01 | Tampering | locator injection via CLI (`pin "../../etc/passwd"`) | mitigate | validate locator against known make_id prefixes (turn:/ledger:/decision:/convention:/note:) before writing .pins.json; reject + exit 1 (RESEARCH V5) |
| T-V23-07-02 | Tampering | corrupt .pins.json from manual edit breaks list/pin | mitigate | _load_pins try/except → empty set; verbs degrade gracefully |
| T-V23-07-03 | Information disclosure | show prints sensitive memory body to terminal | accept | show is an explicit operator command on the operator's own local store; no new exposure |
| T-V23-07-SC | Tampering | npm/pip/cargo installs | accept | No installs; zero new packages (RESEARCH audit) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "cli or pin or reindex or drift" -q` GREEN
- `.venv/bin/python -m pytest tests/harness/ -k "memory" -q` no regression in existing memory CLI tests
- Manual smoke (optional): `voss memory list` exits 0 on a real repo
</verification>

<success_criteria>
VRNK-07 GREEN; pin/unpin/list/show/reindex verbs live under voss memory; telemetry + pins operator-visible; reindex exit contract matches sync --check; --global supported; locator injection rejected.
</success_criteria>

<output>
Create `.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-07-SUMMARY.md` when done.
</output>
