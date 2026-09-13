# What the active Voss-ADE changes about the harness plan

2026-09-12. Source inspection and proposed priorities; no implementation or live application validation in this pass.

Follow-up option: [Laravel/PHP as a local retained-memory service](2026-09-12-laravel-local-memory-api.md). This evaluates a user-requested alternative to extending the Python memory API; it is not an approved architecture change.

## Correction and direction

The first research pass inspected `Voss/archive/voss-ade`, not the separate active `Voss-ADE` repository. The active ADE materially changes the delivery plan: there is already a canvas and a concrete client integration plan. Harness work should enable that experience.

Authoritative context:

- [ADE PLAN.md](Voss-ADE/PLAN.md:362): Sprints 11–15 cover the optional harness bridge, task composer/pane, Agents page, Review page, and context/memory.
- [HARNESS-INTEGRATION.md](Voss-ADE/docs/HARNESS-INTEGRATION.md:5): ADE is a client of the harness, never its own orchestrator. Ordinary terminals, messaging, workspaces, and basic worktree review should work without the harness.
- [ANALYSIS.md](Voss-ADE/ANALYSIS.md:3): explicitly superseded in part. Its older remote/HTTP/WebSocket architecture is not the current build guide.

Preserve the product decisions: local single-machine workflow; canvas as home; actual events behind status/graphs; context attached from existing notes/files; no prominent budget UI. Internal execution limits remain useful without becoming the product's centerpiece.

## What exists in the active ADE

| Area | Evidence and current boundary |
|---|---|
| Canvas and terminals | `web/src/`, `crates/core/src/terminals.rs`, `tmux.rs`, `discovery.rs`, and `store.rs` implement panes, PTYs, tmux reattachment, and persistence. PLAN records remaining manual gates; implementation does not equal full UX validation. |
| Agent awareness | `agents/hooks.rs`, `agents/mod.rs`, detection/scraping code, and `web/src/agent.js` implement hook-driven status with fallback detection. Live provider gates remain incomplete in PLAN. |
| Workspaces and revival | Workspace state and lost-pane/revive paths exist. `terminal_revive` recreates terminal state and can resume a CLI conversation. This is separate from recovering an interrupted harness task. |
| Messaging and identity | `agents/messaging.rs` implements workspace tags, a roster, queued delivery to busy agents, and `voss-msg` handling. SessionStart hook replies inject roster/usage context. “Delivered” currently means input injection succeeded, not that an agent acknowledged or completed the request. |
| Optional harness bridge | `crates/core/src/harness/mod.rs` implements lifecycle states, lazy SDK Supervisor startup, shutdown, and doctor. Tauri exposes availability/status/settings/doctor commands. Cargo feature isolation exists. |
| Event mapping | `harness/events.rs` maps SDK events to pane states. Search found its definition, but no call wiring `state_for` into a live event subscription in active ADE Rust code. |
| Task, review, memory surfaces | Sprints 12–15 describe them in detail. Inspected source lacks the planned `tasks.rs`, `review.rs`, `memory.rs`, task/context/review tables, and task/review/memory pages. Treat these as planned, not shipped. |

The integration document says the harness already supplies everything required. Source inspection shows useful primitives, but several required client contracts are still missing or incomplete.

## Harness improvements the ADE actually needs

### 1. “My task survives reconnecting the app”

**Observed:** [session events route](Voss/voss/harness/server/app.py:727) consumes one session queue. It emits no sequence/cursor for replay and cancels an active turn when the event generator is cancelled on disconnect. [ServerSession](Voss/voss/harness/server/sessions.py:22) uses an in-memory bounded queue. Multiple subscribers would consume from the same queue rather than each receiving the complete stream. The [SDK stream](Voss/crates/voss-sdk/src/stream.rs:17) parses event data without exposing a replay cursor.

ADE plans to persist received events in SQLite, reconstruct views, and reconnect after restart. A client-side log cannot recover an event it never received. ADE also shuts its Supervisor down on window destruction, so app quit and a temporary stream disconnect have different execution consequences.

