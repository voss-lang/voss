---
phase: M6-npm-wrapper
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .github/workflows/release.yml          # DELETE (cargo-dist file)
  - .github/workflows/rust.yml              # MODIFY (freeze trigger to workflow_dispatch)
  - npm/package.json                        # CREATE (@voss/cli main, 0.0.0 placeholder)
  - npm/bin/voss.js                         # CREATE (stub — replaced by M6-02)
  - npm/platforms/darwin-arm64/package.json # CREATE (placeholder)
  - npm/platforms/darwin-x64/package.json   # CREATE (placeholder)
  - npm/platforms/linux-x64/package.json    # CREATE (placeholder)
  - npm/platforms/linux-arm64/package.json  # CREATE (placeholder)
  - npm/platforms/win32-x64/package.json    # CREATE (placeholder)
  - npm/README.md                           # CREATE (one-line placeholder so npm pack does not warn)
autonomous: false
requirements: [NPM-01]
must_haves:
  truths:
    - "`@voss` npm org exists and is owned by the project (manual human task confirmed)"
    - "`@voss/cli` 0.0.0 placeholder is published to npm (squat-proof)"
    - "All 5 `@voss/cli-<platform>-<arch>` 0.0.0 placeholders are published to npm"
    - "`.github/workflows/release.yml` no longer contains cargo-dist content (pushing a v* tag does not trigger a broken Rust release)"
    - "`npm/` directory shape exists at repo root with placeholder files matching RESEARCH §13"
  artifacts:
    - path: "npm/package.json"
      provides: "@voss/cli main package manifest (placeholder version 0.0.0, bin entry, optionalDependencies for 5 platforms)"
      contains: '"name": "@voss/cli"'
    - path: "npm/platforms/darwin-arm64/package.json"
      provides: "@voss/cli-darwin-arm64 placeholder manifest with os/cpu fields"
      contains: '"os": ["darwin"]'
    - path: "npm/platforms/darwin-x64/package.json"
      provides: "@voss/cli-darwin-x64 placeholder manifest"
      contains: '"name": "@voss/cli-darwin-x64"'
    - path: "npm/platforms/linux-x64/package.json"
      provides: "@voss/cli-linux-x64 placeholder manifest"
      contains: '"name": "@voss/cli-linux-x64"'
    - path: "npm/platforms/linux-arm64/package.json"
      provides: "@voss/cli-linux-arm64 placeholder manifest"
      contains: '"name": "@voss/cli-linux-arm64"'
    - path: "npm/platforms/win32-x64/package.json"
      provides: "@voss/cli-win32-x64 placeholder manifest with os=win32 cpu=x64"
      contains: '"os": ["win32"]'
    - path: "npm/bin/voss.js"
      provides: "Bin shim stub (real shim authored in M6-02)"
  key_links:
    - from: "npm/package.json"
      to: "npm/bin/voss.js"
      via: "bin entry"
      pattern: '"bin"\\s*:\\s*\\{\\s*"voss"\\s*:\\s*"bin/voss.js"'
    - from: "npm/package.json"
      to: "@voss/cli-<platform>-<arch> subpackages"
      via: "optionalDependencies"
      pattern: '"@voss/cli-darwin-arm64"'
---

<objective>
M6-01 is the Wave-0 prerequisite plan for the entire npm wrapper milestone. It performs three coupled actions: (1) reserves the `@voss` npm org and all 6 npm package names by publishing 0.0.0 placeholders, locking in D-12's scoped-fallback decision (the unscoped `voss` name is confirmed TAKEN per RESEARCH §1 — `@voss/cli` is the operative main-package name); (2) deletes the dead cargo-dist `.github/workflows/release.yml` and freezes `.github/workflows/rust.yml` so pushing a `v*` tag during M6-04 will not silently trigger a broken Rust release; (3) scaffolds the `npm/` directory tree at repo root per RESEARCH §13 with placeholder manifests that downstream plans (M6-02..M6-05) fill in.

