# Security Audit Report

**Date:** 2026-06-17
**Scope:** Snitch Quick Scan, assumed because the interactive Snitch menu tool was unavailable.
**Worktree:** Current on-disk state on `dev`. The server-native swarm lines cited below are in commit `d06749d6`.
**Stack:** Python harness and FastAPI/SSE server, AI provider integrations, Rust crates, Tauri/Solid app, Next static site, npm/pnpm/uv/Cargo locks, GitHub Actions, Docker.

## Summary

- **Overall Risk:** High
- **Findings:** 0 Critical, 3 High, 5 Medium, 2 Low
- **Standards:** CWE Top 25 (2025), OWASP Top 10 (2025), CVSS 4.0
- **Artifacts:** `SBOM.cdx.json` regenerated from the root npm lockfile in lockfile-only mode; `VEX.cdx.json` added for dependency findings.
- **scan_mode_detected_features:** FastAPI bearer-gated harness server, agent tool loop, network fetch tool, Python regex search tools, Next static site, PostHog analytics, GitHub Actions release/container workflows, Dockerfile, `package-lock.json`, `pnpm-lock.yaml`, `uv.lock`, `Cargo.lock`.
- **recheck_candidates:** `uv.lock:20,668`, `package-lock.json:412`, `site/package.json:22`, `voss/harness/net.py:135`, `voss/harness/tools.py:700`, `voss/harness/agent.py:466`, `voss/harness/server/app.py:212,696`, `.github/workflows/*.yml uses:`, `site/vercel.json:34`, `.github/workflows/ci.yml:146`.

## High Findings

### 1. Python lock pins vulnerable `aiohttp` and `cryptography`

- **Severity:** High | CVSS 4.0: ~7.5
- **CWE:** CWE-1395 (Dependency With Known Vulnerability)
- **OWASP:** A03:2025 Software Supply Chain Failures
- **Files:** `uv.lock:20`, `uv.lock:668`, `uv.lock:1503`, `pyproject.toml:26`
- **Evidence:**
  ```toml
  name = "aiohttp"
  version = "3.13.5"
  ...
  name = "cryptography"
  version = "48.0.0"
  ...
  { name = "aiohttp" }
  ```
- **Audit result:** `uvx pip-audit --no-deps --skip-editable --disable-pip -r /tmp/voss-requirements.txt --format json` found 12 known vulnerabilities in 2 packages. `aiohttp` fixes are listed at `3.14.0`/`3.14.1`; `cryptography` fixes at `48.0.1`.
- **Reachability:** `aiohttp` is pulled by `litellm`; direct project source does not import it outside a test compatibility shim. `cryptography` is a direct runtime dependency and is imported by the trust/signature path.
- **Risk:** Known vulnerable packages remain in the production Python lock; impact ranges from DoS and cookie/header handling issues to cryptographic wheel exposure depending on runtime path.
- **Fix:** Refresh the lock after constraining `aiohttp >=3.14.1` and `cryptography >=48.0.1`, then rerun `pip-audit` and the harness test suite.
- **Priority:** P2 | **Confidence:** High | **Author:** Ben

### 2. Root npm lock pins vulnerable `form-data@4.0.5`

- **Severity:** High | CVSS 4.0: ~7.5
- **CWE:** CWE-1395 (Dependency With Known Vulnerability); advisory also maps to CWE-93
- **OWASP:** A03:2025 Software Supply Chain Failures
- **Files:** `package-lock.json:52`, `package-lock.json:412`
- **Evidence:**
  ```json
  "node_modules/@types/node-fetch": {
    "version": "2.6.13",
    "dependencies": {
      "form-data": "^4.0.4"
    }
  },
  "node_modules/form-data": {
    "version": "4.0.5"
  }
  ```
