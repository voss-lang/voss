"""CACHE-01: agent system block cache marker tests for T4-03."""

from voss.harness.agent import _compose_system_blocks


def test_system_blocks_have_single_marker() -> None:
    blocks = _compose_system_blocks(
        voss_md_block="A",
        cognition_text="B",
        prior_context_text="C",
        loop_system="D",
    )

    assert isinstance(blocks, list)
    assert len(blocks) == 4
    assert all(block["type"] == "text" for block in blocks)
    marked = [block for block in blocks if "cache_control" in block]
    assert len(marked) == 1
    assert marked[0] is blocks[-1]
    assert blocks[-1]["cache_control"] == {"type": "ephemeral"}


def test_empty_inputs_produce_empty_block_list() -> None:
    blocks = _compose_system_blocks(
        voss_md_block="",
        cognition_text="",
        prior_context_text="",
        loop_system="",
    )

    assert blocks == []
