"""VXMEM-04 RED tests for markdown heading-boundary chunking."""
from __future__ import annotations


def test_heading_boundary_split():
    """VXMEM-04: preamble plus ATX sections split on heading boundaries."""
    content = (
        "Quickstart preamble before the first heading.\n"
        "\n"
        "## Installation\n"
        "Install the package for the quickstart.\n"
        "\n"
        "## Configuration\n"
        "Configure the source path and glob.\n"
        "\n"
        "## First Steps\n"
        "Run the first command.\n"
    )

    from voss.harness.recall.external_index import extract_md_chunks

    chunks = extract_md_chunks(content)
    assert len(chunks) == 4
    assert chunks[0][0] == 1
    assert "Quickstart preamble" in chunks[0][2]
    assert chunks[1][0] == 3
    assert "## Installation" in chunks[1][2]
    assert chunks[2][0] == 6
    assert "## Configuration" in chunks[2][2]
    assert chunks[3][0] == 9
    assert "## First Steps" in chunks[3][2]


def test_headingless_one_chunk():
    """VXMEM-04: a headingless markdown file is indexed as one chunk."""
    content = "Plain notes without headings.\nStill searchable as one region.\n"

    from voss.harness.recall.external_index import extract_md_chunks

    chunks = extract_md_chunks(content)
    assert len(chunks) == 1
    line_start, line_end, text = chunks[0]
    assert line_start == 1
    assert line_end == 2
    assert text == content


def test_oversize_subsplit():
    """VXMEM-04: >800-char markdown sections use the shared oversize guard."""
    body = "\n".join(
        f"Embedding oversize guard padding line {i} with boundary vocabulary."
        for i in range(40)
    )
    content = f"## Oversize Guard\n{body}\n"
    assert len(content) > 800

    from voss.harness.recall.external_index import extract_md_chunks

    chunks = extract_md_chunks(content)
    assert len(chunks) >= 2
    assert chunks[0][0] == 1
    assert any("Embedding oversize guard" in chunk_text for _, _, chunk_text in chunks)


def test_non_md_skipped(tmp_path):
    """VXMEM-04: the ingest suffix gate includes md/markdown but skips txt."""
    md_path = tmp_path / "guide.md"
    markdown_path = tmp_path / "reference.markdown"
    txt_path = tmp_path / "notes.txt"

    from voss.harness.recall import external_index

    assert md_path.suffix in external_index._MD_SUFFIXES
    assert markdown_path.suffix in external_index._MD_SUFFIXES
    assert txt_path.suffix not in external_index._MD_SUFFIXES


def test_code_fence_heading_ignored():
    """VXMEM-04: ATX-looking lines inside code fences are not boundaries."""
    content = (
        "## ATX Headings\n"
        "Normal text before the fence.\n"
        "```python\n"
        "# not a markdown heading\n"
        "print('still inside the fence')\n"
        "```\n"
        "Text after the fence remains in the first section.\n"
        "\n"
        "## Oversize Guard\n"
        "A real second heading starts here.\n"
    )

    from voss.harness.recall.external_index import extract_md_chunks

    chunks = extract_md_chunks(content)
    assert len(chunks) == 2
    assert "# not a markdown heading" in chunks[0][2]
    assert "Text after the fence" in chunks[0][2]
    assert "## Oversize Guard" in chunks[1][2]
