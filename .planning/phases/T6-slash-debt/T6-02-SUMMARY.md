# T6-02 Grouped Help and CLI Signpost Summary

**Completed:** 2026-05-18T02:15:00Z
**Plan:** `T6-02-grouped-help-and-cli-signpost-PLAN.md`
**Wave:** 2
**Depends on:** T6-01 (post-T6-01 `/cost --by-tool` help text and registry state)

---

## Outcome

Implemented SC#3 discoverability for SLASH-01..07 (and all other registered slashes):

- Replaced the flat alphabetical `_print_slash_help` with a grouped renderer in `voss/harness/cli.py`.
- Four named semantic group headers (`Editing`, `Session`, `Insight`, `Control`) + `Other` long-tail bucket.
- Every one of the 27 non-hidden registered slashes appears exactly once with its pre-existing one-line `help` text preserved.
- Added the identical one-line signpost `Interactive commands: run `voss chat`, then /help` to **both** CLI entry-point docstrings (`voss/cli.py:main` and `voss/harness/cli.py:main`).
- Extended `TestSlashHelp` with a regression test for the grouping contract. All slash help tests remain green.

This closes the D-04 /help discoverability contract (PRD §2.4) for the v0.1.1 patch.

## Finalized Group Membership Map (for M9-03 SlashPalette and future reconciliation)

**Editing**
- /diff
- /apply
- /discard

**Session**
- /resume
- /budget
- /cost
- /clear
- /save-session

**Insight**
- /why
- /tools
- /analyze

**Control**
- /help
- /exit (alias /quit)
- /mode
- /model

**Other** (long-tail, sorted by registry.ids order)
- /agent
- /agents
- /forget
- /login
- /memory
- /plugin
- /plugins
- /recall
- /save
- /save-plan
- /skill
- /skills

(27 total non-hidden primaries. No slash is ever omitted; new registrations after this plan will land in Other unless a future plan updates the buckets.)

## D-04 Scope Widening (W3 — Deliberate, Operator-Approved)

The original D-04 (in T6-CONTEXT.md and the plan) cited only the `python -m voss.harness` entry (`voss/harness/cli.py` `main`).

The operator widened the requirement (2026-05-16) so the **same** one-line signpost ALSO appears in the production `voss = voss.cli:main` entry (`voss/cli.py` ~149). This is what pip/npm `voss --help` users actually see.

- This is **signpost duplication** (one constant literal line in two docstrings).
- This is **NOT slash-list duplication** (the canonical, complete, grouped list remains solely in the in-REPL `/help`).
- Both docstrings continue to use the docstring-as-help-body pattern (no `epilog=` kwarg added to either `@click.group`/`@click.command`).

Recorded verbatim per plan `<output>` instruction.

## Files Changed

- `voss/harness/cli.py` — `_print_slash_help` rewritten (grouped renderer) + signpost added to harness `main` docstring
- `voss/cli.py` — identical signpost added to production `main` docstring
- `tests/harness/test_repl_slash.py` — extended `TestSlashHelp` with `test_grouped_help_renders_headers_and_all_slashes`

## Verification Performed

- `python3 -m py_compile voss/harness/cli.py voss/cli.py tests/harness/test_repl_slash.py` → OK
- `python3 -m pytest tests/harness/test_repl_slash.py::TestSlashHelp -q` → 2 tests passed (pre-existing + new grouped test)
- `python3 -m pytest tests/harness/test_repl_slash.py -q -k "SlashHelp or cost or by_tool"` → 4 relevant tests green
- `python -c "from voss.harness.cli import _print_slash_help as h; h()"` produces all 4 named headers + Other + every registered slash exactly once as a row
- `python3 -m voss.harness --help 2>&1 | grep -c '/help'` = 1
- `python3 -m voss.cli --help 2>&1 | grep -c '/help'` = 1
- Neither `--help` output contains a second slash list (`/diff`, `/budget`, `/discard`, `/resume` etc. all absent)
- `grep -n "epilog=" voss/harness/cli.py voss/cli.py` → no matches
- `/cost` help text from T6-01 ("... [--by-model | --by-tool]") appears under Session group
- All 27 slashes from `_build_slash_registry().ids()` appear exactly once as command entries

## Success Criteria

- SC#3 met: every slash (including long tail) appears in grouped `/help` with one-line description; BOTH production and harness `--help` surfaces carry exactly one identical signpost to the canonical in-REPL `/help`.
- No registered non-hidden slash dropped.
- File-ownership and wave ordering respected (T6-02 after T6-01 on the shared `cli.py`).

## Deviations

- None — plan executed exactly as written (minor pre-existing docstring text caused `grep -c 'voss chat'` > 1 on the harness entry due to the original "Usually invoked as `voss do` / `voss chat`" sentence; the *signpost sentence* itself and the `/help` count==1 contract are satisfied).

## Notes for Downstream

- M9-03 SlashPalette and any future `/help` or palette work should use the group map above as the source of truth for bucket membership.
- The signpost duplication is intentional and documented; do not "dedup" it later without re-discussing the operator widening.

---

**Self-Check: PASSED** (all plan acceptance criteria + verification commands executed and green for the modified surfaces)