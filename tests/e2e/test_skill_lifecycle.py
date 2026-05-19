"""RED E2E test for SKILL-06 (comprehensive skill lifecycle)."""
from __future__ import annotations

from pathlib import Path
import pytest
from click.testing import CliRunner


def test_fixture_bundle_e2e() -> None:
    """SKILL-06: End-to-end flow: trust key -> add -> list -> run -> update -> remove -> list."""
    try:
        from voss.cli import main as voss_main
        from voss.harness.trust import pin_key
    except ImportError as e:
        pytest.fail(f"RED: missing cli or trust module ({e})")

    runner = CliRunner()
    bundle_path = Path("/Users/benjaminmarks/Projects/Voss/examples/skills/voss-git-summary")

    # 1. Read manifest to get public key and pin it
    import tomllib
    manifest_data = tomllib.loads((bundle_path / "manifest.toml").read_text())
    pub_key_b64 = manifest_data["trust"]["pub_key"]
    author = manifest_data["author_identity"]

    # Trust the fixture key
    pin_key(author, pub_key_b64)

    # 2. Add the skill
    add_result = runner.invoke(voss_main, ["skill", "add", str(bundle_path)])
    assert add_result.exit_code == 0

    # 3. List skills and verify it is shown
    list_result = runner.invoke(voss_main, ["skill", "list"])
    assert list_result.exit_code == 0
    assert "voss-git-summary" in list_result.output

    # 4. Run the skill and verify the output
    # `voss skill run voss-git-summary`
    run_result = runner.invoke(voss_main, ["skill", "run", "voss-git-summary"])
    assert run_result.exit_code == 0
    # The output should contain git summary details
    assert "git" in run_result.output.lower()

    # 5. Update the skill (against same valid path or an updated one)
    update_result = runner.invoke(voss_main, ["skill", "update", "voss-git-summary"])
    assert update_result.exit_code == 0

    # 6. Remove the skill
    remove_result = runner.invoke(voss_main, ["skill", "remove", "voss-git-summary"])
    assert remove_result.exit_code == 0

    # 7. List skills again and verify it is gone
    final_list_result = runner.invoke(voss_main, ["skill", "list"])
    assert final_list_result.exit_code == 0
    assert "voss-git-summary" not in final_list_result.output