Purpose: This plan exists because (a) name reservation is D-14's hard-locked first task, (b) the npm-org creation is a human-only step that must complete before any CI publish step can succeed, and (c) the cargo-dist workflow is a live foot-gun that would corrupt the first real v0.1 release if left in place (RESEARCH §11, Risk 5).

Output: A skeleton `npm/` tree, 6 published npm placeholders at version `0.0.0`, a deleted `release.yml`, and a frozen `rust.yml`. No functional shim, no PBS download, no wheel install yet — those land in M6-02..M6-04.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/M6-npm-wrapper/M6-CONTEXT.md
@.planning/phases/M6-npm-wrapper/M6-RESEARCH.md
@.planning/phases/M6-npm-wrapper/M6-PATTERNS.md
@.github/workflows/release.yml
@.github/workflows/rust.yml
@.github/workflows/ci.yml
@pyproject.toml
</context>

<sequencing>
**Task ordering is strict.** Task 0 is a `checkpoint:human-action` [BLOCKING] gate. Tasks 1, 2, 3, and 4 MUST NOT begin until Task 0 returns the resume-signal "org ready" (or "different scope" with a substitution). The four auto tasks are at the scope_sanity warning threshold (4 auto tasks in one plan), but they are NOT split because D-14 requires atomic name-claim-and-scaffold within a single plan: deleting cargo-dist (Task 1), scaffolding the npm tree (Task 2), re-verifying availability (Task 3), and publishing placeholders (Task 4) form one indivisible operation — splitting them would create a window where an attacker could claim `@voss/cli` between scaffold and publish. The sequencing is therefore: Task 0 (human) → Task 1 → Task 2 → Task 3 → Task 4 (strict linear order; no parallelism within this plan).
</sequencing>

<tasks>

<task type="checkpoint:human-action" gate="blocking">
  <name>Task 0: Human creates @voss npm organization (BLOCKING prerequisite)</name>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §1 "Org creation" and §14 Open Question 4
    - .planning/phases/M6-npm-wrapper/M6-CONTEXT.md D-12, D-14
  </read_first>
  <what-built>
    Nothing yet. Claude cannot create an npm organization — it requires a browser login at npmjs.com with the user's account. This checkpoint blocks all subsequent tasks in M6 until the human confirms the org exists.
  </what-built>
  <how-to-verify>
    Human must complete these steps at https://www.npmjs.com:
    1. Log in (or create an npm account if none exists for the user).
    2. Create a new organization named exactly `voss` (the scope becomes `@voss`). Free tier is sufficient — no paid plan needed for public scoped packages.
    3. Create an "Automation" token (Account → Access Tokens → Generate New Token → Automation). Automation tokens bypass 2FA, which is required for CI publish.
    4. Add the token to the GitHub repository's Actions secrets as `NPM_TOKEN` (Settings → Secrets and variables → Actions → New repository secret). Scope = repository.
    5. Sanity-check at terminal: `curl -s https://registry.npmjs.org/-/org/voss/user | head -1` should NOT return a 404. Anonymous registry GET against an org may still 404 by design — the authoritative check is logging into npmjs.com and seeing the org dashboard.
    6. Confirm `npm view @voss/cli` returns a 404 (E404 — name still available) — this is required so the placeholder publish in Task 4 succeeds.
  </how-to-verify>
  <acceptance_criteria>
    - npmjs.com shows an `@voss` organization the user owns or has publish access to.
    - GitHub Actions secret `NPM_TOKEN` exists in the repo and is an Automation-class token from the @voss org.
    - `npm view @voss/cli` returns a 404 / E404 (name still unclaimed; placeholder publish path is clear).
  </acceptance_criteria>
  <resume-signal>Type "org ready" to proceed, "not yet" to pause, or "different scope" with a replacement scope name (e.g. `@vosshq`) if `@voss` is unavailable.</resume-signal>