- **Audit result:** `npm audit --omit=dev` and `pnpm audit --prod` report GHSA-hmw2-7cc7-3qxx / CVE-2026-12143, fixed in `form-data >=4.0.6`.
- **Reachability:** The vulnerable package is transitive through `litellm` provider SDK dependencies. The advisory is conditional on untrusted multipart field names or filenames.
- **Risk:** If the dependency path is used with attacker-controlled multipart names, it can alter outbound multipart headers/parts sent to downstream services.
- **Fix:** Regenerate the root lock with `form-data >=4.0.6` or add a temporary package-manager override until upstream dependencies resolve it.
- **Priority:** P2 | **Confidence:** High | **Author:** Ben

### 3. Site `posthog-js` pulls vulnerable transitive telemetry packages

- **Severity:** High | CVSS 4.0: ~7.5
- **CWE:** CWE-1395 (Dependency With Known Vulnerability)
- **OWASP:** A03:2025 Software Supply Chain Failures
- **Files:** `site/package.json:22`, `site/package-lock.json:6403`, `site/package-lock.json:6466`
- **Evidence:**
  ```json
  "posthog-js": "^1.376.4"
  ...
  "node_modules/posthog-js": {
    "version": "1.376.4",
    "dependencies": {
      "@opentelemetry/exporter-logs-otlp-http": "^0.208.0",
      "dompurify": "^3.3.2"
    }
  },
  "node_modules/protobufjs": {
    "version": "7.5.9"
  }
  ```
- **Audit result:** `npm audit --omit=dev` in `site/` reports 11 production advisories: 1 high in `protobufjs`, plus moderate advisories through OpenTelemetry and DOMPurify. `posthog-js` is the direct dependency in the vulnerable range `1.319.0 - 1.379.0`.
- **Reachability:** The site initializes and uses PostHog in `site/components/PostHogProvider.tsx:36` and `site/lib/analytics.ts:14`.
- **Risk:** A production client dependency includes vulnerable transitive code; exploitability depends on whether the affected telemetry/parser paths process attacker-controlled input in the browser.
- **Fix:** Upgrade `posthog-js` past the audited range, regenerate `site/package-lock.json`, and rerun `npm audit --omit=dev` in `site/`.
- **Priority:** P2 | **Confidence:** High | **Author:** Ben

## Medium Findings

### 4. `web_fetch` lacks URL scheme and private-address validation

- **Severity:** Medium | CVSS 4.0: ~6.4
- **CWE:** CWE-918 (Server-Side Request Forgery)
- **OWASP:** A10:2025 Server-Side Request Forgery
- **Files:** `voss/harness/tools.py:830`, `voss/harness/net.py:135`, `voss/harness/permissions.py:304`
- **Evidence:**
  ```python
  async def web_fetch(url: str, timeout_s: float = 30.0) -> str:
      ...
      return await net.fetch(url, timeout_s=timeout_s)

  resp = await self._http().get(url, timeout=timeout_s)
  ```
- **Input trace:** The URL originates in an agent tool call (`step.args`) and reaches the HTTP client through `web_fetch` with no URL parse, scheme allowlist, DNS/IP resolution check, or redirect target validation. The only observed gate is whether network tools are enabled.
- **Risk:** When network access is enabled, prompt-injected or user-steered tool calls can fetch loopback, link-local, private-network, or cloud metadata targets and return the response into model context.
- **Fix:** Parse URLs before request, allow only `http`/`https`, resolve hostnames, reject loopback/link-local/private/multicast/reserved ranges for both initial and redirected targets, and consider an explicit allowlist for intended domains.
- **Priority:** P2 | **Confidence:** Medium, because the source is LLM-generated and needs human confirmation for intended local-network behavior | **Author:** Ben

### 5. Python regex tools can be CPU-exhausted by model-supplied patterns

- **Severity:** Medium | CVSS 4.0: ~5.5
- **CWE:** CWE-1333 (Inefficient Regular Expression Complexity)
- **OWASP:** A04:2025 Insecure Design
- **Files:** `voss/harness/tools.py:700`, `voss/harness/code/regex_fallback.py:31`, `voss/harness/agent.py:1493`
- **Evidence:**
  ```python
  rx = re.compile(pattern)
  ...
  if rx.search(line):

  regex = re.compile(pattern)
  ...
  if regex.search(line):
  ```
