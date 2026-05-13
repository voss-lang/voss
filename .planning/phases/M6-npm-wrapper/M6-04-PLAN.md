---
phase: M6-npm-wrapper
plan: 04
type: execute
wave: 3
depends_on: ["M6-01", "M6-02", "M6-03"]
files_modified:
  - .github/workflows/release.yml      # CREATE (new — old cargo-dist deleted in M6-01)
  - .github/workflows/ci.yml           # MODIFY (add version-sync check job)
  - npm/package.json                   # AMEND (bumped to 0.1.0 by bump_version.py)
  - npm/platforms/*/package.json       # AMEND (5 files; bumped to 0.1.0)
autonomous: false
requirements: [NPM-02]
must_haves:
  truths:
    - "Pushing a `v0.1.0` git tag triggers .github/workflows/release.yml which builds the voss wheel, fans out across 5 OS+arch runners, calls build_platform.py per platform, and publishes all 5 @voss/cli-<triple> packages plus the @voss/cli main package to npm — all at the same version"
    - "The release workflow has a pre-publish version-sync gate that fails if npm/package.json version differs from pyproject.toml version"
    - "Each platform job verifies the PBS tarball sha256 against pbs_manifest.json before extract"
    - "Each platform job calls build_platform.py with the right --out target so npm/platforms/<triple>/python/ is populated before npm publish"
    - "The main @voss/cli package is published LAST (after all 5 platform packages succeed) so its optionalDependencies references resolve at install time"
    - "A trial test tag (v0.1.0-test or pre-release) was pushed and the full workflow ran green end-to-end before the real v0.1.0 tag"
    - "ci.yml (push/PR) runs a fast version-sync check on every commit so drift between pyproject.toml and npm/package.json is caught in code review, not at release time"
  artifacts:
    - path: ".github/workflows/release.yml"
      provides: "Tag-triggered npm publish workflow: wheel build + 5-way matrix platform build + 6 npm publishes"
      min_lines: 80
      contains: "actions/checkout@v4"
    - path: ".github/workflows/ci.yml"
      provides: "Extended with a version-sync check job"
      contains: "bump_version.py"
  key_links:
    - from: ".github/workflows/release.yml"
      to: "npm/scripts/build_platform.py"
      via: "matrix job step that calls the script per platform"
      pattern: "npm/scripts/build_platform\\.py"
    - from: ".github/workflows/release.yml"
      to: "npm/scripts/bump_version.py"
      via: "step that runs bump_version before npm publish"
      pattern: "bump_version\\.py"
    - from: ".github/workflows/release.yml"
      to: "secrets.NPM_TOKEN"
      via: "NODE_AUTH_TOKEN env on publish steps"
      pattern: "NPM_TOKEN"
    - from: ".github/workflows/release.yml"
      to: "npm/platforms/<triple>/package.json"
      via: "cd into platform dir + npm publish --access public"
      pattern: "npm publish --access public"
---

<objective>
M6-04 wires the build machinery (M6-03) into a GitHub Actions release workflow that fires on `git push tags v*`. The workflow runs in 5-way matrix mode (one job per platform/runner combo, all GitHub-hosted free-tier including the new `ubuntu-24.04-arm` for linux-arm64), and a final `publish-main` job that depends on all 5 and publishes the meta `@voss/cli` package. The workflow replaces the cargo-dist release.yml that M6-01 already deleted.

Purpose: NPM-02 needs an actual publish path. Without this workflow, M6-03's scripts are unused. This plan also adds a fast version-sync gate to ci.yml so drift between pyproject.toml and npm/package.json is caught in code review on every push, not at release time.

Output: A working tag-triggered release pipeline, exercised end-to-end against a `v0.1.0-test1` (or pre-release suffixed) tag with all 6 packages publishing successfully to npm at a test version. The real `v0.1.0` publish stays gated behind M6-05's smoke test. This plan does NOT publish the production v0.1.0 — that is the final act after M6-05's smoke test passes against a freshly-published test version.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M6-npm-wrapper/M6-RESEARCH.md
@.planning/phases/M6-npm-wrapper/M6-PATTERNS.md
@.planning/phases/M6-npm-wrapper/M6-CONTEXT.md
@.planning/phases/M6-npm-wrapper/M6-01-PLAN.md
@.planning/phases/M6-npm-wrapper/M6-02-PLAN.md
@.planning/phases/M6-npm-wrapper/M6-03-PLAN.md
@.github/workflows/ci.yml
@pyproject.toml
@npm/package.json
@npm/scripts/build_platform.py
@npm/scripts/bump_version.py
@npm/scripts/pbs_manifest.json

<interfaces>
GitHub Actions matrix shape (from RESEARCH §7):

  matrix:
    include:
      - { npm-platform: darwin-arm64, runner: macos-latest,    pbs-triple: aarch64-apple-darwin,        python-bin: python/bin/python3 }
      - { npm-platform: darwin-x64,   runner: macos-13,        pbs-triple: x86_64-apple-darwin,         python-bin: python/bin/python3 }
      - { npm-platform: linux-x64,    runner: ubuntu-24.04,    pbs-triple: x86_64-unknown-linux-gnu,    python-bin: python/bin/python3 }
      - { npm-platform: linux-arm64,  runner: ubuntu-24.04-arm,pbs-triple: aarch64-unknown-linux-gnu,   python-bin: python/bin/python3 }
      - { npm-platform: win32-x64,    runner: windows-latest,  pbs-triple: x86_64-pc-windows-msvc,      python-bin: python/python.exe }

Step sequence per platform job:
  1. actions/checkout@v4
  2. actions/setup-python@v5 (python-version: "3.12")
  3. actions/setup-node@v4 (registry-url: https://registry.npmjs.org)
  4. pip install build
  5. python3 npm/scripts/bump_version.py <platform>   # rewrite the platform's package.json to pyproject.toml version
  6. python3 npm/scripts/bump_version.py main         # rewrite main package.json (idempotent across all matrix jobs)
  7. python3 npm/scripts/build_platform.py <platform> --out npm/platforms/<platform>/python   # produces npm/platforms/<platform>/python/
  8. version-sync verify (RESEARCH §8 inline bash):
       PYVER=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
       NPMVER=$(node -e "console.log(require('./npm/package.json').version)")
       [ "$PYVER" = "$NPMVER" ] || (echo MISMATCH && exit 1)
  9. cd npm/platforms/<platform> && npm publish --access public
     env: NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

publish-main job: `needs: build-platform`, single ubuntu-latest runner. Steps:
  1. actions/checkout@v4
  2. actions/setup-node@v4 (registry-url)
  3. python3 npm/scripts/bump_version.py main
  4. cd npm && npm publish --access public
     env: NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

Workflow trigger:
  on:
    push:
      tags: ['v*']
    workflow_dispatch:   # manual dispatch for re-runs without retagging

ci.yml (existing) — already has `permissions: contents: read` and matrix jobs. Add a new
`version-sync` job: ubuntu-latest, one step that runs the same PYVER vs NPMVER check.
This job runs on every push/PR (not just tags).

NPM authentication: GitHub Actions secret NPM_TOKEN is read into NODE_AUTH_TOKEN env on
every step that runs `npm publish`. The token was created in M6-01 Task 0 and is an
Automation-class token (bypasses 2FA).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write .github/workflows/release.yml</name>
  <files>.github/workflows/release.yml</files>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §7 (Release Workflow — full section)
    - .planning/phases/M6-npm-wrapper/M6-PATTERNS.md ".github/workflows/release.yml (new)"
    - .github/workflows/ci.yml (existing matrix shape + secret reference pattern)
    - npm/scripts/build_platform.py (just authored in M6-03)
    - npm/scripts/bump_version.py (just authored in M6-03)
  </read_first>
  <action>
    Create .github/workflows/release.yml from scratch (M6-01 deleted the cargo-dist version). Structure:

    Top of file:
    - `name: Release`
    - `permissions: { contents: read }` (matches ci.yml lines 3-4 pattern).
    - `on: push: tags: ['v*']` plus `workflow_dispatch:` for manual re-runs.

    Two jobs.

    Job 1: `build-platform`. `strategy.fail-fast: false` (so one platform's failure doesn't cancel the others — we want to see all failures at once). `strategy.matrix.include`: 5 rows per the `<interfaces>` block. `runs-on: ${{ matrix.runner }}`. Steps:
    1. `uses: actions/checkout@v4`
    2. `uses: actions/setup-python@v5` with `python-version: "3.12"` (pinned per D-05; not matrix-varied).
    3. `uses: actions/setup-node@v4` with `node-version: "20"` and `registry-url: 'https://registry.npmjs.org'` and `scope: '@voss'` (sets up .npmrc for scoped publish).
    4. `run: python -m pip install --upgrade pip build` (build is required by build_platform.py:ensure_wheel; pinning a recent build version is fine).
    5. `name: Sync version` `run: python3 npm/scripts/bump_version.py main && python3 npm/scripts/bump_version.py ${{ matrix.npm-platform }}`. (Bumps the main + this platform's package.json to pyproject.toml's version.)
    6. `name: Verify version sync` — inline shell from `<interfaces>` (PYVER vs NPMVER); fails the job on mismatch.
    7. `name: Build platform artifact` `run: python3 npm/scripts/build_platform.py ${{ matrix.npm-platform }} --out npm/platforms/${{ matrix.npm-platform }}/python`. The script will print SITE_PACKAGES_SIZE_MB and exit 1 on SIZE_BUDGET_EXCEEDED, failing the job.
    8. `name: npm pack dry-run` `run: cd npm/platforms/${{ matrix.npm-platform }} && npm pack --dry-run 2>&1 | tee /tmp/pack.log && (grep -E 'unpacked size|package size' /tmp/pack.log || true)`. This logs the per-platform tarball size for audit (RESEARCH §14 Open Question 2). Non-fatal — informational only.
    9. `name: Publish platform package` `run: cd npm/platforms/${{ matrix.npm-platform }} && npm publish --access public`. `env: { NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }} }`.

    Job 2: `publish-main`. `needs: build-platform` (waits for all 5 platform jobs). `runs-on: ubuntu-latest`. Steps:
    1. `uses: actions/checkout@v4`
    2. `uses: actions/setup-python@v5` (`python-version: "3.12"`).
    3. `uses: actions/setup-node@v4` (same as platform job).
    4. `name: Sync version` `run: python3 npm/scripts/bump_version.py main`.
    5. `name: Verify version sync` (same inline check).
    6. `name: Publish @voss/cli` `run: cd npm && npm publish --access public`. `env: NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}`.

    Add a comment block at the top of the file explaining: this workflow REPLACES the cargo-dist release.yml; trigger is `v*` git tags; the workflow expects the @voss npm org + NPM_TOKEN secret to exist (claimed in M6-01); the SIZE_BUDGET_MB=300 gate lives in build_platform.py.

    Validate yaml shape with `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"` (PyYAML is in the existing pyproject [tool.poetry.dependencies] via M2). Reading the file via `cat` to confirm step names match the verify regex.
  </action>
  <verify>
    <automated>python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/release.yml')); assert d['name']=='Release'; trig=d.get(True) or d.get('on'); assert 'tags' in str(trig); jobs=d['jobs']; assert set(jobs.keys())=={'build-platform','publish-main'}; bp=jobs['build-platform']; mat=bp['strategy']['matrix']['include']; assert len(mat)==5; plats={r['npm-platform'] for r in mat}; assert plats=={'darwin-arm64','darwin-x64','linux-x64','linux-arm64','win32-x64'}; assert jobs['publish-main']['needs']=='build-platform' or 'build-platform' in jobs['publish-main']['needs']; src=open('.github/workflows/release.yml').read(); for tok in ['build_platform.py','bump_version.py','NPM_TOKEN','npm publish --access public','actions/checkout@v4','actions/setup-node@v4']: assert tok in src, tok; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - .github/workflows/release.yml exists and is valid YAML.
    - `on:` triggers on `push: tags: ['v*']` and `workflow_dispatch`.
    - `build-platform` job has a 5-row matrix exactly covering the D-13 triples with the runner mapping from RESEARCH §7.
    - `publish-main` job has `needs: build-platform`.
    - The workflow calls `build_platform.py`, `bump_version.py`, and `npm publish --access public`.
    - NPM_TOKEN is read from `secrets.NPM_TOKEN` as `NODE_AUTH_TOKEN`.
    - `actions/checkout@v4` and `actions/setup-node@v4` are present in both jobs.
    - The matrix has `fail-fast: false` so all platform failures surface together.
  </acceptance_criteria>
  <done>Release workflow is wired and yaml-valid. Trigger is the `v*` tag pattern. No execution yet — Task 3 exercises it via a test tag.</done>
</task>

<task type="auto">
  <name>Task 2: Add version-sync check to ci.yml</name>
  <files>.github/workflows/ci.yml</files>
  <read_first>
    - .github/workflows/ci.yml (existing full file)
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §8 (the inline version-sync shell snippet)
    - npm/package.json (to confirm the version field path)
  </read_first>
  <action>
    Append a new top-level job to .github/workflows/ci.yml named `npm-version-sync`. `runs-on: ubuntu-latest`. Steps:
    1. `uses: actions/checkout@v4`
    2. `uses: actions/setup-python@v5` with `python-version: "3.12"` (matches existing ci.yml setup-python pattern).
    3. `uses: actions/setup-node@v4` with `node-version: "20"`. (Node is needed only for `node -e "require..."`.)
    4. `name: Verify pyproject.toml and npm/package.json versions match` with a `run:` step that contains the inline shell from RESEARCH §8 (multi-line, plain `run: |` block). The script must:
       - Read `PYVER` from pyproject.toml via `python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"`.
       - Read `NPMVER` from npm/package.json via `node -e "console.log(require('./npm/package.json').version)"`.
       - If `$PYVER` != `$NPMVER`, echo `VERSION MISMATCH: pyproject.toml=$PYVER npm/package.json=$NPMVER`, then echo `Run: python3 npm/scripts/bump_version.py`, then `exit 1`.
       - Else echo `Version sync OK: $PYVER`.
       The literal substrings `PYVER=`, `NPMVER=`, `VERSION MISMATCH`, `bump_version.py`, and `exit 1` must all appear in the run block — the verify step greps for them.

    This job is independent of the existing stub/full matrix jobs and runs on every push + PR (the existing ci.yml `on:` block covers both). Do NOT modify any existing job in ci.yml; only append the new job at the end of the `jobs:` map.

    Note: at the moment M6-04 first commits this, pyproject.toml is `0.1.0` and npm/package.json is `0.0.0` (from M6-01). The CI job will FAIL until Task 4 runs `bump_version.py` and commits the new versions. This is intentional — it means the check is real, not vacuous. Task 4 includes the bump commit so the CI returns to green.
  </action>
  <verify>
    <automated>python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); assert 'npm-version-sync' in d['jobs']; vs=d['jobs']['npm-version-sync']; assert vs['runs-on']=='ubuntu-latest'; src=open('.github/workflows/ci.yml').read(); assert 'PYVER=' in src and 'NPMVER=' in src and 'bump_version.py' in src; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - .github/workflows/ci.yml has a new top-level job `npm-version-sync`.
    - Job runs on ubuntu-latest with setup-python 3.12 + setup-node 20.
    - Shell snippet contains both `PYVER=` and `NPMVER=` literals plus the `exit 1` mismatch branch.
    - Existing jobs in ci.yml are unchanged (diff shows only an addition at the end of `jobs:`).
  </acceptance_criteria>
  <done>Drift between pyproject.toml and npm/package.json is now caught on every push, not at release time.</done>
</task>

<task type="auto">
  <name>Task 3: Bump npm versions to 0.1.0 and dry-run validate the workflow locally</name>
  <files>npm/package.json, npm/platforms/darwin-arm64/package.json, npm/platforms/darwin-x64/package.json, npm/platforms/linux-x64/package.json, npm/platforms/linux-arm64/package.json, npm/platforms/win32-x64/package.json</files>
  <read_first>
    - npm/scripts/bump_version.py (M6-03)
    - pyproject.toml (confirm version is still 0.1.0 — should be, no bump has happened)
    - npm/package.json (currently 0.0.0 from M6-01)
  </read_first>
  <action>
    Run `python3 npm/scripts/bump_version.py` (no args = "all"). This rewrites npm/package.json from 0.0.0 to 0.1.0 and all 5 platform package.json files to 0.1.0. The script also rewrites optionalDependencies values in the main package.json to 0.1.0.

    Verify the result:
    - `node -e "const m=require('./npm/package.json'); console.log(m.version)"` prints `0.1.0`.
    - For each platform, `node -e "console.log(require('./npm/platforms/<plat>/package.json').version)"` prints `0.1.0`.
    - The main package.json's optionalDependencies entries are all pinned to `"0.1.0"`.

    Then run `act` (if installed) or skip — `act` is not a hard requirement. Instead, do a static workflow validation: parse release.yml + ci.yml with PyYAML and assert the structure invariants from Task 1's verify block plus Task 2's verify block. If `actionlint` is available on the host, run `actionlint .github/workflows/release.yml` and `actionlint .github/workflows/ci.yml` and surface any warnings to the user.

    Commit the version bumps. The ci.yml job from Task 2 will pass on the next push.

    Document the result in the plan output: confirm 0.0.0 -> 0.1.0 transition succeeded for all 6 manifests, and that optionalDependencies were also updated.
  </action>
  <verify>
    <automated>node -e "const m=require('./npm/package.json'); if(m.version!=='0.1.0') process.exit(1); for(const k of Object.keys(m.optionalDependencies)){ if(m.optionalDependencies[k]!=='0.1.0') {console.error('opt dep '+k+' = '+m.optionalDependencies[k]); process.exit(1);}} for(const p of ['darwin-arm64','darwin-x64','linux-x64','linux-arm64','win32-x64']){ const sp=require('./npm/platforms/'+p+'/package.json'); if(sp.version!=='0.1.0') {console.error(p+' = '+sp.version); process.exit(1);}} console.log('ok')" &amp;&amp; python3 -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml')); yaml.safe_load(open('.github/workflows/ci.yml'))"</automated>
  </verify>
  <acceptance_criteria>
    - npm/package.json version is "0.1.0".
    - All 5 platform package.json files have version "0.1.0".
    - The main package.json's optionalDependencies entries are all "0.1.0".
    - Both workflow files parse as valid YAML.
    - The version bumps are committed to git (git diff --stat shows 6 npm/*.json files modified).
  </acceptance_criteria>
  <done>All 6 npm manifests are at 0.1.0 matching pyproject.toml. The ci.yml version-sync gate will pass on the next push.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 4: Exercise the release workflow with a test tag</name>
  <what-built>
    Tasks 1-3 produced .github/workflows/release.yml and bumped npm/*.json to 0.1.0. The workflow has not yet been EXERCISED end-to-end against real GitHub Actions runners. This checkpoint asks the user to push a test tag, watch the workflow run, and confirm all 6 packages publish at the test version before the real v0.1.0 publish in M6-05.
  </what-built>
  <how-to-verify>
    1. Bump pyproject.toml [project] version temporarily to a pre-release marker: `0.1.0rc1` (Python PEP 440 pre-release) which maps to npm `0.1.0-rc.1` (semver pre-release). Edit pyproject.toml to `version = "0.1.0rc1"`. Note: npm and PyPI semver disagree on pre-release format — Python uses `rcN`, npm uses `-rc.N`. The cleanest fix is to use a different pre-release path for npm: edit npm/scripts/bump_version.py temporarily (or accept that pyproject.toml = `0.1.0rc1` and the npm side will end up as `0.1.0rc1` which IS valid npm semver too because npm accepts non-strict versions). Simpler: bump pyproject.toml to `0.1.0` and use a git tag suffix only (`v0.1.0-test1`); the workflow fires on `v*` so it triggers, and the published package.json still says `0.1.0`. But that would clobber the real 0.1.0 namespace. CLEANEST APPROACH: bump pyproject.toml to `0.0.1` for the test cycle (the actual semver), run bump_version.py to sync, commit, tag `v0.0.1-test1`, push tag, watch workflow, then after success revert pyproject.toml to `0.1.0`, re-run bump_version.py, commit, and that becomes the real release commit.

    2. Push the test tag: `git push origin v0.0.1-test1` (or whatever the chosen test version is).

    3. Watch the workflow at https://github.com/<owner>/<repo>/actions. Expected duration: ~10-25 minutes (PBS download per platform ~30s, wheel build + pip install ~3-5 min per platform, npm publish ~1-3 min per package). All 5 platform jobs run in parallel; publish-main waits for them.

    4. Inspect each platform job's logs:
       - Confirm `SITE_PACKAGES_SIZE_MB=` is printed and is below the budget for ALL 5 (M6-03's host build only proved 1).
       - Confirm `npm pack --dry-run` size output is reasonable for each platform.
       - Confirm `npm publish` exits 0 for each.

    5. After all jobs succeed, verify via `npm view`:
       - `npm view @voss/cli versions` includes the test version.
       - `npm view @voss/cli-darwin-arm64 versions` includes the test version.
       - (etc. for the other 4)

    6. Sanity test a fresh install (any one platform):
       `mkdir /tmp/voss-test-install && cd /tmp/voss-test-install && npm init -y && npm i @voss/cli@<test-version> && npx voss --help`
       Expected: prints voss help text, exits 0.

    7. If anything failed, surface the failure mode and DO NOT proceed to revert pyproject.toml. Diagnose, fix, push another test tag.

    8. If everything passed, revert pyproject.toml to `0.1.0`, re-run `python3 npm/scripts/bump_version.py`, commit. Do NOT push the `v0.1.0` real tag yet — M6-05 is the final smoke gate.
  </how-to-verify>
  <acceptance_criteria>
    - A test tag (e.g. v0.0.1-test1 or v0.1.0-rc1) was pushed and triggered the workflow.
    - All 5 build-platform jobs exited 0.
    - The publish-main job exited 0.
    - `npm view @voss/cli versions` lists the test version.
    - `npm view @voss/cli-<plat> versions` lists the test version for all 5 triples.
    - A fresh `npm i @voss/cli@<test-version> && npx voss --help` works on at least one host.
    - pyproject.toml is back at 0.1.0 (or whatever the real ship version is) and all 6 npm manifests are bumped in sync, ready for M6-05.
  </acceptance_criteria>
  <resume-signal>Reply "release workflow green at version <X>", or "failed at <step>: <details>".</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GitHub Actions runner -> npm registry | NPM_TOKEN crosses this boundary on every publish step. |
| GitHub Actions runner -> astral-sh GitHub releases (PBS) | Outbound HTTPS to a third-party for the interpreter tarball. |
| GitHub Actions runner -> PyPI | Outbound HTTPS for transitive C-extension wheels during `pip install`. |
| Git tag push -> workflow trigger | Anyone with push access to the repo can trigger a real publish. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M6-04-01 | Information Disclosure | NPM_TOKEN leaks in workflow logs | mitigate | GitHub Actions automatically masks secret values from log output. Never `echo $NPM_TOKEN`. Never `set -x` near publish steps. NPM_TOKEN is referenced only via `${{ secrets.NPM_TOKEN }}` in env blocks. |
| T-M6-04-02 | Elevation of Privilege | Anyone who can push to the repo can trigger a real publish | accept | Workflow fires on any `v*` tag. Mitigations are administrative: branch protection on master; workflow_dispatch should be gated by environment protection rules if higher assurance is needed (deferred for v0.1). Token is Automation-class, scoped to @voss org only. |
| T-M6-04-03 | Tampering | PBS tarball hash mismatch on a runner | mitigate | build_platform.py verifies sha256 against pbs_manifest.json. First-run captures hash; subsequent runs enforce. Cross-platform: each runner's first build captures its own triple's hash. |
| T-M6-04-04 | Tampering | Version mismatch between pyproject.toml and npm/package.json | mitigate | Two layers: (a) ci.yml `npm-version-sync` job runs on every push/PR; (b) release.yml step 6 fails the publish if a same-tag mismatch slipped through. |
| T-M6-04-05 | Denial of Service | A single platform job failure cancels the workflow before others complete | mitigate | `strategy.fail-fast: false` lets all 5 platforms run; user sees the full failure surface in one workflow run. |
| T-M6-04-06 | Tampering | A malicious PR adds an exfiltration step to release.yml between merge and tag | mitigate | Workflow YAML changes go through code review; branch protection requires PR approval on master. (Administrative.) |
</threat_model>

<verification>
- release.yml is valid YAML, has a 5-row matrix, has `needs: build-platform` on publish-main, references NPM_TOKEN, build_platform.py, bump_version.py, and `npm publish --access public`.
- ci.yml has the new `npm-version-sync` job with the PYVER/NPMVER shell check.
- All 6 npm manifests are at version 0.1.0 (matching pyproject.toml).
- A test tag has been pushed and the workflow ran green end-to-end, with all 6 packages visible in `npm view`.
</verification>

<success_criteria>
1. Release workflow exists, is YAML-valid, replaces the deleted cargo-dist file, and fires on `v*` tags.
2. Version-sync drift is caught on every push (ci.yml) and re-checked at release time (release.yml step 6).
3. The workflow was exercised end-to-end against a test tag and all 6 packages published.
4. pyproject.toml -> npm/package.json -> npm/platforms/*/package.json are all in lockstep at 0.1.0.
5. The supply-chain check (sha256 verify) ran successfully on each runner's PBS tarball at least once.
</success_criteria>

<output>
After completion, create .planning/phases/M6-npm-wrapper/M6-04-SUMMARY.md recording: workflow file structure, the test tag used + run URL, per-platform SITE_PACKAGES_SIZE_MB numbers from the workflow logs, per-platform npm pack sizes, any new sha256 entries written into pbs_manifest.json by runners, and a `pyproject.toml = X / npm/package.json = X` snapshot of the version after revert.
</output>
