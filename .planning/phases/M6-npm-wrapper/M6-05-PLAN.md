---
phase: M6-npm-wrapper
plan: 05
type: execute
wave: 4
depends_on: ["M6-02", "M6-04"]
files_modified:
  - tests/packaging/test_npm_install.py  # CREATE (NPM-04 smoke, @pytest.mark.slow)
  - tests/packaging/test_readme.py       # AMEND (add @voss/cli assertion)
  - README.md                            # MODIFY (promote npm i -g @voss/cli to primary)
  - pyproject.toml                       # AMEND only if a real v0.1.0 push is approved at task 4
autonomous: false
requirements: [NPM-04, NPM-05]
must_haves:
  truths:
    - "`pytest -m slow tests/packaging/test_npm_install.py` exits 0 on a host where the platform subpackage built by M6-03 (or pulled fresh from the npm registry test version) is available"
    - "The smoke test runs `npm pack` on `npm/`, installs the resulting tarball into a fresh temp Node project alongside the host's platform subpackage, then exercises the post-install commands `node bin/voss.js --help`, `doctor`, `check <inline-sample>`, `compile <inline-sample>` and asserts the M6 NPM-04 contract"
    - "`voss doctor` exit code is asserted to be in {0, 1} per the M1 D-13 contract"
    - "The .voss fixture is inline in the test (not a samples/ path) per RESEARCH §9 — the wheel does not ship samples/"
    - "README.md primary install path is `npm i -g @voss/cli` (or equivalent `npm install -g @voss/cli`); `pip install voss` is documented as the secondary path"
    - "The README still contains the v0.1 framing line about the Python harness (M5-06's invariant)"
    - "tests/packaging/test_readme.py has a new assertion pinning the `@voss/cli` install string so README drift is caught in CI"
  artifacts:
    - path: "tests/packaging/test_npm_install.py"
      provides: "NPM-04 packaging smoke test mirroring tests/packaging/test_wheel_install.py"
      contains: "@pytest.mark.slow"
    - path: "tests/packaging/test_readme.py"
      provides: "README invariants including new @voss/cli assertion"
      contains: "@voss/cli"
    - path: "README.md"
      provides: "v0.1 install docs with npm as primary path"
      contains: "npm i -g @voss/cli"
  key_links:
    - from: "tests/packaging/test_npm_install.py"
      to: "npm/bin/voss.js"
      via: "subprocess.run(['node', voss_js, ...])"
      pattern: "voss\\.js"
    - from: "tests/packaging/test_npm_install.py"
      to: "tests/packaging/test_entrypoint._repo_root"
      via: "import"
      pattern: "from tests\\.packaging\\.test_entrypoint import _repo_root"
    - from: "README.md"
      to: "@voss/cli npm package"
      via: "install command literal"
      pattern: "npm i -g @voss/cli|npm install -g @voss/cli"
---

<objective>
M6-05 closes NPM-04 and NPM-05. It writes the packaging smoke test that proves a fresh Node project install of `@voss/cli` plus the host's platform subpackage exits cleanly through `npx voss --help`, `voss doctor`, `voss check`, and `voss compile`. It also updates README.md so the primary v0.1 install path is npm; pip becomes secondary. After both succeed and the user confirms via the final checkpoint, the real `v0.1.0` git tag can be pushed and the M6-04 workflow ships v0.1.0 to npm.

Purpose: NPM-04 is the contract that proves end users actually get a working voss after `npm i -g @voss/cli` on a fresh machine. NPM-05 is the docs invariant that surfaces the npm path to readers of the README. The two are bundled here because they share a verification rhythm (one new test file + one README edit + one new test assertion) and because the README edit only makes sense once the smoke test has proven the npm path actually works.

Output: A new @pytest.mark.slow test module that mirrors tests/packaging/test_wheel_install.py almost line for line (but invokes via `node bin/voss.js` instead of `voss` console script), a README edit that promotes the npm command, a new test_readme.py assertion pinning the new install string, and a final go/no-go checkpoint for the v0.1.0 real-tag push.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M6-npm-wrapper/M6-RESEARCH.md
@.planning/phases/M6-npm-wrapper/M6-PATTERNS.md
@.planning/phases/M6-npm-wrapper/M6-CONTEXT.md
@.planning/phases/M6-npm-wrapper/M6-02-PLAN.md
@.planning/phases/M6-npm-wrapper/M6-04-PLAN.md
@tests/packaging/test_wheel_install.py
@tests/packaging/test_readme.py
@tests/packaging/test_entrypoint.py
@README.md
@npm/bin/voss.js

