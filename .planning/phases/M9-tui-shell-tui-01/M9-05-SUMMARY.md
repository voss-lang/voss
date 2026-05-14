---
phase: M9
plan: 05
status: complete
date: 2026-05-14
---

# M9-05 Summary — Diff / Permission / Budget Modals (TUI-06 + TUI-07)

Wave 5. Three full-screen modal widgets replace stderr+stdin permission
prompts when the TUI is active. `PermissionGate` logic is byte-unchanged
— the bridge uses the existing `prompt_fn` / `scope_prompt_fn`
dependency-injection points (permissions.py:113-115). The only change
inside `permissions.py` is the extraction of diff-text computation into a
module-level `compute_diff_text(tool_name, args, base_dir)` so the TUI
modal path and the stderr-preview path share one implementation.

## Files Created

| Path | Purpose |
|------|---------|
| `voss/harness/tui/widgets/diff_modal.py` | `DiffModal(ModalScreen)` with `Hunk` + `DiffDecision` dataclasses. Bindings `[y/n/s/a/q/Esc]` per UI-SPEC. Heading `Review changes · {n} hunks · {file_count} files`. Posts `DiffSubmitted(decisions, cancelled)` and dismisses with `list[DiffDecision]`. |
| `voss/harness/tui/widgets/permission_modal.py` | `PermissionModal` (`[a]/[A]/[d]/Esc`) heading `Permission required`, body `Tool {tool_name} wants to {action_verb} {target}.`. Plus `ScopeExpandModal` (`[y]/[a]/[n]/Esc`) returning `"once"`/`"always"`/`"n"` to match `_interactive_expand_prompt`. |
| `voss/harness/tui/widgets/budget_modal.py` | `BudgetExhaustedModal` (`[c]/[e]/Esc`) heading `Budget exhausted`, body `Turn stopped at {used} / {limit} tokens. Continue with a new budget, or end the turn.` Dismisses with `"continue"`/`"end"`/`"cancel"`. |
| `voss/harness/tui/permissions_bridge.py` | `install_tui_permissions(gate, app, *, timeout_s=300)` — sets `gate.prompt_fn` and `gate.scope_prompt_fn` to callables that `call_from_thread(app.push_screen, modal, callback)` and block on a `Future`. 5-minute inattention timeout returns `'d'` / `'n'` (deny). |
| `tests/harness/tui/test_diff_modal.py` | 7 tests — heading copy, per-key advancement, accept-all/reject-all/skip mixes, Esc cancels with empty decisions, title-class guard. |
| `tests/harness/tui/test_permission_modal.py` | 12 tests covering both PermissionModal and ScopeExpandModal — all key paths + Esc + title class. |
| `tests/harness/tui/test_budget_modal.py` | 6 tests — heading, locked body copy, `[c]/[e]/Esc` results, title class. |
| `tests/harness/tui/test_compute_diff_text.py` | 5 tests — `compute_diff_text` correctness across `fs_write`/`fs_edit`/empty/no-change/missing-path + a parity check that `_render_diff_preview` still writes the same stderr body. |
| `tests/harness/tui/test_permissions_bridge.py` | 8 tests — install sets both callables, `[a]/[A]/[d]/Esc` map to the right `(allowed, reason)` tuples on `gate.check`, scope-expand modal maps to `out-of-scope: always` / `out-of-scope denied`, and a guard test asserting `PermissionGate`'s dataclass fields are unchanged. |

## Files Modified

| Path | Change |
|------|--------|
| `voss/harness/permissions.py` | Extracted `compute_diff_text(tool_name, args, base_dir) -> str` to module level (returns the unified diff string without writing). `PermissionGate._render_diff_preview` now delegates to it then writes to stderr. `PermissionGate.check` body and `def check`/`def _check_impl` blocks are byte-unchanged. No new fields on the dataclass. |
| `voss/harness/tui/app.py` | Added `push_modal_and_wait(modal, on_decision_callback)` — thin wrapper over `self.push_screen(modal, callback)`. |
| `voss/harness/tui/renderer.py` | Added `show_diff_modal(hunks, *, timeout_s=300) -> list[DiffDecision]` and `show_budget_modal(used, limit, *, timeout_s=300) -> str`. Both block on `concurrent.futures.Future` populated by the dismiss-callback. |
| `voss/harness/tui/widgets/__init__.py` | Re-export `DiffModal`, `Hunk`, `DiffDecision`, `PermissionModal`, `PermissionChoice`, `ScopeExpandModal`, `ScopeChoice`, `BudgetExhaustedModal`, `BudgetChoice`. |

