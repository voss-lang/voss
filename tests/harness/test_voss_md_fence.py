"""M8-01 fence parser tests."""
from __future__ import annotations

import hashlib

import pytest

from voss.harness.voss_md import (
    Block,
    HashMismatch,
    parse,
    read_fence_body,
    write_fence_body,
)


def _fence(fence_id: str, body: str, *, recorded_hash: str | None = None) -> str:
    """Compose a single fenced block for fixture text."""
    h = recorded_hash if recorded_hash is not None else hashlib.sha256(body.encode()).hexdigest()
    if body and not body.endswith("\n"):
        body = body + "\n"
    return (
        f"<!-- voss:begin id={fence_id} -->\n"
        f"<!-- voss:hash {h} -->\n"
        f"{body}"
        f"<!-- voss:end id={fence_id} -->\n"
    )


class TestParse:
    def test_parse_human_blocks(self) -> None:
        text = "# Project Guide\n\nUse tabs.\n"
        blocks = parse(text)
        assert blocks == [Block(kind="human", id=None, body=text, recorded_hash=None)]

    def test_parse_machine_blocks(self) -> None:
        prefix = "# Project Guide\n\nHuman intro.\n"
        body = "## Architecture\n\nDetails go here.\n"
        text = prefix + _fence("architecture", body)
        blocks = parse(text)
        kinds = [b.kind for b in blocks]
        assert "machine" in kinds
        machine = next(b for b in blocks if b.kind == "machine")
        assert machine.id == "architecture"
        assert machine.body == body
        assert machine.recorded_hash == hashlib.sha256(body.encode()).hexdigest()
        # Human prefix preserved verbatim.
        human = next(b for b in blocks if b.kind == "human")
        assert human.body == prefix


class TestHashGuard:
    def test_hash_mismatch_raises(self, tmp_path) -> None:
        body_on_disk = "X"
        wrong_hash = hashlib.sha256(b"Y").hexdigest()
        path = tmp_path / "VOSS.md"
        path.write_text(_fence("architecture", body_on_disk, recorded_hash=wrong_hash))

        with pytest.raises(HashMismatch) as excinfo:
            read_fence_body(path, fence_id="architecture")

        err = excinfo.value
        assert err.fence_id == "architecture"
        assert err.recorded == wrong_hash
        assert err.actual == hashlib.sha256(b"X\n").hexdigest() or err.actual == hashlib.sha256(b"X").hexdigest()
        # `on_disk` is exactly the parsed body bytes — whatever the parser saw.
        assert err.on_disk in ("X", "X\n")


class TestWriteRoundTrip:
    def test_write_fence_body_round_trip(self, tmp_path) -> None:
        path = tmp_path / "VOSS.md"
        human_prose = "# Project Guide\n\nKeep this paragraph intact.\n\n"
        original_body = "original\n"
        path.write_text(human_prose + _fence("architecture", original_body))

        write_fence_body(path, fence_id="architecture", body="updated\n")

        after = path.read_text()
        assert human_prose in after, "human paragraph must survive write_fence_body"

        read_back = read_fence_body(path, fence_id="architecture")
        assert read_back == "updated\n"

        blocks = parse(after)
        machine = next(b for b in blocks if b.kind == "machine" and b.id == "architecture")
        assert machine.recorded_hash == hashlib.sha256(b"updated\n").hexdigest()