**Improve:** Reuse existing durable event/session infrastructure to provide an ordered task journal, task snapshot, cursor-based replay, and independent subscribers. Make disconnect separate from explicit cancellation. Decide app-quit behavior explicitly: checkpoint/interruption and later resume fits the current app-owned Supervisor; uninterrupted background execution would require an intentional lifecycle change.

**Proof:** Disconnect a viewer mid-turn, reconnect, and recover each event in order without restarting the task or repeating a write. Two viewers agree. Restart after a checkpoint restores an honest interrupted state and a safe next action. Do not promise process-level continuation across a reboot.

### 2. “Every screen tells the same truth”

**Observed:** ADE's [event mapper](Voss-ADE/crates/core/src/harness/events.rs:5) maps every warning to failure and final/session-idle to idle. Harness warnings have only a message, while plan steps carry name/args rather than durable task-step lifecycle identities. Existing candidate-ready events do not affect this ADE state mapping. [UiProjection](Voss/crates/voss-sdk/src/projection.rs) omits swarm events from its supported projections.

**Improve:** Define authoritative task state and typed transitions for queued, running, waiting on input, ready for review, finished, failed, and abandoned. Keep worker activity distinct from task completion. Distinguish a recoverable warning from a failed task. Expose stable task/step/agent/artifact identities where the views require them; extend existing event contracts rather than reconstructing meaning from strings.

**Proof:** The graph, board, attention badge, and review queue project the same stored state. A warning does not falsely fail a task. An unintegrated candidate does not become “finished” merely because the worker exits.

### 3. “Start, steer, and approve exactly this task”

**Observed:** [CreateSessionBody](Voss/voss/harness/server/app.py:422) supports cwd/model/resume and identity fields, but not the planned attached-context IDs or allow/deny scope lists. Messages supply free-form mode; busy sessions reject new messages with 409. Permission replies do have request IDs and stale-response handling. Abort cancels the turn; it is not a checkpointed pause. SDK calls cover basic sessions/messages/permissions, not all composer/swarm/memory needs.

**Improve:** A validated task request with explicit scope, supported execution mode, context references, and effective model/policy returned to the client. Reuse request-specific permission handling and add discoverable pending actions after reconnect. Implement queued steering where wanted. Advertise only supported controls: disable Pause until resumable pause semantics exist. Add a small capability/version contract and matching typed SDK methods.

**Proof:** ADE's composer settings reach actual enforcement, unsupported settings fail visibly, stale approval cannot approve a different request, and a resumed task retains applicable constraints. Current user Git/model restrictions remain authoritative.

### 4. “Attach this note—and show whether it reached the agent”

**Observed:** SessionStart additional-context delivery already exists for ADE messaging information. General attachment delivery, context tables, and lens are planned. Harness [server turn assembly](Voss/voss/harness/server/app.py:339) injects project/code context but does not pass the CLI's pinned-memory block. The session API lacks the planned attachment surface. Swarm recall limits results to owned-file locators.

**Improve:** Bring CLI and server briefing assembly into parity using existing helpers. Expose the actual included items with source, revision, delivery/inclusion status, and truncation. Separate relevant reading from edit ownership. Distinguish attached, sent, and observed-in-context; a clipboard paste does not prove that a third-party agent read a file. Removing an attachment stops future inclusion, not knowledge already delivered.

**Proof:** Attach a note to a harness task and observe that precise version in the next turn's context manifest. A fresh CLI agent can receive approved attachments through its adapter. Failed/queued delivery is visible. The lens labels external-CLI visibility as partial rather than claiming to show its full internal context.

### 5. “Remember this once, find it wherever I work”

**Observed:** [GET /memory](Voss/voss/harness/server/app.py:779) returns a summary string and optional search hits. It is not a full editable memory inventory. Memory creation, pinning, and other operations already exist in Python store/CLI code. ADE proposes local fallback memory plus harness memory, with provenance back to panes/tasks.