- **Input trace:** The `pattern` argument comes from an agent tool call and is invoked directly by the Python search tools. These paths use Python's backtracking regex engine and do not wrap matching with a timeout or complexity guard.
- **Risk:** A pathological pattern can monopolize CPU during a harness turn, causing local denial of service and potentially blocking a server-backed session.
- **Fix:** Cap pattern length, reject known catastrophic shapes, and execute searches through a timeout-enforced worker or a linear-time engine. Add regression tests for rejected pathological patterns.
- **Priority:** P3 | **Confidence:** High | **Author:** Ben

### 6. Tool outputs replay into later model turns without an explicit untrusted-data boundary

- **Severity:** Medium | CVSS 4.0: ~5.8
- **CWE:** CWE-1427 (Input Used for LLM Prompting)
- **OWASP:** A05:2025 Injection
- **Files:** `voss/harness/agent.py:459`, `voss/harness/agent.py:466`, `voss/templates/prompts/plan_loop_system.txt.jinja:5`, `voss/harness/net.py:174`
- **Evidence:**
  ```python
  lines = [f"Tool results for iteration {iter_rec.index}:"]
  result_str = str(tr.get("result", ""))[:400]
  lines.append(f"- {name}({args_str}) -> {result_str}")
  user_msg = {"role": "user", "content": "\n".join(lines)}
  ```
- **Input trace:** External content returned by `web_fetch` is stored as a tool result, then serialized into a later user-role message. The prompt tells the model to review prior tool results but does not explicitly mark them as untrusted data whose instructions must be ignored.
- **Risk:** Indirect prompt injection from fetched pages, files, or tool output can steer later tool calls; this chains with the URL validation gap when network tools are enabled.
- **Fix:** Wrap every tool result in a structured untrusted-data envelope with provenance, add a system-level rule that tool-result text is data only, and require confirmation or policy checks before tool results can influence network or write actions.
- **Priority:** P3 | **Confidence:** High | **Author:** Ben

### 7. Swarm owned-file assignments are recorded but not enforced by the server permission gate

- **Severity:** Medium | CVSS 4.0: ~5.6
- **CWE:** CWE-862 (Missing Authorization)
- **OWASP:** A01:2025 Broken Access Control
- **Files:** `voss/harness/server/app.py:212`, `voss/harness/server/app.py:696`, `voss/harness/swarm_store.py:134`, `voss/harness/server/sessions.py:58`
- **Evidence:**
  ```python
  gate = PermissionGate(
      mode=mode,
      store=PermissionStore.load(session.cwd),
      auto_yes=False,
  )
  ...
  builder.swarm_owned_files = task.owned_files
  ```
- **Input trace:** `/swarm/{swarm_id}/message` assignment stores `task.owned_files` on the builder session, and `build_ownership_policy()` exists, but `_run_turn()` still constructs `PermissionGate` without composing that ownership policy into `project_policy`.
- **Risk:** A builder assigned a narrow file set is not technically prevented by the server gate from attempting writes outside that file set. This is bearer-gated and limited to server-native swarm mode, but it is a real current-state enforcement gap.
- **Fix:** Compose `build_ownership_policy(session.swarm_owned_files)` into the server turn's `PermissionGate` for builder sessions, preserving existing project policy denial precedence. Add a server-route test proving a builder assigned `src/a.py` cannot write `src/b.py`.
- **Priority:** P2 | **Confidence:** High | **Author:** Ben

### 8. Non-release GitHub workflows still use tag-pinned actions

