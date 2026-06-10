---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 02
type: execute
wave: 2
depends_on: [V17-01]
files_modified:
  - voss/harness/claims.py
autonomous: true
requirements: [VBUS-01, VBUS-02]
# D-02 deviation: storage at .voss-cache/claims.sqlite (NOT .voss/) — locked, see CONTEXT.md D-02.

must_haves:
  truths:
    - "Glob overlap is detected statically with no filesystem reads, matching all SPEC cases"
    - "URI overlap is segment-aware: exact + path-prefix at / boundaries only"
    - "A claim is atomically staked or atomically rejected — concurrent overlapping stakes yield exactly one winner"
    - "Claims persist in .voss-cache/claims.sqlite with no server running and always carry expires_at"
    - "Expired claims never block check/stake and are excluded from list (unless --all)"
    - "Same-agent re-stake of overlapping patterns is idempotent refresh, never a conflict"
  artifacts:
    - path: "voss/harness/claims.py"
      provides: "Overlap engine + SQLite storage layer + atomic stake (no CLI yet)"
      contains: "BEGIN IMMEDIATE"
      min_lines: 120
  key_links:
    - from: "voss/harness/claims.py atomic_stake"
      to: "sqlite3 BEGIN IMMEDIATE on .voss-cache/claims.sqlite"
      via: "explicit conn.execute('BEGIN IMMEDIATE')"
      pattern: "BEGIN IMMEDIATE"
---

<objective>
Build the claims engine: the pure overlap algorithms (glob + URI), the SQLite storage layer at `.voss-cache/claims.sqlite` (WAL + busy_timeout), and the atomic check-and-stake transaction (`BEGIN IMMEDIATE`) that guarantees exactly-one-winner under concurrency. This plan delivers the storage + computation core only — the click CLI verbs land in V17-03 against this engine (interface-first ordering).

