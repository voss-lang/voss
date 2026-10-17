"""Content-addressed artifact store + append-only run log for one experiment."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .spec import RunRecord


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.objects = root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.runs = root / "runs.jsonl"

    @property
    def experiment_id(self) -> str:
        return self.root.name

    def put(self, data: str | bytes) -> str:
        raw = data.encode() if isinstance(data, str) else data
        sha = hashlib.sha256(raw).hexdigest()
        path = self.objects / sha
        if not path.exists():
            path.write_bytes(raw)
        return sha

    def get(self, sha: str) -> bytes:
        return (self.objects / sha).read_bytes()

    def append(self, record: RunRecord) -> None:
        with self.runs.open("a") as f:
            f.write(record.model_dump_json() + "\n")

    def write_manifest(self, manifest: dict) -> None:
        (self.root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def read_runs(root: Path) -> list[RunRecord]:
    path = root / "runs.jsonl" if root.is_dir() else root
    return [RunRecord.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]
