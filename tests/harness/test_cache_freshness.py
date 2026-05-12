from __future__ import annotations

import hashlib
import json

import pytest

from voss.exceptions import VossError
from voss.harness import cache
from voss.harness.diagnostics import StaleHarnessCacheError
from voss.harness.sandbox import SandboxError, write_cache


def _write_loop(project_root, text: str = "let x = 1\n"):
    source_dir = project_root / "voss" / "harness" / "agent"
    source_dir.mkdir(parents=True)
    (source_dir / "loop.voss").write_text(text)


def test_assert_fresh_passes_after_compile(tmp_path):
    _write_loop(tmp_path)
    entries = cache.compute_source_shas(tmp_path)
    cache.write_manifest(tmp_path, entries)

    cache.assert_fresh(tmp_path)


def test_stale_cache_raises_on_source_change(tmp_path):
    _write_loop(tmp_path)
    entries = cache.compute_source_shas(tmp_path)
    cache.write_manifest(tmp_path, entries)
    (tmp_path / "voss" / "harness" / "agent" / "loop.voss").write_text("let x = 2\n")

    with pytest.raises(StaleHarnessCacheError) as exc_info:
        cache.assert_fresh(tmp_path)
    assert "voss compile voss/harness/agent/" in str(exc_info.value)


def test_missing_manifest_raises(tmp_path):
    _write_loop(tmp_path)

    with pytest.raises(StaleHarnessCacheError) as exc_info:
        cache.assert_fresh(tmp_path)
    assert "voss compile voss/harness/agent/" in str(exc_info.value)


def test_version_mismatch_raises(tmp_path):
    _write_loop(tmp_path)
    entries = cache.compute_source_shas(tmp_path)
    manifest = cache.write_manifest(tmp_path, entries)
    data = json.loads(manifest.read_text())
    data["voss_version"] = "0.0.0-stale"
    manifest.write_text(json.dumps(data))

    with pytest.raises(StaleHarnessCacheError):
        cache.assert_fresh(tmp_path)


def test_stale_harness_cache_error_subclasses_voss_error():
    assert issubclass(StaleHarnessCacheError, VossError)


def test_sha256_text():
    assert cache.sha256_text("foo") == hashlib.sha256(b"foo").hexdigest()


def test_write_cache_writes_under_voss_cache(tmp_path):
    target = write_cache(tmp_path, "harness/loop.py", "content")

    assert target == tmp_path / ".voss-cache" / "harness" / "loop.py"
    assert target.read_text() == "content"


def test_write_cache_rejects_escape(tmp_path):
    with pytest.raises(SandboxError):
        write_cache(tmp_path, "../escape.txt", "content")
