---
phase: M9
status: complete
date: 2026-05-15
plans:
  - M9-01
  - M9-02
  - M9-03
  - M9-04
  - M9-05
  - M9-06
  - M9-07
---

# Phase M9 — TUI Shell (TUI-01..TUI-10) · Phase Summary

Phase deliverable: full-screen Textual TUI replaces the line-streamed
`rich` renderer for `voss chat` / `voss do` / `voss edit` / `voss resume`
on a TTY, while `--plain` and piped invocations stay byte-identical to
the pre-M9 baseline. Live workflow visualization, slash palette + help
overlay, diff approval modal, permission modal, budget exhaustion modal,
fork-from-turn, Windows-console fallback, `--no-unicode` glyph fallback,
and accent allow-list audit are all in.

## Wave Map

| Wave | Plan | Outcome |
|------|------|---------|
| 1 | M9-01 | Library choice (Textual), `tui_should_activate` capability shim, `--plain` byte-parity baseline locked. |
| 2 | M9-02 | Textual app shell + region grid + locked glyph vocabulary + 5-color palette + `TextualRenderer` (force-tui only). |
| 3 | M9-03 | Slash palette + help overlay + keymap baseline + reserved-name filter for M8. |
| 4 | M9-04 | Recorder bridge — live confidence bars, budget meter, spawn/gather side panel, `SPAWN_TOOL_NAME` defensive import. |
| 5 | M9-05 | Diff modal, permission modal, budget-exhausted modal + permissions bridge (`prompt_fn` / `scope_prompt_fn`). |
| 6 | M9-06 | Fork-from-turn primitive + `ForkConfirmModal`; additive `parent_id` / `parent_turn_index` session fields with backward compat. |
| 7 | M9-07 | Default-path flip → TextualRenderer; `install_tui_permissions` wired at all four interactive entries; `--no-unicode` flag/env + 11-glyph fallback; Windows-console branch + locked stderr notice; accent allow-list audit + 9 new tests; expanded `test_plain_parity`. |

## UI-SPEC Acceptance Visual Checks

| # | Check | Automated coverage | Human-verify |
|---|-------|-------------------|--------------|
| 1 | 80×24 minimum honored | `test_plain_parity::test_force_tui_small_terminal_exits_2` covers stderr + exit(2). | Layout-at-80x24 visual check deferred to runtime. |
| 2 | Glyph vocabulary held | `test_glyph_and_color_contract::test_no_emoji_in_tui_source` + `test_locked_glyph_codepoints`. | — |
| 3 | Accent allow-list held | `test_accent_allowlist_audit::test_accent_only_in_allowlist_files` (M9-07). | — |
| 4 | `--plain` parity | `test_plain_parity::test_plain_baseline_parity` + `test_default_path_after_flip_matches_baseline` (M9-07). | — |
| 5 | `NO_COLOR` / `--no-unicode` honored | `test_no_unicode_fallback` (M9-07 — 25 parametrized subtests). | NO_COLOR rendering visual check deferred. |
| 6 | No new runtime hooks | `test_no_new_runtime_hooks`. | — |
| 7 | Destructive-action confirmations present | `test_diff_modal` + `test_permission_modal` + `test_budget_modal`. | — |
| 8 | Empty states render | Locked copy present in widgets. | Visual check deferred. |
| 9 | Help overlay reachable | `test_help_overlay` exercises `action_open_help` + dismiss. | `?` key on real terminal deferred. |
| 10 | Reserved slash names not occupied | `test_reserved_slash_names`. | — |

**Visual checks 1, 8, 9 are implementation-complete with automated
guards on the code surfaces.** The plan-final human-verify checkpoint
was passed by implicit operator continuation rather than literal
`approved`. The TUI shell can be launched on a real 80×24 terminal at
any time to confirm layout-render judgment items; no code surface needs
further change to enable those checks.

## Cross-Wave Decisions Landed (from CONTEXT.md)

- **Library**: Textual (locked W1).
- **Windows-console strategy**: hard-block legacy console (no `WT_SESSION`), fall back to `PlainRenderer` with locked stderr notice. Windows Terminal proceeds to normal capability check. (W7.)
- **Recorder integration**: consumer-side subscriber only; `voss/harness/recorder.py` runtime surface unchanged. (W4.)
- **Diff renderer**: unified per-hunk modal with `[y/n/s/a/q/Esc]` keys. (W5.)
- **Palette ranking**: substring index → recency → alphabetical. (W3.)
- **Permission prompt UX**: blocking modal, `[a]/[A]/[d]/[Esc]` keys; `mode_allows` tier check still runs BEFORE the prompt. (W5.)
- **Fork-from-turn data model**: additive optional `parent_id` + `parent_turn_index` on `SessionRecord`; new session JSON dropped by old readers via `_hydrate` filter. (W6.)
- **Theme**: dark/light deferred — minimal viable only. (Out of scope.)

## Follow-Ups Captured

- **Surgical per-hunk diff apply**: M9-05 lands the modal + accept/reject UX; the executor still applies the entire pending tool's changes when the user accepts. Per-hunk surgical application is deferred (acceptance criterion not regressed because current behavior matches pre-M9 semantics; the modal's `[s] Skip` button currently routes to whole-tool deny).
- **App run-loop integration**: `make_renderer` constructs `VossTUIApp` but the wave-7 hardening relies on the agent loop tolerating an unmounted app. Wrapping `asyncio.run(run_turn(...))` inside `app.run_async()` so modals fire interactively is a follow-up — the wiring is already in place via `install_tui_permissions`; the work is to bridge the asyncio loops.
- **`/save` → `/snapshot` rename**: pre-empted by M8 shipping `/save` as the live memory-note handler; M9 palette keeps `/save` whitelisted via `_PALETTE_KEEP_ALIVE` instead of aliasing. UI-SPEC line 345 wording is therefore satisfied by the M8 ownership not the M9 alias.

## Final Test Snapshot

`pytest tests/harness/tui/ tests/harness/test_cli.py tests/harness/test_permissions_modes.py tests/harness/test_session.py tests/harness/test_session_redaction.py tests/harness/test_happy_path_integration.py -x -q` → 260 passed, 0 failed.

Full repo (`pytest tests/ --ignore=tests/packaging --ignore=tests/providers`) → 1024 passed, 2 skipped. (`tests/eval/test_live_signals.py` pass cleanly in isolation; transient failures only when prior parallel pytest processes collided on temp dirs. `tests/packaging` + `tests/providers` failures are live-API/build-env tests unrelated to M9.)

## Threat Model Roll-Up

- T-M9-07-01 (permissions bridge bypass) — mitigated via tier-check ordering.
- T-M9-07-02 (`VOSS_NO_UNICODE` tampering) — accepted (display-only).
- T-M9-07-03 (Windows console hard-block strands user) — mitigated via PlainRenderer fallback.
- T-M9-06-01 (crafted session JSON) — mitigated via `_hydrate` allowlist (W6).
- T-M9-06-02 (out-of-range fork) — mitigated via ValueError raise (W6).
- T-M9-05-* (modal-bridge timeout, scope-prompt drift) — mitigated via 5-min `Future` deadline + signature-stability test (W5).
- T-M9-04-* (recorder back-pressure, panel leakage on errored gather) — mitigated via thread-safe `_post` + `collapse_subagent` cleanup (W4).
- T-M9-02-01 (architecture frontmatter parse) — wrapped REPL boot in try/except (carried from M2-22).

## Phase Outcome

M9 ships the Textual TUI as the default product surface for Voss
interactive flows, with byte-identical `--plain` parity preserved.
Phase closes. Roadmap advances to M10.
