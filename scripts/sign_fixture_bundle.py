#!/usr/bin/env python3
"""Author-side tool to sign the voss-git-summary fixture bundle manifest.

Generates the test Ed25519 keypair if absent, serialization is in raw 32-byte Base64.
Computes a detached Ed25519 signature over manifest.toml and writes it as hex to manifest.toml.sig.
"""
from __future__ import annotations

import base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def main() -> None:
    bundle_dir = Path(__file__).parent.parent / "examples" / "skills" / "voss-git-summary"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    priv_key_path = bundle_dir / "test_signing_key"
    pub_key_path = bundle_dir / "test_signing_key.pub"
    manifest_path = bundle_dir / "manifest.toml"
    sig_path = bundle_dir / "manifest.toml.sig"

    # 1. Generate or load keypair
    if not priv_key_path.exists() or not pub_key_path.exists():
        print("Generating new test keypair...")
        private_key = ed25519.Ed25519PrivateKey.generate()
        
        # Serialize raw private key to base64
        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        priv_key_path.write_text(base64.b64encode(priv_bytes).decode("utf-8").strip() + "\n")

        # Serialize raw public key to base64
        public_key = private_key.public_key()
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        pub_key_path.write_text(base64.b64encode(pub_bytes).decode("utf-8").strip() + "\n")
    else:
        print("Loading existing test keypair...")
        priv_bytes = base64.b64decode(priv_key_path.read_text().strip())
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)

    # 2. Write placeholder manifest if it doesn't exist yet to avoid FileNotFoundError
    if not manifest_path.exists():
        # Get public key base64 for manifest embedding
        public_key = private_key.public_key()
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        pub_key_b64 = base64.b64encode(pub_bytes).decode("utf-8").strip()

        manifest_content = f"""id = "voss-git-summary"
name = "Git Working Tree Summary"
description = "Summarizes the git status and diff in the current working directory"
version = "0.1.0"
author_identity = "voss-fixture@example.com"

[skill]
id = "voss-git-summary"
entry = "git_summary.voss"
mutating = false

[scopes]
tools = "read-only"
fs = "cwd"
net = false

[trust]
sig_file = "manifest.toml.sig"
pub_key = "{pub_key_b64}"

[install]
source_url = ""
installed_at = ""
"""
        manifest_path.write_text(manifest_content)

    # 3. Read manifest and sign
    manifest_bytes = manifest_path.read_bytes()
    signature = private_key.sign(manifest_bytes)
    
    # Detached signature stored as hex string
    sig_hex = signature.hex()
    sig_path.write_text(sig_hex.strip() + "\n")
    print(f"Manifest signed successfully. Signature saved to {sig_path.name}")


if __name__ == "__main__":
    main()
