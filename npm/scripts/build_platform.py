#!/usr/bin/env python3
"""Build one platform's vendored Python tree for the npm wrapper.

Steps (per RESEARCH §3-§5):
  1. Build (or accept) the voss wheel.
  2. Download the pinned PBS tarball for <triple>.
  3. Verify sha256 against npm/scripts/pbs_manifest.json (or capture+log
     if the manifest's slot is PENDING).
  4. Extract; confirm the expected interpreter exists.
  5. Run prune_pbs.py to trim stdlib bloat.
  6. pip-install the voss wheel into the vendored interpreter (no
     --target / --prefix — RESEARCH §5).
  7. Measure site-packages size, print SITE_PACKAGES_SIZE_MB=<N>, and
     gate on SIZE_BUDGET_MB. SIZE_BUDGET_MB = 300 is the hard cap from
     RESEARCH §5 Risk 2 — published npm tarballs above this are
     considered unusable for first-install UX.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "npm" / "scripts" / "pbs_manifest.json"
PRUNE_SCRIPT = ROOT / "npm" / "scripts" / "prune_pbs.py"
SIZE_BUDGET_MB = 300

PLATFORMS = ["darwin-arm64", "darwin-x64", "linux-x64", "linux-arm64", "win32-x64"]


def load_manifest() -> dict:
    with MANIFEST.open("r", encoding="utf-8") as f:
        return json.load(f)


def download_pbs(triple: str, manifest: dict, dest: Path) -> Path:
    pbs_triple = manifest["triples"][triple]["pbs_triple"]
    url = manifest["url_template"].format(
        pbs_release=manifest["pbs_release"],
        python_version=manifest["python_version"],
        pbs_triple=pbs_triple,
    )
    out = dest / "pbs.tar.gz"
    total = 0
    print(f"Downloading {url}")
    with urllib.request.urlopen(url) as resp, out.open("wb") as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
    print(f"Downloaded {url} -> {total} bytes")
    return out


def verify_sha256(tarball: Path, expected: str) -> str:
    h = hashlib.sha256()
    with tarball.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    digest = h.hexdigest()
    if expected == "PENDING":
        print(f"SHA256({tarball.name})={digest}")
        print(
            f"Update pbs_manifest.json for this triple with this digest, then commit."
        )
        return digest
    if digest != expected:
        sys.stderr.write(
            f"sha256 mismatch for {tarball.name}\n  expected: {expected}\n  actual:   {digest}\n"
        )
        sys.exit(2)
    print(f"sha256 OK: {digest}")
    return digest


def extract_pbs(tarball: Path, dest: Path) -> Path:
    with tarfile.open(tarball, "r:gz") as t:
        t.extractall(dest)
    extract_root = dest / "python"
    unix_py = extract_root / "bin" / "python3"
    win_py = extract_root / "python.exe"
    if not (unix_py.exists() or win_py.exists()):
        sys.stderr.write(
            f"extract_pbs: no python interpreter found under {extract_root}\n"
        )
        sys.exit(2)
    return extract_root


def run_prune(extract_root: Path) -> None:
    subprocess.run(
        [sys.executable, str(PRUNE_SCRIPT), str(extract_root.parent)],
        check=True,
        timeout=120,
    )


def install_wheel(extract_root: Path, wheel: Path) -> None:
    is_windows = (extract_root / "python.exe").exists()
    python_bin = (
        extract_root / "python.exe" if is_windows else extract_root / "bin/python3"
    )
    if not is_windows:
        os.chmod(python_bin, 0o755)
    print(f"Installing wheel {wheel.name} into {python_bin}")
    subprocess.run(
        [str(python_bin), "-m", "pip", "install", "--no-cache-dir", str(wheel)],
        check=True,
        timeout=900,
    )


def measure_site_packages(extract_root: Path) -> int:
    is_windows = (extract_root / "python.exe").exists()
    if is_windows:
        sp = extract_root / "Lib" / "site-packages"
    else:
        sp = extract_root / "lib" / "python3.12" / "site-packages"
    if not sp.is_dir():
        sys.stderr.write(f"site-packages missing at {sp}\n")
        sys.exit(2)
    total = 0
    for p in sp.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def ensure_wheel(wheel_arg) -> Path:
    if wheel_arg is not None:
        wp = Path(wheel_arg)
        if wp.exists():
            return wp
        sys.stderr.write(f"--wheel path does not exist: {wp}\n")
        sys.exit(2)
    dist = ROOT / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    print(f"Building wheel into {dist}")
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(ROOT)],
        check=True,
        timeout=600,
    )
    wheels = sorted(dist.glob("voss-*.whl"))
    if len(wheels) != 1:
        sys.stderr.write(
            f"ensure_wheel: expected exactly one voss-*.whl in {dist}, found {len(wheels)}\n"
        )
        sys.exit(2)
    return wheels[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one platform's vendored Python tree.")
    parser.add_argument("triple", choices=PLATFORMS)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--wheel", default=None)
    parser.add_argument("--keep-tarball", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    wheel = ensure_wheel(args.wheel)

    started = time.time()
    with tempfile.TemporaryDirectory(prefix="voss-pbs-") as tmp_s:
        tmp = Path(tmp_s)
        tarball = download_pbs(args.triple, manifest, tmp)
        verify_sha256(tarball, manifest["triples"][args.triple]["sha256"])
        extract_root = extract_pbs(tarball, tmp)
        run_prune(extract_root)
        install_wheel(extract_root, wheel)
        size_bytes = measure_site_packages(extract_root)
        size_mb = size_bytes // (1024 * 1024)

        # Move into place atomically: remove dest if any, then rename.
        out = args.out.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            shutil.rmtree(out)
        shutil.move(str(extract_root), str(out))

        if args.keep_tarball:
            kept = out.parent / tarball.name
            shutil.copy(tarball, kept)
            print(f"Kept tarball at {kept}")

    elapsed = time.time() - started
    print(f"SITE_PACKAGES_SIZE_MB={size_mb}")
    print(f"build_platform: triple={args.triple} out={args.out} elapsed={elapsed:.1f}s")

    if size_mb > SIZE_BUDGET_MB:
        sys.stderr.write(
            f"SIZE_BUDGET_EXCEEDED budget={SIZE_BUDGET_MB} actual={size_mb}\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
