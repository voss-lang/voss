"""Hermetic CLI coverage for the checked-in voss-demos programs."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from tests.examples.helpers import (
    SUPPORT_FAKE_INDEX_SITECUSTOMIZE,
    deterministic_subprocess_env,
    run_cmd,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEMOS_ROOT = REPO_ROOT / "voss-demos"
DEMO_SOURCES = tuple(sorted(DEMOS_ROOT.glob("*.voss")))
assert DEMO_SOURCES, "expected voss-demos/*.voss fixtures"


FAKE_SEMANTIC_MEMORY_SITECUSTOMIZE = """
import voss_runtime as _voss_runtime
import voss_runtime.memory as _voss_memory
import builtins as _builtins


class _FakeSemanticMemory:
    def __init__(self, source=None, model=None, collection_name="voss_semantic", persist_dir="chroma"):
        self.source = source
        self.model = model
        self.collection_name = collection_name
        self.persist_dir = persist_dir

    def add(self, text, *, metadata=None, id=None):
        return None

    def retrieve(self, query, *, top_k=5):
        return [
            "Voss makes confidence, context budgets, tools, and memory explicit."
        ][:top_k]


_voss_runtime.SemanticMemory = _FakeSemanticMemory
_voss_memory.SemanticMemory = _FakeSemanticMemory
_builtins.kb = _FakeSemanticMemory(source="./voss-demos/knowledge")
"""


def _run_voss(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float = 120.0,
):
    return run_cmd(
        [sys.executable, "-m", "voss.cli", *args],
        cwd=cwd,
        env=env,
        timeout=timeout,
    )


@pytest.mark.parametrize(
    "source",
    [pytest.param(path, id=path.stem) for path in DEMO_SOURCES],
)
def test_voss_demo_check_and_run_are_hermetic(tmp_path: Path, source: Path):
    repo_cache_before = set((REPO_ROOT / ".voss-cache").glob("*.idx"))
    demo_source = tmp_path / source.name
    shutil.copyfile(source, demo_source)

    env = deterministic_subprocess_env(
        tmp_path,
        default_response="stub response",
        extra_sitecustomize=(
            SUPPORT_FAKE_INDEX_SITECUSTOMIZE
            + "\n"
            + FAKE_SEMANTIC_MEMORY_SITECUSTOMIZE
        ),
    )
    cache_dir = tmp_path / ".voss-cache"

    check_result = _run_voss(
        ["check", str(demo_source), "--cache-dir", str(cache_dir)],
        cwd=tmp_path,
        env=env,
    )
    assert check_result.returncode == 0, check_result.stderr
    assert "Traceback" not in check_result.stderr

    run_result = _run_voss(
        ["run", str(demo_source), "--cache-dir", str(cache_dir)],
        cwd=tmp_path,
        env=env,
    )
    assert run_result.returncode == 0, run_result.stderr
    assert "Traceback" not in run_result.stderr
    assert run_result.stdout.strip() != ""
    assert set((REPO_ROOT / ".voss-cache").glob("*.idx")) == repo_cache_before
