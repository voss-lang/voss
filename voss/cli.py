from __future__ import annotations

import importlib.resources
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

import click

from . import __version__
from .analyzer import analyze
from .ast_serializer import to_dict
from .codegen import CodegenError, generate_python
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


def _default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".py")


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _compile_source(
    source_path: Path,
    *,
    output_path: Path | None,
    project_root: Path | None,
    cache_dir: Path,
    verbose: bool = False,
) -> Path:
    if source_path.suffix != ".voss":
        raise click.ClickException(
            f"expected a .voss source file, got {source_path}"
        )
    program = _parse_file(source_path)
    try:
        analysis = analyze(
            program,
            source_path=str(source_path),
            project_root=project_root,
            cache_dir=cache_dir,
            emit_indexes=True,
        )
    except VossError as exc:
        raise click.ClickException(str(exc))
    _print_diagnostics(analysis.diagnostics)
    if analysis.errors:
        raise click.exceptions.Exit(code=1)

    try:
        gen_kwargs = {
            "source_path": str(source_path),
            "analysis": analysis,
            "cache_dir": cache_dir,
        }
        if project_root is not None:
            gen_kwargs["project_root"] = project_root
        result = generate_python(program, **gen_kwargs)
    except CodegenError as exc:
        raise click.ClickException(str(exc))

    target = output_path if output_path is not None else _default_output_path(source_path)
    _write_text_atomic(target, result.source)
    if verbose:
        click.echo(f"wrote {target}")
    return target


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.version_option(__version__, prog_name="voss")
@click.pass_context
def main(ctx: click.Context) -> None:
    """voss — compiler and agent.

    Compiler verbs : compile · run · check · init · ast
    Agent verbs    : do · chat · edit · doctor · tools · config

    Bare `voss` (no subcommand) drops into the agent REPL.
    """
    if ctx.invoked_subcommand is None:
        from .harness.cli import chat_cmd
        ctx.invoke(
            chat_cmd,
            model=None,
            cwd_str=".",
            json_mode=False,
            mode="plan",  # D-07: bare voss defaults to plan
            auth_pref="auto",
        )


@main.command("compile")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("-o", "--output", "output", type=click.Path(path_type=Path), default=None)
@click.option("--cache-dir", "cache_dir", type=click.Path(path_type=Path), default=Path(".voss-cache"))
@click.option("--project-root", "project_root", type=click.Path(path_type=Path), default=None)
@click.option("--verbose", is_flag=True, default=False)
def compile(
    source: Path,
    output: Path | None,
    cache_dir: Path,
    project_root: Path | None,
    verbose: bool,
) -> None:
    """Compile a Voss source file to Python."""
    _compile_source(
        source,
        output_path=output,
        project_root=project_root,
        cache_dir=cache_dir,
        verbose=verbose,
    )


@main.command("run")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("--cache-dir", "cache_dir", type=click.Path(path_type=Path), default=Path(".voss-cache"))
@click.option("--project-root", "project_root", type=click.Path(path_type=Path), default=None)
@click.option("--verbose", is_flag=True, default=False)
def run(
    source: Path,
    cache_dir: Path,
    project_root: Path | None,
    verbose: bool,
) -> None:
    """Compile and execute a Voss source file."""
    with tempfile.TemporaryDirectory(prefix="voss-run-") as tmp:
        tmp_dir = Path(tmp)
        generated = tmp_dir / (source.stem + ".py")
        _compile_source(
            source,
            output_path=generated,
            project_root=project_root,
            cache_dir=cache_dir,
            verbose=verbose,
        )
        completed = subprocess.run(
            [sys.executable, str(generated)],
            capture_output=True,
            text=True,
        )
        if completed.stdout:
            click.echo(completed.stdout, nl=False)
        if completed.stderr:
            click.echo(completed.stderr, nl=False, err=True)
        raise click.exceptions.Exit(code=completed.returncode)


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


_INIT_TEMPLATE_NAMES = (
    ".gitattributes",
    ".gitignore",
    "pyproject.toml",
    "README.md",
    "hello.voss",
)


def _scaffold_target(target: Path, *, force: bool) -> None:
    target_resolved = target.resolve()
    if target_resolved.exists():
        if not target_resolved.is_dir():
            raise click.ClickException(f"target exists and is not a directory: {target}")
        if any(target_resolved.iterdir()) and not force:
            raise click.ClickException(
                f"target directory is not empty: {target}; pass --force to overwrite"
            )
    else:
        target_resolved.mkdir(parents=True)

    template_root = importlib.resources.files("voss").joinpath("templates/init")
    for name in _INIT_TEMPLATE_NAMES:
        template = template_root.joinpath(name)
        if not template.is_file():
            raise click.ClickException(f"missing scaffold template: {name}")
        dest = (target_resolved / name).resolve()
        if not dest.is_relative_to(target_resolved):
            raise click.ClickException(f"refused to write outside target: {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(template.read_text())


@main.command("init")
@click.argument("target", type=click.Path(path_type=Path))
@click.option("--force", is_flag=True, default=False)
def init(target: Path, force: bool) -> None:
    """Scaffold a new Voss project."""
    _scaffold_target(target, force=force)
    click.echo(f"initialized voss project at {target}")


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


# Register agent commands (do / chat / doctor) on the unified `voss` group.
from .harness.cli import register as _register_agent_commands  # noqa: E402

_register_agent_commands(main)


if __name__ == "__main__":
    main()
