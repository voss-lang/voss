# Security Audit Report

## Summary
- **Project:** Voss
- **Scan date:** 2026-05-10
- **Scan mode:** Quick Scan
- **Selected categories:** 1 SQL Injection, 2 XSS, 3 Hardcoded Secrets, 4 Authentication, 5 SSRF, 12 Logging and Data Exposure, 15 AI API Security, 27 Dependencies, 30 Input Validation, 32 Security Headers, 33 Unused Dependencies
- **MCP status:** Not connected; embedded Snitch guidance only
- **Overall Risk:** Medium
- **Findings:** 0 Critical, 0 High, 6 Medium, 1 Low
- **Standards:** CWE Top 25 (2025), OWASP Top 10 (2025), CVSS 4.0
- **scan_mode_detected_features:** Python package, Rust workspace, Next.js static site, OAuth credential handling, AI provider integrations, package lockfiles, GitHub Actions
- **recheck_candidates:** F-001 `voss_runtime/context.py:84`, F-002 `voss/harness/auth.py:141`, F-003 `voss/bridge_server.py:59`, F-004 `site/next.config.ts:3`, F-005 `site/package-lock.json:5378`, F-006 `voss/harness/session.py:65`, F-007 `voss/harness/providers.py:177`

## Scan Comparison
- **Previous:** No previous `SECURITY_AUDIT_REPORT.md`
- **This scan:** 7 findings
- **Resolved:** N/A
- **New:** 7

## Findings

### F-001: AI provider calls can omit an output cap on the OpenAI path
- **Severity:** Medium | CVSS 4.0: ~6.0
- **CWE:** CWE-770 (Allocation of Resources Without Limits or Throttling)
- **OWASP:** A04:2025 Insecure Design
- **Category:** 15 AI API Security
- **File:** `voss_runtime/context.py:84`
- **Evidence:** `resp = await self._provider.complete(`
- **Supporting Evidence:** `voss/harness/providers.py:311` — `if max_tokens is not None:`
- **Risk:** `ContextScope.ask(...)` does not pass an output cap, and the OpenAI provider only sends a cap when the caller supplies one. A large completion can increase cost and latency for local harness runs.
- **Fix:** Add a runtime default output cap and thread it through `ContextScope.ask(...)`, harness planning calls, and provider requests. Allow callers to override it explicitly.
- **Priority:** P2 (Important)
- **Confidence:** High

### F-002: Python OAuth fallback writes refreshed credentials without owner-only permissions
- **Severity:** Medium | CVSS 4.0: ~5.5
- **CWE:** CWE-522 (Insufficiently Protected Credentials)
- **OWASP:** A07:2025 Authentication Failures
- **Category:** 4 Authentication
- **File:** `voss/harness/auth.py:141`
- **Evidence:** `path.write_text(json.dumps(blob, indent=2))`
- **Supporting Evidence:** `voss/harness/auth.py:248` — `path.write_text(json.dumps(data, indent=2))`
- **Risk:** When the macOS keychain path is unavailable, refreshed OAuth credentials are persisted to local JSON files using default process permissions. On systems with permissive umask settings, another local user could read those credentials.
- **Fix:** After writing credential files, set owner-only permissions (`0600` on Unix-like systems). Prefer atomic write-then-rename to avoid transient broad permissions.
- **Priority:** P2 (Important)
- **Confidence:** High

### F-003: Bridge file parameters are not confined to a project root
- **Severity:** Medium | CVSS 4.0: ~6.4
- **CWE:** CWE-20 (Improper Input Validation)
- **OWASP:** A05:2025 Injection
- **Category:** 30 Input Validation
- **File:** `voss/bridge_server.py:59`
- **Evidence:** `path = params["path"]`
- **Supporting Evidence:** `voss/bridge_server.py:87` — `Path(out).write_text(cg.source)`
- **Risk:** The stdio bridge accepts caller-controlled read and output paths without root confinement. If an editor integration, plugin, or local client forwards untrusted params, the bridge can read or overwrite files outside the intended project.
- **Fix:** Resolve all bridge paths against an explicit project root, reject escapes, and restrict compile output to the source tree or a configured build directory.
- **Priority:** P3 (Plan)
- **Confidence:** Medium

