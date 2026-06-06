---
phase: V7-engineering-manager-loop-supersedes-o5
plan: 02
type: execute
wave: 2
depends_on: ["V7-01"]
files_modified:
  - voss/harness/cli.py
autonomous: true
requirements: [VEM-CLI, VEM-PERSIST, VEM-SIGNOFF]
must_haves:
  truths:
    - "voss team run \"<goal>\" composes team + session-tree + board + reviewer + em_loop and runs autonomously to all-cards-terminal, exits 0 on stub"
    - "With no .voss/team.voss the run uses the DEFAULT_ROSTER 7-role roster + default ceiling; an explicit file overrides"
    - "RunFinal persists to .voss/sessions/<root_id>/run-final.json (10 fields) and is re-readable"
    - "The CLI prints the RunFinal summary and prompts approve/reject; the decision is recorded into run-final.json; reject reverts nothing on disk"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "@team_group.command('run') team_run_cmd + _default_team_config() + _persist_run_final() helpers"
      contains: "team_group.command(\"run\")"
    - path: "voss/harness/cli.py"
      provides: "_persist_run_final mirroring _write_node_file (mkdir parents, asdict, chmod 0o600)"
      contains: "_persist_run_final"
  key_links:
    - from: "voss/harness/cli.py team_run_cmd"
      to: "voss.harness.em.loop.em_loop"
      via: "asyncio.run(em_loop(idea=goal, em_handle=..., em_agent=DeterministicEMStub, ...))"
      pattern: "asyncio\\.run\\(.*em_loop"
    - from: "voss/harness/cli.py _persist_run_final"
      to: ".voss/sessions/<root_id>/run-final.json"
      via: "path derived from rf.root_id; write_text(json.dumps(asdict(rf)+sign_off)); chmod 0o600"
      pattern: "run-final\\.json"
    - from: "voss/harness/cli.py team_run_cmd"
      to: "board.spawn_card"
      via: "await board.spawn_card(risk_tier=\"med\") BEFORE em_loop so total_cards>=1"
      pattern: "spawn_card"
---

<objective>
Implement `voss team run "<goal>"` and its two helpers in `voss/harness/cli.py`, turning the V7-01 RED scaffold GREEN. This is the entire VEM-CLI/PERSIST/SIGNOFF delta: a single click subcommand that composes the shipped V3–V6 + O5 stack, runs the async `em_loop` to terminal, persists RunFinal to a session-root sidecar, prints a summary, and records a human approve/reject decision.

Purpose: Turn the shipped O5 pieces into a runnable product. Pure composition — no reimplementation of em_loop, the cage, the board, or the session tree.

Output: Three additions to cli.py — `_default_team_config()` (module-level helper, no parser), `_persist_run_final()` (module-level helper mirroring `_write_node_file`), and `@team_group.command("run")` (`team_run_cmd`). The V7-01 suite goes from 10 RED to 10 GREEN; `tests/harness/em/` stays 79/79 green.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-SPEC.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-CONTEXT.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-RESEARCH.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-PATTERNS.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-VALIDATION.md

<interfaces>
<!-- All VERIFIED via direct execution in V7-RESEARCH.md. Use these exact signatures — no codebase exploration needed. -->

em_loop (voss/harness/em/loop.py:88) — async, keyword-only:
  async def em_loop(*, idea: str, em_handle: EMBoardHandle, em_agent: object,
                    roster_descriptions: dict[str,str] | None = None,
                    max_iterations: int = 50) -> RunFinal

EMBoardHandle (voss/harness/em/handle.py:82) — keyword-only:
  EMBoardHandle(*, board, registry, team_config, manager, base_gate, cwd,
                subagent_runner=None, renderer=None, provider=None, model="")

Board.from_team_config (voss/harness/board/machine.py:266) — SINGLE reviewer slot (V6-03 NOT executed):
  Board.from_team_config(team_config, *, recorder, reviewer, cwd,
                         clock=time.monotonic, parent_node_id=None, per_card_budget=100_000)
  board.spawn_card(risk_tier="med")  # async; call BEFORE em_loop so total_cards>=1

SessionTreeManager (voss/harness/session_tree.py:147) — keyword-only:
  SessionTreeManager(root_node, *, reserve: int, cwd: Path)
  root: SessionTreeNode.create_root(cwd=cwd, limit=500_000)
  rf.root_id == manager root id

