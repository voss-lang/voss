---
phase: M10
plan: 03
status: complete
date: 2026-05-18
wave: 3
---

# M10-03 Summary — ast-grep + Regex Fallback + Service (Wave 3)

M10-03 completed the structural search backend (CODE-03).

## Deliverables

- `voss/harness/code/ast_grep.py`: Subprocess wrapper around `ast-grep run --json=stream` with timeout, output caps, JSONL parsing, and graceful missing-binary handling.
- `voss/harness/code/regex_fallback.py`: Bounded regex search over files (with path jailing). Returns hits with `source="regex"`.
- `voss/harness/code/service.py`: Initial `CodeIntelService` that tries ast-grep then falls back to regex. Returns source-tagged envelopes with `fallback` marker when needed.
- `tests/harness/test_code_search.py`: Basic coverage for both backends and the service.

All plan verifications passed:
- No rewrite/update flags in ast-grep wrapper
- Fallback marker and max_results handling present
- Compiles and tests green
- Read-only search only

**M10-03 execution complete.**

The search path (`code_search` primitive) is now functional and safe for later tool/slash integration in M10-04/05.
