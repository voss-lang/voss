---
phase: F5-commit-with-critique-hook
plan: 02
status: complete
---

# F5-02 Summary — Hook Lifecycle Commands

## What shipped

1. **`voss hooks install`** — writes 3-line shell shim to `.git/hooks/pre-commit`:
   - Uses `git rev-parse --show-toplevel` for correct git root (OQ-2)
   - Creates hooks dir if missing
   - Refuses when hook exists (D-07), `--force` overwrites
   - Sets chmod 0o755

2. **`voss hooks uninstall`** — removes voss-installed hooks only:
   - Checks `HOOK_MARKER` in content before deletion
   - Refuses foreign hooks with exit 1
   - Exits 0 silently when no hook found

3. **`hooks_group` registered in `AGENT_COMMANDS`** — `voss hooks` appears in `--help`

4. **7 hook lifecycle tests** appended to `test_consensus.py`:
   - install writes shim, refuses existing, --force overwrites
   - uninstall removes, refuses foreign, noop on missing
   - hooks in voss --help

## Verification

| Check | Result |
|-------|--------|
| `hooks` in `voss --help` | ✓ |
| 30 total tests GREEN (23 Plan 01 + 7 Plan 02) | ✓ |
| test_cli.py regression (14 pass) | ✓ |
| HOOK_SHIM exact content match | ✓ |
| chmod 0o755 on installed hook | ✓ |
| Foreign hook protection | ✓ |
