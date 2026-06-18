"""R3 agent axis (SWARM-RECONCILIATION): Role.agent resolution to a CLI argv,
plus explicit-roster persistence/replay through the SwarmStore."""
from __future__ import annotations

import pytest

from voss.harness.swarm_agents import (
    AGENT_CATALOG,
    UnknownAgentError,
    is_native,
    known_agents,
    resolve_agent_argv,
)
from voss.harness.swarm_store import Role, SwarmStore


# -- resolver ---------------------------------------------------------------
def test_native_role_is_native_and_has_no_argv():
    r = Role(name="coordinator")  # default agent="voss"
    assert is_native(r)
    with pytest.raises(ValueError):
        resolve_agent_argv(r, cwd="/wt")


def test_catalog_agent_with_explicit_model():
    r = Role(name="b1", agent="codex", model="gpt-5.5")
    argv = resolve_agent_argv(r, cwd="/wt", task_text="do the thing")
    assert argv == ["codex", "--model", "gpt-5.5", "--cwd", "/wt", "do the thing"]


def test_catalog_agent_falls_through_to_default_model():
    # claude has a safe default alias; an unset model uses it.
    r = Role(name="b1", agent="claude", model="default")
    argv = resolve_agent_argv(r, cwd="/wt")
    assert argv == ["claude", "--model", "sonnet", "--cwd", "/wt"]


def test_catalog_agent_no_default_omits_model_flag():
    # opencode has no default; unset model => no --model flag at all.
    r = Role(name="b1", agent="opencode", model="")
    argv = resolve_agent_argv(r, cwd="/wt")
    assert argv == ["opencode", "--cwd", "/wt"]


def test_extra_args_appended_after_cwd_before_task():
    r = Role(name="b1", agent="aider", model="", args=["--yes-always"])
    argv = resolve_agent_argv(r, cwd="/wt", task_text="go")
    assert argv == ["aider", "--cwd", "/wt", "--yes-always", "go"]


def test_custom_agent_tokenizes_command_and_appends_task():
    r = Role(name="b1", agent="custom", command='mycli --flag "two words"')
    argv = resolve_agent_argv(r, cwd="/wt", task_text="task")
    assert argv == ["mycli", "--flag", "two words", "task"]


def test_custom_empty_command_raises():
    r = Role(name="b1", agent="custom", command="   ")
    with pytest.raises(ValueError):
        resolve_agent_argv(r, cwd="/wt")


def test_unknown_agent_raises():
    r = Role(name="b1", agent="not-a-real-agent")
    with pytest.raises(UnknownAgentError):
        resolve_agent_argv(r, cwd="/wt")


def test_known_agents_lists_native_custom_and_catalog():
    ka = known_agents()
    assert ka[0] == "voss" and "custom" in ka
    assert set(AGENT_CATALOG).issubset(ka)


# -- explicit roster persistence + replay -----------------------------------
def test_explicit_roster_persists_and_replays_agent_axis(tmp_path):
    store = SwarmStore(cwd=tmp_path)
    roster = [
        Role(name="coordinator", agent="voss", model="claude-opus-4-8"),
        Role(name="builder-1", agent="codex", model="gpt-5.5", args=["--fast"]),
        Role(name="reviewer", agent="custom", command="reviewbot --strict"),
    ]
    swarm = store.create(goal="g", cwd=str(tmp_path), roster=roster)

    # Live roster carries the axis.
    by_name = {r.name: r for r in swarm.roster}
    assert by_name["builder-1"].agent == "codex"
    assert by_name["builder-1"].args == ["--fast"]
    assert by_name["reviewer"].command == "reviewbot --strict"

    # Replayed purely from the event log reconstructs the same agent axis.
    replayed = {r.name: r for r in store.replay(swarm.id).roster}
    assert replayed["builder-1"].agent == "codex"
    assert replayed["builder-1"].model == "gpt-5.5"
    assert replayed["builder-1"].args == ["--fast"]
    assert replayed["reviewer"].agent == "custom"
    assert replayed["reviewer"].command == "reviewbot --strict"


def test_default_roster_is_all_native_backward_compat(tmp_path):
    store = SwarmStore(cwd=tmp_path)
    swarm = store.create(goal="g", cwd=str(tmp_path))  # no explicit roster
    assert all(is_native(r) for r in swarm.roster)
    assert [r.name for r in swarm.roster] == ["coordinator", "builder-1", "builder-2", "reviewer"]
