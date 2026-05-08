from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import click

from . import __version__
from .analyzer import analyze
from .ast_serializer import to_dict
from .diagnostics import AnalysisResult, Diagnostic
from .exceptions import VossError
from .parser import VossParseError, parse


def _read_source(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        raise click.ClickException(f"file not found: {path}")
    except OSError as exc:
        raise click.ClickException(f"could not read {path}: {exc}")


def _parse_file(path: Path):
    source = _read_source(path)
    try:
        return parse(source, file=str(path))
    except VossParseError as exc:
        raise click.ClickException(str(exc))


def _print_diagnostics(diagnostics: Iterable[Diagnostic]) -> None:
    for diag in diagnostics:
        click.echo(str(diag))


def _exit_for_diagnostics(result: AnalysisResult, *, warnings_fail: bool) -> None:
    if result.errors:
        raise click.exceptions.Exit(code=1)
    if warnings_fail and result.warnings:
        raise click.exceptions.Exit(code=1)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="voss")
def main() -> None:
    """Voss compiler command-line interface."""


@main.command("compile")
@click.argument("source", required=False)
@click.option("-o", "--output", type=click.Path(), default=None)
def compile(source: str | None, output: str | None) -> None:
    """Compile a Voss source file to Python."""
    raise click.ClickException("not implemented yet")


@main.command("run")
@click.argument("source", required=False)
def run(source: str | None) -> None:
    """Compile and execute a Voss source file."""
    raise click.ClickException("not implemented yet")


@main.command("check")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("--warnings-as-errors", "warnings_as_errors", is_flag=True, default=False)
@click.option("--cache-dir", "cache_dir", type=click.Path(path_type=Path), default=Path(".voss-cache"))
@click.option("--project-root", "project_root", type=click.Path(path_type=Path), default=None)
def check(
    source: Path,
    warnings_as_errors: bool,
    cache_dir: Path,
    project_root: Path | None,
) -> None:
    """Parse and analyze a Voss source file without emitting code."""
    program = _parse_file(source)
    try:
        result = analyze(
            program,
            source_path=str(source),
            project_root=project_root,
            cache_dir=cache_dir,
            emit_indexes=False,
        )
    except VossError as exc:
        raise click.ClickException(str(exc))
    _print_diagnostics(result.diagnostics)
    _exit_for_diagnostics(result, warnings_fail=warnings_as_errors)


@main.command("init")
@click.argument("name", required=False)
def init(name: str | None) -> None:
    """Scaffold a new Voss project."""
    raise click.ClickException("not implemented yet")


@main.command("ast")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("--normalize-spans", "normalize_spans", is_flag=True, default=False)
@click.option("--compact", is_flag=True, default=False)
def ast(source: Path, normalize_spans: bool, compact: bool) -> None:
    """Print the parsed AST of a Voss source file."""
    program = _parse_file(source)
    data = to_dict(program, normalize_spans=normalize_spans)
    if compact:
        click.echo(json.dumps(data))
    else:
        click.echo(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
