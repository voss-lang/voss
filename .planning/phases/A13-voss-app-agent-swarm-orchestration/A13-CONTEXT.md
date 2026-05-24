# A13 — Agent Swarm Orchestration

## What This Phase Delivers

A file-mediated multi-agent swarm system where the user can launch a coordinated team of agents (Claude, Codex, OpenCode, etc.) that decompose a task, work in parallel, and synthesize results — all visible and controllable from the sidebar.

## Why Now

A12 built the ADE sidebar with agent detection, launch modal, and monitoring. But agents currently work in isolation — each pane is independent. The swarm system makes Voss an actual orchestration platform where agents collaborate on a shared goal.

## Core Concept: File-Mediated Swarm

Third-party CLIs (Claude Code, Codex, OpenCode) can't share memory or use custom IPC protocols. But they all understand files. The swarm coordinator:

1. Decomposes user's task into subtasks
2. Writes task files to `.voss/swarm/tasks/`
3. Spawns agents with prompt prefix: "Read your task file, do the work, write results"
4. Monitors completion via fs events + PTY output markers
5. Synthesizes results and presents to user

## Design Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D-01 | File-mediated communication | Works with any CLI agent without modification |
| D-02 | Single coordinator pattern (not peer-to-peer) | Simpler, debuggable, auditable — coordinator owns all routing |
| D-03 | Coordinator is a lightweight LLM call, not a full agent | Avoids recursion; coordinator decomposes then monitors, doesn't do work |
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
| D-14 | Completion detection: fs watch on result files + PTY idle heuristic | Belt and suspenders; don't rely solely on terminal output parsing |

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
