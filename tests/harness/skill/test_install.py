"""Tests for SKILL-01 (install from local path + GitHub shorthand)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import tomllib

from voss.harness.plugins import load_plugins, user_plugin_dir
from voss.harness.skill.fetch import GITHUB_SHORTHAND, fetch_bundle
from voss.harness.skill.install import SkillTrustError, install_bundle
from voss.harness.trust import pin_key


def test_add_local(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-01: Installing a local skill bundle places it in user_plugin_dir and enables it."""
    # Trust the fixture key
    manifest_data = tomllib.loads((signed_fixture_bundle / "manifest.toml").read_text())
    pin_key(manifest_data["author_identity"], manifest_data["trust"]["pub_key"])

    skill_id = install_bundle(str(signed_fixture_bundle), cwd=tmp_path)

    assert skill_id == "voss-git-summary"

    # Bundle dir exists under user_plugin_dir
    installed = user_plugin_dir() / "voss-git-summary"
    assert installed.is_dir()
    assert (installed / "manifest.toml").exists()
    assert (installed / "manifest.toml.sig").exists()

    # Discoverable via load_plugins
    plugins = load_plugins(tmp_path)
    ids = [p.id for p in plugins]
    assert "voss-git-summary" in ids


def test_add_github(tmp_path: Path) -> None:
    """SKILL-01: GitHub shorthand is parsed and resolved to HTTPS clone URL."""
    # Verify shorthand regex matches valid owner/repo patterns
    assert GITHUB_SHORTHAND.match("voss-lang/voss-git-summary")
    assert GITHUB_SHORTHAND.match("owner/repo")
    assert GITHUB_SHORTHAND.match("a.b/c-d_e")
    assert not GITHUB_SHORTHAND.match("https://github.com/x/y")
    assert not GITHUB_SHORTHAND.match("owner/repo/extra")
    assert not GITHUB_SHORTHAND.match("/repo")

    # Mock git clone to verify the URL transformation without network
    staging = tmp_path / "staging"
    staging.mkdir()
    with patch("voss.harness.skill.fetch.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        bundle_dir = staging / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "manifest.toml").write_text('id = "test"')

        try:
            fetch_bundle("voss-lang/voss-git-summary", staging)
        except (RuntimeError, FileNotFoundError):
            pass

        # Verify git clone was called with the HTTPS URL
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "clone" in call_args
        assert "https://github.com/voss-lang/voss-git-summary.git" in call_args


def test_untrusted_key_refuses(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-01: Untrusted key with allow_tofu=False refuses; nothing written to plugin dir."""
    # Do NOT pin the key — install should refuse
    with pytest.raises(SkillTrustError, match="untrusted key"):
        install_bundle(str(signed_fixture_bundle), cwd=tmp_path, allow_tofu=False)

    # Nothing written
    assert not (user_plugin_dir() / "voss-git-summary").exists()


def test_tampered_manifest_refuses(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-01: Tampered manifest fails signature verification; nothing written."""
    manifest_data = tomllib.loads((signed_fixture_bundle / "manifest.toml").read_text())
    pin_key(manifest_data["author_identity"], manifest_data["trust"]["pub_key"])

    # Create tampered copy
    tampered = tmp_path / "tampered_bundle"
    import shutil
    shutil.copytree(signed_fixture_bundle, tampered)
    (tampered / "manifest.toml").write_text(
        (tampered / "manifest.toml").read_text() + "\n# tampered"
    )

    with pytest.raises(SkillTrustError, match="signature verification failed"):
        install_bundle(str(tampered), cwd=tmp_path)

    assert not (user_plugin_dir() / "voss-git-summary").exists()


def test_insecure_transport_rejected() -> None:
    """SKILL-01: git:// and http:// URLs are rejected."""
    staging = Path("/tmp/test-staging")
    with pytest.raises(ValueError, match="insecure transport"):
        fetch_bundle("git://example.com/repo.git", staging)
    with pytest.raises(ValueError, match="insecure transport"):
        fetch_bundle("http://example.com/repo.git", staging)
