---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/harness/claims/__init__.py
  - tests/harness/claims/test_overlap.py
  - tests/harness/claims/test_claims_verbs.py
  - tests/harness/claims/test_claims_concurrent.py
  - tests/harness/claims/test_claims_ttl.py
  - tests/harness/claims/test_claims_advice.py
  - tests/harness/bus/__init__.py
  - tests/harness/bus/test_bus_wait.py
  - tests/harness/bus/test_bus_inbox.py
  - tests/harness/bus/test_bus_durability.py
  - tests/harness/test_env_injection.py
  - tests/harness/test_coordination_doc.py
  - tests/harness/test_coherence_guard.py
autonomous: true
requirements: [VBUS-01, VBUS-02, VBUS-03, VBUS-04, VBUS-05, VBUS-06, VBUS-07, VBUS-08]
# D-02 deviation note: claims storage is .voss-cache/claims.sqlite (NOT .voss/) — locked in discussion, see CONTEXT.md D-02.

must_haves:
  truths:
    - "Every VBUS-01..08 acceptance criterion has a named pytest that currently fails (RED) or is xfail-gated on V15"
    - "Running the claims+identity+coherence test suite produces collected-but-failing tests, not collection errors"
  artifacts:
    - path: "tests/harness/claims/test_overlap.py"
      provides: "Glob + URI overlap unit cases from SPEC VBUS-01/02"
    - path: "tests/harness/claims/test_claims_verbs.py"
      provides: "Two-agent stake/check/release acceptance sequence"
    - path: "tests/harness/claims/test_claims_concurrent.py"
      provides: "Concurrent-stake exactly-one-winner test"
    - path: "tests/harness/bus/test_bus_wait.py"
      provides: "Bus wait/timeout scaffold (xfail until V15)"
    - path: "tests/harness/test_coherence_guard.py"
      provides: "VBUS-08 substrate-absence assertions"
  key_links:
    - from: "tests/harness/claims/test_claims_verbs.py"
      to: "voss.harness.claims.claims_group"
      via: "import (will fail until V17-03 ships)"
      pattern: "from voss.harness.claims import"
---

<objective>
Wave 0 test scaffold for all of V17. Create the failing-test surface (RED) that every later plan must turn GREEN, so the phase is Nyquist-compliant: each VBUS-01..08 acceptance criterion maps to a named, collectable pytest assertion. Bus tests (VBUS-04/05) are scaffolded but `xfail(strict=False)`-gated because their implementation is V15-gated — they collect and run without erroring, and will XPASS once the bus plans ship post-V15.

Purpose: No later task may claim "no test exists." Tests come first.
Output: `tests/harness/claims/`, `tests/harness/bus/`, and three top-level harness test files, all collectable.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-PATTERNS.md

<interfaces>
<!-- Contracts the scaffold writes tests AGAINST. These are the targets later plans implement. -->

claims module (V17-02 / V17-03 will provide): voss/harness/claims.py
  - claims_group: click.Group with subcommands stake, check, release, extend, list
  - overlap helpers (V17-02): glob_patterns_overlap(p1: str, p2: str) -> bool ; uri_overlap(u1: str, u2: str) -> bool
  - Exit codes: 0 = clear/success, 1 = conflict, 2 = identity/usage error
  - Identity source: VOSS_AGENT_ID env var; absent on stake/check/release/extend/list -> exit 2
  - --cwd option on every subcommand; storage at <cwd>/.voss-cache/claims.sqlite (D-02)
  - --json on every subcommand; conflict --json includes non-empty "advice": [<str>...] with a runnable `voss bus send "@<owner> ..."` (D-07, VBUS-06)
  - --ttl <seconds> on stake (default 1800); --all on list

bus client module (V17-06, V15-gated): voss.harness.bus_client.bus_group
  - subcommands send / inbox / wait ; discovers server via VOSS_SERVER_PORT + VOSS_SERVER_TOKEN; absent -> exit 2
  - wait --mention <id> --timeout <s> ; timeout -> exit 124

bus server (V17-05, V15-gated): POST /bus/send, GET /bus/inbox, GET /bus/events ; journal .voss/bus/messages.jsonl + cursors.json
</interfaces>

