# Security Audit Report — Voss

**Date:** 2026-06-09
**Scope:** Quick Scan (11 categories: 1, 2, 3, 4, 5, 12, 15, 27, 31, 42, 65)
**Stack:** Python harness (FastAPI+SSE server, litellm/anthropic/openai, keyring) + Rust crates + Tauri/Solid app + pnpm monorepo + GitHub Actions + Docker

---

## Summary

- **Overall Risk:** Medium
- **Findings:** 0 Critical, 0 High, 14 Medium, 1 Low
- **Standards:** CWE Top 25 (2025), OWASP Top 10 (2025), CVSS 4.0
- **scan_mode:** Quick | **subagent_dispatch:** true (4 parallel batches)
- **scan_mode_detected_features:** FastAPI+SSE harness server, anthropic/openai/litellm SDKs, keyring credential storage, OAuth (codex) auth flow, pyyaml, rusqlite, xterm.js frontend, 6 GitHub Actions workflows, Dockerfile, pnpm/uv/Cargo lockfiles
- **recheck_candidates:** `.github/workflows/ci.yml:39,40,146,174`, `.github/workflows/rust.yml:37,40`, `.github/workflows/publish-container.yml:34,38,46,60,69`, `.github/workflows/mcp-integration.yml:17,18,23`, `.github/workflows/haskell-frontend.yml:24`, `voss/harness/tools.py:716`

## Scan Comparison

Previous scan 2026-05-27 (Full, 32 cats): 5 findings (1 Critical, 0 High, 2 Medium, 2 Low) | This scan: 15

- **Resolved (verified):** "CI/CD tag pins on release workflow" — `release.yml` now pins all actions to commit SHA (e.g. `actions/checkout@de0fac2e…`). Confirmed as a Pass this scan.
- **Not re-checked this run (out of Quick-Scan scope):** the prior Critical (Rust `shell_run` metacharacter guard, Cat 10) and PostHog consent / CSP items. Note: the Python sandbox now enforces metacharacter rejection + allowlist (`voss/harness/sandbox.py:43-73`); re-verify the Rust port in a Cat 10 scan.
- **New:** 13 tag-pin findings in the five *non-release* workflows, 1 agent SSRF gap, 1 unpinned service image.

---

## Medium Findings

### 1. GitHub Actions pinned by tag, not commit SHA (13 occurrences)

- **Severity:** Medium | CVSS 4.0: ~5.8
- **CWE:** CWE-426 (Untrusted Search Path) / supply-chain workflow hijack
- **OWASP:** A08:2025 Software & Data Integrity Failures
- **Risk:** A force-pushed or re-tagged action version runs attacker code in CI at next trigger. Highest stakes in `publish-container.yml`, which holds GHCR login credentials and signs build provenance — a hijacked `docker/login-action` or `build-push-action` could exfiltrate registry credentials or inject malicious image layers with valid attestation.
- **Shared fix:** Pin every `uses:` to a full commit SHA with a version comment, exactly as `release.yml` already does (e.g. `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2`). Dependabot is already configured for action bumps (monthly + 3-day cooldown), so SHA pins stay maintained automatically.
- **Priority:** P2 | **Confidence:** High | **Author:** Ben

| File | Line | Action |
|---|---|---|
| `.github/workflows/ci.yml` | 39 | `actions/checkout@v6.0.2` |
| `.github/workflows/ci.yml` | 40 | `actions/setup-python@v6` |
| `.github/workflows/ci.yml` | 174 | `actions/setup-node@v6` |
| `.github/workflows/rust.yml` | 37 | `dtolnay/rust-toolchain@stable` (branch ref — least reproducible) |
| `.github/workflows/rust.yml` | 40 | `Swatinem/rust-cache@v2` |
| `.github/workflows/publish-container.yml` | 34 | `docker/setup-buildx-action@v4` |
| `.github/workflows/publish-container.yml` | 38 | `docker/login-action@v4` (holds GHCR creds) |
| `.github/workflows/publish-container.yml` | 46 | `docker/metadata-action@v6` |
| `.github/workflows/publish-container.yml` | 60 | `docker/build-push-action@v7` |
| `.github/workflows/publish-container.yml` | 69 | `actions/attest-build-provenance@v4` (signs provenance) |
| `.github/workflows/mcp-integration.yml` | 17 | `actions/checkout@v6.0.2` |
| `.github/workflows/mcp-integration.yml` | 18 | `actions/setup-python@v6` |
| `.github/workflows/mcp-integration.yml` | 23 | `actions/setup-node@v6` |
| `.github/workflows/haskell-frontend.yml` | 24 | `haskell-actions/setup@v2` |