<interfaces>
Smoke test invocation contract (RESEARCH §9):

  Test path:    tests/packaging/test_npm_install.py
  Marker:       @pytest.mark.slow
  Helpers:      reuses _repo_root from tests.packaging.test_entrypoint
                (PATTERNS.md "shared patterns")

  Run model (one test does all of these; or split into 2-3 tests with shared
  fixture):

  1. tmp_path / "proj" is a fresh Node project: `npm init -y` (or write a
     minimal package.json directly).
  2. The HOST platform subpackage (e.g. @voss/cli-darwin-arm64) must be
     resolvable. Three viable sources:
     (a) From the live npm registry at the test version (requires the
         test version published in M6-04 to still be available).
     (b) From a local `npm pack` of npm/platforms/<host-triple>/ —
         requires the python/ tree to exist there (built by build_platform.py).
     (c) Mocked by setting TEST_PBS_EXTRACT env var to point at an
         already-built PBS extract on disk; the test installs via
         `npm install <path-to-pack-tgz>`.
     Choose (b) — most reliable, no registry dependency.
  3. `npm pack npm/` produces voss-cli-<version>.tgz in tmp_path.
  4. `cd tmp_path/proj && npm install <main-tgz> <platform-tgz>` installs both.
  5. Resolve voss bin: `tmp_path/proj/node_modules/.bin/voss`. Or invoke directly:
     `node tmp_path/proj/node_modules/@voss/cli/bin/voss.js`.
  6. Smoke commands:
     - voss --help                  -> exit 0
     - voss doctor                   -> exit in {0, 1}  (M1 D-13)
     - voss check <inline-sample>    -> exit 0
     - voss compile <inline-sample>  -> exit 0
     - python -c "import voss_runtime" (via the vendored python)  -> exit 0
  7. Inline .voss fixture: tmp_path / "smoke.voss" with body `agent SmokeAgent { }`
     (matches RESEARCH §9 recommendation; the wheel does not ship samples/).

  Skip rule: if `which node` returns non-zero, OR if
  `npm/platforms/<host-triple>/python` does not exist (build_platform.py
  was not run for the host), the test SKIPS with a clear reason.

README invariants (from existing tests/packaging/test_readme.py):
  - test_pip_install_voss_present:        "pip install voss" must appear
  - test_voss_doctor_first_run_mentioned: "voss doctor" must appear
  - test_samples_link_present:            "samples/" or "samples](" must appear
  - test_v01_framing_line_present:        "Python harness" or "python harness" must appear
  - test_no_rust_install_path:            "cargo install" must NOT appear; "brew install voss" must NOT appear

NEW invariants to add (this plan):
  - test_npm_install_voss_cli_present:    "npm i -g @voss/cli" OR "npm install -g @voss/cli" must appear
  - test_npm_install_is_primary:          the npm install line appears BEFORE the pip install line in the README (top-to-bottom order)

README edit shape (NPM-05): The existing install section needs a new code block above the pip section. Final structure roughly:
  ## Install

  ```
  npm i -g @voss/cli
  ```

  (one-line description that this brings the Python harness with no manual Python setup)

  Alternative: install from PyPI directly with `pip install voss` (requires Python 3.11+).

  ```
  pip install voss
  ```

