# A13 — Agent Swarm Orchestration

## What This Phase Delivers

A file-mediated multi-agent swarm system where the user can launch a coordinated team of agents (Claude, Codex, OpenCode, etc.) that decompose a task, work in parallel, and synthesize results — all visible and controllable from the sidebar.

## Why Now

A12 built the ADE sidebar with agent detection, launch modal, and monitoring. But agents currently work in isolation — each pane is independent. The swarm system makes Voss an actual orchestration platform where agents collaborate on a shared goal.

## Core Concept: File-Mediated Swarm

Third-party CLIs (Claude Code, Codex, OpenCode) can't share memory or use custom IPC protocols. But they all understand files. The swarm coordinator:

1. Decomposes user's task into subtasks (single Opus call)
2. Writes task files to `.voss/swarm/tasks/`
3. Spawns agents with task as CLI positional arg
4. Monitors completion via fs.watch on result files
5. Synthesizes results and presents to user

## Design Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-01 | File-mediated communication | Works with any CLI agent without modification |
| D-02 | Single coordinator pattern (not peer-to-peer) | Simpler, debuggable, auditable — coordinator owns all routing |
| D-03 | Coordinator is a single Opus LLM call (not a full agent) | Deep analysis of codebase + goal; avoids recursion |
| D-04 | `.voss/swarm/` directory convention | Consistent location; gitignored; scoped to workspace |
| D-05 | Task files are markdown (not JSON) | Agents understand markdown better; human-readable |
| D-06 | Result files are markdown with structured frontmatter | Machine-parseable header + human-readable body |
| D-07 | Fan-out/fan-in (not pipeline) | Most flexible; pipeline is a special case of fan-out with dependencies |
| D-08 | Swarm visible in sidebar AGENTS section | Swarm agents appear as regular agents with a "swarm" group indicator |
| D-09 | User can stop individual swarm agents or entire swarm | Granular control; sidebar context menu adds "Stop swarm" option |
| D-10 | Swarm layout auto-applies "swarm" grid preset | N panes arranged per existing swarm layout preset |
| D-11 | Coordinator prompt uses project CLAUDE.md / .voss context | Decomposition is project-aware |
| D-12 | Max 6 concurrent agents per swarm | Resource safety; user can override |
| D-13 | Swarm state persisted in `.voss/swarm/manifest.json` | Survives app restart; resumable |
| D-14 | Completion detection: fs.watch on `.voss/swarm/results/` (primary) | File creation is reliable, no PTY parsing needed |
| D-15 | Swarm launch via sidebar button + launch modal Swarm tab | Sidebar has dedicated swarm button; modal has 7th "Swarm" tab for goal entry |
| D-16 | Coordinator picks agents (user gives goal only) | Coordinator decides best CLI per subtask (Claude for planning, Codex for implementation, etc.) |
| D-17 | Task decomposition uses single Opus call with codebase context | Reads repo structure + README + goal, outputs subtask array with file scopes |
| D-18 | Subtasks include goal + file scope boundaries | "Refactor src/auth/. Don't touch src/auth/tests/." — clear boundaries, soft enforcement via instructions |
| D-19 | Agent receives task via CLI positional arg | `claude 'Read .voss/swarm/tasks/agent-1.task.md and follow instructions.'` — universal, works with all CLIs |
| D-20 | Scope boundaries are instruction-only (soft) | Task file says which files to modify/avoid. Agent honor system. Accept occasional overlap. |
| D-21 | Completion: fs.watch on result files (primary), PTY exit (fallback) | Primary: agent writes `.voss/swarm/results/agent-N.result.md`. Fallback: PTY exit event. |
| D-22 | Failure: timeout + notify user | If no result after N minutes, mark stuck in sidebar. User decides: retry, reassign, or skip. No auto-retry. |

## File Protocol

### Directory Structure
```
.voss/swarm/
├── manifest.json           # Swarm metadata: id, goal, status, agent list
├── tasks/
│   ├── agent-1.task.md     # Subtask assignment with file scope
│   └── agent-2.task.md
├── results/
│   ├── agent-1.result.md   # Agent output with structured frontmatter
│   └── agent-2.result.md
└── shared/
    └── context.md          # Shared project context (CLAUDE.md excerpt)
```

### Task File Format
```markdown
---
swarm: swarm-{timestamp}
agent: agent-{N}
cli: claude
---

## Your Task
{goal description}

## File Scope
- Modify: {list of paths/patterns}
- Do NOT modify: {exclusion paths}

## Shared Context
Read `.voss/swarm/shared/context.md` for project context.

## When Done
Write results to `.voss/swarm/results/agent-{N}.result.md`
```

### Result File Format
```markdown
---
agent: agent-{N}
status: complete | error
files_modified: [list]
---

## Summary
{what was done}
```

## Coordinator Flow

1. User provides goal text via sidebar button or Swarm tab in launch modal
2. Coordinator (single Opus call) receives: goal + repo file tree + CLAUDE.md + shared context
3. Coordinator outputs: JSON array of subtasks with `{ id, cli, goal, fileScope, excludeScope }`
4. SwarmController writes manifest.json + task files + shared/context.md
5. SwarmController spawns N agent panes via existing `spawn_agent` with task as positional CLI arg
6. SwarmController starts fs.watch on `.voss/swarm/results/`
7. As result files appear, sidebar updates per-agent status
8. When all agents complete (or timeout), coordinator synthesizes results
9. User sees summary in sidebar ACTIVITY + toast notification

## Sidebar Integration

- AGENTS section: swarm agents appear as cards with swarm group badge
- Swarm group header shows: "Swarm: {goal}" with progress (2/4 complete)
- Context menu adds: "Stop swarm" (kills all agents in swarm)
- ACTIVITY section: shows per-agent completion events
- USAGE section: shows per-agent token usage (from budget_update events)

## Dependencies

- A12 (ADE sidebar + agent detection + launch modal) — **complete**
- A4 (Layout presets including "swarm") — **complete**
- Existing `spawn_agent` Tauri command — **complete**

## Out of Scope (A13)

- Agent-to-agent direct messaging (peer-to-peer) — coordinator handles all routing
- .voss language `team{}` execution — that's O2
- Recursive sub-swarms (agent spawns its own swarm) — defer
- Cross-workspace swarms — single workspace only
- Budget enforcement across swarm agents — defer to O1
- Auto-retry on failure — user decides on stuck agents

## Canonical References

- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md` — requirements SWM-01..12
- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md` — this file
- `apps/voss-app/src/pane/pty-ipc.ts` — PtyTransport, spawn_agent interface
- `apps/voss-app/src/components/sidebar/AgentSidebar.tsx` — sidebar component to extend
- `apps/voss-app/src/components/modal/AgentLaunchModal.tsx` — modal to add Swarm tab
- `apps/voss-app/src-tauri/src/lib.rs` — Tauri command registration
- `apps/voss-app/src/grid/layoutPresets.ts` — swarm layout preset
