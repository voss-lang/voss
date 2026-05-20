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

    # Tamper a byte INSIDE a TOML string value so the file still parses as
    # TOML — the verify path resolves author_identity from the manifest
    # before checking the signature, so a tamper that breaks TOML decoding
    # would short-circuit before reaching the Ed25519 check.
    tampered_manifest = tmp_path / "manifest.toml"
    content = manifest_path.read_bytes()
    assert b"Summarizes" in content, "fixture manifest changed; update tamper marker"
    tampered_content = content.replace(b"Summarizes", b"summarizes", 1)
    assert tampered_content != content
    tampered_manifest.write_bytes(tampered_content)

    # Trust the REAL fixture public key (strip trailing whitespace from .pub file)
    # so verification reaches the Ed25519 path and fails on the tampered bytes,
    # not on malformed base64 in a placeholder key.
    pub_key_b64 = (signed_fixture_bundle / "test_signing_key.pub").read_text().strip()
    trusted_keys = {"voss-fixture@example.com": pub_key_b64}
    ok, err = verify_manifest(tampered_manifest, sig_path, trusted_keys=trusted_keys)
    assert not ok
    assert "signature" in err.lower(), err

    # Create a tampered bundle dir with the tampered manifest + original sig
    import shutil
    tampered_bundle = tmp_path / "tampered_bundle"
    shutil.copytree(signed_fixture_bundle, tampered_bundle)
    (tampered_bundle / "manifest.toml").write_bytes(tampered_content)

    # Pin key so we reach the signature check (not the trust check)
    from voss.harness.trust import pin_key
    pin_key("voss-fixture@example.com", pub_key_b64)

    from voss.harness.skill.install import install_bundle, SkillTrustError
    with pytest.raises(SkillTrustError, match="signature verification failed"):
        install_bundle(str(tampered_bundle), cwd=tmp_path)


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

    from voss.harness.skill.install import install_bundle
    skill_id = install_bundle(str(signed_fixture_bundle), cwd=tmp_path)
    assert skill_id == "voss-git-summary"