The "Python harness" framing line elsewhere in the README must stay (per the M5-06
invariant `test_v01_framing_line_present`). Do NOT delete the pip path; just demote it.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write tests/packaging/test_npm_install.py (NPM-04 smoke)</name>
  <files>tests/packaging/test_npm_install.py</files>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §9 (NPM-04 smoke test design)
    - .planning/phases/M6-npm-wrapper/M6-PATTERNS.md "tests/packaging/test_npm_install.py" (exact-match analog discussion)
    - tests/packaging/test_wheel_install.py (full file — the line-by-line analog)
    - tests/packaging/test_entrypoint.py (_repo_root helper)
    - npm/bin/voss.js (just authored in M6-02)
  </read_first>
  <action>
    Create tests/packaging/test_npm_install.py with the structure from RESEARCH §9 + PATTERNS analog mapping. The file should mirror tests/packaging/test_wheel_install.py in structure (imports, helpers, @pytest.mark.slow on each test, subprocess.run with check + timeout). Concrete structure:

    Top of file: module docstring `"""M6 NPM-04: pack @voss/cli, install via npm, smoke CLI surface via vendored Python. Marked @pytest.mark.slow; mirrors tests/packaging/test_wheel_install.py for the npm distribution surface."""`.

    Imports per PATTERNS.md shared pattern: `from __future__ import annotations`, then `import os, platform, shutil, subprocess, sys` and `from pathlib import Path`, then `import pytest`, then `from tests.packaging.test_entrypoint import _repo_root`.

    Module-level helpers:
    1. `_host_triple() -> str | None`: read `platform.system().lower()` and `platform.machine().lower()`; return one of the 5 supported triples or None. Same mapping the M6-03 Task 3 detection used.
    2. `_platform_python_built(triple: str) -> Path | None`: return `_repo_root() / "npm" / "platforms" / triple / "python"` if it exists, else None.
    3. `_node_available() -> bool`: `shutil.which("node") is not None`.
    4. `_npm_available() -> bool`: `shutil.which("npm") is not None`.
    5. `_npm_pack(src_dir: Path, out_dir: Path) -> Path`: runs `npm pack <src_dir>` with cwd=out_dir, check=True, timeout=120; returns the path to the produced .tgz (glob for `*.tgz` in out_dir).

    A module-level skip guard for the whole module: if any of (`_node_available`, `_npm_available`, host triple is None, platform python is not built) — skip the whole module with a clear reason. Use `pytestmark = pytest.mark.skipif(...)` to skip without writing per-test skip boilerplate.

    Three @pytest.mark.slow tests:

    test_npm_pack_main(tmp_path): asserts `npm pack npm/` produces exactly one .tgz file with a name starting with `voss-cli-` (npm normalizes `@voss/cli` -> `voss-cli`).

    test_npm_install_and_help(tmp_path): packs both main and host platform subpackage; creates a fresh Node project (`npm init -y`); `npm install` both tarballs; runs `node node_modules/@voss/cli/bin/voss.js --help` with capture_output=True, text=True, timeout=30; asserts returncode == 0 and stdout contains "Usage" or "voss" (matches the click help output convention).

    test_npm_smoke_full(tmp_path): same setup as test_npm_install_and_help, then exercises:
      - voss doctor -> assert returncode in {0, 1}; (M1 D-13). Assert stderr+stdout combined contains "python" or "provider" (matches the existing wheel smoke).
      - Write `tmp_path / "smoke.voss"` with body `'agent SmokeAgent { }\n'`.
      - voss check <smoke.voss> -> assert returncode == 0.
      - voss compile <smoke.voss> -o <tmp_path/smoke.py> -> assert returncode == 0 AND smoke.py is a file.
      - Run the vendored python directly: `node_modules/@voss/cli-<triple>/python/bin/python3 -c "import voss_runtime"` -> assert returncode == 0 (cross-confirms the vendored interpreter has both voss and voss_runtime).

    For every subprocess.run, use `capture_output=True, text=True, timeout=<n>` with reasonable timeouts (30s for --help/doctor, 60s for check/compile, 120s for the npm install step). On any non-zero exit when expected zero, the assertion should include r.stderr to make CI failures debuggable (same idiom as test_wheel_install.py:120: `assert r.returncode == 0, r.stderr`).

    Windows nuance: `node_modules/@voss/cli-win32-x64/python/python.exe` is the path on win32 (no bin/ subdir). Since the smoke ALSO drives the vendored python directly in the last assertion, branch on `sys.platform == "win32"` to pick the right interpreter path inside the platform subpackage.

    Make sure the test file does NOT depend on the live npm registry — everything works against `npm pack` locally.
  </action>
  <verify>
    <automated>pytest --collect-only tests/packaging/test_npm_install.py 2>&amp;1 | grep -E "test_(npm_pack_main|npm_install_and_help|npm_smoke_full)" | wc -l | grep -E "^[[:space:]]*3$" &amp;&amp; python3 -c "import ast; t=ast.parse(open('tests/packaging/test_npm_install.py').read()); fns={n.name for n in ast.walk(t) if isinstance(n, ast.FunctionDef)}; assert {'_host_triple','_platform_python_built','_node_available','_npm_available','_npm_pack'}.issubset(fns); src=open('tests/packaging/test_npm_install.py').read(); assert 'pytestmark' in src and '@pytest.mark.slow' in src and 'returncode in {0, 1}' in src and 'agent SmokeAgent' in src"</automated>
  </verify>
  <acceptance_criteria>
    - tests/packaging/test_npm_install.py exists with module docstring + the 5 helpers + 3 @pytest.mark.slow tests.
    - Module-level `pytestmark = pytest.mark.skipif(...)` guards the whole file when prerequisites are missing.
    - Each test uses subprocess.run with check / capture_output / text / timeout.
    - `voss doctor` exit code assertion uses `in {0, 1}` (the M1 D-13 contract literal).
    - The inline .voss fixture body is `agent SmokeAgent { }` (matches RESEARCH §9).
    - The file imports `_repo_root` from `tests.packaging.test_entrypoint`.
    - The vendored-python `import voss_runtime` assertion is present in `test_npm_smoke_full`.
  </acceptance_criteria>
  <done>NPM-04 has a concrete pytest test. It skips cleanly on hosts without node/npm/host-platform-build; runs the full smoke when prerequisites are present.</done>
