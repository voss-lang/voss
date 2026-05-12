---
phase: M5
plan: 06
type: execute
wave: 5
status: complete
date: 2026-05-12
---

# M5-06 Summary — Wheel-in-Tempvenv Smoke + README Install Polish

Completes EVAL-05 and Wave 5 of M5. Closes the M6 prerequisite gap: M6's npm
wrapper vendors the same wheel this plan now smoke-tests.

## What shipped

### `tests/packaging/test_wheel_install.py` (3 @pytest.mark.slow tests)

| Test | Boundary |
|---|---|
| `test_wheel_builds` | `python -m build --wheel --outdir <tmp>` produces exactly one `voss-*.whl`. Pure-Python build, no shared state with the install/smoke tests. |
| `test_install` | Fresh `venv.create(...)` venv accepts `pip install <wheel>` WITH dependencies (no `--no-deps`, no `--system-site-packages`). Asserts the `voss` console-script lands on the bin/Scripts path. |
| `test_smoke_asserts` | Inside the isolated venv: `voss --help`, `voss compile samples/classify.voss -o <tmp>/classify.py` (cwd=repo), `voss check samples/classify.voss` (cwd=repo), `voss doctor` (exit ∈ {0,1}), and `python -c "import voss_runtime"` all succeed. |

Each test is independent — the wheel + venv are rebuilt per test instead of
sharing a session-scoped fixture, so a flake surfaces with full attribution
to whichever boundary broke.

### `tests/packaging/test_readme.py` (5 fast content-assert tests)

Pins the v0.1 install narrative so it cannot silently drift:

- `pip install voss` literal present
- `voss doctor` literal present
- `samples/` directory link present (raw or `samples](...)` form)
- `Python harness` framing line present
- No `cargo install` or `brew install voss` install instructions

### `README.md` install section

Six edits per D-18:

1. `pip install voss` replaces `pip install -e ".[dev]"` as primary install.
2. `voss doctor` first-run guidance added directly after install.
3. `[samples/`](samples/) link present (already existed in the "What is .voss"
   section; the install section also references it via a `voss check
   samples/classify.voss` example).
4. Harness command surface listed (`voss doctor`, `voss do`, `voss chat`,
   `voss edit`, `voss sessions`, `voss resume`) with link to
   `.planning/HARNESS-PLAN.md` §2.2.
5. Framing line in the project overview: *"Voss v0.1 ships as a Python
   harness plus the `.voss` workflow-control language. A native Rust shell
   is preserved in `crates/` as a frozen spike and stays out of the v0.1
   ship path — npm (M6) distributes the same Python harness with a vendored
   interpreter."*
6. Roadmap-notes footer mentions `npm i -g voss` (M6) and explicitly defers
   Rust/Homebrew — no `cargo install` or `brew install voss` commands.

Development install (`pip install -e ".[dev]"`) retained in a separate
"Development install" subsection.

## Packaging fix discovered + applied

`pyproject.toml` previously declared `packages = ["voss_runtime", "voss"]`
explicitly, which **excluded the `voss.harness`, `voss.harness.skills`, and
`voss.eval` subpackages from the wheel**. The smoke test caught this on the
first run (post-install `voss --help` failed with `ModuleNotFoundError: No
module named 'voss.harness'`).

Fix:

```toml
[tool.setuptools]
include-package-data = false

[tool.setuptools.packages.find]
include = ["voss*", "voss_runtime*"]
exclude = ["tests*", "build*", "dist*"]

[tool.setuptools.package-data]
voss = [
    "grammar.lark",
    "py.typed",
    "templates/init/*",
    "harness/agent/*.voss",
]
voss_runtime = ["py.typed"]
```

Switched to `packages.find` so future subpackages auto-include. Added
`harness/agent/*.voss` to `package-data` so the M4 compiled-harness backend
can find its `.voss` sources after a pip install (required for
`VOSS_HARNESS=compiled` to work post-install).

## Deliberate divergences from the editable-install test

| Editable test (`test_editable_install_exposes_voss_help`) | Wheel smoke (this plan) |
|---|---|
| `--system-site-packages` venv | Isolated venv |
| `pip install -e --no-deps <repo>` | `pip install <wheel>` (WITH declared deps) |
| Proves the entry-point resolves against the repo | Proves the published wheel installs into a clean Python and exposes the full CLI surface |

Different contracts, different invariants — both kept.

## Exit-code accept window for `voss doctor`

`assert r.returncode in {0, 1}` matches the M1 D-13 contract. In a clean
tempvenv with no provider creds in the environment, `voss doctor` exits 1
(loud-failure missing-creds posture); if `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
happen to be in env, it exits 0. The smoke asserts at least one of
`python` / `provider` appears in `stdout|stderr` so a silent crash is still
caught.

## Verification

- `pytest -m slow tests/packaging/test_wheel_install.py -q` → **3 passed** in 83.77s.
- `pytest -q -m "not slow and not live"` → **661 passed, 2 skipped, 11 deselected**.
- `pytest -q -m "not slow and not live" tests/packaging/test_readme.py` → **5 passed**.
- No new top-level dependencies. Build module already present.

## Outstanding

Out of scope per D-19: actual PyPI publish — deferred until M6 (npm wrapper
needs the wheel on PyPI or a pinned git tag to vendor).

## What this unblocks

M6 (`/gsd-discuss-phase M6`) is now unblocked. The wheel installs cleanly,
the post-install surface is smoke-tested, and the README narrative aligns
with the npm-wrapper pyright-pattern distribution plan.
