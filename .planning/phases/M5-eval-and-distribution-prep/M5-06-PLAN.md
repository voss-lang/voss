---
phase: M5
plan: 06
type: execute
wave: 5
depends_on: []
files_modified:
  - tests/packaging/test_wheel_install.py
  - tests/packaging/test_readme.py
  - README.md
autonomous: true
requirements:
  - EVAL-05
must_haves:
  truths:
    - "`python -m build --wheel` produces `dist/voss-*.whl` against the repo."
    - "A tempvenv created via `venv.create(...)` can `pip install <wheel>` (WITH deps) and exposes `voss` on the bin/Scripts path."
    - "Inside the tempvenv: `voss --help`, `voss compile samples/classify.voss`, `voss check samples/classify.voss`, `voss doctor`, and `import voss_runtime` all succeed (doctor exit ∈ {0,1} per M1 D-13)."
    - "README install section uses `pip install voss` (not `pip install -e \".[dev]\"`), instructs users to run `voss doctor` after install, links to samples and harness commands, and contains a v0.1 framing line declaring the harness is Python-only with Rust deferred."
    - "README contains NO Rust install commands (`cargo install`, `brew install voss`); a 'Rust later' note is acceptable."
  artifacts:
    - path: "tests/packaging/test_wheel_install.py"
      provides: "@pytest.mark.slow wheel-in-tempvenv smoke (build + install + CLI surface asserts)"
      contains: "@pytest.mark.slow"
    - path: "tests/packaging/test_readme.py"
      provides: "Content-assert tests for README install section per D-18"
    - path: "README.md"
      provides: "Updated install section with v0.1 framing"
      contains: "pip install voss"
  key_links:
    - from: "tests/packaging/test_wheel_install.py"
      to: "tests/packaging/test_entrypoint.py:_repo_root"
      via: "Reuse the existing helper to locate the repo root"
      pattern: "from tests.packaging.test_entrypoint import _repo_root"
    - from: "tests/packaging/test_wheel_install.py"
      to: "stdlib build module"
      via: "subprocess.run([sys.executable, '-m', 'build', '--wheel', '--outdir', ...])"
      pattern: "-m\", \"build"
    - from: "README.md"
      to: "samples/ and harness command docs"
      via: "install section adds links to samples directory and harness commands"
      pattern: "samples/"
---

<objective>
Verify the Python harness installs cleanly from a built wheel into a temp virtualenv, and polish the README install section to match the v0.1 distribution posture (Python harness on PyPI; Rust/Homebrew deferred). This is the EVAL-05 contract; PyPI publish is explicitly OUT of M5 scope per CONTEXT D-19.

Purpose: Independent of all other M5 plans (no dependency on the eval CLI being green) — this plan can be planned in parallel with Plan 05 fixtures or Plan 04 summary. Marked `@pytest.mark.slow` so local fast iteration stays fast; CI runs it per PR.

Output: New `tests/packaging/test_wheel_install.py` (3 slow tests) + new `tests/packaging/test_readme.py` (5 content tests) + README install section edit.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md
@.planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md
@.planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md
@tests/packaging/test_entrypoint.py
@pyproject.toml
@README.md
@samples/classify.voss

<interfaces>
<!-- Existing analog — tests/packaging/test_entrypoint.py:65-105 -->
# @pytest.mark.slow
# def test_editable_install_exposes_voss_help(tmp_path):
#     venv_dir = tmp_path / "venv"
#     subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(venv_dir)], ...)
#     venv_python = venv_dir / "bin" / "python"
#     if not venv_python.exists(): venv_python = venv_dir / "Scripts" / "python.exe"
#     subprocess.run([str(venv_python), "-m", "pip", "install", "-q", "--no-deps", "-e", str(_repo_root())], ...)
#     voss_bin = venv_dir / "bin" / "voss"  # or Scripts/voss.exe on Windows
#     assert voss_bin.exists()
#     bin_help = subprocess.run([str(voss_bin), "--help"], ...)
#     assert "compile" in bin_help.stdout

<!-- pyproject.toml — slow + live markers already declared -->
# voss = "voss.cli:main" console script declared
# requires-python>=3.11
# build 1.5.0 confirmed present (RESEARCH §Standard Stack)