Purpose: VBUS-02 serverless concurrent-safe storage + the overlap semantics VBUS-01 depends on.
Output: `voss/harness/claims.py` with overlap helpers, db helpers, and `atomic_stake`.
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
<!-- Engine API this plan must export, consumed by V17-03 CLI verbs -->
voss/harness/claims.py exports:
  - glob_patterns_overlap(p1: str, p2: str) -> bool          # conservative static, no fs reads (D-05)
  - uri_overlap(u1: str, u2: str) -> bool                    # segment-aware exact+prefix (D-06)
  - patterns_overlap(set_a: list[str], set_b: list[str]) -> bool   # any-vs-any across glob+URI
  - open_claims_db(cwd: Path) -> sqlite3.Connection         # .voss-cache/claims.sqlite, WAL, busy_timeout=5000
  - atomic_stake(conn, agent_id, claim_id, patterns, ttl) -> tuple[bool, list[ConflictRow]]
  - active_claims(conn, exclude_agent: str | None, now: float) -> list[row]
  - release_claims(conn, agent_id, claim_id: str | None) -> int
  - extend_claim(conn, agent_id, claim_id, ttl) -> bool
  - canonicalize_pattern(pattern: str, cwd: Path) -> str     # reject .. traversal per sandbox.rs precedent
  - DEFAULT_TTL_SECONDS = 1800
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Overlap engine (glob + URI + canonicalization)</name>
  <files>voss/harness/claims.py</files>
  <behavior>
    - glob_patterns_overlap("src/api/**","src/api/handlers.py") -> True
    - glob_patterns_overlap("src/api/**","src/other/**") -> False
    - glob_patterns_overlap("src/api/**","src/api/**") -> True (idempotent same-base)
    - uri_overlap("card://123","card://123") -> True
    - uri_overlap("card://123","card://124") -> False
    - uri_overlap("card://12","card://123") -> False (segment boundary, D-06)
    - uri_overlap("bead://p/x","bead://p") -> True (prefix at / boundary)
    - patterns_overlap(["src/api/**","card://1"], ["src/api/x.py"]) -> True
    - canonicalize_pattern("../../etc/passwd", cwd) raises/rejects traversal
  </behavior>
  <read_first>
    - voss/harness/claims.py (current state — created here; if absent this is the first write)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md (Pattern 3 glob algorithm, Pattern 4 URI algorithm, canonicalization-from-CWD note)
    - crates/voss-app-core/src/sandbox.rs (lines ~31-61 validate_scope — port the traversal-rejection logic to Python; do NOT modify this Rust file)
    - tests/harness/claims/test_overlap.py (the RED tests this task must turn GREEN)
  </read_first>
  <action>Create `voss/harness/claims.py` with stdlib imports (json, os, sqlite3, sys, time, pathlib, fnmatch, click). Implement `glob_patterns_overlap` using the base-dir + glob-tail split from RESEARCH Pattern 3: extract_base_and_tail splits at the first path segment containing any of `*?[{`; bases are related if one is relative_to the other; if either tail is empty or in {`**`,`*`,`**/*`} treat as match-all; else fnmatch the tails both directions. Implement `uri_overlap` per RESEARCH Pattern 4: rstrip trailing `/`, equal -> True, else `u2.startswith(u1 + "/") or u1.startswith(u2 + "/")` — a URI is anything containing `://`. Implement `patterns_overlap(set_a, set_b)` dispatching each pair to uri_overlap when both look like URIs, glob_patterns_overlap otherwise; return True on any overlapping pair. Implement `canonicalize_pattern(pattern, cwd)`: for non-URI patterns, if relative join with cwd then `os.path.normpath`, reject any pattern whose normalized form escapes cwd or contains a `..` component (mirror sandbox.rs validate_scope precedent — raise ValueError); URIs pass through unchanged. Set `DEFAULT_TTL_SECONDS = 1800`. No fenced code in commit messages; no filesystem reads inside overlap functions (D-05).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/claims/test_overlap.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - test_overlap.py passes (all six SPEC overlap cases GREEN)
    - `grep -v '^#' voss/harness/claims.py | grep -c 'def glob_patterns_overlap'` returns 1
    - glob/URI functions perform no os.stat/os.listdir/open calls (no filesystem reads) — verify by source inspection in summary
    - canonicalize_pattern raises on a `..` traversal input
  </acceptance_criteria>
  <done>Overlap engine GREEN against test_overlap.py; traversal rejected; zero filesystem reads in overlap path.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: SQLite storage + atomic stake (exactly-one-winner)</name>
  <files>voss/harness/claims.py</files>
  <behavior>
    - open_claims_db(cwd) creates <cwd>/.voss-cache/claims.sqlite with WAL + busy_timeout, schema-if-missing
    - atomic_stake on a non-conflicting pattern returns (True, [])
    - atomic_stake on a pattern overlapping ANOTHER agent's active claim returns (False, [conflict_row])
    - atomic_stake on a pattern overlapping the SAME agent's claim returns (True, []) — idempotent refresh (D-04)
    - N concurrent processes staking the same overlapping pattern: exactly one returns (True, _)
    - active_claims excludes rows with expires_at <= now
    - release_claims(conn, agent, None) deletes all that agent's claims; release_claims(conn, agent, id) deletes one
    - extend_claim refreshes expires_at for the agent's claim set
  </behavior>
  <read_first>
    - voss/harness/claims.py (overlap engine from Task 1 — build storage on top)
    - voss/harness/code/index.py (lines ~107-148 — _get_db_path + _ensure_schema WAL pattern to mirror)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md (Pattern 1 atomic_stake, Complete SQLite Schema, Pitfall 1 in-memory isolation, Pitfall 2 BEGIN DEFERRED, Pitfall 6 prune)
    - tests/harness/claims/test_claims_concurrent.py + test_claims_ttl.py (RED tests to turn GREEN)
  </read_first>
  <action>Add to `voss/harness/claims.py`: `_get_db_path(cwd) -> Path` returning `cwd/".voss-cache"/"claims.sqlite"` (D-02 — note the deviation from SPEC's `.voss/`); `open_claims_db(cwd)` that makedirs the parent, connects with `timeout=5.0`, sets `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, and creates table `claims(id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, patterns TEXT NOT NULL, expires_at REAL NOT NULL)` plus indexes on expires_at and agent_id (RESEARCH Complete SQLite Schema). Implement `atomic_stake(conn, agent_id, claim_id, patterns, ttl)`: compute `now=time.time()`, `expires_at=now+ttl`; `conn.execute("BEGIN IMMEDIATE")` (NEVER `with conn:` — Pitfall 2); SELECT id,agent_id,patterns from claims WHERE agent_id != ? AND expires_at > ?; decode each patterns JSON and test `patterns_overlap` against the requested patterns; if any conflict -> rollback, return (False, conflict_rows); else `INSERT OR REPLACE` the claim (patterns stored as `json.dumps`), commit, return (True, []). Same-agent overlap is excluded by the `agent_id != ?` filter so re-staking is idempotent (D-04). Implement `active_claims`, `release_claims`, `extend_claim` with `expires_at > now` filtering everywhere (Pitfall 6). All queries must filter expired rows. Use a file path always — never `:memory:` (Pitfall 1).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/claims/test_claims_concurrent.py tests/harness/claims/test_claims_ttl.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - test_claims_concurrent.py passes: concurrent overlapping stakes grant exactly one winner
    - test_claims_ttl.py passes: --ttl 1 claim stops blocking after expiry; default TTL applied when absent
    - `grep -v '^#' voss/harness/claims.py | grep -c 'BEGIN IMMEDIATE'` returns at least 1
    - `grep -c ':memory:' voss/harness/claims.py` returns 0
    - active_claims / release_claims / extend_claim each include `expires_at` in their WHERE clause (source assertion in summary)
  </acceptance_criteria>
  <done>Storage + atomic stake GREEN; concurrency and TTL tests pass; BEGIN IMMEDIATE used; no in-memory db.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI invoker cwd -> claims.sqlite path | Untrusted cwd / pattern strings used to build storage path + claim keys |
| concurrent CLI processes -> shared sqlite file | Multiple OS processes contend for the same WAL db |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V17-02 | Tampering | claim pattern traversal (`../../etc`) | mitigate | canonicalize_pattern rejects `..` components + cwd-escape per sandbox.rs validate_scope precedent |
| T-V17-03 | Tampering | claims.sqlite path | mitigate | db path resolved from `Path(cwd).resolve()/.voss-cache/claims.sqlite`; no user-supplied absolute path accepted |
| T-V17-04 | Elevation | concurrent double-grant | mitigate | BEGIN IMMEDIATE write-lock at txn start serializes stakes — exactly one winner (RESEARCH live-tested) |
| T-V17-05 | Spoofing | agent_id forgery | accept | Advisory system by design (SEED-001); VOSS_AGENT_ID spoofing accepted, not over-engineered |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/claims/test_overlap.py tests/harness/claims/test_claims_concurrent.py tests/harness/claims/test_claims_ttl.py -x -q` all GREEN.
- `grep -c ':memory:' voss/harness/claims.py` == 0.
</verification>

<success_criteria>
Overlap engine matches all SPEC cases; serverless SQLite storage at `.voss-cache/claims.sqlite` with mandatory TTL; atomic stake grants exactly one winner under concurrency; same-agent re-stake is idempotent.
</success_criteria>

<output>
Create `.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-02-SUMMARY.md` when done.
</output>
