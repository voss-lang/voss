"""R3 swarm agent axis — resolve a swarm `Role` to a concrete CLI argv.

Single server-side source of truth, mirroring the desktop app's catalog
(`apps/voss-app/src/agents/modelPrefs.ts`): the CLI binary equals the agent key,
the model is passed as `--model <value>`, the working dir as `--cwd <value>`, and
the task prompt as a trailing positional — exactly how the app's
`AgentLaunchModal.buildConfig` assembles argv, so a swarm member launched
headlessly and one launched from the GUI invoke the CLI identically.

Two special agents:
  * `voss`   — the native in-process `run_turn` loop (V25). No argv; the swarm
               runs it directly, not as a subprocess. This is the default so an
               unspecified roster stays backward compatible.
  * `custom` — `Role.command` tokenized via `shlex`; the operator owns the full
               invocation. Only the task prompt is appended (no model/cwd flags
               injected, since an arbitrary command may not accept them).

The returned argv is run by the host with `cwd` = the member's git worktree
(see SWARM-RECONCILIATION: worktree-per-member). This module is pure — no spawn,
no fs, no git — so it is trivially unit-testable and importable from both the
server routes and the worktree/host layers.
"""
from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path

from .swarm_store import Role

# The native loop key. A role with this agent is not a subprocess.
NATIVE = "voss"
CUSTOM = "custom"

# A model value meaning "unspecified" — fall through to the agent's default.
_UNSET_MODELS = {"", "default"}


@dataclass(frozen=True)
class AgentSpec:
    """How to invoke one catalog CLI. `binary == catalog key` by convention."""

    binary: str
    model_flag: str = "--model"
    default_model: str | None = None


# Mirrors MODEL_PRESETS in apps/voss-app/src/agents/modelPrefs.ts (binary == key).
# Only Claude has a known-safe default model alias; the others let the local CLI
# pick unless the role names a model explicitly.
AGENT_CATALOG: dict[str, AgentSpec] = {
    "claude": AgentSpec("claude", default_model="sonnet"),
    "codex": AgentSpec("codex"),
    "gemini": AgentSpec("gemini"),
    "opencode": AgentSpec("opencode"),
    "aider": AgentSpec("aider"),
}


class UnknownAgentError(ValueError):
    """A role names an agent that is neither native, custom, nor in the catalog."""


def is_native(role: Role) -> bool:
    """True if this role runs the in-process voss loop (no subprocess argv)."""
    return role.agent == NATIVE


def known_agents() -> list[str]:
    """All selectable agent ids (native + custom + catalog), for pickers/validation."""
    return [NATIVE, CUSTOM, *AGENT_CATALOG.keys()]


def _resolved_model(role: Role, spec: AgentSpec) -> str | None:
    if role.model not in _UNSET_MODELS:
        return role.model
    return spec.default_model


def resolve_agent_argv(role: Role, *, cwd: str | Path, task_text: str = "") -> list[str]:
    """Build the argv to launch `role` as a CLI member.

    Raises ValueError for native roles (they have no argv) and UnknownAgentError
    for an unrecognized catalog agent. `cwd` is the member's worktree path.
    """
    if is_native(role):
        raise ValueError(
            f"role {role.name!r} is native (agent={NATIVE!r}); run it in-process, "
            "it has no CLI argv"
        )

    if role.agent == CUSTOM:
        argv = shlex.split(role.command)
        if not argv:
            raise ValueError(f"role {role.name!r} agent={CUSTOM!r} has an empty command")
        # Operator owns the full invocation; only append the task prompt.
        if task_text:
            argv.append(task_text)
        return argv

    spec = AGENT_CATALOG.get(role.agent)
    if spec is None:
        raise UnknownAgentError(
            f"role {role.name!r} names unknown agent {role.agent!r}; "
            f"known: {', '.join(known_agents())}"
        )

    argv = [spec.binary]
    model = _resolved_model(role, spec)
    if model:
        argv += [spec.model_flag, model]
    argv += ["--cwd", str(cwd)]
    argv += list(role.args)
    if task_text:
        argv.append(task_text)
    return argv
