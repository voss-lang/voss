"""RED tests for SKILL-05 (lifecycle: remove, update, and tamper protection)."""
from __future__ import annotations

from pathlib import Path
import pytest


def test_remove(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-05: Removing an installed skill removes it from filesystem and registry."""
    try:
        from voss.harness.skill.install import install_bundle, remove_bundle
        from voss.harness.skill_registry import default_skill_registry
    except ImportError as e:
        pytest.fail(f"RED: missing install/lifecycle module ({e})")

    # Install first
    install_bundle(str(signed_fixture_bundle), cwd=tmp_path)

    registry = default_skill_registry()
    assert registry.get("voss-git-summary") is not None

    # Remove
    remove_bundle("voss-git-summary", cwd=tmp_path)

    # Registry and listing should now omit it
    assert registry.get("voss-git-summary") is None


def test_update_tamper_leaves_prior_intact(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-05: If an update package has a tampered manifest, the update fails and the prior version remains untouched."""
    try:
        from voss.harness.skill.install import install_bundle, update_bundle
        from voss.harness.skill_registry import default_skill_registry
        from voss.harness.trust import verify_manifest
    except ImportError as e:
        pytest.fail(f"RED: missing install/lifecycle or trust module ({e})")

    # Install original valid version
    install_bundle(str(signed_fixture_bundle), cwd=tmp_path)

    registry = default_skill_registry()
    original_entry = registry.get("voss-git-summary")
    assert original_entry is not None

    # Prepare a tampered update bundle
    tampered_dir = tmp_path / "tampered_update"
    tampered_dir.mkdir()
    # Copy manifest and program
    manifest_path = tampered_dir / "manifest.toml"
    sig_path = tampered_dir / "manifest.toml.sig"
    manifest_path.write_text((signed_fixture_bundle / "manifest.toml").read_text())
    sig_path.write_text((signed_fixture_bundle / "manifest.toml.sig").read_text())
    (tampered_dir / "git_summary.voss").write_text((signed_fixture_bundle / "git_summary.voss").read_text())

    # Tamper the update manifest
    manifest_path.write_text(manifest_path.read_text() + "\n# tampered byte")

    # Trying to update should raise an error due to signature verification failure
    with pytest.raises(Exception):
        update_bundle("voss-git-summary", cwd=tmp_path)

    # Confirm the original intact version is still registered and active
    current_entry = registry.get("voss-git-summary")
    assert current_entry is not None
    assert current_entry == original_entry
