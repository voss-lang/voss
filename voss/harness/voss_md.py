"""VOSS.md file-format owner: parse fenced blocks, inject into system context, migrate legacy architecture.md.

D-05: VOSS.md is a single markdown file with human prose interleaved with
machine fences marked by `<!-- voss:begin id=<id> -->` / `<!-- voss:end id=<id> -->`
and a `<!-- voss:hash <sha256> -->` integrity header.

D-07: Machine writes refuse when the recorded hash drifts from the on-disk
body's sha256 (HashMismatch). Drift resolution lives in `voss memory adopt`.

D-08: `read_and_inject(cwd) -> str | None` returns the verbatim bytes of
cwd/VOSS.md, or None when absent. Absence degrades silently — no log, no
exception.

M8-01 implements parse / read_and_inject / read_fence_body / write_fence_body /
machine_fence_path_or_marker + HashMismatch. M8-02 fills `ensure_migrated`.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


FENCE_BEGIN = re.compile(r"<!-- voss:begin id=([\w-]+) -->")
FENCE_HASH = re.compile(r"<!-- voss:hash ([0-9a-f]{64}) -->")
FENCE_END = re.compile(r"<!-- voss:end id=([\w-]+) -->")


@dataclass(frozen=True)
class Block:
    kind: str
    id: str | None
    body: str
    recorded_hash: str | None


class HashMismatch(Exception):
    def __init__(self, fence_id: str, *, recorded: str, actual: str, on_disk: str) -> None:
        super().__init__(
            f"VOSS.md fence id={fence_id} hash mismatch: "
            f"recorded={recorded[:16]}, actual={actual[:16]}"
        )
        self.fence_id = fence_id
        self.recorded = recorded
        self.actual = actual
        self.on_disk = on_disk

    def __str__(self) -> str:
        return (
            f"VOSS.md fence id={self.fence_id} hash mismatch: "
            f"recorded={self.recorded[:16]}, actual={self.actual[:16]}"
        )


def parse(text: str) -> list[Block]:
    """Split VOSS.md text into a list of human + machine Blocks (D-05).

    Line-by-line scan. Human runs accumulate between fences. Machine fences
    capture id and the optional `<!-- voss:hash ... -->` header that follows
    the begin marker.
    """
    blocks: list[Block] = []
    lines = text.splitlines(keepends=True)
    i = 0
    n = len(lines)
    while i < n:
        m_begin = FENCE_BEGIN.match(lines[i].strip())
        if not m_begin:
            start = i
            while i < n and not FENCE_BEGIN.match(lines[i].strip()):
                i += 1
            human_body = "".join(lines[start:i])
            if human_body:
                blocks.append(Block(kind="human", id=None, body=human_body, recorded_hash=None))
            continue

        fence_id = m_begin.group(1)
        recorded: str | None = None
        body_start = i + 1
        if body_start < n:
            m_hash = FENCE_HASH.match(lines[body_start].strip())
            if m_hash:
                recorded = m_hash.group(1)
                body_start += 1

        j = body_start
        while j < n:
            m_end = FENCE_END.match(lines[j].strip())
            if m_end and m_end.group(1) == fence_id:
                break
            j += 1

        body = "".join(lines[body_start:j])
        blocks.append(Block(kind="machine", id=fence_id, body=body, recorded_hash=recorded))
        i = j + 1
    return blocks


def read_and_inject(cwd: Path) -> str | None:
    """Return verbatim VOSS.md bytes for D-08 system-context injection.

    Returns None when the file is absent or unreadable. Never raises (Req 1
    silent degradation).
    """
    path = cwd / "VOSS.md"
    if not path.exists():
        return None
    try:
        return path.read_text()
    except (OSError, UnicodeDecodeError):
        return None


def ensure_migrated(cwd: Path) -> bool:
    """Idempotent migration of .voss/architecture.md into VOSS.md id=architecture fence.

    Contract (D-06 + Req 2):
      - Idempotent: if cwd/VOSS.md already exists, return False without
        touching any file. Second-run safety.
      - Byte-identical archive: hashlib.sha256(archive bytes) ==
        hashlib.sha256(pre-migration architecture.md bytes). Asserted before
        the source file is unlinked; mismatch raises RuntimeError so the
        original file survives.
      - Verbatim fence body: the architecture.md frontmatter + body lands at
        the head of the id=architecture fence body, so cognition.FRONTMATTER_RE
        still matches without modification.
    """
    from . import cognition  # local import; cognition imports from voss_md

    voss_md_path = cwd / "VOSS.md"
    if voss_md_path.exists():
        return False

    arch_path = cognition.voss_dir(cwd) / "architecture.md"
    if not arch_path.exists():
        return False

    arch_bytes = arch_path.read_bytes()
    arch_sha = hashlib.sha256(arch_bytes).hexdigest()

    archive_dir = cognition.voss_dir(cwd) / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_path = archive_dir / f"architecture-{today}.md"
    suffix = 2
    while archive_path.exists():
        archive_path = archive_dir / f"architecture-{today}-{suffix}.md"
        suffix += 1

    archive_path.write_bytes(arch_bytes)
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != arch_sha:
        raise RuntimeError(
            f"VOSS.md migration archive sha256 mismatch at {archive_path}; "
            "original architecture.md left intact"
        )

    try:
        fence_body = arch_bytes.decode("utf-8")
    except UnicodeDecodeError:
        fence_body = arch_bytes.decode("utf-8", errors="replace")
        print(
            f"warning: {arch_path} contained non-UTF-8 bytes; "
            "migrated with replacement characters",
            file=sys.stderr,
        )

    write_fence_body(voss_md_path, fence_id="architecture", body=fence_body)
    arch_path.unlink()
    return True


def read_fence_body(path: Path, *, fence_id: str) -> str | None:
    """Return fence body text; raises HashMismatch when recorded != computed sha256 (D-07).

    Returns None when the fence id is absent from the file (or the file
    itself is missing). Raises HashMismatch on integrity failure.
    """
    if not path.exists():
        return None
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return None

    for block in parse(text):
        if block.kind != "machine" or block.id != fence_id:
            continue
        if block.recorded_hash is not None:
            actual = hashlib.sha256(block.body.encode()).hexdigest()
            if actual != block.recorded_hash:
                raise HashMismatch(
                    fence_id,
                    recorded=block.recorded_hash,
                    actual=actual,
                    on_disk=block.body,
                )
        return block.body
    return None


def write_fence_body(path: Path, *, fence_id: str, body: str) -> None:
    """Write body into id=<fence_id>; recompute hash; preserve human content.

    Atomic: writes to <path>.tmp then os.replace into place.
    Raises HashMismatch when the existing fence on disk fails its hash gate
    (D-07): caller must `voss memory adopt --id <fence_id>` to reset baseline.
    Appends a new fully-formed fence at EOF when fence id is absent.
    """
    existing_text = ""
    if path.exists():
        try:
            existing_text = path.read_text()
        except (OSError, UnicodeDecodeError):
            existing_text = ""

    blocks = parse(existing_text)
    new_hash = hashlib.sha256(body.encode()).hexdigest()
    new_machine_block = Block(
        kind="machine", id=fence_id, body=body, recorded_hash=new_hash
    )

    replaced = False
    new_blocks: list[Block] = []
    for block in blocks:
        if block.kind == "machine" and block.id == fence_id:
            if block.recorded_hash is not None:
                actual = hashlib.sha256(block.body.encode()).hexdigest()
                if actual != block.recorded_hash:
                    raise HashMismatch(
                        fence_id,
                        recorded=block.recorded_hash,
                        actual=actual,
                        on_disk=block.body,
                    )
            new_blocks.append(new_machine_block)
            replaced = True
        else:
            new_blocks.append(block)

    if not replaced:
        if new_blocks and not new_blocks[-1].body.endswith("\n"):
            tail = new_blocks[-1]
            new_blocks[-1] = Block(
                kind=tail.kind,
                id=tail.id,
                body=tail.body + "\n",
                recorded_hash=tail.recorded_hash,
            )
        new_blocks.append(new_machine_block)

    rendered = _render(new_blocks)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(rendered)
    os.replace(tmp, path)


def machine_fence_path_or_marker(cwd: Path, *, fence_id: str) -> Path:
    """Return the VOSS.md path consumed by fence writers (used by analyze.py via M8-05)."""
    return cwd / "VOSS.md"


def _render(blocks: list[Block]) -> str:
    """Serialize a list of Blocks back to VOSS.md source text."""
    parts: list[str] = []
    for block in blocks:
        if block.kind == "human":
            parts.append(block.body)
            continue
        body = block.body
        if body and not body.endswith("\n"):
            body += "\n"
        hash_header = block.recorded_hash or hashlib.sha256(block.body.encode()).hexdigest()
        parts.append(
            f"<!-- voss:begin id={block.id} -->\n"
            f"<!-- voss:hash {hash_header} -->\n"
            f"{body}"
            f"<!-- voss:end id={block.id} -->\n"
        )
    return "".join(parts)
