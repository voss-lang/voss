"""Signature-trust verification and pinned-key trust store implementation."""
from __future__ import annotations

import base64
import datetime
import hashlib
import os
import tomllib
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
import portalocker

try:
    import tomli_w
except Exception:  # noqa: BLE001
    tomli_w = None  # type: ignore[assignment]


def trust_store_path() -> Path:
    """Resolve trusted_keys.toml path under XDG_CONFIG_HOME or fallback."""
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "trusted_keys.toml"


def load_trusted_keys() -> dict[str, dict]:
    """Load trusted keys from the trust store TOML file.
    
    Returns:
        Dict mapping author identity to public_key, pinned_at, tofu dict.
        Missing or corrupt files safely return {} (never raise).
    """
    path = trust_store_path()
    if not path.exists():
        return {}
    try:
        text = path.read_text()
        raw = tomllib.loads(text)
        keys = raw.get("keys", {})
        if not isinstance(keys, dict):
            return {}
        out: dict[str, dict] = {}
        for ident, val in keys.items():
            if isinstance(val, dict):
                out[str(ident)] = {
                    "public_key": str(val.get("public_key", "")),
                    "pinned_at": str(val.get("pinned_at", "")),
                    "tofu": bool(val.get("tofu", False)),
                }
        return out
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def is_key_trusted(pub_key_b64: str) -> bool:
    """Check if the given base64 public key is currently trusted in the store."""
    keys = load_trusted_keys()
    for entry in keys.values():
        if entry.get("public_key") == pub_key_b64:
            return True
    return False


def key_fingerprint(pub_key_b64: str) -> str:
    """Compute sha256 hex fingerprint of raw decoded public key bytes."""
    raw_bytes = base64.b64decode(pub_key_b64)
    return hashlib.sha256(raw_bytes).hexdigest()


def pin_key(identity: str, pub_key_b64: str, *, tofu: bool = False) -> Path:
    """Validate and write key to trusted_keys.toml under portalocker exclusive lock.
    
    Locks the file exclusively, reads, modifies, writes back, and sets chmod 0600.
    
    Returns:
        Path to the trust store file.
    """
    try:
        raw_bytes = base64.b64decode(pub_key_b64)
        if len(raw_bytes) != 32:
            raise ValueError("invalid public key length")
        ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)
    except Exception as e:
        raise ValueError(f"invalid public key: {e}") from e

    path = trust_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with portalocker.Lock(path, mode="a+", flags=portalocker.LOCK_EX) as fh:
        fh.seek(0)
        content = fh.read()
        
        keys = {}
        if content.strip():
            try:
                raw = tomllib.loads(content)
                keys = raw.get("keys", {})
            except Exception:
                keys = {}

        pinned_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        keys[identity] = {
            "public_key": pub_key_b64,
            "pinned_at": pinned_at,
            "tofu": tofu,
        }

        payload = {"keys": keys}
        if tomli_w is not None:
            text = tomli_w.dumps(payload)
        else:
            lines: list[str] = []
            for k, v in sorted(payload["keys"].items()):
                escaped_k = k.replace('"', '\\"')
                lines.append(f'[keys."{escaped_k}"]')
                lines.append(f'public_key = "{v["public_key"]}"')
                lines.append(f'pinned_at = "{v["pinned_at"]}"')
                lines.append(f"tofu = {'true' if v['tofu'] else 'false'}")
                lines.append("")
            text = "\n".join(lines)

        fh.seek(0)
        fh.truncate(0)
        fh.write(text)
        fh.flush()

    path.chmod(0o600)
    return path


def verify_manifest(
    manifest_path: Path,
    sig_path: Path,
    *,
    pub_key_b64: str | None = None,
    trusted_keys: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Verify manifest signature against the public key.
    
    Returns:
        (True, "ok") if signature is verified.
        (False, "<reason>") on verification failure or format errors.
        NEVER raises exceptions.
    """
    try:
        if not manifest_path.exists():
            return False, f"manifest file not found: {manifest_path.name}"

        if pub_key_b64 is None:
            try:
                manifest_data = tomllib.loads(manifest_path.read_text())
                author = manifest_data.get("author_identity")
            except Exception as e:
                return False, f"malformed manifest toml: {e}"

            if not author:
                return False, "missing author_identity in manifest"

            if trusted_keys is None:
                trusted_keys_store = load_trusted_keys()
                if author in trusted_keys_store:
                    pub_key_b64 = trusted_keys_store[author]["public_key"]
                else:
                    return False, f"untrusted author key for: {author}"
            else:
                if author in trusted_keys:
                    pub_key_b64 = trusted_keys[author]
                else:
                    return False, f"untrusted author key: {author}"

        raw_pub_bytes = base64.b64decode(pub_key_b64)
        if len(raw_pub_bytes) != 32:
            return False, "invalid public key length"
        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub_bytes)

        if not sig_path.exists():
            return False, f"signature file not found: {sig_path.name}"
        sig_hex = sig_path.read_text().strip()
        sig_bytes = bytes.fromhex(sig_hex)

        manifest_bytes = manifest_path.read_bytes()

        pub_key.verify(sig_bytes, manifest_bytes)
        return True, "ok"
    except InvalidSignature:
        return False, "signature invalid"
    except Exception as e:
        return False, str(e)
