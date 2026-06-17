---
phase: V25-server-native-swarm-runtime
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - crates/voss-app-core/src/agent_registry.rs
autonomous: true
requirements: [VSWARM-09]
must_haves:
  truths:
    - "agent_sessions gains swarm_id/role/owned_files columns via an idempotent migration that survives re-open"
    - "register_agent accepts the swarm fields and list_agents_by_swarm returns a swarm's agents carrying swarm_id/role/owned_files"
    - "AgentEntry serializes the new fields camelCase (swarmId/role/ownedFiles) for IPC parity"
  artifacts:
    - path: "crates/voss-app-core/src/agent_registry.rs"
      provides: "swarm columns + list_agents_by_swarm query + AgentEntry swarm fields"
      contains: "swarm_id"
  key_links:
    - from: "create_schema"
      to: "agent_sessions ALTER TABLE ADD COLUMN"
      via: "PRAGMA table_info guard (idempotent)"
      pattern: "swarm_id"
---

<objective>
Add the `swarm_id`/`role`/`owned_files` columns to the `agent_sessions` SQLite table in `agent_registry.rs`, extend `AgentEntry` + `register_agent` to carry them, and add a `list_agents_by_swarm` query. This is the voss-app pane-binding surface for VSWARM-09 — verified via `cargo test`. It is file-disjoint from all Python plans, so it runs in Wave 1 in parallel with everything else.

Purpose: The headless Python acceptance for VSWARM-09 is the SwarmStore session index (V25-01). This plan delivers the Rust SQLite column-add so the eventual voss-app spawn (V24 scope) can register swarm agents against panes. Per RESEARCH Open-Q2 and the VALIDATION manual-only row, the Rust migration is verified separately in `cargo test`.

Output: migrated schema + extended AgentEntry/register_agent + list_agents_by_swarm in `crates/voss-app-core/src/agent_registry.rs`.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V25-server-native-swarm-runtime/V25-SPEC.md
@.planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md

<interfaces>
<!-- Verified against source: crates/voss-app-core/src/agent_registry.rs -->

AgentEntry (agent_registry.rs:27-37): #[serde(rename_all="camelCase")] struct with pane_id,
session_id, cli_binary, cli_args, cwd, status, last_seen. Frontend reads paneId/cliBinary/lastSeen.
create_schema (agent_registry.rs:90-108): execute_batch CREATE TABLE IF NOT EXISTS agent_sessions(...).
register_agent (agent_registry.rs:111+): INSERT OR REPLACE into the 7 existing columns.
AgentRegistryError (agent_registry.rs:11-19): OpenFailed/QueryFailed/WriteFailed typed errors.
Existing cargo tests live in this crate (TEST_GLOBAL_REGISTRY_PATH thread-local at :56-63 indicates a test harness).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Migrate schema + extend AgentEntry/register_agent</name>
  <read_first>
    - crates/voss-app-core/src/agent_registry.rs (full file: AgentEntry :27-37, create_schema :90-108, register_agent :111+, error enum :11-19, test thread-local :56-63)
    - .planning/phases/V25-server-native-swarm-runtime/V25-RESEARCH.md (VSWARM-09 migration SQL + PRAGMA table_info guard; Assumption A6 ALTER TABLE ADD COLUMN DEFAULT NULL)
  </read_first>
  <action>
    In `create_schema` (agent_registry.rs:90-108), after the CREATE TABLE, add an idempotent migration that adds three nullable columns when absent: query `PRAGMA table_info(agent_sessions)`, and for each of `swarm_id TEXT`, `role TEXT`, `owned_files TEXT` not present, run `ALTER TABLE agent_sessions ADD COLUMN <col> TEXT DEFAULT NULL` (RESEARCH VSWARM-09; ALTER ADD COLUMN errors if the column already exists, hence the PRAGMA guard — A6). Extend `AgentEntry` (:27-37) with `pub swarm_id: Option<String>`, `pub role: Option<String>`, `pub owned_files: Option<String>` (JSON array string) — camelCase rename yields `swarmId`/`role`/`ownedFiles` for IPC. Extend `register_agent` (:111+) with optional swarm params and write them in the INSERT OR REPLACE; keep the existing call sites working by accepting `Option`/defaulting to NULL. Map any new rusqlite error through the existing `AgentRegistryError` variants.
  </action>
  <verify>
    <automated>cargo test -p voss-app-core agent_registry 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    Schema migration is idempotent across re-open (no duplicate-column error); AgentEntry carries swarm_id/role/owned_files; register_agent persists them. `cargo test -p voss-app-core agent_registry` PASSES (VSWARM-09 Rust surface, VALIDATION manual-only row).
  </acceptance_criteria>
  <done>Columns added idempotently; AgentEntry/register_agent extended; existing cargo tests stay green.</done>
</task>

<task type="auto">
  <name>Task 2: Add list_agents_by_swarm query + test</name>
  <read_first>
    - crates/voss-app-core/src/agent_registry.rs (the file as modified in Task 1; existing query/list functions for the row-mapping pattern)
  </read_first>
  <action>
    Add `pub fn list_agents_by_swarm(conn: &Connection, swarm_id: &str) -> Result<Vec<AgentEntry>, AgentRegistryError>` selecting all `agent_sessions` rows WHERE swarm_id = ?1, mapping each row to a full `AgentEntry` (including the new fields) using the existing row-mapping pattern. Add a cargo test that opens an in-memory/temp registry, `register_agent` with swarm_id="s1"/role="builder"/owned_files=`["a.py"]`, and asserts `list_agents_by_swarm(conn, "s1")` returns the row with the correct swarm_id/role/owned_files (RESEARCH VSWARM-09 acceptance: registry listable by swarm_id).
  </action>
  <verify>
    <automated>cargo test -p voss-app-core agent_registry 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    `list_agents_by_swarm` returns a swarm's agents carrying correct swarm_id/role/owned_files; the new cargo test PASSES (VSWARM-09 listability).
  </acceptance_criteria>
  <done>list_agents_by_swarm exists and its cargo test passes.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| SQLite migration → existing DB | a re-run migration must not corrupt or error on already-migrated DBs |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V25-03-01 | Denial of service | non-idempotent ALTER bricks registry open | mitigate | PRAGMA table_info guard before each ADD COLUMN; columns are nullable DEFAULT NULL (no data copy) |
| T-V25-03-02 | Tampering | owned_files JSON string malformed on read | accept | Stored as opaque TEXT; TS parses JSON defensively (existing camelCase IPC discipline) |
| T-V25-03-SC | Tampering | cargo crate installs | accept | No new Rust deps (RESEARCH audit empty); rusqlite/serde already in Cargo.toml |
</threat_model>

<verification>
- `cargo test -p voss-app-core agent_registry` green
- `cargo build -p voss-app-core` succeeds
</verification>

<success_criteria>
- agent_sessions has swarm_id/role/owned_files (idempotent migration) (VSWARM-09 Rust)
- list_agents_by_swarm returns a swarm's agents listable by swarm_id (VSWARM-09)
- AgentEntry serializes the new fields camelCase
</success_criteria>

<output>
Create `.planning/phases/V25-server-native-swarm-runtime/V25-03-SUMMARY.md` when done
</output>
