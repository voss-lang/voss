"""Install, remove, and update skill bundles with staging-verify-copy discipline."""
from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

from voss.harness.plugins import set_plugin_enabled, user_plugin_dir
from voss.harness.skill.fetch import fetch_bundle
from voss.harness.skill.scope import scope_spec_from_manifest
from voss.harness.trust import is_key_trusted, key_fingerprint, pin_key, verify_manifest


class SkillTrustError(Exception):
    """Raised when a bundle fails trust or signature verification."""


def _staging_root() -> Path:
    """Same-filesystem staging dir (Pitfall 3: atomic rename)."""
    return user_plugin_dir().parent / "._staging"


def _read_bundle_manifest(bundle_dir: Path) -> dict:
    manifest_path = bundle_dir / "manifest.toml"
    if not manifest_path.exists():
        raise SkillTrustError(f"no manifest.toml in bundle: {bundle_dir}")
    return tomllib.loads(manifest_path.read_text())


def _jail_path(base: Path, target: Path) -> None:
    """Reject paths that escape the base directory (T-M15-04-05)."""
    try:
        target.resolve().relative_to(base.resolve())
    except ValueError:
        raise SkillTrustError(f"path traversal rejected: {target}") from None


def install_bundle(
    source: str,
    *,
    cwd: Path,
    allow_tofu: bool = False,
) -> str:
    """Fetch, verify, and install a skill bundle.

    Returns the skill_id on success.
    Raises ``SkillTrustError`` if the key is untrusted or signature fails.
    """
    staging_root = _staging_root()
    staging_root.mkdir(parents=True, exist_ok=True)
    staging = staging_root / "pending"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    try:
        bundle_dir = fetch_bundle(source, staging)
        raw = _read_bundle_manifest(bundle_dir)

        # Extract trust fields
        trust_tbl = raw.get("trust", {})
        if not isinstance(trust_tbl, dict):
            trust_tbl = {}
        pub_key_b64 = str(trust_tbl.get("pub_key", "")).strip()
        sig_file = str(trust_tbl.get("sig_file", "manifest.toml.sig"))
        author = str(raw.get("author_identity", "")).strip()

        if not pub_key_b64:
            raise SkillTrustError("bundle manifest missing [trust].pub_key")

        # Trust gate: is key trusted?
        if not is_key_trusted(pub_key_b64):
            if allow_tofu and author:
                fp = key_fingerprint(pub_key_b64)
                pin_key(author, pub_key_b64, tofu=True)
            else:
                fp = key_fingerprint(pub_key_b64)
                raise SkillTrustError(
                    f"untrusted key (fingerprint: {fp[:16]}...). "
                    f"Run: voss skill trust {pub_key_b64}"
                )

        # Verify signature — nothing copied until this passes (Pitfall 1)
        manifest_path = bundle_dir / "manifest.toml"
        sig_path = bundle_dir / sig_file
        ok, reason = verify_manifest(manifest_path, sig_path, pub_key_b64=pub_key_b64)
        if not ok:
            raise SkillTrustError(f"signature verification failed: {reason}")

        # Validate scopes parse
        scope_spec_from_manifest(raw)

        # Resolve skill_id
        skill_tbl = raw.get("skill", {})
        if not isinstance(skill_tbl, dict):
            skill_tbl = {}
        skill_id = str(skill_tbl.get("id", raw.get("id", ""))).strip()
        if not skill_id:
            raise SkillTrustError("bundle manifest missing skill id")

        # Path traversal check on all bundle entries
        for child in bundle_dir.rglob("*"):
            _jail_path(bundle_dir, child)

        # Copy to install dir (ONLY after verify passes)
        install_dir = user_plugin_dir() / skill_id
        if install_dir.exists():
            shutil.rmtree(install_dir)
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundle_dir, install_dir)

        # Write install metadata back into installed manifest
        _write_install_metadata(install_dir / "manifest.toml", source)

        set_plugin_enabled(skill_id, True)
        return skill_id
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def remove_bundle(skill_id: str, *, cwd: Path) -> None:
    """Remove an installed skill bundle."""
    install_dir = user_plugin_dir() / skill_id
    if install_dir.exists():
        shutil.rmtree(install_dir)
    set_plugin_enabled(skill_id, False)


def update_bundle(skill_id: str, *, cwd: Path) -> None:
    """Re-fetch and re-verify an installed bundle.

    On verification failure, the prior install is left completely intact.
    On success, atomic swap via rename (same filesystem — Pitfall 3).
    """
    install_dir = user_plugin_dir() / skill_id
    if not install_dir.exists():
        raise SkillTrustError(f"skill not installed: {skill_id}")

    # Read stored source_url from installed manifest
    raw = _read_bundle_manifest(install_dir)
    install_tbl = raw.get("install", {})
    if not isinstance(install_tbl, dict):
        install_tbl = {}
    source_url = str(install_tbl.get("source_url", "")).strip()
    if not source_url:
        raise SkillTrustError(f"no source_url stored for {skill_id}; cannot update")

    staging_root = _staging_root()
    staging_root.mkdir(parents=True, exist_ok=True)
    staging = staging_root / "update"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    try:
        bundle_dir = fetch_bundle(source_url, staging)
        new_raw = _read_bundle_manifest(bundle_dir)

        # Re-verify trust gate
        trust_tbl = new_raw.get("trust", {})
        if not isinstance(trust_tbl, dict):
            trust_tbl = {}
        pub_key_b64 = str(trust_tbl.get("pub_key", "")).strip()
        sig_file = str(trust_tbl.get("sig_file", "manifest.toml.sig"))

        if not pub_key_b64:
            raise SkillTrustError("updated bundle missing [trust].pub_key")
        if not is_key_trusted(pub_key_b64):
            raise SkillTrustError(f"untrusted key in updated bundle for {skill_id}")

        manifest_path = bundle_dir / "manifest.toml"
        sig_path = bundle_dir / sig_file
        ok, reason = verify_manifest(manifest_path, sig_path, pub_key_b64=pub_key_b64)
        if not ok:
            raise SkillTrustError(f"update signature verification failed: {reason}")

        # Atomic swap: current→.bak, new→current, rm .bak
        bak_dir = install_dir.with_name(install_dir.name + ".bak")
        try:
            install_dir.rename(bak_dir)
            try:
                shutil.copytree(bundle_dir, install_dir)
                _write_install_metadata(install_dir / "manifest.toml", source_url)
            except OSError:
                # Restore from backup
                if bak_dir.exists():
                    if install_dir.exists():
                        shutil.rmtree(install_dir)
                    bak_dir.rename(install_dir)
                raise
            # Success — remove backup
            shutil.rmtree(bak_dir, ignore_errors=True)
        except OSError:
            # Restore from backup if swap failed
            if bak_dir.exists() and not install_dir.exists():
                bak_dir.rename(install_dir)
            raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def _write_install_metadata(manifest_path: Path, source_url: str) -> None:
    """Append [install] source_url to installed manifest if not present."""
    text = manifest_path.read_text()
    if "[install]" not in text:
        text += f"\n[install]\nsource_url = {source_url!r}\n"
        manifest_path.write_text(text)
    else:
        # Update existing source_url
        import re
        text = re.sub(
            r'(source_url\s*=\s*)(".*?"|\'.*?\'|[^\n]*)',
            f'\\1"{source_url}"',
            text,
        )
        manifest_path.write_text(text)