Stubs:
  DeterministicReviewerStub(conf=0.99, verdict="pass")  # voss.harness.board.stub
  DeterministicEMStub(scripted=[EMPlanResponse(ops=[CreateTicketOp(original_idea=..., worker_role="backend")]), EMPlanResponse(ops=[NoopOp(reason="waiting")])])  # voss.harness.em.stub / .schema

Default-roster helper inputs (voss/harness/team.py):
  DEFAULT_ROSTER (:48, 7 roles); TeamCeiling(budget_tokens=500_000, scope=None, latency_seconds=3600)
  subagent_spec_from_role(role_name=..., role_decl_span=Span(file="<default>", line_start=0, col_start=0, line_end=0, col_end=0), kvs={}, ceiling=ceiling, ceiling_ast=None, apply_role_defaults=True)
  SubagentRegistry().register(spec); registry.entries() → specs with .id/.description
  TeamConfig(name="default", ceiling=..., policy=TeamPolicy(p=None), em_agent_id=None, roster_ids=frozenset(DEFAULT_ROSTER), board=BoardSpec(raw_items=()), rituals=())

PermissionGate(mode="auto", auto_yes=True)  # voss.harness.permissions

RunFinal (voss/harness/em/tickets.py:112) — 10 fields, frozen+slots, do NOT mutate:
  root_id, idea, total_cards, done_count, blocked_count, killed_count, rescope_count, em_iterations, ts, kind

_write_node_file analog (voss/harness/session_tree.py:97-102):
  path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(..., indent=2)); path.chmod(0o600)

Team-file load (cli.py:3800-3816, team_check_cmd analog):
  from voss import parse; from voss.ast_nodes import TeamDecl; from voss.harness.team import compile_team
  parse(src if src.endswith("\n") else src+"\n", str(p)); team_decl=next(d for d in program.body if isinstance(d,TeamDecl)); compile_team(team_decl) -> (config, registry)

