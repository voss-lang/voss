from __future__ import annotations

from pathlib import Path

import pytest

from tests.examples.helpers import deterministic_subprocess_env


DEMO_SITECUSTOMIZE = """
import numpy as _np
import voss.analyzer as _voss_analyzer
import voss_runtime as _voss_runtime
import voss_runtime.memory as _voss_memory
import voss_runtime.semantic as _voss_semantic


class _DemoFakeIndexBuilder:
    model = "fake-embedding-model"

    def build_cases(self, cases):
        embeds = [[1.0, 0.0], [0.0, 1.0]]
        return [
            {"label": label, "description": desc, "embedding": embeds[i]}
            for i, (desc, label) in enumerate(cases)
        ]


_voss_analyzer.SemanticMatcherIndexBuilder = _DemoFakeIndexBuilder


def _demo_fake_encode(self, texts):
    out = []
    for text in texts:
        t = (text or "").lower()
        if any(k in t for k in ("refund", "cancel", "billing", "invoice")):
            out.append([1.0, 0.0])
        else:
            out.append([0.0, 1.0])
    return _np.asarray(out, dtype=_np.float32)


_voss_semantic.SemanticMatcher._encode = _demo_fake_encode
_voss_semantic.SemanticMatcher._ensure_encoder = lambda self: None


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
"""


@pytest.fixture
def demo_env(tmp_path: Path) -> dict[str, str]:
    return deterministic_subprocess_env(
        tmp_path,
        default_response="stub-response",
        extra_sitecustomize=DEMO_SITECUSTOMIZE,
    )
