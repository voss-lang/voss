---
phase: 05-cli-packaging-linguist
plan: 05-04
subsystem: cli
tags: [cli, init, scaffold, templates, linguist]

requires:
  - phase: 05-cli-packaging-linguist/05-03
    provides: compile and run commands
provides:
  - voss init scaffold command with --force protection
  - voss/templates/init/* package-bundled templates
  - exact .gitattributes Linguist override line in scaffold

key-files:
  created:
    - voss/templates/init/.gitattributes
    - voss/templates/init/.gitignore
    - voss/templates/init/pyproject.toml
    - voss/templates/init/README.md
    - voss/templates/init/hello.voss
    - tests/cli/test_init.py
  modified:
    - voss/cli.py
    - pyproject.toml

requirements-completed:
  - CLI-04
  - CLI-06
  - TOOL-02

completed: 2026-05-08
---

# Phase 05 Plan 04: Init Scaffold Summary

`voss init TARGET` copies bundled templates to a project directory using `importlib.resources`. Refuses non-empty targets without `--force`; preserves unrelated files when `--force` is passed.

## Tasks

| Task | Status | Notes |
|---|---|---|
| 05-04-0 | PASSED | Confirmed `phase5-cli-contract-ok` marker. |
| 05-04-1 | PASSED | `tests/cli/test_init.py` — 6 tests covering scaffold files, parseable hello.voss, non-empty refusal, --force, target-only writes, importlib.resources access. |
| 05-04-2 | PASSED | Created `voss/templates/init/{.gitattributes,.gitignore,pyproject.toml,README.md,hello.voss}` with exact Linguist line and parseable hello world. |
| 05-04-3 | PASSED | Implemented `init` command + helper, updated package-data to include `templates/init/*`. |

## Verification

- `pytest tests/cli/test_init.py -q` → 6 passed.
- `init-templates-ok` printed.
- `init-template-package-data-ok` printed.
- `git diff --check` clean.

## Decisions

- Templates are package data via `importlib.resources.files("voss").joinpath("templates/init")`.
- Hello world is a 2-line `let greeting = "hello, voss"\nprint(greeting)` program (parseable, provider-free).
- `_scaffold_target` resolves each destination and rejects writes outside the resolved target with `is_relative_to` guard.

## Self-Check

PASSED. `voss init` produces a parseable scaffold with the exact `.gitattributes` Voss override and protects existing files.