Async-drive analog: cli.py:3575 consensus_cmd → asyncio.run(coro) in sync click body.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add _default_team_config() and _persist_run_final() helpers to cli.py</name>
  <files>voss/harness/cli.py</files>
  <behavior>
    - _default_team_config() returns (TeamConfig, SubagentRegistry) with 7 DEFAULT_ROSTER roles registered, ceiling budget 500_000 / latency 3600 / scope None, roster_ids == frozenset(DEFAULT_ROSTER).
    - _persist_run_final(rf, cwd, decision=None) writes <cwd>/.voss/sessions/<rf.root_id>/run-final.json containing dataclasses.asdict(rf) (the 10 fields); when decision is not None, adds a superset "sign_off" key {"decision", "ts"}; file mode is 0o600; returns the path. RunFinal is never mutated.
    - Re-readability: json.loads(path.read_text()) round-trips; calling _persist_run_final twice (without then with decision) overwrites the same path adding sign_off.
  </behavior>
  <read_first>
    - voss/harness/cli.py:3777-3878 (team_group + team_check_cmd lazy-import style + AGENT_COMMANDS — confirm team_group already registered)
    - voss/harness/cli.py:3540-3584 (consensus_cmd: Path(cwd_str).resolve(), asyncio.run, click.echo, sys.exit conventions)
    - voss/harness/session_tree.py:97-102 (_write_node_file — the chmod 0o600 sidecar-write pattern to mirror)
    - voss/harness/team.py:48 (DEFAULT_ROSTER), :588 (compile_team), and subagent_spec_from_role signature
    - voss/harness/em/tickets.py:112 (RunFinal frozen 10 fields)
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-RESEARCH.md (Pattern 2, Pattern 4, Pitfall 5 Span kwargs, Pitfall 7 model-tier)
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-PATTERNS.md (_default_team_config + _persist_run_final analog sections)
  </read_first>
  <action>
    Add two module-level helpers near the team subcommands in cli.py (above where team_run_cmd will live in Task 2). Follow the project-wide lazy-import-inside-function convention only where it avoids circular imports; team/session_tree/em imports are already safe at these call sites — match team_check_cmd's local-import style.

    `_default_team_config() -> tuple[TeamConfig, SubagentRegistry]`: build TeamCeiling(budget_tokens=500_000, scope=None, latency_seconds=3600); create SubagentRegistry(); loop DEFAULT_ROSTER calling subagent_spec_from_role with keyword Span(file="<default>", line_start=0, col_start=0, line_end=0, col_end=0), kvs={}, ceiling=ceiling, ceiling_ast=None, apply_role_defaults=True; register each; return TeamConfig(name="default", ceiling=ceiling, policy=TeamPolicy(p=None), em_agent_id=None, roster_ids=frozenset(DEFAULT_ROSTER), board=BoardSpec(raw_items=()), rituals=()) and the registry. Do NOT construct AST TeamDecl — direct construction only (V7-RESEARCH anti-pattern). Note Pitfall 7: apply_role_defaults=True resolves model tiers via get_model_tiers(); production relies on a configured catalog; the V7-01 test fixture monkeypatches it.

    `_persist_run_final(rf, cwd, decision=None) -> Path`: run_dir = cwd / ".voss" / "sessions" / rf.root_id; run_dir.mkdir(parents=True, exist_ok=True); persist_path = run_dir / "run-final.json"; data = dataclasses.asdict(rf); if decision is not None: data["sign_off"] = {"decision": decision, "ts": <UTC isoformat seconds>}; persist_path.write_text(json.dumps(data, indent=2)); persist_path.chmod(0o600); return persist_path. SECURITY: root_id comes ONLY from rf.root_id (a SessionTreeNode UUID), never user input — this prevents path traversal (threat T-V7-05). Mirror _write_node_file exactly; do NOT mutate rf (it is frozen+slots; AttributeError if attempted).

    No fenced code in this action. Identifiers/signatures are in <interfaces>.
  </action>
  <verify>
    <automated>.venv/bin/python -c "import ast,sys; src=open('voss/harness/cli.py').read(); assert '_default_team_config' in src and '_persist_run_final' in src and 'run-final.json' in src and 'chmod(0o600)' in src.replace(' ',''), 'helpers missing'; print('helpers present')" && .venv/bin/python -m pytest tests/harness/em/ -x -q 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - cli.py defines module-level `_default_team_config` and `_persist_run_final`.
    - `_persist_run_final` writes path `.voss/sessions/<rf.root_id>/run-final.json`, calls `mkdir(parents=True, exist_ok=True)`, serializes via `dataclasses.asdict(rf)`, and calls `chmod(0o600)`.
    - root_id is sourced from `rf.root_id` (grep shows no user-supplied root_id in the path build).
    - RunFinal is not mutated (no `rf.<attr> =` assignment; sign_off lives only in the JSON dict).
    - `tests/harness/em/` still 79/79 green (no regression from the import/helper additions).
  </acceptance_criteria>
  <done>Both helpers exist in cli.py with the verified signatures; default config builds the 7-role roster; sidecar writer mirrors _write_node_file with 0o600 and root_id-derived path; em suite green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add @team_group.command("run") composing the stack, persisting, and prompting sign-off</name>
  <files>voss/harness/cli.py</files>
  <behavior>
    - `voss team run "<goal>"` with no .voss/team.voss → uses _default_team_config(); exits 0 on stub; produces ≥1 board card (pre-spawned med) and a RunFinal.
    - With .voss/team.voss present → parse + compile_team that roster/ceiling instead.
    - After the loop, run-final.json exists under .voss/sessions/<root_id>/ with the 10 fields; CLI prints the RunFinal summary; click.prompt(approve/reject) records the decision into the sidecar (re-write with sign_off).
    - reject records decision="reject" and reverts nothing on disk (no node JSON added/removed by the sign-off path).
  </behavior>
  <read_first>
    - voss/harness/cli.py:3540-3584 (consensus_cmd async-drive + echo + exit) and :3777-3816 (team_group + team_check_cmd team-file load branch)
    - voss/harness/em/loop.py:88 (em_loop keyword-only signature)
    - voss/harness/em/handle.py:82 (EMBoardHandle constructor)
    - voss/harness/board/machine.py:266 (Board.from_team_config SINGLE reviewer slot) + spawn_card
    - voss/harness/board/stub.py (DeterministicReviewerStub) ; voss/harness/em/stub.py + em/schema.py (DeterministicEMStub, EMPlanResponse, CreateTicketOp, NoopOp)
    - voss/harness/session_tree.py:147 (SessionTreeManager) + SessionTreeNode.create_root
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-RESEARCH.md (Pattern 1/3/5/6 + Pitfalls 1,2,4,6)
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-PATTERNS.md (subcommand registration, async-drive, sign-off prompt, output echo)
  </read_first>
  <action>
    Register `@team_group.command("run")` directly below team_check_cmd (same group, same indent) — team_group is already in AGENT_COMMANDS (cli.py:3877), no registration change. Options: `@click.argument("goal")`, `@click.option("--cwd", "cwd_str", default=".")`, `@click.option("--max-iterations", default=50, type=int)`. The command body is SYNC; do the async work via `asyncio.run(...)` (consensus_cmd pattern), NOT _run_turn_cancellable.

    First action: `cwd = Path(cwd_str).resolve()`. Resolve team config: if `(cwd/".voss"/"team.voss").is_file()` → read, parse (append "\n" if missing), find the TeamDecl, compile_team(team_decl) → (config, registry); else → _default_team_config(). (Take the FALLBACK branch where team_check_cmd would _fail.)

    Define an inner `async def _run() -> RunFinal` (or a module-level `_team_run_async`) that builds the stack in this exact order (V7-RESEARCH Pattern 3): SessionTreeNode.create_root(cwd=cwd, limit=500_000) → SessionTreeManager(root, reserve=0, cwd=cwd) → reviewer = DeterministicReviewerStub(conf=0.99, verdict="pass") → Board.from_team_config(config, recorder=manager, reviewer=reviewer, cwd=cwd, per_card_budget=100_000) → **await board.spawn_card(risk_tier="med")** (MANDATORY pre-spawn so RunFinal.total_cards>=1 — Pitfall 1) → base_gate = PermissionGate(mode="auto", auto_yes=True) → handle = EMBoardHandle(board=board, registry=registry, team_config=config, manager=manager, base_gate=base_gate, cwd=cwd) → roster_descs = {spec.id: spec.description for spec in registry.entries()} → em_agent = DeterministicEMStub(scripted=[EMPlanResponse(ops=[CreateTicketOp(original_idea=goal, worker_role=<a roster role, e.g. "backend">)]), EMPlanResponse(ops=[NoopOp(reason="waiting")])]) → return await em_loop(idea=goal, em_handle=handle, em_agent=em_agent, roster_descriptions=roster_descs, max_iterations=max_iterations).

    Drive it: `rf = asyncio.run(_run())`. Do NOT use reviewer_a/reviewer_b kwargs (V6-03 unexecuted — TypeError; Pitfall 2). Do NOT access rf.evidence_refs/diff_summary/residual (not on RunFinal; Pitfall 3).

    Persist initial: `_persist_run_final(rf, cwd)`. Print summary via click.echo — a readable RunFinal summary (idea, total_cards, done/blocked/killed/rescope counts, em_iterations); table-vs-text is Claude's discretion (CONTEXT). Then `decision = click.prompt("Sign off on this run", type=click.Choice(["approve", "reject"]))` (NOT click.confirm — testable via CliRunner input=). Re-persist with the decision: `_persist_run_final(rf, cwd, decision=decision)` (overwrites same path adding sign_off; Pitfall 6). reject is RECORD-ONLY: write the decision, touch nothing else (no revert). `sys.exit(0)` on success; error paths use click.echo(str(exc), err=True) + sys.exit(2) per cli.py conventions.

    No fenced code in this action.
  </action>
  <verify>
    <automated>.venv/bin/python -c "src=open('voss/harness/cli.py').read(); assert 'team_group.command(\"run\")' in src, 'run subcommand missing'; assert 'spawn_card' in src, 'pre-spawn missing'; assert 'asyncio.run' in src, 'async-drive missing'; assert 'click.Choice' in src and 'approve' in src and 'reject' in src, 'signoff prompt missing'; print('cli surface present')" && .venv/bin/python -m pytest tests/harness/test_team_run_cli.py -q 2>&1 | tail -8 && .venv/bin/python -m pytest tests/harness/em/ -x -q 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - cli.py defines `@team_group.command("run")` (team_run_cmd) on the existing team group — NOT a new top-level group.
    - The command pre-spawns a board card via `await board.spawn_card(risk_tier="med")` BEFORE em_loop, and drives em_loop via `asyncio.run(...)`.
    - Uses the SINGLE `reviewer=` slot (no reviewer_a/reviewer_b); never accesses evidence_refs/diff_summary/residual.
    - Sign-off uses `click.prompt(..., type=click.Choice(["approve","reject"]))`; the chosen decision is recorded into run-final.json's `sign_off` key; reject path writes only the sidecar (no other disk change).
    - All 10 V7-01 tests GREEN: `.venv/bin/python -m pytest tests/harness/test_team_run_cli.py -q` exits 0 with 10 passed.
    - `tests/harness/em/` remains 79/79 green; `tests/harness/board/` is NOT in any V7 command (13 pre-existing RED from V6 scaffolds are out of scope).
  </acceptance_criteria>
  <done>`voss team run "<goal>"` composes the stack, pre-spawns ≥1 card, runs em_loop to terminal on the stub, persists RunFinal, prints the summary, prompts approve/reject, records the decision (reject record-only); V7-01 suite 10/10 GREEN; em suite 79/79 green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| human → `voss team run` CLI | User-supplied `goal` string and `--cwd` cross into the harness |
