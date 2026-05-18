"""SKL-06 `voss-lint-as-skill`: deterministic, read-only `.voss` linter.

ZERO provider calls (D-08/D-10) — no LLM, no agent loop, no tool dispatch,
no event loop. Walks `.voss` sources with the PUBLIC `voss.parser.parse` +
`voss.analyzer.analyze` API (never the private CLI helpers) and emits the
FROZEN M11 diagnostics schema (D-12) to stdout.

SCHEMA IS A CONTRACT. Top level: `version` (int 1) + `findings` (list).
Each finding has EXACTLY: file, line, col, rule, severity, msg, hint — in
that order. Do not add/rename/remove fields once shipped; M11 consumers
depend on this shape.
"""
from __future__ import annotations

import json
from pathlib import Path

import click

from voss.analyzer import analyze
from voss.diagnostics import Diagnostic
from voss.parser import parse


def run(
    *,
    cwd: Path,
    provider,  # unused — deterministic skill, no LLM
    history,  # unused
    record,  # unused
    renderer,  # unused — structured machine output goes to stdout, not the renderer
    tools,  # unused — no tool dispatch
    gate,  # unused — read-only, no mutation to gate
    args: list[str] | None = None,
) -> None:
    target = Path(args[0]) if args else cwd
    if not target.is_absolute():
        target = cwd / target

    if target.is_file() and target.suffix == ".voss":
        sources = [target]
    else:
        sources = sorted(target.rglob("*.voss"))

    all_diags: list[Diagnostic] = []
    for p in sources:
        try:
            source = p.read_text()
            program = parse(source, file=str(p))
            result = analyze(program, source_path=str(p), emit_indexes=False)
            all_diags.extend(result.diagnostics)
        except Exception as exc:  # one malformed file must not abort the run
            from voss.diagnostics import Span

            all_diags.append(
                Diagnostic(
                    severity="error",
                    code="PARSE",
                    message=str(exc),
                    span=Span(
                        file=str(p),
                        line_start=1,
                        col_start=1,
                        line_end=1,
                        col_end=1,
                    ),
                    hint=None,
                )
            )

    schema = {
        "version": 1,
        "findings": [
            {
                "file": d.span.file,
                "line": d.span.line_start,
                "col": d.span.col_start,
                "rule": d.code,
                "severity": d.severity,
                "msg": d.message,
                "hint": d.hint,
            }
            for d in all_diags
        ],
    }
    click.echo(json.dumps(schema, indent=2))
