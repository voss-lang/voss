---
phase: 04-codegen
plan: 04-05
subsystem: codegen
tags: [python, codegen, agents, tools, prompts, pydantic, tests]

requires:
  - phase: 04-codegen/04-04
    provides: semantic match manifest consumption and use-import lowering
provides:
  - AgentDecl lowering to VossAgent subclasses
  - @tool decorator emission on generated async functions
  - PromptDecl constants with parent-before-child inheritance
  - ClassDecl lowering to Pydantic BaseModel subclasses
  - awaited gather(...) lowering with timeout normalization

key-files:
  created:
    - tests/codegen/test_agents_tools_prompts.py
  modified:
    - voss/codegen.py

requirements-completed:
  - GEN-01
  - GEN-02

completed: 2026-05-08
---

# Phase 04 Plan 05: Agents, Tools, Prompts, Classes Summary

GEN-01 construct coverage for agents, tools, prompts, classes, spawn, and gather is implemented and covered by focused codegen tests.

## Tasks

| Task | Status | Notes |
|---|---|---|
| 04-05-1 | PASSED | Added `tests/codegen/test_agents_tools_prompts.py` covering `AgentDecl`, `@tool`, `PromptDecl`, `ClassDecl`, and `gather` timeout lowering. |
| 04-05-2 | PASSED | Implemented generic codegen support in `voss/codegen.py` for the constructs above while preserving async-first output and minimal imports. |

## Commits

| Commit | Description |
|---|---|
| `e2eac8d` | Adds the 04-05 tests and primary codegen implementation alongside 04-04 semantic/import work. |
| pending | Adds this execution summary and the final explicit `await gather(...)` emission cleanup required by the plan sentinel. |

## Decisions

- `spawn` remains synchronous and emits `Researcher().spawn(...)`; only `gather(...)` is awaited in await-capable contexts.
- `@tool` codegen emits the decorator only and does not inspect or import user functions during compilation.
- Prompt inheritance is declaration-order sensitive in v1; a child before its parent raises `CodegenError("prompt parent must be declared before child")`.
- `BaseModel` is imported only when a `ClassDecl` exists.
- `gather(timeout: 500ms)` normalizes to `timeout=0.5`; `60s` normalizes to `timeout=60`.

## Verification

- `phase4-codegen-contract-ok` preflight passed.
- `pytest tests/codegen/test_semantic_match.py tests/codegen/test_imports.py -q` passed before 04-05 execution.
- `pytest tests/codegen/test_agents_tools_prompts.py -q` -> 6 passed.
- `pytest tests/codegen -q` -> 40 passed.
- Plan sentinel printed `agents-tools-prompts-codegen-ok`.
- `git diff --check -- voss/codegen.py tests/codegen/test_agents_tools_prompts.py` passed.

## Deviations

- The TDD red phase was not observable in this session because a concurrent/worker commit had already added the test file and most implementation by the time verification ran.
- `tests/codegen/test_imports.py` and `tests/codegen/test_semantic_match.py` were already part of the concurrent 04-04/04-05 work and were not authored by this final cleanup step.

## Self-Check

PASSED. The plan success criteria are met: agent, tool, prompt, class, spawn, and gather constructs have codegen paths; generated code remains parseable and async-first; imports are construct-driven; and codegen does not execute user dependencies.
