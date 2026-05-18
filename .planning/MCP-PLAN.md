# Server-side MCP plan

This document sketches what it would mean for Voss to expose itself as an MCP
server. It is an explainer, not a locked phase spec.

## Status

Voss has two separate MCP directions:

1. **Client-side MCP**: Voss consumes external MCP servers. This is covered by
   T3 Network Surface. It lets Voss call tools from servers such as a
   filesystem MCP server.
2. **Server-side MCP**: Voss exposes its own harness capabilities to other MCP
   clients. This is the M12 bridge direction.

This document is about the second direction only: **Voss as an MCP server**.

## Why expose Voss as a server?

The useful thing Voss has is not just another file-editing tool. It has a
bounded harness model: repo context, project memory, permission modes, scoped
edits, session records, `.voss` checking, and eventually Voss-aware tools.

Server-side MCP would make those capabilities available to hosts like Claude
Desktop, Claude Code, Cursor, editor plugins, local automations, and future
Voss surfaces without each host reimplementing Voss's repo model.

The simplest product statement:

> Run `voss serve --mcp` inside a repo, attach it to an MCP client, and that
> client can ask Voss for scoped repo intelligence and safe harness actions.

## What MCP surface should Voss expose?

MCP servers can expose tools, resources, and prompts. Voss should use all
three, but with different risk profiles.

### Tools

Tools are callable operations. They are where permission gating matters most.

Read-only tools should be the first server-side surface:

| Tool | Purpose |
|---|---|
| `voss_repo_summary` | Return a concise summary of the current repo using Voss cognition files and lightweight source inspection. |
| `voss_context_pack` | Build a bounded context bundle for a task, with inspected files and rationale. |
| `voss_plan` | Produce a scoped implementation plan without editing files. |
| `voss_diff_summary` | Summarize the current git diff with risks and test suggestions. |
| `voss_check` | Run `.voss` checking on a file or directory. |
| `voss_compile` | Compile `.voss` files to Python artifacts when allowed by the mode. |
| `voss_memory_search` | Search project memory, decisions, sessions, and VOSS.md content. |
| `voss_session_list` | List resumable Voss sessions for the repo. |
| `voss_session_read` | Read a redacted session transcript or run record. |
| `voss_tool_catalog` | Return the active harness tool registry with mutability/network metadata. |

Mutating tools should come later and default off:

| Tool | Purpose |
|---|---|
| `voss_edit_proposal` | Ask Voss to produce a patch proposal for a scoped target, without applying it. |
| `voss_apply_patch` | Apply an approved patch through Voss's existing scoped edit and permission machinery. |
| `voss_memory_write_decision` | Record an explicit project decision into Voss memory. |
| `voss_eval_run` | Run a named eval suite and write results under `.voss/eval/`. |

The first server release should probably ship read-only tools plus patch
proposal. Direct mutation can wait until client approval flows are proven.

### Resources

Resources should expose durable Voss state as addressable context. They should
not perform work or mutate state.

Candidate URI shapes:

| Resource URI | Meaning |
|---|---|
| `voss://project/architecture` | Current architecture summary from `.voss/architecture.md` or VOSS.md. |
| `voss://project/constraints` | Project constraints and permission notes. |
| `voss://project/validation` | Known validation commands and test strategy. |
| `voss://project/roadmap` | Active Voss roadmap/phase context when present. |
| `voss://sessions` | Index of known sessions. |
| `voss://sessions/{session_id}` | Redacted session detail. |
| `voss://plans` | Index of saved plans. |
| `voss://plans/{plan_id}` | Saved plan detail. |
| `voss://memory/search?q=...` | Read-only project memory search. |

Resources are useful because clients can pull Voss context without asking a
model to "run a tool." They also make Voss easier to inspect from the MCP
Inspector.

### Prompts

Prompts should package Voss workflows as user-selected templates. They should
not secretly run the harness.

Candidate prompts:

| Prompt | Purpose |
|---|---|
| `voss-plan-bounded-change` | Guide a host model to ask Voss for a scoped plan before editing. |
| `voss-review-diff` | Review a git diff using Voss's code-review stance and project memory. |
| `voss-investigate-bug` | Gather context, reproduce, propose a minimal fix, and name verification. |
| `voss-generate-tests` | Build focused tests for a completed or planned change. |
| `voss-explain-project` | Generate onboarding context from Voss project cognition. |

Prompts are the right place to expose "how to use Voss well" without turning
that guidance into hidden autonomous behavior.

## Command shape

The local-first command should be:

```bash
voss serve --mcp --cwd .
```

Likely options:

```bash
voss serve --mcp \
  --cwd . \
  --mode plan \
  --scope . \
  --transport stdio
```

Defaults should be conservative:

| Option | Default | Reason |
|---|---|---|
| `--mode` | `plan` | Read-only server by default. |
| `--scope` | current repo root | Keep the path jail explicit. |
| `--transport` | `stdio` | Easiest local MCP integration and no port/auth surface. |
| `--allow-net` | false | Do not inherit network access from the host. |
| `--allow-mutation` | false | Mutating MCP tools require explicit opt-in. |

HTTP transport can be a later addition. A stdio server is enough for local
developer tools and avoids authentication, CORS, port binding, and multi-client
state problems in the first release.

## Permission model

Server-side MCP must reuse Voss's existing safety model instead of creating a
parallel one.

Core rules:

- Default server mode is `plan`.
- Every exported tool has explicit metadata: read-only, mutating, network, or
  privileged.
- Mutating tools are hidden or disabled unless the server starts with an
  explicit mutation opt-in.
- Even with mutation enabled, file writes still pass through scoped edit
  rules.
