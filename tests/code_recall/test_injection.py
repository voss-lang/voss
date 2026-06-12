"""VSEM-06 RED tests: ## Code Recall auto-injection — token cap, evictability,
off-switch.

Planned seams (V19-RESEARCH / V19-PATTERNS):
  voss.harness.cli._render_code_recall_text(cwd, task_text) -> str
  voss.harness.agent._compose_system_blocks(..., code_recall_text="")
  [code_recall] inject = false  in config.toml
"""
from __future__ import annotations


def test_token_cap(indexed_fixture_repo):
    """Injected ## Code Recall section ≤1000 tokens by the V18 counter.

    D-07: the first render kicks the background build and returns "" until
    the service is ready — poll until the section materializes.
    """
    import time

    from voss.harness.agent import _default_token_count
    from voss.harness.cli import _render_code_recall_text

    deadline = time.monotonic() + 30.0
    text = ""
    while not text and time.monotonic() < deadline:
        text = _render_code_recall_text(indexed_fixture_repo, "where is retry backoff handled")
        if not text:
            time.sleep(0.05)

    assert "## Code Recall" in text
    tokens = _default_token_count(text, model="claude-sonnet-4-6")
    assert tokens <= 1000, f"injected section is {tokens} tokens (> 1000 cap)"


def test_evictable():
    """The injected section threads through _compose_system_blocks as its own
    block WITHOUT a cache_control pin — it lives in the V18-evictable region,
    never frozen into the cached prefix."""
    from voss.harness.agent import _compose_system_blocks

    section = "## Code Recall\n[code] code:alpha.py:000 (score 0.90)\n  def alpha_retry_backoff..."
    blocks = _compose_system_blocks(
        voss_md_block="# VOSS.md",
        cognition_text="cognition",
        code_recall_text=section,
        prior_context_text="prior",
        loop_system="loop system",
    )

    recall_blocks = [b for b in blocks if "## Code Recall" in b.get("text", "")]
    assert len(recall_blocks) == 1, "section must be injected as its own block"
    assert "cache_control" not in recall_blocks[0], (
        "code recall block must not be cache-pinned — allocator must be free to evict it"
    )


def test_off_switch(tmp_path, fake_embed_fn, monkeypatch):
    """[code_recall] inject = false → zero injection bytes."""
    config_home = tmp_path / "xdg"
    (config_home / "voss").mkdir(parents=True)
    (config_home / "voss" / "config.toml").write_text("[code_recall]\ninject = false\n")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))

    from voss.harness.config import get_code_recall_config

    cfg = get_code_recall_config()
    assert cfg["inject"] is False

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "alpha.py").write_text("def alpha_retry_backoff(n):\n    return n\n")

    from voss.harness.code.index import build_index

    build_index(repo)

    from voss.harness.code.semantic_index import CodeIndex

    CodeIndex(repo).build(session_id="test-session")

    from voss.harness.cli import _render_code_recall_text

    text = _render_code_recall_text(repo, "where is retry backoff handled")
    assert text == "", "inject=false must produce zero injection bytes"