</task>

<task type="auto">
  <name>Task 1: Delete cargo-dist release.yml and freeze rust.yml</name>
  <read_first>
    - .github/workflows/release.yml (full file — confirm it is cargo-dist)
    - .github/workflows/rust.yml (full file — confirm trigger shape)
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §11 "Existing release.yml Deletion"
    - .planning/phases/M6-npm-wrapper/M6-PATTERNS.md "release.yml (old) — DELETE" and "rust.yml — DISABLE/DELETE"
  </read_first>
  <action>
    Delete `.github/workflows/release.yml` entirely (it is the cargo-dist workflow that would fire on `push: tags: ['v*']` and try to build Rust artifacts — RESEARCH §11 confirms this file is 100% dead per the frozen-spike decision). Use `git rm` so the deletion is staged. Then edit `.github/workflows/rust.yml`: replace the existing `on:` block (currently `push` + `pull_request` to master/main per PATTERNS.md) with `on: workflow_dispatch:` only. This freezes Rust CI without deleting the workflow file — it stays in source control and can be manually re-triggered if the frozen spike is ever revisited. Do NOT touch any `cargo` references inside `rust.yml` body; only the trigger changes. Do NOT delete `Cargo.toml`, `Cargo.lock`, `crates/`, or `dist-workspace.toml` in this plan — those are out of scope (RESEARCH §14 Open Question 6).
  </action>
  <verify>
    <automated>test ! -f .github/workflows/release.yml &amp;&amp; grep -E '^on:[[:space:]]*$|workflow_dispatch:' .github/workflows/rust.yml &amp;&amp; ! grep -E '^\s+push:|^\s+pull_request:' .github/workflows/rust.yml</automated>
  </verify>
  <acceptance_criteria>
    - `.github/workflows/release.yml` does not exist (git status shows it deleted).
    - `.github/workflows/rust.yml` exists; its `on:` block contains only `workflow_dispatch:` (no `push:` or `pull_request:` triggers).
    - No other `.github/workflows/*.yml` file is modified.
    - `git diff --stat` shows exactly two workflow files changed: one deletion, one trigger-edit.
  </acceptance_criteria>
  <done>Cargo-dist file is gone; rust.yml fires only on manual dispatch. Pushing a `v*` tag in M6-04 will not invoke any pre-existing release machinery.</done>
</task>

