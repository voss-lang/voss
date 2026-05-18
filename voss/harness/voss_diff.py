"""Render `.voss` source beside its generated Python."""
from __future__ import annotations

import tempfile
from pathlib import Path

from voss.analyzer import analyze
from voss.codegen import generate_python
from voss.parser import parse


def resolve_generated_python(source: Path, *, cwd: Path) -> tuple[str, str]:
    """Return the origin label and generated Python for a `.voss` source."""
    source_path = _resolve_voss_source(source, cwd=cwd)
    cwd_path = cwd.resolve()

    cached = _cached_harness_artifact(source_path, cwd=cwd_path)
    if cached is not None:
        return _display_path(cached, cwd=cwd_path), cached.read_text()

    source_text = source_path.read_text()
    program = parse(source_text, file=str(source_path))
    with tempfile.TemporaryDirectory(prefix="voss-diff-") as tmp:
        tmp_root = Path(tmp)
        analysis = analyze(
            program,
            source_path=source_path,
            project_root=tmp_root,
            cache_dir=".voss-cache",
            emit_indexes=True,
        )
        result = generate_python(
            program,
            source_path=source_path,
            analysis=analysis,
            project_root=tmp_root,
            cache_dir=".voss-cache",
        )
    return "generated in memory", result.source


def render_voss_py_diff(source: Path, *, cwd: Path, width: int = 120) -> str:
    """Render bounded stacked sections for source and generated Python."""
    source_path = _resolve_voss_source(source, cwd=cwd)
    cwd_path = cwd.resolve()
    source_text = source_path.read_text()
    origin, generated = resolve_generated_python(source_path, cwd=cwd_path)

    source_label = f"Voss source: {_display_path(source_path, cwd=cwd_path)}"
    generated_label = f"Generated Python: {origin}"
    parts = [
        _render_section(source_label, source_text, width=width),
        _render_section(generated_label, generated, width=width),
    ]
    return "\n\n".join(parts) + "\n"


def _resolve_voss_source(source: Path, *, cwd: Path) -> Path:
    cwd_path = cwd.resolve()
    candidate = source if source.is_absolute() else cwd_path / source
    resolved = candidate.resolve()
    if resolved.suffix != ".voss":
        raise ValueError(f"expected a .voss source file, got {source}")
    try:
        resolved.relative_to(cwd_path)
    except ValueError as exc:
        raise ValueError(f"source escapes cwd: {resolved}") from exc
    return resolved


def _cached_harness_artifact(source: Path, *, cwd: Path) -> Path | None:
    agent_root = (cwd / "voss" / "harness" / "agent").resolve()
    try:
        source.relative_to(agent_root)
    except ValueError:
        return None

    cached = (cwd / ".voss-cache" / "harness" / f"{source.stem}.py").resolve()
    try:
        cached.relative_to(cwd)
    except ValueError as exc:
        raise ValueError(f"cached artifact escapes cwd: {cached}") from exc
    if cached.exists():
        return cached
    return None


def _render_section(label: str, text: str, *, width: int) -> str:
    bounded_width = max(40, width)
    border = "=" * min(bounded_width, max(len(label), 20))
    lines = [border, _clip_line(label, bounded_width), border]
    body = text.splitlines() or [""]
    lines.extend(_clip_line(line, bounded_width) for line in body)
    return "\n".join(lines)


def _clip_line(line: str, width: int) -> str:
    if len(line) <= width:
        return line
    if width <= 1:
        return line[:width]
    return line[: width - 3] + "..."


def _display_path(path: Path, *, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)
