"""Editable scope for `voss edit` sessions.

Reads are unrestricted under cwd (the existing path jail covers that). The
scope only restricts WRITES. Per D-02, default scope = <path> + sibling test
mirror. Per D-04, out-of-scope writes prompt; "always" expands the scope for
the rest of the session only — never persisted to PermissionStore.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _candidate_test_siblings(p: Path) -> list[Path]:
    """Return potential test-mirror file paths for a source file `p`.

    Order doesn't matter; the caller filters to ones that exist.
    """
    name = p.stem
    suffix = p.suffix
    parent = p.parent
    candidates: list[Path] = []
    # Adjacent siblings: test_foo.py, foo_test.py.
    candidates.append(parent / f"test_{name}{suffix}")
    candidates.append(parent / f"{name}_test{suffix}")
    # Walk parents looking for a `tests/<rel>/` mirror. Also try stripping
    # common source-root prefixes (`src/`, `lib/`) from the relative path so
    # `src/foo/bar.py` maps to `tests/foo/test_bar.py`.
    for up in range(1, 6):
        anchor = parent
        for _ in range(up):
            if anchor.parent == anchor:
                break
            anchor = anchor.parent
        try:
            rel = parent.relative_to(anchor)
        except ValueError:
            continue
        tests_root = anchor / "tests"
        rel_variants = {rel}
        rel_parts = rel.parts
        if rel_parts and rel_parts[0] in ("src", "lib"):
            rel_variants.add(Path(*rel_parts[1:]) if len(rel_parts) > 1 else Path())
        for rv in rel_variants:
            candidates.append(tests_root / rv / f"test_{name}{suffix}")
            candidates.append(tests_root / rv / f"{name}_test{suffix}")
        candidates.append(tests_root / f"test_{name}{suffix}")
    return candidates


@dataclass
class EditScope:
    """Set of files/dirs allowed to be written during a `voss edit` session."""

    cwd: Path
    files: set[Path] = field(default_factory=set)
    dirs: set[Path] = field(default_factory=set)

    @classmethod
    def resolve(cls, cwd: Path, path: str) -> "EditScope":
        cwd = cwd.resolve()
        target = (
            (cwd / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        )
        scope = cls(cwd=cwd)
        if target.is_dir():
            scope.dirs.add(target)
            try:
                rel = target.relative_to(cwd)
                mirror_variants = {rel}
                rel_parts = rel.parts
                if rel_parts and rel_parts[0] in ("src", "lib"):
                    mirror_variants.add(
                        Path(*rel_parts[1:]) if len(rel_parts) > 1 else Path()
                    )
                for rv in mirror_variants:
                    tests_mirror = cwd / "tests" / rv
                    if tests_mirror.exists() and tests_mirror.is_dir():
                        scope.dirs.add(tests_mirror.resolve())
            except ValueError:
                pass
        else:
            scope.files.add(target)
            for cand in _candidate_test_siblings(target):
                if cand.exists() and cand.is_file():
                    scope.files.add(cand.resolve())
        return scope

    def allows_write(self, target: str | Path) -> bool:
        p = (
            (self.cwd / target).resolve()
            if not Path(target).is_absolute()
            else Path(target).resolve()
        )
        try:
            p.relative_to(self.cwd)
        except ValueError:
            return False
        if p in self.files:
            return True
        for d in self.dirs:
            try:
                p.relative_to(d)
                return True
            except ValueError:
                continue
        return False

    def expand(self, target: str | Path) -> None:
        """Add target to the scope for the rest of the session (D-04)."""
        p = (
            (self.cwd / target).resolve()
            if not Path(target).is_absolute()
            else Path(target).resolve()
        )
        if p.is_dir():
            self.dirs.add(p)
        else:
            self.files.add(p)

    def summary(self) -> list[str]:
        """Sorted list of relative paths for banner display."""
        out: list[str] = []
        for f in self.files:
            try:
                out.append(str(f.relative_to(self.cwd)))
            except ValueError:
                out.append(str(f))
        for d in self.dirs:
            try:
                out.append(str(d.relative_to(self.cwd)) + "/")
            except ValueError:
                out.append(str(d) + "/")
        return sorted(out)
