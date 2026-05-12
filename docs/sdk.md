# Voss SDK

Voss ships two embedding surfaces for Python applications: the **runtime
library** (`voss_runtime`) and the **harness library** (`voss.harness`).
Together they are the SDK.

There is no separate "SDK package" — the same wheel you install with
`pip install voss` (or `npm i -g voss` in M6) exposes both surfaces.

---

## Public API contract

Only the names exported in each package's `__all__` are covered by the
stability contract:

- `voss_runtime.__all__` — runtime primitives for compiled `.voss` programs
  and for Python apps embedding workflow control.
- `voss.harness.__all__` — agent loop, plan schema, permission gate, tool
  registry entry, and the CLI entry point.

Anything reached via a submodule path that is **not** re-exported through
those `__all__` lists is private. Examples of names you must NOT depend on:

```
voss_runtime.providers.litellm_provider   # private
voss_runtime.semantic._encoder            # private
voss.harness.agent._run_step_loop         # private
voss.harness.cli._chat_cmd                # private
voss.harness.session.SessionRecord        # private (subject to schema change)
voss.harness.cognition.*                  # private
```

If you find yourself reaching into a private path, file an issue — the right
fix is usually to promote the missing name into the public surface.

### Versioning

Voss follows semver, with one pre-1.0 carve-out:

| Version axis | Patch (0.1.0 → 0.1.1) | Minor (0.1.0 → 0.2.0) | Major (0.x → 1.0) |
|---|---|---|---|
| Public API behavior | Never broken | May break (pre-1.0) | May break |
| Public API shape (`__all__`) | Never broken | May break (pre-1.0) | May break |
| Private internals | May break | May break | May break |
| Wire formats (sessions, cache, `.voss/`) | Never broken | May break with a migration | May break with a migration |

Post-1.0 the second column tightens: minor releases will not break public
API behavior or shape. Until then, pin to an exact patch version if you
need a frozen surface (`voss==0.1.3`).

### Deprecation policy

Names will be marked with a deprecation warning for at least one full minor
release before removal. Pre-1.0 this is best-effort, not a hard guarantee.

---

## `voss_runtime` — runtime + embedding

Install: `pip install voss` (the wheel ships both `voss` and `voss_runtime`).

### Quick start

```python
import asyncio
from voss_runtime import (
    ContextScope,
    ProbableValue,
    StubProvider,
    configure,
    RuntimeConfig,
)

async def main():
    # Use the deterministic stub provider for tests / CI.
    configure(RuntimeConfig(default_model="__stub__"))

    async with ContextScope(token_budget=4_000) as ctx:
        result: ProbableValue[str] = await ctx.ask("Pick a color: red or blue")
        if result.confidence >= 0.7:
            print(result.value)
        else:
            print("unsure")

asyncio.run(main())
```

### Public surface

| Name | Purpose |
|---|---|
| `ProbableValue` | A value paired with a confidence score; the `probable<T>` runtime representation |
| `ContextScope` | Token-bounded scope (the `ctx(budget: N) { ... }` runtime) |
| `BudgetScope`, `current_budget`, `run_with_budget` | Lower-level budget primitives |
| `RuntimeConfig`, `configure`, `get_config`, `reset_config` | Runtime configuration |
| `ModelProvider`, `ProviderResponse`, `StubProvider` | Provider plug-in interface + the deterministic stub |
| `EpisodicMemory`, `SemanticMemory`, `WorkingMemory` | Memory primitives (`memory.episodic`, `memory.semantic`, `memory.working`) |
| `SemanticMatcher` | Backs the `match similar(...)` construct |
| `VossAgent`, `AgentHandle`, `gather` | Multi-agent primitives (`spawn` / `gather`) |
| `ToolDescriptor`, `tool` | `@tool` decorator + descriptor type |
| `VossRuntimeError`, `BudgetExceededError`, `ConfidenceTooLowError`, `ParseError`, `ProviderError` | Exception hierarchy |

### What `voss_runtime` is not

- Not a general async LLM SDK. The runtime is shaped around `.voss`
  language constructs. Use the provider classes directly if you want raw
  completions outside the language surface.
- Not a tool registry. Tool descriptors live here; the registry that wires
  them to a permission gate lives in `voss.harness`.

---

## `voss.harness` — agent loop + CLI embedding

Install: same `pip install voss`. Imports under `voss.harness`.

### Quick start — drive a turn programmatically

