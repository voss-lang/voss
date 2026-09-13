# A13 Spec — Agent Swarm Orchestration

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| SWM-01 | User can launch a swarm from sidebar with a natural language goal | Must |
| SWM-02 | Coordinator decomposes goal into 2-6 subtasks automatically | Must |
| SWM-03 | Each subtask spawns a dedicated agent pane with task context | Must |
| SWM-04 | Agents read task assignments from `.voss/swarm/tasks/` files | Must |
| SWM-05 | Agents write results to `.voss/swarm/results/` files | Must |
| SWM-06 | Host detects agent completion via result file creation + PTY idle | Must |
| SWM-07 | Coordinator synthesizes all results into a summary for the user | Must |
| SWM-08 | Sidebar shows swarm status (pending/running/complete per agent) | Must |
| SWM-09 | User can stop individual agents or entire swarm from sidebar | Must |
| SWM-10 | Swarm layout preset auto-applied when swarm launches | Should |
| SWM-11 | Swarm state persisted in `.voss/swarm/manifest.json` | Should |
| SWM-12 | Swarm resumable after app restart | Could |

## Architecture

```
User: "Refactor the auth module and add tests"
         │
         ▼
┌─────────────────┐
│   Coordinator    │  (lightweight LLM call — decomposes task)
│   (Rust/TS)     │
└────────┬────────┘
         │ writes task files
         ▼
┌──────────────────────────────────┐
│  .voss/swarm/                     │
│  ├── manifest.json                │
│  ├── tasks/                       │
│  │   ├── agent-1.task.md          │
│  │   └── agent-2.task.md          │
│  ├── results/                     │
│  │   ├── agent-1.result.md        │
│  │   └── agent-2.result.md        │
│  └── shared/                      │
│      └── context.md               │
└──────────────────────────────────┘
         │ spawns agents with task context
         ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Pane 1   │  │ Pane 2   │  │ Pane 3   │
│ Claude   │  │ Codex    │  │ Claude   │
│ refactor │  │ tests    │  │ review   │
└──────────┘  └──────────┘  └──────────┘
         │ writes result files when done
         ▼
┌─────────────────┐
│   Coordinator    │  (reads results, synthesizes)
│   (fan-in)      │
└────────┬────────┘
         ▼
    Summary to user
```

## File Formats

### manifest.json
```json
{
  "id": "swarm-1716900000",
  "goal": "Refactor auth module and add tests",
  "status": "running",
  "created": 1716900000,
  "agents": [
    { "id": "agent-1", "paneId": "pane-abc", "cli": "claude", "status": "running", "task": "refactor" },
    { "id": "agent-2", "paneId": "pane-def", "cli": "codex", "status": "complete", "task": "tests" }
  ]
}
```

### Task file (agent-1.task.md)
```markdown
---
swarm: swarm-1716900000
agent: agent-1
cli: claude
model: opus
---

## Your Task

Refactor the authentication module in `src/auth/` to use the repository pattern.

## Context

- This is part of a coordinated swarm. Other agents are working on related tasks.
- Read `.voss/swarm/shared/context.md` for shared project context.
- Do NOT modify files in `src/auth/tests/` — another agent handles tests.

## When Done

Write your results summary to `.voss/swarm/results/agent-1.result.md` with:
- What you changed
- Files modified
- Any issues encountered
```

### Result file (agent-1.result.md)
```markdown
---
agent: agent-1
status: complete
files_modified: ["src/auth/repo.ts", "src/auth/service.ts"]
duration_secs: 45
---

## Summary

Refactored auth module to use repository pattern. Created `AuthRepository` interface...
```

## Plan Breakdown

| Plan | Name | Wave | Depends |
|------|------|------|---------|
| A13-01 | Swarm file protocol + SwarmController | 1 | — |
| A13-02 | Task decomposition coordinator | 1 | — |
| A13-03 | Agent spawn integration + prompt injection | 2 | 01 |
| A13-04 | Result watching + fan-in synthesis | 2 | 01, 02 |
| A13-05 | Sidebar swarm UI + launch flow | 3 | 01, 03 |
| A13-06 | Swarm persistence + resume | 3 | 01, 04 |
