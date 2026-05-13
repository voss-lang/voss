# M6-01 Summary — Wave-0 Bootstrap

**Status:** ✅ Complete
**Date:** 2026-05-13
**Plan:** [M6-01-PLAN.md](./M6-01-PLAN.md)
**Operator:** Claude Code (execute-plan)

## What Shipped

### Org & names claimed
- npm org **`vosslang`** owned by user `bm97` on npmjs.com (free tier).
- Six npm package names reserved at version `0.0.0`:
  - `@vosslang/cli`
  - `@vosslang/cli-darwin-arm64`
  - `@vosslang/cli-darwin-x64`
  - `@vosslang/cli-linux-x64`
  - `@vosslang/cli-linux-arm64`
  - `@vosslang/cli-win32-x64`
- Tarball SHAs recorded in `npm-name-claim.txt`.

### Workflow changes
- **Deleted:** `.github/workflows/release.yml` (cargo-dist, dead per RESEARCH §11).
- **Frozen:** `.github/workflows/rust.yml` — trigger reduced to `workflow_dispatch:` only.
- **Untouched:** `Cargo.toml`, `Cargo.lock`, `crates/`, `dist-workspace.toml` (out of scope per RESEARCH §14 Open Question 6).

### npm/ scaffold (9 files)
```
npm/
├── README.md              # one-paragraph placeholder
├── bin/voss.js            # stub shim, exit 1, executable (755)
├── package.json           # @vosslang/cli 0.0.0, 5 optionalDependencies
└── platforms/
    ├── darwin-arm64/package.json   # os=darwin cpu=arm64 + postinstall chmod
    ├── darwin-x64/package.json     # os=darwin cpu=x64  + postinstall chmod
    ├── linux-arm64/package.json    # os=linux  cpu=arm64 + postinstall chmod
    ├── linux-x64/package.json      # os=linux  cpu=x64  + postinstall chmod
    └── win32-x64/package.json      # os=win32  cpu=x64  (NO postinstall)
```

### Planning artifacts
- `.planning/phases/M6-npm-wrapper/npm-name-claim-precheck.txt` — Task 3 pre-publish availability check.
- `.planning/phases/M6-npm-wrapper/npm-name-claim.txt` — Task 4 post-publish tarball SHAs.

## Deviations from Plan

| # | Deviation | Reason | Resolution |
|---|-----------|--------|------------|
| D-1 | Scope `@voss` → `@vosslang` | Org `voss` already claimed on npmjs.com on publish day (D-12 confirmed unscoped name was already taken; new finding: scoped org was also taken) | Used plan's resume-signal "different scope" path. All 6 package names re-threaded to `@vosslang/cli*`. All plan key_links, artifacts.contains assertions, and verify steps were satisfied under the substituted scope. |
| D-2 | Task 4 method: GH Actions one-shot tried, fell back to local | GitHub Actions minutes quota exhausted on private repo (all runs failing with 0 billable ms, no steps recorded). Detected via `gh api .../jobs` returning empty `steps: []` and 0 duration_ms. | Created and pushed `.github/workflows/publish-placeholders.yml`, dispatched, observed failure, then `git rm`'d the workflow (commit `f9245b5`). Switched to local `npm publish` per plan's documented approach. |
| D-3 | Initial Granular token lacked "Bypass 2FA" | User generated first token without the Bypass 2FA checkbox enabled. Resulted in E403 "Two-factor authentication or granular access token with bypass 2fa enabled is required to publish packages" even with web-login session active. | User regenerated token with Bypass 2FA ☑. Account 2FA is WebAuthn passkey-only; passkey cannot be exercised via npm CLI for publish (CLI only supports `--otp` TOTP), so a Bypass-2FA Granular token is the only viable publish path for this account. |
| D-4 | Token entered conversation transcript | User chose "paste token" path over "write npmrc yourself" for speed. | Operator wrote `~/.npmrc` line, ran 6 publishes, then restored the pre-existing web-login `~/.npmrc` from a `~/.npmrc.bak.voss-m6-01` snapshot. User is responsible for revoking the bypass token at npmjs.com (or letting it expire in 7 days). Token value should be considered exposed in the conversation transcript and should not be reused. |
| D-5 | Test-publish "successful" output was misleading | An early `npm publish --json` call for `@vosslang/cli-darwin-arm64` output a complete tarball metadata block (integrity, shasum, filename) but the registry showed E404 on `npm view`. JSON output reflects local pack metadata, not registry write acknowledgment. Required a republish (which then returned "cannot publish over previously published versions: 0.0.0" — confirming the original publish HAD registered but CDN propagation was slow). | Waited ~30s for CDN; `npm view` then resolved to `0.0.0`. All 6 names verified at 0.0.0. |