- Shell execution is not exposed in the first server release.
- Network-capable behavior stays behind the same `allow_net` gate used by the
  T3 client-side network surface.
- Session records and telemetry must redact secrets the same way normal Voss
  runs do.

MCP tool annotations should mirror Voss metadata:

| Voss metadata | MCP-facing meaning |
|---|---|
| `is_mutating=False` | Advertise as read-only. |
| `is_mutating=True` | Mark as destructive or mutation-capable. |
| `is_network=True` | Require server `allow_net`. |
| scoped edit target | Enforce through Voss `PermissionGate`, not MCP glue. |

The MCP server should never trust the host client to enforce these boundaries.
The server must enforce them before invoking harness internals.

## Architecture

The server should be a thin protocol adapter over the existing harness.

Proposed package shape:

```text
voss/harness/mcp_server/
  __init__.py
  server.py        # MCP server bootstrap and transport
  tools.py         # Tool definitions backed by harness operations
  resources.py     # voss:// resource registry
  prompts.py       # Prompt templates
  permissions.py   # MCP-facing policy adapter over PermissionGate
  schemas.py       # Pydantic request/response models for Voss tools
```

Reusable internals:

| Existing Voss piece | Server-side use |
|---|---|
| `PermissionGate` | Enforce mode and mutating tool policy. |
| `make_toolset` / `ToolEntry` | Source capability metadata and optionally wrap safe native tools. |
| `run_turn` | Back tools like `voss_plan` and `voss_edit_proposal`. |
| `RunRecorder` / sessions | Persist MCP-triggered work as normal Voss runs. |
| VOSS.md / cognition files | Back resources and context-pack tools. |
| `.voss` check/compile APIs | Back `voss_check` and `voss_compile`. |
| T3 lifecycle helpers | Reuse shutdown cleanup patterns. |

There should not be a second agent loop for MCP. The MCP adapter should call
the same harness functions the CLI uses, then format results for the protocol.

## Request flow

A typical read-only call:

```text
MCP client
  -> tools/call: voss_context_pack
  -> Voss MCP server
  -> validate args and cwd scope
  -> read VOSS.md + cognition + selected files
  -> record telemetry/session event
  -> return bounded context bundle
```

A future mutating call:

```text
MCP client
  -> tools/call: voss_apply_patch
  -> Voss MCP server
  -> check server mutation opt-in
  -> check path scope
  -> route through PermissionGate/edit scope
  -> apply patch or return denial envelope
  -> record session event
  -> return changed files + diff summary
```

## Configuration

Server configuration should live in normal Voss config, not a separate MCP-only
file.

Possible shape:

```toml
[mcp_server]
enabled = true
default_mode = "plan"
transport = "stdio"
allow_mutation = false
allow_net = false

[mcp_server.tools]
repo_summary = true
context_pack = true
plan = true
edit_proposal = true
apply_patch = false
eval_run = false
```

Project-level policy can still come from `.voss/permissions.yml`, especially
path scope and project-specific deny rules.

## What not to expose first

Avoid these in the first server release:

- Raw `shell_run`.
- Arbitrary file write.
- Unbounded repo read.
- Direct provider credential inspection.
- Long-running background jobs.
- HTTP transport.
- Multi-client session sharing.
- Remote/team access.

These are not impossible. They just add security and lifecycle complexity that
is separate from proving the bridge is useful.

## Phased implementation

### Phase 1: Read-only stdio server

Ship `voss serve --mcp --transport stdio` with:

- `initialize` / capability negotiation.
- Tool listing for read-only Voss tools.
- Resource listing and reads for project cognition.
- Prompt listing and prompt retrieval.
- MCP Inspector compatibility.
- No mutation, no shell, no network.

Success criteria:

- MCP Inspector connects and shows tools, resources, and prompts.
- `voss_repo_summary` returns useful context from a real repo.
- `voss_plan` produces a plan and writes a normal session record.
- All calls stay inside the configured cwd.

### Phase 2: Patch proposal

Add `voss_edit_proposal`:

- Accepts task, target path, and optional test path.
- Runs the harness in edit-planning mode.
- Returns a unified diff proposal.
- Does not apply changes.

Success criteria:

- Host clients can ask Voss for a patch and review it in their own UI.
- No repo file changes happen from this tool.

### Phase 3: Explicit mutation

Add mutation only when the server is started with an explicit opt-in:

```bash
voss serve --mcp --mode edit --allow-mutation --scope src/
```

Then expose `voss_apply_patch` and maybe `voss_memory_write_decision`.

Success criteria:

- Mutation is impossible without opt-in.
- Scoped edit tests prove writes outside scope fail.
- Session records capture the host, tool name, requested paths, and result.

### Phase 4: HTTP and multi-client, if needed

Only after stdio proves value:

- Add streamable HTTP transport.
- Add auth.
- Add per-client sessions.
- Add cancellation and long-running job handles.

This should be treated as a separate product decision, not a default part of
the local bridge.

## Open questions

- Should `voss_plan` call a live provider by default, or should server mode
  require an explicit provider selection?
- Should resources expose raw session transcripts or only summaries?
- Should prompts be generated from `.voss` skills once the skill marketplace
  exists?
- Should `voss_apply_patch` exist at all, or should Voss only ever return patch
  proposals over MCP?
- Should server-side MCP reuse the T3 client package name or stay separated as
  `mcp_server` to avoid mixing client and server responsibilities?

## Recommendation

Build the server-side MCP bridge as a local, stdio-only, read-only adapter
first. Expose Voss's strongest differentiator: bounded repo intelligence and
inspectable harness planning. Keep mutation as a later opt-in layer.

That shape makes MCP useful without turning Voss into a broad remote-control
surface for the filesystem or shell.
