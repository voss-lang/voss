# Research Report: Agentic Development Environments for Voss ADE Design Contract
> Generated: 2026-06-08 | Depth: Maximum practical | Research passes: 11 | Sources: 39 URLs + 11 local Voss artifacts
> Focus: Design-contract input for implementing a functioning Voss ADE on top of the existing Voss orchestration stack.

---

## Executive Summary

The ADE category is converging around a clear product shape: a terminal-native or editor-adjacent workbench where the user launches, monitors, steers, reviews, and audits multiple coding agents. The strongest products do not treat the terminal as legacy UI. They treat it as the primary interaction substrate because it exposes commands, logs, tests, shells, and agent actions in the same medium the developer already trusts. Research and current product docs support this: Warp frames the ADE as a combination of Code, Agents, Terminal, and Drive; Lemonade frames its grid as the core; BridgeSpace frames the workspace as a "room" where tasks, terminals, editor context, and agents open together; Vibe Kanban uses the board as the control layer over agent workspaces.

For Voss, the useful direction is not to copy a polished terminal grid. Voss already has that surface in `apps/voss-app`: Tauri shell, PTY panes, sidebar, workspace tabs, command palette, status bar, swarm files, and Org/Run panels. The stricter opportunity is to make the ADE express the Voss product thesis: "agent engineering organization" with scoped roles, budget, permissions, reviewer gates, session-tree replay, and audit. This means the first real screen should center a run board plus live/replayable evidence, with terminals as inspectable execution surfaces. The terminal grid remains necessary, but it should not be the conceptual center once a Voss run exists.

Market evidence points to six reusable interface primitives: goal intake, agent roster, task/board state, execution surfaces, review/diff surfaces, and audit/replay/history. BridgeSpace and Vibe Kanban emphasize task boards and review loops. Warp and Lemonade emphasize agent/session management in terminal-like surfaces. Cursor, GitHub Copilot cloud agent, Devin, and Replit emphasize asynchronous work, isolated environments, branches/checkpoints, and PR/review handoff. Claude Code and OpenCode expose the low-level contracts Voss should respect: explicit agents/subagents, tool permissions, sessions, JSON/server modes, hooks, and dangerous permission bypasses.

The strongest design implication for Voss is a two-mode ADE, not a scattered multi-tool canvas. Mode 1 is "Live Work": terminal grid, rich goal input, agent roster/sidebar, permission queue, status, budget, and attention routing. Mode 2 is "Run Review": board, session tree, audit, reviewer verdicts, diff/verification, blocked decisions, and replay. Voss already has an `OrgViewShell` with 10 tabs, but for a strict design contract it should evolve from tabbed panels into an integrated run cockpit: board as the spine, details as drilldowns, and audit/replay as the sign-off path.

The main category risk is that every ADE markets parallel autonomy while the actual safety boundary remains human review. Academic and product sources agree that agents can run commands, edit files, access networks, and submit PRs; security research shows this broad authority turns prompt injection into real shell risk. PR lifecycle research shows merge authority remains mostly human even when agents initiate work. Voss should use this as differentiation: make the cage visible. Budget, scope, permissions, confidence, reviewer A/B separation, and replay should be visible as product controls, not hidden telemetry.

---

## Table of Contents

1. Research Method
2. Landscape Map
3. Product Findings by ADE
4. Cross-Product UI Patterns
5. Workflow and Process Patterns
6. Voss Stack Anchors
7. Design Contract Implications
8. Implementation Shape for Voss
9. Contradictions and Disputed Claims
10. Confidence Assessment
11. Research Gaps
12. All Sources

---

## 1. Research Method

This report combines:

- External product/source research across BridgeSpace, Warp, Lemonade, Vibe Kanban, Cursor, Devin, Google Antigravity, Windsurf/Devin Desktop Cascade, GitHub Copilot cloud agent, Replit Agent, Claude Code, and OpenCode.
- Academic/security research on terminal-agent collaboration, Claude Code architecture, terminal coding agents, agent PR workflows, and prompt-injection risks.
- Local Voss source and planning review using Graphify first, then Voss planning/source files where necessary.

The report is written as a bridge into a design contract. It intentionally prioritizes UI structure, interaction patterns, workflow controls, and Voss implementation constraints over generic market commentary.

## 2. Landscape Map

### ADE product archetypes

| Archetype | Examples | Interface center | Key lesson for Voss |
|---|---|---|---|
| Terminal-native ADE | Warp, Lemonade, BridgeSpace, OpenCode | Terminal sessions, grids, vertical tabs, universal input | Preserve terminal affordances, but add explicit agent state and evidence. |
| Board/workflow ADE | Vibe Kanban, BridgeSpace | Kanban tasks, workspaces, branches, review | Board state should drive orchestration, not merely visualize it. |
| Agent-first IDE | Cursor, Windsurf/Devin Desktop, Antigravity | Editor + agent side panel/manager + terminal/browser | Useful for synchronous agent steering; less distinct for Voss unless audit is central. |
| Cloud asynchronous agent | Devin, GitHub Copilot cloud agent, Cursor background agents, Replit Agent | Remote workspace, branch/PR/checkpoint handoff | Treat "background work" as a reviewable artifact stream, not a black box. |
| CLI/harness agent | Claude Code, OpenCode, Codex-like CLIs | Terminal loop, tools, permissions, sessions | Voss should interoperate and make permissions/sessions first-class. |

### 8 subtopics discovered

1. Terminal and execution surfaces: how ADEs expose shells, logs, prompts, command output, and long-running tasks.
2. Agent management: how products show multiple agents, sessions, profiles, roles, status, cost, and attention needs.
3. Task and board structure: how work is decomposed into issues/cards, assigned, moved, and reviewed.
4. Review and diff workflows: how AI-generated changes become inspectable and actionable.
5. Context and memory: how files, prior conversations, project notes, prompts, rules, and environment metadata are attached.
6. Permissions and safety: how tools gate commands, dangerous modes, cloud isolation, branches, and approval.
7. Replay, checkpoints, and audit: how work can be reconstructed, rolled back, or signed off.
8. Voss implementation mapping: how these patterns align with `voss serve`, SSE events, `.voss team{}`, session tree, budget, reviewers, and `apps/voss-app`.

## 3. Product Findings by ADE