- **Severity:** Medium | CVSS 4.0: ~5.8
- **CWE:** CWE-1357 (Reliance on Insufficiently Trustworthy Component)
- **OWASP:** A08:2025 Software and Data Integrity Failures
- **Files:** `.github/workflows/ci.yml:39`, `.github/workflows/rust.yml:37`, `.github/workflows/publish-container.yml:43`, `.github/workflows/mcp-integration.yml:17`
- **Evidence:**
  ```yaml
  - uses: actions/checkout@v6.0.2
  - uses: dtolnay/rust-toolchain@stable
  uses: docker/login-action@v4
  ```
- **Scope:** `rg` found 27 tag/branch action references across `ci.yml`, `rust.yml`, `publish-container.yml`, and `mcp-integration.yml`. `release.yml` is already SHA-pinned.
- **Risk:** A moved tag or compromised action release can execute attacker-controlled code in CI. The highest-trust path is the container publish workflow, which logs into GHCR and signs provenance.
- **Fix:** Pin every `uses:` reference to a full commit SHA with a version comment, matching the release workflow's pattern. Let Dependabot keep those SHAs current.
- **Priority:** P2 | **Confidence:** High | **Author:** Ben

## Low Findings

### 9. Site CSP permits inline scripts and styles

- **Severity:** Low | CVSS 4.0: ~3.4
- **CWE:** CWE-693 (Protection Mechanism Failure)
- **OWASP:** A02:2025 Security Misconfiguration
- **Files:** `site/vercel.json:34`, `site/public/_headers:2`
- **Evidence:**
  ```json
  "Content-Security-Policy",
  "value": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; ..."
  ```
- **Risk:** Inline script allowance weakens the CSP as a defense-in-depth control if an HTML injection bug is introduced later.
- **Fix:** Move inline scripts to nonce/hash-based policy. Keep style exceptions only if the framework build truly needs them, and prefer hashes where practical.
- **Priority:** P4 | **Confidence:** High | **Author:** Ben

### 10. CI service image uses `latest`

- **Severity:** Low | CVSS 4.0: ~3.5
- **CWE:** CWE-1357 (Reliance on Insufficiently Trustworthy Component)
- **OWASP:** A03:2025 Software Supply Chain Failures
- **File:** `.github/workflows/ci.yml:146`
- **Evidence:**
  ```yaml
  image: ollama/ollama:latest
  ```
- **Risk:** Scheduled/live CI can silently pull a changed image, reducing reproducibility and making the job dependent on mutable registry state.
- **Fix:** Pin the service image to a version tag or digest and update it through Dependabot or a scheduled maintenance task.
- **Priority:** P4 | **Confidence:** High | **Author:** Ben

## Attack Chains

### Chain 1: Indirect Prompt Injection to Internal Network Fetch

- **Severity:** High (escalated from Medium + Medium)
- **Path:** Tool-output prompt injection (`voss/harness/agent.py:466`) + unvalidated network fetch (`voss/harness/net.py:135`)
- **Scenario:** Attacker-controlled page content fetched by the agent can be replayed as tool-result text in the next iteration and steer the model toward fetching an internal or metadata URL. The fetch path has no private-address block once network tools are enabled.
- **Combined CVSS:** ~7.1
- **Fix priority:** P2 -- fix URL validation first to break the exfiltration path even if indirect prompt injection remains possible.

## Validation Signals

### VS-001 Auth and Timing Controls
- **Status:** pass
- **Category Links:** 4, 44, 50
- **Evidence:** `voss/harness/server/app.py:71` uses constant-time bearer comparison; `voss/harness/server/app.py:381` installs bearer middleware globally.
- **Impact:** The local server routes, including docs and swarm routes, are not unauthenticated by default.
- **Confidence:** high

### VS-002 Dependency Audit Coverage
- **Status:** warn
- **Category Links:** 27, 69
- **Evidence:** Ran `npm audit --omit=dev` at root, `site/`, `sdk/typescript/`, and `npm/`; ran `pnpm audit --prod`; ran `pip-audit` against an exported pinned requirements file. `cargo metadata --locked` passed, but `cargo audit` is not installed.
- **Impact:** Node and Python advisories are current; Rust vulnerability coverage still needs `cargo-audit` or OSV scanning in CI/local tooling.
- **Recommended Action:** Add or run Rust SCA before treating the dependency surface as fully covered.
- **Confidence:** high