<!-- Analog test patterns to copy -->
@tests/harness/board/test_board_cli.py
@tests/harness/conftest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Claims test scaffolds (overlap + verbs + concurrency + ttl + advice)</name>
  <files>tests/harness/claims/__init__.py, tests/harness/claims/test_overlap.py, tests/harness/claims/test_claims_verbs.py, tests/harness/claims/test_claims_concurrent.py, tests/harness/claims/test_claims_ttl.py, tests/harness/claims/test_claims_advice.py</files>
  <read_first>
    - tests/harness/board/test_board_cli.py (CliRunner + tmp_path + env-injection pattern to mirror)
    - tests/harness/conftest.py (isolated_state autouse fixture; new dirs need __init__.py)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md (VBUS-01/02/06 acceptance bullets — every bullet becomes a test)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md (Pattern 3/4 expected overlap results; "Phase Requirements -> Test Map" table)
  </read_first>
  <action>Create empty `tests/harness/claims/__init__.py`. Write five pytest files using `click.testing.CliRunner(mix_stderr=False)` and `tmp_path`, importing `from voss.harness.claims import claims_group` (and `glob_patterns_overlap`, `uri_overlap` in test_overlap). These imports SHOULD fail at collection only if the module is wholly absent — to keep tests collectable now, wrap the import in a module-level guard: `pytest.importorskip("voss.harness.claims")` at top of each file is FORBIDDEN (would green-skip); instead use a try/except ImportError that sets a module flag and `pytestmark = pytest.mark.xfail(reason="claims module not yet implemented (V17-02/03)", strict=False)` so tests RUN, FAIL/xfail now, and XPASS once implemented. test_overlap.py: assert glob_patterns_overlap("src/api/**","src/api/handlers.py") is True; ("src/api/**","src/other/**") is False; uri_overlap("card://123","card://123") True; ("card://123","card://124") False; ("bead://p/x","bead://p") True (prefix at / boundary per D-06); ("card://12","card://123") False. test_claims_verbs.py with @pytest.mark.acceptance: two distinct VOSS_AGENT_ID values via runner env — A stakes src/api/**, B check src/api/handlers.py exits 1 naming A, B check src/other/** exits 0, B stake src/api/** exits 1, A release then B stake exits 0; plus test_missing_agent_id (no VOSS_AGENT_ID -> exit 2, stderr names the var). test_claims_concurrent.py: spin N subprocesses or threads racing to stake an overlapping pattern, assert exactly one exit-0 winner (use a file-backed db under tmp_path; mark it integration). test_claims_ttl.py: stake with --ttl 1 (or 1s), assert check blocks immediately then after sleep past TTL check exits 0; default-TTL applied when --ttl absent. test_claims_advice.py with @pytest.mark.acceptance: `claims check --json` on conflict emits a dict with non-empty "advice" list containing a string starting with "voss bus send" and containing the conflicting owner id (VBUS-06). Do NOT include fenced code in the module beyond test bodies; do NOT use grep-count gates.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/claims/ --co -q</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/claims/ --co -q` lists tests from all five files with zero collection errors
    - `.venv/bin/python -m pytest tests/harness/claims/ -q` reports the tests as xfail or failed (RED), never passed and never errored-on-collection
    - test_overlap.py contains the six SPEC overlap cases above as discrete assertions
    - test_claims_verbs.py contains a function asserting exit_code == 2 when VOSS_AGENT_ID is unset
    - No file uses `pytest.importorskip` and no file uses `grep -c`-style gating
  </acceptance_criteria>
  <done>Five claims test files collect cleanly and run RED/xfail; six overlap cases + exit-code-2 case + advice-array case present.</done>
</task>

<task type="auto">
  <name>Task 2: Bus test scaffolds (wait + inbox + durability), V15-gated xfail</name>
  <files>tests/harness/bus/__init__.py, tests/harness/bus/test_bus_wait.py, tests/harness/bus/test_bus_inbox.py, tests/harness/bus/test_bus_durability.py</files>
  <read_first>
    - tests/harness/conftest.py (server/app fixtures available to harness tests; check for an existing app/client fixture)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md (VBUS-04/05 acceptance bullets)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md (Pattern 2 SSE fan-out; bus durability behavior; "Phase Requirements -> Test Map")
  </read_first>
  <action>Create `tests/harness/bus/__init__.py`. Write three pytest files, each with `pytestmark = pytest.mark.xfail(reason="bus is V15-gated — implemented in V17-05/V17-06 after V15 ships", strict=False)` so they collect and run without erroring and XPASS once bus ships. test_bus_wait.py: a test that `bus wait --mention A --timeout 60` unblocks within 2s of `bus send "@A done"` (assert message printed, exit 0); test_timeout: `bus wait` with no matching message exits 124 (nonzero) at timeout. test_bus_inbox.py: after two `bus send` calls, `bus inbox` returns both, second call returns none (cursor advanced). test_bus_durability.py: send a message, restart the server/app fixture, `inbox` still returns the pre-restart unread message (VBUS-05). Reference `voss.harness.bus_client.bus_group` and the server endpoints in setup; the strict=False xfail prevents these from blocking the now-executable waves. Do NOT inline implementation; keep test bodies declarative.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/bus/ -q</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/bus/ -q` runs to completion reporting xfail (not errored, not passed)
    - All three files carry `pytestmark = pytest.mark.xfail(... strict=False)` with a reason naming V15 gating
    - test_bus_wait.py contains both an unblock-within-2s test and an exit-124 timeout test
    - test_bus_durability.py exercises a server restart and a post-restart inbox read
  </acceptance_criteria>
  <done>Three bus test files collect + run as xfail; V15-gated reason present; no collection errors.</done>
</task>

<task type="auto">
  <name>Task 3: Identity, doc, and coherence-guard test scaffolds</name>
  <files>tests/harness/test_env_injection.py, tests/harness/test_coordination_doc.py, tests/harness/test_coherence_guard.py</files>
  <read_first>
    - apps/voss-app/src/swarm/swarmTypes.ts (the only swarm file today — coherence test asserts swarm/ is byte-unchanged across the phase)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md (VBUS-03/07/08 acceptance bullets)
    - tests/harness/board/test_board_cli.py (CliRunner --help pattern for the doc test)
  </read_first>
  <action>Write three top-level harness test files. test_env_injection.py: VBUS-03 has a manual-only end-to-end (live Tauri PTY, see VALIDATION.md), so the automatable portion is the CLI side — `voss claims stake` with VOSS_AGENT_ID set records that id as owner (xfail until V17-03/V17-04 land), and a bare invocation without the var exits 2. Mark module xfail(strict=False) with reason "needs claims (V17-03) + injection (V17-04)". test_coordination_doc.py: assert `docs/agent-coordination.md` exists and that each shipped verb's `--help` exits 0 via CliRunner against `claims_group` (and `bus_group` guarded by try/except since bus is V15-gated) — xfail(strict=False) until V17-07 writes the doc and V17-03 ships the verbs. test_coherence_guard.py (VBUS-08, NOT xfail — must be enforceable now and at phase end): record the SHA-256 of every file under `apps/voss-app/src/swarm/` (currently swarmTypes.ts) into the test as a baseline dict computed at runtime by hashing the current files, then assert the directory contains no new files beyond the known set; assert no `package.json` under apps/voss-app or harness pyproject.toml adds an fs-watcher/chokidar/watchdog dependency (grep the dependency sections with `grep -v '^#' | grep -c` filtered, expecting 0 fs-watcher matches); assert no new `*.tsx`/`*.jsx` Solid component files were added under apps/voss-app/src for V17 (scope this to a documented allowlist check, not a blanket count). Keep the coherence assertions runnable today (they pass now, and must keep passing — they catch a future violator).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_coherence_guard.py -q</automated>
  </verify>
  <acceptance_criteria>
    - test_coherence_guard.py PASSES today (baseline is clean) and asserts swarm/ file-set unchanged + no fs-watcher dep + no unexpected new Solid component
    - test_env_injection.py and test_coordination_doc.py collect and run as xfail (not errored)
    - The fs-watcher dependency check filters comment lines (`grep -v '^#'`) before counting, never a bare `== 0` on an unfiltered file
    - `.venv/bin/python -m pytest tests/harness/test_env_injection.py tests/harness/test_coordination_doc.py tests/harness/test_coherence_guard.py -q` reports no collection errors
  </acceptance_criteria>
  <done>Coherence guard passes green now; identity + doc scaffolds run xfail; all three collect.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test harness -> filesystem | Tests write only under pytest tmp_path; no writes to repo source |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V17-01 | Tampering | coherence guard baseline | mitigate | Baseline hashes computed at runtime from current files, not hardcoded — a real swarm/ edit fails the test |
| T-V17-SC | Tampering | npm/pip installs | mitigate | V17 adds zero new packages (RESEARCH "No New Dependencies"); coherence test asserts no fs-watcher dep added |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/claims/ tests/harness/bus/ tests/harness/test_env_injection.py tests/harness/test_coordination_doc.py tests/harness/test_coherence_guard.py -q` runs with zero collection errors; coherence guard green; everything else RED/xfail.
</verification>

<success_criteria>
Every VBUS-01..08 acceptance criterion is represented by a named, collectable pytest. No `importorskip`. Bus tests xfail-gated on V15. Coherence guard enforceable now.
</success_criteria>

<output>
Create `.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-01-SUMMARY.md` when done.
</output>
