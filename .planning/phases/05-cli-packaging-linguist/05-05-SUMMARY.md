---
phase: 05-cli-packaging-linguist
plan: 05-05
subsystem: tooling
tags: [linguist, gitattributes, samples, language-metadata]

requires:
  - phase: 05-cli-packaging-linguist/05-04
    provides: init scaffold with bundled .gitattributes template
provides:
  - top-level .gitattributes Linguist override
  - samples/{classify,support,research}.voss representative programs
  - language-metadata/voss.yml draft for future github-linguist PR

key-files:
  created:
    - .gitattributes
    - samples/classify.voss
    - samples/support.voss
    - samples/research.voss
    - language-metadata/voss.yml
    - tests/tooling/__init__.py
    - tests/tooling/test_linguist_assets.py

requirements-completed:
  - TOOL-01
  - TOOL-03

completed: 2026-05-08
---

# Phase 05 Plan 05: Linguist Tooling Assets Summary

Repo-level Linguist preparation: exact `.gitattributes` override, three representative `.voss` samples, draft local language metadata, and tooling tests that keep these files internally consistent without overclaiming upstream support.

## Tasks

| Task | Status | Notes |
|---|---|---|
| 05-05-0 | PASSED | Confirmed `phase5-cli-contract-ok` marker. |
| 05-05-1 | PASSED | `tests/tooling/test_linguist_assets.py` — 5 tests (gitattributes line, samples parse + ≥5 nonblank lines, sample names match, metadata draft+complete, no overclaim). |
| 05-05-2 | PASSED | Top-level `.gitattributes` with `*.voss linguist-language=Voss linguist-detectable=true`. |
| 05-05-3 | PASSED | Copied parser examples to `samples/{classify,support,research}.voss`. |
| 05-05-4 | PASSED | Created `language-metadata/voss.yml` with `name: Voss`, `group: Python`, `ace_mode: "python"`, `fallback_highlighting: Python`, `upstream_status: "draft-local"`. |

## Verification

- `pytest tests/tooling/test_linguist_assets.py -q` → 5 passed.
- `linguist-assets-verify-ok` printed.
- `linguist-no-overclaim-ok` printed.
- `git diff --check` clean.

## Decisions

- Samples mirror parser fixtures rather than diverging copies — easy to detect drift.
- Metadata phrased as draft/local; no "native GitHub support", "accepted upstream", or "registered in Linguist" claims.
- Fallback fields (`group: Python`, `fallback_highlighting: Python`) are planning metadata for future Linguist PR; the exact `.gitattributes` Voss override is preserved separately.

## Self-Check

PASSED. Repo Linguist assets are present, parseable, draft-only, and verified by hermetic tooling tests.