### BridgeSpace / BridgeMind

Primary sources:

- [BridgeSpace product page](https://www.bridgemind.ai/products/bridgespace)
- [BridgeMind BridgeSpace docs](https://docs.bridgemind.ai/docs/bridgespace)

BridgeSpace is the closest public analogue to "ADE as a room." Its product page describes a desktop workspace for up to 16 parallel AI coding agents with multi-pane terminals, Kanban task boards, and integrated editors. The docs define a task board with Todo, In Progress, In Review, and Complete columns, and an execution flow where selecting a task resolves the project folder, creates a workspace or terminal, constructs a command with knowledge context, waits for the shell prompt, sends the command, and monitors execution.

Relevant UI/process details:

- "Room" metaphor: Command Room, Swarm Room, Review Room.
- Work starts from task, repo, or rough idea.
- Opening a room brings up terminal panes, editor context, project tasks, and agent launch points together.
- Swarm flow supports builders, reviewers, scouts, and handoff status.
- Review flow keeps changed files, notes, checks, and ship decision visible.
- Workspace tabs have independent pane layouts and colors.
- Templates include single, split, quad, six, and up to 16 terminals.
- Agent configuration and prompt library are Pro-tier primitives in the docs.

Design extraction for Voss:

- Voss should use "room" only if it maps to a hard runtime mode. Better names: `Live Work`, `Run Review`, `Audit Replay`.
- The board columns in Voss should not mirror BridgeSpace exactly; Voss already has Backlog, Planned, InProgress, InReview, Blocked, Done. Keep Voss's six-column board because it encodes the orchestrator state machine.
- BridgeSpace's execution flow reinforces the need for launch-time binding: task -> cwd -> command/profile -> terminal -> monitor. Voss already has `spawn_agent`, agent registry, and workspace paths; the missing strict contract is how a Voss board card binds to a pane/session.

### Warp

Primary sources:

- [Introducing Warp 2.0](https://www.warp.dev/blog/reimagining-coding-agentic-development-environment)
- [Warp Universal Input docs](https://docs.warp.dev/terminal/universal-input)
- [Universal Agent Support](https://www.warp.dev/blog/universal-agent-support-level-up-coding-agent-warp)

Warp is the most explicit "ADE" narrative: a terminal-born environment with Code, Agents, Terminal, and Drive. The 2025 Warp 2.0 announcement emphasizes agent multi-threading, monitoring multiple agents under user control, prompt-first workflows, planning mode, native code review, and direct diff editing. Its docs describe Universal Input as a shared editor for shell commands and natural-language prompts with Agent Mode, Terminal Mode, and auto-detection. Context chips include current directory, prior conversations, Git status, node version, file attachments, and @ context.

The 2026 universal-agent-support announcement is especially relevant: Warp now supports third-party CLI agents such as Claude Code, Codex, Gemini CLI, and OpenCode with vertical tabs, notifications, native code review, code-as-context, rich input, and remote control.

Relevant UI/process details:

- One rich input surface that handles prompt vs command mode.
- Input mode switcher: Agent, Terminal, Auto.
- Context chips: cwd, prior conversations, Git status, files, runtime metadata.
- Vertical tabs for agent sessions, with metadata like branch/worktree/PR.
- Notifications route attention when agents require input.
- Code review comments can be sent back to a running agent.
- Native code editor/diff editor avoids switching to a separate IDE.

Design extraction for Voss:

- Voss needs a universal goal/input strip, but it must expose Voss-specific mode, role, scope, budget, and permission profile. Do not copy a generic "AI prompt" box.
- Vertical tabs map well to Voss sessions, but Voss's stronger primitive is a session tree. The UI should show both: a compact running-agent list for live work and a tree for run lineage/replay.
- Warp's "richer than CLI" lesson matters: the Voss ADE should not just embed CLI output. It should render structured SSE/JSON events as first-class UI: `plan`, `tool`, `permission.updated`, `budget.updated`, `confidence.updated`, `gate.updated`, and `session.idle`.

### Lemonade

Primary source:

- [Lemonade docs](https://getlemonade.dev/docs)

Lemonade is the cleanest example of "multi-agent terminal grid" as a product. It is not an IDE or AI provider; it runs terminal-compatible agents side by side. Its docs state that any shell command can be added as a custom agent, and the grid layout scales from 1 full-screen agent to 2 side-by-side, 3-4 in a 2x2 grid, 5-6 in a 2x3 grid, and 7-8 in a 2x4 grid. Studio Mode is an infinite canvas with Agent, Group, Note, Task list, Media, and Browser nodes.

Relevant UI/process details:

- Agent presets and custom shell commands.
- Startup delays to prevent focus races on launch.
- Workspaces with independent grids, agents, and working directories.
- Pinned workspaces restore original agent configuration.
- Background workspace tab pulses when an agent is waiting for yes/no input.
- Broadcast mode sends keystrokes to all terminals.
- Studio Mode supports pan/zoom nodes, browser/docs/media beside agents.
- Warnings: dangerous permission bypass modes and high memory usage from many PTY sessions.

Design extraction for Voss:

- Lemonade validates Voss's existing A-track terminal grid, but Voss should cap visible concurrent panes based on cognitive load and budget, not just what the grid can fit.
- "Attention detection" is essential. Voss should create a permission/blocked queue that is visible globally, not hidden inside a pane.
- Broadcast mode is dangerous in a Voss context unless constrained to read-only or explicit safe commands. Voss should avoid blanket broadcast in the first strict contract.
- Studio/freeform canvas is less important than Voss's board/session-tree. It may be a later "investigation canvas," not the core ADE.

### Vibe Kanban

Primary sources:

- [Vibe Kanban product site](https://www.vibekanban.com/)
- [BloopAI/vibe-kanban GitHub](https://github.com/BloopAI/vibe-kanban)

Vibe Kanban is the clearest "board as agent orchestration" reference. It presents parallel coding agents, switching between Claude Code, Codex, OpenCode, and others, code review diffs, comments on AI-generated code, QA with built-in browser, and issue/sub-issue organization. The GitHub repo says each workspace gives an agent a branch, terminal, and dev server; the UI supports inline diff comments sent directly to the agent, built-in browser with devtools/inspect/device emulation, PR creation/merge, and 10+ coding agents.

Relevant UI/process details:

- Kanban board is not decorative; it controls work and status.
- Each agent workspace couples branch + terminal + dev server.
- Review diff and comments are part of the agent feedback loop.
- Browser QA is adjacent to the coding session.
- Agent status updates can flow into issue status and PR lifecycle.

Design extraction for Voss:

- Voss's board should be the spine of the org-loop UI. Each card should have a linked role, scope, budget envelope, terminal/session node, diff, verification, reviewer verdict, and audit evidence.
- Voss should support card drilldowns that send feedback to the appropriate agent/session, but early implementation can shell through the single allowed CLI decision path where V11 requires it.
- Built-in browser is useful for web app verification, but Voss should treat it as a capability/view attached to a card's verification evidence rather than a generic browser node.

### Cursor Background Agents

Primary sources:

- [Cursor background agent docs](https://docs.cursor.com/background-agent)
- [Cursor background agent status API](https://docs.cursor.com/background-agent/api/agent-status)

Cursor background agents are asynchronous remote agents. The docs describe a native sidebar for viewing/searching/starting background agents, `Ctrl+E` mode, and selecting an agent to view status or enter the machine. Agents run in isolated Ubuntu VMs, clone GitHub repos, work on separate branches, and push back for handoff. Environment setup is captured in `.cursor/environment.json` with install/start/terminals. Security notes explicitly distinguish background agents from foreground agents: background agents auto-run terminal commands, while foreground agents require approval for every command.

Relevant UI/process details:

- Native sidebar listing all background agents.
- Remote machine entry/takeover.
- Status values and API fields: running, finished, error, creating, expired; repo/ref; branch; PR URL; created time; summary.
- Environment setup includes install commands, startup commands, and terminal processes.
- Security mode and privacy mode are explicit parts of the product surface.

Design extraction for Voss:

- Voss can start local, but it should still model the same state shape: source ref, working branch/worktree, run status, summary, active terminal, and takeover affordance.
- Voss should show whether commands are auto-approved, per-role allowed, or blocked by PermissionGate. The UI should make foreground vs autonomous mode visually unambiguous.
- `.voss/team{}` plus `.voss/principles.yml` can become the local equivalent of `.cursor/environment.json`, but with stronger role/scope/budget semantics.

### Devin

Primary source:

- [Devin docs introduction](https://docs.devin.ai/get-started/devin-intro)

Devin positions itself as an AI software engineer with a conversational UI, embedded IDE, shell, browser, and web application. The docs recommend clear prompts with explicit completion criteria, verifiable tasks, scoped steps, and using the web app for complex tasks before taking over in Devin's IDE. The interface exposes shell output/logs, IDE edits, and browser activity; users can take over to edit, run commands, or test.

Relevant UI/process details:

- Conversational UI with embedded development tools.
- Shell output and logs are visible/copyable.
- Embedded IDE supports direct takeover.
- Browser can be used by Devin and the user for docs/testing.
- Workflows include Slack/Teams task delegation, web app delegation, local CLI quick fixes, `/handoff`, and draft PRs for review.

Design extraction for Voss:

- Voss should support "take over" semantics for any running agent pane/session. This can be explicit: `Open Terminal`, `Inspect Diff`, `Send Follow-up`, `Abort`, `Replay`.
- Devin's best-practice emphasis on completion criteria aligns with Voss's Reviewer-A bar and audit product. In Voss, completion criteria should be captured into the run/card and tied to verification evidence.

### Google Antigravity

Primary sources:

- [Antigravity product page](https://antigravity.google/product/antigravity-ide?app=antigravity-ide-)
- [Antigravity docs home](https://antigravity.google/docs/home?authuser=0)
- [Antigravity browser docs](https://www.antigravity.google/docs/browser)
- [Antigravity terminal docs](https://antigravity.google/docs/terminal)

Note: Google's Antigravity docs rendered poorly in the fetcher, so the report uses search snippets as a lower-confidence source.

Antigravity frames itself as agent-first: agents are extracted into their own surface and operate across editor, terminal, and browser. Its product page describes an Editor view with autocompletion, natural-language commands, configurable context-aware agent, and an Agent Manager. It emphasizes artifacts: agents record browser actions and present screenshots/videos as artifacts, and users can leave comments/feedback on artifacts.

Relevant UI/process details:

- Agent Manager is a first-class surface.
- Agents operate across editor, terminal, and browser.
- Browser actions can produce screenshots/videos as artifacts.
- Feedback is attached to artifacts, not just chat.
- Terminal integration is partly constrained to local workspaces.

Design extraction for Voss:

- Artifact feedback is directly useful. Voss should treat diffs, test logs, screenshots, browser recordings, reviewer verdicts, and audit sections as commentable evidence objects.
- Voss's audit/replay surface can be a stronger version of Antigravity's artifact stream because Voss has session tree and recorder semantics.

### Windsurf / Devin Desktop Cascade

Primary source:

- [Cascade docs](https://docs.devin.ai/desktop/cascade/cascade)

Cascade exposes Code/Chat modes, planning/Todo lists, queued messages, tool calling, voice input, named checkpoints and reverts, real-time awareness, linter integration, and simultaneous cascades. The docs state that a specialized planning agent refines the long-term plan in the background while the selected model handles short-term actions. Cascade can make up to 20 tool calls per prompt, supports continue/auto-continue, and can revert changes made from a prompt.

Relevant UI/process details:

- Code vs Chat modes.
- Long-term plan/Todo list inside conversation.
- Queued follow-up messages while work is active.
- Tool-call limit and explicit Continue.
- Checkpoint/revert from prompt history.
- Real-time awareness of user actions.
- Problems panel can send errors to the agent.

Design extraction for Voss:

- Voss should separate "plan/board" from "chat/terminal" but keep them mutually aware.
- Queued messages can map to card follow-ups or session messages, but must respect one running turn per session in `PROTOCOL.md`.
- Continue/auto-continue should be governed by Voss budget and confidence gates, not a generic prompt-credit notion.

### GitHub Copilot Cloud Agent

Primary sources:

- [GitHub Copilot cloud agent docs](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)
- [GitHub Blog: coding agent vs agent mode](https://github.blog/developer-skills/github/less-todo-more-done-the-difference-between-coding-agent-and-agent-mode-in-github-copilot/)

GitHub's docs distinguish synchronous IDE agent mode from asynchronous cloud agent. The cloud agent works in GitHub Actions-powered ephemeral environments, researches/plans/makes code changes on a branch, optionally opens PRs, and creates transparency through commits/logs/PR review. The blog frames agent mode as real-time collaboration inside the IDE and coding agent as an asynchronous teammate in the cloud.

Relevant UI/process details:

- Agents panel and GitHub entry points.
- Issue assignment and PR workflow are the control surface.
- Work is visible through branch, commits, logs, and PR.
- Multiple custom agents can specialize in different tasks.
- Human review is the oversight checkpoint.

Design extraction for Voss:

- The "agent mode vs cloud agent" distinction maps to Voss terminal-grid vs org-run view.
- Voss should make branch/worktree/run lineage visible even when work is local.
- Voss's final audit should be more explicit than a PR timeline: it should show original idea, cards, role routing, budget, scope, reviewers, unsupported claims, and residual risks before sign-off.

### Replit Agent

Primary sources:

- [Replit Agent overview](https://docs.replit.com/references/agent/overview)
- [Replit checkpoints and rollbacks](https://docs.replit.com/references/version-control/checkpoints-and-rollbacks)

Replit Agent is a broader app-builder agent, but its UX patterns matter. It supports Plan mode before code changes, Agent modes such as Lite/Economy/Power, Design Canvas, active background task limits, and checkpoints/rollbacks. Checkpoints include AI-generated descriptions, timestamps, change scope, and billing information; they appear in the Agent tab, Git pane, and History view.

Relevant UI/process details:

- Plan mode produces ordered tasks for review before building.
- Agent modes expose cost/speed/capability tradeoffs.
- Checkpoints are complete state snapshots with rollback.
- Billing/cost is attached to checkpoints.
- Design Canvas is a visual pre-code surface.

Design extraction for Voss:

- Voss's budget envelope should be visible like Replit's checkpoint cost metadata, but stricter: parent/card/agent spent, limit, remaining, and gate status.
- Checkpoints map to session-tree nodes and run frames. Voss should not invent a separate checkpoint model if session tree already supports replay.
- Plan mode should be the default before any mutating run unless the user chooses a high-autonomy mode.

### Claude Code

Primary sources:

- [Claude Code subagents docs](https://code.claude.com/docs/en/sub-agents)
- [Claude Code hooks docs](https://code.claude.com/docs/en/hooks)
- [Claude Agent SDK permissions](https://platform.claude.com/docs/en/agent-sdk/permissions)
- [Claude blog on subagents](https://claude.com/blog/how-and-when-to-use-subagents-in-claude-code)

Claude Code is a low-level architecture reference. Subagents are specialized assistants with their own context window, system prompt, tool access, and permissions. They can be invoked automatically, by @ mention, or as a session-wide default. Hooks can run before/after tool use and around subagent lifecycle events. Permission controls and bypass modes are central.

Relevant UI/process details:

- Custom subagents live in project/user markdown files.
- Each subagent has isolated context, tool access, and permissions.
- Hooks can validate commands or run formatters/lints after edits.
- Subagents can be denied by permission rules.
- Permission bypasses are powerful and dangerous.

Design extraction for Voss:

- Voss's role roster should look like a managed version of subagents: role, model, scope, tools, budget, permission mode, current card, status.
- The UI should show inherited permissions and where a subagent/role can act.
- Hooks/lifecycle events map to Voss recorder events and review gates; render them as evidence rather than burying them in logs.

### OpenCode

Primary source:

- [OpenCode CLI docs](https://open-code.ai/en/docs/cli)

OpenCode matters because Voss's protocol intentionally mirrors OpenCode where possible. OpenCode starts a TUI by default, supports CLI automation, custom agents with permissions, `serve` for headless API access, `run --format json`, session list/export/import, stats, MCP, LSP, plugins, and a dangerous skip-permissions mode.

Relevant UI/process details:

- `opencode serve` creates a headless HTTP server for API access.
- `opencode run --format json` supports raw JSON events.
- Agents can be created with mode, permissions/tools, model, and frontmatter.
- Sessions can be listed, exported, imported, forked, continued, and attached.
- Stats expose token usage and cost by sessions/tools/models.

Design extraction for Voss:

- Voss's REST/SSE protocol is directionally right. The ADE should use structured events, not terminal scraping, for Voss-native runs.
- The ADE can still host third-party CLIs in PTYs, but Voss-native panes should graduate to protocol-backed views.
- Session export/import/fork semantics should become visible in the UI because Voss already has session tree lineage.

## 4. Cross-Product UI Patterns

### Pattern 1: One work command surface

Warp's Universal Input, Replit's chat input + Plan mode, and Voss's own CLI point toward one primary input strip. The input should not be "chat" only. It should accept:

- Natural language goal.
- Terminal command.
- Run mode: plan/edit/auto.
- Role/team profile.
- Scope and budget.
- Attachments/context.
- Existing card/session continuation.

Voss contract implication:

The ADE should expose a `GoalBar` or `RunCommandBar` with explicit fields/chips:

- `mode`: Plan, Edit, Auto.
- `team`: selected `.voss team{}` or default roster.
- `scope`: project ceiling and edit scope.
- `budget`: tokens/USD envelope.
- `risk`: low/med/high or computed from scope/budget/core-file touch.
- `context`: files, folders, docs, prior sessions, issue/PR.
- `start`: creates Voss session/run through protocol or CLI.

### Pattern 2: Agent roster/sidebar

BridgeSpace, Warp, Lemonade, Cursor, Antigravity, and Voss A12 all point to an agent roster. Roster rows need more than names:

- Role.
- Model/provider.
- Status.
- Current card/task.
- Cwd/workspace.
- Branch/worktree.
- Cost/budget.
- Permission/autonomy mode.
- Last event / needs attention.

Voss contract implication:

The existing `AgentSidebar` should become a `TeamSidebar` for Voss-native runs. It can still list generic terminal agents, but Voss role agents should render richer data from `TeamConfig`, `SubagentSpec`, session tree, and live SSE events.

### Pattern 3: Board as state machine

Vibe Kanban and BridgeSpace use Kanban as product workflow. Voss goes further: the board is the orchestrator state machine. Therefore the board cannot be just "task cards."

Each Voss card must show:

- Card title and id.
- Column/state.
- Assigned role.
- Risk tier.
- Scope.
- Budget spent/limit.
- Confidence/gate state.
- Verification status.
- Reviewer A/B state.
- Retry count.
- Block reason if blocked.
- Linked session node/terminal.

Voss contract implication:

The board is the center of `Run Review` and the summary band in `Live Work`. Card transitions should be traceable to gate events and reviewer verdicts.

### Pattern 4: Attention and permission queue

Lemonade pulses workspace tabs when background agents wait for yes/no input. Warp has notifications and a unified notification center. Cursor lets users view status and take over. Voss's protocol has `permission.updated`, `gate.updated`, budget/confidence updates, and session idle.

Voss contract implication:

Add a global `AttentionQueue` with these categories:

- Permission needed.
- Budget threshold crossed.
- Confidence below gate.
- Scope violation.
- Agent idle/blocked.
- Verification failed.
- Final sign-off available.

Permission dialogs should include:

- Tool name and arguments.
- Mutability/network/scope dimension.
- Affected file/path/command.
- Role/card/session.
- Budget/confidence context.
- Choices: allow once, allow always for this scoped rule, deny.

### Pattern 5: Diff/review as a first-class loop

Warp, Vibe Kanban, Devin, GitHub Copilot, and Replit all surface changes as reviewable artifacts. Voss has reviewers, verification, unsupported claims, and audit sections; the UI should exploit that.

Voss contract implication:

Diff viewer should not be an isolated tab. It should be a drilldown from:

- Board card.
- Reviewer verdict.
- Audit unsupported claim.
- Replay frame.
- Blocked decision.

Inline comments or follow-up prompts should route back to the correct card/session/role when the harness exposes the write path.

### Pattern 6: Replay/checkpoints/history

Replit checkpoints and OpenCode/Claude sessions show that users need recoverability. Voss's session tree can be more precise than generic checkpoints.

Voss contract implication:

The replay UI should show:

- Timeline of run events.
- Board frame at each transition.
- Agent/tool events.
- Files/diffs at frame.
- Budget/confidence at frame.
- Reviewer/gate decision at frame.

Replay should support "inspect" first. Rollback or re-run can be later.

### Pattern 7: Browser/testing surface

Vibe Kanban, Devin, Antigravity, and Replit all include browser/design/test surfaces. Voss should not add a general browser too early, but should plan for a browser artifact panel.

Voss contract implication:

Browser/testing should be a `VerificationArtifact` view attached to cards:

- URL/test target.
- Screenshot/video.
- Console/network summary.
- Test command/log.
- Reviewer notes.

## 5. Workflow and Process Patterns

### Synchronous vs asynchronous work

GitHub's distinction is useful:

- Synchronous agent mode: local, watched, interactive, continuous oversight.
- Asynchronous coding agent: branch/PR/checkpoint workflow, review at handoff.

Voss should explicitly support both:

- `Live Work`: local/interactive/synchronous.
- `Delegated Run`: Voss team run continues with board/audit handoff.

The same Voss run can move between them. Starting in `Live Work` should produce the same session-tree/audit evidence as a delegated run.

### Plan before mutate

Replit Plan mode, Warp planning mode, GitHub cloud-agent planning, and Voss Reviewer-A bar all support this contract:

- Before mutating files, the agent should produce a plan/cards/acceptance/verification path.
- Human approval should happen at the plan level, not every safe read step.
- Mutating and risky operations then run under predeclared policy.

Voss has a product advantage here because `.voss team{}` can compile plan permissions into role scope/budget/tool filters.

### Agent branch/worktree isolation

Cursor, Vibe Kanban, GitHub, and Claude subagent worktree discussions all converge on branch/worktree isolation. Voss current local app uses PTYs and workspaces; the design contract should require the UI to show isolation level even before full worktree automation exists.

Required visible fields:

- Branch.
- Worktree path.
- Cwd.
- Dirty file count.
- Scope ceiling.
- Card edit scope.

### Human review remains the governance boundary

Academic PR studies show operational agency and merge governance are separate. Agents can initiate work, but human merge/review remains the actual authority. Voss should avoid pretending otherwise. Its "autonomy" should be framed as bounded execution inside a cage with explicit sign-off.

Voss final sign-off should not enable until:

- Run final exists.
- Board has no in-flight cards.
- Reviewer A/B verdicts are visible.
- Unsupported claims and residual risks are visible.
- Scope/budget state is visible.
- Killed/rescoped cards are surfaced.

## 6. Voss Stack Anchors

### Local artifacts reviewed

- `.planning/PROTOCOL.md`
- `.planning/docs/ORCHESTRATION_LAYERS.md`
- `.planning/ORCHESTRATION-PLAN.md`
- `.planning/ADE-REDESIGN.md`
- `.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md`
- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md`
- `.planning/phases/V11-ade-org-integration/V11-SPEC.md`
- `apps/voss-app/src/App.tsx`
- `apps/voss-app/src/org/OrgViewShell.tsx`
- `apps/voss-app/src/org/types.ts`
- `apps/voss-app/src-tauri/src/lib.rs`

### What Voss already has

From local docs and source, Voss already has:

- Tauri/Solid app in `apps/voss-app`.
- PTY panes and terminal grid.
- Agent launch and registry (`spawn_agent`, `get_active_agents`, registry DB).
- Workspaces and workspace tabs.
- Sidebar, status bar, command palette, context panel.
- Swarm file protocol in `.voss/swarm/`.
- Org/Run shell with 10 panels: roster, board, tree, audit, verdict, budget, scope, diff, blocked, replay.
- Voss protocol plan: REST + SSE with versioned payloads.
- Permission protocol: `permission.updated`, modal reply, allow/deny choices.
- Event taxonomy: plan/tool/clarify/final/stream/status/cognition/warning plus Voss-native budget/confidence/gate events.
- Session tree and audit-oriented planning.
- Product thesis around agent engineering organization, six primitives, board state machine, reviewer A/B, budget/scope/confidence cage.

### Current tension

The app currently combines:

- A terminal multiplexer direction.
- A sidebar/visual redesign direction.
- A swarm file direction.
- A V11 org panel direction.

The concern in the user's brief is valid: these can feel like adjacent features rather than a strict ADE contract. The research suggests the fix is not another visual theme. The fix is a hierarchy:

1. Goal/run intake.
2. Board/org state.
3. Agent execution surfaces.
4. Evidence/review/audit.
5. Terminal panes as inspectable execution, not the whole product.

## 7. Design Contract Implications

### Product definition

Voss ADE is a local-first agent engineering organization workbench. It runs terminals and agents, but its primary job is to keep AI engineering work scoped, budgeted, reviewed, and replayable.

### Primary surfaces

1. `Live Work`
   - Goal bar.
   - Team/sidebar roster.
   - Board summary strip.
   - Terminal grid.
   - Permission/attention queue.
   - Status/budget bar.

2. `Run Review`
   - Board as the spine.
   - Details drawer for selected card.
   - Session tree/replay timeline.
   - Diff + verification.
   - Reviewer A/B verdicts.
   - Audit summary/residual risk/sign-off.

3. `Settings/Team`
   - Team roles.
   - Principles.
   - Model/provider.
   - Tool groups.
   - Permission policy.
   - Budget defaults.

### Strict layout recommendation

Avoid a freeform canvas for the first contract. Use a dense, stable operational layout:

```
Titlebar / Workspace Tabs
Run Command Bar
Left Team Sidebar | Main Work Surface | Right Evidence / Attention Drawer
Status Bar
```

Main Work Surface switches between:

- Terminal Grid.
- Board Review.
- Replay.
- Diff/Verification focus.

The same selected card/session should drive all surfaces.

### Component contracts

#### RunCommandBar

Purpose: start or continue work.

Required elements:

- Text input for goal/command.
- Mode segmented control: Plan, Edit, Auto.
- Team selector.
- Scope chip.
- Budget chip.
- Context attach button.
- Start/continue button.
- Explicit "Voss native" vs "terminal agent" execution indicator.

Do not:

- Hide mode in placeholder text.
- Auto-detect destructive autonomy without visible policy.
- Let "Auto" start without budget/scope display.

#### TeamSidebar

Purpose: show humans what agents/roles are doing.

Rows must include:

- Role/name.
- Model/provider.
- Current card/session.
- Status.
- Budget spent/limit.
- Permission mode.
- Attention indicator.

Sections:

- Voss Team.
- External Terminal Agents.
- Sessions/Runs.
- Project context.

#### BoardView

Purpose: orchestrator state machine and run overview.

Columns:

- Backlog.
- Planned.
- InProgress.
- InReview.
- Blocked.
- Done.

Card badges:

- Role.
- Risk.
- Scope.
- Budget.
- Confidence.
- Verification.
- Reviewer A/B.
- Retry count.

Interactions:

- Select card -> details drawer.
- Click terminal/session badge -> focus execution pane.
- Click diff/review badge -> open diff detail.
- Click blocked badge -> open decision path.

#### CardDetails

Purpose: one-card source of truth.

Sections:

- Original idea and EM acceptance criteria.
- Reviewer-A bar/verification.
- Assigned role and routing rationale.
- Scope and files touched.
- Budget history.
- Tool events.
- Diff.
- Tests/evals.
- Reviewer-B verdicts.
- Replay events.
- Decision actions.

#### AttentionQueue

Purpose: prevent hidden stalls.

Items:

- Permission request.
- Blocked card.
- Failed verification.
- Low confidence.
- Budget exhausted/near exhausted.
- Scope violation.
- Agent waiting for input.
- Final sign-off.

Each item should link to card/session/evidence.

#### AuditSignoffPanel

Purpose: final product gate.

Must show:

- Done/blocked/killed/rescoped counts.
- Reviewer separation.
- Unsupported claims.
- Residual risks.
- Scope/budget final state.
- Killed/rescoped card diff/rationale.
- Sign-off action.

## 8. Implementation Shape for Voss

### Keep

- Existing Tauri/Solid app.
- Existing terminal grid and PTY panes.
- Existing AgentSidebar as a base.
- Existing OrgViewShell panel types as a data/rendering base.
- Existing V11 CLI JSON consumer constraints for current phase.
- Existing A12 Ignite theme unless there is a separate visual redesign task.

### Change direction

The current `OrgViewShell` uses tabs for 10 panels. For a strict ADE contract, tabs should become secondary. The integrated flow should be:

1. Board always visible in Run Review.
2. Selecting a card changes detail content.
3. Audit and replay are navigable modes tied to the same selected card/run.
4. Roster, budget, scope, and reviewer verdict become side/detail modules, not equal tabs.

Suggested Run Review layout:

```
Run Header: run id, idea, mode, refresh, sign-off state
Board Spine: six columns, compact cards
Detail Drawer: selected card evidence, reviewer verdicts, diff, tools
Timeline Rail: session tree/replay events
Bottom/Right Gate Bar: budget, confidence, scope, unsupported claims
```

### Protocol-backed path

Voss-native live runs should eventually use `.planning/PROTOCOL.md`:

- Start `voss serve`.
- Create/list sessions through REST.
- Stream run/session events over SSE.
- Render structured event union.
- Use `/permission` for decisions.
- Abort via `/abort`.
- Persist session tree on completion.

Current V11 is static snapshot + manual refresh through Tauri CLI wrappers. That is acceptable short-term, but the design contract should not lock the ADE into polling raw run snapshots forever.

### PTY-backed path

Third-party agents and generic terminal use should remain PTY-backed:

- Claude Code, Codex, Gemini CLI, OpenCode, custom commands.
- Agent registry tracks pane/session/cli/cwd.
- UI detects foreground agent status where possible.
- Permission/cost/state is best-effort unless the agent exposes structured data.

The UI must distinguish:

- `Voss native`: structured events, budgets, gates, audit.
- `Terminal agent`: terminal output, inferred status, limited audit.

### Data model contract

Voss ADE should normalize all visible work into these UI entities:

- `Run`: id, idea, cwd, team, status, created/ended, signoff.
- `Card`: id, title, state, role, risk, scope, budget, confidence, verification, retries.
- `Agent`: id, role, provider/model, status, card, session, permission mode.
- `SessionNode`: id, parent, role, card, envelope, transitions, terminal state.
- `Evidence`: type, source, card/session, timestamp, payload/ref.
- `Decision`: permission, gate, block, signoff.

Existing `apps/voss-app/src/org/types.ts` is a start but should be extended toward this normalized UI model when the protocol/client SDK lands.

### Visual priority

The design should be quiet, dense, and operational. Avoid:

- Marketing hero layout.
- Decorative cards nested inside cards.
- Overlarge type inside panels.
- Generic agent-chat-first hierarchy.
- Canvas sprawl before the board/replay flow is solid.

Use:

- Stable fixed-height headers and bars.
- Compact badges.
- Monospace numeric budget/cost/confidence.
- Semantic colors reserved for state.
- Minimal accent usage.
- Strong selection/linkage across board, terminal, diff, and replay.

## 9. Contradictions and Disputed Claims

### Contradiction 1: "Autonomy" vs human governance

Products market autonomous agents, but GitHub and PR lifecycle research show human review remains the governance endpoint. Copilot cloud agent works on branches/PRs and cannot be treated as merge authority. PR studies show operational initiative and merge governance are decoupled.

Voss implication:

Do not sell or design the ADE as "agents ship for you." Design it as "agents run inside a visible cage; you sign off with evidence."

### Contradiction 2: "Multi-agent speed" vs cognitive overload

Warp, BridgeSpace, Lemonade, and Vibe Kanban all emphasize parallel agents. Lemonade also notes high memory usage from 8 agents plus agent memory footprint. Community criticism of Warp points to UI clutter and loss of terminal focus as the product shifts toward coding-agent platform.

Voss implication:

The ADE should expose WIP limits and attention queues. Parallelism without board/WIP/budget/review is noise.

### Contradiction 3: "Terminal is enough" vs "terminal needs richer UI"

The CHI 2026 terminal paper argues terminals have representational compatibility, transparency, and low entry barriers. Warp argues its platform UI can exceed CLI agents by adding native diff editing, vertical tabs, notifications, and code review.

Voss implication:

Both are true. Preserve terminal transparency, but render Voss structured events in richer UI. The terminal is execution evidence; the ADE is orchestration and review.

### Contradiction 4: "Dangerous modes are useful" vs prompt-injection reality

OpenCode, Lemonade, Claude/Cursor-like tools expose or discuss permission bypass/auto-run modes. Security research shows agentic coding assistants can be turned into an attacker's shell through poisoned external artifacts.

Voss implication:

Dangerous/autonomous modes must be visibly scoped and auditable. Default should be plan/read/safe tools first, with mutating operations guarded by role policy and PermissionGate.

### Contradiction 5: "Board as project management" vs "board as runtime"

Vibe Kanban and BridgeSpace use boards for managing work; Voss's planning docs define the board as the orchestrator state machine. These are superficially similar but different in contract.

Voss implication:

Voss board columns cannot be arbitrary user labels in the first ADE contract. They encode transitions, gates, WIP, and evidence. Custom labels can wait.

## 10. Confidence Assessment

High confidence:

- ADEs need multi-agent/session management, terminal visibility, task/board structure, and review/diff surfaces.
- Voss should distinguish Voss-native structured runs from generic terminal-agent panes.
- Board, budget, scope, permissions, reviewer verdicts, and audit/replay are the differentiating Voss UX.
- Human sign-off/review remains necessary even in "autonomous" workflows.
- Prompt injection and broad shell access are first-class risks for any ADE.

Medium confidence:

- An integrated Board + Details + Timeline layout will be better than the existing 10-tab `OrgViewShell`. This follows from workflow reasoning and competitor patterns, but needs design/prototype validation.
- A universal input strip should be the primary entry point. Strongly supported by Warp/Replit/GitHub patterns, but exact Voss fields require implementation constraints.
- Browser/artifact support should be attached to card verification rather than a freeform node. Strong product logic, but not yet validated by Voss users.

Low confidence:

- Google Antigravity specifics, because official docs rendered poorly through the fetcher and source details relied partly on snippets.
- Product usage/performance claims from vendor marketing such as generated lines or benchmark position. These are not core to the design contract.
- Community sentiment as a representative sample. Reddit/HN-style comments are useful for failure modes, not quantitative conclusions.

## 11. Research Gaps

- BridgeSpace and Lemonade appear young; there is limited independent analysis of actual user workflows.
- Public screenshots/videos are useful for visual layout but were not deeply captured in this text-only report.
- Voss current UI should be inspected visually with screenshots before final design contract decisions.
- Need current structured contracts for V4-V9 JSON exports to avoid designing fields that the app cannot load.
- Need a live `voss serve` prototype path if the next phase moves beyond V11 static snapshot/manual refresh.
- Need to decide whether the ADE should prioritize local-first native app, web app, or both for protocol clients.

## 12. All Sources

### Voss local artifacts

1. `.planning/PROTOCOL.md` - Voss REST/SSE protocol, event taxonomy, permissions, session lifecycle.
2. `.planning/docs/ORCHESTRATION_LAYERS.md` - canonical product thesis and ADE requirements.
3. `.planning/ORCHESTRATION-PLAN.md` - historical caged autonomous team design and board/gate invariants.
4. `.planning/ADE-REDESIGN.md` - current ADE visual/sidebar direction.
5. `.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md` - Ignite theme and layout contract.
6. `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md` - swarm file protocol and sidebar/swarm requirements.
7. `.planning/phases/V11-ade-org-integration/V11-SPEC.md` - Org/Run view, 10 panels, CLI JSON consumer constraints.
8. `apps/voss-app/src/App.tsx` - app composition, workspace/grid/sidebar/org view state.
9. `apps/voss-app/src/org/OrgViewShell.tsx` - current 10-tab Org/Run implementation.
10. `apps/voss-app/src/org/types.ts` - current RunData/session tree/audit/review TypeScript contract.
11. `apps/voss-app/src-tauri/src/lib.rs` - PTY, agent registry, swarm, org integration command wrappers.

### ADE products

12. [BridgeSpace product page](https://www.bridgemind.ai/products/bridgespace) - desktop ADE, up to 16 agents, rooms/workflow.
13. [BridgeSpace docs](https://docs.bridgemind.ai/docs/bridgespace) - Kanban, agent execution, workspace templates, shortcuts.
14. [Warp 2.0 ADE announcement](https://www.warp.dev/blog/reimagining-coding-agentic-development-environment) - ADE thesis, Code/Agents/Terminal/Drive, multithreading, planning, native diff.
15. [Warp Universal Input docs](https://docs.warp.dev/terminal/universal-input) - input modes, context chips, @ context, files, Git status, profile picker.
16. [Warp Universal Agent Support](https://www.warp.dev/blog/universal-agent-support-level-up-coding-agent-warp) - third-party CLI agents, vertical tabs, notifications, code review, remote control.
17. [Lemonade docs](https://getlemonade.dev/docs) - grid layouts, workspaces, attention detection, broadcast mode, Studio Mode, custom agents.
18. [Vibe Kanban site](https://www.vibekanban.com/) - board, parallel agents, review, QA browser, team workflow.
19. [BloopAI/vibe-kanban GitHub](https://github.com/BloopAI/vibe-kanban) - branch/terminal/dev-server workspaces, inline comments, browser/devtools, agent support.
20. [Cursor background agent docs](https://docs.cursor.com/background-agent) - background agents, sidebar, isolated VM, branches, environment setup, security notes.
21. [Cursor background agent status API](https://docs.cursor.com/background-agent/api/agent-status) - status fields, branch, PR URL, summary.
22. [Devin docs introduction](https://docs.devin.ai/get-started/devin-intro) - conversational UI, embedded IDE, shell, browser, takeover.
23. [Antigravity product page](https://antigravity.google/product/antigravity-ide?app=antigravity-ide-) - agent-first IDE, Agent Manager, editor/terminal/browser, artifacts.
24. [Antigravity docs home](https://antigravity.google/docs/home?authuser=0) - agent-first platform, multiple agents/codebases, Agent Manager.
25. [Antigravity browser docs](https://www.antigravity.google/docs/browser) - browser subagent, screenshots/videos as artifacts.
26. [Antigravity terminal docs](https://antigravity.google/docs/terminal) - local workspace terminal integration note.
27. [Devin Desktop Cascade docs](https://docs.devin.ai/desktop/cascade/cascade) - Code/Chat, planning/Todo, queued messages, checkpoints, linter, simultaneous cascades.
28. [GitHub Copilot cloud agent docs](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent) - cloud agent, Actions environment, branch/PR workflow, transparency.
29. [GitHub Blog: coding agent vs agent mode](https://github.blog/developer-skills/github/less-todo-more-done-the-difference-between-coding-agent-and-agent-mode-in-github-copilot/) - synchronous vs asynchronous agent workflows.
30. [Replit Agent overview](https://docs.replit.com/references/agent/overview) - Plan mode, modes, tasks, background limits, Design Canvas.
31. [Replit checkpoints and rollbacks](https://docs.replit.com/references/version-control/checkpoints-and-rollbacks) - checkpoint descriptions, timestamps, scope, billing, rollback UI.
32. [Claude Code subagents docs](https://code.claude.com/docs/en/sub-agents) - custom subagents, isolated contexts, tool permissions, invocation.
33. [Claude Code hooks docs](https://code.claude.com/docs/en/hooks) - lifecycle hooks and permission prompt integration.
34. [Claude Agent SDK permissions](https://platform.claude.com/docs/en/agent-sdk/permissions) - permission controls and bypass risk.
35. [Claude blog on subagents](https://claude.com/blog/how-and-when-to-use-subagents-in-claude-code) - practical subagent role patterns.
36. [OpenCode CLI docs](https://open-code.ai/en/docs/cli) - TUI, agents, permissions, sessions, serve, JSON output, stats, dangerous mode.

### Research, security, and criticism

37. [Terminal Is All You Need](https://arxiv.org/abs/2603.10664) - terminal design properties for human-AI agent collaboration.
38. [Dive into Claude Code](https://arxiv.org/abs/2604.14228) - Claude Code architecture, permissions, compaction, hooks, subagents, session storage.
39. [Building Effective AI Coding Agents for the Terminal](https://arxiv.org/abs/2603.05344) - terminal-native agents, safety controls, context management, planning/execution split.
40. [How Agentic AI Coding Assistants Become the Attacker's Shell](https://arxiv.org/abs/2605.25871) - prompt injection and shell risk.
41. [Your AI, My Shell](https://arxiv.org/abs/2509.22040) - prompt injection attacks on high-privilege agentic coding editors.
42. [Prompt Injection Attacks on Agentic Coding Assistants](https://arxiv.org/abs/2601.17548) - skills/tools/protocol ecosystem risks.
43. [Collaborator or Assistant?](https://arxiv.org/abs/2605.08017) - operational agency vs merge governance in PR lifecycles.
44. [Why Are Agentic Pull Requests Merged or Rejected?](https://arxiv.org/abs/2605.22534) - review interactions and PR outcome interpretation.
45. [AIDev: Studying AI Coding Agents on GitHub](https://arxiv.org/abs/2602.09185) - dataset of agent-authored PRs across major tools.
46. [Where Do AI Coding Agents Fail?](https://arxiv.org/abs/2601.15195) - failed agentic PR taxonomy.
47. [TechRadar on Antigravity security concerns](https://www.techradar.com/pro/googles-ai-powered-antigravity-ide-already-has-some-worrying-security-issues) - reported prompt-injection/exfiltration concerns.
48. [Reddit: Warp universal agent support AMA](https://www.reddit.com/r/warpdotdev/comments/1slf86f/we_just_launched_universal_agent_support_in_warp/) - community questions on vertical tabs, notifications, code review, agent abstractions.
49. [Reddit: terminal kanban for managing agents](https://www.reddit.com/r/VibeCodeDevs/comments/1s5xh5a/terminal_kanban_for_managing_multiple_ai_coding/) - community pattern for kanban + worktrees + tmux/agents.
50. [Reddit: Warp UI/pricing criticism](https://www.reddit.com/r/warpdotdev/comments/1r404b6/what_have_you_done_to_warp_terminal/) - sentiment on terminal-to-coding-app drift and clutter.

---

*Report generated using the deep-research-max workflow adapted to the available Codex tool surface: discovery, parallelized local context gathering, broad web research, contradiction analysis, and synthesis into a single cited markdown artifact.*