<task type="auto">
  <name>Task 2: Scaffold npm/ directory with placeholder manifests</name>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §2 (esbuild main-package shape), §13 (file list)
    - .planning/phases/M6-npm-wrapper/M6-PATTERNS.md "npm/package.json", "npm/platforms/*/package.json"
    - .planning/phases/M6-npm-wrapper/M6-CONTEXT.md D-01..D-13
  </read_first>
  <action>
    Create the `npm/` subdir tree at repo root per RESEARCH §13. Files:

    - `npm/package.json` — version `0.0.0`, `"name": "@voss/cli"`, `"description"` reflecting the v0.1 framing line from README, `"bin": { "voss": "bin/voss.js" }`, `"engines": { "node": ">=18" }`, `"license": "MIT"` (match pyproject.toml license field; confirm by reading pyproject.toml), `"optionalDependencies"` listing all 5 `@voss/cli-<triple>` names pinned to `"0.0.0"`, and `"files": ["bin/", "README.md"]`. Add `"repository"` and `"homepage"` pointing to the existing repo URL (read from pyproject.toml or set to the repo's GitHub URL).
    - `npm/README.md` — one paragraph stating "This is the npm distribution of the Voss Python harness. Real install instructions ship with version >= 0.1.0; see the main repository README for v0.1 docs." This exists so `npm pack` does not warn about a missing README.
    - `npm/bin/voss.js` — stub: `#!/usr/bin/env node` shebang plus `console.error('voss: placeholder — real shim ships in 0.1.0'); process.exit(1);`. The real shim lands in M6-02. Mark executable (`chmod +x`) so npm pack preserves the bit; npm will also auto-generate `voss.cmd` on Windows installs from the `bin` entry.
    - `npm/platforms/<triple>/package.json` for all 5 triples (`darwin-arm64`, `darwin-x64`, `linux-x64`, `linux-arm64`, `win32-x64`). Each contains: `"name": "@voss/cli-<triple>"`, `"version": "0.0.0"`, `"os"` array (exactly one of `["darwin"]`, `["linux"]`, `["win32"]`), `"cpu"` array (exactly one of `["arm64"]`, `["x64"]`), `"files": ["python/"]`, `"description"`, `"license": "MIT"`, `"repository"`. Unix subpackages (4 of 5) include the postinstall chmod script from RESEARCH §10 (`"scripts": { "postinstall": "node -e \"const fs=require('fs'); const p=__dirname+'/python/bin/python3'; if(fs.existsSync(p)) fs.chmodSync(p, 0o755);\"" }`). The win32-x64 subpackage omits postinstall.

    Use plain `Path.write_text` + `json.dumps(data, indent=2)` to write the JSON files so they have a trailing newline and 2-space indent (matches RESEARCH §8's `bump_version.py` output format — this lets the M6-04 version-sync step produce identical diffs). Do NOT create `python/` subdirectories yet — those are populated at CI build time in M6-04. Do NOT create `npm/scripts/` files here — those land in M6-03 and M6-04.
  </action>
  <verify>
    <automated>node -e "const m=require('./npm/package.json'); if(m.name!=='@voss/cli'||m.version!=='0.0.0'||!m.bin.voss||Object.keys(m.optionalDependencies).length!==5) process.exit(1); for(const p of ['darwin-arm64','darwin-x64','linux-x64','linux-arm64','win32-x64']){const s=require('./npm/platforms/'+p+'/package.json'); if(s.name!=='@voss/cli-'+p||s.version!=='0.0.0'||!s.os||!s.cpu||!s.files.includes('python/')) {console.error('bad '+p);process.exit(1);}} console.log('ok');"</automated>
  </verify>
  <acceptance_criteria>
    - `npm/package.json` exists with name `@voss/cli`, version `0.0.0`, bin.voss = `bin/voss.js`, and 5 entries under optionalDependencies — each keyed exactly `@voss/cli-<triple>` with value `0.0.0`.
    - All 5 `npm/platforms/<triple>/package.json` files exist with matching `os`/`cpu` arrays (darwin-arm64 → os=[darwin] cpu=[arm64], etc.).
    - The 4 Unix subpackages include a `postinstall` script that chmods `python/bin/python3` to 0o755.
    - The win32-x64 subpackage has no `postinstall` script.
    - `npm/bin/voss.js` exists, has the `#!/usr/bin/env node` shebang, exits 1 with the placeholder warning when run.
    - `npm/README.md` exists.
  </acceptance_criteria>
  <done>The full `npm/` directory shape from RESEARCH §13 exists. Every JSON file is valid (parses with `node -e "require('./...')"`). The placeholder shim exits 1, signalling the package is unwired pending M6-02.</done>
</task>

<task type="auto">
  <name>Task 3: Verify name availability before publish</name>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §1 (npm name availability)
    - .planning/phases/M6-npm-wrapper/M6-CONTEXT.md D-12 (fallback to @voss/cli) and D-14 (reserve names IMMEDIATELY)
  </read_first>
  <action>
    Run `npm view <pkg>` for each of the 6 names to confirm they are still available (research was done on 2026-05-13; this task re-verifies on the actual publish day to catch any same-day squatting). Names to check: `@voss/cli`, `@voss/cli-darwin-arm64`, `@voss/cli-darwin-x64`, `@voss/cli-linux-x64`, `@voss/cli-linux-arm64`, `@voss/cli-win32-x64`. Each should return `npm error code E404` ("Not found"). Also confirm the unscoped `voss` name is still TAKEN by `shawn_xu` (RESEARCH §1 fingerprint) — if for some reason it has been deleted and is now available, surface that finding to the user before proceeding, because the user's stated preference was the unscoped name (CONTEXT specifics). If all 5 @voss/cli-* names + @voss/cli are confirmed available, write a brief manifest at `.planning/phases/M6-npm-wrapper/npm-name-claim-precheck.txt` recording the date/time and the verified-available list. If ANY of the 6 names is no longer available, STOP and emit a `## ⚠ Name Conflict` block to the user — do not proceed to Task 4.
  </action>
  <verify>
    <automated>for n in '@voss/cli' '@voss/cli-darwin-arm64' '@voss/cli-darwin-x64' '@voss/cli-linux-x64' '@voss/cli-linux-arm64' '@voss/cli-win32-x64'; do (npm view "$n" version 2>&amp;1 | grep -qE 'E404|404 Not Found|404 not found' || (echo "TAKEN: $n"; exit 1)) || exit 1; done; test -f .planning/phases/M6-npm-wrapper/npm-name-claim-precheck.txt</automated>
  </verify>
  <acceptance_criteria>
    - All 6 `npm view` calls return E404 (name available).
    - `npm view voss version` returns a non-404 (still taken — confirms D-12 fallback path is unchanged).
    - `.planning/phases/M6-npm-wrapper/npm-name-claim-precheck.txt` is committed with timestamp + list.
  </acceptance_criteria>
  <done>Same-day name availability re-verified. Any squatting since 2026-05-13 surfaces here, before any publish.</done>
</task>

<task type="auto">
  <name>Task 4: Publish 0.0.0 placeholder packages to claim names</name>
  <read_first>
    - .planning/phases/M6-npm-wrapper/M6-RESEARCH.md §1 (scoped publish requires --access public) and §7 (NPM_TOKEN handling)
    - .planning/phases/M6-npm-wrapper/M6-CONTEXT.md D-14 (claim immediately)
    - npm/package.json (just created in Task 2)
  </read_first>
  <action>
    Authenticate npm CLI to the Automation token from Task 0. The canonical approach: write `NPM_TOKEN=<token>` to a `~/.npmrc` line in the form `//registry.npmjs.org/:_authToken=${NPM_TOKEN}`, or invoke `npm publish` with `NODE_AUTH_TOKEN` env var set (matches the release workflow). Do NOT echo the token. Publish in this order:
    1. The 5 platform subpackages first: `cd npm/platforms/<triple> &amp;&amp; npm publish --access public`. Each must exit 0. Platform packages have NO files beyond `package.json` at this stage (the `files: ["python/"]` entry resolves to nothing because `python/` does not exist — `npm publish` packs whatever exists; that is fine for a placeholder, the published tarball is essentially empty).
    2. The main `@voss/cli` package last: `cd npm &amp;&amp; npm publish --access public`. This is published last so its optionalDependencies references can resolve (npm does not require this strictly, but it makes the dependency graph internally consistent at publish time).
    Verify each publish with `npm view <pkg> version` returning `0.0.0` afterwards. Record the publish manifest at `.planning/phases/M6-npm-wrapper/npm-name-claim.txt` with each `npm publish` output's tarball SHA (the `Tarball Hash` line) for audit. Delete `~/.npmrc` after publish completes (or unset NODE_AUTH_TOKEN) — do not leave credentials on disk.
  </action>
  <verify>
    <automated>for n in '@voss/cli' '@voss/cli-darwin-arm64' '@voss/cli-darwin-x64' '@voss/cli-linux-x64' '@voss/cli-linux-arm64' '@voss/cli-win32-x64'; do v=$(npm view "$n" version 2>/dev/null) || exit 1; [ "$v" = "0.0.0" ] || (echo "expected 0.0.0 got $v for $n"; exit 1); done; test -f .planning/phases/M6-npm-wrapper/npm-name-claim.txt</automated>
  </verify>
  <acceptance_criteria>
    - `npm view @voss/cli version` returns `0.0.0`.
    - All 5 `npm view @voss/cli-<triple> version` calls return `0.0.0`.
    - The 6 names are now owned by the `@voss` org and cannot be claimed by anyone else.
    - `.planning/phases/M6-npm-wrapper/npm-name-claim.txt` is committed with tarball SHAs for each publish.
    - No npm token or `.npmrc` file remains on disk after the task completes.
  </acceptance_criteria>
  <done>6 names reserved at 0.0.0. M6-04's release workflow can later publish the real 0.1.0 artifacts to these claimed names without squatting risk.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| local repo → npm registry | Outbound publish carries credentials and package contents to a third-party registry. |
| GitHub repo → GitHub Actions runner | Future M6-04 workflows read `NPM_TOKEN` from secret store; M6-01 only writes the secret, never reads it from CI. |
| developer machine → ~/.npmrc | Temporary credential file holds the publish token during Task 4. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M6-01-01 | Information Disclosure | NPM_TOKEN handling in Task 4 | mitigate | Use `NODE_AUTH_TOKEN` env var, never echo, delete `~/.npmrc` after publish, never commit `.npmrc` to repo. CI path uses GitHub Actions secret which is masked in logs by default. |
| T-M6-01-02 | Tampering | npm name squatting between research (2026-05-13) and publish day | mitigate | Task 3 re-runs `npm view` for all 6 names same-day before any publish; halts and surfaces conflict if any name is taken. |
| T-M6-01-03 | Spoofing | Anyone claiming `@voss/cli` if org creation lapses | mitigate | Org+placeholder publish completes within this single plan; D-14 ordering ensures no window between org creation and name claim. Org owned by user's npm account; 2FA on account recommended. |
| T-M6-01-04 | Denial of Service | Stale `.github/workflows/release.yml` triggers cargo-dist on first v* tag in M6-04 | mitigate | Task 1 deletes the file entirely; verify step confirms absence. RESEARCH §11 and Risk 5 explicitly call out this foot-gun. |
| T-M6-01-05 | Elevation of Privilege | Compromised Automation token publishes malicious package to @voss org | accept | v0.1 risk; future-work mitigations (sigstore, provenance, signed wheels) are explicitly deferred per RESEARCH/CONTEXT "deferred ideas". Token rotation is the v0.1 control. |
</threat_model>

<verification>
After all 4 tasks complete:
- `git status` shows: `release.yml` deleted; `rust.yml` modified (trigger only); 9 new files under `npm/`; 2 new files under `.planning/phases/M6-npm-wrapper/` (`npm-name-claim-precheck.txt`, `npm-name-claim.txt`).
- All 6 npm packages return `0.0.0` from `npm view <pkg> version`.
- No grep hit for `NPM_TOKEN` or any token literal anywhere in committed files.
- `npm pack npm/` (dry-run) succeeds and produces a tarball <50KB (placeholder only — no python/, no real shim yet).
</verification>

<success_criteria>
1. The 6 npm names are claimed by the `@voss` org at version 0.0.0.
2. The cargo-dist workflow is gone; pushing `v0.1.0-test` in M6-04 will not trigger it.
3. The `npm/` directory tree exists with valid placeholder manifests that downstream plans can extend without redoing scaffolding work.
4. The `@voss` npm org exists, owned by the user, with an Automation token stored as `NPM_TOKEN` GitHub Actions secret.
5. No credentials leak into the repo or the local filesystem.
</success_criteria>

<output>
After completion, create `.planning/phases/M6-npm-wrapper/M6-01-SUMMARY.md` recording: org confirmation, 6 names claimed (with tarball SHAs from npm-name-claim.txt), deleted/modified workflow files, scaffolded npm tree, and any deviations from the plan (e.g. if a name was unavailable and a fallback scope was used).
</output>
