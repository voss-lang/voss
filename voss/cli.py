from __future__ import annotations

import click

from . import __version__


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
@click.argument("source", required=False)
def check(source: str | None) -> None:
    """Parse and analyze a Voss source file without emitting code."""
    raise click.ClickException("not implemented yet")


@main.command("init")
@click.argument("name", required=False)
def init(name: str | None) -> None:
    """Scaffold a new Voss project."""
    raise click.ClickException("not implemented yet")


@main.command("ast")
@click.argument("source", required=False)
def ast(source: str | None) -> None:
    """Print the parsed AST of a Voss source file."""
    raise click.ClickException("not implemented yet")


if __name__ == "__main__":
    main()
