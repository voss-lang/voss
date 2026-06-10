---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 03
type: execute
wave: 3
depends_on: [V17-02]
files_modified:
  - voss/harness/claims.py
  - voss/harness/cli.py
autonomous: true
requirements: [VBUS-01, VBUS-02, VBUS-06]

must_haves:
  truths:
    - "voss claims stake|check|release|extend|list exist as click subcommands and register into the main CLI"
    - "check exits 0 on no overlap, 1 on conflict naming the conflicting claim + owner, 2 on missing identity"
    - "claims verbs read identity from VOSS_AGENT_ID; absent -> exit 2 with an actionable stderr message"
    - "check/stake --json conflict output includes a non-empty advice array with a runnable `voss bus send` command naming the owner"
    - "the full two-agent stake/check/release sequence passes with no server running"
  artifacts:
    - path: "voss/harness/claims.py"
      provides: "claims_group click group with five subcommands + advice composition"
      contains: "claims_group"
    - path: "voss/harness/cli.py"
      provides: "claims_group registered in AGENT_COMMANDS"
      contains: "claims_group"
  key_links:
    - from: "voss/harness/cli.py AGENT_COMMANDS"
      to: "voss.harness.claims.claims_group"
      via: "import + tuple membership"
      pattern: "claims_group"
    - from: "claims check conflict path"
      to: "advice array"
      via: "voss bus send command string naming owner"
      pattern: "voss bus send"
---

<objective>
Wrap the V17-02 engine in the `voss claims` click group (stake/check/release/extend/list), wire identity resolution from `VOSS_AGENT_ID` (exit 2 when absent), implement the exit-code contract (0/1/2), and emit `advice` arrays in `--json` output on conflict (VBUS-06). Register the group into the main CLI via `AGENT_COMMANDS`.

Purpose: VBUS-01 shell-scriptable pre-edit guard + VBUS-06 advice arrays, serverless (VBUS-02 acceptance sequence).
Output: `claims_group` in `voss/harness/claims.py`, registered in `voss/harness/cli.py`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-SPEC.md
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-PATTERNS.md

<interfaces>
<!-- Engine from V17-02 this plan consumes -->
voss/harness/claims.py (already provides):
  glob_patterns_overlap, uri_overlap, patterns_overlap, open_claims_db,
  atomic_stake(conn, agent_id, claim_id, patterns, ttl) -> (won, conflicts),
  active_claims, release_claims, extend_claim, canonicalize_pattern, DEFAULT_TTL_SECONDS=1800