<!-- D-18 README required content -->
# - `pip install voss` (replaces `pip install -e ".[dev]"`)
# - `voss doctor` first-run check
# - link to samples/
# - link to harness commands
# - "v0.1 is a Python harness; Rust later" framing
# - NO Rust install commands
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wheel-in-tempvenv smoke (3 slow tests)</name>
  <files>tests/packaging/test_wheel_install.py</files>
  <read_first>
    - tests/packaging/test_entrypoint.py — full file (esp. `_repo_root` helper at top; the `test_editable_install_exposes_voss_help` analog at line 65-105)
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/packaging/test_wheel_install.py" (lines 1410-1538) — full target shape (3 tests)
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-16, D-17 — wheel smoke definition + @pytest.mark.slow
    - .planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md §"Common Pitfalls" — voss doctor exit-code contract (M1 D-13: exit ∈ {0,1}); `cwd=repo` needed for `voss compile samples/classify.voss`; `--no-deps` rejected (smoke proves WITH deps); `python -m build` 1.5.0 verified present
    - pyproject.toml — confirm `voss = "voss.cli:main"` console script + python>=3.11 + slow marker declared
    - voss/harness/diagnostics.py:181-198 — `aggregate_exit_code` (FAIL→1; otherwise 0)
  </read_first>
  <behavior>
    - `pytest -m slow tests/packaging/test_wheel_install.py::test_wheel_builds -q` passes: `python -m build --wheel --outdir <tmp>` produces exactly one `voss-*.whl`.
    - `pytest -m slow tests/packaging/test_wheel_install.py::test_install -q` passes: a tempvenv created via stdlib `venv` accepts the wheel via `pip install <wheel>` (WITH deps; no `--no-deps`).
    - `pytest -m slow tests/packaging/test_wheel_install.py::test_smoke_asserts -q` passes:
      - `<venv>/bin/voss --help` exits 0.
      - `<venv>/bin/voss compile samples/classify.voss` exits 0 (cwd=repo so the file resolves).
      - `<venv>/bin/voss check samples/classify.voss` exits 0 (cwd=repo).
      - `<venv>/bin/voss doctor` exits in `{0, 1}` per M1 D-13 (1 in a clean tempvenv with no provider creds; 0 if creds happen to be in env); stdout mentions either `python` or `provider` (case-insensitive).
      - `<venv>/bin/python -c "import voss_runtime"` exits 0.
    - Tests skip cleanly on platforms where `<venv>/bin/...` does not exist by falling back to `<venv>/Scripts/...` (Windows path).
    - All three tests are marked `@pytest.mark.slow`.
  </behavior>
  <action>
    Create `tests/packaging/test_wheel_install.py` per M5-PATTERNS.md lines 1441-1530:

    Module docstring `"""M5 EVAL-05 / D-16: build wheel, install in temp venv, smoke the post-install CLI surface."""`.

    Imports:
    - `import shutil`, `import subprocess`, `import sys`
    - `from pathlib import Path`
    - `import pytest`
    - `from tests.packaging.test_entrypoint import _repo_root` — reuse existing helper (per M5-PATTERNS.md line 1449)

    Three `@pytest.mark.slow` tests:

    **`test_wheel_builds(tmp_path)`**: per M5-PATTERNS.md lines 1452-1461:
    - `dist = tmp_path / "dist"`.
    - `subprocess.run([sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(_repo_root())], check=True, timeout=600)`.
    - `wheels = list(dist.glob("voss-*.whl"))`; assert `len(wheels) == 1, f"expected 1 wheel, got {wheels}"`.

    **`test_install(tmp_path)`**: per M5-PATTERNS.md lines 1464-1481:
    - Re-run the build step (each slow test is independent; do NOT share state via session-scoped fixtures because they obscure flake sources).
    - Find `wheel = next(dist.glob("voss-*.whl"))`.
    - Create venv: `subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, timeout=60)`. Do NOT use `--system-site-packages` (RESEARCH §Anti-Patterns: smoke must validate an isolated venv).
    - Cross-platform python resolution: `py = venv_dir / "bin" / "python"`; if not py.exists(): `py = venv_dir / "Scripts" / "python.exe"`.
    - `subprocess.run([str(py), "-m", "pip", "install", "-q", str(wheel)], check=True, timeout=600)` — install WITH deps (no `--no-deps`).

    **`test_smoke_asserts(tmp_path)`**: per M5-PATTERNS.md lines 1484-1529:
    - Build + venv create + pip install <wheel> (same as test_install).
    - Resolve `voss_bin = venv_dir / "bin" / "voss"`; cross-platform fallback to `venv_dir / "Scripts" / "voss.exe"`.
    - `assert voss_bin.exists()`.
    - `repo = _repo_root()`.
    - **`voss --help`**: subprocess.run([str(voss_bin), "--help"], capture_output=True, text=True, timeout=30). `assert r.returncode == 0, r.stderr`.
    - **`voss compile samples/classify.voss`** with `cwd=repo`: subprocess.run([str(voss_bin), "compile", "samples/classify.voss"], capture_output=True, text=True, timeout=60, cwd=repo). `assert r.returncode == 0, r.stderr`. (`cwd=repo` because the wheel installs the binary but not the repo samples per RESEARCH §Common Pitfalls.)
    - **`voss check samples/classify.voss`** with `cwd=repo`: same shape; assert returncode 0.
    - **`voss doctor`** (no cwd needed): subprocess.run([str(voss_bin), "doctor"], capture_output=True, text=True, timeout=30). `assert r.returncode in {0, 1}, f"voss doctor crashed: {r.stderr}"`. Then: `assert "python" in r.stdout.lower() or "provider" in r.stdout.lower()`. (Exit-1 is the loud-failure missing-creds case per M1 D-13.)
    - **`import voss_runtime`**: subprocess.run([str(py), "-c", "import voss_runtime"], capture_output=True, text=True, timeout=30). `assert r.returncode == 0, r.stderr`.

    Do NOT pass `--no-deps` on `pip install <wheel>` (RESEARCH §Anti-Patterns: smoke proves the wheel installs with its declared deps; the existing editable test uses --no-deps because it's a different contract).
    Do NOT pass `--system-site-packages` to `venv` (RESEARCH §Anti-Patterns: validates isolated venv).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest -m slow tests/packaging/test_wheel_install.py -q --timeout=900</automated>
  </verify>
  <done>
    `tests/packaging/test_wheel_install.py` exists with 3 `@pytest.mark.slow` tests. All three pass on a clean checkout. `pytest -q -m "not slow"` continues to skip these. Wheel builds, installs into a clean venv, and the post-install CLI surface (help, compile, check, doctor, import voss_runtime) is exercised.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: README install section polish + README content-assert tests</name>
  <files>tests/packaging/test_readme.py, README.md</files>
  <read_first>
    - README.md — full current content. The install section currently uses `pip install -e ".[dev]"` (per RESEARCH §"Compiler/Runtime Gaps Flagged as Sub-Plans" lines 476-477) and may say "Not on PyPI yet".
    - tests/cli/test_check.py:70-97 — string-content assertion pattern (analog for test_readme.py)
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/packaging/test_readme.py" (lines 1541-1586) — 5 test cases
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"README.md (MODIFY)" (lines 1595-1607) — required content
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-18 — required content list (install command, voss doctor, samples link, harness link, v0.1 framing line, no Rust install)
    - .planning/phases/M5-eval-and-distribution-prep/M5-VALIDATION.md row `readme-install-polish`
  </read_first>
  <behavior>
    - `pytest -q -m "not slow and not live" tests/packaging/test_readme.py` passes 5 tests:
      - `pip install voss` appears literally in README.
      - `voss doctor` appears literally in README.
      - `samples/` appears literally OR an explicit markdown link `samples](...)` appears.
      - One of `"Python harness"` or `"python harness"` appears (case-permissive v0.1 framing line).
      - `cargo install` does NOT appear; `brew install voss` does NOT appear.
    - The README still reads naturally — no broken section headers, no orphan bullets.
  </behavior>
  <action>
    Read the current `README.md`. Edit the install section per CONTEXT D-18:

    **Required additions/changes:**
    1. Replace any `pip install -e ".[dev]"` or "Not on PyPI yet" text in the install section with the literal command `pip install voss`. (If the dev-install command is useful elsewhere, retain it in a separate "Development" or "Contributing" subsection.)
    2. Add a "First run" line directly after the install command: instruct users to run `voss doctor` to verify the setup. The exact substring `voss doctor` must appear.
    3. Add a link to the samples directory. The simplest form: `[Samples](samples/)` or a sentence ending `... see samples/.` — `test_samples_link_present` accepts either.
    4. Add a link to the harness commands documentation OR a sentence mentioning the harness command surface (something like `voss doctor`, `voss do`, `voss edit`, `voss chat` …). Reuse existing README structure if there's already a "Commands" section.
    5. Near the top of the README (after the title/tagline, before the install command), add a framing line that contains the exact substring `Python harness` (case-insensitive OK; lowercase works too). Suggested phrasing: `"Voss v0.1 ships as a Python harness; a Rust shell is planned for a later release."`
    6. Remove (or move to a "Roadmap" footer) any Rust install instructions. A single sentence such as `"Rust + Homebrew distribution arrive after v0.1 usage proves out."` is acceptable. The substrings `cargo install` and `brew install voss` must NOT appear anywhere in the README.

    **Constraints (CLAUDE.md §3 surgical changes):**
    - Do NOT rewrite the README tone or restructure unrelated sections.
    - Edit existing prose surgically; preserve formatting style (headers, bullet density, code-fence language tags).
    - Do NOT add other unrelated content (no badges, no acknowledgements, no FAQ).

    Create `tests/packaging/test_readme.py` per M5-PATTERNS.md lines 1546-1586:
    - Module docstring `"""M5 D-18: README install section contains required content."""`.
    - `REPO_ROOT = Path(__file__).resolve().parents[2]`.
    - `_readme() -> str`: read `REPO_ROOT / "README.md"`.
    - `test_pip_install_voss_present`: `assert "pip install voss" in _readme()`.
    - `test_voss_doctor_first_run_mentioned`: `assert "voss doctor" in _readme()`.
    - `test_samples_link_present`: `text = _readme(); assert "samples/" in text or "samples](" in text`.
    - `test_v01_framing_line_present`: `text = _readme(); assert "Python harness" in text or "python harness" in text`.
    - `test_no_rust_install_path`: `text = _readme(); assert "cargo install" not in text; assert "brew install voss" not in text`. (Permit free-text "Rust later" mentions; reject actual install commands.)
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest -q -m "not slow and not live" tests/packaging/test_readme.py</automated>
  </verify>
  <done>
    README.md install section updated with the 6 required changes. All 5 content-assert tests pass. No unrelated README sections modified.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `python -m build` → wheel artifact | Wheel build pulls build dependencies from configured indexes; CI environment controls the index allowlist |
| Tempvenv → host filesystem | venv is created under `tmp_path` (pytest-managed); auto-cleaned on test teardown |
| README content → user expectations | README install instructions are the authoritative install contract for v0.1 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M5-06-wheel-deps-leak | T (Tampering) / Supply Chain | wheel install w/o --no-deps | mitigate | Smoke explicitly installs WITH deps; the existing editable-install test uses --no-deps and tests a different contract. Different tests, different invariants — pinned by the `pip install -q <wheel>` line (no --no-deps flag). |
| T-M5-06-doctor-exit-misread | T (Tampering) | voss doctor exit assertion | mitigate | Assertion accepts `{0, 1}` per M1 D-13 exit-code contract. Exit 1 in clean tempvenv represents the loud-failure missing-creds posture; that's the intended behavior. |
| T-M5-06-build-network | Supply Chain | python -m build first-run network | accept | `python -m build` downloads `setuptools`/`wheel` on first invocation; CI environment is expected to be online for the slow-marked smoke. RESEARCH §Common Pitfalls notes the `@pytest.mark.slow` gate is correct. If CI becomes air-gapped, fall back to `python -m pip wheel --no-deps .` (RESEARCH Assumption A3). |
| T-M5-06-rust-install-instructions | T (Tampering) | README | mitigate | `test_no_rust_install_path` regression-guards against accidental re-introduction of `cargo install` / `brew install voss` lines. |
| T-M5-06-readme-framing-drift | T (Tampering) | README framing line | mitigate | `test_v01_framing_line_present` pins the "Python harness" string; SCOPE-04 explicitly defers Rust/Homebrew. |
</threat_model>

<verification>
- `pytest -m slow tests/packaging/test_wheel_install.py -q --timeout=900` passes (3 tests).
- `pytest -q -m "not slow and not live" tests/packaging/test_readme.py` passes (5 tests).
- README.md install section contains all 6 required elements; no Rust install commands.
- No new top-level dependencies (relies on `build` 1.5.0 already present per RESEARCH).
</verification>

<success_criteria>
1. Wheel builds via `python -m build --wheel`.
2. Wheel installs into a clean tempvenv (no `--no-deps`, no `--system-site-packages`).
3. Post-install CLI surface exercised: `--help`, `compile`, `check`, `doctor` (exit ∈ {0,1}), `import voss_runtime`.
4. README install section uses `pip install voss`, mentions `voss doctor`, links to samples/, contains a v0.1 framing line, has no Rust install commands.
5. All 5 README content-assert tests pass; all 3 wheel-install slow tests pass.
</success_criteria>

<output>
After completion, create `.planning/phases/M5-eval-and-distribution-prep/M5-06-SUMMARY.md` summarizing: 3 wheel-smoke test boundaries (build / install / smoke-asserts), the explicit no-`--no-deps` + no-`--system-site-packages` divergence from the editable test, the exit-`{0,1}` accept window for voss doctor, and the README edits actually made (with the framing-line phrasing chosen).
</output>