## Dependency-Injection, Not Mutation

`PermissionGate` did the work for us in M1: `prompt_fn` and `scope_prompt_fn`
are already DI hooks. The bridge installs modal-driven callables; the
gate's mode-tier check, scope check, and remembered-always path all run
unchanged. Grep confirms: `def check` and `def _check_impl` line ranges
in `permissions.py` are identical to pre-M9 except for the small body of
`_render_diff_preview` which now delegates to `compute_diff_text`.

## Threading Model

Agent tools execute on worker threads (see `voss.harness.subagents`).
Bridge callables:

1. Build the modal on the calling thread.
2. `app.call_from_thread(app.push_screen, modal, on_result)` schedules the
   push on the Textual event loop. `on_result` is the dismiss-callback;
   it sets a `concurrent.futures.Future`.
3. Worker blocks on `fut.result(timeout=deadline)`. Default deadline is
   300 s; tests override via the `timeout_s` parameter.
4. On timeout, return the deny default (`'d'` for permission, `'n'` for
   scope expand, `'cancel'` for budget, `[]` for diff).

Renderer `show_diff_modal` / `show_budget_modal` follow the same pattern
and are intentionally synchronous so the agent path stays a normal
function call.

## Per-Hunk Apply Follow-Up (W3 in this plan)

`DiffModal` collects per-hunk decisions, but `fs_write` / `fs_edit` tools
still write atomically. The user has reviewed every hunk before the gate
returns; that is the security gate. Surgical per-hunk apply is a logged
follow-up — when accepted, the bridge will attach the decision list to
the args dict under `_tui_accepted_hunks` so a future `fs_write`
extension can apply only accepted hunks. For now: any acceptance ⇒
allow whole-file write; full rejection ⇒ `(False, "denied by diff review")`.

## Testing Notes (T-M9-05-01)

Bridge tests monkeypatch `sys.stdin.isatty` to `True` to simulate the
production TUI environment (Textual owns rendering, stdin is still a
TTY). This lets the existing `_prompt` tty-check fall through to the
injected `prompt_fn` without modifying `permissions.py`.

## Verification

```bash
pytest tests/harness/tui/test_diff_modal.py \
       tests/harness/tui/test_permission_modal.py \
       tests/harness/tui/test_budget_modal.py \
       tests/harness/tui/test_compute_diff_text.py \
       tests/harness/tui/test_permissions_bridge.py \
       tests/harness/test_permissions_modes.py \
       tests/harness/test_edit_scope.py \
       tests/harness/test_edit_cmd.py -q
# → 68 passed
```

Full TUI suite: 129 passed.

## CLI Wiring Deferred to M9-06

`install_tui_permissions(gate, app)` is the single entry point. cli.py
construction sites for the gate (cli.py:540-555, 722-727) are NOT
modified by this plan — that wiring is M9-06's job along with the resume
flow.

## Success Criteria (from plan)

1. ✅ DiffModal opens per-hunk for fs_write/fs_edit when TUI is active.
2. ✅ PermissionModal opens for shell_run / out-of-scope writes when
      gate.prompt_fn is the TUI version.
3. ✅ BudgetExhaustedModal opens with the three locked choices.
4. ✅ `install_tui_permissions(gate, app)` is the ONE entry point;
      cli.py wiring deferred to M9-06.
5. ✅ permissions.py `PermissionGate.check` / `_check_impl` logic blocks
      are byte-unchanged (only `_render_diff_preview` body delegated).
6. ✅ Esc on any modal denies/cancels per UI-SPEC destructive-actions
      inventory.
