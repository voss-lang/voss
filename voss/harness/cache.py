from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from voss import __version__ as VOSS_VERSION

from .sandbox import write_cache

HARNESS_AGENT_DIR = "voss/harness/agent"
CACHE_HARNESS_DIR = ".voss-cache/harness"
MANIFEST_NAME = "_manifest.json"
MANIFEST_VERSION = 1
STALE_CACHE_MESSAGE = "compiled harness cache stale — run: voss compile voss/harness/agent/"


@dataclass(frozen=True)
class ManifestEntry:
    sha256: str
    lines: int


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_source_shas(project_root: Path) -> dict[str, ManifestEntry]:
    source_root = project_root / HARNESS_AGENT_DIR
    entries: dict[str, ManifestEntry] = {}
    for path in sorted(source_root.glob("*.voss")):
        text = path.read_text()
        entries[path.name] = ManifestEntry(
            sha256=sha256_text(text),
            lines=text.count("\n") + 1,
        )
    return entries


def write_manifest(project_root: Path, entries: dict[str, ManifestEntry]) -> Path:
    payload = {
        "version": MANIFEST_VERSION,
        "voss_version": VOSS_VERSION,
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            name: asdict(entry)
            for name, entry in sorted(entries.items())
        },
    }
    return write_cache(
        project_root,
        f"harness/{MANIFEST_NAME}",
        json.dumps(payload, indent=2) + "\n",
    )


def load_manifest(project_root: Path) -> dict | None:
    path = project_root / CACHE_HARNESS_DIR / MANIFEST_NAME
    if not path.exists():
        return None
    return json.loads(path.read_text())


def assert_fresh(project_root: Path) -> None:
    from .diagnostics import StaleHarnessCacheError

    manifest = load_manifest(project_root)
    if manifest is None:
        raise StaleHarnessCacheError(STALE_CACHE_MESSAGE)
    if manifest.get("version") != MANIFEST_VERSION:
        raise StaleHarnessCacheError(STALE_CACHE_MESSAGE)
    if manifest.get("voss_version") != VOSS_VERSION:
        raise StaleHarnessCacheError(STALE_CACHE_MESSAGE)

    expected = compute_source_shas(project_root)
    actual = manifest.get("sources")
    if not isinstance(actual, dict):
        raise StaleHarnessCacheError(STALE_CACHE_MESSAGE)
    expected_payload = {name: asdict(entry) for name, entry in sorted(expected.items())}
    if actual != expected_payload:
        raise StaleHarnessCacheError(STALE_CACHE_MESSAGE)