| EM agent → EMBoardHandle (cage) | The EM may only act through the cage facade; mutation methods are absent by design |
| process → disk (`.voss/sessions/<root_id>/`) | RunFinal sidecar write; path must be derived, not user-controlled |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V7-01 | Elevation of Privilege | EM mutating ceiling/p/budget via handle | mitigate | Cage by surface area: EMBoardHandle omits set_ceiling/set_p/set_budget/extend_budget. V7 injects the existing handle and adds NO mutation methods. Re-verified by V7-03 (TestCageInvariant1Introspection). |
| T-V7-02 | Spoofing / EoP | EM dispatching to an undeclared role | mitigate | dispatch_card checks role_id ∈ team_config.roster_ids → raises EMCageViolation. roster_ids built from DEFAULT_ROSTER (fallback) or compile_team. Re-verified by V7-03 (TestCageInvariant2NonRoster). |
| T-V7-03 | Tampering | EM kill/rescope of a Done card | mitigate | kill_card/rescope_card guard column == "Done". Lineage recorded. Re-verified by V7-03 (em dispatch/lineage tests). |
| T-V7-04 | Repudiation | Sign-off bypass (no human decision recorded) | mitigate | click.prompt(Choice) is not optional in the command flow; both approve and reject paths record into run-final.json. CliRunner tests cover both (V7-01 TestSignOff). |
| T-V7-05 | Tampering | run-final.json path traversal via crafted root_id | mitigate | Path is `.voss/sessions/<rf.root_id>/run-final.json` with root_id sourced ONLY from the SessionTreeNode UUID (rf.root_id), NEVER user input. `--cwd` is resolved; goal is text only. |
| T-V7-06 | Information Disclosure | world-readable run-final.json | mitigate | persist_path.chmod(0o600), mirroring _write_node_file. |
| T-V7-07 | Tampering | goal-string injection into em_loop idea= | accept | idea is passed as text to the stub/LLM; no shell execution, no path use. Low risk on the stub path; LLM-side prompt-injection handling is out of V7 scope. |
| T-V7-SC | Tampering | npm/pip/cargo installs | accept | V7 adds NO new third-party dependencies (V7-RESEARCH §Package Legitimacy Audit empty). No install tasks → no slopcheck checkpoint needed. |

High-severity dispositions (T-V7-01..06) are all `mitigate` with concrete, testable controls; none are deferred or accepted at high risk, so no blocking human checkpoint is required.
</threat_model>

<verification>
- `voss team run "<goal>"` exits 0 on stub, produces ≥1 card + RunFinal, persists the sidecar, prompts + records sign-off.
- Full V7 gate: `.venv/bin/python -m pytest tests/harness/em/ tests/harness/test_team_run_cli.py tests/harness/test_team_check_cli.py -q` (do NOT add tests/harness/board/).
- No new deps; cli.py is the only modified file.
</verification>

<success_criteria>
All 10 V7-01 tests GREEN; em suite 79/79; the run-final.json sidecar carries the 10 RunFinal fields + sign_off and is re-readable; cage untouched (verified in V7-03).
</success_criteria>

<output>
Create `.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-02-SUMMARY.md` when done.
</output>