<!-- CLI registration target -->
voss/harness/cli.py:
  AGENT_COMMANDS = ( ... )  near line 4484 ; register() iterates it (line 4522)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: claims click group + identity + exit codes + advice</name>
  <files>voss/harness/claims.py</files>
  <behavior>
    - claims stake src/api/** (VOSS_AGENT_ID=claude-1) -> exit 0, claim recorded
    - claims check src/api/handlers.py (VOSS_AGENT_ID=codex-2) -> exit 1, stderr/stdout names claude-1 + the conflicting claim
    - claims check src/other/** (codex-2) -> exit 0
    - claims stake src/api/** (codex-2) -> exit 1 (atomic reject)
    - claims release (claude-1) then claims stake src/api/** (codex-2) -> exit 0
    - any verb with VOSS_AGENT_ID unset -> exit 2, stderr explains how to set it
    - claims check --json on conflict -> JSON with "advice": ["voss bus send \"@claude-1 ...\"", ...] non-empty, owner named
    - claims list shows active claims; expired hidden unless --all
    - claims extend <id> refreshes TTL
  </behavior>
  <read_first>
    - voss/harness/claims.py (the V17-02 engine being wrapped)
    - voss/harness/cli.py (lines ~3556-3614 mcp_group click-group + --json pattern; lines ~2882-2886 jobs_cmd NDJSON; lines ~2304-2327 + ~491 exit-2/exit-1 conventions)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-CONTEXT.md (D-03 release/extend granularity, D-04 idempotent, D-07 advice must name owner + be runnable)
    - tests/harness/claims/test_claims_verbs.py + test_claims_advice.py (RED tests to turn GREEN)
  </read_first>
  <action>Add `@click.group("claims")` (`claims_group`) to `voss/harness/claims.py` with subcommands stake/check/release/extend/list. Each subcommand takes `--cwd` (default ".", `click.Path(file_okay=False)`), `--json "json_mode"` is_flag, and resolves identity via a helper `_resolve_agent_id()` reading `os.environ.get("VOSS_AGENT_ID")` — if empty, `click.echo("VOSS_AGENT_ID not set. Set it to your agent id (e.g. export VOSS_AGENT_ID=claude-1), or run inside a voss-managed pane.", err=True); sys.exit(2)`. stake: `--ttl` (default DEFAULT_TTL_SECONDS), nargs=-1 patterns required; canonicalize each via canonicalize_pattern (catch ValueError -> exit 2), derive a deterministic claim_id (e.g. `agent_id` so one claim-set per agent per D-03, or `agent_id:<hash>`), call atomic_stake; on (False, conflicts) print conflict (and on --json a dict with conflict True, owner, conflicting patterns, and `advice`) then sys.exit(1); on success print/echo and exit 0. check: same overlap scan via active_claims(exclude_agent=me) + patterns_overlap; on conflict echo the owner + conflicting claim and exit 1, else exit 0; --json conflict output MUST include `"advice"` list whose first element is `f'voss bus send "@{owner} I need {pattern} — when are you done?"'` plus a retry hint `voss claims check ...` (D-07/VBUS-06). release: optional claim id arg; bare = release all own (D-03) via release_claims. extend: claim id (or own set) refresh via extend_claim. list: active_claims; `--all` includes expired; print columns (id, agent, patterns, expires-in) or one JSON record per line under --json. Use exit codes 0/1/2 consistently. No fenced code in commits.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/claims/test_claims_verbs.py tests/harness/claims/test_claims_advice.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - test_claims_verbs.py passes including the exit-2-on-missing-VOSS_AGENT_ID case
    - test_claims_advice.py passes: conflict --json advice array non-empty, contains a string beginning "voss bus send" naming the owner
    - `grep -v '^#' voss/harness/claims.py | grep -c 'sys.exit(2)'` >= 1 and `grep -c 'sys.exit(1)' voss/harness/claims.py` >= 1
    - `.venv/bin/python -m voss claims --help` style: `CliRunner().invoke(claims_group, ["--help"]).exit_code == 0` (asserted in a test or summary)
  </acceptance_criteria>
  <done>All five verbs work; identity exit-2 enforced; conflict exit-1 with owner-named advice; serverless sequence GREEN.</done>
</task>

<task type="auto">
  <name>Task 2: Register claims_group in the main CLI</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py (lines ~4484-4525 — AGENT_COMMANDS tuple + register() loop)
    - voss/harness/claims.py (claims_group to import)
  </read_first>
  <action>Import `claims_group` from `voss.harness.claims` at the top-of-module import block in `voss/harness/cli.py` (match existing relative/absolute import style used for other command groups). Add `claims_group` as a new entry in the `AGENT_COMMANDS` tuple (near line 4484) alongside the existing groups (e.g. after `board_cmd`/`audit_cmd`). Do NOT modify `register()` itself — it already iterates `AGENT_COMMANDS`. Do NOT touch board/jobs code paths (VBUS-06 surgical scope). Verify the top-level `voss claims --help` resolves through the registered group.</action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness import cli; assert any(getattr(c, 'name', None) == 'claims' for c in cli.AGENT_COMMANDS), 'claims_group not registered'; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - The one-liner above prints OK (claims_group is a member of AGENT_COMMANDS)
    - `git diff voss/harness/cli.py` shows only an import line + a tuple-entry addition (no board/jobs changes)
    - `grep -c 'claims_group' voss/harness/cli.py` >= 2 (import + tuple entry)
  </acceptance_criteria>
  <done>claims group reachable from the main CLI; no collateral edits to board/jobs.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| shell env -> claims CLI | VOSS_AGENT_ID and pattern args are attacker-controllable input |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V17-06 | Tampering | pattern args -> storage | mitigate | canonicalize_pattern (V17-02) rejects traversal before stake/check |
| T-V17-07 | Spoofing | VOSS_AGENT_ID forgery | accept | Advisory-only design (SEED-001); documented in VBUS-07 doc, not enforced |
| T-V17-08 | Info disclosure | conflict output leaks owner id | accept | Owner id disclosure is the feature (coordinate-with-owner); advisory, low-value |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/claims/ -x -q` fully GREEN (overlap + verbs + concurrent + ttl + advice).
- claims_group registered; board/jobs diff-clean.
</verification>

<success_criteria>
Five claims verbs shippable as a shell pre-edit guard with the 0/1/2 exit contract, identity from VOSS_AGENT_ID, and owner-naming advice arrays — all serverless.
</success_criteria>

<output>
Create `.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-03-SUMMARY.md` when done.
</output>