### VS-003 SBOM Coverage
- **Status:** warn
- **Category Links:** 27, 41, 69
- **Evidence:** `SBOM.cdx.json` is CycloneDX 1.5 with 66 components and 68 dependency edges, generated from the root npm lockfile in lockfile-only mode.
- **Impact:** The SBOM is useful but incomplete for the repo: it does not cover `site/package-lock.json`, `uv.lock`, or `Cargo.lock`.
- **Recommended Action:** Generate separate SBOMs per ecosystem or use a multi-ecosystem SBOM tool.
- **Confidence:** high

### VS-004 CI Baseline Controls
- **Status:** warn
- **Category Links:** 31, 45
- **Evidence:** Workflows use explicit `permissions:` and no `pull_request_target`; `release.yml` is SHA-pinned. Non-release workflows still have tag-pinned `uses:` references.
- **Impact:** CI has good least-privilege structure, but supply-chain reproducibility is uneven.
- **Confidence:** high

### VS-005 Runtime Guardrails
- **Status:** warn
- **Category Links:** 5, 15, 30, 61, 68
- **Evidence:** Network fetch has timeout, redirect cap, rate limit, TLS verification, and a 1 MB body cap; agent loops have iteration and token budgets. Missing controls are URL address validation and regex execution timeout.
- **Impact:** Existing availability and cost controls reduce blast radius but do not close the reported source-to-sink gaps.
- **Confidence:** high

## Passed Checks

- [x] SQL calls use literal statements and bound parameters in Python and Rust; no user input was found interpolated into raw SQL (Cat 1).
- [x] Raw HTML render paths in the site are fed by build-time Shiki output or static JSON-LD constants, not user-controlled content (Cat 2).
- [x] No committed production secret values found in source; local env files are ignored, and scanner hits were placeholders, tests, or env-var names (Cat 3).
- [x] Harness server auth is bearer-gated, defaults to loopback serving, and restricts CORS to localhost/Tauri origins (Cat 4, 8, 44, 50).
- [x] Telemetry/session paths redact token/key-like fields before persistence or replay where explicitly implemented (Cat 12, 15).
- [x] API keys are sourced from env/keyring/OAuth files, not hardcoded into runtime source (Cat 15, 52).
- [x] Dockerfile runs as non-root and uses selective `COPY`; `.dockerignore` excludes `.env` and `.env*.local` (Cat 42).
- [x] No production debug endpoint was found without auth; FastAPI docs are covered by the same bearer middleware (Cat 51).
- [x] YAML parsing uses the safe loader; JSON paths use standard typed decoding; no unsafe object deserialization path was found (Cat 65).
- [x] Secret comparisons on the server auth path use constant-time comparison; targeted loose-comparison searches did not find an auth bypass pattern (Cat 50, 67).

## Final Tally

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 3 |
| Medium | 5 |
| Low | 2 |
| Passed | 10 |

**Categories scanned:** 22 of 67 | **Sinks traced:** 18 | **Confidence:** High overall; Medium for the model-generated URL source in Finding 4.

### Top finding -- fix this first

**[HIGH-001] Python lock pins vulnerable `aiohttp` and `cryptography`** -- `uv.lock:20`, `uv.lock:668`

This is the broadest runtime dependency exposure and has a straightforward remediation path: refresh the Python lock with patched package versions and rerun the dependency audit plus harness tests.

**Quick fix:** constrain `aiohttp >=3.14.1` and `cryptography >=48.0.1`, regenerate `uv.lock`, then run `pip-audit` again.

*Scanned by Snitch for Claude Code v1.0.0 -- 67 categories. https://snitchplugin.com*
