"""M8-02 migration tests: byte-identical archive + fence fold + Pitfall 2 read symmetry."""
from __future__ import annotations

import hashlib
from pathlib import Path

from voss.harness import cognition, voss_md


def _arch_bytes() -> bytes:
    return (
        "---\n"
        "git_head: abc123def456\n"
        "analyzed_at: 2026-05-14T10:00:00+00:00\n"
        "file_count: 42\n"
        "analyzer_version: 1\n"
        "---\n\n"
        "# Architecture\n\nMigration fixture body.\n"
    ).encode()


def _write_pre_m8_arch(repo: Path) -> bytes:
    arch = cognition.voss_dir(repo) / "architecture.md"
    arch.parent.mkdir(parents=True, exist_ok=True)
    data = _arch_bytes()
    arch.write_bytes(data)
    return data


def test_archive_sha256_matches_pre_migration(tmp_voss_repo: Path) -> None:
    original = _write_pre_m8_arch(tmp_voss_repo)
    original_sha = hashlib.sha256(original).hexdigest()

    ret = voss_md.ensure_migrated(tmp_voss_repo)
    assert ret is True

    arch_path = cognition.voss_dir(tmp_voss_repo) / "architecture.md"
    assert not arch_path.exists()

    archive_dir = cognition.voss_dir(tmp_voss_repo) / "archive"
    archives = sorted(archive_dir.glob("architecture-*.md"))
    assert len(archives) == 1
    assert hashlib.sha256(archives[0].read_bytes()).hexdigest() == original_sha


def test_voss_md_contains_pre_migration_content(tmp_voss_repo: Path) -> None:
    original = _write_pre_m8_arch(tmp_voss_repo)

    voss_md.ensure_migrated(tmp_voss_repo)
    voss_md_path = tmp_voss_repo / "VOSS.md"
    assert voss_md_path.exists()

    body = voss_md.read_fence_body(voss_md_path, fence_id="architecture")
    assert body == original.decode()
    assert cognition.FRONTMATTER_RE.match(body)


def test_re_analyze_preserves_human_sections(tmp_voss_repo: Path) -> None:
    _write_pre_m8_arch(tmp_voss_repo)
    voss_md.ensure_migrated(tmp_voss_repo)

    voss_md_path = tmp_voss_repo / "VOSS.md"
    existing = voss_md_path.read_text()
    voss_md_path.write_text(existing + "\n## Human notes\n\nhand-written content\n")

    new_body = (
        "---\n"
        "git_head: deadbeefcafe\n"
        "analyzed_at: 2026-05-14T11:00:00+00:00\n"
        "file_count: 99\n"
        "analyzer_version: 1\n"
        "---\n\n"
        "# Architecture\n\nUPDATED machine content\n"
    )
    voss_md.write_fence_body(voss_md_path, fence_id="architecture", body=new_body)

    after = voss_md_path.read_text()
    assert "hand-written content" in after
    assert voss_md.read_fence_body(voss_md_path, fence_id="architecture") == new_body

    bundle = cognition.load(tmp_voss_repo)
    assert bundle.architecture_md is not None
    assert "UPDATED machine content" in bundle.architecture_md


def test_ensure_migrated_idempotent_on_voss_md_present(tmp_voss_repo: Path) -> None:
    (tmp_voss_repo / "VOSS.md").write_text("# pre-existing\n")
    _write_pre_m8_arch(tmp_voss_repo)

    assert voss_md.ensure_migrated(tmp_voss_repo) is False
    assert (cognition.voss_dir(tmp_voss_repo) / "architecture.md").exists(), (
        "ensure_migrated must not touch architecture.md when VOSS.md already exists"
    )


def test_ensure_migrated_missing_sources_returns_false(tmp_voss_repo: Path) -> None:
    assert voss_md.ensure_migrated(tmp_voss_repo) is False
    assert not (tmp_voss_repo / "VOSS.md").exists()
