---
phase: T8-input-bar-ergonomics-v0-2
plan: 05
subsystem: tui
tags: [input-bar, reverse-search, paste-image, pillow, snapshots]
requires:
  - phase: T8-03
    provides: LocalBlockNotice style target and local-event path
  - phase: T8-04
    provides: VossTUIApp.history and on_local_event notice target
provides:
  - Ctrl-R inline reverse-i-search over app.history
  - Clipboard image probe and model-name vision gate
  - Pending image indicator and no-vision notice
  - LocalBlockNotice dismiss/timer behavior
  - Snapshot anchors 8-11
affects: []
tech-stack:
  added: [Pillow]
  patterns: [history corpus helper, clipboard image probe helper, vision model name gate]
key-files:
  created:
    - tests/harness/tui/__snapshots__/test_reverse_search/test_snap8_reverse_search_prompt_anchor.svg
    - tests/harness/tui/__snapshots__/test_reverse_search/test_snap9_reverse_search_no_match_anchor.svg
    - tests/harness/tui/__snapshots__/test_paste_image/test_snap10_image_attached_anchor.svg
    - tests/harness/tui/__snapshots__/test_paste_image/test_snap11_no_vision_notice_anchor.svg
  modified:
    - pyproject.toml
    - voss/harness/tui/widgets/input_bar.py
    - voss/harness/tui/widgets/local_block.py
    - voss/harness/tui/widgets/__init__.py
    - tests/harness/tui/test_reverse_search.py
    - tests/harness/tui/test_paste_image.py
key-decisions:
  - "Vision support is a conservative model-name prefix gate because no provider capability API exists."
  - "Clipboard image probe catches ImportError, NotImplementedError, ChildProcessError, and OSError as graceful no-op paths."
patterns-established:
  - "Ctrl-R uses the live per-project `app.history` corpus and never reads disk session state."
  - "No-vision paste feedback is local TUI state only and does not enter model history."
requirements-completed: [INPUT-04, INPUT-05]
duration: unknown
completed: 2026-05-18
---

# T8-05: Reverse Search and Paste Image Summary

**The input bar now supports inline Ctrl-R history search and clipboard-image handling with a vision gate.**

## Performance

- **Duration:** unknown
- **Started:** 2026-05-18
- **Completed:** 2026-05-18
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- Added `_build_corpus()` and Ctrl-R search mode over `VossTUIApp.history`, including query filtering, Enter-loads-editable, Esc-restore, and no-match rendering.
- Added Pillow as a dev-only dependency plus `_probe_clipboard_image()` and `_model_supports_vision()`.
- Added paste-image behavior: vision-capable models get a pending image indicator, no-vision models get a local warning notice, unsupported clipboard probes degrade silently.
- Added `LocalBlockNotice` and generated snapshot anchors 8-11.

## Task Commits

1. **Task 1-3: Reverse search and paste image implementation** - `9699558` (`feat(input-bar): enhance InputBar with reverse search and image handling`)
2. **Task 1-3: T8-05 tests and snapshots** - `9369e08` (`test(tui): enhance paste image and reverse search tests`)
3. **Task 3: Timer assertion fix** - `de42447` (`test(T8-05): fix notice dismiss timer assertion`)

**Plan metadata:** this summary commit.

## Files Created/Modified

- `pyproject.toml` - Adds `Pillow>=10.0` under `dev` only.
- `voss/harness/tui/widgets/input_bar.py` - Adds reverse-search state, corpus/probe/vision helpers, and paste-image action.
- `voss/harness/tui/widgets/local_block.py` - Adds `LocalBlockNotice`.
- `voss/harness/tui/widgets/__init__.py` - Exports `LocalBlockNotice`.
- `tests/harness/tui/test_reverse_search.py` - Ctrl-R corpus and interaction coverage plus snapshots 8-9.
- `tests/harness/tui/test_paste_image.py` - Clipboard probe, vision gate, notice, and snapshots 10-11.

## Decisions Made

- Kept image attachment as pending local input-bar state; forwarding image bytes into provider calls remains outside this phase.
- Used a model-name prefix allowlist for vision capability and documented it as assumed.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The full non-e2e suite is not green for existing unrelated/environmental reasons:
  - `tests/eval/test_voss_eval_stub.py::test_voss_eval_without_creds_points_to_stub` fails because the isolated subprocess cannot import `platformdirs`.
  - `tests/harness/tui/test_no_new_runtime_hooks.py::test_runtime_surface_files_unchanged` reports pre-existing `voss/harness/recorder.py` runtime-surface baseline drift.
  - `tests/packaging/test_npm_shim_logic.py::test_shim_reports_unsupported_platform_or_missing_package` now sees the npm shim exit 0 on this checkout.
  - `tests/providers/test_litellm_provider.py::test_live_complete_returns_text[claude-sonnet-4-5]` fails with 401 for the configured test key.
  - `tests/providers/test_litellm_provider.py::test_live_complete_returns_text[ollama/llama3.2:1b]` fails because the local Ollama model is missing.

## Verification

- `python3 -m pip install -e '.[dev]'` -> pass; Pillow already installed and declared.
- `pytest tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py -q` -> 24 passed, 4 snapshots passed.
- `pytest tests/harness/tui/test_input_bar_textarea.py tests/harness/tui/test_prefix_dispatch.py tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py tests/harness/tui/test_full_flow_pilot.py tests/harness/tui/test_app_interrupt.py -q` -> 53 passed, 11 snapshots passed.
- `python3 -c "from PIL import ImageGrab, Image; print('ok')"` -> pass.
- `python3 -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert 'Pillow' not in ' '.join(d['project']['dependencies']); print('dev-only')"` -> pass.
- `grep -A12 'def _probe_clipboard_image' voss/harness/tui/widgets/input_bar.py | grep -c 'NotImplementedError'` -> 1.
- `python3 -c "from voss.harness.tui.widgets import LocalBlockNotice; assert hasattr(LocalBlockNotice,'dismiss'); print('ok')"` -> pass.
- `python3 -m py_compile voss/harness/tui/widgets/input_bar.py voss/harness/tui/widgets/local_block.py tests/harness/tui/test_reverse_search.py tests/harness/tui/test_paste_image.py` -> pass.
- `git diff --check` -> pass.
- `pytest tests/ -q --ignore=tests/e2e` -> fails with the five blockers listed above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

All T8 plans are implemented and summarized. Final phase audit should use the focused 53-test T8 selection plus the documented full-suite blockers rather than treating the full suite as green.

---
*Phase: T8-input-bar-ergonomics-v0-2*
*Completed: 2026-05-18*
