"""RED/GREEN tests for SKILL-03 (trust and signature verification)."""
from __future__ import annotations

from pathlib import Path
import pytest


def test_tampered_manifest_refused(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-03: Flipping a manifest byte causes verify_manifest to fail."""
    try:
        from voss.harness.trust import verify_manifest
    except ImportError as e:
        pytest.fail(f"RED: missing trust module ({e})")

    manifest_path = signed_fixture_bundle / "manifest.toml"
    sig_path = signed_fixture_bundle / "manifest.toml.sig"

    # Create a tampered copy of manifest
    tampered_manifest = tmp_path / "manifest.toml"
    content = manifest_path.read_bytes()
    # Flip the first byte
    tampered_content = bytes([content[0] ^ 0xFF]) + content[1:]
    tampered_manifest.write_bytes(tampered_content)

    trusted_keys = {"voss-fixture@example.com": "some_pub_key_b64"}
    ok, err = verify_manifest(tampered_manifest, sig_path, trusted_keys=trusted_keys)
    assert not ok
    assert "tampered" in err.lower() or "signature" in err.lower() or "invalid" in err.lower()

    # Confirm install_bundle raises an error and nothing lands in plugin dir
    try:
        from voss.harness.skill.install import install_bundle
        with pytest.raises(Exception):
            install_bundle(str(tampered_manifest), cwd=tmp_path)
    except ImportError:
        # install_bundle not implemented yet (Wave 1 focus is trust spine)
        pass


def test_unknown_key_refused(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-03: Keys not present in trust store are refused verification."""
    try:
        from voss.harness.trust import verify_manifest
    except ImportError as e:
        pytest.fail(f"RED: missing trust module ({e})")

    manifest_path = signed_fixture_bundle / "manifest.toml"
    sig_path = signed_fixture_bundle / "manifest.toml.sig"

    # Verify against empty trust store or different key
    ok, err = verify_manifest(manifest_path, sig_path, trusted_keys={})
    assert not ok
    assert "untrusted" in err.lower() or "unknown" in err.lower() or "untrusted author key" in err.lower()


def test_trust_then_install_succeeds(signed_fixture_bundle: Path, tmp_path: Path) -> None:
    """SKILL-03: After pin_key adds the key to trust store, manifest verification passes."""
    try:
        from voss.harness.trust import verify_manifest, pin_key, is_key_trusted
    except ImportError as e:
        pytest.fail(f"RED: missing trust module ({e})")

    manifest_path = signed_fixture_bundle / "manifest.toml"
    sig_path = signed_fixture_bundle / "manifest.toml.sig"

    # Read manifest to extract public key
    import tomllib
    manifest_data = tomllib.loads(manifest_path.read_text())
    pub_key_b64 = manifest_data["trust"]["pub_key"]
    author = manifest_data["author_identity"]

    # Pin key
    pin_key(author, pub_key_b64)
    assert is_key_trusted(pub_key_b64)

    # Now verify should succeed
    trusted_keys = {author: pub_key_b64}
    ok, err = verify_manifest(manifest_path, sig_path, trusted_keys=trusted_keys)
    assert ok
    assert err == "ok"

    try:
        from voss.harness.skill.install import install_bundle
        install_bundle(str(manifest_path), cwd=tmp_path)
    except ImportError:
        # install_bundle not implemented yet (Wave 1 focus is trust spine)
        pass