### F-004: Static site has no application-level web security headers
- **Severity:** Medium | CVSS 4.0: ~5.3
- **CWE:** CWE-693 (Protection Mechanism Failure)
- **OWASP:** A02:2025 Security Misconfiguration
- **Category:** 32 Security Headers
- **File:** `site/next.config.ts:3`
- **Evidence:** `const nextConfig: NextConfig = {`
- **Supporting Evidence:** `site/next.config.ts:4` — `output: "export",`
- **Risk:** The Next.js static export config does not define browser security headers. Unless the hosting layer adds them, the public site lacks defense-in-depth for script, framing, MIME sniffing, and referrer controls.
- **Fix:** Add equivalent headers at the hosting layer used for static export, such as Vercel/Netlify/Cloudflare config, or a static `_headers` file where supported.
- **Priority:** P2 (Important)
- **Confidence:** High

### F-005: Production Next dependency pulls a vulnerable PostCSS version
- **Severity:** Medium | CVSS 4.0: ~6.1
- **CWE:** CWE-1395 (Dependency With Known Vulnerabilities)
- **OWASP:** A03:2025 Software Supply Chain Failures
- **Category:** 27 Dependencies
- **File:** `site/package.json:12`
- **Evidence:** `"next": "16.2.6",`
- **Supporting Evidence:** `site/package-lock.json:5379` — `"version": "8.4.31",`
- **Risk:** `npm audit --json` reports GHSA-qx2v-qp2m-jg93 for the locked PostCSS package under Next. The vulnerable package is pulled through a production dependency.
- **Fix:** Upgrade Next to a version that no longer pins the affected PostCSS range, or apply a package-manager override once a compatible fixed dependency is available.
- **Priority:** P2 (Important)
- **Confidence:** High

### F-006: Saved sessions persist full transcripts with default file permissions
- **Severity:** Medium | CVSS 4.0: ~5.0
- **CWE:** CWE-200 (Exposure of Sensitive Information)
- **OWASP:** A09:2025 Security Logging and Alerting Failures
- **Category:** 12 Logging and Data Exposure
- **File:** `voss/harness/session.py:62`
- **Evidence:** `record.turns = history.last(10_000)  # full transcript`
- **Supporting Evidence:** `voss/harness/session.py:65` — `path.write_text(json.dumps(asdict(record), indent=2))`
- **Risk:** Session snapshots intentionally exclude provider credentials, but they persist full user and assistant transcripts in plaintext. Those transcripts can include proprietary code, prompts, or operational data, and the write path does not set owner-only permissions.
- **Fix:** Set owner-only permissions on session files, document the persistence behavior clearly, and consider opt-in redaction or an encrypted local store for transcript history.
- **Priority:** P3 (Plan)
- **Confidence:** High

### F-007: Provider failure handling can disclose upstream response bodies to CLI users
- **Severity:** Low | CVSS 4.0: ~3.7
- **CWE:** CWE-209 (Generation of Error Message Containing Sensitive Information)
- **OWASP:** A09:2025 Security Logging and Alerting Failures
- **Category:** 12 Logging and Data Exposure
- **File:** `voss/harness/providers.py:177`
- **Evidence:** `f"Anthropic OAuth call failed [{resp.status_code}]: {resp.text[:500]}"`
- **Supporting Evidence:** `voss/harness/cli.py:320` — `click.echo(f"error: {e}", err=True)`
- **Risk:** Upstream error bodies are included in exceptions and printed by the REPL. Provider error text can contain request metadata or internal diagnostics that should not be displayed by default.
- **Fix:** Print a generic provider failure message by default. Gate raw provider response snippets behind an explicit debug flag and redact credential-like values before display.
- **Priority:** P4 (Track)
- **Confidence:** Medium

## Validation Signals

### VS-001 Reproducibility Hooks
- **Status:** pass
- **Category Links:** 4, 15, 30
- **Evidence:** `tests/harness/test_auth.py:11` — `@pytest.fixture`
- **Impact:** Security-relevant harness auth paths have reproducible tests.
- **Recommended Action:** Keep auth tests paired with credential persistence changes.
- **Confidence:** high

