"""Tests for SKILL-05 (lifecycle: remove, update, tamper protection)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import tomllib

from voss.harness.plugins import load_plugins, user_plugin_dir
from voss.harness.skill.install import (
    SkillTrustError,
    install_bundle,
    remove_bundle,
    update_bundle,
)
from voss.harness.trust import pin_key


def _install_fixture(signed_fixture_bundle: Path, tmp_path: Path) -> str:
    """Pin key and install the fixture bundle. Returns skill_id."""
    manifest_data = tomllib.loads((signed_fixture_bundle / "manifest.toml").read_text())
    pin_key(manifest_data["author_identity"], manifest_data["trust"]["pub_key"])
    return install_bundle(str(signed_fixture_bundle), cwd=tmp_path)


def test_remove(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-05: Removing an installed skill removes it from filesystem and discovery."""
    skill_id = _install_fixture(signed_fixture_bundle, tmp_path)
    install_dir = user_plugin_dir() / skill_id

    assert install_dir.is_dir()

    remove_bundle(skill_id, cwd=tmp_path)

    assert not install_dir.exists()
    # Not discoverable via load_plugins
    plugins = load_plugins(tmp_path)
    ids = [p.id for p in plugins]
    assert skill_id not in ids


def test_update_tamper_leaves_prior_intact(
    signed_fixture_bundle: Path, tmp_path: Path
) -> None:
    """SKILL-05: Tampered upstream update fails; prior version remains byte-intact."""
    skill_id = _install_fixture(signed_fixture_bundle, tmp_path)
    install_dir = user_plugin_dir() / skill_id

    # Snapshot prior version bytes
    prior_manifest = (install_dir / "manifest.toml").read_bytes()
    prior_sig = (install_dir / "manifest.toml.sig").read_bytes()

    # Create a tampered "upstream" that the update will fetch from
    tampered_upstream = tmp_path / "tampered_upstream"
    shutil.copytree(signed_fixture_bundle, tampered_upstream)
    # Tamper the manifest (breaks signature)
    m = tampered_upstream / "manifest.toml"
    m.write_text(m.read_text() + "\n# tampered byte")

    # Point the installed manifest's source_url at the tampered upstream
    installed_manifest = install_dir / "manifest.toml"
    text = installed_manifest.read_text()
    text = text.replace('source_url = ""', f'source_url = "{tampered_upstream}"')
    installed_manifest.write_text(text)

    # Update should fail due to tampered signature
    with pytest.raises(SkillTrustError):
        update_bundle(skill_id, cwd=tmp_path)

    # Prior version still intact and byte-identical (except source_url we set)
    assert install_dir.is_dir()
    assert (install_dir / "manifest.toml").exists()
    assert (install_dir / "manifest.toml.sig").read_bytes() == prior_sig
    # Manifest still loadable
    plugins = load_plugins(tmp_path)
    ids = [p.id for p in plugins]
    assert skill_id in ids
