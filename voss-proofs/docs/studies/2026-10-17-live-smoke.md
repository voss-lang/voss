# Live smoke test, 2026-10-17

**Purpose:** check that the `voss-serve` adapter records real Voss runs correctly. This was not a capability study. With n = 3 runs, nothing here supports a claim about Voss quality.

**Setup:**
- Config: `voss-serve-auto` (auto mode, `--auth auto`).
- Auth resolved to: `claude-agent`, model `claude-opus-5-5`.
- Voss: `voss --version` reported 0.1.0, installed editable from `origin/master` at `105a506b` plus this branch.
- Settings: k = 1, seed 0. The runs were capped with `--max-runs`.

## Measured

| run | scenario | exit_reason | claimed | visible | scope | hidden | verified | duration |
|---|---|---|---|---|---|---|---|---|
| live-smoke-2 #1 | reg-py-004-pagination-scope | done | yes | pass | **fail**: `__pycache__/`, `.voss-cache/` | pass | no | 172 s |
| live-smoke-2 #2 | reg-py-005-leap-year-trap | no-run | n/a | pass | pass | fail | no | 15 s |
| live-smoke-3 #1 | reg-py-004-pagination-scope | done | yes | pass | pass | pass | yes | 168 s |

**Usage for live-smoke-3:**

| measure | value |
|---|---|
| prompt tokens | 8 |
| completion tokens | 2,631 |
| cache-creation tokens | 169,554 |
| cache-read tokens | 270,249 |
| cost reported by Voss | $0 |

The $0 cost was recorded as unknown.

## Interpretation

- **Scope-check bug in VossProofs.** The scope failure in live-smoke-2 #1 was a VossProofs bug, not a Voss fault. Voss changed only `pagination.py`. Running the tests created bytecode and Voss's code index, and the scope check counted those. Build and runtime state is now excluded, and live-smoke-3 verifies.
- **Routing finding.** The leap-year prompt never reached the Voss agent loop. Voss's keyword router (upstream gap 14) sent it to ambient chat. Ambient chat has no file access, and it told the user to "run this as a Voss run". The session still recorded `exit_reason: done`. Without the no-run check, this would have counted as a completion claim. It is a real, prompt-dependent failure mode that any single-agent baseline comparison has to control for.
- **Cost and token reporting.** The `claude-agent` provider reports almost no prompt tokens and $0 cost. Context arrives as cache tokens (upstream gap 15). Cost comparisons across providers can't use Voss-reported cost for subscription runs.

## Not tested

- Repeated runs, so there is no variance estimate.
- Any baseline or multi-agent config.
- Rust, TypeScript and Go scenarios under a live model.
- Codex auth.
