"""Sealed answers for locked sets: hidden tests and the reference patch, encrypted at rest."""
from __future__ import annotations

import getpass
import io
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SEALED = "answers.enc"
ANSWERS = ("hidden", "reference.patch")
OPENSSL = ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "stdin"]
_key: str | None = None


class SealError(Exception):
    pass


def key(*, confirm: bool = False) -> str:
    """Typed in once per process. Never put in an env var or file: other processes of the same user can read both."""
    global _key
    if _key is None:
        typed = getpass.getpass("key for sealed answers: ")
        if confirm and getpass.getpass("same key again: ") != typed:
            raise SealError("the two keys differ")
        _key = typed
    return _key


def _openssl(args: list[str], data: bytes) -> bytes:
    p = subprocess.run([*OPENSSL, *args], input=key().encode() + b"\n" + data, capture_output=True)
    if p.returncode:
        raise SealError(f"openssl failed (wrong key?): {p.stderr.decode(errors='replace')[:200]}")
    return p.stdout


def seal(task_dir: Path) -> Path:
    """Encrypt hidden/ and reference.patch into answers.enc, check it opens, then remove the plaintext."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name in ANSWERS:
            tar.add(task_dir / name, arcname=name)
    out = task_dir / SEALED
    out.write_bytes(_openssl(["-salt"], buf.getvalue()))
    with answers(task_dir) as opened:
        for name in ANSWERS:
            if not (opened / name).exists():
                raise SealError(f"{out}: {name} missing after decrypting")
    shutil.rmtree(task_dir / "hidden")
    (task_dir / "reference.patch").unlink()
    return out


@contextmanager
def answers(task_dir: Path) -> Iterator[Path]:
    """The directory that holds hidden/ and reference.patch: the scenario itself, or a decrypted temp copy."""
    if not (task_dir / SEALED).exists():
        yield task_dir
        return
    with tempfile.TemporaryDirectory(prefix="proofs-answers-") as tmp:
        plain = _openssl(["-d"], (task_dir / SEALED).read_bytes())
        with tarfile.open(fileobj=io.BytesIO(plain), mode="r:gz") as tar:
            tar.extractall(tmp, filter="data")
        yield Path(tmp)