</task>

<task type="auto">
  <name>Task 2: Run the NPM-04 smoke test against the host build</name>
  <files>.planning/phases/M6-npm-wrapper/M6-05-smoke-log.txt</files>
  <read_first>
    - tests/packaging/test_npm_install.py (just authored)
    - .planning/phases/M6-npm-wrapper/M6-03-host-build-log.txt (confirm the host build exists)
  </read_first>
  <action>
    Confirm that npm/platforms/<host-triple>/python/ exists from M6-03 Task 3. If it does NOT (e.g. M6-03 used `--out /tmp/...` and the artifact was cleaned up), re-run `python3 npm/scripts/build_platform.py <host-triple> --out npm/platforms/<host-triple>/python` to materialize the directory inside the repo. (M6-04's CI puts it there; for this local smoke we need it persisted.)

    Run the smoke: `pytest -q -m slow tests/packaging/test_npm_install.py 2>&1 | tee .planning/phases/M6-npm-wrapper/M6-05-smoke-log.txt`.

    Expected outcome: all 3 tests pass. If any fail, capture the failure context (which test, which subprocess call, what exit code, what stderr) and surface as a `## FAILURE` block to the user before continuing. Do NOT silently continue past failures.

    After tests pass, clean up the local `npm/platforms/<host-triple>/python/` directory (it is a multi-hundred-MB tree that is .gitignored — never committed; CI rebuilds it fresh on every release). Add a `.gitignore` entry at `npm/platforms/*/python/` (or extend the existing root `.gitignore`) so an accidental `git add` cannot commit the vendored python tree. Verify with `git status` showing nothing new under npm/platforms/<triple>/python/.

    Append a `## RESULT` section to M6-05-smoke-log.txt: triple smoked, pytest pass/fail, time taken.
  </action>
  <verify>
    <automated>test -f .planning/phases/M6-npm-wrapper/M6-05-smoke-log.txt &amp;&amp; grep -qE "^[0-9]+ passed" .planning/phases/M6-npm-wrapper/M6-05-smoke-log.txt &amp;&amp; ! grep -qE "[0-9]+ failed" .planning/phases/M6-npm-wrapper/M6-05-smoke-log.txt &amp;&amp; grep -qE "^## RESULT" .planning/phases/M6-npm-wrapper/M6-05-smoke-log.txt &amp;&amp; grep -qE "npm/platforms/\\*?/python/" .gitignore</automated>
  </verify>
  <acceptance_criteria>
    - .planning/phases/M6-npm-wrapper/M6-05-smoke-log.txt exists.
    - Log shows `3 passed` (or equivalent pytest summary) from the test_npm_install module.
    - A `## RESULT` section is appended to the log with triple + pass/fail + elapsed.
    - .gitignore covers `npm/platforms/*/python/` so the vendored python tree cannot be committed.
    - No vendored python tree is under git tracking (`git ls-files npm/platforms/` returns only package.json files, never python/ paths).
  </acceptance_criteria>
  <done>NPM-04 smoke passes on the host. The gitignore guard prevents accidental commit of the heavy artifact.</done>
</task>

<task type="auto">
  <name>Task 3: Update README.md and extend test_readme.py</name>
  <files>README.md, tests/packaging/test_readme.py</files>
  <read_first>
    - README.md (full file — to locate the existing pip install section)
    - tests/packaging/test_readme.py (existing assertions)
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §13 (file list NPM-05) + §"Architectural Responsibility Map" "Smoke testing" row
    - .planning/phases/M6-npm-wrapper/M6-PATTERNS.md "test_readme.py (extend existing file)"
    - .planning/phases/M5-eval-and-distribution-prep/M5-06-SUMMARY.md (the v0.1 framing line invariant — must NOT be deleted)
  </read_first>
  <action>
    README.md edit (NPM-05): locate the existing install section (read the README to discover the current heading — likely `## Install` or `## Getting Started`). Insert a new install block ABOVE the existing pip install block. The new block contains:
    - A heading "Recommended: npm" (use whichever heading level matches the existing install section's depth — usually `###` if the install section is `##`).
    - A code block containing exactly the literal `npm i -g @voss/cli` (one line, no flags beyond `-g`).
    - One paragraph stating it brings the Python harness with vendored Python 3.12 + voss wheel + all dependencies + zero manual Python setup, and mentioning that `voss doctor` verifies the environment.
    - A subsequent heading "Alternative: pip" (same heading depth).
    - One sentence stating "If you already manage Python yourself, you can install from PyPI:".
    - A code block containing exactly the literal `pip install voss`.
    The key invariant: the npm command literal appears BEFORE the pip command literal in source-text order. Do NOT delete: the existing "Python harness" framing line elsewhere in the README (preserved by `test_v01_framing_line_present`); the existing `samples/` reference (preserved by `test_samples_link_present`); the existing `voss doctor` mention (preserved by `test_voss_doctor_first_run_mentioned`). Do NOT add: any reference to `cargo install` or `brew install voss` (would break `test_no_rust_install_path`).

    tests/packaging/test_readme.py edit: append two new test functions matching PATTERNS.md "new assertion to add" plus an ordering invariant.

    First new function `test_npm_install_voss_cli_present`: read README via the existing `_readme()` helper; assert one of the literals `npm i -g @voss/cli` or `npm install -g @voss/cli` appears in the text.

    Second new function `test_npm_install_is_primary_over_pip`: read README; locate `npm i -g @voss/cli` via str.find (fall back to `npm install -g @voss/cli` if the short form is absent); locate `pip install voss` via str.find; assert both indices are not -1 (each command must exist), and assert the npm index is less than the pip index (npm appears first in source-text order). The assertion failure messages must name the searched literal so a CI failure points the maintainer at exactly which token is missing.

    Both functions follow the style of the existing 5 tests in tests/packaging/test_readme.py (module-level `REPO_ROOT`, `_readme()` helper, simple `def test_*():` plus assertions, no fixtures).

    Run the full test_readme.py module locally and confirm 7 tests pass (5 existing + 2 new).
  </action>
  <verify>
    <automated>grep -E "npm i -g @voss/cli|npm install -g @voss/cli" README.md &amp;&amp; grep -E "pip install voss" README.md &amp;&amp; pytest -q tests/packaging/test_readme.py 2>&amp;1 | tail -10 | grep -E "^[0-9]+ passed"</automated>
  </verify>
  <acceptance_criteria>
    - README.md contains `npm i -g @voss/cli` (or the `npm install -g @voss/cli` long form).
    - The npm install command appears before the `pip install voss` command in the file.
    - "Python harness" or "python harness" still appears in the README (v0.1 framing preserved).
    - "cargo install" still does NOT appear; "brew install voss" still does NOT appear.
    - tests/packaging/test_readme.py has the 2 new test functions and all 7 tests pass.
  </acceptance_criteria>
  <done>NPM-05 docs invariant is met. Drift is now pinned by 2 new assertions on top of the existing 5.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 4: Final v0.1.0 release approval</name>
  <what-built>
    All M6 tasks 01-05 are complete. The test version published in M6-04 confirmed the workflow shape. The host smoke test in M6-05 Task 2 confirmed the install path is correct. README + test_readme.py pin the docs invariants. The remaining step is the production v0.1.0 npm publish, which only the user should authorize.
  </what-built>
  <how-to-verify>
    1. Read the M6 summaries: M6-01-SUMMARY (names claimed), M6-03-SUMMARY (size budget green), M6-04-SUMMARY (test tag passed), and the M6-05 smoke log.
    2. Confirm pyproject.toml is at `0.1.0` and all 6 npm manifests show `0.1.0` (`grep '"version"' npm/package.json npm/platforms/*/package.json` should all show 0.1.0).
    3. Confirm npm-version-sync CI job is green on master.
    4. Confirm there is no stale `v0.1.0` git tag (`git tag -l v0.1.0` returns empty). If a previous attempt left one, delete locally and remotely first.
    5. Authorize the publish: `git tag v0.1.0` then `git push origin v0.1.0`. The M6-04 workflow will fire on the tag.
    6. Watch the workflow at GitHub Actions; all 5 platform jobs + publish-main should exit 0.
    7. Verify on the registry: `npm view @voss/cli@0.1.0 version` returns `0.1.0`; same for all 5 `@voss/cli-<triple>@0.1.0`.
    8. Smoke a clean install on at least one machine the user has access to: `npm i -g @voss/cli && voss --help && voss doctor`.
    9. If anything fails, surface the failure mode; the v0.1.0 publish is not retryable at the same version — the user may need to publish 0.1.1 to fix.

    If you decide NOT to publish v0.1.0 yet (e.g. you want to dogfood the test version a bit longer), respond "hold" and the plan completes with M6 in "Ready to release" state, no real tag pushed.
  </how-to-verify>
  <acceptance_criteria>
    - User has reviewed M6-01..M6-04 summaries + M6-05 smoke log.
    - User responds "publish 0.1.0" or "hold".
    - If publish: `npm view @voss/cli@0.1.0 version` returns `0.1.0`; same for all 5 platform subpackages.
    - If hold: no v0.1.0 tag exists; M6 plan summary documents the hold rationale.
  </acceptance_criteria>
  <resume-signal>Reply "publish 0.1.0" (then watch the workflow + verify npm view), or "hold: <reason>".</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| smoke test subprocess -> npm pack tarball | Local file boundary; no network. |
| smoke test subprocess -> vendored python -m voss.cli | Crosses into the wrapped Python harness via the shim. |
| README.md -> end-user reading | The documented install command is the entry point for new users. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M6-05-01 | Information Disclosure | Smoke test inadvertently captures provider creds in its stdout assertions | mitigate | The smoke test invokes `voss doctor`, which by M1 D-09 design must NOT print API key values. Assertions check only that the combined stdout/stderr contains "python" or "provider" — never asserts the absence of secret strings (no negative-match). The test runs in a fresh tmp_path with default env; the test does NOT export provider keys, so the doctor will report missing creds and exit 1 — that is the expected path. |
| T-M6-05-02 | Tampering | README install command edited to point at a malicious npm package | mitigate | tests/packaging/test_readme.py pins the literal `@voss/cli` install string and the npm-before-pip ordering. Any swap (e.g. someone edits the README to `npm i -g voss-cli-evil`) breaks the test in CI. |
| T-M6-05-03 | Spoofing | A typosquat `@voss-cli` or `@voss/clii` published by a bad actor | accept | The README documents the canonical name; users typing it correctly land on the real package. v0.1 mitigation; a future plan could publish defensive typosquat placeholders (deferred, not in NPM-01..05). |
| T-M6-05-04 | Denial of Service | Smoke test hangs forever | mitigate | Every subprocess.run uses an explicit timeout (30s..120s). pytest itself enforces a global timeout via existing config. |
| T-M6-05-05 | Tampering | git tag v0.1.0 pushed without the bump_version step running | mitigate | release.yml step 6 (M6-04) verifies pyproject.toml version == npm/package.json version before publish. If they drift, the publish job fails before any npm publish runs. Task 4's checklist also has the user confirm versions are aligned before pushing the tag. |
</threat_model>

<verification>
- tests/packaging/test_npm_install.py exists with module-level pytestmark skip + 3 @pytest.mark.slow tests + 5 helpers.
- pytest -q -m slow tests/packaging/test_npm_install.py passes on the host (3 passed).
- tests/packaging/test_readme.py has 7 tests total (5 existing + 2 new); all pass.
- README.md contains the npm install command before the pip install command, preserves the v0.1 framing line, and does not introduce cargo/brew install paths.
- .gitignore covers npm/platforms/*/python/ so the heavy vendored tree cannot be committed.
- Task 4 has a recorded user decision: either v0.1.0 is published on npm at 0.1.0 across all 6 packages, OR the user explicitly held the release with a documented rationale.
</verification>

<success_criteria>
1. NPM-04 has a concrete, fast-skipping, slow-when-prereqs-met pytest smoke that exercises the full post-install command surface.
2. NPM-05 README invariant is in place and pinned by 2 new test_readme.py assertions.
3. The v0.1.0 release is either shipped to npm (all 6 packages at 0.1.0) or explicitly held by the user with rationale recorded.
4. .gitignore prevents accidental commit of the multi-hundred-MB vendored python tree.
</success_criteria>

<output>
After completion, create .planning/phases/M6-npm-wrapper/M6-05-SUMMARY.md recording: test function names + per-test runtime, host triple smoked, README diff summary, the 2 new test_readme.py assertions, the final Task 4 decision (publish 0.1.0 or hold), and (if published) the npm view output for all 6 packages at 0.1.0.
</output>