### 2. Agent `web_fetch` tool has no URL validation (private-range / metadata reachability)

- **Severity:** Medium | CVSS 4.0: ~5.3
- **CWE:** CWE-918 (Server-Side Request Forgery)
- **OWASP:** A10:2025 SSRF
- **File:** `voss/harness/tools.py:716`
- **Evidence:**
  ```python
  async def web_fetch(url: str, timeout_s: float = 30.0) -> str:
      if net is None:
          return ("<error: net disabled: set tools.allow_net = true in "
                  "harness.toml or pass --allow-net>")
      return await net.fetch(url, timeout_s=timeout_s)
  ```
- **Input trace:** URL originates from the LLM agent's tool call and reaches `net.fetch()` with no parsing, allow-list, or private-IP rejection. Mitigations on the path: tool gated behind `tools.allow_net` opt-in; harness server is localhost-bound and bearer-token-protected. Source classification: **un-traceable beyond the model** (LLM-generated, indirectly steerable by prompt-injected content the agent reads) → reported at reduced confidence.
- **Risk:** A prompt-injected agent (e.g. via fetched page content or repo files) can be steered to request `169.254.169.254`, `localhost` services, or private-range hosts and feed the response back into the model context.
- **Fix:** In `web_fetch` (or `net.fetch`): parse with `urllib.parse.urlparse`, reject loopback/link-local/private ranges (`127.0.0.0/8`, `169.254.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `::1`, `fc00::/7`) and non-http(s) schemes; optionally add a config allow-list.
- **Priority:** P2 | **Confidence:** Medium — needs human verification (is local-network fetch ever intended?)
- **Author:** Ben

## Low Findings

### 3. Unpinned `ollama/ollama:latest` service image in CI

- **Severity:** Low | CVSS 4.0: ~3.5
- **CWE:** CWE-1357 (Reliance on Insufficiently Trustworthy Component)
- **File:** `.github/workflows/ci.yml:146`
- **Evidence:** `image: ollama/ollama:latest`
- **Risk:** Next CI run silently pulls whatever the registry serves — non-reproducible, and a compromised tag runs in CI.
- **Fix:** Pin to a version tag or digest; let Dependabot bump it.
- **Priority:** P3 | **Confidence:** High | **Author:** Ben

---

## Validation Signals

### VS-001 Reproducibility Hooks
- **Status:** pass | **Category Links:** 4, 5, 15
- **Evidence:** `tests/harness/` contains `test_auth.py`, `test_auth_persistence.py`, `test_oauth_provider.py`, `test_server_app.py`, `test_sandbox.py`, `test_sandbox_fuzz.py` — risky paths (auth, server, shell sandbox) have dedicated suites.
- **Confidence:** high

### VS-002 Negative Testing Coverage
- **Status:** pass | **Category Links:** 15
- **Evidence:** `tests/harness/test_sandbox.py:38-59` — adversarial cases assert denial: `"wget http://x", # not in allowlist`, `assert not ok, f"should deny: {cmd}"`, pipeline-exfil cases; plus `test_sandbox_fuzz.py`.
- **Confidence:** high

### VS-003 Fix Verification Path
- **Status:** pass | **Category Links:** 31
- **Evidence:** `.github/workflows/ci.yml:58` runs `pytest -q -m "not live" --cov=voss_runtime` on every push/PR; live-marked tests at line 158; Rust + frontend jobs in sibling workflows.
- **Confidence:** high

### VS-005 Sensitive Flow Traceability
- **Status:** pass | **Category Links:** 4, 12
- **Evidence:** `voss/harness/telemetry.py:40-150` — redaction of `password`/`secret`/`token`/`api_key`/`authorization` fields and URL query/fragment/userinfo before logging.
- **Confidence:** high

### VS-006 Runtime Guardrails
- **Status:** pass | **Category Links:** 5, 15
- **Evidence:** `voss/harness/tools.py:716` (`allow_net` opt-in gate, 30s fetch timeout); `voss/harness/sandbox.py:43-73` (shell allowlist + deny-tokens + metacharacter rejection, no shell interpreter); `voss/harness/providers.py:228` (`max_tokens` cap); `voss/harness/agent.py:511-578` (`max_iterations`, `token_budget`).
- **Confidence:** high

---

## Passed Checks

- [x] SQL parameterized throughout — `crates/voss-app-core/src/agent_registry.rs:118-228` uses `rusqlite::params!`/`params_from_iter`; placeholder `format!` interpolates indices only; no raw SQL string-building in Python (Cat 1)
- [x] No unsafe HTML assignment in frontend — Solid components render via safe primitives/`textContent`; no raw-HTML property writes outside test resets (Cat 2)
- [x] No committed secrets — `.env*.local` gitignored; no real key prefixes (`sk-ant-`, `AKIA`, `ghp_`) in tracked code; test fixtures use placeholders (`sk-test`, `OLD_RT`) (Cat 3)
- [x] Harness server authenticated + localhost-bound — ASGI bearer middleware with `secrets.compare_digest()` (`voss/harness/server/app.py:51-76`); binds `127.0.0.1` ephemeral (`serve.py:39`); token = `secrets.token_urlsafe(32)`, handed off out-of-band (Cat 4)
- [x] Constant-time token comparison on the server auth path (Cat 4 / timing)
- [x] Telemetry + error responses redact secrets — `voss/harness/telemetry.py:40-150`; server errors name config *sources* (e.g. "keyring", env var name), not values (Cat 12)
- [x] API keys from keychain/env only, never hardcoded — `voss/harness/auth.py:356-359` (Cat 15)
- [x] System/user prompt roles strictly separated — `voss/harness/providers.py:200-209` (Cat 15)
- [x] Shell tool: allowlist + deny-tokens + metachar rejection, `create_subprocess_exec` (never a shell), `stdin=DEVNULL` — `voss/harness/sandbox.py:43-73`, `voss/harness/tools.py:289-291` (Cat 15)
- [x] File tools jailed to cwd — `jail_path()` `relative_to()` escape check + 30KB read cap — `voss/harness/tools.py:140-156` (Cat 15)
- [x] LLM structured output validated via Pydantic `model_validate_json`; tool args inspected before dispatch, never executed raw — `voss/harness/providers.py:447-450,670` (Cat 15)
- [x] Agent loop bounded — `max_iterations` + `token_budget` + confidence gating — `voss/harness/agent.py:511-578` (Cat 15)
- [x] Tool-arg telemetry redaction — `voss/harness/telemetry.py:105-130` (Cat 15)
- [x] `pnpm audit`: 0 vulnerabilities across 256 deps; lockfile committed; no postinstall scripts (Cat 27)
- [x] Python + Rust deps version-pinned with `uv.lock` / `Cargo.lock` (`pip-audit`/`cargo audit` not installed — not run) (Cat 27)
- [x] No `pull_request_target`; secrets only via `${{ secrets.* }}`; least-privilege `permissions:` blocks in all 6 workflows; no `github.event.*` interpolation into `run:` (Cat 31)
- [x] `release.yml` fully SHA-pinned (the model the other workflows should copy) (Cat 31)
- [x] Dependabot configured: monthly action bumps, 3-day cooldown, grouped PRs (Cat 31)
- [x] Dockerfile: pinned `python:3.12-slim` base, non-root `USER voss`, apt cache cleaned, `COPY` not `ADD`, no secrets in ENV/ARG (Cat 42)
- [x] `.dockerignore` excludes `.env`, `.git`, `node_modules`, build dirs (Cat 42)
- [x] No pickle/marshal/shelve/dill anywhere; all YAML via `yaml.safe_load()`; JSON via stdlib; Rust serde only — loaded data is app-bundled templates + local config (Cat 65)

---

## Final Tally

| Severity | Count |
|---|---|
| Critical | 0 |
| High     | 0 |
| Medium   | 14 |
| Low      | 1 |
| Passed   | 21 |

**Categories scanned:** 11 of 67   |   **Sinks traced:** 17 documented trace points (cats 1, 2, 5, 12, 15, 65)   |   **Confidence:** High (one Medium-confidence finding flagged for human verification)

### Top finding — fix this first

**[MED-001] Tag-pinned `docker/login-action@v4` in container publish workflow** — `.github/workflows/publish-container.yml:38`

A re-tagged release of this third-party action would run attacker code in the job that holds GHCR registry credentials and signs build provenance — the single highest-trust job in the repo.

**Quick fix:** SHA-pin all 13 listed actions the same way `release.yml` already does; Dependabot keeps them current.

*Scanned by Snitch for Claude Code v1.0.0 — 67 categories. https://snitchplugin.com*