```python
import asyncio
from pathlib import Path

from voss.harness import (
    Plan,
    PermissionGate,
    ToolEntry,
    TurnResult,
    run_turn,
)
from voss.harness.render import NullRenderer  # private path; example only

async def main():
    tools: dict[str, ToolEntry] = {}  # populate with your tool descriptors
    permissions = PermissionGate(mode="plan")  # read-only tier

    result: TurnResult = await run_turn(
        task="summarize this repo",
        tools=tools,
        cwd=Path.cwd(),
        renderer=NullRenderer(),
        permissions=permissions,
        confidence_threshold=0.6,
        token_budget=60_000,
    )

    print(result.final)
    print(f"confidence={result.confidence} cost=${result.cost_usd:.4f}")

asyncio.run(main())
```

> Note: `NullRenderer` is a private name today. Promote-to-public is a known
> follow-up — until then, callers either pass a real `Renderer` or supply a
> minimal stub. See "Known gaps" below.

### Quick start — invoke the CLI from Python

```python
from voss.harness import main

# Equivalent to `voss do "summarize this repo"`.
main(["do", "summarize this repo"])
```

This is mostly useful for tests and meta-tooling. Production embeddings
should call `run_turn` directly to keep control of permissions, rendering,
and session writes.

### Public surface

| Name | Purpose |
|---|---|
| `run_turn` | Run one agent turn. Returns `TurnResult`. |
| `Plan`, `ToolCall` | Pydantic schema the planner returns. Stable. |
| `TurnResult` | Dataclass returned from `run_turn` (plan, confidence, final, tool_results, cost_usd). |
| `RunSemantics` | Closing-turn semantics from the privileged record_run call. |
| `PermissionGate` | Tier-mapped gate for tool calls (`plan`, `edit`, `auto`). |
| `ToolEntry` | Single entry in the tool registry. |
| `main` | CLI entry point — `voss = voss.cli:main` and `voss.harness.main` are the same callable. |

### Permission tiers (mirrors M1 D-05)

| Mode | Read-only tools | `fs_write`/`fs_edit` | `shell_run` |
|---|---|---|---|
| `plan` | ✓ | ✗ | ✗ |
| `edit` | ✓ | prompt per call | ✗ |
| `auto` | ✓ | prompt once per file, remember "always" | allowlisted, prompt on miss |

Tool descriptors carry `is_mutating: bool`. Anything mutating is gated.

---

## Known gaps (v0.1 → v0.2 candidates)

These are public-API-shaped holes today. Mention them when filing an issue
that bumps into a private path.

- **`Renderer` interface** is private. Embedding callers that want silent
  runs or custom rendering currently reach into `voss.harness.render` for a
  null renderer. A `NullRenderer` + a documented `Renderer` protocol should
  land in `voss.harness.__all__`.
- **`ToolEntry` construction helpers**. The class is public; the convenient
  builder for wrapping a Python callable as a tool descriptor lives in
  private code. A `tool_entry_from_callable(...)` factory belongs in the
  public surface.
- **Session record types** (`SessionRecord`, `RunRecord`) are private. If
  embedders need to introspect sessions, promote a read-only view type
  instead of exposing the on-disk schema directly.
- **Configuration via TOML.** Today you call `configure(RuntimeConfig(...))`.
  A `from_toml(path)` helper would let embedders share the harness config
  file at `~/.config/voss/config.toml`.

---

## Plugin authoring (informal in v0.1)

Voss has plug-in seams but no formal plug-in SDK yet:

- **Providers** — implement `voss_runtime.ModelProvider` and register via
  `voss_runtime.providers.register(...)` (currently a private call). For
  v0.1, in-tree providers (`anthropic`, `openai`, `__stub__`, litellm pass-
  through) are the supported set.
- **Tools** — define a `ToolEntry` and add it to the harness's tool registry
  before calling `run_turn`. There is no auto-discovery mechanism.

A formal plug-in SDK (entry-points, plug-in manifest, sandboxed loading)
lands when external authors arrive. Until then, fork or vendor.

---

## What is NOT an SDK in v0.1

- **TS/JS SDK.** M6 ships an npm wrapper around the Python CLI, not a Node
  library. A JS/TS SDK is a v0.2 candidate, gated on real demand from
  JS-side embedders.
- **HTTP/remote SDK.** Voss is local-first by design. No service, no client.
  Deferred with `TEAM-*` / `WEB-*` requirements.
- **`.voss` LSP / editor SDK.** Tree-sitter grammar (`EDIT-01`) and VS Code
  marketplace release (`EDIT-02`) are explicit post-v0.1 deferrals.

---

## Filing issues against the SDK

When the SDK doesn't do what you need, the fix is almost always one of:

1. **Promote a private name into `__all__`** — file an issue and link the
   private path you reached for.
2. **Add a missing helper** (renderer, factory, TOML loader) — file an
   issue with a minimal usage sketch.
3. **Document an undocumented behavior** — file an issue with the snippet
   that surprised you.

Avoid pinning to private paths and shipping. The contract above is explicit
about what we will and will not break — anything else is on you.