### VS-002 Negative Testing Coverage
- **Status:** pass
- **Category Links:** 30
- **Evidence:** `tests/harness/test_sandbox.py:61` — `def test_relative_traversal_rejected(self, tmp_path: Path) -> None:`
- **Impact:** Existing sandbox code has negative path traversal coverage.
- **Recommended Action:** Add equivalent bridge-server path confinement tests when fixing F-003.
- **Confidence:** high

### VS-003 Fix Verification Path
- **Status:** warn
- **Category Links:** 27
- **Evidence:** `.github/workflows/ci.yml:26` — `- run: pytest -q -m "not live" --cov=voss_runtime --cov-report=term-missing`
- **Impact:** CI verifies tests, but the selected dependency-audit category is not enforced in CI.
- **Recommended Action:** Add npm, Python, and Rust dependency audit jobs once the chosen audit tools are available in CI.
- **Confidence:** high

### VS-005 Sensitive Flow Traceability
- **Status:** warn
- **Category Links:** 12
- **Evidence:** `voss/harness/session.py:62` — `record.turns = history.last(10_000)  # full transcript`
- **Impact:** Sensitive transcript persistence is explicit, but there is no redaction or restricted-permission check in the save path.
- **Recommended Action:** Add tests that verify session file permissions and redaction behavior.
- **Confidence:** high

### VS-006 Runtime Guardrails
- **Status:** fail
- **Category Links:** 15
- **Evidence:** `voss/harness/providers.py:311` — `if max_tokens is not None:`
- **Impact:** One provider path depends on callers to supply output caps, and current runtime callers can omit them.
- **Recommended Action:** Add default output caps at the runtime boundary and verify both provider payloads include them.
- **Confidence:** high

## Passed Checks
- **Category 1 SQL Injection:** No raw SQL construction was found in production code. The database-like hit was ChromaDB SDK usage at `voss_runtime/memory/semantic.py:81`.
- **Category 2 XSS:** Raw-render candidates in the Next.js site were generated from Shiki or static page constants; no user-controlled raw markup flow was confirmed.
- **Category 3 Hardcoded Secrets:** Credential-shaped values appeared only in tests as placeholders; production code references environment variables or local credential stores rather than committed secret values.
- **Category 5 SSRF:** Provider network calls use fixed provider endpoints or configured base URLs; no user-controlled server-side fetch target was confirmed.
- **Category 15 AI API Security:** OpenAI payloads set `store: False`, and Anthropic payloads include a default output cap. F-001 covers the remaining cap gap.
- **Category 27 Dependencies:** `site/package-lock.json` and `Cargo.lock` are committed. `npm audit --json` completed; `pip-audit` and `cargo-audit` were not installed in this environment.
- **Category 30 Input Validation:** Harness tool filesystem access uses a jail helper with negative tests. F-003 covers the bridge path gap.
- **Category 33 Unused Dependencies:** Direct site dependencies are used directly or required by the Next/React runtime relationship; no unused production dependency finding was confirmed.

## Suppressed
- None.

## SBOM
- Generated `SBOM.cdx.json` in CycloneDX 1.5 format from `site/package-lock.json`.

## Post-Fix Verification
- **2026-05-10:** F-001 through F-006 were fixed after explicit user confirmation. F-007 was not in the requested fix batch.
- **F-001:** Added default output caps to runtime config, Python runtime calls, Python harness planning, and Rust agent planning.
- **F-002:** Set owner-only permissions after Python OAuth credential file writes.
- **F-003:** Added project-root confinement for bridge source and output paths.
- **F-004:** Added static-export security headers in `site/public/_headers`.
- **F-005:** Added a package override and regenerated `site/package-lock.json`; `npm audit --json` now reports zero vulnerabilities.
- **F-006:** Set owner-only permissions after Python and Rust session snapshot writes.
- **Verification:** `arch -arm64 pytest tests/test_context.py tests/harness/test_auth.py tests/harness/test_session.py tests/test_bridge_server.py -q`, `cargo test -p voss-agent -p voss-cli`, `npm audit --json`, and `npm run build` passed.

*Scanned by Snitch -- 60 built-in categories. Create a free account at https://snitch.live for automatic updates, MCP server access, custom rules, and more.*
