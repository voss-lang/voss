---
phase: V20-edict-residue-hardening
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/subagents.py
  - voss/harness/em/handle.py
  - tests/harness/test_mission_brief.py
autonomous: true
requirements: [VEDR-03]
must_haves:
  truths:
    - "A worker dispatched while sibling cards are in flight receives a prompt containing the outcome line, sibling roster (role + task one-liner), and claimed-scope file hints"
    - "agent_task without a brief is byte-identical to today's output (role_prompt + task) — zero churn for existing callers and prompt-sentinel tests"
    - "Brief is read-only over existing sources: claims DB (active_claims) + EM ticket table; no new persistence"
  artifacts:
    - path: "voss/harness/subagents.py"
      provides: "MissionBrief dataclass + agent_task(spec, task, brief=None) appending Outcome/Siblings/Claimed-scope sections"
      contains: "MissionBrief"
    - path: "voss/harness/em/handle.py"
      provides: "dispatch_card assembles MissionBrief from tickets + active_claims"
      contains: "MissionBrief"
    - path: "tests/harness/test_mission_brief.py"
      provides: "RED-first: prompt contains sibling list + file hints; no-brief unchanged"
      contains: "test_dispatch_prompt_contains_siblings"
  key_links:
    - from: "voss/harness/em/handle.py"
      to: "voss.harness.claims.active_claims"
      via: "open_claims_db(cwd) read at dispatch time, claims grouped by agent_id -> scope patterns"
      pattern: "active_claims"
---

<objective>
Stop dispatching blind workers. agent_task (subagents.py:172) injects only role_prompt + task,
so a worker has no idea what outcome the card serves, who its siblings are, or which file
scopes are already owned — even though claims.py (active_claims:204) and the EM ticket table
(handle.py) already hold exactly that. Result: scope collisions the claims system then has to
referee after the fact, instead of workers steering around each other up front.

Inject a mission brief at dispatch: outcome, sibling roster, claimed-scope file hints.
</objective>

<context>
- agent_task: voss/harness/subagents.py:172-173. Callers: grep `agent_task(` before changing
  the signature — keyword-only `brief=None` keeps them all valid.
- dispatch_card: voss/harness/em/handle.py:186-240 — has self._tickets (card_id → Ticket with
  original_idea/acceptance/worker_role), self._team_config.roster_ids, cwd for claims DB.
- Claims: voss/harness/claims.py open_claims_db:149, active_claims:204 (returns rows incl.
  agent_id, patterns, expiry — confirm exact tuple shape at implementation time).
- Watch: prompt-sentinel/parity tests may pin worker prompt text — run
  tests/harness -k "prompt or subagent" early to find pins; update sentinels only with
  evidence (per stale-sentinel discipline).
</context>

<tasks>

## Task 1 — RED tests (commit 1: `test(harness): RED mission brief injection`)
tests/harness/test_mission_brief.py:
1. `test_agent_task_no_brief_unchanged` — agent_task(spec, task) == today's exact string.
2. `test_agent_task_with_brief_sections` — brief with outcome + 2 siblings + 2 scope hints →
   prompt contains "## Outcome", each sibling role/task line, each file pattern.
3. `test_dispatch_prompt_contains_siblings` — EMBoardHandle with 2 in-flight tickets +
   staked claims in a tmp claims DB → dispatch_card's assembled task prompt contains sibling
   roster + claimed patterns (drive via the same fixture style as existing handle tests).
4. `test_dispatch_no_claims_no_siblings` — single card, empty claims DB → brief degrades to
   outcome-only; no empty "Siblings:" header noise.

## Task 2 — MissionBrief + renderer (commit 2: `feat(harness): mission brief in agent_task`)
- subagents.py: frozen dataclass `MissionBrief(outcome: str, siblings: tuple[SiblingLine,...],
  claimed_scopes: tuple[ScopeLine,...])` (SiblingLine = role_id, task_summary; ScopeLine =
  owner_agent, patterns). Render as compact sections appended after Task:
  `## Outcome`, `## Siblings (do not duplicate their work)`, `## Claimed scopes (do not touch)`.
- Keep rendering deterministic (sorted) — prompts feed hashing/parity checks elsewhere.

## Task 3 — assemble at dispatch (commit 3: `feat(em): dispatch_card builds mission brief`)
- handle.py dispatch_card: build brief =
  - outcome: ticket.original_idea (+ acceptance one-liner if short),
  - siblings: other tickets whose cards are in non-terminal columns (truncate task to ~120 chars),
  - claimed_scopes: active_claims(open_claims_db(cwd)) grouped by agent.
- Claims read is best-effort: DB missing/locked → empty scopes, never block dispatch.
- Thread brief into the agent_task call site (wherever dispatch hands task text to the
  subagent runner — locate via rr/dispatch flow, keep change surgical).

## Task 4 — GREEN + suite
`.venv/bin/python -m pytest tests/harness/test_mission_brief.py tests/harness/em tests/harness -k "subagent or dispatch" -q` green; full harness suite spot-run.
</tasks>

<verification>
- Spawned worker prompt contains sibling list + file hints (headline verify line).
- No-brief path byte-identical; claims absence degrades silently.
</verification>
