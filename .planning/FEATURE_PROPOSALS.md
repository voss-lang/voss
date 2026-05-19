# Voss Feature Proposals

This document outlines proposed features for the Voss Harness and ADE (Agent Development Environment) to enhance multi-agent coordination, developer experience, and semantic intelligence.

## 1. Voss Harness: Durable Multi-Agent Coordination

**Goal:** Allow agents to run in the background as long-lived entities that persist across CLI sessions.

- **Durable Agent Registry**: A new storage layer in `.voss/agents.json` to track running background agents.
- **`voss bg` command**: Spawn an agent that detaches from the current terminal but continues to run (useful for long-running research or refactoring).
- **Persistent Agent Handles**: Update `subagents.py` to support "restoring" an agent handle from a persistent ID.
- **`voss subagents list/kill`**: CLI commands to manage background agents.

## 2. Voss Harness: "Commit with Critique" Hook

**Goal:** Enforce project constraints and quality standards at the point of commit.

- **`voss hook install`**: Installs a `.git/hooks/pre-commit` script that calls `voss critique-commit`.
- **`voss critique-commit` command**:
    - Analyzes the staged diff.
    - Compares against `.voss/constraints.yml`.
    - Invokes a "Reviewer" agent to provide feedback.
    - Block or warn based on agent confidence and constraint violations.

## 3. Voss ADE: Agent-Native Layout Presets & Wiring

**Goal:** Make the grid layout semantically aware of agent relationships.

- **Semantic Wiring (L3)**: Add "Semantic Wiring" to Layer 3 specifications.
- **Layout Wiring DSL**: Add syntax to `.voss` to define how data flows between panes.
    ```voss
    layout "TDD" {
      pane "tests"  { loop: "watcher.voss", on: "file_change" }
      pane "code"   { loop: "main.voss",    receives: "tests.failures" }
      pane "review" { loop: "reviewer.voss", watches: "code" }
    }
    ```
- **Visual Flow Indicators**: Subtle UI animations in the ADE showing data "moving" between panes when an event triggers a dependent cell.

## 4. Voss ADE: Visual Context & Budget Visualizer

**Goal:** Transparency in agent "thinking" and cost management.

- **Context Heatmap**: A UI component that shows which parts of the codebase the agent is currently "looking at" or has in its context window.
- **IPC Context Snapshots**: Add support for rendering "Context Snapshot" events to the IPC stream.
- **Real-time Budget Progress**: A circular progress bar in the cell HUD showing token usage vs. budget limit.

## 5. Semantic Intelligence: Hybrid Search & Auto-Skill Registry

**Goal:** Improve tool-calling and code retrieval accuracy.

- **Hybrid Search**: Integrate BM25 search alongside Vector search for `memory.semantic`.
- **`voss skill scan`**: Command to scan a project for functions with docstrings and automatically generate a `skills.json` or `.voss` tool definitions.