## Success Criteria — All Met

1. ✅ Six npm names claimed by `@vosslang` org at version 0.0.0 (verified via `npm view <pkg> version`).
2. ✅ Cargo-dist `release.yml` deleted; pushing `v*` tags will not trigger any pre-existing release machinery.
3. ✅ `npm/` directory tree exists with valid placeholder manifests; `node -e "require('./npm/package.json')"` and per-platform requires parse cleanly.
4. ✅ `@vosslang` npm org exists, owned by `bm97`; `NPM_TOKEN` GitHub Actions secret in place (see open follow-ups about the secret's Bypass-2FA flag).
5. ✅ No credentials remain in repo files. `grep -r NPM_TOKEN .` returns no token literals. `~/.npmrc` restored to pre-task web-login state.

## Files Changed (final)

| Status | Path |
|--------|------|
| Deleted | `.github/workflows/release.yml` |
| Modified | `.github/workflows/rust.yml` (trigger → `workflow_dispatch:`) |
| Added | `npm/package.json` |
| Added | `npm/README.md` |
| Added | `npm/bin/voss.js` |
| Added | `npm/platforms/darwin-arm64/package.json` |
| Added | `npm/platforms/darwin-x64/package.json` |
| Added | `npm/platforms/linux-x64/package.json` |
| Added | `npm/platforms/linux-arm64/package.json` |
| Added | `npm/platforms/win32-x64/package.json` |
| Added | `.planning/phases/M6-npm-wrapper/npm-name-claim-precheck.txt` |
| Added | `.planning/phases/M6-npm-wrapper/npm-name-claim.txt` |
| Added | `.planning/phases/M6-npm-wrapper/M6-01-SUMMARY.md` |

Intermediate commits during execution:
- `eb647c7` chore(release): remove outdated release workflow configuration
- `f009f00` chore(workflow): update Rust CI configuration to use workflow_dispatch (also contains npm scaffold + precheck.txt — bundled by an auto-commit hook; sub-optimal grouping but content correct)
- `9754e82` ci(M6-01): add one-shot publish-placeholders workflow (later reverted)
- `f9245b5` revert(M6-01): remove publish-placeholders workflow

## Open Follow-Ups for User

1. **Revoke local bypass-2FA token** at https://www.npmjs.com/settings/bm97/tokens (delete the `Voss` Granular token used for local publish). Or let it expire in 7 days. This token's value entered the conversation transcript and must not be reused.
2. **Re-enable "Require 2FA for write actions"** at https://www.npmjs.com/settings/bm97/tfa (was toggled off during a failed troubleshooting attempt; was not the operative fix). This pref does not affect Bypass-2FA tokens, so future CI publishes still work.
3. **Verify the GitHub `NPM_TOKEN` secret was generated with Bypass 2FA enabled** — the token in the GH secret is the one user generated first (per chat history, the form screenshot suggested the Bypass-2FA box was unchecked on the first attempt; the second granular token user generated for local publish DID have it checked). If the GH secret's token lacks Bypass 2FA, M6-04's CI publish will fail. Recommendation: revoke and regenerate the GH secret using the now-confirmed correct flag, before M6-04 begins.
4. **License file missing** — `pyproject.toml` has no `license` field and there is no `LICENSE` file at repo root. The npm placeholder manifests declare `"license": "MIT"` per plan. Either add a `LICENSE` file (MIT or chosen) before M6-04 publishes the real 0.1.0, or change the npm manifests' license string to match the actual license intent. Currently a discrepancy.

## Scope-Sanity Notes for M6-02

- All 6 placeholder publishes are 0.0.0 with essentially empty tarballs (410–631 bytes; only `package.json`). When M6-02 lands real shim content, it will publish 0.0.1 or 0.1.0 — both are higher than 0.0.0, so SemVer ordering puts the placeholders below the real release. Users running `npm install -g @vosslang/cli` will receive the real version by default.
- The 5 platform packages have `"files": ["python/"]` but no `python/` directory exists yet. The placeholder tarballs are therefore effectively empty (no python payload). This is expected — M6-04 populates `python/` at build time.
