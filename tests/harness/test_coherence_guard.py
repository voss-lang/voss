"""
VBUS-08 coherence guard — enforceable NOW, not xfail.
V17 adds no parallel substrate. These assertions pass on the pre-V17
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# Watcher packages V17 must not introduce. `watchdog` pre-dates V17 in the
# root pyproject (one runtime + one dev pin) — that baseline is allowed.
WATCHER_TOKENS = ("chokidar", "watchdog", "watchfiles", "fs-watcher", "fsevents")
PYPROJECT_WATCHDOG_BASELINE = 2


def test_no_fs_watcher_dependency_added() -> None:
    # pyproject: filter comment lines BEFORE matching — never count raw text.
    pyproject_lines = [
        line
        for line in (REPO_ROOT / "pyproject.toml").read_text().splitlines()
        if not line.strip().startswith("#")
    ]
    watchdog_hits = [l for l in pyproject_lines if "watchdog" in l]
    assert len(watchdog_hits) == PYPROJECT_WATCHDOG_BASELINE, (
        f"watchdog mentions in pyproject changed from the pre-V17 baseline "
        f"({PYPROJECT_WATCHDOG_BASELINE}): {watchdog_hits!r}"
    )
    for token in WATCHER_TOKENS:
        if token == "watchdog":
            continue
        hits = [l for l in pyproject_lines if token in l]
        assert not hits, f"fs-watcher dep {token!r} added to pyproject: {hits!r}"


# ---------------------------------------------------------------------------
# V18 VOPT-08 coherence guard — no duplicated substrate, frozen surfaces.
# (The /cost + F3 HUD visual render stays manual per V18-VALIDATION.md.)
# ---------------------------------------------------------------------------

V18_FILES = [
    "voss/harness/context_allocator.py",
    "voss/harness/packing_eval.py",
    "voss/harness/agent.py",
    "voss/harness/recorder.py",
    "voss/harness/config.py",
]

_V18_SUBSTRATE_TOKENS = (
    "chromadb",
    "faiss",
    "annoy",
    "embedding",
    "sentence_transformers",
    "pinecone",
    "vectorstore",
)


def test_v18_no_new_retrieval_substrate() -> None:
    """VOPT-08: zero index/embedding/vector tokens in the V18 diff surface.

    Comment lines stripped first so header prose cannot self-invalidate
    the gate.
    """
    for rel in V18_FILES:
        body = "\n".join(
            line
            for line in (REPO_ROOT / rel).read_text().splitlines()
            if not line.strip().startswith("#")
        ).lower()
        hits = [t for t in _V18_SUBSTRATE_TOKENS if t in body]
        assert not hits, f"{rel}: retrieval-substrate tokens found: {hits}"


def test_v18_budget_osc_shape_frozen() -> None:
    """VOPT-08: _emit_budget_osc keeps the frozen five-field signature."""
    import inspect

    import voss.harness.recorder as recorder

    assert list(inspect.signature(recorder._emit_budget_osc).parameters) == [
        "tokens_used",
        "token_limit",
        "cost_usd",
        "iteration",
        "model",
    ]


def test_v18_no_second_budget_emitter() -> None:
    """VOPT-08: the only budget plumbing is the existing F3 recorder OSC."""
    import ast

    src = (REPO_ROOT / "voss" / "harness" / "recorder.py").read_text()
    tree = ast.parse(src)
    budget_emitters = [
        n.name
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("_emit")
        and "budget" in n.name.lower()
    ]
    assert budget_emitters == ["_emit_budget_osc"], budget_emitters