**Improve:** Expose a bounded structured memory API over the existing store: selected-item creation, inspection/listing, search, pin/unpin, and forgetting. Preserve project scope and source provenance. Give ADE-created local entries stable identities so explicit promotion can avoid duplicates. Display actual project/global storage location; avoid assuming all content lives under `~/.voss`.

**Proof:** Explicitly save an approved note, retrieve it in a later task, and trace its origin. Promoting the same local item twice creates one retained entry. No automatic capture of terminal transcripts or sensitive records. Supersession/freshness from the original feature plan follows this basic usable path.

### 6. “Open the worker that is already doing the job”

**Observed:** ADE plans to spawn terminal panes on worker assignment. Harness [CLI runtime](Voss/voss/harness/swarm_runtime.py:64) already launches the worker process in its worktree. Assignment identity alone does not provide a PTY/tmux attachment handle. Launching again from the client risks duplicate workers. ADE messaging uses terminal injection; managed harness messaging belongs to the server.

**Improve:** Choose one execution owner per worker. Harness schedules/manages work; ADE either attaches to the existing managed terminal or explicitly supplies the terminal executor through a narrow contract. Return a usable process/terminal handle with worker identity. Adapt message delivery by worker type, preserving sender identity and acknowledgement status; keep existing standalone `voss-msg` useful.

**Proof:** One assignment creates exactly one process. Opening/closing its view never duplicates execution. Requests sent while a target is busy, awaiting permission, lost, or offline remain distinguishable and do not accidentally answer a permission prompt.

### 7. “Review the result with its evidence”

**Observed:** Voss has review sidecars, run validation, and immutable candidate metadata. ADE plans to combine CLI audit/review output with worktree diffs and a merge action. Its initial document conflates several approval surfaces that serve different purposes.

**Improve:** Expose a structured review bundle over existing records: candidate identity/base, changed files, actual checks and their results, and unresolved issues. Keep tool permission, reviewer approval, and explicit Git integration separate. Bind evidence to candidate/file state so new edits can invalidate it.

**Proof:** Review shows a real candidate and its checks. Changed code marks affected evidence stale. Reviewing cannot silently merge; the exact Git action remains subject to the user's explicit authorization.

## Revised delivery order

| Milestone | Smallest useful result | Aligns with |
|---|---|---|
| 1: task survives its view | One task with durable state, reconnect/replay, truthful status, explicit stop and recovery | ADE S11 and S12 before graph/timeline polish |
| 2: context is visible and usable | Shared briefing assembly, attach/inspect, selected-note memory creation/search | Pull a narrow vertical slice of S15 forward |
| 3: review is actionable | Candidate plus validation evidence and pending decisions | S13/S14 |
| 4: coordinated workers are dependable | Dependency readiness, single worker ownership, terminal attachment, message acknowledgements | S9/S12 integration |
| 5: continuity improves over time | Decision-preserving compression, memory supersession, outcome-based suggestions | Original feature plan, built on the above contracts |

The practical first demo is: start a task in ADE, attach a note, close and reconnect its view, answer its specific question, and inspect a real result with evidence. This establishes more harness value than an animated graph without reliable underlying task state.

No separate orchestration engine, memory backend, or always-on swarm is needed. Preserve the optional-harness boundary. Let ADE own canvas/terminal presentation and local fallback data; let the harness own managed execution, authoritative task events, policy enforcement, and managed memory.

## Verification limits

Read PLAN.md, HARNESS-INTEGRATION.md, relevant ANALYSIS.md status, ADE bridge/hooks/messaging/store/Tauri wiring, and Voss server/session/event/SDK/runtime code. Source searches identified absent integrations; these are bounded findings, not proof that no alternate path exists anywhere. No runtime tests were run during this follow-up; the earlier 13 passing tests do not cover these client integration gaps. Neither live session captures nor user credentials were opened. Only research documents in Voss were changed.
