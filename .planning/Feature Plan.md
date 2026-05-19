# Voss Feature Proposals (v1 Prioritized)

This document outlines proposed features for the Voss Harness and ADE, categorized by their priority for the **v1 (Layer 2 — Voss Substrate)** release.

## 🔴 MUST Ship (v1)

### 1. Durable Session Persistence
**Goal:** Ensure agent cells in the ADE resume correctly after app restarts or crashes.
- **Durable Agent Registry**: Track active cell states in `.voss/sessions.sqlite`.
- **Rust Supervisor**: The ADE core automatically restarts `voss` subprocesses for active sessions on boot.

### 2. Hybrid Semantic Search
**Goal:** Improve retrieval accuracy by combining Keyword (BM25) and Vector search.
- **Reciprocal Rank Fusion**: Combine scores from ChromaDB and BM25 to rank results.
- **Symbol Accuracy**: Significantly improves the agent's ability to find exact function and class names.

### 3. Real-time Budget & Token Visualization
**Goal:** Make cost and token constraints visible in the cell HUD.
- **HUD Progress Indicators**: Circular or linear progress bars showing token usage vs. budget limits.
- **Live Cost Updates**: IPC events that update the status bar cost meter per token.

## 🟡 SHOULD Ship (v1)

### 4. Visual Context Heatmap
**Goal:** Transparency into what the agent has in its context window.
- **Context Pane**: A list in the ADE showing which files are currently "In Context" and which have been compressed or summarized.
- **Pinning UI**: Allow users to manually pin files into the agent's context.

### 5. "Commit with Critique" Hook
**Goal:** Enforce project constraints and quality standards at the point of commit.
- **Git Integration**: A `pre-commit` hook that invokes a Voss agent to critique diffs against `.voss/constraints.yml`.

### 8. Multi-Model Agent Council
**Goal:** Enable a panel of agents from different LLM providers to deliberate on architectural decisions and converge on consensus.
- **CLI-Native Execution**: Spawn council members as standard agent cells using locally-authenticated CLIs (Claude Code, Codex, Antigravity, OpenCode, etc.) — same config as terminal agents, no separate API key management.
- **Council Protocol**: Feed identical prompt/context to each council member, collect responses, then run a structured debate round where each critiques the others' proposals.
- **Consensus Engine**: Score and rank proposals via voting, critique weighting, or a designated "judge" agent. Surface the winning recommendation with full reasoning trail.
- **Use Cases**: Architecture decisions, plan review, code review tiebreakers, implementation strategy selection.

## 🔵 DEFER to v2 (Layer 3)

### 6. General Layout Wiring DSL
- **Flexible Data Flow**: Move general inter-pane event wiring via `.voss` DSL to Layer 3.
- **v1 Focus**: Use hardcoded patterns (e.g., Reviewer-as-Pair-Programmer) for the initial release.

### 7. Auto-Skill Registry
- **Dynamic Discovery**: Magic scanning of project functions to generate tools is a quality-of-life improvement for later.
- **v1 Standard**: Stick to explicit `@tool` annotation for clarity and safety.
