"""RED tests for SKILL-02 (Skill Registry and Adapter)."""
from __future__ import annotations

from pathlib import Path
import pytest


def test_voss_skill_dispatch(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-02: Installed skill translates to a SkillHandler and registers with default_skill_registry."""
    try:
        from voss.harness.skill.scope import ScopeSpec
        from voss.harness.skill.adapter import make_voss_skill_handler
        from voss.harness.skill_registry import default_skill_registry, SkillEntry
    except ImportError as e:
        pytest.fail(f"RED: missing adapter or registry module ({e})")

    voss_path = signed_fixture_bundle / "git_summary.voss"
    spec = ScopeSpec(tools="read-only", fs="cwd", net=False)

    # Adapt `.voss` program into a SkillHandler
    handler = make_voss_skill_handler(voss_path, spec)
    assert callable(handler)

    # Register in default registry
    registry = default_skill_registry()
    entry = SkillEntry(
        id="voss-git-summary",
        description="Summarize git tree",
        handler=handler,
        mutating=False,
    )
    registry.register(entry)

    # Get from registry
    resolved = registry.get("voss-git-summary")
    assert resolved is not None
    assert resolved.id == "voss-git-summary"
    assert resolved.mutating is False

    # Execute handler (dispatch)
    # The handler expects (agent/context, args)
    # We pass mock agent/context and empty args
    class MockAgent:
        def __init__(self):
            self.actions = []
        def log(self, msg):
            self.actions.append(msg)

    agent = MockAgent()
    resolved.handler(agent, [])


def test_unknown_skill_not_found() -> None:
    """SKILL-02: Querying an unknown or uninstalled skill ID returns None."""
    try:
        from voss.harness.skill_registry import default_skill_registry
    except ImportError as e:
        pytest.fail(f"RED: missing registry module ({e})")

    registry = default_skill_registry()
    assert registry.get("non-existent-skill-id-12345") is None
